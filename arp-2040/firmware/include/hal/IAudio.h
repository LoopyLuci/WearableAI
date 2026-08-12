/**
 * @file IAudio.h
 * @brief Audio capture interface — frozen contract
 */

#ifndef HAL_IAUDIO_H
#define HAL_IAUDIO_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

struct AudioConfig {
  uint32_t sample_rate_hz;   // 16000 typical
  uint8_t  bits_per_sample;  // 16
  uint8_t  channels;         // 1 (mono)
  uint16_t frame_duration_ms; // 10 ms typical
  bool     dma_enabled;
};

class IAudio {
public:
  virtual ~IAudio() = default;

  virtual ErrorCode init() = 0;
  virtual ErrorCode configure(const AudioConfig& config) = 0;
  virtual ErrorCode start() = 0;
  virtual ErrorCode stop() = 0;
  virtual ErrorCode read(int16_t* out_samples, size_t max_samples,
                         size_t* out_samples_read, uint32_t timeout_ms) = 0;
  virtual bool data_available() const = 0;
  virtual uint32_t sample_rate() const = 0;
};

} // namespace arp::hal

#endif // HAL_IAUDIO_H
