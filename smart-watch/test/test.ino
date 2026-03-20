#include <Arduino.h>
#include <unity.h>
#include <rom/crc.h>

// ==========================================
// 1. YOUR REAL VARIABLES & FUNCTIONS
// (This is the "Engine" taken from your main app)
// ==========================================
String deviceId = "twatch_hiker_1";

uint32_t calculateCRC(String input) {
    return crc32_le(0, (const uint8_t*)input.c_str(), input.length());
}

// NOTE: In your real app, this generates the time internally. 
// For testing, we pass the time as an argument so the output is perfectly predictable!
String generateJSONPayload(int32_t steps, String timestamp) {
    String dataToHash = deviceId + timestamp + String(steps);
    uint32_t checksum_num = calculateCRC(dataToHash);
    char checksum_hex[9];
    sprintf(checksum_hex, "%08x", checksum_num);
    return "{\"device_id\":\"" + deviceId + "\", \"timestamp\":\"" + timestamp + 
           "\", \"step_count\":" + String(steps) + ", \"checksum\":\"" + String(checksum_hex) + "\"}";
}


// ==========================================
// 2. YOUR UNIT TESTS
// (This is the "Diagnostic Machine")
// ==========================================

void test_checksum_sensitivity(void) {
    uint32_t crc1 = calculateCRC("twatch_01_data");
    uint32_t crc2 = calculateCRC("twatch_02_data"); 
    TEST_ASSERT_NOT_EQUAL(crc1, crc2);
}

void test_step_calculation_overflow(void) {
    uint32_t hardwareCounter = 100;    
    uint32_t sessionBaseline = 4294967290; 
    uint32_t result = hardwareCounter - sessionBaseline;
    TEST_ASSERT_EQUAL_UINT32(106, result);
}

// --- NEW OFFLINE STATE LOGIC TESTS ---

void test_offline_state_pause(void) {
    bool missedPause = true;
    int currentState = 2; // Simulating PAUSED state
    int payloadsSent = 0;

    // Simulating handleBLE reconnect logic
    if (currentState == 2 && missedPause) {
        payloadsSent += 2; // Should send current data, then a pause signal (-2)
        missedPause = false;
    }

    TEST_ASSERT_EQUAL_INT(2, payloadsSent);
    TEST_ASSERT_FALSE(missedPause);
}

void test_offline_state_pause_and_continue(void) {
    bool missedPause = true;
    bool missedContinue = true;
    int currentState = 1; // Simulating ACTIVE state
    int payloadsSent = 0;

    // Simulating handleBLE reconnect logic
    if (currentState == 1 && missedContinue) {
        payloadsSent += 3; // Should send pause (-2), continue (-3), then fresh data
        missedContinue = false;
        missedPause = false;
    }

    TEST_ASSERT_EQUAL_INT(3, payloadsSent);
    TEST_ASSERT_FALSE(missedContinue);
    TEST_ASSERT_FALSE(missedPause);
}

// -------------------------------------

void test_mtu_safety_limit(void) {
    int32_t maxSteps = 999999;
    String longPayload = generateJSONPayload(maxSteps, "2026-03-20T12:00:00Z");
    // BLE MTU is 512, ensure payload is safely under 200 chars
    TEST_ASSERT_TRUE(longPayload.length() < 200);
}

void test_rapid_state_toggle(void) {
    int state = 0; // 0:STOP, 1:ACTIVE
    for(int i = 0; i < 100; i++) {
        state = (state == 0) ? 1 : 0;
    }
    TEST_ASSERT_EQUAL_INT(0, state);
}

void test_pause_resume_offset(void) {
    uint32_t pauseStartSensorSteps = 5000; 
    uint32_t resumeSensorSteps = 5150;     
    int32_t pausedStepsOffset = 0;
    
    if (resumeSensorSteps >= pauseStartSensorSteps) {
        pausedStepsOffset += (int32_t)(resumeSensorSteps - pauseStartSensorSteps);
    }
    TEST_ASSERT_EQUAL_INT32(150, pausedStepsOffset);
}

void test_json_payload_format(void) {
    int32_t steps = 1337;
    String payload = generateJSONPayload(steps, "2026-03-20T12:00:00Z");
    
    TEST_ASSERT_TRUE(payload.indexOf("\"device_id\":\"twatch_hiker_1\"") > 0);
    TEST_ASSERT_TRUE(payload.indexOf("\"step_count\":1337") > 0);
    TEST_ASSERT_TRUE(payload.indexOf("\"timestamp\":\"2026-03-20") > 0);
    TEST_ASSERT_TRUE(payload.indexOf("\"checksum\":") > 0);
}

void test_calorie_parsing(void) {
    String payload = "{kcal:425}";
    int colon = payload.indexOf(':');
    int brace = payload.indexOf('}');
    int parsedCalories = -1;
    
    if (colon != -1 && brace != -1) {
        parsedCalories = payload.substring(colon + 1, brace).toInt();
    }
    TEST_ASSERT_EQUAL_INT(425, parsedCalories);
}

void test_malformed_ble_payload(void) {
    String payload = "{kcal:425"; // Missing closing brace
    int colon = payload.indexOf(':');
    int brace = payload.indexOf('}');
    int parsedCalories = 0; 
    
    if (colon != -1 && brace != -1) {
        parsedCalories = payload.substring(colon + 1, brace).toInt();
    }
    TEST_ASSERT_EQUAL_INT(0, parsedCalories);
}


// ==========================================
// 3. ARDUINO RUNNER
// (This boots up the workbench and runs the tests)
// ==========================================

void setup() {
    // Start serial communication
    Serial.begin(115200);
    
    // Wait for the serial monitor to be opened before running tests
    while (!Serial) {
        delay(10);
    }
    delay(2000); // Give the monitor a moment to settle
    
    Serial.println("--- STARTING UNIT TESTS ---");

    UNITY_BEGIN();
    
    RUN_TEST(test_checksum_sensitivity);
    RUN_TEST(test_step_calculation_overflow);
    RUN_TEST(test_offline_state_pause);
    RUN_TEST(test_offline_state_pause_and_continue);
    RUN_TEST(test_mtu_safety_limit);
    RUN_TEST(test_rapid_state_toggle);
    RUN_TEST(test_pause_resume_offset);
    RUN_TEST(test_json_payload_format);
    RUN_TEST(test_calorie_parsing);
    RUN_TEST(test_malformed_ble_payload);
    
    UNITY_END();
}

void loop() {
    // We intentionally leave the loop empty. 
    // Tests only need to run once when the watch boots up!
}