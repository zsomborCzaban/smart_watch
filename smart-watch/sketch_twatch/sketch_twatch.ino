#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <rom/crc.h> 

#define LILYGO_WATCH_2020_V2
#define LILYGO_WATCH_HAS_GPS
#include <LilyGoWatch.h>

// Forward declarations
void drawUI();
void updateTopDisplay();
void handleTouch(int16_t x, int16_t y);

TTGOClass *ttgo;

// ==========================================
// GLOBALS & CONFIGURATION
// ==========================================
// --- BLE Configuration ---
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define STEP_DATA_CHAR_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CALORIE_CHAR_UUID   "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
#define SYNC_TIME_CHAR_UUID "6e400004-b5a3-f393-e0a9-e50e24dcca9e"

BLEServer* pServer = NULL;
BLECharacteristic* pNotifyChar = NULL;
BLECharacteristic* pCalorieChar = NULL;
BLECharacteristic* pSyncTimeChar = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;
String bleMacAddress = "";

enum SessionState { STOPPED, ACTIVE, PAUSED };
SessionState currentState = STOPPED;

String deviceId = "twatch_hiker_1";
uint32_t sessionStartSteps = 0;
int32_t currentSteps = 0;
int currentCalories = 0; 
bool lastChargingState = false;
uint32_t pauseStartSensorSteps = 0;
int32_t pausedStepsOffset = 0;

// --- Timers & Offline State Tracking ---
unsigned long lastLogTime = 0;
unsigned long lastSecUpdate = 0;
unsigned long lastTouchTime = 0; // Added for non-blocking touch debounce

// Track state changes that happened while disconnected
bool missedPause = false;
bool missedContinue = false;

void updateTopDisplay();
void drawUI();

class CalorieCallback: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pChar) {
        std::string rxValue = pChar->getValue();
        if (rxValue.length() > 0) {
            String payload = String(rxValue.c_str());
            int colon = payload.indexOf(':');
            int brace = payload.indexOf('}');
            if (colon != -1 && brace != -1) {
                currentCalories = payload.substring(colon + 1, brace).toInt();
                updateTopDisplay(); // Force UI update on new data
            }
        }
    }
};

class TimeSyncCallback: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pChar) {
        std::string rxValue = pChar->getValue();
        if (rxValue.length() > 0) {
            String payload = String(rxValue.c_str());
            int colonIndex = payload.indexOf(':');
            int braceIndex = payload.indexOf('}');
            if (colonIndex != -1 && braceIndex != -1) {
                String timestampStr = payload.substring(colonIndex + 1, braceIndex);
                time_t unixTime = timestampStr.toInt();
                struct timeval tv = {unixTime, 0};
                settimeofday(&tv, nullptr);
            }
        }
    }
};

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; };
    void onDisconnect(BLEServer* pServer) { deviceConnected = false; }
};

String getCurrentTimestamp() {
    time_t now = time(nullptr);
    struct tm* timeinfo = gmtime(&now);
    char buffer[30];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", timeinfo);
    return String(buffer);
}

String generateJSONPayload(int32_t steps) {
    String timestamp = getCurrentTimestamp();
    String dataToHash = deviceId + timestamp + String(steps);
    uint32_t checksum_num = crc32_le(0, (const uint8_t*)dataToHash.c_str(), dataToHash.length());
    char checksum_hex[9];
    sprintf(checksum_hex, "%08x", checksum_num);
    return "{\"device_id\":\"" + deviceId + "\", \"timestamp\":\"" + timestamp + 
           "\", \"step_count\":" + String(steps) + ", \"checksum\":\"" + String(checksum_hex) + "\"}";
}

// Replaced sendOrCache with simple sendData
void sendData(String payload) {
    if (deviceConnected) {
        pNotifyChar->setValue(payload.c_str());
        pNotifyChar->notify();
    }
}

