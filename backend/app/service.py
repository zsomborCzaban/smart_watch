from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from math import floor
from typing import Awaitable, Callable
from uuid import uuid4

from .config import Settings
from .models import HikingSession, SessionRecord, UIStatusPayload, WatchPayload
from .storage import SQLiteStorage
from .websocket_manager import WebSocketManager


CaloriesSender = Callable[[int], Awaitable[None]]


class SessionService:
    def __init__(
        self,
        storage: SQLiteStorage,
        settings: Settings,
        ws_manager: WebSocketManager,
    ) -> None:
        self._storage = storage
        self._settings = settings
        self._ws_manager = ws_manager
        self._lock = asyncio.Lock()
        self._watch_connected = False
        self._calories_sender: CaloriesSender | None = None

    def set_calories_sender(self, sender: CaloriesSender) -> None:
        self._calories_sender = sender

    async def set_watch_connected(self, connected: bool) -> None:
        self._watch_connected = connected
        await self._broadcast_state()

    def get_weight(self) -> float:
        return self._storage.get_weight()

    async def set_weight(self, weight: float) -> float:
        self._storage.set_weight(weight)
        await self._broadcast_state()
        return weight

    def get_all_sessions(self) -> list[HikingSession]:
        return [session.to_api_model() for session in self._storage.list_sessions()]

    def get_active_session(self) -> HikingSession | None:
        session = self._storage.get_active_session()
        return session.to_api_model() if session else None

    async def delete_session(self, session_id: str) -> bool:
        deleted = self._storage.delete_session(session_id)
        if deleted:
            await self._broadcast_state()
        return deleted

    async def process_watch_payload(self, payload: WatchPayload) -> HikingSession:
        calories_to_send: list[int] = []

        async with self._lock:
            session = self._storage.get_active_session(payload.device_id)
            if session and payload.step_count < session.step_count:
                session.is_active = False
                session.end_time = payload.timestamp
                session.last_update_time = payload.timestamp
                self._storage.save_session(session)
                session = None

            if session is None:
                session = SessionRecord(
                    session_id=str(uuid4()),
                    device_id=payload.device_id,
                    is_active=True,
                    start_time=payload.timestamp,
                    end_time=None,
                    last_update_time=payload.timestamp,
                    step_count=0,
                    burned_calories=0.0,
                    distance_walked=0.0,
                    last_reported_calories=0,
                )

            session.step_count = payload.step_count
            session.last_update_time = payload.timestamp
            session.distance_walked = self._calculate_distance(payload.step_count)
            session.burned_calories = self._calculate_calories(session.distance_walked)

            current_reportable_calories = floor(session.burned_calories)
            if current_reportable_calories > session.last_reported_calories:
                calories_to_send = list(
                    range(session.last_reported_calories + 1, current_reportable_calories + 1)
                )
                session.last_reported_calories = current_reportable_calories

            self._storage.save_session(session)

        for calories in calories_to_send:
            if self._calories_sender is not None:
                await self._calories_sender(calories)

        await self._broadcast_state()
        return session.to_api_model()

    async def expire_inactive_sessions(self) -> None:
        now = datetime.now(timezone.utc)
        timeout = timedelta(seconds=self._settings.inactivity_timeout_seconds)
        expired_any = False

        async with self._lock:
            for session in self._storage.list_active_sessions():
                if session.last_update_time + timeout > now:
                    continue

                session.is_active = False
                session.end_time = session.last_update_time + timeout
                self._storage.save_session(session)
                expired_any = True

        if expired_any:
            await self._broadcast_state()

    def build_snapshot(self) -> dict:
        active_session = self._storage.get_active_session()
        sessions = [session.to_api_model().model_dump() for session in self._storage.list_sessions()]
        ui_state = self._build_ui_state(active_session).model_dump()
        return {
            "type": "snapshot",
            "connected": self._watch_connected,
            "activeSession": active_session.to_api_model().model_dump() if active_session else None,
            "sessions": sessions,
            "uiState": ui_state,
        }

    async def _broadcast_state(self) -> None:
        await self._ws_manager.broadcast_json(self.build_snapshot())

    def _build_ui_state(self, active_session: SessionRecord | None) -> UIStatusPayload:
        if active_session is None:
            return UIStatusPayload(
                step_count=0,
                calories_burnt=0,
                hike_session_time=None,
                hike_start_time=None,
                is_hike_active=False,
            )
        return active_session.to_ui_status()

    def _calculate_distance(self, step_count: int) -> float:
        return step_count * self._settings.step_length_meters

    def _calculate_calories(self, distance_walked_meters: float) -> float:
        distance_km = distance_walked_meters / 1000
        return distance_km * self._storage.get_weight() * self._settings.calories_per_km_per_kg