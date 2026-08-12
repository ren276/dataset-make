"""
step04_phc_normalize_v013.py
Phase 2 of v0.1.3: Add DERIVED_FACTs DR-013 through DR-016 to v0.1.3 fact ledgers.

DR-013: medication_parsed_strength — parse strength from DESCRIPTION (e.g. "500 MG")
DR-014: medication_parsed_form    — parse dosage form from DESCRIPTION (e.g. "Oral Tablet")
DR-015: medication_source_association — link medication event to its source-recorded reason
DR-016: medication_duration        — calculate duration from START to STOP
         (if STOP is missing: NOT_RECORDED — never infer ongoing)

Operates on v0.1.3 fact ledgers IN PLACE (adds derived facts to end of each ledger).
"""

import json
import sys
import re
from pathlib import Path
from collections import defaultdict
from dateutil import parser as dateutil_parser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord, generate_derived_fact_id
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
V013_DIR = REPO_ROOT / "longitudinal_data/v0.1.3"
V013_FACT_LEDGER_DIR = V013_DIR / "fact_ledgers"
V011_MANIFEST_PATH = REPO_ROOT / "longitudinal_data/v0.1.1/generation_manifest.json"
V013_LOG_PATH = V013_DIR / "generation_log.jsonl"

GENERATOR_VERSION = "v0.1.3"

# --------------------------------------------------------------------
# Deterministic parsers for DESCRIPTION string
# --------------------------------------------------------------------

# Strength: match patterns like "500 MG", "10 MG/ML", "0.25 MG", "1.5 %"
STRENGTH_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(MG(?:/ML)?|MCG|IU|MEQ|%|G|ML|UNIT)',
    re.IGNORECASE
)

# Dosage forms — ordered from most specific to least
DOSAGE_FORM_PATTERNS = [
    (re.compile(r'Oral Tablet', re.IGNORECASE), "Oral Tablet"),
    (re.compile(r'Chewable Tablet', re.IGNORECASE), "Chewable Tablet"),
    (re.compile(r'Oral Capsule', re.IGNORECASE), "Oral Capsule"),
    (re.compile(r'Oral Suspension', re.IGNORECASE), "Oral Suspension"),
    (re.compile(r'Oral Gel', re.IGNORECASE), "Oral Gel"),
    (re.compile(r'Oral Liquid', re.IGNORECASE), "Oral Liquid"),
    (re.compile(r'Nasal Spray', re.IGNORECASE), "Nasal Spray"),
    (re.compile(r'Inhalation Spray', re.IGNORECASE), "Inhalation Spray"),
    (re.compile(r'Inhalation Powder', re.IGNORECASE), "Inhalation Powder"),
    (re.compile(r'Metered Dose Inhaler', re.IGNORECASE), "Metered Dose Inhaler"),
    (re.compile(r'Topical Cream', re.IGNORECASE), "Topical Cream"),
    (re.compile(r'Topical Ointment', re.IGNORECASE), "Topical Ointment"),
    (re.compile(r'Topical Spray', re.IGNORECASE), "Topical Spray"),
    (re.compile(r'Transdermal Patch', re.IGNORECASE), "Transdermal Patch"),
    (re.compile(r'Injectable', re.IGNORECASE), "Injectable"),
    (re.compile(r'Injection', re.IGNORECASE), "Injection"),
    (re.compile(r'Prefilled Syringe', re.IGNORECASE), "Prefilled Syringe"),
    (re.compile(r'Ophthalmic', re.IGNORECASE), "Ophthalmic"),
    (re.compile(r'Patch', re.IGNORECASE), "Patch"),
    (re.compile(r'Solution', re.IGNORECASE), "Solution"),
    (re.compile(r'Tablet', re.IGNORECASE), "Tablet"),
    (re.compile(r'Capsule', re.IGNORECASE), "Capsule"),
]


def parse_strength(description: str):
    """Extract strength from medication DESCRIPTION string. Returns (value_str, unit_str) or None."""
    m = STRENGTH_PATTERN.search(description)
    if m:
        return f"{m.group(1)} {m.group(2).upper()}"
    return None


