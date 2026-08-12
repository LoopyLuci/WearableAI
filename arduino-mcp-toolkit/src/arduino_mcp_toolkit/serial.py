"""
arduino_mcp_toolkit.serial — Async serial port manager
"""
from __future__ import annotations
import asyncio
import logging
import serial
import serial.tools.list_ports
from typing import Optional, Callable
from arduino_mcp_toolkit.utils import get_config

logger = logging.getLogger("arduino-mcp")


class SerialManager:
    """Singleton async serial port manager."""

    _instance: SerialManager | None = None

    def __init__(self, config: dict):
        self._config = config
        self._ports: dict[str, serial.Serial] = {}
        self._readers: dict[str, asyncio.StreamReader] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> SerialManager:
        if cls._instance is None:
            config = get_config()
            cls._instance = cls(config)
        return cls._instance

    async def open(self, port: str, baud: int = 115200, timeout: float = 1.0) -> bool:
        async with self._lock:
            if port in self._ports and self._ports[port].is_open:
                return True
            try:
                loop = asyncio.get_event_loop()
                ser = await loop.run_in_executor(
                    None,
                    lambda: serial.Serial(port=port, baudrate=baud, timeout=timeout, write_timeout=timeout),
                )
                self._ports[port] = ser
                logger.info(f"Opened serial: {port} @ {baud}")
                return True
            except serial.SerialException as e:
                logger.error(f"Failed to open {port}: {e}")
                return False

    async def close(self, port: str):
        async with self._lock:
            if port in self._ports:
                try:
                    self._ports[port].close()
                except Exception:
                    pass
                del self._ports[port]
                logger.info(f"Closed serial: {port}")

    async def read_line(self, port: str, timeout: float = 5.0) -> str:
        """Read one line from the serial port."""
        ser = self._ports.get(port)
        if not ser or not ser.is_open:
            raise ConnectionError(f"Port {port} not open")

        loop = asyncio.get_event_loop()
        try:
            line = await asyncio.wait_for(
                loop.run_in_executor(None, ser.readline),
                timeout=timeout,
            )
            return line.decode("utf-8", errors="replace").strip()
        except asyncio.TimeoutError:
            raise

    async def read_bytes(self, port: str, count: int, timeout: float = 5.0) -> bytes:
        ser = self._ports.get(port)
        if not ser or not ser.is_open:
            raise ConnectionError(f"Port {port} not open")

        loop = asyncio.get_event_loop()
        try:
            data = await asyncio.wait_for(
                loop.run_in_executor(None, ser.read, count),
                timeout=timeout,
            )
            return data
        except asyncio.TimeoutError:
            raise

    async def write(self, port: str, data: str) -> int:
        ser = self._ports.get(port)
        if not ser or not ser.is_open:
            raise ConnectionError(f"Port {port} not open")

        loop = asyncio.get_event_loop()
        encoded = data.encode("utf-8") if isinstance(data, str) else data
        return await loop.run_in_executor(None, ser.write, encoded)

    async def send_command(self, port: str, command: str, timeout: float = 5.0) -> str:
        """Send a command and read the response."""
        await self.write(port, command + "\n")
        try:
            response = await asyncio.wait_for(self.read_line(port, timeout), timeout=timeout + 1)
            return response
        except asyncio.TimeoutError:
            return "TIMEOUT"

    def list_ports(self) -> list[dict]:
        """List all available serial ports."""
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            result.append({
                "device": p.device,
                "description": p.description or "",
                "hwid": p.hwid or "",
                "vid": p.vid,
                "pid": p.pid,
                "serial_number": p.serial_number,
            })
        return result

    async def auto_open(self, baud: int = 115200) -> Optional[str]:
        """Auto-detect and open the first Arduino port."""
        ports = self.list_ports()
        for p in ports:
            if "arduino" in p["description"].lower() or "nina" in p["description"].lower() or p["vid"] in [0x2341, 0x2E8A, 0x239A, 0x10C4, 0x1A86]:
                if await self.open(p["device"], baud):
                    return p["device"]
        return None
