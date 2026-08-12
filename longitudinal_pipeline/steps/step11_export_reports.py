import json
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
SOURCE_DIR = DATASET_VERSION_DIR / "source/csv"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
TASKS_DIR = DATASET_VERSION_DIR / "tasks"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
SPLITS_PATH = DATASET_VERSION_DIR / "patient_splits.json"

def run():
    print("Generating Authoritative Independent Reports (Targeted Correction 2)...")
    
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    with open(SPLITS_PATH, 'r') as f:
        splits = json.load(f)

    # 1. Authoritative Source Counts
    pat_df = pd.read_csv(SOURCE_DIR / "patients.csv") if (SOURCE_DIR / "patients.csv").exists() else None
    enc_df = pd.read_csv(SOURCE_DIR / "encounters.csv") if (SOURCE_DIR / "encounters.csv").exists() else None
    
    unique_patients = len(pat_df) if pat_df is not None else len(splits)
    unique_encounters = len(enc_df) if enc_df is not None else 0
    
    # Update manifest population_size
    manifest['population_size'] = unique_patients
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2)

    # 2. Independent Ledger Scan
    fact_counts = defaultdict(int)
    semantic_role_counts = defaultdict(int)
    scenario_counts = defaultdict(int)
    total_scenarios = 0
    total_ledger_facts = 0
    
    for file_path in sorted(FACT_LEDGER_DIR.glob("*.jsonl")):
        if not file_path.is_file(): continue
        with open(file_path, 'r') as f:
            for line in f:
                fact = json.loads(line)
                total_ledger_facts += 1
                cat = fact.get("fact_category", "UNKNOWN")
                fact_counts[cat] += 1
                
                if cat == "SOURCE_FACT" and fact.get("semantic_role"):
                    semantic_role_counts[fact["semantic_role"]] += 1
                    
                if cat == "SCENARIO_FACT":
                    rule = fact.get("scenario_rule", "UNKNOWN")
                    scenario_counts[rule] += 1
                    total_scenarios += 1
                    
    # 3. Independent Task Scan
    task_counts = defaultdict(int)
    task_family_counts = defaultdict(int)
    scenario_family_counts = defaultdict(int)
    difficulty_counts = defaultdict(int)
    language_counts = defaultdict(int)
    input_mode_counts = defaultdict(int)
    total_tasks = 0
    
    for split in ["train", "validation", "test", "safety_test"]:
        tp = TASKS_DIR / f"{split}.jsonl"
        if not tp.exists(): continue
        with open(tp, 'r') as f:
            for line in f:
                task = json.loads(line)
                total_tasks += 1
                task_counts[split.upper()] += 1
                task_family_counts[task.get("task_family", "UNKNOWN")] += 1
                scenario_family_counts[task.get("scenario_family", "UNKNOWN")] += 1
                difficulty_counts[task.get("difficulty", "UNKNOWN")] += 1
                language_counts[task.get("language", "UNKNOWN")] += 1
                input_mode_counts[task.get("input_mode", "UNKNOWN")] += 1
                
    # 4. Ingestion Reconciliation Stats from log
    exclusion_stats = {}
    if LOG_PATH.exists():
        with open(LOG_PATH, 'r') as f:
            for line in f:
                entry = json.loads(line)
                if entry['step_name'] == "step02b_source_ingestion":
                    exclusion_stats = entry['validation_summary'].get('coverage', {})
                    
    # 5. Generate Reports
    card = f"""# PHC SaMD Dataset Card (v0.1.1)

## Overview
Targeted correction release for v0.1.1 enforcing rigorous provenance, collision-safe deterministic identities, evidence-grounded clinical targets, and semantic role eligibility.

## India Adaptation
**WARNING:** This is India-adapted synthetic data. It is not a real-world Indian clinical dataset and does not establish Indian epidemiological representativeness or clinical performance.

## Pipeline Metadata
Generator Version: {manifest.get('generator_version')}
Synthea Seed: {manifest.get('generation_seed')}
Population Size: {unique_patients} unique patients
"""
    (DATASET_VERSION_DIR / "DATASET_CARD.md").write_text(card)
    
    evidence = """# Dataset Evidence & Limitations
This dataset is synthetic development/evaluation data.
It does **NOT** establish:
- clinical validity
- clinical performance
- regulatory approval
- safety in real patients
- physician equivalence
"""
    (DATASET_VERSION_DIR / "DATASET_EVIDENCE_LIMITATIONS.md").write_text(evidence)
    
    gaps = """# Schema Gap Report
1. **Production Kernel:** The actual PHC production kernel is NOT_AVAILABLE in this repository. 
2. **Missing Clinical Dimensions:** Synthea does not provide clinically linked chief complaints by default.
"""
    (DATASET_VERSION_DIR / "DATASET_SCHEMA_GAP_REPORT.md").write_text(gaps)
    
    adapt = """# India Adaptation Report
- US Race and Ethnicity have been stripped explicitly via code lists.
- Names are translated via `indian_names.yaml`.
"""
    (DATASET_VERSION_DIR / "INDIA_ADAPTATION_REPORT.md").write_text(adapt)
    
    coverage = f"""# Clinical Coverage Report

## Authoritative Population & Encounters
- Unique Patients: {unique_patients} (generating {fact_counts.get('SOURCE_FACT', 0)} patient demographic/source records)
- Unique Encounters: {unique_encounters}

## Fact Ledger Summary
Total Ledger Facts: {total_ledger_facts}
```json
{json.dumps(dict(fact_counts), indent=2)}
```

## Semantic Roles (Source Facts)
```json
{json.dumps(dict(semantic_role_counts), indent=2)}
```

## Source Ingestion Reconciliation
```json
{json.dumps(exclusion_stats, indent=2)}
```

## Base Scenarios Artifact
Total Base Scenarios: {total_scenarios}
```json
{json.dumps(dict(scenario_counts), indent=2)}
```
"""
    (DATASET_VERSION_DIR / "CLINICAL_COVERAGE_REPORT.md").write_text(coverage)
    
    pilot = f"""# v0.1.1 Pilot Report (Targeted Correction 2)

## Authoritative Dataset Statistics
- Unique Patients: {unique_patients}
- Unique Encounters: {unique_encounters}
- Total Base Scenarios: {total_scenarios}
- Total Exported Tasks: {total_tasks}

## Task Distribution by Patient Split
```json
{json.dumps(dict(task_counts), indent=2)}
```

## Tasks by Task Family
```json
{json.dumps(dict(task_family_counts), indent=2)}
```

## Tasks by Scenario Family
```json
{json.dumps(dict(scenario_family_counts), indent=2)}
```

## Tasks by Language
```json
{json.dumps(dict(language_counts), indent=2)}
```

## Tasks by Input Mode
```json
{json.dumps(dict(input_mode_counts), indent=2)}
```
"""
    (DATASET_VERSION_DIR / "DATASET_PILOT_REPORT.md").write_text(pilot)
    
    print("Independent Reports generated successfully based on authoritative artifacts.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)

