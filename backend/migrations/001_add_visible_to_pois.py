import sqlite3


def up(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(pois)").fetchall()}
    if "visible" in existing:
        return
    conn.execute("ALTER TABLE pois ADD COLUMN visible INTEGER NOT NULL DEFAULT 1")
    conn.commit()
