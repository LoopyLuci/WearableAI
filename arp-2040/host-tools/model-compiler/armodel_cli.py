"""
model-compiler CLI — Host-side model build pipeline
PyTorch/ONNX → TFLite → quantize → sign → package as .armodel
"""
import argparse
import hashlib
import struct
import sys
import os
import time


MAGIC_ARML = 0x41524D4C  # "ARML"


def crc32(data: bytes) -> int:
    return 0xFFFFFFFF & (hashlib.crc32(data) ^ 0xFFFFFFFF)


def build_armodel(input_path: str, model_id: int, name: str,
                  output_path: str = None, version: int = 1) -> str:
    """
    Build an ARP-2040 model file from a TFLite FlatBuffer.
    Wraps it in the ARP-2040 Model Format header.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, 'rb') as f:
        tflite_data = f.read()

    weight_len = len(tflite_data)
    weight_crc = crc32(tflite_data)

    # Build metadata (JSON-like string)
    metadata = (
        f'{{"name":"{name}","model_id":{model_id},'
        f'"version":{version},"weight_len":{weight_len},'
        f'"weight_crc":0x{weight_crc:08X},'
        f'"built":{int(time.time())}}}'
    ).encode('utf-8')

    metadata_len = len(metadata)

    # Build ARP-2040 Model Format header (32 bytes)
    header = struct.pack(
        '<IIIIIIII',
        MAGIC_ARML,       # magic
        version,          # version
        model_id,         # model_id
        1,                # schema_version
        weight_crc,       # weight_crc
        weight_len,       # weight_length
        metadata_len,     # metadata_length
        0                 # flags
    )

    output_path = output_path or f"{name}_v{version}.armodel"
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(metadata)
        f.write(tflite_data)

    actual_size = os.path.getsize(output_path)
    print(f"Built {output_path}")
    print(f"  Model: {name} (ID: 0x{model_id:04X})")
    print(f"  Version: {version}")
    print(f"  TFLite weights: {weight_len:,} bytes")
    print(f"  Metadata: {metadata_len} bytes")
    print(f"  Total: {actual_size:,} bytes")
    print(f"  Weight CRC: 0x{weight_crc:08X}")
    return output_path


def verify_armodel(armodel_path: str) -> bool:
    """Verify an .armodel file: check magic, CRC, structure."""
    with open(armodel_path, 'rb') as f:
        data = f.read()

    if len(data) < 32:
        print(f"ERROR: File too small: {len(data)} bytes")
        return False

    magic, version, model_id, schema, weight_crc, weight_len, meta_len, flags = \
        struct.unpack('<IIIIIIII', data[:32])

    if magic != MAGIC_ARML:
        print(f"ERROR: Invalid magic: 0x{magic:08X} (expected 0x{MAGIC_ARML:08X})")
        return False

    expected_size = 32 + meta_len + weight_len
    if len(data) != expected_size:
        print(f"ERROR: Size mismatch: {len(data)} != {expected_size}")
        return False

    # Verify CRC
    actual_metadata = data[32:32 + meta_len]
    actual_weights = data[32 + meta_len:]
    actual_crc = crc32(actual_weights)

    if actual_crc != weight_crc:
        print(f"ERROR: CRC mismatch: 0x{actual_crc:08X} != 0x{weight_crc:08X}")
        return False

    print(f"✓ {armodel_path}")
    print(f"  Model ID: 0x{model_id:04X}, Version: {version}")
    print(f"  Schema: {schema}, Flags: 0x{flags:08X}")
    print(f"  Metadata: {meta_len} bytes")
    print(f"  Weights: {weight_len:,} bytes")
    print(f"  CRC: OK")
    return True


def main():
    parser = argparse.ArgumentParser(description="ARP-2040 Model Compiler")
    subparsers = parser.add_subparsers(dest='command', required=True)

    build_parser = subparsers.add_parser('build', help='Build .armodel from TFLite')
    build_parser.add_argument('--input', '-i', required=True, help='Input TFLite file')
    build_parser.add_argument('--id', type=lambda x: int(x, 0), required=True,
                              help='Model ID (hex or decimal)')
    build_parser.add_argument('--name', '-n', required=True, help='Model name')
    build_parser.add_argument('--version', '-v', type=int, default=1, help='Version')
    build_parser.add_argument('--output', '-o', help='Output .armodel path')

    verify_parser = subparsers.add_parser('verify', help='Verify .armodel file')
    verify_parser.add_argument('file', help='.armodel file to verify')

    args = parser.parse_args()

    if args.command == 'build':
        build_armodel(args.input, args.id, args.name, args.output, args.version)
    elif args.command == 'verify':
        ok = verify_armodel(args.file)
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
