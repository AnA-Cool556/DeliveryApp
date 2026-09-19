# DeliveryApp

Food delivery around Chiang Mai University. This repository currently contains the team setup. Users, Products, Orders, and Tracking features are not implemented yet.

## Getting started

Install Git and Docker Desktop, then run:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

On PowerShell, use `Copy-Item .env.example .env`. Change the local passwords in `.env` and keep that file out of Git. If ports `5432` or `27017` are unavailable, change `POSTGRES_PORT` or `MONGO_PORT` in `.env`.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| PostgreSQL | localhost:5432 |
| MongoDB | localhost:27017 |

`curl http://localhost:8000/health` should return `{"status":"ok"}`. This checks the API only; use `docker compose ps` to check the databases. Stop services with `docker compose down`; named volumes preserve data.

DDL, migrations, and seed scripts do not exist yet. Once the team adds them, the intended commands are:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed
docker compose exec api python -m scripts.verify_seed
```

Read the [decisions](docs/decisions.md), [data model](docs/data-model.md), [API contract](docs/api-contract.md), and [backlog](docs/backlog.md) before feature work. The team should replace roles A–D with real names and confirm the open questions with the instructor.
