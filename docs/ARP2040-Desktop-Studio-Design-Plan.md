# ARP-2040 Desktop Studio — Comprehensive Design Plan

## 1. Vision & Scope

A single cross-platform desktop application that serves as the **unified control plane** for the ARP-2040 wearable project. It must cover:

- **Device lifecycle**: detect, configure, flash, monitor, and debug the Arduino RP2040 over USB/serial.
- **Telemetry pipeline**: ingest, buffer, visualize, and export IMU/audio/model inference data in real time.
- **Model workflow**: manage TFLite models, run host-side inference, compare device vs. host results, and tune thresholds.
- **Project orchestration**: scaffold, build, test, and package firmware from the same UI.
- **CLI shell**: a built-in terminal exposing every capability as a typed command, with history, autocomplete, and piping.
- **Reliability**: atomic hot reload of UI panels, CLI extensions, and visualization plugins without restarting the app or dropping device connections.

The app must feel **simple for daily use** but **powerful enough that an advanced user never needs to leave it**.

---

## 2. Technology Stack

### 2.1 Rationale
We need:
- True cross-platform binaries (Windows, macOS, Linux).
- A stable, fast GUI framework with strong widget support and accessibility.
- Rust for the backend (device I/O, serial, filesystem, compression, database).
- A web-based frontend for rapid visualization iteration.
- Built-in terminal emulation.
- Hot reload without restarting native code.

**Tauri 2.x + React + TypeScript** is the best fit:
- Tauri bundles a Rust backend and a webview frontend into a ~10 MB native binary.
- The Rust side owns device/serial/filesystem work with full async support.
- The frontend can use any JS visualization library (Plotly, Deck.gl, D3, ECharts).
- Tauri 2.x supports **stateful hot reload** of the frontend without rebuilding the Rust binary.
- `tauri-cli` supports **`tauri dev`** for iterative development and `tauri build` for packaging.

### 2.2 Stack Summary

| Layer              | Technology                                           | Why                                                                 |
|--------------------|------------------------------------------------------|---------------------------------------------------------------------|
| Desktop shell      | Tauri 2.x (Rust + Webview2/WebKit)                   | Small binary, secure IPC, hot reload frontend, cross-platform.    |
| Frontend framework | React 18 + TypeScript + Vite                         | Ecosystem depth, hot module reload, strong typing.                 |
| UI component lib   | MUI v6 or ShadCN UI                                  | Accessible, themeable, keyboard-friendly, professional look.      |
| Charts             | Plotly.js + ECharts + lightweight Canvas charts       | Telemetry-ready, zoom/pan, large dataset performance.             |
| Terminal           | xterm.js + node-pty-style Rust backend process       | Full PTY emulation, ANSI colors, scrollback.                      |
| Database           | SQLite (via `rusqlite`) + DuckDB for analytics        | Local-first, embedded, fast time-series queries.                  |
| Serial/USB         | `serialport` equivalent in Rust (`serialport` crate)  | Cross-platform serial, hotplug, permission handling.              |
| Firmware build     | PlatformIO core library (Rust wrapper or subprocess) | Reuse existing `pio run`, parse output, extract artifacts.         |
| CLI framework      | `clap` (Rust) for native CLI + Tauri commands        | Subcommand hierarchy, shell completions, help generation.         |
| State management   | Zustand + Immer                                      | Simple, fast, serializable for hot reload.                        |
| Hot reload system  | Tauri events + file watcher + HMR                    | Frontend: Vite HMR; Backend: plugin hot-swap + config reload.     |
| Testing            | Vitest (frontend), `cargo test` (Rust), Playwright    | Unit, integration, and E2E coverage.                              |
| CI/CD              | GitHub Actions                                       | Matrix build for Windows/macOS/Linux, sign and notarize.          |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React/TS)                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │
│  │ Device Panel │ │ Telemetry UI │ │ Model Studio             │  │
│  │ - Detect     │ │ - Real-time  │ │ - Upload / Run / Compare │  │
│  │ - Flash      │ │ - Charts     │ │ - Threshold tuning       │  │
│  │ - Serial     │ │ - Heatmaps   │ │ - Quantization preview   │  │
│  └──────┬───────┘ └──────┬───────┘ └───────────┬──────────────┘  │
│         │                │                     │                 │
│  ┌──────▼────────────────▼─────────────────────▼──────────────┐  │
│  │                  State Store (Zustand)                      │  │
│  │  - Device state  - Telemetry buffers  - Model registry      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│         │                │                     │                 │
│  ┌──────▼────────────────▼─────────────────────▼──────────────┐  │
│  │               Tauri IPC Bridge                               │  │
│  └────────────────────────┬────────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     Rust Backend (Tauri)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │ Device Mgmt │ │ Serial/Snap │ │ Firmware    │ │ CLI Shell │  │
│  │ - USB enum  │ │ - Ring buf  │ │ - PIO wrap  │ │ - PTY     │  │
│  │ - Bootsel   │ │ - Parquet   │ │ - ELF/UF2   │ │ - Autocom │  │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘  │
│         │                │                │              │       │
│  ┌──────▼────────────────▼────────────────▼──────────────▼─────┐ │
│  │                   Core Services                              │ │
│  │  - Event bus  - Config mgmt  - Plugin loader  - Hot reload  │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘

