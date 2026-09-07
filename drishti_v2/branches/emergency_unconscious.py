"""
drishti_v2/branches/emergency_unconscious.py
The `emergency_unconscious` Tier-0 emergency router (branch-authoring-batch-4-memo.md section 8).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import AnswerOption, BranchDef, QuestionNode, TerminalNode
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "emergency_unconscious"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_EMERGENCY"

CONDITIONS = {
    "unconscious_coma_or_altered_sensorium": ConditionSpec(
        "unconscious_coma_or_altered_sensorium", 1.0, "IND-PRESENT",
        "Acute unresponsiveness, coma, or profound metabolic/structural encephalopathy",
        severeConditions=("unconscious",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "unconscious_coma_or_altered_sensorium": {"mild": 0.05, "moderate": 0.25, "severe": 0.70},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_rr = specs["respiratory_rate"]
    base_spo2 = specs["spo2"]
    if severity_band == "severe":
        specs["respiratory_rate"] = VitalSpec(max(8.0, base_rr.mean - 4), 3.0, 5, 50)
        specs["spo2"] = VitalSpec(88.0, 4.0, 50, 100)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

_NODES = {
    "EUC-00": QuestionNode(
        nodeId="EUC-00", fieldId="unconscious_time_of_onset", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("uo_minutes", "Minutes ago", next="EUC-01"),
            AnswerOption("uo_lt_1h", "Less than 1 hour ago", next="EUC-01"),
            AnswerOption("uo_1_6h", "1 to 6 hours ago", next="EUC-01"),
            AnswerOption("uo_gt_6h", "More than 6 hours ago", next="EUC-01"),
            AnswerOption("uo_found", "Found unconscious — time not known", next="EUC-01"),
        ],
        default_next="EUC-01", unknown_option="uo_unknown", **_nu(0.02)
    ),
    "EUC-01": QuestionNode(
        nodeId="EUC-01", fieldId="unconscious_breathing", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ub_yes_normal", "Yes — breathing normally", next="EUC-02"),
            AnswerOption("ub_yes_abnormal", "Yes — but noisy, gasping, or very slow", next="EUC-02"),
            AnswerOption("ub_no", "No — not breathing", next="EUC-02"),
        ],
        default_next="EUC-02", unknown_option="ub_unknown", **_nu(0.02)
    ),
    "EUC-02": QuestionNode(
        nodeId="EUC-02", fieldId="unconscious_first_aid", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("fa_recovery", "Turned on side (recovery position)", next="EUC-END"),
            AnswerOption("fa_airway", "Airway cleared / head tilted", next="EUC-END"),
            AnswerOption("fa_nothing", "Nothing done", next="EUC-END"),
        ],
        default_next="EUC-END", none_option="fa_nothing", unknown_option="fa_unknown", **_nu(0.02)
    ),
    "EUC-END": TerminalNode("EUC-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="EUC-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Emergency unconscious distribution"

_entries = []

_entries += expand_entries("EUC-00", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"uo_minutes": 0.35, "uo_lt_1h": 0.30, "uo_1_6h": 0.15, "uo_gt_6h": 0.05, "uo_found": 0.15}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EUC-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ub_yes_normal": 0.85, "ub_yes_abnormal": 0.15, "ub_no": 0.00},
    "moderate": {"ub_yes_normal": 0.60, "ub_yes_abnormal": 0.38, "ub_no": 0.02},
    "severe": {"ub_yes_normal": 0.30, "ub_yes_abnormal": 0.60, "ub_no": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EUC-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"fa_recovery": 0.35, "fa_airway": 0.40, "fa_nothing": 0.45}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
