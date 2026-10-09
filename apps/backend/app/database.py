"""
Database engine, session factory, and connection helpers.
Uses SQLModel on top of SQLAlchemy 2.0.
"""
import os
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fitness:fitness123@localhost:5432/fitness_challenge")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# NullPool is safe for serverless (Neon/Fly). For long-running servers,
# swap to pool_size=5, max_overflow=10 for better connection reuse.
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("ENVIRONMENT", "development") == "development",
    poolclass=NullPool,
)


def create_db_and_tables() -> None:
    """Called at startup to create tables if they don't exist.
    In production Alembic migrations are used instead.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a session per request, always closed."""
    with Session(engine) as session:
        yield session
