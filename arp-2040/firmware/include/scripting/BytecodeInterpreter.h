/**
 * @file BytecodeInterpreter.h
 * @brief Safe bytecode interpreter implementation
 */

#ifndef SCRIPTING_BYTECODEINTERPRETER_H
#define SCRIPTING_BYTECODEINTERPRETER_H

#include "IBytecodeInterpreter.h"
#include "BytecodeOpcodes.h"
#include <cstdint>
#include <cstddef>
#include <cstring>

namespace arp::scripting {

static constexpr size_t MAX_STACK_DEPTH = 16;
static constexpr size_t DEFAULT_MAX_CYCLES = 1000;

class BytecodeInterpreter : public IBytecodeInterpreter {
public:
  BytecodeInterpreter();
  ~BytecodeInterpreter() override = default;

  ErrorCode load(const uint8_t* bytecode, size_t len) override;
  ErrorCode execute(const ScriptContext& ctx, uint32_t max_cycles,
                    ActionResult* out_action) override;
  ErrorCode validate(const uint8_t* bytecode, size_t len,
                     char* out_error, size_t error_buf_len) override;
  size_t max_stack_depth() const noexcept override { return MAX_STACK_DEPTH; }
  uint32_t supported_opcodes() const noexcept override { return 0x0001FFFF; }

private:
  uint8_t _bytecode[4096];
  size_t   _bytecode_len;
  uint32_t _opcode_count;

  float    _stack[MAX_STACK_DEPTH];
  int      _sp;  // Stack pointer (-1 = empty)
  uint32_t _pc;  // Program counter (byte offset into _bytecode)

  ErrorCode _execute_op(const uint8_t* op, const ScriptContext& ctx,
                        ActionResult* out_action, uint32_t* cycles_used);
};

} // namespace arp::scripting

#endif // SCRIPTING_BYTECODEINTERPRETER_H
