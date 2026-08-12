"""
Arduino Dashboard Backend
FastAPI + WebSocket server providing:
- COM/BLE/Wi-Fi connectivity to Arduino
- Real-time telemetry streaming
- Full Arduino tool orchestration
- MCP Arduino toolkit integration
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from dataclasses import dataclass, field, asdict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "host-tools"))

def _load_transports():
    from transport.serial_transport import SerialTransport
    from transport.ble_transport import BLETransport
    from transport.wifi_transport import WiFiTransport
    return SerialTransport, BLETransport, WiFiTransport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arduino-dashboard")

app = FastAPI(title="Arduino Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== State Management =====

@dataclass
class ConnectionState:
    transport_type: str = "none"  # none, serial, ble, wifi
    port: Optional[str] = None
    connected: bool = False
    board_type: str = ""
    firmware_version: str = ""
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class TelemetryPoint:
    timestamp: str
    type: str  # heartbeat, sensor, battery, memory, agent, graph
    data: Dict[str, Any]

class DashboardState:
    def __init__(self):
        self.connection = ConnectionState()
        self.telemetry_log: list[TelemetryPoint] = []
        self.max_telemetry = 10000
        self.active_websockets: list[WebSocket] = []
        self.transport = None  # Active transport instance
        self.training_jobs: Dict[str, Dict[str, Any]] = {}
        self.training_progress: Dict[str, Dict[str, Any]] = {}

state = DashboardState()

# ===== WebSocket Connection Manager =====

async def broadcast(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    dead = []
    for ws in state.active_websockets:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        state.active_websockets.remove(ws)

async def stream_telemetry(point: TelemetryPoint):
    """Add telemetry and stream to clients"""
    state.telemetry_log.append(point)
    if len(state.telemetry_log) > state.max_telemetry:
        state.telemetry_log.pop(0)
    await broadcast({"type": "telemetry", "data": asdict(point)})

# ===== REST Endpoints =====

@app.get("/")
async def root():
    return FileResponse(Path(__file__).parent.parent / "frontend" / "index.html")

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "connected": state.connection.connected,
        "transport": state.connection.transport_type,
        "port": state.connection.port,
        "board": state.connection.board_type,
        "firmware": state.connection.firmware_version,
        "uptime": time.time()
    }

# ===== Transport Endpoints =====

@app.post("/api/connect/serial")
async def connect_serial(port: str = "COM15", baudrate: int = 921600):
    """Connect to Arduino via serial"""
    try:
        SerialTransport, _, _ = _load_transports()
        transport = SerialTransport(port=port, baudrate=baudrate)
        await transport.connect()
        state.transport = transport
        state.connection = ConnectionState(
            transport_type="serial",
            port=port,
            connected=True,
            board_type="Arduino Nano RP2040 Connect",
            firmware_version="detecting..."
        )
        # Start background telemetry reader
        asyncio.create_task(_serial_telemetry_loop(transport))
        return {"status": "connected", "port": port, "baudrate": baudrate}
    except Exception as e:
        logger.error(f"Serial connect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/connect/ble")
async def connect_ble(device_name: str = "ARP-2040"):
    """Connect to Arduino via BLE"""
    try:
        _, BLETransport, _ = _load_transports()
        transport = BLETransport(device_name=device_name)
        await transport.connect()
        state.transport = transport
        state.connection = ConnectionState(
            transport_type="ble",
            port=device_name,
            connected=True,
            board_type="Arduino Nano RP2040 Connect (BLE)",
            firmware_version="detecting..."
        )
        asyncio.create_task(_ble_telemetry_loop(transport))
        return {"status": "connected", "device": device_name}
    except Exception as e:
        logger.error(f"BLE connect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/connect/wifi")
async def connect_wifi(host: str = "192.168.4.1", port: int = 8080):
    """Connect to Arduino via Wi-Fi"""
    try:
        _, _, WiFiTransport = _load_transports()
        transport = WiFiTransport(host=host, port=port)
        await transport.connect()
        state.transport = transport
        state.connection = ConnectionState(
            transport_type="wifi",
            port=f"{host}:{port}",
            connected=True,
            board_type="Arduino Nano RP2040 Connect (WiFi)",
            firmware_version="detecting..."
        )
        asyncio.create_task(_wifi_telemetry_loop(transport))
        return {"status": "connected", "host": host, "port": port}
    except Exception as e:
        logger.error(f"WiFi connect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/disconnect")
async def disconnect():
    """Disconnect from current transport"""
    if state.transport:
        try:
            await state.transport.disconnect()
        except Exception:
            pass
    state.transport = None
    state.connection = ConnectionState()
    return {"status": "disconnected"}

@app.get("/api/connection")
async def get_connection():
    """Get current connection status"""
    return asdict(state.connection)

# ===== Tool Endpoints =====

@app.post("/api/tools/compile")
async def tool_compile(sketch_path: str, fqbn: str = "arduino:mbed_nano:nanorp2040connect"):
    """Compile an Arduino sketch"""
    try:
        from tools import compile_sketch
        result = await compile_sketch(sketch_path, fqbn)
        return result
    except Exception as e:
        logger.error(f"Compile failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/flash")
async def tool_flash(firmware_path: str, port: str = "COM15"):
    """Flash firmware to Arduino"""
    try:
        from tools import flash_firmware
        result = await flash_firmware(firmware_path, port)
        return result
    except Exception as e:
        logger.error(f"Flash failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/build_and_flash")
async def tool_build_and_flash(sketch_path: str, port: str = "COM15"):
    """Compile and flash in one atomic operation"""
    try:
        from tools import build_and_flash
        result = await build_and_flash(sketch_path, port)
        return result
    except Exception as e:
        logger.error(f"Build and flash failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/self_test")
async def tool_self_test():
    """Run comprehensive self-test on connected board"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("SELF_TEST")
        return result
    except Exception as e:
        logger.error(f"Self-test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/memory_report")
