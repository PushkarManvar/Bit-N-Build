"""Database engine, session factory, and FastAPI dependency.

The default engine targets the compose PostgreSQL service. Tests override
``get_db`` with an in-memory SQLite engine so no external database is
required for the unit/integration test suite.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()