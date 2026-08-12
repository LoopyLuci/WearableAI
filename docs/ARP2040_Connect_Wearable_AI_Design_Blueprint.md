# ARP-2040 Connect Wearable Personal Assistant
## Next-Generation Design Blueprint — Production Grade
*Grounded in: ABX00053 datasheet, ABX00053 pinout, ABX00053 schematics, NINA-W10 Data Sheet UBX-17065507 R17*

---

## Table of Contents
1. [Hardware Architecture & Constraints](#1-hardware-architecture--constraints)
2. [Software Architecture Overview](#2-software-architecture-overview)
3. [Dual-Core Utilization Strategy](#3-dual-core-utilization-strategy)
4. [AI/ML Model Design & TinyML Pipeline](#4-aiml-model-design--tinyml-pipeline)
5. [Connectivity Layer — Wi-Fi, BLE, Mesh, & Servers](#5-connectivity-layer--wi-fi-ble-mesh--servers)
6. [Sensor Stack & Environmental Awareness](#6-sensor-stack--environmental-awareness)
7. [Vision Pipeline](#7-vision-pipeline)
8. [Language & Speech Pipeline](#8-language--speech-pipeline)
9. [Learning — Real-Time & Training-Data](#9-learning--real-time--training-data)
10. [Mobile/Desktop Hybrid Server Architecture](#10-mobiledesktop-hybrid-server-architecture)
11. [Power Management & Wearable Optimization](#11-power-management--wearable-optimization)
12. [Security Architecture](#12-security-architecture)
13. [OTA, Recovery, & Field Upgrade](#13-ota-recovery--field-upgrade)
14. [First-Class Individual Use](#14-first-class-individual-use)
15. [Production-Grade Practices](#15-production-grade-practices)
16. [Roadmap](#16-roadmap)
17. [Atomic Operations & Hot Reload](#17-atomic-operations--hot-reload)

---

## 1. Hardware Architecture & Constraints

### 1.1 Actual silicon at your disposal

**RP2040 (U1)**
- 133 MHz dual-core Arm® Cortex®-M0+
- 264 KB SRAM (split across 6 independent banks)
- QSPI bus to 16 MB off-chip flash (AT25SF128A, U5) — XIP capable, 532 Mbps
- USB 1.1 device
- 8 PIO state machines
- 4-channel 12-bit ADC (0.5 MSa/s), internal temperature sensor
- DMA controller
- SWD debug on pads
- 2× PLLs

**NINA-W102 (U2)**
- 240 MHz dual-core Xtensa LX6 (independently programmable via SWD pads)
- 520 KB SRAM + 448 KB ROM + 16 Mbit Flash (hardware-encrypted)
- 1 kbit eFUSE (MAC, config, flash-encryption, chip-ID)
- IEEE 802.11b/g/n single-band 2.4 GHz (15 dBm conducted, 18 dBm EIRP)
- Bluetooth 4.2 + BLE dual-mode (5 dBm BLE, 8 dBm EIRP)
- UART (3×), SPI, I2C, SDIO, CAN, QSPI, RMII, JTAG, 2× DAC, 4× ADC
- Cryptographic hardware accelerators, secure boot
- Power modes: Active, Modem-sleep (20–30 mA), Light-sleep (~800 µA), Deep-sleep (~150 µA), Hibernate (~5 µA)
- PIFA internal antenna (no external antenna on W102)
- **UART0 is the firmware-upgrade path** — must not be routed away

**ATECC608A (U4)**
- SHA-256, HMAC, AES-128/GCM
- NIST SP 800-90A/B/C RNG
- ECDSA secure boot validation
- 1 kbit secure key storage

**LSM6DSOXTR (U9)**
- 6-axis IMU: 3D accelerometer, 3D gyroscope
- Onboard Machine Learning Core (finite-state-machine gesture detection at sensor)
- Step detector/counter, pedometer, significant-motion detection, free-fall, 6D/4D orientation

**MP34DT06JTR (U8)**
- Omnidirectional MEMS microphone
- 64 dB SNR, -26 dBFS ± 1 dB
- PDM digital output → RP2040 PIO input

**AT25SF128A (U5)**
- 16 MB NOR flash on QSPI bus
- XIP (execute-in-place)

### 1.2 Key constraints that govern every design decision

| Resource | Available | Notes |
|---|---|---|
| RP2040 SRAM | 264 KB | Shared by both cores; must partition |
| RP2040 QSPI flash | 16 MB | XIP-capable; store models, logs, code here |
| NINA SRAM | 520 KB | Separate from RP2040; shared Wi-Fi/BLE stack buffer |
| NINA Flash | 16 Mbit (2 MB) | Encrypted; firmware + NINA app code |
| RP2040 ADC | 4× 12-bit | A0–A3; A4–A7 are NINA-side ADC |
| RP2040 GPIO | 30 usable | After USB, QSPI, PDM, I2C, UART |
| NINA GPIO | Multiplexable | UART, SPI, I2C, SDIO, CAN, 4× ADC, 2× DAC |
| Max GPIO sink | 50 mA total | Careful with LED/display loads |
| 3.3V rail | 800 mA max | USB buck regulator |
| RP2040 clock | 133 MHz | Can overclock slightly (125–250 MHz documented) |
| NINA clock | 240 MHz | Fixed |
| Temperature | −20 to +80 °C | Board spec; NINA spec −40 to +85 °C |

**The single biggest constraint is SRAM.** 264 KB on RP2040 and 520 KB on NINA must jointly hold the RTOS kernel, network stacks, sensor buffers, the ML model's feature maps, and inference state. The model, therefore, must be architected for sub-100 KB active SRAM footprint with weights streamed from flash.

### 1.3 Inter-chip communication

The RP2040 and NINA-W102 communicate over UART. The default UART used by the Arduino `WiFiNINA` and `ArduinoBLE` libraries is **UART0** on the RP2040 side. The NINA runs an Espressif ESP32-class firmware that exposes AT commands / native API over this UART.

**Critical constraint:** UART0 on the NINA is also the firmware-upgrade path. If you reroute UART0 away from its default pins, OTA firmware update to the NINA becomes impossible without SWD. **Never route UART0 on NINA.** Use UART1 or UART2 on the NINA for any custom protocol (e.g., a high-bandwidth sensor bridge).

Recommended channel allocation:
- RP2040 ↔ NINA: UART0, 921600 baud (default, AT-command API)
- RP2040 ↔ external sensors: I2C0 (A4=SDA, A5=SCL), up to 400 kHz
- RP2040 ↔ PDM microphone: PIO state machine (bit-banged PDM)
- RP2040 ↔ QSPI flash: native QSPI bus (XIP + data log)

---

## 2. Software Architecture Overview

The firmware is structured in three layers, running across the two processors in a cooperative multi-agent pattern.

```
┌─────────────────────────────────────────────────────────────┐
│  MOBILE/DESKTOP HYBRID SERVER                                 │
│  (phone app / tablet / desktop Electron/PWA)                 │
│  — LLM inference                                              │
│  — Large model training                                       │
│  — Data aggregation & visualization                           │
│  — Long-term memory & context                                 │
│  — Mirror / relay server                                      │
└───────────────┬─────────────────────────────────────────────┘
                │ BLE + Wi-Fi (dual simultaneous)
┌───────────────▼─────────────────────────────────────────────┐
│  ARP-2040 CONNECT — DEVICE FIRMWARE                         │
│                                                              │
│  Layer 3: Application Agents (FreeRTOS / Arduino tasks)     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Voice    │ │ Vision   │ │ Sensor  │ │ Connectivity  │  │
│  │ Agent    │ │ Agent    │ │ Agent   │ │ Agent         │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│                                                              │
│  Layer 2: AI Runtime (TinyML / TensorFlow Lite Micro)       │
│  ┌──────────────────────────────────────────────┐           │
│  │  NLP (keyword + embedding)  │  Vision (CNN)  │           │
│  │  IMU inference              │  Audio (MFCC)  │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
│  Layer 1: Hardware Abstraction (Arduino core + custom HAL)  │
│  ┌──────────────────────────────────────────────┐           │
│  │ RP2040 HAL   │   NINA comms   │  Sensor HAL  │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Framework choice: FreeRTOS + Arduino Core + custom HAL

Do **not** use bare-metal Arduino `loop()` for this. Use **FreeRTOS** on the RP2040 (available via the Arduino-Pico core `RP2040 FreeRTOS` port) to get proper task isolation, priority-based scheduling, and a unified API that runs across both cores.

Recommended stack:
- **Arduino-Pico core** (earlephilhower/arduino-pico) — provides RP2040 FreeRTOS, PIO, USB stack, QSPI, ADC, I2C, SPI, UART
- **WiFiNINA library** (Arduino official) — AT-command interface to NINA-W102
- **ArduinoBLE** or **NimBLE** — BLE on NINA
- **TensorFlow Lite Micro** — inference runtime on RP2040
- **CMSIS-NN or optimized kernels** — for critical operators
- **FatFS / LittleFS** — filesystem on 16 MB QSPI flash for model weights, logs
- **mbedTLS** (lightweight subset) — TLS/DTLS for secure communications
- **ArduinoJson** (or a minimal custom JSON parser) — protocol with mobile server

### 2.2 Code organization

```
firmware/
├── platformio.ini or CMakeLists.txt
├── src/
│   ├── main.cpp                  # FreeRTOS entry point, core affinity
│   ├── hal/
│   │   ├── rp2040_hal.cpp        # RP2040 peripheral init
│   │   ├── nina_hal.cpp          # UART0 AT-cmd transport to NINA
│   │   ├── imu_hal.cpp           # LSM6DSOX I2C driver
│   │   ├── mic_hal.cpp           # PDM via PIO state machine
│   │   ├── crypto_hal.cpp        # ATECC608A via I2C (SWI mode)
│   │   └── flash_hal.cpp         # LittleFS on QSPI flash
│   ├── agents/
│   │   ├── voice_agent.cpp       # VAD, audio feature extraction, ASR
│   │   ├── vision_agent.cpp      # Camera capture + inference
│   │   ├── sensor_agent.cpp      # IMU polling + MLC inference
│   │   ├── env_agent.cpp         # Mic audio scene classification
│   │   └── conn_agent.cpp        # Wi-Fi/BLE/mesh management
│   ├── ai/
│   │   ├── tflite_runtime.cpp    # TFLite Micro integration
│   │   ├── keyword_spotter.cpp   # Quantized 8-bit KWS model
│   │   ├── gesture_model.cpp     # IMU gesture TinyML model
│   │   ├── scene_classifier.cpp  # Audio scene classifier
│   │   └── vision_model.cpp      # Vision TinyML model
│   ├── learning/
│   │   ├── incremental.cpp       # Online weight update logic
│   │   ├── federated.cpp         # Federated averaging protocol
│   │   └── buffer_manager.cpp    # Circular sample buffer
│   ├── transport/
│   │   ├── proto.cpp             # Binary protocol (mobile server)
│   │   ├── wifi_server.cpp       # TCP + HTTP on NINA
│   │   ├── ble_service.cpp       # BLE GATT services
│   │   └── mesh.cpp              # Wi-Fi/BLE hybrid routing
│   └── utils/
│       ├── power_mgr.cpp         # Power state machine
│       ├── logger.cpp            # Ring buffer → QSPI flash log
│       └── security.cpp          # ATECC608A wrapper
├── models/
│   ├── kws_8bit.tflite           # Quantized keyword spotter
│   ├── imu_gesture.tflite        # IMU gesture model
│   └── ...
└── tests/
    ├── test_imu_hal.cpp
    ├── test_voice_features.cpp
    └── ...
```

---

## 3. Dual-Core Utilization Strategy

This is where the board's unique capability becomes a genuine competitive advantage over single-core wearable solutions.

### 3.1 Core partitioning

**Core 0 (RP2040) — "Perception & Inference"**
- Voice agent (audio capture, MFCC feature extraction, TFLite inference for KWS)
- Sensor agent (IMU polling at 100 Hz, LSM6DSOX MLC result reading)
- Vision agent (if camera attached via PIO/SPI)
- Logger
- FreeRTOS task scheduler runs here; Core 1 is launched as a worker

**Core 1 (RP2040) — "Connectivity & Orchestration"**
- NINA UART comms (WiFiNINA library runs blocking-ish)
- BLE stack (NimBLE)
- Wi-Fi server (TCP listener, HTTP responses)
- Federated learning client
- Data aggregation & packetization before offload to mobile

**NINA-W102 dual Xtensa cores — "Radio & Secure Gateway"**
- Core A: Wi-Fi TCP/IP stack, BLE stack
- Core B: AT-command interpreter, firmware update handler
- The user does not directly program these cores; they run Espressif firmware
- The RP2040 talks to NINA via AT-command API over UART0

### 3.2 Inter-core communication

Use a **lock-free ring buffer** between Core 0 and Core 1 via the RP2040's shared SRAM. The ring buffer carries:
- `VoiceResult` struct: `{bool keyword_detected, char keyword[16], float confidence, uint32_t timestamp}`
- `SensorResult` struct: `{float accel[3], float gyro[3], uint8_t gesture_id, uint32_t timestamp}`
- `InferenceRequest` struct: `{uint8_t agent_id, uint8_t payload[64]}`

Avoid `xQueue` for high-throughput sensor paths (IMU at 100 Hz = 10 ms budget per sample); use `spinlock_mutex` + `volatile` ring buffer. Use `xQueue` / `xTaskNotify` only for low-frequency events (keyword detected, connection state change).

### 3.3 FreeRTOS task design

```
Core 0 tasks (priority high→low):
  voice_task        (pri 4, 100 Hz audio frame ISR → feature extraction)
  imu_task          (pri 3, 100 Hz IMU poll)
  vision_task       (pri 3, if camera present)
  inference_task    (pri 2, TFLite invoke, block on inference_request queue)
  logger_task       (pri 1, batch writes to LittleFS)

Core 1 tasks (priority high→low):
  nina_comms_task   (pri 4, UART0 ISR-driven, AT command state machine)
  ble_task          (pri 3, BLE GATT event handler)
  server_task       (pri 2, TCP socket accept/read/write)
  federated_task    (pri 2, batch aggregation + send)
  power_task        (pri 1, 1 Hz power-state monitor)
```

Critical constraint: **TFLite `Invoke()` must run in a single non-preempted block.** Allocate its heap in Core 0's SRAM bank 0 and raise its priority to maximum for the duration of inference. A typical TinyML model at 8-bit quantization runs in 5–50 ms on a 133 MHz Cortex-M0+, well within the budget.

---

## 4. AI/ML Model Design & TinyML Pipeline

### 4.1 The fundamental architecture decision

This device cannot run a large language model. What it *can* do is run a **stack of specialized, quantized, edge-optimized models** that together approximate the capabilities of a personal assistant. The "intelligence" is distributed:

```
On-device (always-on, sub-100 KB SRAM):
  • Keyword Spotting (KWS) — 5–20 keywords + silence, 8-bit quantized
  • Audio Scene Classifier — home/office/outdoor/noisy, 8-bit
  • IMU Gesture Recognizer — wrist-tap, shake, flick, nod, 8-bit
  • Anomaly Detector (IMU + audio energy) — fall detection, anomaly flag

Off-device (mobile/desktop server):
  • Full NLP LLM (phi-3-mini, Llama-3.2-1B, etc.)
  • Vision-language model (for camera frames)
  • Contextual memory, conversation history
  • Model fine-tuning
```

The on-device models serve as **the always-on trigger and pre-processor**. They decide when to wake the full stack, compress raw sensor data into semantic tokens, and answer simple queries locally.

### 4.2 Model selection and constraints

**Keyword Spotting (KWS)**
- Architecture: Depthwise-separable CNN (MobileNet-style) or CRDNN
- Input: 1-second window of log-MFCCs (e.g., 40 mel bands × 98 time frames = 3,920 features)
- Recommended: **MicroNet** or **TinyCNN** from Google's speech_commands benchmark
- Quantized to int8; SRAM footprint: ~20–40 KB for activations
- Flash storage for weights: ~40–80 KB (fits easily in NINA flash or RP2040 QSPI XIP)
- Target keywords: "Hey ARP", "stop", "help", "yes", "no", "call", "remind", "time", "weather", plus silence/noise classes
- Multi-language: train separate models or use a single multilingual model (more SRAM but one model)

**IMU Gesture Recognition**
- Use the **LSM6DSOX embedded Machine Learning Core** for simple, always-on gesture detection at the sensor level
- The MLC is a hardware finite-state machine that can detect 8 patterns without waking the main CPU
- Program it via I2C register writes
- For complex gestures: run a TinyML model on the RP2040
- Recommended: **1D CNN** on 2-second IMU window (accel + gyro, 100 Hz = 600 samples)
- Quantized to int8; ~15–30 KB activation memory

**Audio Scene Classification**
- Same MFCC pipeline as KWS, different classifier head
- Classes: quiet, conversation, music, noise, alarm
- TinyML model; 8-bit quantized; ~30 KB SRAM

**Vision (if camera attached)**
- The Nano RP2040 Connect does not have a camera connector by default. Add one via:
  - **Arduino Nano 33 BLE Vision** style: OV7675 via parallel interface → RP2040 PIO
  - **Serial camera (OV2640/5640)**: SPI or SCCB/I2C → slower but uses existing I2C
  - **External lightweight camera**: Arducam Mini 2MP with SPI interface
- Model: quantized MobileNetV1 (224×224 → 1000 classes) is ~200 KB SRAM; too large
- Use **MobileNetV1 96×96** or **EfficientNet-Lite0 128×128** with int8 quantization; ~80–150 KB activations
- Accept 5–10 fps; good enough for object/scene tagging

### 4.3 Model training pipeline

```
Host PC (or mobile server):
  1. Collect training data (audio, IMU, optionally camera)
     - Use the device itself to collect in-field data
     - Or simulate/augment on host
  2. Train in TensorFlow / PyTorch on host
  3. Post-train quantization: int8 with full-integer quantization
     - Use representative dataset for quantization calibration
     - Verify accuracy drop < 2% vs float32
  4. Convert to TFLite FlatBuffer (.tflite)
  5. Validate with TFLite Micro on host (using C simulator or QEMU)
  6. Deploy to device:
     a. OTA push via Wi-Fi/BLE (preferred)
     b. Staged roll-out: load to QSPI flash, atomic swap on next boot
     c. Fallback: USB mass-storage + reboot
  7. Shadow-test: run new model in parallel, compare outputs, auto-revert if degradation
```

### 4.4 Memory budget (target)

| Component | SRAM (active) | Flash (weights) | Notes |
|---|---|---|---|
| FreeRTOS + HAL overhead | ~20 KB | ~50 KB | Fixed |
| NINA UART comms buffer | ~8 KB | — | Double-buffered |
| Voice agent (PDM DMA) | ~4 KB | — | Circular DMA buffer |
| MFCC feature extraction | ~8 KB | — | On-the-fly, no audio storage |
| KWS TFLite model | ~35 KB | ~60 KB (int8 weights) | 98-frame context window |
| IMU gesture TFLite | ~25 KB | ~30 KB | 2-second window |
| LSM6DSOX MLC config | — | ~200 bytes | Sensor-side |
| Audio scene model | ~20 KB | ~40 KB | |
| Federated weight delta buffer | ~15 KB | — | Encrypted staging |
| **TOTAL SRAM** | **~135 KB** | **~130 KB** | Within 264 KB budget ✓ |
| Unallocated reserve | ~129 KB | — | For future expansion |

This budget is tight but achievable. The key design principle: **never hold raw audio or raw IMU in SRAM.** Process in-place via PIO DMA, extract features, discard raw samples.

---

## 5. Connectivity Layer — Wi-Fi, BLE, Mesh, & Servers

### 5.1 What the NINA-W102 actually provides

From the datasheet:
- **Wi-Fi:** IEEE 802.11b/g/n, 2.4 GHz, channels 1–13 (region-limited), 15 dBm conducted, 18 dBm EIRP
- **Bluetooth:** BR/EDR (Classic) + BLE 4.2 dual-mode, 5 dBm BLE, 8 dBm EIRP, up to 7 BLE slaves
- **Antenna:** Internal PIFA (no external antenna connector on W102)
- **UART-based AT-command API** (Arduino WiFiNINA library wraps this)
- **Secure boot** on NINA firmware (cannot be bypassed)

The NINA is a **co-processor**, not a network processor that the RP2040 simply attaches. You must command it via AT-style commands or use its native API. For maximum control (servers, mesh), use the **Native API mode** if available in the NINA firmware, or implement a custom protocol over UART0.

### 5.2 Wi-Fi server on NINA

The Arduino `WiFiNINA` library supports AP mode and server mode. However, the NINA's internal TCP/IP stack has memory constraints. Design guidelines:

- **Maximum simultaneous connections:** 5–8 TCP sockets (NINA has ~520 KB shared SRAM)
- **Use lightweight protocol:** binary protobuf or MessagePack, not JSON, for on-device traffic
- **Server modes:**
  - **TCP server** on port 8888 (device control, raw sensor stream)
  - **HTTP server** on port 80 (simple REST API for mobile app, OTA model download)
  - **WebSocket** (if NINA firmware supports it) for real-time bi-directional stream
- **Wi-Fi Direct / Wi-Fi P2P:** The NINA does NOT support Wi-Fi P2P natively. Use **SoftAP + BLE** as the pairing mechanism, then switch to station mode for data transfer.

### 5.3 BLE as the "always-on" channel

BLE is the right always-on channel because:
- NINA Deep-sleep mode retains BLE connections (via RTC + ULP co-processor)
- BLE advertising is a valid device-discovery protocol
- BLE GATT can carry compressed inference results, sensor summaries, and control commands

Recommended GATT services:
- **Device Information Service** (standard)
- **Custom Inference Service** (notify on keyword detection, gesture)
- **Custom Sensor Service** (notify/indicate IMU + audio energy)
- **Custom Control Service** (write commands: change mode, trigger inference, etc.)
- **Custom Model Transfer Service** (write large payload in chunks for OTA models)

Use **NimBLE** (nimble-based BLE stack, lighter than ArduinoBLE) to reduce memory.

### 5.4 Hybrid Wi-Fi + BLE mesh

True mesh (Thread/IEEE 802.11s) is not available on this hardware. However, you can implement a **practical hybrid mesh**:

**BLE Mesh (Mesh networking via BLE advertising + GATT)**
- Use BLE advertising to discover neighboring ARP-2040 devices
- Each device maintains a peer table (up to ~16 BLE connections on NINA)
- Relay inference results and sensor data hop-by-hop
- Use a simple flooding protocol with TTL (max 3 hops to avoid broadcast storm)
- Rate-limit: 1 relay message per 5 seconds per device

**Wi-Fi Mesh (Ad-hoc + routing)**
- NINA does NOT support IEEE 802.11s mesh natively
- Workaround: **SoftAP + station relay**
  - Device A runs SoftAP; Device B connects as station
  - Device C connects to Device A's SoftAP
  - Device B acts as a relay (TCP forwarder) between Device C and Device A
  - This creates a 3-node star-topology "mesh" through SoftAP chaining
- Practical limit: 2–3 hops due to bandwidth constraints
- Use this to extend BLE range when devices are within Wi-Fi range

**Role of mobile/desktop server:**
- The phone/desktop is the **gateway root**: always connected to at least one device via BLE, optionally via Wi-Fi
- All long-range connectivity (internet, cloud) routes through the mobile/desktop gateway
- The device never needs to connect to a public Wi-Fi network directly
- This also serves as the **data aggregation point** for federated learning

### 5.5 Connection state machine

```
States: DEEP_SLEEP → BLE_ADVERTISING → BLE_CONNECTED → 
        WIFI_CONNECTING → WIFI_CONNECTED → ACTIVE_SYNC

Transitions:
  DEEP_SLEEP → BLE_ADVERTISING  (IMU wake event or timer)
  BLE_ADVERTISING → BLE_CONNECTED (incoming connection)
  BLE_CONNECTED → ACTIVE_SYNC (BLE link sufficient for data)
  BLE_CONNECTED → WIFI_CONNECTING (user-initiated sync, large transfer)
  WIFI_CONNECTING → WIFI_CONNECTED (associated + DHCP)
  WIFI_CONNECTED → ACTIVE_SYNC (TCP server ready)
  ACTIVE_SYNC → BLE_CONNECTED (sync complete)
  BLE_CONNECTED → BLE_ADVERTISING (connection lost, keep advertising)
  BLE_ADVERTISING → DEEP_SLEEP (timeout, no activity)
```

---

## 6. Sensor Stack & Environmental Awareness

### 6.1 Onboard sensors (fully specified in datasheet)

**LSM6DSOX 6-axis IMU (I2C address 0x6A)**
- Accelerometer: ±2/±4/±8/±16 g, configurable ODR up to 6.66 kHz
- Gyroscope: ±125/±250/±500/±1000/±2000 dps
- Embedded **MLC (Machine Learning Core)**: finite-state-machine gesture detection at sensor
- Hardware interrupts: free-fall, wake-up, 6D/4D orientation, click, double-click, tilt
- Significant Motion Detection (SMD)
- Step detector/counter with pedometer
- Temperature sensor onboard

**Recommended IMU config for wearable:**
```c
// Accelerometer: ±4 g, 50 Hz ODR (wearable motion band)
// Gyroscope: ±500 dps, 50 Hz ODR
// Enable MLC for wrist-tap, shake, fall detection
// Enable Step Counter for activity tracking
// Enable Significant Motion Detection as wake source
// Connect INT1 to RP2040 GPIO as interrupt (not used on Nano RP2040 Connect
// by default, but can be wired via breakout headers JP2)
// Poll at 100 Hz via I2C in imu_task
```

**Note:** On the Arduino Nano RP2040 Connect, the IMU is hardwired to the RP2040's I2C bus (A4=SDA, A5=SCL). There is no separate INT line broken out to headers by default. You must poll at 50–100 Hz, or modify the board to route INT1. Given the always-on nature, polling at 50 Hz uses minimal CPU.

**MP34DT06J MEMS Microphone (PDM)**
- PDM digital output → RP2040 PIO state machine
- Use one of the 8 PIO state machines for PDM → PCM conversion
- Configure PIO to sample at 2× or 4× the target audio rate (1.536 MHz for 48 kHz audio)
- DMA the PIO FIFO into a circular buffer in SRAM (4 KB ring buffer)
- Extract 10 ms frames for MFCC computation

**ATECC608A Crypto Chip (I2C)**
- Use for:
  - Device identity (unique serial from eFUSE, signed challenge-response)
  - Secure storage of Wi-Fi credentials, BLE pairing keys
  - Message signing for firmware OTA
  - TLS session key derivation (shared secret → session keys)

### 6.2 External sensor expansion (via headers)

The board exposes 30 GPIO pins through JP1 and JP2 headers. For a personal assistant, the most valuable external sensors:

| Sensor | Interface | Use Case |
|---|---|---|
| BMP280 / BME280 | I2C | Temperature, pressure, altitude (context awareness) |
| SGP30 / CCS811 | I2C | Air quality, eCO2, TVOC (health monitoring) |
| VEML7700 | I2C | Ambient light (screen brightness, sleep/wake) |
| MAX30102 | I2C | Heart rate / SpO2 (wearable health) |
| VL53L0X | I2C | Time-of-flight proximity (gesture near-field) |
| DS18B20 | 1-Wire (PIO bit-bang) | External temperature probe |
| GPS (u-blox NEO-6M/8M) | UART1 | Location context |
| OLED display (SSD1306/SH1106) | I2C or SPI | Status display, interaction feedback |

### 6.3 Environmental awareness logic

The "awareness" agent fuses data from all sensors into a context state vector updated at 1 Hz:

```c
struct ContextState {
  // IMU
  bool is_moving;
  ActivityType activity; // still, walking, running, unknown
  bool was_shaken;
  // Audio
  AudioScene scene; // quiet, conversation, music, noise
  float audio_energy_db;
  bool voice_active;
  // Environmental
  float temperature_c;
  float humidity_pct;
  float pressure_hpa;
  float altitude_m;
  int co2_ppm;
  int light_lux;
  // Time
  uint32_t unix_timestamp;
  bool is_night;
  // Health (if PPG attached)
  int heart_rate_bpm;
  int spo2_pct;
  // Device state
  bool wifi_connected;
  bool ble_connected;
  bool mobile_gateway_nearby;
  PowerState power_state;
};
```

This context vector is:
1. Used locally for rule-based triggers (e.g., "if night + still + no voice → sleep mode")
2. Sent as compressed state to mobile server for LLM context
3. Logged to QSPI flash for personal analytics

---

## 7. Vision Pipeline

The RP2040 Connect does not ship with a camera. Adding one requires careful bandwidth planning.

**Option A: OV7670 parallel camera → RP2040 PIO**
- Use 2 PIO state machines to bit-bang SCCB/I2C control + parallel data capture
- Grayscale 80×80 at 10 fps = 64,000 bytes/sec → manageable via DMA
- Run a quantized MobileNetV1 96×96 on 80×80 input (resize in-place)
- ~80 ms inference on 133 MHz Cortex-M0+ (acceptable for scene classification)
- Use case: object detection, scene tagging, QR code scanning

**Option B: Serial camera (e.g., OV2640 in JPEG mode) → SPI or I2C**
- Slower but uses existing SPI or I2C bus
- Capture full-resolution JPEG, send to mobile server for full VLM
- On-device: just detect "camera event" and send image blob

**Option C: No camera on-device — phone as camera**
- When mobile phone is connected via BLE, trigger phone camera capture
- Phone sends image to mobile server
- Mobile server runs full vision-language model (phi-3-vision, LLaVA, etc.)
- Result is sent back to device as text + structured action

This is the **recommended approach for production** because it puts the heavy vision model on a device with real GPU/GPU-class compute, avoids bandwidth constraints on the NINA Wi-Fi link, and dramatically reduces device power consumption.

The device's role in vision is:
1. Decide *when* to ask for a visual input (via IMU tilt toward user, voice command "look at this", periodic context sampling)
2. Send a vision request to the mobile gateway
3. Receive structured result: `{label, confidence, bounding_box, description}`
4. Act on it or relay it to user via audio

---

## 8. Language & Speech Pipeline

### 8.1 On-device speech

The complete on-device speech pipeline:

```
PDM mic → PIO DMA → 16 kHz PCM circular buffer
  → 10 ms frame hop (160 samples)
    → MFCC computation (40 mel bands, 25 ms window, 10 ms hop)
      → Sliding window of 98 frames (0.98 seconds context)
        → TFLite KWS inference (int8 CNN)
          → Keyword detected? → Wake event to orchestrator
```

**MFCC computation on RP2040:**
- FFT: use `kissfft` (single-file, no dependencies) or implement a 512-point real FFT
- Mel filterbank: 40 triangular filters, precompute weights, dot-product
- Log + DCT (type-II, first 13 coefficients)
- Total compute: ~2–3 ms per frame at 133 MHz — easily fits in 10 ms budget

### 8.2 On-device NLP (lightweight)

For local commands (no mobile gateway), the device needs a **keyword → action** mapping:

```
Keyword detected → command parser
  "hey arp [command] [args]"
  → action dispatcher
  → execute locally or send to mobile server

Supported local commands:
  "hey arp what time" → RTC read + TTS announcement (via BLE to phone)
  "hey arp my heart rate" → read MAX30102 + speak via BLE
  "hey arp log this" → start 30-second sensor/audio log
  "hey arp stop" → stop current action / alert emergency contact
  "hey arp help" → emergency alert: BLE broadcast + SMS via phone
  "hey arp [reminder text]" → store to flash, announce at time
```

### 8.3 Mobile-gateway NLP (full LLM)

When connected to the mobile/desktop server:
1. Device sends text transcript (from on-device KWS) or compressed audio blob
2. Mobile server sends transcript to local LLM (phi-3-mini-4k, Llama-3.2-1B, etc.)
3. LLM returns structured intent + action plan
4. Action plan is serialized as a compact binary command to device

Intent examples:
- `{intent: "query", target: "weather", location: "current"}` → device reads BME280 temperature, server fetches weather
- `{intent: "log_activity", duration: "5m"}` → device records sensor stream
- `{intent: "alert_contact", message: "fall detected", priority: "high"}` → device triggers BLE alert + server sends SMS
- `{intent: "set_reminder", time: "18:00", text: "take medication"}` → store in flash RTC alarm

### 8.4 TTS output

The device does not have a speaker. Audio output routes:
1. **BLE audio:** BLE HID keyboard (type answers as text input on phone)
2. **BLE GATT notification:** send short text to phone app for TTS
3. **Phone app TTS:** using native platform TTS engine (most natural)
4. **Vibration motor** (if attached via GPIO): haptic feedback for alerts

---

## 9. Learning — Real-Time & Training-Data

### 9.1 Three learning modes

**Mode 1: On-device incremental learning (lightweight)**
- For KWS and IMU models: apply **on-device fine-tuning** using LoRA-style low-rank updates
- Each LoRA update is ~1–2 KB (rank-4, 8-bit), easily staged in flash
- Triggered after every N (e.g., 100) new labeled samples
- Requires: (a) ground-truth label, (b) feature vector, (c) loss computation
- Loss computation on RP2040: simple cross-entropy over softmax output vs. label
- Optimizer: SGD with momentum (1-bit quantization for optimizer states)
- Aggregate gradient over mini-batch, then commit delta to flash

```c
// Conceptual on-device LoRA update
void apply_lora_update(uint8_t* feature, uint8_t label) {
  float grad = compute_cross_entropy_grad(feature, label);
  lora_accumulate(grad, feature);  // rank-4 update to adapter weights
  if (sample_count % BATCH_SIZE == 0) {
    lora_commit();  // write 2 KB delta to QSPI flash staging area
    send_federated_delta_to_mobile();  // or queue for next sync
  }
}
```

**Mode 2: Federated learning (with mobile server as aggregator)**
- Mobile server collects model deltas from multiple enrolled devices
- Runs FedAvg (Federated Averaging) on collected deltas
- Produces a new global model version
- Distributes back to devices via OTA
- This is the key "learns from community" mechanism
- Delta signing with ATECC608A private key prevents poisoning attacks

**Mode 3: Host-based retraining (full training)**
- When enough new data accumulates (e.g., 1000+ labeled samples), trigger full model retraining on host/server
- User can label samples via phone app
- New model validated against held-out test set
- Deployed as OTA model update with shadow-test phase

### 9.2 Data collection and labeling

Data is stored in a structured format on QSPI flash:

```c
struct SampleHeader {
  uint32_t magic;        // 0x41525030 ("ARP0")
  uint32_t version;
  uint32_t sample_id;
  uint32_t timestamp_unix;
  uint8_t  modality;     // AUDIO, IMU, VISION, CONTEXT
  uint8_t  sensor_rate_hz;
  uint16_t sample_count; // number of frames in this record
  uint16_t feature_dim;  // dimension of extracted features
  uint8_t  label_valid;  // 1 if label is set
  uint8_t  label;        // user-assigned or auto-assigned label
  uint32_t reserved;
  float    confidence;   // auto-label confidence
};
```

Raw data is **not** stored on-device due to flash/SRAM constraints. Only **extracted features** (MFCCs, IMU windows) and **metadata** are stored. This is also privacy-preserving.

Labeling workflows:
- **Explicit:** User says "that was [label]" within 5 seconds of an event → label applied retroactively
- **Implicit:** KWS confidence > 0.95 + no correction within 3 seconds → auto-label
- **Active learning:** Mobile server detects model uncertainty, prompts user "what was that sound?"

---

## 10. Mobile/Desktop Hybrid Server Architecture

This is where the "absolute smallest footprint on the Arduino itself" requirement is satisfied: the heavy compute lives on the paired device, not on the RP2040.

### 10.1 Architecture diagram

```
┌───────────────────────────────────────────────────────────────┐
│ MOBILE / DESKTOP (phone, tablet, PC)                          │
│                                                               │
│ ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│ │ Local LLM   │  │ Vision LM    │  │ Data Store          │   │
│ │ (phi-3-mini │  │ (LLaVA /     │  │ (SQLite / indexed   │   │
│ │  1B-3B)     │  │  phi-3-v)    │  │  JSONL on disk)     │   │
│ └──────┬──────┘  └──────┬───────┘  └──────────┬──────────┘   │
│        │                │                      │              │
│ ┌──────▼────────────────▼──────────────────────▼──────────┐   │
│ │              Inference Orchestrator                       │   │
│ │  • Intent parsing  • Action planning  • Memory retrieval  │   │
│ │  • Context management  • Multi-device coordination        │   │
│ └───────────────────────────────────┬──────────────────────┘   │
│                                    │                          │
│ ┌───────────────────────────────────▼──────────────────────┐   │
│ │           Connection Layer                                │   │
│ │  BLE GATT client  │  TCP server  │  WebSocket server     │   │
│ └───────────────────────────────────┬──────────────────────┘   │
│                                    │                          │
└────────────────────────────────────┼──────────────────────────┘
                                     │ BLE + Wi-Fi
┌────────────────────────────────────▼──────────────────────────┐
│  ARP-2040 CONNECT                                             │
│  (on-device: wake word, feature extraction, lightweight ML)   │
└────────────────────────────────────────────────────────────────┘
```

### 10.2 Transport protocol between device and server

**Protocol design principles:**
- Binary encoding (MessagePack or custom TLV) — minimal bytes over air
- Request/response pattern for commands, publish/subscribe for sensor streams
- All messages are 32-bit length-prefixed for framing over TCP
- BLE uses ATT MTU up to 512 bytes (negotiated); chunk large payloads

**Message types:**

| Type | Direction | Purpose |
|---|---|---|
| `VOICE_EVENT` | Device → Server | KWS result: `{keyword, confidence, timestamp}` |
| `SENSOR_SNAPSHOT` | Device → Server | Compressed context state: ~100 bytes |
| `IMU_BUFFER` | Device → Server | 5-second IMU window: ~1 KB compressed |
| `AUDIO_BLOB` | Device → Server | Compressed audio for transcription: ~5–20 KB |
| `COMMAND` | Server → Device | Structured intent: ~50–200 bytes |
| `MODEL_PUSH` | Server → Device | New TFLite model: 40–200 KB |
| `MODEL_DELTA` | Device ↔ Server | Federated LoRA delta: ~1–2 KB |
| `ALERT` | Device → Server | Emergency: `{type, location, timestamp}` |
| `CONFIG` | Server → Device | Update thresholds, sampling rates, model selection |
| `TIME_SYNC` | Server → Device | NTP-style timestamp correction |

### 10.3 Mobile app design

**Platform recommendation:** **Flutter** (single codebase for iOS + Android) with platform channels for:
- BLE (via `flutter_blue_plus` or `reactive_ble`)
- Wi-Fi hotspot management (for device SoftAP mode)
- Local LLM inference (via `llama.cpp` bindings or `flutter_ai_toolkit`)
- Background execution (for always-on BLE listener)
- Notifications and TTS output
- SQLite for local data persistence

**Desktop app:** **Electron** (or Tauri for smaller footprint) with:
- Node.js BLE library (`@abandonware/noble` or `bleak` via Python backend)
- llama.cpp or Ollama integration for local LLM
- SQLite or better-sqlite3 for data store
- WebSocket server for browser-based dashboard
- Electron's auto-updater for desktop app updates

**Minimum viable mobile app features:**
1. Device discovery (BLE scan for ARP-2040)
2. Pairing (ATECC608A challenge-response over BLE)
3. Connection status + signal strength
4. Live sensor stream (IMU, audio energy, context)
5. Voice command transcript display
6. LLM chat interface
7. Model update management
8. Data export (CSV/JSON for personal analytics)
9. Emergency alert configuration + contacts

### 10.4 Desktop as primary gateway

For personal use, the desktop app is the **preferred gateway** because:
- Runs full LLM with no mobile hardware constraints
- No background-app restrictions (runs 24/7 on desktop)
- Large storage for long-term data
- Can expose a local web dashboard (localhost:3000) for visualization
- Can act as Wi-Fi AP for the device if needed
- Always-on sync keeps device state fresh

The mobile app is the **portable extension**:
- Connects when user is away from desktop
- Runs smaller model (phi-3-mini-2k or similar)
- Syncs back to desktop when reconnected

---

## 11. Power Management & Wearable Optimization

### 11.1 Power states and transitions

Based on the NINA datasheet power consumption data:

| State | NINA current | RP2040 current (typ) | Use Case |
|---|---|---|---|
| **Active** | 130 mA (BLE TX) / 95 mA (Wi-Fi) | ~40–80 mA (core active, peripherals) | Inference, data transfer |
| **Modem-sleep** | 20–30 mA | ~10 mA | Wi-Fi associated, idle |
| **Light-sleep** | ~800 µA | ~5–10 mA (DORMANT) | BLE connected, standby |
| **Deep-sleep** | ~150 µA | ~5 µA (DORMANT) | BLE advertising, timer wake |
| **Hibernate** | ~5 µA | ~2 µA (RTC only) | Long-term standby |

**RP2040 low-power modes:**
- `rp2040.idle_other_core()` — idle Core 1
- `rp2040.sleep()` — CPU halt, clocks off, DMA/WDT/runtime wake
- `rp2040.hibernate()` — RTC only, 2 µA; wake on GPIO/RTC alarm

### 11.2 Wearable power strategy

```c
// Default wearable state machine
typedef enum {
  STATE_ACTIVE,        // User interacting, inference running
  STATE_STANDBY,       // Light-sleep, BLE connected, IMU polling at 10 Hz
  STATE_IDLE,          // Deep-sleep, BLE advertising, wake on IMU/timer
  STATE_HIBERNATE      // RTC only, wake on daily sync or significant motion
} PowerState;

// Automatic transitions:
//   User motion detected (IMU)  → IDLE → STANDBY
//   KWS keyword detected        → IDLE → ACTIVE
//   BLE connection established  → IDLE → STANDBY
//   No activity for 5 min       → STANDBY → IDLE
//   No activity for 1 hour      → IDLE → HIBERNATE
//   User tap gesture            → HIBERNATE → IDLE
//   Timer alarm (RTC)           → HIBERNATE → STANDBY (check mobile)
```

**Power budget for typical wearable day:**

| Scenario | Active time | Current (avg) | Battery (500 mAh LiPo) |
|---|---|---|---|
| Heavy use (2 hrs) | 2 h @ 100 mA | ~100 mA | 5 h runtime |
| Moderate use (30 min) | 0.5 h @ 80 mA | ~20 mA avg | 25 h |
| Light use | 10 min @ 50 mA | ~10 mA avg | 50 h |
| Idle/wear | 23.5 h @ 1 mA | ~1 mA | 500 h (21 days) |

With a 500 mAh LiPo, expect **3–7 days** of real-world use depending on interaction frequency. Optimize further:
- Reduce IMU polling to 10 Hz in standby (still captures significant motion)
- Use LSM6DSOX hardware SMD (Significant Motion Detection) as true wake source
- Batch BLE notifications (notify every 100 ms, not every sample)
- Defer Wi-Fi to explicit user action only

### 11.3 Power-aware inference

The inference task runs at different rates depending on power state:
- **Active:** Full 100 Hz IMU + continuous audio KWS
- **Standby:** 10 Hz IMU polling + MLC hardware gesture detection + periodic 1-second audio snapshots (every 30 seconds)
- **Idle:** MLC-only; RP2040 in DORMANT between MLC interrupts
- **Hibernate:** MLC off; wake on RTC timer only

The MLC is the secret weapon: it runs on the IMU chip itself, consuming microamps, and can wake the RP2040 via interrupt only when a meaningful gesture occurs. Most of the time, the RP2040 is fully asleep.

---

## 12. Security Architecture

### 12.1 Device identity

- **ATECC608A** generates a unique ECDSA keypair at manufacture (key never leaves chip)
- Device public key is the device's identity fingerprint
- Server stores public key; device proves identity via challenge-response

### 12.2 Pairing & communication security

- **BLE pairing:** Use Secure Connections (LE Secure Connections, not Just Works)
  - ATECC608A assists with ECDH key exchange
  - MITM protection via numeric comparison or OOB (out-of-band) confirmation
- **Wi-Fi:** mbedTLS-based TLS 1.2/1.3 for all TCP connections
  - Pre-shared device certificate (ATECC608A signs CSR)
  - Server validates device cert before accepting data
- **Data at rest on QSPI flash:** AES-128 encryption (ATECC608A provides key, RP2040 AES hardware via PIO or bit-banged)

### 12.3 OTA security

- All OTA model/firmware blobs are signed with ECDSA (ATECC608A private key on host side)
- RP2040 verifies signature using ATECC608A public key (stored in eFUSE)
- Boot chain: RP2040 bootloader → verify NINA firmware signature → boot NINA → verify RP2040 app signature
- Anti-rollback: firmware version number stored in ATECC608A; downgrade attempts rejected

### 12.4 Privacy

- Raw audio and IMU data never leave the device without explicit user consent
- Only extracted features and text transcripts are transmitted to server
- User owns all data; server stores only what user permits
- Device-side data deletion: secure erase of QSPI flash sectors (ATECC608A can assist with key destruction)
- Federated learning deltas are anonymous (no device identity in delta payload)

---

## 13. OTA, Recovery, & Field Upgrade

### 13.1 NINA firmware OTA

The NINA firmware is upgraded via UART0 using Espressif's serial download protocol. The RP2040 acts as the host. Implement as:
1. Download new NINA firmware blob from server via Wi-Fi (NINA running old firmware)
2. Store blob on RP2040 QSPI flash (staging area)
3. Reset NINA into download mode (toggle RESET_N while holding GPIO low)
4. RP2040 streams firmware to NINA via UART0 at 115200 baud
5. NINA reboots with new firmware
6. RP2040 verifies NINA is responsive; erases staging area

**Fallback:** If NINA firmware update fails, NINA falls back to factory firmware (16 Mbit internal flash has dual-bank boot).

### 13.2 RP2040 application OTA

Since the RP2040 boots from its internal flash (2 MB ROM bootloader), OTA works via:
1. Download new firmware blob to QSPI flash (staging partition)
2. Reset RP2040 into BOOTSEL mode (double-tap reset button or RP2040-initiated)
3. Bootloader copies new firmware from QSPI flash to internal flash
4. RP2040 reboots; verifies signature; runs new firmware

**Atomic swap pattern:**
- QSPI flash layout: `[current_app | new_app_staging | log_ring | model_storage]`
- On boot: if staging CRC valid and version > current → copy to current, erase staging
- If copy fails → boot from current (no brick)

### 13.3 Model OTA (no full firmware update needed)

Models are stored on QSPI flash as TFLite FlatBuffers. OTA model update:
1. Server pushes new `.tflite` file (40–200 KB) via TCP or BLE
2. Device stores to `model_staging` partition
3. On next boot, run **shadow test**: execute new model on last 100 cached samples
4. If new model accuracy ≥ old model → promote `staging` → `active`
5. If degraded → keep old model, report metrics to server, trigger full retrain

---

## 14. First-Class Individual Use

The design decisions above should all serve the end user: a person wearing this device. Here are the specific features that make this genuinely useful for personal use.

### 14.1 Privacy-first by design

- **No cloud dependency for basic functionality.** KWS, IMU tracking, and local commands work without any network.
- **User owns all data.** Local SQLite on mobile/desktop, device QSPI flash is user-writable.
- **No telemetry by default.** All analytics are opt-in, anonymous, and user-controlled.
- **Device is identifiable by user only.** No serial numbers in transmitted data without consent.

### 14.2 Invisibility principle

The best wearable is one the user forgets they're wearing. Design targets:
- **Always-on wake word** ("Hey ARP") → no button press
- **Haptic + bone-conduction audio** (if attached to wrist) for private output
- **Smart alerting:** only notify via audio/vibration for genuinely important events; use screen-only for informational
- **Context-aware quiet:** detects when user is in meeting (audio scene) → suppresses voice output, uses BLE text notification only

### 14.3 Personalization

Every user is different. The learning pipeline is designed for per-user personalization:

- **Voice:** On-device KWS adapts to user's accent, cadence, and common phrases via incremental learning. Start with generic model, fine-tune after 50–100 user samples.
- **Gestures:** IMU model personalizes to user's movement patterns (hand size, typical motion)
- **Context:** Location + time + activity patterns become user-specific. "Your commute" means the user's commute, not a generic one.
- **LLM persona:** The mobile/desktop LLM is configured with user's preferences, contacts, calendar, and history. This is the main personalization layer.
- **Style:** LLM learns user's communication style (formal, casual, terse, verbose) via conversation history.

### 14.4 Health and safety

- **Fall detection:** IMU + audio anomaly detection → auto-alert to emergency contacts via mobile phone SMS
- **Medication reminders:** RTC alarm + voice announcement via mobile TTS
- **Activity tracking:** IMU pedometer + heart rate (if MAX30102 attached)
- **Sleep tracking:** IMU stillness + audio silence → sleep/wake detection, sleep log
- **Environmental alerts:** BME280 temperature/humidity alerts for asthma, allergies, heat sensitivity
- **Location tracking:** GPS via UART1 + mobile server logging; "where did I leave my keys?" via BLE proximity

### 14.5 Accessibility

- **Voice-first interaction:** No need to look at screen
- **Large haptic feedback:** confirm actions via vibration motor on GPIO
- **Screen-reader compatible mobile app**
- **Customizable wake word:** train on user's preferred phrase
- **Simplified command set:** local commands work even when mobile server unavailable

---

## 15. Production-Grade Practices

### 15.1 Testing

- **Unit tests:** Every HAL driver (imu, mic, nina_hal, crypto) has a test using `ArduinoFake` or host-simulated I2C
- **Integration tests:** Run on actual hardware via `pytest` + `pyserial` test harness
- **Model accuracy tests:** Automated regression test — every model commit runs on last 1000 cached samples, must meet accuracy threshold
- **Power profile tests:** Measure current draw at each power state using INA219 or shunt resistor + ADC; regression alert if >10% deviation
- **Stress tests:** 72-hour continuous operation test; verify no memory leaks, no watchdog resets, no NINA lockups
- **BLE range test:** Minimum 10 m line-of-sight; 5 m through wall
- **Wi-Fi throughput test:** Minimum 100 KB/s sustained TCP throughput to mobile server

### 15.2 CI/CD

```
GitHub Actions (or GitLab CI):
  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐
  │ Push / PR │───▶│ Build + Lint │───▶│ Unit tests        │
  └──────────┘    └──────────────┘    └────────┬──────────┘
                                               │ pass
                          ┌────────────────────▼──────────┐
                          │ Hardware-in-loop test runner   │
                          │ (device connected via USB)     │
                          │  • HAL tests                  │
                          │  • Sensor readback            │
                          │  • Model inference benchmark   │
                          │  • Memory usage check         │
                          └────────────────┬──────────────┘
                                           │ pass
                      ┌────────────────────▼──────────────┐
                      │ OTA package build                  │
                      │  • Model blobs                    │
                      │  • Signed firmware                │
                      │  • Changelog                      │
                      └───────────────────────────────────┘
```

### 15.3 Error handling and resilience

- **Watchdog:** RP2040 has a hardware watchdog; feed it in the idle task. NINA has its own internal watchdog.
- **NINA crash recovery:** RP2040 monitors NINA health via periodic AT ping. If NINA unresponsive for 3 consecutive pings → hardware reset NINA via RESET_N GPIO, reinitialize UART0, re-establish Wi-Fi/BLE.
- **Brown-out protection:** The onboard buck regulator provides this. RP2040 does not have internal BOR; add external BOR if using VIN above 5V.
- **Flash wear leveling:** QSPI flash has 100K program/erase cycle rating. Use LittleFS (wear-leveling filesystem) for all QSPI writes.
- **Graceful degradation:** If KWS model fails to load → fall back to BLE button-press activation. If IMU fails → fall back to timer-based sampling.

### 15.4 Observability

- **Structured logging** to QSPI flash ring buffer: `{timestamp, level, module, message}` — 64 KB ring, oldest overwritten first
- **Health metrics** exposed via BLE GATT characteristic: uptime, free heap, NINA status, IMU status, battery voltage
- **Event tracing:** Significant events (keyword detected, gesture, alert, connection change) tagged with high-priority log entry
- **Fault counter:** Track watchdog resets, NINA crash count, model inference failures → report to mobile server

### 15.5 Mechanical design (wearable form factor)

The Arduino Nano RP2040 Connect is 18×48 mm. For a wrist-wearable:
- **3D-printed wristband mount** (TPU for comfort)
- **Coin-cell or LiPo battery** (LiPo 3.7V 500 mAh is ideal; matches 3.3V rail efficiency)
- **Charging:** Use the Micro USB port (J1); add a TP4056 charging module for LiPo
- **Water resistance:** Consider IP67 enclosure (silicone case with waterproof connectors for external sensors)
- **Antenna performance:** The internal PIFA antenna on NINA-W102 is designed for free-space. In a wrist-worn enclosure near skin/body, expect ~3–5 dB attenuation. This reduces BLE range to ~5–8 m and Wi-Fi range to ~20 m. Test with actual enclosure.

---

## 16. Roadmap

### Phase 0 — Foundation (Weeks 1–4)
- [x] Extract and read all datasheets
- [ ] Set up build system (PlatformIO or CMake)
- [ ] Implement HAL layer (imu, mic, nina_hal, crypto, flash)
- [ ] FreeRTOS task skeleton with core 0 / core 1 partitioning
- [ ] UART0 ↔ NINA communication (WiFiNINA basic test)
- [ ] Basic power-state machine (active ↔ deep-sleep)

### Phase 1 — On-Device Sensing (Weeks 5–8)
- [ ] IMU polling at 50 Hz + LSM6DSOX MLC configuration
- [ ] PDM microphone → MFCC feature extraction
- [ ] KWS model: train int8 quantized CNN, deploy TFLite Micro
- [ ] IMU gesture model: train + deploy
- [ ] Trigger integration: keyword → wake → BLE notify → phone response
- [ ] Context state vector construction

### Phase 2 — Connectivity & Server (Weeks 9–12)
- [ ] BLE GATT services (inference, sensor, control, model transfer)
- [ ] Wi-Fi SoftAP + TCP server on NINA
- [ ] Binary protocol implementation (device ↔ server)
- [ ] Mobile app (Flutter): BLE discovery, pairing, stream display
- [ ] Desktop app (Electron/Tauri): local LLM (phi-3-mini), data store, dashboard

### Phase 3 — Intelligence & Learning (Weeks 13–20)
- [ ] Full NLP pipeline via mobile/desktop LLM
- [ ] On-device LoRA incremental learning implementation
- [ ] Federated averaging protocol
- [ ] Shadow-test model promotion
- [ ] OTA model + firmware delivery with ATECC608A signing
- [ ] Vision pipeline (phone-camera as vision input, structured VLM result)

### Phase 4 — Production Polish (Weeks 21–28)
- [ ] Full test suite + CI/CD pipeline
- [ ] Power optimization (achieve 7-day target)
- [ ] Mechanical enclosure design
- [ ] Comprehensive documentation
- [ ] User onboarding flow
- [ ] Privacy & security audit

### Phase 5 — Expansion (Ongoing)
- [ ] External sensor library (BME280, MAX30102, GPS)
- [ ] Wi-Fi/BLE hybrid mesh protocol
- [ ] Multi-device coordination (family/team wearable network)
- [ ] Apple Health / Google Fit integration
- [ ] Custom model training UI in mobile app

---

## Appendix A: Key Code Patterns

### A.1 RP2040 FreeRTOS entry point

```cpp
// main.cpp
#include <Arduino.h>
#include <FreeRTOS.h>

void setup() {
  // Core 0: all init happens on core 0 first
  Serial.begin(115200);
  hal_init();
  sensors_init();
  ai_models_init();
  
  // Launch core 1 task
  rp2040.idleOtherCore();
  rp2040.fork(conn_task, nullptr);
  
  // Launch core 0 tasks
  xTaskCreate(voice_task, "voice", 8192, nullptr, 4, nullptr);
  xTaskCreate(imu_task, "imu", 4096, nullptr, 3, nullptr);
  xTaskCreate(inference_task, "infer", 16384, nullptr, 2, nullptr);
  
  vTaskStartScheduler();
}

void loop() {
  vTaskDelete(nullptr); // FreeRTOS takes over
}
```

### A.2 IMU + MLC interrupt handler

```cpp
// LSM6DSOX MLC generates INT1 when gesture detected
void IRAM_ATTR imu_interrupt_handler() {
  BaseType_t higher_priority_task_woken = pdFALSE;
  xTaskNotifyFromISR(imu_task_handle, GESTURE_DETECTED_BIT, 
                     eSetBits, &higher_priority_task_woken);
  portYIELD_FROM_ISR(higher_priority_task_woken);
}
```

### A.3 Power state transitions

```cpp
void power_task(void* param) {
  TickType_t last_wake = xTaskGetTickCount();
  while (true) {
    vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(1000)); // 1 Hz monitor
    
    bool activity = imu_significant_motion() || ble_connected() || keyword_recent();
    if (activity && current_state == STATE_IDLE) {
      enter_standby();
    } else if (!activity && current_state == STATE_STANDBY) {
      uint32_t idle_seconds = get_idle_time();
      if (idle_seconds > 3600) enter_hibernate();
      else enter_idle();
    }
  }
}
```
---

## 17. Atomic Operations & Hot Reload

### Design mandate
No single point of failure may exist anywhere in the firmware stack. Every upgrade — whether it is a model weight, a task binary, a configuration record, or a logic patch — must be **atomic, verifiable, and reversible without downtime.** The device must be able to continue operating while its own code is being rewritten, tested, and promoted. This is achieved by treating the entire firmware image as a versioned transactional object and separating execution from storage through indirection layers.

---

### 17.1 Failure modes this must survive

1. Power loss during flash write
2. Radio packet corruption during OTA transfer
3. TFLite model weight corruption
4. NINA-W102 firmware crash and auto-reset
5. RP2040 task deadlock or stack overflow
6. Watchdog timeout during a long-running operation
7. Flash wear-out from repeated writes
8. Bit-flip in SRAM from cosmic ray / EMI
9. BLE/Wi-Fi disconnection mid-transfer
10. User-initiated rollback request

---

### 17.2 QSPI flash layout — transactional image design

The 16 MB QSPI flash (AT25SF128A) is partitioned into named, checksummed, versioned regions. Every region has an **active** instance and a **staging** instance. Writes always go to staging. Promotion is an atomic metadata switch.

```
QSPI Flash Layout (16 MB = 134,217,728 bytes)
═══════════════════════════════════════════════════════════════════════════
Offset              Size       Region
───────────────────────────────────────────────────────────────────────────
0x00000000          256 KB     RP2040 Bootloader / BOOTSELECT area
0x00040000          496 KB     RP2040 App A (current firmware) [ACTIVE]
0x000C0000          496 KB     RP2040 App B (staging firmware) [STAGING]
0x00140000          128 KB     Firmware Metadata + Rollback Journal
0x00160000          128 KB     Configuration Store (versioned, transactional)
0x00180000            4 MB     Model Store A (active models) [ACTIVE]
0x00580000            4 MB     Model Store B (staging models) [STAGING]
0x00980000          128 KB     Model Metadata + Checksum Index
0x00A00000            1 MB     Federated Learning Delta Ring Buffer
0x00B00000            2 MB     Sensor Data Log (LittleFS, wear-leveled)
0x00D00000            2 MB     Application Data / User Preferences
0x00F00000          256 KB     Crash / Recovery Journal (ring buffer)
0x00F40000          ~4.5 MB    Unallocated (future expansion)
═══════════════════════════════════════════════════════════════════════════
```

**Structuring principle:** Nothing is ever written in-place to the active region. The flow is always: staging → verify → atomic-promote → stale-active can be erased later.

---

### 17.3 Transactional metadata records

Every upgradeable entity has a metadata header immediately preceding its data region. The metadata record is small (64 bytes), written atomically using a two-phase commit, and checked on every boot.

```c
#define MAGIC_ACTIVE   0x41505246  /* "APRF" — Active Region */
#define MAGIC_STAGING  0x53505246  /* "SPRF" — Staging Region */
#define MAGIC_EMPTY    0x00000000  /* Unprogrammed flash */

struct ImageMetadata {
  uint32_t magic;           /* MAGIC_ACTIVE or MAGIC_STAGING */
  uint32_t version;         /* Monotonically increasing uint32 */
  uint32_t image_length;    /* Exact byte length of the payload */
  uint32_t payload_crc32;   /* CRC-32 of the payload data */
  uint32_t metadata_crc32;  /* CRC-32 of this metadata struct */
  uint32_t timestamp_unix;  /* When this image was written */
  uint32_t source;          /* OTA / USB / SELF / FACTORY */
  uint32_t flags;           /* Bitfield: rollback_allowed, test_promote, etc. */
  uint8_t  reserved[32];    /* Future use */
};

/* Two-phase commit write order:
 * Phase 1: Write payload to staging region
 * Phase 2: Write metadata with MAGIC_STAGING
 * Phase 3: On promotion, change MAGIC_STAGING → MAGIC_ACTIVE in metadata
 *          This is a single 4-byte atomic write on QSPI (page-aligned)
 */
```

**Atomic promotion trick:** The QSPI flash writes in 256-byte pages. By placing the 4-byte `magic` field at the start of a 256-byte-aligned metadata page and ensuring all other metadata fields are already valid, promotion is a single-page program operation. If power is lost during promotion, the magic field is either old (`MAGIC_ACTIVE`, safe) or new (`MAGIC_STAGING` → treated as not-yet-promoted). There is no torn state.

---

### 17.4 Hardware-level atomicity guarantees

The RP2040 and AT25SF128A together provide:

| Mechanism | Role |
|---|---|
| QSPI page program (256 B) | Minimum atomic unit; partial page not allowed by hardware |
| RP2040 flash ROM bootloader | Reads first 256 B of flash to decide boot path |
| RP2040 XIP | Code executes directly from QSPI; no copy needed |
| RP2040 SRAM6 | Dedicated 20 KB SRAM bank for boot-time atomic operations |
| RP2040 watchdog | 8-level maskable watchdog; feeds from idle task |
| NINA internal watchdog | NINA self-resets if AT stack hangs |
| ATECC608A monotonic counter | Prevents rollback attacks on signed firmware |
| RP2040 BOOTSEL | Hardware recovery via double-tap reset button |

**Key insight:** The RP2040 cannot write to its own boot-selection flash region (first 256 bytes of QSPI) during normal operation. Use a **software bootloader stub** in SRAM that runs at startup, checks metadata, and copies or branches accordingly before handing control to the application.

---

### 17.5 Firmware atomic hot-swap pattern

This is the core mechanism that enables "software that works on its own code while it is running with no errors or downtime."

```
Boot-time flow (every boot, ~200 ms total):
═══════════════════════════════════════════════
1. RP2040 boots from QSPI XIP into minimal boot stub (SRAM, ~8 KB)
2. Boot stub reads RP2040 App A metadata (offset 0x00040000)
3. If MAGIC_ACTIVE + CRC valid → branch to App A entry point
4. If MAGIC_ACTIVE invalid → check RP2040 App B metadata
5. If App B valid → promote App B to active, branch to App B
6. If both invalid → enter bootloader mode (USB mass storage)
```

**Hot-swap during runtime:**
The running application never modifies itself directly. Instead, it:
1. Downloads new firmware into `App B` staging region via Wi-Fi/BLE
2. Writes metadata with `MAGIC_STAGING`
3. Validates CRC
4. Triggers a **controlled reboot** via `watchdog_enable(0, true)` or `rp2040.reboot()`
5. On next boot, boot stub promotes App B to active and runs it

**Zero-downtime guarantee:** Between the user requesting an update and the new firmware running, the only visible gap is the reboot time (~2 seconds). During this gap, the NINA continues advertising BLE and can accept reconnection immediately.

---

### 17.6 Model atomic hot-reload pattern

Models are larger than firmware and must be reloadable without rebooting. The model runtime uses a **pointer-swap** technique:

```c
/* Model runtime holds a pointer to the "live" model descriptor.
 * A new model is staged in Model Store B, validated, then the
 * live pointer is atomically swapped. The old model memory is
 * freed on the next inference cycle when no task holds a reference.
 */

typedef struct {
  uint32_t magic;
  uint32_t version;
  uint32_t model_id;
  uint32_t weight_crc;
  uint32_t weight_length;
  uint32_t metadata_crc;
  const uint8_t* weight_data;    /* Points into QSPI XIP region */
  size_t weight_size;
  uint32_t reference_count;      /* Incremented during inference */
} ModelDescriptor;

static ModelDescriptor* live_model = nullptr;
static ModelDescriptor* shadow_model = nullptr;

/* Called by inference task before invoking TFLite */
ModelDescriptor* acquire_model(uint32_t model_id) {
  if (live_model && live_model->model_id == model_id) {
    __sync_fetch_and_add(&live_model->reference_count, 1);
    return live_model;
  }
  /* Fallback: try to load from QSPI staging */
  return load_model_from_flash(model_id);
}

/* Called by inference task after TFLite invoke completes */
void release_model(ModelDescriptor* model) {
  __sync_fetch_and_sub(&model->reference_count, 1);
  /* If reference_count == 0 and this is the old live_model,
   * free it or mark for deferred reclaim */
}

/* Hot-reload entry point (called from conn_agent or model push handler) */
int hot_reload_model(uint32_t new_model_id, const uint8_t* new_weights, size_t len) {
  /* 1. Write new weights to Model Store B staging region */
  flash_write_staging(MODEL_REGION, new_weights, len);
  
  /* 2. Build shadow ModelDescriptor in SRAM */
  shadow_model = create_descriptor(new_model_id, STAGING_REGION_ADDR, len);
  
  /* 3. Verify CRC */
  if (!verify_model_crc(shadow_model)) {
    flash_erase_staging(MODEL_REGION);
    return -1;
  }
  
  /* 4. Run shadow test: invoke shadow model on last 100 cached samples */
  float shadow_accuracy = run_shadow_benchmark(shadow_model);
  float live_accuracy = get_live_model_accuracy();
  
  if (shadow_accuracy < live_accuracy * 0.95) {
    flash_erase_staging(MODEL_REGION);
    return -2; /* Regression detected, reject */
  }
  
  /* 5. Atomic swap — the only critical section */
  taskENTER_CRITICAL(); /* FreeRTOS critical section */
  ModelDescriptor* old = live_model;
  live_model = shadow_model;
  shadow_model = nullptr;
  if (old) schedule_deferred_reclaim(old);
  taskEXIT_CRITICAL();
  
  /* 6. Async erase of old model in background */
  xTaskNotify(flash_cleanup_task, OLD_MODEL_ERASE_BIT, eSetBits);
  
  return 0; /* Success — new model live */
}
```

**Critical guarantee:** The `taskENTER_CRITICAL()` block is bounded to <10 µs on RP2040 (it disables interrupts on the calling core only; Core 1 continues running). The pointer swap itself is a single machine instruction. Any inference task that called `acquire_model()` before the swap holds a reference to the old descriptor and finishes safely. No inference is interrupted mid-call.

---

### 17.7 Atomic configuration updates

Configuration is a versioned key-value store with transactional writes. Each config write produces a new config version, never modifies the existing one in-place.

```c
struct ConfigHeader {
  uint32_t magic;           /* 0x434F4E46 "CONF" */
  uint32_t version;         /* Monotonic uint32 */
  uint32_t record_count;    /* Number of key-value records */
  uint32_t total_crc32;     /* CRC of entire config blob */
  uint32_t timestamp_unix;
  uint32_t flags;
  uint8_t  reserved[40];
};

/* Config store: two copies — active and staging */
#define CONFIG_ACTIVE_ADDR  0x00160000
#define CONFIG_STAGING_ADDR 0x00162000

/* Write path:
 * 1. Serialize new config to staging
 * 2. CRC-check staging
 * 3. Atomic: copy ConfigHeader from staging to active (single 256B page)
 * 4. On reboot, boot stub reads active ConfigHeader
 * 5. If config CRC fails, fall back to previous active config (kept in 3rd copy)
 */
```

**Three-copy redundancy for config:** The config store maintains three copies in a ring: `[A | B | C]`. Writes always go to the oldest invalid copy. If any copy's CRC fails on boot, the next valid copy is used. This handles a torn write from power loss.

---

### 17.8 Task-level hot-reload: self-modifying control graphs

The most radical requirement is that the firmware **works on its own code while running.** This is implemented via an indirection layer called the **Control Graph** — a runtime data structure that defines what each FreeRTOS task does, how often, and what it calls into.

Instead of hard-coding task behavior, every agent's behavior is driven by a **Control Graph Node** that can be updated at runtime:

```c
typedef enum {
  NODE_SENSOR_POLL,      /* Periodic sensor read */
  NODE_MODEL_INFERENCE,  /* TFLite invoke */
  NODE_FORWARD,          /* Forward data to next node */
  NODE_FILTER,           /* Apply filter/threshold */
  NODE_ROUTE,            /* Conditional routing */
  NODE_ACTION,           /* Execute actuator command */
  NODE_LOGGER,           /* Log to flash */
  NODE_SLEEP,            /* Yield/sleep task */
  NODE_CUSTOM_SCRIPT     /* Execute bytecode from script region */
} NodeType;

struct ControlNode {
  uint32_t node_id;
  NodeType type;
  uint32_t param_a;
  uint32_t param_b;
  uint32_t next_node_true;
  uint32_t next_node_false;
  uint32_t interval_ms;
  uint32_t flags;
};

/* The entire sensor/voice/inference pipeline is a linked list of
 * ControlNodes stored in a dedicated QSPI region. The task iterates
 * this linked list in a loop. Updating the pipeline means rewriting
 * the linked list in staging, then atomic pointer swap.
 */

typedef struct {
  uint32_t magic;           /* 0x43474E48 "CGNH" */
  uint32_t version;
  uint32_t entry_node_id;
  uint32_t node_count;
  uint32_t graph_crc32;
  uint32_t timestamp_unix;
  /* Followed by node_count ControlNode records */
} ControlGraphHeader;

/* voice_task becomes a generic graph executor:
 * while (running) {
 *   next = graph_get_next(current_node, sensor_result);
 *   execute_node(next, context);
 *   vTaskDelay(next->interval_ms);
 * }
 */

/* Hot-reload of a control graph:
 * 1. Write new graph nodes to staging region
 * 2. Verify CRC
 * 3. Atomic: update graph pointer in SRAM
 * 4. Next loop iteration, task uses new graph
 * 5. Old graph memory is reclaimed after all tasks release references
 */
```

**What this achieves:**
- The voice pipeline can be changed from `mic → KWS → BLE notify` to `mic → VAD → audio_record → server_send` without flashing new firmware
- The inference graph can swap which model runs on which sensor input without rebooting
- New nodes can be added: `NODE_ALERT_IF_HR_HIGH`, `NODE_TRIGGER_ON_GESTURE`
- A **scripting node** (`NODE_CUSTOM_SCRIPT`) executes a small bytecode program stored in QSPI, enabling arbitrary logic changes without recompilation

---

### 17.9 Custom bytecode interpreter for runtime self-modification

For the device to truly "work on its own code," a minimal bytecode interpreter runs alongside the control graph. Bytecode is stored in a dedicated QSPI region, loaded on demand, and can be hot-reloaded.

```c
/* Minimal stack-based bytecode interpreter (~200 lines of C)
 * Opcodes are chosen to be safe: no unbounded loops, bounded memory,
 * explicit instruction budgets. Every script has a max_cycles limit.
 */

typedef enum {
  OP_POP,           /* Pop stack top */
  OP_PUSH_IMM,      /* Push immediate value */
  OP_LOAD_VAR,      /* Load named sensor variable to stack */
  OP_STORE_VAR,     /* Store stack top to named variable */
  OP_ADD, OP_SUB, OP_MUL, OP_DIV,
  OP_CMP_EQ, OP_CMP_GT, OP_CMP_LT,
  OP_JUMP_IF,       /* Pop condition, pop target, jump if true */
  OP_CALL_NODE,     /* Call a control graph node by ID */
  OP_SEND_BLE,      /* Send stack top as BLE notification */
  OP_LOG,           /* Log value to flash ring buffer */
  OP_SET_INTERVAL,  /* Set current node's interval */
  OP_HALT,          /* End script */
  OP_COUNT
} OpCode;

struct ScriptHeader {
  uint32_t magic;         /* 0x53435250 "SCRP" */
  uint32_t version;
  uint32_t opcode_count;
  uint32_t max_cycles;    /* Safety budget per invocation */
  uint32_t script_crc;
  uint32_t flags;
};

/* Script execution:
 * - Runs inside the task that owns the NODE_CUSTOM_SCRIPT node
 * - Max 1000 cycles per invocation (prevents runaway loops)
 * - All stack values are float32; overflow wraps safely
 * - Script cannot touch SRAM outside its own stack frame
 * - Script output is a structured Action record, not raw memory write
 */

typedef struct {
  uint32_t action_type;
  float    params[4];
} Action;

/* Example: user says "remind me in 10 minutes"
 * Mobile server generates bytecode:
 *   OP_LOAD_VAR  (VAR_UNIX_TIMESTAMP)
 *   OP_PUSH_IMM  (600.0)
 *   OP_ADD
 *   OP_STORE_VAR  (VAR_ALARM_TIME)
 *   OP_CALL_NODE  (NODE_SET_RTC_ALARM)
 *   OP_SEND_BLE   (MSG_ALARM_SET)
 *   OP_HALT
 * Device stores this bytecode in staging, atomic-promotes,
 * next execution of the reminder graph node runs the new script.
 */
```

**Safety properties:**
- Scripts are **not Turing-complete** in practice (bounded by `max_cycles` and `max_stack_depth = 16`)
- No memory allocation inside the interpreter
- No function pointers; all external calls go through a **whitelist table** of approved `Action` handlers
- Scripts are **signed** with ATECC608A before being accepted by the device
- Any script that exceeds its cycle budget is killed; the task continues with the next node in the graph
- Scripts can be **shadow-tested** before promotion: run the new script on historical data in a sandbox task, verify no exceptions or violations, then promote

---

### 17.10 NINA firmware atomic swap

The NINA-W102 runs its own firmware in its internal 16 Mbit flash. The RP2040 is the host that can reprogram it over UART0. Apply the same transactional pattern:

```
NINA Flash Layout (2 MB internal flash)
═══════════════════════════════════════════════════════════════════════
0x000000  16 KB   NINA Bootloader (factory, never overwritten)
0x004000  496 KB  NINA App A (active firmware)
0x084000  496 KB  NINA App B (staging firmware)
0x104000  128 KB  NINA App Metadata + CRC
═══════════════════════════════════════════════════════════════════════
```

**NINA OTA atomic update protocol:**

1. RP2040 downloads new NINA firmware blob from server (via current NINA's Wi-Fi/TCP)
2. RP2040 stores blob in its own QSPI `NINA staging` partition (not NINA's flash yet)
3. RP2040 toggles NINA `RESET_N` pin low, holds `GPIO_0` (bootstrap) low → NINA enters download mode
4. RP2040 streams blob to NINA UART0 using Espressif serial download protocol
5. RP2040 reads back NINA flash, verifies CRC against blob
6. RP2040 updates NINA metadata (if NINA firmware supports metadata API; otherwise done via RP2040-side ledger)
7. RP2040 releases NINA `RESET_N` → NINA boots new firmware
8. RP2040 verifies NINA is responsive via AT ping

**Rollback:** If NINA does not respond within 10 seconds, RP2040 repeats step 3–7 with App A blob (the previous firmware stored in RP2040's own staging). This gives an automatic rollback without user intervention.

**Constraint:** NINA-W102's 16 Mbit flash is not dual-banked by default on all firmware variants. If the running firmware supports it, write new firmware to the second half and update a 4-byte boot pointer. If not, the only safe pattern is **download-mode rewrite with CRC verification + rollback**, which costs ~20 seconds of BLE/Wi-Fi downtime.

---

### 17.11 Crash detection and autonomous recovery

The system must detect and recover from any fault without user action. Recovery operates at multiple layers:

**Layer 1 — Hardware watchdogs**
- RP2040 watchdog: fed by the FreeRTOS idle task. If no task calls `vTaskDelay` or yields for >5 seconds → reset. The idle task is the lowest-priority task; if a higher-priority task starves it, the watchdog fires.
- NINA internal watchdog: feeds itself during normal AT command processing. RP2040 monitors for missed AT responses.
- RP2040 brown-out detector: if 3.3V rail drops below threshold, hardware holds reset.

**Layer 2 — Software fault detection**
- FreeRTOS stack overflow hook: `vApplicationStackOverflowHook` → log task name + stack watermark, reset task to safe default, increment fault counter
- FreeRTOS malloc failure hook: `vApplicationMallocFailedHook` → log heap state, trigger graceful memory reclaim, if unrecoverable → reboot with rollback journal
- TFLite invocation timeout: wrap `Interpreter::Invoke()` with a watchdog feed + timeout. If Invoke exceeds 3× expected duration → abort model, mark as corrupted, reload shadow model or fall back to simpler model
- NINA communication timeout: if no AT response within 2 seconds → reset NINA. Counter increments; if >3 resets in 1 minute → reduce baud rate or enter degraded mode

**Layer 3 — Crash journal and post-mortem**

The RP2040 QSPI flash has a 256 KB ring-buffer crash journal. On any fault (watchdog, assertion, TFLite abort, NINA reset storm), the system writes a structured crash record:

```c
struct CrashRecord {
  uint32_t magic;           /* 0x43525348 "CRSH" */
  uint32_t version;
  uint32_t timestamp_unix;
  uint32_t fault_type;      /* WATCHDOG / STACK_OVERFLOW / TFLITE_ABORT / etc. */
  uint32_t faulting_task_id;
  uint32_t pc_at_fault;     /* Program counter from exception frame */
  uint32_t lr_at_fault;     /* Link register */
  uint32_t r0_r3[4];        /* First 4 registers from exception frame */
  uint32_t xpsr;
  uint32_t heap_free;       /* Free heap at time of fault */
  uint32_t stack_watermark; /* Remaining stack of faulting task */
  uint32_t nina_reset_count;
  uint32_t uptime_seconds;
  uint32_t active_model_version;
  uint32_t config_version;
  uint8_t  reserved[64];
};
```

This journal is read by the desktop app and displayed in the dashboard. It provides enough information to debug field failures without a debugger attached.

**Layer 4 — Autonomous self-repair**

After writing a crash record, the recovery logic runs:

```c
void autonomous_recovery(CrashRecord* rec) {
  switch (rec->fault_type) {
    case FAULT_WATCHDOG:
      /* Most likely: deadlock or infinite loop.
       * Action: roll back last control graph change.
       * Rollback journal stores last N graph versions.
       */
      rollback_control_graph();
      break;
      
    case FAULT_TFLITE_ABORT:
      /* Model corruption or invalid input.
       * Action: demote corrupted model, promote shadow model,
       * or load fallback minimal model from factory partition.
       */
      demote_model(rec->active_model_version);
      promote_fallback_model();
      break;
      
    case FAULT_STACK_OVERFLOW:
      /* Task-specific: reduce that task's stack, or restart task.
       * Record which task overflows; if same task overflows 3 times,
       * disable that task's optional nodes in control graph.
       */
      restart_task_with_larger_stack(rec->faulting_task_id);
      break;
      
    case FAULT_NINA_RESET_STORM:
      /* NINA crashing repeatedly.
       * Action: downgrade NINA firmware to previous stable version,
       * or enter degraded mode (BLE-only, no Wi-Fi server).
       */
      rollback_nina_firmware();
      enter_degraded_mode();
      break;
      
    case FAULT_FLASH_CORRUPTION:
      /* QSPI flash CRC failures detected at boot.
       * Action: restore from factory defaults partition.
       * Factory partition: minimal KWS model + basic connectivity,
       * stored at fixed offset, write-protected by boot stub.
       */
      restore_factory_partition();
      break;
      
    default:
      /* Unknown fault: full reboot with rollback journal replay.
       * On reboot, boot stub reads rollback journal, reverts last
       * transaction of each type.
       */
      full_reboot_with_rollback();
      break;
  }
  
  /* After recovery, send alert to mobile server with crash details */
  queue_alert_to_server(ALERT_RECOVERY, rec);
}
```

---

### 17.12 Rollback journal

Every transactional change is recorded in a 128 KB rollback journal on QSPI flash:

```c
struct JournalEntry {
  uint32_t magic;         /* 0x524F4C4C "ROLL" */
  uint32_t entry_id;      /* Monotonic sequence */
  uint32_t timestamp_unix;
  uint32_t operation;     /* FIRMWARE_PROMOTE / MODEL_PROMOTE / CONFIG_CHANGE /
                             GRAPH_CHANGE / NINA_FIRMWARE_PROMOTE */
  uint32_t old_version;   /* Version before change */
  uint32_t new_version;   /* Version after change */
  uint32_t old_region_addr; /* Where the old data lives (or 0 if erased) */
  uint32_t old_region_size;
  uint32_t flags;         /* Can_rollback, Force_keep */
};

/* Journal is a ring buffer. On boot, the boot stub reads all entries
 * since the last stable checkpoint. If the journal indicates an
 * incomplete transaction (new_version active but old_version not yet
 * marked as fully superseded), roll back.
 */

/* Manual rollback command (from mobile app):
 * 1. App sends ROLLBACK command with target entry_id
 * 2. Device reads journal entry, finds old_version data location
 * 3. Performs atomic promotion of old_version back to active
 * 4. Writes new journal entry: ROLLBACK_COMPLETE
 * 5. Notifies server of rollback
 */
```

---

### 17.13 Zero-downtime task restart

Individual FreeRTOS tasks can be restarted without rebooting the entire system. This is essential for recovering from a stuck task or a logic change in a single agent:

```c
typedef struct {
  TaskHandle_t handle;
  const char* name;
  uint32_t restart_count;
  uint32_t last_restart_time;
  uint32_t stable_since;  /* Uptime without restart; reset on restart */
} TaskRegistryEntry;

static TaskRegistryEntry task_registry[MAX_TASKS];

/* Restart a task atomically:
 * 1. Suspend the task (vTaskSuspend)
 * 2. Delete it (vTaskDelete) — frees its stack and TCB
 * 3. Recreate with same priority, same name, fresh stack
 * 4. Re-initialize task-local state from configuration
 * 5. Resume new task handle
 * 
 * During the restart window (~1 ms), other tasks continue running.
 * The sensor data this task would have processed is buffered in the
 * ring buffer and consumed when the task resumes.
 */

esp_err_t hot_restart_task(const char* task_name) {
  TaskRegistryEntry* entry = registry_find(task_name);
  if (!entry) return ESP_ERR_NOT_FOUND;
  
  /* Prevent restart loops: if restarted >5 times in 60 seconds,
   * disable the task and flag for investigation.
   */
  if (entry->restart_count >= 5 &&
      (xTaskGetTickCount() - entry->last_restart_time) < pdMS_TO_TICKS(60000)) {
    disable_task(task_name);
    queue_alert_to_server(ALERT_TASK_DISABLED, task_name);
    return ESP_ERR_INVALID_STATE;
  }
  
  vTaskSuspend(entry->handle);
  vTaskDelete(entry->handle);
  
  /* Recreate */
  TaskHandle_t new_handle;
  BaseType_t result = xTaskCreate(
    entry->task_entry, entry->name,
    entry->stack_size, entry->param,
    entry->priority, &new_handle
  );
  
  if (result != pdPASS) {
    /* Cannot recreate: mark as disabled, alert server */
    disable_task(task_name);
    return ESP_ERR_NO_MEM;
  }
  
  entry->handle = new_handle;
  entry->restart_count++;
  entry->last_restart_time = xTaskGetTickCount();
  
  return ESP_OK;
}

/* Self-healing trigger: if a task's notification queue overflows
 * (xTaskNotifyWait returns pdFALSE with errno = errCOULD_NOT_UNLOCK),
 * the watchdog task automatically calls hot_restart_task for that task.
 */
```

---

### 17.14 Memory safety guarantees

On a Cortex-M0+ without MPU hardening, memory safety relies on disciplined patterns:

| Pattern | Implementation |
|---|---|
| **Stack watermarking** | `uxTaskGetStackHighWaterMark()` every 10 seconds; alert if <128 bytes free |
| **Heap poisoning** | Wrap `pvPortMalloc`/`vPortFree` with magic-number preambles; check on free |
| **Buffer bounds** | All ring buffers use `capacity - 1` sizing and mask-based indexing; overflow impossible |
| **Null pointer trap** | RP2040: set `PPB_BASE->CPACR` to enable UsageFault; trap null dereference instead of hardfault |
| **DMA coherence** | All DMA buffers are in SRAM bank 0 (coherent); invalidate DCache before CPU read after DMA |
| **No dynamic allocation in ISR** | Enforced by code review rule + static analysis |
| **Maximum allocation size** | `configTOTAL_HEAP_SIZE` set to 60 KB; any single allocation >4 KB is rejected |
| **TFLite arena** | Fixed-size allocation arena; `Interpreter::AllocateTensors()` fails fast if insufficient |

---

### 17.15 Live self-coding workflow

The "work on its own code while running" requirement is satisfied through a **4-layer sandbox** that allows the device (and the connected mobile server acting as a compiler/validator) to generate, test, and promote code changes:

```
Layer 0 — Control Graph edits (hot, no reboot)
  • Linked-list of ControlNodes in QSPI
  • Node types, parameters, routing can be changed at runtime
  • Used for: reconfiguring sensor pipelines, changing inference targets,
    adding new trigger conditions

Layer 1 — Bytecode scripts (hot, no reboot)
  • Stack-based interpreter with bounded execution
  • Scripts stored in QSPI, signed, shadow-tested before promotion
  • Used for: custom logic, reminders, conditional actions,
    user-defined automations

Layer 2 — Parameter optimization (hot, no reboot)
  • Model thresholds, activation levels, sampling rates, power budgets
  • Stored in versioned config store; atomic pointer-swap updates
  • Used for: personalization, environment adaptation, power tuning

Layer 3 — Full model weight updates (hot, no reboot)
  • TFLite FlatBuffer weights in QSPI; pointer-swap reload
  • Shadow-test before promotion; automatic rollback on regression
  • Used for: KWS adaptation, gesture model personalization,
    federated learning updates

Layer 4 — Full firmware update (controlled reboot, 2-second window)
  • New firmware in staging QSPI region
  • Atomic promotion at boot
  • Rollback journal + factory fallback
  • Used for: major version upgrades, new agent types, new hardware support
```

**Mobile server as the compiler:** The mobile/desktop app can:
1. Receive the current control graph and bytecode scripts from the device
2. Apply transformations: add a node, change a threshold, insert a filter
3. Compile a new control graph or bytecode script
4. Sign with ATECC608A
5. Push to device via BLE/Wi-Fi
6. Device shadow-tests the change on cached data
7. If valid → atomic-promote; if invalid → reject with error code

This gives the device a **programmable nervous system** that can be reshaped while it operates, with every change verified before it takes effect.

---

### 17.16 Verification and testing of atomic operations

Every atomic path must be exercised in development:

| Test | How |
|---|---|
| **Power-loss during QSPI write** | Cut power mid-write with relay; verify CRC on boot, reject corrupted staging |
| **Double promotion race** | Simultaneously trigger firmware + model promotion; verify only one wins |
| **Pointer-swap atomicity** | Run inference on Core 0 while Core 1 triggers hot-reload; verify no crashes |
| **Rollback chain** | Write 5 config versions; roll back 3; verify correct state |
| **Script sandbox escape** | Attempt to write beyond stack; verify trap and kill |
| **NINA firmware rollback** | Push intentionally bad NINA firmware; verify auto-rollback to previous |
| **Watchdog starvation** | Create a task that disables interrupts; verify watchdog reset + recovery |
| **Flash wear** | 1000 write cycles to staging region; verify no bit errors via CRC |

Automate these in a hardware-in-loop test runner (Phase 4).

---

### 17.17 Summary of guarantees

| Property | Mechanism | Downtime |
|---|---|---|
| Firmware upgrade | Staging → CRC → atomic-promote → reboot | ~2 seconds |
| Model upgrade | Shadow-test → pointer-swap | Zero |
| Config change | 3-copy ring → atomic header swap | Zero |
| Control graph change | Staging linked list → pointer swap | Zero |
| Bytecode change | Staging → shadow-test → pointer swap | Zero |
| NINA firmware upgrade | Download mode → CRC → auto-rollback | ~20 seconds |
| Crash recovery | Watchdog → crash journal → autonomous_recovery() | <5 seconds |
| Task restart | Suspend → delete → recreate | ~1 ms |
| Rollback | Journal replay on boot | ~200 ms at boot |
| Power-loss safety | Two-phase commit + CRC validation | Zero (next boot rejects torn state) |

The system is designed so that **no single fault can brick the device, no fault can corrupt data silently, and no upgrade requires the user to be present or the device to be tethered.** Every operation is staged, verified, and reversible. The device can continue operating while its logic, models, and parameters are being rewritten, tested, and promoted by itself or by the connected mobile/desktop server.

---

## Appendix A: Key Code Patterns

---

## Appendix B: Reference — Hardware Constraints Summary

| Resource | Spec | Your Budget |
|---|---|---|
| RP2040 SRAM | 264 KB total | ~135 KB used, ~129 KB free |
| RP2040 QSPI Flash | 16 MB XIP | ~2 MB models/logs, rest free |
| NINA SRAM | 520 KB | Shared with Wi-Fi/BLE stack |
| NINA Flash | 16 Mbit (2 MB) encrypted | NINA firmware + AT commands |
| ATECC608A | 1 kbit eFUSE | Identity + key storage |
| LSM6DSOX MLC | 8-state FSM | Always-on gesture detection |
| PDM Mic | PDM via PIO | 16 kHz audio, 4 KB ring buffer |
| GPIO headers | 30 pins | Sensors, LEDs, haptics, display |
| 3.3V rail | 800 mA max | All peripherals + RP2040 + NINA |
| RP2040 clock | 133 MHz | Sufficient for TinyML + audio DSP |
| NINA clock | 240 MHz | Wi-Fi/BLE stack + crypto accelerators |
| BLE max slaves | 7 | Multi-device mesh possible |
| Wi-Fi max clients | 5–8 (SoftAP) | Practical mesh limit |
| Temperature range | −20 to +80 °C | Wearable-grade |
| Battery | 3.7V LiPo 500 mAh | 3–7 days typical |

---

*This document is the authoritative design reference. All implementation decisions should be traceable to these specifications and the datasheets in `Z:\Projects\WearableAI\ArduinoNanoRP2040Connect\`.*
