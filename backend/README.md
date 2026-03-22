# Backend Hub: Hiking Tracker Server

A Raspberry Pi-based BLE hub and REST API server that bridges smartwatch data with a web frontend. Receives step data via Bluetooth Low Energy, processes hike sessions, calculates calories burned, and serves real-time updates via WebSocket.

## Overview

The Backend Hub runs as the central coordinator between the T-Watch hiking tracker and the web UI. It continuously listens for incoming step data via BLE from the smartwatch, manages hiking sessions in SQLite, calculates calories burned based on user weight and activity, and exposes REST endpoints and WebSocket connections for the frontend to consume live and historical session data.

## ✨ Features

### BLE Communication

- **Central BLE Device** - Acts as a Bluetooth Low Energy central (client) connecting to the smartwatch
- **Real-time Step Reception** - Receives step count updates with CRC32 checksum validation
- **Automatic Session Tracking** - Starts sessions on first data reception, ends on button press or timeout (1 hour)
- **Calorie Feedback Loop** - Sends calculated calories back to the watch in real-time
- **Data Integrity** - Validates incoming data with CRC32 checksums

### Session Management

- **Automatic Session Creation** - Begins on first BLE connection with valid data
- **Duration Tracking** - Records start/end times and session length
- **Step Aggregation** - Accumulates step counts throughout the hike
- **Calorie Calculation** - Uses MET formula adjusted for user body weight
- **Session Persistence** - Stores completed sessions in SQLite database
- **Session Termination** - Ends on explicit watch button press (step_count = -1) or timeout

### REST API

- **GET /api/activeSession** - Current session snapshot (404 when idle)
- **GET /api/allSessions** - All sessions including the active one
- **DELETE /api/session/{session_id}** - Remove a completed session
- **POST /api/setWeight** - Store user body weight (kg)
- **GET /api/weight** - Retrieve stored body weight
- **WS /api/ws** - WebSocket for real-time session updates (1 second push)

### Database Persistence

- **Sessions Table** - Stores all hiking sessions with comprehensive statistics
- **Weight Table** - Persists user body weight for calorie calculations
- **SQLite 3** - Lightweight, file-based database (no external DB required)

## 🏗️ Architecture

### Module Architecture

```
receiver.py (Entry Point)
├── BLE Hub (bt.py)
│   └── BLE Server Client - Receives step data
├── Database (db.py)
│   └── SQLite - Session & weight persistence
├── Session State (hike.py)
│   └── Calorie calculations & session logic
└── Web Server (wserver.py)
    └── FastAPI + WebSocket - REST & real-time endpoints
```

### Data Flow

```
T-Watch (BLE Server)
        ↓ (step data with CRC32)
BLE Hub (bt.py)
        ↓ (validates & processes)
Session State (hike.py)
        ↓ (calculates calories)
Database (db.py) ← Persistence
        ↓
Web Server (wserver.py) ← API responses & WebSocket broadcasts
        ↓
Frontend UI (React/WebSocket)
```

### Async Concurrency

The backend runs BLE receiver and web server concurrently in a single asyncio event loop:

- **BLE Receiver** - Continuous listening task for incoming step data
- **Web Server** - FastAPI application serving REST and WebSocket clients
- **Session Monitor** - Background task that auto-ends expired sessions

## 🛠️ Tech Stack

- **Language**: Python 3.9+
- **BLE Library**: Bleak (BlueZ compatible, Raspberry Pi native)
- **Web Framework**: FastAPI
- **Server**: Uvicorn with SSL/TLS support
- **Real-time**: WebSockets
- **Database**: SQLite 3
- **Validation**: Pydantic
- **Testing**: pytest

## 📡 BLE Protocol Details

### GATT Service Structure

