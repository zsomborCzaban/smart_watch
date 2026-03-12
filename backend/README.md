# Backend

Python backend for the smart hiking watch project. It provides:

- BLE integration for receiving step payloads from the watch and sending calorie updates back
- HTTPS-ready REST and WebSocket APIs for the web UI
- SQLite persistence for weight configuration and hiking sessions
- Automatic session timeout after 1 hour of inactivity

## Tech Stack

- FastAPI
- SQLite
- Bleak for BLE communication
- Uvicorn ASGI server

## Implemented API

- `GET /api/activeSession`
- `GET /api/allSessions`
- `DELETE /api/session/{id}`
- `GET /api/weight`
- `POST /api/setWeight`
- `GET /api/health`
- `WS /api/ws`

The `POST /api/setWeight` endpoint accepts either of these JSON bodies:

```json
{ "weight": 75.0 }
```

```json
{ "body_weight": 75.0 }
```

## Watch Payload Contract

Incoming payloads from the watch are expected as UTF-8 JSON over the configured BLE characteristic:

```json
{
  "device_id": "watch-01",
  "timestamp": "2026-03-12T12:00:00Z",
  "step_count": 1234
}
```

Outgoing payloads to the watch are sent as UTF-8 JSON over the configured BLE characteristic:

```json
{
  "calories_burned": 42
}
```

## Environment Variables

- `BACKEND_HOST` default `0.0.0.0`
- `BACKEND_PORT` default `8000`
- `BACKEND_DB_PATH` optional path to SQLite database
- `DEFAULT_WEIGHT_KG` default `75.0`
- `STEP_LENGTH_METERS` default `0.78`
- `CALORIES_PER_KM_PER_KG` default `0.75`
- `SESSION_IDLE_TIMEOUT_SECONDS` default `3600`
- `SESSION_IDLE_CHECK_SECONDS` default `30`
- `UI_CORS_ORIGINS` comma-separated list, default `*`
- `TLS_CERTFILE` path to HTTPS certificate
- `TLS_KEYFILE` path to HTTPS private key
- `BLE_AUTO_CONNECT` set to `true` to enable BLE bridge on startup
- `BLE_PAIR` default `true`
- `BLE_DEVICE_ADDRESS` BLE MAC/address of the watch
- `BLE_DEVICE_NAME` alternative discovery name if address is not fixed
- `BLE_STEP_CHARACTERISTIC_UUID` characteristic UUID receiving step JSON
- `BLE_CALORIE_CHARACTERISTIC_UUID` characteristic UUID sending calorie JSON

Set either `BLE_DEVICE_ADDRESS` or `BLE_DEVICE_NAME`.

## Local Setup

```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```

On Raspberry Pi or Linux, activate the virtual environment before installing:

```bash
source .venv/bin/activate
```

On a standard Windows Python installation:

```bash
.venv\Scripts\activate
```

## HTTPS on Raspberry Pi

For secure UI connections, start the backend with a certificate and key:

```bash
set TLS_CERTFILE=C:\path\to\cert.pem
set TLS_KEYFILE=C:\path\to\key.pem
python main.py
```

For Linux or Raspberry Pi shell:

```bash
export TLS_CERTFILE=/home/pi/certs/cert.pem
export TLS_KEYFILE=/home/pi/certs/key.pem
python main.py
```

## BLE Notes

Secure BLE pairing depends on the Raspberry Pi Bluetooth stack and the watch firmware. The backend requests pairing through Bleak when `BLE_PAIR=true`, but the OS and device still need to support authenticated bonding.

The default requirements file installs `bleak` only on Linux because this project is intended to run on Raspberry Pi. The backend still starts on non-Linux development machines without BLE enabled.

On Raspberry Pi OS you will typically need:

- Bluetooth enabled and working through BlueZ
- The watch advertising the configured GATT characteristics
- Sufficient permissions to access BLE devices

## Session Behaviour

- A session starts when the first valid step payload arrives.
- If an active session receives a smaller `step_count` than before, the previous session is closed and a new one starts.
- If no step payload is received for 1 hour, the backend closes the session automatically.
- The UI WebSocket pushes snapshots immediately after state changes.
