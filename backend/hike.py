from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

# ── Calorie constants ─────────────────────────────────────────────────────────
MET_HIKING = 6.0          # Metabolic Equivalent of Task for hiking
SECONDS_PER_STEP = 0.5    # assumed average hiking pace (steps per second)
HOURS_PER_STEP = SECONDS_PER_STEP / 3600.0
AVERAGE_STRIDE_M = 0.75   # average hiking stride length in metres
DEFAULT_WEIGHT_KG = 70.0  # fallback body weight when none is stored


def calc_kcal(steps: int, weight_kg: float) -> int:
    """MET-based calorie estimate adjusted for body weight.

    Formula: kcal = MET × weight_kg × (steps × time_per_step_hours)

    Args:
        steps: total step count.
        weight_kg: user body weight in kilograms.

    Returns:
        Kilocalories burned rounded to the nearest integer.
    """
    return round(MET_HIKING * weight_kg * HOURS_PER_STEP * steps)


# ── Completed session model ───────────────────────────────────────────────────

class HikeSession:
    """A completed hiking session stored in the database."""

    def __init__(
        self,
        session_id: int = 0,
        device_id: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        duration_seconds: float = 0.0,
        steps: int = 0,
        calories_burnt: int = 0,
        body_weight_kg: float = DEFAULT_WEIGHT_KG,
    ):
        self.id = session_id
        self.device_id = device_id
        self.start_time = start_time
        self.end_time = end_time
        self.duration_seconds = duration_seconds
        self.steps = steps
        self.calories_burnt = calories_burnt
        self.body_weight_kg = body_weight_kg

    def to_dict(self) -> dict:
        """Serialise to the camelCase JSON shape expected by the web UI."""
        return {
            "isActive": False,
            "sessionId": str(self.id),
            "startTime": self.start_time.isoformat() if self.start_time else None,
            "endTime": self.end_time.isoformat() if self.end_time else None,
            "stepCount": self.steps,
            "burnedCalories": self.calories_burnt,
            "distanceWalked": round(self.steps * AVERAGE_STRIDE_M),
            'bodyWeightKg': self.body_weight_kg,
        }

    def __repr__(self) -> str:
        return (
            f"HikeSession({self.id}, device={self.device_id!r}, "
            f"steps={self.steps}, kcal={self.calories_burnt})"
        )


def from_row(row: tuple) -> HikeSession:
    """Construct a HikeSession from a database row tuple.

    Expected column order (matches db.py SELECT):
        session_id, device_id, start_time, end_time,
        duration_seconds, steps, calories_burnt, body_weight_kg
    """
    (
        session_id, device_id, start_time_str, end_time_str,
        duration_seconds, steps, calories_burnt, body_weight_kg,
    ) = row
    return HikeSession(
        session_id=session_id,
        device_id=device_id,
        start_time=datetime.fromisoformat(start_time_str) if start_time_str else None,
        end_time=datetime.fromisoformat(end_time_str) if end_time_str else None,
        duration_seconds=duration_seconds,
        steps=steps,
        calories_burnt=calories_burnt,
        body_weight_kg=body_weight_kg,
    )


# ── Live session state ────────────────────────────────────────────────────────

