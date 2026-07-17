"""Alembic migration environment for ChoreTracker."""

from logging.config import fileConfig

from alembic import context
from app.core.config import get_settings
from sqlalchemy import engine_from_config, pool

config = context.config
settings = get_settings()

# Alembic receives the database URL from typed application settings.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No application models exist yet, so autogeneration has no metadata target.
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations without creating a live database connection."""

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
