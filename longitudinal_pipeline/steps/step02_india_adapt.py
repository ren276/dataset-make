import pandas as pd
import json
import sys
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from longitudinal_pipeline.adapters.india_geography_adapter import IndiaGeographyAdapter
from longitudinal_pipeline.adapters.india_names_adapter import IndiaNamesAdapter
from longitudinal_pipeline.adapters.india_encounter_adapter import IndiaEncounterAdapter
from longitudinal_pipeline.schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.0"
SYNTHEA_RAW_DIR = DATASET_VERSION_DIR / "source/csv"
ADAPTED_DIR = DATASET_VERSION_DIR / "source/adapted"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
CONFIG_DIR = REPO_ROOT / "longitudinal_pipeline/config"

def run():
    ADAPTED_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    seed = manifest['random_seed']
    
    geo_adapter = IndiaGeographyAdapter(CONFIG_DIR / "india_geography.yaml")
    names_adapter = IndiaNamesAdapter(CONFIG_DIR / "indian_names.yaml")
    encounter_adapter = IndiaEncounterAdapter()
    
    print("Adapting patients...")
    patients_df = pd.read_csv(SYNTHEA_RAW_DIR / "patients.csv")
    
    adapted_patients = []
    
    for i, row in tqdm(patients_df.iterrows(), total=len(patients_df)):
        pat_id = row['Id']
        sex = row['GENDER']
        
        geo = geo_adapter.adapt(pat_id, seed)
        name = names_adapter.adapt(pat_id, sex, geo['state_code'], seed)
        
        # synthetic_patient_id format: SYN-{STATE}-{seq:06d}
        syn_id = f"SYN-{geo['state_code']}-{i+1:06d}"
        
        row_dict = row.to_dict()
        row_dict['synthetic_patient_id'] = syn_id
        row_dict.update(geo)
        row_dict.update(name)
        adapted_patients.append(row_dict)
        
    adapted_patients_df = pd.DataFrame(adapted_patients)
    adapted_patients_df.to_csv(ADAPTED_DIR / "patients.csv", index=False)
    
    print("Adapting encounters...")
    encounters_df = pd.read_csv(SYNTHEA_RAW_DIR / "encounters.csv")
    
    adapted_encounters = []
    for i, row in tqdm(encounters_df.iterrows(), total=len(encounters_df)):
        e_class = row.get('ENCOUNTERCLASS', '')
        desc = row.get('DESCRIPTION', '')
        
        phc_type = encounter_adapter.adapt(e_class, desc)
        
        row_dict = row.to_dict()
        row_dict['phc_encounter_type'] = phc_type
        adapted_encounters.append(row_dict)
        
    adapted_encounters_df = pd.DataFrame(adapted_encounters)
    adapted_encounters_df.to_csv(ADAPTED_DIR / "encounters.csv", index=False)
    
    # Copy over the rest of the CSVs untouched so we have a full adapted folder
    for csv_file in ["conditions.csv", "medications.csv", "observations.csv", "procedures.csv", "allergies.csv", "careplans.csv"]:
        if (SYNTHEA_RAW_DIR / csv_file).exists():
            shutil.copy2(SYNTHEA_RAW_DIR / csv_file, ADAPTED_DIR / csv_file)
            
    validation = {
        "adapted_patients": len(adapted_patients_df),
        "adapted_encounters": len(adapted_encounters_df)
    }
    
    log_entry = GenerationLogEntry.create(
        step_name="step02_india_adapt",
        seed=seed,
        input_rows=len(patients_df),
        output_rows=len(adapted_patients_df),
        validation=validation
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print("India adaptation complete.")
    return True

if __name__ == "__main__":
    import shutil
    ok = run()
    sys.exit(0 if ok else 1)
