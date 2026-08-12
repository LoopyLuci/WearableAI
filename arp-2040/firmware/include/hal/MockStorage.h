/**
 * @file MockStorage.h
 * @brief Mock IStorage implementation backed by FlashSimulator
 */

#ifndef HAL_IMOCKSTORAGE_H
#define HAL_IMOCKSTORAGE_H

#include "IStorage.h"
#include <cstdint>
#include <cstddef>
#include <vector>
#include <string>
#include <unordered_map>

extern "C" {
#include "flash_sim/flash_sim.h"
}

namespace arp::hal {

class MockStorage : public IStorage {
public:
  explicit MockStorage(const char* flash_file = ":memory:");

  ErrorCode init() override;
  ErrorCode read(FlashOffset offset, uint8_t* out_buffer, FlashLength length) override;
  ErrorCode write(FlashOffset offset, const uint8_t* data, FlashLength length) override;
  ErrorCode erase(FlashOffset offset, FlashLength length) override;

  ErrorCode write_image_staging(const FlashRegion& staging_region,
                                const uint8_t* payload, FlashLength payload_len) override;
  ErrorCode read_metadata(const FlashRegion& region, ImageMetadata* out_meta) override;
  ErrorCode promote_image(const FlashRegion& active_region,
                          const FlashRegion& staging_region) override;
  ErrorCode verify_region(const FlashRegion& region) override;

  ErrorCode read_config(uint32_t config_id, uint8_t* out_buffer,
                        size_t buffer_size, size_t* out_len) override;
  ErrorCode write_config(uint32_t config_id, const uint8_t* data, size_t data_len) override;
  ErrorCode delete_config(uint32_t config_id) override;

  ErrorCode file_open(const char* path, const char* mode) override;
  ErrorCode file_close(int fd) override;
  ErrorCode file_read(int fd, uint8_t* buffer, size_t len, size_t* bytes_read) override;
  ErrorCode file_write(int fd, const uint8_t* data, size_t len) override;
  ErrorCode file_seek(int fd, int32_t offset, int whence) override;
  ErrorCode file_unlink(const char* path) override;

  FlashLength capacity() const override { return CAPACITY; }
  FlashLength page_size() const override { return PAGE_SIZE; }
  ErrorCode format() override;

private:
  std::string _flash_path;
  FlashSimulator _flash;
  int _next_fd;
  std::unordered_map<int, std::pair<std::string, long>> _open_files;
};

} // namespace arp::hal

#endif // HAL_IMOCKSTORAGE_H
