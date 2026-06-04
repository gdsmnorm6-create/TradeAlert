import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("TRADEALERT_DATABASE_URL", "sqlite+pysqlite:///./test_tradealert.db")
os.environ.setdefault("TRADEALERT_SECRET_KEY", "test-secret")
os.environ.setdefault("TRADEALERT_REDIS_URL", "redis://localhost:6399/0")

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import seed_default_templates  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_default_templates(db)
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "ian@example.com",
            "password": "password123",
            "business_name": "Ian's Plumbing",
            "trade": "plumber",
            "callback_window_minutes": 10,
            "appointment_window": "4-hour",
            "business_phone": "07700 900100",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

