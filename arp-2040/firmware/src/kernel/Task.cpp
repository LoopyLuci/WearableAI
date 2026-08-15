/**
 * @file Task.cpp
 * @brief Cooperative task wrapper implementation
 */

#include "ITask.h"
#include <cstdint>
#include <cstring>

namespace arp::kernel {

class Task : public ITask {
public:
  using EntryPoint = void(*)(void*);

  static Task* create(EntryPoint fn, void* param,
                      const char* name, uint32_t stack_words,
                      Priority priority, CoreNumber core) {
    Task* t = new Task(fn, param, name, stack_words, priority, core);
    t->_task_id = reinterpret_cast<uintptr_t>(t);
    t->_running = true;
    return t;
  }

  ~Task() override = default;

  TaskID id() const noexcept override { return _task_id; }
  const char* name() const noexcept override { return _name; }
  Priority priority() const noexcept override { return _priority; }
  CoreNumber core() const noexcept override { return _core; }
  bool is_running() const noexcept override { return _running; }

  ErrorCode start() override {
    _running = true;
    return ErrorCode::OK;
  }

  ErrorCode suspend() override {
    _running = false;
    return ErrorCode::OK;
  }

  ErrorCode resume() override {
    _running = true;
    return ErrorCode::OK;
  }

  ErrorCode remove() override {
    _running = false;
    return ErrorCode::OK;
  }

  ErrorCode notify(uint32_t bits) override {
    (void)bits;
    return ErrorCode::OK;
  }

  uint32_t wait_notification(uint32_t bits, uint32_t timeout_ms) override {
    (void)bits;
    (void)timeout_ms;
    return 0;
  }

private:
  EntryPoint _fn;
  void* _param;
  char _name[32];
  uint32_t _stack_words;
  Priority _priority;
  CoreNumber _core;
  TaskID _task_id = 0;
  bool _running = true;

  Task(EntryPoint fn, void* param, const char* name, uint32_t stack_words,
       Priority priority, CoreNumber core)
    : _fn(fn), _param(param), _stack_words(stack_words),
      _priority(priority), _core(core) {
    strncpy(_name, name, sizeof(_name) - 1);
    _name[sizeof(_name) - 1] = '\0';
  }
};

} // namespace arp::kernel
