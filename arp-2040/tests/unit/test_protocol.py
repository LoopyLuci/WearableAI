"""
test_protocol.py — Wire protocol contract tests
"""
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "host-tools", "firmware", "include", "transport"))

# We test protocol types without compiling firmware
# by redefining the minimal needed types here

MESSAGE_HEADER_SIZE = 13  # version_major(1) + version_minor(1) + type(1) + payload_len(2) + timestamp_s(4) + message_id(4)
MAX_PAYLOAD_SIZE = 512

MAGIC_ARML = 0x41524D4C  # "ARML"


def encode_message(msg_type, payload, message_id=1, timestamp_s=0):
    """Encode a protocol message."""
    header = bytes([
        1,  # version_major
        0,  # version_minor
        msg_type,
    ])
    header += len(payload).to_bytes(2, 'little')
    header += timestamp_s.to_bytes(4, 'little')
    header += message_id.to_bytes(4, 'little')
    return header + payload


def decode_message(data):
    """Decode a protocol message, return dict."""
    if len(data) < MESSAGE_HEADER_SIZE:
        raise ValueError("Message too short")
    version_major = data[0]
    version_minor = data[1]
    msg_type = data[2]
    payload_len = int.from_bytes(data[3:5], 'little')
    timestamp_s = int.from_bytes(data[5:9], 'little')
    message_id = int.from_bytes(data[9:13], 'little')
    payload = data[13:13 + payload_len]
    return {
        'version_major': version_major,
        'version_minor': version_minor,
        'type': msg_type,
        'payload_len': payload_len,
        'timestamp_s': timestamp_s,
        'message_id': message_id,
        'payload': payload
    }


def test_message_header_size():
    assert MESSAGE_HEADER_SIZE == 13
    print("✓ Message header size is 13 bytes")


def test_encode_decode_roundtrip():
    payload = b'Hello, ARP-2040!'
    encoded = encode_message(0x01, payload, message_id=42, timestamp_s=1000000)
    decoded = decode_message(encoded)

    assert decoded['version_major'] == 1
    assert decoded['version_minor'] == 0
    assert decoded['type'] == 0x01
    assert decoded['payload_len'] == len(payload)
    assert decoded['message_id'] == 42
    assert decoded['timestamp_s'] == 1000000
    assert decoded['payload'] == payload
    print(f"✓ Encode/decode roundtrip: {len(encoded)} bytes")


def test_max_payload_size():
    max_payload = b'\x00' * MAX_PAYLOAD_SIZE
    encoded = encode_message(0x02, max_payload)
    decoded = decode_message(encoded)
    assert len(decoded['payload']) == MAX_PAYLOAD_SIZE
    print(f"✓ Max payload size: {MAX_PAYLOAD_SIZE} bytes")


def test_model_format_header():
    """Test ARP-2040 Model Format header."""
    header = struct.pack('<IIIIIIII',
                         MAGIC_ARML,  # magic
                         2,           # version
                         0x0001,      # model_id
                         1,           # schema_version
                         0xDEADBEEF,  # weight_crc
                         1024,        # weight_length
                         64,          # metadata_length
                         0)           # flags
    assert len(header) == 32
    magic = struct.unpack('<I', header[:4])[0]
    assert magic == MAGIC_ARML
    print("✓ Model format header: 32 bytes, magic=0x41524D4C")


def test_version_negotiation():
    """Test protocol version negotiation logic."""
    device_versions = {1, 2}
    server_versions = {2, 3}
    common = max(device_versions & server_versions)
    assert common == 2
    print(f"✓ Protocol version negotiation: highest common = {common}")


if __name__ == '__main__':
    test_message_header_size()
    test_encode_decode_roundtrip()
    test_max_payload_size()
    test_model_format_header()
    test_version_negotiation()
    print("\nAll protocol contract tests passed.")
