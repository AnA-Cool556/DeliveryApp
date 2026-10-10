import os
import sys

import psycopg


def verify_backfill() -> bool:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://deliveryapp:change-me-local-postgres@localhost:5432/deliveryapp",
    ).replace("postgresql+psycopg://", "postgresql://", 1)

    passed = True
    print("--- Verifying Backfill Integrity ---")

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            # 1. Check total users
            cur.execute("SELECT count(*) FROM users")
            total_users = cur.fetchone()[0]
            print(f"[CHECK] Total users: {total_users}")

            # 2. Check NULL first_name count
            cur.execute("SELECT count(*) FROM users WHERE first_name IS NULL")
            null_first = cur.fetchone()[0]
            print(f"[CHECK] Users with first_name IS NULL: {null_first}")
            if null_first > 0:
                print(f"  [FAIL] Expected 0 NULL first_name, found {null_first}")
                passed = False
            else:
                print("  [PASS] All users have first_name populated.")

            # 3. Check consistency against 'name' column if it still exists
            cur.execute(
                """
                SELECT count(*)
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'name'
                """
            )
            has_name_col = cur.fetchone()[0] > 0

            if has_name_col:
                cur.execute(
                    """
                    SELECT count(*)
                    FROM users
                    WHERE trim(first_name || CASE WHEN last_name IS NOT NULL AND last_name != '' THEN ' ' || last_name ELSE '' END) != trim(name)
                    """
                )
                mismatch_count = cur.fetchone()[0]
                print(f"[CHECK] Name reconstruction mismatches (first_name || ' ' || last_name != name): {mismatch_count}")
                if mismatch_count > 0:
                    print(f"  [FAIL] Found {mismatch_count} name mismatches!")
                    passed = False
                else:
                    print("  [PASS] Name reconstruction matches original name perfectly.")
            else:
                print("[INFO] Column 'name' has been dropped (contract phase). Mismatch check skipped.")

    if passed:
        print("[RESULT] Backfill verification PASSED!")
    else:
        print("[RESULT] Backfill verification FAILED!")

    return passed


if __name__ == "__main__":
    success = verify_backfill()
    sys.exit(0 if success else 1)
