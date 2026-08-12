"""
arduino_mcp_toolkit.tools.serial_tools — Serial monitor & write tools
"""
from __future__ import annotations
import asyncio
import logging
import re
from typing import Any
from arduino_mcp_toolkit.serial import SerialManager
from arduino_mcp_toolkit.tools import tool

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.serial_monitor",
    "Open a serial monitor to read/write data to/from the Arduino.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "baud": {"type": "integer", "default": 115200},
            "timeout_s": {"type": "integer", "default": 0},
            "filter": {"type": "string", "description": "Regex filter for output lines"},
            "send": {"type": "string", "description": "Initial string to send"},
        },
        "required": ["port"],
    },
)
async def serial_monitor(args: dict) -> str:
    serial_mgr = SerialManager.get_instance()
    port = args["port"]
    baud = args.get("baud", 115200)
    timeout_s = args.get("timeout_s", 0)
    filter_re = args.get("filter")
    send_data = args.get("send")

    lines = [f"Opening serial monitor on {port} @ {baud} baud"]

    if send_data:
        lines.append(f"> {send_data}")
        await serial_mgr.write(port, send_data)

    if timeout_s == 0:
        lines.append("Monitoring indefinitely (no timeout). Press Ctrl+C to stop.")
        return "\n".join(lines)

    deadline = asyncio.get_event_loop().time() + timeout_s
    captured = []
    pattern = re.compile(filter_re) if filter_re else None

    while asyncio.get_event_loop().time() < deadline:
        try:
            line = await asyncio.wait_for(serial_mgr.read_line(port), timeout=1.0)
            if line:
                if pattern and not pattern.search(line):
                    continue
                captured.append(line)
                if len(captured) > 100:
                    captured.pop(0)
        except asyncio.TimeoutError:
            continue

    lines.append(f"Captured {len(captured)} lines:")
    lines.extend(captured[-50:])
    return "\n".join(lines)


@tool(
    "arduino.serial_write",
    "Write data to the Arduino serial port.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "data": {"type": "string"},
            "append_newline": {"type": "boolean", "default": True},
        },
        "required": ["port", "data"],
    },
)
async def serial_write(args: dict) -> str:
    serial_mgr = SerialManager.get_instance()
    port = args["port"]
    data = args["data"]
    if args.get("append_newline", True):
        data += "\n"
    await serial_mgr.write(port, data)
    return f"Sent {len(data)} bytes to {port}"
