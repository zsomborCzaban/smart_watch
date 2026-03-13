# ⌚ T-Watch Hiker: BLE Step & GPS Tracker

An ESP32-based hiking companion for the **LilyGO T-Watch 2020 v2**. This project tracks steps and GPS coordinates, caching data during signal drops and syncing via **BLE 5.0** to a Raspberry Pi Hub.

## 🚀 Features
- **Real-time Tracking**: Counts steps using the BMA423 accelerometer.
- **GPS Integration**: Monitors location via the built-in GPS module.
- **Offline Caching**: Stores up to 50 data points locally when the Raspberry Pi is out of range.
- **BLE Notification System**: Sends JSON-formatted data with CRC32 checksums for integrity.
- **Bi-directional Sync**: Receives calculated "Burned Calories" from the backend and displays them in real-time.

## 🛠 Hardware
- **Device**: LilyGO T-Watch 2020 v2
- **Processor**: ESP32-D0WDQ6-V3 (WROVER)
- **Sensors**: BMA423 (Accel), GPS (L76-L)
- **Display**: 1.54 inch LCD Capacitive Touch

## 📦 Requirements & Setup

### Arduino IDE Settings
- **Board**: `ESP32 Wrover Module`
- **PSRAM**: `Enabled`
- **Partition Scheme**: `Huge APP (3MB No OTA)`
- **Flash Frequency**: `80MHz`

### Libraries Needed
1. `LilyGoWatch` by Lewis He
2. `BLE` (Built into ESP32 Core)

## 📡 BLE Protocol
The watch acts as a **BLE Server** with the following GATT structure:
- **Service UUID**: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`
- **Notify Characteristic**: `beb5483e-36e1-4688-b7f5-ea07361b26a8` (Sends Step JSON)
- **Write Characteristic**: `6e400003-b5a3-f393-e0a9-e50e24dcca9e` (Receives Calorie JSON)

### Data Format
The Hub expects a JSON payload with a CRC32 checksum:
```json
{
  "device_id": "twatch_hiker_1",
  "timestamp": "ISO-8601",
  "step_count": 1234,
  "checksum": "8char-hex-crc"
}