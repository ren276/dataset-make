"""
drishti_v2/branches/breathlessness.py
The `breathlessness` branch (branch-authoring-batch-1-memo.md section 4).
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

CATEGORY_ID = "breathlessness"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_URGENT"

CONDITIONS = {
    "copd_or_asthma_exacerbation": ConditionSpec("copd_or_asthma_exacerbation", 0.38, "IND-PRESENT",
        "COPD or asthma acute exacerbation", severeConditions=("severe asthma",)),
    "pneumonia_lower_respiratory": ConditionSpec("pneumonia_lower_respiratory", 0.22, "IND-PRESENT",
        "Community-acquired pneumonia / LRTI", severeConditions=("pneumonia",)),
    "congestive_heart_failure": ConditionSpec("congestive_heart_failure", 0.18, "IND-PRESENT",
        "Acute decompensated heart failure", severeConditions=("heart failure",)),
    "severe_anaemia_breathlessness": ConditionSpec("severe_anaemia_breathlessness", 0.10, "IND-PRESENT",
        "Severe anaemia presenting with dyspnoea", severeConditions=("severe anaemia",)),
    "pulmonary_embolism_or_dvt": ConditionSpec("pulmonary_embolism_or_dvt", 0.05, "WORLD",
        "Pulmonary embolism or DVT", severeConditions=("pulmonary embolism",)),
    "acute_allergic_anaphylaxis": ConditionSpec("acute_allergic_anaphylaxis", 0.04, "ASSUMED",
        "Acute anaphylaxis / angio-oedema", severeConditions=("anaphylaxis",)),
    "tuberculosis_breathlessness": ConditionSpec("tuberculosis_breathlessness", 0.03, "IND-PROG",
        "Pulmonary tuberculosis presenting with dyspnoea", severeConditions=("pulmonary tuberculosis",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "copd_or_asthma_exacerbation": {"mild": 0.50, "moderate": 0.35, "severe": 0.15},
    "pneumonia_lower_respiratory": {"mild": 0.30, "moderate": 0.45, "severe": 0.25},
    "congestive_heart_failure": {"mild": 0.25, "moderate": 0.45, "severe": 0.30},
    "severe_anaemia_breathlessness": {"mild": 0.30, "moderate": 0.40, "severe": 0.30},
    "pulmonary_embolism_or_dvt": {"mild": 0.10, "moderate": 0.30, "severe": 0.60},
    "acute_allergic_anaphylaxis": {"mild": 0.15, "moderate": 0.35, "severe": 0.50},
    "tuberculosis_breathlessness": {"mild": 0.30, "moderate": 0.45, "severe": 0.25},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]
    base_spo2 = specs["spo2"]
    base_temp = specs["temperature"]

    # Breathlessness always impacts resp_rate and spo2
    if severity_band == "severe":
        specs["respiratory_rate"] = VitalSpec(34.0, 4.0, 10, 60)
        specs["spo2"] = VitalSpec(86.0, 3.5, 50, 100)
        specs["pulse"] = VitalSpec(base_pulse.mean + 25, 10.0, 35, 220)
    elif severity_band == "moderate":
        specs["respiratory_rate"] = VitalSpec(26.0, 3.0, 10, 50)
        specs["spo2"] = VitalSpec(92.0, 2.5, 60, 100)
        specs["pulse"] = VitalSpec(base_pulse.mean + 12, 8.0, 35, 220)
    else:
        specs["respiratory_rate"] = VitalSpec(22.0, 2.5, 10, 40)
        specs["spo2"] = VitalSpec(96.0, 1.5, 70, 100)

    if condition_id in ("pneumonia_lower_respiratory", "tuberculosis_breathlessness"):
        specs["temperature"] = VitalSpec(base_temp.mean + (1.2 if severity_band != "severe" else 2.0), 0.4, 34, 41)

    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_bre_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_bre_emg2(fields, ctx):
    return (any_of(fields, "danger_signs", ["ds_cannot_speak_sentence", "ds_blue_lips", "ds_chest_indrawing"])
            or equals(fields, "breathlessness_present", "bp_at_rest"))

def _gw_bre_emg3(fields, ctx):
    return contains(fields, "danger_signs", "ds_swollen_face")

def _gw_bre_emg4(fields, ctx):
    return contains(fields, "danger_signs", "ds_frothy_sputum") or (
        contains(fields, "danger_signs", "ds_cannot_lie_flat") and equals(fields, "ankle_swelling", "as_both_legs")
    )

def _gw_bre_emg5_pe(fields, ctx):
    return equals(fields, "ankle_swelling", "as_one_leg") and (
        equals(fields, "breathlessness_present", "bp_at_rest") or equals(fields, "chest_pain_present", "cp_with_breathing")
    )

def _gw_bre_emg6_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_bre_urg1_anaemia(fields, ctx):
    return contains(fields, "danger_signs", "ds_severe_pallor")

def _gw_bre_urg2_hf(fields, ctx):
    return any_of(fields, "orthopnoea", ["op_needs_pillows", "op_wakes_gasping", "op_both"]) or equals(fields, "ankle_swelling", "as_both_legs")

def _gw_bre_urg3_tb(fields, ctx):
    return equals(fields, "cough_character", "cc_blood") or (
        value_of(fields, "duration_bucket") in ("month_plus", "chronic") and contains(fields, "smoking_biomass_exposure", "sb_occupational")
    )

_NODES = {
    "BRE-00": QuestionNode(
        nodeId="BRE-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_cannot_speak_sentence", "Too breathless to finish a sentence", next="BRE-G1a"),
            AnswerOption("ds_blue_lips", "Blue lips or tongue", next="BRE-G1a"),
            AnswerOption("ds_chest_indrawing", "Chest pulling in below the ribs when breathing", next="BRE-G1a"),
            AnswerOption("ds_cannot_lie_flat", "Cannot lie flat — has to sit up to breathe", next="BRE-G1a"),
            AnswerOption("ds_frothy_sputum", "Coughing up pink or frothy spit", next="BRE-G1a"),
            AnswerOption("ds_swollen_face", "Swollen face, lips or tongue", next="BRE-G1a"),
            AnswerOption("ds_severe_pallor", "Palms or inner eyelids look very pale", next="BRE-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="BRE-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="BRE-G1a"),
        ],
        default_next="BRE-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "BRE-G1a": GatewayNode("BRE-G1a", "GW-BRE-EMG-1", _gw_bre_emg1, next="BRE-G1b",
                           routeTo="emergency_unconscious", severeConditions=["respiratory failure", "severe pneumonia", "severe anaemia", "sepsis"]),
    "BRE-G1b": GatewayNode("BRE-G1b", "GW-BRE-EMG-2", _gw_bre_emg2, next="BRE-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["pneumonia", "severe asthma", "COPD exacerbation", "respiratory failure"]),
    "BRE-G1c": GatewayNode("BRE-G1c", "GW-BRE-EMG-3", _gw_bre_emg3, next="BRE-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["anaphylaxis", "angio-oedema"]),
    "BRE-G1d": GatewayNode("BRE-G1d", "GW-BRE-EMG-4", _gw_bre_emg4, next="BRE-G1e",
                           raisesTo="REFER_EMERGENCY", severeConditions=["acute heart failure", "pulmonary oedema"]),
    "BRE-G1e": GatewayNode("BRE-G1e", "GW-BRE-EMG-6", _gw_bre_emg6_infant, next="BRE-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "BRE-01": QuestionNode(
        nodeId="BRE-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="BRE-02"),
            AnswerOption("pr_same", "About the same", next="BRE-02"),
            AnswerOption("pr_worse", "Worse", next="BRE-02"),
        ],
        default_next="BRE-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "BRE-02": QuestionNode(
        nodeId="BRE-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="BRE-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="BRE-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="BRE-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="BRE-03"),
            AnswerOption("pt_other", "Other treatment", next="BRE-03"),
        ],
        default_next="BRE-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "BRE-03": QuestionNode(
        nodeId="BRE-03", fieldId="breathlessness_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bp_at_rest", "Even at rest", next="BRE-04"),
            AnswerOption("bp_on_exertion", "On walking or on exertion", next="BRE-04"),
            AnswerOption("bp_no", "Not at the moment", next="BRE-04"),
        ],
        default_next="BRE-04", unknown_option="bp_unknown", **_nu(0.03)
    ),
    "BRE-04": QuestionNode(
        nodeId="BRE-04", fieldId="orthopnoea", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("op_needs_pillows", "Has to sit up or use extra pillows to breathe", next="BRE-05"),
            AnswerOption("op_wakes_gasping", "Wakes at night gasping for breath", next="BRE-05"),
            AnswerOption("op_both", "Both", next="BRE-05"),
            AnswerOption("op_sleeps_flat", "Sleeps flat without trouble", next="BRE-05"),
        ],
        default_next="BRE-05", unknown_option="op_unknown", **_nu(0.03)
    ),
    "BRE-05": QuestionNode(
        nodeId="BRE-05", fieldId="wheeze", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("wh_audible", "Whistling heard by you or the family", next="BRE-06"),
            AnswerOption("wh_reported", "Patient feels tightness or wheeze inside", next="BRE-06"),
            AnswerOption("wh_no", "No whistling or tightness", next="BRE-06"),
        ],
        default_next="BRE-06", unknown_option="wh_unknown", **_nu(0.03)
    ),
    "BRE-06": QuestionNode(
        nodeId="BRE-06", fieldId="chest_pain_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("cp_with_breathing", "Sharp pain that is worse when breathing in", next="BRE-07"),
            AnswerOption("cp_other", "Pain in the chest, but not worse with breathing", next="BRE-07"),
            AnswerOption("cp_no", "No chest pain", next="BRE-07"),
        ],
        default_next="BRE-07", unknown_option="cp_unknown", **_nu(0.03)
    ),
    "BRE-07": QuestionNode(
        nodeId="BRE-07", fieldId="ankle_swelling", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("as_both_legs", "Yes — both legs", next="BRE-08"),
            AnswerOption("as_one_leg", "Yes — one leg only", next="BRE-08"),
            AnswerOption("as_no", "No", next="BRE-08"),
        ],
        default_next="BRE-08", unknown_option="as_unknown", **_nu(0.03)
    ),
    "BRE-08": QuestionNode(
        nodeId="BRE-08", fieldId="cough_character", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("cc_dry", "Dry cough", next="BRE-09"),
            AnswerOption("cc_productive", "Cough with spit or phlegm", next="BRE-09"),
            AnswerOption("cc_blood", "Blood in the spit", next="BRE-09"),
            AnswerOption("cc_paroxysmal", "Severe bouts that leave the patient gasping", next="BRE-09"),
            AnswerOption("cc_none", "No cough", next="BRE-09"),
        ],
        default_next="BRE-09", unknown_option="cc_unknown", **_nu(0.03)
    ),

    "BRE-09": QuestionNode(
        nodeId="BRE-09", fieldId="smoking_biomass_exposure", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("sb_tobacco_current", "Smokes bidi or cigarette currently", next="BRE-S1"),
            AnswerOption("sb_tobacco_past", "Smoked in the past", next="BRE-S1"),
            AnswerOption("sb_chulha", "Cooks with wood, crop residue, or dung (chulha)", next="BRE-S1"),
            AnswerOption("sb_occupational", "Work exposure to heavy dust, flour, grain, or stone", next="BRE-S1"),
            AnswerOption("sb_secondhand", "Lives with a smoker", next="BRE-S1"),
        ],
        default_next="BRE-S1", unknown_option="sb_unknown", none_option="sb_none", **_nu(0.03)
    ),

    "BRE-S1": SubtreeRefNode("BRE-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="BRE-G2"),

    "BRE-G2": GatewayNode("BRE-G2", "GW-BRE-EMG-2", _gw_bre_emg2, next="BRE-G3",
                          raisesTo="REFER_EMERGENCY", severeConditions=["pneumonia", "severe asthma", "COPD exacerbation", "respiratory failure"]),
    "BRE-G3": GatewayNode("BRE-G3", "GW-BRE-EMG-4", _gw_bre_emg4, next="BRE-G4",
                          raisesTo="REFER_EMERGENCY", severeConditions=["acute heart failure", "pulmonary oedema"]),
    "BRE-G4": GatewayNode("BRE-G4", "GW-BRE-EMG-5", _gw_bre_emg5_pe, next="BRE-G5",
                          raisesTo="REFER_EMERGENCY", severeConditions=["pulmonary embolism", "deep vein thrombosis"]),
    "BRE-G5": GatewayNode("BRE-G5", "GW-BRE-URG-1", _gw_bre_urg1_anaemia, next="BRE-G6",
                          raisesTo="REFER_URGENT", severeConditions=["severe anaemia requiring transfusion"]),
    "BRE-G6": GatewayNode("BRE-G6", "GW-BRE-URG-2", _gw_bre_urg2_hf, next="BRE-G7",
                          raisesTo="REFER_URGENT", severeConditions=["heart failure", "cor pulmonale", "renal failure"]),
    "BRE-G7": GatewayNode("BRE-G7", "GW-BRE-URG-3", _gw_bre_urg3_tb, next="BRE-END",
                          raisesTo="REFER_URGENT", severeConditions=["pulmonary tuberculosis", "silicosis", "lung malignancy"]),

    "BRE-END": TerminalNode("BRE-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="BRE-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Breathlessness clinical distribution"

_entries = []

_entries += expand_entries("BRE-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_cannot_speak_sentence": 0.01, "ds_blue_lips": 0.005, "ds_chest_indrawing": 0.01,
             "ds_cannot_lie_flat": 0.02, "ds_frothy_sputum": 0.002, "ds_swollen_face": 0.005,
             "ds_severe_pallor": 0.02, "ds_unconscious": 0.002, "ds_cannot_feed": 0.01},
    "moderate": {"ds_cannot_speak_sentence": 0.08, "ds_blue_lips": 0.03, "ds_chest_indrawing": 0.08,
                "ds_cannot_lie_flat": 0.10, "ds_frothy_sputum": 0.01, "ds_swollen_face": 0.02,
                "ds_severe_pallor": 0.05, "ds_unconscious": 0.01, "ds_cannot_feed": 0.03},
    "severe": {"ds_cannot_speak_sentence": 0.40, "ds_blue_lips": 0.25, "ds_chest_indrawing": 0.35,
               "ds_cannot_lie_flat": 0.35, "ds_frothy_sputum": 0.08, "ds_swollen_face": 0.08,
               "ds_severe_pallor": 0.12, "ds_unconscious": 0.06, "ds_cannot_feed": 0.12},
}, overrides={
    ("congestive_heart_failure", "severe"): {"ds_cannot_speak_sentence": 0.35, "ds_blue_lips": 0.20, "ds_chest_indrawing": 0.15,
                                            "ds_cannot_lie_flat": 0.70, "ds_frothy_sputum": 0.30, "ds_swollen_face": 0.01,
                                            "ds_severe_pallor": 0.05, "ds_unconscious": 0.05, "ds_cannot_feed": 0.10},
    ("acute_allergic_anaphylaxis", "severe"): {"ds_cannot_speak_sentence": 0.50, "ds_blue_lips": 0.30, "ds_chest_indrawing": 0.40,
                                              "ds_cannot_lie_flat": 0.10, "ds_frothy_sputum": 0.01, "ds_swollen_face": 0.85,
                                              "ds_severe_pallor": 0.02, "ds_unconscious": 0.15, "ds_cannot_feed": 0.10},
    ("severe_anaemia_breathlessness", "severe"): {"ds_cannot_speak_sentence": 0.25, "ds_blue_lips": 0.05, "ds_chest_indrawing": 0.10,
                                                 "ds_cannot_lie_flat": 0.15, "ds_frothy_sputum": 0.01, "ds_swollen_face": 0.01,
                                                 "ds_severe_pallor": 0.85, "ds_unconscious": 0.05, "ds_cannot_feed": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.45, "pr_worse": 0.40},
    "severe": {"pr_better": 0.05, "pr_same": 0.20, "pr_worse": 0.75},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.35, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.08,
        "pt_prescribed_prior": 0.25, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bp_at_rest": 0.05, "bp_on_exertion": 0.80, "bp_no": 0.15},
    "moderate": {"bp_at_rest": 0.20, "bp_on_exertion": 0.75, "bp_no": 0.05},
    "severe": {"bp_at_rest": 0.75, "bp_on_exertion": 0.23, "bp_no": 0.02},
}, overrides={
    ("copd_or_asthma_exacerbation", "severe"): {"bp_at_rest": 0.85, "bp_on_exertion": 0.15, "bp_no": 0.00},
    ("pulmonary_embolism_or_dvt", "severe"): {"bp_at_rest": 0.90, "bp_on_exertion": 0.10, "bp_no": 0.00},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"op_needs_pillows": 0.10, "op_wakes_gasping": 0.05, "op_both": 0.05, "op_sleeps_flat": 0.80},
    "moderate": {"op_needs_pillows": 0.25, "op_wakes_gasping": 0.15, "op_both": 0.15, "op_sleeps_flat": 0.45},
    "severe": {"op_needs_pillows": 0.35, "op_wakes_gasping": 0.20, "op_both": 0.30, "op_sleeps_flat": 0.15},
}, overrides={
    ("congestive_heart_failure", "moderate"): {"op_needs_pillows": 0.40, "op_wakes_gasping": 0.20, "op_both": 0.30, "op_sleeps_flat": 0.10},
    ("congestive_heart_failure", "severe"): {"op_needs_pillows": 0.30, "op_wakes_gasping": 0.20, "op_both": 0.45, "op_sleeps_flat": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"wh_audible": 0.10, "wh_reported": 0.20, "wh_no": 0.70},
    "moderate": {"wh_audible": 0.25, "wh_reported": 0.30, "wh_no": 0.45},
    "severe": {"wh_audible": 0.45, "wh_reported": 0.30, "wh_no": 0.25},
}, overrides={
    ("copd_or_asthma_exacerbation", "mild"): {"wh_audible": 0.35, "wh_reported": 0.45, "wh_no": 0.20},
    ("copd_or_asthma_exacerbation", "moderate"): {"wh_audible": 0.60, "wh_reported": 0.30, "wh_no": 0.10},
    ("copd_or_asthma_exacerbation", "severe"): {"wh_audible": 0.75, "wh_reported": 0.20, "wh_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"cp_with_breathing": 0.08, "cp_other": 0.05, "cp_no": 0.87},
    "moderate": {"cp_with_breathing": 0.20, "cp_other": 0.10, "cp_no": 0.70},
    "severe": {"cp_with_breathing": 0.35, "cp_other": 0.15, "cp_no": 0.50},
}, overrides={
    ("pulmonary_embolism_or_dvt", "moderate"): {"cp_with_breathing": 0.60, "cp_other": 0.10, "cp_no": 0.30},
    ("pulmonary_embolism_or_dvt", "severe"): {"cp_with_breathing": 0.75, "cp_other": 0.10, "cp_no": 0.15},
    ("pneumonia_lower_respiratory", "moderate"): {"cp_with_breathing": 0.50, "cp_other": 0.05, "cp_no": 0.45},
    ("pneumonia_lower_respiratory", "severe"): {"cp_with_breathing": 0.65, "cp_other": 0.05, "cp_no": 0.30},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"as_both_legs": 0.10, "as_one_leg": 0.02, "as_no": 0.88},
    "moderate": {"as_both_legs": 0.25, "as_one_leg": 0.05, "as_no": 0.70},
    "severe": {"as_both_legs": 0.40, "as_one_leg": 0.08, "as_no": 0.52},
}, overrides={
    ("congestive_heart_failure", "moderate"): {"as_both_legs": 0.70, "as_one_leg": 0.02, "as_no": 0.28},
    ("congestive_heart_failure", "severe"): {"as_both_legs": 0.85, "as_one_leg": 0.02, "as_no": 0.13},
    ("pulmonary_embolism_or_dvt", "moderate"): {"as_both_legs": 0.05, "as_one_leg": 0.55, "as_no": 0.40},
    ("pulmonary_embolism_or_dvt", "severe"): {"as_both_legs": 0.05, "as_one_leg": 0.70, "as_no": 0.25},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-08", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"cc_dry": 0.35, "cc_productive": 0.25, "cc_blood": 0.01, "cc_paroxysmal": 0.05, "cc_none": 0.34},
    "moderate": {"cc_dry": 0.35, "cc_productive": 0.35, "cc_blood": 0.02, "cc_paroxysmal": 0.08, "cc_none": 0.20},
    "severe": {"cc_dry": 0.30, "cc_productive": 0.45, "cc_blood": 0.06, "cc_paroxysmal": 0.09, "cc_none": 0.10},
}, overrides={
    ("tuberculosis_breathlessness", "moderate"): {"cc_dry": 0.15, "cc_productive": 0.60, "cc_blood": 0.20, "cc_paroxysmal": 0.03, "cc_none": 0.02},
    ("tuberculosis_breathlessness", "severe"): {"cc_dry": 0.10, "cc_productive": 0.50, "cc_blood": 0.35, "cc_paroxysmal": 0.03, "cc_none": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BRE-09", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"sb_tobacco_current": 0.20, "sb_tobacco_past": 0.10, "sb_chulha": 0.35,
        "sb_occupational": 0.10, "sb_secondhand": 0.25}
    for s in SEVERITIES
}, overrides={
    ("copd_or_asthma_exacerbation", s): {"sb_tobacco_current": 0.50, "sb_tobacco_past": 0.30, "sb_chulha": 0.55,
                                         "sb_occupational": 0.15, "sb_secondhand": 0.35}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("pneumonia_lower_respiratory", "tuberculosis_breathlessness"),
    bleeding_conditions=("tuberculosis_breathlessness",),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
