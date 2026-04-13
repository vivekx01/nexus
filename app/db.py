"""
SQLite-backed access control for Nexus.
All functions open and close their own connection — safe for use across
the Telegram bot process and the FastAPI process sharing the same db file.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("NEXUS_DB_PATH", "nexus.db"))


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(seed_ids: list[int] | None = None) -> None:
    """Create schema and optionally seed initial allowed chat IDs."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS allowed_users (
                chat_id    INTEGER PRIMARY KEY,
                label      TEXT    NOT NULL DEFAULT '',
                granted_at TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        con.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('public_mode', 'false')"
        )
        if seed_ids:
            con.executemany(
                "INSERT OR IGNORE INTO allowed_users (chat_id) VALUES (?)",
                [(cid,) for cid in seed_ids],
            )


def is_allowed(chat_id: int) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM allowed_users WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return row is not None


def grant_access(chat_id: int, label: str = "") -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO allowed_users (chat_id, label) VALUES (?, ?)",
            (chat_id, label),
        )


def revoke_access(chat_id: int) -> None:
    with _conn() as con:
        con.execute(
            "DELETE FROM allowed_users WHERE chat_id = ?", (chat_id,)
        )


def is_public_mode() -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT value FROM settings WHERE key = 'public_mode'"
        ).fetchone()
    return bool(row and row["value"] == "true")


def set_public_mode(enabled: bool) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('public_mode', ?)",
            ("true" if enabled else "false",),
        )


def list_users() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT chat_id, label, granted_at FROM allowed_users ORDER BY granted_at"
        ).fetchall()
    return [dict(row) for row in rows]
