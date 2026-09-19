# Shared decisions (draft)

These are starting agreements for the team. Confirm them with the team and instructor before writing migrations.

| Topic | Decision |
| --- | --- |
| Scope | One restaurant per order, fixed delivery fee, simulated cash on delivery |
| IDs | Use UUID strings for identifiers shared across databases |
| Time | Store UTC and convert to the user's time zone for display |
| Money | Use integer satang or PostgreSQL `NUMERIC`; never use floating point for money |
| Order price | The backend calculates and stores a price snapshot when the order is placed |
| Order status | `PLACED → ACCEPTED → PREPARING → OUT_FOR_DELIVERY → DELIVERED` |
| Cancellation | Allowed before acceptance; restore stock exactly once |
| API | Prefix `/api/v1`; use one error response format |
| Authorization | Customers see only their orders; riders update only assigned deliveries |
| Tracking | Older events must not overwrite the latest rider location |
| Source of truth | PostgreSQL owns orders, stock, and delivery state; MongoDB owns catalog details and telemetry |
| Cross-database writes | Two writes are not automatically atomic; add retry and reconciliation |

## Confirm before feature work

- Whether SQLAlchemy and Alembic are permitted
- What the course means by `Dual-DB transaction`
- The fixed delivery fee and service area
- The real names for roles A–D and the current CP1/CP2 deadlines

Chat, payment gateways, complex coupons, and competitive rider assignment are out of scope.
