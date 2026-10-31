import pytest
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Force SQLite for test suite
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "development"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.database.connection import Base, get_db
from backend.database.models import User
from backend.core.security import hash_password, create_access_token
from backend.main import app

# Create in-memory SQLite engine
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db():
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_a(db):
    user = User(
        email="user_a@test.local",
        hashed_password=hash_password("password123"),
        full_name="User Alpha",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_b(db):
    user = User(
        email="user_b@test.local",
        hashed_password=hash_password("password123"),
        full_name="User Beta",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers_a(user_a):
    token = create_access_token({"sub": user_a.id, "email": user_a.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_b(user_b):
    token = create_access_token({"sub": user_b.id, "email": user_b.email})
    return {"Authorization": f"Bearer {token}"}
