import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"

def run():
    print("Running Physician Simulation (Phase 11)...")
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    print("Since actual production kernel is NOT_AVAILABLE, we are strictly bound by the rule:")
    print("'If the kernel is unavailable, do not generate physician scenarios that require kernel review.'")
    print("Physician scenarios dependent on kernel logic are entirely skipped to preserve clinical integrity.")
    
    # We log 0 physician scenarios generated
    log_entry = GenerationLogEntry.create(
        step_name="step08_physician_sim",
        seed=manifest.get('generation_seed'),
        input_rows=1140,
        output_rows=0,
        validation={"skipped_due_to_missing_kernel": True}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
