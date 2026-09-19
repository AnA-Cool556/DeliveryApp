# Sprint 1 backlog

Workflow: Todo → Doing → Review → Done. Each person should have one main task in Doing at a time. Roles A–D still need real names.

| ID | Task | Owner | Done when |
| --- | --- | --- | --- |
| SETUP-01 | Monorepo and Compose | D | API, frontend, PostgreSQL, and MongoDB start |
| SETUP-02 | Health checks and environment template | D | No secrets in Git; API starts after databases are healthy |
| DB-01 | PostgreSQL schema and migrations | A | Schema builds from an empty database |
| DB-02 | MongoDB collections and indexes | B | Catalog and location queries work |
| DATA-01 | Seed and verification | A, B, C | At least 1,000 records per DB; reruns do not duplicate data |
| API-01 | Users API | A | Create/read and handle duplicate email |
| API-02 | Products API | B | Dynamic attributes and pagination |
| API-03 | Orders API | C | Transaction, price snapshot, rollback, and duplicate request handling |
| TRACK-01 | Location API and simulator | B, D | Older locations cannot replace newer ones |
| TEST-01 | Integration tests | All | Success, failure, rollback, and duplicate requests covered |
| CI-01 | PR checks | D | Backend check and frontend build pass |
| DOC-01 | README, ERD, demo script | All | A teammate can set up and demo the system |

Ten-day sequence: day 1 scope, owners, and contract → day 2 setup → day 3 schema and indexes → day 4 seed → day 5 Users and Products → day 6 Orders → day 7 concurrency and rollback → day 8 Tracking → day 9 integration and clean setup → day 10 audit and demo.
