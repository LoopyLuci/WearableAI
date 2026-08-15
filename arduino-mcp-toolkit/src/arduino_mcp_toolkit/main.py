"""
arduino_mcp_toolkit.main — MCP server entry point
"""
import asyncio
import logging
import sys

from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Tool,
    TextContent,
    EmbeddedResource,
    LoggingLevel,
)

from arduino_mcp_toolkit.tools import register_all_tools
from arduino_mcp_toolkit.resources import register_all_resources
from arduino_mcp_toolkit.hardware import HardwareManager
from arduino_mcp_toolkit.compiler import CompilerManager
from arduino_mcp_toolkit.serial import SerialManager
from arduino_mcp_toolkit.utils import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arduino-mcp")

server = Server("arduino-mcp-toolkit")

# Global managers (initialized in main)
_hw_manager: HardwareManager | None = None
_compiler_manager: CompilerManager | None = None
_serial_manager: SerialManager | None = None


def get_hw() -> HardwareManager:
    if _hw_manager is None:
        raise RuntimeError("HardwareManager not initialized")
    return _hw_manager


def get_compiler() -> CompilerManager:
    if _compiler_manager is None:
        raise RuntimeError("CompilerManager not initialized")
    return _compiler_manager


def get_serial() -> SerialManager:
    if _serial_manager is None:
        raise RuntimeError("SerialManager not initialized")
    return _serial_manager


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return register_all_tools()


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent | EmbeddedResource]:
    """Route tool calls to their handlers."""
    from arduino_mcp_toolkit.tools import TOOL_HANDLERS

    if name not in TOOL_HANDLERS:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    handler = TOOL_HANDLERS[name]
    try:
        result = await handler(arguments)
        if isinstance(result, str):
            return [TextContent(type="text", text=result)]
        elif isinstance(result, list):
            return result
        else:
            return [TextContent(type="text", text=str(result))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"ERROR: {e}")]


@server.list_resources()
async def handle_list_resources() -> list:
    """List available MCP resources."""
    return register_all_resources()


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Serve MCP resources."""
    from arduino_mcp_toolkit.resources import RESOURCE_HANDLERS

    if uri not in RESOURCE_HANDLERS:
        raise ValueError(f"Unknown resource: {uri}")

    handler = RESOURCE_HANDLERS[uri]
    return await handler()


async def main_async():
    """Async entry point for the MCP server."""
    global _hw_manager, _compiler_manager, _serial_manager

    config = get_config()

    # Initialize managers
    _hw_manager = HardwareManager(config)
    _compiler_manager = CompilerManager(config)
    _serial_manager = SerialManager(config)

    logger.info("Arduino MCP Toolkit v1.0.0 starting...")
    logger.info(f"Config: {config.get('workspace', 'unknown')}")

    # Auto-detect hardware
    await _hw_manager.auto_detect()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="arduino-mcp-toolkit",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(
                        prompts_changed=True,
                        resources_changed=True,
                        tools_changed=True,
                    ),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="arduino-mcp",
        description="Agentic Arduino MCP Toolkit — 100-year modular embedded agent runtime"
    )
    parser.add_argument("--version", action="version", version="arduino-mcp-toolkit 1.0.0")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no hardware writes)")
    parser.add_argument("--tcp-port", type=int, default=None, help="Enable TCP transport on this port instead of stdio")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.tcp_port is not None:
            from arduino_mcp_toolkit.tcp_transport import run_tcp
            asyncio.run(run_tcp(args.tcp_port, config_path=args.config, dry_run=args.dry_run))
        else:
            asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
