"""
drishti_v2/branches/chest_pain.py
The `chest_pain` branch (branch-authoring-batch-1-memo.md section 5).
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

CATEGORY_ID = "chest_pain"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_URGENT"

CONDITIONS = {
    "musculoskeletal_chest_pain": ConditionSpec("musculoskeletal_chest_pain", 0.40, "IND-PRESENT",
        "Musculoskeletal / chest wall pain"),
    "acute_coronary_syndrome": ConditionSpec("acute_coronary_syndrome", 0.22, "IND-PRESENT",
        "Acute coronary syndrome (MI / unstable angina)", severeConditions=("myocardial infarction", "unstable angina")),
    "stable_angina": ConditionSpec("stable_angina", 0.15, "IND-PRESENT",
        "Stable angina pectoris", severeConditions=("stable angina",)),
    "gastro_oesophageal_reflux": ConditionSpec("gastro_oesophageal_reflux", 0.12, "IND-PRESENT",
        "GERD / oesophageal spasm"),
    "pleurisy_or_pneumonia": ConditionSpec("pleurisy_or_pneumonia", 0.05, "IND-PRESENT",
        "Pleurisy or pneumonia with chest pain", severeConditions=("pneumonia",)),
    "pulmonary_embolism_cp": ConditionSpec("pulmonary_embolism_cp", 0.03, "WORLD",
        "Pulmonary embolism", severeConditions=("pulmonary embolism",)),
    "pericarditis": ConditionSpec("pericarditis", 0.02, "WORLD",
        "Acute pericarditis / myocarditis", severeConditions=("pericarditis",)),
    "aortic_dissection": ConditionSpec("aortic_dissection", 0.01, "ASSUMED",
        "Aortic dissection", severeConditions=("aortic dissection",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "musculoskeletal_chest_pain": {"mild": 0.65, "moderate": 0.30, "severe": 0.05},
    "acute_coronary_syndrome": {"mild": 0.10, "moderate": 0.45, "severe": 0.45},
    "stable_angina": {"mild": 0.35, "moderate": 0.50, "severe": 0.15},
    "gastro_oesophageal_reflux": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
    "pleurisy_or_pneumonia": {"mild": 0.25, "moderate": 0.50, "severe": 0.25},
    "pulmonary_embolism_cp": {"mild": 0.05, "moderate": 0.35, "severe": 0.60},
    "pericarditis": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "aortic_dissection": {"mild": 0.02, "moderate": 0.18, "severe": 0.80},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sbp = specs["bp_systolic"]
    base_dbp = specs["bp_diastolic"]
    base_temp = specs["temperature"]

    if condition_id in ("acute_coronary_syndrome", "aortic_dissection", "pulmonary_embolism_cp"):
        if severity_band == "severe":
            specs["pulse"] = VitalSpec(118.0, 15.0, 35, 220)
            specs["bp_systolic"] = VitalSpec(90.0, 15.0, 50, 220)
            specs["bp_diastolic"] = VitalSpec(58.0, 10.0, 30, 140)
        else:
            specs["pulse"] = VitalSpec(base_pulse.mean + 15, base_pulse.sd, 35, 220)
    elif condition_id in ("pleurisy_or_pneumonia", "pericarditis"):
        specs["temperature"] = VitalSpec(base_temp.mean + (1.0 if severity_band != "severe" else 1.8), 0.4, 34, 41)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_cpn_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_cpn_emg2_stage_a(fields, ctx):
    return any_of(fields, "danger_signs", [
        "ds_sweating_with_pain", "ds_radiating", "ds_pain_at_rest", "ds_collapse", "ds_vomiting_with_pain"
    ])

def _gw_cpn_emg3(fields, ctx):
    return contains(fields, "danger_signs", "ds_tearing_to_back")

def _gw_cpn_emg4_stage_a(fields, ctx):
    return contains(fields, "danger_signs", "ds_breathless_at_rest")

def _gw_cpn_emg2_acs(fields, ctx):
    return _gw_cpn_emg2_stage_a(fields, ctx) or (
        equals(fields, "duration_minutes_band", "dm_gt_20_ongoing") and equals(fields, "relieved_by_rest", "rr_no")
    ) or (
        equals(fields, "exertional_relation", "er_at_rest") and equals(fields, "relieved_by_rest", "rr_no")
    )

def _gw_cpn_emg4_pe(fields, ctx):
    return _gw_cpn_emg4_stage_a(fields, ctx) or equals(fields, "breathlessness_present", "bp_at_rest") or (
        equals(fields, "pain_character_chest", "pc_sharp_on_breathing") and equals(fields, "ankle_swelling", "as_one_leg")
    )

def _gw_cpn_urg1_stable(fields, ctx):
    return equals(fields, "exertional_relation", "er_on_exertion") and equals(fields, "relieved_by_rest", "rr_within_minutes")

def _gw_cpn_urg2_pericarditis(fields, ctx):
    return any_of(fields, "postural_relation", ["po_worse_lying_flat", "po_better_sitting_forward"]) and equals(fields, "fever_present", "fp_yes")

def _gw_cpn_urg3_hf(fields, ctx):
    return equals(fields, "ankle_swelling", "as_both_legs")

_NODES = {
    "CPN-00": QuestionNode(
        nodeId="CPN-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_sweating_with_pain", "Cold sweat with the pain", next="CPN-G1a"),
            AnswerOption("ds_radiating", "Pain spreading to the arm, neck or jaw", next="CPN-G1a"),
            AnswerOption("ds_pain_at_rest", "The pain started at rest and is still there now", next="CPN-G1a"),
            AnswerOption("ds_breathless_at_rest", "Breathless at rest along with the pain", next="CPN-G1a"),
            AnswerOption("ds_collapse", "Collapsed or fainted", next="CPN-G1a"),
            AnswerOption("ds_tearing_to_back", "Sudden tearing pain going through to the back", next="CPN-G1a"),
            AnswerOption("ds_vomiting_with_pain", "Vomiting with the pain", next="CPN-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="CPN-G1a"),
        ],
        default_next="CPN-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "CPN-G1a": GatewayNode("CPN-G1a", "GW-CPN-EMG-1", _gw_cpn_emg1, next="CPN-G1b",
                           routeTo="emergency_unconscious", severeConditions=["cardiac arrest", "cardiogenic shock", "massive PE"]),
    "CPN-G1b": GatewayNode("CPN-G1b", "GW-CPN-EMG-2", _gw_cpn_emg2_stage_a, next="CPN-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["myocardial infarction", "unstable angina"]),
    "CPN-G1c": GatewayNode("CPN-G1c", "GW-CPN-EMG-3", _gw_cpn_emg3, next="CPN-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["aortic dissection"]),
    "CPN-G1d": GatewayNode("CPN-G1d", "GW-CPN-EMG-4", _gw_cpn_emg4_stage_a, next="CPN-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["pulmonary embolism", "pneumothorax"]),

    "CPN-01": QuestionNode(
        nodeId="CPN-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="CPN-02"),
            AnswerOption("pr_same", "About the same", next="CPN-02"),
            AnswerOption("pr_worse", "Worse", next="CPN-02"),
        ],
        default_next="CPN-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "CPN-02": QuestionNode(
        nodeId="CPN-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="CPN-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="CPN-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="CPN-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="CPN-03"),
            AnswerOption("pt_other", "Other treatment", next="CPN-03"),
        ],
        default_next="CPN-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "CPN-03": QuestionNode(
        nodeId="CPN-03", fieldId="pain_character_chest", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pc_heavy_pressing", "Heavy, pressing or squeezing", next="CPN-04"),
            AnswerOption("pc_tight_band", "Tight, like a band around the chest", next="CPN-04"),
            AnswerOption("pc_sharp_on_breathing", "Sharp, and worse on breathing in", next="CPN-04"),
            AnswerOption("pc_burning", "Burning", next="CPN-04"),
            AnswerOption("pc_tender_to_press", "Sore, and tender when pressed", next="CPN-04"),
        ],
        default_next="CPN-04", unknown_option="pc_unknown", **_nu(0.03)
    ),
    "CPN-04": QuestionNode(
        nodeId="CPN-04", fieldId="duration_minutes_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("dm_lt_2min", "Less than 2 minutes", next="CPN-05"),
            AnswerOption("dm_2_20min", "2 to 20 minutes, then settles", next="CPN-05"),
            AnswerOption("dm_gt_20_ongoing", "More than 20 minutes, and it is still there", next="CPN-05"),
            AnswerOption("dm_hours_days", "Hours or days, more or less constant", next="CPN-05"),
        ],
        default_next="CPN-05", unknown_option="dm_unknown", **_nu(0.03)
    ),
    "CPN-05": QuestionNode(
        nodeId="CPN-05", fieldId="exertional_relation", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("er_on_exertion", "Walking, climbing or working brings it on", next="CPN-06"),
            AnswerOption("er_at_rest", "It comes on at rest, with nothing to bring it on", next="CPN-06"),
            AnswerOption("er_no_relation", "No pattern to it", next="CPN-06"),
        ],
        default_next="CPN-06", unknown_option="er_unknown", **_nu(0.03)
    ),
    "CPN-06": QuestionNode(
        nodeId="CPN-06", fieldId="relieved_by_rest", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rr_within_minutes", "Yes — settles within a few minutes of stopping", next="CPN-07"),
            AnswerOption("rr_partly", "Settles a little, but does not go", next="CPN-07"),
            AnswerOption("rr_no", "No — resting makes no difference", next="CPN-07"),
        ],
        default_next="CPN-07", unknown_option="rr_unknown", **_nu(0.03)
    ),
    "CPN-07": QuestionNode(
        nodeId="CPN-07", fieldId="postural_relation", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("po_worse_lying_flat", "Worse lying flat", next="CPN-08"),
            AnswerOption("po_better_sitting_forward", "Better sitting up and leaning forward", next="CPN-08"),
            AnswerOption("po_worse_on_breathing", "Worse on taking a deep breath", next="CPN-08"),
            AnswerOption("po_worse_on_movement", "Worse on moving or turning", next="CPN-08"),
            AnswerOption("po_no_change", "No change with position or breathing", next="CPN-08"),
        ],
        default_next="CPN-08", unknown_option="po_unknown", **_nu(0.03)
    ),
    "CPN-08": QuestionNode(
        nodeId="CPN-08", fieldId="breathlessness_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bp_at_rest", "Even at rest", next="CPN-09"),
            AnswerOption("bp_on_exertion", "On walking or on exertion", next="CPN-09"),
            AnswerOption("bp_no", "Not at the moment", next="CPN-09"),
        ],
        default_next="CPN-09", unknown_option="bp_unknown", **_nu(0.03)
    ),
    "CPN-09": QuestionNode(
        nodeId="CPN-09", fieldId="ankle_swelling", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("as_both_legs", "Yes — both legs", next="CPN-S1"),
            AnswerOption("as_one_leg", "Yes — one leg only", next="CPN-S1"),
            AnswerOption("as_no", "No", next="CPN-S1"),
        ],
        default_next="CPN-S1", unknown_option="as_unknown", **_nu(0.03)
    ),

    "CPN-S1": SubtreeRefNode("CPN-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="CPN-G2"),

    "CPN-G2": GatewayNode("CPN-G2", "GW-CPN-EMG-2", _gw_cpn_emg2_acs, next="CPN-G3",
                          raisesTo="REFER_EMERGENCY", severeConditions=["myocardial infarction", "unstable angina"]),
    "CPN-G3": GatewayNode("CPN-G3", "GW-CPN-EMG-4", _gw_cpn_emg4_pe, next="CPN-G4",
                          raisesTo="REFER_EMERGENCY", severeConditions=["pulmonary embolism", "pneumothorax"]),
    "CPN-G4": GatewayNode("CPN-G4", "GW-CPN-URG-1", _gw_cpn_urg1_stable, next="CPN-G5",
                          raisesTo="REFER_URGENT", severeConditions=["stable angina", "ischaemic heart disease"]),
    "CPN-G5": GatewayNode("CPN-G5", "GW-CPN-URG-2", _gw_cpn_urg2_pericarditis, next="CPN-G6",
                          raisesTo="REFER_URGENT", severeConditions=["pericarditis", "myocarditis"]),
    "CPN-G6": GatewayNode("CPN-G6", "GW-CPN-URG-3", _gw_cpn_urg3_hf, next="CPN-END",
                          raisesTo="REFER_URGENT", severeConditions=["heart failure"]),

    "CPN-END": TerminalNode("CPN-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="CPN-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Chest pain clinical distribution"

_entries = []

_entries += expand_entries("CPN-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_sweating_with_pain": 0.01, "ds_radiating": 0.02, "ds_pain_at_rest": 0.05,
             "ds_breathless_at_rest": 0.01, "ds_collapse": 0.001, "ds_tearing_to_back": 0.001,
             "ds_vomiting_with_pain": 0.005, "ds_unconscious": 0.001},
    "moderate": {"ds_sweating_with_pain": 0.08, "ds_radiating": 0.12, "ds_pain_at_rest": 0.15,
                "ds_breathless_at_rest": 0.08, "ds_collapse": 0.01, "ds_tearing_to_back": 0.005,
                "ds_vomiting_with_pain": 0.03, "ds_unconscious": 0.005},
    "severe": {"ds_sweating_with_pain": 0.35, "ds_radiating": 0.40, "ds_pain_at_rest": 0.45,
               "ds_breathless_at_rest": 0.30, "ds_collapse": 0.08, "ds_tearing_to_back": 0.05,
               "ds_vomiting_with_pain": 0.15, "ds_unconscious": 0.05},
}, overrides={
    ("acute_coronary_syndrome", "moderate"): {"ds_sweating_with_pain": 0.45, "ds_radiating": 0.55, "ds_pain_at_rest": 0.60,
                                             "ds_breathless_at_rest": 0.25, "ds_collapse": 0.05, "ds_tearing_to_back": 0.01,
                                             "ds_vomiting_with_pain": 0.20, "ds_unconscious": 0.02},
    ("acute_coronary_syndrome", "severe"): {"ds_sweating_with_pain": 0.75, "ds_radiating": 0.80, "ds_pain_at_rest": 0.85,
                                           "ds_breathless_at_rest": 0.45, "ds_collapse": 0.18, "ds_tearing_to_back": 0.02,
                                           "ds_vomiting_with_pain": 0.35, "ds_unconscious": 0.08},
    ("aortic_dissection", "severe"): {"ds_sweating_with_pain": 0.60, "ds_radiating": 0.30, "ds_pain_at_rest": 0.85,
                                      "ds_breathless_at_rest": 0.40, "ds_collapse": 0.25, "ds_tearing_to_back": 0.85,
                                      "ds_vomiting_with_pain": 0.20, "ds_unconscious": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.45, "pr_worse": 0.40},
    "severe": {"pr_better": 0.05, "pr_same": 0.20, "pr_worse": 0.75},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.35, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.05,
        "pt_prescribed_prior": 0.25, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pc_heavy_pressing": 0.15, "pc_tight_band": 0.15, "pc_sharp_on_breathing": 0.20, "pc_burning": 0.25, "pc_tender_to_press": 0.25},
    "moderate": {"pc_heavy_pressing": 0.30, "pc_tight_band": 0.25, "pc_sharp_on_breathing": 0.15, "pc_burning": 0.20, "pc_tender_to_press": 0.10},
    "severe": {"pc_heavy_pressing": 0.50, "pc_tight_band": 0.25, "pc_sharp_on_breathing": 0.12, "pc_burning": 0.10, "pc_tender_to_press": 0.03},
}, overrides={
    ("acute_coronary_syndrome", "moderate"): {"pc_heavy_pressing": 0.65, "pc_tight_band": 0.25, "pc_sharp_on_breathing": 0.02, "pc_burning": 0.06, "pc_tender_to_press": 0.02},
    ("acute_coronary_syndrome", "severe"): {"pc_heavy_pressing": 0.75, "pc_tight_band": 0.20, "pc_sharp_on_breathing": 0.01, "pc_burning": 0.03, "pc_tender_to_press": 0.01},
    ("musculoskeletal_chest_pain", "mild"): {"pc_heavy_pressing": 0.02, "pc_tight_band": 0.03, "pc_sharp_on_breathing": 0.20, "pc_burning": 0.05, "pc_tender_to_press": 0.70},
    ("musculoskeletal_chest_pain", "moderate"): {"pc_heavy_pressing": 0.03, "pc_tight_band": 0.05, "pc_sharp_on_breathing": 0.25, "pc_burning": 0.05, "pc_tender_to_press": 0.62},
    ("gastro_oesophageal_reflux", "mild"): {"pc_heavy_pressing": 0.05, "pc_tight_band": 0.05, "pc_sharp_on_breathing": 0.05, "pc_burning": 0.80, "pc_tender_to_press": 0.05},
    ("gastro_oesophageal_reflux", "moderate"): {"pc_heavy_pressing": 0.10, "pc_tight_band": 0.10, "pc_sharp_on_breathing": 0.05, "pc_burning": 0.70, "pc_tender_to_press": 0.05},
    ("pleurisy_or_pneumonia", "moderate"): {"pc_heavy_pressing": 0.05, "pc_tight_band": 0.05, "pc_sharp_on_breathing": 0.80, "pc_burning": 0.05, "pc_tender_to_press": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"dm_lt_2min": 0.20, "dm_2_20min": 0.40, "dm_gt_20_ongoing": 0.10, "dm_hours_days": 0.30},
    "moderate": {"dm_lt_2min": 0.10, "dm_2_20min": 0.45, "dm_gt_20_ongoing": 0.25, "dm_hours_days": 0.20},
    "severe": {"dm_lt_2min": 0.02, "dm_2_20min": 0.20, "dm_gt_20_ongoing": 0.65, "dm_hours_days": 0.13},
}, overrides={
    ("acute_coronary_syndrome", "severe"): {"dm_lt_2min": 0.00, "dm_2_20min": 0.10, "dm_gt_20_ongoing": 0.85, "dm_hours_days": 0.05},
    ("stable_angina", "moderate"): {"dm_lt_2min": 0.15, "dm_2_20min": 0.80, "dm_gt_20_ongoing": 0.03, "dm_hours_days": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"er_on_exertion": 0.30, "er_at_rest": 0.20, "er_no_relation": 0.50},
    "moderate": {"er_on_exertion": 0.40, "er_at_rest": 0.30, "er_no_relation": 0.30},
    "severe": {"er_on_exertion": 0.35, "er_at_rest": 0.50, "er_no_relation": 0.15},
}, overrides={
    ("stable_angina", "mild"): {"er_on_exertion": 0.85, "er_at_rest": 0.05, "er_no_relation": 0.10},
    ("stable_angina", "moderate"): {"er_on_exertion": 0.90, "er_at_rest": 0.05, "er_no_relation": 0.05},
    ("acute_coronary_syndrome", "severe"): {"er_on_exertion": 0.25, "er_at_rest": 0.70, "er_no_relation": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"rr_within_minutes": 0.50, "rr_partly": 0.30, "rr_no": 0.20},
    "moderate": {"rr_within_minutes": 0.35, "rr_partly": 0.40, "rr_no": 0.25},
    "severe": {"rr_within_minutes": 0.10, "rr_partly": 0.30, "rr_no": 0.60},
}, overrides={
    ("stable_angina", "mild"): {"rr_within_minutes": 0.85, "rr_partly": 0.12, "rr_no": 0.03},
    ("stable_angina", "moderate"): {"rr_within_minutes": 0.80, "rr_partly": 0.15, "rr_no": 0.05},
    ("acute_coronary_syndrome", "severe"): {"rr_within_minutes": 0.02, "rr_partly": 0.18, "rr_no": 0.80},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"po_worse_lying_flat": 0.10, "po_better_sitting_forward": 0.05, "po_worse_on_breathing": 0.15, "po_worse_on_movement": 0.30, "po_no_change": 0.40},
    "moderate": {"po_worse_lying_flat": 0.15, "po_better_sitting_forward": 0.08, "po_worse_on_breathing": 0.18, "po_worse_on_movement": 0.25, "po_no_change": 0.34},
    "severe": {"po_worse_lying_flat": 0.18, "po_better_sitting_forward": 0.10, "po_worse_on_breathing": 0.18, "po_worse_on_movement": 0.20, "po_no_change": 0.34},
}, overrides={
    ("pericarditis", "moderate"): {"po_worse_lying_flat": 0.50, "po_better_sitting_forward": 0.40, "po_worse_on_breathing": 0.05, "po_worse_on_movement": 0.02, "po_no_change": 0.03},
    ("pericarditis", "severe"): {"po_worse_lying_flat": 0.55, "po_better_sitting_forward": 0.40, "po_worse_on_breathing": 0.03, "po_worse_on_movement": 0.01, "po_no_change": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-08", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bp_at_rest": 0.02, "bp_on_exertion": 0.15, "bp_no": 0.83},
    "moderate": {"bp_at_rest": 0.12, "bp_on_exertion": 0.35, "bp_no": 0.53},
    "severe": {"bp_at_rest": 0.45, "bp_on_exertion": 0.35, "bp_no": 0.20},
}, overrides={
    ("acute_coronary_syndrome", "severe"): {"bp_at_rest": 0.65, "bp_on_exertion": 0.25, "bp_no": 0.10},
    ("pulmonary_embolism_cp", "severe"): {"bp_at_rest": 0.85, "bp_on_exertion": 0.12, "bp_no": 0.03},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("CPN-09", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"as_both_legs": 0.05, "as_one_leg": 0.01, "as_no": 0.94},
    "moderate": {"as_both_legs": 0.15, "as_one_leg": 0.03, "as_no": 0.82},
    "severe": {"as_both_legs": 0.25, "as_one_leg": 0.06, "as_no": 0.69},
}, overrides={
    ("pulmonary_embolism_cp", "moderate"): {"as_both_legs": 0.02, "as_one_leg": 0.60, "as_no": 0.38},
    ("pulmonary_embolism_cp", "severe"): {"as_both_legs": 0.02, "as_one_leg": 0.75, "as_no": 0.23},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("pleurisy_or_pneumonia", "pericarditis"),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
