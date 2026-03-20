"""Main entry point for the backend.

Runs the BLE receiver and the HTTPS web server concurrently in the same
asyncio event loop so real-time step data flows directly to both the
database and the web UI without inter-process communication.
"""

import asyncio
import logging

import uvicorn

import bt
import db
import hike
import wserver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    hubdb  = db.HubDatabase()
    state  = hike.ActiveSessionState()
    wserver.configure(hubdb, state)

    ble_hub = bt.HubBluetooth()
    server  = uvicorn.Server(wserver.get_uvicorn_config())

    logger.info("Smart Watch backend starting…")
    await asyncio.gather(
        ble_hub.run(state, hubdb),
        server.serve(),
        wserver.broadcast_state(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt – shutting down.")