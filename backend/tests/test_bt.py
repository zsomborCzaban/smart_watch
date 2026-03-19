import asyncio

import pytest

pytest.importorskip("bleak")

import bt
import hike


class DummyState:
    def __init__(self, session):
        self._session = session

    def finalize(self):
        return self._session


class DummyHubDB:
    def __init__(self, weight: float = 70.0):
        self.weight = weight
        self.saved_session = None

    def get_weight(self) -> float:
        return self.weight

    def save_session(self, session) -> None:
        self.saved_session = session


def test_compute_checksum_and_validate_payload() -> None:
    payload = {
        "device_id": "watch-01",
        "timestamp": "2026-03-19T08:00:00+00:00",
        "step_count": 321,
    }
    payload["checksum"] = bt._compute_checksum(
        payload["device_id"], payload["timestamp"], payload["step_count"]
    )

    assert bt._validate_payload(payload) is True


def test_validate_payload_rejects_corrupted_data() -> None:
    payload = {
        "device_id": "watch-01",
        "timestamp": "2026-03-19T08:00:00+00:00",
        "step_count": 321,
        "checksum": "deadbeef",
    }

    assert bt._validate_payload(payload) is False


def test_finalize_session_saves_weighted_session() -> None:
    hub = bt.HubBluetooth()
    session = hike.HikeSession(device_id="watch-01", steps=123)
    state = DummyState(session)
    hubdb = DummyHubDB(weight=84.7)

    asyncio.run(hub._finalize_session(state, hubdb))

    assert hubdb.saved_session is session
    assert session.body_weight_kg == 84.7


def test_finalize_session_noop_when_no_active_session() -> None:
    hub = bt.HubBluetooth()
    state = DummyState(None)
    hubdb = DummyHubDB()

    asyncio.run(hub._finalize_session(state, hubdb))

    assert hubdb.saved_session is None
