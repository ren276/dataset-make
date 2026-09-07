"""
drishti_v2/branches/diarrhoea.py
The `diarrhoea` branch (branch-authoring-batch-1-memo.md section 2).
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
    make_dehydration_nodes, make_fever_qual_nodes,
    expand_dehydration_entries, expand_fever_qual_entries
)

CATEGORY_ID = "diarrhoea"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "acute_gastroenteritis": ConditionSpec("acute_gastroenteritis", 0.65, "IND-PRESENT",
        "AIIMS Bhopal diarrhoeal disease 7.9%"),
    "amoebiasis_or_giardiasis": ConditionSpec("amoebiasis_or_giardiasis", 0.15, "IND-PRESENT",
        "Protozoal diarrhoea in rural cohort"),
    "dysentery_shigellosis": ConditionSpec("dysentery_shigellosis", 0.10, "IND-PRESENT",
        "Invasive bacterial dysentery", severeConditions=("dysentery",)),
    "severe_secretory_diarrhoea_or_cholera": ConditionSpec("severe_secretory_diarrhoea_or_cholera", 0.05, "WORLD",
        "High-output secretory diarrhoea / cholera", severeConditions=("cholera", "dehydration")),
    "enteric_fever_diarrhoea": ConditionSpec("enteric_fever_diarrhoea", 0.05, "WORLD",
        "Salmonella enteric presentation with diarrhoea", severeConditions=("enteric fever",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "acute_gastroenteritis": {"mild": 0.65, "moderate": 0.25, "severe": 0.10},
    "amoebiasis_or_giardiasis": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
    "dysentery_shigellosis": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "severe_secretory_diarrhoea_or_cholera": {"mild": 0.05, "moderate": 0.25, "severe": 0.70},
    "enteric_fever_diarrhoea": {"mild": 0.15, "moderate": 0.50, "severe": 0.35},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sbp = specs["bp_systolic"]
    base_dbp = specs["bp_diastolic"]
    base_temp = specs["temperature"]

    if condition_id == "severe_secretory_diarrhoea_or_cholera":
        if severity_band == "severe":
            specs["pulse"] = VitalSpec(135.0, 10.0, 35, 220)
            specs["bp_systolic"] = VitalSpec(82.0, 6.0, 50, 180)
            specs["bp_diastolic"] = VitalSpec(52.0, 5.0, 30, 120)
        else:
            specs["pulse"] = VitalSpec(base_pulse.mean + 15, base_pulse.sd, 35, 220)
    elif condition_id == "dysentery_shigellosis" or condition_id == "enteric_fever_diarrhoea":
        specs["temperature"] = VitalSpec(base_temp.mean + (1.2 if severity_band != "severe" else 2.0), 0.4, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + (12 if severity_band != "severe" else 25), base_pulse.sd, 35, 220)
    elif severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 20, 10.0, 35, 220)
        specs["bp_systolic"] = VitalSpec(base_sbp.mean - 15, 8.0, 50, 200)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_dia_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_convulsion")

def _gw_dia_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_dia_emg4(fields, ctx):
    return contains(fields, "danger_signs", "ds_abdomen_rigid")

def _gw_dia_emg5(fields, ctx):
    return ctx.get("age_years", 99) < 5 and (contains(fields, "danger_signs", "ds_cannot_feed") or contains(fields, "danger_signs", "ds_cannot_drink"))

def _gw_dia_urg2_dys(fields, ctx):
    bs = value_of(fields, "blood_in_stool")
    return bs in ("bs_frank", "bs_streaks", "bs_black") or contains(fields, "danger_signs", "ds_blood_stool")

def _gw_dia_urg3_high(fields, ctx):
    return (equals(fields, "stool_consistency", "sc_rice_water")
            or equals(fields, "stool_frequency_band", "sf_gt_10")
            or equals(fields, "vomiting_present", "vm_yes_everything")
            or (equals(fields, "water_source", "ws_surface") and equals(fields, "household_others_affected", "ho_yes")))

def _gw_dia_emg3_imci(fields, ctx):
    thirst = value_of(fields, "dehydration_thirst")
    eyes = value_of(fields, "dehydration_eyes")
    pinch = value_of(fields, "skin_pinch")
    gen = value_of(fields, "general_condition")
    A = (gen == "gc_lethargic")
    B = (eyes == "de_yes")
    C = thirst in ("dt_unable", "dt_poor")
    D = (pinch == "sp_very_slow")
    return (A and B) or (A and C) or (A and D) or (B and C) or (B and D) or (C and D)

def _gw_dia_urg1_some(fields, ctx):
    thirst = value_of(fields, "dehydration_thirst")
    eyes = value_of(fields, "dehydration_eyes")
    pinch = value_of(fields, "skin_pinch")
    urine = value_of(fields, "urine_output_reduced")
    gen = value_of(fields, "general_condition")
    return (thirst == "dt_eager" or eyes == "de_yes" or pinch == "sp_slow"
            or urine in ("uo_reduced", "uo_none_since_yesterday") or gen == "gc_restless")

def _gw_dia_urg4_enteric(fields, ctx):
    return equals(fields, "fever_present", "fp_yes") and value_of(fields, "duration_bucket") in ("week_plus", "month_plus", "chronic")

_NODES = {
    "DIA-00": QuestionNode(
        nodeId="DIA-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="DIA-G1a"),
            AnswerOption("ds_convulsion", "Fits or convulsions", next="DIA-G1a"),
            AnswerOption("ds_cannot_drink", "Unable to drink, or drinking poorly", next="DIA-G1a"),
            AnswerOption("ds_sunken_eyes", "Eyes look sunken", next="DIA-G1a"),
            AnswerOption("ds_no_urine", "Has not passed urine since yesterday", next="DIA-G1a"),
            AnswerOption("ds_blood_stool", "Blood in the stool", next="DIA-G1a"),
            AnswerOption("ds_abdomen_rigid", "Belly hard and tender to touch", next="DIA-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="DIA-G1a"),
        ],
        default_next="DIA-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "DIA-G1a": GatewayNode("DIA-G1a", "GW-DIA-EMG-1", _gw_dia_emg1, next="DIA-G1b",
                           routeTo="emergency_convulsions", severeConditions=["severe dehydration with electrolyte disturbance"]),
    "DIA-G1b": GatewayNode("DIA-G1b", "GW-DIA-EMG-2", _gw_dia_emg2, next="DIA-G1c",
                           routeTo="emergency_unconscious", severeConditions=["hypovolaemic shock", "severe dehydration", "sepsis"]),
    "DIA-G1c": GatewayNode("DIA-G1c", "GW-DIA-EMG-4", _gw_dia_emg4, next="DIA-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["enteric perforation", "peritonitis"]),
    "DIA-G1d": GatewayNode("DIA-G1d", "GW-DIA-EMG-5", _gw_dia_emg5, next="DIA-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "DIA-01": QuestionNode(
        nodeId="DIA-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="DIA-02"),
            AnswerOption("pr_same", "About the same", next="DIA-02"),
            AnswerOption("pr_worse", "Worse", next="DIA-02"),
        ],
        default_next="DIA-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "DIA-02": QuestionNode(
        nodeId="DIA-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedy", next="DIA-03"),
            AnswerOption("pt_pharmacy_medicine", "Pharmacy medicine", next="DIA-03"),
            AnswerOption("pt_ayush", "AYUSH / traditional medicine", next="DIA-03"),
            AnswerOption("pt_other_facility", "Treated at another facility", next="DIA-03"),
        ],
        default_next="DIA-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.02)
    ),
    "DIA-03": QuestionNode(
        nodeId="DIA-03", fieldId="stool_frequency_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("sf_lt_3", "Fewer than 3 times", next="DIA-04"),
            AnswerOption("sf_3_5", "3 to 5 times", next="DIA-04"),
            AnswerOption("sf_6_10", "6 to 10 times", next="DIA-04"),
            AnswerOption("sf_gt_10", "More than 10 times", next="DIA-G2"),
        ],
        default_next="DIA-04", unknown_option="sf_unknown", **_nu(0.03)
    ),
    "DIA-G2": GatewayNode("DIA-G2", "GW-DIA-URG-3", _gw_dia_urg3_high, next="DIA-04",
                           raisesTo="REFER_URGENT", severeConditions=["cholera", "severe secretory diarrhoea"]),
    "DIA-04": QuestionNode(
        nodeId="DIA-04", fieldId="stool_consistency", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("sc_loose_semisolid", "Loose but still formed", next="DIA-05"),
            AnswerOption("sc_watery", "Watery, no form at all", next="DIA-05"),
            AnswerOption("sc_rice_water", "Watery and pale, like rice washings", next="DIA-G2b"),
            AnswerOption("sc_greasy", "Greasy, floats, hard to flush", next="DIA-05"),
        ],
        default_next="DIA-05", unknown_option="sc_unknown", **_nu(0.03)
    ),
    "DIA-G2b": GatewayNode("DIA-G2b", "GW-DIA-URG-3", _gw_dia_urg3_high, next="DIA-05",
                            raisesTo="REFER_URGENT", severeConditions=["cholera"]),
    "DIA-05": QuestionNode(
        nodeId="DIA-05", fieldId="blood_in_stool", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bs_frank", "Yes — visible red blood", next="DIA-G2c"),
            AnswerOption("bs_streaks", "Yes — streaks on surface only", next="DIA-G2c"),
            AnswerOption("bs_black", "Stool is black and tarry", next="DIA-G2c"),
            AnswerOption("bs_no", "No blood seen", next="DIA-06"),
        ],
        default_next="DIA-06", unknown_option="bs_unknown", **_nu(0.03)
    ),
    "DIA-G2c": GatewayNode("DIA-G2c", "GW-DIA-URG-2", _gw_dia_urg2_dys, next="DIA-06",
                            raisesTo="REFER_URGENT", severeConditions=["dysentery (shigellosis)", "amoebic colitis"]),
    "DIA-06": QuestionNode(
        nodeId="DIA-06", fieldId="vomiting_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vm_yes_keeping_fluids", "Yes, but can keep fluids down", next="DIA-07"),
            AnswerOption("vm_yes_everything", "Yes — brings up everything", next="DIA-G2d"),
            AnswerOption("vm_no", "No", next="DIA-07"),
        ],
        default_next="DIA-07", unknown_option="vm_unknown", **_nu(0.03)
    ),
    "DIA-G2d": GatewayNode("DIA-G2d", "GW-DIA-URG-3", _gw_dia_urg3_high, next="DIA-07",
                            raisesTo="REFER_URGENT", severeConditions=["severe gastroenteritis"]),
    "DIA-07": QuestionNode(
        nodeId="DIA-07", fieldId="water_source", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ws_piped_treated", "Piped or treated supply", next="DIA-08"),
            AnswerOption("ws_handpump", "Hand pump or borewell", next="DIA-08"),
            AnswerOption("ws_open_well", "Open well", next="DIA-08"),
            AnswerOption("ws_surface", "Pond, river, canal or surface water", next="DIA-08"),
            AnswerOption("ws_tanker", "Tanker or bought water", next="DIA-08"),
        ],
        default_next="DIA-08", unknown_option="ws_unknown", **_nu(0.03)
    ),
    "DIA-08": QuestionNode(
        nodeId="DIA-08", fieldId="household_others_affected", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ho_yes", "Yes", next="DIA-G2e"),
            AnswerOption("ho_no", "No", next="DIA-S1"),
        ],
        default_next="DIA-S1", unknown_option="ho_unknown", **_nu(0.03)
    ),
    "DIA-G2e": GatewayNode("DIA-G2e", "GW-DIA-URG-3", _gw_dia_urg3_high, next="DIA-S1",
                            raisesTo="REFER_URGENT", severeConditions=["foodborne outbreak", "cholera"]),

    "DIA-S1": SubtreeRefNode("DIA-S1", make_dehydration_nodes(), entry="DEH-01", returnNext="DIA-G3a"),
    "DIA-G3a": GatewayNode("DIA-G3a", "GW-DIA-EMG-3", _gw_dia_emg3_imci, next="DIA-G3b",
                            raisesTo="REFER_EMERGENCY", severeConditions=["severe dehydration", "hypovolaemic shock"]),
    "DIA-G3b": GatewayNode("DIA-G3b", "GW-DIA-URG-1", _gw_dia_urg1_some, next="DIA-S2",
                            raisesTo="REFER_URGENT", severeConditions=["dehydration"]),

    "DIA-S2": SubtreeRefNode("DIA-S2", make_fever_qual_nodes(), entry="FQ-00", returnNext="DIA-G4"),
    "DIA-G4": GatewayNode("DIA-G4", "GW-DIA-URG-4", _gw_dia_urg4_enteric, next="DIA-END",
                           raisesTo="REFER_URGENT", severeConditions=["enteric fever", "chronic infection"]),
    "DIA-END": TerminalNode("DIA-END"),
}

BRANCH = BranchDef(categoryId=CATEGORY_ID, version=BRANCH_VERSION,
                    requiredDisposition=REQUIRED_DISPOSITION, nodes=_NODES, entry="DIA-00")

_SRC = "IND-PRESENT"
_SRC_TEXT = "AIIMS Bhopal / POSEIDON diarrhoeal disease presentation"

_entries = []
_entries += expand_entries("DIA-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_unconscious": 0.001, "ds_convulsion": 0.001, "ds_cannot_drink": 0.002,
             "ds_sunken_eyes": 0.01, "ds_no_urine": 0.005, "ds_blood_stool": 0.01,
             "ds_abdomen_rigid": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_unconscious": 0.005, "ds_convulsion": 0.005, "ds_cannot_drink": 0.03,
                 "ds_sunken_eyes": 0.15, "ds_no_urine": 0.05, "ds_blood_stool": 0.05,
                 "ds_abdomen_rigid": 0.01, "ds_cannot_feed": 0.03},
    "severe": {"ds_unconscious": 0.08, "ds_convulsion": 0.05, "ds_cannot_drink": 0.25,
               "ds_sunken_eyes": 0.45, "ds_no_urine": 0.25, "ds_blood_stool": 0.10,
               "ds_abdomen_rigid": 0.05, "ds_cannot_feed": 0.20},
}, overrides={
    ("dysentery_shigellosis", "severe"): {"ds_blood_stool": 0.65, "ds_cannot_drink": 0.15,
                                          "ds_sunken_eyes": 0.25, "ds_no_urine": 0.10,
                                          "ds_abdomen_rigid": 0.08, "ds_unconscious": 0.05,
                                          "ds_convulsion": 0.05, "ds_cannot_feed": 0.10},
    ("severe_secretory_diarrhoea_or_cholera", "severe"): {"ds_cannot_drink": 0.55, "ds_sunken_eyes": 0.70,
                                                         "ds_no_urine": 0.50, "ds_unconscious": 0.20,
                                                         "ds_convulsion": 0.08, "ds_blood_stool": 0.01,
                                                         "ds_abdomen_rigid": 0.02, "ds_cannot_feed": 0.40},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.40, "pr_same": 0.40, "pr_worse": 0.20},
    "moderate": {"pr_better": 0.20, "pr_same": 0.45, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.45, "pt_pharmacy_medicine": 0.35, "pt_ayush": 0.05, "pt_other_facility": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"sf_lt_3": 0.30, "sf_3_5": 0.55, "sf_6_10": 0.12, "sf_gt_10": 0.03},
    "moderate": {"sf_lt_3": 0.10, "sf_3_5": 0.45, "sf_6_10": 0.35, "sf_gt_10": 0.10},
    "severe": {"sf_lt_3": 0.02, "sf_3_5": 0.18, "sf_6_10": 0.45, "sf_gt_10": 0.35},
}, overrides={
    ("severe_secretory_diarrhoea_or_cholera", "severe"): {"sf_lt_3": 0.01, "sf_3_5": 0.04, "sf_6_10": 0.30, "sf_gt_10": 0.65}
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"sc_loose_semisolid": 0.65, "sc_watery": 0.30, "sc_rice_water": 0.01, "sc_greasy": 0.04},
    "moderate": {"sc_loose_semisolid": 0.35, "sc_watery": 0.58, "sc_rice_water": 0.02, "sc_greasy": 0.05},
    "severe": {"sc_loose_semisolid": 0.15, "sc_watery": 0.70, "sc_rice_water": 0.10, "sc_greasy": 0.05},
}, overrides={
    ("severe_secretory_diarrhoea_or_cholera", "moderate"): {"sc_loose_semisolid": 0.10, "sc_watery": 0.55, "sc_rice_water": 0.30, "sc_greasy": 0.05},
    ("severe_secretory_diarrhoea_or_cholera", "severe"): {"sc_loose_semisolid": 0.02, "sc_watery": 0.38, "sc_rice_water": 0.58, "sc_greasy": 0.02},
    ("amoebiasis_or_giardiasis", "mild"): {"sc_loose_semisolid": 0.40, "sc_watery": 0.35, "sc_rice_water": 0.01, "sc_greasy": 0.24},
    ("amoebiasis_or_giardiasis", "moderate"): {"sc_loose_semisolid": 0.40, "sc_watery": 0.35, "sc_rice_water": 0.01, "sc_greasy": 0.24},
    ("amoebiasis_or_giardiasis", "severe"): {"sc_loose_semisolid": 0.40, "sc_watery": 0.35, "sc_rice_water": 0.01, "sc_greasy": 0.24}
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bs_frank": 0.02, "bs_streaks": 0.03, "bs_black": 0.01, "bs_no": 0.94},
    "moderate": {"bs_frank": 0.05, "bs_streaks": 0.08, "bs_black": 0.02, "bs_no": 0.85},
    "severe": {"bs_frank": 0.10, "bs_streaks": 0.12, "bs_black": 0.03, "bs_no": 0.75},
}, overrides={
    ("dysentery_shigellosis", "mild"): {"bs_frank": 0.25, "bs_streaks": 0.45, "bs_black": 0.02, "bs_no": 0.28},
    ("dysentery_shigellosis", "moderate"): {"bs_frank": 0.45, "bs_streaks": 0.35, "bs_black": 0.03, "bs_no": 0.17},
    ("dysentery_shigellosis", "severe"): {"bs_frank": 0.65, "bs_streaks": 0.25, "bs_black": 0.04, "bs_no": 0.06},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vm_yes_keeping_fluids": 0.15, "vm_yes_everything": 0.02, "vm_no": 0.83},
    "moderate": {"vm_yes_keeping_fluids": 0.35, "vm_yes_everything": 0.10, "vm_no": 0.55},
    "severe": {"vm_yes_keeping_fluids": 0.40, "vm_yes_everything": 0.30, "vm_no": 0.30},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ws_piped_treated": 0.25, "ws_handpump": 0.40, "ws_open_well": 0.20,
        "ws_surface": 0.10, "ws_tanker": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DIA-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ho_yes": 0.20, "ho_no": 0.80} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

# Subtrees
_entries += expand_dehydration_entries(CONDITION_IDS, SEVERITIES,
                                       dehydration_conditions=("severe_secretory_diarrhoea_or_cholera", "acute_gastroenteritis"))
_entries += expand_fever_qual_entries(CONDITION_IDS, SEVERITIES,
                                      fever_conditions=("enteric_fever_diarrhoea", "dysentery_shigellosis"),
                                      bleeding_conditions=("dysentery_shigellosis",),
                                      source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
