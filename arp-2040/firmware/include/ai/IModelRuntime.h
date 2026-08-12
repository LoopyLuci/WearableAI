/**
 * @file IModelRuntime.h
 * @brief Model runtime interface — frozen contract
 */
#ifndef AI_IMODELRUNTIME_H
#define AI_IMODELRUNTIME_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::ai {

struct ModelInfo {
  uint32_t model_id;
  uint32_t version;
  uint32_t input_size;
  uint32_t output_size;
  uint32_t arena_size_bytes;
  uint32_t weight_size_bytes;
  char     name[64];
};

struct InputTensor {
  const uint8_t* data;
  size_t size;
};

struct OutputTensor {
  uint8_t* data;
  size_t capacity;
  size_t size;
};

class IModelRuntime {
public:
  virtual ~IModelRuntime() = default;

  virtual ErrorCode load_model(const uint8_t* model_blob, size_t blob_len) = 0;
  virtual ErrorCode invoke(const InputTensor& in, OutputTensor& out) = 0;
  virtual ModelInfo info() const = 0;
  virtual uint32_t version() const noexcept = 0;
  virtual ErrorCode unload() = 0;
};

} // namespace arp::ai
#endif // AI_IMODELRUNTIME_H
