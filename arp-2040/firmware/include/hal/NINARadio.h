/**
 * @file NINARadio.h
 * @brief NINA-W102 radio HAL implementation
 */

#ifndef NINARadio_h
#define NINARadio_h

#include "IRadio.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

class NINARadio : public IRadio {
public:
  NINARadio();
  ~NINARadio() override = default;

  ErrorCode init() override;
  ErrorCode shutdown() override;
  ErrorCode wifi_set_mode(WiFiMode mode) override;
  ErrorCode wifi_connect(const WiFiCredentials& cred) override;
  ErrorCode wifi_disconnect() override;
  ErrorCode wifi_start_ap(const WiFiAPConfig& ap) override;
  ErrorCode wifi_stop_ap() override;
  ConnectionState wifi_state() const override;
  int8_t wifi_rssi() const override;
  MACAddress wifi_mac() const override;
  uint32_t wifi_ip() const override;
  ErrorCode ble_start_advertising(const char* name, uint16_t service_uuid) override;
  ErrorCode ble_stop_advertising() override;
  ConnectionState ble_state() const override;
  size_t ble_connected_peers() const override;
  ErrorCode ble_get_peers(BLEPeer* out_peers, size_t max_peers,
                          size_t* out_count) override;
  ErrorCode tcp_server_start(uint16_t port, uint8_t max_connections) override;
  ErrorCode tcp_server_stop() override;
  bool tcp_server_running() const override;
  ErrorCode ping() override;
  uint32_t reset_count() const override;
  uint32_t uptime_s() const override;
  ErrorCode get_firmware_version(char* out_buffer, size_t buffer_size) override;
  ErrorCode get_mac_address(MACAddress* out_mac) override;

private:
  mutable struct {
    ConnectionState wifi_state_val;
    ConnectionState ble_state_val;
    bool wifi_connected;
    bool ap_running;
    bool ble_advertising;
    bool tcp_server_running_val;
    WiFiMode wifi_mode;
    MACAddress mac;
  } _state;
};

}  // namespace arp::hal

#endif // NINARadio_h
