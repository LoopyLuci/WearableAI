/**
 * @file ControlGraph.h
 * @brief Control graph types for self-modifying pipelines
 */

#ifndef SCRIPTING_CONTROLGRAPH_H
#define SCRIPTING_CONTROLGRAPH_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::scripting {

enum class NodeType : uint32_t {
  SENSOR_POLL      = 0x01,
  MODEL_INFERENCE  = 0x02,
  FORWARD          = 0x03,
  FILTER           = 0x04,
  ROUTE            = 0x05,
  ACTION           = 0x06,
  LOGGER           = 0x07,
  SLEEP            = 0x08,
  CUSTOM_SCRIPT    = 0x09
};

struct ControlNode {
  uint32_t node_id;
  NodeType type;
  uint32_t param_a;
  uint32_t param_b;
  uint32_t next_node_true;
  uint32_t next_node_false;
  uint32_t interval_ms;
  uint32_t flags;
};

struct ControlGraphHeader {
  static constexpr uint32_t MAGIC = 0x43474E48;  // "CGNH"
  uint32_t magic;
  uint32_t version;
  uint32_t entry_node_id;
  uint32_t node_count;
  uint32_t graph_crc32;
  TimestampS timestamp_unix;
  uint8_t  reserved[40];
  // Followed by node_count ControlNode records
};

static_assert(sizeof(ControlGraphHeader) == 64, "ControlGraphHeader size mismatch");

} // namespace arp::scripting

#endif // SCRIPTING_CONTROLGRAPH_H
