"""
Shared pytest configuration and fixtures.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))
sys.path.insert(0, '/app')

os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test_secret_key_for_jwt_auth_testing_123456789"
os.environ["GROQ_API_KEY"] = "test_key_not_used"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
import app.database as db_module

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
db_module.engine = test_engine

def override_get_session():
    with Session(test_engine) as session:
        yield session

from main import app
from app.database import get_session
app.dependency_overrides[get_session] = override_get_session

SQLModel.metadata.create_all(test_engine)
client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    """Wipe all tables before and after each test for isolation."""
    with test_engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())
    yield
    with test_engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())
