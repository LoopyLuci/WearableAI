/**
 * @file IRadio.h
 * @brief Unified Wi-Fi + Bluetooth radio interface — frozen contract
 *
 * Abstracts the NINA-W102 module. All Wi-Fi and BLE operations
 * go through this interface. The implementation talks to NINA over UART0.
 */

#ifndef HAL_IRADIO_H
#define HAL_IRADIO_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

struct WiFiCredentials {
  char ssid[33];
  char password[65];
  uint8_t channel;
};

struct WiFiAPConfig {
  char ssid[33];
  char password[65];
  uint8_t channel;
  uint8_t max_clients;  // Max 8 for NINA SoftAP
  bool   hidden;
};

struct MACAddress {
  uint8_t bytes[6];
  bool operator==(const MACAddress& other) const {
    for (int i = 0; i < 6; i++) if (bytes[i] != other.bytes[i]) return false;
    return true;
  }
};

struct BLEPeer {
  MACAddress mac;
  int8_t     rssi;
  uint8_t    address_type;
};

enum class WiFiMode : uint8_t {
  OFF = 0,
  STATION = 1,
  AP = 2,
  STA_AP = 3  // Simultaneous station + AP (if supported)
};

class IRadio {
public:
  virtual ~IRadio() = default;

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  virtual ErrorCode init() = 0;
  virtual ErrorCode shutdown() = 0;

  // ── Wi-Fi ──────────────────────────────────────────────────────────────────
  virtual ErrorCode wifi_set_mode(WiFiMode mode) = 0;
  virtual ErrorCode wifi_connect(const WiFiCredentials& cred) = 0;
  virtual ErrorCode wifi_disconnect() = 0;
  virtual ErrorCode wifi_start_ap(const WiFiAPConfig& ap) = 0;
  virtual ErrorCode wifi_stop_ap() = 0;
  virtual ConnectionState wifi_state() const = 0;
  virtual int8_t wifi_rssi() const = 0;
  virtual MACAddress wifi_mac() const = 0;
  virtual uint32_t wifi_ip() const = 0;  // Network byte order

  // ── BLE ────────────────────────────────────────────────────────────────────
  virtual ErrorCode ble_start_advertising(const char* name, uint16_t service_uuid) = 0;
  virtual ErrorCode ble_stop_advertising() = 0;
  virtual ConnectionState ble_state() const = 0;
  virtual size_t ble_connected_peers() const = 0;
  virtual ErrorCode ble_get_peers(BLEPeer* out_peers, size_t max_peers, size_t* out_count) = 0;

  // ── TCP server (runs on NINA Wi-Fi) ────────────────────────────────────────
  virtual ErrorCode tcp_server_start(uint16_t port, uint8_t max_connections) = 0;
  virtual ErrorCode tcp_server_stop() = 0;
  virtual bool tcp_server_running() const = 0;

  // ── Health monitoring ──────────────────────────────────────────────────────
  virtual ErrorCode ping() = 0;  // AT ping to NINA
  virtual uint32_t reset_count() const = 0;
  virtual uint32_t uptime_s() const = 0;

  // ── Firmware management ────────────────────────────────────────────────────
  virtual ErrorCode get_firmware_version(char* out_buffer, size_t buffer_size) = 0;
  virtual ErrorCode get_mac_address(MACAddress* out_mac) = 0;
};

} // namespace arp::hal

#endif // HAL_IRADIO_H
