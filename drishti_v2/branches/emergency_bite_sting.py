"""
drishti_v2/branches/emergency_bite_sting.py
The `emergency_bite_sting` Tier-0 emergency router (branch-authoring-batch-4-memo.md section 9).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import AnswerOption, BranchDef, QuestionNode, TerminalNode
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "emergency_bite_sting"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_EMERGENCY"

CONDITIONS = {
    "venomous_or_animal_bite_sting": ConditionSpec(
        "venomous_or_animal_bite_sting", 1.0, "IND-PRESENT",
        "Acute snake envenomation, scorpion sting, or rabid animal bite",
        severeConditions=("bite/sting envenomation",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "venomous_or_animal_bite_sting": {"mild": 0.20, "moderate": 0.40, "severe": 0.40},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]
    if severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 28, 12.0, 40, 220)
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + 8, 4.0, 10, 60)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

_NODES = {
    "EBS-00": QuestionNode(
        nodeId="EBS-00", fieldId="bite_species", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("sp_snake", "Snake", next="EBS-01"),
            AnswerOption("sp_scorpion", "Scorpion", next="EBS-01"),
            AnswerOption("sp_dog", "Dog or other animal", next="EBS-01"),
        ],
        default_next="EBS-01", unknown_option="sp_unknown", **_nu(0.02)
    ),
    "EBS-01": QuestionNode(
        nodeId="EBS-01", fieldId="bite_time", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bt_lt_1h", "Less than 1 hour ago", next="EBS-02"),
            AnswerOption("bt_1_6h", "1 to 6 hours ago", next="EBS-02"),
            AnswerOption("bt_gt_6h", "More than 6 hours ago", next="EBS-02"),
        ],
        default_next="EBS-02", unknown_option="bt_unknown", **_nu(0.02)
    ),
    "EBS-02": QuestionNode(
        nodeId="EBS-02", fieldId="bite_site", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bsi_hand_arm", "Hand or arm", next="EBS-03"),
            AnswerOption("bsi_foot_leg", "Foot or leg", next="EBS-03"),
            AnswerOption("bsi_trunk", "Body / trunk", next="EBS-03"),
            AnswerOption("bsi_face_neck", "Face or neck", next="EBS-03"),
        ],
        default_next="EBS-03", unknown_option="bsi_unknown", **_nu(0.02)
    ),
    "EBS-03": QuestionNode(
        nodeId="EBS-03", fieldId="bite_first_aid", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("fa_immobilised", "Limb kept still / splinted", next="EBS-04"),
            AnswerOption("fa_washed", "Wound washed with water and soap", next="EBS-04"),
            AnswerOption("fa_tourniquet", "Tourniquet or tight bandage applied", next="EBS-04"),
            AnswerOption("fa_traditional", "Traditional remedy / incision / suction applied", next="EBS-04"),
            AnswerOption("fa_nothing", "Nothing done", next="EBS-04"),
        ],
        default_next="EBS-04", none_option="fa_nothing", unknown_option="fa_unknown", **_nu(0.02)
    ),
    "EBS-04": QuestionNode(
        nodeId="EBS-04", fieldId="bite_symptoms", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("bsym_swelling", "Swelling at the bite", next="EBS-END"),
            AnswerOption("bsym_bleeding_site", "Bleeding from the bite that won't stop", next="EBS-END"),
            AnswerOption("bsym_bleeding_gums", "Bleeding gums or nose", next="EBS-END"),
            AnswerOption("bsym_drooping", "Drooping eyelids or difficulty swallowing", next="EBS-END"),
            AnswerOption("bsym_difficulty_br", "Difficulty breathing", next="EBS-END"),
            AnswerOption("bsym_none", "None of these", next="EBS-END"),
        ],
        default_next="EBS-END", none_option="bsym_none", unknown_option="bsym_unknown", **_nu(0.02)
    ),
    "EBS-END": TerminalNode("EBS-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="EBS-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Emergency bite sting distribution"

_entries = []

_entries += expand_entries("EBS-00", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"sp_snake": 0.50, "sp_scorpion": 0.25, "sp_dog": 0.25}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EBS-01", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bt_lt_1h": 0.45, "bt_1_6h": 0.40, "bt_gt_6h": 0.15}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EBS-02", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bsi_hand_arm": 0.35, "bsi_foot_leg": 0.55, "bsi_trunk": 0.05, "bsi_face_neck": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EBS-03", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"fa_immobilised": 0.30, "fa_washed": 0.40, "fa_tourniquet": 0.25, "fa_traditional": 0.20, "fa_nothing": 0.25}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EBS-04", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"bsym_swelling": 0.40, "bsym_bleeding_site": 0.10, "bsym_bleeding_gums": 0.01,
             "bsym_drooping": 0.01, "bsym_difficulty_br": 0.005},
    "moderate": {"bsym_swelling": 0.70, "bsym_bleeding_site": 0.25, "bsym_bleeding_gums": 0.08,
                "bsym_drooping": 0.08, "bsym_difficulty_br": 0.05},
    "severe": {"bsym_swelling": 0.90, "bsym_bleeding_site": 0.50, "bsym_bleeding_gums": 0.35,
               "bsym_drooping": 0.40, "bsym_difficulty_br": 0.35},
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
