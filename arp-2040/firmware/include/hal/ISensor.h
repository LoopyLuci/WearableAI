/**
 * @file ISensor.h
 * @brief Abstract sensor interface — frozen contract
 *
 * ALL sensor implementations must satisfy this interface.
 * This file must NEVER change unless a fundamentally new sensor category is invented.
 */

#ifndef HAL_ISENSOR_H
#define HAL_ISENSOR_H

#include "common_types.h"
#include <cstdint>

namespace arp::hal {

struct SensorConfig {
  SensorSampleRate rate;
  uint8_t  accel_range_g;   // For IMU: 2, 4, 8, 16
  uint8_t  gyro_range_dps;  // For IMU: 125, 250, 500, 1000, 2000
  bool     enable_mlc;      // Enable LSM6DSOX Machine Learning Core
  uint8_t  mlc_fsm_slot;    // Which FSM slot to use (0-7)
  bool     enable_interrupt;
  uint8_t  interrupt_pin;   // GPIO pin for INT1/INT2
  uint8_t  reserved[3];
};

struct IMUSample {
  int16_t accel_mg[3];   // mg * 1000 (int16 gives ±16g range)
  int16_t gyro_mdps[3];  // mdps * 1000
  int16_t temp_c_x100;   // Celsius * 100
  uint8_t mlc_event;     // MLC FSM output, or 0xFF if no event
  uint8_t reserved[3];
};

struct AudioSample {
  int16_t samples[160];  // 10 ms @ 16 kHz
  uint32_t timestamp_us;
  float   energy_db;
};

class ISensor {
public:
  virtual ~ISensor() = default;

  virtual SensorType type() const noexcept = 0;
  virtual const char* name() const noexcept = 0;

  /**
   * @brief Initialize the sensor hardware
   * @return ErrorCode::OK on success
   */
  virtual ErrorCode init() = 0;

  /**
   * @brief Configure sensor parameters
   * @param config Desired configuration
   * @return ErrorCode::OK on success
   */
  virtual ErrorCode configure(const SensorConfig& config) = 0;

  /**
   * @brief Read samples into caller-provided buffer
   * @param out_buffer Buffer to fill
   * @param max_samples Maximum samples to read
   * @param out_samples Actual samples written
   * @return ErrorCode::OK on success
   */
  virtual ErrorCode read(void* out_buffer, size_t max_samples, size_t* out_samples) = 0;

  /**
   * @brief Self-test without external test gear
   * @return ErrorCode::OK if sensor passes
   */
  virtual ErrorCode self_test() = 0;

  /**
   * @brief Unique serial number (from chip ID or hardcoded)
   */
  virtual uint32_t serial_number() const noexcept = 0;

  /**
   * @brief Check if new data is available
   */
  virtual bool data_available() const = 0;
};

} // namespace arp::hal

#endif // HAL_ISENSOR_H
