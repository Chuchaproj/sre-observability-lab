# Observability decisions

RabbitMQ provides native Prometheus metrics and familiar queue acknowledgement semantics. At-least-once delivery with SQL UUID deduplication separates broker delivery from durable processing; there is no claim of end-to-end exactly-once. Broker/consumer failure before ack can redeliver, and POST retries can create new jobs.

RED metrics come from application middleware with bounded route labels; raw URLs and user IDs are never labels. USE metrics come from node/cAdvisor/exporters. Nginx stub_status lacks status breakdown, so structured edge logs and a Loki ruler detect 502/504. An upstream outage cannot be diagnosed only from application counters.

Faults are opt-in Compose profiles or bounded environment changes. Resource pressure is confined to a dedicated limited container. Database exhaustion auto-recovers, but can prevent the DB exporter/admin connection; missing telemetry is itself an incident signal.

Sources: [RabbitMQ monitoring](https://www.rabbitmq.com/docs/monitoring), [Prometheus histograms](https://prometheus.io/docs/practices/histograms/), [Loki Docker setup](https://grafana.com/docs/loki/latest/setup/install/docker/).

Docker Desktop with the containerd image store exposes raw cgroup IDs through cAdvisor but may not attach Docker names. Container dashboards and the CPU quota alert use exact top-level /docker/<64-hex-id> cgroups, which were observed locally. Correlate IDs using docker inspect; named-container metadata is not claimed. The node CPU/RAM/network metrics describe Linux VM interfaces. Filesystem metrics reflect the bind-mounted host root and must not be interpreted as a physical Linux server result on macOS.

Redis stores a five-second versioned list cache. PostgreSQL writes commit before generation invalidation; failed invalidation can leave stale reads until TTL expiry. Redis is deliberately required, but PostgreSQL readiness is still checked even when a cached list exists.

Schema bootstrap acquires a transaction-scoped PostgreSQL advisory lock before table creation, preventing concurrent replica DDL races. This is a minimal lab bootstrap, not a substitute for versioned production migrations.

`make secrets` scans Git history, staged changes and the current tracked and nonignored source files. Generated local credentials remain ignored; a forced/staged credential file is still inspected. There is no allowlist for credential-bearing .env paths.

The runtime uses a digest-pinned Python 3.11 / Alpine 3.24 base. The API dependency stage installs binary musllinux wheels into a virtual environment; only that environment and application source enter the runtime. No compiler or pip/setuptools/wheel is retained. This removes unused Debian system utilities instead of suppressing their findings. The trade-off is musl compatibility: new dependencies must provide matching wheels or require an explicitly reviewed build stage. Native arm64 execution is checked locally; amd64 execution belongs to the first hosted CI run.

The redundant NginxUpstreamErrors Prometheus alert was removed: backend metrics cannot measure rejected gateway requests. The dedicated Loki NginxGatewayErrors rule measures those log events. Resource-pressure and DB-blocker helpers reuse the audited backend runtime instead of an unrelated older Python image.
