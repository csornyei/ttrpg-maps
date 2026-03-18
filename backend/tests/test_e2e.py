"""
End-to-end tests for the full backend stack.

These tests exercise the complete request/response cycle through FastAPI,
the POI store, SQLite migrations, authentication, WebSocket, and health
endpoints — using a real (in-memory / tmp) SQLite database.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AUTH_HEADER

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(db_path):
    """Full-stack test client wired to an isolated SQLite database."""
    from src.main import app
    import src.routes.pois as pois_module
    import src.routes.health as health_module
    from src.config import Settings, get_settings
    from src.poi_store import PoiStore

    test_store = PoiStore(db_path=db_path)

    original_store_pois = pois_module.poi_store
    original_store_health = health_module.poi_store

    pois_module.poi_store = test_store
    health_module.poi_store = test_store

    test_settings = Settings(api_auth_token="test-token", env="dev")
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as c:
        yield c

    pois_module.poi_store = original_store_pois
    health_module.poi_store = original_store_health
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

STATIC_POI = {
    "id": "tavern",
    "name": "The Rusty Flagon",
    "color": "#c8a96e",
    "description": "A dimly lit tavern in the old quarter.",
    "notes": "Owner is suspicious.",
    "col": 5,
    "row": 3,
}

MOVING_POI = {
    "id": "patrol",
    "name": "Guard Patrol",
    "color": "#ff4444",
    "description": "Rotating guard patrol.",
    "notes": "Switches direction at dusk.",
    "path": [
        {"col": 1, "row": 1},
        {"col": 2, "row": 1},
        {"col": 3, "row": 1},
    ],
}

HIDDEN_POI = {
    "id": "hidden_cache",
    "name": "Hidden Cache",
    "color": "#888888",
    "description": "Secret stash.",
    "notes": "",
    "col": 10,
    "row": 10,
    "visible": False,
}


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


class TestHealthEndpoints:
    def test_liveness(self, client: TestClient) -> None:
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_readiness_when_db_ok(self, client: TestClient) -> None:
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}


# ---------------------------------------------------------------------------
# Migrations ran: schema is correct
# ---------------------------------------------------------------------------


class TestMigrations:
    def test_pois_table_exists(self, db_path: str) -> None:
        """Verify that the initial migration created the pois table."""
        from src.poi_store import PoiStore

        PoiStore(db_path=db_path)  # triggers migrations
        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        assert "pois" in tables
        assert "poi_path_points" in tables
        assert "poi_path_index" in tables
        assert "schema_migrations" in tables

    def test_all_migrations_recorded(self, db_path: str) -> None:
        """Every .py file in migrations/ must appear in schema_migrations."""
        from src.poi_store import PoiStore, MIGRATIONS_DIR

        PoiStore(db_path=db_path)
        conn = sqlite3.connect(db_path)
        applied = {
            row[0]
            for row in conn.execute("SELECT name FROM schema_migrations").fetchall()
        }
        conn.close()
        expected = {p.name for p in sorted(MIGRATIONS_DIR.glob("*.py"))}
        assert expected == applied

    def test_migrations_not_reapplied_on_restart(self, db_path: str) -> None:
        """Creating a second PoiStore on the same DB must not duplicate migrations."""
        from src.poi_store import PoiStore

        PoiStore(db_path=db_path)
        PoiStore(db_path=db_path)  # second startup
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        conn.close()
        from src.poi_store import MIGRATIONS_DIR

        expected = len(list(MIGRATIONS_DIR.glob("*.py")))
        assert count == expected


# ---------------------------------------------------------------------------
# Full static POI lifecycle
# ---------------------------------------------------------------------------


class TestStaticPoiLifecycle:
    def test_create(self, client: TestClient) -> None:
        resp = client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == STATIC_POI["id"]
        assert data["col"] == STATIC_POI["col"]
        assert data["row"] == STATIC_POI["row"]
        assert data["color"] == STATIC_POI["color"]

    def test_appears_in_list(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        data = client.get("/api/pois").json()
        ids = {p["id"] for p in data}
        assert STATIC_POI["id"] in ids

    def test_detail_fields(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        resp = client.get(f"/api/pois/{STATIC_POI['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == STATIC_POI["description"]
        assert data["notes"] == STATIC_POI["notes"]
        assert data["visible"] is True
        assert data["path"] is None

    def test_full_update(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        update = {
            "name": "The Golden Griffin",
            "color": "#ffd700",
            "description": "Upscale establishment.",
            "notes": "Owner is helpful.",
            "col": 7,
            "row": 9,
        }
        resp = client.put(
            f"/api/pois/{STATIC_POI['id']}", json=update, headers=AUTH_HEADER
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "The Golden Griffin"
        assert data["col"] == 7
        assert data["row"] == 9

    def test_partial_patch(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        resp = client.patch(
            f"/api/pois/{STATIC_POI['id']}",
            json={"name": "The Patched Flagon"},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "The Patched Flagon"
        # Other fields unchanged
        assert data["col"] == STATIC_POI["col"]
        assert data["color"] == STATIC_POI["color"]

    def test_delete(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        resp = client.delete(f"/api/pois/{STATIC_POI['id']}", headers=AUTH_HEADER)
        assert resp.status_code == 204
        assert client.get(f"/api/pois/{STATIC_POI['id']}").status_code == 404

    def test_gone_from_list_after_delete(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        client.delete(f"/api/pois/{STATIC_POI['id']}", headers=AUTH_HEADER)
        ids = {p["id"] for p in client.get("/api/pois").json()}
        assert STATIC_POI["id"] not in ids


# ---------------------------------------------------------------------------
# Full moving POI lifecycle
# ---------------------------------------------------------------------------


class TestMovingPoiLifecycle:
    def test_create_moving_poi(self, client: TestClient) -> None:
        resp = client.post("/api/pois", json=MOVING_POI, headers=AUTH_HEADER)
        assert resp.status_code == 201
        data = resp.json()
        # Initial position is first path point
        assert data["col"] == MOVING_POI["path"][0]["col"]
        assert data["row"] == MOVING_POI["path"][0]["row"]

    def test_path_returned_when_requested(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_POI, headers=AUTH_HEADER)
        data = client.get(f"/api/pois/{MOVING_POI['id']}?path=true").json()
        assert data["path"] == MOVING_POI["path"]

    def test_path_omitted_by_default(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_POI, headers=AUTH_HEADER)
        data = client.get(f"/api/pois/{MOVING_POI['id']}").json()
        assert data["path"] is None

    def test_position_advances_after_store_advance(self, client: TestClient) -> None:
        import src.routes.pois as pois_module

        client.post("/api/pois", json=MOVING_POI, headers=AUTH_HEADER)
        pois_module.poi_store.advance_moving_pois()

        data = client.get(f"/api/pois/{MOVING_POI['id']}").json()
        # Should now be at path[1]
        assert data["col"] == MOVING_POI["path"][1]["col"]
        assert data["row"] == MOVING_POI["path"][1]["row"]

    def test_convert_moving_to_static(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_POI, headers=AUTH_HEADER)
        resp = client.patch(
            f"/api/pois/{MOVING_POI['id']}",
            json={"col": 8, "row": 8},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["col"] == 8
        assert data["row"] == 8
        # Path should no longer be returned
        assert (
            client.get(f"/api/pois/{MOVING_POI['id']}?path=true").json()["path"] is None
        )

    def test_convert_static_to_moving(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        new_path = [{"col": 1, "row": 1}, {"col": 2, "row": 2}]
        resp = client.patch(
            f"/api/pois/{STATIC_POI['id']}",
            json={"path": new_path},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["col"] == new_path[0]["col"]
        assert data["row"] == new_path[0]["row"]


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


class TestVisibility:
    def test_hidden_poi_excluded_from_list(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        client.post("/api/pois", json=HIDDEN_POI, headers=AUTH_HEADER)
        ids = {p["id"] for p in client.get("/api/pois").json()}
        assert STATIC_POI["id"] in ids
        assert HIDDEN_POI["id"] not in ids

    def test_hidden_poi_still_reachable_by_detail(self, client: TestClient) -> None:
        client.post("/api/pois", json=HIDDEN_POI, headers=AUTH_HEADER)
        resp = client.get(f"/api/pois/{HIDDEN_POI['id']}")
        assert resp.status_code == 200
        assert resp.json()["visible"] is False

    def test_hide_unhide_via_patch(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)

        client.patch(
            f"/api/pois/{STATIC_POI['id']}",
            json={"visible": False},
            headers=AUTH_HEADER,
        )
        ids = {p["id"] for p in client.get("/api/pois").json()}
        assert STATIC_POI["id"] not in ids

        client.patch(
            f"/api/pois/{STATIC_POI['id']}",
            json={"visible": True},
            headers=AUTH_HEADER,
        )
        ids = {p["id"] for p in client.get("/api/pois").json()}
        assert STATIC_POI["id"] in ids


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_list_requires_no_auth(self, client: TestClient) -> None:
        assert client.get("/api/pois").status_code == 200

    def test_detail_requires_no_auth(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        assert client.get(f"/api/pois/{STATIC_POI['id']}").status_code == 200

    def test_create_requires_auth(self, client: TestClient) -> None:
        assert client.post("/api/pois", json=STATIC_POI).status_code == 401

    def test_update_requires_auth(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        update = {**STATIC_POI, "name": "No Auth"}
        assert (
            client.put(f"/api/pois/{STATIC_POI['id']}", json=update).status_code == 401
        )

    def test_patch_requires_auth(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        assert (
            client.patch(
                f"/api/pois/{STATIC_POI['id']}", json={"name": "X"}
            ).status_code
            == 401
        )

    def test_delete_requires_auth(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        assert client.delete(f"/api/pois/{STATIC_POI['id']}").status_code == 401

    def test_bearer_token_accepted(self, client: TestClient) -> None:
        resp = client.post(
            "/api/pois",
            json=STATIC_POI,
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 201

    def test_wrong_token_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/pois",
            json=STATIC_POI,
            headers={"X-API-Key": "wrong-token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    def test_create_duplicate_id(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        assert (
            client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER).status_code
            == 409
        )

    def test_get_nonexistent(self, client: TestClient) -> None:
        assert client.get("/api/pois/ghost").status_code == 404

    def test_update_nonexistent(self, client: TestClient) -> None:
        update = {**STATIC_POI, "id": "ghost"}
        assert (
            client.put("/api/pois/ghost", json=update, headers=AUTH_HEADER).status_code
            == 404
        )

    def test_patch_nonexistent(self, client: TestClient) -> None:
        assert (
            client.patch(
                "/api/pois/ghost", json={"name": "X"}, headers=AUTH_HEADER
            ).status_code
            == 404
        )

    def test_delete_nonexistent(self, client: TestClient) -> None:
        assert client.delete("/api/pois/ghost", headers=AUTH_HEADER).status_code == 404

    def test_create_invalid_both_col_and_path(self, client: TestClient) -> None:
        payload = {**STATIC_POI, "path": [{"col": 1, "row": 2}]}
        assert (
            client.post("/api/pois", json=payload, headers=AUTH_HEADER).status_code
            == 422
        )

    def test_create_invalid_neither_col_nor_path(self, client: TestClient) -> None:
        payload = {k: v for k, v in STATIC_POI.items() if k not in ("col", "row")}
        assert (
            client.post("/api/pois", json=payload, headers=AUTH_HEADER).status_code
            == 422
        )


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


class TestWebSocket:
    def test_ws_broadcasts_visible_pois(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        client.post("/api/pois", json=HIDDEN_POI, headers=AUTH_HEADER)
        with client.websocket_connect("/ws/pois") as ws:
            data = ws.receive_json()
        ids = {p["id"] for p in data}
        assert STATIC_POI["id"] in ids
        assert HIDDEN_POI["id"] not in ids

    def test_ws_broadcasts_moving_poi_position(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_POI, headers=AUTH_HEADER)
        with client.websocket_connect("/ws/pois") as ws:
            data = ws.receive_json()
        pois = {p["id"]: p for p in data}
        assert MOVING_POI["id"] in pois
        assert pois[MOVING_POI["id"]]["col"] == MOVING_POI["path"][0]["col"]
        assert pois[MOVING_POI["id"]]["row"] == MOVING_POI["path"][0]["row"]

    def test_ws_summary_fields(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        with client.websocket_connect("/ws/pois") as ws:
            data = ws.receive_json()
        poi = next(p for p in data if p["id"] == STATIC_POI["id"])
        for field in ("id", "name", "col", "row", "color", "visible"):
            assert field in poi, f"Missing field '{field}' in WS summary"

    def test_ws_empty_when_no_pois(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/pois") as ws:
            data = ws.receive_json()
        assert data == []


# ---------------------------------------------------------------------------
# Multi-POI interactions
# ---------------------------------------------------------------------------


class TestMultiPoi:
    def test_list_sorted_by_name(self, client: TestClient) -> None:
        """POIs should be returned in case-insensitive name order."""
        for poi in (
            {**STATIC_POI, "id": "z", "name": "Zzz Place"},
            {**STATIC_POI, "id": "a", "name": "Aaa Place"},
            {**STATIC_POI, "id": "m", "name": "Mmm Place"},
        ):
            client.post("/api/pois", json=poi, headers=AUTH_HEADER)

        names = [p["name"] for p in client.get("/api/pois").json()]
        assert names == sorted(names, key=str.casefold)

    def test_multiple_pois_independent(self, client: TestClient) -> None:
        """Deleting one POI should not affect others."""
        client.post("/api/pois", json=STATIC_POI, headers=AUTH_HEADER)
        client.post("/api/pois", json=MOVING_POI, headers=AUTH_HEADER)

        client.delete(f"/api/pois/{STATIC_POI['id']}", headers=AUTH_HEADER)

        ids = {p["id"] for p in client.get("/api/pois").json()}
        assert MOVING_POI["id"] in ids
        assert STATIC_POI["id"] not in ids
