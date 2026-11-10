import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.services import fixture_seed


@pytest.fixture
def client():
    test_database_url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    engine_options = {}
    if test_database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    if test_database_url in ("sqlite://", "sqlite:///:memory:"):
        engine_options["poolclass"] = StaticPool
    engine = create_engine(test_database_url, **engine_options)
    if test_database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestingSession() as session:
        fixture_seed(session)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app(
        Settings(app_env="test", database_url=test_database_url, mock_auth_enabled=True)
    )
    app.state.test_session_factory = TestingSession
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def login(client, user_key="analyst-a"):
    response = client.post("/api/v1/auth/mock-login", json={"user_key": user_key})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    org_id = response.json()["data"]["principal"]["memberships"][0]["organization_id"]
    return {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}, org_id
