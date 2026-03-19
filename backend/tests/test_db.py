from datetime import datetime, timezone

import db
import hike
import pytest


@pytest.fixture
def hubdb(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_FILE_NAME", tmp_path / "sessions_test.db")
    database = db.HubDatabase()
    yield database
    database._con.close()


def test_get_weight_returns_default_when_missing(hubdb) -> None:
    assert hubdb.get_weight() == hike.DEFAULT_WEIGHT_KG


def test_save_weight_round_trip(hubdb) -> None:
    hubdb.save_weight(81.5)
    assert hubdb.get_weight() == 81.5


def test_save_get_delete_session(hubdb) -> None:
    start = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
    session = hike.HikeSession(
        device_id="watch-01",
        start_time=start,
        end_time=end,
        duration_seconds=1800,
        steps=1234,
        calories_burnt=95,
        body_weight_kg=79.2,
    )

    session_id = hubdb.save_session(session)
    fetched = hubdb.get_session(session_id)

    assert fetched is not None
    assert fetched.id == session_id
    assert fetched.device_id == "watch-01"
    assert fetched.start_time == start
    assert fetched.end_time == end
    assert fetched.duration_seconds == 1800
    assert fetched.steps == 1234
    assert fetched.calories_burnt == 95
    assert fetched.body_weight_kg == 79.2

    all_sessions = hubdb.get_sessions()
    assert len(all_sessions) == 1
    assert all_sessions[0].id == session_id

    hubdb.delete_session(session_id)
    assert hubdb.get_session(session_id) is None
