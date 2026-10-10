import os
import sys

import psycopg

VALID_PHASES = {"expand", "dual_write", "backfill", "switch_read", "contract"}


def set_phase(phase: str) -> None:
    phase = phase.lower().strip()
    if phase not in VALID_PHASES:
        print(f"[ERROR] Invalid phase '{phase}'. Must be one of: {sorted(VALID_PHASES)}", file=sys.stderr)
        sys.exit(1)

    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://deliveryapp:change-me-local-postgres@localhost:5432/deliveryapp",
    ).replace("postgresql+psycopg://", "postgresql://", 1)

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO migration_state (name, phase, updated_at)
                VALUES ('user_names', %s, now())
                ON CONFLICT (name) DO UPDATE
                SET phase = EXCLUDED.phase, updated_at = now();
                """,
                (phase,),
            )
        conn.commit()

    print(f"[OK] Migration phase for 'user_names' updated to: {phase}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python -m scripts.set_migration_phase <{'|'.join(sorted(VALID_PHASES))}>")
        sys.exit(1)
    set_phase(sys.argv[1])
