"""SQLite persistence layer for hike sessions and user body weight.

Security notes
--------------
* All SQL statements use parameter binding (?-placeholders) to prevent
  SQL-injection attacks.
* WAL journal mode + PRAGMA synchronous=NORMAL guarantees that completed
  sessions survive an unexpected power-off (RPi requirement).
* A single threading.Lock serialises every write so the same HubDatabase
  instance can safely be shared between the BLE asyncio task and the
  ASGI web-server without sqlite3 multi-thread conflicts.
"""

import sqlite3
import threading
from typing import Optional

import hike

DB_FILE_NAME = "sessions.db"

_CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id       INTEGER PRIMARY KEY,
    device_id        TEXT    NOT NULL DEFAULT '',
    start_time       TEXT    NOT NULL DEFAULT '',
    end_time         TEXT    NOT NULL DEFAULT '',
    duration_seconds REAL    NOT NULL DEFAULT 0,
    steps            INTEGER NOT NULL DEFAULT 0,
    calories_burnt   INTEGER NOT NULL DEFAULT 0,
    body_weight_kg   REAL    NOT NULL DEFAULT 70.0
)
"""

_CREATE_WEIGHT_TABLE = """
CREATE TABLE IF NOT EXISTS weight (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    body_weight_kg REAL    NOT NULL
)
"""

_SELECT_SESSION_COLS = (
    "session_id, device_id, start_time, end_time, "
    "duration_seconds, steps, calories_burnt, body_weight_kg"
)


class HubDatabase:
    """SQLite-backed storage for hike sessions and user body weight.

    Attributes:
        _lock: serialises writes across threads.
        _con:  sqlite3 connection (check_same_thread=False, protected by _lock).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._con = sqlite3.connect(DB_FILE_NAME, check_same_thread=False)
        self._con.execute("PRAGMA journal_mode=WAL")    # survive power-off
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._con.execute(_CREATE_SESSIONS_TABLE)
        self._con.execute(_CREATE_WEIGHT_TABLE)
        self._con.commit()

    # ── weight ─────────────────────────────────────────────────────────────────────

    def save_weight(self, weight_kg: float) -> None:
        """Persist the user’s body weight (upsert: only one row is kept)."""
        with self._lock:
            self._con.execute(
                "INSERT INTO weight (id, body_weight_kg) VALUES (1, ?)"
                " ON CONFLICT(id) DO UPDATE SET body_weight_kg = excluded.body_weight_kg",
                (weight_kg,),
            )
            self._con.commit()

    def get_weight(self) -> float:
        """Return the stored body weight, or DEFAULT_WEIGHT_KG if none is set."""
        with self._lock:
            row = self._con.execute(
                "SELECT body_weight_kg FROM weight WHERE id = 1"
            ).fetchone()
        return row[0] if row else hike.DEFAULT_WEIGHT_KG

    # ── sessions ───────────────────────────────────────────────────────────────

    def save_session(self, session: hike.HikeSession) -> int:
        """Insert a completed session and return its auto-generated session_id."""
        start_str = session.start_time.isoformat() if session.start_time else ""
        end_str   = session.end_time.isoformat()   if session.end_time   else ""
        with self._lock:
            cur = self._con.execute(
                "INSERT INTO sessions"
                " (device_id, start_time, end_time, duration_seconds,"
                "  steps, calories_burnt, body_weight_kg)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session.device_id,
                    start_str,
                    end_str,
                    session.duration_seconds,
                    session.steps,
                    session.calories_burnt,
                    session.body_weight_kg,
                ),
            )
            self._con.commit()
            return cur.lastrowid

    def delete_session(self, session_id: int) -> None:
        """Remove a session by primary key."""
        with self._lock:
            self._con.execute(
                "DELETE FROM sessions WHERE session_id = ?", (session_id,)
            )
            self._con.commit()

    def get_sessions(self) -> list[hike.HikeSession]:
        """Return all completed sessions ordered by session_id."""
        with self._lock:
            rows = self._con.execute(
                f"SELECT {_SELECT_SESSION_COLS} FROM sessions ORDER BY session_id"
            ).fetchall()
        return [hike.from_row(row) for row in rows]

    def get_session(self, session_id: int) -> Optional[hike.HikeSession]:
        """Return a single session by ID, or None if not found."""
        with self._lock:
            rows = self._con.execute(
                f"SELECT {_SELECT_SESSION_COLS} FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        return hike.from_row(rows[0]) if rows else None

    def __del__(self) -> None:
        try:
            self._con.close()
        except Exception:
            pass