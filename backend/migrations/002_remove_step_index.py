import sqlite3


def up(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(poi_path_points)").fetchall()
    if not any(col[1] == "step_index" for col in columns):
        return

    conn.executescript(
        """
        CREATE TABLE poi_path_points_new (
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
