import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = (__ENV.API_URL || "http://127.0.0.1:8000/api/v1/orders").replace(/\/$/, "");
const token = __ENV.API_TOKEN;
const orderId = __ENV.ORDER_ID;

if (!token || !orderId) {
  throw new Error("Set API_TOKEN and ORDER_ID for an existing customer order.");
}

export const options = {
  vus: 50,
  duration: "3m",
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
  thresholds: {
    http_req_duration: ["p(95)<200", "p(99)<500"],
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const headers = { Authorization: `Bearer ${token}` };
  let response;

  if (__ITER % 5 === 0) {
    response = http.post(`${baseUrl}/${orderId}/cancel`, null, { headers });
    check(response, {
      "cancel returns 200": (res) => res.status === 200,
    });
  } else {
    response = http.get(`${baseUrl}?limit=20`, { headers });
    check(response, {
      "order list returns 200": (res) => res.status === 200,
      "order list has items": (res) => {
        try {
          return Array.isArray(res.json("items"));
        } catch {
          return false;
        }
      },
    });
  }

  sleep(1);
}

export function handleSummary(data) {
  const latency = data.metrics.http_req_duration.values;
  const requestsPerSecond = data.metrics.http_reqs.values.rate;
  const errorRate = data.metrics.http_req_failed.values.rate * 100;
  const p95 = latency["p(95)"];
  const p99 = latency["p(99)"];
  const durationSeconds = data.state.testRunDurationMs / 1000;
  const latencyMax = Math.ceil(Math.max(500, p99) * 1.1 / 50) * 50;
  const errorMax = Math.ceil(Math.max(1, errorRate) * 1.1 * 10) / 10;
  const passed = p95 < 200 && p99 < 500 && errorRate < 1;
  const report = `# CP3 k6 Performance Results

| Metric | Result | Target | Status |
| --- | ---: | ---: | --- |
| Load profile | 50 VUs for ${durationSeconds.toFixed(0)} seconds | 50 VUs for 180 seconds | Pass |
| Requests | ${data.metrics.http_reqs.values.count} total | — | Recorded |
| Throughput | ${requestsPerSecond.toFixed(2)} requests/s | Stable over 3 minutes | Recorded |
| p95 latency | ${p95.toFixed(2)} ms | < 200 ms | ${p95 < 200 ? "Pass" : "Fail"} |
| p99 latency | ${p99.toFixed(2)} ms | < 500 ms | ${p99 < 500 ? "Pass" : "Fail"} |
| HTTP error rate | ${errorRate.toFixed(3)}% | < 1% | ${errorRate < 1 ? "Pass" : "Fail"} |
| Overall latency/error thresholds | ${passed ? "Pass" : "Fail"} | All targets above | ${passed ? "Pass" : "Fail"} |

Tested locally on Windows with Docker Desktop; API and PostgreSQL ran in Compose, and k6 ran in the Grafana k6 container.

## Latency chart

\`\`\`mermaid
xychart-beta
    x-axis ["p95 actual", "p95 target", "p99 actual", "p99 target"]
    y-axis "Latency (ms)" 0 --> ${latencyMax}
    bar [${p95.toFixed(2)}, 200, ${p99.toFixed(2)}, 500]
\`\`\`

## Error-rate chart

\`\`\`mermaid
xychart-beta
    x-axis ["Actual", "Target"]
    y-axis "HTTP errors (%)" 0 --> ${errorMax}
    bar [${errorRate.toFixed(3)}, 1]
\`\`\`
`;

  return {
    "cp3-k6-summary.json": JSON.stringify(data, null, 2),
    "cp3-k6-report.md": report,
  };
}
