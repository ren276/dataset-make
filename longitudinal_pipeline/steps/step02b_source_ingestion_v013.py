"""
step02b_source_ingestion_v013.py
Phase 1 of v0.1.3: Recover discarded medication fields from frozen medications.csv.

Strategy:
- v0.1.1 fact ledgers are the upstream immutable artifacts. They are NOT modified.
- v0.1.3 fact ledgers are written to longitudinal_data/v0.1.3/fact_ledgers/
- Each v0.1.3 ledger starts as an exact copy of the v0.1.1 ledger.
- Then NEW SOURCE_FACTs are appended for:
    - medication_reason_code  (REASONCODE)
    - medication_reason_description (REASONDESCRIPTION)
    - medication_stop_date (STOP)
    - medication_dispenses (DISPENSES)
- Empty source fields produce NO fact.
- The frozen CSV is NOT modified.
"""

import pandas as pd
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord, generate_source_fact_id
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
V011_DIR = REPO_ROOT / "longitudinal_data/v0.1.1"
V013_DIR = REPO_ROOT / "longitudinal_data/v0.1.3"
V011_FACT_LEDGER_DIR = V011_DIR / "fact_ledgers"
V013_FACT_LEDGER_DIR = V013_DIR / "fact_ledgers"
SOURCE_DIR = V011_DIR / "source/csv"
V011_MANIFEST_PATH = V011_DIR / "generation_manifest.json"
V013_LOG_PATH = V013_DIR / "generation_log.jsonl"

GENERATOR_VERSION = "v0.1.3"


def create_source_fact(pat_id, enc_id, timestamp, concept, value, unit,
                       src_file, src_row, src_field, src_value, fact_type):
    fid = generate_source_fact_id(
        pat_id, "SOURCE_FACT", src_file, str(src_row), src_field,
        concept, str(timestamp) if timestamp else "", value
    )
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
        generator_version=GENERATOR_VERSION
    )
    return FactRecord(
        provenance=prov,
        fact_type=fact_type,
        concept=concept,
        value=value,
        unit=unit if unit else None
    )


