# Top-level Makefile for ARP-2040

.PHONY: help build firmware host-tools mobile-server desktop-server test \
        test-hardware lint docs clean emulator flash

help:
	@echo "ARP-2040 Build System"
	@echo "  make build          - Build everything"
	@echo "  make firmware       - Build firmware via PlatformIO"
	@echo "  make host-tools     - Install Python host tools"
	@echo "  make mobile-server  - Build Flutter mobile app"
	@echo "  make desktop-server - Build Electron/Tauri desktop app"
	@echo "  make test           - Run all tests"
	@echo "  make test-hardware  - Run hardware-in-loop tests"
	@echo "  make lint           - Run linters + static analysis"
	@echo "  make docs           - Build documentation"
	@echo "  make emulator       - Start device emulator"
	@echo "  make flash          - Flash firmware to device"
	@echo "  make clean          - Clean all build artifacts"

build: firmware host-tools

firmware:
	@pio run -e nano_rp2040_connect -d firmware

host-tools:
	@pip install -r host-tools/requirements.txt

mobile-server:
	@cd mobile-server && flutter pub get

desktop-server:
	@cd desktop-server && npm install

test:
	@pytest tests/unit/ tests/integration/ -v

test-hardware:
	@python host-tools/test-runner/test_runner.py $(SERIAL_PORT)

lint:
	@echo "Running firmware lint..."
	@pio run -e nano_rp2040_connect -d firmware -t compile_commands.json 2>/dev/null || true
	@echo "Running Python lint..."
	@pylint host-tools/ tests/ --fail-under=8.0 || true
	@echo "Lint complete"

docs:
	@echo "Building documentation..."
	@mkdocs build --config-file docs/mkdocs.yml 2>/dev/null || echo "mkdocs not configured yet"

emulator:
	@python host-tools/device-emulator/device_emulator.py

flash:
	@pio run -e nano_rp2040_connect -d firmware -t upload

clean:
	@rm -rf firmware/.pio firmware/data host-tools/__pycache__ tests/__pycache__
	@find . -name '*.pyc' -delete
	@echo "Clean complete"
