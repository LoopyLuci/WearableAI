"""
arduino_mcp_toolkit.tools.compiler_tools — Compile, flash, build+flash tools
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any
from arduino_mcp_toolkit.compiler import CompilerManager
from arduino_mcp_toolkit.tools import tool

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.compile",
    "Compile an Arduino sketch (.ino) or PlatformIO project.",
    {
        "type": "object",
        "properties": {
            "source_path": {"type": "string", "description": "Path to .ino or project dir"},
            "fqbn": {"type": "string", "description": "Fully Qualified Board Name"},
            "verbose": {"type": "boolean", "default": False},
            "optimize_for": {"type": "string", "enum": ["size", "speed", "debug"], "default": "size"},
        },
        "required": ["source_path"],
    },
)
async def compile(args: dict) -> str:
    compiler = CompilerManager.get_instance()
    result = await compiler.compile(
        source_path=args["source_path"],
        fqbn=args.get("fqbn"),
        verbose=args.get("verbose", False),
        optimize_for=args.get("optimize_for", "size"),
    )
    lines = [
        f"Compile {'PASSED' if result.success else 'FAILED'}",
        f"Binary: {result.binary_path}",
        f"Size: {result.flash_usage_kb:.1f} KB flash, {result.sram_usage_kb:.1f} KB SRAM",
    ]
    if result.warnings:
        lines.append(f"Warnings ({len(result.warnings)}):")
        for w in result.warnings[:10]:
            lines.append(f"  {w}")
    if result.errors:
        lines.append(f"Errors ({len(result.errors)}):")
        for e in result.errors[:10]:
            lines.append(f"  {e}")
    return "\n".join(lines)


@tool(
    "arduino.flash",
    "Flash a compiled binary to an Arduino.",
    {
        "type": "object",
        "properties": {
            "binary_path": {"type": "string"},
            "port": {"type": "string"},
            "fqbn": {"type": "string"},
            "reset_method": {"type": "string", "enum": ["auto", "dtr", "manual", "no_reset"], "default": "auto"},
            "verify": {"type": "boolean", "default": True},
        },
        "required": [],
    },
)
async def flash(args: dict) -> str:
    compiler = CompilerManager.get_instance()
    result = await compiler.flash(
        binary_path=args.get("binary_path"),
        port=args.get("port"),
        fqbn=args.get("fqbn"),
        reset_method=args.get("reset_method", "auto"),
        verify=args.get("verify", True),
    )
    return f"Flash {'SUCCESS' if result.success else 'FAILED'}\n{result.message}"


@tool(
    "arduino.build_and_flash",
    "Compile AND flash in one atomic operation with automatic rollback on failure.",
    {
        "type": "object",
        "properties": {
            "source_path": {"type": "string"},
            "fqbn": {"type": "string"},
            "port": {"type": "string"},
            "watchdog_timeout_s": {"type": "integer", "default": 30},
        },
        "required": ["source_path"],
    },
)
async def build_and_flash(args: dict) -> str:
    compiler = CompilerManager.get_instance()
    result = await compiler.build_and_flash(
        source_path=args["source_path"],
        fqbn=args.get("fqbn"),
        port=args.get("port"),
        watchdog_timeout_s=args.get("watchdog_timeout_s", 30),
    )
    lines = [
        f"Build+Flash {'SUCCESS' if result.success else 'FAILED'}",
        f"Binary: {result.binary_path}",
        f"Flash: {result.flash_usage_kb:.1f} KB, SRAM: {result.sram_usage_kb:.1f} KB",
        f"Rollback: {'Available' if result.rollback_available else 'N/A'}",
    ]
    return "\n".join(lines)
