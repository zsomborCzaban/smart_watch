from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class WatchPayload(BaseModel):
    device_id: str = Field(min_length=1)
    timestamp: datetime
    step_count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def normalize_timestamp(self) -> "WatchPayload":
        self.timestamp = ensure_utc(self.timestamp)
        return self


class WeightPayload(BaseModel):
    weight: float | None = Field(default=None, gt=0)
    body_weight: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_weight(self) -> "WeightPayload":
        if self.weight is None and self.body_weight is None:
            raise ValueError("Either 'weight' or 'body_weight' must be provided.")
        return self

    @property
    def resolved_weight(self) -> float:
        return self.body_weight if self.body_weight is not None else float(self.weight)


class WeightResponse(BaseModel):
    weight: float
    body_weight: float


class HikingSession(BaseModel):
    isActive: bool
    sessionId: str
    startTime: str
    endTime: str
    stepCount: int
    burnedCalories: float
    distanceWalked: float


class UIStatusPayload(BaseModel):
    step_count: int
    calories_burnt: int
    hike_session_time: str | None
    hike_start_time: str | None
    is_hike_active: bool


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    device_id: str
    is_active: bool
    start_time: datetime
    end_time: datetime | None
    last_update_time: datetime
    step_count: int
    burned_calories: float
    distance_walked: float
    last_reported_calories: int

    def to_api_model(self) -> HikingSession:
        return HikingSession(
            isActive=self.is_active,
            sessionId=self.session_id,
            startTime=self.start_time.isoformat(),
            endTime=(self.end_time or self.last_update_time).isoformat(),
            stepCount=self.step_count,
            burnedCalories=round(self.burned_calories, 2),
            distanceWalked=round(self.distance_walked, 2),
        )

    def to_ui_status(self) -> UIStatusPayload:
        reference_time = self.last_update_time if self.is_active else self.end_time
        return UIStatusPayload(
            step_count=self.step_count,
            calories_burnt=int(self.burned_calories),
            hike_session_time=reference_time.isoformat() if reference_time else None,
            hike_start_time=self.start_time.isoformat(),
            is_hike_active=self.is_active,
        )