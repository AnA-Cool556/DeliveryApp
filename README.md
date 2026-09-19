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

Read the [decisions](docs/decisions.md), [data model](docs/data-model.md), [API contract](docs/api-contract.md), and [backlog](docs/backlog.md) before feature work. The team should replace roles A–D with real names and confirm the open questions with the instructor.
