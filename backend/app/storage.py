from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from .models import SessionRecord, ensure_utc


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return ensure_utc(datetime.fromisoformat(value))


class SQLiteStorage:
    def __init__(self, database_path: Path, default_weight_kg: float) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self._database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize(default_weight_kg)

    def _initialize(self, default_weight_kg: float) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    is_active INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    last_update_time TEXT NOT NULL,
                    step_count INTEGER NOT NULL,
                    burned_calories REAL NOT NULL,
                    distance_walked REAL NOT NULL,
                    last_reported_calories INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                ("weight", str(default_weight_kg)),
            )
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def get_weight(self) -> float:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM settings WHERE key = ?",
                ("weight",),
            ).fetchone()
            return float(row[0])

    def set_weight(self, weight: float) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("weight", str(weight)),
            )
            self._connection.commit()

    def list_sessions(self) -> list[SessionRecord]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM sessions ORDER BY is_active DESC, start_time DESC"
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def list_active_sessions(self) -> list[SessionRecord]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM sessions WHERE is_active = 1 ORDER BY start_time DESC"
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_active_session(self, device_id: str | None = None) -> SessionRecord | None:
        query = "SELECT * FROM sessions WHERE is_active = 1"
        parameters: tuple[str, ...] = ()
        if device_id is not None:
            query += " AND device_id = ?"
            parameters = (device_id,)
        query += " ORDER BY start_time DESC LIMIT 1"

        with self._lock:
            row = self._connection.execute(query, parameters).fetchone()
        return self._row_to_session(row) if row else None

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            self._connection.commit()
        return cursor.rowcount > 0

    def save_session(self, session: SessionRecord) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO sessions(
                    session_id,
                    device_id,
                    is_active,
                    start_time,
                    end_time,
                    last_update_time,
                    step_count,
                    burned_calories,
                    distance_walked,
                    last_reported_calories
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    device_id = excluded.device_id,
                    is_active = excluded.is_active,
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    last_update_time = excluded.last_update_time,
                    step_count = excluded.step_count,
                    burned_calories = excluded.burned_calories,
                    distance_walked = excluded.distance_walked,
                    last_reported_calories = excluded.last_reported_calories
                """,
                (
                    session.session_id,
                    session.device_id,
                    int(session.is_active),
                    session.start_time.isoformat(),
                    session.end_time.isoformat() if session.end_time else None,
                    session.last_update_time.isoformat(),
                    session.step_count,
                    session.burned_calories,
                    session.distance_walked,
                    session.last_reported_calories,
                ),
            )
            self._connection.commit()

    def _row_to_session(self, row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            session_id=row["session_id"],
            device_id=row["device_id"],
            is_active=bool(row["is_active"]),
            start_time=ensure_utc(datetime.fromisoformat(row["start_time"])),
            end_time=_parse_datetime(row["end_time"]),
            last_update_time=ensure_utc(datetime.fromisoformat(row["last_update_time"])),
            step_count=row["step_count"],
            burned_calories=row["burned_calories"],
            distance_walked=row["distance_walked"],
            last_reported_calories=row["last_reported_calories"],
        )