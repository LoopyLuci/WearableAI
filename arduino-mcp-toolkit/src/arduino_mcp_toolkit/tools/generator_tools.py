"""
arduino_mcp_toolkit.tools.generator_tools — Sketch, HAL, and project generation tools
"""
from __future__ import annotations
import os
import logging
from typing import Any
from arduino_mcp_toolkit.tools import tool
from arduino_mcp_toolkit.generator import SketchGenerator, HALGenerator, ProjectGenerator

logger = logging.getLogger("arduino-mcp")


@tool(
    "arduino.generate_sketch",
    "Generate a complete, production-ready Arduino sketch from a natural language description.",
    {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Natural language description"},
            "board": {"type": "string"},
            "features": {"type": "array", "items": {"type": "string"}},
            "output_path": {"type": "string"},
            "include_tests": {"type": "boolean", "default": True},
        },
        "required": ["description"],
    },
)
async def generate_sketch(args: dict) -> str:
    description = args["description"]
    output_path = args.get("output_path", "generated_sketch.ino")
    features = args.get("features", [])
    include_tests = args.get("include_tests", True)

    generator = SketchGenerator()
    code = generator.generate(description, features=features, include_tests=include_tests)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(code)

    lines = [f"Generated sketch: {output_path}"]
    lines.append(f"  Lines of code: {len(code.splitlines())}")
    lines.append(f"  Features: {', '.join(features) or 'none specified'}")
    lines.append(f"  Tests included: {include_tests}")
    lines.append("")
    lines.append("Next steps:")
    lines.append(f"  arduino-mcp compile --source {output_path}")
    lines.append(f"  arduino-mcp build-and-flash --source {output_path}")
    return "\n".join(lines)


@tool(
    "arduino.generate_hal",
    "Generate a complete Hardware Abstraction Layer (HAL) for a specific board.",
    {
        "type": "object",
        "properties": {
            "board": {"type": "string"},
            "output_dir": {"type": "string"},
        },
        "required": ["board"],
    },
)
async def generate_hal(args: dict) -> str:
    board = args["board"]
    output_dir = args.get("output_dir", f"hal_{board}")

    generator = HALGenerator()
    files = generator.generate(board, output_dir)

    lines = [f"Generated HAL for {board}: {output_dir}/"]
    lines.append(f"  Files generated: {len(files)}")
    for f in files:
        lines.append(f"    {f}")
    lines.append("")
    lines.append("HAL interfaces:")
    lines.append("  ISensor  — All sensor drivers (IMU, mic, temp, etc.)")
    lines.append("  IRadio   — Wi-Fi + BLE via NINA-W102")
    lines.append("  ICrypto  — ATECC608A hardware crypto")
    lines.append("  IStorage — QSPI flash + LittleFS")
    lines.append("  IPower   — Power states, battery monitor")
    lines.append("  IAudio   — PDM microphone")
    lines.append("  IDisplay — OLED/LCD displays")
    lines.append("  IActuator — LED, vibration, GPIO")
    return "\n".join(lines)


@tool(
    "arduino.generate_project",
    "Generate a complete PlatformIO project structure.",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "board": {"type": "string"},
            "output_dir": {"type": "string"},
            "framework": {"type": "string", "enum": ["arduino", "platformio", "cmake"], "default": "platformio"},
            "features": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name", "board"],
    },
)
async def generate_project(args: dict) -> str:
    name = args["name"]
    board = args["board"]
    output_dir = args.get("output_dir", name)
    framework = args.get("framework", "platformio")
    features = args.get("features", [])

    generator = ProjectGenerator()
    files = generator.generate(name, board, output_dir, framework=framework, features=features)

    lines = [f"Generated project '{name}' in {output_dir}/"]
    lines.append(f"  Framework: {framework}")
    lines.append(f"  Board: {board}")
    lines.append(f"  Files: {len(files)}")
    lines.append(f"  Features: {', '.join(features) or 'none'}")
    for f in files:
        lines.append(f"    {f}")
    lines.append("")
    lines.append("Next steps:")
    lines.append(f"  cd {output_dir}")
    lines.append(f"  arduino-mcp build-and-flash --source {output_dir}")
    return "\n".join(lines)
