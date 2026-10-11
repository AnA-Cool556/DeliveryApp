import os
from uuid import NAMESPACE_URL, uuid5

import psycopg

from app.security import hash_password


def restaurant_id(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"deliveryapp:restaurant:{index}"))


def product_id(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"deliveryapp:product:{index}"))


def user_id(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"deliveryapp:user:{index}"))


def seed_postgres() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    seed_password = os.environ.get("SEED_USER_PASSWORD")
    if not seed_password or len(seed_password) < 8:
        raise ValueError("Set SEED_USER_PASSWORD to a local demo password of at least 8 characters")
    default_password_hash = hash_password(seed_password)

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            # 1. Seed Restaurants (10)
            restaurant_records = [
                (restaurant_id(i), f"CMU Kitchen {i}")
                for i in range(10)
            ]
            cur.executemany(
                """
                INSERT INTO restaurants (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                restaurant_records,
            )

            # 2. Seed Users (1,480 customers, 20 riders, one demo merchant)
            user_records = []
            for i in range(1500):
                uid = user_id(i)
                if i < 1480:
                    role = "customer"
                    email = f"customer_{i}@cmu.ac.th"
                    name = f"Customer {i}"
                else:
                    role = "rider"
                    email = f"rider_{i}@cmu.ac.th"
                    name = f"Rider {i}"
                user_records.append((uid, email, name, default_password_hash, role))

            user_records.append(
                (user_id(1500), "merchant@cmu.example", "CMU Demo Merchant", default_password_hash, "merchant")
            )

            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                """
            )
            columns = {row[0] for row in cur.fetchall()}

            if "name" in columns and "first_name" in columns:
                cur.executemany(
                    """
                    INSERT INTO users (id, email, name, first_name, last_name, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    [
                        (
                            uid,
                            email,
                            name,
                            name.split(" ", 1)[0],
                            name.split(" ", 1)[1] if " " in name else "",
                            pwd,
                            role,
                        )
                        for uid, email, name, pwd, role in user_records
                    ],
                )
            elif "first_name" in columns and "name" not in columns:
                cur.executemany(
                    """
                    INSERT INTO users (id, email, first_name, last_name, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    [
                        (
                            uid,
                            email,
                            name.split(" ", 1)[0],
                            name.split(" ", 1)[1] if " " in name else "",
                            pwd,
                            role,
                        )
                        for uid, email, name, pwd, role in user_records
                    ],
                )
            else:
                cur.executemany(
                    """
                    INSERT INTO users (id, email, name, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    user_records,
                )

            # 3. Seed Inventory (1,000 items: 100 per restaurant)
            inventory_records = []
            for i in range(1000):
                pid = product_id(i)
                rest_id = restaurant_id(i // 100)
                quantity = 50 + (i % 25)
                inventory_records.append((pid, rest_id, quantity))

            cur.executemany(
                """
                INSERT INTO inventory (product_id, restaurant_id, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT (product_id) DO NOTHING
                """,
                inventory_records,
            )

        conn.commit()

    print(
        f"PostgreSQL seed completed: {len(restaurant_records)} restaurants, "
        f"{len(user_records)} users, {len(inventory_records)} inventory items."
    )


if __name__ == "__main__":
    seed_postgres()

