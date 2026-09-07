"""
drishti_v2/branches/headache.py
The `headache` branch (branch-authoring-batch-2-memo.md section 5).
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
from .subtrees import make_fever_qual_nodes, expand_fever_qual_entries

CATEGORY_ID = "headache"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "tension_type_headache": ConditionSpec("tension_type_headache", 0.50, "IND-POP",
        "Tension-type headache"),
    "migraine_without_or_with_aura": ConditionSpec("migraine_without_or_with_aura", 0.25, "IND-PRESENT",
        "Migraine with or without aura"),
    "hypertensive_headache": ConditionSpec("hypertensive_headache", 0.12, "IND-PRESENT",
        "Headache secondary to uncontrolled hypertension", severeConditions=("hypertensive emergency",)),
    "acute_sinusitis_headache": ConditionSpec("acute_sinusitis_headache", 0.06, "IND-PRESENT",
        "Acute frontal or maxillary sinusitis"),
    "meningitis_or_cns_infection": ConditionSpec("meningitis_or_cns_infection", 0.04, "ASSUMED",
        "Acute bacterial/viral meningitis or cerebral malaria", severeConditions=("meningitis", "cerebral malaria")),
    "subarachnoid_haemorrhage_or_stroke": ConditionSpec("subarachnoid_haemorrhage_or_stroke", 0.03, "ASSUMED",
        "Subarachnoid haemorrhage or ischaemic stroke", severeConditions=("subarachnoid haemorrhage", "stroke")),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "tension_type_headache": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
    "migraine_without_or_with_aura": {"mild": 0.20, "moderate": 0.55, "severe": 0.25},
    "hypertensive_headache": {"mild": 0.25, "moderate": 0.50, "severe": 0.25},
    "acute_sinusitis_headache": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "meningitis_or_cns_infection": {"mild": 0.05, "moderate": 0.25, "severe": 0.70},
    "subarachnoid_haemorrhage_or_stroke": {"mild": 0.02, "moderate": 0.18, "severe": 0.80},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sbp = specs["bp_systolic"]
    base_dbp = specs["bp_diastolic"]
    base_temp = specs["temperature"]

    if condition_id == "hypertensive_headache":
        specs["bp_systolic"] = VitalSpec(175.0, 15.0, 80, 240)
        specs["bp_diastolic"] = VitalSpec(105.0, 10.0, 50, 150)
    elif condition_id == "meningitis_or_cns_infection":
        specs["temperature"] = VitalSpec(base_temp.mean + (1.5 if severity_band != "severe" else 2.2), 0.4, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + (15 if severity_band != "severe" else 25), base_pulse.sd, 35, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_hdc_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_seizure")

def _gw_hdc_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_hdc_emg3_stage_a(fields, ctx):
    return contains(fields, "danger_signs", "ds_worst_ever_sudden") or (
        contains(fields, "danger_signs", "ds_neck_stiff") and contains(fields, "danger_signs", "ds_high_fever_head")
    )

def _gw_hdc_emg4_stroke(fields, ctx):
    return any_of(fields, "danger_signs", ["ds_one_side_weak", "ds_vision_sudden"]) or (
        contains(fields, "danger_signs", "ds_confusion") and (value_of(fields, "severity_band") == "severe" or equals(fields, "severity_score", 8) or equals(fields, "severity_score", 9) or equals(fields, "severity_score", 10))
    )

def _gw_hdc_emg5_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_hdc_emg3_full(fields, ctx):
    return _gw_hdc_emg3_stage_a(fields, ctx) or equals(fields, "neck_stiffness_on_exam", "ns_cannot")

def _gw_hdc_urg1_htn(fields, ctx):
    return contains(fields, "danger_signs", "ds_vision_sudden") and (
        value_of(fields, "severity_band") == "severe" or equals(fields, "severity_score", 8) or equals(fields, "severity_score", 9) or equals(fields, "severity_score", 10)
    )

def _gw_hdc_urg2_preeclampsia(fields, ctx):
    return ctx.get("sex") == "F" and equals(fields, "pregnancy_status", "pg_yes") and (
        value_of(fields, "severity_band") == "severe" or equals(fields, "severity_score", 8) or equals(fields, "severity_score", 9) or equals(fields, "severity_score", 10)
    )

def _gw_hdc_urg3_icp(fields, ctx):
    return equals(fields, "vomiting_present", "vm_yes_everything") and (
        any_of(fields, "visual_disturbance", ["vd_blurring", "vd_loss"]) or equals(fields, "progression", "pr_worse")
    )

def _gw_hdc_urg4_cns(fields, ctx):
    return equals(fields, "fever_present", "fp_yes") and (
        contains(fields, "danger_signs", "ds_neck_stiff") or equals(fields, "neck_stiffness_on_exam", "ns_cannot") or contains(fields, "danger_signs", "ds_confusion")
    )

_NODES = {
    "HDC-00": QuestionNode(
        nodeId="HDC-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_worst_ever_sudden", "The worst headache of their life, came on suddenly", next="HDC-G1a"),
            AnswerOption("ds_neck_stiff", "Neck stiffness, or cannot bend the neck forward", next="HDC-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="HDC-G1a"),
            AnswerOption("ds_one_side_weak", "Weakness or drooping on one side of the body", next="HDC-G1a"),
            AnswerOption("ds_vision_sudden", "Sudden loss of vision or double vision", next="HDC-G1a"),
            AnswerOption("ds_seizure", "Fits or convulsions", next="HDC-G1a"),
            AnswerOption("ds_high_fever_head", "High fever with the headache", next="HDC-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="HDC-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="HDC-G1a"),
        ],
        default_next="HDC-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "HDC-G1a": GatewayNode("HDC-G1a", "GW-HDC-EMG-1", _gw_hdc_emg1, next="HDC-G1b",
                           routeTo="emergency_convulsions", severeConditions=["meningitis", "cerebral malaria", "eclampsia"]),
    "HDC-G1b": GatewayNode("HDC-G1b", "GW-HDC-EMG-2", _gw_hdc_emg2, next="HDC-G1c",
                           routeTo="emergency_unconscious", severeConditions=["stroke", "cerebral malaria", "meningitis"]),
    "HDC-G1c": GatewayNode("HDC-G1c", "GW-HDC-EMG-3", _gw_hdc_emg3_stage_a, next="HDC-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["subarachnoid haemorrhage", "meningitis"]),
    "HDC-G1d": GatewayNode("HDC-G1d", "GW-HDC-EMG-4", _gw_hdc_emg4_stroke, next="HDC-G1e",
                           raisesTo="REFER_EMERGENCY", severeConditions=["stroke", "space-occupying lesion"]),
    "HDC-G1e": GatewayNode("HDC-G1e", "GW-HDC-EMG-5", _gw_hdc_emg5_infant, next="HDC-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "HDC-01": QuestionNode(
        nodeId="HDC-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="HDC-02"),
            AnswerOption("pr_same", "About the same", next="HDC-02"),
            AnswerOption("pr_worse", "Worse", next="HDC-02"),
        ],
        default_next="HDC-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "HDC-02": QuestionNode(
        nodeId="HDC-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="HDC-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="HDC-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="HDC-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="HDC-03"),
            AnswerOption("pt_other", "Other treatment", next="HDC-03"),
        ],
        default_next="HDC-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "HDC-03": QuestionNode(
        nodeId="HDC-03", fieldId="headache_site", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hs_one_side", "One side of the head", next="HDC-04"),
            AnswerOption("hs_both_sides", "Both sides, or all over", next="HDC-04"),
            AnswerOption("hs_behind_eyes", "Behind or around the eyes", next="HDC-04"),
            AnswerOption("hs_back_head", "Back of the head and neck", next="HDC-04"),
            AnswerOption("hs_forehead", "Forehead", next="HDC-04"),
        ],
        default_next="HDC-04", unknown_option="hs_unknown", **_nu(0.03)
    ),
    "HDC-04": QuestionNode(
        nodeId="HDC-04", fieldId="headache_character", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hc_throbbing", "Throbbing or pounding", next="HDC-05"),
            AnswerOption("hc_pressing", "Pressing or tight, like a band", next="HDC-05"),
            AnswerOption("hc_stabbing", "Sharp or stabbing", next="HDC-05"),
        ],
        default_next="HDC-05", unknown_option="hc_unknown", **_nu(0.03)
    ),
    "HDC-05": QuestionNode(
        nodeId="HDC-05", fieldId="photophobia", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ph_yes", "Yes — light makes it worse", next="HDC-06"),
            AnswerOption("ph_no", "No", next="HDC-06"),
        ],
        default_next="HDC-06", unknown_option="ph_unknown", **_nu(0.03)
    ),
    "HDC-06": QuestionNode(
        nodeId="HDC-06", fieldId="vomiting_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vm_yes_keeping_fluids", "Yes — keeping some fluids down", next="HDC-07"),
            AnswerOption("vm_yes_everything", "Yes — vomiting everything", next="HDC-07"),
            AnswerOption("vm_no", "No vomiting", next="HDC-07"),
        ],
        default_next="HDC-07", unknown_option="vm_unknown", **_nu(0.03)
    ),
    "HDC-07": QuestionNode(
        nodeId="HDC-07", fieldId="visual_disturbance", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vd_aura", "Flashing lights or zigzag lines before or with the headache", next="HDC-08"),
            AnswerOption("vd_blurring", "Vision blurred", next="HDC-08"),
            AnswerOption("vd_loss", "Part of the vision lost", next="HDC-08"),
            AnswerOption("vd_no", "No change", next="HDC-08"),
        ],
        default_next="HDC-08", unknown_option="vd_unknown", **_nu(0.03)
    ),
    "HDC-08": QuestionNode(
        nodeId="HDC-08", fieldId="neck_stiffness_on_exam", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ns_can_do", "Yes — chin touches chest easily", next="HDC-S1"),
            AnswerOption("ns_cannot", "No — cannot or painful", next="HDC-S1"),
        ],
        default_next="HDC-S1", unknown_option="ns_unknown", **_nu(0.03)
    ),

    "HDC-S1": SubtreeRefNode("HDC-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="HDC-G2"),
    "HDC-G2": GatewayNode("HDC-G2", "GW-HDC-EMG-3", _gw_hdc_emg3_full, next="HDC-G3a",
                          raisesTo="REFER_EMERGENCY", severeConditions=["subarachnoid haemorrhage", "meningitis"]),
    "HDC-G3a": GatewayNode("HDC-G3a", "GW-HDC-URG-1", _gw_hdc_urg1_htn, next="HDC-G3b",
                           raisesTo="REFER_URGENT", severeConditions=["hypertensive emergency"]),
    "HDC-G3b": GatewayNode("HDC-G3b", "GW-HDC-URG-2", _gw_hdc_urg2_preeclampsia, next="HDC-G3c",
                           raisesTo="REFER_URGENT", severeConditions=["pre-eclampsia"]),
    "HDC-G3c": GatewayNode("HDC-G3c", "GW-HDC-URG-3", _gw_hdc_urg3_icp, next="HDC-G3d",
                           raisesTo="REFER_URGENT", severeConditions=["raised intracranial pressure", "space-occupying lesion"]),
    "HDC-G3d": GatewayNode("HDC-G3d", "GW-HDC-URG-4", _gw_hdc_urg4_cns, next="HDC-END",
                           raisesTo="REFER_URGENT", severeConditions=["cerebral malaria", "meningitis", "encephalitis"]),
    "HDC-END": TerminalNode("HDC-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="HDC-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Headache clinical distribution"

_entries = []

_entries += expand_entries("HDC-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_worst_ever_sudden": 0.005, "ds_neck_stiff": 0.005, "ds_confusion": 0.002,
             "ds_one_side_weak": 0.001, "ds_vision_sudden": 0.005, "ds_seizure": 0.001,
             "ds_high_fever_head": 0.01, "ds_unconscious": 0.001, "ds_cannot_feed": 0.005},
    "moderate": {"ds_worst_ever_sudden": 0.02, "ds_neck_stiff": 0.02, "ds_confusion": 0.01,
                "ds_one_side_weak": 0.005, "ds_vision_sudden": 0.02, "ds_seizure": 0.002,
                "ds_high_fever_head": 0.05, "ds_unconscious": 0.002, "ds_cannot_feed": 0.01},
    "severe": {"ds_worst_ever_sudden": 0.15, "ds_neck_stiff": 0.15, "ds_confusion": 0.10,
               "ds_one_side_weak": 0.08, "ds_vision_sudden": 0.10, "ds_seizure": 0.05,
               "ds_high_fever_head": 0.20, "ds_unconscious": 0.03, "ds_cannot_feed": 0.05},
}, overrides={
    ("subarachnoid_haemorrhage_or_stroke", "severe"): {"ds_worst_ever_sudden": 0.85, "ds_neck_stiff": 0.65, "ds_confusion": 0.40,
                                                      "ds_one_side_weak": 0.55, "ds_vision_sudden": 0.35, "ds_seizure": 0.15,
                                                      "ds_high_fever_head": 0.05, "ds_unconscious": 0.20, "ds_cannot_feed": 0.05},
    ("meningitis_or_cns_infection", "severe"): {"ds_worst_ever_sudden": 0.45, "ds_neck_stiff": 0.85, "ds_confusion": 0.55,
                                               "ds_one_side_weak": 0.10, "ds_vision_sudden": 0.10, "ds_seizure": 0.25,
                                               "ds_high_fever_head": 0.90, "ds_unconscious": 0.15, "ds_cannot_feed": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.45, "pt_pharmacy_medicine": 0.45, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.20, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"hs_one_side": 0.25, "hs_both_sides": 0.35, "hs_behind_eyes": 0.15, "hs_back_head": 0.10, "hs_forehead": 0.15},
    "moderate": {"hs_one_side": 0.30, "hs_both_sides": 0.30, "hs_behind_eyes": 0.15, "hs_back_head": 0.10, "hs_forehead": 0.15},
    "severe": {"hs_one_side": 0.35, "hs_both_sides": 0.25, "hs_behind_eyes": 0.15, "hs_back_head": 0.15, "hs_forehead": 0.10},
}, overrides={
    ("migraine_without_or_with_aura", "moderate"): {"hs_one_side": 0.75, "hs_both_sides": 0.10, "hs_behind_eyes": 0.10, "hs_back_head": 0.02, "hs_forehead": 0.03},
    ("migraine_without_or_with_aura", "severe"): {"hs_one_side": 0.80, "hs_both_sides": 0.08, "hs_behind_eyes": 0.08, "hs_back_head": 0.02, "hs_forehead": 0.02},
    ("tension_type_headache", "mild"): {"hs_one_side": 0.05, "hs_both_sides": 0.65, "hs_behind_eyes": 0.05, "hs_back_head": 0.15, "hs_forehead": 0.10},
    ("tension_type_headache", "moderate"): {"hs_one_side": 0.05, "hs_both_sides": 0.60, "hs_behind_eyes": 0.05, "hs_back_head": 0.20, "hs_forehead": 0.10},
    ("acute_sinusitis_headache", "moderate"): {"hs_one_side": 0.15, "hs_both_sides": 0.10, "hs_behind_eyes": 0.35, "hs_back_head": 0.02, "hs_forehead": 0.38},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"hc_throbbing": 0.25, "hc_pressing": 0.55, "hc_stabbing": 0.20},
    "moderate": {"hc_throbbing": 0.40, "hc_pressing": 0.40, "hc_stabbing": 0.20},
    "severe": {"hc_throbbing": 0.50, "hc_pressing": 0.30, "hc_stabbing": 0.20},
}, overrides={
    ("migraine_without_or_with_aura", "moderate"): {"hc_throbbing": 0.80, "hc_pressing": 0.12, "hc_stabbing": 0.08},
    ("migraine_without_or_with_aura", "severe"): {"hc_throbbing": 0.85, "hc_pressing": 0.08, "hc_stabbing": 0.07},
    ("tension_type_headache", "moderate"): {"hc_throbbing": 0.10, "hc_pressing": 0.80, "hc_stabbing": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ph_yes": 0.15, "ph_no": 0.85},
    "moderate": {"ph_yes": 0.35, "ph_no": 0.65},
    "severe": {"ph_yes": 0.60, "ph_no": 0.40},
}, overrides={
    ("migraine_without_or_with_aura", "moderate"): {"ph_yes": 0.80, "ph_no": 0.20},
    ("migraine_without_or_with_aura", "severe"): {"ph_yes": 0.90, "ph_no": 0.10},
    ("meningitis_or_cns_infection", "severe"): {"ph_yes": 0.85, "ph_no": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vm_yes_keeping_fluids": 0.08, "vm_yes_everything": 0.01, "vm_no": 0.91},
    "moderate": {"vm_yes_keeping_fluids": 0.25, "vm_yes_everything": 0.04, "vm_no": 0.71},
    "severe": {"vm_yes_keeping_fluids": 0.40, "vm_yes_everything": 0.20, "vm_no": 0.40},
}, overrides={
    ("migraine_without_or_with_aura", "severe"): {"vm_yes_keeping_fluids": 0.60, "vm_yes_everything": 0.15, "vm_no": 0.25},
    ("subarachnoid_haemorrhage_or_stroke", "severe"): {"vm_yes_keeping_fluids": 0.35, "vm_yes_everything": 0.45, "vm_no": 0.20},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vd_aura": 0.08, "vd_blurring": 0.08, "vd_loss": 0.01, "vd_no": 0.83},
    "moderate": {"vd_aura": 0.18, "vd_blurring": 0.15, "vd_loss": 0.02, "vd_no": 0.65},
    "severe": {"vd_aura": 0.20, "vd_blurring": 0.25, "vd_loss": 0.10, "vd_no": 0.45},
}, overrides={
    ("migraine_without_or_with_aura", "mild"): {"vd_aura": 0.35, "vd_blurring": 0.05, "vd_loss": 0.01, "vd_no": 0.59},
    ("migraine_without_or_with_aura", "moderate"): {"vd_aura": 0.50, "vd_blurring": 0.10, "vd_loss": 0.01, "vd_no": 0.39},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HDC-08", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ns_can_do": 0.98, "ns_cannot": 0.02},
    "moderate": {"ns_can_do": 0.92, "ns_cannot": 0.08},
    "severe": {"ns_can_do": 0.75, "ns_cannot": 0.25},
}, overrides={
    ("meningitis_or_cns_infection", "moderate"): {"ns_can_do": 0.30, "ns_cannot": 0.70},
    ("meningitis_or_cns_infection", "severe"): {"ns_can_do": 0.10, "ns_cannot": 0.90},
    ("subarachnoid_haemorrhage_or_stroke", "severe"): {"ns_can_do": 0.35, "ns_cannot": 0.65},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("meningitis_or_cns_infection", "acute_sinusitis_headache"),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
