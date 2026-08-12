/**
 * @file ITask.h
 * @brief FreeRTOS task wrapper interface
 */
#ifndef KERNEL_ITASK_H
#define KERNEL_ITASK_H

#include "common_types.h"
#include <cstdint>

namespace arp::kernel {

using TaskID = uint32_t;
using Priority = uint8_t;
using CoreNumber = uint8_t;

class ITask {
public:
  virtual ~ITask() = default;
  virtual TaskID id() const noexcept = 0;
  virtual const char* name() const noexcept = 0;
  virtual ErrorCode start() = 0;
  virtual ErrorCode suspend() = 0;
  virtual ErrorCode resume() = 0;
  virtual ErrorCode remove() = 0;
  virtual ErrorCode notify(uint32_t bits) = 0;
  virtual uint32_t wait_notification(uint32_t bits, uint32_t timeout_ms) = 0;
  virtual Priority priority() const noexcept = 0;
  virtual CoreNumber core() const noexcept = 0;
  virtual bool is_running() const noexcept = 0;
};

} // namespace arp::kernel
#endif // KERNEL_ITASK_H
