/**
 * @file IActuator.h
 * @brief Actuator interface — frozen contract
 */

#ifndef HAL_IACTUATOR_H
#define HAL_IACTUATOR_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

struct VibrationConfig {
  uint16_t duration_ms;
  uint8_t  intensity_pct;  // 0-100
  uint8_t  pattern;         // 0=single, 1=double, 2=triple, 3=heartbeat
};

class IActuator {
public:
  virtual ~IActuator() = default;

  // ── LED ────────────────────────────────────────────────────────────────────
  virtual ErrorCode led_set_rgb(uint8_t r, uint8_t g, uint8_t b) = 0;
  virtual ErrorCode led_set_brightness(uint8_t brightness_pct) = 0;
  virtual ErrorCode led_blink(uint16_t on_ms, uint16_t off_ms, uint8_t count) = 0;
  virtual ErrorCode led_stop() = 0;

  // ── Vibration motor ────────────────────────────────────────────────────────
  virtual ErrorCode vibrate(const VibrationConfig& config) = 0;
  virtual ErrorCode vibrate_stop() = 0;

  // ── GPIO ───────────────────────────────────────────────────────────────────
  virtual ErrorCode gpio_write(uint8_t pin, bool level) = 0;
  virtual bool     gpio_read(uint8_t pin) = 0;
  virtual ErrorCode gpio_set_mode(uint8_t pin, uint8_t mode) = 0;
};

} // namespace arp::hal

#endif // HAL_IACTUATOR_H
