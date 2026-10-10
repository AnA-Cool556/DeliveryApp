"""Expand users table with first_name, last_name, migration state, and dual-write trigger.

Revision ID: 0003_expand_user_names
Revises: 0002_user_accounts
"""

from alembic import op

revision = "0003_expand_user_names"
down_revision = "0002_user_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        -- 1. Add nullable first_name and last_name without default
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS first_name text NULL,
            ADD COLUMN IF NOT EXISTS last_name text NULL;

        -- 2. State tracking for zero-downtime phases
        CREATE TABLE IF NOT EXISTS migration_state (
            name text PRIMARY KEY,
            phase text NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now()
        );

        INSERT INTO migration_state (name, phase)
        VALUES ('user_names', 'expand')
        ON CONFLICT (name) DO NOTHING;

        -- 3. Checkpoint tracking for batched backfill
        CREATE TABLE IF NOT EXISTS migration_checkpoint (
            migration_name text PRIMARY KEY,
            last_id uuid,
            processed_count integer NOT NULL DEFAULT 0,
            updated_at timestamptz NOT NULL DEFAULT now()
        );

        -- 4. Database-level trigger safety net for dual-write
        CREATE OR REPLACE FUNCTION fn_users_dual_write()
        RETURNS TRIGGER AS $$
        DECLARE
            space_pos integer;
        BEGIN
            IF NEW.first_name IS NULL AND NEW.name IS NOT NULL AND NEW.name != '' THEN
                space_pos := position(' ' in NEW.name);
                IF space_pos > 0 THEN
                    NEW.first_name := substring(NEW.name from 1 for space_pos - 1);
                    NEW.last_name := trim(substring(NEW.name from space_pos + 1));
                ELSE
                    NEW.first_name := NEW.name;
                    NEW.last_name := '';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_users_dual_write ON users;
        CREATE TRIGGER trg_users_dual_write
        BEFORE INSERT OR UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION fn_users_dual_write();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_users_dual_write ON users;
        DROP FUNCTION IF EXISTS fn_users_dual_write();
        DROP TABLE IF EXISTS migration_checkpoint;
        DROP TABLE IF EXISTS migration_state;
        ALTER TABLE users
            DROP COLUMN IF EXISTS last_name,
            DROP COLUMN IF EXISTS first_name;
    """)
