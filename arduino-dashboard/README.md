# Arduino Dashboard

Full Arduino dashboard with COM/BLE/Wi-Fi connectivity, all Arduino tools, telemetry streaming, and visualization.

## Quick Start

```bash
# Install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install fastapi uvicorn websockets httpx pyserial

# Run tests
python -m pytest tests/ -v

# Start dashboard
python scripts\build_runner.py dashboard
```

Open http://localhost:8080

## Features

- COM/BLE/Wi-Fi connectivity
- Real-time telemetry streaming
- All Arduino tools: compile, flash, self-test, memory report, battery, crypto, OTA, rollback
- Live serial monitor with DUMP command
- TinyML model management
- Linear-style dark UI
- WebSocket real-time updates
- Chart.js visualizations

## Transport Support

- **Serial**: USB CDC with 921600 baud
- **BLE**: Web Bluetooth bridge
- **WiFi**: HTTP/WebSocket to Arduino AP

## Scripts

```bash
# Build only
python scripts\build_runner.py build

# Flash
python scripts\build_runner.py flash --port COM15

# Build and flash
python scripts\build_runner.py build-flash --port COM15

# Run all tests
python scripts\build_runner.py test

# Lint
python scripts\build_runner.py lint

# Dashboard
python scripts\build_runner.py dashboard
```

## Architecture

```
arduino-dashboard/
  backend/main.py          # FastAPI + WebSocket server
  host-tools/
    transport/             # Serial/BLE/WiFi transports
    tools.py               # arduino-cli wrappers
    tinyml.py              # TinyML pipeline
    log_reader.py          # Buffered log reader
  frontend/index.html      # Single-page dashboard UI
  tests/                   # Pytest suite
  scripts/build_runner.py  # Windows build runner
```
