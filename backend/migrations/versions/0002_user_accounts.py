"""Add user accounts fields, role constraints, and lowercase email index.

Revision ID: 0002_user_accounts
Revises: 0001_order_baseline
"""

from alembic import op

revision = "0002_user_accounts"
down_revision = "0001_order_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS password_hash text NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'customer'
                CHECK (role IN ('customer', 'rider', 'merchant', 'admin')),
            ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower ON users (LOWER(email));
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_users_email_lower;
        ALTER TABLE users
            DROP COLUMN IF EXISTS created_at,
            DROP COLUMN IF EXISTS role,
            DROP COLUMN IF EXISTS password_hash;
    """)