MCP SERVER INTEGRATION (cross-cutting):
┌─────────────────────────────────────────────────────────────────┐
│                   Built-in MCP Server (stdio/stdout)             │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │
│  │ Device Tools  │ │ Telemetry     │ │ Model/Project Tools   │  │
│  │ - list        │ │ - read_live   │ │ - build               │  │
│  │ - flash       │ │ - query       │ │ - flash               │  │
│  │ - monitor     │ │ - export      │ │ - run_model           │  │
│  │ - bootsel     │ │ - snapshot    │ │ - list_models         │  │
│  └───────────────┘ └───────────────┘ └───────────────────────┘  │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │
│  │ GUI Control   │ │ CLI Bridge    │ │ Plugin/System Tools   │  │
│  │ - open_panel  │ │ - execute     │ │ - plugin_list         │  │
│  │ - set_config  │ │ - history     │ │ - config_get/set      │  │
│  │ - screenshot  │ │ - autocomplete│ │ - hot_reload          │  │
│  └───────────────┘ └───────────────┘ └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. MCP Server Integration (Built-in)

### 4.1 Why MCP Must Be First-Class
Hermes Agent and any external agent must control the desktop studio exactly like a human user: open panels, start streams, flash firmware, run models, and read state. The Model Context Protocol is the universal interface for that. This app therefore ships with a **built-in MCP server**, not as an afterthought plugin, but as a core runtime component.

### 4.2 Architecture: Dual Frontends, One Backend
```
┌─────────────────────────────────────────────────────────────────┐
│                     Built-in MCP Server                          │
│  • stdio/stdout transport by default                             │
│  • Optional TCP/WebSocket transport for remote agents            │
│  • All tools map 1:1 to existing Rust backend commands           │
│  • GUI actions exposed as MCP resources and tools               │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
   ┌────────────▼───────────┐   ┌───────────▼───────────────┐
   │ Human GUI (React/TS)   │   │ Agent Runtime (Hermes,    │
   │ - same Tauri IPC       │   │ Claude Code, OpenCode)    │
   │ - same event bus       │   │ - stdio MCP client        │
   │ - hot reload panels    │   │ - TCP MCP client          │
   └────────────────────────┘   └───────────────────────────┘
```

### 4.3 MCP Tool Surface

#### 4.3.1 Device Tools
- `device_list` → `DeviceManager::list_devices()`
- `device_info` → `DeviceManager::device_info(id)`
- `device_flash` → `DeviceManager::flash_firmware(id, path)`
- `device_monitor` → `SerialManager::open_stream(id)`
- `device_bootsel` → `DeviceManager::enter_bootsel(id)`
- `device_reboot` → `DeviceManager::reboot(id)`

#### 4.3.2 Telemetry Tools
- `telemetry_start` → start streaming from device
- `telemetry_stop` → stop streaming
- `telemetry_query` → DuckDB time-range query
- `telemetry_export` → export to Parquet/CSV
- `telemetry_snapshot` → force snapshot now
- `telemetry_live` → returns SSE/MCP notification stream

#### 4.3.3 Firmware & Project Tools
- `firmware_build` → wrap `pio run`
- `firmware_build_status` → poll running build
- `firmware_artifacts` → list `.elf/.uf2/.bin`
- `project_open` → switch project directory
- `project_config_get` → read `config.yaml`
- `project_config_set` → write `config.yaml` with atomic reload

#### 4.3.4 Model Tools
- `model_list` → model registry
- `model_upload` → copy `.tflite` into project
- `model_info` → inspect tensors/ops
- `model_run_host` → Rust TFLite inference
- `model_run_device` → send inference over serial
- `model_compare` → host vs. device diff data

