# Draft API contract

Base path: `/api/v1`. Requests and responses use JSON, IDs are UUID strings, timestamps use ISO 8601 UTC, and prices are integer satang. These routes and their validation are not implemented yet.

| Group | Planned endpoints | Purpose |
| --- | --- | --- |
| Users | `POST /users`, `GET /users/{id}` | Create and read users; reject duplicate email addresses |
| Products | `POST /products`, `GET /products` | Manage products and provide paginated listing |
| Orders | `POST /orders`, `GET /orders/{id}`, `GET /orders` | Create and read orders with authorization |
| Orders | `POST /orders/{id}/cancel` | Cancel before acceptance and restore stock once |
| Tracking | `POST /deliveries/{id}/locations`, `GET /deliveries/{id}/location` | Submit a location and read the latest one |

Proposed shared error format, to be confirmed by the team:

```json
{
  "error": {
    "code": "OUT_OF_STOCK",
    "message": "Insufficient stock",
    "details": {}
  }
}
```

Proposed HTTP status codes: `201` created, `400` bad request, `401` unauthenticated, `403` forbidden, `404` not found, `409` conflict, and `422` validation error. Define request and response examples for each endpoint before implementation and notify frontend owners when the contract changes.
