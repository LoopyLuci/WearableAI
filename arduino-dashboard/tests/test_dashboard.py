"""
Tests for Arduino Dashboard Backend, Transport, TinyML, and Log Reader
"""
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "host-tools"))

# Test basic imports
def test_imports():
    """Verify all modules can be imported"""
    from transport.serial_transport import SerialTransport
    from transport.ble_transport import BLETransport, BLETransportBridge, ble_bridge
    from transport.wifi_transport import WiFiTransport
    from tools import compile_sketch, flash_firmware, build_and_flash, call_tool, TOOLS
    assert SerialTransport is not None
    assert BLETransport is not None
    assert WiFiTransport is not None
    assert len(TOOLS) > 0

# Test transport classes
def test_serial_transport_init():
    from transport.serial_transport import SerialTransport
    t = SerialTransport(port="COM15", baudrate=921600)
    assert t.port == "COM15"
    assert t.baudrate == 921600
    assert t.serial is None

def test_ble_transport_init():
    from transport.ble_transport import BLETransport, BLETransportBridge, ble_bridge
    t = BLETransport(device_name="ARP-2040")
    assert t.device_name == "ARP-2040"
    assert t._connected is False
    assert ble_bridge is not None

def test_wifi_transport_init():
    from transport.wifi_transport import WiFiTransport
    t = WiFiTransport(host="192.168.4.1", port=8080)
    assert t.host == "192.168.4.1"
    assert t.port == 8080
    assert t.base_url == "http://192.168.4.1:8080"

# Test tools registry
def test_tools_registry():
    from tools import TOOLS, call_tool
    assert "compile" in TOOLS
    assert "flash" in TOOLS
    assert "build_and_flash" in TOOLS

# Test backend imports
def test_backend_import():
    """Test backend main module can be imported without error"""
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    import main
    assert main.app is not None
    assert main.state is not None

# Test TinyML pipeline
def test_tinyml_import():
    """Test TinyML pipeline module can be imported"""
    sys.path.insert(0, str(Path(__file__).parent.parent / "host-tools"))
    from tinyml import TinyMLPipeline, pipeline, list_models, get_model_details, generate_dummy_model, train_model, validate_model, package_model, deploy_model, get_model_status, delete_model
    assert pipeline is not None
    assert len(pipeline.models_dir.name) > 0

@pytest.mark.asyncio
async def test_tinyml_generate_dummy():
    """Test generating a dummy model"""
    from tinyml import generate_dummy_model
    result = await generate_dummy_model("kws_cnn", overwrite=True)
    assert result["ok"] is True
    assert result["model"] == "kws_cnn"
    assert Path(result["path"]).exists()

@pytest.mark.asyncio
async def test_tinyml_train_dummy():
    """Test simulated training"""
    from tinyml import train_model
    result = await train_model("kws_cnn", epochs=1)
    assert result["ok"] is True
    assert "training" in result
    assert result["training"]["status"] == "completed"

@pytest.mark.asyncio
async def test_tinyml_validate():
    """Test model validation"""
    from tinyml import validate_model
    result = await validate_model("nonexistent.tflite")
    assert result["ok"] is False

@pytest.mark.asyncio
async def test_tinyml_package():
    """Test model packaging"""
    from tinyml import generate_dummy_model, package_model
    gen = await generate_dummy_model("kws_cnn", overwrite=True)
    assert gen["ok"] is True
    pkg = await package_model(gen["path"])
    assert pkg["ok"] is True
    assert pkg["format"] == "armodel"
    assert Path(pkg["output"]).exists()

@pytest.mark.asyncio
async def test_tinyml_deploy():
    """Test model deployment"""
    from tinyml import generate_dummy_model, deploy_model
    gen = await generate_dummy_model("kws_cnn", overwrite=True)
    assert gen["ok"] is True
    dep = await deploy_model("kws_cnn")
    assert dep["ok"] is True
    assert dep["target"] == "device"

@pytest.mark.asyncio
async def test_tinyml_list_and_status():
    """Test listing models and status"""
    from tinyml import list_models, get_model_status
    listing = await list_models()
    assert "models" in listing
    assert "available_specs" in listing
    
    status = await get_model_status()
    assert "models_dir" in status
    assert "models" in status
    assert status["count"] >= 0

# Test transport classes
def test_serial_transport_init():
    from transport.serial_transport import SerialTransport
    t = SerialTransport(port="COM15", baudrate=921600)
    assert t.port == "COM15"
    assert t.baudrate == 921600
    assert t.serial is None

def test_ble_transport_init():
    from transport.ble_transport import BLETransport, BLETransportBridge, ble_bridge
    t = BLETransport(device_name="ARP-2040")
    assert t.device_name == "ARP-2040"
    assert t._connected is False
    assert ble_bridge is not None

def test_wifi_transport_init():
    from transport.wifi_transport import WiFiTransport
    t = WiFiTransport(host="192.168.4.1", port=8080)
    assert t.host == "192.168.4.1"
    assert t.port == 8080
    assert t.base_url == "http://192.168.4.1:8080"

# Test tools registry
def test_tools_registry():
    from tools import TOOLS, call_tool
    assert "compile" in TOOLS
    assert "flash" in TOOLS
    assert "build_and_flash" in TOOLS

# Test backend imports
def test_backend_import():
    """Test backend main module can be imported without error"""
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    import main
    assert main.app is not None
    assert main.state is not None

# Test log reader
def test_log_reader_import():
    from log_reader import read_boot_log, tail_live_log
    assert read_boot_log is not None
    assert tail_live_log is not None

# Test async serial transport (no real hardware)
@pytest.mark.asyncio
async def test_serial_list_ports():
    from transport.serial_transport import SerialTransport
    ports = await SerialTransport.list_ports()
    assert isinstance(ports, list)
