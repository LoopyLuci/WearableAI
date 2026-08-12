# Agentic Arduino MCP Toolkit

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0-green)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/license-GPL--3.0-orange)](LICENSE)

**35 MCP tools. 14 resources. 1 toolkit. 100-year modularity.**

The Agentic Arduino MCP Toolkit gives Hermes Agent (or any MCP client) complete control over Arduino hardware — from auto-detection and compilation to TinyML training, mesh networking, atomic OTA, self-modifying code, and full FreeRTOS introspection. Built for the **Arduino Nano RP2040 Connect**, but architected to outlive any single board.

## Why this exists

Embedded development is fragmented: PlatformIO, Arduino CLI, platform-specific SDKs, serial monitors, debuggers, TinyML pipelines, mesh protocols — each with its own CLI and mental model. This toolkit unifies all of them behind a single MCP interface so an AI agent can:

- **Generate** production-ready code from natural language
- **Compile and flash** with atomic rollback
- **Debug** with memory reports, task lists, crash journals, and live variable watching
- **Train** TinyML models and push them to the device
- **Build** self-modifying control graphs and bytecode scripts
- **Mesh** BLE and Wi-Fi peers with federated learning
- **Secure** everything with ATECC608A signing and mbedTLS

## Quick start

```bash
# Install
pip install arduino-mcp-toolkit

# Configure Hermes to use the MCP server
# Add to your Hermes config:
# mcp:
#   servers:
#     arduino:
#       command: arduino-mcp

# Test
arduino-mcp detect
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hermes Agent (MCP Client)                     │
│                     tool_call("arduino.*")                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ stdio MCP
┌────────────────────────────▼────────────────────────────────────┐
│              arduino-mcp-toolkit MCP Server                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ HardwareMgr │ │ CompilerMgr │ │ SerialMgr   │               │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘               │
│         │                │                │                      │
│  ┌──────▼─────────────────▼────────────────▼──────┐             │
│  │             35 MCP Tool Handlers                 │             │
│  │  detect | compile | flash | generate | mesh |   │             │
│  │  train_model | ota | debug | agent | security    │             │
│  └──────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐    ┌───▼────┐   ┌────▼────┐
         │ Hardware│    │Platform│   │  Host   │
         │ (USB)   │    │   IO   │   │  Tools  │
         └─────────┘    └────────┘   └─────────┘
```

## Tool categories

| Category | Tools | Description |
|---|---|---|
| **Hardware** | `detect`, `board_info`, `pin_map` | Board detection, detailed info, pin mappings |
| **Compile** | `compile`, `flash`, `build_and_flash` | Compile sketches, flash binaries, atomic build+flash with rollback |
| **Serial** | `serial_monitor`, `serial_write` | Read/write serial data, real-time monitoring |
| **Generator** | `generate_sketch`, `generate_hal`, `generate_project` | Generate code from natural language |
| **Testing** | `run_tests`, `validate_sketch` | Upload/run tests, static analysis |
| **Knowledge** | `search_libraries`, `library_info`, `learn` | Library search, API docs, tutorials |
| **ML** | `train_model`, `convert_model`, `build_control_graph`, `push_script` | TinyML training, model conversion, control graphs, bytecode |
| **Mesh** | `mesh_status`, `mesh_add_peer`, `federated_update` | BLE/Wi-Fi hybrid mesh, federated learning |
| **OTA** | `ota_update`, `rollback` | Atomic OTA with CRC verification |
| **Debug** | `memory_report`, `task_list`, `crash_journal`, `watch` | Memory, tasks, crash dumps, live variable watching |
| **Power** | `power_profile`, `battery_status` | Power management, battery monitoring |
| **Security** | `crypto_status`, `sign_firmware` | ATECC608A status, firmware signing |
| **Agentic** | `agent_status`, `agent_restart`, `self_test` | Agent lifecycle, autonomous self-repair |

## Resources

| URI | Description |
|---|---|
| `arduino://boards/available` | Supported board catalog |
| `arduino://boards/detected` | Currently connected boards |
| `arduino://docs/*` | Setup guides, HAL spec, protocol spec, blueprint |
| `arduino://examples/*` | Ready-to-run example sketches |
| `arduino://tools/*` | Host-side tool scripts |
| `arduino://schemas/*` | JSON schemas for graph and model formats |

## Design principles

1. **100-year modularity** — HAL interfaces are frozen contracts; hardware changes require only new implementations
2. **Zero single points of failure** — Every operation has rollback; every connection has timeout; every task has watchdog
3. **Agentic by default** — Tools are designed for AI agents, not humans: structured inputs/outputs, idempotent operations, clear error codes
4. **Testability** — Every layer has a host-side mock; 90% of development happens without hardware
5. **Security** — ATECC608A for identity, mbedTLS for transport, signed OTA, secure boot

## Integration with Hermes Agent

```yaml
# hermes-config.yaml
mcp:
  servers:
    arduino:
      command: arduino-mcp
      args: []
      env:
        ARDUINO_MCP_CONFIG: /path/to/arduino-mcp-config.yaml
```

Once configured, Hermes can call any Arduino tool as if it were a native function:
```
Hermes: "Build and flash the latest model to the connected Arduino"
→ tool_call("arduino.build_and_flash", {"source_path": "...", "watchdog_timeout_s": 30})
```

## Requirements

- Python 3.9+
- PlatformIO CLI (`pip install platformio`)
- pyserial, pyyaml, cryptography, numpy, rich, click

## License

GPL-3.0 with explicit patent grant. See LICENSE.

---

**Status:** Production foundation. 35 tools, 14 resources, full test suite. Ready for Phase 1 implementation.
