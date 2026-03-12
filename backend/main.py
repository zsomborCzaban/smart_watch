from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app.ble import BLEWatchBridge
from app.config import get_settings
from app.models import HikingSession, WeightPayload, WeightResponse
from app.service import SessionService
from app.storage import SQLiteStorage
from app.websocket_manager import WebSocketManager


logging.basicConfig(level=logging.INFO)

settings = get_settings()
storage = SQLiteStorage(settings.database_path, settings.default_weight_kg)
ws_manager = WebSocketManager()
session_service = SessionService(storage, settings, ws_manager)
ble_bridge = BLEWatchBridge(
    settings=settings,
    on_payload=session_service.process_watch_payload,
    on_connection_change=session_service.set_watch_connected,
)
session_service.set_calories_sender(ble_bridge.send_calories)


async def _session_expiry_loop() -> None:
    while True:
        await session_service.expire_inactive_sessions()
        await asyncio.sleep(settings.idle_check_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    expiry_task = asyncio.create_task(_session_expiry_loop(), name="session-expiry-loop")
    await ble_bridge.start()
    try:
        yield
    finally:
        expiry_task.cancel()
        try:
            await expiry_task
        except asyncio.CancelledError:
            pass
        await ble_bridge.stop()
        storage.close()


app = FastAPI(title="Smart Watch Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ui_cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "bleAutoConnect": settings.ble_auto_connect,
        "tlsEnabled": bool(settings.tls_certfile and settings.tls_keyfile),
    }


@app.get("/api/activeSession", response_model=HikingSession)
async def get_active_session() -> HikingSession:
    session = session_service.get_active_session()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")
    return session


@app.get("/api/allSessions", response_model=list[HikingSession])
async def get_all_sessions() -> list[HikingSession]:
    return session_service.get_all_sessions()


@app.delete("/api/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str) -> None:
    deleted = await session_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@app.get("/api/weight", response_model=WeightResponse)
async def get_weight() -> WeightResponse:
    weight = session_service.get_weight()
    return WeightResponse(weight=weight, body_weight=weight)


@app.post("/api/setWeight", response_model=WeightResponse)
async def set_weight(payload: WeightPayload) -> WeightResponse:
    weight = await session_service.set_weight(payload.resolved_weight)
    return WeightResponse(weight=weight, body_weight=weight)


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    await websocket.send_json(session_service.build_snapshot())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        ssl_certfile=settings.tls_certfile,
        ssl_keyfile=settings.tls_keyfile,
        reload=False,
    )