- **Service UUID**: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`
- **Notify Characteristic**: `beb5483e-36e1-4688-b7f5-ea07361b26a8` (watch → hub, step data)
- **Write Characteristic**: `6e400003-b5a3-f393-e0a9-e50e24dcca9e` (hub → watch, calories)

### Incoming Data Format

```json
{
  "device_id": "twatch_hiker_1",
  "timestamp": "2024-03-22T14:30:45+00:00",
  "step_count": 1234,
  "checksum": "a1b2c3d4"
}
```

- **step_count = -1**: Explicit session-end signal from watch button
- **CRC32 Checksum**: 8-character hex string for data integrity validation

### Outgoing Data Format

```json
{
  "calories_burned": 425
}
```

### Calorie Calculation Formula

```
kcal = MET × weight_kg × (steps × time_per_step_hours)
```

- **MET** (Metabolic Equivalent): 6.0 for hiking
- **Stride**: 0.75 meters average
- **Pace**: 0.5 seconds per step (assumed)

## 📦 Installation & Setup

### Prerequisites

- Python 3.9+
- Raspberry Pi OS (or Linux with BlueZ)
- pip 21+

### Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### SSL/TLS Setup (Optional)

For HTTPS support, generate self-signed certificates:

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
```

Place `cert.pem` and `key.pem` in the backend directory.

### Running the Server

```bash
# Basic run
python receiver.py

# With custom logging
PYTHONUNBUFFERED=1 python receiver.py
```

The server will:

1. Initialize the SQLite database (if needed)
2. Start the BLE hub listening for the smartwatch
3. Launch the FastAPI server on `https://localhost:8000` (or HTTP if no certs)
4. Expose WebSocket at `wss://localhost:8000/api/ws`

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest

# Specific module
pytest tests/test_bt.py
pytest tests/test_db.py
pytest tests/test_hike.py

# Verbose output
pytest -v

# With coverage
pytest --cov=. tests/
```

Test files:

- **test_bt.py** - BLE receiver and message validation
- **test_db.py** - Database operations and persistence
- **test_hike.py** - Session state and calorie calculations
- **test_receiver.py** - Main loop concurrency
- **test_wserver.py** - REST API endpoints and WebSocket

## 📋 Configuration

Key constants in `hike.py`:

```python
MET_HIKING = 6.0              # Metabolic equivalent for hiking
SECONDS_PER_STEP = 0.5        # Average step duration
AVERAGE_STRIDE_M = 0.75       # Stride length in meters
SESSION_TIMEOUT_SECONDS = 3600 # Auto-end after 1 hour idle
DEFAULT_WEIGHT_KG = 70.0      # Fallback weight for calorie calc
```

## 📚 API Examples

### Get Active Session

```bash
curl https://localhost:8000/api/activeSession
```

Response (200 OK):

```json
{
  "session_id": 1,
  "device_id": "twatch_hiker_1",
  "start_time": "2024-03-22T14:30:00+00:00",
  "steps": 1234,
  "calories_burned": 425,
  "body_weight_kg": 75.0,
  "duration_seconds": 1800
}
```

### Set User Weight

```bash
curl -X POST https://localhost:8000/api/setWeight \
  -H "Content-Type: application/json" \
  -d '{"body_weight_kg": 75.0}'
```

### Get All Sessions

```bash
curl https://localhost:8000/api/allSessions
```

### Delete Session

```bash
curl -X DELETE https://localhost:8000/api/session/1
```

### WebSocket Connection

```javascript
const ws = new WebSocket("wss://localhost:8000/api/ws");
ws.onmessage = (event) => {
  const sessionData = JSON.parse(event.data);
  console.log("Updated session:", sessionData);
};
```

## 🔗 Integration with Frontend

The frontend communicates with this backend via:

1. **REST Calls** - Fetch session data, set weight, delete sessions
2. **WebSocket** - Subscribe to real-time updates (1 Hz push rate)
3. **CORS Support** - Frontend can connect from different origins

## 📝 File Structure

- **receiver.py** - Main entry point, event loop orchestration
- **bt.py** - BLE central device, smartwatch communication
- **db.py** - SQLite database layer, persistence
- **hike.py** - Session state, calorie calculations
- **wserver.py** - FastAPI server, REST & WebSocket endpoints
- **requirements.txt** - Python package dependencies
- **tests/** - Test suite

## 🚀 Deployment Considerations

- **CORS Enabled** - Frontend can connect from any origin (configurable)
- **SSL/TLS** - Use self-signed certs for development, proper CA certs for production
- **Logging** - Configurable log level (INFO by default)
- **Async I/O** - Non-blocking BLE and network operations for efficiency
