/**
 * @file MockStorage.cpp
 * @brief Mock IStorage implementation backed by FlashSimulator
 */
#include "MockStorage.h"
#include <cstring>

namespace arp::hal {

MockStorage::MockStorage(const char* flash_file)
    : _flash_path(flash_file), _next_fd(0) {
    flash_sim_init(&_flash, CAPACITY, PAGE_SIZE);
  }

ErrorCode MockStorage::init() {
  return ErrorCode::OK;
}

ErrorCode MockStorage::read(FlashOffset offset, uint8_t* out_buffer, FlashLength length) {
  return flash_sim_read(&_flash, offset, out_buffer, length) == 0 ? ErrorCode::OK : ErrorCode::IO_ERROR;
}

ErrorCode MockStorage::write(FlashOffset offset, const uint8_t* data, FlashLength length) {
  return flash_sim_write(&_flash, offset, data, length) == 0 ? ErrorCode::OK : ErrorCode::IO_ERROR;
}

ErrorCode MockStorage::erase(FlashOffset offset, FlashLength length) {
  return flash_sim_erase(&_flash, offset, length) == 0 ? ErrorCode::OK : ErrorCode::IO_ERROR;
}

ErrorCode MockStorage::write_image_staging(const FlashRegion& staging_region,
                                const uint8_t* payload, FlashLength payload_len) {
  (void)staging_region; (void)payload; (void)payload_len;
  return ErrorCode::OK;
}

ErrorCode MockStorage::read_metadata(const FlashRegion& region, ImageMetadata* out_meta) {
  (void)region; (void)out_meta;
  return ErrorCode::OK;
}

ErrorCode MockStorage::promote_image(const FlashRegion& active_region,
                          const FlashRegion& staging_region) {
  (void)active_region; (void)staging_region;
  return ErrorCode::OK;
}

ErrorCode MockStorage::verify_region(const FlashRegion& region) {
  (void)region;
  return ErrorCode::OK;
}

ErrorCode MockStorage::read_config(uint32_t config_id, uint8_t* out_buffer,
                      size_t buffer_size, size_t* out_len) {
  (void)config_id; (void)out_buffer; (void)buffer_size;
  if (out_len) *out_len = 0;
  return ErrorCode::OK;
}

ErrorCode MockStorage::write_config(uint32_t config_id, const uint8_t* data, size_t data_len) {
  (void)config_id; (void)data; (void)data_len;
  return ErrorCode::OK;
}

ErrorCode MockStorage::delete_config(uint32_t config_id) {
  (void)config_id;
  return ErrorCode::OK;
}

ErrorCode MockStorage::file_open(const char* path, const char* mode) {
  (void)path; (void)mode;
  return ErrorCode::OK;
}

ErrorCode MockStorage::file_close(int fd) {
  (void)fd;
  return ErrorCode::OK;
}

ErrorCode MockStorage::file_read(int fd, uint8_t* buffer, size_t len, size_t* bytes_read) {
  (void)fd; (void)buffer; (void)len;
  if (bytes_read) *bytes_read = 0;
  return ErrorCode::OK;
}

ErrorCode MockStorage::file_write(int fd, const uint8_t* data, size_t len) {
  (void)fd; (void)data; (void)len;
  return ErrorCode::OK;
}

ErrorCode MockStorage::file_seek(int fd, int32_t offset, int whence) {
  (void)fd; (void)offset; (void)whence;
  return ErrorCode::OK;
}

ErrorCode MockStorage::file_unlink(const char* path) {
  (void)path;
  return ErrorCode::OK;
}

ErrorCode MockStorage::format() { return ErrorCode::OK; }

} // namespace arp::hal
