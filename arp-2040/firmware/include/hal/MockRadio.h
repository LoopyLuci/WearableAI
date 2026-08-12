/**
 * @file MockRadio.h
 * @brief Mock IRadio implementation for host-side testing
 */

#ifndef HAL_IMOCKRADIO_H
#define HAL_IMOCKRADIO_H

#include "IRadio.h"
#include <cstdint>
#include <cstring>
#include <vector>
#include <string>

namespace arp::hal {

struct MockRadioState {
  WiFiMode wifi_mode = WiFiMode::OFF;
  bool wifi_connected = false;
  bool ap_running = false;
  bool ble_advertising = false;
  ConnectionState wifi_state_val = ConnectionState::DISCONNECTED;
  ConnectionState ble_state_val = ConnectionState::DISCONNECTED;
  MACAddress mac = {{0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF}};
  bool tcp_server_running_val = false;
  uint32_t reset_count_val = 0;
  uint32_t uptime_val = 0;
  std::vector<BLEPeer> peers;
};

class MockRadio : public IRadio {
public:
  MockRadio() = default;
  explicit MockRadio(const char* device_name) {}

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

  MockRadioState& state() { return _state; }
  const MockRadioState& state() const { return _state; }

private:
  MockRadioState _state;
};

} // namespace arp::hal

#endif // HAL_IMOCKRADIO_H
