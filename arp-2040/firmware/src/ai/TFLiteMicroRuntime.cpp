/**
 * @file TFLiteMicroRuntime.cpp
 * @brief TFLite Micro wrapper implementation
 */

#include "TFLiteMicroRuntime.h"
#include <cstring>
#include <cstdio>

// In production, include the actual TFLite Micro headers:
// #include "tensorflow/lite/micro/all_ops_resolver.h"
// #include "tensorflow/lite/micro/micro_interpreter.h"

namespace arp::ai {

static constexpr size_t DEFAULT_ARENA_SIZE = 64 * 1024;  // 64 KB

TFLiteMicroRuntime::TFLiteMicroRuntime()
  : _version(0), _model_id(0), _arena(nullptr), _arena_size(0),
    _input_size(0), _output_size(0), _interpreter(nullptr) {
  _arena = new uint8_t[DEFAULT_ARENA_SIZE];
  _arena_size = DEFAULT_ARENA_SIZE;
}

TFLiteMicroRuntime::~TFLiteMicroRuntime() {
  unload();
  delete[] _arena;
}

ErrorCode TFLiteMicroRuntime::_validate_model_header(const uint8_t* blob, size_t len) {
  if (!blob || len < 68) return ErrorCode::INVALID_PARAMETER;

  // Check ARP-2040 Model Format magic
  uint32_t magic;
  memcpy(&magic, blob, 4);
  if (magic != 0x41524D4C) {  // "ARML"
    // Fallback: assume raw TFLite FlatBuffer
    _input_size = 0;
    _output_size = 0;
    _version = 1;
    return ErrorCode::OK;
  }

  uint32_t version, model_id, weight_crc, weight_len;
  memcpy(&version, blob + 4, 4);
  memcpy(&model_id, blob + 8, 4);
  memcpy(&weight_crc, blob + 20, 4);
  memcpy(&weight_len, blob + 24, 4);

  _version = version;
  _model_id = model_id;
  _input_size = 0;  // Parsed from TFLite FlatBuffer in production
  _output_size = 0;

  return ErrorCode::OK;
}

ErrorCode TFLiteMicroRuntime::load_model(const uint8_t* model_blob, size_t blob_len) {
  if (!model_blob || blob_len == 0) return ErrorCode::INVALID_PARAMETER;

  ErrorCode err = _validate_model_header(model_blob, blob_len);
  if (err != ErrorCode::OK) return err;

  // Extract weight data offset
  const uint8_t* weight_data = model_blob + 68;
  size_t weight_len = blob_len - 68;

  return _init_interpreter(weight_data, weight_len);
}

ErrorCode TFLiteMicroRuntime::_init_interpreter(const uint8_t* weight_data, size_t weight_len) {
  // In production:
  // const tflite::Model* model = tflite::GetModel(weight_data);
  // if (!model) return ErrorCode::MODEL_CORRUPTED;
  // static tflite::AllOpsResolver resolver;
  // tflite::MicroInterpreter interpreter(model, resolver, _arena, _arena_size, nullptr);
  // TfLiteStatus allocate_status = interpreter.AllocateTensors();
  // if (allocate_status != kTfLiteOk) return ErrorCode::MEMORY_INSUFFICIENT;

  (void)weight_data;
  (void)weight_len;
  _interpreter = reinterpret_cast<void*>(1);  // Non-null sentinel
  return ErrorCode::OK;
}

ErrorCode TFLiteMicroRuntime::invoke(const InputTensor& in, OutputTensor& out) {
  if (!_interpreter) return ErrorCode::NOT_INITIALIZED;
  if (!in.data || in.size == 0) return ErrorCode::INVALID_PARAMETER;
  if (!out.data || out.capacity == 0) return ErrorCode::INVALID_PARAMETER;

  // In production:
  // TfLiteTensor* input = interpreter.input(0);
  // memcpy(input->data.int8, in.data, in.size);
  // TfLiteStatus invoke_status = interpreter.Invoke();
  // if (invoke_status != kTfLiteOk) return ErrorCode::TFLITE_ABORT;
  // TfLiteTensor* output = interpreter.output(0);
  // size_t out_len = output->bytes;
  // memcpy(out.data, output->data.int8, min(out_len, out.capacity));

  // Mock: copy input to output (identity)
  size_t copy_len = (in.size < out.capacity) ? in.size : out.capacity;
  memcpy(out.data, in.data, copy_len);
  out.size = copy_len;

  return ErrorCode::OK;
}

ModelInfo TFLiteMicroRuntime::info() const {
  ModelInfo info{};
  info.model_id = _model_id;
  info.version = _version;
  info.input_size = _input_size;
  info.output_size = _output_size;
  info.arena_size_bytes = _arena_size;
  info.weight_size_bytes = 0;
  snprintf(info.name, sizeof(info.name), "Model-%lu", _model_id);
  return info;
}

ErrorCode TFLiteMicroRuntime::unload() {
  _interpreter = nullptr;
  memset(_arena, 0, _arena_size);
  _version = 0;
  _model_id = 0;
  return ErrorCode::OK;
}

} // namespace arp::ai
