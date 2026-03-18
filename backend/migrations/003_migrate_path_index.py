import sqlite3


def up(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(pois)").fetchall()
    has_path_index = any(col[1] == "path_index" for col in columns)

    if has_path_index:
        conn.execute(
            """
            INSERT OR IGNORE INTO poi_path_index (poi_id, current_index)
            SELECT id, path_index
            FROM pois
            WHERE col IS NULL AND row IS NULL
            """
        )
    else:
        conn.execute(
            """
            INSERT OR IGNORE INTO poi_path_index (poi_id, current_index)
            SELECT id, 0
            FROM pois
            WHERE col IS NULL AND row IS NULL
            """
        )
    conn.commit()
