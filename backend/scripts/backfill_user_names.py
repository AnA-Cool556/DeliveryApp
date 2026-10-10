import os
import sys
import time
from uuid import UUID

import psycopg

from app.users import split_name

BATCH_SIZE = 500


def backfill() -> int:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://deliveryapp:change-me-local-postgres@localhost:5432/deliveryapp",
    ).replace("postgresql+psycopg://", "postgresql://", 1)

    print(f"Starting keyset pagination backfill (batch size: {BATCH_SIZE})...")
    start_time = time.time()
    total_processed = 0
    batch_num = 0

    with psycopg.connect(url, autocommit=False) as conn:
        with conn.cursor() as cur:
            # Check total rows needing backfill
            cur.execute("SELECT count(*) FROM users WHERE first_name IS NULL")
            initial_unmigrated = cur.fetchone()[0]
            print(f"[INFO] Initial rows needing backfill (first_name IS NULL): {initial_unmigrated}")

            if initial_unmigrated == 0:
                print("[OK] No rows to backfill. All users already have first_name populated.")
                return 0

            # Get checkpoint if exists
            cur.execute(
                "SELECT last_id, processed_count FROM migration_checkpoint WHERE migration_name = 'user_names'"
            )
            checkpoint = cur.fetchone()
            last_id = checkpoint[0] if checkpoint else None
            if last_id:
                print(f"[INFO] Resuming from checkpoint: last_id = {last_id}")

            while True:
                batch_num += 1
                if last_id is not None:
                    cur.execute(
                        """
                        SELECT id, name
                        FROM users
                        WHERE id > %s AND first_name IS NULL
                        ORDER BY id
                        LIMIT %s
                        """,
                        (last_id, BATCH_SIZE),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, name
                        FROM users
                        WHERE first_name IS NULL
                        ORDER BY id
                        LIMIT %s
                        """,
                        (BATCH_SIZE,),
                    )

                rows = cur.fetchall()
                if not rows:
                    # Double check if any rows remain from beginning
                    cur.execute("SELECT id, name FROM users WHERE first_name IS NULL ORDER BY id LIMIT %s", (BATCH_SIZE,))
                    rows = cur.fetchall()
                    if not rows:
                        break

                # Prepare updates
                update_params = []
                for row_id, name in rows:
                    first, last = split_name(name or "")
                    if not first:
                        first = "User"
                    update_params.append((first, last, row_id))
                    last_id = row_id

                cur.executemany(
                    """
                    UPDATE users
                    SET first_name = %s, last_name = %s
                    WHERE id = %s
                    """,
                    update_params,
                )

                batch_count = len(update_params)
                total_processed += batch_count

                # Update checkpoint
                cur.execute(
                    """
                    INSERT INTO migration_checkpoint (migration_name, last_id, processed_count, updated_at)
                    VALUES ('user_names', %s, %s, now())
                    ON CONFLICT (migration_name) DO UPDATE
                    SET last_id = EXCLUDED.last_id,
                        processed_count = migration_checkpoint.processed_count + EXCLUDED.processed_count,
                        updated_at = now();
                    """,
                    (last_id, batch_count),
                )

                conn.commit()
                print(f"[BATCH {batch_num}] Processed {batch_count} users (last_id: {last_id}) | Total: {total_processed}")

                if batch_count < BATCH_SIZE:
                    # Final check if any unmigrated records exist
                    cur.execute("SELECT count(*) FROM users WHERE first_name IS NULL")
                    remaining = cur.fetchone()[0]
                    if remaining == 0:
                        break

    elapsed = time.time() - start_time
    print(f"[DONE] Backfill completed in {elapsed:.2f}s! Total backfilled rows: {total_processed}")
    return total_processed


if __name__ == "__main__":
    backfill()