#### 4.3.5 GUI Control Tools
- `gui_open_panel` → focus or open a view by id
- `gui_set_theme` → switch theme atomically
- `gui_screenshot` → capture current view as PNG
- `gui_layout_load` → apply saved layout
- `gui_layout_save` → persist current layout
- `gui_show_toast` → surface transient notification

#### 4.3.6 CLI Bridge Tools
- `cli_execute` → run built-in CLI command
- `cli_history` → read CLI history
- `cli_autocomplete` → get completions for prefix

#### 4.3.7 Plugin & System Tools
- `plugin_list` → enumerate loaded plugins
- `plugin_reload` → atomic plugin hot swap
- `system_info` → OS, app version, device count
- `hot_reload_trigger` → force frontend/backend reload
- `config_get` / `config_set` → atomic config with schema validation

### 4.4 Transport Modes

| Mode | Use Case | Implementation |
|------|----------|----------------|
| stdio | Local agent in same terminal | `stdin/stdout` JSON-RPC |
| TCP | Remote agent over network | `tokio::net::TcpListener` on `127.0.0.1:4532` |
| WebSocket | Browser-based agent | `tokio-tungstenite` on same port |

The transport is selected at startup via CLI flag or config:
```
arp-2040-studio --mcp-stdio
arp-2040-studio --mcp-tcp 127.0.0.1:4532
arp-2040-studio --mcp-ws
```

### 4.5 Permission & Security Model

MCP tools are gated by capability tokens, mirroring Tauri’s capability system:

```yaml
mcp:
  allow:
    - device_list
    - device_flash
    - telemetry_start
    - telemetry_stop
    - model_run_host
  deny:
    - device_bootsel
    - system_info
  require_confirmation:
    - device_flash
    - firmware_build
    - plugin_reload
```

- **Allow list**: tools available to external agents by default.
- **Deny list**: explicitly blocked tools (e.g., `device_bootsel` without UI confirmation).
- **Require confirmation**: tools that prompt the user via GUI before executing.

Hermes Agent, when launched as the user’s trusted agent, receives a session token granting the full allow list. Untrusted agents get a restricted view.

### 4.6 Atomic Hot Reload via MCP

MCP itself is the safest hot-reload trigger because it is serialized and can observe success/failure:

1. Agent calls `hot_reload_trigger` with `target: frontend|backend|config`.
2. Backend writes new assets to `.new` paths.
3. Backend atomically swaps paths and broadcasts `hot_reload_complete`.
4. Frontend VMR reloads new chunks; backend `libloading` swaps `.so`/`.dll`/`.dylib`.
5. If any step fails, backend rolls back and returns error via MCP tool result.

This makes hot reload **agent-controllable and observable**, which is required for autonomous long-running sessions.

### 4.7 Implementation Plan

#### Phase M1: MCP Core (Week 1)
- Add `rmcp` or `mcp-server-rs` crate to Tauri backend.
- Implement stdio transport with JSON-RPC 2.0.
- Expose 5 seed tools: `device_list`, `device_flash`, `telemetry_start`, `firmware_build`, `gui_open_panel`.
- Write Hermes integration test: spawn studio, call tools, assert state.

#### Phase M2: Transport & Permissions (Week 2)
- Add TCP/WebSocket transports.
- Implement capability token system.
- Add `config_get/set` with atomic file write + schema validation.
- Document MCP surface in `docs/mcp-tools.md`.

#### Phase M3: GUI Bridge (Week 3)
- Map every frontend action to an MCP tool or resource.
- Add `gui_screenshot`, `gui_layout_save/load`, `gui_show_toast`.
- Ensure MCP tool calls are observable in CLI and build log panels.

#### Phase M4: Observability & Hooks (Week 4)
- Add MCP notification channel for telemetry stream.
- Add `telemetry_live` as a streaming resource.
- Add hooks for plugin authors to register custom MCP tools.

---

### 4.1 Device Manager
**Goal**: manage the RP2040 as a first-class citizen.

- Enumerate USB devices, detect bootloader vs. runtime mode.
- Expose `device list`, `device info <id>`, `device reboot`, `device bootsel`.
- Flash UF2/BIN/ELF with progress bar and retry on disconnect.
- Auto-detect serial port on attach/detatch.
- Persist device profiles (serial number, nickname, last-used build).

