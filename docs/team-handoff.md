# CP1 team handoff

This repository has a working Compose setup, an Orders API, and PostgreSQL migration `0001_order_baseline`. Users and Products APIs, CP1 seed scripts, and MongoDB indexes are still missing.

Send each teammate their own brief:

| Person | Brief | Primary result |
| --- | --- | --- |
| Teammate A | [Users and PostgreSQL](handoff-users-postgres.md) | Registration/login, compatible customer tokens, PostgreSQL seed and verification |
| Teammate B | [Products and MongoDB](handoff-products-mongo.md) | Product create/list, MongoDB indexes, MongoDB seed and cross-database verification |
| Project owner | Orders API and integration | Review both PRs, add seed/verify wrappers, test setup on another machine, prepare the CP1 demo |

Both teammates use the [shared seed contract](seed-contract.md) so independently written seed data joins correctly. Start from `main`, work in separate feature branches, and open separate PRs. Do not edit `0001_order_baseline` after it has been applied; add a new migration. Each PR should include test commands/results, migration notes, and any new environment variables.

The integration gate after both PRs merge is:

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed
docker compose exec api python -m scripts.verify_seed
docker compose exec api python -m scripts.smoke_orders
```

`scripts.seed` and `scripts.verify_seed` are target commands; they do not exist yet. A and B add their individual seed modules. The project owner adds the small wrappers after both PRs merge. CP1 is ready for a clean setup test when both databases contain at least 1,000 records/documents, Users/Products/Orders work together, and another teammate can follow the README without assistance. Confirm with the instructor that Alembic is permitted and what `Dual-DB transaction` requires.
