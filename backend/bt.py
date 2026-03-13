"""Bluetooth Low Energy interface between the Raspberry Pi hub and the smartwatch.

The hub operates as a BLE central (client). The smartwatch exposes a custom
GATT service with two characteristics:

* STEP_DATA_CHAR_UUID  – Notify  – watch → hub  (step-update JSON, req2)
* CALORIE_CHAR_UUID    – Write   – hub  → watch (calorie-response JSON, req3)

Incoming message format  (req2 + mandatory checksum field):
    {"device_id": "str", "timestamp": "ISO-8601", "step_count": int,
     "checksum": "CRC32-hex-8chars"}

A step_count of -1 signals an explicit session-end event from the watch button.
If no data is received for SESSION_TIMEOUT_SECONDS (3600 s), the session is
automatically ended (req5).

Outgoing message format (req3):
    {"calories_burned": int}

The CRC32 field guards against in-transit data corruption (req).
BLE 5.0 native pairing / bonding provides link-layer encryption (req1).
"""

import asyncio
import json
import logging
import traceback
import zlib
from datetime import datetime, timezone

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

import db
import hike

logger = logging.getLogger(__name__)

# ── BLE configuration ─────────────────────────────────────────────────────────────

# Replace with the actual BLE MAC address (Linux) or UUID (macOS) of the watch.
WATCH_BT_ADDRESS = "44:17:93:88:d0:8e"

# Custom GATT UUIDs – must match the watch firmware.
STEP_SERVICE_UUID   = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
STEP_DATA_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"  # Notify
CALORIE_CHAR_UUID   = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Write

SESSION_TIMEOUT_SECONDS = 3600  # req5: auto-end the session after 1 h of silence
RECONNECT_INTERVAL_SEC  = 2     # seconds to wait between reconnect attempts


# ── Checksum helpers ──────────────────────────────────────────────────────────────

def _compute_checksum(device_id: str, timestamp: str, step_count: int) -> str:
    """Return an 8-character hex CRC32 over the concatenated key fields."""
    data = f"{device_id}{timestamp}{step_count}".encode("utf-8")
    return format(zlib.crc32(data) & 0xFFFF_FFFF, "08x")


def _validate_payload(payload: dict) -> bool:
    """Return True when the payload's checksum field matches the recomputed value.

    Returns False (never raises) for any missing or incorrect checksum so that
    corrupted messages are silently discarded rather than crashing the receiver.
    """
    try:
        received = payload.get("checksum", "")
        expected = _compute_checksum(
            payload["device_id"], payload["timestamp"], payload["step_count"]
        )
        return received == expected
    except (KeyError, TypeError):
        return False


# ── Core BLE manager ─────────────────────────────────────────────────────────────

