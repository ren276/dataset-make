"""
drishti_v2/branches/cold_sore_throat.py
The `cold_sore_throat` branch (branch-authoring-batch-3-memo.md section 5).
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

CATEGORY_ID = "cold_sore_throat"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "viral_rhinosinusitis_common_cold": ConditionSpec("viral_rhinosinusitis_common_cold", 0.65, "IND-PRESENT",
        "Acute viral common cold / rhinitis"),
    "acute_tonsillopharyngitis_strep_or_viral": ConditionSpec("acute_tonsillopharyngitis_strep_or_viral", 0.20, "IND-PRESENT",
        "Acute tonsillitis or pharyngitis"),
    "acute_otitis_media_with_urti": ConditionSpec("acute_otitis_media_with_urti", 0.08, "IND-PRESENT",
        "Acute otitis media secondary to URTI"),
    "paediatric_bronchopneumonia_urti_presentation": ConditionSpec("paediatric_bronchopneumonia_urti_presentation", 0.05, "IND-PRESENT",
        "Early lower respiratory infection presenting as cold", severeConditions=("paediatric pneumonia presenting as 'cold'",)),
    "peritonsillar_abscess_quinsy": ConditionSpec("peritonsillar_abscess_quinsy", 0.02, "ASSUMED",
        "Peritonsillar cellulitis or quinsy", severeConditions=("rheumatic fever after streptococcal sore throat",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "viral_rhinosinusitis_common_cold": {"mild": 0.75, "moderate": 0.22, "severe": 0.03},
    "acute_tonsillopharyngitis_strep_or_viral": {"mild": 0.35, "moderate": 0.50, "severe": 0.15},
    "acute_otitis_media_with_urti": {"mild": 0.30, "moderate": 0.55, "severe": 0.15},
    "paediatric_bronchopneumonia_urti_presentation": {"mild": 0.10, "moderate": 0.45, "severe": 0.45},
    "peritonsillar_abscess_quinsy": {"mild": 0.05, "moderate": 0.35, "severe": 0.60},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]
    base_temp = specs["temperature"]

    if condition_id == "paediatric_bronchopneumonia_urti_presentation":
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + (8 if severity_band != "severe" else 18), 3.0, 15, 70)
        specs["temperature"] = VitalSpec(base_temp.mean + 1.2, 0.4, 34, 41)
    elif condition_id in ("acute_tonsillopharyngitis_strep_or_viral", "peritonsillar_abscess_quinsy"):
        specs["temperature"] = VitalSpec(base_temp.mean + (1.0 if severity_band != "severe" else 1.8), 0.4, 34, 41)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_cst_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_cst_emg2(fields, ctx):
    return any_of(fields, "danger_signs", ["ds_stridor", "ds_drooling"])

def _gw_cst_emg3(fields, ctx):
    return contains(fields, "danger_signs", "ds_fast_breathing") or equals(fields, "fast_breathing_child", "fb_fast")

def _gw_cst_emg4_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_cst_urg1_quinsy(fields, ctx):
    return equals(fields, "throat_pain_swallowing", "ts_severe") or (
        contains(fields, "danger_signs", "ds_swelling_neck") and contains(fields, "danger_signs", "ds_high_fever_throat")
    )

def _gw_cst_urg2_rheumatic(fields, ctx):
    return equals(fields, "rash_with_sore_throat", "rt_yes") and equals(fields, "fever_present", "fp_yes")

def _gw_cst_urg3_ear(fields, ctx):
    return equals(fields, "ear_pain_with_cold", "ep_discharge")

def _gw_cst_urg4_blood(fields, ctx):
    return equals(fields, "cough_character", "cc_blood")

_NODES = {
    "CST-00": QuestionNode(
        nodeId="CST-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_stridor", "Noisy breathing when breathing in (stridor)", next="CST-G1a"),
            AnswerOption("ds_drooling", "Drooling, cannot swallow saliva", next="CST-G1a"),
            AnswerOption("ds_fast_breathing", "Breathing fast — chest pulling in with each breath", next="CST-G1a"),
            AnswerOption("ds_high_fever_throat", "High fever with the sore throat", next="CST-G1a"),
            AnswerOption("ds_swelling_neck", "Swelling in the front of the neck, below the jaw", next="CST-G1a"),
            AnswerOption("ds_rash_with_fever", "Rash with fever and sore throat", next="CST-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="CST-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="CST-G1a"),
        ],
        default_next="CST-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "CST-G1a": GatewayNode("CST-G1a", "GW-CST-EMG-1", _gw_cst_emg1, next="CST-G1b",
                           routeTo="emergency_unconscious", severeConditions=["epiglottitis", "meningitis"]),
    "CST-G1b": GatewayNode("CST-G1b", "GW-CST-EMG-2", _gw_cst_emg2, next="CST-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["epiglottitis", "croup (severe)", "retropharyngeal abscess"]),
    "CST-G1c": GatewayNode("CST-G1c", "GW-CST-EMG-3", _gw_cst_emg3, next="CST-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["paediatric pneumonia"]),
    "CST-G1d": GatewayNode("CST-G1d", "GW-CST-EMG-4", _gw_cst_emg4_infant, next="CST-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "CST-01": QuestionNode(
        nodeId="CST-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="CST-02"),
            AnswerOption("pr_same", "About the same", next="CST-02"),
            AnswerOption("pr_worse", "Worse", next="CST-02"),
        ],
        default_next="CST-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "CST-02": QuestionNode(
        nodeId="CST-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or warm fluids", next="CST-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="CST-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="CST-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="CST-03"),
            AnswerOption("pt_other", "Other treatment", next="CST-03"),
        ],
        default_next="CST-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "CST-03": QuestionNode(
        nodeId="CST-03", fieldId="throat_pain_swallowing", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ts_severe", "Yes — very painful, can barely swallow", next="CST-04"),
            AnswerOption("ts_mild", "Yes — a little painful", next="CST-04"),
            AnswerOption("ts_no", "No throat pain", next="CST-04"),
        ],
        default_next="CST-04", unknown_option="ts_unknown", **_nu(0.03)
    ),
    "CST-04": QuestionNode(
        nodeId="CST-04", fieldId="cough_character", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("cc_dry", "Dry cough", next="CST-05"),
            AnswerOption("cc_productive", "Cough with spit or phlegm", next="CST-05"),
            AnswerOption("cc_blood", "Blood in the spit", next="CST-05"),
            AnswerOption("cc_paroxysmal", "Severe bouts that leave the patient gasping", next="CST-05"),
            AnswerOption("cc_none", "No cough", next="CST-05"),
        ],
        default_next="CST-05", unknown_option="cc_unknown", **_nu(0.03)
    ),
    "CST-05": QuestionNode(
        nodeId="CST-05", fieldId="ear_pain_with_cold", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ep_one_ear", "Yes — one ear", next="CST-06"),
            AnswerOption("ep_both_ears", "Yes — both ears", next="CST-06"),
            AnswerOption("ep_discharge", "Discharge coming from the ear", next="CST-06"),
            AnswerOption("ep_no", "No", next="CST-06"),
        ],
        default_next="CST-06", unknown_option="ep_unknown", **_nu(0.03)
    ),
    "CST-06": QuestionNode(
        nodeId="CST-06", fieldId="fast_breathing_child", answerType="SINGLE_CHOICE",
        guard=lambda fields: fields.get("_age_years") is not None and fields["_age_years"].value < 5,
        options=[
            AnswerOption("fb_fast", "Yes — breathing fast", next="CST-07"),
            AnswerOption("fb_normal", "No — normal rate", next="CST-07"),
            AnswerOption("fb_not_counted", "Could not count", next="CST-07"),
        ],
        default_next="CST-07", unknown_option="fb_not_counted", **_nu(0.03)
    ),
    "CST-07": QuestionNode(
        nodeId="CST-07", fieldId="rash_with_sore_throat", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rt_yes", "Yes — fine sandpaper rash", next="CST-S1"),
            AnswerOption("rt_no", "No rash", next="CST-S1"),
        ],
        default_next="CST-S1", unknown_option="rt_unknown", **_nu(0.03)
    ),

    "CST-S1": SubtreeRefNode("CST-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="CST-G2a"),
    "CST-G2a": GatewayNode("CST-G2a", "GW-CST-EMG-3", _gw_cst_emg3, next="CST-G2b",
                           raisesTo="REFER_EMERGENCY", severeConditions=["paediatric pneumonia"]),
    "CST-G2b": GatewayNode("CST-G2b", "GW-CST-URG-1", _gw_cst_urg1_quinsy, next="CST-G2c",
                           raisesTo="REFER_URGENT", severeConditions=["peritonsillar abscess", "deep neck infection"]),
    "CST-G2c": GatewayNode("CST-G2c", "GW-CST-URG-2", _gw_cst_urg2_rheumatic, next="CST-G2d",
                           raisesTo="REFER_URGENT", severeConditions=["scarlet fever", "rheumatic fever risk"]),
    "CST-G2d": GatewayNode("CST-G2d", "GW-CST-URG-3", _gw_cst_urg3_ear, next="CST-G2e",
                           raisesTo="REFER_URGENT", severeConditions=["chronic suppurative otitis media"]),
    "CST-G2e": GatewayNode("CST-G2e", "GW-CST-URG-4", _gw_cst_urg4_blood, next="CST-END",
                           raisesTo="REFER_URGENT", severeConditions=["TB", "pneumonia", "foreign body"]),
    "CST-END": TerminalNode("CST-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="CST-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Cold sore throat clinical distribution"

_entries = []

_entries += expand_entries("CST-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_stridor": 0.001, "ds_drooling": 0.001, "ds_fast_breathing": 0.01,
             "ds_high_fever_throat": 0.02, "ds_swelling_neck": 0.005, "ds_rash_with_fever": 0.005,
             "ds_unconscious": 0.001, "ds_cannot_feed": 0.005},
    "moderate": {"ds_stridor": 0.005, "ds_drooling": 0.005, "ds_fast_breathing": 0.05,
                "ds_high_fever_throat": 0.08, "ds_swelling_neck": 0.02, "ds_rash_with_fever": 0.02,
                "ds_unconscious": 0.002, "ds_cannot_feed": 0.02},
    "severe": {"ds_stridor": 0.10, "ds_drooling": 0.08, "ds_fast_breathing": 0.25,
               "ds_high_fever_throat": 0.20, "ds_swelling_neck": 0.10, "ds_rash_with_fever": 0.08,
               "ds_unconscious": 0.02, "ds_cannot_feed": 0.08},
}, overrides={
    ("paediatric_bronchopneumonia_urti_presentation", "severe"): {"ds_stridor": 0.15, "ds_drooling": 0.05, "ds_fast_breathing": 0.85,
                                                                 "ds_high_fever_throat": 0.40, "ds_swelling_neck": 0.02, "ds_rash_with_fever": 0.02,
                                                                 "ds_unconscious": 0.05, "ds_cannot_feed": 0.20},
    ("peritonsillar_abscess_quinsy", "severe"): {"ds_stridor": 0.25, "ds_drooling": 0.70, "ds_fast_breathing": 0.10,
                                                "ds_high_fever_throat": 0.75, "ds_swelling_neck": 0.80, "ds_rash_with_fever": 0.02,
                                                "ds_unconscious": 0.02, "ds_cannot_feed": 0.45},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CST-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CST-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.55, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.15, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CST-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ts_severe": 0.05, "ts_mild": 0.55, "ts_no": 0.40},
    "moderate": {"ts_severe": 0.20, "ts_mild": 0.60, "ts_no": 0.20},
    "severe": {"ts_severe": 0.55, "ts_mild": 0.35, "ts_no": 0.10},
}, overrides={
    ("acute_tonsillopharyngitis_strep_or_viral", "moderate"): {"ts_severe": 0.50, "ts_mild": 0.45, "ts_no": 0.05},
    ("acute_tonsillopharyngitis_strep_or_viral", "severe"): {"ts_severe": 0.80, "ts_mild": 0.18, "ts_no": 0.02},
    ("peritonsillar_abscess_quinsy", "severe"): {"ts_severe": 0.95, "ts_mild": 0.05, "ts_no": 0.00},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CST-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"cc_dry": 0.40, "cc_productive": 0.25, "cc_blood": 0.005, "cc_paroxysmal": 0.05, "cc_none": 0.295},
    "moderate": {"cc_dry": 0.40, "cc_productive": 0.35, "cc_blood": 0.01, "cc_paroxysmal": 0.09, "cc_none": 0.15},
    "severe": {"cc_dry": 0.30, "cc_productive": 0.45, "cc_blood": 0.03, "cc_paroxysmal": 0.12, "cc_none": 0.10},
}, overrides={
    ("paediatric_bronchopneumonia_urti_presentation", "moderate"): {"cc_dry": 0.25, "cc_productive": 0.60, "cc_blood": 0.02, "cc_paroxysmal": 0.10, "cc_none": 0.03},
    ("paediatric_bronchopneumonia_urti_presentation", "severe"): {"cc_dry": 0.15, "cc_productive": 0.70, "cc_blood": 0.05, "cc_paroxysmal": 0.08, "cc_none": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CST-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ep_one_ear": 0.05, "ep_both_ears": 0.02, "ep_discharge": 0.01, "ep_no": 0.92},
    "moderate": {"ep_one_ear": 0.12, "ep_both_ears": 0.05, "ep_discharge": 0.03, "ep_no": 0.80},
    "severe": {"ep_one_ear": 0.20, "ep_both_ears": 0.08, "ep_discharge": 0.06, "ep_no": 0.66},
}, overrides={
    ("acute_otitis_media_with_urti", "moderate"): {"ep_one_ear": 0.65, "ep_both_ears": 0.20, "ep_discharge": 0.10, "ep_no": 0.05},
    ("acute_otitis_media_with_urti", "severe"): {"ep_one_ear": 0.55, "ep_both_ears": 0.25, "ep_discharge": 0.18, "ep_no": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CST-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"fb_fast": 0.05, "fb_normal": 0.90, "fb_not_counted": 0.05},
    "moderate": {"fb_fast": 0.15, "fb_normal": 0.80, "fb_not_counted": 0.05},
    "severe": {"fb_fast": 0.40, "fb_normal": 0.55, "fb_not_counted": 0.05},
}, overrides={
    ("paediatric_bronchopneumonia_urti_presentation", "moderate"): {"fb_fast": 0.65, "fb_normal": 0.30, "fb_not_counted": 0.05},
    ("paediatric_bronchopneumonia_urti_presentation", "severe"): {"fb_fast": 0.88, "fb_normal": 0.08, "fb_not_counted": 0.04},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CST-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"rt_yes": 0.05, "rt_no": 0.95} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("viral_rhinosinusitis_common_cold", "acute_tonsillopharyngitis_strep_or_viral", "paediatric_bronchopneumonia_urti_presentation", "peritonsillar_abscess_quinsy"),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
