"""
arduino_mcp_toolkit.resources.handlers — Resource content providers
"""
from __future__ import annotations
import os
import logging
from arduino_mcp_toolkit.resources import resource

logger = logging.getLogger("arduino-mcp")


@resource("arduino://boards/available")
async def available_boards() -> str:
    return """[
      {"name": "Arduino Nano RP2040 Connect", "fqbn": "rp2040:rp2040:nano_rp2040_connect", "mcu": "RP2040", "flash_kb": 16384, "sram_kb": 264},
      {"name": "Arduino Uno", "fqbn": "arduino:avr:uno", "mcu": "ATmega328P", "flash_kb": 32, "sram_kb": 2},
      {"name": "Arduino Nano 33 BLE Sense", "fqbn": "arduino:mbed:nano33ble", "mcu": "nRF52840", "flash_kb": 1024, "sram_kb": 256},
      {"name": "Arduino Portenta H7", "fqbn": "arduino:mbed_portenta:portenta_h7_m7", "mcu": "STM32H747", "flash_kb": 2048, "sram_kb": 512},
      {"name": "Arduino ESP32 Dev Module", "fqbn": "esp32:esp32:esp32dev", "mcu": "ESP32", "flash_kb": 4096, "sram_kb": 520}
    ]"""


@resource("arduino://boards/detected")
async def detected_boards() -> str:
    return "[]"


@resource("arduino://docs/setup")
async def setup_guide() -> str:
    return """# ARP-2040 Agentic Arduino MCP Toolkit Setup Guide

## Prerequisites
- Python 3.9+
- PlatformIO CLI
- Git
- USB cable (data-capable)

## Installation
```bash
git clone https://github.com/your-org/arduino-mcp-toolkit.git
cd arduino-mcp-toolkit
pip install -e .
```

## Configure Hermes Agent
Add to your Hermes config:
```yaml
mcp:
  servers:
    arduino:
      command: arduino-mcp
      args: []
```

## First Use
```bash
arduino-mcp detect        # Auto-detect boards
arduino-mcp board-info    # Get detailed info
arduino-mcp generate-project --name my_project --board nano_rp2040_connect
arduino-mcp build-and-flash --source my_project
```
"""


@resource("arduino://docs/hal-spec")
async def hal_spec() -> str:
    return """# HAL Specification

## Interfaces (frozen)

| Interface | Purpose |
|---|---|
| ISensor  | All sensor drivers |
| IRadio   | Wi-Fi + BLE via NINA-W102 |
| ICrypto  | ATECC608A hardware crypto |
| IStorage | QSPI flash + LittleFS |
| IPower   | Power states, battery monitor |
| IAudio   | PDM microphone |
| IDisplay | OLED/LCD displays |
| IActuator | LED, vibration, GPIO |

## Dependency rule
No HAL implementation may depend on agents, AI, transport, or scripting.
"""


@resource("arduino://docs/protocol-spec")
async def protocol_spec() -> str:
    return """# Wire Protocol Specification (FROZEN)

## Framing
All TCP messages are 13-byte length-prefixed:
[1B version_major] [1B version_minor] [1B type] [2B payload_len LE] [4B timestamp_s LE] [4B message_id LE] [N bytes payload]

## Message types
| Type | Code | Direction |
|---|---|---|
| VOICE_EVENT | 0x01 | Device → Server |
| SENSOR_SNAPSHOT | 0x02 | Device → Server |
| COMMAND | 0x81 | Server → Device |
| MODEL_PUSH | 0x82 | Server → Device |
| GRAPH_PUSH | 0x84 | Server → Device |
| SCRIPT_PUSH | 0x85 | Server → Device |
"""


@resource("arduino://docs/blueprint")
async def blueprint() -> str:
    return "Full design blueprint available at: docs/ARP2040_Connect_Wearable_AI_Design_Blueprint.md"


@resource("arduino://examples/ble_peripheral")
async def ble_example() -> str:
    return """#include <ArduinoBLE.h>

BLEService ledService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic switchCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLEWrite);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!BLE.begin()) {
    Serial.println("starting BLE failed!");
    while (1);
  }

  BLE.setLocalName("BLE Peripheral");
  BLE.setAdvertisedService(ledService);
  ledService.addCharacteristic(switchCharacteristic);
  BLE.addService(ledService);
  switchCharacteristic.writeValue(0);
  BLE.advertise();
  Serial.println("BLE Peripheral active, waiting for connections...");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());
    while (central.connected()) {
      if (switchCharacteristic.written()) {
        int val = switchCharacteristic.value();
        Serial.print("Received: ");
        Serial.println(val);
      }
    }
    Serial.println("Central disconnected");
  }
}
"""


