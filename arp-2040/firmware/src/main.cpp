/**
 * @file main.cpp
 * @brief ARP-2040 Connect Firmware entry point
 *
 * Target: Arduino Nano RP2040 Connect (ABX00053)
 */

#include <Arduino.h>
#include <WiFiNINA.h>
#include <ArduinoBLE.h>
#include <ArduinoJson.h>
#include "common/common_types.h"
#include "kernel/ITask.h"
#include "kernel/IAgentRegistry.h"
#include "hal/ISensor.h"
#include "hal/IRadio.h"
#include "hal/ICrypto.h"
#include "hal/IStorage.h"
#include "hal/IPower.h"
#include "hal/IAudio.h"
#include "hal/HALFactory.h"
#include "ai/TFLiteMicroRuntime.h"
#include "scripting/ControlGraphLoader.h"
#include "scripting/BytecodeInterpreter.h"

/* ─── Version ─────────────────────────────────────────────────────────── */
#define FW_VERSION_MAJOR 1
#define FW_VERSION_MINOR 0
#define FW_VERSION_PATCH 0
#define FW_BUILD_DATE __DATE__
#define FW_BUILD_TIME __TIME__

static const char* const kFirmwareVersion =
  "arp-2040-connect/1.0.0 (" FW_BUILD_DATE " " FW_BUILD_TIME ")";
static const char* const kDeviceId = "arp2040-connect-001";

/* ─── Hardware instances ──────────────────────────────────────────────── */
static ISensor*      g_sensor      = nullptr;
static IRadio*       g_radio       = nullptr;
static ICrypto*      g_crypto      = nullptr;
static IStorage*     g_storage     = nullptr;
static IPower*       g_power       = nullptr;
static IAudio*       g_audio       = nullptr;
static IModelRuntime*g_runtime     = nullptr;

static AgentRegistry g_registry;
static ControlGraphLoader g_graph_loader;
static BytecodeInterpreter g_interpreter;

/* ─── Forward declarations ────────────────────────────────────────────── */
static void sensor_task(void* params);
static void inference_task(void* params);
static void connectivity_task(void* params);
static void power_task(void* params);
static void learning_task(void* params);

/* ─── Helpers ─────────────────────────────────────────────────────────── */
static void log_boot_info() {
  Serial.begin(921600);
  while (!Serial && millis() < 3000) { delay(10); }

  Serial.println();
  Serial.println(F("========================================"));
  Serial.println(F(" ARP-2040 Connect Firmware"));
  Serial.print(F(" Version: ")); Serial.println(kFirmwareVersion);
  Serial.print(F(" Device:  ")); Serial.println(kDeviceId);
  Serial.print(F(" MCU:     RP2040 @ "));
  Serial.print(SystemCoreClock / 1000000);
  Serial.println(F(" MHz"));
  Serial.print(F(" SRAM:    "));
  Serial.print(HEAP_SIZE / 1024);
  Serial.println(F(" KB"));
  Serial.println(F("========================================"));
}

static bool init_hardware() {
  bool ok = true;
  if (!g_sensor) {
    g_sensor = HALFactory::create_sensor().release();
    if (!g_sensor) {
      Serial.println(F("[BOOT] Sensor HAL init failed"));
      ok = false;
    }
  }
  if (!g_radio) {
    g_radio = HALFactory::create_radio().release();
    if (!g_radio) {
      Serial.println(F("[BOOT] Radio HAL init failed"));
      ok = false;
    }
  }
  if (!g_crypto) {
    Serial.println(F("[BOOT] Crypto HAL pending"));
    ok = false;
  }
  if (!g_storage) {
    g_storage = HALFactory::create_storage().release();
    if (!g_storage) {
      Serial.println(F("[BOOT] Storage HAL init failed"));
      ok = false;
    }
  }
  if (!g_power) {
    Serial.println(F("[BOOT] Power HAL pending"));
    ok = false;
  }
  if (!g_audio) {
    Serial.println(F("[BOOT] Audio HAL pending"));
    ok = false;
  }
  if (!g_runtime) {
    Serial.println(F("[BOOT] Runtime HAL pending"));
    ok = false;
  }
  return ok;
}

static void create_agents() {
  TaskCreate(sensor_task, "sensor", 4096, nullptr, 3, nullptr);
  TaskCreate(inference_task, "inference", 16384, nullptr, 2, nullptr);
  TaskCreate(connectivity_task, "connectivity", 8192, nullptr, 3, nullptr);
  TaskCreate(power_task, "power", 2048, nullptr, 1, nullptr);
  TaskCreate(learning_task, "learning", 4096, nullptr, 1, nullptr);
}

/* ─── Agents ──────────────────────────────────────────────────────────── */

static void sensor_task(void* /*params*/) {
  Serial.println(F("[SensorAgent] Started"));
  TickType_t last = xTaskGetTickCount();
  while (true) {
    // TODO: g_sensor->readAll(...)
    //       g_audio->readPDM(...)
    //       MLC gesture -> queue to inference_task
    vTaskDelayUntil(&last, pdMS_TO_TICKS(100));  // 10 Hz
  }
}

static void inference_task(void* /*params*/) {
  Serial.println(F("[InferenceAgent] Started"));
  TickType_t last = xTaskGetTickCount();
  while (true) {
    // TODO: g_runtime->runModel(kws_model, ...)
    //       g_runtime->runModel(imu_model, ...)
    //       Control graph dispatch via g_interpreter
    vTaskDelayUntil(&last, pdMS_TO_TICKS(50));  // 20 Hz
  }
}

static void connectivity_task(void* /*params*/) {
  Serial.println(F("[ConnectivityAgent] Started"));
  TickType_t last = xTaskGetTickCount();
  while (true) {
    // TODO: g_radio->bleAdvertise()
    //       g_radio->wifiConnect(ssid, pass)
    //       TCP server on SoftAP
    //       MCP wire protocol handling
    vTaskDelayUntil(&last, pdMS_TO_TICKS(1000));
  }
}

static void power_task(void* /*params*/) {
  Serial.println(F("[PowerAgent] Started"));
  TickType_t last = xTaskGetTickCount();
  while (true) {
    // TODO: g_power->readBattery()
    //       Transition to dormant/sleep based on state machine
    vTaskDelayUntil(&last, pdMS_TO_TICKS(1000));  // 1 Hz
  }
}

static void learning_task(void* /*params*/) {
  Serial.println(F("[LearningAgent] Started"));
  TickType_t last = xTaskGetTickCount();
  while (true) {
    // TODO: aggregate MODEL_DELTA messages
    //       shadow-test promoted models
    //       push MODEL_PUSH back to device
    vTaskDelayUntil(&last, pdMS_TO_TICKS(5000));  // 0.2 Hz
  }
}

/* ─── Main ────────────────────────────────────────────────────────────── */
void setup() {
  log_boot_info();

  Serial.println(F("[BOOT] Initializing hardware..."));
  if (!init_hardware()) {
    Serial.println(F("[BOOT] HAL implementations missing - agents created in stub mode"));
  }

  Serial.println(F("[BOOT] Creating agent tasks..."));
  create_agents();

  Serial.println(F("[BOOT] Boot complete."));
}

void loop() {
  // Empty: all work is in FreeRTOS tasks
  delay(1000);
}
