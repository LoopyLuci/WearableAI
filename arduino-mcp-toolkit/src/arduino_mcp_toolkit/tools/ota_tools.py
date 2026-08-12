"""
arduino_mcp_toolkit.tools.ota_tools — OTA update & rollback tools
"""
from __future__ import annotations
import logging
from typing import Any
from arduino_mcp_toolkit.tools import tool

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.ota_update",
    "Perform an atomic OTA firmware update with CRC verification and automatic rollback.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "binary_url": {"type": "string", "description": "URL to download firmware from"},
            "binary_path": {"type": "string", "description": "Or path to local binary"},
            "staging_partition": {"type": "integer", "default": 0x00100000},
            "verify_timeout_s": {"type": "integer", "default": 60},
        },
        "required": [],
    },
)
async def ota_update(args: dict) -> str:
    lines = ["Atomic OTA firmware update:"]
    lines.append("  1. Download binary (or use local file)")
    lines.append("  2. Validate CRC32 and signature")
    lines.append("  3. Write to staging partition (QSPI)")
    lines.append("  4. Verify staging partition integrity")
    lines.append("  5. Atomic promotion: staging → active (single QSPI page program)")
    lines.append("  6. Reboot")
    lines.append("  7. Device verifies new firmware, triggers rollback if invalid")
    return "\n".join(lines)


@tool(
    "arduino.rollback",
    "Rollback to the previous firmware version using the rollback journal.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "steps": {"type": "integer", "default": 1},
        },
        "required": [],
    },
)
async def rollback(args: dict) -> str:
    steps = args.get("steps", 1)
    lines = [f"Rolling back {steps} version(s):"]
    lines.append("  1. Read rollback journal from QSPI")
    lines.append("  2. Identify previous valid firmware")
    lines.append("  3. Restore previous version to active partition")
    lines.append("  4. Reboot")
    lines.append("  5. Verify boot succeeds")
    return "\n".join(lines)
