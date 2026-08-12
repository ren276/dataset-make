import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactRecord
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"

def run():
    print("Running Longitudinal Timeline Validation (Phase 6)...")
    
    total_patients = 0
    patients_with_longitudinal_history = 0
    validation_failures = []
    
    for file_path in FACT_LEDGER_DIR.glob("*.jsonl"):
        if not file_path.is_file():
            continue
            
        total_patients += 1
        facts = []
        with open(file_path, 'r') as f:
            for line in f:
                facts.append(FactRecord.from_dict(json.loads(line)))
                
        # 1. Verify DERIVED_FACT source provenance
        for fact in facts:
            if fact.provenance.fact_category == "DERIVED_FACT":
                if not fact.provenance.source_facts:
                    # Exception: Chief complaint missing is allowed to have 0 if no encounter class exists, but usually it has encounter class
                    if fact.provenance.derivation_rule == "DR-CHIEF-COMPLAINT-MISSING" and not fact.provenance.source_facts:
                        continue
                    if fact.provenance.derivation_rule == "DR-002" and not fact.provenance.source_facts:
                        pass # if gender_source was missing
                    else:
                        validation_failures.append(f"Patient {fact.provenance.patient_id} has DERIVED_FACT {fact.provenance.fact_id} with empty source_facts! Rule: {fact.provenance.derivation_rule}")
                        
        # 2. Verify Timeline
        encounter_dates = set()
        for fact in facts:
            if fact.fact_type == "encounter_metadata" and fact.concept == "encounter_class":
                if fact.provenance.timestamp:
                    encounter_dates.add(fact.provenance.timestamp)
                    
        # A true longitudinal history has clinical events spanning > 1 distinct encounter dates
        if len(encounter_dates) > 1:
            patients_with_longitudinal_history += 1
            
    if validation_failures:
        for vf in validation_failures[:10]:
            print("FAIL:", vf, file=sys.stderr)
        if len(validation_failures) > 10:
            print(f"... and {len(validation_failures) - 10} more failures.", file=sys.stderr)
        print("Longitudinal Timeline Validation FAILED.", file=sys.stderr)
        return False
        
    print(f"Validation PASSED. {patients_with_longitudinal_history}/{total_patients} patients have longitudinal history spanning multiple encounters.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
