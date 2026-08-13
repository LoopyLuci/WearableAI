/**
 * @file RP2040Sensor.h
 * @brief LSM6DSOX 6-axis IMU + MP34DT06J PDM microphone implementation
 *
 * Target: Arduino Nano RP2040 Connect (ABX00053)
 * I2C Address: 0x6A
 */
#ifndef HAL_RP2040_SENSOR_H
#define HAL_RP2040_SENSOR_H

#include "common_types.h"
#include "ISensor.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

struct SensorCapabilities {
  bool has_imu;
  bool has_mic;
  bool has_mlc;
  uint8_t imu_rate_hz;
  uint16_t mic_rate_hz;
  uint8_t mlc_states;
};

class RP2040Sensor final : public ISensor {
public:
  RP2040Sensor() = default;
  ~RP2040Sensor() override = default;

  SensorType type() const noexcept override;
  const char* name() const noexcept override;
  ErrorCode init() override;
  ErrorCode configure(const SensorConfig& config) override;
  ErrorCode read(void* out_buffer, size_t max_samples, size_t* out_samples) override;
  ErrorCode self_test() override;
  uint32_t serial_number() const noexcept override;
  bool data_available() const override;

  // Extended IMU read API used by host tools / agents
  ErrorCode readIMU(float* ax, float* ay, float* az,
                    float* gx, float* gy, float* gz);
  ErrorCode readAudio(int16_t* buffer, size_t samples);
  ErrorCode configureMLC(const uint8_t* fsms, size_t len);
  ErrorCode readMLC(uint8_t* gesture, size_t len);
  SensorCapabilities capabilities() const;

private:
  static bool write_reg(uint8_t reg, uint8_t value);
  static bool read_regs(uint8_t start_reg, uint8_t* buffer, size_t len);

  bool _imu_present = false;
  bool _mic_present = false;
  uint32_t _serial = 0;
};

} // namespace arp::hal

#endif // HAL_RP2040_SENSOR_H
