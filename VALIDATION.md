# Local validation — sre-observability-lab

## Validation scope

Application tests, static checks, local runtime exercises and an all-severity Trivy scan were completed on 2026-10-03. [SECURITY.md](SECURITY.md) records the image identity, findings and scope limitations.

## Observed results

| Check | Result | Evidence / scope |
|---|---|---|
| Application tests | PASS | 6 tests including cache, queue publisher failure, consumer retry/nack, acknowledgement and duplicate counter semantics. One development TestClient/httpx deprecation warning. |
| Static checks | PASS | Ruff, ShellCheck, yamllint, Hadolint and actionlint. |
| Docker / Compose | PASS | Final custom backend built; Compose config accepted; complete stack became healthy; API exact write/read smoke and WebSocket passed. |
| Metrics | PASS | Eight targets up: backend, containers, nginx, node, postgres, prometheus, rabbitmq, redis. HTTP counters/histograms, CPU/RAM/disk/network, raw container cgroups, database connections, Redis memory, broker queue and Nginx connections returned real series. |
| Grafana / logs | PASS | Provisioned SRE dashboard read back via API; Loki received app and edge logs, including gateway-error queries. |
| Alert configuration | PASS | Promtool config and 12 Prometheus rules (one backend-error alert avoids duplicate conditions); outage rule unit test. Loki gateway-error rule configured. Not every threshold was driven to firing. |
| Latency incident | PASS | Configured 1 s delay: observed 1.032 s HTTP response; recovery smoke passed. |
| PostgreSQL exhaustion | PASS | Helper held 29 connections; 20 client requests returned 503/504; recovery smoke passed. |
| Redis outage | PASS | API 503, readiness 503 and liveness 200; dependency restoration and smoke passed. |
| Gateway incident | PASS | Stopped backend produced Nginx 502; Loki query returned two streams; recovery passed. During startup/DNS transition 504 is also possible. |
| Resource pressure | PASS | Dedicated container capped at 0.25 CPU / 64 MiB, bounded to 120 s. Observed 0.24999 core and 51.55 MiB; recovery passed. Host disk was not filled. |
| Broker runtime | PASS | Publisher-confirmed job UUID was processed and persisted. Under PostgreSQL exhaustion consumer emitted retry events; queued job persisted after recovery with the SAME backend container ID (no backend restart). |
| Clean k6 baseline | PASS | Isolated 5 VUs / 2 min: 2791 requests, 0 failed, all checks passed, p95 25.17 ms; both thresholds passed. See [measured snapshot](docs/load-test.md). |
| Runtime dependency audit | PASS | Pinned Python runtime graph: pip-audit reported no known vulnerabilities. See SECURITY.md for the separate OS scan scope. |
| Kubernetes / Helm / Terraform / Ansible | NOT APPLICABLE | This Compose lab does not use these tools. |

## Corrections and measurement discipline

An initial load run overlapped recovery work and recorded nine errors; another run was interrupted to free resources for Kubernetes. Neither is used as the normal-operation baseline. The reported final run was isolated after recovery and before any cleanup. An early incident assertion assumed only 502 and failed on a possible 504; the recovered gateway exercise and log query were rerun successfully. These corrected local checks are not production acceptance evidence.

The consumer originally could stop on a DB failure; it now requeues, logs the exception type and stays alive. Unit tests and a real PostgreSQL exhaustion/recovery check verify the behavior. Duplicate deliveries do not double-count completed jobs.

## NOT TESTED and remaining limitations

- Native Linux exporter/host monitoring. Docker Desktop exposes raw cgroup IDs; named container labels were unavailable in its cAdvisor Docker factory. CPU/RAM/network describe the Linux VM; some filesystem mounts reflect macOS bind mounts.
- Full alert firing/clearing coverage, external notification delivery and Loki ruler end-to-end notification acceptance.
- Thirty-day SLO evaluation. Seven-day default retention is insufficient for the proposed 30-day window; extend retention/storage first.
- Backups/restoration, broker failover, multi-host HA and poison-message/dead-letter handling. In-process worker has unbounded transient retries and no outbox.
- Authentication/TLS and production least-privilege monitoring role are not implemented. Privileged cAdvisor and Docker socket access require a trusted lab host.
- No host disk exhaustion was attempted: the chosen safe resource-pressure alternative meets the incident scope.

The lab containers and network were removed after validation; named data volumes remain.

## Validation boundary

Date: 2026-10-03. Host: macOS, 8 GiB physical RAM; Docker Desktop Linux VM approximately 3.8 GiB. Runtime checks were performed sequentially. Docker 29.5.3, Compose 5.1.4, Python 3.11, Trivy 0.75.0 and Gitleaks 8.30.0 were available. No paid resources were created. PASS means the stated check was observed locally, not that every production failure mode is covered.

`make install`, application tests, Docker builds and the documented local deployment/smoke/cleanup paths were exercised.

## Security checks

- PASS: Gitleaks scanned local Git history, staged changes and the tracked sources. No finding was reported. This is a detector result, not proof that every possible secret is absent.
- PASS: `.env`, environment variants, virtual environments, generated artifacts and private key files are ignored; `.env.example` is tracked. No local credential file is included in the tracked sources.
- PASS WITH SCOPE LIMITS: the final Alpine custom runtime scan reports zero detected vulnerabilities. The previous Debian image had 44 HIGH; the audit investigates every unique CVE and removes affected base packages without suppressions. See [security report](docs/security-scan.md). Third-party stack images and exploitability were not audited. The CI custom-runtime vulnerability gate blocks HIGH/CRITICAL; secret scanning also blocks.
- PASS: actionlint and YAML lint checked workflow syntax. Hosted GitHub Actions execution and environment protection are **NOT TESTED**; local syntax checks do not establish runner behavior or reviewer enforcement.

## Recheck

Run `make install test lint secrets` in a clean checkout with the prerequisites from README. Generate local credentials where required; do not copy someone else's `.env`. Follow README deployment and cleanup commands one project at a time. Image findings and dependency versions are a dated snapshot; refresh scans before wider deployment or dependency changes.

Final runtime recheck: complete rebuilt stack, eight healthy scrape targets and Grafana/Loki read-back passed. Promtool validated 12 rules and its outage unit scenario. All five incidents and exact write/read recovery passed: 1.032 s latency, PostgreSQL 503/504, Redis items/readiness 503 with liveness 200, Nginx 502 with Loki streams, resource helper 0.24999 core and 51.55 MiB under 64 MiB while API stayed 200. Consumer recovered a queued job after DB exhaustion without container replacement. Final isolated k6 run: 2791 requests, zero failures, p95 25.17 ms, maximum 695.33 ms; both declared thresholds passed. This is not a maximum-latency guarantee.

Additional telemetry check: the latency request increased the histogram sum beyond one second; Redis and PostgreSQL outages produced their dependency failure counters. See [incident evidence](docs/incident-evidence.json). No assertion is made that every alert fired or external delivery occurred.
