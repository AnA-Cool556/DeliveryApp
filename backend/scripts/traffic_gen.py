import argparse
import asyncio
import os
import random
import sys
import time
from uuid import uuid4

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


class TrafficStats:
    def __init__(self) -> None:
        self.total = 0
        self.status_2xx = 0
        self.status_4xx = 0
        self.status_5xx = 0
        self.missing_fields = 0
        self.latencies: list[float] = []
        self.start_time = time.time()
        self.end_time = time.time()

    def record(self, status_code: int, latency_ms: float, has_missing_field: bool) -> None:
        self.total += 1
        self.latencies.append(latency_ms)
        if 200 <= status_code < 300:
            self.status_2xx += 1
        elif 400 <= status_code < 500:
            self.status_4xx += 1
        elif 500 <= status_code < 600:
            self.status_5xx += 1

        if has_missing_field:
            self.missing_fields += 1

    def p(self, percentile: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        k = (len(sorted_lat) - 1) * (percentile / 100.0)
        f = int(k)
        c = min(f + 1, len(sorted_lat) - 1)
        d0 = sorted_lat[f] * (c - k)
        d1 = sorted_lat[c] * (k - f)
        return d0 + d1

    def print_summary(self, target_rate: float) -> bool:
        duration = max(self.end_time - self.start_time, 0.001)
        actual_rate = self.total / duration
        p50 = self.p(50)
        p90 = self.p(90)
        p99 = self.p(99)

        pass_5xx = self.status_5xx == 0
        pass_p99 = p99 < 500.0
        pass_rate = actual_rate >= (target_rate * 0.85)  # Allow slight warmup tolerance
        pass_fields = self.missing_fields == 0
        overall = pass_5xx and pass_p99 and pass_fields

        print("\n" + "=" * 54)
        print("           CP2 TRAFFIC GENERATOR SUMMARY          ")
        print("=" * 54)
        print(f"Duration:            {duration:.2f} s")
        print(f"Total Requests:      {self.total}")
        print(f"Actual Throughput:   {actual_rate:.2f} req/s (Target: >= {target_rate} req/s)")
        print(f"HTTP 2xx (Success):  {self.status_2xx}")
        print(f"HTTP 4xx (Client):   {self.status_4xx}")
        print(f"HTTP 5xx (Server):   {self.status_5xx}  -> {'PASS' if pass_5xx else 'FAIL'}")
        print(f"Missing Fields:      {self.missing_fields}  -> {'PASS' if pass_fields else 'FAIL'}")
        print(f"Latency p50:         {p50:.2f} ms")
        print(f"Latency p90:         {p90:.2f} ms")
        print(f"Latency p99:         {p99:.2f} ms (Req: < 500ms) -> {'PASS' if pass_p99 else 'FAIL'}")
        print("=" * 54)
        print(f"OVERALL STATUS:      {'[PASS]' if overall else '[FAIL]'}")
        print("=" * 54 + "\n")
        return overall


async def run_traffic(
    duration: float = 30.0,
    target_rate: float = 25.0,
    base_url: str = BASE_URL,
) -> bool:
    stats = TrafficStats()
    registered_users: list[dict] = []
    stop_event = asyncio.Event()

    # Pre-register a few users so GET requests can immediately start
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        print("[INIT] Pre-registering test accounts for authenticated GET traffic...")
        for i in range(5):
            unique = uuid4().hex[:6]
            email = f"init_{unique}_{i}@cmu.example"
            resp = await client.post(
                "/api/v1/users",
                json={"email": email, "name": f"Initial User {i}", "password": "Password123!"},
            )
            if resp.status_code == 201:
                user_data = resp.json()
                # Login to get token
                login_resp = await client.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": "Password123!"},
                )
                if login_resp.status_code == 200:
                    token = login_resp.json()["access_token"]
                    registered_users.append({"id": user_data["id"], "token": token})

    print(f"[START] Firing traffic at ~{target_rate} req/s for {duration} seconds to {base_url}...")

    interval = 1.0 / target_rate

    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        async def send_one() -> None:
            # 20% POST (new registration), 80% GET (profile read with token)
            is_post = random.random() < 0.20 or len(registered_users) < 3
            start = time.perf_counter()
            missing = False

            try:
                if is_post:
                    unique = uuid4().hex[:6]
                    email = f"traffic_{unique}@cmu.example"
                    resp = await client.post(
                        "/api/v1/users",
                        json={
                            "email": email,
                            "name": f"Traffic User {unique}",
                            "password": "Password123!",
                        },
                    )
                    latency = (time.perf_counter() - start) * 1000.0
                    if resp.status_code == 201:
                        data = resp.json()
                        if not data.get("name"):
                            missing = True
                        # If dual-write or later, check if token can be obtained
                        if len(registered_users) < 50:
                            login_resp = await client.post(
                                "/api/v1/auth/login",
                                json={"email": email, "password": "Password123!"},
                            )
                            if login_resp.status_code == 200:
                                registered_users.append({
                                    "id": data["id"],
                                    "token": login_resp.json()["access_token"],
                                })
                    stats.record(resp.status_code, latency, missing)
                else:
                    user = random.choice(registered_users)
                    resp = await client.get(
                        f"/api/v1/users/{user['id']}",
                        headers={"Authorization": f"Bearer {user['token']}"},
                    )
                    latency = (time.perf_counter() - start) * 1000.0
                    if resp.status_code == 200:
                        data = resp.json()
                        if not data.get("name"):
                            missing = True
                    stats.record(resp.status_code, latency, missing)

            except Exception:
                latency = (time.perf_counter() - start) * 1000.0
                stats.record(500, latency, True)

        # Worker loop
        end_time = time.time() + duration
        last_log = time.time()

        while time.time() < end_time and not stop_event.is_set():
            asyncio.create_task(send_one())
            await asyncio.sleep(interval)

            now = time.time()
            if now - last_log >= 2.0:
                elapsed = now - stats.start_time
                current_rate = stats.total / max(elapsed, 0.001)
                p99 = stats.p(99)
                print(
                    f"  [RUNNING] {elapsed:.1f}s | Req: {stats.total} | "
                    f"Rate: {current_rate:.1f} req/s | 5xx: {stats.status_5xx} | "
                    f"p99: {p99:.1f}ms"
                )
                last_log = now

        # Drain pending requests
        await asyncio.sleep(1.0)

    stats.end_time = time.time()
    return stats.print_summary(target_rate)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zero-Downtime Migration Traffic Generator")
    parser.add_argument("--duration", type=float, default=20.0, help="Duration in seconds (default: 20)")
    parser.add_argument("--rate", type=float, default=25.0, help="Target req/s (default: 25)")
    parser.add_argument("--url", type=str, default=BASE_URL, help="Base API URL")
    args = parser.parse_args()

    success = asyncio.run(run_traffic(duration=args.duration, target_rate=args.rate, base_url=args.url))
    sys.exit(0 if success else 1)
