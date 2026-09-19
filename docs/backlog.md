# Sprint 1 backlog

Workflow: Todo → Doing → Review → Done. Each person should have one main task in Doing at a time. This split assumes three people; replace the role labels with real names.

| ID | Task | Owner | Done when |
| --- | --- | --- | --- |
| SETUP-01 | Monorepo and Compose | You | API, frontend, PostgreSQL, and MongoDB start; done |
| SETUP-02 | Health checks and environment template | You | No secrets in Git and API starts after databases are healthy; done |
| DB-01 | Extend PostgreSQL schema with new migrations | Teammate A | Users and restaurant data work with the existing baseline |
| DB-02 | MongoDB collections and indexes | Teammate B | Catalog and location queries work |
| DATA-01 | Seed and verification | A and B | At least 1,000 records per DB; reruns do not duplicate data |
| API-01 | Users API and token issuance | Teammate A | Create/read users, reject duplicate email, issue compatible HS256 tokens |
| API-02 | Products API | Teammate B | Dynamic attributes and pagination; products match the Orders contract |
| API-03 | Orders API | You | Transaction, price snapshot, stock locking, cancellation, and duplicate request handling; done |
| TRACK-01 | Location API and simulator | Teammate B | Older locations cannot replace newer ones; after core CP1 work |
| TEST-01 | Integration tests | All | Success, failure, rollback, and duplicate requests covered |
| CI-01 | PR checks | You | Backend check, frontend build, and Orders integration pass |
| DOC-01 | README, ERD, demo script | All | A teammate can set up and demo the system |

Ten-day sequence: day 1 scope, owners, and contract → day 2 setup → day 3 schema and indexes → day 4 seed → day 5 Users and Products → day 6 Orders → day 7 concurrency and rollback → day 8 Tracking → day 9 integration and clean setup → day 10 audit and demo.
