"""
drishti_v2/branches/other_not_in_list.py
The `other_not_in_list` branch (tree memo section 1.1, batch 4 memo section 15.2).
Degenerate branch: opens narrative, ALWAYS_ABSTAIN, emits NOT_ASKED on all fields.
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import BranchDef, TerminalNode
from ..vitals import baseline_vitals
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "other_not_in_list"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "unspecified_condition": ConditionSpec(
        "unspecified_condition", 1.0, "ASSUMED",
        "Out of scope presentation / fallback to manual physician consultation"
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "unspecified_condition": {"mild": 0.34, "moderate": 0.33, "severe": 0.33},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    return dict(baseline_vitals(age_years))

_NODES = {
    "OTH-END": TerminalNode("OTH-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="OTH-END",
)

ANSWER_MODEL_ENTRIES = []

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
