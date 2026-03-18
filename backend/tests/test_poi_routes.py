from fastapi.testclient import TestClient

from tests.conftest import AUTH_HEADER

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STATIC_PAYLOAD = {
    "id": "p1",
    "name": "Test POI",
    "color": "#ff0000",
    "description": "A description",
    "notes": "Some notes",
    "col": 3,
    "row": 5,
}

MOVING_PAYLOAD = {
    "id": "m1",
    "name": "Moving POI",
    "color": "#00ff00",
    "description": "Moves around",
    "notes": "",
    "path": [{"col": 1, "row": 2}, {"col": 3, "row": 4}],
}

UPDATE_PAYLOAD = {
    "name": "Updated",
    "color": "#0000ff",
    "description": "Updated desc",
    "notes": "Updated notes",
    "col": 10,
    "row": 20,
}


# ---------------------------------------------------------------------------
# GET /api/pois
# ---------------------------------------------------------------------------

class TestListPois:
    def test_list_pois_empty(self, client: TestClient) -> None:
        resp = client.get("/api/pois")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_pois_returns_summaries(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        client.post("/api/pois", json={**MOVING_PAYLOAD, "id": "m1"}, headers=AUTH_HEADER)
        resp = client.get("/api/pois")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        ids = {item["id"] for item in data}
        assert ids == {"p1", "m1"}
        for item in data:
            assert "id" in item
            assert "name" in item
            assert "col" in item
            assert "row" in item
            assert "color" in item

    def test_list_pois_no_auth_required(self, client: TestClient) -> None:
        resp = client.get("/api/pois")
        assert resp.status_code == 200

    def test_list_pois_excludes_hidden(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        client.post(
            "/api/pois",
            json={**STATIC_PAYLOAD, "id": "p2", "name": "Hidden", "visible": False},
            headers=AUTH_HEADER,
        )
        data = client.get("/api/pois").json()
        ids = {item["id"] for item in data}
        assert "p1" in ids
        assert "p2" not in ids

    def test_list_pois_patch_hidden_removes_from_list(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        client.patch("/api/pois/p1", json={"visible": False}, headers=AUTH_HEADER)
        assert client.get("/api/pois").json() == []


# ---------------------------------------------------------------------------
# GET /api/pois/{poi_id}
# ---------------------------------------------------------------------------

class TestGetPoiDetail:
    def test_get_detail_found(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.get("/api/pois/p1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "p1"
        assert data["description"] == "A description"
        assert data["notes"] == "Some notes"

    def test_get_detail_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/pois/nonexistent")
        assert resp.status_code == 404

    def test_path_omitted_by_default(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_PAYLOAD, headers=AUTH_HEADER)
        data = client.get("/api/pois/m1").json()
        assert data["path"] is None

    def test_path_returned_for_moving_poi(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_PAYLOAD, headers=AUTH_HEADER)
        data = client.get("/api/pois/m1?path=true").json()
        assert data["path"] == MOVING_PAYLOAD["path"]

    def test_path_null_for_static_poi_even_with_param(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        data = client.get("/api/pois/p1?path=true").json()
        assert data["path"] is None


# ---------------------------------------------------------------------------
# POST /api/pois
# ---------------------------------------------------------------------------

class TestCreatePoi:
    def test_create_static_poi(self, client: TestClient) -> None:
        resp = client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "p1"
        assert data["col"] == 3
        assert data["row"] == 5

    def test_create_moving_poi(self, client: TestClient) -> None:
        resp = client.post("/api/pois", json=MOVING_PAYLOAD, headers=AUTH_HEADER)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "m1"
        assert data["col"] == 1
        assert data["row"] == 2

    def test_create_poi_no_auth(self, client: TestClient) -> None:
        resp = client.post("/api/pois", json=STATIC_PAYLOAD)
        assert resp.status_code == 401

    def test_create_poi_duplicate_id(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        assert resp.status_code == 409

    def test_create_poi_invalid_body_both_col_and_path(self, client: TestClient) -> None:
        payload = {**STATIC_PAYLOAD, "path": [{"col": 1, "row": 2}]}
        resp = client.post("/api/pois", json=payload, headers=AUTH_HEADER)
        assert resp.status_code == 422

    def test_create_poi_invalid_body_neither_col_nor_path(self, client: TestClient) -> None:
        payload = {k: v for k, v in STATIC_PAYLOAD.items() if k not in ("col", "row")}
        resp = client.post("/api/pois", json=payload, headers=AUTH_HEADER)
        assert resp.status_code == 422

    def test_create_poi_bearer_token_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/pois",
            json=STATIC_PAYLOAD,
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 201

    def test_create_poi_api_key_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/pois",
            json=STATIC_PAYLOAD,
            headers={"X-API-Key": "test-token"},
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# PUT /api/pois/{poi_id}
# ---------------------------------------------------------------------------

class TestUpdatePoi:
    def test_update_poi_success(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.put("/api/pois/p1", json=UPDATE_PAYLOAD, headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["col"] == 10
        assert data["row"] == 20

    def test_update_poi_not_found(self, client: TestClient) -> None:
        resp = client.put("/api/pois/ghost", json=UPDATE_PAYLOAD, headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_update_poi_no_auth(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.put("/api/pois/p1", json=UPDATE_PAYLOAD)
        assert resp.status_code == 401

    def test_update_poi_invalid_body(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        # Both col/row and path — Pydantic validation error
        invalid = {**UPDATE_PAYLOAD, "path": [{"col": 1, "row": 2}]}
        resp = client.put("/api/pois/p1", json=invalid, headers=AUTH_HEADER)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/pois/{poi_id}
# ---------------------------------------------------------------------------


class TestPatchPoi:
    def test_patch_name_only(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch("/api/pois/p1", json={"name": "Renamed"}, headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Renamed"
        assert data["color"] == STATIC_PAYLOAD["color"]
        assert data["col"] == STATIC_PAYLOAD["col"]
        assert data["row"] == STATIC_PAYLOAD["row"]

    def test_patch_visible(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch("/api/pois/p1", json={"visible": False}, headers=AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.json()["visible"] is False

    def test_patch_static_position(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch("/api/pois/p1", json={"col": 99, "row": 88}, headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["col"] == 99
        assert data["row"] == 88

    def test_patch_static_to_moving(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch(
            "/api/pois/p1",
            json={"path": [{"col": 1, "row": 2}, {"col": 3, "row": 4}]},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["col"] == 1
        assert data["row"] == 2

    def test_patch_moving_to_static(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch("/api/pois/m1", json={"col": 5, "row": 6}, headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["col"] == 5
        assert data["row"] == 6

    def test_patch_moving_poi_keeps_path(self, client: TestClient) -> None:
        client.post("/api/pois", json=MOVING_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch("/api/pois/m1", json={"name": "Renamed"}, headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Renamed"
        assert data["col"] == MOVING_PAYLOAD["path"][0]["col"]
        assert data["row"] == MOVING_PAYLOAD["path"][0]["row"]

    def test_patch_not_found(self, client: TestClient) -> None:
        resp = client.patch("/api/pois/ghost", json={"name": "X"}, headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_patch_no_auth(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch("/api/pois/p1", json={"name": "X"})
        assert resp.status_code == 401

    def test_patch_col_without_row_invalid(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch("/api/pois/p1", json={"col": 5}, headers=AUTH_HEADER)
        assert resp.status_code == 422

    def test_patch_col_and_path_invalid(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.patch(
            "/api/pois/p1",
            json={"col": 1, "row": 2, "path": [{"col": 1, "row": 2}]},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/pois/{poi_id}
# ---------------------------------------------------------------------------

class TestDeletePoi:
    def test_delete_poi_success(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.delete("/api/pois/p1", headers=AUTH_HEADER)
        assert resp.status_code == 204
        assert resp.content == b""

    def test_delete_poi_not_found(self, client: TestClient) -> None:
        resp = client.delete("/api/pois/ghost", headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_delete_poi_no_auth(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        resp = client.delete("/api/pois/p1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# WebSocket /ws/pois
# ---------------------------------------------------------------------------


class TestPoisWebSocket:
    def test_ws_returns_only_visible_pois(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        client.post(
            "/api/pois",
            json={**STATIC_PAYLOAD, "id": "p2", "name": "Hidden", "visible": False},
            headers=AUTH_HEADER,
        )
        with client.websocket_connect("/ws/pois") as ws:
            data = ws.receive_json()
        ids = {item["id"] for item in data}
        assert "p1" in ids
        assert "p2" not in ids

    def test_ws_excludes_poi_after_patch_hidden(self, client: TestClient) -> None:
        client.post("/api/pois", json=STATIC_PAYLOAD, headers=AUTH_HEADER)
        client.patch("/api/pois/p1", json={"visible": False}, headers=AUTH_HEADER)
        with client.websocket_connect("/ws/pois") as ws:
            data = ws.receive_json()
        assert data == []
