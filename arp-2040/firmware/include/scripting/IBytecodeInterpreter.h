/**
 * @file IBytecodeInterpreter.h
 * @brief Safe bytecode interpreter interface
 */
#ifndef SCRIPTING_IBYTECODEINTERPRETER_H
#define SCRIPTING_IBYTECODEINTERPRETER_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::scripting {

struct ScriptContext {
  // Runtime context provided to scripts
  uint32_t unix_timestamp_s;
  float    imu_accel[3];
  float    imu_gyro[3];
  float    audio_energy_db;
  bool     ble_connected;
  bool     wifi_connected;
  uint8_t  reserved[32];
};

struct ActionResult {
  uint32_t action_type;
  float    params[4];
};

class IBytecodeInterpreter {
public:
  virtual ~IBytecodeInterpreter() = default;

  /**
   * @brief Load bytecode from buffer
   */
  virtual ErrorCode load(const uint8_t* bytecode, size_t len) = 0;

  /**
   * @brief Execute loaded bytecode with given context
   * @param max_cycles Safety budget
   * @param out_action Result action (if any)
   */
  virtual ErrorCode execute(const ScriptContext& ctx, uint32_t max_cycles,
                            ActionResult* out_action) = 0;

  /**
   * @brief Validate bytecode without executing (static analysis)
   */
  virtual ErrorCode validate(const uint8_t* bytecode, size_t len,
                             char* out_error, size_t error_buf_len) = 0;

  virtual size_t max_stack_depth() const noexcept = 0;
  virtual uint32_t supported_opcodes() const noexcept = 0;
};

} // namespace arp::scripting
#endif // SCRIPTING_IBYTECODEINTERPRETER_H
