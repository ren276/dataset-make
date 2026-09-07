"""
drishti_v2/generate.py
========================
The five-stage generation pipeline (dataset-regeneration-design-memo.md
section 2.2):

    1. DRAW CATEGORY        category_id ~ TargetMarginal
    2. INSTANTIATE LATENT    condition | category_id; severity | condition;
                             vitals_true | condition, severity, age, sex
    3. WALK THE BRANCH       the authored branch file, node by node
    4. NOT_ASKED             every node the walk never reached (by construction)
    5. FLATTEN               BranchOutput -> one row

Every draw goes through a RowRng scoped to that row's row_id; there is no
module-level or sequential RNG state anywhere in this file.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .answer_model import AnswerModel
from .branches import ALL_SPECS
from .category_marginal import draw_category
from .demographics import draw_demographics, age_band_label
from .emergency import THRESHOLD_TABLE_VERSION, path1_triggered, path2_aggregate_score, path2_disposition
from .rng import RowRng
from .schema import FieldValue, collect_multi_fields, max_disposition, walk_branch
from .vitals import (VITALS, draw_encounter_date, draw_facility_tier, generate_vitals,
                      DEVICE_MEASURED, MANUAL_ENTERED)

GENERATOR_COMMIT = "drishti_v2-build-2"
ANSWER_MODEL_VERSION = "answer_model-0.1.0-draft"
CATEGORY_REGISTRY_VERSION = "category_registry-0.1.0-draft"

SPECS = ALL_SPECS
ANSWER_MODELS = {cid: AnswerModel(spec.answer_model_entries) for cid, spec in SPECS.items()}
MULTI_FIELDS = {cid: collect_multi_fields(spec.branch) for cid, spec in SPECS.items()}

CODING_BACKBONE = {
    "fever": {"icd10_mapping": "R50.9", "icpc3_basis": "A03"},
    "weakness_unwell": {"icd10_mapping": "R53", "icpc3_basis": "A04,A05"},
    "body_ache": {"icd10_mapping": "M79.1,M79.7", "icpc3_basis": "A01"},
    "weight_loss": {"icd10_mapping": "R63.4", "icpc3_basis": "T08"},
    "oedema": {"icd10_mapping": "R60.9", "icpc3_basis": "K07"},
    "cough": {"icd10_mapping": "R05", "icpc3_basis": "R05"},
    "cold_sore_throat": {"icd10_mapping": "J00,J02.9,J06.9", "icpc3_basis": "R07,R21,R74"},
    "breathlessness": {"icd10_mapping": "R06.0", "icpc3_basis": "R02"},
    "abdominal_pain": {"icd10_mapping": "R10.4", "icpc3_basis": "D01,D06"},
    "acidity_heartburn": {"icd10_mapping": "R12,K30", "icpc3_basis": "D03,D08"},
    "diarrhoea": {"icd10_mapping": "A09,K52.9", "icpc3_basis": "D11"},
    "vomiting_nausea": {"icd10_mapping": "R11", "icpc3_basis": "D09,D10"},
    "joint_pain": {"icd10_mapping": "M25.5", "icpc3_basis": "L20,L15"},
    "back_neck_pain": {"icd10_mapping": "M54.5,M54.2", "icpc3_basis": "L01,L02,L03"},
    "injury": {"icd10_mapping": "T14.9", "icpc3_basis": "A80,L81"},
    "rash": {"icd10_mapping": "R21", "icpc3_basis": "S06,S07"},
    "itching": {"icd10_mapping": "L29.9", "icpc3_basis": "S02"},
    "skin_infection": {"icd10_mapping": "L02,L03", "icpc3_basis": "S10,S11,S76"},
    "headache": {"icd10_mapping": "R51", "icpc3_basis": "N01"},
    "dizziness": {"icd10_mapping": "R42", "icpc3_basis": "N17"},
    "urinary_symptoms": {"icd10_mapping": "R30.0,N39.0", "icpc3_basis": "U01,U02,U71"},
    "chest_pain": {"icd10_mapping": "R07.4", "icpc3_basis": "K01,K02"},
    "known_hypertension": {"icd10_mapping": "I10", "icpc3_basis": "K86"},
    "known_diabetes": {"icd10_mapping": "E11", "icpc3_basis": "T90"},
    "pallor_anaemia": {"icd10_mapping": "D50.9,D64.9", "icpc3_basis": "B80,B82"},
    "antenatal_visit": {"icd10_mapping": "Z34,Z35", "icpc3_basis": "W78"},
    "other_not_in_list": {"icd10_mapping": "R69", "icpc3_basis": "A29"},
    "emergency_convulsions": {"icd10_mapping": "R56.9", "icpc3_basis": "N07"},
    "emergency_unconscious": {"icd10_mapping": "R40.2", "icpc3_basis": "N05,A29"},
    "emergency_bite_sting": {"icd10_mapping": "T63,W59,T14.1", "icpc3_basis": "A80,S13"},
    "emergency_poisoning": {"icd10_mapping": "T65.9", "icpc3_basis": "A86"},
    "emergency_heavy_bleeding": {"icd10_mapping": "R58", "icpc3_basis": "A10"},
    "emergency_pregnancy_danger": {"icd10_mapping": "O20.9,O15,O46", "icpc3_basis": "W03,W99"},
}

_CHILD_DANGER_SIGN_IDS = {
    "ds_convulsion", "ds_unconscious", "ds_breathing", "ds_no_urine", "ds_neck_stiff", "ds_cannot_feed",
    "ds_chest_pain", "ds_weakness", "ds_speech", "ds_vision", "ds_severe_head",
    "ds_mucosal", "ds_skin_peeling", "ds_purpura", "ds_fever_high", "ds_swollen_face",
    "ds_vomiting_every", "ds_blood_stool", "ds_black_tarry_stool", "ds_abdomen_rigid",
    "ds_cough_blood", "ds_wheeze_stridor", "ds_spreading_red", "ds_crepitus", "ds_wound_gas",
    "ds_high_fever_inf", "ds_breathless_rest", "ds_severe_pallor", "ds_lump_swelling", "ds_fever_gt_2wk",
    "ds_blood_in_cough", "ds_facial_puffiness", "ds_reduced_urine", "ds_rapid_pulse", "ds_bleeding_now",
    "ds_one_side_weak", "ds_speech_change", "ds_jaundice", "ds_swollen_face_lips", "ds_rash_petechial",
    "ds_high_fever_urine", "ds_flank_pain_severe", "ds_ear_discharge", "ds_fever_chills_severe",
    "ds_fever_with_sweat", "ds_breathless_stiff", "ds_swollen_face_h", "ds_severe_abd_pain",
    "ds_no_fetal_move", "ds_water_break", "ds_fever_preg", "ds_vaginal_bleed",
}


def row_id_for(index: int) -> str:
    return f"row_{index:07d}"


def generate_row(row_index: int, master_seed: str, urinary_mode: str = "odisha") -> dict:
    row_id = row_id_for(row_index)
    rng = RowRng(master_seed, row_id)

    category_id = draw_category(rng, urinary_mode)
    spec = SPECS[category_id]
    answer_model = ANSWER_MODELS[category_id]

    demo = draw_demographics(rng)
    age_band = age_band_label(demo.age_years)
    facility_tier = draw_facility_tier(rng)

    condition_id = spec.draw_condition(rng)
    severity_band = spec.draw_severity(rng, condition_id)

    vitals_specs = spec.vitals_fn(rng, demo.age_years, demo.sex, age_band, condition_id, severity_band)
    vitals = generate_vitals(rng, demo.age_years, age_band, facility_tier, vitals_specs)

    prefilled: Dict[str, FieldValue] = {
        "_sex": FieldValue("_sex", "ANSWERED", demo.sex, None),
        "_age_years": FieldValue("_age_years", "ANSWERED", demo.age_years, None),
    }
    temp = vitals.get("temperature")
    if temp is not None and temp.provenance in (DEVICE_MEASURED, MANUAL_ENTERED):
        prefilled["temperature"] = FieldValue("temperature", "ANSWERED", temp.observed_value, "PREFILL_MEASURED")

    context = {"vitals": vitals, "age_years": demo.age_years, "sex": demo.sex, "facility_tier": facility_tier}

    output = walk_branch(spec.branch, condition_id, severity_band, answer_model, rng, context,
                          prefilled_fields=prefilled)

    child_danger = False
    if demo.age_years < 18:
        for ds_field in ("danger_signs", "danger_signs_pregnancy"):
            ds = output.fields.get(ds_field)
            if ds is not None and isinstance(ds.value, (frozenset, set)):
                child_danger = child_danger or bool(ds.value & _CHILD_DANGER_SIGN_IDS)

    p1 = path1_triggered(vitals, demo.age_years, child_danger_sign_present=child_danger)
    p2_score = path2_aggregate_score(vitals)
    p2_disp = path2_disposition(p2_score)

    final_disposition = output.dispositionFloor
    if p1:
        final_disposition = "REFER_EMERGENCY"
    elif p2_disp:
        final_disposition = max_disposition(final_disposition, p2_disp)

    encounter_date = draw_encounter_date(rng, row_id)

    row: Dict[str, object] = {
        "row_id": row_id,
        "master_seed": master_seed,
        "stream_id": row_id,
        "generator_commit": GENERATOR_COMMIT,
        "threshold_table_version": THRESHOLD_TABLE_VERSION,
        "answer_model_version": ANSWER_MODEL_VERSION,
        "category_registry_version": CATEGORY_REGISTRY_VERSION,
        "branch_version": output.branchVersion,
        "synthetic": True,
        "source": "drishti_v2_generator",
        "encounter_date": encounter_date,
        "category_id": category_id,
        "icd10_mapping": CODING_BACKBONE[category_id]["icd10_mapping"],
        "icpc3_basis": CODING_BACKBONE[category_id]["icpc3_basis"],
        "age_at_encounter": demo.age_years,
        "age_band": age_band,
        "sex": demo.sex,
        "facility_tier": facility_tier,
        # audit-only, never model features (D4 / memo 7.4 rule 3):
        "_condition_id": condition_id,
        "_severity_band": severity_band,
        "path_taken": "|".join(output.pathTaken),
        "fired_gateways": "|".join(g["gatewayId"] for g in output.firedGateways),
        "disposition_floor": final_disposition,
        "tree_disposition_floor": output.dispositionFloor,
        "path1_emergency": p1,
        "path2_aggregate_score": p2_score,
        "routed_to": output.routedTo or "",
        "attachment_photo_present": bool(output.attachments),
    }

    for vital in VITALS:
        triple = vitals[vital]
        row[f"{vital}_true"] = triple.true_value
        row[vital] = triple.observed_value
        row[f"{vital}_provenance"] = triple.provenance

    multi_fields = MULTI_FIELDS[category_id]
    for field_id, fv in output.fields.items():
        if field_id.startswith("_"):
            continue
        row[f"{field_id}__status"] = fv.status
        if field_id in multi_fields:
            selected = fv.value if isinstance(fv.value, (frozenset, set)) else set()
            for opt in multi_fields[field_id]:
                row[f"{field_id}__{opt}"] = (opt in selected) if fv.status != "NOT_ASKED" else None
        else:
            # tree memo 1.5: value is null whenever status != ANSWERED (UNKNOWN's
            # meaning is fully carried by __status; no need to also leak which
            # unknown-sentinel optionId was used internally for routing).
            row[field_id] = fv.value if fv.status == "ANSWERED" else None

    return row


def generate_rows(n: int, master_seed: str, urinary_mode: str = "odisha") -> List[dict]:
    return [generate_row(i, master_seed, urinary_mode) for i in range(n)]
