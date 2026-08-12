import argparse
import shutil
import subprocess
import sys
import json
from pathlib import Path
import os

# Import the GenerationLogEntry
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from longitudinal_pipeline.schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNTHEA_ROOT = REPO_ROOT / "synthea"
SYNTHEA_BIOMETRICS = SYNTHEA_ROOT / "src/main/resources/biometrics.yml"
SYNTHEA_BIOMETRICS_BACKUP = SYNTHEA_ROOT / "src/main/resources/biometrics_original.yml"
INDIA_BIOMETRICS_SRC = REPO_ROOT / "synthea-international/in/src/main/resources/biometrics.yml"
SYNTHEA_RUN_PROPS = REPO_ROOT / "longitudinal_pipeline/config/synthea_run.properties"
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.0"
SYNTHEA_OUTPUT_DIR = DATASET_VERSION_DIR / "source/csv"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"

GRADLEW = SYNTHEA_ROOT / ("gradlew.bat" if os.name == 'nt' else "gradlew")

def backup_biometrics():
    if not SYNTHEA_BIOMETRICS_BACKUP.exists():
        shutil.copy2(SYNTHEA_BIOMETRICS, SYNTHEA_BIOMETRICS_BACKUP)
        print(f"Backed up biometrics.yml")

def install_india_biometrics():
    shutil.copy2(INDIA_BIOMETRICS_SRC, SYNTHEA_BIOMETRICS)
    print(f"India biometrics.yml installed.")

def restore_biometrics():
    if SYNTHEA_BIOMETRICS_BACKUP.exists():
        shutil.copy2(SYNTHEA_BIOMETRICS_BACKUP, SYNTHEA_BIOMETRICS)
        print(f"Original biometrics.yml restored.")

def run_synthea(seed: int, pop_size: int) -> bool:
    age_range = "5-80"
    props_path = str(SYNTHEA_RUN_PROPS).replace("\\", "/")
    
    raw_args = ["-s", str(seed), "-p", str(pop_size), "-a", age_range, "-c", props_path]
    q = "'"
    params_str = "[" + ",".join(f"{q}{a}{q}" for a in raw_args) + "]"
    cmd = [str(GRADLEW), "run", f"-Params={params_str}"]

    print(f"Running Synthea: seed={seed}, pop={pop_size}, age={age_range}")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SYNTHEA_ROOT),
            capture_output=False,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            print(f"ERROR: Synthea exited with code {result.returncode}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print("ERROR: Synthea timed out.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False

def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f) - 1 # exclude header

def run():
    # Read manifest
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found at {MANIFEST_PATH}. Run step00_manifest.py first.", file=sys.stderr)
        return False
        
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    seed = manifest['random_seed']
    pop_size = manifest['population_size']
    
    backup_biometrics()
    install_india_biometrics()
    try:
        success = run_synthea(seed, pop_size)
    finally:
        restore_biometrics()

    if not success:
        return False
        
    # Verify outputs
    expected_files = ['patients.csv', 'observations.csv', 'conditions.csv', 'medications.csv', 'encounters.csv']
    validation = {"missing_files": [], "file_sizes": {}}
    
    for fname in expected_files:
        fpath = SYNTHEA_OUTPUT_DIR / fname
        if not fpath.exists():
            validation["missing_files"].append(fname)
        else:
            validation["file_sizes"][fname] = fpath.stat().st_size
            
    if validation["missing_files"]:
        print(f"ERROR: Missing files {validation['missing_files']}", file=sys.stderr)
        return False
        
    num_patients = count_csv_rows(SYNTHEA_OUTPUT_DIR / "patients.csv")
    
    # Write log
    log_entry = GenerationLogEntry.create(
        step_name="step01_generate_source",
        seed=seed,
        input_rows=0,
        output_rows=num_patients,
        validation=validation
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print(f"Synthea generation complete. {num_patients} patients generated.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
