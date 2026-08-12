import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactRecord
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"

def run():
    print("Running India Adaptation Validation (Phase 7)...")
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    validation_failures = []
    total_ledgers = 0
    
    for file_path in FACT_LEDGER_DIR.glob("*.jsonl"):
        if not file_path.is_file():
            continue
            
        total_ledgers += 1
        with open(file_path, 'r') as f:
            for line in f:
                fact = FactRecord.from_dict(json.loads(line))
                c = str(fact.concept).lower()
                
                # Check for US Race/Ethnicity
                if "race" in c or "ethnicity" in c:
                    validation_failures.append(f"Found forbidden US demographic: {fact.concept} = {fact.value} in {fact.provenance.fact_id}")
                    
                # Check for fake pincodes
                if "pincode" in c or "zip" in c:
                    # must be synthetic marked
                    if "synthetic" not in str(fact.value).lower() and "synthetic" not in c:
                        validation_failures.append(f"Found unvalidated non-synthetic pincode: {fact.concept} = {fact.value} in {fact.provenance.fact_id}")
                        
    if validation_failures:
        for vf in validation_failures[:10]:
            print("FAIL:", vf, file=sys.stderr)
        if len(validation_failures) > 10:
            print(f"... and {len(validation_failures) - 10} more failures.", file=sys.stderr)
        print("India Adaptation Validation FAILED.", file=sys.stderr)
        return False
        
    print(f"Validation PASSED. No US Race, Ethnicity, or unvalidated pincodes found across {total_ledgers} ledgers.")
    
    log_entry = GenerationLogEntry.create(
        step_name="step04c_india_adapt_validation",
        seed=manifest.get('generation_seed'),
        input_rows=total_ledgers,
        output_rows=total_ledgers,
        validation={"failures": len(validation_failures), "passed": True}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
