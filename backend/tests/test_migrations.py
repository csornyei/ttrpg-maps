import importlib.util
import sqlite3
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


def load(name: str):
    path = MIGRATIONS_DIR / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def index_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    yield c
    c.close()


# ---------------------------------------------------------------------------
# 000_initial_schema
# ---------------------------------------------------------------------------


class Test000InitialSchema:
    def test_creates_all_tables(self, conn):
        load("000_initial_schema.py").up(conn)
        tables = table_names(conn)
        assert {"pois", "poi_path_points", "poi_path_index"}.issubset(tables)

    def test_creates_path_points_index(self, conn):
        load("000_initial_schema.py").up(conn)
        assert "idx_path_points_poi_id" in index_names(conn)

    def test_pois_columns(self, conn):
        load("000_initial_schema.py").up(conn)
        assert {"id", "name", "color", "description", "notes", "col", "row"}.issubset(
            column_names(conn, "pois")
        )

    def test_idempotent(self, conn):
        m = load("000_initial_schema.py")
        m.up(conn)
        m.up(conn)  # IF NOT EXISTS — must not raise

    def test_cascade_delete(self, conn):
        load("000_initial_schema.py").up(conn)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            "INSERT INTO pois VALUES ('p1', 'X', '#fff', '', '', 1, 1)"
        )
        conn.execute(
            "INSERT INTO poi_path_index VALUES ('p1', 0)"
        )
        conn.commit()
        conn.execute("DELETE FROM pois WHERE id = 'p1'")
        conn.commit()
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM poi_path_index WHERE poi_id = 'p1'"
        ).fetchone()
        assert row["c"] == 0


# ---------------------------------------------------------------------------
# 001_add_visible_to_pois
# ---------------------------------------------------------------------------


class Test001AddVisibleToPois:
    def test_adds_visible_column(self, conn):
        load("000_initial_schema.py").up(conn)
        load("001_add_visible_to_pois.py").up(conn)
        assert "visible" in column_names(conn, "pois")

    def test_visible_defaults_to_one(self, conn):
        load("000_initial_schema.py").up(conn)
        load("001_add_visible_to_pois.py").up(conn)
        conn.execute(
            "INSERT INTO pois (id, name, color, description, notes, col, row) "
            "VALUES ('p1', 'Test', '#fff', '', '', 1, 1)"
        )
        conn.commit()
        row = conn.execute("SELECT visible FROM pois WHERE id = 'p1'").fetchone()
        assert row["visible"] == 1

    def test_existing_rows_get_default(self, conn):
        load("000_initial_schema.py").up(conn)
        conn.execute(
            "INSERT INTO pois (id, name, color, description, notes, col, row) "
            "VALUES ('p1', 'Test', '#fff', '', '', 1, 1)"
        )
        conn.commit()
        load("001_add_visible_to_pois.py").up(conn)
        row = conn.execute("SELECT visible FROM pois WHERE id = 'p1'").fetchone()
        assert row["visible"] == 1


# ---------------------------------------------------------------------------
# 002_remove_step_index
# ---------------------------------------------------------------------------


class Test002RemoveStepIndex:
    def test_noop_when_step_index_absent(self, conn):
        load("000_initial_schema.py").up(conn)
        load("002_remove_step_index.py").up(conn)
        assert "step_index" not in column_names(conn, "poi_path_points")

    def test_removes_step_index_column(self, conn):
        conn.executescript(
            """
            CREATE TABLE pois (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, color TEXT NOT NULL,
                description TEXT NOT NULL, notes TEXT NOT NULL,
                col INTEGER, row INTEGER
            );
            CREATE TABLE poi_path_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poi_id TEXT NOT NULL, col INTEGER NOT NULL,
                row INTEGER NOT NULL, step_index INTEGER NOT NULL
            );
            CREATE TABLE poi_path_index (
                poi_id TEXT PRIMARY KEY, current_index INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        load("002_remove_step_index.py").up(conn)
        assert "step_index" not in column_names(conn, "poi_path_points")

    def test_preserves_rows_ordered_by_step_index(self, conn):
        conn.executescript(
            """
            CREATE TABLE pois (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, color TEXT NOT NULL,
                description TEXT NOT NULL, notes TEXT NOT NULL,
                col INTEGER, row INTEGER
            );
            CREATE TABLE poi_path_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poi_id TEXT NOT NULL, col INTEGER NOT NULL,
                row INTEGER NOT NULL, step_index INTEGER NOT NULL
            );
            CREATE TABLE poi_path_index (
                poi_id TEXT PRIMARY KEY, current_index INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO pois VALUES ('m1', 'Mover', '#fff', '', '', NULL, NULL);
            INSERT INTO poi_path_points (poi_id, col, row, step_index) VALUES ('m1', 50, 60, 2);
            INSERT INTO poi_path_points (poi_id, col, row, step_index) VALUES ('m1', 10, 20, 0);
            INSERT INTO poi_path_points (poi_id, col, row, step_index) VALUES ('m1', 30, 40, 1);
            """
        )
        load("002_remove_step_index.py").up(conn)
        points = conn.execute(
            "SELECT col, row FROM poi_path_points WHERE poi_id = 'm1' ORDER BY id"
        ).fetchall()
        assert [(p["col"], p["row"]) for p in points] == [(10, 20), (30, 40), (50, 60)]


# ---------------------------------------------------------------------------
# 003_migrate_path_index
# ---------------------------------------------------------------------------


class Test003MigratePathIndex:
    def test_seeds_index_zero_without_path_index_column(self, conn):
        load("000_initial_schema.py").up(conn)
        conn.execute(
            "INSERT INTO pois (id, name, color, description, notes, col, row) "
            "VALUES ('m1', 'Mover', '#fff', '', '', NULL, NULL)"
        )
        conn.commit()
        load("003_migrate_path_index.py").up(conn)
        row = conn.execute(
            "SELECT current_index FROM poi_path_index WHERE poi_id = 'm1'"
        ).fetchone()
        assert row is not None
        assert row["current_index"] == 0

    def test_migrates_path_index_column_values(self, conn):
        conn.executescript(
            """
            CREATE TABLE pois (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, color TEXT NOT NULL,
                description TEXT NOT NULL, notes TEXT NOT NULL,
                col INTEGER, row INTEGER, path_index INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE poi_path_index (
                poi_id TEXT PRIMARY KEY, current_index INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO pois VALUES ('m1', 'Mover', '#fff', '', '', NULL, NULL, 2);
            """
        )
        load("003_migrate_path_index.py").up(conn)
        row = conn.execute(
            "SELECT current_index FROM poi_path_index WHERE poi_id = 'm1'"
        ).fetchone()
        assert row is not None
        assert row["current_index"] == 2

    def test_does_not_overwrite_existing_index_entry(self, conn):
        load("000_initial_schema.py").up(conn)
        conn.execute(
            "INSERT INTO pois (id, name, color, description, notes, col, row) "
            "VALUES ('m1', 'Mover', '#fff', '', '', NULL, NULL)"
        )
        conn.execute("INSERT INTO poi_path_index VALUES ('m1', 5)")
        conn.commit()
        load("003_migrate_path_index.py").up(conn)
        row = conn.execute(
            "SELECT current_index FROM poi_path_index WHERE poi_id = 'm1'"
        ).fetchone()
        assert row["current_index"] == 5
