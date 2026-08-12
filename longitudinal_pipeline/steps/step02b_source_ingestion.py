import pandas as pd
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord, generate_source_fact_id
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
SOURCE_DIR = DATASET_VERSION_DIR / "source/csv"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"

class IngestionTracker:
    def __init__(self):
        self.stats = defaultdict(lambda: {"source_rows": 0, "consumed": 0, "excluded": 0, "unmapped": 0, "source_facts": 0, "excluded_reasons": defaultdict(int)})
        
    def record_consumed(self, resource: str, facts_generated: int):
        self.stats[resource]["consumed"] += 1
        self.stats[resource]["source_facts"] += facts_generated
        
    def record_excluded(self, resource: str, reason: str):
        self.stats[resource]["excluded"] += 1
        self.stats[resource]["excluded_reasons"][reason] += 1
        
    def record_unmapped(self, resource: str):
        self.stats[resource]["unmapped"] += 1

class SourceIngester:
    def __init__(self, tracker: IngestionTracker, manifest: dict):
        self.tracker = tracker
        self.manifest = manifest
        self.ledgers = defaultdict(list)
        
    def create_source_fact(self, pat_id, enc_id, timestamp, concept, value, unit, src_file, src_row, src_field, src_value, fact_type):
        fid = generate_source_fact_id(pat_id, "SOURCE_FACT", src_file, str(src_row), src_field, concept, str(timestamp) if timestamp else "", value)
        prov = FactProvenance(
            fact_id=fid,
            fact_category="SOURCE_FACT",
            patient_id=pat_id,
            encounter_id=enc_id,
            timestamp=str(timestamp) if timestamp else None,
            source_file=src_file,
            source_row_identifier=str(src_row),
            source_field=src_field,
            source_value=str(src_value),
            generator_version=self.manifest.get("source_ingestion_version", self.manifest.get("generator_version", "v0.1.1"))
        )
        return FactRecord(
            provenance=prov,
            fact_type=fact_type,
            concept=concept,
            value=value,
            unit=unit if unit else None
        )

    def ingest_patients(self):
        df = pd.read_csv(SOURCE_DIR / "patients.csv").fillna('')
        df = df.sort_values(by=['Id'])
        self.tracker.stats["patients"]["source_rows"] = len(df)
        for _, row in df.iterrows():
            pat_id = row['Id']
            f1 = self.create_source_fact(pat_id, None, None, "birthdate_source", row['BIRTHDATE'], None, "patients.csv", pat_id, "BIRTHDATE", row['BIRTHDATE'], "demographic")
            f2 = self.create_source_fact(pat_id, None, None, "gender_source", row['GENDER'], None, "patients.csv", pat_id, "GENDER", row['GENDER'], "demographic")
            self.ledgers[pat_id].extend([f1, f2])
            self.tracker.record_consumed("patients", 2)
            
    def ingest_encounters(self):
        df = pd.read_csv(SOURCE_DIR / "encounters.csv").fillna('')
        df = df.sort_values(by=['Id', 'START'])
        self.tracker.stats["encounters"]["source_rows"] = len(df)
        for _, row in df.iterrows():
            pat_id = row['PATIENT']
            enc_id = row['Id']
            f1 = self.create_source_fact(pat_id, enc_id, row['START'], "encounter_class", row['ENCOUNTERCLASS'], None, "encounters.csv", enc_id, "ENCOUNTERCLASS", row['ENCOUNTERCLASS'], "encounter_metadata")
            f2 = self.create_source_fact(pat_id, enc_id, row['START'], "encounter_description", row['DESCRIPTION'], None, "encounters.csv", enc_id, "DESCRIPTION", row['DESCRIPTION'], "encounter_metadata")
            self.ledgers[pat_id].extend([f1, f2])
            self.tracker.record_consumed("encounters", 2)
            
    def ingest_conditions(self):
        df = pd.read_csv(SOURCE_DIR / "conditions.csv").fillna('')
        df = df.sort_values(by=['PATIENT', 'START', 'CODE'])
        self.tracker.stats["conditions"]["source_rows"] = len(df)
        for idx, row in df.iterrows():
            pat_id = row['PATIENT']
            enc_id = row.get('ENCOUNTER', '')
            row_id = f"cond_{idx}"
            f1 = self.create_source_fact(pat_id, enc_id if enc_id else None, row['START'], "condition_description", row['DESCRIPTION'], None, "conditions.csv", row_id, "DESCRIPTION", row['DESCRIPTION'], "condition")
            self.ledgers[pat_id].append(f1)
            self.tracker.record_consumed("conditions", 1)

    def ingest_observations(self):
        df = pd.read_csv(SOURCE_DIR / "observations.csv").fillna('')
        df = df.sort_values(by=['PATIENT', 'DATE', 'CODE'])
        self.tracker.stats["observations"]["source_rows"] = len(df)
        for idx, row in df.iterrows():
            pat_id = row['PATIENT']
            enc_id = row.get('ENCOUNTER', '')
            row_id = f"obs_{idx}"
            cat = str(row.get('CATEGORY', ''))
            desc = str(row.get('DESCRIPTION', ''))
            code = str(row.get('CODE', ''))
            
            # Exact deterministic exclusion for Race and Ethnicity
            if code in ['32624-9', '56127-4'] or desc in ['Race', 'Ethnicity']:
                self.tracker.record_excluded("observations", reason="US_DEMOGRAPHIC_EXCLUDED")
            elif cat in ['vital-signs', 'laboratory', 'survey']:
                f1 = self.create_source_fact(pat_id, enc_id if enc_id else None, row['DATE'], row['DESCRIPTION'], row['VALUE'], row.get('UNITS', ''), "observations.csv", row_id, "VALUE", row['VALUE'], "observation")
                self.ledgers[pat_id].append(f1)
                self.tracker.record_consumed("observations", 1)
            else:
                self.tracker.record_excluded("observations", reason="OUT_OF_CANONICAL_SCOPE")

    def ingest_medications(self):
        df = pd.read_csv(SOURCE_DIR / "medications.csv").fillna('')
        df = df.sort_values(by=['PATIENT', 'START', 'CODE'])
        self.tracker.stats["medications"]["source_rows"] = len(df)
        for idx, row in df.iterrows():
            pat_id = row['PATIENT']
            enc_id = row.get('ENCOUNTER', '')
            row_id = f"med_{idx}"
            f1 = self.create_source_fact(pat_id, enc_id if enc_id else None, row['START'], "medication_event", row['DESCRIPTION'], None, "medications.csv", row_id, "DESCRIPTION", row['DESCRIPTION'], "medication")
            self.ledgers[pat_id].append(f1)
            self.tracker.record_consumed("medications", 1)

    def ingest_simple_resource(self, filename: str, concept_col: str, fact_type: str):
        path = SOURCE_DIR / filename
        resource_name = filename.replace('.csv', '')
        if not path.exists():
            return
        df = pd.read_csv(path).fillna('')
        
        date_col = 'DATE' if 'DATE' in df.columns else ('START' if 'START' in df.columns else None)
        sort_cols = ['PATIENT']
        if date_col: sort_cols.append(date_col)
        if 'CODE' in df.columns: sort_cols.append('CODE')
        df = df.sort_values(by=sort_cols)
        
        self.tracker.stats[resource_name]["source_rows"] = len(df)
        for idx, row in df.iterrows():
            pat_id = row['PATIENT']
            enc_id = row.get('ENCOUNTER', '')
            row_id = f"{resource_name}_{idx}"
            timestamp = row[date_col] if date_col else None
            
            f1 = self.create_source_fact(pat_id, enc_id if enc_id else None, timestamp, resource_name, row[concept_col], None, filename, row_id, concept_col, row[concept_col], fact_type)
            self.ledgers[pat_id].append(f1)
            self.tracker.record_consumed(resource_name, 1)

    def write_ledgers(self):
        FACT_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        # Clear out old ledgers to be safe
        for old in FACT_LEDGER_DIR.glob("*.jsonl"):
            old.unlink()
            
        for pat_id, facts in self.ledgers.items():
            out_path = FACT_LEDGER_DIR / f"{pat_id}.jsonl"
            with open(out_path, 'w') as f:
                for fact in facts:
                    f.write(json.dumps(fact.to_dict()) + "\n")

