from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return float(raw_value)


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value)


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database_path: Path
    inactivity_timeout_seconds: int
    idle_check_interval_seconds: int
    default_weight_kg: float
    step_length_meters: float
    calories_per_km_per_kg: float
    ui_cors_origins: list[str]
    tls_certfile: str | None
    tls_keyfile: str | None
    ble_device_address: str | None
    ble_device_name: str | None
    ble_step_characteristic_uuid: str | None
    ble_calorie_characteristic_uuid: str | None
    ble_pair: bool
    ble_auto_connect: bool


def get_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[1]
    cors_origins = os.getenv("UI_CORS_ORIGINS", "*")

    return Settings(
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=_env_int("BACKEND_PORT", 8000),
        database_path=Path(
            os.getenv(
                "BACKEND_DB_PATH",
                str(backend_dir / "data" / "smart_watch.db"),
            )
        ),
        inactivity_timeout_seconds=_env_int("SESSION_IDLE_TIMEOUT_SECONDS", 3600),
        idle_check_interval_seconds=_env_int("SESSION_IDLE_CHECK_SECONDS", 30),
        default_weight_kg=_env_float("DEFAULT_WEIGHT_KG", 75.0),
        step_length_meters=_env_float("STEP_LENGTH_METERS", 0.78),
        calories_per_km_per_kg=_env_float("CALORIES_PER_KM_PER_KG", 0.75),
        ui_cors_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
        tls_certfile=os.getenv("TLS_CERTFILE"),
        tls_keyfile=os.getenv("TLS_KEYFILE"),
        ble_device_address=os.getenv("BLE_DEVICE_ADDRESS"),
        ble_device_name=os.getenv("BLE_DEVICE_NAME"),
        ble_step_characteristic_uuid=os.getenv("BLE_STEP_CHARACTERISTIC_UUID"),
        ble_calorie_characteristic_uuid=os.getenv("BLE_CALORIE_CHARACTERISTIC_UUID"),
        ble_pair=_env_bool("BLE_PAIR", True),
        ble_auto_connect=_env_bool("BLE_AUTO_CONNECT", False),
    )