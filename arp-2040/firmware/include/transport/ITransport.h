/**
 * @file ITransport.h
 * @brief Transport abstraction — frozen contract
 */
#ifndef TRANSPORT_ITRANSPORT_H
#define TRANSPORT_ITRANSPORT_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::transport {

enum class TransportType : uint8_t {
  BLE = 0x01,
  WIFI_TCP = 0x02,
  USB_CDC = 0x03
};

struct Message {
  uint8_t  type;
  uint16_t payload_len;
  uint8_t  payload[512];
  uint32_t timestamp_s;
};

class ITransport {
public:
  virtual ~ITransport() = default;

  virtual TransportType type() const noexcept = 0;
  virtual ErrorCode connect() = 0;
  virtual ErrorCode disconnect() = 0;
  virtual ErrorCode send(const Message& msg) = 0;
  virtual ErrorCode receive(Message& out_msg, uint32_t timeout_ms) = 0;
  virtual bool is_connected() const = 0;
  virtual ConnectionState state() const = 0;
};

} // namespace arp::transport
#endif // TRANSPORT_ITRANSPORT_H
