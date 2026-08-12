/**
 * @file AgentRegistry.h
 * @brief Central agent registry implementation
 */

#ifndef KERNEL_AGENTREGISTRY_H
#define KERNEL_AGENTREGISTRY_H

#include "IAgentRegistry.h"
#include "agents/IAgent.h"
#include <vector>
#include <cstring>

namespace arp::kernel {

class AgentRegistry : public IAgentRegistry {
public:
  ErrorCode register_agent(AgentID id, const char* name) override {
    if (_find(id) != -1) return ErrorCode::ALREADY_INITIALIZED;
    Entry e{};
    e.id = id;
    strncpy(e.name, name, sizeof(e.name) - 1);
    e.name[sizeof(e.name) - 1] = '\0';
    e.running = false;
    e.restart_count = 0;
    _entries.push_back(e);
    return ErrorCode::OK;
  }

  ErrorCode unregister_agent(AgentID id) override {
    int idx = _find(id);
    if (idx == -1) return ErrorCode::NOT_INITIALIZED;
    _entries.erase(_entries.begin() + idx);
    return ErrorCode::OK;
  }

  ErrorCode restart_agent(AgentID id) override {
    int idx = _find(id);
    if (idx == -1) return ErrorCode::NOT_INITIALIZED;
    _entries[idx].restart_count++;
    return ErrorCode::OK;
  }

  ErrorCode pause_all() override {
    for (auto& e : _entries) e.running = false;
    return ErrorCode::OK;
  }

  ErrorCode resume_all() override {
    for (auto& e : _entries) e.running = true;
    return ErrorCode::OK;
  }

  std::vector<AgentStatus> list_all() const override {
    std::vector<AgentStatus> result;
    for (const auto& e : _entries) {
      AgentStatus s{};
      s.id = e.id;
      s.name = e.name;
      s.running = e.running;
      s.restart_count = e.restart_count;
      s.uptime_seconds = 0;
      result.push_back(s);
    }
    return result;
  }

private:
  struct Entry {
    AgentID id;
    char name[32];
    bool running;
    uint32_t restart_count;
  };

  std::vector<Entry> _entries;

  int _find(AgentID id) const {
    for (size_t i = 0; i < _entries.size(); i++) {
      if (_entries[i].id == id) return static_cast<int>(i);
    }
    return -1;
  }
};

} // namespace arp::kernel
#endif // KERNEL_AGENTREGISTRY_H