def run():
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    tracker = IngestionTracker()
    ingester = SourceIngester(tracker, manifest)
    
    print("Ingesting patients...")
    ingester.ingest_patients()
    print("Ingesting encounters...")
    ingester.ingest_encounters()
    print("Ingesting conditions...")
    ingester.ingest_conditions()
    print("Ingesting observations...")
    ingester.ingest_observations()
    print("Ingesting medications...")
    ingester.ingest_medications()
    
    print("Ingesting allergies, procedures, immunizations, careplans...")
    ingester.ingest_simple_resource("allergies.csv", "DESCRIPTION", "allergy")
    ingester.ingest_simple_resource("procedures.csv", "DESCRIPTION", "procedure")
    ingester.ingest_simple_resource("immunizations.csv", "DESCRIPTION", "immunization")
    ingester.ingest_simple_resource("careplans.csv", "DESCRIPTION", "careplan")
    
    print("Writing ledgers...")
    ingester.write_ledgers()
    
    failed = False
    print("\n--- Source Coverage Report ---")
    for res, stats in tracker.stats.items():
        reconciled = stats['consumed'] + stats['excluded'] + stats['unmapped']
        if reconciled != stats['source_rows']:
            print(f"FAIL {res}: source_rows({stats['source_rows']}) != reconciled({reconciled})")
            failed = True
        if stats['unmapped'] > 0:
            print(f"FAIL {res}: UNMAPPED > 0 ({stats['unmapped']})")
            failed = True
            
        print(f"{res.upper()}:")
        print(f"  source_rows: {stats['source_rows']}")
        print(f"  consumed: {stats['consumed']}")
        print(f"  excluded_with_reason: {stats['excluded']}")
        for reason, c in stats['excluded_reasons'].items():
            print(f"    - {reason}: {c}")
        print(f"  unmapped: {stats['unmapped']}")
        print(f"  source_facts_generated: {stats['source_facts']}")
        
    if failed:
        print("Coverage Validation FAILED.", file=sys.stderr)
        return False
        
    log_entry = GenerationLogEntry.create(
        step_name="step02b_source_ingestion",
        seed=manifest['generation_seed'],
        input_rows=sum(s['source_rows'] for s in tracker.stats.values()),
        output_rows=sum(s['source_facts'] for s in tracker.stats.values()),
        validation={"coverage": {k: {**v, "excluded_reasons": dict(v["excluded_reasons"])} for k, v in tracker.stats.items()}}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print("Source ingestion complete and coverage fully reconciled.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
