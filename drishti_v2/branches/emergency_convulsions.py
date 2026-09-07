"""
drishti_v2/branches/emergency_convulsions.py
The `emergency_convulsions` Tier-0 emergency router (branch-authoring-batch-4-memo.md section 7).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import AnswerOption, BranchDef, QuestionNode, TerminalNode
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "emergency_convulsions"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_EMERGENCY"

CONDITIONS = {
    "active_or_recent_convulsions": ConditionSpec(
        "active_or_recent_convulsions", 1.0, "IND-PRESENT",
        "Acute generalised or focal seizures / status epilepticus presentation",
        severeConditions=("convulsions",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "active_or_recent_convulsions": {"mild": 0.10, "moderate": 0.30, "severe": 0.60},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]
    if severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 30, 12.0, 40, 220)
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + 8, 4.0, 10, 60)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

_NODES = {
    "ECN-00": QuestionNode(
        nodeId="ECN-00", fieldId="convulsion_time_of_onset", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("co_minutes", "Minutes ago — still happening or just stopped", next="ECN-01"),
            AnswerOption("co_lt_1h", "Less than 1 hour ago", next="ECN-01"),
            AnswerOption("co_1_6h", "1 to 6 hours ago", next="ECN-01"),
            AnswerOption("co_gt_6h", "More than 6 hours ago", next="ECN-01"),
        ],
        default_next="ECN-01", unknown_option="co_unknown", **_nu(0.02)
    ),
    "ECN-01": QuestionNode(
        nodeId="ECN-01", fieldId="convulsion_first_aid", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("fa_position", "Turned on side (recovery position)", next="ECN-02"),
            AnswerOption("fa_nothing_mouth", "Kept things out of the mouth", next="ECN-02"),
            AnswerOption("fa_medicine", "Given medicine", next="ECN-02"),
            AnswerOption("fa_nothing", "Nothing done", next="ECN-02"),
        ],
        default_next="ECN-02", none_option="fa_nothing", unknown_option="fa_unknown", **_nu(0.02)
    ),
    "ECN-02": QuestionNode(
        nodeId="ECN-02", fieldId="convulsion_still_happening", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("cs_yes", "Yes — still fitting", next="ECN-END"),
            AnswerOption("cs_no", "No — fits have stopped", next="ECN-END"),
        ],
        default_next="ECN-END", unknown_option="cs_unknown", **_nu(0.02)
    ),
    "ECN-END": TerminalNode("ECN-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="ECN-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Emergency convulsions distribution"

_entries = []

_entries += expand_entries("ECN-00", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"co_minutes": 0.45, "co_lt_1h": 0.35, "co_1_6h": 0.15, "co_gt_6h": 0.05}
    for s in SEVERITIES
}, overrides={
    ("active_or_recent_convulsions", "severe"): {"co_minutes": 0.70, "co_lt_1h": 0.20, "co_1_6h": 0.08, "co_gt_6h": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ECN-01", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"fa_position": 0.40, "fa_nothing_mouth": 0.50, "fa_medicine": 0.15, "fa_nothing": 0.30}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ECN-02", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"cs_yes": 0.10, "cs_no": 0.90},
    "moderate": {"cs_yes": 0.30, "cs_no": 0.70},
    "severe": {"cs_yes": 0.65, "cs_no": 0.35},
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
