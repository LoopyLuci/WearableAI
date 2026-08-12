"""
arduino_mcp_toolkit.resources — MCP resource definitions
"""
from __future__ import annotations
import logging
import os
from typing import Any, Callable, Awaitable

logger = logging.getLogger("arduino-mcp")

RESOURCE_HANDLERS: dict[str, Callable[[], Awaitable[str]]] = {}


def resource(uri: str):
    """Decorator to register a resource handler."""
    def decorator(fn: Callable[[], Awaitable[str]]):
        RESOURCE_HANDLERS[uri] = fn
        return fn
    return decorator


RESOURCE_SPECS = [
    {"uri": "arduino://boards/available",     "name": "Available Boards",        "description": "List of all supported Arduino boards", "mimeType": "application/json"},
    {"uri": "arduino://boards/detected",      "name": "Detected Boards",         "description": "Currently connected boards", "mimeType": "application/json"},
    {"uri": "arduino://docs/setup",           "name": "Setup Guide",             "description": "Step-by-step setup instructions", "mimeType": "text/markdown"},
    {"uri": "arduino://docs/hal-spec",        "name": "HAL Specification",       "description": "Hardware Abstraction Layer interface contracts", "mimeType": "text/markdown"},
    {"uri": "arduino://docs/protocol-spec",   "name": "Protocol Specification",  "description": "Device ↔ server wire protocol", "mimeType": "text/markdown"},
    {"uri": "arduino://docs/blueprint",       "name": "Design Blueprint",        "description": "Full hardware-grounded design blueprint", "mimeType": "text/markdown"},
    {"uri": "arduino://examples/ble_peripheral", "name": "BLE Peripheral Example", "description": "Minimal BLE peripheral sketch", "mimeType": "text/x-c++src"},
    {"uri": "arduino://examples/wifi_scan",   "name": "Wi-Fi Scan Example",      "description": "Scan and connect to Wi-Fi networks", "mimeType": "text/x-c++src"},
    {"uri": "arduino://examples/tinyml_kws",  "name": "TinyML KWS Example",     "description": "Keyword spotting with TFLite Micro", "mimeType": "text/x-c++src"},
    {"uri": "arduino://examples/imu_mlc",     "name": "IMU MLC Example",         "description": "LSM6DSOX Machine Learning Core gesture detection", "mimeType": "text/x-c++src"},
    {"uri": "arduino://examples/control_graph","name": "Control Graph Example",   "description": "Self-modifying pipeline with bytecode interpreter", "mimeType": "text/x-c++src"},
    {"uri": "arduino://tools/armodel_compiler", "name": "ARModel Compiler",       "description": "Host-side model build pipeline", "mimeType": "application/octet-stream"},
    {"uri": "arduino://tools/graph_compiler", "name": "Graph Compiler",          "description": "Control graph binary compiler", "mimeType": "application/octet-stream"},
    {"uri": "arduino://schemas/control_graph","name": "Control Graph Schema",    "description": "JSON schema for control graph definitions", "mimeType": "application/json"},
    {"uri": "arduino://schemas/armodel",      "name": "ARModel Schema",          "description": "Binary format specification for .armodel files", "mimeType": "application/json"},
]


def register_all_resources() -> list[dict]:
    """Return all resource specs and register handlers."""
    from arduino_mcp_toolkit.resources.handlers import register_resource_handlers
    register_resource_handlers()
    return RESOURCE_SPECS
