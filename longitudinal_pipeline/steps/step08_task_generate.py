import json
import sys
import uuid
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.0"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LLM_DATASET_DIR = DATASET_VERSION_DIR / "llm_dataset"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"

class TaskGenerator:
    def __init__(self, seed: int):
        self.seed = seed
        
    def generate_task(self, ledger_path: Path):
        facts = []
        with open(ledger_path, 'r') as f:
            for line in f:
                if not line.strip(): continue
                facts.append(json.loads(line))
                
        # Get patient and encounter
        pat_id = None
        for f in facts:
            if pat_id is None and f.get('patient_id'):
                pat_id = f['patient_id']
                break
                
        if not pat_id: return None
        
        # We find a scenario question and create a task
        source_facts_used = []
        scenario_facts_used = []
        question = ""
        
        for f in facts:
            cat = f.get('fact_category')
            if cat == "SCENARIO_FACT" and f.get('concept') == 'scenario_question':
                question = f.get('value', '')
                scenario_facts_used.append(f)
            elif cat == "SOURCE_FACT":
                source_facts_used.append(f)
                
        if not question: return None
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        example = {
            "task_id": task_id,
            "patient_id": pat_id,
            "instruction": f"Patient asks: {question}. Answer based on facts.",
            "target": "As a deterministic pilot, I advise you to consult the clinic based on your vitals.",
            "target_generation_method": "template_v1",
            "context": {
                "source_facts": [f['fact_id'] for f in source_facts_used],
                "scenario_facts": [f['fact_id'] for f in scenario_facts_used],
                "derived_facts": [],
                "kernel_outputs": [],
                "physician_facts": []
            },
            "contains_scenario_facts": len(scenario_facts_used) > 0,
            "split": "safety_test" if len(scenario_facts_used) > 0 else "train"
        }
        
        return example

def run():
    LLM_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    (LLM_DATASET_DIR / "train").mkdir(parents=True, exist_ok=True)
    (LLM_DATASET_DIR / "safety_test").mkdir(parents=True, exist_ok=True)
    
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    seed = manifest['random_seed']
    
    generator = TaskGenerator(seed)
    total_tasks = 0
    
    ledger_files = list(FACT_LEDGER_DIR.glob("*.jsonl"))
    print(f"Running task generator on {len(ledger_files)} ledgers...")
    
    with open(LLM_DATASET_DIR / "safety_test" / "examples.jsonl", 'w') as sf, \
         open(LLM_DATASET_DIR / "train" / "examples.jsonl", 'w') as tf:
        
        for lf in tqdm(ledger_files):
            task = generator.generate_task(lf)
            if task:
                total_tasks += 1
                if task['split'] == 'safety_test':
                    sf.write(json.dumps(task) + "\n")
                else:
                    tf.write(json.dumps(task) + "\n")
                    
    log_entry = GenerationLogEntry.create(
        step_name="step08_task_generate",
        seed=seed,
        input_rows=len(ledger_files),
        output_rows=total_tasks,
        validation={"num_ledgers": len(ledger_files)}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print(f"Task generation complete. {total_tasks} tasks created.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
