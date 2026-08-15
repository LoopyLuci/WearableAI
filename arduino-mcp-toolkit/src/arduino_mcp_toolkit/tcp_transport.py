"""
arduino_mcp_toolkit.tcp_transport — TCP server transport for the Arduino MCP toolkit
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from arduino_mcp_toolkit.main import server
from arduino_mcp_toolkit.tools import register_all_tools
from arduino_mcp_toolkit.resources import register_all_resources
from arduino_mcp_toolkit.hardware import HardwareManager
from arduino_mcp_toolkit.compiler import CompilerManager
from arduino_mcp_toolkit.serial import SerialManager
from arduino_mcp_toolkit.utils import get_config

logger = logging.getLogger("arduino-mcp")


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr = writer.get_extra_info("peername")
    logger.info("MCP TCP client connected: %s", addr)
    try:
        buffer = ""
        while not reader.at_eof():
            data = await reader.read(4096)
            if not data:
                break
            buffer += data.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                response = await _process_line(line)
                if response is not None:
                    writer.write((json.dumps(response, default=str) + "\n").encode("utf-8"))
                    await writer.drain()
    except Exception as exc:
        logger.error("TCP client error: %s", exc, exc_info=True)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
    logger.info("MCP TCP client disconnected: %s", addr)


async def _process_line(line: str) -> Any:
    try:
        request = json.loads(line)
    except json.JSONDecodeError as exc:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": f"Parse error: {exc}"},
        }

    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "arduino-mcp-toolkit", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        try:
            from arduino_mcp_toolkit.tools import TOOL_SPECS
            tools = TOOL_SPECS
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
        except Exception as exc:
            logger.error("tools/list failed: %s", exc, exc_info=True)
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}

    if method == "tools/call":
        tool_calls = params.get("tool_calls", [])
        results = []
        for call in tool_calls:
            name = call.get("name")
            arguments = call.get("arguments", {})
            try:
                from arduino_mcp_toolkit.tools import TOOL_HANDLERS
                handler = TOOL_HANDLERS[name]
                result = await handler(arguments)
                if isinstance(result, str):
                    content = [{"type": "text", "text": result}]
                elif isinstance(result, list):
                    content = result
                else:
                    content = [{"type": "text", "text": str(result)}]
                results.append({"tool_call_id": call.get("id"), "result": {"content": content, "isError": False}})
            except Exception as exc:
                logger.error("Tool %s failed: %s", name, exc, exc_info=True)
                results.append({
                    "tool_call_id": call.get("id"),
                    "result": {"content": [{"type": "text", "text": f"ERROR: {exc}"}], "isError": True},
                })
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tool_results": results}}

    if method == "resources/list":
        resources = register_all_resources()
        return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": resources}}

    if method == "resources/read":
        uri = params.get("uri")
        if not uri:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Missing uri"}}
        try:
            from arduino_mcp_toolkit.resources import RESOURCE_HANDLERS
            handler = RESOURCE_HANDLERS[uri]
            content = await handler()
            return {"jsonrpc": "2.0", "id": request_id, "result": {"contents": [{"uri": uri, "text": content}]}}
        except KeyError:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown resource: {uri}"}}

    if method == "shutdown":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


async def run_tcp(port: int, config_path: str | None = None, dry_run: bool = False) -> None:
    """
    Start the Arduino MCP Toolkit on a TCP port.
    """
    register_all_tools()
    register_all_resources()

    # Initialize managers with config
    from arduino_mcp_toolkit.utils import get_config
    config = get_config(config_path)
    HardwareManager(config)
    CompilerManager(config)
    SerialManager(config)

    logger.info("Arduino MCP Toolkit v1.0.0 starting TCP server on port %s ...", port)
    server_instance = await asyncio.start_server(_handle_client, host="127.0.0.1", port=port)
    addr = server_instance.sockets[0].getsockname()
    logger.info("MCP server listening on tcp://%s", addr)
    async with server_instance:
        await server_instance.serve_forever()
