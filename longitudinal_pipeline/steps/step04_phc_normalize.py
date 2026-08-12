import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dateutil import parser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord, generate_derived_fact_id
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_VERSION_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
FACT_LEDGER_DIR = DATASET_VERSION_DIR / "fact_ledgers"
LOG_PATH = DATASET_VERSION_DIR / "generation_log.jsonl"
MANIFEST_PATH = DATASET_VERSION_DIR / "generation_manifest.json"

def calculate_age(birthdate_str: str, encounter_date_str: str) -> int:
    try:
        bdate = parser.parse(birthdate_str).replace(tzinfo=None)
        edate = parser.parse(encounter_date_str).replace(tzinfo=None)
        return edate.year - bdate.year - ((edate.month, edate.day) < (bdate.month, bdate.day))
    except Exception:
        return -1

def assign_semantic_role(fact: FactRecord) -> str:
    ft = fact.fact_type
    desc = str(fact.value).lower()
    
    if ft == "demographic":
        return "DEMOGRAPHIC"
    if ft == "encounter_metadata":
        return "ENCOUNTER_METADATA"
    if ft == "medication":
        return "MEDICATION_EVENT"
    if ft == "allergy":
        return "ALLERGY"
    if ft == "procedure":
        return "PROCEDURE"
    if ft == "immunization":
        return "IMMUNIZATION"
    if ft == "careplan":
        return "CAREPLAN"
    if ft == "condition":
        if "medication review" in desc or "encounter" in desc or "examination" in desc or "screening" in desc:
            return "ENCOUNTER_METADATA"
        if "history of" in desc or "past history" in desc:
            return "MEDICAL_HISTORY"
        if "refugee" in desc or "employment" in desc or "education" in desc or "social" in desc or "person" in desc or "housing" in desc:
            return "SOCIAL_HISTORY"
        if "finding" in desc:
            return "CLINICAL_FINDING"
        if "symptom" in desc:
            return "SYMPTOM"
        if "disorder" in desc or "disease" in desc or "syndrome" in desc or "infection" in desc or "itis" in desc or "hypertension" in desc or "diabetes" in desc or "asthma" in desc or "neoplasm" in desc or "carcinoma" in desc:
            return "DIAGNOSIS"
        if "situation" in desc:
            return "OTHER"
        return "DIAGNOSIS" # Default for actual clinical conditions
    if ft == "observation":
        if fact.concept in ["Diastolic Blood Pressure", "Systolic Blood Pressure", "Heart rate", "Respiratory rate", "Body Mass Index", "Body Weight", "Body Height"]:
            return "VITAL_SIGN"
        return "LAB_RESULT"
    return "OTHER"

