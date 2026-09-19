import os

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
database_url = os.environ["DATABASE_URL"]


def run_migrations_offline() -> None:
    context.configure(url=database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
