"""
drishti_v2/branches/oedema.py
The `oedema` branch (branch-authoring-batch-4-memo.md section 1).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import (
    AnswerOption, BranchDef, GatewayNode, QuestionNode, TerminalNode,
    SubtreeRefNode, any_of, contains, equals, value_of
)
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries, peaked
from .spec import CategorySpec, ConditionSpec
from .subtrees import (
    make_fever_qual_nodes, expand_fever_qual_entries
)

CATEGORY_ID = "oedema"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_URGENT"

CONDITIONS = {
    "congestive_heart_failure_fluid_retention": ConditionSpec(
        "congestive_heart_failure_fluid_retention", 0.35, "IND-POP",
        "Congestive heart failure presenting with dependent peripheral oedema",
        severeConditions=("heart failure",)
    ),
    "nephrotic_syndrome_or_renal_failure": ConditionSpec(
        "nephrotic_syndrome_or_renal_failure", 0.25, "IND-POP",
        "Nephrotic syndrome or acute/chronic kidney injury with fluid retention",
        severeConditions=("nephrotic syndrome/renal failure",)
    ),
    "chronic_liver_disease_cirrhosis": ConditionSpec(
        "chronic_liver_disease_cirrhosis", 0.15, "IND-POP",
        "Decompensated cirrhosis with portal hypertension and peripheral oedema",
        severeConditions=("chronic liver disease",)
    ),
    "bilateral_dependent_venous_stasis_oedema": ConditionSpec(
        "bilateral_dependent_venous_stasis_oedema", 0.15, "IND-POP",
        "Chronic venous insufficiency or dependent stasis oedema without systemic failure"
    ),
    "deep_vein_thrombosis_unilateral_oedema": ConditionSpec(
        "deep_vein_thrombosis_unilateral_oedema", 0.05, "IND-POP",
        "Acute unilateral deep vein thrombosis of the lower extremity",
        severeConditions=("deep vein thrombosis",)
    ),
    "pre_eclampsia_toxaemia_in_pregnancy": ConditionSpec(
        "pre_eclampsia_toxaemia_in_pregnancy", 0.05, "IND-POP",
        "Pre-eclampsia presenting with acute facial, hand or generalized oedema",
        severeConditions=("pre-eclampsia",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "congestive_heart_failure_fluid_retention": {"mild": 0.25, "moderate": 0.45, "severe": 0.30},
    "nephrotic_syndrome_or_renal_failure": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "chronic_liver_disease_cirrhosis": {"mild": 0.25, "moderate": 0.45, "severe": 0.30},
    "bilateral_dependent_venous_stasis_oedema": {"mild": 0.55, "moderate": 0.35, "severe": 0.10},
    "deep_vein_thrombosis_unilateral_oedema": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "pre_eclampsia_toxaemia_in_pregnancy": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sys = specs["bp_systolic"]
    base_dia = specs["bp_diastolic"]
    base_rr = specs["respiratory_rate"]

    if condition_id == "congestive_heart_failure_fluid_retention":
        specs["pulse"] = VitalSpec(base_pulse.mean + 15, 10.0, 35, 200)
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + 6, 3.0, 10, 55)
    elif condition_id == "pre_eclampsia_toxaemia_in_pregnancy":
        specs["bp_systolic"] = VitalSpec(base_sys.mean + 35, 12.0, 70, 240)
        specs["bp_diastolic"] = VitalSpec(base_dia.mean + 20, 8.0, 40, 150)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_oed_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_oed_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_breathless_rest")

def _gw_oed_emg3(fields, ctx):
    age_band = ctx.get("age_band", "")
    return (
        age_band in ("infant", "child")
        and contains(fields, "danger_signs", "ds_cannot_feed")
    )

def _gw_oed_emg4(fields, ctx):
    return contains(fields, "danger_signs", "ds_reduced_urine")

def _gw_oed_urg1_dvt(fields, ctx):
    return equals(fields, "oedema_site", "os_one_foot")

def _gw_oed_urg2_nephrotic(fields, ctx):
    return equals(fields, "facial_puffiness_morning", "fm_yes") and equals(fields, "urine_frothy", "uf_yes")

def _gw_oed_urg3_preeclampsia(fields, ctx):
    return equals(fields, "pregnancy_status", "pg_yes")

_NODES = {
    "OED-00": QuestionNode(
        nodeId="OED-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_breathless_rest", "Breathless at rest or cannot lie flat", next="OED-G1a"),
            AnswerOption("ds_chest_pain", "Chest pain or heaviness", next="OED-G1a"),
            AnswerOption("ds_facial_puffiness", "Face and eyelids swollen, worse in morning", next="OED-G1a"),
            AnswerOption("ds_reduced_urine", "Has not passed urine since yesterday", next="OED-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="OED-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="OED-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="OED-G1a"),
            AnswerOption("ds_none", "None of these", next="OED-01"),
        ],
        default_next="OED-G1a", none_option="ds_none", unknown_option="ds_unknown", **_nu(0.01)
    ),
    "OED-G1a": GatewayNode("OED-G1a", "GW-OED-EMG-1", _gw_oed_emg1, next="OED-G1b",
                           routeTo="emergency_unconscious"),
    "OED-G1b": GatewayNode("OED-G1b", "GW-OED-EMG-2", _gw_oed_emg2, next="OED-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["heart failure"]),
    "OED-G1c": GatewayNode("OED-G1c", "GW-OED-EMG-3", _gw_oed_emg3, next="OED-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),
    "OED-G1d": GatewayNode("OED-G1d", "GW-OED-EMG-4", _gw_oed_emg4, next="OED-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["renal failure"]),

    "OED-01": QuestionNode(
        nodeId="OED-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Getting better", next="OED-02"),
            AnswerOption("pr_same", "About the same", next="OED-02"),
            AnswerOption("pr_worse", "Getting worse", next="OED-02"),
        ],
        default_next="OED-02", unknown_option="pr_unknown", **_nu(0.02)
    ),
    "OED-02": QuestionNode(
        nodeId="OED-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies", next="OED-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy / shop", next="OED-03"),
            AnswerOption("pt_ayush", "Ayurvedic / homeopathic / traditional medicine", next="OED-03"),
            AnswerOption("pt_prescribed_prior", "Prescription medicine from another doctor", next="OED-03"),
            AnswerOption("pt_other", "Other treatment", next="OED-03"),
            AnswerOption("pt_none", "No prior treatment", next="OED-03"),
        ],
        default_next="OED-03", none_option="pt_none", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "OED-03": QuestionNode(
        nodeId="OED-03", fieldId="oedema_site", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("os_both_feet", "Both feet or ankles", next="OED-G2"),
            AnswerOption("os_one_foot", "One foot or leg only", next="OED-G2"),
            AnswerOption("os_face", "Face or around the eyes", next="OED-G2"),
            AnswerOption("os_whole_body", "All over — face, hands, feet", next="OED-G2"),
            AnswerOption("os_hands", "Hands or fingers", next="OED-G2"),
        ],
        default_next="OED-G2", unknown_option="os_unknown", **_nu(0.02)
    ),
    "OED-G2": GatewayNode("OED-G2", "GW-OED-URG-1", _gw_oed_urg1_dvt, next="OED-04",
                          raisesTo="REFER_URGENT", severeConditions=["deep vein thrombosis"]),

    "OED-04": QuestionNode(
        nodeId="OED-04", fieldId="oedema_pitting", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("op_yes_deep", "Yes — deep pit, slow to fill", next="OED-05"),
            AnswerOption("op_yes_shallow", "Yes — shallow pit", next="OED-05"),
            AnswerOption("op_no", "No pit — swelling is firm", next="OED-05"),
        ],
        default_next="OED-05", unknown_option="op_unknown", **_nu(0.03)
    ),
    "OED-05": QuestionNode(
        nodeId="OED-05", fieldId="facial_puffiness_morning", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fm_yes", "Yes — worse in the morning", next="OED-06"),
            AnswerOption("fm_no", "No — same all day or worse at night", next="OED-06"),
        ],
        default_next="OED-06", unknown_option="fm_unknown", **_nu(0.03)
    ),
    "OED-06": QuestionNode(
        nodeId="OED-06", fieldId="urine_frothy", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("uf_yes", "Yes", next="OED-G_neph"),
            AnswerOption("uf_no", "No", next="OED-G_neph"),
        ],
        default_next="OED-G_neph", unknown_option="uf_unknown", **_nu(0.03)
    ),
    "OED-G_neph": GatewayNode("OED-G_neph", "GW-OED-URG-2", _gw_oed_urg2_nephrotic, next="OED-07",
                              raisesTo="REFER_URGENT", severeConditions=["nephrotic syndrome"]),

    "OED-07": QuestionNode(
        nodeId="OED-07", fieldId="pregnancy_status", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pg_yes", "Yes", next="OED-G3"),
            AnswerOption("pg_no", "No", next="OED-S1"),
        ],
        default_next="OED-S1", unknown_option="pg_unknown", **_nu(0.03)
    ),
    "OED-G3": GatewayNode("OED-G3", "GW-OED-URG-3", _gw_oed_urg3_preeclampsia, next="OED-S1",
                          routeTo="emergency_pregnancy_danger"),

    "OED-S1": SubtreeRefNode("OED-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="OED-END"),
    "OED-END": TerminalNode("OED-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="OED-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Oedema clinical distribution"

_entries = []

_entries += expand_entries("OED-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_breathless_rest": 0.02, "ds_chest_pain": 0.02, "ds_facial_puffiness": 0.05,
             "ds_reduced_urine": 0.01, "ds_confusion": 0.005, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_breathless_rest": 0.08, "ds_chest_pain": 0.06, "ds_facial_puffiness": 0.15,
                "ds_reduced_urine": 0.04, "ds_confusion": 0.01, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_breathless_rest": 0.30, "ds_chest_pain": 0.15, "ds_facial_puffiness": 0.35,
               "ds_reduced_urine": 0.15, "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, overrides={
    ("congestive_heart_failure_fluid_retention", "moderate"): {
        "ds_breathless_rest": 0.40, "ds_chest_pain": 0.20, "ds_facial_puffiness": 0.05,
        "ds_reduced_urine": 0.05, "ds_confusion": 0.01, "ds_unconscious": 0.00, "ds_cannot_feed": 0.01
    },
    ("congestive_heart_failure_fluid_retention", "severe"): {
        "ds_breathless_rest": 0.85, "ds_chest_pain": 0.45, "ds_facial_puffiness": 0.08,
        "ds_reduced_urine": 0.15, "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05
    },
    ("nephrotic_syndrome_or_renal_failure", "moderate"): {
        "ds_breathless_rest": 0.05, "ds_chest_pain": 0.02, "ds_facial_puffiness": 0.60,
        "ds_reduced_urine": 0.20, "ds_confusion": 0.02, "ds_unconscious": 0.00, "ds_cannot_feed": 0.01
    },
    ("nephrotic_syndrome_or_renal_failure", "severe"): {
        "ds_breathless_rest": 0.25, "ds_chest_pain": 0.05, "ds_facial_puffiness": 0.85,
        "ds_reduced_urine": 0.50, "ds_confusion": 0.10, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05
    },
    ("pre_eclampsia_toxaemia_in_pregnancy", "severe"): {
        "ds_breathless_rest": 0.30, "ds_chest_pain": 0.10, "ds_facial_puffiness": 0.70,
        "ds_reduced_urine": 0.25, "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("OED-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.25, "pr_same": 0.55, "pr_worse": 0.20},
    "moderate": {"pr_better": 0.10, "pr_same": 0.45, "pr_worse": 0.45},
    "severe": {"pr_better": 0.02, "pr_same": 0.20, "pr_worse": 0.78},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("OED-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.30, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.30, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("OED-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"os_both_feet": 0.65, "os_one_foot": 0.08, "os_face": 0.12, "os_whole_body": 0.10, "os_hands": 0.05}
    for s in SEVERITIES
}, overrides={
    ("deep_vein_thrombosis_unilateral_oedema", "mild"): {"os_both_feet": 0.05, "os_one_foot": 0.90, "os_face": 0.01, "os_whole_body": 0.02, "os_hands": 0.02},
    ("deep_vein_thrombosis_unilateral_oedema", "moderate"): {"os_both_feet": 0.02, "os_one_foot": 0.95, "os_face": 0.01, "os_whole_body": 0.01, "os_hands": 0.01},
    ("deep_vein_thrombosis_unilateral_oedema", "severe"): {"os_both_feet": 0.01, "os_one_foot": 0.97, "os_face": 0.01, "os_whole_body": 0.01, "os_hands": 0.00},
    ("nephrotic_syndrome_or_renal_failure", "moderate"): {"os_both_feet": 0.35, "os_one_foot": 0.02, "os_face": 0.40, "os_whole_body": 0.20, "os_hands": 0.03},
    ("nephrotic_syndrome_or_renal_failure", "severe"): {"os_both_feet": 0.20, "os_one_foot": 0.01, "os_face": 0.45, "os_whole_body": 0.30, "os_hands": 0.04},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("OED-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"op_yes_deep": 0.15, "op_yes_shallow": 0.65, "op_no": 0.20},
    "moderate": {"op_yes_deep": 0.45, "op_yes_shallow": 0.45, "op_no": 0.10},
    "severe": {"op_yes_deep": 0.75, "op_yes_shallow": 0.20, "op_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("OED-05", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"fm_yes": 0.20, "fm_no": 0.80}
    for s in SEVERITIES
}, overrides={
    ("nephrotic_syndrome_or_renal_failure", "mild"): {"fm_yes": 0.65, "fm_no": 0.35},
    ("nephrotic_syndrome_or_renal_failure", "moderate"): {"fm_yes": 0.80, "fm_no": 0.20},
    ("nephrotic_syndrome_or_renal_failure", "severe"): {"fm_yes": 0.85, "fm_no": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("OED-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"uf_yes": 0.10, "uf_no": 0.90}
    for s in SEVERITIES
}, overrides={
    ("nephrotic_syndrome_or_renal_failure", "mild"): {"uf_yes": 0.55, "uf_no": 0.45},
    ("nephrotic_syndrome_or_renal_failure", "moderate"): {"uf_yes": 0.75, "uf_no": 0.25},
    ("nephrotic_syndrome_or_renal_failure", "severe"): {"uf_yes": 0.85, "uf_no": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("OED-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pg_yes": 0.03, "pg_no": 0.97}
    for s in SEVERITIES
}, overrides={
    ("pre_eclampsia_toxaemia_in_pregnancy", "mild"): {"pg_yes": 0.95, "pg_no": 0.05},
    ("pre_eclampsia_toxaemia_in_pregnancy", "moderate"): {"pg_yes": 0.98, "pg_no": 0.02},
    ("pre_eclampsia_toxaemia_in_pregnancy", "severe"): {"pg_yes": 0.99, "pg_no": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=(),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
