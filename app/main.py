import asyncio
import json
import logging
import os
import uuid

import aio_pika
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field
from redis.asyncio import Redis

logger = logging.getLogger("platform")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
log_dir = os.getenv("LOG_DIR")
if log_dir:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.addHandler(logging.FileHandler(Path(log_dir) / "app.log"))
requests = Counter("http_requests_total", "HTTP responses", ["method", "route", "status"])
latency = Histogram("http_request_duration_seconds", "HTTP duration", ["method", "route"],
                    buckets=[.01, .05, .1, .25, .5, 1, 2, 5, 10])
failures = Counter("dependency_failures_total", "Failed dependency operations", ["dependency"])


@asynccontextmanager
async def lifespan(app):
    pool = AsyncConnectionPool(os.environ["DATABASE_URL"], min_size=1, max_size=5,
                               timeout=2, open=False, kwargs={"connect_timeout": 3, "application_name": "lab-backend"})
    cache = Redis.from_url(os.environ["REDIS_URL"], socket_timeout=2, socket_connect_timeout=2)
    await pool.open()
    app.state.pool, app.state.cache = pool, cache
    try:
        await pool.wait(timeout=30)
        async with pool.connection() as conn:
            await conn.execute("CREATE TABLE IF NOT EXISTS items (id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL)")
        async with pool.connection() as conn:
            await conn.execute("CREATE TABLE IF NOT EXISTS processed_jobs (id UUID PRIMARY KEY, name TEXT NOT NULL)")
        broker = await aio_pika.connect_robust(os.environ["AMQP_URL"], timeout=5)
        channel = await broker.channel(publisher_confirms=True)
        await channel.set_qos(prefetch_count=5)
        queue = await channel.declare_queue("jobs", durable=True)
        app.state.channel = channel
        worker = asyncio.create_task(consume(queue, pool))
        try:
            yield
        finally:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            await broker.close()
    finally:
        await cache.aclose()
        await pool.close()


app = FastAPI(title="Homelab platform", lifespan=lifespan)


@app.middleware("http")
async def observe(request, call_next):
    start = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = getattr(request.scope.get("route"), "path", "unmatched")
        if route not in ("/metrics", "/live", "/ready"):
            duration = time.monotonic() - start
            requests.labels(request.method, route, str(status)).inc()
            latency.labels(request.method, route).observe(duration)
            logger.info(json.dumps({"method": request.method, "route": route,
                                    "status": status, "duration_seconds": duration}))


@app.get("/live")
async def live():
    return {"status": "alive"}


@app.get("/ready")
async def ready():
    try:
        async with app.state.pool.connection() as conn:
            await conn.execute("SELECT 1")
        await app.state.cache.ping()
    except Exception:
        raise HTTPException(503, "Dependencies unavailable") from None
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")


class Item(BaseModel):
    name: str = Field(min_length=1, max_length=200)


@app.post("/items", status_code=201)
async def create_item(item: Item):
    try:
        async with app.state.pool.connection() as conn:
            cursor = await conn.execute("INSERT INTO items(name) VALUES (%s) RETURNING id", (item.name,))
            row = await cursor.fetchone()
    except Exception:
        failures.labels("postgres").inc()
        raise HTTPException(503, "Database unavailable") from None
    # Invalidate cache after the transaction commits; reads use DB as source of truth.
    try:
        await app.state.cache.incr("items:version")
    except Exception:
        failures.labels("redis").inc()
        logger.warning('cache_invalidation_failed')
    return {"id": row[0], "name": item.name}


@app.get("/items")
async def list_items():
    delay = float(os.getenv("LAB_LATENCY_SECONDS", "0"))
    if delay:
        await asyncio.sleep(min(delay, 10))
    # Redis is a required dependency in this lab so its outage is observable as 503.
    try:
        version = await app.state.cache.get("items:version") or b"0"
        if isinstance(version, bytes):
            version = version.decode()
        cache_key = f"items:{version}"
        cached = await app.state.cache.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        failures.labels("redis").inc()
        raise HTTPException(503, "Cache unavailable") from None
    try:
        async with app.state.pool.connection() as conn:
            cursor = await conn.execute("SELECT id, name FROM items ORDER BY id LIMIT 100")
            rows = await cursor.fetchall()
    except Exception:
        failures.labels("postgres").inc()
        raise HTTPException(503, "Database unavailable") from None
    result = [{"id": row[0], "name": row[1]} for row in rows]
    try:
        await app.state.cache.setex(cache_key, 5, json.dumps(result))
    except Exception:
        failures.labels("redis").inc()
        logger.warning("cache_fill_failed")
    return result


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            message = await ws.receive_text()
            await ws.send_json({"echo": message})
    except WebSocketDisconnect:
        return


jobs = Counter("jobs_processed_total", "Durably processed jobs")


async def consume(queue, pool):
    async with queue.iterator() as messages:
        async for message in messages:
            async with message.process(requeue=True):
                payload = json.loads(message.body)
                async with pool.connection() as conn:
                    await conn.execute(
                        "INSERT INTO processed_jobs(id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                        (payload["id"], payload["name"]))
                jobs.inc()
                logger.info(json.dumps({"event": "job_processed", "id": payload["id"]}))


@app.post("/jobs", status_code=202)
async def enqueue(item: Item):
    payload = {"id": str(uuid.uuid4()), "name": item.name}
    try:
        await asyncio.wait_for(app.state.channel.default_exchange.publish(
            aio_pika.Message(json.dumps(payload).encode(),
                             delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key="jobs"), timeout=3)
    except Exception:
        failures.labels("rabbitmq").inc()
        raise HTTPException(503, "Broker unavailable") from None
    return payload


@app.get("/jobs")
async def processed_jobs():
    try:
        async with app.state.pool.connection() as conn:
            cursor = await conn.execute("SELECT id, name FROM processed_jobs ORDER BY id LIMIT 100")
            rows = await cursor.fetchall()
    except Exception:
        raise HTTPException(503, "Database unavailable") from None
    return [{"id": str(row[0]), "name": row[1]} for row in rows]
