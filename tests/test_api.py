from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


class Connection:
    async def execute(self, sql, params=None):
        return SimpleNamespace(fetchone=AsyncMock(return_value=(7,)),
                               fetchall=AsyncMock(return_value=[(7, "lab")]))


class Pool:
    @asynccontextmanager
    async def connection(self):
        yield Connection()


@pytest.fixture
def client():
    app.state.pool = Pool()
    app.state.cache = SimpleNamespace(ping=AsyncMock(), get=AsyncMock(return_value=None),
                                      incr=AsyncMock(return_value=1), setex=AsyncMock())
    return TestClient(app)


def test_rest_and_validation(client):
    assert client.get("/ready").status_code == 200
    assert client.post("/items", json={"name": "lab"}).json() == {"id": 7, "name": "lab"}
    assert client.post("/items", json={"name": ""}).status_code == 422
    assert client.get("/items").json() == [{"id": 7, "name": "lab"}]


def test_outage_keeps_liveness(client):
    app.state.cache.ping.side_effect = ConnectionError()
    app.state.cache.get.side_effect = ConnectionError()
    assert client.get("/items").status_code == 503
    assert client.get("/ready").status_code == 503
    assert client.get("/live").status_code == 200
    assert "dependency_failures_total" in client.get("/metrics").text


def test_websocket(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_text("hello")
        assert ws.receive_json() == {"echo": "hello"}


def test_job_publish_confirmation_and_failure(client):
    app.state.channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=AsyncMock()))
    response = client.post("/jobs", json={"name": "queued"})
    assert response.status_code == 202
    assert response.json()["name"] == "queued"
    assert app.state.channel.default_exchange.publish.await_count == 1
    app.state.channel.default_exchange.publish.side_effect = ConnectionError()
    assert client.post("/jobs", json={"name": "queued"}).status_code == 503


def test_versioned_cache_and_write_invalidation(client):
    app.state.cache.get.side_effect = [b"4", b'[{"id":9,"name":"cached"}]']
    assert client.get("/items").json() == [{"id": 9, "name": "cached"}]
    assert app.state.cache.setex.await_count == 0
    assert client.post("/items", json={"name": "new"}).status_code == 201
    app.state.cache.incr.assert_awaited_once_with("items:version")


def test_worker_retries_and_deduplicates(monkeypatch):
    import asyncio

    from app.main import consume, jobs

    outcomes = []

    class Message:
        body = b'{"id":"eb7a812a-3346-4f92-a64b-f44e6260c915","name":"job"}'

        @asynccontextmanager
        async def process(self, requeue):
            assert requeue
            try:
                yield
            except Exception:
                outcomes.append("nack")
                raise
            else:
                outcomes.append("ack")

    class Messages:
        def __aiter__(self):
            self.messages = iter([Message(), Message(), Message()])
            return self

        async def __anext__(self):
            try:
                return next(self.messages)
            except StopIteration:
                raise StopAsyncIteration from None

    class Queue:
        @asynccontextmanager
        async def iterator(self):
            yield Messages()

    execute = AsyncMock(side_effect=[ConnectionError(), SimpleNamespace(rowcount=1),
                                    SimpleNamespace(rowcount=0)])

    class WorkerPool:
        @asynccontextmanager
        async def connection(self):
            yield SimpleNamespace(execute=execute)

    monkeypatch.setattr("app.main.asyncio.sleep", AsyncMock())
    before = jobs._value.get()
    asyncio.run(consume(Queue(), WorkerPool()))
    assert outcomes == ["nack", "ack", "ack"]
    assert execute.await_count == 3
    assert jobs._value.get() == before + 1
