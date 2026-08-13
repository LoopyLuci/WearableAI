/**
 * @file LockFreeRing.h
 * @brief Lock-free ring buffer template for ISR-to-task communication
 */

#ifndef KERNEL_LOCKFREERING_H
#define KERNEL_LOCKFREERING_H

#include "common_types.h"
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace arp::kernel {

template<typename T, size_t N>
class LockFreeRing {
  static_assert((N & (N-1)) == 0, "Capacity must be power of 2");
public:
  LockFreeRing() : _head(0), _tail(0) {}
  ~LockFreeRing() = default;

  bool push(const T& item) {
    size_t head = _head.load(std::memory_order_relaxed);
    size_t next = (head + 1) & _mask;
    if (next == _tail.load(std::memory_order_acquire)) {
      return false;  // Full
    }
    _buffer[head] = item;
    _head.store(next, std::memory_order_release);
    return true;
  }

  bool pop(T& out_item) {
    size_t tail = _tail.load(std::memory_order_relaxed);
    if (tail == _head.load(std::memory_order_acquire)) {
      return false;  // Empty
    }
    out_item = _buffer[tail];
    _tail.store((tail + 1) & _mask, std::memory_order_release);
    return true;
  }

  size_t available() const {
    return (_head.load(std::memory_order_acquire) - _tail.load(std::memory_order_relaxed)) & _mask;
  }

  void reset() {
    _head.store(0, std::memory_order_relaxed);
    _tail.store(0, std::memory_order_release);
  }

private:
  alignas(std::atomic<T>) T _buffer[N];
  std::atomic<size_t> _head;
  std::atomic<size_t> _tail;
  static constexpr size_t _mask = N - 1;
};

} // namespace arp::kernel

#endif // KERNEL_LOCKFREERING_H