**IPC surface**:
```rust
// Rust
#[tauri::command]
fn list_devices() -> Result<Vec<DeviceInfo>, DeviceError>;
#[tauri::command]
fn flash_firmware(device: &str, path: &str, progress: Callback) -> Result<(), FlashError>;
#[tauri::command]
fn enter_bootsel(device: &str) -> Result<(), DeviceError>;
```

### 4.2 Serial/Snapshot Manager
**Goal**: high-throughput, loss-tolerant telemetry ingestion.

- Spawn a background thread per serial port reading binary frames.
- Frame format: `[HEADER 4B][PAYLOAD N][CRC 4B]`.
- Parse IMU samples, audio frames, model outputs, log lines.
- Buffer into a ring buffer (SPSC, `crossbeam` or `ringbuf`).
- Periodic snapshot to DuckDB for querying.
- Expose live stream to frontend via Tauri events.

**Snapshot format**:
```
snapshots/<device_id>/<yyyy-mm-dd>/<hh-mm-ss>.parquet
```

Columns: `timestamp_ns`, `stream_id`, `payload_bytes`, `crc_ok`.

### 4.3 Firmware Build & Project Manager
**Goal**: unified build, flash, and monitor loop.

- Wrap `pio run -e nanorp2040connect -j 2` as a background process.
- Stream stdout/stderr to the built-in CLI and to a build log panel.
- Parse `Compiling <file>.cpp.o` and `Linking` lines for progress.
- On success, auto-offer to flash.
- Project structure:
  ```
  project/
    firmware/
      platformio.ini
      src/
      include/
    models/
      gesture.tflite
      audio.tflite
    config/
      device_profiles.json
      threshold_overrides.json
    logs/
  ```
- Detect `platformio.ini` changes → offer to rebuild.

### 4.4 Telemetry Visualizer
**Goal**: fast, beautiful, interactive charts.

- **Real-time line charts**: IMU accel/gyro, RSSI, battery, temperature.
- **Heatmap**: spectrogram of audio or model activation over time.
- **Scatter / 3D**: pose or quaternion visualizations.
- **Table/log view**: structured log lines with filtering.
- **Sync**: all charts share a time cursor; zoom/pan in one zooms all.
- **Export**: CSV, Parquet, PNG snapshot.

Frontend libraries: Plotly for quick interactive charts; Deck.gl or lightweight Canvas for >100k points.

### 4.5 Model Studio
**Goal**: manage TFLite models end-to-end.

- **Library**: upload `.tflite`, view metadata (tensors, ops, size).
- **Host runner**: load model in WASM or Rust (`tflite` crate), run sample input, compare output.
- **Device runner**: send inference request over serial, collect output.
- **Threshold tuner**: sliders for confidence/smoothing; plot precision/recall trade-off from labeled validation set.
- **Quantization preview**: int8 vs. float32 accuracy delta.
- **Conversion pipeline**: integrate `cargo run --bin convert-model` if a Python converter is needed.

### 4.6 Built-in CLI Shell
**Goal**: every feature is accessible by command.

- Rust `clap` subcommands, exposed over a PTY backend.
- Commands mirror IPC commands: `device list`, `flash`, `monitor`, `build`, `model list`, `model run`, `viz start`.
- Piping: `monitor | grep IMU | viz plot`.
- Autocomplete: generate `bash`/`zsh`/`fish`/`powershell` completions.
- History file per project: `.arp-2040/history`.
- Multi-line editing, search (`Ctrl+R`).

### 4.7 Hot Reload & Atomic Reload System

#### 4.7.1 Frontend Hot Reload
- Vite HMR in dev mode.
- In release mode, watch `plugins/` and `themes/` directories.
- On change, download new chunk, swap module, preserve React state via Zustand store serialized to `localStorage`.

#### 4.7.2 Backend Plugin Hot Reload
- Plugins are compiled as `.so`/`.dll`/`.dylib` files loaded via `libloading`.
- **Atomic swap**:
  1. Write new plugin to `<name>.new.<ext>`.
  2. Rename atomically to `<name>.<ext>`.
  3. Unload old plugin, load new plugin.
  4. Call `plugin_init()`; if it fails, roll back to previous plugin file.
- State migration: plugins export `migrate_state(v1: &State) -> State` so settings survive updates.

#### 4.7.3 Config Hot Reload
- `config.yaml` watched via `notify` crate.
- On change, deep-merge with defaults, validate schema, then broadcast `config_changed` event.
- Panels reload their config subscriptions; if a config key is removed, fall back to default.

