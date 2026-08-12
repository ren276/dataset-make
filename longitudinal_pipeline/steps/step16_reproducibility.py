import os
import shutil
import subprocess
from pathlib import Path
import json
import hashlib

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_V012_DIR = REPO_ROOT / "longitudinal_data/v0.1.2"
DIFF_REPORT_PATH = DATASET_V012_DIR / "reproducibility_diff.json"

def canonical_hash_directory(directory: Path) -> tuple:
    hasher = hashlib.sha256()
    records = []
    
    for file_path in sorted(directory.rglob("*.jsonl")):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                obj = json.loads(line)
                if 'generated_at' in obj:
                    del obj['generated_at']
                canon_str = json.dumps(obj, sort_keys=True)
                records.append((file_path.name, canon_str))
                hasher.update(canon_str.encode('utf-8'))
                
    return hasher.hexdigest(), records

def run_reproducibility_test():
    print("--- Running v0.1.2 Reproducibility Test (Phase 15) ---")
    
    # 1. Hash Run A (Current state of v0.1.2)
    print("Hashing Current v0.1.2 Run (Run A)...")
    tasks_hash_A, tasks_recs_A = canonical_hash_directory(DATASET_V012_DIR / "tasks")
    quality_hash_A, quality_recs_A = canonical_hash_directory(DATASET_V012_DIR / "quality")
    
    # 2. Re-run complete pipeline to produce Run B
    print("Executing Pipeline Rerun (Run B)...")
    subprocess.run(["python3", "longitudinal_pipeline/steps/step02b_source_ingestion.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step04_phc_normalize.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step07_scenario_engine.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step09_task_generate.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step10_validate.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step14_quality_herder.py"], check=True)
    
    # 3. Hash Run B
    print("Hashing Rerun (Run B)...")
    tasks_hash_B, tasks_recs_B = canonical_hash_directory(DATASET_V012_DIR / "tasks")
    quality_hash_B, quality_recs_B = canonical_hash_directory(DATASET_V012_DIR / "quality")
    
    print(f"Task Hash A: {tasks_hash_A}")
    print(f"Task Hash B: {tasks_hash_B}")
    print(f"Quality Hash A: {quality_hash_A}")
    print(f"Quality Hash B: {quality_hash_B}")
    
    diffs = []
    if tasks_hash_A != tasks_hash_B:
        print("ERROR: Tasks hash mismatch between Run A and Run B!")
        for idx in range(min(len(tasks_recs_A), len(tasks_recs_B))):
            if tasks_recs_A[idx] != tasks_recs_B[idx]:
                diffs.append({"type": "task", "file": tasks_recs_A[idx][0], "idx": idx})
                break
                
    if quality_hash_A != quality_hash_B:
        print("ERROR: Quality ledger hash mismatch between Run A and Run B!")
        for idx in range(min(len(quality_recs_A), len(quality_recs_B))):
            if quality_recs_A[idx] != quality_recs_B[idx]:
                diffs.append({"type": "quality", "file": quality_recs_A[idx][0], "idx": idx})
                break

    diff_report = {
        "is_reproducible": (tasks_hash_A == tasks_hash_B) and (quality_hash_A == quality_hash_B),
        "tasks_hash_A": tasks_hash_A,
        "tasks_hash_B": tasks_hash_B,
        "quality_hash_A": quality_hash_A,
        "quality_hash_B": quality_hash_B,
        "diff_count": len(diffs),
        "diffs": diffs
    }
    
    DIFF_REPORT_PATH.write_text(json.dumps(diff_report, indent=2))
    print(f"Reproducibility report written to {DIFF_REPORT_PATH}")
    
    if diffs:
        return False
        
    print("SUCCESS: v0.1.2 Quality Herding Pipeline is 100% deterministic and reproducible.")
    return True

if __name__ == "__main__":
    ok = run_reproducibility_test()
    import sys
    sys.exit(0 if ok else 1)
