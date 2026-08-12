import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"

def run():
    print("Running Kernel Adapter (Phase 8)...")
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    total_ledgers = 0
    total_kernel_facts = 0
    
    # Check if production kernel exists. It does not exist in this repo.
    kernel_available = False
    
    for file_path in FACT_LEDGER_DIR.glob("*.jsonl"):
        if not file_path.is_file():
            continue
            
        total_ledgers += 1
        facts = []
        with open(file_path, 'r') as f:
            for line in f:
                facts.append(FactRecord.from_dict(json.loads(line)))
                
        # Since kernel is unavailable, we emit a single NOT_AVAILABLE kernel fact per patient 
        # (or just skip, but the spec says "mark KERNEL_OUTPUT = NOT_AVAILABLE")
        pat_id = facts[0].provenance.patient_id if facts else "unknown"
        
        prov = FactProvenance(
            fact_category="KERNEL_OUTPUT",
            patient_id=pat_id,
            kernel_version="NOT_AVAILABLE",
            generator_version=manifest.get("generator_version", "v0.1.1")
        )
        kernel_fact = FactRecord(
            provenance=prov,
            fact_type="clinical",
            concept="kernel_safety_result",
            status="NOT_AVAILABLE"
        )
        total_kernel_facts += 1
        
        with open(file_path, 'a') as fw:
            fw.write(json.dumps(kernel_fact.to_dict()) + "\n")

    print(f"Kernel Adapter complete. Production kernel is NOT_AVAILABLE. Marked {total_kernel_facts} kernel facts as NOT_AVAILABLE.")
    
    log_entry = GenerationLogEntry.create(
        step_name="step05_kernel_adapter",
        seed=manifest.get('generation_seed'),
        input_rows=total_ledgers,
        output_rows=total_kernel_facts,
        validation={"kernel_status": "NOT_AVAILABLE", "kernel_facts": total_kernel_facts}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
