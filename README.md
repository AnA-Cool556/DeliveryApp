# DeliveryApp

Food delivery around Chiang Mai University. The setup and Orders API are implemented. Users, Products, and Tracking APIs are still pending.

## Getting started

Install Git and Docker Desktop, then run:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

On PowerShell, use `Copy-Item .env.example .env`. Change the local passwords in `.env` and keep that file out of Git. If ports `5432` or `27017` are unavailable, change `POSTGRES_PORT` or `MONGO_PORT` in `.env`. Replace `AUTH_SECRET` with a long random value shared by the API and the future Users token issuer.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| PostgreSQL | localhost:5432 |
| MongoDB | localhost:27017 |

`curl http://localhost:8000/health` should return `{"status":"ok"}`. This checks the API only; use `docker compose ps` to check the databases. Stop services with `docker compose down`; named volumes preserve data.

Apply the relational baseline migration:

```bash
docker compose exec api alembic upgrade head
```

The Orders API reads catalog documents from MongoDB and updates stock and orders in one PostgreSQL transaction. It requires an HS256 customer bearer token and an `Idempotency-Key` for order creation. Until the Users API and catalog seed are added, run the disposable integration smoke test after migration:

```bash
docker compose exec api python -m scripts.smoke_orders
```

The script creates temporary users, a restaurant, inventory, and products; tests order creation, replay, stock conflicts, concurrent requests, cancellation, and access control; then removes its data. Seed and verification scripts for the CP1 dataset are still pending.

## CP3: concurrency and performance audit

Order creation protects shared inventory with PostgreSQL row locks (`SELECT ... FOR UPDATE`) inside the order transaction. Stock is checked and decremented while those locks are held, so only one transaction can purchase the final unit. Order cancellation also locks its order row before restoring stock.

`GET /api/v1/orders` selects only response fields and order-item fields in one `LEFT JOIN` query. It groups the returned rows in memory, so query count is constant regardless of page size; it does not issue per-order queries.

### Concurrency verification

With the Compose services running and migrations applied, run the dedicated 20-request last-unit race test:

```bash
docker compose exec api python -m scripts.test_concurrency
```

It creates disposable test records, sends 20 simultaneous orders for one unit, and expects exactly one `201` and 19 `409` responses. It removes its records afterward. Set `API_URL` in the API container environment to target a non-default API address.

### Automated load test

Prepare an active customer bearer token and an order ID owned by that customer, then run from the repository root. This PowerShell command runs k6 in Docker Desktop without installing it on the host:

```powershell
$env:API_TOKEN = "<customer bearer token>"
$env:ORDER_ID = "<owned order UUID>"
docker run --rm --add-host=host.docker.internal:host-gateway `
  -e "API_URL=http://host.docker.internal:8000/api/v1/orders" `
  -e "API_TOKEN=$env:API_TOKEN" `
  -e "ORDER_ID=$env:ORDER_ID" `
  -v "${PWD}:/work" -w /work grafana/k6:latest run ./k6_script.js
```

The script runs 50 virtual users for three minutes, with four order-list reads per cancellation request. Cancellation is safe to repeat; the first request cancels the prepared order and subsequent requests verify idempotent behavior. k6 enforces p95 < 200 ms, p99 < 500 ms, and errors < 1%. Each run generates `cp3-k6-report.md` with throughput, latency/error metrics, and Mermaid charts, plus `cp3-k6-summary.json` with the raw k6 summary. Retain both with the submitted report.

### Audit report and results

| Audit item | Implementation / result |
| --- | --- |
| Write concurrency | PostgreSQL row-level `FOR UPDATE` locks within transactions |
| Race verification | `backend/scripts/test_concurrency.py`; expected 1 success / 19 conflicts |
| List query count | One projected SQL `LEFT JOIN` for each paginated list request |
| Load profile | 50 VUs, 3 minutes, 80% order-list reads / 20% order cancellations |
| Throughput | 48.77 requests/s over the 3-minute local run |
| p95 / p99 latency | 31.48 ms / 104.09 ms (both target thresholds passed) |
| HTTP error rate | 0% (target threshold passed) |

The local benchmark meets the specified thresholds. Re-run in the evaluation environment and include its generated summary and deployment details (API host, database size, and machine) in the submitted report.

Read the [decisions](docs/decisions.md), [data model](docs/data-model.md), [API contract](docs/api-contract.md), and [backlog](docs/backlog.md) before feature work. Give teammates their individual briefs from the [CP1 team handoff](docs/team-handoff.md), replace role labels with real names, and confirm open questions with the instructor.
