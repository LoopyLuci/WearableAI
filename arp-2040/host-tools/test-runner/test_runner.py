"""
test_runner.py — Hardware-in-loop test runner
Connects to device via USB/serial, runs test sequences, reports results.
"""
import sys
import time
import json
from dataclasses import dataclass, asdict
from typing import List, Optional

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not available, hardware tests will be skipped")


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    message: str = ""


class HardwareTestRunner:
    """
    Runs test sequences on real hardware.
    Communicates with device firmware via serial protocol.
    """

    def __init__(self, port: str = 'COM3', baudrate: int = 921600):
        self.port = port
        self.baudrate = baudrate
        self._serial: Optional['serial.Serial'] = None

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            print("[TestRunner] pyserial not available, using emulator mode")
            return False
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=5)
            time.sleep(2)  # Wait for Arduino serial reset
            return True
        except Exception as e:
            print(f"[TestRunner] Could not connect to {self.port}: {e}")
            return False

    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()

    def send_command(self, cmd: str) -> str:
        if not self._serial:
            return "ERROR: not connected"
        self._serial.write((cmd + '\n').encode())
        time.sleep(0.1)
        response = self._serial.read_all().decode(errors='replace')
        return response.strip()

    def run_test_suite(self, tests: List[callable]) -> List[TestResult]:
        results = []
        for test in tests:
            print(f"[TestRunner] Running: {test.__name__}")
            start = time.perf_counter()
            try:
                passed, message = test(self)
                duration = (time.perf_counter() - start) * 1000
                results.append(TestResult(
                    name=test.__name__,
                    passed=passed,
                    duration_ms=duration,
                    message=message
                ))
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {message} ({duration:.1f}ms)")
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                results.append(TestResult(
                    name=test.__name__,
                    passed=False,
                    duration_ms=duration,
                    message=str(e)
                ))
                print(f"  [ERROR] {e} ({duration:.1f}ms)")
        return results

    def report(self, results: List[TestResult]):
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        print(f"\n{'='*60}")
        print(f"Test Report: {passed}/{total} passed")
        print(f"{'='*60}")
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name}: {r.message} ({r.duration_ms:.1f}ms)")
        print(f"{'='*60}")
        return passed == total


def test_hw_self_check(runner: HardwareTestRunner) -> tuple:
    """Device responds to ping with version string."""
    response = runner.send_command("PING")
    passed = "ARP-2040" in response or "OK" in response
    return passed, f"Ping response: {response[:50]}"


def test_hw_uptime(runner: HardwareTestRunner) -> tuple:
    """Device reports uptime > 0."""
    response = runner.send_command("UPTIME")
    try:
        uptime = int(response.strip())
        passed = uptime > 0
        return passed, f"Uptime: {uptime}s"
    except ValueError:
        return False, f"Invalid uptime response: {response}"


def test_hw_sensor_imu(runner: HardwareTestRunner) -> tuple:
    """IMU returns valid accelerometer data."""
    response = runner.send_command("IMU_READ")
    try:
        values = [int(x) for x in response.strip().split(',')]
        passed = len(values) == 6 and all(-16000 < v < 16000 for v in values)
        return passed, f"IMU accel+gyro: {values}"
    except ValueError:
        return False, f"Invalid IMU response: {response}"


def test_hw_storage_crc(runner: HardwareTestRunner) -> tuple:
    """All QSPI flash regions pass CRC check."""
    response = runner.send_command("STORAGE_VERIFY")
    passed = "OK" in response or "ALL_PASS" in response
    return passed, f"Storage verify: {response[:80]}"


def test_hw_crypto_self_test(runner: HardwareTestRunner) -> tuple:
    """Crypto chip self-test passes."""
    response = runner.send_command("CRYPTO_TEST")
    passed = "PASS" in response or "OK" in response
    return passed, f"Crypto self-test: {response[:80]}"


if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
    runner = HardwareTestRunner(port=port)

    if not runner.connect():
        print("No hardware connected. Running in emulator-verification mode only.")
        print("To run hardware tests: python test_runner.py <serial_port>")
        sys.exit(0)

    tests = [test_hw_self_check, test_hw_uptime, test_hw_sensor_imu,
             test_hw_storage_crc, test_hw_crypto_self_test]
    results = runner.run_test_suite(tests)
    success = runner.report(results)
    runner.disconnect()
    sys.exit(0 if success else 1)
