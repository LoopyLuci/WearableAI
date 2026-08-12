"""
arduino_mcp_toolkit.tools.hardware_tools — Board detection & info tools
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any
from arduino_mcp_toolkit.hardware import HardwareManager
from arduino_mcp_toolkit.tools import tool, TOOL_HANDLERS

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.detect",
    "Auto-detect connected Arduino boards. Returns board type, port, firmware version, and capabilities.",
    {"type": "object", "properties": {}, "required": []},
)
async def detect(args: dict) -> str:
    hw = HardwareManager.get_instance()
    boards = await hw.detect_boards()
    if not boards:
        return "No Arduino boards detected. Check USB connection and drivers."

    lines = [f"Detected {len(boards)} board(s):"]
    for b in boards:
        lines.append(f"  - Port: {b.get('port','?')}")
        lines.append(f"    Board: {b.get('board_type','?')}")
        lines.append(f"    MCU: {b.get('mcu','?')}")
        lines.append(f"    FQBN: {b.get('fqbn','?')}")
        lines.append(f"    VID:PID: {b.get('vid',0):04X}:{b.get('pid',0):04X}")
    return "\n".join(lines)


@tool(
    "arduino.board_info",
    "Get detailed hardware info about a connected board: MCU, flash, SRAM, pins, sensors, radio.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string", "description": "Serial port"},
            "timeout_ms": {"type": "integer", "default": 5000},
        },
        "required": [],
    },
)
async def board_info(args: dict) -> str:
    hw = HardwareManager.get_instance()
    port = args.get("port")
    timeout_ms = args.get("timeout_ms", 5000)
    info = await hw.get_board_info(port, timeout_ms=timeout_ms)
    lines = [
        f"Board: {info.get('board_type', 'Unknown')}",
        f"MCU: {info.get('mcu', 'Unknown')}",
        f"Clock: {info.get('clock_mhz', '?')} MHz",
        f"Flash: {info.get('flash_kb', '?')} KB",
        f"SRAM: {info.get('sram_kb', '?')} KB",
        f"Pins: {info.get('digital_pins', '?')} digital, {info.get('analog_pins', '?')} analog",
        f"Sensors: {', '.join(info.get('sensors', [])) or 'None detected'}",
        f"Radio: {', '.join(info.get('radio', [])) or 'None'}",
        f"Crypto: {', '.join(info.get('crypto', [])) or 'None'}",
        f"Firmware: {info.get('firmware_version', 'Unknown')}",
    ]
    return "\n".join(lines)


@tool(
    "arduino.pin_map",
    "Get the complete pin mapping for a board: GPIO, ADC, PWM, I2C, SPI, UART pins.",
    {
        "type": "object",
        "properties": {
            "board": {"type": "string", "description": "Board type (e.g., nano_rp2040_connect)"},
        },
        "required": [],
    },
)
async def pin_map(args: dict) -> str:
    hw = HardwareManager.get_instance()
    board = args.get("board")
    pins = hw.get_pin_map(board)
    lines = [f"Pin map for {board or 'auto-detected board'}:"]
    for p in pins:
        lines.append(f"  {p['name']:12s} | {p['type']:10s} | {p['description']}")
    return "\n".join(lines)