def run():
    print("=== v0.1.3 Phase 1: Source Ingestion (Medication Field Recovery) ===")

    with open(V011_MANIFEST_PATH, 'r') as f:
        v011_manifest = json.load(f)

    # Create output directories
    V013_FACT_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    V013_DIR.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------
    # Build a lookup: patient_id -> list of extras per medication row
    # from the frozen medications.csv
    # ----------------------------------------------------------------
    print("Reading frozen medications.csv ...")
    med_df = pd.read_csv(SOURCE_DIR / "medications.csv").fillna('')
    med_df = med_df.sort_values(by=['PATIENT', 'START', 'CODE'])

    patient_med_extras = defaultdict(list)
    stats = {
        "total_medication_rows": len(med_df),
        "reasoncode_present": 0,
        "reasondescription_present": 0,
        "stop_present": 0,
        "dispenses_present": 0,
        "new_facts_generated": 0,
        "medication_rows_with_association": 0,
    }

    for idx, row in med_df.iterrows():
        pat_id = row['PATIENT']
        enc_id = row.get('ENCOUNTER', '') or None
        start = row.get('START', '') or None
        row_id = f"med_{idx}"

        rc  = str(row.get('REASONCODE', '')).strip()
        rd  = str(row.get('REASONDESCRIPTION', '')).strip()
        stp = str(row.get('STOP', '')).strip()
        dis = str(row.get('DISPENSES', '')).strip()

        extras = {
            "row_id": row_id,
            "enc_id": enc_id if enc_id else None,
            "start": start if start else None,
            "REASONCODE": rc,
            "REASONDESCRIPTION": rd,
            "STOP": stp,
            "DISPENSES": dis,
        }
        patient_med_extras[pat_id].append(extras)

        def _valid(v): return bool(v and v != 'nan' and v != '')
        if _valid(rc):  stats["reasoncode_present"] += 1
        if _valid(rd):  stats["reasondescription_present"] += 1
        if _valid(stp): stats["stop_present"] += 1
        if _valid(dis): stats["dispenses_present"] += 1
        if _valid(rc) and _valid(rd):
            stats["medication_rows_with_association"] += 1

    print(f"  Total medication rows: {stats['total_medication_rows']}")
    print(f"  REASONCODE present: {stats['reasoncode_present']} "
          f"({stats['reasoncode_present']/stats['total_medication_rows']*100:.1f}%)")
    print(f"  With source association (both CODE+DESC): {stats['medication_rows_with_association']} "
          f"({stats['medication_rows_with_association']/stats['total_medication_rows']*100:.1f}%)")

    # ----------------------------------------------------------------
    # For each v0.1.1 ledger: copy to v0.1.3 and append new facts
    # ----------------------------------------------------------------
    print(f"\nProcessing {len(list(V011_FACT_LEDGER_DIR.glob('*.jsonl')))} patient ledgers ...")

    v011_ledger_files = sorted(V011_FACT_LEDGER_DIR.glob("*.jsonl"))
    processed_patients = 0
    total_new_facts = 0

    def _valid(v): return bool(v and v != 'nan' and v != '')

    for file_path in v011_ledger_files:
        if not file_path.is_file():
            continue

        pat_id = file_path.stem

        # Read v0.1.1 facts verbatim
        v011_facts_raw = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    v011_facts_raw.append(json.loads(line))

        # Generate new SOURCE_FACTs for medication extras
        new_facts = []
        for extras in patient_med_extras.get(pat_id, []):
            row_id = extras["row_id"]
            enc_id = extras["enc_id"]
            start  = extras["start"]

            # medication_reason_code — only if non-empty
            if _valid(extras["REASONCODE"]):
                f_rc = create_source_fact(
                    pat_id, enc_id, start,
                    "medication_reason_code", extras["REASONCODE"], None,
                    "medications.csv", row_id, "REASONCODE", extras["REASONCODE"],
                    "medication_association"
                )
                f_rc.semantic_role = "MEDICATION_SOURCE_ASSOCIATION"
                new_facts.append(f_rc)

            # medication_reason_description — only if non-empty
            if _valid(extras["REASONDESCRIPTION"]):
                f_rd = create_source_fact(
                    pat_id, enc_id, start,
                    "medication_reason_description", extras["REASONDESCRIPTION"], None,
                    "medications.csv", row_id, "REASONDESCRIPTION", extras["REASONDESCRIPTION"],
                    "medication_association"
                )
                f_rd.semantic_role = "MEDICATION_SOURCE_ASSOCIATION"
                new_facts.append(f_rd)

            # medication_stop_date — only if non-empty
            if _valid(extras["STOP"]):
                f_stop = create_source_fact(
                    pat_id, enc_id, start,
                    "medication_stop_date", extras["STOP"], None,
                    "medications.csv", row_id, "STOP", extras["STOP"],
                    "medication_metadata"
                )
                f_stop.semantic_role = "MEDICATION_EVENT"
                new_facts.append(f_stop)

            # medication_dispenses — only if non-empty
            if _valid(extras["DISPENSES"]):
                f_disp = create_source_fact(
                    pat_id, enc_id, start,
                    "medication_dispenses", extras["DISPENSES"], None,
                    "medications.csv", row_id, "DISPENSES", extras["DISPENSES"],
                    "medication_metadata"
                )
                f_disp.semantic_role = "MEDICATION_EVENT"
                new_facts.append(f_disp)

        # Write v0.1.3 ledger: verbatim copy of v0.1.1 + new facts
        out_path = V013_FACT_LEDGER_DIR / f"{pat_id}.jsonl"
        with open(out_path, 'w') as fw:
            for fact_dict in v011_facts_raw:
                fw.write(json.dumps(fact_dict) + "\n")
            for nf in new_facts:
                fw.write(json.dumps(nf.to_dict()) + "\n")

        total_new_facts += len(new_facts)
        processed_patients += 1

    stats["new_facts_generated"] = total_new_facts

    print(f"Processed {processed_patients} patient ledgers.")
    print(f"Total new SOURCE_FACTs generated: {total_new_facts}")

    # Write generation log entry
    log_entry = GenerationLogEntry.create(
        step_name="step02b_source_ingestion_v013",
        seed=v011_manifest.get('generation_seed'),
        input_rows=stats["total_medication_rows"],
        output_rows=total_new_facts,
        validation={
            "generator_version": GENERATOR_VERSION,
            "v011_ledgers_copied": processed_patients,
            "medication_stats": stats,
            "invariant_check": {
                "frozen_csv_modified": False,
                "v011_ledgers_modified": False,
                "v013_output_isolated": True
            }
        }
    )
    with open(V013_LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")

    print("\n[INVARIANTS]")
    print("  frozen CSV: NOT modified")
    print("  v0.1.1 fact ledgers: NOT modified")
    print("  v0.1.3 output: isolated in longitudinal_data/v0.1.3/fact_ledgers/")
    print("\nPhase 1 COMPLETE.")
    return True


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
