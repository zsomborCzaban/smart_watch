"""HTTPS / WebSocket web server (req7, req9, req11).

Endpoints consumed by the web UI
---------------------------------
    GET    /api/activeSession        – live session snapshot (404 when idle)
    GET    /api/allSessions          – all sessions, active one included
    DELETE /api/session/{session_id} – delete a completed session
    POST   /api/setWeight            – store the user’s body weight (req8/req10)
    GET    /api/weight               – retrieve the stored body weight
    WS     /api/ws                   – real-time push every second (req11)

HTTPS (req7)
-----------
Enabled when cert.pem and key.pem are present in the working directory.
Generate a self-signed certificate for development:

    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \\
        -days 365 -nodes -subj "/CN=smartwatch-hub"

For production use a certificate issued by a trusted CA.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
import hike

logger = logging.getLogger(__name__)

SSL_CERTFILE = "cert.pem"
SSL_KEYFILE  = "key.pem"
SERVER_HOST  = "0.0.0.0"
# Port 8443 does not require root. Use 443 in production with proper
# Linux capabilities (CAP_NET_BIND_SERVICE) or a reverse-proxy.
SERVER_PORT  = 8443

app = FastAPI(title="Smart Watch Hiking Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict to specific origins in production
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# Injected once at startup by receiver.py – never mutated afterwards.
_hubdb: "db.HubDatabase | None" = None
_state: "hike.ActiveSessionState | None" = None
_ws_clients: list[WebSocket] = []


class WeightRequest(BaseModel):
    weight: float = Field(..., gt=0, lt=500, description="Body weight in kilograms")


# ── startup injection ──────────────────────────────────────────────────────────

def configure(hubdb: "db.HubDatabase", state: "hike.ActiveSessionState") -> None:
    """Inject shared dependencies before the server starts serving requests."""
    global _hubdb, _state
    _hubdb = hubdb
    _state = state


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/allSessions")
async def get_all_sessions() -> list[dict[str, Any]]:
    """Return all completed sessions plus the active session (if any).

    The frontend derives activeSession = sessions.find(s => s.isActive).
    """
    if _hubdb is None or _state is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    sessions: list[dict[str, Any]] = [s.to_dict() for s in _hubdb.get_sessions()]
    if _state.is_active:
        sessions.append(_state.snapshot())
    return sessions


@app.delete("/api/session/{session_id}", status_code=204)
async def delete_session(session_id: int) -> None:
    """Delete a completed session by its integer ID."""
    if _hubdb is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    if _hubdb.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _hubdb.delete_session(session_id)


@app.post("/api/setWeight", status_code=204)
async def set_weight(body: WeightRequest) -> None:
    """Persist the user’s body weight (req8 / req10)."""
    if _hubdb is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    _hubdb.save_weight(body.weight)


@app.get("/api/weight")
async def get_weight() -> dict[str, float]:
    """Return the currently stored body weight."""
    if _hubdb is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"weight": _hubdb.get_weight()}


# ── WebSocket (req11) ──────────────────────────────────────────────────────────

@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            # Drain any client messages to keep the connection alive;
            # the hub only pushes, it does not consume client data here.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


async def _broadcast(data: dict) -> None:
    """Fan-out a JSON payload to every connected WebSocket client."""
    if not _ws_clients:
        return
    payload = json.dumps(data)
    dead: list[WebSocket] = []
    for ws in list(_ws_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


async def broadcast_state() -> None:
    """Push the live session state to all WebSocket clients every second.

    Runs as a background task so the UI always reflects the latest data (req11).
    The `connected` field in the payload is consumed by useWatchStatus().
    """
    while True:
        try:
            await asyncio.sleep(1)
            if _state is not None:
                await _broadcast({"type": "session_update", **_state.snapshot()})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("broadcast_state error: %s", exc)


# ── server factory ──────────────────────────────────────────────────────────────

def get_uvicorn_config() -> uvicorn.Config:
    """Build a uvicorn.Config with TLS enabled when cert/key files are present."""
    cert = Path(SSL_CERTFILE)
    key  = Path(SSL_KEYFILE)
    use_ssl = cert.exists() and key.exists()

    if not use_ssl:
        logger.warning(
            "TLS certificate not found (%s / %s). Running plain HTTP. "
            "Generate with: openssl req -x509 -newkey rsa:4096 "
            "-keyout key.pem -out cert.pem -days 365 -nodes",
            SSL_CERTFILE,
            SSL_KEYFILE,
        )

    kwargs: dict[str, Any] = dict(
        app=app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
    )
    if use_ssl:
        kwargs["ssl_certfile"] = SSL_CERTFILE
        kwargs["ssl_keyfile"]  = SSL_KEYFILE

    return uvicorn.Config(**kwargs)