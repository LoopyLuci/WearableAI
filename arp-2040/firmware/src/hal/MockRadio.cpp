/**
 * @file MockRadio.cpp
 * @brief MockRadio implementation
 */

#include "MockRadio.h"
#include <cstring>

namespace arp::hal {

ErrorCode MockRadio::init() {
  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  _state.ble_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ErrorCode MockRadio::shutdown() {
  _state.wifi_connected = false;
  _state.ap_running = false;
  _state.ble_advertising = false;
  _state.tcp_server_running_val = false;
  _state.wifi_mode = WiFiMode::OFF;
  return ErrorCode::OK;
}

ErrorCode MockRadio::wifi_set_mode(WiFiMode mode) {
  _state.wifi_mode = mode;
  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ErrorCode MockRadio::wifi_connect(const WiFiCredentials& cred) {
  _state.wifi_connected = true;
  _state.wifi_state_val = ConnectionState::CONNECTED;
  return ErrorCode::OK;
}

ErrorCode MockRadio::wifi_disconnect() {
  _state.wifi_connected = false;
  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ErrorCode MockRadio::wifi_start_ap(const WiFiAPConfig& ap) {
  _state.ap_running = true;
  return ErrorCode::OK;
}

ErrorCode MockRadio::wifi_stop_ap() {
  _state.ap_running = false;
  return ErrorCode::OK;
}

ConnectionState MockRadio::wifi_state() const {
  return _state.wifi_state_val;
}

int8_t MockRadio::wifi_rssi() const {
  return -50;  // Mock: strong signal
}

MACAddress MockRadio::wifi_mac() const {
  return _state.mac;
}

uint32_t MockRadio::wifi_ip() const {
  return 0xC0A80001;  // 192.168.1.1
}

ErrorCode MockRadio::ble_start_advertising(const char* name, uint16_t service_uuid) {
  _state.ble_advertising = true;
  _state.ble_state_val = ConnectionState::CONNECTED;
  return ErrorCode::OK;
}

ErrorCode MockRadio::ble_stop_advertising() {
  _state.ble_advertising = false;
  _state.ble_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ConnectionState MockRadio::ble_state() const {
  return _state.ble_state_val;
}

size_t MockRadio::ble_connected_peers() const {
  return _state.peers.size();
}

ErrorCode MockRadio::ble_get_peers(BLEPeer* out_peers, size_t max_peers,
                                    size_t* out_count) {
  size_t count = (_state.peers.size() < max_peers) ? _state.peers.size() : max_peers;
  for (size_t i = 0; i < count; i++) {
    out_peers[i] = _state.peers[i];
  }
  if (out_count) *out_count = count;
  return ErrorCode::OK;
}

ErrorCode MockRadio::tcp_server_start(uint16_t port, uint8_t max_connections) {
  _state.tcp_server_running_val = true;
  return ErrorCode::OK;
}

ErrorCode MockRadio::tcp_server_stop() {
  _state.tcp_server_running_val = false;
  return ErrorCode::OK;
}

bool MockRadio::tcp_server_running() const {
  return _state.tcp_server_running_val;
}

ErrorCode MockRadio::ping() {
  return ErrorCode::OK;
}

uint32_t MockRadio::reset_count() const {
  return _state.reset_count_val;
}

uint32_t MockRadio::uptime_s() const {
  return _state.uptime_val;
}

ErrorCode MockRadio::get_firmware_version(char* out_buffer, size_t buffer_size) {
  const char* ver = "ARP-2040-FW v0.1.0-mock";
  size_t len = strlen(ver) + 1;
  if (len > buffer_size) return ErrorCode::INVALID_PARAMETER;
  memcpy(out_buffer, ver, len);
  return ErrorCode::OK;
}

ErrorCode MockRadio::get_mac_address(MACAddress* out_mac) {
  if (!out_mac) return ErrorCode::INVALID_PARAMETER;
  *out_mac = _state.mac;
  return ErrorCode::OK;
}

} // namespace arp::hal
