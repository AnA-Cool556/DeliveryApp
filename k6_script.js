import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const baseUrl = (__ENV.API_URL || "http://127.0.0.1:8000/api/v1/orders").replace(/\/$/, "");
const token = __ENV.API_TOKEN;
const restaurantId = __ENV.RESTAURANT_ID;
const productIds = (__ENV.PRODUCT_IDS || "")
  .split(",")
  .map((productId) => productId.trim())
  .filter(Boolean);
const runId = __ENV.RUN_ID;
const startedAt = Date.now();
const windowSeconds = 10;
const testDurationSeconds = 180;
const requestWindows = Array.from(
  { length: 18 },
  (_, index) => new Counter(`requests_window_${String(index).padStart(2, "0")}`),
);

if (!token || !restaurantId || productIds.length < 50 || !runId) {
  throw new Error("Set API_TOKEN, RESTAURANT_ID, 50 PRODUCT_IDS, and a unique RUN_ID for this benchmark.");
}
if (new Set(productIds).size !== productIds.length) {
  throw new Error("PRODUCT_IDS must contain unique product IDs.");
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
  const productId = productIds[(__VU - 1) % productIds.length];
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "Idempotency-Key": `k6-${runId}-${__VU}-${__ITER}`,
  };
  const body = JSON.stringify({
    restaurant_id: restaurantId,
    items: [{ product_id: productId, quantity: 1 }],
  });
  const createStartedAt = Date.now();
  const created = http.post(baseUrl, body, { headers });
  recordRequest(createStartedAt);
  const createdSuccessfully = check(created, {
    "order create returns 201": (res) => res.status === 201,
  });

  if (createdSuccessfully) {
    const orderId = created.json("id");
    const cancelStartedAt = Date.now();
    const cancelled = http.post(`${baseUrl}/${orderId}/cancel`, null, {
      headers: { Authorization: `Bearer ${token}` },
    });
    recordRequest(cancelStartedAt);
    check(cancelled, {
      "order cancel returns 200": (res) => res.status === 200,
      "order is cancelled": (res) => res.json("status") === "CANCELLED",
    });
  }

  sleep(1);
}

function recordRequest(requestStartedAt) {
  const elapsedSeconds = (requestStartedAt - startedAt) / 1000;
  if (elapsedSeconds < 0 || elapsedSeconds >= testDurationSeconds) {
    return;
  }
  const windowIndex = Math.floor(elapsedSeconds / windowSeconds);
  requestWindows[windowIndex].add(1);
}

export function handleSummary(data) {
  const latency = data.metrics.http_req_duration.values;
  const requestsPerSecond = data.metrics.http_reqs.values.rate;
  const errorRate = data.metrics.http_req_failed.values.rate * 100;
  const p95 = latency["p(95)"];
  const p99 = latency["p(99)"];
  const durationSeconds = data.state.testRunDurationMs / 1000;
  const loadProfilePassed =
    data.metrics.vus_max.values.max === 50 && durationSeconds >= 180;
  const createdOrders = data.root_group.checks.find(
    (result) => result.name === "order create returns 201",
  ).passes;
  const cancelledOrders = data.root_group.checks.find(
    (result) => result.name === "order cancel returns 200",
  ).passes;
  const latencyMax = Math.ceil(Math.max(500, p99) * 1.1 / 50) * 50;
  const errorMax = Math.ceil(Math.max(1, errorRate) * 1.1 * 10) / 10;
  const passed = p95 < 200 && p99 < 500 && errorRate < 1;
  const windowRates = requestWindows.map((_, index) => {
    const metric = data.metrics[`requests_window_${String(index).padStart(2, "0")}`];
    return (metric ? metric.values.count : 0) / windowSeconds;
  });
  const rpsMax = Math.max(1, ...windowRates);
  const rpsAxisMax = Math.ceil(rpsMax / 10) * 10;
  const windowLabels = requestWindows.map((_, index) => `"${index * windowSeconds}"`).join(", ");
  const rpsValues = windowRates.map((rate) => rate.toFixed(2)).join(", ");
  const lowestWindowRps = Math.min(...windowRates);
  const highestWindowRps = Math.max(...windowRates);
  const meanWindowRps = windowRates.reduce((total, rate) => total + rate, 0) / windowRates.length;
  const rpsSpreadPercent = meanWindowRps
    ? ((highestWindowRps - lowestWindowRps) / meanWindowRps) * 100
    : 0;
  const report = `# CP3 k6 Performance Results

| Metric | Result | Target | Status |
| --- | ---: | ---: | --- |
| Load profile | 50 VUs for 180 seconds (${durationSeconds.toFixed(0)} seconds total incl. graceful stop) | 50 VUs for 180 seconds | ${loadProfilePassed ? "Pass" : "Fail"} |
| Requests | ${data.metrics.http_reqs.values.count} total | — | Recorded |
| Fresh orders | ${createdOrders} created / ${cancelledOrders} cancelled | Each create gets one cancel | ${createdOrders > 0 && createdOrders === cancelledOrders ? "Pass" : "Fail"} |
| Throughput | ${requestsPerSecond.toFixed(2)} requests/s | — | Recorded |
| 10-second RPS range | ${lowestWindowRps.toFixed(2)}-${highestWindowRps.toFixed(2)} requests/s (${rpsSpreadPercent.toFixed(1)}% of mean) | See chart | ${rpsSpreadPercent < 20 ? "Steady" : "Variable"} |
| p95 latency | ${p95.toFixed(2)} ms | < 200 ms | ${p95 < 200 ? "Pass" : "Fail"} |
| p99 latency | ${p99.toFixed(2)} ms | < 500 ms | ${p99 < 500 ? "Pass" : "Fail"} |
| HTTP error rate | ${errorRate.toFixed(3)}% | < 1% | ${errorRate < 1 ? "Pass" : "Fail"} |
| Overall latency/error thresholds | ${passed ? "Pass" : "Fail"} | All targets above | ${passed ? "Pass" : "Fail"} |

Each iteration creates a new order with a unique idempotency key and cancels that order once. The 50 VUs each use a different product/inventory row to avoid serializing all writes on one stock row. Supply 50 distinct active product IDs for the same restaurant, each with stock available throughout the run.

Test deployment: API and databases in Docker Compose, with k6 running in the Grafana k6 container on Windows.

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

## Request throughput over time

\`\`\`mermaid
xychart-beta
    x-axis "Time (seconds)" [${windowLabels}]
    y-axis "Requests/s" 0 --> ${rpsAxisMax}
    line [${rpsValues}]
\`\`\`
`;

  return {
    "cp3-k6-summary.json": JSON.stringify(data, null, 2),
    "cp3-k6-report.md": report,
  };
}
