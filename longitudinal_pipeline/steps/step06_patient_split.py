import json
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
SPLITS_PATH = DATASET_VERSION_DIR / "patient_splits.json"

def run():
    print("Running Patient-Level Split (Phase 9)...")
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    seed = manifest.get('generation_seed', 42)
    random.seed(seed)
    
    patient_ids = []
    for file_path in FACT_LEDGER_DIR.glob("*.jsonl"):
        if file_path.is_file():
            patient_ids.append(file_path.stem)
            
    patient_ids.sort()
    random.shuffle(patient_ids)
    
    total = len(patient_ids)
    train_end = int(total * 0.7)
    val_end = int(total * 0.8)
    test_end = int(total * 0.9)
    
    train_ids = patient_ids[:train_end]
    val_ids = patient_ids[train_end:val_end]
    test_ids = patient_ids[val_end:test_end]
    safety_ids = patient_ids[test_end:]
    
    splits = {}
    for pid in train_ids: splits[pid] = "TRAIN"
    for pid in val_ids: splits[pid] = "VALIDATION"
    for pid in test_ids: splits[pid] = "TEST"
    for pid in safety_ids: splits[pid] = "SAFETY_TEST"
    
    with open(SPLITS_PATH, 'w') as f:
        json.dump(splits, f, indent=2)
        
    print(f"Splitting complete: TRAIN={len(train_ids)}, VAL={len(val_ids)}, TEST={len(test_ids)}, SAFETY={len(safety_ids)}")
    
    # Validation: Mutually exclusive
    assert len(set(train_ids).intersection(set(val_ids))) == 0
    assert len(set(train_ids).intersection(set(test_ids))) == 0
    assert len(set(train_ids).intersection(set(safety_ids))) == 0
    
    log_entry = GenerationLogEntry.create(
        step_name="step06_patient_split",
        seed=seed,
        input_rows=total,
        output_rows=total,
        validation={"TRAIN": len(train_ids), "VALIDATION": len(val_ids), "TEST": len(test_ids), "SAFETY_TEST": len(safety_ids)}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
