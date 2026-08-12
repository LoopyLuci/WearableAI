"""
arduino_mcp_toolkit.hardware — Hardware detection, board info, pin maps
"""
from __future__ import annotations
import asyncio
import logging
import serial.tools.list_ports
from typing import Any
from dataclasses import dataclass

from arduino_mcp_toolkit.utils import get_config

logger = logging.getLogger("arduino-mcp")

KNOWN_BOARDS = {
    # VID:PID -> board info
    "0x2341:0x0043": {"board": "arduino:avr:uno",    "mcu": "ATmega328P", "flash_kb": 32, "sram_kb": 2, "clock_mhz": 16},
    "0x2341:0x0001": {"board": "arduino:avr:uno",    "mcu": "ATmega328P", "flash_kb": 32, "sram_kb": 2, "clock_mhz": 16},
    "0x2341:0x005E": {"board": "rp2040:rp2040:nano_rp2040_connect", "mcu": "RP2040", "flash_kb": 16384, "sram_kb": 264, "clock_mhz": 133},
    "0x2E8A:0x000A": {"board": "rp2040:rp2040:nano_rp2040_connect", "mcu": "RP2040", "flash_kb": 16384, "sram_kb": 264, "clock_mhz": 133},
    "0x239A:0x8020": {"board": "rp2040:rp2040:pico", "mcu": "RP2040", "flash_kb": 2048, "sram_kb": 264, "clock_mhz": 133},
    "0x10C4:0xEA60": {"board": "esp32:esp32:generic", "mcu": "ESP32", "flash_kb": 4096, "sram_kb": 520, "clock_mhz": 240},
    "0x1A86:0x7523": {"board": "esp32:esp32:generic", "mcu": "ESP32", "flash_kb": 4096, "sram_kb": 520, "clock_mhz": 240},
}

PIN_MAPS = {
    "nano_rp2040_connect": [
        {"name": "D0",  "type": "GPIO",   "description": "UART0 RX / GPIO0"},
        {"name": "D1",  "type": "GPIO",   "description": "UART0 TX / GPIO1"},
        {"name": "D2",  "type": "GPIO",   "description": "GPIO2 / I2C SDA"},
        {"name": "D3",  "type": "GPIO",   "description": "GPIO3 / I2C SCL"},
        {"name": "D4",  "type": "GPIO",   "description": "GPIO4"},
        {"name": "D5",  "type": "PWM",    "description": "GPIO5 / PWM"},
        {"name": "D6",  "type": "PWM",    "description": "GPIO6 / PWM"},
        {"name": "D7",  "type": "GPIO",   "description": "GPIO7"},
        {"name": "D8",  "type": "GPIO",   "description": "GPIO8"},
        {"name": "D9",  "type": "PWM",    "description": "GPIO9 / PWM"},
        {"name": "D10", "type": "PWM",    "description": "GPIO10 / PWM / SPI SS"},
        {"name": "D11", "type": "PWM",    "description": "GPIO11 / PWM / SPI MOSI"},
        {"name": "D12", "type": "GPIO",   "description": "GPIO12 / SPI MISO"},
        {"name": "D13", "type": "GPIO",   "description": "GPIO13 / SPI SCK / LED"},
        {"name": "A0",  "type": "ADC",    "description": "GPIO26 / ADC0"},
        {"name": "A1",  "type": "ADC",    "description": "GPIO27 / ADC1"},
        {"name": "A2",  "type": "ADC",    "description": "GPIO28 / ADC2"},
        {"name": "A3",  "type": "ADC",    "description": "GPIO29 / ADC3"},
        {"name": "SDA", "type": "I2C",    "description": "GPIO2 / I2C SDA (shared)"},
        {"name": "SCL", "type": "I2C",    "description": "GPIO3 / I2C SCL (shared)"},
        {"name": "MOSI","type": "SPI",    "description": "GPIO11 / SPI MOSI"},
        {"name": "MISO","type": "SPI",    "description": "GPIO12 / SPI MISO"},
        {"name": "SCK", "type": "SPI",    "description": "GPIO13 / SPI SCK"},
        {"name": "RX",  "type": "UART",   "description": "GPIO1 / UART0 RX (NINA reserved)"},
        {"name": "TX",  "type": "UART",   "description": "GPIO0 / UART0 TX (NINA reserved)"},
    ],
    "uno": [
        {"name": "D0",  "type": "GPIO",  "description": "UART0 RX"},
        {"name": "D1",  "type": "GPIO",  "description": "UART0 TX"},
        {"name": "D2",  "type": "GPIO",  "description": "External interrupt"},
        {"name": "D3",  "type": "PWM",   "description": "PWM (Timer2)"},
        {"name": "D4",  "type": "GPIO",  "description": "Built-in LED"},
        {"name": "D5",  "type": "PWM",   "description": "PWM (Timer0)"},
        {"name": "D6",  "type": "PWM",   "description": "PWM (Timer0)"},
        {"name": "D7",  "type": "GPIO",  "description": "Digital I/O"},
        {"name": "D8",  "type": "GPIO",  "description": "Digital I/O"},
        {"name": "D9",  "type": "PWM",   "description": "PWM (Timer1)"},
        {"name": "D10", "type": "PWM",   "description": "PWM (Timer1) / SPI SS"},
        {"name": "D11", "type": "PWM",   "description": "PWM (Timer2) / SPI MOSI"},
        {"name": "D12", "type": "GPIO",  "description": "SPI MISO"},
        {"name": "D13", "type": "GPIO",  "description": "SPI SCK / Built-in LED"},
        {"name": "A0",  "type": "ADC",   "description": "ADC0"},
        {"name": "A1",  "type": "ADC",   "description": "ADC1"},
        {"name": "A2",  "type": "ADC",   "description": "ADC2"},
        {"name": "A3",  "type": "ADC",   "description": "ADC3"},
        {"name": "A4",  "type": "I2C",   "description": "I2C SDA / ADC4"},
        {"name": "A5",  "type": "I2C",   "description": "I2C SCL / ADC5"},
    ],
}