---

## 5. UI/UX Design Principles

1. **Three-panel layout**:
   - **Left**: device + project tree.
   - **Center**: active view (visualizer, model studio, build log, file editor).
   - **Right**: properties / telemetry stats / CLI output.

2. **Command palette** (`Ctrl+Shift+P`):
   - Fuzzy search all commands, panels, and files.
   - Execute CLI commands, switch views, open settings.

3. **Dark theme default** with high-contrast accent colors for telemetry traces.

4. **Keyboard-first**:
   - `Ctrl+1..9` switch panels.
   - `Ctrl+Enter` runs selected command in CLI.
   - Arrow keys navigate device tree.

5. **Telemetry UX**:
   - Auto-scale axes.
   - Pause/resume stream.
   - Bookmark timestamps.
   - Drag to select region → export or replay.

6. **Model UX**:
   - Drag-and-drop `.tflite` into Model Library.
   - One-click "Run on Device" or "Run on Host".
   - Diff view: overlaid charts of host vs. device outputs.

7. **Feedback**:
   - Non-blocking toasts for background operations.
   - Progress bars with cancel for long operations (flash, build).
   - Status bar: device connected / building / streaming / idle.

---

## 6. Data Flow

```
RP2040 (USB Serial)
    │
    ▼
Serial Port Thread ──► Ring Buffer ──► DuckDB Writer
    │                     │                │
    │                     ▼                ▼
    │               Live Stream ──► Frontend Charts
    ▼
CLI / Device Manager
```

```
Host Model Inference
    │
    ▼
Model Studio ──► Rust TFLite runtime ──► Frontend diff chart
```

---

## 7. CLI Command Reference (Illustrative)

```bash
# Device
device list
device info <id>
device reboot <id>
device bootsel <id>
device flash <id> <firmware.uf2>
device monitor <id> --baud 921600

# Build
build firmware
build firmware --env nanorp2040connect
build status

# Model
model list
model upload <path>
model info <name>
model run-host <name> --input <tensor.bin>
model run-device <name> --input <tensor.bin>
model diff <name> --host-vs-device

# Telemetry
stream start <id>
stream stop <id>
stream export <id> --format parquet --start <t0> --end <t1>

# Config
config get <key>
config set <key> <value>
config reset

# Plugin
plugin list
plugin install <path>
plugin reload <name>

# Help
help [command]
```

---

## 8. Build, Package, and CI

### 8.1 Local Development
```bash
# Install Rust + Node.js + Tauri CLI
cargo install tauri-cli
npm install

# Run dev mode with HMR
npm run tauri dev

# Build release binaries
npm run tauri build
```

### 8.2 CI Matrix (GitHub Actions)
```yaml
jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run tauri build
      - uses: actions/upload-artifact@v4
        with:
          name: app-${{ matrix.os }}
          path: src-tauri/target/release/bundle/**
```

### 8.3 Code Signing & Notarization
- Windows: signtool with EV code signing cert.
- macOS: `xcrun notarytool` + stapling.
- Linux: AppImage + optional `debpkg`/`rpm`.

---

## 9. Testing Strategy

| Layer              | Tool                        | Coverage Target |
|--------------------|-----------------------------|-----------------|
| Rust backend       | `cargo test` + `proptest`   | ≥ 80% unit     |
| IPC commands       | Rust integration tests      | All commands    |
| Frontend           | Vitest + Testing Library    | ≥ 75% component|
| E2E                | Playwright                  | Happy paths +  |
|                    |                             | hot reload      |
| Serial protocol    | Property-based serial tests | Fuzz decode     |

---

## 10. Roadmap (MVP First)

### Phase 1: Foundation (Weeks 1-3)
- Scaffold Tauri 2.x app with React + TypeScript.
- Implement Device Manager (list, detect, flash).
- Implement Serial Manager (read lines, emit events).
- Build device tree panel and serial monitor panel.
- Add built-in CLI shell with basic `device`, `monitor`, `build` commands.

### Phase 2: Telemetry (Weeks 4-6)
- Add binary frame protocol and ring buffer.
- Build real-time chart panel.
- Add DuckDB snapshot writer and time-range query.
- Implement export to Parquet/CSV.

### Phase 3: Firmware & Build (Weeks 7-8)
- Wrap `pio run` with progress parsing.
- Auto-flash on successful build.
- Build log panel with syntax highlighting.

