"""
drishti_v2/branches/urinary_symptoms.py
The `urinary_symptoms` branch (branch-authoring-batch-3-memo.md section 4).
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

CATEGORY_ID = "urinary_symptoms"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "lower_urinary_tract_infection_cystitis": ConditionSpec("lower_urinary_tract_infection_cystitis", 0.65, "IND-PRESENT",
        "Uncomplicated acute lower UTI / cystitis"),
    "pyelonephritis_upper_uti": ConditionSpec("pyelonephritis_upper_uti", 0.12, "IND-PRESENT",
        "Acute pyelonephritis / upper UTI", severeConditions=("pyelonephritis",)),
    "urolithiasis_renal_colic": ConditionSpec("urolithiasis_renal_colic", 0.10, "IND-PRESENT",
        "Renal / ureteric calculus presenting with dysuria or haematuria", severeConditions=("urinary obstruction/stone",)),
    "sexually_transmitted_infection_urethritis": ConditionSpec("sexually_transmitted_infection_urethritis", 0.08, "IND-PRESENT",
        "Urethritis / gonococcal or chlamydial STI", severeConditions=("STI",)),
    "benign_prostatic_hyperplasia_or_stricture": ConditionSpec("benign_prostatic_hyperplasia_or_stricture", 0.05, "IND-POP",
        "BPH or urethral stricture with lower urinary tract symptoms"),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "lower_urinary_tract_infection_cystitis": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
    "pyelonephritis_upper_uti": {"mild": 0.15, "moderate": 0.50, "severe": 0.35},
    "urolithiasis_renal_colic": {"mild": 0.15, "moderate": 0.55, "severe": 0.30},
    "sexually_transmitted_infection_urethritis": {"mild": 0.45, "moderate": 0.45, "severe": 0.10},
    "benign_prostatic_hyperplasia_or_stricture": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    if condition_id == "pyelonephritis_upper_uti":
        specs["temperature"] = VitalSpec(base_temp.mean + (1.2 if severity_band != "severe" else 2.0), 0.4, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + (12 if severity_band != "severe" else 25), base_pulse.sd, 35, 220)
    elif condition_id == "urolithiasis_renal_colic" and severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 15, base_pulse.sd, 35, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_urn_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_urn_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_high_fever_urine") and contains(fields, "danger_signs", "ds_confusion")

def _gw_urn_emg3(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_urn_urg2_obstruction(fields, ctx):
    return contains(fields, "danger_signs", "ds_cannot_pass_urine") or contains(fields, "danger_signs", "ds_severe_flank_pain")

def _gw_urn_urg1_pyelo(fields, ctx):
    return any_of(fields, "flank_pain", ["fp_one_side", "fp_both"]) and (
        equals(fields, "fever_present", "fp_yes") or contains(fields, "danger_signs", "ds_high_fever_urine")
    )

def _gw_urn_urg3_haematuria(fields, ctx):
    return equals(fields, "haematuria", "hu_visible") or contains(fields, "danger_signs", "ds_blood_in_urine")

def _gw_urn_urg4_pregnancy(fields, ctx):
    return equals(fields, "pregnancy_status", "pg_yes") and equals(fields, "burning_on_urination", "bu_yes")

def _gw_urn_urg5_sti(fields, ctx):
    return equals(fields, "urethral_discharge", "ud_yes")

_NODES = {
    "URN-00": QuestionNode(
        nodeId="URN-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_cannot_pass_urine", "Has not been able to pass urine at all", next="URN-G1a"),
            AnswerOption("ds_high_fever_urine", "High fever with the urinary symptoms", next="URN-G1a"),
            AnswerOption("ds_severe_flank_pain", "Severe pain in the side or back going to the groin", next="URN-G1a"),
            AnswerOption("ds_blood_in_urine", "Blood in the urine", next="URN-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="URN-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="URN-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="URN-G1a"),
        ],
        default_next="URN-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "URN-G1a": GatewayNode("URN-G1a", "GW-URN-EMG-1", _gw_urn_emg1, next="URN-G1b",
                           routeTo="emergency_unconscious", severeConditions=["urosepsis"]),
    "URN-G1b": GatewayNode("URN-G1b", "GW-URN-EMG-2", _gw_urn_emg2, next="URN-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["urosepsis"]),
    "URN-G1c": GatewayNode("URN-G1c", "GW-URN-EMG-3", _gw_urn_emg3, next="URN-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),
    "URN-G1d": GatewayNode("URN-G1d", "GW-URN-URG-2", _gw_urn_urg2_obstruction, next="URN-01",
                           raisesTo="REFER_URGENT", severeConditions=["urinary obstruction", "renal colic"]),

    "URN-01": QuestionNode(
        nodeId="URN-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="URN-02"),
            AnswerOption("pr_same", "About the same", next="URN-02"),
            AnswerOption("pr_worse", "Worse", next="URN-02"),
        ],
        default_next="URN-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "URN-02": QuestionNode(
        nodeId="URN-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="URN-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="URN-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="URN-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="URN-03"),
            AnswerOption("pt_other", "Other treatment", next="URN-03"),
        ],
        default_next="URN-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "URN-03": QuestionNode(
        nodeId="URN-03", fieldId="burning_on_urination", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bu_yes", "Yes", next="URN-04"),
            AnswerOption("bu_no", "No", next="URN-04"),
        ],
        default_next="URN-04", unknown_option="bu_unknown", **_nu(0.03)
    ),
    "URN-04": QuestionNode(
        nodeId="URN-04", fieldId="frequency_increased", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fi_yes", "Yes — much more often", next="URN-05"),
            AnswerOption("fi_slightly", "A little more often", next="URN-05"),
            AnswerOption("fi_no", "No", next="URN-05"),
        ],
        default_next="URN-05", unknown_option="fi_unknown", **_nu(0.03)
    ),
    "URN-05": QuestionNode(
        nodeId="URN-05", fieldId="flank_pain", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fp_one_side", "Yes — one side", next="URN-06"),
            AnswerOption("fp_both", "Yes — both sides", next="URN-06"),
            AnswerOption("fp_no", "No", next="URN-06"),
        ],
        default_next="URN-06", unknown_option="fp_unknown", **_nu(0.03)
    ),
    "URN-06": QuestionNode(
        nodeId="URN-06", fieldId="haematuria", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hu_visible", "Yes — visible blood or colour", next="URN-07"),
            AnswerOption("hu_no", "No — normal colour", next="URN-07"),
        ],
        default_next="URN-07", unknown_option="hu_unknown", **_nu(0.03)
    ),
    "URN-07": QuestionNode(
        nodeId="URN-07", fieldId="urethral_discharge", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ud_yes", "Yes", next="URN-08"),
            AnswerOption("ud_no", "No", next="URN-08"),
        ],
        default_next="URN-08", unknown_option="ud_unknown", **_nu(0.03)
    ),
    "URN-08": QuestionNode(
        nodeId="URN-08", fieldId="pregnancy_status", answerType="SINGLE_CHOICE",
        guard=lambda fields: fields.get("_sex") is not None and fields["_sex"].value == "F" and fields.get("_age_years") is not None and 15 <= fields["_age_years"].value <= 49,
        options=[
            AnswerOption("pg_yes", "Yes", next="URN-S1"),
            AnswerOption("pg_no", "No", next="URN-S1"),
        ],
        default_next="URN-S1", unknown_option="pg_unknown", **_nu(0.03)
    ),

    "URN-S1": SubtreeRefNode("URN-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="URN-G2a"),
    "URN-G2a": GatewayNode("URN-G2a", "GW-URN-URG-1", _gw_urn_urg1_pyelo, next="URN-G2b",
                           raisesTo="REFER_URGENT", severeConditions=["pyelonephritis"]),
    "URN-G2b": GatewayNode("URN-G2b", "GW-URN-URG-3", _gw_urn_urg3_haematuria, next="URN-G2c",
                           raisesTo="REFER_URGENT", severeConditions=["renal stone", "malignancy", "glomerulonephritis"]),
    "URN-G2c": GatewayNode("URN-G2c", "GW-URN-URG-4", _gw_urn_urg4_pregnancy, next="URN-G2d",
                           raisesTo="REFER_URGENT", severeConditions=["UTI in pregnancy (preterm risk)"]),
    "URN-G2d": GatewayNode("URN-G2d", "GW-URN-URG-5", _gw_urn_urg5_sti, next="URN-END",
                           raisesTo="REFER_URGENT", severeConditions=["STI — partner notification", "syndromic management"]),
    "URN-END": TerminalNode("URN-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="URN-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Urinary symptoms clinical distribution"

_entries = []

_entries += expand_entries("URN-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_cannot_pass_urine": 0.005, "ds_high_fever_urine": 0.01, "ds_severe_flank_pain": 0.01,
             "ds_blood_in_urine": 0.01, "ds_confusion": 0.001, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_cannot_pass_urine": 0.02, "ds_high_fever_urine": 0.05, "ds_severe_flank_pain": 0.05,
                "ds_blood_in_urine": 0.05, "ds_confusion": 0.005, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_cannot_pass_urine": 0.12, "ds_high_fever_urine": 0.25, "ds_severe_flank_pain": 0.25,
               "ds_blood_in_urine": 0.15, "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_cannot_feed": 0.02},
}, overrides={
    ("pyelonephritis_upper_uti", "moderate"): {"ds_cannot_pass_urine": 0.01, "ds_high_fever_urine": 0.65, "ds_severe_flank_pain": 0.50,
                                               "ds_blood_in_urine": 0.10, "ds_confusion": 0.02, "ds_unconscious": 0.01, "ds_cannot_feed": 0.02},
    ("pyelonephritis_upper_uti", "severe"): {"ds_cannot_pass_urine": 0.05, "ds_high_fever_urine": 0.85, "ds_severe_flank_pain": 0.70,
                                             "ds_blood_in_urine": 0.20, "ds_confusion": 0.25, "ds_unconscious": 0.08, "ds_cannot_feed": 0.05},
    ("urolithiasis_renal_colic", "severe"): {"ds_cannot_pass_urine": 0.40, "ds_high_fever_urine": 0.05, "ds_severe_flank_pain": 0.90,
                                             "ds_blood_in_urine": 0.45, "ds_confusion": 0.01, "ds_unconscious": 0.01, "ds_cannot_feed": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.05,
        "pt_prescribed_prior": 0.15, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bu_yes": 0.85, "bu_no": 0.15} for s in SEVERITIES
}, overrides={
    ("lower_urinary_tract_infection_cystitis", s): {"bu_yes": 0.95, "bu_no": 0.05} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"fi_yes": 0.40, "fi_slightly": 0.40, "fi_no": 0.20},
    "moderate": {"fi_yes": 0.65, "fi_slightly": 0.25, "fi_no": 0.10},
    "severe": {"fi_yes": 0.80, "fi_slightly": 0.15, "fi_no": 0.05},
}, overrides={
    ("lower_urinary_tract_infection_cystitis", "moderate"): {"fi_yes": 0.85, "fi_slightly": 0.12, "fi_no": 0.03},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"fp_one_side": 0.05, "fp_both": 0.02, "fp_no": 0.93},
    "moderate": {"fp_one_side": 0.15, "fp_both": 0.05, "fp_no": 0.80},
    "severe": {"fp_one_side": 0.30, "fp_both": 0.10, "fp_no": 0.60},
}, overrides={
    ("pyelonephritis_upper_uti", "moderate"): {"fp_one_side": 0.65, "fp_both": 0.20, "fp_no": 0.15},
    ("pyelonephritis_upper_uti", "severe"): {"fp_one_side": 0.70, "fp_both": 0.25, "fp_no": 0.05},
    ("urolithiasis_renal_colic", "moderate"): {"fp_one_side": 0.80, "fp_both": 0.05, "fp_no": 0.15},
    ("urolithiasis_renal_colic", "severe"): {"fp_one_side": 0.85, "fp_both": 0.05, "fp_no": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"hu_visible": 0.03, "hu_no": 0.97},
    "moderate": {"hu_visible": 0.10, "hu_no": 0.90},
    "severe": {"hu_visible": 0.25, "hu_no": 0.75},
}, overrides={
    ("urolithiasis_renal_colic", "moderate"): {"hu_visible": 0.65, "hu_no": 0.35},
    ("urolithiasis_renal_colic", "severe"): {"hu_visible": 0.80, "hu_no": 0.20},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ud_yes": 0.05, "ud_no": 0.95} for s in SEVERITIES
}, overrides={
    ("sexually_transmitted_infection_urethritis", s): {"ud_yes": 0.88, "ud_no": 0.12} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("URN-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pg_yes": 0.15, "pg_no": 0.85} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("pyelonephritis_upper_uti",),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
