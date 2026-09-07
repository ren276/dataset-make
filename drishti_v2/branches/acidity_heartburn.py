"""
drishti_v2/branches/acidity_heartburn.py
The `acidity_heartburn` branch (branch-authoring-batch-3-memo.md section 3).
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

CATEGORY_ID = "acidity_heartburn"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "gastro_oesophageal_reflux_gerd": ConditionSpec("gastro_oesophageal_reflux_gerd", 0.50, "IND-PRESENT",
        "Gastro-oesophageal reflux disease / functional heartburn"),
    "peptic_ulcer_disease_gastritis": ConditionSpec("peptic_ulcer_disease_gastritis", 0.30, "IND-PRESENT",
        "Peptic ulcer disease / H. pylori gastritis / NSAID gastropathy"),
    "cardiac_angina_mimic": ConditionSpec("cardiac_angina_mimic", 0.10, "IND-PRESENT",
        "Atypical angina / ACS presenting as epigastric burning", severeConditions=("cardiac pain presenting as acidity",)),
    "bleeding_peptic_ulcer": ConditionSpec("bleeding_peptic_ulcer", 0.05, "WORLD",
        "Complicated peptic ulcer with upper GI bleeding", severeConditions=("peptic ulcer bleeding",)),
    "gastric_or_oesophageal_malignancy": ConditionSpec("gastric_or_oesophageal_malignancy", 0.05, "ASSUMED",
        "Upper GI malignancy with alarm symptoms", severeConditions=("gastric malignancy",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "gastro_oesophageal_reflux_gerd": {"mild": 0.65, "moderate": 0.30, "severe": 0.05},
    "peptic_ulcer_disease_gastritis": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "cardiac_angina_mimic": {"mild": 0.15, "moderate": 0.50, "severe": 0.35},
    "bleeding_peptic_ulcer": {"mild": 0.05, "moderate": 0.35, "severe": 0.60},
    "gastric_or_oesophageal_malignancy": {"mild": 0.10, "moderate": 0.45, "severe": 0.45},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sbp = specs["bp_systolic"]

    if condition_id in ("cardiac_angina_mimic", "bleeding_peptic_ulcer") and severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 20, 10.0, 35, 220)
        specs["bp_systolic"] = VitalSpec(base_sbp.mean - 15, 8.0, 50, 200)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_ach_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_ach_emg2_stage_a(fields, ctx):
    return contains(fields, "danger_signs", "ds_chest_pain_exertion") and contains(fields, "danger_signs", "ds_sweating_with_pain")

def _gw_ach_emg3_stage_a(fields, ctx):
    return contains(fields, "danger_signs", "ds_vomiting_blood")

def _gw_ach_emg4_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_ach_emg2_full(fields, ctx):
    return _gw_ach_emg2_stage_a(fields, ctx) or (
        equals(fields, "exertional_relation", "er_on_exertion") and contains(fields, "danger_signs", "ds_sweating_with_pain")
    )

def _gw_ach_emg3_full(fields, ctx):
    return contains(fields, "danger_signs", "ds_vomiting_blood") or any_of(fields, "blood_in_stool", ["bs_frank", "bs_black"])

def _gw_ach_urg1_cardiac(fields, ctx):
    return equals(fields, "exertional_relation", "er_on_exertion")

def _gw_ach_urg2_dysphagia(fields, ctx):
    return any_of(fields, "dysphagia", ["dy_solids", "dy_liquids"])

def _gw_ach_urg3_alarm(fields, ctx):
    return contains(fields, "danger_signs", "ds_weight_loss_marked") or (
        equals(fields, "nsaid_use", "nu_current") and any_of(fields, "blood_in_stool", ["bs_frank", "bs_streaks", "bs_black"])
    )

_NODES = {
    "ACH-00": QuestionNode(
        nodeId="ACH-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_chest_pain_exertion", "Pain or heaviness in the chest that comes with walking or effort", next="ACH-G1a"),
            AnswerOption("ds_sweating_with_pain", "Sweating with the chest pain or heaviness", next="ACH-G1a"),
            AnswerOption("ds_vomiting_blood", "Vomiting blood or dark material like coffee grounds", next="ACH-G1a"),
            AnswerOption("ds_black_tarry_stool", "Black or tarry stool", next="ACH-G1a"),
            AnswerOption("ds_cannot_swallow", "Cannot swallow even liquids", next="ACH-G1a"),
            AnswerOption("ds_weight_loss_marked", "Noticed weight loss over weeks", next="ACH-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="ACH-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="ACH-G1a"),
        ],
        default_next="ACH-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "ACH-G1a": GatewayNode("ACH-G1a", "GW-ACH-EMG-1", _gw_ach_emg1, next="ACH-G1b",
                           routeTo="emergency_unconscious", severeConditions=["MI", "upper GI bleed with shock"]),
    "ACH-G1b": GatewayNode("ACH-G1b", "GW-ACH-EMG-2", _gw_ach_emg2_stage_a, next="ACH-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["acute coronary syndrome"]),
    "ACH-G1c": GatewayNode("ACH-G1c", "GW-ACH-EMG-3", _gw_ach_emg3_stage_a, next="ACH-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["upper GI haemorrhage", "variceal bleeding"]),
    "ACH-G1d": GatewayNode("ACH-G1d", "GW-ACH-EMG-4", _gw_ach_emg4_infant, next="ACH-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "ACH-01": QuestionNode(
        nodeId="ACH-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="ACH-02"),
            AnswerOption("pr_same", "About the same", next="ACH-02"),
            AnswerOption("pr_worse", "Worse", next="ACH-02"),
        ],
        default_next="ACH-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "ACH-02": QuestionNode(
        nodeId="ACH-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="ACH-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="ACH-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="ACH-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="ACH-03"),
            AnswerOption("pt_other", "Other treatment", next="ACH-03"),
        ],
        default_next="ACH-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "ACH-03": QuestionNode(
        nodeId="ACH-03", fieldId="relation_to_food", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rf_better_after_food", "Better after eating", next="ACH-04"),
            AnswerOption("rf_worse_after_food", "Worse after eating", next="ACH-04"),
            AnswerOption("rf_empty_stomach", "Worse on empty stomach", next="ACH-04"),
            AnswerOption("rf_no_relation", "No change with food", next="ACH-04"),
        ],
        default_next="ACH-04", unknown_option="rf_unknown", **_nu(0.03)
    ),
    "ACH-04": QuestionNode(
        nodeId="ACH-04", fieldId="exertional_relation", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("er_on_exertion", "Yes — comes with effort", next="ACH-05"),
            AnswerOption("er_at_rest", "Only at rest", next="ACH-05"),
            AnswerOption("er_no_relation", "No clear relation", next="ACH-05"),
        ],
        default_next="ACH-05", unknown_option="er_unknown", **_nu(0.03)
    ),
    "ACH-05": QuestionNode(
        nodeId="ACH-05", fieldId="night_symptoms", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ns_acid_yes", "Yes — acid or burning feeling at night", next="ACH-06"),
            AnswerOption("ns_no", "No", next="ACH-06"),
        ],
        default_next="ACH-06", unknown_option="ns_unknown", **_nu(0.03)
    ),
    "ACH-06": QuestionNode(
        nodeId="ACH-06", fieldId="dysphagia", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("dy_solids", "Yes — solid food gets stuck", next="ACH-07"),
            AnswerOption("dy_liquids", "Yes — even liquids are difficult", next="ACH-07"),
            AnswerOption("dy_no", "No difficulty swallowing", next="ACH-07"),
        ],
        default_next="ACH-07", unknown_option="dy_unknown", **_nu(0.03)
    ),
    "ACH-07": QuestionNode(
        nodeId="ACH-07", fieldId="nsaid_use", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("nu_current", "Yes — currently taking", next="ACH-08"),
            AnswerOption("nu_recent", "Took them recently but stopped", next="ACH-08"),
            AnswerOption("nu_no", "No", next="ACH-08"),
        ],
        default_next="ACH-08", unknown_option="nu_unknown", **_nu(0.03)
    ),
    "ACH-08": QuestionNode(
        nodeId="ACH-08", fieldId="blood_in_stool", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bs_frank", "Red blood with stool", next="ACH-S1"),
            AnswerOption("bs_streaks", "Streaks of blood on stool surface", next="ACH-S1"),
            AnswerOption("bs_black", "Black or tarry stool", next="ACH-S1"),
            AnswerOption("bs_no", "No blood seen", next="ACH-S1"),
        ],
        default_next="ACH-S1", unknown_option="bs_unknown", **_nu(0.03)
    ),

    "ACH-S1": SubtreeRefNode("ACH-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="ACH-G2a"),
    "ACH-G2a": GatewayNode("ACH-G2a", "GW-ACH-EMG-2", _gw_ach_emg2_full, next="ACH-G2b",
                           raisesTo="REFER_EMERGENCY", severeConditions=["acute coronary syndrome"]),
    "ACH-G2b": GatewayNode("ACH-G2b", "GW-ACH-EMG-3", _gw_ach_emg3_full, next="ACH-G3a",
                           raisesTo="REFER_EMERGENCY", severeConditions=["upper GI haemorrhage", "variceal bleeding"]),
    "ACH-G3a": GatewayNode("ACH-G3a", "GW-ACH-URG-1", _gw_ach_urg1_cardiac, next="ACH-G3b",
                           raisesTo="REFER_URGENT", severeConditions=["cardiac pain presenting as acidity"]),
    "ACH-G3b": GatewayNode("ACH-G3b", "GW-ACH-URG-2", _gw_ach_urg2_dysphagia, next="ACH-G3c",
                           raisesTo="REFER_URGENT", severeConditions=["oesophageal stricture", "gastric malignancy"]),
    "ACH-G3c": GatewayNode("ACH-G3c", "GW-ACH-URG-3", _gw_ach_urg3_alarm, next="ACH-END",
                           raisesTo="REFER_URGENT", severeConditions=["gastric malignancy", "NSAID-related ulcer bleed"]),
    "ACH-END": TerminalNode("ACH-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="ACH-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Acidity heartburn clinical distribution"

_entries = []

_entries += expand_entries("ACH-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_chest_pain_exertion": 0.01, "ds_sweating_with_pain": 0.01, "ds_vomiting_blood": 0.002,
             "ds_black_tarry_stool": 0.005, "ds_cannot_swallow": 0.005, "ds_weight_loss_marked": 0.01,
             "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_chest_pain_exertion": 0.05, "ds_sweating_with_pain": 0.05, "ds_vomiting_blood": 0.01,
                "ds_black_tarry_stool": 0.02, "ds_cannot_swallow": 0.02, "ds_weight_loss_marked": 0.05,
                "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_chest_pain_exertion": 0.20, "ds_sweating_with_pain": 0.20, "ds_vomiting_blood": 0.10,
               "ds_black_tarry_stool": 0.15, "ds_cannot_swallow": 0.10, "ds_weight_loss_marked": 0.15,
               "ds_unconscious": 0.02, "ds_cannot_feed": 0.02},
}, overrides={
    ("cardiac_angina_mimic", "moderate"): {"ds_chest_pain_exertion": 0.65, "ds_sweating_with_pain": 0.45, "ds_vomiting_blood": 0.00,
                                           "ds_black_tarry_stool": 0.00, "ds_cannot_swallow": 0.00, "ds_weight_loss_marked": 0.01,
                                           "ds_unconscious": 0.02, "ds_cannot_feed": 0.01},
    ("cardiac_angina_mimic", "severe"): {"ds_chest_pain_exertion": 0.85, "ds_sweating_with_pain": 0.75, "ds_vomiting_blood": 0.00,
                                         "ds_black_tarry_stool": 0.00, "ds_cannot_swallow": 0.00, "ds_weight_loss_marked": 0.01,
                                         "ds_unconscious": 0.08, "ds_cannot_feed": 0.02},
    ("bleeding_peptic_ulcer", "severe"): {"ds_chest_pain_exertion": 0.02, "ds_sweating_with_pain": 0.10, "ds_vomiting_blood": 0.75,
                                         "ds_black_tarry_stool": 0.80, "ds_cannot_swallow": 0.02, "ds_weight_loss_marked": 0.05,
                                         "ds_unconscious": 0.08, "ds_cannot_feed": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.45, "pt_pharmacy_medicine": 0.50, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.25, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"rf_better_after_food": 0.30, "rf_worse_after_food": 0.40, "rf_empty_stomach": 0.20, "rf_no_relation": 0.10},
    "moderate": {"rf_better_after_food": 0.30, "rf_worse_after_food": 0.40, "rf_empty_stomach": 0.20, "rf_no_relation": 0.10},
    "severe": {"rf_better_after_food": 0.25, "rf_worse_after_food": 0.35, "rf_empty_stomach": 0.20, "rf_no_relation": 0.20},
}, overrides={
    ("peptic_ulcer_disease_gastritis", "moderate"): {"rf_better_after_food": 0.45, "rf_worse_after_food": 0.15, "rf_empty_stomach": 0.35, "rf_no_relation": 0.05},
    ("cardiac_angina_mimic", "moderate"): {"rf_better_after_food": 0.05, "rf_worse_after_food": 0.10, "rf_empty_stomach": 0.05, "rf_no_relation": 0.80},
    ("cardiac_angina_mimic", "severe"): {"rf_better_after_food": 0.02, "rf_worse_after_food": 0.08, "rf_empty_stomach": 0.02, "rf_no_relation": 0.88},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"er_on_exertion": 0.05, "er_at_rest": 0.35, "er_no_relation": 0.60},
    "moderate": {"er_on_exertion": 0.15, "er_at_rest": 0.40, "er_no_relation": 0.45},
    "severe": {"er_on_exertion": 0.25, "er_at_rest": 0.45, "er_no_relation": 0.30},
}, overrides={
    ("cardiac_angina_mimic", "moderate"): {"er_on_exertion": 0.80, "er_at_rest": 0.10, "er_no_relation": 0.10},
    ("cardiac_angina_mimic", "severe"): {"er_on_exertion": 0.85, "er_at_rest": 0.10, "er_no_relation": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ns_acid_yes": 0.25, "ns_no": 0.75},
    "moderate": {"ns_acid_yes": 0.45, "ns_no": 0.55},
    "severe": {"ns_acid_yes": 0.60, "ns_no": 0.40},
}, overrides={
    ("gastro_oesophageal_reflux_gerd", "moderate"): {"ns_acid_yes": 0.70, "ns_no": 0.30},
    ("gastro_oesophageal_reflux_gerd", "severe"): {"ns_acid_yes": 0.85, "ns_no": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"dy_solids": 0.02, "dy_liquids": 0.005, "dy_no": 0.975},
    "moderate": {"dy_solids": 0.08, "dy_liquids": 0.02, "dy_no": 0.90},
    "severe": {"dy_solids": 0.20, "dy_liquids": 0.10, "dy_no": 0.70},
}, overrides={
    ("gastric_or_oesophageal_malignancy", "moderate"): {"dy_solids": 0.60, "dy_liquids": 0.15, "dy_no": 0.25},
    ("gastric_or_oesophageal_malignancy", "severe"): {"dy_solids": 0.40, "dy_liquids": 0.50, "dy_no": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"nu_current": 0.15, "nu_recent": 0.15, "nu_no": 0.70}
    for s in SEVERITIES
}, overrides={
    ("peptic_ulcer_disease_gastritis", s): {"nu_current": 0.45, "nu_recent": 0.25, "nu_no": 0.30} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ACH-08", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bs_frank": 0.005, "bs_streaks": 0.01, "bs_black": 0.005, "bs_no": 0.98},
    "moderate": {"bs_frank": 0.02, "bs_streaks": 0.03, "bs_black": 0.02, "bs_no": 0.93},
    "severe": {"bs_frank": 0.10, "bs_streaks": 0.08, "bs_black": 0.15, "bs_no": 0.67},
}, overrides={
    ("bleeding_peptic_ulcer", "moderate"): {"bs_frank": 0.15, "bs_streaks": 0.10, "bs_black": 0.65, "bs_no": 0.10},
    ("bleeding_peptic_ulcer", "severe"): {"bs_frank": 0.25, "bs_streaks": 0.05, "bs_black": 0.68, "bs_no": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=(),
    bleeding_conditions=("bleeding_peptic_ulcer",),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
