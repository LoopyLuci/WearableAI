"""
Windows build runner - replaces Makefile functionality
"""
import subprocess
import sys
import time
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FIRMWARE_DIR = PROJECT_ROOT / "arp-2040" / "firmware"
TESTS_DIR = PROJECT_ROOT / "arp-2040" / "tests"
DASHBOARD_DIR = PROJECT_ROOT / "arduino-dashboard"

def run(cmd, cwd=None, capture=True):
    """Run command and return result"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=str(cwd or PROJECT_ROOT),
            timeout=300
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def build_firmware(sketch_path=None):
    """Build firmware"""
    sketch = sketch_path or FIRMWARE_DIR / "validation_firmware_v1.0.0" / "validation_firmware_v1.0.0.ino"
    cmd = [
        sys.executable, "-m", "arduino_cli",
        "compile",
        "--fqbn", "arduino:mbed_nano:nanorp2040connect",
        str(sketch)
    ]
    print(f"Building firmware: {sketch}")
    ok, stdout, stderr = run(cmd, cwd=FIRMWARE_DIR)
    if ok:
        print("✓ Build successful")
        return True
    else:
        print(f"✗ Build failed:\n{stderr}")
        return False

def flash_firmware(firmware_path=None, port="COM15"):
    """Flash firmware to board"""
    fw = firmware_path or FIRMWARE_DIR / "validation_firmware_v1.0.0" / "validation_firmware_v1.0.0.ino"
    cmd = [
        sys.executable, "-m", "arduino_cli",
        "upload",
        "-p", port,
        "--fqbn", "arduino:mbed_nano:nanorp2040connect",
        str(fw)
    ]
    print(f"Flashing firmware to {port}: {fw}")
    ok, stdout, stderr = run(cmd, cwd=FIRMWARE_DIR)
    if ok:
        print(f"✓ Flash successful on {port}")
        return True
    else:
        print(f"✗ Flash failed:\n{stderr}")
        return False

def build_and_flash(sketch_path=None, port="COM15"):
    """Build and flash atomically"""
    if not build_firmware(sketch_path):
        return False
    return flash_firmware(sketch_path, port)

def run_tests():
    """Run all tests"""
    tests = []
    
    # arp-2040 tests
    if TESTS_DIR.exists():
        print("Running arp-2040 tests...")
        ok, stdout, stderr = run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=PROJECT_ROOT / "arp-2040"
        )
        tests.append(("arp-2040", ok, stdout, stderr))
    
    # dashboard tests
    if DASHBOARD_DIR.exists():
        print("Running dashboard tests...")
        ok, stdout, stderr = run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=DASHBOARD_DIR
        )
        tests.append(("dashboard", ok, stdout, stderr))
    
    # toolkit tests
    toolkit_dir = PROJECT_ROOT / "arduino-mcp-toolkit"
    if toolkit_dir.exists():
        print("Running toolkit tests...")
        ok, stdout, stderr = run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=toolkit_dir
        )
        tests.append(("toolkit", ok, stdout, stderr))
    
    all_ok = all(ok for _, ok, _, _ in tests)
    for name, ok, stdout, stderr in tests:
        status = "✓" if ok else "✗"
        print(f"\n{status} {name} tests: {'PASSED' if ok else 'FAILED'}")
        if not ok:
            print(f"  stderr: {stderr[:200]}")
    
    return all_ok

def lint_code():
    """Run linting"""
    print("Running lint checks...")
    ok, stdout, stderr = run(
        [sys.executable, "-m", "py_compile",
         str(FIRMWARE_DIR / "validation_firmware_v1.0.0" / "validation_firmware_v1.0.0.ino")],
        cwd=FIRMWARE_DIR
    )
    if ok:
        print("✓ Lint checks passed")
    else:
        print(f"✗ Lint failed:\n{stderr}")
    return ok

def start_dashboard(host="0.0.0.0", port=8080):
    """Start dashboard server"""
    backend_dir = DASHBOARD_DIR / "backend"
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", host, "--port", str(port), "--log-level", "info"]
    print(f"Starting dashboard on {host}:{port}")
    print("Press Ctrl+C to stop")
    try:
        subprocess.run(cmd, cwd=backend_dir)
    except KeyboardInterrupt:
        print("\nDashboard stopped")

def main():
    parser = argparse.ArgumentParser(description="Arduino Build Runner")
    parser.add_argument("command", choices=["build", "flash", "build-flash", "test", "lint", "dashboard", "all"])
    parser.add_argument("--port", default="COM15", help="Serial port")
    parser.add_argument("--sketch", help="Sketch path")
    parser.add_argument("--host", default="0.0.0.0", help="Dashboard host")
    parser.add_argument("--dashboard-port", type=int, default=8080, help="Dashboard port")
    args = parser.parse_args()
    
    if args.command == "build":
        success = build_firmware(args.sketch)
    elif args.command == "flash":
        success = flash_firmware(args.sketch, args.port)
    elif args.command == "build-flash":
        success = build_and_flash(args.sketch, args.port)
    elif args.command == "test":
        success = run_tests()
    elif args.command == "lint":
        success = lint_code()
    elif args.command == "dashboard":
        start_dashboard(args.host, args.dashboard_port)
        return
    elif args.command == "all":
        success = lint_code() and build_firmware(args.sketch) and run_tests()
    else:
        parser.print_help()
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
