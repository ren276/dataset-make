import os
import shutil
import subprocess
from pathlib import Path
import json
import hashlib

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
DIFF_REPORT_PATH = DATASET_VERSION_DIR / "reproducibility_diff.json"

def canonical_hash_directory(directory: Path) -> tuple:
    hasher = hashlib.sha256()
    records = []
    
    for file_path in sorted(directory.rglob("*.jsonl")):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                obj = json.loads(line)
                # Strip only execution metadata timestamp, NOT clinical timestamps or deterministic IDs!
                if 'generated_at' in obj:
                    del obj['generated_at']
                canon_str = json.dumps(obj, sort_keys=True)
                records.append((file_path.name, canon_str))
                hasher.update(canon_str.encode('utf-8'))
                
    return hasher.hexdigest(), records

def run():
    print("--- Running Reproducibility Test (Targeted Correction 2) ---")
    
    # 1. Hash Run A (Current state of v0.1.1)
    print("Hashing Current Run (Run A)...")
    ledger_hash_A, ledger_recs_A = canonical_hash_directory(DATASET_VERSION_DIR / "fact_ledgers")
    task_hash_A, task_recs_A = canonical_hash_directory(DATASET_VERSION_DIR / "tasks")
    
    # 2. Re-run pipeline to test deterministic reproducibility
    print("Executing Pipeline Rerun (Run B)...")
    shutil.rmtree(DATASET_VERSION_DIR / "fact_ledgers")
    shutil.rmtree(DATASET_VERSION_DIR / "tasks")
    
    subprocess.run(["python3", "longitudinal_pipeline/steps/step02b_source_ingestion.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step04_phc_normalize.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step07_scenario_engine.py"], check=True)
    subprocess.run(["python3", "longitudinal_pipeline/steps/step09_task_generate.py"], check=True)
    
    # 3. Hash Run B
    print("Hashing Rerun (Run B)...")
    ledger_hash_B, ledger_recs_B = canonical_hash_directory(DATASET_VERSION_DIR / "fact_ledgers")
    task_hash_B, task_recs_B = canonical_hash_directory(DATASET_VERSION_DIR / "tasks")
    
    print(f"Ledger Hash A: {ledger_hash_A}")
    print(f"Ledger Hash B: {ledger_hash_B}")
    print(f"Task Hash A:   {task_hash_A}")
    print(f"Task Hash B:   {task_hash_B}")
    
    diffs = []
    
    if ledger_hash_A != ledger_hash_B:
        print("ERROR: Fact Ledger hash mismatch between Run A and Run B!")
        for idx in range(min(len(ledger_recs_A), len(ledger_recs_B))):
            if ledger_recs_A[idx] != ledger_recs_B[idx]:
                diffs.append({
                    "artifact_type": "ledger",
                    "file_name": ledger_recs_A[idx][0],
                    "record_index": idx,
                    "run_A_content": ledger_recs_A[idx][1],
                    "run_B_content": ledger_recs_B[idx][1]
                })
                break
                
    if task_hash_A != task_hash_B:
        print("ERROR: Task JSONL hash mismatch between Run A and Run B!")
        for idx in range(min(len(task_recs_A), len(task_recs_B))):
            if task_recs_A[idx] != task_recs_B[idx]:
                diffs.append({
                    "artifact_type": "task",
                    "file_name": task_recs_A[idx][0],
                    "record_index": idx,
                    "run_A_content": task_recs_A[idx][1],
                    "run_B_content": task_recs_B[idx][1]
                })
                break

    diff_report = {
        "is_reproducible": (ledger_hash_A == ledger_hash_B) and (task_hash_A == task_hash_B),
        "ledger_hash_A": ledger_hash_A,
        "ledger_hash_B": ledger_hash_B,
        "task_hash_A": task_hash_A,
        "task_hash_B": task_hash_B,
        "diff_count": len(diffs),
        "diffs": diffs
    }
    
    DIFF_REPORT_PATH.write_text(json.dumps(diff_report, indent=2))
    print(f"Reproducibility report written to {DIFF_REPORT_PATH}")
    
    if diffs:
        return False
        
    print("SUCCESS: Pipeline is 100% deterministic and reproducible across semantic records and lineage.")
    return True

if __name__ == "__main__":
    ok = run()
    import sys
    sys.exit(0 if ok else 1)

