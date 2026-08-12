"""
graph-compiler CLI — Control graph compiler
JSON/YAML graph definition → binary ControlGraph record
"""
import argparse
import json
import struct
import sys
import os

MAGIC_CGNH = 0x43474E48  # "CGNH"


def compile_graph(graph_def: dict) -> bytes:
    """Compile a graph definition dict into binary ControlGraph record."""
    nodes = graph_def.get('nodes', [])
    entry_node_id = graph_def.get('entry_node', nodes[0]['id'] if nodes else 0)

    if not nodes:
        raise ValueError("Graph must have at least one node")

    # Validate all node IDs
    node_ids = {n['id'] for n in nodes}
    for n in nodes:
        for next_id in [n.get('next_true'), n.get('next_false')]:
            if next_id is not None and next_id != 0xFFFFFFFF and next_id not in node_ids:
                raise ValueError(f"Node {n['id']} references undefined node {next_id}")

    # Build header
    header = struct.pack(
        '<IIIIII',
        MAGIC_CGNH,
        graph_def.get('version', 1),
        entry_node_id,
        len(nodes),
        0,  # graph_crc (filled later)
        int(__import__('time').time())
    )
    header += b'\x00' * 40  # reserved

    # Build node records
    node_data = b''
    for n in nodes:
        node_type = n.get('type', 'SENSOR_POLL')
        type_map = {
            'SENSOR_POLL': 1, 'MODEL_INFERENCE': 2, 'FORWARD': 3,
            'FILTER': 4, 'ROUTE': 5, 'ACTION': 6, 'LOGGER': 7,
            'SLEEP': 8, 'CUSTOM_SCRIPT': 9
        }
        node_type_val = type_map.get(node_type, 1)
        node_record = struct.pack(
            '<IIIIIIII',
            n['id'],
            node_type_val,
            n.get('param_a', 0),
            n.get('param_b', 0),
            n.get('next_true', 0xFFFFFFFF),
            n.get('next_false', 0xFFFFFFFF),
            n.get('interval_ms', 100),
            n.get('flags', 0)
        )
        node_data += node_record

    # Compute CRC over header + nodes
    full_data = header + node_data
    # Overwrite placeholder CRC
    crc = 0xFFFFFFFF & (__import__('hashlib').crc32(full_data[12:]) ^ 0xFFFFFFFF)
    full_data = full_data[:12] + struct.pack('<I', crc) + full_data[16:]

    return full_data


def main():
    parser = argparse.ArgumentParser(description="ARP-2040 Graph Compiler")
    parser.add_argument('--input', '-i', required=True, help='Input JSON graph file')
    parser.add_argument('--output', '-o', required=True, help='Output binary graph file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        graph_def = json.load(f)

    binary = compile_graph(graph_def)

    with open(args.output, 'wb') as f:
        f.write(binary)

    print(f"Compiled {args.input} → {args.output} ({len(binary)} bytes)")
    print(f"Nodes: {graph_def.get('nodes', []) and len(graph_def['nodes'])}")


if __name__ == '__main__':
    main()
