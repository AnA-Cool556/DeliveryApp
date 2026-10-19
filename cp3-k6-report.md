# CP3 k6 Performance Results

| Metric | Result | Target | Status |
| --- | ---: | ---: | --- |
| Load profile | 50 VUs for 180 seconds (195 seconds total incl. graceful stop) | 50 VUs for 180 seconds | Pass |
| Requests | 12464 total | — | Recorded |
| Fresh orders | 6232 created / 6232 cancelled | Each create gets one cancel | Pass |
| Throughput | 64.05 requests/s | — | Recorded |
| 10-second RPS range | 49.10-73.20 requests/s (37.1% of mean) | See chart | Variable |
| p95 latency | 537.14 ms | < 200 ms | Fail |
| p99 latency | 1014.01 ms | < 500 ms | Fail |
| HTTP error rate | 0.000% | < 1% | Pass |
| Overall latency/error thresholds | Fail | All targets above | Fail |

Each iteration creates a new order with a unique idempotency key and cancels that order once. The 50 VUs each use a different product/inventory row to avoid serializing all writes on one stock row. Supply 50 distinct active product IDs for the same restaurant, each with stock available throughout the run.

Test deployment: API and databases in Docker Compose, with k6 running in the Grafana k6 container on Windows.

## Latency chart

```mermaid
xychart-beta
    x-axis ["p95 actual", "p95 target", "p99 actual", "p99 target"]
    y-axis "Latency (ms)" 0 --> 1150
    bar [537.14, 200, 1014.01, 500]
```

## Error-rate chart

```mermaid
xychart-beta
    x-axis ["Actual", "Target"]
    y-axis "HTTP errors (%)" 0 --> 1.1
    bar [0.000, 1]
```

## Request throughput over time

```mermaid
xychart-beta
    x-axis "Time (seconds)" ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "110", "120", "130", "140", "150", "160", "170"]
    y-axis "Requests/s" 0 --> 80
    line [67.60, 71.60, 49.10, 73.20, 72.50, 55.00, 69.70, 66.50, 56.00, 69.70, 67.60, 58.10, 59.00, 71.40, 70.70, 51.70, 69.40, 70.50]
```
