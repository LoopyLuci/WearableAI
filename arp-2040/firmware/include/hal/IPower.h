/**
 * @file IPower.h
 * @brief Power management interface — frozen contract
 */

#ifndef HAL_IPOWER_H
#define HAL_IPOWER_H

#include "common_types.h"
#include <cstdint>

namespace arp::hal {

struct BatteryStatus {
  uint16_t voltage_mv;
  uint16_t soc_percent;       // State of charge, 0-100
  uint8_t  charging;
  uint8_t  low_battery;
};

class IPower {
public:
  virtual ~IPower() = default;

  virtual ErrorCode init() = 0;
  virtual ErrorCode set_state(PowerState state) = 0;
  virtual PowerState get_state() const = 0;
  virtual ErrorCode get_battery_status(BatteryStatus* out_status) = 0;
  virtual uint32_t estimated_runtime_seconds() const = 0;
  virtual void feed_watchdog() = 0;
  virtual uint32_t reset_count() const = 0;
};

} // namespace arp::hal

#endif // HAL_IPOWER_H
