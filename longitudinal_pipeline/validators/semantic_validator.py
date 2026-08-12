import json
from pathlib import Path
from typing import List, Dict, Any

class SemanticValidator:
    def __init__(self, dataset_dir: Path, ledger_dir: Path):
        self.dataset_dir = dataset_dir
        self.ledger_dir = ledger_dir
        self.errors = []
        
    def validate_split(self, split_name: str) -> bool:
        file_path = self.dataset_dir / split_name / "examples.jsonl"
        if not file_path.exists():
            return True
            
        with open(file_path, 'r') as f:
            for line_idx, line in enumerate(f):
                if not line.strip(): continue
                example = json.loads(line)
                
                # Rule: SCENARIO_FACT must not be in TRAIN split
                if split_name == "train" and example.get('contains_scenario_facts', False):
                    self.errors.append({
                        "type": "scenario_leakage",
                        "split": split_name,
                        "task_id": example['task_id'],
                        "message": "SCENARIO_FACT leaked into TRAIN split."
                    })
                    
                # Rule: target_generation_method must be template_v1
                if example.get('target_generation_method') != 'template_v1':
                    self.errors.append({
                        "type": "invalid_generation_method",
                        "split": split_name,
                        "task_id": example['task_id'],
                        "message": "Only template_v1 is allowed in pilot."
                    })
        return len(self.errors) == 0
        
    def validate_ledgers(self) -> bool:
        for ledger_path in self.ledger_dir.glob("*.jsonl"):
            with open(ledger_path, 'r') as f:
                for line in f:
                    if not line.strip(): continue
                    fact = json.loads(line)
                    prov = fact.get('fact_category', 'UNKNOWN')
                    
                    if prov == "DERIVED_FACT" and not fact.get('derivation_rule'):
                        self.errors.append({
                            "type": "missing_provenance",
                            "fact_id": fact.get('fact_id'),
                            "message": "DERIVED_FACT missing derivation_rule."
                        })
                    
                    if prov == "SCENARIO_FACT" and not fact.get('scenario_rule'):
                        self.errors.append({
                            "type": "missing_provenance",
                            "fact_id": fact.get('fact_id'),
                            "message": "SCENARIO_FACT missing scenario_rule."
                        })
                        
        return len(self.errors) == 0
        
    def run_all(self) -> Dict[str, Any]:
        self.validate_ledgers()
        self.validate_split("train")
        self.validate_split("safety_test")
        
        return {
            "is_valid": len(self.errors) == 0,
            "errors": self.errors
        }
