# Local validation — sre-observability-lab

## Observed results

| Check | Result | Evidence / scope |
|---|---|---|
| Application tests | PASS | 6 tests including cache, queue publisher failure, consumer retry/nack, acknowledgement and duplicate counter semantics. One development TestClient/httpx deprecation warning. |
| Static checks | PASS | Ruff, ShellCheck, yamllint, Hadolint and actionlint. |
| Docker / Compose | PASS | Final custom backend built; Compose config accepted; complete stack became healthy; API exact write/read smoke and WebSocket passed. |
| Metrics | PASS | Eight targets up: backend, containers, nginx, node, postgres, prometheus, rabbitmq, redis. HTTP counters/histograms, CPU/RAM/disk/network, raw container cgroups, database connections, Redis memory, broker queue and Nginx connections returned real series. |
| Grafana / logs | PASS | Provisioned SRE dashboard read back via API; Loki received app and edge logs, including gateway-error queries. |
| Alert configuration | PASS | Promtool config and 13 Prometheus rules; outage rule unit test. Loki gateway-error rule configured. Not every threshold was driven to firing. |
| Latency incident | PASS | Configured 1 s delay: observed 1.127 s HTTP response; recovery smoke passed. |
| PostgreSQL exhaustion | PASS | Helper held 29 connections; 20 client requests returned 503/504; recovery smoke passed. |
| Redis outage | PASS | API 503, readiness 503 and liveness 200; dependency restoration and smoke passed. |
| Gateway incident | PASS | Stopped backend produced Nginx 502; Loki query returned two streams; recovery passed. During startup/DNS transition 504 is also possible. |
| Resource pressure | PASS | Dedicated container capped at 0.25 CPU / 64 MiB, bounded to 120 s. Observed 0.25013 core and 52.14 MiB; recovery passed. Host disk was not filled. |
| Broker runtime | PASS | Publisher-confirmed job UUID was processed and persisted. Under PostgreSQL exhaustion consumer emitted retry events; queued job persisted after recovery with the SAME backend container ID (no backend restart). |
| Clean k6 baseline | PASS | Isolated 5 VUs / 2 min: 2796 requests, 0 failed, all checks passed, p95 22.32 ms; both thresholds passed. See [measured snapshot](docs/load-test.md). |
| Runtime dependency audit | PASS | Pinned Python runtime graph: pip-audit reported no known vulnerabilities. OS scan has findings below. |
| Kubernetes / Helm / Terraform / Ansible | NOT APPLICABLE | They are implemented and validated in the other portfolio repositories. |

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

The lab containers and network were removed after validation; named data volumes remain. Unrelated Grandora containers remained healthy.

## Validation boundary

Date: 2026-10-03. Host: macOS, 8 GiB physical RAM; Docker Desktop Linux VM approximately 3.8 GiB. Runtime checks were performed sequentially. Docker 29.5.3, Compose 5.1.4, Python 3.11, Trivy 0.75.0 and Gitleaks 8.30.0 were available. No paid resources were created. PASS means the stated check was observed locally, not that every production failure mode is covered.

`make install`, application tests, Docker builds and the documented local deployment/smoke/cleanup paths were exercised. Sources are independently versioned in this repository. Commit dates are real; no history was squashed or backdated. GitHub publication is pending explicit approval.

## Security and publication checks

- PASS: Gitleaks scanned local Git history, staged changes and the tracked publication tree. No finding was reported. This is a detector result, not proof that every possible secret is absent.
- PASS: `.env`, environment variants, virtual environments, generated artifacts and private key files are ignored; `.env.example` is tracked. No local credential file is included in the publication tree.
- EXECUTED WITH FINDINGS: custom runtime image Trivy scan reported 44 HIGH, 60 MEDIUM, 60 LOW and 2 UNKNOWN findings; zero CRITICAL. The HIGH findings have no fixed package version in the scan result. See [security report](docs/security-scan.md). Third-party stack images and exploitability were not audited. The CI vulnerability scan reports findings without blocking; secret scanning blocks.
- PASS: actionlint and YAML lint checked workflow syntax. GitHub Actions execution, environment protection and CI status badges are **NOT TESTED** because the repository has not been published. No badge asserts a successful remote check.

## Recheck

Run `make install test lint secrets` in a clean checkout with the prerequisites from README. Generate local credentials where required; do not copy someone else's `.env`. Follow README deployment and cleanup commands one project at a time. Image findings and dependency versions are a dated snapshot; refresh scans before publication or wider use.
