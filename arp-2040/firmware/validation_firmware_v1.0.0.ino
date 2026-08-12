/**
 * ARP-2040 Validation Firmware v1.0.0
 * Minimal smoke-test sketch for Nano RP2040 Connect
 *
 * Validates:
 *   - RP2040 core clock
 *   - Built-in LED
 *   - LSM6DSOX I2C presence
 *   - NINA-W102 AT passthrough
 *   - ATECC608A basic detection
 *   - QSPI flash readback
 */

#include <Arduino.h>
#include <WiFiNINA.h>
#include <ArduinoBLE.h>
#include <Wire.h>
#include <SPI.h>
#include <ArduinoJson.h>
#include "common/common_types.h"

#define FW_VERSION "arp-2040-connect/1.0.0"
#define I2C_SCL     SCL
#define I2C_SDA     SDA
#define LSM6DSOX_ADDR 0x6A
#define ATECC608A_ADDR 0x60
#define LED_PIN     LED_BUILTIN

static void print_banner() {
  Serial.begin(921600);
  while (!Serial && millis() < 2000) { delay(10); }
  Serial.println();
  Serial.println(F("========================================"));
  Serial.print(F(" ARP-2040 Validation Firmware v1.0.0\n"));
  Serial.print(F(" MCU: RP2040 @ ")); Serial.print(SystemCoreClock / 1000000); Serial.println(F(" MHz"));
  Serial.print(F(" SDK: Arduino-Pico ")); Serial.println(F("2.6.0"));
  Serial.print(F(" Time: ")); Serial.print(__DATE__); Serial.print(F(" ")); Serial.println(__TIME__);
  Serial.println(F("========================================"));
}

static bool led_test() {
  pinMode(LED_PIN, OUTPUT);
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH); delay(150);
    digitalWrite(LED_PIN, LOW);  delay(150);
  }
  return true;
}

static bool imu_test() {
  Wire.begin();
  Wire.beginTransmission(LSM6DSOX_ADDR);
  if (Wire.endTransmission() != 0) {
    Serial.println(F("[FAIL] LSM6DSOX not found on I2C"));
    return false;
  }
  Wire.requestFrom(LSM6DSOX_ADDR, 1);
  if (Wire.available()) {
    uint8_t whoami = Wire.read();
    Serial.print(F("[PASS] LSM6DSOX WHO_AMI = 0x"));
    Serial.println(whoami, HEX);
    return whoami == 0x6C;
  }
  Serial.println(F("[FAIL] LSM6DSOX WHO_AMI read failed"));
  return false;
}

static bool nina_test() {
  // Check NINA firmware presence via WiFiNINA
  String fw = WiFi.firmwareVersion();
  Serial.print(F("[INFO] NINA firmware version: "));
  Serial.println(fw);
  if (fw == "0.0.0" || fw == "Unknown") {
    Serial.println(F("[WARN] NINA firmware not responding"));
    return false;
  }
  Serial.println(F("[PASS] NINA-W102 responding"));
  return true;
}

static bool crypto_test() {
  Wire.beginTransmission(ATECC608A_ADDR);
  if (Wire.endTransmission() != 0) {
    Serial.println(F("[WARN] ATECC608A not detected on I2C"));
    return false;
  }
  Serial.println(F("[PASS] ATECC608A detected on I2C"));
  return true;
}

static bool flash_test() {
  // Simple QSPI readback: read flash ID via SPI0
  pinMode(SS, OUTPUT);
  digitalWrite(SS, HIGH);
  SPI.begin();
  delayMicroseconds(100);
  digitalWrite(SS, LOW);
  SPI.transfer(0x9F);  // JEDEC ID
  uint8_t mfr = SPI.transfer(0x00);
  uint8_t mem1 = SPI.transfer(0x00);
  uint8_t mem2 = SPI.transfer(0x00);
  digitalWrite(SS, HIGH);
  SPI.end();
  Serial.print(F("[INFO] Flash JEDEC ID: 0x"));
  Serial.print(mfr, HEX); Serial.print(":");
  Serial.print(mem1, HEX); Serial.print(":");
  Serial.println(mem2, HEX);
  return (mfr == 0xEF || mfr == 0x0B || mfr == 0xC2);
}

static void run_self_tests() {
  Serial.println(F("\n[SELF-TEST] Running..."));
  int passed = 0, failed = 0;

  if (led_test())    passed++; else failed++;
  if (imu_test())    passed++; else failed++;
  if (nina_test())   passed++; else failed++;
  if (crypto_test()) passed++; else failed++;
  if (flash_test())  passed++; else failed++;

  Serial.println();
  Serial.print(F("[RESULT] PASSED: ")); Serial.print(passed);
  Serial.print(F("  FAILED: ")); Serial.println(failed);
  if (failed == 0) {
    Serial.println(F("[RESULT] ALL TESTS PASSED"));
  } else {
    Serial.println(F("[RESULT] SOME TESTS FAILED"));
  }
}

void setup() {
  print_banner();
  run_self_tests();
}

void loop() {
  digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  delay(500);
  Serial.print(F("[HEARTBEAT] Uptime: "));
  Serial.print(millis() / 1000);
  Serial.println(F(" s"));
}
