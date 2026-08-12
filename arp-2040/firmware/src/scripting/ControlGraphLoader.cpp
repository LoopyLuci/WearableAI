/**
 * @file ControlGraphLoader.cpp
 * @brief Control graph loader implementation
 */

#include "ControlGraphLoader.h"
#include <cstring>
#include <cstdio>

namespace arp::scripting {

ControlGraphLoader::ControlGraphLoader()
  : _graph(nullptr), _graph_buffer(nullptr), _buffer_size(0) {}

const ControlGraphHeader* ControlGraphLoader::load(const uint8_t* data, size_t len) {
  if (!data || len < sizeof(ControlGraphHeader)) return nullptr;

  // Allocate buffer (in production, this points into QSPI XIP)
  if (_graph_buffer) delete[] _graph_buffer;
  _graph_buffer = new uint8_t[len];
  memcpy(_graph_buffer, data, len);
  _buffer_size = len;

  ErrorCode err = _parse_and_validate(data, len);
  if (err != ErrorCode::OK) {
    delete[] _graph_buffer;
    _graph_buffer = nullptr;
    _graph = nullptr;
    return nullptr;
  }

  return _graph;
}

const ControlNode* ControlGraphLoader::get_node(uint32_t node_id) const {
  if (!_graph) return nullptr;
  const uint8_t* base = reinterpret_cast<const uint8_t*>(_graph) + sizeof(ControlGraphHeader);
  for (uint32_t i = 0; i < _graph->node_count; i++) {
    const ControlNode* node = reinterpret_cast<const ControlNode*>(base + i * sizeof(ControlNode));
    if (node->node_id == node_id) return node;
  }
  return nullptr;
}

const ControlNode* ControlGraphLoader::entry_node() const {
  if (!_graph) return nullptr;
  return get_node(_graph->entry_node_id);
}

ErrorCode ControlGraphLoader::validate() const {
  if (!_graph) return ErrorCode::NOT_INITIALIZED;

  // Verify magic
  if (_graph->magic != ControlGraphHeader::MAGIC) {
    return ErrorCode::FIRMWARE_MISMATCH;
  }

  // Verify entry node exists
  if (get_node(_graph->entry_node_id) == nullptr) {
    return ErrorCode::INVALID_PARAMETER;
  }

  // Verify all node references are valid (no dangling next pointers)
  const uint8_t* base = reinterpret_cast<const uint8_t*>(_graph) + sizeof(ControlGraphHeader);
  for (uint32_t i = 0; i < _graph->node_count; i++) {
    const ControlNode* node = reinterpret_cast<const ControlNode*>(base + i * sizeof(ControlNode));
    if (node->next_node_true != 0xFFFFFFFF && get_node(node->next_node_true) == nullptr) {
      return ErrorCode::INVALID_PARAMETER;
    }
    if (node->next_node_false != 0xFFFFFFFF && get_node(node->next_node_false) == nullptr) {
      return ErrorCode::INVALID_PARAMETER;
    }
  }

  return ErrorCode::OK;
}

void ControlGraphLoader::unload() {
  if (_graph_buffer) {
    delete[] _graph_buffer;
    _graph_buffer = nullptr;
  }
  _graph = nullptr;
  _buffer_size = 0;
}

ErrorCode ControlGraphLoader::_parse_and_validate(const uint8_t* data, size_t len) {
  if (len < sizeof(ControlGraphHeader)) return ErrorCode::INVALID_PARAMETER;

  const ControlGraphHeader* hdr = reinterpret_cast<const ControlGraphHeader*>(data);

  if (hdr->magic != ControlGraphHeader::MAGIC) {
    return ErrorCode::FIRMWARE_MISMATCH;
  }

  if (hdr->node_count == 0) {
    return ErrorCode::INVALID_PARAMETER;
  }

  size_t expected_size = sizeof(ControlGraphHeader) + hdr->node_count * sizeof(ControlNode);
  if (len < expected_size) {
    return ErrorCode::INVALID_PARAMETER;
  }

  _graph = reinterpret_cast<ControlGraphHeader*>(_graph_buffer);
  return validate();
}

} // namespace arp::scripting
