/**
 * @file Task.h
 * @brief FreeRTOS task wrapper implementation
 */

#ifndef KERNEL_TASK_H
#define KERNEL_TASK_H

#include "ITask.h"
#include <cstdint>
#include <cstring>

extern "C" {
#include "FreeRTOS.h"
#include "task.h"
}

namespace arp::kernel {

class Task : public ITask {
public:
  using EntryPoint = void(*)(void*);

  static Task* create(EntryPoint fn, void* param,
                      const char* name, uint32_t stack_words,
                      Priority priority, CoreNumber core) {
    Task* t = new Task(fn, param, name, stack_words, priority, core);
    BaseType_t result = xTaskCreate(
      _task_entry, name, stack_words, t, priority, &t->_handle
    );
    if (result != pdPASS) {
      delete t;
      return nullptr;
    }
    t->_task_id = reinterpret_cast<uintptr_t>(t->_handle);
    return t;
  }

  ~Task() override = default;

  TaskID id() const noexcept override { return _task_id; }
  const char* name() const noexcept override { return _name; }
  Priority priority() const noexcept override { return _priority; }
  CoreNumber core() const noexcept override { return _core; }
  bool is_running() const noexcept override { return _running; }

  ErrorCode start() override {
    vTaskResume(_handle);
    _running = true;
    return ErrorCode::OK;
  }

  ErrorCode suspend() override {
    vTaskSuspend(_handle);
    _running = false;
    return ErrorCode::OK;
  }

  ErrorCode resume() override {
    vTaskResume(_handle);
    _running = true;
    return ErrorCode::OK;
  }

  ErrorCode remove() override {
    vTaskDelete(_handle);
    _running = false;
    return ErrorCode::OK;
  }

  ErrorCode notify(uint32_t bits) override {
    BaseType_t higher = pdFALSE;
    xTaskNotify(_handle, bits, eSetBits, &higher);
    return ErrorCode::OK;
  }

  uint32_t wait_notification(uint32_t bits, uint32_t timeout_ms) override {
    uint32_t received = 0;
    TickType_t ticks = (timeout_ms == UINT32_MAX) ? portMAX_DELAY
                                                   : pdMS_TO_TICKS(timeout_ms);
    xTaskNotifyWait(0x00, 0xFFFFFFFF, &received, ticks);
    return received & bits;
  }

private:
  EntryPoint _fn;
  void* _param;
  char _name[32];
  uint32_t _stack_words;
  Priority _priority;
  CoreNumber _core;
  TaskHandle_t _handle = nullptr;
  TaskID _task_id = 0;
  bool _running = true;

  Task(EntryPoint fn, void* param, const char* name, uint32_t stack_words,
       Priority priority, CoreNumber core)
    : _fn(fn), _param(param), _stack_words(stack_words),
      _priority(priority), _core(core) {
    strncpy(_name, name, sizeof(_name) - 1);
    _name[sizeof(_name) - 1] = '\0';
  }

  static void _task_entry(void* param) {
    Task* self = static_cast<Task*>(param);
    self->_fn(self->_param);
    vTaskDelete(nullptr);
  }
};

} // namespace arp::kernel

#endif // KERNEL_TASK_H
