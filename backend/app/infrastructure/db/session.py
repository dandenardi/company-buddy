# app/infrastructure/db/session.py
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Engine
engine = create_engine(
    settings.database_url,
    # Só precisa disso para SQLite, Postgres ignora
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to provide a database session to FastAPI routes.
    """
    database_session: Session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
