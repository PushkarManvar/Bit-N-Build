"""Test fixtures: hermetic SQLite database + JSON fixture loading.

Tests never touch the compose PostgreSQL database. The app's ``get_db``
dependency is overridden with an in-memory SQLite engine created per test.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def load_fixture(relative_path: str) -> dict:
    with (DATA_ROOT / relative_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture()
def riya_web_valid() -> dict:
    return load_fixture("fixtures/g1/riya_web_valid.json")


@pytest.fixture()
def riya_web_duplicate() -> dict:
    return load_fixture("fixtures/g1/riya_web_duplicate.json")


@pytest.fixture()
def web_invalid_missing_timestamp() -> dict:
    return load_fixture("fixtures/g1/web_invalid_missing_timestamp.json")


@pytest.fixture()
def riya_web_canonical_expected() -> dict:
    return load_fixture("expected/g1/riya_web_canonical.json")