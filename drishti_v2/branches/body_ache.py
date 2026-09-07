"""
drishti_v2/branches/body_ache.py
The `body_ache` branch (branch-authoring-batch-3-memo.md section 7).
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

CATEGORY_ID = "body_ache"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "viral_myalgia_or_flu": ConditionSpec("viral_myalgia_or_flu", 0.50, "IND-PRESENT",
        "Acute self-limiting viral myalgia or influenza-like illness"),
    "malaria_with_generalised_aches": ConditionSpec("malaria_with_generalised_aches", 0.20, "IND-PRESENT",
        "Uncomplicated malaria presenting primarily as generalised ache"),
    "dengue_fever_myalgia": ConditionSpec("dengue_fever_myalgia", 0.15, "IND-PRESENT",
        "Dengue fever with severe break-bone ache or retro-orbital pain", severeConditions=("dengue",)),
    "chikungunya_fever_polyarthralgia": ConditionSpec("chikungunya_fever_polyarthralgia", 0.10, "IND-PRESENT",
        "Chikungunya fever with debilitating body ache and polyarthralgia", severeConditions=("chikungunya",)),
    "severe_dengue_warning_presentation": ConditionSpec("severe_dengue_warning_presentation", 0.05, "ASSUMED",
        "Severe dengue with warning signs (haemorrhage/petechiae)", severeConditions=("dengue",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "viral_myalgia_or_flu": {"mild": 0.65, "moderate": 0.30, "severe": 0.05},
    "malaria_with_generalised_aches": {"mild": 0.30, "moderate": 0.50, "severe": 0.20},
    "dengue_fever_myalgia": {"mild": 0.15, "moderate": 0.55, "severe": 0.30},
    "chikungunya_fever_polyarthralgia": {"mild": 0.15, "moderate": 0.55, "severe": 0.30},
    "severe_dengue_warning_presentation": {"mild": 0.05, "moderate": 0.30, "severe": 0.65},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    specs["temperature"] = VitalSpec(base_temp.mean + (1.2 if severity_band != "severe" else 2.0), 0.4, 34, 41)
    specs["pulse"] = VitalSpec(base_pulse.mean + (10 if severity_band != "severe" else 20), base_pulse.sd, 35, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_bac_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_bac_emg2(fields, ctx):
    return (contains(fields, "danger_signs", "ds_rash_petechial") and contains(fields, "danger_signs", "ds_bleeding")) or (
        contains(fields, "danger_signs", "ds_bleeding") and contains(fields, "danger_signs", "ds_high_fever_ache")
    )

def _gw_bac_emg3(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_bac_urg1_dengue(fields, ctx):
    return equals(fields, "ache_distribution", "ad_behind_eyes") or (
        equals(fields, "rash_with_ache", "ra_yes") and equals(fields, "fever_present", "fp_yes")
    )

def _gw_bac_urg2_chik(fields, ctx):
    return any_of(fields, "joint_swelling", ["js_yes_hot", "js_yes_cold"]) and equals(fields, "fever_present", "fp_yes")

_NODES = {
    "BAC-00": QuestionNode(
        nodeId="BAC-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_rash_petechial", "Rash — small red/purple spots that do not blanch", next="BAC-G1a"),
            AnswerOption("ds_bleeding", "Bleeding from gums, nose, or under the skin", next="BAC-G1a"),
            AnswerOption("ds_high_fever_ache", "High fever with the body ache", next="BAC-G1a"),
            AnswerOption("ds_severe_pain", "Pain so severe the patient cannot move", next="BAC-G1a"),
            AnswerOption("ds_swollen_face", "Face or throat swelling up", next="BAC-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="BAC-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="BAC-G1a"),
        ],
        default_next="BAC-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "BAC-G1a": GatewayNode("BAC-G1a", "GW-BAC-EMG-1", _gw_bac_emg1, next="BAC-G1b",
                           routeTo="emergency_unconscious", severeConditions=["cerebral malaria", "severe dengue"]),
    "BAC-G1b": GatewayNode("BAC-G1b", "GW-BAC-EMG-2", _gw_bac_emg2, next="BAC-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["severe dengue", "DIC"]),
    "BAC-G1c": GatewayNode("BAC-G1c", "GW-BAC-EMG-3", _gw_bac_emg3, next="BAC-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "BAC-01": QuestionNode(
        nodeId="BAC-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="BAC-02"),
            AnswerOption("pr_same", "About the same", next="BAC-02"),
            AnswerOption("pr_worse", "Worse", next="BAC-02"),
        ],
        default_next="BAC-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "BAC-02": QuestionNode(
        nodeId="BAC-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="BAC-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="BAC-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="BAC-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="BAC-03"),
            AnswerOption("pt_other", "Other treatment", next="BAC-03"),
        ],
        default_next="BAC-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "BAC-03": QuestionNode(
        nodeId="BAC-03", fieldId="ache_distribution", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ad_all_over", "All over the body", next="BAC-04"),
            AnswerOption("ad_muscles", "Mainly in the muscles — arms, legs", next="BAC-04"),
            AnswerOption("ad_bones", "Deep ache — feels like it is in the bones", next="BAC-04"),
            AnswerOption("ad_behind_eyes", "Pain behind or around the eyes", next="BAC-04"),
        ],
        default_next="BAC-04", unknown_option="ad_unknown", **_nu(0.03)
    ),
    "BAC-04": QuestionNode(
        nodeId="BAC-04", fieldId="rash_with_ache", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ra_yes", "Yes", next="BAC-05"),
            AnswerOption("ra_no", "No rash seen", next="BAC-05"),
        ],
        default_next="BAC-05", unknown_option="ra_unknown", **_nu(0.03)
    ),
    "BAC-05": QuestionNode(
        nodeId="BAC-05", fieldId="joint_swelling", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("js_yes_hot", "Yes — swollen and hot or red", next="BAC-S1"),
            AnswerOption("js_yes_cold", "Yes — swollen but not hot", next="BAC-S1"),
            AnswerOption("js_no", "No swelling seen", next="BAC-S1"),
        ],
        default_next="BAC-S1", unknown_option="js_unknown", **_nu(0.03)
    ),

    "BAC-S1": SubtreeRefNode("BAC-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="BAC-G2a"),
    "BAC-G2a": GatewayNode("BAC-G2a", "GW-BAC-URG-1", _gw_bac_urg1_dengue, next="BAC-G2b",
                           raisesTo="REFER_URGENT", severeConditions=["dengue (warning signs)"]),
    "BAC-G2b": GatewayNode("BAC-G2b", "GW-BAC-URG-2", _gw_bac_urg2_chik, next="BAC-END",
                           raisesTo="REFER_URGENT", severeConditions=["chikungunya", "reactive arthritis"]),
    "BAC-END": TerminalNode("BAC-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="BAC-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Body ache clinical distribution"

_entries = []

_entries += expand_entries("BAC-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_rash_petechial": 0.002, "ds_bleeding": 0.002, "ds_high_fever_ache": 0.02,
             "ds_severe_pain": 0.01, "ds_swollen_face": 0.002, "ds_unconscious": 0.001, "ds_cannot_feed": 0.005},
    "moderate": {"ds_rash_petechial": 0.01, "ds_bleeding": 0.01, "ds_high_fever_ache": 0.10,
                "ds_severe_pain": 0.08, "ds_swollen_face": 0.005, "ds_unconscious": 0.002, "ds_cannot_feed": 0.01},
    "severe": {"ds_rash_petechial": 0.10, "ds_bleeding": 0.10, "ds_high_fever_ache": 0.35,
               "ds_severe_pain": 0.30, "ds_swollen_face": 0.02, "ds_unconscious": 0.05, "ds_cannot_feed": 0.05},
}, overrides={
    ("severe_dengue_warning_presentation", "severe"): {"ds_rash_petechial": 0.75, "ds_bleeding": 0.80, "ds_high_fever_ache": 0.85,
                                                      "ds_severe_pain": 0.65, "ds_swollen_face": 0.05, "ds_unconscious": 0.15, "ds_cannot_feed": 0.15},
    ("dengue_fever_myalgia", "severe"): {"ds_rash_petechial": 0.25, "ds_bleeding": 0.15, "ds_high_fever_ache": 0.85,
                                        "ds_severe_pain": 0.70, "ds_swollen_face": 0.01, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BAC-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BAC-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.45, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.15, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BAC-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ad_all_over": 0.60, "ad_muscles": 0.25, "ad_bones": 0.10, "ad_behind_eyes": 0.05},
    "moderate": {"ad_all_over": 0.45, "ad_muscles": 0.25, "ad_bones": 0.18, "ad_behind_eyes": 0.12},
    "severe": {"ad_all_over": 0.30, "ad_muscles": 0.20, "ad_bones": 0.30, "ad_behind_eyes": 0.20},
}, overrides={
    ("dengue_fever_myalgia", "moderate"): {"ad_all_over": 0.15, "ad_muscles": 0.15, "ad_bones": 0.35, "ad_behind_eyes": 0.35},
    ("dengue_fever_myalgia", "severe"): {"ad_all_over": 0.10, "ad_muscles": 0.10, "ad_bones": 0.40, "ad_behind_eyes": 0.40},
    ("malaria_with_generalised_aches", "moderate"): {"ad_all_over": 0.75, "ad_muscles": 0.15, "ad_bones": 0.08, "ad_behind_eyes": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BAC-04", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ra_yes": 0.08, "ra_no": 0.92} for s in SEVERITIES
}, overrides={
    ("dengue_fever_myalgia", "mild"): {"ra_yes": 0.45, "ra_no": 0.55},
    ("dengue_fever_myalgia", "moderate"): {"ra_yes": 0.45, "ra_no": 0.55},
    ("dengue_fever_myalgia", "severe"): {"ra_yes": 0.45, "ra_no": 0.55},
    ("severe_dengue_warning_presentation", "mild"): {"ra_yes": 0.65, "ra_no": 0.35},
    ("severe_dengue_warning_presentation", "moderate"): {"ra_yes": 0.65, "ra_no": 0.35},
    ("severe_dengue_warning_presentation", "severe"): {"ra_yes": 0.65, "ra_no": 0.35},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BAC-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"js_yes_hot": 0.02, "js_yes_cold": 0.05, "js_no": 0.93},
    "moderate": {"js_yes_hot": 0.05, "js_yes_cold": 0.10, "js_no": 0.85},
    "severe": {"js_yes_hot": 0.10, "js_yes_cold": 0.15, "js_no": 0.75},
}, overrides={
    ("chikungunya_fever_polyarthralgia", "moderate"): {"js_yes_hot": 0.25, "js_yes_cold": 0.50, "js_no": 0.25},
    ("chikungunya_fever_polyarthralgia", "severe"): {"js_yes_hot": 0.35, "js_yes_cold": 0.55, "js_no": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("viral_myalgia_or_flu", "malaria_with_generalised_aches", "dengue_fever_myalgia", "chikungunya_fever_polyarthralgia", "severe_dengue_warning_presentation"),
    bleeding_conditions=("severe_dengue_warning_presentation", "dengue_fever_myalgia"),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
