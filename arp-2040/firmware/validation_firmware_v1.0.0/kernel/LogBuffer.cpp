/**
 * @file LogBuffer.cpp
 * @brief Lock-free circular log buffer for boot/self-test output
 */
#include "LogBuffer.h"
#include <cstring>

namespace arp::kernel {

void LogBuffer::write(const char* msg, size_t len) {
  if (len == 0) return;
  size_t free = CAPACITY - size();
  if (len > free) {
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

void LogBuffer::write_line(const char* msg) {
  write(msg, std::strlen(msg));
  write("\n", 1);
}

size_t LogBuffer::read(char* out, size_t max_len) {
  size_t avail = size();
  size_t to_read = (avail < max_len) ? avail : max_len;
  for (size_t i = 0; i < to_read; i++) {
    out[i] = _buffer[_head];
    _head = (_head + 1) % CAPACITY;
  }
  return to_read;
}

size_t LogBuffer::dump(char* out, size_t max_len) const {
  size_t total = size();
  size_t to_copy = (total < max_len) ? total : max_len;
  size_t idx = _head;
  for (size_t i = 0; i < to_copy; i++) {
    out[i] = _buffer[idx];
    idx = (idx + 1) % CAPACITY;
  }
  return to_copy;
}

void LogBuffer::clear() {
  _head = 0;
  _tail = 0;
}

}  // namespace arp::kernel
