"""
Pre-upload script: copy model files from models/ to firmware/data/
"""
import os
import shutil

SRC = os.path.join(os.path.dirname(__file__), "..", "models")
DST = os.path.join(os.path.dirname(__file__), "data")

os.makedirs(DST, exist_ok=True)
for root, dirs, files in os.walk(SRC):
    for f in files:
        if f.endswith(".tflite") or f.endswith(".armodel"):
            src_path = os.path.join(root, f)
            rel = os.path.relpath(src_path, SRC)
            dst_path = os.path.join(DST, rel)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)
            print(f"Copied {rel} -> data/")
