/**
 * @file BytecodeInterpreter.cpp
 * @brief Bytecode interpreter implementation
 */

#include "BytecodeInterpreter.h"
#include <cstdio>
#include <cstring>
#include <cmath>

namespace arp::scripting {

BytecodeInterpreter::BytecodeInterpreter()
  : _bytecode_len(0), _opcode_count(0), _sp(-1), _pc(0) {
  memset(_bytecode, 0, sizeof(_bytecode));
  memset(_stack, 0, sizeof(_stack));
}

ErrorCode BytecodeInterpreter::load(const uint8_t* bytecode, size_t len) {
  if (!bytecode || len == 0 || len > sizeof(_bytecode))
    return ErrorCode::INVALID_PARAMETER;

  memcpy(_bytecode, bytecode, len);
  _bytecode_len = len;

  // Count opcodes (each opcode is at least 1 byte)
  _opcode_count = 0;
  size_t i = 0;
  while (i < len) {
    _opcode_count++;
    uint8_t op = _bytecode[i];
    size_t op_len = 1;
    switch (static_cast<OpCode>(op)) {
      case OpCode::OP_PUSH_IMM:   op_len += 4; break;
      case OpCode::OP_LOAD_VAR:   op_len += 1; break;
      case OpCode::OP_STORE_VAR:  op_len += 1; break;
      case OpCode::OP_JUMP_IF:    op_len += 4; break;
      case OpCode::OP_CALL_NODE:  op_len += 4; break;
      case OpCode::OP_SEND_BLE:   op_len += 2; break;
      case OpCode::OP_LOG:        op_len += 4; break;
      case OpCode::OP_SET_INTERVAL: op_len += 4; break;
      default: break;
    }
    i += op_len;
  }
  return ErrorCode::OK;
}

ErrorCode BytecodeInterpreter::validate(const uint8_t* bytecode, size_t len,
                                         char* out_error, size_t error_buf_len) {
  if (!bytecode || len == 0) {
    snprintf(out_error, error_buf_len, "Empty bytecode");
    return ErrorCode::INVALID_PARAMETER;
  }
  if (len > 4096) {
    snprintf(out_error, error_buf_len, "Bytecode too large: %zu > 4096", len);
    return ErrorCode::INVALID_PARAMETER;
  }

  size_t i = 0;
  while (i < len) {
    uint8_t op = bytecode[i];
    if (op == 0 || op > static_cast<uint8_t>(OpCode::OP_COUNT)) {
      snprintf(out_error, error_buf_len, "Invalid opcode 0x%02X at offset %zu", op, i);
      return ErrorCode::INVALID_PARAMETER;
    }
    size_t op_len = 1;
    switch (static_cast<OpCode>(op)) {
      case OpCode::OP_PUSH_IMM:   op_len += 4; break;
      case OpCode::OP_LOAD_VAR:   op_len += 1; break;
      case OpCode::OP_STORE_VAR:  op_len += 1; break;
      case OpCode::OP_JUMP_IF:    op_len += 4; break;
      case OpCode::OP_CALL_NODE:  op_len += 4; break;
      case OpCode::OP_SEND_BLE:   op_len += 2; break;
      case OpCode::OP_LOG:        op_len += 4; break;
      case OpCode::OP_SET_INTERVAL: op_len += 4; break;
      default: break;
    }
    i += op_len;
  }
  return ErrorCode::OK;
}

ErrorCode BytecodeInterpreter::execute(const ScriptContext& ctx, uint32_t max_cycles,
                                        ActionResult* out_action) {
  if (_bytecode_len == 0) return ErrorCode::NOT_INITIALIZED;
  if (!out_action) return ErrorCode::INVALID_PARAMETER;

  _sp = -1;
  _pc = 0;
  uint32_t cycles = 0;
  const uint32_t cycle_budget = (max_cycles > 0) ? max_cycles : DEFAULT_MAX_CYCLES;

  memset(out_action, 0, sizeof(ActionResult));

  while (_pc < _bytecode_len && cycles < cycle_budget) {
    uint8_t op = _bytecode[_pc];
    if (op == 0 || op > static_cast<uint8_t>(OpCode::OP_COUNT)) {
      return ErrorCode::UNKNOWN;  // Invalid opcode
    }

    ErrorCode err = _execute_op(&_bytecode[_pc], ctx, out_action, &cycles);
    if (err != ErrorCode::OK) return err;
  }

  if (cycles >= cycle_budget) {
    return ErrorCode::TIMEOUT;  // Cycle budget exhausted
  }
  return ErrorCode::OK;
}

ErrorCode BytecodeInterpreter::_execute_op(const uint8_t* op, const ScriptContext& ctx,
                                            ActionResult* out_action, uint32_t* cycles) {
  OpCode opcode = static_cast<OpCode>(op[0]);
  (*cycles)++;

  switch (opcode) {
    case OpCode::OP_POP: {
      if (_sp < 0) return ErrorCode::INVALID_STATE;
      _sp--;
      _pc += 1;
      break;
    }

    case OpCode::OP_PUSH_IMM: {
      if (_sp >= MAX_STACK_DEPTH - 1) return ErrorCode::MEMORY_INSUFFICIENT;
      float val;
      memcpy(&val, &op[1], 4);
      _sp++;
      _stack[_sp] = val;
      _pc += 5;
      break;
    }

    case OpCode::OP_LOAD_VAR: {
      if (_sp >= MAX_STACK_DEPTH - 1) return ErrorCode::MEMORY_INSUFFICIENT;
      ScriptVar var = static_cast<ScriptVar>(op[1]);
      float val = 0.0f;
      switch (var) {
        case ScriptVar::VAR_UNIX_TIMESTAMP: val = static_cast<float>(ctx.unix_timestamp_s); break;
        case ScriptVar::VAR_IMU_ACCEL_X:    val = ctx.imu_accel[0]; break;
        case ScriptVar::VAR_IMU_ACCEL_Y:    val = ctx.imu_accel[1]; break;
        case ScriptVar::VAR_IMU_ACCEL_Z:    val = ctx.imu_accel[2]; break;
        case ScriptVar::VAR_AUDIO_ENERGY:   val = ctx.audio_energy_db; break;
        case ScriptVar::VAR_BATTERY_PCT:    val = 85.0f; break;  // Mock
        case ScriptVar::VAR_BLE_CONNECTED:  val = ctx.ble_connected ? 1.0f : 0.0f; break;
        default: val = 0.0f; break;
      }
      _sp++;
      _stack[_sp] = val;
      _pc += 2;
      break;
    }

    case OpCode::OP_STORE_VAR: {
      if (_sp < 0) return ErrorCode::INVALID_STATE;
      ScriptVar var = static_cast<ScriptVar>(op[1]);
      float val = _stack[_sp];
      _sp--;
      // In production, store to context or variable table
      (void)var; (void)val;
      _pc += 2;
      break;
    }

    case OpCode::OP_ADD: {
      if (_sp < 1) return ErrorCode::INVALID_STATE;
      float b = _stack[_sp]; _sp--;
      float a = _stack[_sp];
      _stack[_sp] = a + b;
      _pc += 1;
      break;
    }

    case OpCode::OP_SUB: {
      if (_sp < 1) return ErrorCode::INVALID_STATE;
      float b = _stack[_sp]; _sp--;
      float a = _stack[_sp];
      _stack[_sp] = a - b;
      _pc += 1;
      break;
    }

    case OpCode::OP_MUL: {
      if (_sp < 1) return ErrorCode::INVALID_STATE;
      float b = _stack[_sp]; _sp--;
      float a = _stack[_sp];
      _stack[_sp] = a * b;
      _pc += 1;
      break;
    }

    case OpCode::OP_DIV: {
      if (_sp < 1) return ErrorCode::INVALID_STATE;
      float b = _stack[_sp]; _sp--;
      float a = _stack[_sp];
      if (b == 0.0f) return ErrorCode::INVALID_PARAMETER;
      _stack[_sp] = a / b;
      _pc += 1;
      break;
    }

    case OpCode::OP_CMP_EQ: {
      if (_sp < 1) return ErrorCode::INVALID_STATE;
      float b = _stack[_sp]; _sp--;
      float a = _stack[_sp];
      _stack[_sp] = (a == b) ? 1.0f : 0.0f;
      _pc += 1;
      break;
    }

    case OpCode::OP_JUMP_IF: {
      if (_sp < 1) return ErrorCode::INVALID_STATE;
      float cond = _stack[_sp]; _sp--;
      uint32_t target;
      memcpy(&target, &op[1], 4);
      if (cond != 0.0f) {
        _pc = target;
      } else {
        _pc += 5;
      }
      break;
    }

    case OpCode::OP_CALL_NODE: {
      uint32_t node_id;
      memcpy(&node_id, &op[1], 4);
      // In production, dispatch to control graph node
      (void)node_id;
      _pc += 5;
      break;
    }

    case OpCode::OP_SEND_BLE: {
      uint16_t msg_type;
      memcpy(&msg_type, &op[1], 2);
      // In production, queue BLE notification
      (void)msg_type;
      _pc += 3;
      break;
    }

    case OpCode::OP_LOG: {
      uint32_t value;
      memcpy(&value, &op[1], 4);
      // In production, write to flash ring buffer
      (void)value;
      _pc += 5;
      break;
    }

    case OpCode::OP_SET_INTERVAL: {
      uint32_t interval_ms;
      memcpy(&interval_ms, &op[1], 4);
      // In production, update current node's interval
      (void)interval_ms;
      _pc += 5;
      break;
    }

    case OpCode::OP_HALT: {
      return ErrorCode::OK;
    }

    default:
      return ErrorCode::UNKNOWN;
  }

  return ErrorCode::OK;
}

} // namespace arp::scripting
