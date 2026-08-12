/**
 * @file TFLiteMicroRuntime.h
 * @brief TensorFlow Lite Micro model runtime wrapper
 */

#ifndef AI_TFLITEMICRUNTIME_H
#define AI_TFLITEMICRUNTIME_H

#include "IModelRuntime.h"
#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::ai {

class TFLiteMicroRuntime : public IModelRuntime {
public:
  TFLiteMicroRuntime();
  ~TFLiteMicroRuntime() override;

  ErrorCode load_model(const uint8_t* model_blob, size_t blob_len) override;
  ErrorCode invoke(const InputTensor& in, OutputTensor& out) override;
  ModelInfo info() const override;
  uint32_t version() const noexcept override { return _version; }
  ErrorCode unload() override;

private:
  uint32_t _version;
  uint32_t _model_id;
  uint8_t* _arena;
  size_t   _arena_size;
  uint32_t _input_size;
  uint32_t _output_size;

  // Placeholder: actual TFLite Micro interpreter pointer
  void* _interpreter;

  ErrorCode _validate_model_header(const uint8_t* blob, size_t len);
  ErrorCode _init_interpreter(const uint8_t* weight_data, size_t weight_len);
};

} // namespace arp::ai

#endif // AI_TFLITEMICRUNTIME_H
