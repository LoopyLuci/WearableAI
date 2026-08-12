# ARP-2040 Connect — 100-Year Build & Execution Plan
## From Blueprint to Production-Grade, Modular, Immortal Codebase
*Companion to: ARP2040_Connect_Wearable_AI_Design_Blueprint.md*

---

## Table of Contents
1. [The Immortality Principle](#1-the-immortality-principle)
2. [Phase 0 — Foundation Lock (Weeks 1-6)](#2-phase-0--foundation-lock-weeks-1-6)
3. [Phase 1 — HAL Abstraction Layer (Weeks 7-14)](#3-phase-1--hal-abstraction-layer-weeks-7-14)
4. [Phase 2 — Kernel & Runtime (Weeks 15-22)](#4-phase-2--kernel--runtime-weeks-15-22)
5. [Phase 3 — Agent Framework (Weeks 23-30)](#5-phase-3--agent-framework-weeks-23-30)
6. [Phase 4 — Model Infrastructure (Weeks 31-40)](#6-phase-4--model-infrastructure-weeks-31-40)
7. [Phase 5 — Connectivity Mesh (Weeks 41-50)](#7-phase-5--connectivity-mesh-weeks-41-50)
8. [Phase 6 — Self-Modification Engine (Weeks 51-60)](#8-phase-6--self-modification-engine-weeks-51-60)
9. [Phase 7 — Mobile/Desktop Server (Weeks 61-72)](#9-phase-7--mobiledesktop-server-weeks-61-72)
10. [Phase 8 — Production Hardening (Weeks 73-84)](#10-phase-8--production-hardening-weeks-73-84)
11. [Scalability & Modularity Rules](#11-scalability--modularity-rules)
12. [100-Year Architecture Principles](#12-100-year-architecture-principles)
13. [Tooling & Developer Experience](#13-tooling--developer-experience)
14. [Testing Strategy](#14-testing-strategy)
15. [Risk Register & Mitigations](#15-risk-register--mitigations)

---

## 1. The Immortality Principle

A codebase that lasts 100 years doesn't optimize for the hardware it runs on today. It optimizes for:
- **Abstraction purity** — hardware details never leak above the HAL
- **Interface stability** — public APIs change once per decade, not per sprint
- **Data format longevity** — all on-flash data structures are versioned, self-describing, and backwards-compatible
- **Modular replaceability** — any agent, model, transport, or sensor can be swapped without touching the rest of the system
- **Testability** — every layer is independently testable, including on host without hardware
- **Documentation as code** — API contracts are verified by compile-time checks and runtime assertions, not just prose

**The golden rule:** If you cannot test a component on a host machine without the RP2040 connected, the abstraction is wrong.

---

## 2. Phase 0 — Foundation Lock (Weeks 1-6)

### 2.1 Repository structure

```
arp-2040/
├── firmware/                  # RP2040 firmware
│   ├── hal/                   # Hardware abstraction layer
│   ├── kernel/                # FreeRTOS wrapper + scheduler
│   ├── agents/                # Agent implementations
│   ├── ai/                   # Model runtime + models
│   ├── transport/            # Wi-Fi/BLE/mesh protocols
│   ├── learning/             # Federated + incremental learning
│   ├── security/             # Crypto, signing, auth
│   ├── storage/              # QSPI flash, LittleFS, transactional I/O
│   ├── scripting/            # Bytecode interpreter + control graph
│   └── main.cpp
│
├── host-tools/               # Runs on desktop, NOT on device
│   ├── model-compiler/       # Train → quantize → TFLite Micro pipeline
│   ├── graph-compiler/       # Control graph → binary + validator
│   ├── script-compiler/      # Bytecode assembler + verifier
│   ├── ota-server/           # Signed OTA package generator
│   ├── device-emulator/      # Host-based RP2040/NINA simulator
│   └── test-runner/          # Hardware-in-loop automation
│
├── mobile-server/            # Flutter app (iOS + Android)
│   ├── lib/
│   ├── native/               # Platform channels (BLE, llama.cpp, TTS)
│   └── assets/
│
├── desktop-server/           # Electron/Tauri app (Windows/Mac/Linux)
│   ├── src/
│   ├── backend/              # Python: LLM, federated learning, data store
│   └── assets/
│
├── docs/                     # All documentation
│   ├── blueprint.md          # Hardware-grounded design reference
│   ├── hal-spec.md           # HAL interface contracts
│   ├── protocol-spec.md      # Device-server wire protocol
│   ├── api-reference.md      # Generated from code comments
│   └── build-guide.md        # Step-by-step build instructions
│
├── tests/                    # ALL tests, host-side and device-side
│   ├── unit/                 # HAL mocks, pure logic tests
│   ├── integration/          # Cross-module tests on host emulator
│   ├── hardware/             # Hardware-in-loop tests
│   └── models/               # Model accuracy regression tests
│
├── models/                   # Source model definitions + training scripts
│   ├── kws/
│   ├── imu-gesture/
│   └── audio-scene/
│
├── scripts/                  # Build, flash, test automation
│   ├── build.sh
│   ├── flash.sh
│   ├── test.sh
│   └── ci/
│
├── .github/workflows/        # CI/CD
├── CMakeLists.txt            # Top-level CMake
├── platformio.ini            # PlatformIO for firmware
├── Makefile                  # Top-level build targets
└── README.md                 # Project overview + getting started
```

### 2.2 Lock the build system

**Decision: CMake + PlatformIO hybrid.**

- **CMakeLists.txt** at the root controls everything: firmware, host-tools, mobile-server, desktop-server
- **PlatformIO** handles the actual firmware compilation for RP2040 (arduino-pico core) and NINA (ESP32 core)
- **Why CMake:** It is the only build system that can express cross-language, cross-platform dependencies (C firmware + Python tools + Flutter mobile + Electron desktop) in a single dependency graph
- **Why PlatformIO:** The Arduino-Pico and WiFiNINA ecosystems are best supported through PlatformIO; fighting CMake to compile Arduino libraries is not worth it

**CMake top-level targets:**
```cmake
add_custom_target(firmware ALL
  COMMAND pio run -e nano_rp2040_connect
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/firmware)

add_custom_target(host-tools ALL
  COMMAND pip install -r requirements.txt
  COMMAND python setup.py build
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/host-tools)

add_custom_target(mobile-server ALL
  COMMAND flutter build apk --debug
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/mobile-server)

add_custom_target(desktop-server ALL
  COMMAND npm run build
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/desktop-server)

add_custom_target(test ALL
  DEPENDS firmware host-tools
  COMMAND ctest --output-on-failure)
```

### 2.3 Lock the HAL interface (the most critical decision)

Before writing a single line of hardware-specific code, define the **HAL interface contracts** in `docs/hal-spec.md`. These are pure virtual C++ classes with no implementation. Every HAL implementation must satisfy the same interface.

```cpp
// firmware/include/hal/ISensor.h
// This file NEVER changes unless a fundamentally new sensor type is invented.

class ISensor {
public:
  virtual ~ISensor() = default;
  virtual SensorType type() const = 0;
  virtual ErrorCode init() = 0;
  virtual ErrorCode read(Sample* out_buffer, size_t* out_samples) = 0;
  virtual ErrorCode configure(const SensorConfig& config) = 0;
  virtual ErrorCode self_test() = 0;  // Returns PASS/FAIL without external test gear
  virtual uint32_t serial_number() const = 0;
};
```

**Rule:** Every HAL module has a corresponding `I*` interface class. Implementation files (`LSM6DSOX.cpp`, `MP34DT06.cpp`, `NINA_W102.cpp`) are in `hal/impl/`. Tests use mock implementations (`MockLSM6DSOX.cpp`) that satisfy the same interface.

**HAL modules to define first:**
1. `ISensor` + `ISensorHub` (aggregates multiple sensors)
2. `IRadio` (Wi-Fi + BLE unified)
3. `ICrypto` (ATECC608A)
4. `IStorage` (QSPI flash, LittleFS)
5. `IPower` (power state machine, battery monitor)
6. `IAudio` (PDM microphone + codec)
7. `IDisplay` (any attached OLED/LCD)
8. `IActuator` (vibration motor, RGB LED)

### 2.4 Set up CI/CD from day one

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  host-tools-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r host-tools/requirements.txt
      - run: pytest tests/unit/ tests/integration/

  firmware-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: arduino/compile-sketches@v1
        with:
          fqbn: rp2040:rp2040:nano_rp2040_connect
          sketch-paths: firmware/

  hardware-test:
    needs: [host-tools-test, firmware-lint]
    runs-on: self-hosted  # Machine with RP2040 connected via USB
    steps:
      - uses: actions/checkout@v4
      - run: scripts/test.sh --hardware
```

---

## 3. Phase 1 — HAL Abstraction Layer (Weeks 7-14)

### 3.1 Implementation order

Week 7-8: `IStorage` + QSPI flash transactional layer
- This is the foundation for everything else. Models, configs, logs, OTA staging all depend on it
- Implement: `FlashTransaction`, `FlashRegion`, `FlashJournal`, `LittleFSAdapter`
- **Test first:** Create a host-side flash simulator (`host-tools/flash-sim/`) that maps a 16 MB file to the same API. All HAL tests run against this simulator.

Week 9-10: `IRadio` + NINA-W102 HAL
- Implement UART0 AT-command transport layer
- Wrap WiFiNINA library calls behind `IRadio` interface
- Add NINA health monitor (AT ping + timeout detection)
- **Test:** `MockRadio` that simulates NINA responses; integration test runs against real NINA via USB

Week 11-12: `ISensor` + onboard sensors
- LSM6DSOX: I2C driver, MLC configuration, polling + interrupt paths
- MP34DT06: PIO state machine driver, DMA ring buffer, MFCC feature extraction
- **Test:** Record sensor data on real hardware, save as binary fixtures, replay in host tests

Week 13-14: `ICrypto` + `IPower`
- ATECC608A: SWI/I2C driver, challenge-response, key storage
- Power state machine: active/standby/idle/hibernate transitions, battery ADC

### 3.2 HAL testing contract

Every HAL implementation MUST pass:
1. **Unit test on host** (using mock bus: `MockI2C`, `MockUART`)
2. **Hardware-in-loop test** (real sensor, compare against reference values)
3. **Fault injection test** (simulate I2C NACK, UART timeout, flash write failure)
4. **Power-loss test** (cut power during flash write, verify recovery on reboot)

### 3.3 Sensor data format

All sensors produce data in a common format defined once, forever:

```cpp
// firmware/include/common/SensorSample.h

struct SensorSample {
  uint32_t magic;           // 0x534E5350 "SNSP"
  uint32_t sensor_id;       // Which sensor produced this
  uint64_t timestamp_us;    // Microsecond timestamp from RP2040 RTC
  uint16_t sample_count;    // Number of frames in this record
  uint8_t  data[];          // Variable-length: type-specific payload
};

// IMU sample payload:
struct IMUPayload {
  int16_t accel[3];   // mg * 1000, LSB aligned
  int16_t gyro[3];    // deg/s * 100, LSB aligned
  int16_t temp;       // Celsius * 100
};

// Audio sample payload:
struct AudioPayload {
  int16_t samples[160]; // 10 ms @ 16 kHz
};
```

This format is used for: real-time sensor streaming, flash logging, model input, network transmission. One format, everywhere.

---

## 4. Phase 2 — Kernel & Runtime (Weeks 15-22)

### 4.1 FreeRTOS wrapper

Do not use raw FreeRTOS API throughout the codebase. Wrap it:

```cpp
// firmware/include/kernel/Task.h
class Task {
public:
  using EntryPoint = void(*)(void*);
  
  static Task* create(EntryPoint fn, void* param, 
                      const char* name, uint32_t stack_words,
                      UBaseType_t priority, CoreNumber core);
  void suspend();
  void resume();
  void delete_();
  void notify(uint32_t bits);
  uint32_t wait_notification(uint32_t bits, TickType_t timeout);
  
  // Never expose xTaskHandle directly above HAL boundary
};
```

**Why:** If you ever need to migrate from FreeRTOS to another RTOS (Zephyr, ThreadX, bare-metal), only the wrapper implementation changes. The rest of the codebase calls `Task::create()`.

### 4.2 Interrupt-safe communication

Design the inter-core and ISR-to-task communication primitives once:

```cpp
// firmware/include/kernel/LockFreeRing.h
// Generic, templated ring buffer for ISR → task communication
template<typename T, size_t N>
class LockFreeRing {
  static_assert((N & (N-1)) == 0, "N must be power of 2");
public:
  bool push(const T& item);      // ISR-safe, no lock
  bool pop(T& out_item);         // Task-side
  size_t available() const;      // Approximate count
};
```

**Used for:** IMU samples, audio frames, radio RX packets, model inference requests. Never use `xQueue` for high-frequency paths.

### 4.3 Kernel testing

Host-side kernel simulator:
```cpp
// host-tools/kernel-sim/SimTask.h
// Runs "tasks" as threads on host, simulating FreeRTOS scheduling
// Tests verify: priority ordering, context switch timing, deadlock detection
```

---

## 5. Phase 3 — Agent Framework (Weeks 23-30)

### 5.1 Agent interface

Every agent is a `Task` + a `ControlGraph`:

```cpp
// firmware/include/agents/IAgent.h
class IAgent {
public:
  virtual ~IAgent() = default;
  virtual AgentID id() const = 0;
  virtual const char* name() const = 0;
  
  // Lifecycle
  virtual ErrorCode start() = 0;
  virtual ErrorCode stop() = 0;
  virtual ErrorCode restart() = 0;  // Hot restart without reboot
  
  // Control graph
  virtual ErrorCode set_graph(const ControlGraph& graph) = 0;
  virtual ControlGraph get_graph() const = 0;
  
  // Status
  virtual AgentStatus status() const = 0;
  virtual uint32_t restart_count() const = 0;
};
```

**Built-in agents (implemented first):**
1. `SensorAgent` — IMU + microphone polling, feature extraction
2. `InferenceAgent` — TFLite invocation, model hot-reload
3. `VoiceAgent` — KWS, audio scene, VAD
4. `ConnectivityAgent` — NINA UART, BLE, Wi-Fi server
5. `PowerAgent` — Power state machine, battery monitor
6. `LearningAgent` — Federated averaging, delta collection
7. `SecurityAgent` — ATECC608A, secure boot, signing
8. `LoggingAgent` — Flash ring buffer, crash journal

### 5.2 Agent registry

A central registry manages all agents. It is the only component that holds `Task` handles and `IAgent` pointers:

```cpp
// firmware/include/kernel/AgentRegistry.h
class AgentRegistry {
public:
  ErrorCode register_agent(IAgent* agent);
  ErrorCode unregister_agent(AgentID id);
  IAgent* get_agent(AgentID id) const;
  
  // Hot restart
  ErrorCode restart_agent(AgentID id);
  
  // Bulk operations
  ErrorCode pause_all();
  ErrorCode resume_all();
  
  // Status
  std::vector<AgentStatus> list_all() const;
};
```

**Testing:** Mock agents that report fake sensor data, fake inference results. Full integration test: register 8 agents, verify they all run concurrently, verify inter-agent message routing, kill one agent, verify recovery.

---

## 6. Phase 4 — Model Infrastructure (Weeks 31-40)

### 6.1 Model format specification

Define the on-device model format **once**, in `docs/model-format.md`. This is the format that TFLite Micro loads, that OTA pushes, that the shadow-tester validates.

```
ARP-2040 Model Format (flatbuffer-compatible)
═══════════════════════════════════════════════
[4B] magic: 0x41524D4C "ARML"
[4B] version: uint32
[4B] model_id: uint32
[4B] schema_version: uint32
[4B] weight_crc32: uint32
[4B] weight_length: uint32
[4B] metadata_length: uint32
[4B] flags: uint32
[8B] reserved
[metadata_length B] JSON metadata (model name, training data, accuracy, author, date)
[weight_length B] TFLite FlatBuffer (or custom quantized weight format)
═══════════════════════════════════════════════
```

**Critical:** The weight section is a **self-contained TFLite FlatBuffer**. The wrapper is 32 bytes of header + optional metadata. The TFLite interpreter is initialized with a pointer to the weight section. No parsing, no conversion, no runtime unpacking.

### 6.2 Model compiler pipeline

```
Host-side pipeline (runs on desktop, not device):
═══════════════════════════════════════════════════════
1. Train model in PyTorch/TensorFlow
2. Export to ONNX (framework-agnostic intermediate)
3. Convert ONNX → TFLite (via tflite/onnx-tflite)
4. Quantize to int8 (full-integer, representative dataset)
5. Validate: run on host with TFLite Micro C++ simulator
6. Wrap in ARP-2040 Model Format (32B header + metadata)
7. Sign with ATECC608A private key
8. Generate shadow-test harness (100 representative samples + expected outputs)
9. Package: .armodel file (signed, self-contained)
═══════════════════════════════════════════════════════
```

**Tool:** `host-tools/model-compiler/armodel-cli` — a single command does steps 2-8:
```bash
armodel-cli build \
  --input model.onnx \
  --id 0x0001 \
  --name "KWS-v2" \
  --representative-dataset calibration_data/ \
  --output KWS-v2.armodel
```

### 6.3 Model runtime

```cpp
// firmware/include/ai/IModelRuntime.h
class IModelRuntime {
public:
  virtual ~IModelRuntime() = default;
  virtual ErrorCode load_model(const ModelDescriptor& desc) = 0;
  virtual ErrorCode invoke(const InputTensor& in, OutputTensor& out) = 0;
  virtual ModelInfo info() const = 0;
  virtual uint32_t version() const = 0;
};
```

**Implementation:** `TFLiteMicroRuntime` wraps `tflite::MicroInterpreter`. The interpreter is allocated from a fixed-size arena (no heap). Arena size is compile-time configurable per model.

### 6.4 Shadow testing

Before any model is promoted to `live`, it runs against 100 cached samples:

```cpp
// firmware/include/ai/ShadowTester.h
class ShadowTester {
public:
  struct Result {
    float live_accuracy;
    float shadow_accuracy;
    bool regression_detected;
    std::vector<uint32_t> mismatched_samples;
  };
  
  Result test(const ModelDescriptor& live, const ModelDescriptor& shadow);
};
```

**Host-side shadow tester:** Same code, compiled for host, runs on 1000-sample validation set during CI. Device-side shadow tester runs on 100 cached samples (the last 100 inference inputs stored in the flash ring buffer).

---

## 7. Phase 5 — Connectivity Mesh (Weeks 41-50)

### 7.1 Protocol design document

Before implementing any network code, write `docs/protocol-spec.md`. This is the **immutable contract** between device, mobile, and desktop. It defines:
- Message framing (TLV over TCP, chunked BLE)
- Every message type (see Section 10.2 of blueprint)
- Binary encoding rules (endianness, alignment, versioning)
- Error handling (retry, timeout, backpressure)
- Security (encryption, signing, replay protection)

**Rule:** Any change to this document is a major version bump. Implementation must support at least 2 protocol versions simultaneously for backwards compatibility.

### 7.2 Transport abstraction

```cpp
// firmware/include/transport/ITransport.h
class ITransport {
public:
  virtual ~ITransport() = default;
  virtual TransportType type() const = 0;
  virtual ErrorCode connect() = 0;
  virtual ErrorCode disconnect() = 0;
  virtual ErrorCode send(const Message& msg) = 0;
  virtual ErrorCode receive(Message& out_msg, uint32_t timeout_ms) = 0;
  virtual bool is_connected() const = 0;
};
```

Implementations:
- `BLETransport` (NimBLE GATT client + server)
- `WiFiTransport` (TCP client + server via NINA)
- `USBTransport` (CDC ACM for debugging + flashing)

**Testing:** `MockTransport` that records sent messages and replays pre-recorded receive sequences. Full integration tests run against a host-side server without hardware.

### 7.3 BLE GATT service design

Define GATT services in `docs/gatt-services.md` as UUID + characteristic tables:

```
Custom Services:
═══════════════════════════════════════════════════════
Service: Inference (0000xxxx-...)
  Char: KeywordEvent (notify)     — KWS result
  Char: GestureEvent (notify)     — IMU gesture
  Char: SensorSnapshot (notify)   — Context state
  Char: Alert (notify)            — Emergency alert
  Char: ModelPush (write, long)   — OTA model transfer
  Char: ConfigPush (write)        — Config update
  Char: ControlGraphPush (write)  — Graph update
  Char: ScriptPush (write, long)  — Bytecode script
  Char: Command (write, indicate) — Server → device command
═══════════════════════════════════════════════════════
```

---

## 8. Phase 6 — Self-Modification Engine (Weeks 51-60)

This is the highest-risk, highest-reward component. Implement it last, after every other layer is stable and tested.

### 8.1 Implementation order

Week 51-52: Control Graph compiler
- `host-tools/graph-compiler/`: takes a JSON/YAML graph definition, produces binary `ControlGraph` record
- Validates: no cycles (except explicit feedback loops), all node IDs valid, all next-node references valid
- Device-side: `ControlGraphLoader` loads binary from QSPI, validates CRC, produces `ControlGraphHeader` in SRAM

Week 53-54: Bytecode interpreter
- `firmware/scripting/interpreter.cpp`: stack-based VM, ~200 lines
- `host-tools/script-compiler/`: assembles human-readable bytecode to binary
- Shadow-test harness: runs bytecode against historical sensor data in sandbox task

Week 55-56: Atomic hot-reload coordinator
- `HotReloadCoordinator` class manages staging → verify → shadow-test → atomic-swap pipeline
- Coordinates between: `IAgent::set_graph()`, `IModelRuntime::load_model()`, `IConfigStore::write()`

Week 57-58: Self-coding sandbox
- Sandbox task runs new code in isolation
- Detects: stack overflow, memory access outside bounds, timeout, return value anomaly
- If sandbox passes → promote. If fails → reject + log.

Week 59-60: Mobile-server self-coding UI
- Flutter screen: "Edit Voice Pipeline" — drag-and-drop control graph nodes
- Visual script editor for bytecode
- Push button: "Deploy" → compile → sign → push → shadow-test → promote

---

## 9. Phase 7 — Mobile/Desktop Server (Weeks 61-72)

### 9.1 Protocol server implementation

**Desktop server (Python backend):**
- `FastAPI` or `aiohttp` for async TCP server
- `bleak` for BLE client (cross-platform)
- `llama.cpp` Python bindings for local LLM inference
- `sqlite3` for data store (or `duckdb` for analytical queries)
- `pydantic` for message serialization/deserialization

**Mobile server (Flutter):**
- `flutter_blue_plus` for BLE
- `llama.cpp` via FFI for on-device LLM (when phone is the gateway)
- `sqflite` for local data store
- Background isolate for always-on BLE listener

### 9.2 LLM integration

**Model options by device capability:**

| Device | Recommended Model | Size | RAM Required |
|---|---|---|---|
| Desktop (8 GB+) | Llama-3.2-3B-Instruct | ~2 GB | 4 GB |
| Desktop (4 GB) | Phi-3-mini-4k-instruct | ~2.4 GB | 3 GB |
| Desktop (low) | Qwen2.5-1.5B-Instruct | ~1 GB | 2 GB |
| High-end phone (8 GB+) | Phi-3-mini-3.8B | ~2.2 GB | 3 GB |
| Mid phone (4 GB) | Qwen2.5-0.5B-Instruct | ~400 MB | 1 GB |
| Low phone | Gemma-2-2B-IT | ~1.5 GB | 2 GB |

**Context management:**
- Device sends compressed context vector (128 floats, ~512 bytes) every 5 seconds
- Server maintains per-user context store with sliding window
- System prompt includes: user preferences, device state, recent events, time/location
- Server sends structured intent back to device (not raw text) for reliability

### 9.3 Federated learning server

```python
# desktop-server/backend/federated/server.py

class FederatedLearningServer:
  def __init__(self, db_path: str):
    self.db = sqlite3.connect(db_path)
    self.pending_deltas: Dict[DeviceID, LoRADelta] = {}
  
  def receive_delta(self, device_id: DeviceID, delta: LoRADelta):
    """Receive signed delta from device, validate, queue for aggregation."""
    if not self.verify_signature(delta, device_id):
      raise SignatureError("Invalid delta signature")
    self.pending_deltas[device_id] = delta
  
  def aggregate(self, min_devices: int = 3) -> GlobalModel:
    """Run FedAvg on collected deltas, produce new global model."""
    if len(self.pending_deltas) < min_devices:
      raise InsufficientData("Need at least 3 deltas")
    
    deltas = list(self.pending_deltas.values())
    global_delta = self.fedavg(deltas)
    
    # Validate global delta against held-out test set
    accuracy = self.validate(global_delta)
    if accuracy < self.min_accuracy:
      raise RegressionError(f"Accuracy {accuracy:.2%} below threshold")
    
    return GlobalModel(delta=global_delta, version=self.next_version())
  
  def distribute(self, model: GlobalModel):
    """Push new model to all enrolled devices."""
    for device_id in self.enrolled_devices():
      self.push_model(device_id, model)
```

---

## 10. Phase 8 — Production Hardening (Weeks 73-84)

### 10.1 Complete test suite

Target coverage metrics:
- **Firmware HAL unit tests:** 100% of HAL interface methods have mock-based tests
- **Agent integration tests:** 100% of agent message flows tested on host emulator
- **Hardware-in-loop tests:** 100% of HAL modules tested on real hardware weekly
- **Model accuracy regression:** Every model commit triggers accuracy test against 1000-sample validation set
- **Protocol compliance:** Fuzzing test on device-side parser (send malformed messages, verify graceful rejection)
- **Power profile tests:** Automated current measurement at each power state; regression alert if >10% deviation

### 10.2 Static analysis

```bash
# Firmware
pio run -e nano_rp2040_connect -t compile_commands.json
clang-tidy firmware/src/**/*.cpp --checks='*' --warning-as-errors='*'

# Host tools
mypy host-tools/ --strict
pylint host-tools/ --fail-under=9.0

# Mobile
flutter analyze
```

### 10.3 Fuzzing

```bash
# Protocol fuzzer (host-side)
python host-tools/test-runner/fuzz_protocol.py \
  --target firmware/include/transport/ \
  --duration 3600 \
  --corpus-dir tests/fuzz/corpus/
```

### 10.4 Documentation automation

- Use Doxygen for C++ API docs → generates `docs/api-reference/`
- Use `mkdocs` with `mkdocstrings` for Python docs
- Use `flutter_api_guard` for Flutter API docs
- All docs are built and deployed on every merge to `main`

---

## 11. Scalability & Modularity Rules

These are **non-negotiable architectural laws**. Violating any of them creates the tight coupling that kills long-term projects.

### Rule 1: Dependency direction is always inward

```
agents  →  kernel  →  hal
   ↓         ↓        ↓
transport  →  storage  →  crypto
```

Agents may depend on kernel and HAL. Kernel may depend on HAL. HAL may depend on nothing outside itself. **Never create a dependency from HAL to agents.** This means the HAL cannot reference any agent type, any AI model type, or any transport type.

### Rule 2: Interfaces are frozen, implementations are replaceable

- `ISensor` is frozen. Adding a new sensor means writing a new `Impl*` class, not changing `ISensor`.
- `IRadio` is frozen. Adding Wi-Fi 6 or Bluetooth 5.2 means writing a new `Impl*`, not changing `IRadio`.
- Model format is frozen. Adding a new quantization scheme means extending the format version, not changing the parser.

**Freeze process:** An interface is only changed after a 6-month deprecation period. The old interface is kept as a compatibility shim for one major version cycle.

### Rule 3: No global mutable state

Every piece of mutable state is owned by exactly one object and accessed through an interface. No `extern` variables, no singleton patterns, no global registries that can be modified from anywhere.

**Exception:** `AgentRegistry` is the one global immutable registry, initialized at boot and never modified. Agents register themselves at startup. The registry is `const` after initialization.

### Rule 4: Every module is independently buildable and testable

```bash
# Build and test HAL only (no firmware, no agents)
make -C firmware hal-test

# Build and test kernel only
make -C firmware kernel-test

# Build host-side device emulator + run full integration tests
make integration-test

# Build and flash ONLY the HAL test suite
pio run -e nano_rp2040_connect -t upload
```

### Rule 5: Data formats are versioned and backwards-compatible

Every on-flash structure has a `version` field. The reader always handles versions older than the current one. The writer never produces versions newer than the reader understands.

```cpp
struct ConfigHeaderV1 { uint32_t magic; uint32_t version; ...; };
struct ConfigHeaderV2 : ConfigHeaderV1 { uint32_t new_field; ...; };

ErrorCode read_config_v1(const FlashRegion& r, ConfigV1& out);
ErrorCode read_config_v2(const FlashRegion& r, ConfigV2& out);

// Reader:
ErrorCode read_config(const FlashRegion& r, ConfigHeader& out) {
  if (r.version == 1) return read_config_v1(r, out);
  if (r.version == 2) return read_config_v2(r, out);
  return ErrorCode::UNSUPPORTED_VERSION;
}
```

### Rule 6: Failure is always recoverable

Every component has a `self_test()` method that returns PASS/FAIL without external test gear. On boot, every component runs `self_test()`. If any component fails, it is disabled and the system enters degraded mode with an alert to the server.

---

## 12. 100-Year Architecture Principles

### 12.1 Hardware independence

The HAL is so thoroughly abstracted that the entire firmware codebase (above `hal/impl/`) could be compiled for a different MCU by writing a new HAL implementation without changing a single line of application code.

**Target future hardware platforms:**
- RP2350 (RP2040 successor, same Pico ecosystem)
- ESP32-S3 (if NINA module is replaced)
- nRF9160 (Nordic SiP with integrated LTE-M/NB-IoT)
- Custom ASIC (if this design justifies silicon)

### 12.2 Radio independence

The `IRadio` interface abstracts Wi-Fi, BLE, LTE, Thread, Zigbee, or any future radio. Adding a new radio means:
1. Write `IRadio` implementation
2. Write protocol adapter (translate internal messages to radio-specific frames)
3. Update `ConnectivityAgent` to use new implementation

### 12.3 Model format independence

The `IModelRuntime` interface currently wraps TFLite Micro. In 10 years, TFLite may be obsolete. The interface is stable; swap the implementation:

```cpp
class OnnxRuntimeMicroRuntime : public IModelRuntime { ... };
class CustomDSPRuntime : public IModelRuntime { ... };
class FutureFormatRuntime : public IModelRuntime { ... };
```

The model compiler toolchain (`host-tools/model-compiler/`) is similarly plugin-based:
```python
# host-tools/model-compiler/backends/
tflite_backend.py
onnx_backend.py
custom_backend.py
```

### 12.4 Protocol evolution

The wire protocol supports multiple versions simultaneously. The device implements both old and new parsers during transition periods. The server negotiates the highest common version during connection setup.

```cpp
// Protocol version negotiation
Message negotiate_version(const VersionRange& device_versions,
                          const VersionRange& server_versions) {
  uint8_t common = highest_common(device_versions, server_versions);
  return Message::version_ack(common);
}
```

### 12.5 Data portability

All user data stored on QSPI flash is in a format that can be read and migrated by a future host-tools version:

- Sensor logs: CSV-like with versioned header, readable by any spreadsheet or analysis tool
- Model deltas: Versioned binary, with documented byte layout
- Config: JSON in metadata section, versioned header
- Crash journal: Versioned binary, with documented layout

**Migration rule:** Every new data format version includes a migration path from the previous version. The host-tools `migrate` command converts old-format flash dumps to new-format.

```bash
# Migrate flash dump from v1 firmware to current format
armigrate --input flash_dump_v1.bin --output flash_dump_v2.bin
```

### 12.6 Licensing and governance

For a project intended to last 100 years:
- **License:** Choose a copyleft license (GPL-3.0 or AGPL-3.0) to prevent proprietary forks from fragmenting the ecosystem
- **Governance:** Establish a lightweight foundation or collective. Even if you are the sole maintainer today, document the succession plan.
- **Patent grant:** Include an explicit patent grant in the license to prevent future patent trolls from attacking users.

---

## 13. Tooling & Developer Experience

### 13.1 Essential scripts

```bash
# Top-level Makefile targets:
make build          # Build firmware + host-tools + mobile + desktop
make flash          # Flash firmware via USB
make test           # Run all tests
make test-hardware  # Run hardware-in-loop tests
make emulator       # Start host-side device emulator for rapid dev
make lint           # Run all linters + static analysis
make docs           # Build documentation site
make clean          # Clean all build artifacts

# Rapid dev loop:
make emulator       # Starts device emulator on localhost:7777
make test           # Tests run against emulator (no hardware needed)
# Developer can iterate on 90% of changes without touching hardware
```

### 13.2 Device emulator

The most important developer tool. A host-side simulator that implements every `I*` interface using host resources:

```cpp
// host-tools/device-emulator/MockRadio.cpp
class MockRadio : public IRadio {
public:
  ErrorCode connect() override {
    // Actually opens a TCP connection to a host-side network simulator
    return ErrorCode::OK;
  }
  ErrorCode send(const Message& msg) override {
    // Serializes to JSON, sends to network simulator
    return ErrorCode::OK;
  }
};

// host-tools/device-emulator/network_simulator.py
# Simulates BLE/Wi-Fi by actually using host's network stack
# Allows full integration testing without hardware
```

**Goal:** A developer can write, test, and debug 90% of firmware code on their desktop without ever plugging in the RP2040.

### 13.3 Debugging support

- `SerialDebug` class: sends debug messages over USB CDC (or UART0 to NINA → Wi-Fi → desktop)
- Log levels: `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`
- All `TRACE`/`DEBUG` messages are compiled out in release builds (zero overhead)
- Desktop app has a live log viewer that shows messages from all connected devices simultaneously

---

## 14. Testing Strategy

### 14.1 Test pyramid

```
        ┌─────────────┐
        │ Hardware    │  10% — Runs weekly, requires physical device
        │ in-loop     │
        ├─────────────┤
        │ Integration │  30% — Runs on every commit, uses emulator
        ├─────────────┤
        │ Unit        │  60% — Runs on every commit, host-only, <1s each
        └─────────────┘
```

### 14.2 Test categories

| Category | Tool | Frequency |
|---|---|---|
| HAL unit tests | GoogleTest + mocks | Every commit |
| Agent logic tests | GoogleTest | Every commit |
| Kernel tests | GoogleTest + host-sim | Every commit |
| Protocol parser tests | Python pytest + fuzzing | Every commit |
| Model accuracy regression | host-tools + pytest | Every commit (on changed models) |
| Integration tests | Device emulator + pytest | Every commit |
| Hardware-in-loop | Custom test runner | Weekly + on release |
| Power profile tests | INA219 + pytest | Weekly |
| Stress test (72h) | Hardware runner | Before each release |
| Security audit | Manual + SAST tools | Before each major release |

### 14.3 Test fixtures

All sensor data, model inputs, and protocol messages used in tests are stored as binary fixtures in `tests/fixtures/`. These fixtures are recorded from real hardware and checked into git. This ensures tests are deterministic and reproducible.

```bash
tests/fixtures/
├── imu/
│   ├── walking_30s.bin
│   ├── running_30s.bin
│   └── falling_5s.bin
├── audio/
│   ├── keyword_hey_arp_01.bin
│   └── background_noise_01.bin
├── models/
│   ├── kws_v1_accuracy_samples.bin
│   └── kws_v2_accuracy_samples.bin
└── protocol/
    ├── valid_messages.bin
    └── fuzz_corpus/
```

---

## 15. Risk Register & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NINA firmware is not open-source | High | High | Wrap NINA behind `IRadio` interface. If NINA becomes unavailable, swap to ESP32-S3 module with compatible `IRadio` implementation. Application code never changes. |
| TFLite Micro is abandoned | Medium | High | Model format is plugin-based. Add `ONNX Runtime Micro` backend. All model compiler outputs ONNX as intermediate. |
| RP2040 becomes obsolete | Medium | Medium | HAL abstraction allows port to RP2350 or any ARM Cortex-M with similar peripheral set. Port effort: ~4 weeks for HAL layer only. |
| Arduino-Pico core maintenance stops | Low | Medium | If Arduino-Pico is abandoned, port to bare-metal RP2040 SDK. HAL layer isolates this dependency. |
| ATECC608A supply shortage | Medium | Low | Crypto interface is abstracted. Fallback: software crypto (mbedTLS) + device-unique key derived from RP2040 unique ID. |
| FreeRTOS licensing conflict | Low | Medium | Use Amazon FreeRTOS (MIT) or Zephyr (Apache 2.0) as alternative. Kernel wrapper isolates this. |
| Memory budget exceeded | Medium | High | Fixed-size arenas, pre-allocated pools. If model grows beyond SRAM, add external PSRAM via QSPI (RP2040 supports it). |
| Flash wear | Medium | Medium | LittleFS wear-leveling. Staging regions absorb most writes. 100K cycle rating × staging regions = effectively infinite. |

---

## Appendix A: Week-by-Week Execution Checklist

### Weeks 1-6: Foundation
- [ ] Repository structure created
- [ ] CMake + PlatformIO build system working
- [ ] `ISensor`, `IRadio`, `ICrypto`, `IStorage` interfaces defined in `docs/hal-spec.md`
- [ ] CI/CD pipeline running (lint + unit tests)
- [ ] Host-side flash simulator working
- [ ] First HAL test passing on host (mock I2C, mock flash)

### Weeks 7-14: HAL
- [ ] `IStorage` + QSPI transactional layer implemented + tested
- [ ] `IRadio` + NINA UART transport implemented + tested
- [ ] LSM6DSOX + MP34DT06 drivers implemented + tested
- [ ] `ICrypto` + ATECC608A driver implemented + tested
- [ ] `IPower` + power state machine implemented + tested
- [ ] Every HAL module has host-side mock + hardware-in-loop test

### Weeks 15-22: Kernel
- [ ] FreeRTOS wrapper (`Task`, `LockFreeRing`, `AgentRegistry`)
- [ ] Kernel tests pass on host simulator
- [ ] Boot stub working (reads metadata, promotes firmware)
- [ ] Crash journal + rollback journal implemented
- [ ] Power-loss recovery tested with relay-cut method

### Weeks 23-30: Agents
- [ ] All 8 built-in agents implemented
- [ ] AgentRegistry + hot_restart_task working
- [ ] Each agent has unit test + integration test
- [ ] Inter-agent message routing verified

### Weeks 31-40: Models
- [ ] Model format specification finalized
- [ ] `armodel-cli` tool working (ONNX → signed .armodel)
- [ ] TFLiteMicroRuntime implemented + tested
- [ ] Shadow tester working on host + device
- [ ] First KWS model trained, quantized, deployed, tested

### Weeks 41-50: Connectivity
- [ ] Protocol spec finalized + frozen
- [ ] `ITransport` + BLE + WiFi implementations
- [ ] GATT services implemented + tested
- [ ] Binary protocol parser + fuzzer passing
- [ ] Mobile app (Flutter) BLE discovery + streaming working

### Weeks 51-60: Self-Modification
- [ ] Control graph compiler + loader
- [ ] Bytecode interpreter + assembler
- [ ] HotReloadCoordinator (atomic pipeline)
- [ ] Shadow-test sandbox for code changes
- [ ] Mobile app graph editor + script editor

### Weeks 61-72: Servers
- [ ] Desktop server: TCP + BLE server + LLM integration
- [ ] Mobile app: full feature set (discovery, pairing, streaming, LLM, TTS)
- [ ] Federated learning server + client protocol
- [ ] Data store + analytics dashboard
- [ ] Shadow-test promotion from server

### Weeks 73-84: Hardening
- [ ] 100% HAL unit test coverage
- [ ] 72-hour stress test passing
- [ ] Power profile tests: 7-day battery target met
- [ ] Security audit (static analysis + manual review)
- [ ] Documentation complete (Doxygen, mkdocs, API reference)
- [ ] Release candidate tagged + tested on 3 devices

---

## Appendix B: The 100-Year Checklist

Before declaring v1.0.0 production-ready, verify:

- [ ] Every public API has a version number and a deprecation policy
- [ ] Every on-flash data structure has a version field and backward-compatible reader
- [ ] Every HAL module has a host-side mock and a hardware-in-loop test
- [ ] Every agent has a self_test() that returns PASS/FAIL without external gear
- [ ] The build system can compile the entire project from a fresh checkout in <10 minutes
- [ ] A new developer can build, flash, and run the device from scratch in <2 hours (per build-guide.md)
- [ ] The device can recover from any single fault without user intervention
- [ ] Any model, config, or logic change can be made without rebooting (or with <2s reboot)
- [ ] Any previous model, config, or logic version can be restored in <5 seconds
- [ ] The protocol specification is versioned and backwards-compatible for at least 2 major versions
- [ ] All user data is in a documented, versioned, migratable format
- [ ] The project has a succession plan (who maintains it if the original author cannot)
- [ ] The license includes an explicit patent grant
- [ ] All third-party licenses are tracked and compliant
- [ ] The CI/CD pipeline builds, tests, and packages the entire project on every commit
- [ ] The device emulator can run the full firmware stack without hardware
- [ ] Static analysis passes with zero warnings
- [ ] Fuzzing has been run for ≥1000 CPU-hours on the protocol parser
- [ ] Power loss during any operation has been tested and verified to recover correctly
- [ ] The codebase compiles with ≥3 different compiler versions without warnings

---

*This document is the execution plan. The blueprint (`ARP2040_Connect_Wearable_AI_Design_Blueprint.md`) is the design reference. Together they define everything that needs to be built, in what order, and to what standard.*
