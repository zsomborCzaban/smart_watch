import asyncio
import json
from datetime import datetime, timedelta, timezone

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


class DummyStepState:
    def __init__(self) -> None:
        self.is_active = False
        self.is_paused = False
        self.device_id = ""
        self.paused = False
        self.resumed = False
        self.started_with = None
        self.ingested = []
        self.last_data_time = datetime.now(timezone.utc)
        self.bt_connected = True

    def start_session(self, device_id, start_time) -> None:
        self.is_active = True
        self.device_id = device_id
        self.started_with = (device_id, start_time)

    def ingest_raw_steps(self, step_count, weight_kg) -> int:
        self.ingested.append((step_count, weight_kg))
        return 123

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.resumed = True


class DummyClient:
    def __init__(self, fail_write: bool = False) -> None:
        self.fail_write = fail_write
        self.writes = []

    async def write_gatt_char(self, char_uuid, payload, response=False):
        if self.fail_write:
            raise bt.BleakError("write failed")
        self.writes.append((char_uuid, payload, response))


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


def _payload_bytes(step_count: int, timestamp: str = "2026-03-19T08:00:00+00:00") -> bytes:
    payload = {
        "device_id": "watch-01",
        "timestamp": timestamp,
        "step_count": step_count,
    }
    payload["checksum"] = bt._compute_checksum(
        payload["device_id"], payload["timestamp"], payload["step_count"]
    )
    return json.dumps(payload).encode("utf-8")


def test_handle_step_data_ignores_bad_json() -> None:
    hub = bt.HubBluetooth()
    client = DummyClient()
    state = DummyStepState()
    hubdb = DummyHubDB()

    asyncio.run(hub._handle_step_data(b"not-json", client, state, hubdb))

    assert state.ingested == []
    assert client.writes == []


def test_handle_step_data_ignores_bad_checksum() -> None:
    hub = bt.HubBluetooth()
    client = DummyClient()
    state = DummyStepState()
    hubdb = DummyHubDB()
    payload = {
        "device_id": "watch-01",
        "timestamp": "2026-03-19T08:00:00+00:00",
        "step_count": 10,
        "checksum": "bad",
    }

    asyncio.run(
        hub._handle_step_data(
            json.dumps(payload).encode("utf-8"),
            client,
            state,
            hubdb,
        )
    )

    assert state.ingested == []
    assert client.writes == []


def test_handle_step_data_pause_resume_and_finalize_signals(monkeypatch) -> None:
    hub = bt.HubBluetooth()
    client = DummyClient()
    state = DummyStepState()
    hubdb = DummyHubDB()
    finalized = {"called": 0}

    async def fake_finalize(s, d):
        finalized["called"] += 1

    monkeypatch.setattr(hub, "_finalize_session", fake_finalize)

    asyncio.run(hub._handle_step_data(_payload_bytes(-2), client, state, hubdb))
    asyncio.run(hub._handle_step_data(_payload_bytes(-3), client, state, hubdb))
    asyncio.run(hub._handle_step_data(_payload_bytes(-1), client, state, hubdb))

    assert state.paused is True
    assert state.resumed is True
    assert finalized["called"] == 1


def test_handle_step_data_starts_session_writes_calories() -> None:
    hub = bt.HubBluetooth()
    client = DummyClient()
    state = DummyStepState()
    hubdb = DummyHubDB(weight=79.0)

    asyncio.run(hub._handle_step_data(_payload_bytes(42), client, state, hubdb))

    assert state.started_with is not None
    assert state.started_with[0] == "watch-01"
    assert state.ingested == [(42, 79.0)]
    assert len(client.writes) == 1
    char_uuid, payload, response = client.writes[0]
    assert char_uuid == bt.CALORIE_CHAR_UUID
    assert response is False
    assert json.loads(payload.decode("utf-8")) == {"calories_burned": 123}


def test_handle_step_data_write_error_is_handled() -> None:
    hub = bt.HubBluetooth()
    client = DummyClient(fail_write=True)
    state = DummyStepState()
    hubdb = DummyHubDB(weight=79.0)

    asyncio.run(hub._handle_step_data(_payload_bytes(42), client, state, hubdb))

    assert state.ingested == [(42, 79.0)]


def test_sync_time_with_watch_writes_timestamp() -> None:
    hub = bt.HubBluetooth()
    client = DummyClient()

    asyncio.run(hub._sync_time_with_watch(client))

    assert len(client.writes) == 1
    assert client.writes[0][0] == bt.SYNC_TIME_CHAR_UUID


def test_sync_time_with_watch_handles_errors() -> None:
    hub = bt.HubBluetooth()
    client = DummyClient(fail_write=True)

    asyncio.run(hub._sync_time_with_watch(client))

    assert client.writes == []


def test_session_timeout_loop_finalizes_expired_session(monkeypatch) -> None:
    hub = bt.HubBluetooth()
    state = DummyStepState()
    state.is_active = True
    state.last_data_time = datetime.now(timezone.utc) - timedelta(seconds=3700)
    hubdb = DummyHubDB()
    finalized = {"called": 0}

    async def fake_finalize(s, d):
        finalized["called"] += 1
        raise asyncio.CancelledError()

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(hub, "_finalize_session", fake_finalize)
    monkeypatch.setattr(bt.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(hub._session_timeout_loop(state, hubdb))

    assert finalized["called"] == 1


def test_connection_loop_marks_disconnected_after_failure(monkeypatch) -> None:
    hub = bt.HubBluetooth()
    state = DummyStepState()
    state.bt_connected = True
    hubdb = DummyHubDB()

    async def fake_connect_and_sync(_state, _hubdb):
        raise RuntimeError("boom")

    async def fake_sleep(_seconds):
        raise asyncio.CancelledError()

    monkeypatch.setattr(hub, "_connect_and_sync", fake_connect_and_sync)
    monkeypatch.setattr(bt.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(hub._connection_loop(state, hubdb))

    assert state.bt_connected is False
