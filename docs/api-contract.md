# Draft API contract

Base path: `/api/v1`. Requests and responses use JSON, IDs are UUID strings, timestamps use ISO 8601 UTC, and prices are integer satang. Orders routes are implemented; the other routes remain planned.

| Group | Planned endpoints | Purpose |
| --- | --- | --- |
| Users | `POST /users`, `GET /users/{id}` | Create and read users; reject duplicate email addresses |
| Products | `POST /products`, `GET /products` | Manage products and provide paginated listing |
| Orders | `POST /orders`, `GET /orders/{id}`, `GET /orders` | Create and read orders with authorization; implemented |
| Orders | `POST /orders/{id}/cancel` | Cancel before acceptance and restore stock once; implemented |
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

Orders authentication uses an HS256 bearer token with `sub` (user UUID), `role: "customer"`, and `exp` (Unix timestamp). The Users owner must issue compatible tokens and use the same `AUTH_SECRET`. Orders read only the authenticated customer's records. `POST /orders` also requires an `Idempotency-Key` header (1–128 characters). A replay with the same body returns `200`; reusing the key for different content returns `409`.

Example create request:

```json
{
  "restaurant_id": "4b6b748e-c8ba-4b06-bda5-981bf9cebe32",
  "items": [{"product_id": "9b9fdbb9-4b46-4b40-8c1b-00fa95d982f8", "quantity": 2}]
}
```

MongoDB database `deliveryapp`, collection `products`, uses a UUID string as `_id`, with `restaurant_id` (UUID string), `name` (string), `price_satang` (integer), and `active` (boolean). PostgreSQL `inventory.product_id` matches `_id`. Product prices are copied at purchase time; MongoDB is read only during order creation.

Orders return `201` on creation, `200` on reads or replay, `401` for missing/invalid tokens, `403` for noncustomer tokens, `404` for inaccessible records or products, `409` for stock/idempotency conflicts, `422` for invalid input, and `503` when a database is unavailable. The Users and Products owners should define their own request/response examples before implementation and notify frontend owners when contracts change.
