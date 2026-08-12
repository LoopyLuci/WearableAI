"""
device_emulator.py — Host-side RP2040/NINA device emulator
Implements all I* interfaces using host resources.
This is the primary development and testing tool.
"""
import socket
import threading
import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Callable

from flash_sim import FlashSimulator, ImageMetadata, MAGIC_ACTIVE, MAGIC_STAGING, crc32


@dataclass
class EmulatedSensorSample:
    sensor_id: int
    timestamp_us: int
    data: bytes


class EmulatedRadio:
    """Implements IRadio using host TCP sockets + BLE-like advertising."""

    def __init__(self, device_name: str = "ARP-2040-Emu"):
        self.device_name = device_name
        self.wifi_mode = 0  # OFF
        self.wifi_connected = False
        self.ap_running = False
        self.ble_advertising = False
        self.tcp_server_socket: Optional[socket.socket] = None
        self.tcp_clients: List[socket.socket] = []
        self._running = True
        self._lock = threading.Lock()
        self._reset_count = 0
        self._uptime_start = time.time()
        self._message_handler: Optional[Callable] = None

    def init(self):
        print(f"[EmuRadio] Initialized as '{self.device_name}'")
        return 0

    def shutdown(self):
        self._running = False
        for c in self.tcp_clients:
            c.close()
        if self.tcp_server_socket:
            self.tcp_server_socket.close()

    def wifi_set_mode(self, mode: int) -> int:
        with self._lock:
            self.wifi_mode = mode
            return 0

    def wifi_connect(self, ssid: str, password: str) -> int:
        print(f"[EmuRadio] Connecting to Wi-Fi SSID='{ssid}'")
        time.sleep(0.3)
        with self._lock:
            self.wifi_connected = True
        return 0

    def wifi_disconnect(self) -> int:
        with self._lock:
            self.wifi_connected = False
        return 0

    def wifi_start_ap(self, ssid: str, channel: int = 1) -> int:
        print(f"[EmuRadio] Starting AP SSID='{ssid}' ch={channel}")
        with self._lock:
            self.ap_running = True
        return 0

    def wifi_stop_ap(self) -> int:
        with self._lock:
            self.ap_running = False
        return 0

    def ble_start_advertising(self, name: str, service_uuid: int) -> int:
        print(f"[EmuRadio] BLE advertising as '{name}' UUID=0x{service_uuid:04X}")
        self.ble_advertising = True
        return 0

    def ble_stop_advertising(self) -> int:
        self.ble_advertising = False
        return 0

    def tcp_server_start(self, port: int, max_conn: int) -> int:
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server_socket.bind(('127.0.0.1', port))
        self.tcp_server_socket.listen(max_conn)
        print(f"[EmuRadio] TCP server listening on port {port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return 0

    def tcp_server_stop(self) -> int:
        if self.tcp_server_socket:
            self.tcp_server_socket.close()
            self.tcp_server_socket = None
        return 0

    def tcp_server_running(self) -> bool:
        return self.tcp_server_socket is not None

    def _accept_loop(self):
        while self._running and self.tcp_server_socket:
            try:
                client, addr = self.tcp_server_socket.accept()
                with self._lock:
                    self.tcp_clients.append(client)
                print(f"[EmuRadio] TCP client connected from {addr}")
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, client: socket.socket):
        try:
            while self._running:
                data = client.recv(4096)
                if not data:
                    break
                if self._message_handler:
                    self._message_handler(data)
        except Exception:
            pass
        finally:
            with self._lock:
                if client in self.tcp_clients:
                    self.tcp_clients.remove(client)
            client.close()

    def ping(self) -> int:
        return 0

    def reset_count(self) -> int:
        return self._reset_count

    def uptime_s(self) -> int:
        return int(time.time() - self._uptime_start)

    def on_message(self, handler: Callable):
        self._message_handler = handler


