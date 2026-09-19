"""Create the relational baseline needed by orders.

Revision ID: 0001_order_baseline
Revises:
"""

from alembic import op

revision = "0001_order_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            id uuid PRIMARY KEY,
            email text NOT NULL UNIQUE,
            name text NOT NULL
        );
        CREATE TABLE restaurants (
            id uuid PRIMARY KEY,
            name text NOT NULL
        );
        CREATE TABLE inventory (
            product_id uuid PRIMARY KEY,
            restaurant_id uuid NOT NULL REFERENCES restaurants(id),
            quantity integer NOT NULL CHECK (quantity >= 0),
            UNIQUE (product_id, restaurant_id)
        );
        CREATE INDEX ix_inventory_restaurant_id ON inventory(restaurant_id);
        CREATE TABLE orders (
            id uuid PRIMARY KEY,
            customer_id uuid NOT NULL REFERENCES users(id),
            restaurant_id uuid NOT NULL REFERENCES restaurants(id),
            status text NOT NULL DEFAULT 'PLACED'
                CHECK (status IN ('PLACED', 'ACCEPTED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')),
            subtotal_satang integer NOT NULL CHECK (subtotal_satang >= 0),
            delivery_fee numeric(10,2) NOT NULL CHECK (delivery_fee >= 0),
            total_satang integer NOT NULL CHECK (total_satang >= 0),
            idempotency_key text NOT NULL,
            request_hash text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (customer_id, idempotency_key),
            CHECK (total_satang = subtotal_satang + (delivery_fee * 100)::integer)
        );
        CREATE INDEX ix_orders_customer_created ON orders(customer_id, created_at DESC);
        CREATE TABLE order_items (
            id uuid PRIMARY KEY,
            order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id uuid NOT NULL REFERENCES inventory(product_id),
            product_name text NOT NULL,
            quantity integer NOT NULL CHECK (quantity > 0),
            unit_price_satang integer NOT NULL CHECK (unit_price_satang >= 0),
            line_total_satang integer NOT NULL CHECK (line_total_satang = quantity * unit_price_satang),
            UNIQUE (order_id, product_id)
        );
        CREATE INDEX ix_order_items_order_id ON order_items(order_id);
        CREATE TABLE deliveries (
            id uuid PRIMARY KEY,
            order_id uuid NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
            rider_id uuid REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE order_status_history (
            id uuid PRIMARY KEY,
            order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            status text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_order_status_history_order_id ON order_status_history(order_id, created_at);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE order_status_history;
        DROP TABLE deliveries;
        DROP TABLE order_items;
        DROP TABLE orders;
        DROP TABLE inventory;
        DROP TABLE restaurants;
        DROP TABLE users;
    """)
