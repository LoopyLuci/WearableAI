"""
arduino_mcp_toolkit.tools.serial_command — hardened single-shot serial command tool
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from arduino_mcp_toolkit.serial import SerialManager
from arduino_mcp_toolkit.tools import tool

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.serial_command",
    "Send a single-line command to the Arduino and capture the response. "
    "Uses a hardened path with retries and clearer line framing than the monitor tool.",
    {
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
)
async def serial_command(args: dict) -> str:
    port = args["port"]
    command = args["command"]
    baud = int(args.get("baud", 921600))
    timeout_s = float(args.get("timeout_s", 4.0))
    max_retries = int(args.get("max_retries", 2))
    append_newline = bool(args.get("append_newline", True))

    serial_mgr = SerialManager.get_instance()
    opened_here = False
    last_err = ""

    for attempt in range(max_retries + 1):
        try:
            if port not in serial_mgr._ports or not serial_mgr._ports[port].is_open:
                opened_here = True
                ok = await serial_mgr.open(port, baud=baud, timeout=1.0)
                if not ok:
                    last_err = f"open_failed:{port}"
                    if attempt < max_retries:
                        await asyncio.sleep(0.5)
                        continue
                    return f"ERROR: could not open {port}\n{last_err}"

            response = await asyncio.wait_for(
                serial_mgr.send_command(port, command, timeout=timeout_s),
                timeout=timeout_s + 1.0,
            )
            response = (response or "").strip()
            if not response:
                last_err = "empty_response"
                if attempt < max_retries:
                    await asyncio.sleep(0.3)
                    continue
                return f"ERROR: no response from {port} for `{command}`"
            return f"cmd: {command}\nport: {port}\nresponse: {response}"
        except asyncio.TimeoutError:
            last_err = "timeout"
            if attempt < max_retries:
                await asyncio.sleep(0.4)
                continue
            return f"ERROR: timeout waiting for response on {port} for `{command}`"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            if attempt < max_retries:
                await asyncio.sleep(0.4)
                continue
            return f"ERROR: {last_err}\ncommand={command}\nport={port}"
        finally:
            if opened_here:
                try:
                    await serial_mgr.close(port)
                except Exception:
                    pass
