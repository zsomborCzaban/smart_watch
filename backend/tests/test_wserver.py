from datetime import datetime, timezone

from fastapi.testclient import TestClient

import hike
import wserver


class FakeHubDB:
    def __init__(self) -> None:
        self.sessions: list[hike.HikeSession] = []
        self.weight = hike.DEFAULT_WEIGHT_KG

    def get_sessions(self) -> list[hike.HikeSession]:
        return list(self.sessions)

    def get_session(self, session_id: int):
        for session in self.sessions:
            if session.id == session_id:
                return session
        return None

    def delete_session(self, session_id: int) -> None:
        self.sessions = [s for s in self.sessions if s.id != session_id]

    def save_weight(self, weight: float) -> None:
        self.weight = weight

    def get_weight(self) -> float:
        return self.weight


class FakeState:
    def __init__(self, is_active: bool = False, snapshot_data: dict | None = None) -> None:
        self.is_active = is_active
        self._snapshot_data = snapshot_data or {
            "isActive": True,
            "sessionId": "active",
            "stepCount": 200,
            "burnedCalories": 20,
        }

    def snapshot(self) -> dict:
        return dict(self._snapshot_data)


def test_service_not_ready_returns_503(monkeypatch) -> None:
    monkeypatch.setattr(wserver, "_hubdb", None)
    monkeypatch.setattr(wserver, "_state", None)
    client = TestClient(wserver.app)

    response = client.get("/api/weight")

    assert response.status_code == 503


def test_get_all_sessions_includes_active_snapshot(monkeypatch) -> None:
    hubdb = FakeHubDB()
    session = hike.HikeSession(
        session_id=1,
        device_id="watch-01",
        start_time=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        steps=1000,
        calories_burnt=80,
    )
    hubdb.sessions = [session]
    state = FakeState(is_active=True)

    monkeypatch.setattr(wserver, "_hubdb", hubdb)
    monkeypatch.setattr(wserver, "_state", state)
    client = TestClient(wserver.app)

    response = client.get("/api/allSessions")
    body = response.json()

    assert response.status_code == 200
    assert len(body) == 2
    assert body[0]["sessionId"] == "1"
    assert body[1]["sessionId"] == "active"


def test_delete_session_not_found_returns_404(monkeypatch) -> None:
    hubdb = FakeHubDB()
    monkeypatch.setattr(wserver, "_hubdb", hubdb)

    client = TestClient(wserver.app)
    response = client.delete("/api/session/999")

    assert response.status_code == 404


def test_set_and_get_weight(monkeypatch) -> None:
    hubdb = FakeHubDB()
    monkeypatch.setattr(wserver, "_hubdb", hubdb)
    monkeypatch.setattr(wserver, "_state", FakeState())
    client = TestClient(wserver.app)

    set_response = client.post("/api/setWeight", json={"weight": 82.3})
    get_response = client.get("/api/weight")

    assert set_response.status_code == 204
    assert get_response.status_code == 200
    assert get_response.json() == {"weight": 82.3}
