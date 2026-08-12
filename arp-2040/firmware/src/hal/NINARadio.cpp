/**
 * @file NINARadio.cpp
 * @brief NINA-W102 radio HAL implementation via WiFiNINA/BLE libraries
 *
 * Target: Arduino Nano RP2040 Connect (ABX00053)
 * Radio: NINA-W102 via UART0 AT commands / WiFiNINA library
 */

#include "IRadio.h"
#include <Arduino.h>
#include <WiFiNINA.h>
#include <ArduinoBLE.h>

namespace arp::hal {

// NINA-W102 UART0 constants (from datasheet)
static constexpr uint32_t NINA_BAUD = 115200;
static constexpr uint32_t NINA_AT_TIMEOUT_MS = 2000;

ErrorCode NINARadio::init() {
  // Initialize WiFiNINA firmware
  if (WiFi.status() == WL_NO_MODULE) {
    _state.wifi_state_val = ConnectionState::FAILED;
    return ErrorCode::NOT_READY;
  }

  // Get firmware version
  String fw_ver = WiFi.firmwareVersion();
  if (fw_ver == "0.0.0" || fw_ver == "Unknown") {
    _state.wifi_state_val = ConnectionState::FAILED;
    return ErrorCode::NOT_READY;
  }

  // Store MAC address
  uint8_t mac[6];
  WiFi.macAddress(mac);
  _state.mac.bytes[0] = mac[0];
  _state.mac.bytes[1] = mac[1];
  _state.mac.bytes[2] = mac[2];
  _state.mac.bytes[3] = mac[3];
  _state.mac.bytes[4] = mac[4];
  _state.mac.bytes[5] = mac[5];

  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  _state.ble_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ErrorCode NINARadio::shutdown() {
  WiFi.disconnect();
  WiFi.end();
  BLE.stopAdvertise();
  BLE.disconnect();
  _state.wifi_connected = false;
  _state.ap_running = false;
  _state.ble_advertising = false;
  _state.wifi_mode = WiFiMode::OFF;
  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  _state.ble_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ErrorCode NINARadio::wifi_set_mode(WiFiMode mode) {
  switch (mode) {
    case WiFiMode::STATION:
      WiFi.mode(WIFI_STA);
      break;
    case WiFiMode::AP:
      WiFi.mode(WIFI_AP);
      break;
    case WiFiMode::STA_AP:
      WiFi.mode(WIFI_AP_STA);
      break;
    case WiFiMode::OFF:
    default:
      WiFi.mode(WIFI_OFF);
      break;
  }
  _state.wifi_mode = mode;
  return ErrorCode::OK;
}

ErrorCode NINARadio::wifi_connect(const WiFiCredentials& cred) {
  int status = WiFi.begin(cred.ssid.c_str(), cred.password.c_str());
  if (status == WL_CONNECTED) {
    _state.wifi_connected = true;
    _state.wifi_state_val = ConnectionState::CONNECTED;
    return ErrorCode::OK;
  } else if (status == WL_CONNECT_FAILED) {
    _state.wifi_state_val = ConnectionState::FAILED;
    return ErrorCode::TIMEOUT;
  }
  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::NOT_READY;
}

ErrorCode NINARadio::wifi_disconnect() {
  WiFi.disconnect();
  _state.wifi_connected = false;
  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ErrorCode NINARadio::wifi_start_ap(const WiFiAPConfig& ap) {
  bool success = WiFi.beginAP(ap.ssid.c_str(), ap.password.c_str(),
                               ap.channel, ap.hidden);
  if (success) {
    _state.ap_running = true;
    _state.wifi_state_val = ConnectionState::CONNECTED;
    return ErrorCode::OK;
  }
  _state.wifi_state_val = ConnectionState::FAILED;
  return ErrorCode::NOT_READY;
}

ErrorCode NINARadio::wifi_stop_ap() {
  WiFi.end();
  _state.ap_running = false;
  _state.wifi_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ConnectionState NINARadio::wifi_state() const {
  return _state.wifi_state_val;
}

int8_t NINARadio::wifi_rssi() const {
  return static_cast<int8_t>(WiFi.RSSI());
}

MACAddress NINARadio::wifi_mac() const {
  return _state.mac;
}

uint32_t NINARadio::wifi_ip() const {
  IPAddress ip = WiFi.localIP();
  return (static_cast<uint32_t>(ip[0]) << 24) |
         (static_cast<uint32_t>(ip[1]) << 16) |
         (static_cast<uint32_t>(ip[2]) << 8) |
         static_cast<uint32_t>(ip[3]);
}

ErrorCode NINARadio::ble_start_advertising(const char* name, uint16_t service_uuid) {
  if (!BLE.begin()) {
    _state.ble_state_val = ConnectionState::FAILED;
    return ErrorCode::NOT_READY;
  }
  BLE.setLocalName(name);
  BLE.setAdvertisedServiceUuid(service_uuid);
  BLE.advertise();
  _state.ble_advertising = true;
  _state.ble_state_val = ConnectionState::CONNECTED;
  return ErrorCode::OK;
}

ErrorCode NINARadio::ble_stop_advertising() {
  BLE.stopAdvertise();
  _state.ble_advertising = false;
  _state.ble_state_val = ConnectionState::DISCONNECTED;
  return ErrorCode::OK;
}

ConnectionState NINARadio::ble_state() const {
  return _state.ble_state_val;
}

size_t NINARadio::ble_connected_peers() const {
  // WiFiNINA doesn't expose BLE peer count directly
  return BLE.connected() ? 1 : 0;
}

ErrorCode NINARadio::ble_get_peers(BLEPeer* out_peers, size_t max_peers,
                                    size_t* out_count) {
  // WiFiNINA doesn't expose BLE peer list
  if (out_count) *out_count = 0;
  return ErrorCode::OK;
}

ErrorCode NINARadio::tcp_server_start(uint16_t port, uint8_t max_connections) {
  // TCP server would require custom AT command handling
  _state.tcp_server_running_val = false;
  return ErrorCode::NOT_READY;
}

ErrorCode NINARadio::tcp_server_stop() {
  _state.tcp_server_running_val = false;
  return ErrorCode::OK;
}

bool NINARadio::tcp_server_running() const {
  return _state.tcp_server_running_val;
}

ErrorCode NINARadio::ping() {
  if (WiFi.status() == WL_NO_MODULE) {
    return ErrorCode::NOT_READY;
  }
  return ErrorCode::OK;
}

uint32_t NINARadio::reset_count() const {
  // NINA-W102 doesn't expose reset count via WiFiNINA API
  return _state.reset_count_val;
}

uint32_t NINARadio::uptime_s() const {
  return static_cast<uint32_t>(millis() / 1000);
}

ErrorCode NINARadio::get_firmware_version(char* out_buffer, size_t buffer_size) {
  String fw_ver = WiFi.firmwareVersion();
  size_t len = fw_ver.length() + 1;
  if (len > buffer_size) return ErrorCode::INVALID_PARAMETER;
  fw_ver.toCharArray(out_buffer, buffer_size);
  return ErrorCode::OK;
}

ErrorCode NINARadio::get_mac_address(MACAddress* out_mac) {
  if (!out_mac) return ErrorCode::INVALID_PARAMETER;
  *out_mac = _state.mac;
  return ErrorCode::OK;
}

}  // namespace arp::hal
