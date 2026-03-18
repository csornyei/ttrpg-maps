import pytest

from src.models import HexCoord, PoiCreate, PoiUpdate
from src.poi_store import PoiStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_static(
    poi_id: str, name: str = "Test POI", col: int = 3, row: int = 5
) -> PoiCreate:
    return PoiCreate(
        id=poi_id,
        name=name,
        color="#ff0000",
        description="desc",
        notes="notes",
        col=col,
        row=row,
    )


def make_moving(poi_id: str, name: str = "Moving POI") -> PoiCreate:
    return PoiCreate(
        id=poi_id,
        name=name,
        color="#00ff00",
        description="desc",
        notes="notes",
        path=[HexCoord(col=1, row=2), HexCoord(col=3, row=4), HexCoord(col=5, row=6)],
    )


# ---------------------------------------------------------------------------
# Schema & seeding
# ---------------------------------------------------------------------------


class TestSchemaAndSeeding:
    def test_schema_creates_tables(self, store: PoiStore) -> None:
        conn = store._connection
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "pois" in tables
        assert "poi_path_points" in tables
        assert "poi_path_index" in tables

    def test_empty_store_no_seed(self, store: PoiStore) -> None:
        assert store.get_all_summaries() == []

    def test_is_healthy_returns_true(self, store: PoiStore) -> None:
        assert store.is_healthy() is True


# ---------------------------------------------------------------------------
# Static POI CRUD
# ---------------------------------------------------------------------------


class TestStaticPoiCrud:
    def test_create_static_poi(self, store: PoiStore) -> None:
        poi = store.create_poi(make_static("p1"))
        assert poi.id == "p1"
        assert poi.col == 3
        assert poi.row == 5
        assert poi.color == "#ff0000"

    def test_create_static_poi_duplicate_id_raises(self, store: PoiStore) -> None:
        store.create_poi(make_static("p1"))
        with pytest.raises(ValueError, match="already exists"):
            store.create_poi(make_static("p1"))

    def test_get_all_summaries_ordered_by_name(self, store: PoiStore) -> None:
        store.create_poi(make_static("z", name="Zephyr"))
        store.create_poi(make_static("a", name="Alpha"))
        store.create_poi(
            make_static("m", name="mango")
        )  # lowercase, still collates after Alpha
        summaries = store.get_all_summaries()
        names = [s.name for s in summaries]
        assert names == sorted(names, key=str.lower)

    def test_get_detail_not_found_returns_none(self, store: PoiStore) -> None:
        assert store.get_detail_by_id("nonexistent") is None

    def test_update_static_poi(self, store: PoiStore) -> None:
        store.create_poi(make_static("p1"))
        update = PoiUpdate(
            name="Updated",
            color="#0000ff",
            description="new desc",
            notes="new notes",
            col=10,
            row=20,
        )
        detail = store.update_poi("p1", update)
        assert detail is not None
        assert detail.name == "Updated"
        assert detail.col == 10
        assert detail.row == 20
        assert detail.color == "#0000ff"

    def test_delete_static_poi(self, store: PoiStore) -> None:
        store.create_poi(make_static("p1"))
        deleted = store.delete_poi("p1")
        assert deleted is True
        assert store.get_detail_by_id("p1") is None

    def test_delete_nonexistent_returns_false(self, store: PoiStore) -> None:
        assert store.delete_poi("ghost") is False


# ---------------------------------------------------------------------------
# Moving POI CRUD
# ---------------------------------------------------------------------------


class TestMovingPoiCrud:
    def test_create_moving_poi(self, store: PoiStore) -> None:
        store.create_poi(make_moving("m1"))
        detail = store.get_detail_by_id("m1")
        assert detail is not None
        # Should resolve to first waypoint
        assert detail.col == 1
        assert detail.row == 2

    def test_advance_moving_poi(self, store: PoiStore) -> None:
        store.create_poi(make_moving("m1"))
        store.advance_moving_pois()
        detail = store.get_detail_by_id("m1")
        assert detail is not None
        assert detail.col == 3
        assert detail.row == 4

    def test_advance_wraps_around(self, store: PoiStore) -> None:
        # path has 3 waypoints; advance 3 times → wraps to index 0
        store.create_poi(make_moving("m1"))
        store.advance_moving_pois()
        store.advance_moving_pois()
        store.advance_moving_pois()
        detail = store.get_detail_by_id("m1")
        assert detail is not None
        assert detail.col == 1
        assert detail.row == 2

    def test_update_static_to_moving(self, store: PoiStore) -> None:
        store.create_poi(make_static("p1"))
        update = PoiUpdate(
            name="Now Moving",
            color="#ff0000",
            description="desc",
            notes="notes",
            path=[HexCoord(col=7, row=8), HexCoord(col=9, row=10)],
        )
        detail = store.update_poi("p1", update)
        assert detail is not None
        assert detail.col == 7
        assert detail.row == 8

    def test_update_moving_to_static(self, store: PoiStore) -> None:
        store.create_poi(make_moving("m1"))
        update = PoiUpdate(
            name="Now Static",
            color="#00ff00",
            description="desc",
            notes="notes",
            col=99,
            row=88,
        )
        detail = store.update_poi("m1", update)
        assert detail is not None
        assert detail.col == 99
        assert detail.row == 88

    def test_delete_moving_poi_cascades_path(self, store: PoiStore) -> None:
        store.create_poi(make_moving("m1"))
        store.delete_poi("m1")
        conn = store._connection
        points = conn.execute(
            "SELECT COUNT(*) AS c FROM poi_path_points WHERE poi_id = 'm1'"
        ).fetchone()
        index = conn.execute(
            "SELECT COUNT(*) AS c FROM poi_path_index WHERE poi_id = 'm1'"
        ).fetchone()
        assert points["c"] == 0
        assert index["c"] == 0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_is_healthy_with_broken_db(self, store: PoiStore) -> None:
        store._connection.close()
        assert store.is_healthy() is False
