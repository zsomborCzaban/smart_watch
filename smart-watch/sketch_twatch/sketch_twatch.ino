#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <rom/crc.h> 

#define LILYGO_WATCH_2020_V2
#define LILYGO_WATCH_HAS_GPS
#include <LilyGoWatch.h>
#include <vector>

// Forward declarations
void drawUI();
void updateTopDisplay();
void handleTouch(int16_t x, int16_t y);

TTGOClass *ttgo;

// --- BLE State ---
BLEServer* pServer = NULL;
BLECharacteristic* pNotifyChar = NULL;
BLECharacteristic* pCalorieChar = NULL;
BLECharacteristic* pSyncTimeChar = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;
String bleMacAddress = "";

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define STEP_DATA_CHAR_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CALORIE_CHAR_UUID   "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
#define SYNC_TIME_CHAR_UUID "6e400004-b5a3-f393-e0a9-e50e24dcca9e"

enum SessionState { STOPPED, ACTIVE, PAUSED };
SessionState currentState = STOPPED;

String deviceId = "twatch_hiker_1";
uint32_t sessionStartSteps = 0;
int32_t currentSteps = 0;
int currentCalories = 0; 

unsigned long lastLogTime = 0;
const unsigned long logInterval = 5000; 
unsigned long lastCacheFlushTime = 0;
std::vector<String> offlineCache;
const size_t MAX_CACHE_SIZE = 50; 

// --- Calorie Write Callback ---
class CalorieCallback: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pChar) {
        std::string rxValue = pChar->getValue();
        if (rxValue.length() > 0) {
            String payload = String(rxValue.c_str());
            int colon = payload.indexOf(':');
            int brace = payload.indexOf('}');
            if (colon != -1 && brace != -1) {
                currentCalories = payload.substring(colon + 1, brace).toInt();
                ttgo->tft->setTextColor(TFT_ORANGE, TFT_BLACK);
                ttgo->tft->drawString("kcal: " + String(currentCalories), 120, 25, 2);
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
                timestampStr.trim();
                time_t unixTime = timestampStr.toInt();
                struct timeval tv = {unixTime, 0};
                settimeofday(&tv, nullptr);
                Serial.println("Time synced from backend: " + timestampStr);
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

void setup() {
    Serial.begin(115200);
    ttgo = TTGOClass::getWatch();
    ttgo->begin();
    ttgo->openBL();

    // --- CRITICAL STEP COUNTER FIX ---
    ttgo->bma->begin();
    ttgo->bma->enableAccel(); // Wakes up the hardware
    ttgo->bma->enableFeature(BMA423_STEP_CNTR, true); // Turns on step logic
    ttgo->bma->resetStepCounter(); // Set hardware to zero
    // ---------------------------------

    ttgo->gps_begin();
    
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

void loop() {
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); pServer->startAdvertising(); oldDeviceConnected = deviceConnected; updateTopDisplay(); 
    }
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected; updateTopDisplay(); 
    }
    
    // GPS Feed
    if (ttgo->hwSerial && ttgo->hwSerial->available()) {
        while (ttgo->hwSerial->available()) ttgo->gps->encode(ttgo->hwSerial->read());
    }

    // Touch
    int16_t x, y;
    if (ttgo->getTouch(x, y)) { handleTouch(x, y); delay(150); }

    // Logging
    if (currentState == ACTIVE && (millis() - lastLogTime >= logInterval)) {
        lastLogTime = millis();
        // Read current hardware steps
        currentSteps = ttgo->bma->getCounter() - sessionStartSteps;
        sendOrCache(generateJSONPayload(currentSteps));
        updateTopDisplay(); 
    }

    // Cache Flush
    if (deviceConnected && !offlineCache.empty() && (millis() - lastCacheFlushTime > 100)) {
        lastCacheFlushTime = millis();
        pNotifyChar->setValue(offlineCache.front().c_str());
        pNotifyChar->notify();
        offlineCache.erase(offlineCache.begin());
    }
}

void sendOrCache(String payload) {
    if (deviceConnected && offlineCache.empty()) {
        pNotifyChar->setValue(payload.c_str());
        pNotifyChar->notify();
    } else if (offlineCache.size() < MAX_CACHE_SIZE) {
        offlineCache.push_back(payload);
    }
}

void handleTouch(int16_t x, int16_t y) {
    if (y > 80 && y < 160) {
        if (x < 120 && currentState == STOPPED) {
            currentState = ACTIVE; 
            sessionStartSteps = ttgo->bma->getCounter(); // Capture start baseline
            currentSteps = 0; currentCalories = 0; offlineCache.clear();
            sendOrCache(generateJSONPayload(0));
        } else if (x >= 120 && currentState != STOPPED) {
            currentState = STOPPED; 
            sendOrCache(generateJSONPayload(-1));
        }
    } else if (y >= 160) {
        if (x < 120 && currentState == ACTIVE) {
            currentState = PAUSED;
            sendOrCache(generateJSONPayload(-2)); // -2 signals PAUSE
        } else if (x >= 120 && currentState == PAUSED) {
            currentState = ACTIVE;
            sendOrCache(generateJSONPayload(-3)); // -3 signals RESUME
        }
    }
    drawUI(); 
}

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
    String stateStr = (currentState == ACTIVE) ? "ACTIVE" : (currentState == PAUSED ? "PAUSED" : "STOPPED");
    ttgo->tft->drawString("State: " + stateStr, 10, 5, 2);
    ttgo->tft->drawString("Steps: " + String(currentSteps), 10, 25, 2);
    ttgo->tft->setTextColor(TFT_ORANGE);
    ttgo->tft->drawString("kcal: " + String(currentCalories), 120, 25, 2);
    ttgo->tft->setTextColor(TFT_WHITE);
    ttgo->tft->drawString(deviceConnected ? "BLE: OK" : "BLE: DC", 10, 45, 2);
    ttgo->tft->setTextColor(TFT_YELLOW);
    ttgo->tft->drawString("MAC: " + bleMacAddress, 10, 65, 1);
    ttgo->tft->setTextColor(TFT_WHITE);
}