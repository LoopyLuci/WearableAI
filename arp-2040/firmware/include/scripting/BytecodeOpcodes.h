/**
 * @file BytecodeOpcodes.h
 * @brief Bytecode interpreter opcodes and format
 */

#ifndef SCRIPTING_BYTECODEOPCODES_H
#define SCRIPTING_BYTECODEOPCODES_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::scripting {

enum class OpCode : uint8_t {
  OP_POP           = 0x01,
  OP_PUSH_IMM      = 0x02,
  OP_LOAD_VAR      = 0x03,
  OP_STORE_VAR     = 0x04,
  OP_ADD           = 0x05,
  OP_SUB           = 0x06,
  OP_MUL           = 0x07,
  OP_DIV           = 0x08,
  OP_CMP_EQ        = 0x09,
  OP_CMP_GT        = 0x0A,
  OP_CMP_LT        = 0x0B,
  OP_JUMP_IF       = 0x0C,
  OP_CALL_NODE     = 0x0D,
  OP_SEND_BLE      = 0x0E,
  OP_LOG           = 0x0F,
  OP_SET_INTERVAL  = 0x10,
  OP_HALT          = 0x11,
  OP_COUNT         = 0x12
};

enum class ScriptVar : uint8_t {
  VAR_UNIX_TIMESTAMP = 0x01,
  VAR_IMU_ACCEL_X    = 0x02,
  VAR_IMU_ACCEL_Y    = 0x03,
  VAR_IMU_ACCEL_Z    = 0x04,
  VAR_IMU_GYRO_X     = 0x05,
  VAR_IMU_GYRO_Y     = 0x06,
  VAR_IMU_GYRO_Z     = 0x07,
  VAR_AUDIO_ENERGY   = 0x08,
  VAR_BATTERY_PCT    = 0x09,
  VAR_BLE_CONNECTED  = 0x0A,
  VAR_WIFI_CONNECTED = 0x0B,
  VAR_ALARM_TIME     = 0x0C,
  VAR_CUSTOM_1       = 0xF0,
  VAR_CUSTOM_2       = 0xF1,
  VAR_CUSTOM_3       = 0xF2
};

struct ScriptHeader {
  static constexpr uint32_t MAGIC = 0x53435250;  // "SCRP"
  uint32_t magic;
  uint32_t version;
  uint32_t opcode_count;
  uint32_t max_cycles;
  uint32_t script_crc;
  uint32_t flags;
  uint8_t  reserved[40];
};

static_assert(sizeof(ScriptHeader) == 64, "ScriptHeader size mismatch");

} // namespace arp::scripting

#endif // SCRIPTING_BYTECODEOPCODES_H
