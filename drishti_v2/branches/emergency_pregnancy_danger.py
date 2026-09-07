"""
drishti_v2/branches/emergency_pregnancy_danger.py
The `emergency_pregnancy_danger` Tier-0 emergency router (branch-authoring-batch-4-memo.md section 12).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import AnswerOption, BranchDef, QuestionNode, TerminalNode
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "emergency_pregnancy_danger"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_EMERGENCY"

CONDITIONS = {
    "acute_pregnancy_or_obstetric_emergency": ConditionSpec(
        "acute_pregnancy_or_obstetric_emergency", 1.0, "IND-PRESENT",
        "Eclampsia, antepartum/postpartum haemorrhage, uterine rupture, or cord prolapse",
        severeConditions=("obstetric emergency",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "acute_pregnancy_or_obstetric_emergency": {"mild": 0.05, "moderate": 0.30, "severe": 0.65},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sys = specs["bp_systolic"]
    base_dia = specs["bp_diastolic"]
    if severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 25, 12.0, 40, 220)
        specs["bp_systolic"] = VitalSpec(base_sys.mean + 40, 15.0, 80, 260)
        specs["bp_diastolic"] = VitalSpec(base_dia.mean + 25, 10.0, 50, 160)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

_NODES = {
    "EPD-00": QuestionNode(
        nodeId="EPD-00", fieldId="pregnancy_danger_type", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pd_bleeding", "Vaginal bleeding", next="EPD-01"),
            AnswerOption("pd_convulsion", "Fits or convulsions", next="EPD-01"),
            AnswerOption("pd_headache", "Severe headache that will not go away", next="EPD-01"),
            AnswerOption("pd_vision", "Blurred or disturbed vision", next="EPD-01"),
            AnswerOption("pd_swollen", "Face and hands suddenly swollen", next="EPD-01"),
            AnswerOption("pd_no_movement", "Baby has not moved for more than 12 hours", next="EPD-01"),
            AnswerOption("pd_water_break", "Water has broken / leaking fluid", next="EPD-01"),
            AnswerOption("pd_high_fever", "High fever", next="EPD-01"),
            AnswerOption("pd_severe_pain", "Severe abdominal pain", next="EPD-01"),
            AnswerOption("pd_none", "None of these", next="EPD-01"),
        ],
        default_next="EPD-01", none_option="pd_none", unknown_option="pd_unknown", **_nu(0.02)
    ),
    "EPD-01": QuestionNode(
        nodeId="EPD-01", fieldId="pregnancy_danger_weeks", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pw_lt_20", "Less than 20 weeks (first half)", next="EPD-02"),
            AnswerOption("pw_20_36", "20 to 36 weeks", next="EPD-02"),
            AnswerOption("pw_gt_36", "More than 36 weeks (close to due date)", next="EPD-02"),
            AnswerOption("pw_postpartum", "Just delivered — within the last 6 weeks", next="EPD-02"),
        ],
        default_next="EPD-02", unknown_option="pw_unknown", **_nu(0.02)
    ),
    "EPD-02": QuestionNode(
        nodeId="EPD-02", fieldId="pregnancy_danger_first_aid", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("fa_lying_left", "Patient lying on left side", next="EPD-END"),
            AnswerOption("fa_pad_applied", "Pad or cloth applied for bleeding", next="EPD-END"),
            AnswerOption("fa_nothing", "Nothing done", next="EPD-END"),
        ],
        default_next="EPD-END", none_option="fa_nothing", unknown_option="fa_unknown", **_nu(0.02)
    ),
    "EPD-END": TerminalNode("EPD-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="EPD-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Emergency pregnancy danger distribution"

_entries = []

_entries += expand_entries("EPD-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pd_bleeding": 0.40, "pd_convulsion": 0.20, "pd_headache": 0.35, "pd_vision": 0.25,
        "pd_swollen": 0.30, "pd_no_movement": 0.20, "pd_water_break": 0.25, "pd_high_fever": 0.15,
        "pd_severe_pain": 0.35}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EPD-01", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pw_lt_20": 0.20, "pw_20_36": 0.45, "pw_gt_36": 0.25, "pw_postpartum": 0.10}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EPD-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"fa_lying_left": 0.45, "fa_pad_applied": 0.40, "fa_nothing": 0.35}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
