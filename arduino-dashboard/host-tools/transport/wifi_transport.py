"""
WiFi transport for Arduino communication over network
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger("wifi-transport")

class WiFiTransport:
    """WiFi transport using HTTP + WebSocket"""
    
    def __init__(self, host: str = "192.168.4.1", port: int = 8080):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self._connected = False
        self._ws = None

    async def connect(self):
        """Connect to WiFi Arduino"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/health")
                if resp.status_code == 200:
                    self._connected = True
                    logger.info(f"Connected to WiFi Arduino at {self.base_url}")
                else:
                    raise ConnectionError(f"Health check failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"WiFi connection failed: {e}")
            raise

    async def disconnect(self):
        """Disconnect from WiFi Arduino"""
        self._connected = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("WiFi disconnected")

    async def send_command(self, command: str, payload: dict = None) -> dict:
        """Send command via HTTP POST"""
        if not self._connected:
            raise RuntimeError("Not connected to WiFi Arduino")
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/api/tools/{command.lower()}",
                json=payload or {},
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                raise RuntimeError(f"Command failed: {resp.status_code} {resp.text}")

    async def read_line(self) -> Optional[str]:
        """Read from WebSocket stream"""
        # For WiFi, we use WebSocket for streaming
        return None

    async def write_line(self, line: str):
        """Write via WebSocket"""
        pass
