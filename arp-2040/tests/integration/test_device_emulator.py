import os
import sys
import time

# Ensure host-tools are importable when running via pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "host-tools", "device-emulator"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "host-tools", "flash-sim"))

from device_emulator import DeviceEmulator
from flash_sim import FlashSimulator, ImageMetadata, MAGIC_ACTIVE, MAGIC_STAGING, crc32

def test_emulator_boot():
    # Import with fallback for direct pytest runs
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "host-tools", "device-emulator"))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "host-tools", "flash-sim"))
    from device_emulator import DeviceEmulator
    from flash_sim import FlashSimulator

    emu = DeviceEmulator()
    emu.boot()
    assert emu.radio.ping() == 0
    emu.shutdown()
    print("✓ Emulator boots, radio responds to ping")


def test_flash_lifecycle():
    with FlashSimulator(':memory:') as flash:
        # Write staging image
        payload = b'ARP-2040 FACTORY TEST IMAGE\x00' + b'\x00' * 400
        meta = flash.write_image_staging(0x00040000, payload, version=1, source=3)
        assert meta.magic == 0x53505246  # MAGIC_STAGING
        assert meta.image_length == len(payload)

        # Promote
        ok = flash.promote_image(0x00040000, 0x00040000)
        assert ok is True

        # Verify
        ok = flash.verify_region(0x00040000)
        assert ok is True

    print("✓ Flash: staging → promote → verify")


def test_flash_power_loss_simulation():
    """Simulate power loss during staging write."""
    with FlashSimulator('/tmp/arp2040_flash_test.bin') as flash:
        # Write valid staging
        payload = b'GOOD IMAGE DATA' * 10
        flash.write_image_staging(0x00080000, payload, version=1, source=0)

        # Simulate corruption: overwrite part of payload
        flash.write(0x00080068, b'\xFF' * 10)

        # Verify should fail
        ok = flash.verify_region(0x00080000)
        assert ok is False, "Corrupted staging should fail verification"

    print("✓ Flash: corrupted staging rejected on verification")


def test_emulator_sensor_injection():
    emu = DeviceEmulator()
    emu.boot()
    emu.inject_sensor_sample(0x01, b'\x01\x02\x03\x04\x05\x06')
    samples = emu.get_sensor_samples(0x01)
    assert len(samples) == 1
    assert samples[0].data == b'\x01\x02\x03\x04\x05\x06'
    print("✓ Sensor sample injection works")


def test_emulator_radio_connectivity():
    emu = DeviceEmulator()
    emu.boot()
    emu.radio.wifi_connect("TestNetwork", "password123")
    assert emu.radio.wifi_connected is True
    emu.radio.wifi_disconnect()
    assert emu.radio.wifi_connected is False
    print("✓ Radio Wi-Fi connect/disconnect state machine")


def test_emulator_ble():
    emu = DeviceEmulator()
    emu.boot()
    result = emu.radio.ble_start_advertising("ARP-2040-Test", 0x180A)
    assert result == 0  # OK
    print("✓ BLE advertising state machine")


def test_emulator_crypto():
    emu = DeviceEmulator()
    emu.boot()
    pub = emu.crypto.get_public_key()
    assert len(pub) == 64
    token, counter = emu.crypto.create_challenge()
    assert len(token) == 32
    assert counter == 0
    print("✓ Crypto: public key + challenge-response")


def test_emulator_power_states():
    emu = DeviceEmulator()
    emu.boot()
    assert emu.power.get_state() == 0  # ACTIVE
    emu.power.set_state(2)  # IDLE
    assert emu.power.get_state() == 2
    bs = emu.power.get_battery_status()
    assert bs.voltage_mv > 0
    print("✓ Power state transitions + battery status")


if __name__ == '__main__':
    test_emulator_boot()
    test_flash_lifecycle()
    test_flash_power_loss_simulation()
    test_emulator_sensor_injection()
    test_emulator_radio_connectivity()
    test_emulator_ble()
    test_emulator_crypto()
    test_emulator_power_states()
    print("\nAll device emulator integration tests passed.")
