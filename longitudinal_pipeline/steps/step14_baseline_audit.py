import json
import sys
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_V011_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
TASKS_DIR = DATASET_V011_DIR / "tasks"
FACT_LEDGER_DIR = DATASET_V011_DIR / "fact_ledgers"
REPORT_PATH = DATASET_V011_DIR / "baseline_diagnostic_report.json"

def run_diagnostic():
    print("Running Baseline Diagnostic Audit on v0.1.1 Candidate Pool...")
    
    diagnostic_failures = defaultdict(int)
    total_candidates = 0
    
    # 1. Inspect Fact Ledgers for semantic roles
    role_counts = defaultdict(int)
    non_diag_in_cond = 0
    for file_path in sorted(FACT_LEDGER_DIR.glob("*.jsonl")):
        with open(file_path, 'r') as f:
            for line in f:
                rec = json.loads(line)
                role = rec.get("semantic_role", "UNKNOWN")
                role_counts[role] += 1
                if rec.get("fact_type") == "condition" and role != "DIAGNOSIS":
                    non_diag_in_cond += 1

    # 2. Inspect Tasks
    for split in ["train", "validation", "test", "safety_test"]:
        tp = TASKS_DIR / f"{split}.jsonl"
        if not tp.exists(): continue
        with open(tp, 'r') as f:
            for line in f:
                task = json.loads(line)
                total_candidates += 1
                
                target = task.get("target", "")
                inst = task.get("instruction", "")
                tfam = task.get("task_family", "")
                
                if "Medication review due" in inst or "Medication review due" in target:
                    diagnostic_failures["medication_review_mislabeled_as_diagnosis"] += 1
                if "NOT_RECORDED" in inst or "NOT_RECORDED" in target:
                    diagnostic_failures["not_recorded_treated_as_fact"] += 1
                if "How did my address change" in inst or "address" in inst.lower():
                    diagnostic_failures["low_relevance_address_retrieval"] += 1
                if "The medication record specifies" in target and tfam == "PRESCRIPTION_EXPLANATION":
                    diagnostic_failures["medication_event_prescription_wording_check"] += 1
                if "use/indication for" in target and "is not recorded" in target:
                    diagnostic_failures["medication_knowledge_unavailable_rate"] += 1

    report = {
        "v011_total_candidates": total_candidates,
        "role_breakdown": dict(role_counts),
        "non_diagnosis_conditions": non_diag_in_cond,
        "diagnostic_defect_counts": dict(diagnostic_failures),
        "diagnostic_status": "DIAGNOSTIC_ONLY_COMPLETE"
    }
    
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"Diagnostic Report written to {REPORT_PATH}")
    print(json.dumps(report, indent=2))
    return True

if __name__ == "__main__":
    run_diagnostic()
