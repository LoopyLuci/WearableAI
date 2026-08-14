#ifndef KERNEL_IAGENTREGISTRY_H
#define KERNEL_IAGENTREGISTRY_H

#include "common_types.h"
#include <vector>
#include <cstdint>

namespace arp::kernel {

struct AgentStatus {
  AgentID id;
  const char* name;
  bool running;
  uint32_t restart_count;
  uint32_t uptime_seconds;
};

class IAgentRegistry {
public:
  virtual ~IAgentRegistry() = default;
  virtual ErrorCode register_agent(AgentID id, const char* name) = 0;
  virtual ErrorCode unregister_agent(AgentID id) = 0;
  virtual ErrorCode restart_agent(AgentID id) = 0;
  virtual ErrorCode pause_all() = 0;
  virtual ErrorCode resume_all() = 0;
  virtual std::vector<AgentStatus> list_all() const = 0;
};

} // namespace arp::kernel
#endif // KERNEL_IAGENTREGISTRY_H
