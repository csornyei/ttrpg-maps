import os

# Must be set before any src imports so main.py module-level get_settings() succeeds
os.environ.setdefault("API_AUTH_TOKEN", "test-token")

import pytest
from fastapi.testclient import TestClient

from src.config import Settings, get_settings
from src.poi_store import PoiStore

AUTH_HEADER = {"X-API-Key": "test-token"}


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "test_pois.db")


@pytest.fixture
def store(db_path) -> PoiStore:
    return PoiStore(db_path=db_path)


@pytest.fixture
def client(db_path):
    from src.main import app
    import src.routes.pois as pois_module

    test_store = PoiStore(db_path=db_path)
    original_store = pois_module.poi_store
    pois_module.poi_store = test_store

    test_settings = Settings(api_auth_token="test-token", env="dev")
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as c:
        yield c

    pois_module.poi_store = original_store
    app.dependency_overrides.clear()
