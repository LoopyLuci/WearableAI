/**
 * @file IStorage.h
 * @brief Flash storage interface — frozen contract
 *
 * Abstracts QSPI flash and LittleFS. All data is read/written
 * through this interface. The implementation handles transactional
 * writes, CRC verification, and wear leveling.
 */

#ifndef HAL_ISTORAGE_H
#define HAL_ISTORAGE_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

using FlashOffset = uint32_t;
using FlashLength = uint32_t;

struct FlashRegion {
  FlashOffset offset;
  FlashLength length;
  const char* name;
};

struct ImageMetadata {
  static constexpr uint32_t MAGIC_ACTIVE  = 0x41505246;  // "APRF"
  static constexpr uint32_t MAGIC_STAGING = 0x53505246;  // "SPRF"
  static constexpr uint32_t MAGIC_EMPTY   = 0x00000000;

  uint32_t magic;
  uint32_t version;
  uint32_t image_length;
  uint32_t payload_crc32;
  uint32_t metadata_crc32;
  TimestampS timestamp_unix;
  uint32_t source;       // 0=OTA, 1=USB, 2=SELF, 3=FACTORY
  uint32_t flags;
  uint8_t  reserved[32];
};

class IStorage {
public:
  virtual ~IStorage() = default;

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  virtual ErrorCode init() = 0;

  // ── Raw flash R/W ──────────────────────────────────────────────────────────
  virtual ErrorCode read(FlashOffset offset, uint8_t* out_buffer, FlashLength length) = 0;
  virtual ErrorCode write(FlashOffset offset, const uint8_t* data, FlashLength length) = 0;
  virtual ErrorCode erase(FlashOffset offset, FlashLength length) = 0;

  // ── Transactional image management ────────────────────────────────────────
  /**
   * @brief Write a complete image to staging region
   */
  virtual ErrorCode write_image_staging(const FlashRegion& staging_region,
                                        const uint8_t* payload, FlashLength payload_len) = 0;

  /**
   * @brief Read metadata from a region
   */
  virtual ErrorCode read_metadata(const FlashRegion& region, ImageMetadata* out_meta) = 0;

  /**
   * @brief Promote staging image to active (atomic)
   */
  virtual ErrorCode promote_image(const FlashRegion& active_region,
                                  const FlashRegion& staging_region) = 0;

  /**
   * @brief Verify CRC of a region's payload against its metadata
   */
  virtual ErrorCode verify_region(const FlashRegion& region) = 0;

  // ── Versioned config store ─────────────────────────────────────────────────
  virtual ErrorCode read_config(uint32_t config_id, uint8_t* out_buffer,
                                size_t buffer_size, size_t* out_len) = 0;
  virtual ErrorCode write_config(uint32_t config_id, const uint8_t* data, size_t data_len) = 0;
  virtual ErrorCode delete_config(uint32_t config_id) = 0;

  // ── LittleFS file operations ────────────────────────────────────────────────
  virtual ErrorCode file_open(const char* path, const char* mode) = 0;
  virtual ErrorCode file_close(int fd) = 0;
  virtual ErrorCode file_read(int fd, uint8_t* buffer, size_t len, size_t* bytes_read) = 0;
  virtual ErrorCode file_write(int fd, const uint8_t* data, size_t len) = 0;
  virtual ErrorCode file_seek(int fd, int32_t offset, int whence) = 0;
  virtual ErrorCode file_unlink(const char* path) = 0;

  // ── Utility ────────────────────────────────────────────────────────────────
  virtual FlashLength capacity() const = 0;
  virtual FlashLength page_size() const = 0;
  virtual ErrorCode format() = 0;
};

} // namespace arp::hal

#endif // HAL_ISTORAGE_H
