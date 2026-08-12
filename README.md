# WearableAI

Personal wearable AI assistant built from scratch for the Arduino Nano RP2040 Connect.

## What this is

A complete firmware + host-tools + mobile-server + desktop-server codebase for a modular, self-healing, self-improving wearable AI assistant. Every layer — from HAL interfaces to wire protocol to model format — is designed to outlive any single component.

## Repository layout

- `arp-2040/` — RP2040 firmware (FreeRTOS, C++17), host tools, emulators, model compilers
- `arduino-mcp-toolkit/` — MCP server with 35 tools for Arduino control, TinyML, mesh, OTA
- `arduino-dashboard/` — FastAPI + WebSocket dashboard with serial/BLE/Wi-Fi transports
- `docs/` — Design blueprint, HAL spec, protocol spec, build plans

## Hardware target

- **Arduino Nano RP2040 Connect** — RP2040 dual-core 133 MHz + NINA-W102 Wi-Fi/Bluetooth
- Onboard: LSM6DSOX IMU, MP34DT06J MEMS mic, ATECC608A crypto, 16 MB QSPI flash

## Key features

- Atomic firmware upgrades with rollback
- Hot model reload without downtime
- Self-modifying code via control graphs and bytecode interpreter
- TinyML training and on-device inference
- BLE + Wi-Fi hybrid mesh networking
- ATECC608A hardware security

## Getting started

See subproject READMEs for detailed setup:

- `arp-2040/README.md` — firmware, emulator, build steps
- `arduino-mcp-toolkit/README.md` — MCP tools and Hermes integration
- `arduino-dashboard/README.md` — dashboard setup and transports

## Documentation

- `docs/ARP2040_Connect_Wearable_AI_Design_Blueprint.md` — Hardware-grounded design reference
- `docs/ARP2040_Connect_100Year_Build_Plan.md` — 84-week execution plan

## License

GPL-3.0 with explicit patent grant. See `LICENSE`.
