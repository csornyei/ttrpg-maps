import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
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