void setup() {
    Serial.begin(115200);
    ttgo = TTGOClass::getWatch();
    ttgo->begin();

    // Enable Battery Sensor
    ttgo->power->adc1Enable(AXP202_BATT_VOL_ADC1 | AXP202_BATT_CUR_ADC1, true);
    lastChargingState = ttgo->power->isChargeing();

    // Setup BMA Step Counter
    ttgo->bma->begin();
    ttgo->bma->enableAccel(); 
    ttgo->bma->enableFeature(BMA423_STEP_CNTR, true); 
    ttgo->bma->resetStepCounter(); 

    ttgo->openBL();
    ttgo->gps_begin();
    
    // BLE Setup
    BLEDevice::init("TWatch_Hiker_BLE");
    BLEDevice::setMTU(512); 
    bleMacAddress = BLEDevice::getAddress().toString().c_str();
    bleMacAddress.toUpperCase();

    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    BLEService *pService = pServer->createService(SERVICE_UUID);

    pNotifyChar = pService->createCharacteristic(STEP_DATA_CHAR_UUID, BLECharacteristic::PROPERTY_NOTIFY);
    pNotifyChar->addDescriptor(new BLE2902());

    pCalorieChar = pService->createCharacteristic(CALORIE_CHAR_UUID, BLECharacteristic::PROPERTY_WRITE);
    pCalorieChar->setCallbacks(new CalorieCallback());

    pSyncTimeChar = pService->createCharacteristic(SYNC_TIME_CHAR_UUID, BLECharacteristic::PROPERTY_WRITE);
    pSyncTimeChar->setCallbacks(new TimeSyncCallback());

    pService->start();
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true); 
    BLEDevice::startAdvertising();

    drawUI();
}

void handleBLE() {
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); 
        pServer->startAdvertising(); 
        oldDeviceConnected = deviceConnected; 
        updateTopDisplay(); 
    }
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected; 
        updateTopDisplay(); 
        
        // Reconnect Logic: Process missing offline states
        if (currentState == PAUSED && missedPause) {
            // User paused while offline: send current data, then pause signal
            sendData(generateJSONPayload(currentSteps));
            sendData(generateJSONPayload(-2));
            missedPause = false;
        } 
        else if (currentState == ACTIVE && missedContinue) {
            // User paused AND continued while offline: send pause signal, continue signal, then fresh data
            sendData(generateJSONPayload(-2)); 
            sendData(generateJSONPayload(-3)); 
            sendData(generateJSONPayload(currentSteps));
            missedContinue = false;
            missedPause = false; // Clear both just in case
        } 
        else if (currentState == ACTIVE || currentState == PAUSED) {
            // Normal reconnect: just blast out the freshest data
            sendData(generateJSONPayload(currentSteps));
        }
    }
}

void handleGPS() {
    if (ttgo->hwSerial && ttgo->hwSerial->available()) {
        while (ttgo->hwSerial->available()) ttgo->gps->encode(ttgo->hwSerial->read());
    }
}

void handleTouchInput() {
    int16_t x, y;
    unsigned long currentMillis = millis();

    // Only process a touch if 150ms have passed since the last one (Non-blocking debounce)
    if (currentMillis - lastTouchTime < 150) {
        return; 
    }

    if (ttgo->getTouch(x, y)) {
        lastTouchTime = currentMillis; // Record the time of this touch

        if (y > 80 && y < 160) {
            if (x < 120 && currentState == STOPPED) {
                currentState = ACTIVE; 
                sessionStartSteps = ttgo->bma->getCounter(); 
                currentSteps = 0; currentCalories = 0; 
                pauseStartSensorSteps = 0;
                pausedStepsOffset = 0;
                missedPause = false;
                missedContinue = false;
                sendData(generateJSONPayload(0));
            } else if (x >= 120 && currentState != STOPPED) {
                currentState = STOPPED; 
                sendData(generateJSONPayload(-1));
            }
        } else if (y >= 160) {
            if (x < 120 && currentState == ACTIVE) {
                currentState = PAUSED;
                pauseStartSensorSteps = ttgo->bma->getCounter();
                int32_t rawSessionSteps = (int32_t)ttgo->bma->getCounter() - (int32_t)sessionStartSteps;
                currentSteps = rawSessionSteps - pausedStepsOffset;
                if (currentSteps < 0) {
                    currentSteps = 0;
                }
                
                if (!deviceConnected) missedPause = true;

                sendData(generateJSONPayload(currentSteps));
                sendData(generateJSONPayload(-2)); 
            } else if (x >= 120 && currentState == PAUSED) {
                currentState = ACTIVE;
                uint32_t resumeSensorSteps = ttgo->bma->getCounter();
                if (resumeSensorSteps >= pauseStartSensorSteps) {
                    pausedStepsOffset += (int32_t)(resumeSensorSteps - pauseStartSensorSteps);
                }
                
                if (!deviceConnected) missedContinue = true;

                sendData(generateJSONPayload(-3)); 
            }
        }
        drawUI(); 
    }
}

