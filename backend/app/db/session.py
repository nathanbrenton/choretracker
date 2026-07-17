"""SQLAlchemy engine and database connectivity helpers."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


def check_database_connection(database_engine: Engine = engine) -> bool:
    """Return whether PostgreSQL accepts a simple query."""

    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False

    return True
