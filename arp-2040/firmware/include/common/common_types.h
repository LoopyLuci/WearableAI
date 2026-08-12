/**
 * @file common_types.h
 * @brief Shared type definitions for the ARP-2040 firmware
 *
 * These types are used across all HAL interfaces and must remain stable.
 * Do not modify without updating all dependents.
 */

#ifndef COMMON_TYPES_H
#define COMMON_TYPES_H

#include <cstdint>
#include <cstddef>

namespace arp {
// ──────────────────────────────────────────────────────────────────────────────
// Error codes
// ──────────────────────────────────────────────────────────────────────────────
enum class ErrorCode : int32_t {
  OK = 0,
  NOT_INITIALIZED = -1,
  ALREADY_INITIALIZED = -2,
  INVALID_PARAMETER = -3,
  INVALID_STATE = -4,
  TIMEOUT = -5,
  BUSY = -6,
  IO_ERROR = -7,
  CRC_MISMATCH = -8,
  SIGNATURE_INVALID = -9,
  FLASH_CORRUPTED = -10,
  MEMORY_INSUFFICIENT = -11,
  UNSUPPORTED_VERSION = -12,
  FIRMWARE_MISMATCH = -13,
  MODEL_CORRUPTED = -14,
  REGRESSION_DETECTED = -15,
  RATE_LIMITED = -16,
  TRANSPORT_DISCONNECTED = -17,
  HARDWARE_FAULT = -18,
  UNKNOWN = -99
};

// ──────────────────────────────────────────────────────────────────────────────
// Sensor types
// ──────────────────────────────────────────────────────────────────────────────
enum class SensorType : uint8_t {
  IMU_6AXIS = 0x01,
  MICROPHONE_PDM = 0x02,
  TEMPERATURE = 0x03,
  HUMIDITY = 0x04,
  PRESSURE = 0x05,
  LIGHT = 0x06,
  HEART_RATE = 0x07,
  GPS = 0x08,
  PROXIMITY = 0x09,
  CUSTOM = 0xFF
};

enum class SensorSampleRate : uint8_t {
  RATE_1_HZ = 1,
  RATE_10_HZ = 10,
  RATE_25_HZ = 25,
  RATE_50_HZ = 50,
  RATE_100_HZ = 100,
  RATE_200_HZ = 200,
  RATE_1000_HZ = 1000
};

// ──────────────────────────────────────────────────────────────────────────────
// Radio types
// ──────────────────────────────────────────────────────────────────────────────
enum class RadioType : uint8_t {
  WIFI_STATION = 0x01,
  WIFI_AP = 0x02,
  BLE_CENTRAL = 0x03,
  BLE_PERIPHERAL = 0x04
};

enum class ConnectionState : uint8_t {
  DISCONNECTED = 0,
  CONNECTING = 1,
  CONNECTED = 2,
  DISCONNECTING = 3,
  ERROR = 4
};

// ──────────────────────────────────────────────────────────────────────────────
// Power states
// ──────────────────────────────────────────────────────────────────────────────
enum class PowerState : uint8_t {
  ACTIVE = 0,
  STANDBY = 1,
  IDLE = 2,
  HIBERNATE = 3
};

// ──────────────────────────────────────────────────────────────────────────────
// Agent types
// ──────────────────────────────────────────────────────────────────────────────
enum class AgentID : uint8_t {
  SENSOR = 0x01,
  INFERENCE = 0x02,
  VOICE = 0x03,
  CONNECTIVITY = 0x04,
  POWER = 0x05,
  LEARNING = 0x06,
  SECURITY = 0x07,
  LOGGING = 0x08,
  CUSTOM = 0xFF
};

// ──────────────────────────────────────────────────────────────────────────────
// Fault types
// ──────────────────────────────────────────────────────────────────────────────
enum class FaultType : uint32_t {
  NONE = 0,
  WATCHDOG = 1,
  STACK_OVERFLOW = 2,
  HEAP_CORRUPTION = 3,
  TFLITE_ABORT = 4,
  NINA_RESET_STORM = 5,
  FLASH_CORRUPTION = 6,
  UNKNOWN_FAULT = 99
};

// ──────────────────────────────────────────────────────────────────────────────
// Timestamp utilities
// ──────────────────────────────────────────────────────────────────────────────
using TimestampUs = uint64_t;  // Microsecond Unix timestamp
using TimestampS  = uint32_t;  // Second Unix timestamp

inline TimestampUs now_us() {
  // Implemented in kernel; placeholder here
  return 0;
}

inline TimestampS now_s() {
  return static_cast<TimestampS>(now_us() / 1000000ULL);
}

} // namespace arp

#endif // COMMON_TYPES_H