@resource("arduino://examples/wifi_scan")
async def wifi_example() -> str:
    return """#include <WiFiNINA.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("NINA-W102 not found");
    while (true) delay(1000);
  }

  Serial.println("Scanning networks...");
  int n = WiFi.scanNetworks();
  Serial.print("Found ");
  Serial.print(n);
  Serial.println(" networks:");
  for (int i = 0; i < n; i++) {
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(WiFi.SSID(i));
    Serial.print(" (");
    Serial.print(WiFi.RSSI(i));
    Serial.println(" dBm)");
    delay(10);
  }
}

void loop() { delay(10000); }
"""


@resource("arduino://examples/tinyml_kws")
async def tinyml_kws_example() -> str:
    return """#include <TensorFlowLite.h>

// Keyword spotting model
constexpr int kAudioSampleSize = 16000;
constexpr int kAudioSampleFrequency = 16000;

void setup() {
  Serial.begin(115200);
  Serial.println("TinyML KWS starting...");
  // Load model from QSPI flash
}

void loop() {
  // Capture audio, run inference
  delay(100);
}
"""


@resource("arduino://examples/imu_mlc")
async def imu_mlc_example() -> str:
    return """#include <Arduino_LSM6DSOX.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);

  if (!IMU.begin()) {
    Serial.println("LSM6DSOX not found");
    while (true) delay(1000);
  }

  // Configure MLC for gesture detection
  // ...
}

void loop() {
  if (IMU.mlcActivity()) {
    Serial.println("Gesture detected!");
  }
  delay(100);
}
"""


@resource("arduino://examples/control_graph")
async def control_graph_example() -> str:
    return """// Control graph + bytecode interpreter example
#include "ControlGraph.h"
#include "BytecodeInterpreter.h"

void setup() {
  Serial.begin(115200);
  Serial.println("Control graph example");
}

void loop() {
  // Load graph from QSPI, execute nodes
  delay(1000);
}
"""


@resource("arduino://tools/armodel_compiler")
async def armodel_compiler_tool() -> str:
    return """Host-side model build pipeline:
host-tools/model-compiler/armodel_cli.py

Usage:
  armodel_cli.py build --input model.tflite --id 0x0001 --name KWS_Model --version 1
  armodel_cli.py verify model_v1.armodel
"""


@resource("arduino://tools/graph_compiler")
async def graph_compiler_tool() -> str:
    return """Control graph compiler:
host-tools/graph-compiler/graph_cli.py

Usage:
  graph_cli.py --input graph.json --output graph.bin
"""


@resource("arduino://schemas/control_graph")
async def control_graph_schema() -> str:
    return """{
  "type": "object",
  "properties": {
    "version": {"type": "integer"},
    "entry_node": {"type": "integer"},
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "integer"},
          "type": {"type": "string", "enum": ["SENSOR_POLL", "MODEL_INFERENCE", "FORWARD", "FILTER", "ROUTE", "ACTION", "LOGGER", "SLEEP", "CUSTOM_SCRIPT"]},
          "param_a": {"type": "integer"},
          "param_b": {"type": "integer"},
          "next_true": {"type": "integer"},
          "next_false": {"type": "integer"},
          "interval_ms": {"type": "integer"},
          "flags": {"type": "integer"}
        },
        "required": ["id"]
      }
    }
  },
  "required": ["nodes"]
}"""


@resource("arduino://schemas/armodel")
async def armodel_schema() -> str:
    return """{
  "magic": "0x41524D4C (ARML)",
  "version": 2,
  "model_id": "uint32",
  "schema_version": 1,
  "weight_crc": "uint32",
  "weight_length": "uint32",
  "metadata_length": "uint32",
  "flags": "uint32",
  "metadata": "JSON string",
  "weights": "TFLite FlatBuffer"
}"""


def register_resource_handlers():
    """Register all resource handlers."""
    pass  # Handlers are registered via decorator
