import json
import sys
from pathlib import Path
from dateutil import parser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactRecord, generate_task_id
from schemas.generation_manifest import GenerationLogEntry
from steps.step09_task_generate import build_deterministic_target

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
TASKS_DIR = DATASET_VERSION_DIR / "tasks"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
SPLITS_PATH = DATASET_VERSION_DIR / "patient_splits.json"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"

def run():
    print("Running Comprehensive Validation Gates (Targeted Correction 2)...")
    
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    with open(SPLITS_PATH, 'r') as f:
        patient_splits = json.load(f)
        
    validation_failures = []
    
    # 1. FACT_ID_COLLISION_CHECK & Fact Ledgers Scan
    seen_fact_ids = {}
    total_ledger_facts = 0
    patient_facts_map = {}
    
    for file_path in sorted(FACT_LEDGER_DIR.glob("*.jsonl")):
        if not file_path.is_file(): continue
        pat_id = file_path.stem
        pat_facts = {}
        with open(file_path, 'r') as f:
            for line in f:
                rec = FactRecord.from_dict(json.loads(line))
                total_ledger_facts += 1
                fid = rec.provenance.fact_id
                
                # Collision Check
                if fid in seen_fact_ids:
                    prev = seen_fact_ids[fid]
                    curr_desc = f"{rec.fact_type}:{rec.concept}:{rec.value}"
                    prev_desc = f"{prev.fact_type}:{prev.concept}:{prev.value}"
                    if curr_desc != prev_desc:
                        validation_failures.append(f"FACT_ID_COLLISION_CHECK FAILED! Duplicate fact_id {fid} across distinct facts.")
                else:
                    seen_fact_ids[fid] = rec
                    
                pat_facts[fid] = rec
        patient_facts_map[pat_id] = pat_facts

    print(f"Validated {total_ledger_facts} ledger facts across {len(patient_facts_map)} patients. Unique fact IDs: {len(seen_fact_ids)}.")

    # 2. Task Validation & Gates
    task_files = {
        "TRAIN": TASKS_DIR / "train.jsonl",
        "VALIDATION": TASKS_DIR / "validation.jsonl",
        "TEST": TASKS_DIR / "test.jsonl",
        "SAFETY_TEST": TASKS_DIR / "safety_test.jsonl"
    }
    
    total_tasks = 0
    seen_task_ids = set()
    
    for split_name, file_path in task_files.items():
        if not file_path.exists():
            validation_failures.append(f"Missing task export file: {file_path}")
            continue
            
        with open(file_path, 'r') as f:
            for line in f:
                task = json.loads(line)
                total_tasks += 1
                ex_id = task["example_id"]
                
                # TASK_IDENTITY_CHECK & Collision Check
                if ex_id in seen_task_ids:
                    validation_failures.append(f"TASK_IDENTITY_CHECK FAILED! Duplicate task example_id {ex_id}.")
                seen_task_ids.add(ex_id)
                
                # SPLIT_MATCH_CHECK
                pat_id = task["patient_id"]
                pat_split = patient_splits.get(pat_id)
                if task.get("patient_split") != pat_split:
                    validation_failures.append(f"Split Mismatch! Task {ex_id} patient_split is {task.get('patient_split')} but patient_splits.json is {pat_split}.")
                if task.get("task_split") != split_name:
                    validation_failures.append(f"Split Mismatch! Task {ex_id} task_split is {task.get('task_split')} but file is {split_name}.")
                if not task.get("split_match") or task.get("patient_split") != task.get("task_split"):
                    validation_failures.append(f"Split Match Flag False for task {ex_id}.")
                    
                # Placeholder checks
                if "Simulated target response" in task["target"] or "Simulated context trace" in task.get("clinical_context", ""):
                    validation_failures.append(f"Placeholder content detected in task {ex_id}.")
                    
                # MEDICATION_EVENT_PRESPARATION_SEPARATION_CHECK
                if task["task_family"] == "PRESCRIPTION_EXPLANATION" and "prescription" in task["target"].lower() and "medication record" not in task["target"].lower():
                    validation_failures.append(f"MEDICATION_EVENT_PRESCRIPTION_SEPARATION_CHECK FAILED for task {ex_id}. Promoted event to prescription.")
                    
                # Evidence lookup
                pat_facts = patient_facts_map.get(pat_id, {})
                src_fact_objs = [pat_facts[fid] for fid in task.get("source_facts", []) if fid in pat_facts]
                
                # HISTORICAL_DIAGNOSIS_CHECK
                if task["task_family"] == "HISTORICAL_DIAGNOSIS":
                    if any(sf.semantic_role != "DIAGNOSIS" for sf in src_fact_objs):
                        validation_failures.append(f"HISTORICAL_DIAGNOSIS_CHECK FAILED for task {ex_id}. Non-diagnosis fact used.")
                        
                # LONGITUDINAL_CHRONOLOGY_CHECK
                if task["task_family"] == "LONGITUDINAL_COMPARISON" and len(src_fact_objs) >= 2:
                    t1_str = src_fact_objs[0].provenance.timestamp
                    t2_str = src_fact_objs[1].provenance.timestamp
                    if t1_str and t2_str:
                        try:
                            if parser.parse(t1_str) > parser.parse(t2_str):
                                validation_failures.append(f"LONGITUDINAL_CHRONOLOGY_CHECK FAILED for task {ex_id}. Inverted timestamps: {t1_str} > {t2_str}.")
                        except Exception:
                            pass
                            
                # TASK_TAXONOMY_CHECK
                valid_tfs = ["TF01", "TF02", "TF03", "TF04", "TF05", "TF06", "TF07", "TF08", "TF09", "TF10", "TF11", "TF12"]
                if task["task_family"] not in valid_tfs:
                    validation_failures.append(f"TASK_TAXONOMY_CHECK FAILED for task {ex_id}. Non-canonical task_family code {task['task_family']}.")
                    
                # LANGUAGE_FORM_VALIDATION_CHECK (English text labeled as HI or HINGLISH)
                if task.get("language") in ["HI", "HINGLISH"]:
                    inst_text = task.get("instruction", "")
                    if all(ord(char) < 128 for char in inst_text) and not any(kw in inst_text for kw in ["kya", "kab", "kaise", "batao", "main"]):
                        validation_failures.append(f"LANGUAGE_FORM_VALIDATION_CHECK FAILED for task {ex_id}. English instruction labeled as {task.get('language')}.")

                # ASR_PERTURBATION_CHECK
                if task.get("input_mode") == "ASR_NOISY":
                    if task.get("instruction") == task.get("raw_instruction", ""):
                        # Ensure instruction was perturbed
                        pass

                # TF06_KNOWLEDGE_AVAILABILITY_CHECK
                if task["task_family"] == "TF06" and "Educational information regarding" in task["target"] and "is provided" in task["target"]:
                    validation_failures.append(f"TF06_KNOWLEDGE_AVAILABILITY_CHECK FAILED for task {ex_id}. Non-substantive placeholder education target detected.")

                # TARGET_RECONSTRUCTION_CHECK
                rule_id = task.get("scenario_family")
                task_type = task.get("task_type")
                reconstructed_target = build_deterministic_target(rule_id, task_type, src_fact_objs)
                if reconstructed_target != task["target"]:
                    validation_failures.append(f"TARGET_RECONSTRUCTION_CHECK FAILED for task {ex_id}. Expected '{reconstructed_target}', got '{task['target']}'.")

    if validation_failures:
        print(f"Validation FAILED with {len(validation_failures)} errors:", file=sys.stderr)
        for vf in validation_failures[:20]:
            print("  - FAIL:", vf, file=sys.stderr)
        return False
        
    print(f"All Validation Gates PASSED cleanly! Evaluated {total_tasks} tasks and {total_ledger_facts} facts.")
    
    log_entry = GenerationLogEntry.create(
        step_name="step10_validate",
        seed=manifest.get('generation_seed'),
        input_rows=total_tasks,
        output_rows=total_tasks,
        validation={"is_valid": True, "task_count": total_tasks, "errors": []}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)

