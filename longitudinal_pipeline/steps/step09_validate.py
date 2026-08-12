import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.generation_manifest import GenerationLogEntry
from validators.semantic_validator import SemanticValidator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.0"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LLM_DATASET_DIR = DATASET_VERSION_DIR / "llm_dataset"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"

def run():
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    seed = manifest['random_seed']
    
    validator = SemanticValidator(LLM_DATASET_DIR, FACT_LEDGER_DIR)
    print("Running semantic validation...")
    results = validator.run_all()
    
    log_entry = GenerationLogEntry.create(
        step_name="step09_validate",
        seed=seed,
        input_rows=0,
        output_rows=0,
        validation=results
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    if results['is_valid']:
        print("Validation PASSED.")
        return True
    else:
        print(f"Validation FAILED with {len(results['errors'])} errors.")
        for err in results['errors'][:10]:
            print(f"  - {err['type']}: {err['message']}")
        if len(results['errors']) > 10:
            print("  ... and more")
        return False

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
