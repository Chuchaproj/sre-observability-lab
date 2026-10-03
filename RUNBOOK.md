# First-response runbook

1. Define impact from the client: HTTP status, latency and failed writes/queue submissions. Check the test time window, preserve logs and record the active injection.
2. Inspect `docker compose ps -a` and `docker compose logs --tail=100 nginx backend postgres redis rabbitmq`. A running process does not prove readiness or correct processing.
3. Query `up`, HTTP 5xx rate, histogram p95, DB connections, redis_up, queue depth, host/container saturation. Check exporter health before interpreting missing series. Correlate with Loki access logs for edge failures.
4. Compare `/live`, `/ready`, `/items` and `/jobs`. Liveness is deliberately independent from Redis/PostgreSQL readiness. Broker confirmation and eventual durable processing are different observations.
5. Follow the matching [incident](INCIDENTS.md). Stop only the relevant fault container or reset latency; do not restart the entire Docker host, delete volumes, or change unrelated services.
6. Run `make recover` and `make smoke`; submit a job and verify its ID appears in GET `/jobs`. Observe alert resolution after rate windows/hold timers, and verify no new errors under baseline load.
7. Record timeline, symptom, diagnostic evidence, verified root cause, recovery evidence and prevention. Do not convert a rehearsed injected fault into commercial incident experience.

Backlog investigation: inspect `docker compose exec rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers`; confirm DB health and worker logs. Poison messages need a retry/dead-letter design, which is a documented limitation of this minimal worker.

Disk-low alert: read `df -h` on the lab VM and volume sizes, check retention and log growth. Do not delete DB data or Docker-wide volumes. Back up required state before targeted retention cleanup. There is no disk-fill injection in this project.
