import json
import sys
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.0"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"

class PhysicianSimulation:
    def __init__(self, seed: int):
        self.seed = seed
        
    def process_ledger(self, ledger_path: Path) -> int:
        facts = []
        with open(ledger_path, 'r') as f:
            for line in f:
                if not line.strip(): continue
                facts.append(json.loads(line))
                
        new_facts = []
        pat_id = None
        enc_id = None
        for f in facts:
            if pat_id is None and f.get('patient_id'):
                pat_id = f['patient_id']
            if f['fact_type'] == 'encounter_metadata':
                enc_id = f.get('encounter_id')
                
        if pat_id:
            prov = FactProvenance(
                fact_category="PHYSICIAN_FACT",
                patient_id=pat_id,
                encounter_id=enc_id
            )
            sim_fact = FactRecord(
                provenance=prov,
                fact_type="physician_review",
                concept="physician_decision",
                value="AGREE",
                status="KNOWN",
                medication_layer="PHYSICIAN_APPROVED_PRESCRIPTION"
            )
            new_facts.append(sim_fact.to_dict())
            
        with open(ledger_path, 'a') as f:
            for nf in new_facts:
                f.write(json.dumps(nf) + "\n")
                
        return len(new_facts)

def run():
    if not FACT_LEDGER_DIR.exists():
        print("Fact ledgers not found.", file=sys.stderr)
        return False
        
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    seed = manifest['random_seed']
    
    sim = PhysicianSimulation(seed)
    total = 0
    
    ledger_files = list(FACT_LEDGER_DIR.glob("*.jsonl"))
    print(f"Running physician simulation on {len(ledger_files)} ledgers...")
    
    for lf in tqdm(ledger_files):
        total += sim.process_ledger(lf)
        
    log_entry = GenerationLogEntry.create(
        step_name="step07_physician_sim",
        seed=seed,
        input_rows=len(ledger_files),
        output_rows=total,
        validation={"num_ledgers": len(ledger_files)}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print(f"Physician simulation complete. {total} physician facts added.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
