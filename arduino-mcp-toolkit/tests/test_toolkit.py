"""
Tests for arduino_mcp_toolkit
"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from arduino_mcp_toolkit.tools import TOOL_SPECS
from arduino_mcp_toolkit.resources import RESOURCE_SPECS, register_all_resources as _register_resources
from arduino_mcp_toolkit import tools as tools_pkg

# Register all tool handlers first
tools_pkg.register_all_tools()
from arduino_mcp_toolkit.tools import TOOL_HANDLERS

# Register all resource handlers
_register_resources()
from arduino_mcp_toolkit.resources import RESOURCE_HANDLERS

from arduino_mcp_toolkit.hardware import HardwareManager, KNOWN_BOARDS
from arduino_mcp_toolkit.compiler import CompilerManager
from arduino_mcp_toolkit.serial import SerialManager
from arduino_mcp_toolkit.generator import SketchGenerator, HALGenerator, ProjectGenerator


# ──────────────────────────────────────────────────────────────────────────────
# Tool registry tests
# ──────────────────────────────────────────────────────────────────────────────

def test_all_tool_specs_have_handlers():
    """Every tool spec must have a registered handler."""
    spec_names = {s["name"] for s in TOOL_SPECS}
    handler_names = set(TOOL_HANDLERS.keys())
    missing = spec_names - handler_names
    assert not missing, f"Tools missing handlers: {missing}"
    print(f"✓ All {len(spec_names)} tools have handlers")


def test_all_handlers_have_specs():
    """Every handler must have a matching spec."""
    spec_names = {s["name"] for s in TOOL_SPECS}
    handler_names = set(TOOL_HANDLERS.keys())
    extra = handler_names - spec_names
    assert not extra, f"Handlers without specs: {extra}"
    print(f"✓ All {len(handler_names)} handlers have specs")


def test_tool_count():
    """We expect at least 35 tools."""
    assert len(TOOL_SPECS) >= 35, f"Expected >= 35 tools, got {len(TOOL_SPECS)}"
    print(f"✓ Tool count: {len(TOOL_SPECS)}")


# ──────────────────────────────────────────────────────────────────────────────
# Resource registry tests
# ──────────────────────────────────────────────────────────────────────────────

def test_all_resources_have_handlers():
    spec_uris = {s["uri"] for s in RESOURCE_SPECS}
    handler_uris = set(RESOURCE_HANDLERS.keys())
    missing = spec_uris - handler_uris
    assert not missing, f"Resources missing handlers: {missing}"
    print(f"✓ All {len(spec_uris)} resources have handlers")


def test_resource_count():
    assert len(RESOURCE_SPECS) >= 10, f"Expected >= 10 resources, got {len(RESOURCE_SPECS)}"
    print(f"✓ Resource count: {len(RESOURCE_SPECS)}")


# ──────────────────────────────────────────────────────────────────────────────
# Hardware manager tests
# ──────────────────────────────────────────────────────────────────────────────

def test_known_boards():
    assert len(KNOWN_BOARDS) >= 4, "Expected at least 4 known boards"
    for vid_pid, info in KNOWN_BOARDS.items():
        assert "board" in info
        assert "mcu" in info
        assert "flash_kb" in info
        assert "sram_kb" in info
    print(f"✓ Known boards: {len(KNOWN_BOARDS)}")


def test_pin_map_available():
    hw = HardwareManager.get_instance()
    pins = hw.get_pin_map("nano_rp2040_connect")
    assert len(pins) > 0, "Pin map should not be empty"
    names = [p["name"] for p in pins]
    assert "D0" in names
    assert "A0" in names
    print(f"✓ Pin map: {len(pins)} pins for nano_rp2040_connect")


# ──────────────────────────────────────────────────────────────────────────────
# Compiler manager tests
# ──────────────────────────────────────────────────────────────────────────────

def test_compiler_manager_singleton():
    c1 = CompilerManager.get_instance()
    c2 = CompilerManager.get_instance()
    assert c1 is c2, "CompilerManager should be singleton"
    print("✓ CompilerManager singleton pattern works")


# ──────────────────────────────────────────────────────────────────────────────
# Serial manager tests
# ──────────────────────────────────────────────────────────────────────────────

def test_serial_manager_singleton():
    s1 = SerialManager.get_instance()
    s2 = SerialManager.get_instance()
    assert s1 is s2, "SerialManager should be singleton"
    print("✓ SerialManager singleton pattern works")


# ──────────────────────────────────────────────────────────────────────────────
# Generator tests
# ──────────────────────────────────────────────────────────────────────────────

def test_sketch_generator_basic():
    gen = SketchGenerator()
    code = gen.generate("Blink the built-in LED", features=["wifi", "tinyml"])
    assert "void setup()" in code
    assert "void loop()" in code
    assert len(code.splitlines()) > 20
    print(f"✓ Generated sketch: {len(code.splitlines())} lines")


def test_hal_generator():
    gen = HALGenerator()
    files = gen.generate("nano_rp2040_connect", os.path.join(tempfile.gettempdir(), "test_hal"))
    assert len(files) == 16, f"Expected 16 HAL files, got {len(files)}"
    for f in files:
        assert f.endswith(".h") or f.endswith(".cpp")
    print(f"✓ Generated HAL: {len(files)} files")


def test_project_generator():
    gen = ProjectGenerator()
    files = gen.generate("TestProject", "rp2040:rp2040:nano_rp2040_connect",
                         os.path.join(tempfile.gettempdir(), "test_proj"), features=["tinyml"])
    assert any("platformio.ini" in f for f in files)
    assert any("main.cpp" in f for f in files)
    print(f"✓ Generated project: {len(files)} files")


# ──────────────────────────────────────────────────────────────────────────────
# Handler async smoke tests
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_handler():
    from arduino_mcp_toolkit.tools.hardware_tools import detect
    result = await detect({})
    assert isinstance(result, str)
    assert "Detected" in result or "No" in result


@pytest.mark.asyncio
async def test_board_info_handler():
    from arduino_mcp_toolkit.tools.hardware_tools import board_info
    result = await board_info({})
    assert isinstance(result, str)
    assert "Board:" in result


@pytest.mark.asyncio
async def test_generate_sketch_handler():
    from arduino_mcp_toolkit.tools.generator_tools import generate_sketch
    tmp_ino = os.path.join(tempfile.gettempdir(), "test_generated.ino")
    result = await generate_sketch({
        "description": "Blink LED with BLE",
        "features": ["ble"],
        "output_path": tmp_ino,
    })
    assert "Generated sketch" in result
    assert os.path.exists(tmp_ino)
    if os.path.exists(tmp_ino):
        os.remove(tmp_ino)


@pytest.mark.asyncio
async def test_generate_hal_handler():
    from arduino_mcp_toolkit.tools.generator_tools import generate_hal
    tmp_hal = os.path.join(tempfile.gettempdir(), "test_hal_out")
    result = await generate_hal({"board": "nano_rp2040_connect", "output_dir": tmp_hal})
    assert "HAL for nano_rp2040_connect" in result


@pytest.mark.asyncio
async def test_generate_project_handler():
    from arduino_mcp_toolkit.tools.generator_tools import generate_project
    tmp_proj = os.path.join(tempfile.gettempdir(), "test_proj_out")
    result = await generate_project({
        "name": "TestProject",
        "board": "rp2040:rp2040:nano_rp2040_connect",
        "output_dir": tmp_proj,
    })
    assert "Generated project" in result


@pytest.mark.asyncio
async def test_search_libraries_handler():
    from arduino_mcp_toolkit.tools.knowledge_tools import search_libraries
    result = await search_libraries({"query": "tinyml"})
    assert "Libraries matching" in result


@pytest.mark.asyncio
async def test_train_model_handler():
    from arduino_mcp_toolkit.tools.ml_tools import train_model
    result = await train_model({"task": "kws", "dataset_path": "/tmp/data.csv"})
    assert "Training TinyML model" in result


@pytest.mark.asyncio
async def test_validate_sketch_handler():
    from arduino_mcp_toolkit.tools.testing_tools import validate_sketch
    result = await validate_sketch({"source_path": "/tmp/test.ino"})
    assert "Validating" in result


@pytest.mark.asyncio
async def test_self_test_handler():
    from arduino_mcp_toolkit.tools.agentic_tools import self_test
    result = await self_test({})
    assert "ALL TESTS PASSED" in result


@pytest.mark.asyncio
async def test_serial_command_handler():
    from arduino_mcp_toolkit.tools.serial_command_tools import serial_command
    result = await serial_command({"port": "COM1", "command": "PING", "timeout_s": 0.5, "max_retries": 0})
    assert "cmd: PING" in result or "ERROR" in result


@pytest.mark.asyncio
async def test_memory_report_handler():
    from arduino_mcp_toolkit.tools.debug_tools import memory_report
    result = await memory_report({"detailed": True})
    assert "Memory Report" in result
    assert "Per-task" in result


@pytest.mark.asyncio
async def test_ota_update_handler():
    from arduino_mcp_toolkit.tools.ota_tools import ota_update
    result = await ota_update({})
    assert "Atomic OTA" in result


# ──────────────────────────────────────────────────────────────────────────────
# Resource handler smoke tests
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_available_boards_resource():
    handler = RESOURCE_HANDLERS.get("arduino://boards/available")
    assert handler
    result = await handler()
    assert "nano_rp2040_connect" in result


@pytest.mark.asyncio
async def test_setup_guide_resource():
    handler = RESOURCE_HANDLERS.get("arduino://docs/setup")
    assert handler
    result = await handler()
    assert "Setup Guide" in result or "setup" in result.lower()


@pytest.mark.asyncio
async def test_control_graph_schema_resource():
    handler = RESOURCE_HANDLERS.get("arduino://schemas/control_graph")
    assert handler
    result = await handler()
    assert "nodes" in result
