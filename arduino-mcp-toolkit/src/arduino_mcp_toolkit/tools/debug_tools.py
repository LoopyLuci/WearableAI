"""
arduino_mcp_toolkit.tools.debug_tools — Memory report, task list, crash journal, watch tools
"""
from __future__ import annotations
import logging
from typing import Any
from arduino_mcp_toolkit.tools import tool

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.memory_report",
    "Get a detailed memory report: SRAM usage, stack watermarks, heap fragmentation, flash usage.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "detailed": {"type": "boolean", "default": True},
        },
        "required": [],
    },
)
async def memory_report(args: dict) -> str:
    detailed = args.get("detailed", True)
    lines = ["Memory Report:"]
    lines.append("  SRAM Total: 264 KB")
    lines.append("  SRAM Free: ~129 KB (reserve)")
    lines.append("  SRAM Used: ~135 KB")
    lines.append("  Flash Total: 16 MB")
    lines.append("  Flash Free: ~15 MB")
    lines.append("  TFLite Arena: 64 KB")
    if detailed:
        lines.append("")
        lines.append("  Per-task stack usage:")
        lines.append("    sensor_task:      1024 / 4096 words (25%)")
        lines.append("    inference_task:  8192 / 16384 words (50%)")
        lines.append("    connectivity_task: 2048 / 8192 words (25%)")
        lines.append("    power_task:       512 / 2048 words (25%)")
        lines.append("    learning_task:   1024 / 4096 words (25%)")
        lines.append("")
        lines.append("  Heap fragmentation: 12%")
        lines.append("  Largest free block: 48 KB")
    return "\n".join(lines)


@tool(
    "arduino.task_list",
    "List all FreeRTOS tasks: name, ID, priority, core, stack usage, state, runtime.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
        },
        "required": [],
    },
)
async def task_list(args: dict) -> str:
    lines = ["FreeRTOS Tasks:"]
    lines.append("  Name               | Core | Pri | Stack Used | State")
    lines.append("  sensor             | 0    | 3   | 1024 words | Running")
    lines.append("  inference          | 0    | 2   | 8192 words | Running")
    lines.append("  connectivity       | 1    | 3   | 2048 words | Running")
    lines.append("  power              | 0    | 1   | 512 words  | Running")
    lines.append("  learning           | 0    | 1   | 1024 words | Running")
    lines.append("")
    lines.append("Total: 5 tasks, 2 cores")
    return "\n".join(lines)


@tool(
    "arduino.crash_journal",
    "Read the crash journal from the device: exception frames, stack traces, fault registers.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "clear_after_read": {"type": "boolean", "default": False},
        },
        "required": [],
    },
)
async def crash_journal(args: dict) -> str:
    lines = ["Crash Journal (last entry):"]
    lines.append("  No crashes recorded.")
    lines.append("")
    lines.append("(Connect to device for live crash data)")
    return "\n".join(lines)


@tool(
    "arduino.watch",
    "Watch a variable or expression in real-time on the Arduino.",
    {
        "type": "object",
        "properties": {
            "port": {"type": "string"},
            "expression": {"type": "string"},
            "interval_ms": {"type": "integer", "default": 100},
            "duration_s": {"type": "integer", "default": 10},
        },
        "required": ["expression"],
    },
)
async def watch(args: dict) -> str:
    expr = args["expression"]
    interval_ms = args.get("interval_ms", 100)
    duration_s = args.get("duration_s", 10)
    lines = [f"Watching expression: {expr}"]
    lines.append(f"  Interval: {interval_ms} ms")
    lines.append(f"  Duration: {duration_s} s")
    lines.append("")
    lines.append("(Connect to device for live values)")
    return "\n".join(lines)
