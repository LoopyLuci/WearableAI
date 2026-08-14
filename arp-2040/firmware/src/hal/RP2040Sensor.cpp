/**
 * @file LSM6DSOX.cpp
 * @brief LSM6DSOX IMU driver for Nano RP2040 Connect
 *
 * Datasheet: STMicroelectronics LSM6DSOX
 * I2C Address: 0x6A (default)
 */
#include "RP2040Sensor.h"
#include "ISensor.h"
#include <Arduino.h>
#include <Wire.h>

namespace arp::hal {

// LSM6DSOX I2C address
static constexpr uint8_t LSM6DSOX_ADDR = 0x6A;

// Register addresses
static constexpr uint8_t REG_WHO_AMI = 0x0F;
static constexpr uint8_t REG_CTRL1_XL = 0x10;  // Accelerometer control
static constexpr uint8_t REG_CTRL2_G = 0x11;   // Gyroscope control
static constexpr uint8_t REG_CTRL3_C = 0x12;   // Control register 3
static constexpr uint8_t REG_OUTX_L_G = 0x22;  // Gyro output low byte
static constexpr uint8_t REG_OUTX_L_XL = 0x28; // Accel output low byte

static constexpr uint8_t EXPECTED_WHO_AMI = 0x6C;

bool RP2040Sensor::write_reg(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(LSM6DSOX_ADDR);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool RP2040Sensor::read_regs(uint8_t start_reg, uint8_t* buffer, size_t len) {
  Wire.beginTransmission(LSM6DSOX_ADDR);
  Wire.write(start_reg);
  if (Wire.endTransmission(false) != 0) {  // Repeated start
    return false;
  }
  Wire.requestFrom(LSM6DSOX_ADDR, len);
  for (size_t i = 0; i < len; i++) {
    if (!Wire.available()) {
      return false;
    }
    buffer[i] = Wire.read();
  }
  return true;
}

ErrorCode RP2040Sensor::configure(const SensorConfig& config) {
  (void)config;
  return ErrorCode::OK;
}

SensorType RP2040Sensor::type() const noexcept {
  return SensorType::IMU_6AXIS;
}

const char* RP2040Sensor::name() const noexcept {
  return "LSM6DSOX";
}

ErrorCode RP2040Sensor::read(void* out_buffer, size_t max_samples, size_t* out_samples) {
  (void)out_buffer;
  (void)max_samples;
  if (out_samples) {
    *out_samples = 0;
  }
  return ErrorCode::OK;
}

ErrorCode RP2040Sensor::init() {
  Wire.begin();
  Wire.setClock(400000);  // 400 kHz I2C
  delayMicroseconds(100);

  // Verify WHO_AMI
  uint8_t whoami = 0;
  if (!read_regs(REG_WHO_AMI, &whoami, 1)) {
    _imu_present = false;
    return ErrorCode::NOT_READY;
  }
  if (whoami != EXPECTED_WHO_AMI) {
    _imu_present = false;
    return ErrorCode::NOT_READY;
  }

  // Configure accelerometer: 104 Hz, ±4g
  // CTRL1_XL = 0x60: ODR_XL=104 Hz, FS_XL=±4g
  if (!write_reg(REG_CTRL1_XL, 0x60)) {
    _imu_present = false;
    return ErrorCode::NOT_READY;
  }

  // Configure gyroscope: 104 Hz, 500 dps
  // CTRL2_G = 0x60: ODR_G=104 Hz, FS_G=500 dps
  if (!write_reg(REG_CTRL2_G, 0x60)) {
    _imu_present = false;
    return ErrorCode::NOT_READY;
  }

  // Enable block update (read multiple registers in burst)
  // CTRL3_C = 0x04: BDU=1 (block data update)
  if (!write_reg(REG_CTRL3_C, 0x04)) {
    _imu_present = false;
    return ErrorCode::NOT_READY;
  }

  _imu_present = true;
  _mic_present = true;  // MP34DT06J always present on this board
  return ErrorCode::OK;
}


ErrorCode RP2040Sensor::readIMU(float* ax, float* ay, float* az,
                                  float* gx, float* gy, float* gz) {
  if (!_imu_present) {
    return ErrorCode::NOT_READY;
  }

  // Read 12 bytes: 6 bytes accel + 6 bytes gyro
  uint8_t buf[12];
  if (!read_regs(REG_OUTX_L_G, buf, 12)) {
    return ErrorCode::TIMEOUT;
  }

  // Convert gyroscope data: 16-bit signed, 500 dps = 16.4 LSB/dps
  int16_t gx_raw = (int16_t)(buf[1] << 8 | buf[0]);
  int16_t gy_raw = (int16_t)(buf[3] << 8 | buf[2]);
  int16_t gz_raw = (int16_t)(buf[5] << 8 | buf[4]);
  *gx = gx_raw / 16.4f;
  *gy = gy_raw / 16.4f;
  *gz = gz_raw / 16.4f;

  // Convert accelerometer data: 16-bit signed, ±4g = 8192 LSB/g
  int16_t ax_raw = (int16_t)(buf[7] << 8 | buf[6]);
  int16_t ay_raw = (int16_t)(buf[9] << 8 | buf[8]);
  int16_t az_raw = (int16_t)(buf[11] << 8 | buf[10]);
  *ax = ax_raw / 8192.0f;
  *ay = ay_raw / 8192.0f;
  *az = az_raw / 8192.0f;

  return ErrorCode::OK;
}

ErrorCode RP2040Sensor::readAudio(int16_t* buffer, size_t samples) {
  if (!_mic_present) {
    return ErrorCode::NOT_READY;
  }
  // Placeholder: real implementation would use PDM + PIO state machine
  // For now, return silence
  memset(buffer, 0, samples * sizeof(int16_t));
  return ErrorCode::OK;
}

ErrorCode RP2040Sensor::configureMLC(const uint8_t* fsms, size_t len) {
  if (!_imu_present) {
    return ErrorCode::NOT_READY;
  }
  // Placeholder: write FSM config to LSM6DSOX MLC registers
  // Real implementation would program the 8-state MLC
  return ErrorCode::OK;
}

ErrorCode RP2040Sensor::readMLC(uint8_t* gesture, size_t len) {
  if (!_imu_present) {
    return ErrorCode::NOT_READY;
  }
  // Placeholder: read MLC interrupt source register
  *gesture = 0;
  return ErrorCode::OK;
}

SensorCapabilities RP2040Sensor::capabilities() const {
  SensorCapabilities caps;
  caps.has_imu = _imu_present;
  caps.has_mic = _mic_present;
  caps.has_mlc = _imu_present;
  caps.imu_rate_hz = 104;
  caps.mic_rate_hz = 16000;
  caps.mlc_states = 8;
  return caps;
}


ErrorCode RP2040Sensor::self_test() {
  if (!_imu_present) {
    return ErrorCode::NOT_READY;
  }
  uint8_t whoami = 0;
  if (!read_regs(REG_WHO_AMI, &whoami, 1)) {
    return ErrorCode::IO_ERROR;
  }
  return whoami == EXPECTED_WHO_AMI ? ErrorCode::OK : ErrorCode::SIGNATURE_INVALID;
}

uint32_t RP2040Sensor::serial_number() const noexcept {
  return _serial;
}

bool RP2040Sensor::data_available() const {
  return _imu_present;
}

}  // namespace arp::hal