async def tool_memory_report():
    """Get detailed memory report"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("MEMORY_REPORT")
        return result
    except Exception as e:
        logger.error(f"Memory report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/battery_status")
async def tool_battery_status():
    """Get battery status"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("BATTERY_STATUS")
        return result
    except Exception as e:
        logger.error(f"Battery status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/crypto_status")
async def tool_crypto_status():
    """Get crypto subsystem status"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("CRYPTO_STATUS")
        return result
    except Exception as e:
        logger.error(f"Crypto status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/agent_status")
async def tool_agent_status():
    """Get agent status"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("AGENT_STATUS")
        return result
    except Exception as e:
        logger.error(f"Agent status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/ota_update")
async def tool_ota_update(firmware_url: str):
    """Perform atomic OTA update"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("OTA_UPDATE", {"url": firmware_url})
        return result
    except Exception as e:
        logger.error(f"OTA update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/rollback")
async def tool_rollback():
    """Rollback to previous firmware version"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("ROLLBACK")
        return result
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/load_model")
async def tool_load_model():
    """Send LOAD_MODEL to device via active transport"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("LOAD_MODEL")
        return result
    except Exception as e:
        logger.error(f"LOAD_MODEL failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/inference_stream")
async def tool_inference_stream(prompt: str = Form(...)):
    """Stream inference result for prompt via active transport"""
    try:
        if not state.transport or not state.connection.connected:
            raise HTTPException(status_code=400, detail="Not connected")
        result = await state.transport.send_command("INFER", {"data": prompt})
        return result
    except Exception as e:
        logger.error(f"Inference stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools/list")
async def tool_list():
    """List all available tools"""
    return {
        "tools": [
            {"name": "compile", "description": "Compile Arduino sketch", "category": "build"},
            {"name": "flash", "description": "Flash firmware to board", "category": "build"},
            {"name": "build_and_flash", "description": "Compile and flash atomically", "category": "build"},
            {"name": "self_test", "description": "Run self-test suite", "category": "diagnostics"},
            {"name": "memory_report", "description": "Get SRAM/stack report", "category": "diagnostics"},
            {"name": "battery_status", "description": "Get battery info", "category": "power"},
            {"name": "crypto_status", "description": "Get ATECC608A status", "category": "security"},
            {"name": "agent_status", "description": "Get agent status", "category": "agents"},
            {"name": "ota_update", "description": "Atomic OTA update", "category": "deployment"},
            {"name": "rollback", "description": "Rollback firmware", "category": "deployment"},
        ]
    }

# ===== TinyML Endpoints =====

@app.get("/api/models/status")
async def models_status():
    """Get TinyML model status"""
    try:
        from tinyml import get_model_status
        return await get_model_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/list")
async def models_list():
    """List all model artifacts"""
    try:
        from tinyml import list_models
        return await list_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/{model_name}")
async def model_details(model_name: str, path: Optional[str] = None):
    """Get detailed info about a specific model by name or file path"""
    try:
        from tinyml import TinyMLPipeline
        pipeline = TinyMLPipeline()
        
        # If path query param is provided, resolve actual model name from file
        lookup_name = model_name
        if path:
            lookup_name = Path(path).stem.split("_")[0]
        
        result = await pipeline.get_model_details(lookup_name)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/{model_name}/generate")
async def model_generate(model_name: str, overwrite: bool = False):
    """Generate a dummy model for testing"""
    try:
        from tinyml import generate_dummy_model
        return await generate_dummy_model(model_name, overwrite=overwrite)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/{model_name}/train")
async def model_train(model_name: str, epochs: Optional[int] = None):
    """Train/simulate training a model"""
    try:
        from tinyml import train_model
        return await train_model(model_name, epochs=epochs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/{model_name}/train")
async def model_train_get(model_name: str, epochs: Optional[int] = None):
    """Train/simulate training a model via GET for browser forms"""
    try:
        from tinyml import train_model
        return await train_model(model_name, epochs=epochs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/{model_name}/train/stream")
async def model_train_stream(model_name: str, epochs: Optional[int] = None):
    """Train model with WebSocket progress streaming"""
    try:
        job_id = f"{model_name}_{int(time.time())}"
        if job_id in state.training_jobs:
            job_id = f"{model_name}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        
        state.training_jobs[job_id] = {"model": model_name, "epochs": epochs, "status": "running"}
        state.training_progress[job_id] = {"progress": 0, "epoch": 0, "total_epochs": epochs or 1, "loss": None, "accuracy": None}
        
        asyncio.create_task(_run_training_job(job_id, model_name, epochs))
        return {"ok": True, "job_id": job_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/train/{job_id}/progress")
async def model_train_progress(job_id: str):
    """Get progress of a training job"""
    if job_id not in state.training_progress:
        raise HTTPException(status_code=404, detail="Job not found")
    return state.training_progress[job_id]

async def _run_training_job(job_id: str, model_name: str, epochs: Optional[int]):
    """Background task to run training with WebSocket streaming"""
    try:
        from tinyml import train_model
        
        def progress_callback(data: Dict[str, Any]):
            state.training_progress[job_id].update({
                "progress": int((data.get("epoch", 0) / max(data.get("total_epochs", 1), 1)) * 100),
                "epoch": data.get("epoch"),
                "total_epochs": data.get("total_epochs"),
                "loss": data.get("loss"),
                "accuracy": data.get("accuracy"),
            })
            asyncio.create_task(broadcast({
                "type": "training_progress",
                "job_id": job_id,
                "data": state.training_progress[job_id]
            }))
        
        result = await train_model(model_name, epochs=epochs, progress_callback=progress_callback)
        state.training_jobs[job_id]["status"] = "completed" if result.get("ok") else "failed"
        state.training_jobs[job_id]["result"] = result
        
        asyncio.create_task(broadcast({
            "type": "training_complete",
            "job_id": job_id,
            "ok": result.get("ok"),
            "data": result
        }))
    except Exception as e:
        state.training_jobs[job_id]["status"] = "error"
        state.training_jobs[job_id]["error"] = str(e)
        asyncio.create_task(broadcast({
            "type": "training_error",
            "job_id": job_id,
            "error": str(e)
        }))

@app.post("/api/models/validate")
async def models_validate(model_path: str):
    """Validate a TFLite/ONNX model"""
    try:
        from tinyml import validate_model
        return await validate_model(model_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/package")
async def models_package(model_path: str, output_name: Optional[str] = None, sign: bool = False):
    """Package a model as .armodel"""
    try:
        from tinyml import package_model
        return await package_model(model_path, output_name, sign=sign)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/{model_name}/deploy")
async def model_deploy(model_name: str, target: str = "device"):
    """Deploy a model to device"""
    try:
        from tinyml import deploy_model
        return await deploy_model(model_name, target=target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/models/{model_name}")
async def model_delete(model_name: str, filename: str):
    """Delete a model artifact"""
    try:
        from tinyml import delete_model
        return await delete_model(model_name, filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Telemetry Endpoints =====

@app.get("/api/telemetry/history")
async def get_telemetry_history(limit: int = 1000, type_filter: Optional[str] = None):
    """Get telemetry history"""
    data = state.telemetry_log
    if type_filter:
        data = [t for t in data if t.type == type_filter]
    return {
        "points": [asdict(t) for t in data[-limit:]],
        "count": len(data),
        "oldest": data[0].timestamp if data else None,
        "newest": data[-1].timestamp if data else None
    }

@app.get("/api/telemetry/live")
async def get_latest_telemetry():
    """Get latest telemetry point"""
    if state.telemetry_log:
        return asdict(state.telemetry_log[-1])
    return {"message": "No telemetry yet"}

# ===== WebSocket =====

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.active_websockets.append(websocket)
    logger.info(f"WebSocket connected, total: {len(state.active_websockets)}")
    try:
        # Send current state immediately
        await websocket.send_json({
            "type": "connection",
            "data": asdict(state.connection)
        })
        # Send recent telemetry
        if state.telemetry_log:
            for point in state.telemetry_log[-50:]:
                await websocket.send_json({"type": "telemetry", "data": asdict(point)})
        
        # Handle incoming commands
        while True:
            data = await websocket.receive_json()
            await handle_ws_command(websocket, data)
    except WebSocketDisconnect:
        state.active_websockets.remove(websocket)
        logger.info(f"WebSocket disconnected, total: {len(state.active_websockets)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in state.active_websockets:
            state.active_websockets.remove(websocket)

async def handle_ws_command(websocket: WebSocket, command: Dict[str, Any]):
    """Handle WebSocket commands from frontend"""
    cmd_type = command.get("type")
    payload = command.get("payload", {})
    
    try:
        if cmd_type == "connect_serial":
            result = await connect_serial(payload.get("port", "COM15"), payload.get("baudrate", 921600))
            await websocket.send_json({"type": "connection", "data": asdict(state.connection)})
        
        elif cmd_type == "connect_ble":
            result = await connect_ble(payload.get("device_name", "ARP-2040"))
            await websocket.send_json({"type": "connection", "data": asdict(state.connection)})
        
        elif cmd_type == "connect_wifi":
            result = await connect_wifi(payload.get("host", "192.168.4.1"), payload.get("port", 8080))
            await websocket.send_json({"type": "connection", "data": asdict(state.connection)})
        
        elif cmd_type == "disconnect":
            await disconnect()
            await websocket.send_json({"type": "connection", "data": asdict(state.connection)})
        
        elif cmd_type == "self_test":
            result = await tool_self_test()
            await websocket.send_json({"type": "tool_result", "tool": "self_test", "data": result})
        
        elif cmd_type == "memory_report":
            result = await tool_memory_report()
            await websocket.send_json({"type": "tool_result", "tool": "memory_report", "data": result})
        
        elif cmd_type == "battery_status":
            result = await tool_battery_status()
            await websocket.send_json({"type": "tool_result", "tool": "battery_status", "data": result})
        
        elif cmd_type == "crypto_status":
            result = await tool_crypto_status()
            await websocket.send_json({"type": "tool_result", "tool": "crypto_status", "data": result})
        
        elif cmd_type == "agent_status":
            result = await tool_agent_status()
            await websocket.send_json({"type": "tool_result", "tool": "agent_status", "data": result})
        
        elif cmd_type == "ota_update":
            result = await tool_ota_update(payload.get("firmware_url", ""))
            await websocket.send_json({"type": "tool_result", "tool": "ota_update", "data": result})
        
        elif cmd_type == "rollback":
            result = await tool_rollback()
            await websocket.send_json({"type": "tool_result", "tool": "rollback", "data": result})
        
        elif cmd_type == "serial_write":
            if state.transport:
                await state.transport.send_command("WRITE", {"data": payload.get("data", "")})
                await websocket.send_json({"type": "ack", "command": "serial_write"})
        
        elif cmd_type == "get_telemetry_history":
            result = await get_telemetry_history(
                payload.get("limit", 1000),
                payload.get("type_filter")
            )
            await websocket.send_json({"type": "telemetry_history", "data": result})
        
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown command: {cmd_type}"
            })
    except Exception as e:
        logger.error(f"Command handler error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e),
            "command": cmd_type
        })

# ===== Background Telemetry Loops =====

async def _serial_telemetry_loop(transport):
    """Read telemetry from serial transport"""
    try:
        while state.connection.transport_type == "serial" and state.connection.connected:
            line = await transport.read_line()
            if line:
                await _parse_telemetry_line(line)
            await asyncio.sleep(0.01)
    except Exception as e:
        logger.error(f"Serial telemetry loop error: {e}")
        await broadcast({"type": "error", "message": f"Serial error: {e}"})

async def _ble_telemetry_loop(transport):
    """Read telemetry from BLE transport"""
    try:
        while state.connection.transport_type == "ble" and state.connection.connected:
            line = await transport.read_line()
            if line:
                await _parse_telemetry_line(line)
            await asyncio.sleep(0.01)
    except Exception as e:
        logger.error(f"BLE telemetry loop error: {e}")
        await broadcast({"type": "error", "message": f"BLE error: {e}"})

async def _wifi_telemetry_loop(transport):
    """Read telemetry from WiFi transport"""
    try:
        while state.connection.transport_type == "wifi" and state.connection.connected:
            line = await transport.read_line()
            if line:
                await _parse_telemetry_line(line)
            await asyncio.sleep(0.01)
    except Exception as e:
        logger.error(f"WiFi telemetry loop error: {e}")
        await broadcast({"type": "error", "message": f"WiFi error: {e}"})

async def _parse_telemetry_line(line: str):
    """Parse telemetry line from board and create telemetry point"""
    try:
        line = line.strip()
        if not line:
            return
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if line.startswith("[HEARTBEAT]"):
            # Parse heartbeat: "[HEARTBEAT] Uptime: 123 s"
            parts = line.split(":")
            uptime = parts[-1].strip().replace(" s", "") if len(parts) > 1 else "0"
            point = TelemetryPoint(
                timestamp=timestamp,
                type="heartbeat",
                data={"uptime_s": int(uptime) if uptime.isdigit() else 0}
            )
        elif line.startswith("[RESULT]"):
            point = TelemetryPoint(
                timestamp=timestamp,
                type="test_result",
                data={"message": line}
            )
        elif line.startswith("[AGENTS]"):
            point = TelemetryPoint(
                timestamp=timestamp,
                type="agent",
                data={"message": line}
            )
        elif line.startswith("[PASS]") or line.startswith("[FAIL]"):
            point = TelemetryPoint(
                timestamp=timestamp,
                type="test",
                data={"result": line}
            )
        elif line.startswith("[INFO]") or line.startswith("[WARN]"):
            point = TelemetryPoint(
                timestamp=timestamp,
                type="log",
                data={"message": line}
            )
        elif line.startswith("[BOOT]") or line.startswith("[SYSTEM]"):
            point = TelemetryPoint(
                timestamp=timestamp,
                type="system",
                data={"message": line}
            )
        else:
            point = TelemetryPoint(
                timestamp=timestamp,
                type="unknown",
                data={"message": line}
            )
        
        await stream_telemetry(point)
    except Exception as e:
        logger.error(f"Parse error: {e}, line: {line}")

# ===== Static Files =====

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# ===== Entry Point =====

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
