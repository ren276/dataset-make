"""
drishti_v2/branches/emergency_poisoning.py
The `emergency_poisoning` Tier-0 emergency router (branch-authoring-batch-4-memo.md section 10).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import AnswerOption, BranchDef, QuestionNode, TerminalNode
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "emergency_poisoning"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_EMERGENCY"

CONDITIONS = {
    "acute_poisoning_or_toxic_ingestion": ConditionSpec(
        "acute_poisoning_or_toxic_ingestion", 1.0, "IND-PRESENT",
        "Acute pesticide, organophosphate, medicinal, or chemical poisoning",
        severeConditions=("poisoning/overdose",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "acute_poisoning_or_toxic_ingestion": {"mild": 0.15, "moderate": 0.35, "severe": 0.50},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]
    base_spo2 = specs["spo2"]
    if severity_band == "severe":
        specs["pulse"] = VitalSpec(52.0, 10.0, 30, 200)  # bradycardia in organophosphate or tachycardia
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + 8, 4.0, 8, 55)
        specs["spo2"] = VitalSpec(88.0, 4.0, 50, 100)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

_NODES = {
    "EPO-00": QuestionNode(
        nodeId="EPO-00", fieldId="poison_substance", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("sub_pesticide", "Pesticide or insecticide (e.g. organophosphate)", next="EPO-01"),
            AnswerOption("sub_rat_poison", "Rat poison or rodenticide", next="EPO-01"),
            AnswerOption("sub_medicine", "Too many tablets or wrong medicine", next="EPO-01"),
            AnswerOption("sub_cleaning", "Cleaning product, acid, or alkali", next="EPO-01"),
            AnswerOption("sub_plant", "Poisonous plant or seed (e.g. oleander, dhatura)", next="EPO-01"),
            AnswerOption("sub_alcohol", "Alcohol or spirit (methanol/ethanol)", next="EPO-01"),
        ],
        default_next="EPO-01", unknown_option="sub_unknown", **_nu(0.02)
    ),
    "EPO-01": QuestionNode(
        nodeId="EPO-01", fieldId="poison_time", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pt_lt_1h", "Less than 1 hour ago", next="EPO-02"),
            AnswerOption("pt_1_4h", "1 to 4 hours ago", next="EPO-02"),
            AnswerOption("pt_gt_4h", "More than 4 hours ago", next="EPO-02"),
        ],
        default_next="EPO-02", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "EPO-02": QuestionNode(
        nodeId="EPO-02", fieldId="poison_route", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_swallowed", "Swallowed / eaten", next="EPO-03"),
            AnswerOption("pr_inhaled", "Breathed in / inhaled", next="EPO-03"),
            AnswerOption("pr_skin", "Skin contact", next="EPO-03"),
        ],
        default_next="EPO-03", unknown_option="pr_unknown", **_nu(0.02)
    ),
    "EPO-03": QuestionNode(
        nodeId="EPO-03", fieldId="poison_first_aid", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("fa_vomited", "Patient has vomited on their own", next="EPO-04"),
            AnswerOption("fa_induced", "Vomiting was induced", next="EPO-04"),
            AnswerOption("fa_washed_skin", "Skin / eyes washed with water", next="EPO-04"),
            AnswerOption("fa_nothing", "Nothing done", next="EPO-04"),
        ],
        default_next="EPO-04", none_option="fa_nothing", unknown_option="fa_unknown", **_nu(0.02)
    ),
    "EPO-04": QuestionNode(
        nodeId="EPO-04", fieldId="poison_symptoms", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("psym_salivation", "Excessive drooling or salivation", next="EPO-END"),
            AnswerOption("psym_constricted", "Pupils very small (pinpoint)", next="EPO-END"),
            AnswerOption("psym_tremor", "Twitching or muscle fasciculation", next="EPO-END"),
            AnswerOption("psym_breathing", "Difficulty breathing", next="EPO-END"),
            AnswerOption("psym_confusion", "Confused or drowsy", next="EPO-END"),
            AnswerOption("psym_none", "None of these", next="EPO-END"),
        ],
        default_next="EPO-END", none_option="psym_none", unknown_option="psym_unknown", **_nu(0.02)
    ),
    "EPO-END": TerminalNode("EPO-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="EPO-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Emergency poisoning distribution"

_entries = []

_entries += expand_entries("EPO-00", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"sub_pesticide": 0.45, "sub_rat_poison": 0.15, "sub_medicine": 0.18,
        "sub_cleaning": 0.10, "sub_plant": 0.07, "sub_alcohol": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EPO-01", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pt_lt_1h": 0.40, "pt_1_4h": 0.45, "pt_gt_4h": 0.15}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EPO-02", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pr_swallowed": 0.80, "pr_inhaled": 0.12, "pr_skin": 0.08}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EPO-03", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"fa_vomited": 0.40, "fa_induced": 0.30, "fa_washed_skin": 0.20, "fa_nothing": 0.30}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("EPO-04", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"psym_salivation": 0.15, "psym_constricted": 0.10, "psym_tremor": 0.05,
             "psym_breathing": 0.05, "psym_confusion": 0.05},
    "moderate": {"psym_salivation": 0.45, "psym_constricted": 0.35, "psym_tremor": 0.25,
                "psym_breathing": 0.20, "psym_confusion": 0.25},
    "severe": {"psym_salivation": 0.80, "psym_constricted": 0.70, "psym_tremor": 0.60,
               "psym_breathing": 0.65, "psym_confusion": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
