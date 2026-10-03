# Proposed service-level objectives

These are design targets for an exercise, not measured commercial guarantees. Dashboards and load tests generate fresh local observations; no production figures are asserted.

## Availability SLI

For backend requests to GET `/items`, successful events are HTTP 2xx/3xx and total events are all responses for that route:

```promql
sum(increase(http_requests_total{route="/items",status=~"2..|3.."}[30d]))
/
sum(increase(http_requests_total{route="/items"}[30d]))
```

No traffic gives no meaningful SLI; do not coerce absence into 100%. Backend counters exclude edge rejection, connection failure, probes and scrapes. For user-facing edge availability, use structured Nginx access logs (Loki `count_over_time` by status), plus an external probe for requests that cannot reach Nginx at all. Do not report the backend ratio as full end-to-end availability.

## Latency SLI

Fraction of observed GET `/items` requests completed within 500 ms:

```promql
sum(increase(http_request_duration_seconds_bucket{route="/items",le="0.5"}[30d]))
/
sum(increase(http_request_duration_seconds_count{route="/items"}[30d]))
```

The latency SLI counts all completed backend responses including errors; evaluate it alongside availability so fast failures are not called healthy. Histogram p95 is useful for diagnosis but is not the fraction-based SLI. Edge timeouts/transport failures are outside this denominator and must be accounted for in an end-to-end objective.

## Exercise objective and error budget

Propose backend availability >=99.5% and latency >=95% within 500 ms over 30 days. The availability event budget is 0.005 times eligible request count; no count is invented here. A time-based objective would permit 216 minutes in 30 days at 99.5%, but only for a separately defined continuous availability probe; it is not interchangeable with a request-count budget.

For a target of 99.5%, availability burn rate is observed error fraction / 0.005. Compare short and long windows before paging. With seven-day lab telemetry retention a true rolling 30-day SLO cannot be evaluated: extend retention or store recording-rule aggregates externally first. The lab's alerts use short operational windows, not a claimed validated SLO paging policy. Low traffic, resets, missing scrapes and injected faults must be annotated. Deliberate incidents consume the measured lab budget unless an explicit policy excludes maintenance beforehand.