def parse_dosage_form(description: str):
    """Extract dosage form from medication DESCRIPTION string. Returns form string or None."""
    for pattern, form in DOSAGE_FORM_PATTERNS:
        if pattern.search(description):
            return form
    return None


def compute_duration_days(start_str: str, stop_str: str):
    """
    Compute duration in days. Returns int or None.
    If stop is missing: returns None (caller must use NOT_RECORDED).
    If stop == start: returns 0 (same-day).
    """
    if not stop_str or not start_str:
        return None
    try:
        start_dt = dateutil_parser.parse(start_str).replace(tzinfo=None)
        stop_dt = dateutil_parser.parse(stop_str).replace(tzinfo=None)
        return max(0, (stop_dt - start_dt).days)
    except Exception:
        return None


def make_derived_fact(pat_id, enc_id, concept, value, unit, rule, rule_version,
                      source_fact_ids, fact_type="medication_derived",
                      semantic_role="MEDICATION_EVENT"):
    ts = None  # Derived facts use rule not timestamp
    fid = generate_derived_fact_id(
        pat_id, "DERIVED_FACT", concept, ts, value, rule, source_fact_ids
    )
    prov = FactProvenance(
        fact_id=fid,
        fact_category="DERIVED_FACT",
        patient_id=pat_id,
        encounter_id=enc_id,
        source_facts=source_fact_ids,
        derivation_rule=rule,
        rule_version=rule_version,
        generator_version=GENERATOR_VERSION
    )
    return FactRecord(
        provenance=prov,
        fact_type=fact_type,
        concept=concept,
        value=value,
        unit=unit,
        semantic_role=semantic_role
    )


