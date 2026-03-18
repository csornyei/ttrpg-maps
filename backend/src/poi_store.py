import sqlite3
from pathlib import Path

from src.db import Database
from src.models import HexCoord, PoiCreate, PoiDetail, PoiPatch, PoiSummary, PoiUpdate

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "pois.db"
MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


class PoiStore:
    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            resolved_db_path = str(DB_PATH)
            self._should_seed = True
        else:
            resolved_db_path = db_path
            self._should_seed = False
        self._db = Database(resolved_db_path, MIGRATIONS_DIR)

    def _get_path_locked(self, poi_id: str) -> list[HexCoord]:
        rows = self._db.execute(
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
        count_row = self._db.execute(
            "SELECT COUNT(*) AS count FROM poi_path_points WHERE poi_id = ?",
            (poi_id,),
        ).fetchone()
        return count_row["count"] if count_row else 0

    def _get_or_create_current_index_locked(self, poi_id: str) -> int:
        index_row = self._db.execute(
            "SELECT current_index FROM poi_path_index WHERE poi_id = ?",
            (poi_id,),
        ).fetchone()
        if index_row is not None:
            return index_row["current_index"]

        self._db.execute(
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
            self._db.execute(
                "UPDATE poi_path_index SET current_index = ? WHERE poi_id = ?",
                (normalized_index, poi_row["id"]),
            )

        position_row = self._db.execute(
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
        visible: bool,
        col: int | None,
        row: int | None,
        path: list[HexCoord] | None,
    ) -> None:
        has_path = path is not None
        if has_path:
            col = None
            row = None

        self._db.execute(
            """
            INSERT INTO pois (id, name, color, description, notes, visible, col, row)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (poi_id, name, color, description, notes, visible, col, row),
        )

        if path is not None:
            self._db.executemany(
                """
                INSERT INTO poi_path_points (poi_id, col, row)
                VALUES (?, ?, ?)
                """,
                [(poi_id, coord.col, coord.row) for coord in path],
            )
            self._db.execute(
                "INSERT INTO poi_path_index (poi_id, current_index) VALUES (?, 0)",
                (poi_id,),
            )

    def _get_poi_row_locked(self, poi_id: str) -> sqlite3.Row | None:
        return self._db.execute(
            """
            SELECT id, name, color, description, notes, visible, col, row
            FROM pois
            WHERE id = ?
            """,
            (poi_id,),
        ).fetchone()

    def advance_moving_pois(self) -> None:
        with self._db.lock:
            moving_pois = self._db.execute(
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
                self._db.execute(
                    "UPDATE poi_path_index SET current_index = ? WHERE poi_id = ?",
                    (next_index, poi["id"]),
                )

            self._db.commit()

    def get_all_summaries(self) -> list[PoiSummary]:
        with self._db.lock:
            rows = self._db.execute(
                """
                SELECT id, name, color, visible, col, row
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
                        visible=bool(row["visible"]),
                    )
                )
            return summaries

    def get_detail_by_id(self, poi_id: str) -> PoiDetail | None:
        with self._db.lock:
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
                visible=bool(row["visible"]),
                description=row["description"],
                notes=row["notes"],
            )

    def create_poi(self, poi: PoiCreate) -> PoiDetail:
        with self._db.lock:
            if self._get_poi_row_locked(poi.id) is not None:
                raise ValueError(f"POI '{poi.id}' already exists")

            self._insert_poi_locked(
                poi_id=poi.id,
                name=poi.name,
                color=poi.color,
                description=poi.description,
                notes=poi.notes,
                visible=poi.visible,
                col=poi.col,
                row=poi.row,
                path=poi.path,
            )
            self._db.commit()

        detail = self.get_detail_by_id(poi.id)
        if detail is None:
            raise RuntimeError("Created POI could not be loaded")
        return detail

    def update_poi(self, poi_id: str, poi: PoiUpdate) -> PoiDetail | None:
        with self._db.lock:
            if self._get_poi_row_locked(poi_id) is None:
                return None

            static_col = poi.col if poi.path is None else None
            static_row = poi.row if poi.path is None else None

            self._db.execute(
                """
                UPDATE pois
                SET name = ?, color = ?, description = ?, notes = ?, visible = ?, col = ?, row = ?
                WHERE id = ?
                """,
                (
                    poi.name,
                    poi.color,
                    poi.description,
                    poi.notes,
                    poi.visible,
                    static_col,
                    static_row,
                    poi_id,
                ),
            )
            self._db.execute(
                "DELETE FROM poi_path_points WHERE poi_id = ?",
                (poi_id,),
            )
            self._db.execute(
                "DELETE FROM poi_path_index WHERE poi_id = ?",
                (poi_id,),
            )

            if poi.path is not None:
                self._db.executemany(
                    """
                    INSERT INTO poi_path_points (poi_id, col, row)
                    VALUES (?, ?, ?)
                    """,
                    [(poi_id, coord.col, coord.row) for coord in poi.path],
                )
                self._db.execute(
                    "INSERT INTO poi_path_index (poi_id, current_index) VALUES (?, 0)",
                    (poi_id,),
                )

            self._db.commit()

        return self.get_detail_by_id(poi_id)

    def patch_poi(self, poi_id: str, patch: PoiPatch) -> PoiDetail | None:
        with self._db.lock:
            row = self._get_poi_row_locked(poi_id)
            if row is None:
                return None

            # Determine new position before any writes
            if patch.path is not None:
                new_col, new_row, new_path = None, None, patch.path
            elif patch.col is not None:
                new_col, new_row, new_path = patch.col, patch.row, None
            else:
                new_col = row["col"]
                new_row = row["row"]
                new_path = (
                    None if row["col"] is not None else self._get_path_locked(poi_id)
                )

            self._db.execute(
                """
                UPDATE pois
                SET name = ?, color = ?, description = ?, notes = ?, visible = ?, col = ?, row = ?
                WHERE id = ?
                """,
                (
                    patch.name if patch.name is not None else row["name"],
                    patch.color if patch.color is not None else row["color"],
                    patch.description if patch.description is not None else row["description"],
                    patch.notes if patch.notes is not None else row["notes"],
                    patch.visible if patch.visible is not None else bool(row["visible"]),
                    new_col,
                    new_row,
                    poi_id,
                ),
            )
            self._db.execute("DELETE FROM poi_path_points WHERE poi_id = ?", (poi_id,))
            self._db.execute("DELETE FROM poi_path_index WHERE poi_id = ?", (poi_id,))

            if new_path is not None:
                self._db.executemany(
                    "INSERT INTO poi_path_points (poi_id, col, row) VALUES (?, ?, ?)",
                    [(poi_id, coord.col, coord.row) for coord in new_path],
                )
                self._db.execute(
                    "INSERT INTO poi_path_index (poi_id, current_index) VALUES (?, 0)",
                    (poi_id,),
                )

            self._db.commit()

        return self.get_detail_by_id(poi_id)

    def delete_poi(self, poi_id: str) -> bool:
        with self._db.lock:
            delete_result = self._db.execute(
                "DELETE FROM pois WHERE id = ?",
                (poi_id,),
            )
            self._db.commit()
            return delete_result.rowcount > 0

    def is_healthy(self) -> bool:
        try:
            with self._db.lock:
                row = self._db.execute("SELECT 1 AS healthy").fetchone()
                return row is not None and row["healthy"] == 1
        except sqlite3.Error:
            return False


poi_store = PoiStore()