def run():
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    total_derived = 0
    total_ledgers = 0
    
    print("Normalizing ledgers, assigning semantic roles, and calculating DERIVED_FACTs...")
    for file_path in sorted(FACT_LEDGER_DIR.glob("*.jsonl")):
        if not file_path.is_file():
            continue
            
        facts = []
        with open(file_path, 'r') as f:
            for line in f:
                facts.append(FactRecord.from_dict(json.loads(line)))
                
        # Phase 2: Semantic Roles
        for fact in facts:
            if fact.provenance.fact_category == "SOURCE_FACT":
                fact.semantic_role = assign_semantic_role(fact)
                
        new_derived_facts = []
        
        # 1. Gather context
        pat_birth_fact = next((f for f in facts if f.concept == "birthdate_source"), None)
        pat_gender_fact = next((f for f in facts if f.concept == "gender_source"), None)
        
        generator_version = manifest.get("canonical_normalization_version", manifest.get("generator_version", "v0.1.1"))
        
        # 2. Derive DR-002: Biological Sex
        if pat_gender_fact:
            canonical_sex = "M" if pat_gender_fact.value == "M" else ("F" if pat_gender_fact.value == "F" else "UNKNOWN")
            src_ids = [pat_gender_fact.provenance.fact_id]
            fid = generate_derived_fact_id(pat_gender_fact.provenance.patient_id, "DERIVED_FACT", "biological_sex", None, canonical_sex, "DR-002", src_ids)
            prov = FactProvenance(
                fact_id=fid,
                fact_category="DERIVED_FACT",
                patient_id=pat_gender_fact.provenance.patient_id,
                encounter_id=None,
                source_facts=src_ids,
                derivation_rule="DR-002",
                rule_version="1.0",
                generator_version=generator_version
            )
            new_derived_facts.append(FactRecord(provenance=prov, fact_type="demographic", concept="biological_sex", value=canonical_sex, semantic_role="DEMOGRAPHIC"))
            
        # Group facts by encounter
        encounters = defaultdict(list)
        for f in facts:
            if f.provenance.encounter_id:
                encounters[f.provenance.encounter_id].append(f)
                
        # 3. Process Encounter level derivations
        for enc_id, enc_facts in encounters.items():
            enc_class_fact = next((f for f in enc_facts if f.concept == "encounter_class"), None)
            enc_date_str = enc_class_fact.provenance.timestamp if enc_class_fact else None
            
            # DR-001: Age at encounter
            if pat_birth_fact and enc_date_str:
                age = calculate_age(pat_birth_fact.value, enc_date_str)
                if age >= 0:
                    src_ids = [pat_birth_fact.provenance.fact_id, enc_class_fact.provenance.fact_id]
                    fid = generate_derived_fact_id(pat_birth_fact.provenance.patient_id, "DERIVED_FACT", "age_at_encounter", enc_date_str, age, "DR-001", src_ids)
                    prov = FactProvenance(
                        fact_id=fid,
                        fact_category="DERIVED_FACT",
                        patient_id=pat_birth_fact.provenance.patient_id,
                        encounter_id=enc_id,
                        source_facts=src_ids,
                        derivation_rule="DR-001",
                        rule_version="1.0",
                        generator_version=generator_version
                    )
                    new_derived_facts.append(FactRecord(provenance=prov, fact_type="demographic", concept="age_at_encounter", value=age, unit="years", semantic_role="DEMOGRAPHIC"))
                    
            # Chief Complaint: explicitly NOT_RECORDED if absent
            src_ids = [enc_class_fact.provenance.fact_id] if enc_class_fact else []
            pat_id_cc = enc_class_fact.provenance.patient_id if enc_class_fact else "unknown"
            fid = generate_derived_fact_id(pat_id_cc, "DERIVED_FACT", "chief_complaint", enc_date_str, "NOT_RECORDED", "DR-CHIEF-COMPLAINT-MISSING", src_ids)
            prov_cc = FactProvenance(
                fact_id=fid,
                fact_category="DERIVED_FACT",
                patient_id=pat_id_cc,
                encounter_id=enc_id,
                source_facts=src_ids,
                derivation_rule="DR-CHIEF-COMPLAINT-MISSING",
                rule_version="1.0",
                generator_version=generator_version
            )
            new_derived_facts.append(FactRecord(provenance=prov_cc, fact_type="clinical", concept="chief_complaint", value="NOT_RECORDED", semantic_role="SYMPTOM"))
            
            # DR-004: Condition Duration
            for f in enc_facts:
                if f.fact_type == "condition":
                    cond_start_str = f.provenance.timestamp
                    if cond_start_str and enc_date_str:
                        duration_days = (parser.parse(enc_date_str).replace(tzinfo=None) - parser.parse(cond_start_str).replace(tzinfo=None)).days
                        bucket = "today" if duration_days == 0 else ("few_days" if duration_days < 7 else ("week_plus" if duration_days < 90 else "chronic"))
                        src_ids = [f.provenance.fact_id]
                        if enc_class_fact: src_ids.append(enc_class_fact.provenance.fact_id)
                        fid = generate_derived_fact_id(f.provenance.patient_id, "DERIVED_FACT", "condition_duration_bucket", enc_date_str, bucket, "DR-004", src_ids)
                        prov = FactProvenance(
                            fact_id=fid,
                            fact_category="DERIVED_FACT",
                            patient_id=f.provenance.patient_id,
                            encounter_id=enc_id,
                            source_facts=src_ids,
                            derivation_rule="DR-004",
                            rule_version="1.0",
                            generator_version=generator_version
                        )
                        new_derived_facts.append(FactRecord(provenance=prov, fact_type="condition_metadata", concept="condition_duration_bucket", value=bucket, semantic_role="OTHER"))
                        
                # DR-005A: Vital Abnormality
                if f.fact_type == "observation" and f.concept in ["Diastolic Blood Pressure", "Systolic Blood Pressure", "Heart rate", "Respiratory rate"]:
                    abnormal = "abnormal"
                    try:
                        val = float(f.value)
                        if f.concept == "Diastolic Blood Pressure" and 60 <= val <= 90: abnormal = "normal"
                        elif f.concept == "Systolic Blood Pressure" and 90 <= val <= 140: abnormal = "normal"
                        elif f.concept == "Heart rate" and 60 <= val <= 100: abnormal = "normal"
                        elif f.concept == "Respiratory rate" and 12 <= val <= 20: abnormal = "normal"
                    except:
                        pass
                    src_ids = [f.provenance.fact_id]
                    fid = generate_derived_fact_id(f.provenance.patient_id, "DERIVED_FACT", f"{f.concept}_classification", enc_date_str, abnormal, "DR-005A", src_ids)
                    prov = FactProvenance(
                        fact_id=fid,
                        fact_category="DERIVED_FACT",
                        patient_id=f.provenance.patient_id,
                        encounter_id=enc_id,
                        source_facts=src_ids,
                        derivation_rule="DR-005A",
                        rule_version="1.0",
                        generator_version=generator_version
                    )
                    src_ids = [f.provenance.fact_id]
                    fid2 = generate_derived_fact_id(f.provenance.patient_id, "DERIVED_FACT", "vital_abnormality", enc_date_str, abnormal, "DR-005A", src_ids)
                    prov2 = FactProvenance(
                        fact_id=fid2,
                        fact_category="DERIVED_FACT",
                        patient_id=f.provenance.patient_id,
                        encounter_id=enc_id,
                        source_facts=src_ids,
                        derivation_rule="DR-005A",
                        rule_version="1.0",
                        generator_version=generator_version
                    )
                    new_derived_facts.append(FactRecord(provenance=prov2, fact_type="observation_metadata", concept="vital_abnormality", value=abnormal, semantic_role="CLINICAL_FINDING"))
                        
        total_derived += len(new_derived_facts)
        total_ledgers += 1
        facts.extend(new_derived_facts)
        
        with open(file_path, 'w') as fw:
            for f_rec in facts:
                fw.write(json.dumps(f_rec.to_dict()) + "\n")

    log_entry = GenerationLogEntry.create(
        step_name="step04_phc_normalize",
        seed=manifest.get('generation_seed'),
        input_rows=total_ledgers,
        output_rows=total_derived,
        validation={"derived_fact_count": total_derived, "processed_ledgers": total_ledgers}
    )
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")
        
    print(f"PHC Canonical Normalization complete. Generated {total_derived} derived facts across {total_ledgers} ledgers.")
    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