void handleTasks() {
    unsigned long currentMillis = millis();

    // 1. One-Second Tasks: Battery Check & Real-time UI Refresh
    if (currentMillis - lastSecUpdate >= 1000) {
        lastSecUpdate = currentMillis;
        
        bool currentCharging = ttgo->power->isChargeing();
        bool stateChanged = (currentCharging != lastChargingState);
        lastChargingState = currentCharging;

        // Update UI if plugged/unplugged, OR if we are currently tracking a hike
        if (stateChanged || currentState == ACTIVE) {
            if (currentState == ACTIVE) {
                int32_t rawSessionSteps = (int32_t)ttgo->bma->getCounter() - (int32_t)sessionStartSteps;
                currentSteps = rawSessionSteps - pausedStepsOffset;
                if (currentSteps < 0) {
                    currentSteps = 0;
                }
            }
            updateTopDisplay(); 
        }
    }

    // 2. Logging Task (Only triggers if active AND connected)
    if (currentState == ACTIVE && (currentMillis - lastLogTime >= 1000)) {
        lastLogTime = currentMillis;
        if (deviceConnected) {
            sendData(generateJSONPayload(currentSteps));
        }
    }
}

void loop() {
    handleBLE();
    handleGPS();
    handleTasks();
    handleTouchInput();
}

// ==========================================
// UI DRAWING
// ==========================================
void drawUI() {
    ttgo->tft->fillScreen(TFT_BLACK);
    updateTopDisplay();
    ttgo->tft->fillRect(0, 80, 118, 78, (currentState == STOPPED) ? TFT_GREEN : TFT_DARKGREY);
    ttgo->tft->drawString("START", 30, 110, 2);
    ttgo->tft->fillRect(122, 80, 118, 78, (currentState != STOPPED) ? TFT_RED : TFT_DARKGREY);
    ttgo->tft->drawString("STOP", 160, 110, 2);
    ttgo->tft->fillRect(0, 162, 118, 78, (currentState == ACTIVE) ? TFT_ORANGE : TFT_DARKGREY);
    ttgo->tft->drawString("PAUSE", 30, 192, 2);
    ttgo->tft->fillRect(122, 162, 118, 78, (currentState == PAUSED) ? TFT_BLUE : TFT_DARKGREY);
    ttgo->tft->drawString("CONT.", 160, 192, 2);
}

void updateTopDisplay() {
    ttgo->tft->fillRect(0, 0, 240, 80, TFT_BLACK);
    
    // --- STATE ---
    String stateStr = (currentState == ACTIVE) ? "ACTIVE" : (currentState == PAUSED ? "PAUSED" : "STOPPED");
    ttgo->tft->setTextColor(TFT_WHITE);
    ttgo->tft->drawString("State: " + stateStr, 10, 5, 2);
    
    // --- BATTERY ---
    String batStr = String(ttgo->power->getBattPercentage()) + "%";
    if (lastChargingState) {
        batStr += " (+)";
        ttgo->tft->setTextColor(TFT_GREEN); 
    } else {
        ttgo->tft->setTextColor(TFT_WHITE);
    }
    ttgo->tft->drawString("Bat: " + batStr, 130, 5, 2); 

    // --- SENSORS ---
    ttgo->tft->setTextColor(TFT_WHITE);
    ttgo->tft->drawString("Steps: " + String(currentSteps), 10, 25, 2);
    ttgo->tft->setTextColor(TFT_ORANGE);
    ttgo->tft->drawString("kcal: " + String(currentCalories), 120, 25, 2);
    
    // --- SYSTEM ---
    ttgo->tft->setTextColor(TFT_WHITE);
    ttgo->tft->drawString(deviceConnected ? "BLE: Ok" : "BLE: Disconnected", 10, 45, 2);
    ttgo->tft->setTextColor(TFT_YELLOW);
    ttgo->tft->drawString("MAC: " + bleMacAddress, 10, 65, 1);
}