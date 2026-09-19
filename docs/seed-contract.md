# Shared CP1 seed contract

A and B write separate scripts. Use Python `uuid.uuid5` with `uuid.NAMESPACE_URL` and these exact names so their IDs match:

```python
from uuid import NAMESPACE_URL, uuid5

def restaurant_id(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"deliveryapp:restaurant:{index}"))

def product_id(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"deliveryapp:product:{index}"))

def user_id(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"deliveryapp:user:{index}"))
```

| Data | Owner | IDs / relation | Minimum count |
| --- | --- | --- | --- |
| `restaurants` in PostgreSQL | A | `restaurant_id(0..9)` | 10 |
| `users` in PostgreSQL | A | `user_id(0..99)`; 0–79 customers, 80–99 riders | 100 |
| `inventory` in PostgreSQL | A | `product_id(0..999)`, restaurant `restaurant_id(index // 100)`, positive quantity | 1,000 |
| `products` in MongoDB | B | `_id = product_id(0..999)`, restaurant `restaurant_id(index // 100)`, nonempty name, integer `price_satang`, `active: true` | 1,000 |
| `rider_locations` in MongoDB | B | `rider_id = user_id(80..99)`, UTC `updated_at`, valid CMU-area coordinates | 20 |

Use insert-if-missing operations on reruns. Do not reset stock after orders have been placed, replace password hashes, or overwrite menu changes. `verify_seed` should check per-database counts and a one-to-one match between seeded product and inventory IDs. The random, disposable records in `scripts.smoke_orders` are an integration test, not CP1 seed data.
