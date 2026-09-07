"""
drishti_v2/branches/known_diabetes.py
The `known_diabetes` branch (branch-authoring-batch-2-memo.md section 4, amended for G-15).
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

CATEGORY_ID = "known_diabetes"
BRANCH_VERSION = "1.0.1-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "controlled_type2_diabetes": ConditionSpec("controlled_type2_diabetes", 0.45, "IND-POP",
        "Controlled type 2 diabetes on lifestyle or oral agents"),
    "uncontrolled_diabetes_hyperglycaemia": ConditionSpec("uncontrolled_diabetes_hyperglycaemia", 0.30, "IND-POP",
        "Uncontrolled diabetes with symptomatic hyperglycaemia"),
    "diabetic_peripheral_neuropathy_or_ulcer": ConditionSpec("diabetic_peripheral_neuropathy_or_ulcer", 0.12, "IND-PRESENT",
        "Diabetic peripheral neuropathy or early foot complication", severeConditions=("diabetic foot",)),
    "recurrent_hypoglycaemia": ConditionSpec("recurrent_hypoglycaemia", 0.06, "ASSUMED",
        "Drug-induced recurrent hypoglycaemia", severeConditions=("hypoglycaemia",)),
    "diabetic_ketoacidosis_emergency": ConditionSpec("diabetic_ketoacidosis_emergency", 0.04, "ASSUMED",
        "Diabetic ketoacidosis or hyperosmolar state", severeConditions=("DKA",)),
    "diabetes_tb_comorbidity": ConditionSpec("diabetes_tb_comorbidity", 0.03, "IND-PROG",
        "Type 2 diabetes with active tuberculosis co-infection", severeConditions=("TB co-infection",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "controlled_type2_diabetes": {"mild": 0.70, "moderate": 0.25, "severe": 0.05},
    "uncontrolled_diabetes_hyperglycaemia": {"mild": 0.30, "moderate": 0.55, "severe": 0.15},
    "diabetic_peripheral_neuropathy_or_ulcer": {"mild": 0.20, "moderate": 0.55, "severe": 0.25},
    "recurrent_hypoglycaemia": {"mild": 0.20, "moderate": 0.45, "severe": 0.35},
    "diabetic_ketoacidosis_emergency": {"mild": 0.05, "moderate": 0.25, "severe": 0.70},
    "diabetes_tb_comorbidity": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]
    base_sbp = specs["bp_systolic"]
    base_dbp = specs["bp_diastolic"]
    base_temp = specs["temperature"]

    if condition_id == "diabetic_ketoacidosis_emergency":
        specs["respiratory_rate"] = VitalSpec(28.0, 3.5, 10, 60)  # Kussmaul
        specs["pulse"] = VitalSpec(115.0, 10.0, 35, 220)
        specs["bp_systolic"] = VitalSpec(95.0, 8.0, 50, 200)
    elif condition_id == "recurrent_hypoglycaemia" and severity_band == "severe":
        specs["pulse"] = VitalSpec(110.0, 10.0, 35, 220)
    elif condition_id == "diabetes_tb_comorbidity":
        specs["temperature"] = VitalSpec(base_temp.mean + 0.8, 0.4, 34, 41)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_dm_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_dm_emg2_dka(fields, ctx):
    return any_of(fields, "danger_signs", ["ds_fast_deep_breath", "ds_fruity_breath"]) or (
        contains(fields, "danger_signs", "ds_vomiting_every") and contains(fields, "danger_signs", "ds_confusion")
    )

def _gw_dm_emg3_hypo(fields, ctx):
    return contains(fields, "danger_signs", "ds_sweating_shaky") and contains(fields, "danger_signs", "ds_confusion")

def _gw_dm_emg4_acs(fields, ctx):
    return contains(fields, "danger_signs", "ds_chest_pain")

def _gw_dm_emg5_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_dm_urg1_decomp(fields, ctx):
    return equals(fields, "polyuria_polydipsia", "pp_both") or equals(fields, "hypoglycaemia_episodes", "he_frequent") or (
        any_of(fields, "diabetes_medication_adherence", ["dma_stopped", "dma_none_given"]) and equals(fields, "progression", "pr_worse")
    )

def _gw_dm_urg2_foot(fields, ctx):
    return any_of(fields, "foot_ulcer_or_numbness", ["fun_wound", "fun_both"]) or contains(fields, "danger_signs", "ds_foot_wound")

def _gw_dm_urg3_tb(fields, ctx):
    return equals(fields, "tb_contact", "tbc_yes") or equals(fields, "cough_ge_2_weeks", "c2_yes") or equals(fields, "weight_loss_present", "wl_yes") or equals(fields, "night_sweats", "ns_yes")

def _gw_dm_adh1(fields, ctx):
    return any_of(fields, "diabetes_medication_adherence", ["dma_stopped", "dma_none_given"])

_NODES = {
    "DM-00": QuestionNode(
        nodeId="DM-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="DM-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="DM-G1a"),
            AnswerOption("ds_vomiting_every", "Vomiting everything, cannot keep fluids down", next="DM-G1a"),
            AnswerOption("ds_fast_deep_breath", "Breathing fast and deep", next="DM-G1a"),
            AnswerOption("ds_fruity_breath", "Breath smells sweet or fruity", next="DM-G1a"),
            AnswerOption("ds_sweating_shaky", "Sweating, shaking, or feeling faint", next="DM-G1a"),
            AnswerOption("ds_chest_pain", "Chest pain or heaviness", next="DM-G1a"),
            AnswerOption("ds_foot_wound", "Open wound or black discolouration on the foot", next="DM-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="DM-G1a"),
        ],
        default_next="DM-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "DM-G1a": GatewayNode("DM-G1a", "GW-DM-EMG-1", _gw_dm_emg1, next="DM-G1b",
                          routeTo="emergency_unconscious", severeConditions=["hypoglycaemic coma", "DKA"]),
    "DM-G1b": GatewayNode("DM-G1b", "GW-DM-EMG-2", _gw_dm_emg2_dka, next="DM-G1c",
                          raisesTo="REFER_EMERGENCY", severeConditions=["DKA"]),
    "DM-G1c": GatewayNode("DM-G1c", "GW-DM-EMG-3", _gw_dm_emg3_hypo, next="DM-G1d",
                          raisesTo="REFER_EMERGENCY", severeConditions=["severe hypoglycaemia"]),
    "DM-G1d": GatewayNode("DM-G1d", "GW-DM-EMG-4", _gw_dm_emg4_acs, next="DM-G1e",
                          raisesTo="REFER_EMERGENCY", severeConditions=["silent MI", "acute coronary syndrome in a diabetic"]),
    "DM-G1e": GatewayNode("DM-G1e", "GW-DM-EMG-5", _gw_dm_emg5_infant, next="DM-01",
                          raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "DM-01": QuestionNode(
        nodeId="DM-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="DM-02"),
            AnswerOption("pr_same", "About the same", next="DM-02"),
            AnswerOption("pr_worse", "Worse", next="DM-02"),
        ],
        default_next="DM-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "DM-02": QuestionNode(
        nodeId="DM-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or diet alone", next="DM-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="DM-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="DM-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed diabetes medicine", next="DM-03"),
            AnswerOption("pt_other", "Other treatment", next="DM-03"),
        ],
        default_next="DM-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "DM-03": QuestionNode(
        nodeId="DM-03", fieldId="visit_reason_subtype", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vr_refill", "Routine check / medicine refill", next="DM-04"),
            AnswerOption("vr_new_symptom", "New complaint since last visit", next="DM-04"),
            AnswerOption("vr_followup", "Follow-up after a referral", next="DM-04"),
            AnswerOption("vr_first", "First visit for known diabetes", next="DM-04"),
            AnswerOption("vr_unknown", "Not known", next="DM-04"),
        ],
        default_next="DM-04", unknown_option="vr_unknown", **_nu(0.03)
    ),
    "DM-04": QuestionNode(
        nodeId="DM-04", fieldId="diabetes_medication_adherence", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("dma_daily", "Every day as prescribed", next="DM-05"),
            AnswerOption("dma_missed_some", "Misses some days", next="DM-05"),
            AnswerOption("dma_stopped", "Stopped taking it", next="DM-05"),
            AnswerOption("dma_none_given", "Never been given medicine", next="DM-05"),
        ],
        default_next="DM-05", unknown_option="dma_unknown", **_nu(0.03)
    ),
    "DM-05": QuestionNode(
        nodeId="DM-05", fieldId="hypoglycaemia_episodes", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("he_frequent", "Yes — more than once a week", next="DM-06"),
            AnswerOption("he_occasional", "Yes — but rarely", next="DM-06"),
            AnswerOption("he_no", "No", next="DM-06"),
        ],
        default_next="DM-06", unknown_option="he_unknown", **_nu(0.03)
    ),
    "DM-06": QuestionNode(
        nodeId="DM-06", fieldId="polyuria_polydipsia", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pp_both", "Yes — both", next="DM-07"),
            AnswerOption("pp_urine", "Mostly frequent urination", next="DM-07"),
            AnswerOption("pp_thirst", "Mostly thirst", next="DM-07"),
            AnswerOption("pp_no", "No", next="DM-07"),
        ],
        default_next="DM-07", unknown_option="pp_unknown", **_nu(0.03)
    ),
    "DM-07": QuestionNode(
        nodeId="DM-07", fieldId="foot_ulcer_or_numbness", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fun_wound", "Yes — wound or ulcer on the foot", next="DM-08"),
            AnswerOption("fun_numb", "Numbness or tingling in the feet", next="DM-08"),
            AnswerOption("fun_both", "Both", next="DM-08"),
            AnswerOption("fun_no", "No wound and no numbness", next="DM-08"),
        ],
        default_next="DM-08", unknown_option="fun_unknown", **_nu(0.03)
    ),
    "DM-08": QuestionNode(
        nodeId="DM-08", fieldId="visual_blurring", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vb_yes", "Yes", next="DM-S1"),
            AnswerOption("vb_no", "No", next="DM-S1"),
        ],
        default_next="DM-S1", unknown_option="vb_unknown", **_nu(0.03)
    ),

    "DM-S1": SubtreeRefNode("DM-S1", subtree_nodes=make_tb_screen_nodes(), entry="TBS-01", returnNext="DM-G3"),
    "DM-G3": GatewayNode("DM-G3", "GW-DM-URG-3", _gw_dm_urg3_tb, next="DM-S2",
                         raisesTo="REFER_URGENT", severeConditions=["TB co-infection"]),
    "DM-S2": SubtreeRefNode("DM-S2", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="DM-G2a"),
    "DM-G2a": GatewayNode("DM-G2a", "GW-DM-URG-1", _gw_dm_urg1_decomp, next="DM-G2b",
                          raisesTo="REFER_URGENT", severeConditions=["uncontrolled diabetes", "recurrent hypoglycaemia"]),
    "DM-G2b": GatewayNode("DM-G2b", "GW-DM-URG-2", _gw_dm_urg2_foot, next="DM-G2c",
                          raisesTo="REFER_URGENT", severeConditions=["diabetic foot", "peripheral vascular disease"]),
    "DM-G2c": GatewayNode("DM-G2c", "GW-DM-ADH-1", _gw_dm_adh1, next="DM-END",
                          raisesTo="PHYSICIAN_REVIEW_MANDATORY", severeConditions=["non-adherence"]),
    "DM-END": TerminalNode("DM-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="DM-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Known diabetes clinical distribution"

_entries = []

_entries += expand_entries("DM-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_confusion": 0.005, "ds_unconscious": 0.001, "ds_vomiting_every": 0.005,
             "ds_fast_deep_breath": 0.002, "ds_fruity_breath": 0.002, "ds_sweating_shaky": 0.02,
             "ds_chest_pain": 0.01, "ds_foot_wound": 0.02, "ds_cannot_feed": 0.005},
    "moderate": {"ds_confusion": 0.02, "ds_unconscious": 0.005, "ds_vomiting_every": 0.02,
                "ds_fast_deep_breath": 0.01, "ds_fruity_breath": 0.01, "ds_sweating_shaky": 0.08,
                "ds_chest_pain": 0.03, "ds_foot_wound": 0.08, "ds_cannot_feed": 0.01},
    "severe": {"ds_confusion": 0.15, "ds_unconscious": 0.05, "ds_vomiting_every": 0.15,
               "ds_fast_deep_breath": 0.15, "ds_fruity_breath": 0.12, "ds_sweating_shaky": 0.20,
               "ds_chest_pain": 0.08, "ds_foot_wound": 0.20, "ds_cannot_feed": 0.05},
}, overrides={
    ("diabetic_ketoacidosis_emergency", "severe"): {"ds_confusion": 0.70, "ds_unconscious": 0.25, "ds_vomiting_every": 0.65,
                                                   "ds_fast_deep_breath": 0.80, "ds_fruity_breath": 0.75, "ds_sweating_shaky": 0.15,
                                                   "ds_chest_pain": 0.10, "ds_foot_wound": 0.05, "ds_cannot_feed": 0.10},
    ("recurrent_hypoglycaemia", "severe"): {"ds_confusion": 0.65, "ds_unconscious": 0.20, "ds_vomiting_every": 0.05,
                                            "ds_fast_deep_breath": 0.02, "ds_fruity_breath": 0.01, "ds_sweating_shaky": 0.85,
                                            "ds_chest_pain": 0.05, "ds_foot_wound": 0.02, "ds_cannot_feed": 0.05},
    ("diabetic_peripheral_neuropathy_or_ulcer", "severe"): {"ds_confusion": 0.02, "ds_unconscious": 0.01, "ds_vomiting_every": 0.02,
                                                           "ds_fast_deep_breath": 0.01, "ds_fruity_breath": 0.01, "ds_sweating_shaky": 0.05,
                                                           "ds_chest_pain": 0.05, "ds_foot_wound": 0.85, "ds_cannot_feed": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.40, "pr_same": 0.50, "pr_worse": 0.10},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.30, "pt_pharmacy_medicine": 0.30, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.65, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vr_refill": 0.70, "vr_new_symptom": 0.15, "vr_followup": 0.10, "vr_first": 0.05},
    "moderate": {"vr_refill": 0.45, "vr_new_symptom": 0.35, "vr_followup": 0.15, "vr_first": 0.05},
    "severe": {"vr_refill": 0.20, "vr_new_symptom": 0.55, "vr_followup": 0.20, "vr_first": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"dma_daily": 0.75, "dma_missed_some": 0.18, "dma_stopped": 0.05, "dma_none_given": 0.02},
    "moderate": {"dma_daily": 0.50, "dma_missed_some": 0.30, "dma_stopped": 0.15, "dma_none_given": 0.05},
    "severe": {"dma_daily": 0.30, "dma_missed_some": 0.30, "dma_stopped": 0.30, "dma_none_given": 0.10},
}, overrides={
    ("diabetic_ketoacidosis_emergency", "severe"): {"dma_daily": 0.10, "dma_missed_some": 0.20, "dma_stopped": 0.60, "dma_none_given": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"he_frequent": 0.02, "he_occasional": 0.15, "he_no": 0.83},
    "moderate": {"he_frequent": 0.08, "he_occasional": 0.25, "he_no": 0.67},
    "severe": {"he_frequent": 0.15, "he_occasional": 0.25, "he_no": 0.60},
}, overrides={
    ("recurrent_hypoglycaemia", "moderate"): {"he_frequent": 0.45, "he_occasional": 0.45, "he_no": 0.10},
    ("recurrent_hypoglycaemia", "severe"): {"he_frequent": 0.75, "he_occasional": 0.20, "he_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pp_both": 0.10, "pp_urine": 0.20, "pp_thirst": 0.15, "pp_no": 0.55},
    "moderate": {"pp_both": 0.30, "pp_urine": 0.25, "pp_thirst": 0.20, "pp_no": 0.25},
    "severe": {"pp_both": 0.55, "pp_urine": 0.20, "pp_thirst": 0.15, "pp_no": 0.10},
}, overrides={
    ("uncontrolled_diabetes_hyperglycaemia", "moderate"): {"pp_both": 0.60, "pp_urine": 0.20, "pp_thirst": 0.15, "pp_no": 0.05},
    ("uncontrolled_diabetes_hyperglycaemia", "severe"): {"pp_both": 0.80, "pp_urine": 0.10, "pp_thirst": 0.08, "pp_no": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"fun_wound": 0.02, "fun_numb": 0.15, "fun_both": 0.01, "fun_no": 0.82},
    "moderate": {"fun_wound": 0.08, "fun_numb": 0.30, "fun_both": 0.05, "fun_no": 0.57},
    "severe": {"fun_wound": 0.15, "fun_numb": 0.35, "fun_both": 0.15, "fun_no": 0.35},
}, overrides={
    ("diabetic_peripheral_neuropathy_or_ulcer", "moderate"): {"fun_wound": 0.25, "fun_numb": 0.50, "fun_both": 0.20, "fun_no": 0.05},
    ("diabetic_peripheral_neuropathy_or_ulcer", "severe"): {"fun_wound": 0.35, "fun_numb": 0.20, "fun_both": 0.40, "fun_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DM-08", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vb_yes": 0.15, "vb_no": 0.85},
    "moderate": {"vb_yes": 0.35, "vb_no": 0.65},
    "severe": {"vb_yes": 0.55, "vb_no": 0.45},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_tb_screen_entries(
    CONDITION_IDS, SEVERITIES,
    tb_conditions=("diabetes_tb_comorbidity",),
    source_type="IND-PROG", source="Nikshay India TB programme",
)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("diabetes_tb_comorbidity",),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
