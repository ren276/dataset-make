"""
drishti_v2/branches/emergency_heavy_bleeding.py
The `emergency_heavy_bleeding` Tier-0 emergency router (branch-authoring-batch-4-memo.md section 11).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import AnswerOption, BranchDef, QuestionNode, TerminalNode
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "emergency_heavy_bleeding"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_EMERGENCY"

CONDITIONS = {
    "acute_severe_haemorrhage": ConditionSpec(
        "acute_severe_haemorrhage", 1.0, "IND-PRESENT",
        "Acute active severe external, obstetric, gastrointestinal, or traumatic haemorrhage",
        severeConditions=("active haemorrhage / hypovolaemic shock",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "acute_severe_haemorrhage": {"mild": 0.10, "moderate": 0.35, "severe": 0.55},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sys = specs["bp_systolic"]
    base_dia = specs["bp_diastolic"]
    if severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 35, 12.0, 40, 230)
        specs["bp_systolic"] = VitalSpec(max(60.0, base_sys.mean - 35), 10.0, 40, 160)
        specs["bp_diastolic"] = VitalSpec(max(40.0, base_dia.mean - 20), 8.0, 20, 100)
    elif severity_band == "moderate":
        specs["pulse"] = VitalSpec(base_pulse.mean + 18, 8.0, 40, 200)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

_NODES = {
    "EHB-00": QuestionNode(
        nodeId="EHB-00", fieldId="bleeding_source", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bls_wound", "From a wound or cut", next="EHB-01"),
            AnswerOption("bls_vomit", "Blood in vomit", next="EHB-01"),
            AnswerOption("bls_stool", "Blood in stool or from rectum", next="EHB-01"),
            AnswerOption("bls_vaginal", "Vaginal bleeding (not period)", next="EHB-01"),
            AnswerOption("bls_nose", "From the nose — won't stop", next="EHB-01"),
            AnswerOption("bls_cough", "Coughing up blood", next="EHB-01"),
            AnswerOption("bls_urine", "Blood in urine", next="EHB-01"),
            AnswerOption("bls_multiple", "From several places (gums, skin, nose)", next="EHB-01"),
        ],
        default_next="EHB-01", unknown_option="bls_unknown", **_nu(0.02)
    ),
    "EHB-01": QuestionNode(
        nodeId="EHB-01", fieldId="bleeding_time_of_onset", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bto_lt_1h", "Less than 1 hour ago", next="EHB-02"),
            AnswerOption("bto_1_6h", "1 to 6 hours ago", next="EHB-02"),
            AnswerOption("bto_gt_6h", "More than 6 hours ago", next="EHB-02"),
        ],
        default_next="EHB-02", unknown_option="bto_unknown", **_nu(0.02)
    ),
    "EHB-02": QuestionNode(
        nodeId="EHB-02", fieldId="bleeding_first_aid", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("fa_pressure", "Direct pressure on the wound", next="EHB-03"),
            AnswerOption("fa_elevated", "Injured part raised above the heart", next="EHB-03"),
            AnswerOption("fa_tourniquet", "Tourniquet applied", next="EHB-03"),
            AnswerOption("fa_nothing", "Nothing done", next="EHB-03"),
        ],
        default_next="EHB-03", none_option="fa_nothing", unknown_option="fa_unknown", **_nu(0.02)
    ),
    "EHB-03": QuestionNode(
        nodeId="EHB-03", fieldId="bleeding_pregnancy", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bp_pregnant", "Yes — pregnant", next="EHB-END"),
            AnswerOption("bp_recent", "Yes — delivered recently", next="EHB-END"),
            AnswerOption("bp_no", "No", next="EHB-END"),
        ],
        default_next="EHB-END", unknown_option="bp_unknown", **_nu(0.02)
    ),
    "EHB-END": TerminalNode("EHB-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="EHB-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Emergency heavy bleeding distribution"

_entries = []

_entries += expand_entries("EHB-00", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bls_wound": 0.35, "bls_vomit": 0.15, "bls_stool": 0.10, "bls_vaginal": 0.20,
        "bls_nose": 0.08, "bls_cough": 0.05, "bls_urine": 0.03, "bls_multiple": 0.04}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EHB-01", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bto_lt_1h": 0.55, "bto_1_6h": 0.35, "bto_gt_6h": 0.10}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EHB-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"fa_pressure": 0.50, "fa_elevated": 0.30, "fa_tourniquet": 0.15, "fa_nothing": 0.30}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EHB-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bp_pregnant": 0.10, "bp_recent": 0.05, "bp_no": 0.85}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
