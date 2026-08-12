/**
 * @file ProtocolTypes.h
 * @brief Wire protocol types — frozen contract
 *
 * Device ↔ Mobile/Desktop communication protocol.
 * All messages are little-endian, 32-bit length-prefixed over TCP,
 * or chunked via BLE ATT MTU.
 */

#ifndef TRANSPORT_PROTOCOLTYPES_H
#define TRANSPORT_PROTOCOLTYPES_H

#include "common_types.h"
#include <cstdint>

namespace arp::transport {

// ──────────────────────────────────────────────────────────────────────────────
// Protocol version
// ──────────────────────────────────────────────────────────────────────────────
static constexpr uint8_t PROTOCOL_VERSION_MAJOR = 1;
static constexpr uint8_t PROTOCOL_VERSION_MINOR = 0;

// ──────────────────────────────────────────────────────────────────────────────
// Message types (device ↔ server)
// ──────────────────────────────────────────────────────────────────────────────
enum class MessageType : uint8_t {
  // Device → Server
  VOICE_EVENT        = 0x01,  // KWS result
  SENSOR_SNAPSHOT    = 0x02,  // Compressed context state
  IMU_BUFFER         = 0x03,  // IMU window
  AUDIO_BLOB         = 0x04,  // Compressed audio
  ALERT              = 0x05,  // Emergency alert
  MODEL_DELTA        = 0x06,  // Federated learning delta
  HEARTBEAT          = 0x07,  // Keep-alive
  STATUS_RESPONSE    = 0x08,  // Response to STATUS query

  // Server → Device
  COMMAND            = 0x81,  // Structured intent
  MODEL_PUSH         = 0x82,  // Full model OTA
  CONFIG_PUSH        = 0x83,  // Config update
  GRAPH_PUSH         = 0x84,  // Control graph update
  SCRIPT_PUSH        = 0x85,  // Bytecode script
  TIME_SYNC          = 0x86,  // Timestamp correction
  STATUS_QUERY       = 0x87,  // Request device status
  ROLLBACK           = 0x88   // Rollback request
};

// ──────────────────────────────────────────────────────────────────────────────
// Message framing (TCP)
// ──────────────────────────────────────────────────────────────────────────────
struct MessageHeader {
  uint8_t   version_major;
  uint8_t   version_minor;
  uint8_t   type;
  uint16_t  payload_len;  // Little-endian
  uint32_t  timestamp_s;  // Little-endian
  uint32_t  message_id;   // Monotonic, for dedup
};

static constexpr size_t MESSAGE_HEADER_SIZE = 12;
static constexpr size_t MAX_PAYLOAD_SIZE   = 512;

// ──────────────────────────────────────────────────────────────────────────────
// Specific message payloads
// ──────────────────────────────────────────────────────────────────────────────

// VOICE_EVENT payload
struct VoiceEventPayload {
  uint32_t timestamp_us;
  float    confidence;
  uint8_t  keyword_len;
  char     keyword[16];  // Null-terminated
};

// SENSOR_SNAPSHOT payload
struct SensorSnapshotPayload {
  uint32_t timestamp_us;
  float    accel_mg[3];
  float    gyro_mdps[3];
  float    temperature_c;
  float    audio_energy_db;
  float    pressure_hpa;
  float    humidity_pct;
  float    light_lux;
  uint8_t  activity_type;  // 0=still, 1=walking, 2=running, 3=unknown
  uint8_t  reserved[3];
};

// ALERT payload
struct AlertPayload {
  uint32_t timestamp_us;
  uint32_t alert_type;   // 1=fall, 2=panic, 3=low_battery, 4=medical
  float    latitude;
  float    longitude;
  char     message[64];
};

// COMMAND payload (server → device)
struct CommandPayload {
  uint32_t intent_id;
  uint32_t target_agent;
  uint32_t action;
  float    params[4];
  char     text_params[64];
};

// MODEL_DELTA payload
struct ModelDeltaPayload {
  uint32_t model_id;
  uint32_t from_version;
  uint32_t to_version;
  uint32_t delta_len;
  uint8_t  delta_signature[64];  // ECDSA signature
};

// TIME_SYNC payload
struct TimeSyncPayload {
  uint32_t server_timestamp_s;
  int32_t  round_trip_ms;
};

} // namespace arp::transport

#endif // TRANSPORT_PROTOCOLTYPES_H
