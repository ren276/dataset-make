"""
drishti_v2/branches/abdominal_pain.py
The `abdominal_pain` branch (branch-authoring-batch-1-memo.md section 3).
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

CATEGORY_ID = "abdominal_pain"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_URGENT"

CONDITIONS = {
    "acute_gastritis_or_dyspepsia": ConditionSpec("acute_gastritis_or_dyspepsia", 0.40, "IND-PRESENT",
        "Dyspepsia / gastritis / non-specific abdominal pain"),
    "acute_appendicitis": ConditionSpec("acute_appendicitis", 0.16, "IND-PRESENT",
        "Acute appendicitis", severeConditions=("appendicitis", "acute abdomen")),
    "urinary_tract_infection": ConditionSpec("urinary_tract_infection", 0.16, "IND-PRESENT",
        "UTI presenting as lower abdominal pain", severeConditions=("urinary tract infection",)),
    "bowel_obstruction": ConditionSpec("bowel_obstruction", 0.08, "WORLD",
        "Bowel obstruction or perforation", severeConditions=("obstruction", "perforation", "acute abdomen")),
    "enteric_fever_abdominal": ConditionSpec("enteric_fever_abdominal", 0.08, "IND-PRESENT",
        "Enteric fever with abdominal pain", severeConditions=("enteric fever",)),
    "acute_pancreatitis": ConditionSpec("acute_pancreatitis", 0.06, "ASSUMED",
        "Acute pancreatitis", severeConditions=("pancreatitis", "acute abdomen")),
    "ectopic_pregnancy": ConditionSpec("ectopic_pregnancy", 0.06, "ASSUMED",
        "Ectopic pregnancy", severeConditions=("ectopic pregnancy", "acute abdomen")),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "acute_gastritis_or_dyspepsia": {"mild": 0.65, "moderate": 0.30, "severe": 0.05},
    "acute_appendicitis": {"mild": 0.15, "moderate": 0.50, "severe": 0.35},
    "urinary_tract_infection": {"mild": 0.45, "moderate": 0.45, "severe": 0.10},
    "bowel_obstruction": {"mild": 0.05, "moderate": 0.35, "severe": 0.60},
    "enteric_fever_abdominal": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "acute_pancreatitis": {"mild": 0.10, "moderate": 0.40, "severe": 0.50},
    "ectopic_pregnancy": {"mild": 0.10, "moderate": 0.35, "severe": 0.55},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sbp = specs["bp_systolic"]
    base_dbp = specs["bp_diastolic"]
    base_temp = specs["temperature"]

    if condition_id in ("bowel_obstruction", "acute_pancreatitis", "ectopic_pregnancy"):
        if severity_band == "severe":
            specs["pulse"] = VitalSpec(125.0, 10.0, 35, 220)
            specs["bp_systolic"] = VitalSpec(85.0, 8.0, 50, 180)
            specs["bp_diastolic"] = VitalSpec(55.0, 6.0, 30, 120)
        else:
            specs["pulse"] = VitalSpec(base_pulse.mean + 15, base_pulse.sd, 35, 220)
    elif condition_id in ("acute_appendicitis", "enteric_fever_abdominal"):
        specs["temperature"] = VitalSpec(base_temp.mean + (1.2 if severity_band != "severe" else 2.0), 0.4, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + (10 if severity_band != "severe" else 20), base_pulse.sd, 35, 220)
    elif severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 15, 10.0, 35, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_abd_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_abd_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_blood_vomit_stool")

def _gw_abd_emg3_acute(fields, ctx):
    return (any_of(fields, "danger_signs", ["ds_abdomen_rigid", "ds_pain_severe_sudden", "ds_no_stool_no_wind", "ds_vomiting_everything"])
            or equals(fields, "vomiting_present", "vm_yes_everything")
            or equals(fields, "bowels_open", "bo_none_and_no_wind"))

def _gw_abd_emg4_ectopic(fields, ctx):
    if ctx.get("sex") != "F" or not (15 <= ctx.get("age_years", 0) <= 49):
        return False
    preg = equals(fields, "pregnancy_status", "pg_yes") or equals(fields, "lmp_known", "lmp_late_or_missed")
    pain = any_of(fields, "pain_site", ["ps_lower_right", "ps_lower_left", "ps_lower_middle"]) or contains(fields, "danger_signs", "ds_faint")
    return preg and pain

def _gw_abd_emg5_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_abd_urg1_app(fields, ctx):
    return equals(fields, "pain_migration", "pm_navel_to_lower_right") or (
        equals(fields, "pain_site", "ps_lower_right") and equals(fields, "fever_present", "fp_yes")
    )

def _gw_abd_urg2_panc(fields, ctx):
    return any_of(fields, "pain_radiation", ["pr_to_back", "pr_to_shoulder"]) and (
        value_of(fields, "severity_band") == "severe" or equals(fields, "severity_score", 8) or equals(fields, "severity_score", 9) or equals(fields, "severity_score", 10)
    )

def _gw_abd_urg3_enteric(fields, ctx):
    return equals(fields, "fever_present", "fp_yes") and value_of(fields, "duration_bucket") in ("week_plus", "month_plus", "chronic")

def _gw_abd_urg4_uti(fields, ctx):
    return equals(fields, "burning_on_urination", "bu_yes") and equals(fields, "fever_present", "fp_yes")

_NODES = {
    "ABD-00": QuestionNode(
        nodeId="ABD-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_abdomen_rigid", "Belly hard and tender to touch", next="ABD-G1a"),
            AnswerOption("ds_pain_severe_sudden", "The pain came on suddenly and is very severe", next="ABD-G1a"),
            AnswerOption("ds_no_stool_no_wind", "No stool and no wind passed since yesterday", next="ABD-G1a"),
            AnswerOption("ds_vomiting_everything", "Vomiting everything, cannot keep fluids down", next="ABD-G1a"),
            AnswerOption("ds_faint", "Fainted, or feels faint on standing", next="ABD-G1a"),
            AnswerOption("ds_blood_vomit_stool", "Blood in the vomit, or black or bloody stool", next="ABD-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="ABD-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="ABD-G1a"),
        ],
        default_next="ABD-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "ABD-G1a": GatewayNode("ABD-G1a", "GW-ABD-EMG-1", _gw_abd_emg1, next="ABD-G1b",
                           routeTo="emergency_unconscious", severeConditions=["haemorrhagic shock", "septic shock", "ruptured ectopic"]),
    "ABD-G1b": GatewayNode("ABD-G1b", "GW-ABD-EMG-2", _gw_abd_emg2, next="ABD-G1c",
                           routeTo="emergency_heavy_bleeding", severeConditions=["upper GI bleed", "enteric perforation with bleeding", "variceal bleed"]),
    "ABD-G1c": GatewayNode("ABD-G1c", "GW-ABD-EMG-3", _gw_abd_emg3_acute, next="ABD-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["acute abdomen", "perforation", "obstruction", "pancreatitis"]),
    "ABD-G1d": GatewayNode("ABD-G1d", "GW-ABD-EMG-5", _gw_abd_emg5_infant, next="ABD-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "ABD-01": QuestionNode(
        nodeId="ABD-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="ABD-02"),
            AnswerOption("pr_same", "About the same", next="ABD-02"),
            AnswerOption("pr_worse", "Worse", next="ABD-02"),
        ],
        default_next="ABD-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "ABD-02": QuestionNode(
        nodeId="ABD-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="ABD-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="ABD-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="ABD-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="ABD-03"),
            AnswerOption("pt_other", "Other treatment", next="ABD-03"),
        ],
        default_next="ABD-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "ABD-03": QuestionNode(
        nodeId="ABD-03", fieldId="pain_site", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ps_upper_right", "Upper right, under the ribs", next="ABD-04"),
            AnswerOption("ps_upper_middle", "Upper middle, below the breastbone", next="ABD-04"),
            AnswerOption("ps_upper_left", "Upper left, under the ribs", next="ABD-04"),
            AnswerOption("ps_around_navel", "Around the navel", next="ABD-04"),
            AnswerOption("ps_lower_right", "Lower right", next="ABD-04"),
            AnswerOption("ps_lower_middle", "Lower middle, above the pubic bone", next="ABD-04"),
            AnswerOption("ps_lower_left", "Lower left", next="ABD-04"),
            AnswerOption("ps_all_over", "All over the belly", next="ABD-04"),
        ],
        default_next="ABD-04", unknown_option="ps_unknown", **_nu(0.03)
    ),
    "ABD-04": QuestionNode(
        nodeId="ABD-04", fieldId="pain_radiation", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_to_back", "Straight through to the back", next="ABD-05"),
            AnswerOption("pr_to_shoulder", "Up to the right shoulder or shoulder tip", next="ABD-05"),
            AnswerOption("pr_to_groin", "Down to the groin or genitals", next="ABD-05"),
            AnswerOption("pr_to_chest", "Up into the chest", next="ABD-05"),
            AnswerOption("pr_none", "Stays in one place", next="ABD-05"),
        ],
        default_next="ABD-05", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "ABD-05": QuestionNode(
        nodeId="ABD-05", fieldId="pain_migration", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pm_navel_to_lower_right", "Started near the navel and moved to the lower right", next="ABD-06"),
            AnswerOption("pm_moved_other", "Started elsewhere and moved", next="ABD-06"),
            AnswerOption("pm_no_move", "Has been in the same place throughout", next="ABD-06"),
        ],
        default_next="ABD-06", unknown_option="pm_unknown", **_nu(0.03)
    ),
    "ABD-06": QuestionNode(
        nodeId="ABD-06", fieldId="vomiting_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vm_yes_keeping_fluids", "Yes — keeping some fluids down", next="ABD-07"),
            AnswerOption("vm_yes_everything", "Yes — vomiting everything", next="ABD-07"),
            AnswerOption("vm_no", "No vomiting", next="ABD-07"),
        ],
        default_next="ABD-07", unknown_option="vm_unknown", **_nu(0.03)
    ),
    "ABD-07": QuestionNode(
        nodeId="ABD-07", fieldId="bowels_open", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bo_normal_today", "Passed normal stool today", next="ABD-08"),
            AnswerOption("bo_loose", "Loose motions", next="ABD-08"),
            AnswerOption("bo_constipated", "Constipated for two days or more", next="ABD-08"),
            AnswerOption("bo_none_and_no_wind", "No stool and no wind passed", next="ABD-08"),
        ],
        default_next="ABD-08", unknown_option="bo_unknown", **_nu(0.03)
    ),
    "ABD-08": QuestionNode(
        nodeId="ABD-08", fieldId="burning_on_urination", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bu_yes", "Yes", next="ABD-09"),
            AnswerOption("bu_no", "No", next="ABD-09"),
        ],
        default_next="ABD-09", unknown_option="bu_unknown", **_nu(0.03)
    ),
    "ABD-09": QuestionNode(
        nodeId="ABD-09", fieldId="lmp_known", answerType="SINGLE_CHOICE",
        guard=lambda fields: fields.get("_sex") is not None and fields["_sex"].value == "F" and fields.get("_age_years") is not None and 15 <= fields["_age_years"].value <= 49,
        options=[
            AnswerOption("lmp_within_4wk", "Within the last 4 weeks", next="ABD-S1"),
            AnswerOption("lmp_late_or_missed", "Late, or missed altogether", next="ABD-S1"),
            AnswerOption("lmp_gt_3_months", "More than 3 months ago", next="ABD-S1"),
            AnswerOption("lmp_not_applicable", "Does not apply", next="ABD-S1"),
        ],
        default_next="ABD-S1", unknown_option="lmp_unknown", **_nu(0.03)
    ),

    "ABD-S1": SubtreeRefNode("ABD-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="ABD-G2"),

    "ABD-G2": GatewayNode("ABD-G2", "GW-ABD-EMG-3", _gw_abd_emg3_acute, next="ABD-G3",
                          raisesTo="REFER_EMERGENCY", severeConditions=["acute abdomen", "perforation", "obstruction", "pancreatitis"]),
    "ABD-G3": GatewayNode("ABD-G3", "GW-ABD-EMG-4", _gw_abd_emg4_ectopic, next="ABD-G4",
                          raisesTo="REFER_EMERGENCY", severeConditions=["ectopic pregnancy", "ruptured ovarian cyst", "tubo-ovarian abscess"]),
    "ABD-G4": GatewayNode("ABD-G4", "GW-ABD-URG-1", _gw_abd_urg1_app, next="ABD-G5",
                          raisesTo="REFER_URGENT", severeConditions=["appendicitis", "mesenteric adenitis", "ileocaecal TB"]),
    "ABD-G5": GatewayNode("ABD-G5", "GW-ABD-URG-2", _gw_abd_urg2_panc, next="ABD-G6",
                          raisesTo="REFER_URGENT", severeConditions=["pancreatitis", "biliary colic", "cholecystitis"]),
    "ABD-G6": GatewayNode("ABD-G6", "GW-ABD-URG-3", _gw_abd_urg3_enteric, next="ABD-G7",
                          raisesTo="REFER_URGENT", severeConditions=["enteric fever", "abdominal tuberculosis"]),
    "ABD-G7": GatewayNode("ABD-G7", "GW-ABD-URG-4", _gw_abd_urg4_uti, next="ABD-END",
                          raisesTo="REFER_URGENT", severeConditions=["pyelonephritis", "urinary obstruction", "UTI in pregnancy"]),

    "ABD-END": TerminalNode("ABD-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="ABD-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Abdominal pain clinical distribution"

_entries = []

_entries += expand_entries("ABD-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_abdomen_rigid": 0.005, "ds_pain_severe_sudden": 0.01, "ds_no_stool_no_wind": 0.01,
             "ds_vomiting_everything": 0.01, "ds_faint": 0.01, "ds_blood_vomit_stool": 0.005,
             "ds_unconscious": 0.002, "ds_cannot_feed": 0.01},
    "moderate": {"ds_abdomen_rigid": 0.03, "ds_pain_severe_sudden": 0.08, "ds_no_stool_no_wind": 0.05,
                "ds_vomiting_everything": 0.06, "ds_faint": 0.03, "ds_blood_vomit_stool": 0.02,
                "ds_unconscious": 0.01, "ds_cannot_feed": 0.03},
    "severe": {"ds_abdomen_rigid": 0.25, "ds_pain_severe_sudden": 0.35, "ds_no_stool_no_wind": 0.20,
               "ds_vomiting_everything": 0.25, "ds_faint": 0.15, "ds_blood_vomit_stool": 0.10,
               "ds_unconscious": 0.08, "ds_cannot_feed": 0.12},
}, overrides={
    ("acute_appendicitis", "severe"): {"ds_abdomen_rigid": 0.50, "ds_pain_severe_sudden": 0.40, "ds_no_stool_no_wind": 0.10,
                                      "ds_vomiting_everything": 0.25, "ds_faint": 0.10, "ds_blood_vomit_stool": 0.01,
                                      "ds_unconscious": 0.05, "ds_cannot_feed": 0.10},
    ("bowel_obstruction", "severe"): {"ds_abdomen_rigid": 0.40, "ds_pain_severe_sudden": 0.30, "ds_no_stool_no_wind": 0.65,
                                      "ds_vomiting_everything": 0.55, "ds_faint": 0.15, "ds_blood_vomit_stool": 0.05,
                                      "ds_unconscious": 0.08, "ds_cannot_feed": 0.15},
    ("ectopic_pregnancy", "severe"): {"ds_abdomen_rigid": 0.45, "ds_pain_severe_sudden": 0.60, "ds_no_stool_no_wind": 0.05,
                                      "ds_vomiting_everything": 0.20, "ds_faint": 0.45, "ds_blood_vomit_stool": 0.02,
                                      "ds_unconscious": 0.15, "ds_cannot_feed": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.45, "pr_worse": 0.40},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.35, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.15, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ps_upper_right": 0.12, "ps_upper_middle": 0.30, "ps_upper_left": 0.08,
             "ps_around_navel": 0.15, "ps_lower_right": 0.10, "ps_lower_middle": 0.12,
             "ps_lower_left": 0.08, "ps_all_over": 0.05},
    "moderate": {"ps_upper_right": 0.12, "ps_upper_middle": 0.25, "ps_upper_left": 0.08,
                "ps_around_navel": 0.15, "ps_lower_right": 0.15, "ps_lower_middle": 0.12,
                "ps_lower_left": 0.08, "ps_all_over": 0.05},
    "severe": {"ps_upper_right": 0.10, "ps_upper_middle": 0.20, "ps_upper_left": 0.08,
               "ps_around_navel": 0.12, "ps_lower_right": 0.20, "ps_lower_middle": 0.10,
               "ps_lower_left": 0.08, "ps_all_over": 0.12},
}, overrides={
    ("acute_appendicitis", "mild"): {"ps_upper_right": 0.02, "ps_upper_middle": 0.10, "ps_upper_left": 0.01,
                                    "ps_around_navel": 0.35, "ps_lower_right": 0.45, "ps_lower_middle": 0.05,
                                    "ps_lower_left": 0.01, "ps_all_over": 0.01},
    ("acute_appendicitis", "moderate"): {"ps_upper_right": 0.01, "ps_upper_middle": 0.05, "ps_upper_left": 0.01,
                                        "ps_around_navel": 0.20, "ps_lower_right": 0.70, "ps_lower_middle": 0.02,
                                        "ps_lower_left": 0.01, "ps_all_over": 0.00},
    ("acute_appendicitis", "severe"): {"ps_upper_right": 0.01, "ps_upper_middle": 0.02, "ps_upper_left": 0.01,
                                      "ps_around_navel": 0.10, "ps_lower_right": 0.75, "ps_lower_middle": 0.05,
                                      "ps_lower_left": 0.01, "ps_all_over": 0.05},
    ("acute_pancreatitis", "severe"): {"ps_upper_right": 0.10, "ps_upper_middle": 0.65, "ps_upper_left": 0.15,
                                      "ps_around_navel": 0.05, "ps_lower_right": 0.01, "ps_lower_middle": 0.01,
                                      "ps_lower_left": 0.01, "ps_all_over": 0.02},
    ("urinary_tract_infection", "moderate"): {"ps_upper_right": 0.02, "ps_upper_middle": 0.05, "ps_upper_left": 0.02,
                                            "ps_around_navel": 0.05, "ps_lower_right": 0.10, "ps_lower_middle": 0.65,
                                            "ps_lower_left": 0.10, "ps_all_over": 0.01},
    ("ectopic_pregnancy", "severe"): {"ps_upper_right": 0.01, "ps_upper_middle": 0.02, "ps_upper_left": 0.01,
                                     "ps_around_navel": 0.05, "ps_lower_right": 0.45, "ps_lower_middle": 0.15,
                                     "ps_lower_left": 0.30, "ps_all_over": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_to_back": 0.05, "pr_to_shoulder": 0.05, "pr_to_groin": 0.05, "pr_to_chest": 0.10, "pr_none": 0.75},
    "moderate": {"pr_to_back": 0.12, "pr_to_shoulder": 0.08, "pr_to_groin": 0.10, "pr_to_chest": 0.10, "pr_none": 0.60},
    "severe": {"pr_to_back": 0.20, "pr_to_shoulder": 0.10, "pr_to_groin": 0.12, "pr_to_chest": 0.08, "pr_none": 0.50},
}, overrides={
    ("acute_pancreatitis", "moderate"): {"pr_to_back": 0.60, "pr_to_shoulder": 0.05, "pr_to_groin": 0.02, "pr_to_chest": 0.03, "pr_none": 0.30},
    ("acute_pancreatitis", "severe"): {"pr_to_back": 0.75, "pr_to_shoulder": 0.05, "pr_to_groin": 0.02, "pr_to_chest": 0.03, "pr_none": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-05", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pm_navel_to_lower_right": 0.05, "pm_moved_other": 0.10, "pm_no_move": 0.85}
    for s in SEVERITIES
}, overrides={
    ("acute_appendicitis", "mild"): {"pm_navel_to_lower_right": 0.45, "pm_moved_other": 0.10, "pm_no_move": 0.45},
    ("acute_appendicitis", "moderate"): {"pm_navel_to_lower_right": 0.65, "pm_moved_other": 0.10, "pm_no_move": 0.25},
    ("acute_appendicitis", "severe"): {"pm_navel_to_lower_right": 0.70, "pm_moved_other": 0.10, "pm_no_move": 0.20},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vm_yes_keeping_fluids": 0.15, "vm_yes_everything": 0.02, "vm_no": 0.83},
    "moderate": {"vm_yes_keeping_fluids": 0.35, "vm_yes_everything": 0.08, "vm_no": 0.57},
    "severe": {"vm_yes_keeping_fluids": 0.40, "vm_yes_everything": 0.30, "vm_no": 0.30},
}, overrides={
    ("bowel_obstruction", "severe"): {"vm_yes_keeping_fluids": 0.30, "vm_yes_everything": 0.60, "vm_no": 0.10},
    ("acute_pancreatitis", "severe"): {"vm_yes_keeping_fluids": 0.40, "vm_yes_everything": 0.50, "vm_no": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bo_normal_today": 0.65, "bo_loose": 0.15, "bo_constipated": 0.18, "bo_none_and_no_wind": 0.02},
    "moderate": {"bo_normal_today": 0.45, "bo_loose": 0.25, "bo_constipated": 0.22, "bo_none_and_no_wind": 0.08},
    "severe": {"bo_normal_today": 0.25, "bo_loose": 0.25, "bo_constipated": 0.25, "bo_none_and_no_wind": 0.25},
}, overrides={
    ("bowel_obstruction", "moderate"): {"bo_normal_today": 0.10, "bo_loose": 0.05, "bo_constipated": 0.40, "bo_none_and_no_wind": 0.45},
    ("bowel_obstruction", "severe"): {"bo_normal_today": 0.02, "bo_loose": 0.03, "bo_constipated": 0.20, "bo_none_and_no_wind": 0.75},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bu_yes": 0.10, "bu_no": 0.90} for s in SEVERITIES
}, overrides={
    ("urinary_tract_infection", "mild"): {"bu_yes": 0.75, "bu_no": 0.25},
    ("urinary_tract_infection", "moderate"): {"bu_yes": 0.88, "bu_no": 0.12},
    ("urinary_tract_infection", "severe"): {"bu_yes": 0.92, "bu_no": 0.08},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ABD-09", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"lmp_within_4wk": 0.70, "lmp_late_or_missed": 0.10, "lmp_gt_3_months": 0.10, "lmp_not_applicable": 0.10}
    for s in SEVERITIES
}, overrides={
    ("ectopic_pregnancy", s): {"lmp_within_4wk": 0.15, "lmp_late_or_missed": 0.80, "lmp_gt_3_months": 0.03, "lmp_not_applicable": 0.02}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("acute_appendicitis", "enteric_fever_abdominal", "urinary_tract_infection"),
    bleeding_conditions=("enteric_fever_abdominal",),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
