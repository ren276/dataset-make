"""
step07_scenario_engine_v013.py
Phase 3 of v0.1.3: Expanded scenario engine.

New scenario rules added vs v0.1.2:
  SC-001a: TF01-R04 medication_retrieval
  SC-001b: TF01-R05 vital_retrieval
  SC-001c: TF01-R06 lab_retrieval
  SC-001d: TF01-R08 allergy_retrieval
  SC-001e: TF01-R07 procedure_retrieval
  SC-001f: TF01-R09 immunization_retrieval
  SC-001g: TF01-R11 first_occurrence (earliest recorded date for a condition)
  SC-001h: TF01-R12 last_occurrence  (latest recorded date for a condition)
  SC-003b: TF03 encounter summary (ENCOUNTER_SUMMARY)
  SC-007b: TF07 clinical output explanation (observation only, non-decision-layer)

All existing v0.1.2 scenarios (SC-001 through SC-013) are preserved.
This engine appends ONLY NEW scenario types not already written by v0.1.2 step07.
"""

import json
import sys
import random
from pathlib import Path
from collections import defaultdict
from dateutil import parser as dateutil_parser
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.fact_ledger import FactProvenance, FactRecord, generate_scenario_fact_id
from schemas.generation_manifest import GenerationLogEntry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
V013_DIR = REPO_ROOT / "longitudinal_data/v0.1.3"
V013_FACT_LEDGER_DIR = V013_DIR / "fact_ledgers"
V013_LOG_PATH = V013_DIR / "generation_log.jsonl"
V011_MANIFEST_PATH = REPO_ROOT / "longitudinal_data/v0.1.1/generation_manifest.json"

GENERATOR_VERSION = "v0.1.3"


def create_scenario(pat_id: str, enc_id: Optional[str], source_facts: list,
                    rule: str, concept: str, value: str, order_matters: bool = False):
    payload = {"text": value}
    fid = generate_scenario_fact_id(pat_id, rule, source_facts, payload, order_matters=order_matters)
    prov = FactProvenance(
        fact_id=fid,
        fact_category="SCENARIO_FACT",
        patient_id=pat_id,
        encounter_id=enc_id,
        source_facts=source_facts,
        scenario_rule=rule,
        rule_version="1.0",
        generator_version=GENERATOR_VERSION
    )
    return FactRecord(
        provenance=prov,
        fact_type="synthetic_scenario",
        concept=concept,
        value=payload,
        semantic_role="OTHER"
    )