class HubBluetooth:
    """Manages the BLE link between the Raspberry Pi hub and the smartwatch.

    Runs two concurrent asyncio tasks:
    * A reconnection loop that discovers the watch, subscribes to step
      notifications, and handles data until the connection drops.
    * A timeout loop that auto-ends the session if no data is received for
      SESSION_TIMEOUT_SECONDS, regardless of BLE connection state (req5).

    Usage::

        hub = HubBluetooth()
        await hub.run(state, hubdb)   # loops forever; reconnects automatically
    """

    # ── public entry point ──────────────────────────────────────────────────────

    async def run(
        self,
        state: hike.ActiveSessionState,
        hubdb: db.HubDatabase,
    ) -> None:
        """Run the BLE connection loop and session-timeout checker concurrently."""
        await asyncio.gather(
            self._connection_loop(state, hubdb),
            self._session_timeout_loop(state, hubdb),
        )

    # ── connection loop ────────────────────────────────────────────────────────

    async def _connection_loop(
        self,
        state: hike.ActiveSessionState,
        hubdb: db.HubDatabase,
    ) -> None:
        while True:
            try:
                await self._connect_and_sync(state, hubdb)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "BLE error: %s – retrying in %d s.", exc, RECONNECT_INTERVAL_SEC
                )
                traceback.print_exc()
            state.bt_connected = False
            await asyncio.sleep(RECONNECT_INTERVAL_SEC)

    async def _connect_and_sync(
        self,
        state: hike.ActiveSessionState,
        hubdb: db.HubDatabase,
    ) -> None:
        logger.info("Scanning for watch (%s)…", WATCH_BT_ADDRESS)
        device = await BleakScanner.find_device_by_address(
            WATCH_BT_ADDRESS, timeout=10.0
        )
        if device is None:
            logger.warning("Watch not found – will retry.")
            return

        async with BleakClient(device, timeout=15.0) as client:
            state.bt_connected = True
            logger.info("Connected to watch via BLE 5.0.")

            # Async notification handler: bleak calls it for every incoming
            # GATT notification on STEP_DATA_CHAR_UUID.
            async def _on_step_data(sender, raw: bytearray) -> None:  # noqa: ANN001
                await self._handle_step_data(raw, client, state, hubdb)

            await client.start_notify(STEP_DATA_CHAR_UUID, _on_step_data)
            logger.info("Subscribed to step-data notifications.")

            # Keep the connection alive; bleak callbacks run on this loop.
            while client.is_connected:
                await asyncio.sleep(1)

        logger.info("Watch disconnected.")

    # ── per-step notification handler ───────────────────────────────────────────

    async def _handle_step_data(
        self,
        raw: bytearray,
        client: BleakClient,
        state: hike.ActiveSessionState,
        hubdb: db.HubDatabase,
    ) -> None:
        """Validate an incoming BLE notification, update state, and reply.

        Called at every step during an active session (req4).
        Sends a calorie response back to the watch within the same call (req6).
        """
        # — decode
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("BLE: cannot decode message – %s", exc)
            return

        # — checksum (req: checksums ensure step-count data is not corrupted)
        if not _validate_payload(payload):
            logger.warning("BLE: checksum mismatch – message discarded.")
            return

        step_count: int = payload["step_count"]

        # step_count == -1 → explicit session-end button press on the watch.
        if step_count < 0:
            logger.info("Session-end signal received from watch.")
            await self._finalize_session(state, hubdb)
            return

        # — start new session on first step after idle
        if not state.is_active:
            try:
                start_dt = datetime.fromisoformat(payload["timestamp"])
            except (ValueError, KeyError):
                start_dt = datetime.now(timezone.utc)
            state.start_session(payload["device_id"], start_dt)
            logger.info("Hiking session started for device '%s'.", payload["device_id"])

        # — calculate and store updated calories
        weight_kg = hubdb.get_weight()
        calories = hike.calc_kcal(step_count, weight_kg)
        state.update(step_count, calories)

        # — send calorie response to the watch (req3 / req6)
        response = json.dumps({"calories_burned": calories}).encode("utf-8")
        try:
            await client.write_gatt_char(CALORIE_CHAR_UUID, response, response=False)
        except BleakError as exc:
            logger.warning("BLE: failed to write calorie response – %s", exc)

    # ── 1-hour session timeout ─────────────────────────────────────────────────────

    async def _session_timeout_loop(
        self,
        state: hike.ActiveSessionState,
        hubdb: db.HubDatabase,
    ) -> None:
        """Check for the 1-hour inactivity timeout every 60 seconds (req5).

        Runs independently of the BLE connection so a session is always
        ended even when the watch is physically out of range.
        """
        while True:
            await asyncio.sleep(60)
            if state.is_active and state.last_data_time is not None:
                elapsed = (
                    datetime.now(timezone.utc) - state.last_data_time
                ).total_seconds()
                if elapsed >= SESSION_TIMEOUT_SECONDS:
                    logger.warning(
                        "Session auto-ended: no data for %.0f s (req5).", elapsed
                    )
                    await self._finalize_session(state, hubdb)

    # ── helper ──────────────────────────────────────────────────────────────────────

    async def _finalize_session(
        self,
        state: hike.ActiveSessionState,
        hubdb: db.HubDatabase,
    ) -> None:
        """Persist the active session to the database and clear the live state."""
        session = state.finalize()
        if session is None:
            return
        session.body_weight_kg = hubdb.get_weight()
        hubdb.save_session(session)
        logger.info("Session saved: %s", session)
