import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core import config as config_module

config_module.settings = config_module.Settings(
    database_url="sqlite://",
    admin_api_key="test-admin-key",
    device_api_key="test-device-key",
)


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def client(engine, monkeypatch):
    from app import db as db_module
    from app.main import app

    monkeypatch.setattr(db_module, "engine", engine)

    def _get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[db_module.get_session] = _get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
