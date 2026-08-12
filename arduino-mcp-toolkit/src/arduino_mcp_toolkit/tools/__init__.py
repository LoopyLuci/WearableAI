"""
arduino_mcp_toolkit.tools — All MCP tool definitions and router
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable
from mcp.types import Tool

logger = logging.getLogger("arduino-mcp")

# Tool handler registry
TOOL_HANDLERS: dict[str, Callable[[dict], Awaitable[Any]]] = {}

def tool(name: str, description: str, input_schema: dict):
    """Decorator to register a tool handler."""
    def decorator(fn: Callable[[dict], Awaitable[Any]]):
        TOOL_HANDLERS[name] = fn
        fn._tool_meta = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }
        return fn
    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# Tool definitions — each returns a Tool spec
# ──────────────────────────────────────────────────────────────────────────────

TOOL_SPECS = [
    # Hardware detection & info
    {
        "name": "arduino.detect",
        "description": "Auto-detect connected Arduino boards. Returns board type, port, firmware version, and capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "arduino.board_info",
        "description": "Get detailed hardware info about a connected board: MCU, flash, SRAM, pins, sensors, radio.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string", "description": "Serial port (e.g., COM3, /dev/ttyACM0). Auto-detected if omitted."},
                "timeout_ms": {"type": "integer", "description": "Read timeout in ms", "default": 5000},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.pin_map",
        "description": "Get the complete pin mapping for a board: GPIO, ADC, PWM, I2C, SPI, UART pins.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "board": {"type": "string", "description": "Board type (e.g., nano_rp2040_connect). Auto-detected if omitted."},
            },
            "required": [],
        },
    },
    # Compile & flash
    {
        "name": "arduino.compile",
        "description": "Compile an Arduino sketch (.ino) or PlatformIO project. Returns binary path, size, flash usage, and warnings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "Path to .ino file or project directory"},
                "fqbn": {"type": "string", "description": "Fully Qualified Board Name (e.g., arduino:avr:uno, rp2040:rp2040:nano_rp2040_connect). Auto-detected if omitted."},
                "verbose": {"type": "boolean", "description": "Verbose compiler output", "default": False},
                "optimize_for": {"type": "string", "description": "Optimization target: size, speed, debug", "default": "size"},
            },
            "required": ["source_path"],
        },
    },
    {
        "name": "arduino.flash",
        "description": "Flash a compiled binary to an Arduino. Returns verification status and boot confirmation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "binary_path": {"type": "string", "description": "Path to .bin/.hex/.elf file. Auto-detected if omitted."},
                "port": {"type": "string", "description": "Serial port. Auto-detected if omitted."},
                "fqbn": {"type": "string", "description": "Board type. Auto-detected if omitted."},
                "reset_method": {"type": "string", "enum": ["auto", "dtr", "manual", "no_reset"], "description": "Board reset method for upload", "default": "auto"},
                "verify": {"type": "boolean", "description": "Verify flash after upload", "default": True},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.build_and_flash",
        "description": "Compile AND flash in one atomic operation. Rolls back to previous firmware if new firmware crashes within 30 seconds.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "Path to .ino or project dir"},
                "fqbn": {"type": "string", "description": "Board FQBN. Auto-detected if omitted."},
                "port": {"type": "string", "description": "Serial port. Auto-detected if omitted."},
                "watchdog_timeout_s": {"type": "integer", "description": "Rollback if no heartbeat within this many seconds", "default": 30},
            },
            "required": ["source_path"],
        },
    },
    # Serial & monitoring
    {
        "name": "arduino.serial_command",
        "description": "Send a single-line command to the Arduino and capture the response. Uses a hardened path with retries and clearer line framing than the monitor tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string", "description": "Serial port"},
                "command": {"type": "string", "description": "Command text, without trailing newline"},
                "baud": {"type": "integer", "description": "Baud rate", "default": 921600},
                "timeout_s": {"type": "number", "description": "Response timeout in seconds", "default": 4.0},
                "max_retries": {"type": "integer", "description": "Retries on timeout/busy-port", "default": 2},
                "append_newline": {"type": "boolean", "description": "Append LF to command", "default": True},
            },
            "required": ["port", "command"],
        },
    },
    {
        "name": "arduino.serial_monitor",
        "description": "Open a serial monitor to read/write data to/from the Arduino. Supports real-time streaming.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string", "description": "Serial port"},
                "baud": {"type": "integer", "description": "Baud rate", "default": 115200},
                "timeout_s": {"type": "integer", "description": "Monitor duration in seconds. 0 = infinite", "default": 0},
                "filter": {"type": "string", "description": "Regex filter for output lines"},
                "send": {"type": "string", "description": "Initial string to send after connect"},
            },
            "required": ["port"],
        },
    },
    {
        "name": "arduino.serial_write",
        "description": "Write data to the Arduino serial port.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "data": {"type": "string", "description": "Data to send"},
                "append_newline": {"type": "boolean", "default": True},
            },
            "required": ["port", "data"],
        },
    },
    # Code generation
    {
        "name": "arduino.generate_sketch",
        "description": "Generate a complete, production-ready Arduino sketch from a natural language description. The generated code includes error handling, power management, and documentation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Natural language description of what the sketch should do"},
                "board": {"type": "string", "description": "Target board. Auto-detected if omitted."},
                "features": {"type": "array", "items": {"type": "string"}, "description": "Feature tags: wifi, ble, tinyml, imu, mic, oled, crypto, power_mgmt, mesh"},
                "output_path": {"type": "string", "description": "Where to save the .ino file"},
                "include_tests": {"type": "boolean", "description": "Include unit test harness in generated sketch", "default": True},
            },
            "required": ["description"],
        },
    },
    {
        "name": "arduino.generate_hal",
        "description": "Generate a complete Hardware Abstraction Layer (HAL) for a specific board. Includes ISensor, IRadio, ICrypto, IStorage, IPower, IAudio interfaces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "board": {"type": "string", "description": "Target board type"},
                "output_dir": {"type": "string", "description": "Output directory for HAL headers"},
            },
            "required": ["board"],
        },
    },
    {
        "name": "arduino.generate_project",
        "description": "Generate a complete PlatformIO project structure: src/, include/, lib/, test/, platformio.ini, with CMakeLists.txt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "board": {"type": "string", "description": "Target board FQBN"},
                "output_dir": {"type": "string", "description": "Where to create the project"},
                "framework": {"type": "string", "enum": ["arduino", "platformio", "cmake"], "default": "platformio"},
                "features": {"type": "array", "items": {"type": "string"}, "description": "Feature tags to enable"},
            },
            "required": ["name", "board"],
        },
    },
    # Testing & validation
    {
        "name": "arduino.run_tests",
        "description": "Upload and run unit tests on the connected Arduino. Returns test results, pass/fail counts, and serial output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "fqbn": {"type": "string"},
                "test_filter": {"type": "string", "description": "Run only tests matching this pattern"},
                "timeout_s": {"type": "integer", "description": "Max test duration", "default": 120},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.validate_sketch",
        "description": "Static analysis of an Arduino sketch: check for common bugs, verify HAL interface usage, check memory constraints, detect blocking code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "Path to .ino file or project dir"},
                "checks": {"type": "array", "items": {"type": "string"}, "description": "Specific checks: memory, blocking, hal_usage, security, power"},
                "strict": {"type": "boolean", "description": "Treat warnings as errors", "default": False},
            },
            "required": ["source_path"],
        },
    },
    # Learning & knowledge
    {
        "name": "arduino.search_libraries",
        "description": "Search the Arduino Library Manager and PlatformIO Registry for libraries matching a query. Returns metadata, compatibility, and usage examples.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g., 'imu', 'wifi', 'tinyml')"},
                "registry": {"type": "string", "enum": ["arduino", "platformio", "both"], "default": "both"},
                "compatible_with": {"type": "string", "description": "Filter by board compatibility"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "arduino.library_info",
        "description": "Get detailed info about an Arduino library: version, dependencies, examples, API reference, license.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name (e.g., 'Adafruit_LSM6DSOX')"},
            },
            "required": ["library_name"],
        },
    },
    {
        "name": "arduino.learn",
        "description": "Query the Arduino knowledge base: API docs, pinouts, tutorials, example code, troubleshooting guides. Powered by embedded documentation and web search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query"},
                "board": {"type": "string", "description": "Board-specific context"},
                "depth": {"type": "string", "enum": ["quick", "standard", "deep"], "default": "standard"},
            },
            "required": ["query"],
        },
    },
    # Advanced: TinyML, control graph, scripting
    {
        "name": "arduino.train_model",
        "description": "Train a TinyML model for on-device inference. Supports KWS, IMU gesture, audio scene classification. Returns quantized TFLite Micro model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "enum": ["kws", "imu_gesture", "audio_scene", "custom"], "description": "Model task type"},
                "dataset_path": {"type": "string", "description": "Path to training data (CSV, WAV, or numpy)"},
                "output_path": {"type": "string", "description": "Where to save the .tflite model"},
                "epochs": {"type": "integer", "description": "Training epochs", "default": 50},
                "quantize": {"type": "boolean", "description": "Quantize to int8", "default": True},
                "target_sram_kb": {"type": "integer", "description": "Max SRAM budget in KB", "default": 64},
            },
            "required": ["task", "dataset_path"],
        },
    },
    {
        "name": "arduino.convert_model",
        "description": "Convert a PyTorch/ONNX model to TFLite Micro format for Arduino. Handles quantization, pruning, and optimization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to .pt/.onnx model"},
                "output_path": {"type": "string", "description": "Output .tflite path"},
                "input_shape": {"type": "array", "items": {"type": "integer"}, "description": "Model input shape (e.g., [1, 98, 40, 1])"},
                "quantize": {"type": "boolean", "default": True},
                "representative_dataset": {"type": "string", "description": "Path to representative data for quantization calibration"},
            },
            "required": ["input_path", "output_path", "input_shape"],
        },
    },
    {
        "name": "arduino.build_control_graph",
        "description": "Build a control graph (DAG of processing nodes) for the Arduino bytecode interpreter. Enables self-modifying agent pipelines.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "graph_definition": {"type": "string", "description": "JSON or YAML graph definition, or natural language description"},
                "output_path": {"type": "string", "description": "Output binary path"},
                "sign": {"type": "boolean", "description": "Sign with ATECC608A if available", "default": False},
            },
            "required": ["graph_definition"],
        },
    },
    {
        "name": "arduino.push_script",
        "description": "Push a bytecode script to the Arduino. The script runs on the device's bytecode interpreter for custom logic without recompilation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "script_path": {"type": "string", "description": "Path to .arb script (assembled bytecode)"},
                "port": {"type": "string"},
                "node_id": {"type": "integer", "description": "Target control graph node ID"},
            },
            "required": ["script_path"],
        },
    },
    # Mesh, federation, sync
    {
        "name": "arduino.mesh_status",
        "description": "Get the current mesh network status: peer count, hop count, link quality, routing table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.mesh_add_peer",
        "description": "Add a peer to the BLE/Wi-Fi hybrid mesh network.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "peer_address": {"type": "string", "description": "Peer MAC address or hostname"},
                "transport": {"type": "string", "enum": ["ble", "wifi", "auto"], "default": "auto"},
            },
            "required": ["peer_address"],
        },
    },
    {
        "name": "arduino.federated_update",
        "description": "Initiate a federated learning round: collect model deltas from mesh peers, aggregate, and push improved model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "model_id": {"type": "integer", "description": "Model to update"},
                "round_id": {"type": "string", "description": "Unique round identifier"},
                "min_peers": {"type": "integer", "description": "Minimum peers to wait for", "default": 2},
            },
            "required": ["model_id", "round_id"],
        },
    },
    # OTA & lifecycle
    {
        "name": "arduino.ota_update",
        "description": "Perform an atomic OTA firmware update. Downloads binary, writes to staging partition, verifies CRC, promotes, and reboots.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "binary_url": {"type": "string", "description": "URL to download firmware binary from"},
                "binary_path": {"type": "string", "description": "Or path to local binary file"},
                "staging_partition": {"type": "integer", "description": "Staging partition offset in flash", "default": 0x00100000},
                "verify_timeout_s": {"type": "integer", "description": "Max time to wait for device to come back", "default": 60},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.rollback",
        "description": "Rollback to the previous firmware version using the rollback journal.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "steps": {"type": "integer", "description": "Number of versions to roll back", "default": 1},
            },
            "required": [],
        },
    },
    # Debug & introspection
    {
        "name": "arduino.memory_report",
        "description": "Get a detailed memory report: SRAM usage, stack watermarks, heap fragmentation, flash usage, TFLite arena size.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "detailed": {"type": "boolean", "description": "Include per-task breakdown", "default": True},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.task_list",
        "description": "List all FreeRTOS tasks: name, ID, priority, core, stack usage, state, runtime.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.crash_journal",
        "description": "Read the crash journal from the device: exception frames, stack traces, fault registers, timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "clear_after_read": {"type": "boolean", "default": False},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.watch",
        "description": "Watch a variable or expression in real-time on the Arduino. Uses GDB stub or custom watchpoint protocol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "expression": {"type": "string", "description": "C expression to watch (e.g., 'battery_voltage', 'imu_accel[0]')"},
                "interval_ms": {"type": "integer", "description": "Polling interval", "default": 100},
                "duration_s": {"type": "integer", "description": "How long to watch", "default": 10},
            },
            "required": ["expression"],
        },
    },
    # Power & battery
    {
        "name": "arduino.power_profile",
        "description": "Get or set the power profile: active, idle, dormant, sleep. Measures and reports current draw.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "profile": {"type": "string", "enum": ["active", "idle", "dormant", "sleep", "hibernate"], "description": "Target power profile"},
                "measure": {"type": "boolean", "description": "Return measured current draw", "default": True},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.battery_status",
        "description": "Get battery status: voltage, current, percentage, estimated time remaining, charge cycle count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
            },
            "required": [],
        },
    },
    # Security
    {
        "name": "arduino.crypto_status",
        "description": "Get crypto subsystem status: ATECC608A presence, public key fingerprint, secure boot enabled, firmware signature.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.sign_firmware",
        "description": "Sign a firmware binary with the ATECC608A secure element. Required for secure boot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "binary_path": {"type": "string", "description": "Path to firmware binary"},
                "output_path": {"type": "string", "description": "Signed output path"},
                "key_slot": {"type": "integer", "description": "ATECC608A key slot (0-15)", "default": 0},
            },
            "required": ["binary_path", "output_path"],
        },
    },
    # Agentic features
    {
        "name": "arduino.agent_status",
        "description": "Get the status of all agents running on the Arduino: SensorAgent, InferenceAgent, ConnectivityAgent, PowerAgent, LearningAgent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "detailed": {"type": "boolean", "default": True},
            },
            "required": [],
        },
    },
    {
        "name": "arduino.agent_restart",
        "description": "Restart a specific agent on the Arduino with automatic rollback if it crashes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "agent_id": {"type": "string", "description": "Agent ID (sensor, inference, connectivity, power, learning)"},
                "max_restarts": {"type": "integer", "description": "Max restart attempts before disabling", "default": 5},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "arduino.self_test",
        "description": "Run a comprehensive self-test on the Arduino: sensor calibration, radio test, memory check, crypto test, power test.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "full": {"type": "boolean", "description": "Run all tests including destructive ones", "default": False},
                "report_path": {"type": "string", "description": "Save report to this path"},
            },
            "required": [],
        },
    },
]


def register_all_tools() -> list[Tool]:
    """Return all tool specifications and register handlers."""
    from arduino_mcp_toolkit.tools.hardware_tools import detect, board_info, pin_map
    from arduino_mcp_toolkit.tools.compiler_tools import compile, flash, build_and_flash
    from arduino_mcp_toolkit.tools.serial_command_tools import serial_command
    from arduino_mcp_toolkit.tools.serial_tools import serial_monitor, serial_write
    from arduino_mcp_toolkit.tools.generator_tools import generate_sketch, generate_hal, generate_project
    from arduino_mcp_toolkit.tools.testing_tools import run_tests, validate_sketch
    from arduino_mcp_toolkit.tools.knowledge_tools import search_libraries, library_info, learn
    from arduino_mcp_toolkit.tools.ml_tools import train_model, convert_model, build_control_graph, push_script
    from arduino_mcp_toolkit.tools.mesh_tools import mesh_status, mesh_add_peer, federated_update
    from arduino_mcp_toolkit.tools.ota_tools import ota_update, rollback
    from arduino_mcp_toolkit.tools.debug_tools import memory_report, task_list, crash_journal, watch
    from arduino_mcp_toolkit.tools.power_tools import power_profile, battery_status
    from arduino_mcp_toolkit.tools.security_tools import crypto_status, sign_firmware
    from arduino_mcp_toolkit.tools.agentic_tools import agent_status, agent_restart, self_test

    # Register all handlers
    handlers = {
        "arduino.detect": detect,
        "arduino.board_info": board_info,
        "arduino.pin_map": pin_map,
        "arduino.compile": compile,
        "arduino.flash": flash,
        "arduino.build_and_flash": build_and_flash,
        "arduino.serial_command": serial_command,
        "arduino.serial_monitor": serial_monitor,
        "arduino.serial_write": serial_write,
        "arduino.generate_sketch": generate_sketch,
        "arduino.generate_hal": generate_hal,
        "arduino.generate_project": generate_project,
        "arduino.run_tests": run_tests,
        "arduino.validate_sketch": validate_sketch,
        "arduino.search_libraries": search_libraries,
        "arduino.library_info": library_info,
        "arduino.learn": learn,
        "arduino.train_model": train_model,
        "arduino.convert_model": convert_model,
        "arduino.build_control_graph": build_control_graph,
        "arduino.push_script": push_script,
        "arduino.mesh_status": mesh_status,
        "arduino.mesh_add_peer": mesh_add_peer,
        "arduino.federated_update": federated_update,
        "arduino.ota_update": ota_update,
        "arduino.rollback": rollback,
        "arduino.memory_report": memory_report,
        "arduino.task_list": task_list,
        "arduino.crash_journal": crash_journal,
        "arduino.watch": watch,
        "arduino.power_profile": power_profile,
        "arduino.battery_status": battery_status,
        "arduino.crypto_status": crypto_status,
        "arduino.sign_firmware": sign_firmware,
        "arduino.agent_status": agent_status,
        "arduino.agent_restart": agent_restart,
        "arduino.self_test": self_test,
    }

    for name, fn in handlers.items():
        TOOL_HANDLERS[name] = fn

    return [Tool(**spec) for spec in TOOL_SPECS]