def run():
    print("=== v0.1.3 Phase 3: Scenario Engine (New SC Rules) ===")

    with open(V011_MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)

    gen_seed = manifest.get('generation_seed', 42)
    random.seed(gen_seed)

    total_scenarios = 0
    scenarios_per_rule = defaultdict(int)

    ledger_files = sorted(V013_FACT_LEDGER_DIR.glob("*.jsonl"))
    print(f"Processing {len(ledger_files)} v0.1.3 ledgers ...")

    for file_path in ledger_files:
        if not file_path.is_file():
            continue

        facts = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    facts.append(FactRecord.from_dict(json.loads(line)))

        if not facts:
            continue

        pat_id = facts[0].provenance.patient_id

        # Collect existing scenario rule IDs so we don't duplicate
        existing_rules = set()
        for f in facts:
            if f.fact_type == "synthetic_scenario" and f.provenance.scenario_rule:
                existing_rules.add(f.provenance.scenario_rule)

        # Group facts by type
        diagnoses   = [f for f in facts if f.fact_type == "condition" and f.semantic_role == "DIAGNOSIS"]
        vitals      = [f for f in facts if f.semantic_role == "VITAL_SIGN" and f.fact_type == "observation"]
        labs        = [f for f in facts if f.semantic_role == "LAB_RESULT" and f.fact_type == "observation"]
        medications = [f for f in facts if f.fact_type == "medication" and f.concept == "medication_event"]
        allergies   = [f for f in facts if f.fact_type == "allergy"]
        procedures  = [f for f in facts if f.fact_type == "procedure"]
        immunizations = [f for f in facts if f.fact_type == "immunization"]
        observations = [f for f in facts if f.fact_type == "observation"]

        new_scenarios = []

        # ------------------------------------------------------------------
        # SC-001a: TF01-R04 medication_retrieval
        # ------------------------------------------------------------------
        if medications:
            # Group medications by encounter
            meds_by_enc = defaultdict(list)
            for m in medications:
                if m.provenance.encounter_id:
                    meds_by_enc[m.provenance.encounter_id].append(m)
            if meds_by_enc:
                enc_id = random.choice(list(meds_by_enc.keys()))
                enc_meds = meds_by_enc[enc_id]
                src_ids = [m.provenance.fact_id for m in enc_meds[:5]]
                s = create_scenario(
                    pat_id, enc_id, src_ids,
                    "SC-001a", "medication_retrieval",
                    "What medications were recorded during this encounter?",
                    order_matters=False
                )
                new_scenarios.append(s)

        # ------------------------------------------------------------------
        # SC-001b: TF01-R05 vital_retrieval
        # ------------------------------------------------------------------
        if vitals:
            v = random.choice(vitals)
            concept_name = v.concept.lower().replace(" ", "_")
            s = create_scenario(
                pat_id, v.provenance.encounter_id,
                [v.provenance.fact_id],
                "SC-001b", "vital_retrieval",
                f"What was my {v.concept} during this encounter?"
            )
            new_scenarios.append(s)

        # ------------------------------------------------------------------
        # SC-001c: TF01-R06 lab_retrieval
        # ------------------------------------------------------------------
        if labs:
            # Most recent lab result
            labs_with_ts = [l for l in labs if l.provenance.timestamp]
            if labs_with_ts:
                try:
                    latest_lab = max(
                        labs_with_ts,
                        key=lambda x: dateutil_parser.parse(x.provenance.timestamp).replace(tzinfo=None)
                    )
                    s = create_scenario(
                        pat_id, latest_lab.provenance.encounter_id,
                        [latest_lab.provenance.fact_id],
                        "SC-001c", "lab_retrieval",
                        f"What was my most recent {latest_lab.concept} result?"
                    )
                    new_scenarios.append(s)
                except Exception:
                    pass

        # ------------------------------------------------------------------
        # SC-001d: TF01-R08 allergy_retrieval
        # ------------------------------------------------------------------
        if allergies:
            src_ids = [a.provenance.fact_id for a in allergies[:5]]
            s = create_scenario(
                pat_id, None, src_ids,
                "SC-001d", "allergy_retrieval",
                "What allergies are recorded in my history?",
                order_matters=False
            )
            new_scenarios.append(s)

        # ------------------------------------------------------------------
        # SC-001e: TF01-R07 procedure_retrieval
        # ------------------------------------------------------------------
        if procedures:
            procs_by_enc = defaultdict(list)
            for p in procedures:
                if p.provenance.encounter_id:
                    procs_by_enc[p.provenance.encounter_id].append(p)
            if procs_by_enc:
                enc_id = random.choice(list(procs_by_enc.keys()))
                enc_procs = procs_by_enc[enc_id]
                src_ids = [p.provenance.fact_id for p in enc_procs[:5]]
                s = create_scenario(
                    pat_id, enc_id, src_ids,
                    "SC-001e", "procedure_retrieval",
                    "What procedures were recorded during this encounter?",
                    order_matters=False
                )
                new_scenarios.append(s)

        # ------------------------------------------------------------------
        # SC-001f: TF01-R09 immunization_retrieval
        # ------------------------------------------------------------------
        if immunizations:
            src_ids = [i.provenance.fact_id for i in immunizations[:5]]
            s = create_scenario(
                pat_id, None, src_ids,
                "SC-001f", "immunization_retrieval",
                "What immunizations are recorded in my history?",
                order_matters=False
            )
            new_scenarios.append(s)

        # ------------------------------------------------------------------
        # SC-001g: TF01-R11 first_occurrence
        # ------------------------------------------------------------------
        diag_with_ts = [d for d in diagnoses if d.provenance.timestamp]
        if diag_with_ts:
            try:
                earliest = min(
                    diag_with_ts,
                    key=lambda x: dateutil_parser.parse(x.provenance.timestamp).replace(tzinfo=None)
                )
                s = create_scenario(
                    pat_id, earliest.provenance.encounter_id,
                    [earliest.provenance.fact_id],
                    "SC-001g", "first_occurrence",
                    f"When was {earliest.value} first recorded?"
                )
                new_scenarios.append(s)
            except Exception:
                pass

        # ------------------------------------------------------------------
        # SC-001h: TF01-R12 last_occurrence
        # ------------------------------------------------------------------
        if diag_with_ts:
            try:
                latest_diag = max(
                    diag_with_ts,
                    key=lambda x: dateutil_parser.parse(x.provenance.timestamp).replace(tzinfo=None)
                )
                s = create_scenario(
                    pat_id, latest_diag.provenance.encounter_id,
                    [latest_diag.provenance.fact_id],
                    "SC-001h", "last_occurrence",
                    f"When was {latest_diag.value} most recently recorded?"
                )
                new_scenarios.append(s)
            except Exception:
                pass

        # ------------------------------------------------------------------
        # SC-003b: TF03 ENCOUNTER_SUMMARY
        # Requires: diagnoses + medications (or procedures) for a single encounter
        # ------------------------------------------------------------------
        if diagnoses and medications:
            # Find encounter with both diagnoses and medications
            enc_diags = defaultdict(list)
            enc_meds_map = defaultdict(list)
            enc_procs_map = defaultdict(list)
            for d in diagnoses:
                if d.provenance.encounter_id:
                    enc_diags[d.provenance.encounter_id].append(d)
            for m in medications:
                if m.provenance.encounter_id:
                    enc_meds_map[m.provenance.encounter_id].append(m)
            for p in procedures:
                if p.provenance.encounter_id:
                    enc_procs_map[p.provenance.encounter_id].append(p)

            candidate_encs = [e for e in enc_diags if e in enc_meds_map or e in enc_procs_map]
            if candidate_encs:
                chosen_enc = random.choice(candidate_encs)
                src_ids = (
                    [d.provenance.fact_id for d in enc_diags.get(chosen_enc, [])[:2]] +
                    [m.provenance.fact_id for m in enc_meds_map.get(chosen_enc, [])[:2]] +
                    [p.provenance.fact_id for p in enc_procs_map.get(chosen_enc, [])[:1]]
                )
                src_ids = list(set(src_ids))
                if len(src_ids) >= 2:
                    s = create_scenario(
                        pat_id, chosen_enc, src_ids,
                        "SC-003b", "encounter_summary",
                        "Summarize the clinical record for this encounter.",
                        order_matters=False
                    )
                    new_scenarios.append(s)

        # ------------------------------------------------------------------
        # SC-007b: TF07 clinical output explanation (observations only)
        # Non-decision-layer: explain what the recorded value is
        # ------------------------------------------------------------------
        eligible_obs = [o for o in observations
                        if o.provenance.timestamp and o.value is not None
                        and str(o.value).strip() != '']
        if eligible_obs:
            obs_choice = random.choice(eligible_obs)
            unit_str = f" {obs_choice.unit}" if obs_choice.unit else ""
            s = create_scenario(
                pat_id, obs_choice.provenance.encounter_id,
                [obs_choice.provenance.fact_id],
                "SC-007b", "observation_explanation",
                f"Explain this recorded observation: {obs_choice.concept} = {obs_choice.value}{unit_str}."
            )
            new_scenarios.append(s)

        # Write new scenarios to ledger
        if new_scenarios:
            with open(file_path, 'a') as fw:
                for s in new_scenarios:
                    fw.write(json.dumps(s.to_dict()) + "\n")
                    total_scenarios += 1
                    scenarios_per_rule[s.provenance.scenario_rule] += 1

    print(f"\nGenerated {total_scenarios} new v0.1.3 scenarios.")
    print("Breakdown by rule:")
    for rule, count in sorted(scenarios_per_rule.items()):
        print(f"  {rule}: {count}")

    log_entry = GenerationLogEntry.create(
        step_name="step07_scenario_engine_v013",
        seed=gen_seed,
        input_rows=len(ledger_files),
        output_rows=total_scenarios,
        validation={"scenarios_generated": total_scenarios, "breakdown": dict(scenarios_per_rule)}
    )
    with open(V013_LOG_PATH, 'a') as f:
        f.write(log_entry.to_json_line() + "\n")

    print("\nPhase 3 COMPLETE.")
    return True


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
