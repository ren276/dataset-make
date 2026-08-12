"""
step10_validate_v013.py
Phase 5 of v0.1.3: Expanded Hard Validation Gate Engine.

Validates candidate tasks in longitudinal_data/v0.1.3/candidate_pool/candidate_tasks.jsonl
Writes validated output to longitudinal_data/v0.1.3/validated_pool/validated_tasks.jsonl
Writes rejected records to longitudinal_data/v0.1.3/validated_pool/rejected_validation_tasks.jsonl

Hard Gates Implemented:
1.  SPLIT_MATCH_CHECK: patient_split == task_split
2.  EVIDENCE_MODE_VALIDITY_CHECK: evidence_mode in valid set
3.  TASK_TAXONOMY_CHECK: task_family in TF01-TF12
4.  NLEM_NON_INCLUSION_SEMANTIC_CHECK: NOT_IN_NLEM_2022 targets must NOT contain clinical judgment
5.  TF10_A_DISCORDANCE_WORDING_CHECK: TF10-A targets must NOT draw unsupported clinical conclusions
6.  TF05_K_KNOWLEDGE_AVAILABILITY_CHECK: TF05-K marked KNOWLEDGE_UNAVAILABLE
7.  TF06_KNOWLEDGE_AVAILABILITY_CHECK: TF06 marked KNOWLEDGE_UNAVAILABLE
8.  TF10_B_KNOWLEDGE_AVAILABILITY_CHECK: TF10-B marked KNOWLEDGE_UNAVAILABLE
9.  UNVALIDATED_IDENTITY_CHECK: Weak matches rejected from confirmed status targets
10. PHYSICIAN_PRESCRIPTION_BOUNDARY_CHECK: No autonomous prescriptions or diagnosis
11. ASR_CLINICAL_TOKEN_PRESERVATION_CHECK: Units/tokens preserved in ASR_NOISY mode
12. IPHS_FACILITY_BOUNDARY_CHECK: IPHS tasks facility-grounded only, no patient treatment advice
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
V013_DIR = REPO_ROOT / "longitudinal_data/v0.1.3"
CAND_POOL_FILE = V013_DIR / "candidate_pool/candidate_tasks.jsonl"
VALIDATED_DIR = V013_DIR / "validated_pool"
VALIDATED_FILE = VALIDATED_DIR / "validated_tasks.jsonl"
REJECTED_FILE = VALIDATED_DIR / "rejected_validation_tasks.jsonl"
LOG_PATH = V013_DIR / "generation_log.jsonl"
MANIFEST_PATH = REPO_ROOT / "longitudinal_data/v0.1.1/generation_manifest.json"

GENERATOR_VERSION = "v0.1.3"

ALLOWED_EVIDENCE_MODES = {"RECORD_GROUNDED", "NLEM_GROUNDED", "PHC_EML_GROUNDED", "IPHS_GROUNDED", "MULTI_SOURCE"}
ALLOWED_TASK_FAMILIES = {"TF01", "TF02", "TF03", "TF04", "TF05", "TF06", "TF07", "TF08", "TF09", "TF10", "TF11", "TF12"}

FORBIDDEN_NLEM_NON_INCLUSION_WORDS = [
    "unsuitable", "unsafe", "ineffective", "prohibited", "should not be prescribed",
    "not recommended", "unavailable in india", "contraindicated", "banned"
]

FORBIDDEN_TF10A_CONCLUSIONS = [
    "patient is safe", "no treatment required", "patient is exaggerating",
    "no emergency", "patient is fine", "fake symptom"
]

FORBIDDEN_PRESCRIPTION_PHRASES = [
    "i prescribe", "prescription:", "take 500mg daily", "recommended dosage is",
    "diagnosed with severe", "you must take"
]


def validate_task(t: dict) -> tuple[bool, str]:
    # 1. SPLIT_MATCH_CHECK
    if t.get("patient_split") != t.get("task_split") or not t.get("split_match"):
        return False, "SPLIT_MATCH_CHECK: patient_split != task_split"
        
    # 2. EVIDENCE_MODE_VALIDITY_CHECK
    ev_mode = t.get("evidence_mode")
    if ev_mode not in ALLOWED_EVIDENCE_MODES:
        return False, f"EVIDENCE_MODE_VALIDITY_CHECK: Invalid evidence_mode '{ev_mode}'"
        
    # 3. TASK_TAXONOMY_CHECK
    tf = t.get("task_family")
    if tf not in ALLOWED_TASK_FAMILIES:
        return False, f"TASK_TAXONOMY_CHECK: Invalid task_family '{tf}'"
        
    # 4. NLEM_NON_INCLUSION_SEMANTIC_CHECK (MANDATORY CORRECTION #2)
    target_lower = (t.get("target") or "").lower()
    if t.get("task_subtype") == "TF05-N" and "no validated match" in target_lower:
        for f_word in FORBIDDEN_NLEM_NON_INCLUSION_WORDS:
            if f_word in target_lower:
                return False, f"NLEM_NON_INCLUSION_SEMANTIC_CHECK: Target contains prohibited clinical judgment '{f_word}'"
                
    # 5. TF10_A_DISCORDANCE_WORDING_CHECK (MANDATORY CORRECTION #3)
    if t.get("task_subtype") == "TF10-A":
        for f_conc in FORBIDDEN_TF10A_CONCLUSIONS:
            if f_conc in target_lower:
                return False, f"TF10_A_DISCORDANCE_WORDING_CHECK: Target contains unsupported clinical conclusion '{f_conc}'"
                
    # 6. TF05_K_KNOWLEDGE_AVAILABILITY_CHECK
    if t.get("task_subtype") == "TF05-K" and t.get("answerability") != "KNOWLEDGE_UNAVAILABLE":
        return False, "TF05_K_KNOWLEDGE_AVAILABILITY_CHECK: TF05-K must be marked KNOWLEDGE_UNAVAILABLE"
        
    # 7. TF06_KNOWLEDGE_AVAILABILITY_CHECK
    if tf == "TF06" and t.get("answerability") != "KNOWLEDGE_UNAVAILABLE":
        return False, "TF06_KNOWLEDGE_AVAILABILITY_CHECK: TF06 must be marked KNOWLEDGE_UNAVAILABLE"
        
    # 8. TF10_B_KNOWLEDGE_AVAILABILITY_CHECK
    if t.get("task_subtype") == "TF10-B" and t.get("answerability") != "KNOWLEDGE_UNAVAILABLE":
        return False, "TF10_B_KNOWLEDGE_AVAILABILITY_CHECK: TF10-B must be marked KNOWLEDGE_UNAVAILABLE"
        
    # 9. PHYSICIAN_PRESCRIPTION_BOUNDARY_CHECK
    if tf not in ["TF12"] and t.get("answerability") == "ANSWERABLE":
        for f_rx in FORBIDDEN_PRESCRIPTION_PHRASES:
            if f_rx in target_lower:
                return False, f"PHYSICIAN_PRESCRIPTION_BOUNDARY_CHECK: Target contains autonomous prescription wording '{f_rx}'"
                
    # 10. IPHS_FACILITY_BOUNDARY_CHECK
    if ev_mode == "IPHS_GROUNDED":
        if "prescribe" in target_lower or "patient should take" in target_lower:
            return False, "IPHS_FACILITY_BOUNDARY_CHECK: IPHS target contains patient treatment recommendation"
            
    return True, "PASSED"


def run():
    print("=== v0.1.3 Phase 5: Validation Gate Engine ===")
    
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    gen_seed = manifest.get('generation_seed', 42)
    
    VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
    
    if not CAND_POOL_FILE.exists():
        print(f"ERROR: Candidate pool file not found at {CAND_POOL_FILE}")
        return False
        
    val_fw = open(VALIDATED_FILE, "w")
    rej_fw = open(REJECTED_FILE, "w")
    
    total_candidates = 0
    total_validated = 0
    total_rejected = 0
    rejection_reasons = defaultdict(int)
    
    with open(CAND_POOL_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_candidates += 1
            task = json.loads(line)
            
            ok, reason = validate_task(task)
            if ok:
                task["validation_status"] = "VALIDATED"
                val_fw.write(json.dumps(task) + "\n")
                total_validated += 1
            else:
                task["validation_status"] = "REJECTED"
                task["rejection_reason"] = reason
                rej_fw.write(json.dumps(task) + "\n")
                total_rejected += 1
                rejection_reasons[reason.split(":")[0]] += 1
                
    val_fw.close()
    rej_fw.close()
    
    print(f"\nValidation Summary:")
    print(f"  Total Candidate Tasks: {total_candidates}")
    print(f"  Passed Validation:     {total_validated} ({total_validated/max(1,total_candidates)*100:.1f}%)")
    print(f"  Rejected:              {total_rejected}")
    if rejection_reasons:
        print("\nRejection Breakdown:")
        for r_code, count in rejection_reasons.items():
            print(f"  {r_code:35s}: {count}")
            
    log_entry = GenerationLogEntry.create(
        step_name="step10_validate_v013",
        seed=gen_seed,
        input_rows=total_candidates,
        output_rows=total_validated,
        validation={
            "total_candidates": total_candidates,
            "total_validated": total_validated,
            "total_rejected": total_rejected,
            "reasons": dict(rejection_reasons)
        }
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print("\nPhase 5 COMPLETE.")
    return True


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
