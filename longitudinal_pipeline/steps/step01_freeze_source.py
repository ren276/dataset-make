import sys
import json
import shutil
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
V010_DIR = REPO_ROOT / "longitudinal_data/v0.1.0"
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
V010_CSV_DIR = V010_DIR / "source/csv"
V011_CSV_DIR = DATASET_VERSION_DIR / "source/csv"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"

def hash_file(file_path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(file_path.read_bytes())
    return hasher.hexdigest()

def run():
    # Read manifest
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found at {MANIFEST_PATH}. Run step00_manifest.py first.", file=sys.stderr)
        return False
        
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    seed = manifest['generation_seed']
    manifest_v010_hashes = manifest['raw_source_hashes']
    
    if not V010_CSV_DIR.exists():
        print(f"ERROR: v0.1.0 source directory not found: {V010_CSV_DIR}", file=sys.stderr)
        return False

    V011_CSV_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Freezing v0.1.0 raw source to v0.1.1...")
    
    # Copy files and hash them
    v011_hashes = {}
    copied_count = 0
    for file_path in V010_CSV_DIR.glob("*.csv"):
        if not file_path.is_file():
            continue
            
        dest_path = V011_CSV_DIR / file_path.name
        shutil.copy2(file_path, dest_path)
        
        v011_hashes[file_path.name] = hash_file(dest_path)
        copied_count += 1
        
    # Validation: Compare hashes
    validation = {
        "v010_hashes": manifest_v010_hashes,
        "v011_hashes": v011_hashes,
        "hash_match": True,
        "mismatched_files": []
    }
    
    for fname, v010_hash in manifest_v010_hashes.items():
        v011_hash = v011_hashes.get(fname)
        if v010_hash != v011_hash:
            validation["hash_match"] = False
            validation["mismatched_files"].append(fname)
            
    if not validation["hash_match"]:
        print(f"ERROR: Raw source hashes do not match! Mismatches: {validation['mismatched_files']}", file=sys.stderr)
        return False
        
    print(f"Successfully froze and verified {copied_count} files from v0.1.0 source.")
    
    # Write log
    log_entry = GenerationLogEntry.create(
        step_name="step01_freeze_source",
        seed=seed,
        input_rows=copied_count,
        output_rows=copied_count,
        validation=validation
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
