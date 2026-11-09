"""
tests/conftest.py — Shared pytest fixtures

Sets up a temporary SQLite database for testing so tests
never touch the real orbit180.db file.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.database import Base, get_db

# Use an in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite:///./test_orbit180.db"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Replace the real DB session with the test DB session."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables before tests run, drop them after."""
    from app.database import models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """Return a TestClient with the test DB injected."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
