/**
 * @file ITransactionalStore.h
 * @brief Transactional store interface — staged writes, atomic promotion
 */
#ifndef STORAGE_ITRANSACTIONALSTORE_H
#define STORAGE_ITRANSACTIONALSTORE_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::storage {

struct TransactionResult {
  bool     committed;
  uint32_t old_version;
  uint32_t new_version;
  ErrorCode error;
};

class ITransactionalStore {
public:
  virtual ~ITransactionalStore() = default;

  /**
   * @brief Begin a new transaction on the given store
   */
  virtual ErrorCode begin_transaction(uint32_t store_id) = 0;

  /**
   * @brief Write data to staging area of the transaction
   */
  virtual ErrorCode write_staging(uint32_t store_id, const uint8_t* data,
                                  size_t len, size_t offset) = 0;

  /**
   * @brief Commit transaction — atomic promotion
   */
  virtual TransactionResult commit(uint32_t store_id) = 0;

  /**
   * @brief Abort transaction — discard staging, keep current active
   */
  virtual ErrorCode abort(uint32_t store_id) = 0;

  /**
   * @brief Read current active data
   */
  virtual ErrorCode read_active(uint32_t store_id, uint8_t* out_buffer,
                                size_t max_len, size_t* out_len) = 0;

  /**
   * @brief Get current version of a store
   */
  virtual uint32_t current_version(uint32_t store_id) const = 0;
};

} // namespace arp::storage
#endif // STORAGE_ITRANSACTIONALSTORE_H
