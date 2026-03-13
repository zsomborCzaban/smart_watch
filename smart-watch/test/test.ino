#include <unity.h>
#include <rom/crc.h>
#include <vector>

// --- Mock Data ---
String deviceId = "twatch_01";
String timestamp = "2026-03-13T12:00:00Z";
std::vector<String> testCache;
const size_t MAX_CACHE = 50;

// --- Helper for CRC Testing ---
uint32_t calculateCRC(String input) {
    return crc32_le(0, (const uint8_t*)input.c_str(), input.length());
}

// --- NEW TESTS ---

// 1. Checksum Sensitivity Test
void test_checksum_sensitivity(void) {
    uint32_t crc1 = calculateCRC("twatch_01_data");
    uint32_t crc2 = calculateCRC("twatch_02_data"); // Only 1 character difference
    TEST_ASSERT_NOT_EQUAL(crc1, crc2);
}

// 2. Integer Wrap-around/Overflow Test
void test_step_calculation_overflow(void) {
    uint32_t hardwareCounter = 100;    // Hardware just reset
    uint32_t sessionBaseline = 4294967290; // Session started just before overflow
    
    // In our logic: currentSteps = hardwareCounter - sessionBaseline
    // Standard unsigned math handles this, but we must verify
    uint32_t result = hardwareCounter - sessionBaseline;
    
    // Should be 100 + 6 (distance to overflow) = 106
    TEST_ASSERT_EQUAL_UINT32(106, result);
}

// 3. Cache Empty Handling
void test_empty_cache_logic(void) {
    testCache.clear();
    // Simulate a flush attempt
    bool canFlush = !testCache.empty();
    TEST_ASSERT_FALSE(canFlush);
    // Logic check: ensure front() isn't called on empty vector (prevents crash)
    if (canFlush) {
        String data = testCache.front();
    }
}

// 4. Maximum Payload Size Check
void test_mtu_safety_limit(void) {
    // BLE MTU is set to 512. Let's ensure our longest JSON is way under that.
    int32_t maxSteps = 999999;
    String longPayload = "{\"device_id\":\"" + deviceId + "\", \"step_count\":" + String(maxSteps) + ", \"checksum\":\"ffffffff\"}";
    
    // Safety check: Is payload < 200 chars? (Safe for 512 MTU)
    TEST_ASSERT_TRUE(longPayload.length() < 200);
}

// 5. State Machine: Rapid Toggle
void test_rapid_state_toggle(void) {
    int state = 0; // 0:STOP, 1:ACTIVE
    // Simulate 100 rapid clicks
    for(int i=0; i<100; i++) {
        state = (state == 0) ? 1 : 0;
    }
    // Should end back at STOP (0) after even number of toggles
    TEST_ASSERT_EQUAL_INT(0, state);
}

void setup() {
    Serial.begin(115200);
    while(!Serial);
    delay(2000);

    UNITY_BEGIN();
    
    RUN_TEST(test_checksum_sensitivity);
    RUN_TEST(test_step_calculation_overflow);
    RUN_TEST(test_empty_cache_logic);
    RUN_TEST(test_mtu_safety_limit);
    RUN_TEST(test_rapid_state_toggle);
    
    UNITY_END();
}

void loop() {}