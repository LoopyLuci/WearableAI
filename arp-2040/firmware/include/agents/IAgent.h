/**
 * @file IAgent.h
 * @brief Agent interface — every agent satisfies this
 */
#ifndef AGENTS_IAGENT_H
#define AGENTS_IAGENT_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::agents {

class IAgent {
public:
  virtual ~IAgent() = default;

  virtual AgentID id() const noexcept = 0;
  virtual const char* name() const noexcept = 0;

  virtual ErrorCode start() = 0;
  virtual ErrorCode stop() = 0;
  virtual ErrorCode restart() = 0;

  virtual ErrorCode set_control_graph(const uint8_t* graph_data, size_t graph_len) = 0;
  virtual ErrorCode get_control_graph(uint8_t* out_buffer, size_t max_len,
                                      size_t* out_len) const = 0;

  virtual ErrorCode self_test() = 0;
  virtual uint32_t restart_count() const noexcept = 0;
};

} // namespace arp::agents
#endif // AGENTS_IAGENT_H
