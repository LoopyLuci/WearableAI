/**
 * @file LogBuffer.h
 * @brief Lock-free circular log buffer for boot/self-test output
 *
 * Captures boot and test logs even if serial monitor attaches late.
 * Host can request a buffered dump via 'DUMP' command after reset.
 */
#ifndef ARP_LOG_BUFFER_H
#define ARP_LOG_BUFFER_H

#include <cstdint>
#include <cstddef>
#include <cstring>

namespace arp::kernel {

class LogBuffer {
public:
  static constexpr size_t CAPACITY = 4096;  // 4 KB circular buffer

  LogBuffer() = default;

  void write(const char* msg, size_t len) {
    if (len == 0) return;
    size_t free = CAPACITY - size();
    if (len > free) {
      // Overwrite oldest data to keep latest boot/test output
      _head = (_head + len - free) % CAPACITY;
    }
    for (size_t i = 0; i < len; i++) {
      _buffer[_tail] = msg[i];
      _tail = (_tail + 1) % CAPACITY;
      if (size() > CAPACITY) {
        _head = (_head + 1) % CAPACITY;
      }
    }
  }

  void write_line(const char* msg) {
    write(msg, std::strlen(msg));
    write("\n", 1);
  }

  // Return bytes available to read
  size_t size() const {
    if (_tail >= _head) return _tail - _head;
    return CAPACITY - _head + _tail;
  }

  // Read up to max_len bytes into out; returns bytes read
  size_t read(char* out, size_t max_len) {
    size_t avail = size();
    size_t to_read = (avail < max_len) ? avail : max_len;
    for (size_t i = 0; i < to_read; i++) {
      out[i] = _buffer[_head];
      _head = (_head + 1) % CAPACITY;
    }
    return to_read;
  }

  // Copy entire buffer to out, return total bytes copied
  size_t dump(char* out, size_t max_len) const {
    size_t total = size();
    size_t to_copy = (total < max_len) ? total : max_len;
    size_t idx = _head;
    for (size_t i = 0; i < to_copy; i++) {
      out[i] = _buffer[idx];
      idx = (idx + 1) % CAPACITY;
    }
    return to_copy;
  }

  void clear() {
    _head = 0;
    _tail = 0;
  }

private:
  char _buffer[CAPACITY]{};
  size_t _head = 0;
  size_t _tail = 0;
};

}  // namespace arp::kernel

#endif // ARP_LOG_BUFFER_H
