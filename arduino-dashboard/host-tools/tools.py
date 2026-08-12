"""
Arduino Dashboard Host Tools
Thin wrappers around arduino-cli, serial, and MCP toolkit
"""
import asyncio
import logging
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("host-tools")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ARDUPATH = PROJECT_ROOT / "arduino-mcp-toolkit"
ARP2040 = PROJECT_ROOT / "arp-2040"

def _run(cmd: list, cwd: Optional[Path] = None, timeout: int = 120) -> Dict[str, Any]:
    """Run a command synchronously"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd or PROJECT_ROOT)
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"ok": False, "error": str(e), "stdout": "", "stderr": ""}

async def _run_async(cmd: list, cwd: Optional[Path] = None, timeout: int = 120) -> Dict[str, Any]:
    """Run a command asynchronously"""
    return await asyncio.get_event_loop().run_in_executor(None, _run, cmd, cwd, timeout)

async def compile_sketch(sketch_path: str, fqbn: str = "arduino:mbed_nano:nanorp2040connect") -> Dict[str, Any]:
    """Compile an Arduino sketch"""
    cmd = ["arduino-cli", "compile", "--fqbn", fqbn, sketch_path]
    logger.info(f"Compiling: {sketch_path}")
    result = await _run_async(cmd, timeout=180)
    logger.info(f"Compile result: ok={result['ok']}")
    return result

async def flash_firmware(firmware_path: str, port: str = "COM15") -> Dict[str, Any]:
    """Flash compiled firmware to board"""
    cmd = ["arduino-cli", "upload", "-p", port, "--fqbn", "arduino:mbed_nano:nanorp2040connect", firmware_path]
    logger.info(f"Flashing: {firmware_path} -> {port}")
    result = await _run_async(cmd, timeout=180)
    logger.info(f"Flash result: ok={result['ok']}")
    return result

async def build_and_flash(sketch_path: str, port: str = "COM15") -> Dict[str, Any]:
    """Compile and flash atomically"""
    compile_result = await compile_sketch(sketch_path)
    if not compile_result.get("ok"):
        return {"ok": False, "stage": "compile", **compile_result}
    
    flash_result = await flash_firmware(sketch_path, port)
    return {"ok": flash_result.get("ok"), "stage": "flash", "compile": compile_result, "flash": flash_result}

async def _serial_command(port: str, command: str, timeout: int = 30) -> Dict[str, Any]:
    cmd = f'python -c "import serial; s=serial.Serial(\'{port}\', 921600, timeout={timeout}); s.write(b\'{command}\\n\'); print(s.readline().decode(\'utf-8\', \'replace\')); s.close()" 2>&1'
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 10)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return {"ok": False, "stdout": "", "error": "timeout"}
    text = stdout.decode("utf-8", "replace")
    return {"ok": proc.returncode == 0, "stdout": text, "error": None if proc.returncode == 0 else "command_failed", "returncode": proc.returncode}

async def model_load(port: str = "COM15") -> Dict[str, Any]:
    """Send model loader endpoint command to device"""
    return await _serial_command(port, "LOAD_MODEL")

async def model_infer(port: str, prompt: str) -> Dict[str, Any]:
    """Stream inference result for a prompt from device"""
    safe = prompt.replace("\\", "\\\\").replace('"', '\\"')
    return await _serial_command(port, f'INFER "{safe}"')

# ===== Tool Registry =====

TOOLS = {
    "compile": compile_sketch,
    "flash": flash_firmware,
    "build_and_flash": build_and_flash,
    "monitor": {"description": "Open serial monitor", "category": "connectivity"},
    "self_test": {"description": "Run self-test suite", "category": "diagnostics"},
    "memory_report": {"description": "Get SRAM/stack report", "category": "diagnostics"},
    "battery_status": {"description": "Get battery info", "category": "power"},
    "crypto_status": {"description": "Get ATECC608A status", "category": "security"},
    "agent_status": {"description": "Get agent status", "category": "agents"},
    "ota_update": {"description": "Atomic OTA update", "category": "deployment"},
    "rollback": {"description": "Rollback firmware", "category": "deployment"},
    "list_models": {"description": "List TinyML models", "category": "models"},
    "train_model": {"description": "Train TinyML model", "category": "models"},
    "package_model": {"description": "Package model as .armodel", "category": "models"},
    "deploy_model": {"description": "Deploy model to device", "category": "models"},
    "load_model": {"description": "Send LOAD_MODEL to device", "category": "models"},
    "inference_stream": {"description": "Stream inference result for prompt", "category": "models"},
}

async def call_tool(name: str, **kwargs) -> Dict[str, Any]:
    """Call a tool by name"""
    if name not in TOOLS:
        return {"ok": False, "error": f"Unknown tool: {name}. Available: {list(TOOLS.keys())}"}
    
    if name == "monitor":
        return {"ok": True, "message": "Use dashboard serial monitor page", "port": kwargs.get("port", "COM15")}
    if name == "self_test":
        return await _serial_command(kwargs.get("port", "COM15"), "TEST")
    if name == "memory_report":
        return await _serial_command(kwargs.get("port", "COM15"), "MEMORY_REPORT")
    if name == "battery_status":
        return await _serial_command(kwargs.get("port", "COM15"), "BATTERY_STATUS")
    if name == "crypto_status":
        return await _serial_command(kwargs.get("port", "COM15"), "CRYPTO_STATUS")
    if name == "agent_status":
        return await _serial_command(kwargs.get("port", "COM15"), "AGENTS")
    if name == "ota_update":
        return await _serial_command(kwargs.get("port", "COM15"), "OTA_UPDATE")
    if name == "rollback":
        return await _serial_command(kwargs.get("port", "COM15"), "ROLLBACK")
    if name == "list_models":
        sys.path.insert(0, str(Path(__file__).parent))
        from tinyml import list_models
        return await list_models()
    if name == "train_model":
        sys.path.insert(0, str(Path(__file__).parent))
        from tinyml import train_model
        return await train_model(kwargs.get("model", "kws_cnn"), kwargs.get("epochs"))
    if name == "package_model":
        sys.path.insert(0, str(Path(__file__).parent))
        from tinyml import package_model
        return await package_model(kwargs.get("model_path", ""), kwargs.get("output_name"), sign=bool(kwargs.get("sign")))
    if name == "deploy_model":
        sys.path.insert(0, str(Path(__file__).parent))
        from tinyml import deploy_model
        return await deploy_model(kwargs.get("model", "kws_cnn"))
    if name == "load_model":
        return await model_load(kwargs.get("port", "COM15"))
    if name == "inference_stream":
        return await model_infer(kwargs.get("port", "COM15"), kwargs.get("prompt", ""))
    
    return {"ok": False, "error": f"Tool not implemented: {name}"}