class EmulatedCrypto:
    """Implements ICrypto using software crypto (fallback when no ATECC608A)."""

    def __init__(self):
        self._has_hw = False
        self._counter = 0

    def init(self):
        print("[EmuCrypto] Initialized (software fallback)")
        return 0

    def has_hardware_key(self) -> bool:
        return self._has_hw

    def get_public_key(self):
        print("[EmuCrypto] Returning dummy public key")
        return bytes(64)

    def device_serial(self) -> int:
        return 0x41424344

    def monotonic_counter(self) -> int:
        return self._counter

    def sign(self, message: bytes, message_len: int):
        print(f"[EmuCrypto] Software sign of {message_len} bytes")
        return bytes(64)

    def verify(self, public_key: bytes, message: bytes, message_len: int, signature: bytes) -> int:
        print(f"[EmuCrypto] Software verify of {message_len} bytes")
        return 0

    def create_challenge(self):
        import os
        token = os.urandom(32)
        counter = self._counter
        self._counter += 1
        return token, counter

    def verify_response(self, challenge, response: bytes, response_len: int) -> int:
        print(f"[EmuCrypto] Verify response len={response_len}")
        return 0

    def random_bytes(self, buffer: bytearray, length: int):
        import os
        buffer[:] = os.urandom(length)
        return 0

    def sha256(self, data: bytes, data_len: int):
        import hashlib
        return hashlib.sha256(data[:data_len]).digest()

    def aes128_encrypt(self, key: bytes, plaintext: bytes):
        # XOR-based placeholder (use real AES in production)
        ct = bytes(a ^ b for a, b in zip(key * 2, plaintext))
        return ct

    def aes128_decrypt(self, key: bytes, ciphertext: bytes):
        pt = bytes(a ^ b for a, b in zip(key * 2, ciphertext))
        return pt


class EmulatedPower:
    def __init__(self):
        self._state = 0  # ACTIVE
        self._voltage_mv = 3700
        self._soc = 85

    def init(self):
        return 0

    def set_state(self, state: int) -> int:
        self._state = state
        return 0

    def get_state(self) -> int:
        return self._state

    def get_battery_status(self):
        from dataclasses import dataclass
        bs = type('BatteryStatus', (), {})()
        bs.voltage_mv = self._voltage_mv
        bs.soc_percent = self._soc
        bs.charging = False
        bs.low_battery = self._soc < 15
        return bs

    def estimated_runtime_seconds(self) -> int:
        return self._soc * 60  # ~1 min per %

    def feed_watchdog(self):
        pass

    def reset_count(self) -> int:
        return 0


class DeviceEmulator:
    """
    Top-level emulator composing all emulated subsystems.
    Tests and host-side code use this as a drop-in replacement for the real device.
    """

    def __init__(self, flash_path: str = ':memory:'):
        self.flash = FlashSimulator(flash_path)
        self.radio = EmulatedRadio()
        self.crypto = EmulatedCrypto()
        self.power = EmulatedPower()
        self.sensor_samples: List[EmulatedSensorSample] = []
        self._boot_metadata_written = False
        self._uptime_start = time.time()

    def boot(self):
        """Simulate device boot sequence."""
        print("[Emulator] === BOOT ===")
        self.radio.init()
        self.crypto.init()
        self.power.init()

        # Write factory partition if not present
        if not self._boot_metadata_written:
            factory_image = b'ARP-2040 FACTORY PARTITION v1.0\x00' + b'\x00' * 400
            meta = self.flash.write_image_staging(
                staging_offset=0x00040000,
                payload=factory_image,
                version=1, source=3  # FACTORY
            )
            self.flash.promote_image(0x00040000, 0x00040000)
            self._boot_metadata_written = True
            print("[Emulator] Factory partition installed")

        print(f"[Emulator] Boot complete in {time.time() - self._uptime_start:.3f}s")

    def shutdown(self):
        self.radio.shutdown()
        print("[Emulator] === SHUTDOWN ===")

    def inject_sensor_sample(self, sensor_id: int, data: bytes):
        """Inject a sensor sample into the emulator for testing."""
        sample = EmulatedSensorSample(
            sensor_id=sensor_id,
            timestamp_us=int(time.time() * 1_000_000),
            data=data
        )
        self.sensor_samples.append(sample)

    def get_sensor_samples(self, sensor_id: int) -> List[EmulatedSensorSample]:
        return [s for s in self.sensor_samples if s.sensor_id == sensor_id]
