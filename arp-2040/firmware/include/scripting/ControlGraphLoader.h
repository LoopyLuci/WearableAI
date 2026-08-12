/**
 * @file ControlGraphLoader.h
 * @brief Control graph loader — atomic hot-reload of agent pipelines
 */

#ifndef SCRIPTING_CONTROLGRAPHLOADER_H
#define SCRIPTING_CONTROLGRAPHLOADER_H

#include "ControlGraph.h"
#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::scripting {

class ControlGraphLoader {
public:
  ControlGraphLoader();
  ~ControlGraphLoader() = default;

  /**
   * @brief Load a control graph from a buffer
   * @param data Binary graph data
   * @param len Length of data
   * @return Pointer to loaded graph header, or nullptr on error
   */
  const ControlGraphHeader* load(const uint8_t* data, size_t len);

  /**
   * @brief Get the current live graph
   */
  const ControlGraphHeader* get_graph() const { return _graph; }

  /**
   * @brief Get a specific node by ID
   */
  const ControlNode* get_node(uint32_t node_id) const;

  /**
   * @brief Get the entry node
   */
  const ControlNode* entry_node() const;

  /**
   * @brief Validate graph integrity
   */
  ErrorCode validate() const;

  /**
   * @brief Unload current graph
   */
  void unload();

private:
  ControlGraphHeader* _graph;
  uint8_t* _graph_buffer;
  size_t   _buffer_size;

  ErrorCode _parse_and_validate(const uint8_t* data, size_t len);
};

} // namespace arp::scripting

#endif // SCRIPTING_CONTROLGRAPHLOADER_H
