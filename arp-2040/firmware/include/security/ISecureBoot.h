/**
 * @file ISecureBoot.h
 * @brief Secure boot and attestation interface
 */
#ifndef SECURITY_ISECUREBOOT_H
#define SECURITY_ISECUREBOOT_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::security {

struct BootInfo {
  uint32_t firmware_version;
  uint32_t config_version;
  uint32_t model_version;
  bool     secure_boot_enabled;
  bool     rollback_detected;
  uint8_t  reserved[32];
};

class ISecureBoot {
public:
  virtual ~ISecureBoot() = default;

  virtual ErrorCode verify_firmware(const uint8_t* firmware_blob, size_t len) = 0;
  virtual ErrorCode verify_model(const uint8_t* model_blob, size_t len) = 0;
  virtual ErrorCode verify_script(const uint8_t* script_blob, size_t len) = 0;
  virtual ErrorCode get_boot_info(BootInfo* out_info) = 0;
  virtual ErrorCode get_device_id(uint8_t* out_id, size_t id_len) = 0;
};

} // namespace arp::security
#endif // SECURITY_ISECUREBOOT_H
