# Measured local load snapshot

Date: 2026-10-03. This is a homelab measurement on an 8 GiB Mac with a Docker Desktop Linux VM of approximately 3.8 GiB. Other portfolio stacks were stopped. It is not a production benchmark, capacity plan or cross-hardware comparison.

After recovery and a successful smoke test, `make load` ran the committed k6 script: five virtual users for two minutes, repeated reads through Nginx, and a 200 ms pause per iteration. No fault was injected or other deployment performed during this run.

| Metric | Observed |
|---|---:|
| Requests / completed iterations | 2796 |
| Failed HTTP requests | 0 / 2796 (0%) |
| Successful checks | 2796 / 2796 |
| Request rate | 23.27388 / s |
| Request duration median | 11.14 ms |
| Request duration p95 | 22.32 ms |
| Request duration maximum | 248.61 ms |
| Interrupted iterations | 0 |

Thresholds `http_req_failed < 1%` and `http_req_duration p95 < 500 ms` both passed. This workload mainly measures warm read/cache behavior; it does not establish write throughput, broker capacity, CPU autoscaling or maximum sustainable load. The rate includes the explicit pause and is not a saturation result. Re-run in your own environment; do not reuse these numbers as production evidence.
