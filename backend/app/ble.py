from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from .config import Settings
from .models import WatchPayload

try:
    from bleak import BleakClient, BleakScanner
except ImportError:  # pragma: no cover - depends on environment.
    BleakClient = None
    BleakScanner = None


logger = logging.getLogger(__name__)

PayloadHandler = Callable[[WatchPayload], Awaitable[None]]
ConnectionHandler = Callable[[bool], Awaitable[None]]


class BLEWatchBridge:
    def __init__(
        self,
        settings: Settings,
        on_payload: PayloadHandler,
        on_connection_change: ConnectionHandler,
    ) -> None:
        self._settings = settings
        self._on_payload = on_payload
        self._on_connection_change = on_connection_change
        self._write_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._runner_task: asyncio.Task[None] | None = None
        self._client: Any = None

    async def start(self) -> None:
        if not self._settings.ble_auto_connect:
            await self._on_connection_change(False)
            return

        if BleakClient is None or BleakScanner is None:
            logger.warning("Bleak is not available; BLE bridge is disabled.")
            await self._on_connection_change(False)
            return

        if not self._settings.ble_step_characteristic_uuid:
            logger.warning("BLE step characteristic UUID missing; BLE bridge is disabled.")
            await self._on_connection_change(False)
            return

        self._runner_task = asyncio.create_task(self._run(), name="ble-watch-bridge")

    async def stop(self) -> None:
        self._stop_event.set()

        if self._runner_task is not None:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass

        if self._client is not None:
            try:
                if self._client.is_connected:
                    await self._client.disconnect()
            except Exception:
                logger.exception("Failed to disconnect BLE client cleanly.")

    async def send_calories(self, calories_burned: int) -> None:
        if (
            self._client is None
            or not self._client.is_connected
            or not self._settings.ble_calorie_characteristic_uuid
        ):
            return

        payload = json.dumps({"calories_burned": calories_burned}).encode("utf-8")
        async with self._write_lock:
            await self._client.write_gatt_char(
                self._settings.ble_calorie_characteristic_uuid,
                payload,
                response=True,
            )

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                device = await self._find_device()
                if device is None:
                    await self._on_connection_change(False)
                    await asyncio.sleep(5)
                    continue

                async with BleakClient(
                    device,
                    pair=self._settings.ble_pair,
                    disconnected_callback=self._handle_disconnect,
                ) as client:
                    self._client = client
                    await self._on_connection_change(True)
                    await client.start_notify(
                        self._settings.ble_step_characteristic_uuid,
                        self._notification_callback,
                    )

                    while client.is_connected and not self._stop_event.is_set():
                        await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("BLE bridge loop failed.")
            finally:
                self._client = None
                await self._on_connection_change(False)

            if not self._stop_event.is_set():
                await asyncio.sleep(5)

    async def _find_device(self) -> Any:
        if self._settings.ble_device_address:
            return await BleakScanner.find_device_by_address(
                self._settings.ble_device_address,
                timeout=10.0,
            )

        if self._settings.ble_device_name:
            return await BleakScanner.find_device_by_filter(
                lambda device, advertisement_data: device.name == self._settings.ble_device_name
                or advertisement_data.local_name == self._settings.ble_device_name,
                timeout=10.0,
            )

        logger.warning("BLE device address or name not configured.")
        return None

    def _handle_disconnect(self, _client: Any) -> None:
        asyncio.create_task(self._on_connection_change(False))

    def _notification_callback(self, _sender: Any, data: bytearray) -> None:
        asyncio.create_task(self._handle_notification(bytes(data)))

    async def _handle_notification(self, data: bytes) -> None:
        try:
            payload = WatchPayload.model_validate_json(data.decode("utf-8"))
        except Exception:
            logger.warning("Received malformed BLE payload: %r", data)
            return

        await self._on_payload(payload)