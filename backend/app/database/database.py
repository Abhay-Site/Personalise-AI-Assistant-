"""
database.py — SQLAlchemy database engine and session management

Design decisions:
- SQLite for MVP (zero-config, single file, easy to reset during development)
- SQLAlchemy 2.x declarative base
- Session is provided per-request via FastAPI dependency injection (get_db)
- init_db() creates all tables on startup; safe to call multiple times
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def _build_engine():
    settings = get_settings()
    # check_same_thread=False is required for SQLite when used with FastAPI
    # because FastAPI handles requests across multiple threads.
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False,  # Set True to log every SQL statement (useful for debugging)
    )


engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Create all tables defined in models.py.
    Called once at application startup via the lifespan event in main.py.
    """
    # Import models here so Base knows about them before create_all()
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")


def get_db():
    """
    FastAPI dependency that yields a database session per request
    and ensures it is closed after the request completes.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
