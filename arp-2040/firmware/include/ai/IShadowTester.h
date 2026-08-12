/**
 * @file IShadowTester.h
 * @brief Shadow testing interface for model promotion gating
 */
#ifndef AI_ISHADOWTESTER_H
#define AI_ISHADOWTESTER_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::ai {

struct ShadowTestResult {
  float live_accuracy;
  float shadow_accuracy;
  bool regression_detected;
  uint32_t total_samples;
  uint32_t mismatched_samples;
};

class IShadowTester {
public:
  virtual ~IShadowTester() = default;
  virtual ErrorCode add_sample(const uint8_t* input, size_t input_len,
                               const uint8_t* expected_output, size_t output_len) = 0;
  virtual ShadowTestResult run(const uint8_t* shadow_model_blob, size_t blob_len) = 0;
  virtual void clear_samples() = 0;
  virtual size_t sample_count() const = 0;
};

} // namespace arp::ai
#endif // AI_ISHADOWTESTER_H
