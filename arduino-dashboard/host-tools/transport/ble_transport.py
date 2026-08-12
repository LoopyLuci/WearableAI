"""
BLE transport for Arduino communication via Web Bluetooth
"""
import asyncio
import logging
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger("ble-transport")

@dataclass
class BLEDevice:
    name: str
    address: str
    rssi: int = -100
    services: list = None

    def __post_init__(self):
        if self.services is None:
            self.services = []

class BLETransport:
    """Web Bluetooth transport - requires browser environment"""
    
    def __init__(self, device_name: str = "ARP-2040"):
        self.device_name = device_name
        self.device: Optional[BLEDevice] = None
        self.characteristics: Dict[str, Any] = {}
        self._connected = False

    async def connect(self):
        """Connect to BLE device - browser only"""
        logger.warning("BLE transport requires browser Web Bluetooth API")
        self._connected = False
        raise NotImplementedError(
            "BLE transport requires browser environment with Web Bluetooth support. "
            "Use the dashboard's connect_ble command from the UI."
        )

    async def disconnect(self):
        """Disconnect from BLE device"""
        self._connected = False
        logger.info("BLE disconnected")

    async def send_command(self, command: str, payload: dict = None) -> dict:
        """Send command via BLE"""
        if not self._connected:
            raise RuntimeError("Not connected to BLE device")
        raise NotImplementedError("BLE command sending requires browser context")

    async def read_line(self) -> Optional[str]:
        """Read line from BLE"""
        return None

    async def write_line(self, line: str):
        """Write line to BLE"""
        pass

    @staticmethod
    async def scan() -> list:
        """Scan for BLE devices - browser only"""
        logger.warning("BLE scan requires browser Web Bluetooth API")
        return []

class BLETransportBridge:
    """
    Bridge for BLE operations executed in browser context.
    This class provides methods that will be called via WebSocket from browser.
    """
    
    def __init__(self):
        self._device_cache: list[BLEDevice] = []

    async def scan(self) -> list:
        """Return cached scan results from browser"""
        return [asdict(d) for d in self._device_cache]

    def update_scan_results(self, devices: list):
        """Update device cache from browser scan"""
        self._device_cache = [BLEDevice(**d) for d in devices]

ble_bridge = BLETransportBridge()
