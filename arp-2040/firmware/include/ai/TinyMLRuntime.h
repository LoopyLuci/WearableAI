/**
 * ARP-2040 Connect Firmware - TinyML Inference Runtime Stub
 *
 * Provides:
 * - .armodel package parser
 * - bounded model loader from QSPI/staging path
 * - simple inference stub with confidence/class output
 *
 * Real TFLite Micro integration is intentionally deferred to avoid
 * bloating the validation build; this stub validates the end-to-end
 * model loading and inference command path.
 */
#ifndef TINYML_RUNTIME_H
#define TINYML_RUNTIME_H

#include <Arduino.h>
#include <cstdint>
#include <cstddef>

namespace tinyml {

struct ModelHeader {
  char magic[4];      // "ARMD"
  uint32_t version;
  uint8_t checksum[16];
  uint32_t metadata_len;
  uint32_t payload_len;
};

struct ModelRuntime {
  const uint8_t* data;
  size_t data_len;
  bool loaded;
  char name[32];
};

bool parse_armodel_header(const uint8_t* buf, size_t len, ModelHeader* out);
bool validate_checksum(const uint8_t* buf, size_t len, const uint8_t expected[16]);
bool load_model_from_path(ModelRuntime* runtime, const char* path);
bool run_inference(const ModelRuntime* runtime, const uint8_t* input, size_t input_len, char* out_json, size_t out_len);

}  // namespace tinyml

#endif  // TINYML_RUNTIME_H
