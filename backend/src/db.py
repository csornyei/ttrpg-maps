import importlib.util
import sqlite3
from pathlib import Path
from threading import RLock

from src.observability import logger


class Database:
    def __init__(self, db_path: str, migrations_dir: Path) -> None:
        logger.info("Initializing database with path: %s", db_path)
        self.lock = RLock()
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._run_migrations(migrations_dir)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._connection.execute(sql, params)

    def executemany(self, sql: str, params) -> sqlite3.Cursor:
        return self._connection.executemany(sql, params)

    def commit(self) -> None:
        self._connection.commit()

    def _run_migrations(self, migrations_dir: Path) -> None:
        if not migrations_dir.is_dir():
            raise RuntimeError(
                f"Migrations directory not found: {migrations_dir}. "
                "Ensure the 'migrations' directory is present alongside 'src'."
            )
        logger.info("Running database migrations from directory: %s", migrations_dir)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._connection.commit()

        applied = {
            row[0]
            for row in self._connection.execute(
                "SELECT name FROM schema_migrations"
            ).fetchall()
        }

        for path in sorted(migrations_dir.glob("*.py")):
            if path.name in applied:
                continue
            self._apply_migration(path)
            self._connection.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)", (path.name,)
            )
            self._connection.commit()
            logger.info("Applied migration: %s", path.name)

    def _apply_migration(self, path: Path) -> None:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.up(self._connection)
