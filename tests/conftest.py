import os

import psycopg
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
import pytest
from sqlalchemy import text


env = dotenv_values(".env")
test_database = "online_banking_test"
with psycopg.connect(
    dbname="postgres",
    user=env.get("POSTGRES_USER", "banking"),
    password=env.get("POSTGRES_PASSWORD", "local_dev_change_me"),
    host=env.get("POSTGRES_HOST", "localhost"),
    port=int(env.get("POSTGRES_PORT", "5433")),
    autocommit=True,
) as connection:
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (test_database,)).fetchone()
    if not exists:
        connection.execute(f'CREATE DATABASE "{test_database}"')

os.environ["POSTGRES_DB"] = test_database
os.environ["APP_ENV"] = "development"

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import app as fastapi_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from scripts.seed_data import seed  # noqa: E402


command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def reset_database() -> None:
    table_names = [table.name for table in reversed(Base.metadata.sorted_tables)]
    quoted = ", ".join(f'"{name}"' for name in table_names)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    seed()


@pytest.fixture
def client() -> TestClient:
    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture
def customer_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "customer1", "password": "Customer@123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
