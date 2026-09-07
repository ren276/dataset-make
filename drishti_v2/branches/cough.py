"""
drishti_v2/branches/cough.py
The `cough` branch (branch-authoring-batch-1-memo.md section 1).
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
from .subtrees import (
    make_tb_screen_nodes, make_fever_qual_nodes,
    expand_tb_screen_entries, expand_fever_qual_entries
)

CATEGORY_ID = "cough"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "acute_bronchitis_or_urti": ConditionSpec("acute_bronchitis_or_urti", 0.60, "IND-PRESENT",
        "POSEIDON/Odisha acute respiratory presentation"),
    "pneumonia": ConditionSpec("pneumonia", 0.12, "IND-PRESENT",
        "Community-acquired pneumonia in PHC population", severeConditions=("pneumonia",)),
    "asthma_or_copd": ConditionSpec("asthma_or_copd", 0.15, "IND-PRESENT",
        "Obstructive airway disease (asthma/COPD)", severeConditions=("asthma", "COPD")),
    "pulmonary_tuberculosis": ConditionSpec("pulmonary_tuberculosis", 0.08, "IND-PROG",
        "Nikshay India TB programme signal", severeConditions=("pulmonary tuberculosis",)),
    "lung_malignancy_or_chronic": ConditionSpec("lung_malignancy_or_chronic", 0.05, "ASSUMED",
        "Malignancy or chronic suppurative lung disease", severeConditions=("lung malignancy",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "acute_bronchitis_or_urti": {"mild": 0.70, "moderate": 0.25, "severe": 0.05},
    "pneumonia": {"mild": 0.10, "moderate": 0.45, "severe": 0.45},
    "asthma_or_copd": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "pulmonary_tuberculosis": {"mild": 0.15, "moderate": 0.55, "severe": 0.30},
    "lung_malignancy_or_chronic": {"mild": 0.10, "moderate": 0.40, "severe": 0.50},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_rr = specs["respiratory_rate"]
    base_spo2 = specs["spo2"]
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    if condition_id == "pneumonia":
        specs["temperature"] = VitalSpec(base_temp.mean + (1.5 if severity_band != "severe" else 2.2), 0.5, 34, 41)
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + (6 if severity_band != "severe" else 14), 4.0, 5, 90)
        if severity_band == "severe":
            specs["spo2"] = VitalSpec(89.0, 2.5, 60, 100)
            specs["pulse"] = VitalSpec(base_pulse.mean + 25, 10.0, 35, 220)
    elif condition_id == "asthma_or_copd":
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + (5 if severity_band != "severe" else 12), 4.0, 5, 90)
        if severity_band == "severe":
            specs["spo2"] = VitalSpec(90.0, 3.0, 60, 100)
            specs["pulse"] = VitalSpec(base_pulse.mean + 20, 10.0, 35, 220)
    elif severity_band == "severe":
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + 8, 4.0, 5, 90)
        specs["pulse"] = VitalSpec(base_pulse.mean + 18, 10.0, 35, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_cgh_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_convulsion")

def _gw_cgh_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_cgh_emg3(fields, ctx):
    return contains(fields, "danger_signs", "ds_large_haemoptysis")

def _gw_cgh_emg4(fields, ctx):
    return any_of(fields, "danger_signs", ["ds_cannot_speak_sentence", "ds_chest_indrawing", "ds_fast_breathing", "ds_blue_lips"])

def _gw_cgh_emg5(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_cgh_urg1_tb(fields, ctx):
    return (equals(fields, "cough_ge_2_weeks", "c2_yes")
            or equals(fields, "cough_character", "cc_blood")
            or equals(fields, "weight_loss_present", "wl_yes")
            or equals(fields, "night_sweats", "ns_yes")
            or equals(fields, "tb_contact", "tbc_yes"))

def _gw_cgh_urg2_resp(fields, ctx):
    return (equals(fields, "breathlessness_present", "bp_at_rest")
            or (equals(fields, "chest_pain_present", "cp_with_breathing") and equals(fields, "fever_present", "fp_yes")))

_NODES = {
    "CGH-00": QuestionNode(
        nodeId="CGH-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_cannot_speak_sentence", "Too breathless to finish a sentence", next="CGH-G1a"),
            AnswerOption("ds_chest_indrawing", "Chest pulling in below the ribs when breathing", next="CGH-G1a"),
            AnswerOption("ds_fast_breathing", "Breathing fast at rest", next="CGH-G1a"),
            AnswerOption("ds_blue_lips", "Blue lips or tongue", next="CGH-G1a"),
            AnswerOption("ds_large_haemoptysis", "Coughing up a large amount of blood", next="CGH-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="CGH-G1a"),
            AnswerOption("ds_convulsion", "Fits or convulsions", next="CGH-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="CGH-G1a"),
        ],
        default_next="CGH-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "CGH-G1a": GatewayNode("CGH-G1a", "GW-CGH-EMG-1", _gw_cgh_emg1, next="CGH-G1b",
                           routeTo="emergency_convulsions", severeConditions=["severe illness in a child", "hypoxic seizure"]),
    "CGH-G1b": GatewayNode("CGH-G1b", "GW-CGH-EMG-2", _gw_cgh_emg2, next="CGH-G1c",
                           routeTo="emergency_unconscious", severeConditions=["respiratory failure", "severe pneumonia", "sepsis"]),
    "CGH-G1c": GatewayNode("CGH-G1c", "GW-CGH-EMG-3", _gw_cgh_emg3, next="CGH-G1d",
                           routeTo="emergency_heavy_bleeding", severeConditions=["massive haemoptysis", "lung malignancy"]),
    "CGH-G1d": GatewayNode("CGH-G1d", "GW-CGH-EMG-4", _gw_cgh_emg4, next="CGH-G1e",
                           raisesTo="REFER_EMERGENCY", severeConditions=["pneumonia", "severe asthma", "COPD exacerbation"]),
    "CGH-G1e": GatewayNode("CGH-G1e", "GW-CGH-EMG-5", _gw_cgh_emg5, next="CGH-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "CGH-01": QuestionNode(
        nodeId="CGH-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="CGH-02"),
            AnswerOption("pr_same", "About the same", next="CGH-02"),
            AnswerOption("pr_worse", "Worse", next="CGH-02"),
        ],
        default_next="CGH-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "CGH-02": QuestionNode(
        nodeId="CGH-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedy", next="CGH-03"),
            AnswerOption("pt_pharmacy_medicine", "Pharmacy medicine", next="CGH-03"),
            AnswerOption("pt_ayush", "AYUSH / traditional medicine", next="CGH-03"),
            AnswerOption("pt_other_facility", "Treated at another facility", next="CGH-03"),
        ],
        default_next="CGH-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.02)
    ),
    "CGH-03": QuestionNode(
        nodeId="CGH-03", fieldId="cough_character", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("cc_dry", "Dry, no phlegm", next="CGH-04"),
            AnswerOption("cc_productive", "Brings up phlegm", next="CGH-04"),
            AnswerOption("cc_blood", "Blood in the phlegm", next="CGH-G2"),
            AnswerOption("cc_paroxysmal", "Bouts of coughing that end in whoop or vomiting", next="CGH-04"),
        ],
        default_next="CGH-04", unknown_option="cc_unknown", **_nu(0.03)
    ),
    "CGH-G2": GatewayNode("CGH-G2", "GW-CGH-URG-1", _gw_cgh_urg1_tb, next="CGH-04",
                           raisesTo="REFER_URGENT", severeConditions=["pulmonary tuberculosis"]),
    "CGH-04": QuestionNode(
        nodeId="CGH-04", fieldId="wheeze", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("wh_audible", "Yes — can be heard without stethoscope", next="CGH-05"),
            AnswerOption("wh_reported", "Patient or family reports it", next="CGH-05"),
            AnswerOption("wh_no", "No", next="CGH-05"),
        ],
        default_next="CGH-05", unknown_option="wh_unknown", **_nu(0.03)
    ),
    "CGH-05": QuestionNode(
        nodeId="CGH-05", fieldId="breathlessness_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bp_at_rest", "Yes — even at rest", next="CGH-G3"),
            AnswerOption("bp_on_exertion", "Yes — on walking or exertion", next="CGH-06"),
            AnswerOption("bp_no", "No", next="CGH-06"),
        ],
        default_next="CGH-06", unknown_option="bp_unknown", **_nu(0.03)
    ),
    "CGH-G3": GatewayNode("CGH-G3", "GW-CGH-URG-2", _gw_cgh_urg2_resp, next="CGH-06",
                           raisesTo="REFER_URGENT", severeConditions=["pneumonia", "pleural effusion"]),
    "CGH-06": QuestionNode(
        nodeId="CGH-06", fieldId="chest_pain_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("cp_with_breathing", "Yes — worse on breathing in or coughing", next="CGH-G3b"),
            AnswerOption("cp_other", "Yes — not related to breathing", next="CGH-07"),
            AnswerOption("cp_no", "No", next="CGH-07"),
        ],
        default_next="CGH-07", unknown_option="cp_unknown", **_nu(0.03)
    ),
    "CGH-G3b": GatewayNode("CGH-G3b", "GW-CGH-URG-2", _gw_cgh_urg2_resp, next="CGH-07",
                            raisesTo="REFER_URGENT", severeConditions=["pneumonia", "pleural effusion"]),
    "CGH-07": QuestionNode(
        nodeId="CGH-07", fieldId="smoking_biomass_exposure", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("sb_tobacco_current", "Smokes tobacco — bidi or cigarette", next="CGH-S1"),
            AnswerOption("sb_tobacco_past", "Smoked in the past, has stopped", next="CGH-S1"),
            AnswerOption("sb_chulha", "Cooks on a chulha or biomass stove", next="CGH-S1"),
            AnswerOption("sb_occupational", "Works with dust, stone or smoke", next="CGH-S1"),
            AnswerOption("sb_secondhand", "Someone else smokes inside the house", next="CGH-S1"),
        ],
        default_next="CGH-S1", unknown_option="sb_unknown", none_option="sb_none", **_nu(0.03)
    ),
    "CGH-S1": SubtreeRefNode("CGH-S1", make_tb_screen_nodes(), entry="TBS-01", returnNext="CGH-G4"),
    "CGH-G4": GatewayNode("CGH-G4", "GW-CGH-URG-1", _gw_cgh_urg1_tb, next="CGH-S2",
                           raisesTo="REFER_URGENT", severeConditions=["pulmonary tuberculosis"]),
    "CGH-S2": SubtreeRefNode("CGH-S2", make_fever_qual_nodes(), entry="FQ-00", returnNext="CGH-END"),
    "CGH-END": TerminalNode("CGH-END"),
}

BRANCH = BranchDef(categoryId=CATEGORY_ID, version=BRANCH_VERSION,
                    requiredDisposition=REQUIRED_DISPOSITION, nodes=_NODES, entry="CGH-00")

_SRC = "IND-PRESENT"
_SRC_TEXT = "POSEIDON/Odisha acute respiratory presentation"

_entries = []
_entries += expand_entries("CGH-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_cannot_speak_sentence": 0.001, "ds_chest_indrawing": 0.001, "ds_fast_breathing": 0.005,
             "ds_blue_lips": 0.001, "ds_large_haemoptysis": 0.001, "ds_unconscious": 0.001,
             "ds_convulsion": 0.001, "ds_cannot_feed": 0.001},
    "moderate": {"ds_cannot_speak_sentence": 0.01, "ds_chest_indrawing": 0.02, "ds_fast_breathing": 0.05,
                 "ds_blue_lips": 0.005, "ds_large_haemoptysis": 0.005, "ds_unconscious": 0.005,
                 "ds_convulsion": 0.005, "ds_cannot_feed": 0.01},
    "severe": {"ds_cannot_speak_sentence": 0.15, "ds_chest_indrawing": 0.20, "ds_fast_breathing": 0.35,
               "ds_blue_lips": 0.08, "ds_large_haemoptysis": 0.05, "ds_unconscious": 0.05,
               "ds_convulsion": 0.03, "ds_cannot_feed": 0.08},
}, overrides={
    ("pneumonia", "severe"): {"ds_fast_breathing": 0.65, "ds_chest_indrawing": 0.50, "ds_blue_lips": 0.15,
                              "ds_cannot_speak_sentence": 0.25, "ds_large_haemoptysis": 0.05, "ds_unconscious": 0.08,
                              "ds_convulsion": 0.05, "ds_cannot_feed": 0.20},
    ("asthma_or_copd", "severe"): {"ds_cannot_speak_sentence": 0.60, "ds_fast_breathing": 0.55, "ds_chest_indrawing": 0.40,
                                   "ds_blue_lips": 0.12, "ds_large_haemoptysis": 0.01, "ds_unconscious": 0.05,
                                   "ds_convulsion": 0.02, "ds_cannot_feed": 0.10},
    ("lung_malignancy_or_chronic", "severe"): {"ds_large_haemoptysis": 0.25, "ds_cannot_speak_sentence": 0.20,
                                              "ds_fast_breathing": 0.25, "ds_chest_indrawing": 0.15, "ds_blue_lips": 0.05,
                                              "ds_unconscious": 0.05, "ds_convulsion": 0.01, "ds_cannot_feed": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CGH-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.45, "pr_worse": 0.20},
    "moderate": {"pr_better": 0.15, "pr_same": 0.45, "pr_worse": 0.40},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CGH-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.30, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.08, "pt_other_facility": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CGH-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"cc_dry": 0.55, "cc_productive": 0.35, "cc_blood": 0.01, "cc_paroxysmal": 0.09},
    "moderate": {"cc_dry": 0.35, "cc_productive": 0.55, "cc_blood": 0.02, "cc_paroxysmal": 0.08},
    "severe": {"cc_dry": 0.25, "cc_productive": 0.60, "cc_blood": 0.08, "cc_paroxysmal": 0.07},
}, overrides={
    ("pulmonary_tuberculosis", "moderate"): {"cc_dry": 0.15, "cc_productive": 0.65, "cc_blood": 0.15, "cc_paroxysmal": 0.05},
    ("pulmonary_tuberculosis", "severe"): {"cc_dry": 0.10, "cc_productive": 0.55, "cc_blood": 0.30, "cc_paroxysmal": 0.05},
    ("lung_malignancy_or_chronic", "severe"): {"cc_dry": 0.20, "cc_productive": 0.50, "cc_blood": 0.25, "cc_paroxysmal": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CGH-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"wh_audible": 0.05, "wh_reported": 0.15, "wh_no": 0.80},
    "moderate": {"wh_audible": 0.15, "wh_reported": 0.30, "wh_no": 0.55},
    "severe": {"wh_audible": 0.35, "wh_reported": 0.35, "wh_no": 0.30},
}, overrides={
    ("asthma_or_copd", "mild"): {"wh_audible": 0.30, "wh_reported": 0.45, "wh_no": 0.25},
    ("asthma_or_copd", "moderate"): {"wh_audible": 0.55, "wh_reported": 0.35, "wh_no": 0.10},
    ("asthma_or_copd", "severe"): {"wh_audible": 0.75, "wh_reported": 0.20, "wh_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CGH-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bp_at_rest": 0.02, "bp_on_exertion": 0.18, "bp_no": 0.80},
    "moderate": {"bp_at_rest": 0.10, "bp_on_exertion": 0.45, "bp_no": 0.45},
    "severe": {"bp_at_rest": 0.45, "bp_on_exertion": 0.45, "bp_no": 0.10},
}, overrides={
    ("asthma_or_copd", "severe"): {"bp_at_rest": 0.70, "bp_on_exertion": 0.25, "bp_no": 0.05},
    ("pneumonia", "severe"): {"bp_at_rest": 0.60, "bp_on_exertion": 0.35, "bp_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CGH-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"cp_with_breathing": 0.08, "cp_other": 0.05, "cp_no": 0.87},
    "moderate": {"cp_with_breathing": 0.25, "cp_other": 0.10, "cp_no": 0.65},
    "severe": {"cp_with_breathing": 0.45, "cp_other": 0.15, "cp_no": 0.40},
}, overrides={
    ("pneumonia", "moderate"): {"cp_with_breathing": 0.45, "cp_other": 0.05, "cp_no": 0.50},
    ("pneumonia", "severe"): {"cp_with_breathing": 0.65, "cp_other": 0.05, "cp_no": 0.30},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CGH-07", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"sb_tobacco_current": 0.20, "sb_tobacco_past": 0.10, "sb_chulha": 0.35,
        "sb_occupational": 0.10, "sb_secondhand": 0.25}
    for s in SEVERITIES
}, overrides={
    ("asthma_or_copd", s): {"sb_tobacco_current": 0.45, "sb_tobacco_past": 0.25, "sb_chulha": 0.50,
                            "sb_occupational": 0.15, "sb_secondhand": 0.30} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

# Subtrees
_entries += expand_tb_screen_entries(CONDITION_IDS, SEVERITIES, tb_conditions=("pulmonary_tuberculosis",),
                                     source_type="IND-PROG", source="Nikshay India TB programme")
_entries += expand_fever_qual_entries(CONDITION_IDS, SEVERITIES, fever_conditions=("pneumonia", "acute_bronchitis_or_urti"),
                                      bleeding_conditions=("lung_malignancy_or_chronic", "pulmonary_tuberculosis"),
                                      source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
