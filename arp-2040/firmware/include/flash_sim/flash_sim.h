#ifndef FLASH_SIM_H
#define FLASH_SIM_H

#include <cstdint>
#include <cstddef>

extern "C" {

typedef uint32_t FlashOffset;
typedef uint32_t FlashLength;

typedef struct {
  FlashOffset offset;
  FlashLength length;
} FlashRegion;

typedef struct {
  uint32_t magic;
  uint32_t version;
  uint32_t image_length;
  uint32_t payload_crc32;
  uint32_t metadata_crc32;
  uint32_t timestamp_unix;
  uint32_t source;
  uint32_t flags;
  uint8_t reserved[32];
} ImageMetadata;

typedef struct {
  int capacity;
  int page_size;
} FlashSimulator;

static inline void flash_sim_init(FlashSimulator* sim, int capacity, int page_size) {
  sim->capacity = capacity;
  sim->page_size = page_size;
}

static inline int flash_sim_read(FlashSimulator* sim, FlashOffset offset, uint8_t* buffer, FlashLength length) {
  (void)sim; (void)offset; (void)buffer; (void)length;
  return 0;
}

static inline int flash_sim_write(FlashSimulator* sim, FlashOffset offset, const uint8_t* data, FlashLength length) {
  (void)sim; (void)offset; (void)data; (void)length;
  return 0;
}

static inline int flash_sim_erase(FlashSimulator* sim, FlashOffset offset, FlashLength length) {
  (void)sim; (void)offset; (void)length;
  return 0;
}

} // extern "C"

#endif // FLASH_SIM_H
