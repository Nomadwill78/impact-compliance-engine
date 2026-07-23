"""
Alembic environment configuration.

Wires Alembic to the application's SQLAlchemy models and settings so that
`alembic revision --autogenerate` and `alembic upgrade head` operate against
the same DATABASE_URL and ORM metadata used by the running application.

Supports both offline (SQL script generation) and online (direct DB) modes.
Since the app uses an async SQLAlchemy engine (asyncpg), online migrations
run the sync-style Alembic API via `run_sync` on an async connection.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Import all ORM models so they are registered on Base.metadata before
# autogenerate compares against them.
from app.models import orm  # noqa: F401

# Alembic Config object, provides access to values within alembic.ini.
config = context.config

# Inject the application's DATABASE_URL as the single source of truth.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata used for autogenerate support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emits SQL without a DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
