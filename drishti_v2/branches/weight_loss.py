"""
drishti_v2/branches/weight_loss.py
The `weight_loss` branch (branch-authoring-batch-3-memo.md section 8).
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

CATEGORY_ID = "weight_loss"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_URGENT"

CONDITIONS = {
    "pulmonary_or_extrapulmonary_tuberculosis": ConditionSpec(
        "pulmonary_or_extrapulmonary_tuberculosis", 0.40, "IND-PROG",
        "Pulmonary or extrapulmonary tuberculosis", severeConditions=("TB",)
    ),
    "undiagnosed_diabetes_mellitus": ConditionSpec(
        "undiagnosed_diabetes_mellitus", 0.20, "IND-POP",
        "Undiagnosed type 1 or type 2 diabetes presenting with catabolic weight loss",
        severeConditions=("diabetes",)
    ),
    "unexplained_underlying_malignancy": ConditionSpec(
        "unexplained_underlying_malignancy", 0.15, "IND-POP",
        "Underlying malignancy presenting as unexplained constitutional weight loss",
        severeConditions=("malignancy",)
    ),
    "hyperthyroidism_thyrotoxicosis": ConditionSpec(
        "hyperthyroidism_thyrotoxicosis", 0.10, "IND-POP",
        "Primary thyrotoxicosis with unintended weight loss despite preserved/increased appetite",
        severeConditions=("hyperthyroidism",)
    ),
    "chronic_infection_or_hiv_related": ConditionSpec(
        "chronic_infection_or_hiv_related", 0.05, "IND-PROG",
        "Chronic HIV wasting syndrome or advanced immunosuppressive illness",
        severeConditions=("HIV",)
    ),
    "inadequate_caloric_intake_or_malnutrition": ConditionSpec(
        "inadequate_caloric_intake_or_malnutrition", 0.10, "IND-POP",
        "Nutritional inadequacy, food insecurity, or severe protein-calorie malnutrition"
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "pulmonary_or_extrapulmonary_tuberculosis": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "undiagnosed_diabetes_mellitus": {"mild": 0.30, "moderate": 0.50, "severe": 0.20},
    "unexplained_underlying_malignancy": {"mild": 0.15, "moderate": 0.45, "severe": 0.40},
    "hyperthyroidism_thyrotoxicosis": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "chronic_infection_or_hiv_related": {"mild": 0.15, "moderate": 0.45, "severe": 0.40},
    "inadequate_caloric_intake_or_malnutrition": {"mild": 0.50, "moderate": 0.35, "severe": 0.15},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    if condition_id == "hyperthyroidism_thyrotoxicosis":
        specs["pulse"] = VitalSpec(base_pulse.mean + 25, 10.0, 40, 220)
    elif condition_id == "pulmonary_or_extrapulmonary_tuberculosis":
        specs["temperature"] = VitalSpec(base_temp.mean + 0.8, 0.4, 34, 41)
    elif condition_id == "unexplained_underlying_malignancy" and severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 15, 8.0, 35, 200)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_wtl_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_wtl_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_blood_in_cough")

def _gw_wtl_emg3(fields, ctx):
    return (
        contains(fields, "danger_signs", "ds_severe_pallor")
        and contains(fields, "danger_signs", "ds_breathless_rest")
    )

def _gw_wtl_emg4(fields, ctx):
    age_band = ctx.get("age_band", "")
    return (
        age_band in ("infant", "child")
        and contains(fields, "danger_signs", "ds_cannot_feed")
    )

def _gw_wtl_urg1_tb(fields, ctx):
    c2 = equals(fields, "cough_ge_2_weeks", "c2_yes")
    tbc = equals(fields, "tb_contact", "tbc_yes")
    wl_ns = equals(fields, "weight_loss_present", "wl_yes") and equals(fields, "night_sweats", "ns_yes")
    return c2 or tbc or wl_ns

def _gw_wtl_urg2_severe_loss(fields, ctx):
    return equals(fields, "weight_loss_amount_band", "wa_gt_10")

def _gw_wtl_urg3_diabetes(fields, ctx):
    return equals(fields, "polyuria_polydipsia", "pp_both")

def _gw_wtl_urg4_haemoptysis(fields, ctx):
    return equals(fields, "cough_character", "cc_blood")

_NODES = {
    "WTL-00": QuestionNode(
        nodeId="WTL-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_severe_pallor", "Very pale — palms, conjunctivae, or tongue white", next="WTL-G1a"),
            AnswerOption("ds_breathless_rest", "Breathless even when sitting still", next="WTL-G1a"),
            AnswerOption("ds_lump_swelling", "A lump or swelling that is growing", next="WTL-G1a"),
            AnswerOption("ds_fever_gt_2wk", "Fever lasting more than 2 weeks", next="WTL-G1a"),
            AnswerOption("ds_blood_in_cough", "Coughing up blood", next="WTL-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="WTL-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="WTL-G1a"),
            AnswerOption("ds_none", "None of these", next="WTL-01"),
        ],
        default_next="WTL-G1a", none_option="ds_none", unknown_option="ds_unknown", **_nu(0.01)
    ),
    "WTL-G1a": GatewayNode("WTL-G1a", "GW-WTL-EMG-1", _gw_wtl_emg1, next="WTL-G1b",
                           routeTo="emergency_unconscious"),
    "WTL-G1b": GatewayNode("WTL-G1b", "GW-WTL-EMG-2", _gw_wtl_emg2, next="WTL-G1c",
                           routeTo="emergency_heavy_bleeding"),
    "WTL-G1c": GatewayNode("WTL-G1c", "GW-WTL-EMG-3", _gw_wtl_emg3, next="WTL-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["severe anaemia", "late-stage malignancy"]),
    "WTL-G1d": GatewayNode("WTL-G1d", "GW-WTL-EMG-4", _gw_wtl_emg4, next="WTL-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "WTL-01": QuestionNode(
        nodeId="WTL-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Getting better", next="WTL-02"),
            AnswerOption("pr_same", "About the same", next="WTL-02"),
            AnswerOption("pr_worse", "Getting worse", next="WTL-02"),
        ],
        default_next="WTL-02", unknown_option="pr_unknown", **_nu(0.02)
    ),
    "WTL-02": QuestionNode(
        nodeId="WTL-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies", next="WTL-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy / shop", next="WTL-03"),
            AnswerOption("pt_ayush", "Ayurvedic / homeopathic / traditional medicine", next="WTL-03"),
            AnswerOption("pt_prescribed_prior", "Prescription medicine from another doctor", next="WTL-03"),
            AnswerOption("pt_other", "Other treatment", next="WTL-03"),
            AnswerOption("pt_none", "No prior treatment", next="WTL-03"),
        ],
        default_next="WTL-03", none_option="pt_none", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "WTL-03": QuestionNode(
        nodeId="WTL-03", fieldId="weight_loss_amount_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("wa_lt_5", "A little — less than 5 kg / clothes a bit loose", next="WTL-G2"),
            AnswerOption("wa_5_10", "5 to 10 kg — clothes noticeably loose", next="WTL-G2"),
            AnswerOption("wa_gt_10", "More than 10 kg — very visible change", next="WTL-G2"),
        ],
        default_next="WTL-G2", unknown_option="wa_unknown", **_nu(0.03)
    ),
    "WTL-G2": GatewayNode("WTL-G2", "GW-WTL-URG-2", _gw_wtl_urg2_severe_loss, next="WTL-04",
                          raisesTo="REFER_URGENT", severeConditions=["malignancy", "advanced TB", "HIV"]),

    "WTL-04": QuestionNode(
        nodeId="WTL-04", fieldId="appetite_change", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ac_decreased", "Decreased — eating less than usual", next="WTL-05"),
            AnswerOption("ac_increased", "Increased — eating more but still losing weight", next="WTL-05"),
            AnswerOption("ac_no_change", "No change in appetite", next="WTL-05"),
        ],
        default_next="WTL-05", unknown_option="ac_unknown", **_nu(0.03)
    ),
    "WTL-05": QuestionNode(
        nodeId="WTL-05", fieldId="cough_character", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("cc_dry", "Dry cough", next="WTL-G_cc"),
            AnswerOption("cc_productive", "Cough with phlegm/sputum", next="WTL-G_cc"),
            AnswerOption("cc_blood", "Cough with blood", next="WTL-G_cc"),
            AnswerOption("cc_paroxysmal", "Severe coughing bouts", next="WTL-G_cc"),
            AnswerOption("cc_none", "No cough", next="WTL-G_cc"),
        ],
        default_next="WTL-G_cc", unknown_option="cc_unknown", **_nu(0.03)
    ),
    "WTL-G_cc": GatewayNode("WTL-G_cc", "GW-WTL-URG-4", _gw_wtl_urg4_haemoptysis, next="WTL-06",
                            raisesTo="REFER_URGENT", severeConditions=["TB", "lung malignancy"]),

    "WTL-06": QuestionNode(
        nodeId="WTL-06", fieldId="polyuria_polydipsia", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pp_both", "Yes — both", next="WTL-G_pp"),
            AnswerOption("pp_urine", "Mostly frequent urination", next="WTL-G_pp"),
            AnswerOption("pp_thirst", "Mostly thirst", next="WTL-G_pp"),
            AnswerOption("pp_no", "No", next="WTL-G_pp"),
        ],
        default_next="WTL-G_pp", unknown_option="pp_unknown", **_nu(0.03)
    ),
    "WTL-G_pp": GatewayNode("WTL-G_pp", "GW-WTL-URG-3", _gw_wtl_urg3_diabetes, next="WTL-S1",
                            raisesTo="REFER_URGENT", severeConditions=["undiagnosed diabetes"]),

    "WTL-S1": SubtreeRefNode("WTL-S1", subtree_nodes=make_tb_screen_nodes(), entry="TBS-01", returnNext="WTL-G3"),
    "WTL-G3": GatewayNode("WTL-G3", "GW-WTL-URG-1", _gw_wtl_urg1_tb, next="WTL-S2",
                          raisesTo="REFER_URGENT", severeConditions=["TB"]),
    "WTL-S2": SubtreeRefNode("WTL-S2", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="WTL-END"),
    "WTL-END": TerminalNode("WTL-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="WTL-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Weight loss clinical distribution"

_entries = []

_entries += expand_entries("WTL-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_severe_pallor": 0.02, "ds_breathless_rest": 0.01, "ds_lump_swelling": 0.02,
             "ds_fever_gt_2wk": 0.02, "ds_blood_in_cough": 0.005, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_severe_pallor": 0.08, "ds_breathless_rest": 0.04, "ds_lump_swelling": 0.06,
                "ds_fever_gt_2wk": 0.06, "ds_blood_in_cough": 0.01, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_severe_pallor": 0.20, "ds_breathless_rest": 0.12, "ds_lump_swelling": 0.15,
               "ds_fever_gt_2wk": 0.15, "ds_blood_in_cough": 0.05, "ds_unconscious": 0.01, "ds_cannot_feed": 0.03},
}, overrides={
    ("pulmonary_or_extrapulmonary_tuberculosis", "moderate"): {
        "ds_severe_pallor": 0.10, "ds_breathless_rest": 0.05, "ds_lump_swelling": 0.05,
        "ds_fever_gt_2wk": 0.35, "ds_blood_in_cough": 0.08, "ds_unconscious": 0.00, "ds_cannot_feed": 0.01
    },
    ("pulmonary_or_extrapulmonary_tuberculosis", "severe"): {
        "ds_severe_pallor": 0.25, "ds_breathless_rest": 0.20, "ds_lump_swelling": 0.10,
        "ds_fever_gt_2wk": 0.60, "ds_blood_in_cough": 0.25, "ds_unconscious": 0.01, "ds_cannot_feed": 0.05
    },
    ("unexplained_underlying_malignancy", "moderate"): {
        "ds_severe_pallor": 0.20, "ds_breathless_rest": 0.05, "ds_lump_swelling": 0.30,
        "ds_fever_gt_2wk": 0.05, "ds_blood_in_cough": 0.03, "ds_unconscious": 0.00, "ds_cannot_feed": 0.02
    },
    ("unexplained_underlying_malignancy", "severe"): {
        "ds_severe_pallor": 0.45, "ds_breathless_rest": 0.25, "ds_lump_swelling": 0.50,
        "ds_fever_gt_2wk": 0.10, "ds_blood_in_cough": 0.10, "ds_unconscious": 0.02, "ds_cannot_feed": 0.10
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WTL-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.15, "pr_same": 0.65, "pr_worse": 0.20},
    "moderate": {"pr_better": 0.05, "pr_same": 0.45, "pr_worse": 0.50},
    "severe": {"pr_better": 0.02, "pr_same": 0.18, "pr_worse": 0.80},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WTL-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.45, "pt_pharmacy_medicine": 0.35, "pt_ayush": 0.15,
        "pt_prescribed_prior": 0.25, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WTL-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"wa_lt_5": 0.70, "wa_5_10": 0.25, "wa_gt_10": 0.05},
    "moderate": {"wa_lt_5": 0.25, "wa_5_10": 0.55, "wa_gt_10": 0.20},
    "severe": {"wa_lt_5": 0.05, "wa_5_10": 0.35, "wa_gt_10": 0.60},
}, overrides={
    ("unexplained_underlying_malignancy", "severe"): {"wa_lt_5": 0.02, "wa_5_10": 0.20, "wa_gt_10": 0.78},
    ("chronic_infection_or_hiv_related", "severe"): {"wa_lt_5": 0.02, "wa_5_10": 0.25, "wa_gt_10": 0.73},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WTL-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ac_decreased": 0.50, "ac_increased": 0.10, "ac_no_change": 0.40},
    "moderate": {"ac_decreased": 0.65, "ac_increased": 0.15, "ac_no_change": 0.20},
    "severe": {"ac_decreased": 0.75, "ac_increased": 0.15, "ac_no_change": 0.10},
}, overrides={
    ("hyperthyroidism_thyrotoxicosis", "mild"): {"ac_decreased": 0.05, "ac_increased": 0.75, "ac_no_change": 0.20},
    ("hyperthyroidism_thyrotoxicosis", "moderate"): {"ac_decreased": 0.05, "ac_increased": 0.85, "ac_no_change": 0.10},
    ("hyperthyroidism_thyrotoxicosis", "severe"): {"ac_decreased": 0.10, "ac_increased": 0.80, "ac_no_change": 0.10},
    ("undiagnosed_diabetes_mellitus", "mild"): {"ac_decreased": 0.10, "ac_increased": 0.55, "ac_no_change": 0.35},
    ("undiagnosed_diabetes_mellitus", "moderate"): {"ac_decreased": 0.10, "ac_increased": 0.65, "ac_no_change": 0.25},
    ("undiagnosed_diabetes_mellitus", "severe"): {"ac_decreased": 0.15, "ac_increased": 0.65, "ac_no_change": 0.20},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WTL-05", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"cc_dry": 0.10, "cc_productive": 0.10, "cc_blood": 0.01, "cc_paroxysmal": 0.02, "cc_none": 0.77}
    for s in SEVERITIES
}, overrides={
    ("pulmonary_or_extrapulmonary_tuberculosis", "mild"): {
        "cc_dry": 0.30, "cc_productive": 0.45, "cc_blood": 0.05, "cc_paroxysmal": 0.05, "cc_none": 0.15
    },
    ("pulmonary_or_extrapulmonary_tuberculosis", "moderate"): {
        "cc_dry": 0.20, "cc_productive": 0.60, "cc_blood": 0.12, "cc_paroxysmal": 0.05, "cc_none": 0.03
    },
    ("pulmonary_or_extrapulmonary_tuberculosis", "severe"): {
        "cc_dry": 0.10, "cc_productive": 0.55, "cc_blood": 0.30, "cc_paroxysmal": 0.03, "cc_none": 0.02
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WTL-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pp_both": 0.04, "pp_urine": 0.06, "pp_thirst": 0.05, "pp_no": 0.85}
    for s in SEVERITIES
}, overrides={
    ("undiagnosed_diabetes_mellitus", "mild"): {"pp_both": 0.60, "pp_urine": 0.20, "pp_thirst": 0.15, "pp_no": 0.05},
    ("undiagnosed_diabetes_mellitus", "moderate"): {"pp_both": 0.75, "pp_urine": 0.12, "pp_thirst": 0.11, "pp_no": 0.02},
    ("undiagnosed_diabetes_mellitus", "severe"): {"pp_both": 0.85, "pp_urine": 0.08, "pp_thirst": 0.06, "pp_no": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_tb_screen_entries(
    CONDITION_IDS, SEVERITIES,
    tb_conditions=("pulmonary_or_extrapulmonary_tuberculosis",),
    source_type="IND-PROG", source="Nikshay India TB programme",
)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("pulmonary_or_extrapulmonary_tuberculosis", "chronic_infection_or_hiv_related"),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
