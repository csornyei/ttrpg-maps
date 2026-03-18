import sqlite3
from pathlib import Path
from threading import RLock

from src.models import HexCoord, PoiCreate, PoiDetail, PoiSummary, PoiUpdate

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "pois.db"


class PoiStore:
    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            resolved_db_path = str(DB_PATH)
            self._should_seed = True
        else:
            resolved_db_path = db_path
            self._should_seed = False
        self._lock = RLock()
        self._connection = sqlite3.connect(resolved_db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS pois (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    color TEXT NOT NULL,
                    description TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    col INTEGER,
                    row INTEGER,
                    CHECK ((col IS NOT NULL AND row IS NOT NULL) OR (col IS NULL AND row IS NULL))
                );
                """
            )

            columns = self._connection.execute(
                "PRAGMA table_info(poi_path_points)"
            ).fetchall()
            has_step_index = any(column[1] == "step_index" for column in columns)

            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS poi_path_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poi_id TEXT NOT NULL,
                    col INTEGER NOT NULL,
                    row INTEGER NOT NULL,
                    FOREIGN KEY (poi_id) REFERENCES pois(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS poi_path_index (
                    poi_id TEXT PRIMARY KEY,
                    current_index INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (poi_id) REFERENCES pois(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_path_points_poi_id
                ON poi_path_points (poi_id, id);
                """
            )

            if has_step_index:
                self._connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS poi_path_points_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        poi_id TEXT NOT NULL,
                        col INTEGER NOT NULL,
                        row INTEGER NOT NULL,
                        FOREIGN KEY (poi_id) REFERENCES pois(id) ON DELETE CASCADE
                    );

                    INSERT INTO poi_path_points_new (poi_id, col, row)
                    SELECT poi_id, col, row
                    FROM poi_path_points
                    ORDER BY poi_id, step_index;

                    DROP TABLE poi_path_points;
                    ALTER TABLE poi_path_points_new RENAME TO poi_path_points;

                    CREATE INDEX IF NOT EXISTS idx_path_points_poi_id
                    ON poi_path_points (poi_id, id);
                    """
                )

            pois_columns = self._connection.execute(
                "PRAGMA table_info(pois)"
            ).fetchall()
            has_poi_path_index_column = any(
                column[1] == "path_index" for column in pois_columns
            )

            if has_poi_path_index_column:
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO poi_path_index (poi_id, current_index)
                    SELECT id, path_index
                    FROM pois
                    WHERE col IS NULL AND row IS NULL
                    """
                )
            else:
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO poi_path_index (poi_id, current_index)
                    SELECT id, 0
                    FROM pois
                    WHERE col IS NULL AND row IS NULL
                    """
                )

            self._connection.commit()

    def _get_path_locked(self, poi_id: str) -> list[HexCoord]:
        rows = self._connection.execute(
            """
            SELECT col, row
            FROM poi_path_points
            WHERE poi_id = ?
            ORDER BY id
            """,
            (poi_id,),
        ).fetchall()
        return [HexCoord(col=row["col"], row=row["row"]) for row in rows]

    def _get_path_length_locked(self, poi_id: str) -> int:
        count_row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM poi_path_points WHERE poi_id = ?",
            (poi_id,),
        ).fetchone()
        return count_row["count"] if count_row else 0

    def _get_or_create_current_index_locked(self, poi_id: str) -> int:
        index_row = self._connection.execute(
            "SELECT current_index FROM poi_path_index WHERE poi_id = ?",
            (poi_id,),
        ).fetchone()
        if index_row is not None:
            return index_row["current_index"]

        self._connection.execute(
            "INSERT INTO poi_path_index (poi_id, current_index) VALUES (?, 0)",
            (poi_id,),
        )
        return 0

    def _resolve_position_locked(self, poi_row: sqlite3.Row) -> HexCoord:
        if poi_row["col"] is not None and poi_row["row"] is not None:
            return HexCoord(col=poi_row["col"], row=poi_row["row"])

        path_length = self._get_path_length_locked(poi_row["id"])
        if path_length == 0:
            raise ValueError(f"Moving POI '{poi_row['id']}' has no path points")

        current_index = self._get_or_create_current_index_locked(poi_row["id"])
        normalized_index = current_index % path_length

        if normalized_index != current_index:
            self._connection.execute(
                "UPDATE poi_path_index SET current_index = ? WHERE poi_id = ?",
                (normalized_index, poi_row["id"]),
            )

        position_row = self._connection.execute(
            """
            SELECT col, row
            FROM poi_path_points
            WHERE poi_id = ?
            ORDER BY id
            LIMIT 1 OFFSET ?
            """,
            (poi_row["id"], normalized_index),
        ).fetchone()

        if position_row is None:
            raise ValueError(f"Moving POI '{poi_row['id']}' has no resolvable point")

        return HexCoord(col=position_row["col"], row=position_row["row"])

    def _insert_poi_locked(
        self,
        *,
        poi_id: str,
        name: str,
        color: str,
        description: str,
        notes: str,
        col: int | None,
        row: int | None,
        path: list[HexCoord] | None,
    ) -> None:
        has_path = path is not None
        if has_path:
            col = None
            row = None

        self._connection.execute(
            """
            INSERT INTO pois (id, name, color, description, notes, col, row)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (poi_id, name, color, description, notes, col, row),
        )

        if path is not None:
            self._connection.executemany(
                """
                INSERT INTO poi_path_points (poi_id, col, row)
                VALUES (?, ?, ?)
                """,
                [(poi_id, coord.col, coord.row) for coord in path],
            )
            self._connection.execute(
                "INSERT INTO poi_path_index (poi_id, current_index) VALUES (?, 0)",
                (poi_id,),
            )

    def _get_poi_row_locked(self, poi_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            """
            SELECT id, name, color, description, notes, col, row
            FROM pois
            WHERE id = ?
            """,
            (poi_id,),
        ).fetchone()

    def advance_moving_pois(self) -> None:
        with self._lock:
            moving_pois = self._connection.execute(
                """
                SELECT id
                FROM pois
                WHERE col IS NULL AND row IS NULL
                """
            ).fetchall()

            for poi in moving_pois:
                path_length = self._get_path_length_locked(poi["id"])
                if path_length == 0:
                    continue

                current_index = self._get_or_create_current_index_locked(poi["id"])
                next_index = (current_index + 1) % path_length
                self._connection.execute(
                    "UPDATE poi_path_index SET current_index = ? WHERE poi_id = ?",
                    (next_index, poi["id"]),
                )

            self._connection.commit()

    def get_all_summaries(self) -> list[PoiSummary]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, name, color, col, row
                FROM pois
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()

            summaries: list[PoiSummary] = []
            for row in rows:
                position = self._resolve_position_locked(row)
                summaries.append(
                    PoiSummary(
                        id=row["id"],
                        name=row["name"],
                        col=position.col,
                        row=position.row,
                        color=row["color"],
                    )
                )
            return summaries

    def get_detail_by_id(self, poi_id: str) -> PoiDetail | None:
        with self._lock:
            row = self._get_poi_row_locked(poi_id)
            if row is None:
                return None

            position = self._resolve_position_locked(row)
            return PoiDetail(
                id=row["id"],
                name=row["name"],
                col=position.col,
                row=position.row,
                color=row["color"],
                description=row["description"],
                notes=row["notes"],
            )

    def create_poi(self, poi: PoiCreate) -> PoiDetail:
        with self._lock:
            if self._get_poi_row_locked(poi.id) is not None:
                raise ValueError(f"POI '{poi.id}' already exists")

            self._insert_poi_locked(
                poi_id=poi.id,
                name=poi.name,
                color=poi.color,
                description=poi.description,
                notes=poi.notes,
                col=poi.col,
                row=poi.row,
                path=poi.path,
            )
            self._connection.commit()

        detail = self.get_detail_by_id(poi.id)
        if detail is None:
            raise RuntimeError("Created POI could not be loaded")
        return detail

    def update_poi(self, poi_id: str, poi: PoiUpdate) -> PoiDetail | None:
        with self._lock:
            if self._get_poi_row_locked(poi_id) is None:
                return None

            static_col = poi.col if poi.path is None else None
            static_row = poi.row if poi.path is None else None

            self._connection.execute(
                """
                UPDATE pois
                SET name = ?, color = ?, description = ?, notes = ?, col = ?, row = ?
                WHERE id = ?
                """,
                (
                    poi.name,
                    poi.color,
                    poi.description,
                    poi.notes,
                    static_col,
                    static_row,
                    poi_id,
                ),
            )
            self._connection.execute(
                "DELETE FROM poi_path_points WHERE poi_id = ?",
                (poi_id,),
            )
            self._connection.execute(
                "DELETE FROM poi_path_index WHERE poi_id = ?",
                (poi_id,),
            )

            if poi.path is not None:
                self._connection.executemany(
                    """
                    INSERT INTO poi_path_points (poi_id, col, row)
                    VALUES (?, ?, ?)
                    """,
                    [(poi_id, coord.col, coord.row) for coord in poi.path],
                )
                self._connection.execute(
                    "INSERT INTO poi_path_index (poi_id, current_index) VALUES (?, 0)",
                    (poi_id,),
                )

            self._connection.commit()

        return self.get_detail_by_id(poi_id)

    def delete_poi(self, poi_id: str) -> bool:
        with self._lock:
            delete_result = self._connection.execute(
                "DELETE FROM pois WHERE id = ?",
                (poi_id,),
            )
            self._connection.commit()
            return delete_result.rowcount > 0

    def is_healthy(self) -> bool:
        try:
            with self._lock:
                row = self._connection.execute("SELECT 1 AS healthy").fetchone()
                return row is not None and row["healthy"] == 1
        except sqlite3.Error:
            return False


poi_store = PoiStore()
