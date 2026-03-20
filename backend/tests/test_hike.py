from datetime import datetime, timedelta, timezone

import hike


def test_calc_kcal_uses_expected_formula() -> None:
    # 7200 steps at 0.5s/step equals 1 hour of activity.
    assert hike.calc_kcal(7200, 70.0) == 420


def test_hike_session_to_dict_shape() -> None:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
    session = hike.HikeSession(
        session_id=10,
        device_id="watch-01",
        start_time=start,
        end_time=end,
        duration_seconds=1800,
        steps=200,
        calories_burnt=17,
        body_weight_kg=72.5,
    )

    payload = session.to_dict()

    assert payload["isActive"] is False
    assert payload["sessionId"] == "10"
    assert payload["startTime"] == start.isoformat()
    assert payload["endTime"] == end.isoformat()
    assert payload["stepCount"] == 200
    assert payload["burnedCalories"] == 17
    assert payload["distanceWalked"] == 150
    assert payload["bodyWeightKg"] == 72.5


def test_active_session_pause_resume_uses_watch_session_steps() -> None:
    state = hike.ActiveSessionState()
    state.start_session("watch-01", datetime.now(timezone.utc))

    state.ingest_raw_steps(100, 70.0)
    assert state.step_count == 100

    state.pause()
    paused_kcal = state.calories_burnt
    state.ingest_raw_steps(150, 70.0)
    assert state.step_count == 100
    assert state.calories_burnt == paused_kcal

    state.resume()
    # The watch already sends pause-adjusted session steps.
    state.ingest_raw_steps(175, 70.0)
    assert state.step_count == 175
    assert state.calories_burnt == hike.calc_kcal(175, 70.0)


def test_finalize_returns_session_and_resets_state() -> None:
    state = hike.ActiveSessionState()
    state.start_session("watch-02", datetime.now(timezone.utc) - timedelta(seconds=100))
    state.ingest_raw_steps(42, 70.0)
    state._total_paused_seconds = 30.0

    session = state.finalize()

    assert session is not None
    assert session.device_id == "watch-02"
    assert session.steps == 42
    assert session.calories_burnt == hike.calc_kcal(42, 70.0)
    assert 68.0 <= session.duration_seconds <= 72.0

    assert state.is_active is False
    assert state.is_paused is False
    assert state.step_count == 0
    assert state.calories_burnt == 0
    assert state.last_data_time is None
