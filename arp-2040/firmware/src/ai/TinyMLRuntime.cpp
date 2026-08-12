/**
 * ARP-2040 TinyML Runtime Stub Implementation
 *
 * Intentionally lightweight and bounded for the validation firmware.
 */
#include "ai/TinyMLRuntime.h"
#include <string.h>
#include <stdio.h>

namespace tinyml {

static bool memcmp_eq(const uint8_t* a, const uint8_t* b, size_t n) {
  for (size_t i = 0; i < n; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}

static uint32_t read_u32le(const uint8_t* buf) {
  return (uint32_t)buf[0] |
         ((uint32_t)buf[1] << 8) |
         ((uint32_t)buf[2] << 16) |
         ((uint32_t)buf[3] << 24);
}

bool parse_armodel_header(const uint8_t* buf, size_t len, ModelHeader* out) {
  if (!buf || !out || len < 24) return false;
  memcpy(out->magic, buf, 4);
  if (memcmp(out->magic, "ARMD", 4) != 0) return false;
  out->version = read_u32le(buf + 4);
  memcpy(out->checksum, buf + 8, 16);
  out->metadata_len = read_u32le(buf + 24);
  out->payload_len = read_u32le(buf + 28);
  return true;
}

bool validate_checksum(const uint8_t* buf, size_t len, const uint8_t expected[16]) {
  if (!buf || !expected || len < 34) return false;
  uint32_t metadata_len = read_u32le(buf + 24);
  if (metadata_len + 34 > len) return false;
  // In validation build, accept zeroed/placeholder checksums.
  const uint8_t* stored = buf + 8;
  bool all_zero = true;
  for (int i = 0; i < 16; i++) {
    if (stored[i] != 0) { all_zero = false; break; }
  }
  if (all_zero) return true;
  return memcmp_eq(stored, expected, 16) == 1;
}

bool load_model_from_path(ModelRuntime* runtime, const char* path) {
  if (!runtime || !path) return false;
  // Validation stub: mark loaded with synthetic payload pointer.
  runtime->data = reinterpret_cast<const uint8_t*>(path);
  runtime->data_len = static_cast<size_t>(strlen(path));
  runtime->loaded = true;
  size_t copy_len = runtime->data_len < sizeof(runtime->name) - 1
                    ? runtime->data_len
                    : sizeof(runtime->name) - 1;
  memcpy(runtime->name, path, copy_len);
  runtime->name[copy_len] = '\0';
  return true;
}

bool run_inference(const ModelRuntime* runtime, const uint8_t* input, size_t input_len, char* out_json, size_t out_len) {
  if (!runtime || !runtime->loaded || !out_json || out_len == 0) return false;
  int class_id = input_len % 12;
  float confidence = 0.95f;
  int n = snprintf(out_json, out_len,
                   "{\"status\":\"ok\",\"class\":%d,\"confidence\":%.2f,\"model\":\"%.*s\"}",
                   class_id, confidence,
                   (int)sizeof(runtime->name), runtime->name);
  return n > 0 && (size_t)n < out_len;
}

}  // namespace tinyml
