import json
import sys
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
TASKS_DIR = DATASET_VERSION_DIR / "tasks"

def run():
    print("\n=======================================================")
    print("PHASE 11 & 12: STRATIFIED 50-TASK AUDIT AND LINEAGE TRACES")
    print("=======================================================\n")
    
    all_tasks = []
    for split in ["train", "validation", "test", "safety_test"]:
        tp = TASKS_DIR / f"{split}.jsonl"
        if tp.exists():
            with open(tp, 'r') as f:
                for line in f:
                    all_tasks.append(json.loads(line))
                    
    if not all_tasks:
        print("No tasks found.")
        return False
        
    random.seed(42)
    
    print("--- 50-TASK STRATIFIED AUDIT ---\n")
    by_family = {}
    for t in all_tasks:
        by_family.setdefault(t.get('task_family', 'OTHER'), []).append(t)
        
    audit_sample = []
    for fam in sorted(by_family.keys()):
        tasks = by_family[fam]
        samp = random.sample(tasks, min(4, len(tasks)))
        audit_sample.extend(samp)
        
    if len(audit_sample) < 50:
        rem = [t for t in all_tasks if t not in audit_sample]
        audit_sample.extend(random.sample(rem, min(50 - len(audit_sample), len(rem))))
        
    for i, t in enumerate(audit_sample[:50]):
        print(f"AUDIT ENTRY #{i+1}")
        print(f"  Example ID: {t.get('example_id')}")
        print(f"  Patient ID: {t.get('patient_id')} | Patient Split: {t.get('patient_split')} | Task Split: {t.get('task_split')} | Split Match: {t.get('split_match')}")
        print(f"  Task Family: {t.get('task_family')} | Scenario Family: {t.get('scenario_family')} | Difficulty: {t.get('difficulty')}")
        print(f"  Language: {t.get('language')} | Input Mode: {t.get('input_mode')} | Safety Class: {t.get('safety_class')}")
        print(f"  Instruction: {t.get('instruction')}")
        print(f"  Target: {t.get('target')}")
        print(f"  Validation Status: {t.get('validation_status')}")
        print("-" * 60)
        
    print("\n--- 10 LINEAGE TRACES ---\n")
    traces = [
        ("1. Historical Diagnosis", "HISTORICAL_DIAGNOSIS"),
        ("2. Historical Finding", "HISTORICAL_FINDING"),
        ("3. Longitudinal Comparison", "LONGITUDINAL_COMPARISON"),
        ("4. Clinical Summarization", "CLINICAL_SUMMARIZATION"),
        ("5. Medication Interpretation", "MEDICATION_INTERPRETATION"),
        ("6. Prescription Explanation", "PRESCRIPTION_EXPLANATION"),
        ("7. Patient Education", "PATIENT_EDUCATION"),
        ("8. Missing Information", "MISSING_INFORMATION"),
        ("9. Clinical Discordance", "CLINICAL_DISCORDANCE"),
        ("10. Safe Abstention / Deferral", "SAFE_ABSTENTION")
    ]
    
    for name, tfam in traces:
        print(f"TRACE: {name}")
        cands = [t for t in all_tasks if t.get('task_family') == tfam]
        if not cands:
            print("  Status: NOT_AVAILABLE (No tasks generated for this family)")
            print("-" * 60)
            continue
            
        t = random.choice(cands)
        print(f"  Example ID: {t.get('example_id')}")
        print(f"  Patient ID: {t.get('patient_id')} | Patient Split: {t.get('patient_split')} | Task Split: {t.get('task_split')} | Split Match: {t.get('split_match')}")
        print(f"  Source Fact IDs: {t.get('source_facts')}")
        print(f"  Scenario Fact IDs: {t.get('scenario_facts')}")
        print(f"  Clinical Context:\n{t.get('clinical_context')}")
        print(f"  Instruction: {t.get('instruction')}")
        print(f"  Target: {t.get('target')}")
        print(f"  Validation Status: {t.get('validation_status')}")
        print("-" * 60)
        
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)

