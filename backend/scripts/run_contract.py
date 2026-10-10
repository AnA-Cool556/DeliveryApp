import os
import sys

import psycopg


def run_contract() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://deliveryapp:change-me-local-postgres@localhost:5432/deliveryapp",
    ).replace("postgresql+psycopg://", "postgresql://", 1)

    print("Executing Phase 5: Contract (dropping column 'name', setting 'first_name' NOT NULL)...")

    with psycopg.connect(url, autocommit=False) as conn:
        with conn.cursor() as cur:
            # Check for any remaining NULL first_name rows as safety check
            cur.execute("SELECT count(*) FROM users WHERE first_name IS NULL")
            null_count = cur.fetchone()[0]
            if null_count > 0:
                print(f"[WARN] Found {null_count} rows with first_name IS NULL. Backfilling before contract...")
                cur.execute("""
                    UPDATE users
                    SET first_name = COALESCE(NULLIF(split_part(name, ' ', 1), ''), 'User'),
                        last_name = COALESCE(NULLIF(trim(substr(name, length(split_part(name, ' ', 1)) + 1)), ''), '')
                    WHERE first_name IS NULL;
                """)

            # 1. Drop dual-write trigger & function
            cur.execute("DROP TRIGGER IF EXISTS trg_users_dual_write ON users;")
            cur.execute("DROP FUNCTION IF EXISTS fn_users_dual_write();")

            # 2. Drop old column 'name'
            cur.execute("ALTER TABLE users DROP COLUMN IF EXISTS name;")

            # 3. Enforce NOT NULL constraint on first_name
            cur.execute("ALTER TABLE users ALTER COLUMN first_name SET NOT NULL;")

            # 4. Set migration_state to 'contract'
            cur.execute("""
                INSERT INTO migration_state (name, phase, updated_at)
                VALUES ('user_names', 'contract', now())
                ON CONFLICT (name) DO UPDATE
                SET phase = 'contract', updated_at = now();
            """)

        conn.commit()

    print("[SUCCESS] Phase 5 Contract executed successfully. Schema contracted to first_name (NOT NULL) and last_name.")


if __name__ == "__main__":
    try:
        run_contract()
    except Exception as error:
        print(f"[ERROR] Failed to run contract migration: {error}", file=sys.stderr)
        sys.exit(1)
