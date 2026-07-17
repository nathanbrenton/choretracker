"""SQLAlchemy engine, sessions, and database connectivity helpers."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db_session() -> Generator[Session]:
    """Yield a request-scoped database session."""

    with SessionLocal() as session:
        yield session


def check_database_connection(database_engine: Engine = engine) -> bool:
    """Return whether PostgreSQL accepts a simple query."""

    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False

    return True
