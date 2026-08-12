import pandas as pd
import json
import sys
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.0"
ADAPTED_DIR = DATASET_VERSION_DIR / "source/adapted"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
CONFIG_DIR = REPO_ROOT / "longitudinal_pipeline/config"

class PHCNormalizer:
    def __init__(self):
        # We assume the config file exists and load it to verify version
        pass
        
    def normalize_patient(self, pat_row) -> list:
        facts = []
        pat_id = pat_row['synthetic_patient_id']
        
        # SOURCE_FACT: demographic
        prov_demo = FactProvenance(
            fact_category="SOURCE_FACT",
            patient_id=pat_id,
            source_file="patients.csv",
            source_field="GENDER"
        )
        facts.append(FactRecord(
            provenance=prov_demo,
            fact_type="demographic",
            concept="gender_source",
            value=pat_row['GENDER']
        ))
        
        # DERIVED_FACT: DR-002 biological_sex
        prov_sex = FactProvenance(
            fact_category="DERIVED_FACT",
            patient_id=pat_id,
            derivation_rule="DR-002",
            rule_version="1.0",
            source_facts=[prov_demo.fact_id]
        )
        sex = "M" if pat_row['GENDER'] == "M" else "F"
        facts.append(FactRecord(
            provenance=prov_sex,
            fact_type="demographic",
            concept="biological_sex",
            value=sex
        ))
        return facts
        
    def normalize_encounter(self, enc_row, pat_id, pat_dob) -> list:
        facts = []
        enc_id = enc_row['Id']
        enc_date = enc_row['START']
        
        # SOURCE_FACT: encounter
        prov_enc = FactProvenance(
            fact_category="SOURCE_FACT",
            patient_id=pat_id,
            encounter_id=enc_id,
            timestamp=enc_date,
            source_file="encounters.csv",
            source_field="ENCOUNTERCLASS"
        )
        facts.append(FactRecord(
            provenance=prov_enc,
            fact_type="encounter_metadata",
            concept="encounter_class_source",
            value=enc_row['ENCOUNTERCLASS']
        ))
        
        # DERIVED_FACT: DR-012 encounter_type
        prov_enc_type = FactProvenance(
            fact_category="DERIVED_FACT",
            patient_id=pat_id,
            encounter_id=enc_id,
            timestamp=enc_date,
            derivation_rule="DR-012",
            rule_version="1.0",
            source_facts=[prov_enc.fact_id]
        )
        facts.append(FactRecord(
            provenance=prov_enc_type,
            fact_type="encounter_metadata",
            concept="canonical_encounter_type",
            value=enc_row.get('phc_encounter_type', 'UNKNOWN')
        ))
        
        # DERIVED_FACT: DR-001 age_at_encounter
        if pd.notnull(pat_dob) and pd.notnull(enc_date):
            ed = pd.Timestamp(enc_date).tz_localize(None)
            bd = pd.Timestamp(pat_dob).tz_localize(None)
            age = (ed - bd).days // 365
            
            prov_age = FactProvenance(
                fact_category="DERIVED_FACT",
                patient_id=pat_id,
                encounter_id=enc_id,
                timestamp=enc_date,
                derivation_rule="DR-001",
                rule_version="1.0",
                source_facts=[] # Needs birthdate fact and enc date fact
            )
            facts.append(FactRecord(
                provenance=prov_age,
                fact_type="demographic",
                concept="age_at_encounter",
                value=int(age)
            ))
        
        return facts

def run():
    FACT_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    seed = manifest['random_seed']
    
    print("Loading adapted source data...")
    patients_df = pd.read_csv(ADAPTED_DIR / "patients.csv")
    encounters_df = pd.read_csv(ADAPTED_DIR / "encounters.csv")
    
    normalizer = PHCNormalizer()
    
    total_facts = 0
    # Process per patient
    for i, pat_row in tqdm(patients_df.iterrows(), total=len(patients_df)):
        pat_id = pat_row['synthetic_patient_id']
        raw_id = pat_row['Id']
        pat_dob = pat_row['BIRTHDATE']
        
        patient_facts = normalizer.normalize_patient(pat_row)
        
        # get encounters
        pat_encs = encounters_df[encounters_df['PATIENT'] == raw_id]
        for _, enc_row in pat_encs.iterrows():
            patient_facts.extend(normalizer.normalize_encounter(enc_row, pat_id, pat_dob))
            
        # Write ledger
        ledger_path = FACT_LEDGER_DIR / f"{pat_id}.jsonl"
        with open(ledger_path, 'w') as f:
            for fact in patient_facts:
                f.write(json.dumps(fact.to_dict()) + "\n")
        total_facts += len(patient_facts)
                
    log_entry = GenerationLogEntry.create(
        step_name="step03_phc_normalize",
        seed=seed,
        input_rows=len(patients_df),
        output_rows=total_facts,
        validation={"num_ledgers": len(patients_df)}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print(f"PHC normalization complete. {total_facts} facts written to {len(patients_df)} ledgers.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
