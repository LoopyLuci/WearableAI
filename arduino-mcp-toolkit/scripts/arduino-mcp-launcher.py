#!/usr/bin/env python3
"""Launcher for arduino-mcp-toolkit with correct PYTHONPATH."""
import os
import sys

# Ensure the source tree is importable
src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if src not in sys.path:
    sys.path.insert(0, src)

from arduino_mcp_toolkit.main import cli_main

if __name__ == "__main__":
    cli_main()
