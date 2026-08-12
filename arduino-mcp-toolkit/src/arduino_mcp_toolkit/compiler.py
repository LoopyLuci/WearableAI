"""
arduino_mcp_toolkit.compiler — Compile, flash, atomic build+flash manager
"""
from __future__ import annotations
import asyncio
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional
from arduino_mcp_toolkit.serial import SerialManager
from arduino_mcp_toolkit.utils import get_config

logger = logging.getLogger("arduino-mcp")


@dataclass
class CompileResult:
    success: bool
    binary_path: str = ""
    flash_usage_kb: float = 0.0
    sram_usage_kb: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rollback_available: bool = False


class CompilerManager:
    """Singleton compile/flash manager."""

    _instance: CompilerManager | None = None

    def __init__(self, config: dict):
        self._config = config
        self._workspace = config.get("workspace", os.getcwd())

    @classmethod
    def get_instance(cls) -> CompilerManager:
        if cls._instance is None:
            config = get_config()
            cls._instance = cls(config)
        return cls._instance

    async def compile(self, source_path: str, fqbn: str = None, verbose: bool = False, optimize_for: str = "size") -> CompileResult:
        source_path = os.path.abspath(source_path)
        if not os.path.exists(source_path):
            return CompileResult(success=False, errors=[f"Path not found: {source_path}"])

        board = fqbn or self._detect_fqbn(source_path)

        # Build PlatformIO command
        cmd = [
            "pio", "run",
            "-e", board.replace(":", "_"),
            "-d", os.path.dirname(source_path) if os.path.isfile(source_path) else source_path,
        ]
        if optimize_for == "size":
            cmd.extend(["-O", "size"])
        elif optimize_for == "speed":
            cmd.extend(["-O", "optimize"])
        else:
            cmd.extend(["-O", "debug"])

        logger.info(f"Compiling: {' '.join(cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return CompileResult(
                    success=False,
                    errors=[stderr_str[-2000:]],
                    warnings=[],
                )

            # Parse output for flash/SRAM usage
            flash_kb, sram_kb = self._parse_size_output(stdout_str + stderr_str)

            # Find binary path
            proj_dir = os.path.dirname(source_path) if os.path.isfile(source_path) else source_path
            pio_dir = os.path.join(proj_dir, ".pio", board.replace(":", "_"))
            firmware_dir = os.path.join(pio_dir, "firmware")
            binary_path = ""
            if os.path.exists(firmware_dir):
                for f in os.listdir(firmware_dir):
                    if f.endswith(".bin"):
                        binary_path = os.path.join(firmware_dir, f)
                        break

            return CompileResult(
                success=True,
                binary_path=binary_path,
                flash_usage_kb=flash_kb,
                sram_usage_kb=sram_kb,
                warnings=self._parse_warnings(stdout_str + stderr_str),
            )
        except asyncio.TimeoutError:
            return CompileResult(success=False, errors=["Compile timeout (>120s)"])
        except FileNotFoundError:
            return CompileResult(success=False, errors=["PlatformIO not found. Install with: pip install platformio"])

    async def flash(self, binary_path: str = None, port: str = None, fqbn: str = None, reset_method: str = "auto", verify: bool = True) -> CompileResult:
        if not binary_path or not os.path.exists(binary_path):
            return CompileResult(success=False, errors=[f"Binary not found: {binary_path}"])

        cmd = [
            "pio", "run",
            "-t", "upload",
            "--upload-port", port or "",
        ]
        if not verify:
            cmd.append("--without-verify")

        logger.info(f"Flashing: {' '.join(cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = (stdout + stderr).decode("utf-8", errors="replace")
            success = proc.returncode == 0
            return CompileResult(success=success, binary_path=binary_path, errors=[] if success else [output[-1000:]])
        except asyncio.TimeoutError:
            return CompileResult(success=False, errors=["Flash timeout"])
        except FileNotFoundError:
            return CompileResult(success=False, errors=["PlatformIO not found"])

    async def build_and_flash(self, source_path: str, fqbn: str = None, port: str = None, watchdog_timeout_s: int = 30) -> CompileResult:
        # Step 1: Compile
        compile_result = await self.compile(source_path, fqbn)
        if not compile_result.success:
            return compile_result

        # Step 2: Flash
        flash_result = await self.flash(compile_result.binary_path, port, fqbn)
        if not flash_result.success:
            return flash_result

        # Step 3: Start watchdog — wait for device to come back
        serial_mgr = SerialManager.get_instance()
        rollback_available = False
        try:
            await asyncio.wait_for(
                self._wait_for_boot(port, serial_mgr),
                timeout=watchdog_timeout_s,
            )
            rollback_available = True
        except asyncio.TimeoutError:
            logger.warning("Device did not come back after flash — rollback may be needed")

        return CompileResult(
            success=True,
            binary_path=compile_result.binary_path,
            flash_usage_kb=compile_result.flash_usage_kb,
            sram_usage_kb=compile_result.sram_usage_kb,
            rollback_available=rollback_available,
        )

    async def _wait_for_boot(self, port: str, serial_mgr: SerialManager, timeout: float = 30):
        """Wait for device to reboot and respond to ping."""
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                response = await asyncio.wait_for(
                    serial_mgr.send_command(port, "PING"),
                    timeout=2.0,
                )
                if "PONG" in response:
                    return
            except (asyncio.TimeoutError, Exception):
                pass
            await asyncio.sleep(0.5)
        raise asyncio.TimeoutError("Device did not boot")

    def _detect_fqbn(self, source_path: str) -> str:
        """Auto-detect FQBN from project or config."""
        # Check platformio.ini
        proj_dir = os.path.dirname(source_path) if os.path.isfile(source_path) else source_path
        ini_path = os.path.join(proj_dir, "platformio.ini")
        if os.path.exists(ini_path):
            with open(ini_path) as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.startswith("[env:") and "native" not in line:
                        return line[5:].strip("]")
        return "nano_rp2040_connect"

    def _parse_size_output(self, output: str) -> tuple[float, float]:
        flash_kb = 0.0
        sram_kb = 0.0
        for line in output.split("\n"):
            if "Flash:" in line or "flash" in line.lower():
                parts = line.split()
                for p in parts:
                    if p.endswith("KB") or p.endswith("bytes"):
                        try:
                            val = float(p.replace("KB", "").replace("bytes", "").strip())
                            if "Flash" in line:
                                flash_kb = val if p.endswith("KB") else val / 1024
                            elif "SRAM" in line or "RAM" in line:
                                sram_kb = val if p.endswith("KB") else val / 1024
                        except ValueError:
                            pass
        return flash_kb, sram_kb

    def _parse_warnings(self, output: str) -> list[str]:
        warnings = []
        for line in output.split("\n"):
            if "warning:" in line.lower() or "warning " in line.lower():
                warnings.append(line.strip())
        return warnings[:20]