class ActiveSessionState:
    """Thread-safe shared state for the currently active hiking session.

    Both the BLE receiver (asyncio) and the FastAPI web server read from and
    write to this object concurrently. A threading.Lock serialises all mutations.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.is_active: bool = False
        self.is_paused: bool = False
        self.device_id: str = ""
        self.start_time: Optional[datetime] = None
        self.step_count: int = 0
        self.calories_burnt: int = 0
        self.last_data_time: Optional[datetime] = None
        self.bt_connected: bool = False
        self._paused_at: Optional[datetime] = None
        self._total_paused_seconds: float = 0.0

    def start_session(self, device_id: str, start_time: datetime) -> None:
        """Begin a new session; resets all counters."""
        with self._lock:
            self.is_active = True
            self.is_paused = False
            self.device_id = device_id
            self.start_time = start_time
            self.step_count = 0
            self.calories_burnt = 0
            self.last_data_time = datetime.now(timezone.utc)
            self._paused_at = None
            self._total_paused_seconds = 0.0

    def ingest_raw_steps(self, raw_step_count: int, weight_kg: float) -> int:
        """Process raw watch step count and return the effective calorie total.

        The watch sends session-relative step counts, already adjusted for
        pause/resume. The backend therefore uses raw_step_count directly.
        While paused, incoming updates are ignored for session counters.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            self.last_data_time = now

            if self.is_paused:
                return self.calories_burnt

            effective_steps = max(0, raw_step_count)
            # Keep counters monotonic in case the watch sends out-of-order values.
            if effective_steps < self.step_count:
                effective_steps = self.step_count

            self.step_count = effective_steps
            self.calories_burnt = calc_kcal(effective_steps, weight_kg)
            return self.calories_burnt

    def pause(self) -> None:
        """Pause the active session."""
        with self._lock:
            if self.is_active and not self.is_paused:
                self.is_paused = True
                self._paused_at = datetime.now(timezone.utc)

    def resume(self) -> None:
        """Resume the paused session."""
        with self._lock:
            if self.is_active and self.is_paused:
                self.is_paused = False
                now = datetime.now(timezone.utc)
                if self._paused_at is not None:
                    self._total_paused_seconds += (now - self._paused_at).total_seconds()
                self._paused_at = None

    def _active_duration_seconds(self, now: datetime) -> float:
        """Return elapsed session time excluding paused intervals."""
        if self.start_time is None:
            return 0.0

        paused_now = 0.0
        if self.is_paused and self._paused_at is not None:
            paused_now = (now - self._paused_at).total_seconds()

        duration = (now - self.start_time).total_seconds() - self._total_paused_seconds - paused_now
        return max(0.0, duration)

    def finalize(self) -> Optional[HikeSession]:
        """Atomically end the active session and return it as a HikeSession.

        Returns None if no session was active.
        Clears all counters so the state is ready for the next session.
        """
        with self._lock:
            if not self.is_active:
                return None
            now = datetime.now(timezone.utc)
            duration = self._active_duration_seconds(now)
            session = HikeSession(
                device_id=self.device_id,
                start_time=self.start_time,
                end_time=now,
                duration_seconds=duration,
                steps=self.step_count,
                calories_burnt=self.calories_burnt,
            )
            self.is_active = False
            self.is_paused = False
            self.step_count = 0
            self.calories_burnt = 0
            self.last_data_time = None
            self._paused_at = None
            self._total_paused_seconds = 0.0
            return session

    def snapshot(self) -> dict:
        """Return a thread-safe JSON-serialisable snapshot for API responses.

        Provides all fields expected by the web UI (req9) plus the WebSocket
        `connected` boolean consumed by useWatchStatus.
        """
        with self._lock:
            if self.is_active and self.start_time:
                now = datetime.now(timezone.utc)
                total_s = int(self._active_duration_seconds(now))
                h, rem = divmod(total_s, 3600)
                m, s = divmod(rem, 60)
                session_time_iso = f"PT{h:02d}H{m:02d}M{s:02d}S"
                start_iso = self.start_time.isoformat()
            else:
                session_time_iso = None
                start_iso = None

            return {
                "isActive": self.is_active,
                "isPaused": self.is_paused,
                "sessionId": "active" if self.is_active else None,
                "startTime": start_iso,
                "endTime": None,
                "stepCount": self.step_count,
                "burnedCalories": self.calories_burnt,
                "distanceWalked": round(self.step_count * AVERAGE_STRIDE_M),
                # extra fields for WebSocket / requirements
                "connected": self.bt_connected,
                "hikeSessionTime": session_time_iso,
            }