### Phase 4: Model Studio (Weeks 9-11)
- Model library view.
- Host-side inference runner.
- Device-side inference runner.
- Diff visualization.

### Phase 5: Polish & Hot Reload (Weeks 12-13)
- Command palette.
- Keyboard shortcuts.
- Frontend plugin system (loadable chart widgets).
- Backend plugin hot swap.
- Atomic config reload.
- Theme system.

### Phase 6: Packaging & Distribution (Week 14)
- CI matrix builds.
- Code signing.
- Auto-update mechanism (Squirrel/Tauri updater).
- Documentation and onboarding tour.

---

## 11. Scalability & 100-Year Survival

- **Plugin architecture**: every panel, visualization, CLI command, and device driver is a plugin with a stable ABI.
- **Config-driven UI**: layout, themes, and keybindings live in `config.yaml`; users can reshape the app without source changes.
- **Protocol versioning**: telemetry frames include a version byte; old/new app versions negotiate format.
- **Backward compatibility**: DuckDB schema migrations are automatic; old snapshots remain queryable.
- **Modular release train**: core app ships quarterly; plugins ship independently via a registry (`arp-2040 plugin install <name>`).
- **Telemetry format**: adopt a self-describing schema (FlatBuffers or Cap'n Proto) so new data types can be added without breaking old parsers.

---

## 12. Security & Permissions

- Tauri capabilities file gates IPC commands.
- Serial port access requires explicit permission prompt on first use (Windows/macOS).
- Firmware flashing requires elevated confirmation.
- Auto-update signatures verified before install.

---

## 9. MCP Server Integration and Hermes Agent Testing

### 9.1 Implementation Status
The MCP server is implemented in `tools/mcp-server/` as a Rust binary with:
- stdio transport
- TCP transport (`--transport tcp --tcp-port 8765 --tcp-bind 127.0.0.1`)
- 6 seed tools: `device_list`, `device_flash`, `telemetry_start`, `telemetry_stop`, `firmware_build`, `gui_open_panel`
- Automated tests in `tests/mcp_tests.rs`

### 9.2 Verified Test Results
```
running 4 tests
test initialize_returns_server_info ... ok
test list_tools_contains_device_list ... ok
test device_list_returns_text_content ... ok
test unknown_tool_returns_error ... ok
test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured
```

### 9.3 Hermes Agent Integration
Hermes Agent connects to the MCP server via one of:
- stdio: spawn `tools/mcp-server/target/debug/arp-2040-mcp.exe`
- TCP: connect to `127.0.0.1:8765` after starting server with `--transport tcp`

Example JSON-RPC for automated testing:
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"hermes-test","version":"0.1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"tool_calls":[{"id":"t1","name":"device_list","arguments":{}}]}}
{"jsonrpc":"2.0","id":4,"method":"shutdown","params":{}}
```

### 9.4 Next Integration Steps
1. Start MCP server in TCP mode: `cargo run --bin arp-2040-mcp -- --transport tcp --tcp-port 8765`
2. Configure Hermes Agent MCP client to connect to `127.0.0.1:8765`
3. Run automated tests from Hermes Agent using the MCP tools
4. Replace stub implementations with real `serialport` enumeration and PlatformIO build calls

---

## 10. Success Criteria

1. A new user can plug in the RP2040, click **Flash**, and see serial output in under 60 seconds.
2. Real-time telemetry renders at 60 fps for 3 concurrent IMU streams.
3. The CLI exposes 100% of GUI functionality.
4. A plugin developer can add a new visualization type without modifying core app code.
5. The app can run for weeks streaming telemetry without memory leaks.
6. Hot reload preserves active device connections and streaming state.

---

## 11. Immediate Next Steps

1. Initialize Tauri 2.x project scaffold.
2. Implement `DeviceManager` Rust module with serial enumeration.
3. Build the three-panel shell (device tree, center view, CLI).
4. Wire up a "Hello World" Tauri command from the CLI panel.
5. Add the serial monitor as the first center view.
6. Start MCP server in TCP mode: `cargo run --bin arp-2040-mcp -- --transport tcp --tcp-port 8765`
7. Configure Hermes Agent MCP client to connect to `127.0.0.1:8765`
8. Run automated tests from Hermes Agent using the MCP tools
9. Replace stub implementations with real `serialport` enumeration and PlatformIO build calls

If you want, I can scaffold the Tauri project structure and implement the `DeviceManager` + CLI shell as the first working prototype.