@dataclass
class BoardInfo:
    port: str
    board_type: str
    fqbn: str
    mcu: str
    flash_kb: int
    sram_kb: int
    clock_mhz: int
    vid: int
    pid: int
    firmware_version: str = "Unknown"
    sensors: list[str] = None
    radio: list[str] = None
    crypto: list[str] = None

    def __post_init__(self):
        if self.sensors is None:
            self.sensors = []
        if self.radio is None:
            self.radio = []
        if self.crypto is None:
            self.crypto = []


class HardwareManager:
    """Singleton hardware detection and info manager."""

    _instance: HardwareManager | None = None

    def __init__(self, config: dict):
        self._config = config
        self._boards: list[BoardInfo] = []

    @classmethod
    def get_instance(cls) -> HardwareManager:
        if cls._instance is None:
            config = get_config()
            cls._instance = cls(config)
        return cls._instance

    async def auto_detect(self) -> list[BoardInfo]:
        """Auto-detect all connected Arduino boards."""
        await asyncio.sleep(0)  # Allow async context
        ports = serial.tools.list_ports.comports()
        boards = []
        for port in ports:
            vid_pid = f"0x{port.vid:04X}:0x{port.pid:04X}" if port.vid and port.pid else None
            info = KNOWN_BOARDS.get(vid_pid)
            if info:
                bi = BoardInfo(
                    port=port.device,
                    board_type=info["board"],
                    fqbn=info["board"],
                    mcu=info["mcu"],
                    flash_kb=info["flash_kb"],
                    sram_kb=info["sram_kb"],
                    clock_mhz=info["clock_mhz"],
                    vid=port.vid or 0,
                    pid=port.pid or 0,
                )
                # Add sensors/radio based on board
                if "rp2040" in info["board"]:
                    bi.sensors = ["LSM6DSOX (IMU)", "MP34DT06J (Mic)"]
                    bi.radio = ["NINA-W102 (Wi-Fi + BLE)"]
                    bi.crypto = ["ATECC608A"]
                boards.append(bi)
        self._boards = boards
        logger.info(f"Detected {len(boards)} Arduino boards")
        return boards

    async def detect_boards(self) -> list[dict]:
        boards = await self.auto_detect()
        return [
            {
                "port": b.port,
                "board_type": b.board_type,
                "fqbn": b.fqbn,
                "mcu": b.mcu,
                "vid": b.vid,
                "pid": b.pid,
            }
            for b in boards
        ]

    async def get_board_info(self, port: str = None, timeout_ms: int = 5000) -> dict:
        boards = await self.auto_detect()
        if port:
            for b in boards:
                if b.port == port:
                    return self._board_info_to_dict(b)
        if boards:
            return self._board_info_to_dict(boards[0])
        return {"error": "No boards detected"}

    def _board_info_to_dict(self, b: BoardInfo) -> dict:
        return {
            "board_type": b.board_type,
            "mcu": b.mcu,
            "clock_mhz": b.clock_mhz,
            "flash_kb": b.flash_kb,
            "sram_kb": b.sram_kb,
            "digital_pins": "varies",
            "analog_pins": "varies",
            "sensors": b.sensors,
            "radio": b.radio,
            "crypto": b.crypto,
            "firmware_version": b.firmware_version,
        }

    def get_pin_map(self, board: str = None) -> list[dict]:
        if board:
            board_key = board.lower()
            for key, pins in PIN_MAPS.items():
                if key in board_key:
                    return pins
        if self._boards:
            btype = self._boards[0].board_type.lower()
            for key, pins in PIN_MAPS.items():
                if key in btype:
                    return pins
        return PIN_MAPS.get("nano_rp2040_connect", [])
