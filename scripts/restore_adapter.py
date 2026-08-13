"""
scripts/restore_adapter.py
Reconstructs experiment_001_qa2_output/final_adapter/adapter_model.safetensors
from its split 50MB parts if missing.
"""

import os
import glob
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER_DIR = REPO_ROOT / "experiment_001_qa2_output/final_adapter"
TARGET_FILE = ADAPTER_DIR / "adapter_model.safetensors"

def restore_adapter():
    if TARGET_FILE.exists() and TARGET_FILE.stat().st_size > 0:
        print(f"Adapter model file already exists: {TARGET_FILE} ({round(TARGET_FILE.stat().st_size / (1024**2), 2)} MB)")
        return

    parts = sorted(glob.glob(str(ADAPTER_DIR / "adapter_model.safetensors.part_*")))
    if not parts:
        print(f"Error: No adapter part files found in {ADAPTER_DIR}")
        return

    print(f"Reconstructing {TARGET_FILE.name} from {len(parts)} parts...")
    with open(TARGET_FILE, "wb") as outfile:
        for p in parts:
            print(f"  Joining {Path(p).name}...")
            with open(p, "rb") as infile:
                outfile.write(infile.read())

    print(f"Success! Restored {TARGET_FILE} ({round(TARGET_FILE.stat().st_size / (1024**2), 2)} MB)")

if __name__ == "__main__":
    restore_adapter()
