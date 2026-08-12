/**
 * @file ICrypto.h
 * @brief Cryptographic operations interface — frozen contract
 *
 * Abstracts ATECC608A hardware crypto chip and provides software fallback.
 */

#ifndef HAL_ICRYPTO_H
#define HAL_ICRYPTO_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

struct PublicKey {
  uint8_t bytes[64];  // ECDSA P-256 public key
};

struct Signature {
  uint8_t r[32];
  uint8_t s[32];
};

struct ChallengeResponse {
  uint8_t  token[32];
  uint32_t counter;
};

class ICrypto {
public:
  virtual ~ICrypto() = default;

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  virtual ErrorCode init() = 0;

  // ── Identity ───────────────────────────────────────────────────────────────
  virtual bool has_hardware_key() const = 0;
  virtual ErrorCode get_public_key(PublicKey* out_key) = 0;
  virtual uint32_t device_serial() const = 0;
  virtual uint32_t monotonic_counter() const = 0;

  // ── Signing ────────────────────────────────────────────────────────────────
  /**
   * @brief Sign a message with the device's private key
   * @param message Message bytes to sign
   * @param message_len Length of message
   * @param out_signature Output signature
   */
  virtual ErrorCode sign(const uint8_t* message, size_t message_len, Signature* out_signature) = 0;

  /**
   * @brief Verify a signature against a known public key
   */
  virtual ErrorCode verify(const PublicKey& public_key,
                           const uint8_t* message, size_t message_len,
                           const Signature& signature) = 0;

  // ── Challenge-response (for pairing) ───────────────────────────────────────
  virtual ErrorCode create_challenge(ChallengeResponse* out_challenge) = 0;
  virtual ErrorCode verify_response(const ChallengeResponse& challenge,
                                    const uint8_t* response, size_t response_len) = 0;

  // ── Random number generation ───────────────────────────────────────────────
  virtual ErrorCode random_bytes(uint8_t* out_buffer, size_t length) = 0;

  // ── Hashing ────────────────────────────────────────────────────────────────
  virtual ErrorCode sha256(const uint8_t* data, size_t data_len, uint8_t* out_hash_32) = 0;

  // ── AES encryption/decryption ──────────────────────────────────────────────
  virtual ErrorCode aes128_encrypt(const uint8_t* key_16, const uint8_t* plaintext_16,
                                   uint8_t* out_ciphertext_16) = 0;
  virtual ErrorCode aes128_decrypt(const uint8_t* key_16, const uint8_t* ciphertext_16,
                                   uint8_t* out_plaintext_16) = 0;
};

} // namespace arp::hal

#endif // HAL_ICRYPTO_H