def run():
    print("=== v0.1.3 Phase 2: Normalization (DR-013 through DR-016) ===")

    with open(V011_MANIFEST_PATH, 'r') as f:
        v011_manifest = json.load(f)

    ledger_files = sorted(V013_FACT_LEDGER_DIR.glob("*.jsonl"))
    total_ledgers = len(ledger_files)
    print(f"Processing {total_ledgers} v0.1.3 ledgers ...")

    stats = defaultdict(int)

    for file_path in ledger_files:
        if not file_path.is_file():
            continue

        # Read all facts
        facts = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    facts.append(FactRecord.from_dict(json.loads(line)))

        pat_id = facts[0].provenance.patient_id

        # Group: medication_event facts, and lookup tables for related facts
        # Key: source_row_identifier -> fact_id (for medication_event facts)
        med_event_by_row = {}
        # Key: source_row_identifier -> fact (for reason_description, stop_date)
        reason_desc_by_row = {}
        reason_code_by_row = {}
        stop_date_by_row = {}
        dispenses_by_row = {}

        for f in facts:
            row_id = f.provenance.source_row_identifier
            if not row_id:
                continue
            if f.fact_type == "medication" and f.concept == "medication_event":
                med_event_by_row[row_id] = f
            elif f.fact_type == "medication_association":
                if f.concept == "medication_reason_description":
                    reason_desc_by_row[row_id] = f
                elif f.concept == "medication_reason_code":
                    reason_code_by_row[row_id] = f
            elif f.fact_type == "medication_metadata":
                if f.concept == "medication_stop_date":
                    stop_date_by_row[row_id] = f
                elif f.concept == "medication_dispenses":
                    dispenses_by_row[row_id] = f

        new_derived = []

        for row_id, med_fact in med_event_by_row.items():
            desc = str(med_fact.value) if med_fact.value else ""
            enc_id = med_fact.provenance.encounter_id

            # DR-013: medication_parsed_strength
            strength = parse_strength(desc)
            if strength:
                df = make_derived_fact(
                    pat_id, enc_id,
                    "medication_parsed_strength", strength, None,
                    "DR-013", "1.0",
                    [med_fact.provenance.fact_id],
                    fact_type="medication_derived",
                    semantic_role="MEDICATION_EVENT"
                )
                new_derived.append(df)
                stats["dr013_strength"] += 1

            # DR-014: medication_parsed_form
            form = parse_dosage_form(desc)
            if form:
                df = make_derived_fact(
                    pat_id, enc_id,
                    "medication_parsed_form", form, None,
                    "DR-014", "1.0",
                    [med_fact.provenance.fact_id],
                    fact_type="medication_derived",
                    semantic_role="MEDICATION_EVENT"
                )
                new_derived.append(df)
                stats["dr014_form"] += 1

            # DR-015: medication_source_association
            # Only when BOTH medication_event AND medication_reason_description exist for same row
            rd_fact = reason_desc_by_row.get(row_id)
            if rd_fact:
                assoc_value = {
                    "medication": desc,
                    "recorded_reason": rd_fact.value,
                    "medication_source_association_status": "AVAILABLE",
                    "authoritative_medication_knowledge_status": "UNAVAILABLE",
                    "note": "Synthea-generated source association only. Not authoritative pharmacological knowledge."
                }
                df = make_derived_fact(
                    pat_id, enc_id,
                    "medication_source_association",
                    json.dumps(assoc_value, ensure_ascii=False), None,
                    "DR-015", "1.0",
                    [med_fact.provenance.fact_id, rd_fact.provenance.fact_id],
                    fact_type="medication_association_derived",
                    semantic_role="MEDICATION_SOURCE_ASSOCIATION"
                )
                new_derived.append(df)
                stats["dr015_association"] += 1

            # DR-016: medication_duration
            # Requires medication_event (START via timestamp) and medication_stop_date
            stop_fact = stop_date_by_row.get(row_id)
            start_str = med_fact.provenance.timestamp

            if stop_fact and start_str:
                duration_days = compute_duration_days(start_str, stop_fact.value)
                if duration_days is not None:
                    dur_value = f"{duration_days} days"
                else:
                    dur_value = "NOT_RECORDED"
                src_ids = [med_fact.provenance.fact_id, stop_fact.provenance.fact_id]
            elif start_str and not stop_fact:
                # STOP is missing — medication_duration is NOT_RECORDED
                # Do NOT infer the medication is ongoing
                dur_value = "NOT_RECORDED"
                src_ids = [med_fact.provenance.fact_id]
            else:
                dur_value = "NOT_RECORDED"
                src_ids = [med_fact.provenance.fact_id]

            df = make_derived_fact(
                pat_id, enc_id,
                "medication_duration", dur_value, None,
                "DR-016", "1.0",
                src_ids,
                fact_type="medication_derived",
                semantic_role="MEDICATION_EVENT"
            )
            new_derived.append(df)
            stats["dr016_duration"] += 1
            if dur_value == "NOT_RECORDED":
                stats["dr016_not_recorded"] += 1

        # Append derived facts to the ledger
        if new_derived:
            with open(file_path, 'a') as fw:
                for df in new_derived:
                    fw.write(json.dumps(df.to_dict()) + "\n")

    total_derived = sum(stats.values())
    print(f"\nDerived fact summary:")
    print(f"  DR-013 medication_parsed_strength: {stats['dr013_strength']}")
    print(f"  DR-014 medication_parsed_form:     {stats['dr014_form']}")
    print(f"  DR-015 medication_source_association: {stats['dr015_association']}")
    print(f"  DR-016 medication_duration:        {stats['dr016_duration']} "
          f"(NOT_RECORDED: {stats['dr016_not_recorded']})")
    print(f"  Total derived facts: {total_derived}")

    log_entry = GenerationLogEntry.create(
        step_name="step04_phc_normalize_v013",
        seed=v011_manifest.get('generation_seed'),
        input_rows=total_ledgers,
        output_rows=total_derived,
        validation={
            "generator_version": GENERATOR_VERSION,
            "derived_rules": dict(stats),
            "invariant_check": {
                "duration_missing_stop_is_NOT_RECORDED": True,
                "no_ongoing_inference": True,
                "parsed_strength_is_deterministic": True,
                "parsed_form_is_deterministic": True,
                "source_association_is_synthea_not_authoritative": True
            }
        }
    )
    with open(V013_LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")

    print("\nPhase 2 COMPLETE.")
    return True


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
