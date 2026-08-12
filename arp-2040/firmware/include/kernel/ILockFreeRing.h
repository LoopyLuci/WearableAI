/**
 * @file ILockFreeRing.h
 * @brief Lock-free ring buffer for ISR-to-task communication
 */
#ifndef KERNEL_ILOCKFREERING_H
#define KERNEL_ILOCKFREERING_H

#include "common_types.h"
#include <cstddef>
#include <cstdint>

namespace arp::kernel {

template<typename T, size_t N>
class ILockFreeRing {
  static_assert((N & (N-1)) == 0, "Capacity must be power of 2");
public:
  virtual ~ILockFreeRing() = default;
  virtual bool push(const T& item) = 0;           // ISR-safe
  virtual bool pop(T& out_item) = 0;              // Task-side
  virtual size_t available() const = 0;           // Approximate count
  virtual void reset() = 0;
};

} // namespace arp::kernel
#endif // KERNEL_ILOCKFREERING_H
