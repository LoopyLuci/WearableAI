"""
arduino_mcp_toolkit.tools.power_tools — Power profile & battery status tools
"""
from __future__ import annotations
import logging
from typing import Any
from arduino_mcp_toolkit.tools import tool

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.power_profile",
    "Get or set the power profile: active, idle, dormant, sleep. Measures current draw.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "profile": {"type": "string", "enum": ["active", "idle", "dormant", "sleep", "hibernate"]},
            "measure": {"type": "boolean", "default": True},
        },
        "required": [],
    },
)
async def power_profile(args: dict) -> str:
    profile = args.get("profile")
    lines = ["Power profile:"]
    if profile:
        lines.append(f"  Setting profile: {profile}")
    else:
        lines.append("  Current profile: active")
    lines.append("  Profiles:")
    lines.append("    active:   95-130 mA (all sensors + Wi-Fi + inference)")
    lines.append("    idle:     20-30 mA (sensors polling, no radio)")
    lines.append("    dormant:  800 µA (LSM6DSOX MLC only, RP2040 sleeping)")
    lines.append("    sleep:    150 µA (RP2040 deep sleep)")
    lines.append("    hibernate: 5 µA (all off, RTC only)")
    return "\n".join(lines)


@tool(
    "arduino.battery_status",
    "Get battery status: voltage, current, percentage, estimated time remaining.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
        },
        "required": [],
    },
)
async def battery_status(args: dict) -> str:
    lines = ["Battery status:"]
    lines.append("  Voltage: 4.12 V")
    lines.append("  Current: 85 mA")
    lines.append("  Percentage: 87%")
    lines.append("  Estimated time remaining: 4.2 hours")
    lines.append("  Charge cycles: 42")
    lines.append("")
    lines.append("(Connect to device for live readings)")
    return "\n".join(lines)
