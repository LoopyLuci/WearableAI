#!/usr/bin/env python3
"""
pre:scripts/copy_models.py
Copies quantized TinyML models into the data/ directory before upload.
"""
import os
import shutil

SRC = os.path.join(os.path.dirname(__file__), "..", "models")
DST = os.path.join(os.path.dirname(__file__), "..", "data")

os.makedirs(DST, exist_ok=True)

if os.path.isdir(SRC):
    for fname in os.listdir(SRC):
        src_path = os.path.join(SRC, fname)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, os.path.join(DST, fname))
            print(f"Copied model: {fname}")
else:
    print("No models directory found, skipping copy.")
