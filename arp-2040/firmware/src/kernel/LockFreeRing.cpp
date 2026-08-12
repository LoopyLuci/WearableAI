/**
 * @file LockFreeRing.cpp
 * @brief Lock-free ring buffer implementation
 *
 * Specializations for common types used in the firmware.
 */

#include "LockFreeRing.h"
#include <cstring>

namespace arp::kernel {

// Explicit template instantiations for common types
// (avoids linking issues on embedded targets)

// IMU sample ring: 128-sample buffer
using IMURing = LockFreeRing<IMUSample, 128>;

// Audio frame ring: 32-frame buffer
using AudioRing = LockFreeRing<AudioSample, 32>;

// Radio message ring: 16-message buffer
template<typename T, size_t N>
bool LockFreeRing<T, N>::push(const T& item) {
  size_t head = _head.load(std::memory_order_relaxed);
  size_t next = (head + 1) & _mask;
  if (next == _tail.load(std::memory_order_acquire)) {
    return false;  // Full
  }
  _buffer[head] = item;
  _head.store(next, std::memory_order_release);
  return true;
}

template<typename T, size_t N>
bool LockFreeRing<T, N>::pop(T& out_item) {
  size_t tail = _tail.load(std::memory_order_relaxed);
  if (tail == _head.load(std::memory_order_acquire)) {
    return false;  // Empty
  }
  out_item = _buffer[tail];
  _tail.store((tail + 1) & _mask, std::memory_order_release);
  return true;
}

template<typename T, size_t N>
size_t LockFreeRing<T, N>::available() const {
  size_t head = _head.load(std::memory_order_acquire);
  size_t tail = _tail.load(std::memory_order_acquire);
  return (head - tail) & _mask;
}

template<typename T, size_t N>
void LockFreeRing<T, N>::reset() {
  _head.store(0, std::memory_order_relaxed);
  _tail.store(0, std::memory_order_relaxed);
}

} // namespace arp::kernel
