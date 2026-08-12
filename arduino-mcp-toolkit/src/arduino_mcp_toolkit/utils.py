"""
arduino_mcp_toolkit.utils — Shared utilities, config loading
"""
from __future__ import annotations
import os
import logging
from typing import Any
import yaml

logger = logging.getLogger("arduino-mcp")

_config_cache: dict | None = None


def get_config(config_path: str | None = None) -> dict:
    """Load configuration from YAML file with defaults."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_path = config_path or os.environ.get("ARDUINO_MCP_CONFIG") or _find_config()

    defaults = {
        "workspace": os.getcwd(),
        "dry_run": False,
        "default_baud": 115200,
        "default_fqbn": "rp2040:rp2040:nano_rp2040_connect",
        "platformio_path": "pio",
        "arduino_cli_path": "arduino-cli",
        "watchdog_timeout_s": 30,
        "max_serial_ports": 10,
        "log_level": "INFO",
    }

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            defaults.update(user_config)
            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config {config_path}: {e}")

    _config_cache = defaults
    return defaults


def _find_config() -> str | None:
    """Search for config file in standard locations."""
    search_paths = [
        os.path.join(os.getcwd(), "arduino-mcp-config.yaml"),
        os.path.join(os.path.expanduser("~"), ".arduino-mcp", "config.yaml"),
        os.path.join(os.path.expanduser("~"), ".config", "arduino-mcp", "config.yaml"),
        "/etc/arduino-mcp/config.yaml",
    ]
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None


def generate_config(output_path: str = "arduino-mcp-config.yaml"):
    """Generate a default config file."""
    defaults = {
        "workspace": os.getcwd(),
        "dry_run": False,
        "default_baud": 115200,
        "default_fqbn": "rp2040:rp2040:nano_rp2040_connect",
        "platformio_path": "pio",
        "arduino_cli_path": "arduino-cli",
        "watchdog_timeout_s": 30,
        "max_serial_ports": 10,
        "log_level": "INFO",
    }
    with open(output_path, "w") as f:
        yaml.dump(defaults, f, default_flow_style=False)
    logger.info(f"Generated config at {output_path}")
    return output_path
