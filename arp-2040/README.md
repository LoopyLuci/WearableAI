# ARP-2040 Connect Wearable Personal Assistant

## Next-generation wearable AI with atomic hot-reload, self-modification, and 100-year modularity

Built from scratch for the **Arduino Nano RP2040 Connect**:
- RP2040 dual-core 133 MHz Arm® Cortex®-M0+
- NINA-W102 dual-core 240 MHz Xtensa LX6 (Wi-Fi 802.11b/g/n + Bluetooth 4.2+BLE)
- LSM6DSOX 6-axis IMU with onboard Machine Learning Core
- MP34DT06J omnidirectional MEMS microphone
- ATECC608A hardware crypto co-processor
- 16 MB QSPI flash, 264 KB SRAM, 520 KB NINA SRAM

## What this is

This is a complete firmware + host-tools + mobile-server + desktop-server codebase for a **truly modular, self-healing, self-improving wearable AI assistant**. Every layer — from HAL interfaces to wire protocol to model format — is designed to outlive any single component.

## Repository layout

```
arp-2040/
├── firmware/           # RP2040 firmware (FreeRTOS, C++17)
│   ├── include/        # Public headers (frozen interfaces)
│   │   ├── hal/        # ISensor, IRadio, ICrypto, IStorage, IPower, IAudio, IDisplay, IActuator
│   │   ├── kernel/     # ITask, ILockFreeRing, IAgentRegistry
│   │   ├── agents/     # IAgent
│   │   ├── ai/         # IModelRuntime, IShadowTester
│   │   ├── transport/  # ITransport
│   │   ├── storage/    # ITransactionalStore
│   │   ├── scripting/  # IBytecodeInterpreter, ControlGraph types
│   │   └── common/     # ErrorCode, SensorType, RadioType, PowerState, etc.
│   ├── src/            # Implementations
│   └── tests/          # Firmware-side tests
│
├── host-tools/         # Runs on desktop, NOT on device
│   ├── flash-sim/      # 16 MB QSPI flash simulator
│   ├── device-emulator/# Full device emulator (all I* interfaces)
│   ├── kernel-sim/     # FreeRTOS task scheduler simulator
│   ├── model-compiler/ # PyTorch → ONNX → TFLite → signed .armodel
│   ├── graph-compiler/ # Control graph → binary
│   ├── script-compiler/# Bytecode assembler
│   └── test-runner/    # Hardware-in-loop test runner
│
├── mobile-server/      # Flutter app (iOS + Android)
├── desktop-server/     # Electron/Tauri app (Windows/Mac/Linux)
├── docs/               # Blueprint, HAL spec, protocol spec, build guide
├── tests/              # Unit, integration, hardware, fixtures
├── models/             # Source model definitions + training scripts
└── scripts/            # Build, flash, test automation
```

## Key architectural properties

| Property | Mechanism |
|---|---|
| **Atomic upgrades** | Staging → CRC → pointer-swap → promote; no in-place writes |
| **Hot model reload** | Shadow-test → `taskENTER_CRITICAL()` pointer-swap; zero downtime |
| **Self-modifying code** | Control graph + bytecode interpreter; logic changes without reflash |
| **Crash recovery** | 4-layer: hardware watchdogs → software hooks → crash journal → autonomous self-repair |
| **Rollback** | 128 KB rollback journal; manual or automatic |
| **100-year modularity** | All hardware behind frozen `I*` interfaces; dependency direction inward |
| **Testability** | Every layer has a host-side mock; 90% of dev happens without hardware |

## Getting started

### Prerequisites

- Python 3.11+
- PlatformIO CLI (`pip install platformio`)
- CMake 3.20+
- Git
- (Optional) pyserial for hardware-in-loop tests

### Build

```bash
# Clone
git clone https://github.com/your-org/arp-2040.git
cd arp-2040

# Install host tools
pip install -r host-tools/requirements.txt

# Run tests (no hardware needed)
pytest tests/unit/ tests/integration/

# Build firmware
pio run -e nano_rp2040_connect -d firmware

# Flash firmware
pio run -e nano_rp2040_connect -d firmware -t upload
```

### Run emulator (no hardware)

```bash
python host-tools/device-emulator/device_emulator.py
python tests/integration/test_device_emulator.py
```

## Documentation

- `docs/ARP2040_Connect_Wearable_AI_Design_Blueprint.md` — Hardware-grounded design reference
- `docs/ARP2040_Connect_100Year_Build_Plan.md` — 84-week execution plan
- `docs/hal-spec.md` — HAL interface contracts (frozen)
- `docs/protocol-spec.md` — Wire protocol specification
- `docs/build-guide.md` — Step-by-step build instructions

## License

GPL-3.0 with explicit patent grant. See LICENSE.

---

**Status:** Foundation phase. HAL interfaces + kernel + emulator + test infrastructure implemented. Buildable structure ready for Phase 1 implementation.
