# Changelog

All notable changes to this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-12

### Added
- Initial repository structure with three integrated subprojects:
  - `arp-2040` — RP2040 firmware, host tools, emulators, model compilers, and tests
  - `arduino-mcp-toolkit` — MCP server exposing 35 tools and 14 resources for Arduino control
  - `arduino-dashboard` — FastAPI + WebSocket dashboard with serial/BLE/Wi-Fi transports
- Top-level `README.md` describing repo layout, hardware target, and getting-started pointers
- `LICENSE` — GNU General Public License v3.0
- `CONTRIBUTING.md` and `SECURITY.md`
- `CHANGELOG.md`
- `.gitignore` with patterns for Python, PlatformIO, caches, and model binaries
- `.gitattributes` for LF normalization and binary safety for model artifacts
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) covering:
  - `arduino-dashboard` tests
  - `arduino-mcp-toolkit` tests
  - `arp-2040` unit tests
  - `arp-2040` integration tests
- Issue templates: bug report and feature request
- Pull request template
- Dependabot configuration for Python dependencies
- `v0.1.0` GitHub release with auto-generated notes

### Changed
- Repository topics: `arduino`, `freertos`, `mcp`, `tinyml`, `wearable`, `wearable-ai`
- Enabled GitHub Issues and Discussions
- Phase 1 firmware scaffolding:
  - Added `HALFactory.h` for HAL construction
  - Added `RP2040Sensor.h` for LSM6DSOX IMU + MP34DT06J microphone
  - Filled `RP2040Sensor.cpp` with I2C register-level IMU read/write, self-test, MLC stubs
  - Fixed PlatformIO include path for `common/common_types.h`

### Fixed
- Removed committed caches, build artifacts, `.bak` files, `.egg-info`, `.pio`, and `.pytest_cache` from history
- Resolved spurious binary diffs on model artifacts caused by line-ending normalization
- Fixed LSP diagnostics for `common_types.h` include resolution in HAL headers

### Verified
- Local pytest is green across all subprojects:
  - `arduino-mcp-toolkit`: 27 passed
  - `arduino-dashboard`: 15 passed
  - `arp-2040` unit + integration: 20 passed
- `main` branch protection enabled:
  - Require CI status checks before merge
  - Require 1 approving review before merge
