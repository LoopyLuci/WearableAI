"""
Serial transport for Arduino communication
"""
import asyncio
import json
import logging
import re
from typing import Optional
from serial.tools import list_ports
import serial
import time

logger = logging.getLogger("serial-transport")

class SerialBusyError(Exception):
    pass

class SerialTransport:
    def __init__(self, port: str = "COM15", baudrate: int = 921600):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self._read_task: Optional[asyncio.Task] = None
        self._telemetry_active = False
        self._command_lock = asyncio.Lock()

    async def connect(self):
        """Connect to serial port"""
        await asyncio.get_event_loop().run_in_executor(None, self._connect_sync)
        self._telemetry_active = True
        self._read_task = asyncio.get_event_loop().create_task(self._reader_loop())
        logger.info(f"Connected to {self.port} @ {self.baudrate}")

    def _connect_sync(self):
        """Synchronous connect in thread executor"""
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=1,
            write_timeout=1
        )
        time.sleep(2)

    async def disconnect(self):
        """Disconnect from serial port"""
        self._telemetry_active = False
        if self._read_task:
            self._read_task.cancel()
            self._read_task = None
        if self.serial and self.serial.is_open:
            self.serial.close()
        logger.info(f"Disconnected from {self.port}")

    async def _reader_loop(self):
        """Background reader that collects telemetry lines"""
        while self._telemetry_active and self.serial and self.serial.is_open:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.serial.readline,
                )
            except Exception as e:
                if self._telemetry_active:
                    logger.error(f"Read error: {e}")
                break
            if not line:
                continue
            text = line.decode("utf-8", "replace").strip()
            if text == "":
                continue
            logger.debug(f"telemetry: {text}")

    async def send_command(self, command: str, payload: dict = None, timeout: float = 3.0) -> dict:
        """Send a command and collect response lines without telemetry interference"""
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("Serial port not open")

        if payload:
            cmd_str = f"{command} {json.dumps(payload)}\n"
        else:
            cmd_str = f"{command}\n"

        async with self._command_lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.serial.write,
                cmd_str.encode()
            )

            lines = []
            deadline = time.time() + timeout
            while time.time() < deadline and len(lines) < 20:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.serial.readline,
                    )
                except Exception as e:
                    logger.error(f"Read error: {e}")
                    break
                if not line:
                    continue
                text = line.decode("utf-8", "replace").strip()
                if text == "":
                    continue
                lines.append(text)
                if text.startswith("[WARN] Unknown command"):
                    break
                if text.startswith("[RESULT]") or text.startswith("[END DUMP]"):
                    break
                if text.startswith("{\"status\":\"ok\""):
                    break
                if text.startswith("[MODEL]") or text.startswith("[PASS]") or text.startswith("[FAIL]"):
                    break
            return {
                "command": command,
                "lines": lines,
                "response": lines[-1] if lines else "",
            }

    async def read_line(self) -> Optional[str]:
        """Read a line from serial port"""
        if not self.serial or not self.serial.is_open:
            return None
        try:
            async with self._command_lock:
                line = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.serial.readline
                )
            return line.decode().strip()
        except Exception as e:
            logger.error(f"Read error: {e}")
            return None

    async def write_line(self, line: str):
        """Write a line to serial port"""
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("Serial port not open")
        async with self._command_lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.serial.write,
                (line + "\n").encode()
            )

    @staticmethod
    async def list_ports() -> list:
        """List available serial ports"""
        ports = []
        for port in list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid
            })
        return ports

    def __repr__(self):
        return f"SerialTransport(port={self.port}, baudrate={self.baudrate}, open={self.serial.is_open if self.serial else False})"
