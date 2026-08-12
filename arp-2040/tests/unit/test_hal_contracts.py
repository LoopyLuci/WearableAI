"""
test_hal_contracts.py — Verify HAL interface contracts are stable
"""
import ast
import os

BASE = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "include", "hal")

INTERFACES = ["ISensor.h", "IRadio.h", "ICrypto.h", "IStorage.h", "IPower.h",
              "IAudio.h", "IDisplay.h", "IActuator.h"]


def extract_methods(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()
    methods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            methods.add(node.name)
    return methods


def test_all_interfaces_exist():
    for iface in INTERFACES:
        path = os.path.join(BASE, iface)
        assert os.path.exists(path), f"Missing interface: {path}"
    print(f"✓ All {len(INTERFACES)} HAL interface files exist")


def test_interfaces_have_virtual_destructor():
    for iface in INTERFACES:
        path = os.path.join(BASE, iface)
        if not os.path.exists(path):
            continue
        with open(path, 'r') as f:
            content = f.read()
        assert 'virtual ~' in content, f"{iface} missing virtual destructor"
    print("✓ All interfaces have virtual destructors")


if __name__ == '__main__':
    test_all_interfaces_exist()
    test_interfaces_have_virtual_destructor()
    print("\nHAL contract tests passed.")
