# CP3 k6 Performance Results

| Metric | Result | Target | Status |
| --- | ---: | ---: | --- |
| Load profile | 50 VUs for 181 seconds | 50 VUs for 180 seconds | Pass |
| Requests | 8,838 total | — | Recorded |
| Throughput | 48.77 requests/s | Stable over 3 minutes | Recorded |
| p95 latency | 31.48 ms | < 200 ms | Pass |
| p99 latency | 104.09 ms | < 500 ms | Pass |
| HTTP error rate | 0.000% | < 1% | Pass |
| Overall latency/error thresholds | Pass | All targets above | Pass |

Tested locally on Windows with Docker Desktop; API and PostgreSQL ran in Compose, and k6 ran in the Grafana k6 container.

## Latency chart

```mermaid
xychart-beta
    x-axis ["p95 actual", "p95 target", "p99 actual", "p99 target"]
    y-axis "Latency (ms)" 0 --> 550
    bar [31.48, 200, 104.09, 500]
```

## Error-rate chart

```mermaid
xychart-beta
    x-axis ["Actual", "Target"]
    y-axis "HTTP errors (%)" 0 --> 1.1
    bar [0.000, 1]
```
