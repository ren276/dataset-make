"""
drishti_v2/branches/weakness_unwell.py
The `weakness_unwell` branch (branch-authoring-batch-3-memo.md section 6).
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

CATEGORY_ID = "weakness_unwell"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "nutritional_iron_deficiency_anaemia": ConditionSpec("nutritional_iron_deficiency_anaemia", 0.45, "IND-POP",
        "Nutritional iron deficiency anaemia", severeConditions=("anaemia (severe)",)),
    "post_viral_asthenia_or_chronic_fatigue": ConditionSpec("post_viral_asthenia_or_chronic_fatigue", 0.25, "IND-PRESENT",
        "Post-viral debility or functional fatigue state"),
    "depressive_disorder_somatic_fatigue": ConditionSpec("depressive_disorder_somatic_fatigue", 0.12, "IND-PRESENT",
        "Depression presenting with somatic fatigue / weakness", severeConditions=("depression",)),
    "undiagnosed_type2_diabetes_weakness": ConditionSpec("undiagnosed_type2_diabetes_weakness", 0.08, "IND-POP",
        "Unrecognised diabetes presenting with lethargy", severeConditions=("diabetes",)),
    "hypothyroidism_fatigue": ConditionSpec("hypothyroidism_fatigue", 0.05, "IND-POP",
        "Primary hypothyroidism presenting as weakness", severeConditions=("hypothyroidism",)),
    "tuberculosis_constitutional_debility": ConditionSpec("tuberculosis_constitutional_debility", 0.05, "IND-PROG",
        "Disseminated or pulmonary TB presenting as constitutional weakness", severeConditions=("TB",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "nutritional_iron_deficiency_anaemia": {"mild": 0.50, "moderate": 0.35, "severe": 0.15},
    "post_viral_asthenia_or_chronic_fatigue": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
    "depressive_disorder_somatic_fatigue": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "undiagnosed_type2_diabetes_weakness": {"mild": 0.35, "moderate": 0.50, "severe": 0.15},
    "hypothyroidism_fatigue": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "tuberculosis_constitutional_debility": {"mild": 0.15, "moderate": 0.50, "severe": 0.35},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    if condition_id == "nutritional_iron_deficiency_anaemia" and severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 20, 10.0, 35, 220)
    elif condition_id == "tuberculosis_constitutional_debility":
        specs["temperature"] = VitalSpec(base_temp.mean + 0.8, 0.4, 34, 41)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_wkn_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_wkn_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_severe_pallor") and contains(fields, "danger_signs", "ds_breathless_rest")

def _gw_wkn_emg3(fields, ctx):
    return equals(fields, "weakness_generalised_or_focal", "wg_one_side")

def _gw_wkn_emg4_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_wkn_urg1_pallor(fields, ctx):
    return contains(fields, "danger_signs", "ds_severe_pallor")

def _gw_wkn_urg2_tb(fields, ctx):
    return equals(fields, "tb_contact", "tbc_yes") or equals(fields, "cough_ge_2_weeks", "c2_yes") or equals(fields, "weight_loss_present", "wl_yes") or equals(fields, "night_sweats", "ns_yes")

def _gw_wkn_urg3_diabetes(fields, ctx):
    return equals(fields, "polyuria_polydipsia", "pp_both")

_NODES = {
    "WKN-00": QuestionNode(
        nodeId="WKN-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_severe_pallor", "Very pale — palms, conjunctivae, or tongue white", next="WKN-G1a"),
            AnswerOption("ds_breathless_rest", "Breathless even when sitting still", next="WKN-G1a"),
            AnswerOption("ds_chest_pain", "Chest pain or heaviness", next="WKN-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="WKN-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="WKN-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="WKN-G1a"),
        ],
        default_next="WKN-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "WKN-G1a": GatewayNode("WKN-G1a", "GW-WKN-EMG-1", _gw_wkn_emg1, next="WKN-G1b",
                           routeTo="emergency_unconscious", severeConditions=["hypoglycaemia", "severe anaemia", "sepsis"]),
    "WKN-G1b": GatewayNode("WKN-G1b", "GW-WKN-EMG-2", _gw_wkn_emg2, next="WKN-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["severe anaemia requiring transfusion"]),
    "WKN-G1c": GatewayNode("WKN-G1c", "GW-WKN-EMG-4", _gw_wkn_emg4_infant, next="WKN-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),
    "WKN-G1d": GatewayNode("WKN-G1d", "GW-WKN-URG-1", _gw_wkn_urg1_pallor, next="WKN-01",
                           raisesTo="REFER_URGENT", severeConditions=["moderate-to-severe anaemia"]),

    "WKN-01": QuestionNode(
        nodeId="WKN-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="WKN-02"),
            AnswerOption("pr_same", "About the same", next="WKN-02"),
            AnswerOption("pr_worse", "Worse", next="WKN-02"),
        ],
        default_next="WKN-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "WKN-02": QuestionNode(
        nodeId="WKN-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="WKN-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="WKN-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="WKN-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="WKN-03"),
            AnswerOption("pt_other", "Other treatment", next="WKN-03"),
        ],
        default_next="WKN-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "WKN-03": QuestionNode(
        nodeId="WKN-03", fieldId="weakness_generalised_or_focal", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("wg_generalised", "All over — general tiredness", next="WKN-04"),
            AnswerOption("wg_one_side", "One side of the body — arm or leg", next="WKN-04"),
            AnswerOption("wg_one_limb", "One arm or leg", next="WKN-04"),
        ],
        default_next="WKN-04", unknown_option="wg_unknown", **_nu(0.03)
    ),
    "WKN-04": QuestionNode(
        nodeId="WKN-04", fieldId="appetite_change", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ac_decreased", "Eating much less than before", next="WKN-05"),
            AnswerOption("ac_increased", "Eating more than before", next="WKN-05"),
            AnswerOption("ac_no_change", "No change", next="WKN-05"),
        ],
        default_next="WKN-05", unknown_option="ac_unknown", **_nu(0.03)
    ),
    "WKN-05": QuestionNode(
        nodeId="WKN-05", fieldId="polyuria_polydipsia", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pp_both", "Yes — both", next="WKN-06"),
            AnswerOption("pp_urine", "Mostly frequent urination", next="WKN-06"),
            AnswerOption("pp_thirst", "Mostly thirst", next="WKN-06"),
            AnswerOption("pp_no", "No", next="WKN-06"),
        ],
        default_next="WKN-06", unknown_option="pp_unknown", **_nu(0.03)
    ),
    "WKN-06": QuestionNode(
        nodeId="WKN-06", fieldId="mood_change", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("mc_sad_hopeless", "Yes — sad, hopeless, or crying", next="WKN-07"),
            AnswerOption("mc_anxious", "Anxious, worried, or unable to relax", next="WKN-07"),
            AnswerOption("mc_irritable", "Irritable", next="WKN-07"),
            AnswerOption("mc_no", "No change", next="WKN-07"),
        ],
        default_next="WKN-07", unknown_option="mc_unknown", **_nu(0.03)
    ),
    "WKN-07": QuestionNode(
        nodeId="WKN-07", fieldId="sleep_change", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("sc_insomnia", "Cannot sleep, or wakes too early", next="WKN-S1"),
            AnswerOption("sc_excessive", "Sleeping much more than usual", next="WKN-S1"),
            AnswerOption("sc_no_change", "No change", next="WKN-S1"),
        ],
        default_next="WKN-S1", unknown_option="sc_unknown", **_nu(0.03)
    ),

    "WKN-S1": SubtreeRefNode("WKN-S1", subtree_nodes=make_tb_screen_nodes(), entry="TBS-01", returnNext="WKN-G2"),
    "WKN-G2": GatewayNode("WKN-G2", "GW-WKN-URG-2", _gw_wkn_urg2_tb, next="WKN-S2",
                          raisesTo="REFER_URGENT", severeConditions=["TB"]),
    "WKN-S2": SubtreeRefNode("WKN-S2", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="WKN-G3a"),
    "WKN-G3a": GatewayNode("WKN-G3a", "GW-WKN-EMG-3", _gw_wkn_emg3, next="WKN-G3b",
                           raisesTo="REFER_EMERGENCY", severeConditions=["stroke", "space-occupying lesion"]),
    "WKN-G3b": GatewayNode("WKN-G3b", "GW-WKN-URG-3", _gw_wkn_urg3_diabetes, next="WKN-END",
                           raisesTo="REFER_URGENT", severeConditions=["undiagnosed diabetes"]),
    "WKN-END": TerminalNode("WKN-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="WKN-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Weakness unwell clinical distribution"

_entries = []

_entries += expand_entries("WKN-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_severe_pallor": 0.02, "ds_breathless_rest": 0.01, "ds_chest_pain": 0.01,
             "ds_confusion": 0.001, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_severe_pallor": 0.08, "ds_breathless_rest": 0.03, "ds_chest_pain": 0.03,
                "ds_confusion": 0.005, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_severe_pallor": 0.25, "ds_breathless_rest": 0.15, "ds_chest_pain": 0.10,
               "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, overrides={
    ("nutritional_iron_deficiency_anaemia", "moderate"): {"ds_severe_pallor": 0.40, "ds_breathless_rest": 0.10, "ds_chest_pain": 0.05,
                                                         "ds_confusion": 0.00, "ds_unconscious": 0.00, "ds_cannot_feed": 0.01},
    ("nutritional_iron_deficiency_anaemia", "severe"): {"ds_severe_pallor": 0.85, "ds_breathless_rest": 0.65, "ds_chest_pain": 0.20,
                                                       "ds_confusion": 0.05, "ds_unconscious": 0.05, "ds_cannot_feed": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WKN-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WKN-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.20, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WKN-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"wg_generalised": 0.88, "wg_one_side": 0.04, "wg_one_limb": 0.08}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WKN-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ac_decreased": 0.25, "ac_increased": 0.05, "ac_no_change": 0.70},
    "moderate": {"ac_decreased": 0.45, "ac_increased": 0.10, "ac_no_change": 0.45},
    "severe": {"ac_decreased": 0.65, "ac_increased": 0.10, "ac_no_change": 0.25},
}, overrides={
    ("tuberculosis_constitutional_debility", "moderate"): {"ac_decreased": 0.75, "ac_increased": 0.01, "ac_no_change": 0.24},
    ("tuberculosis_constitutional_debility", "severe"): {"ac_decreased": 0.90, "ac_increased": 0.01, "ac_no_change": 0.09},
    ("undiagnosed_type2_diabetes_weakness", "moderate"): {"ac_decreased": 0.10, "ac_increased": 0.55, "ac_no_change": 0.35},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WKN-05", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pp_both": 0.05, "pp_urine": 0.10, "pp_thirst": 0.10, "pp_no": 0.75}
    for s in SEVERITIES
}, overrides={
    ("undiagnosed_type2_diabetes_weakness", "moderate"): {"pp_both": 0.65, "pp_urine": 0.15, "pp_thirst": 0.15, "pp_no": 0.05},
    ("undiagnosed_type2_diabetes_weakness", "severe"): {"pp_both": 0.80, "pp_urine": 0.10, "pp_thirst": 0.08, "pp_no": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WKN-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"mc_sad_hopeless": 0.15, "mc_anxious": 0.15, "mc_irritable": 0.10, "mc_no": 0.60},
    "moderate": {"mc_sad_hopeless": 0.25, "mc_anxious": 0.20, "mc_irritable": 0.15, "mc_no": 0.40},
    "severe": {"mc_sad_hopeless": 0.35, "mc_anxious": 0.25, "mc_irritable": 0.15, "mc_no": 0.25},
}, overrides={
    ("depressive_disorder_somatic_fatigue", "moderate"): {"mc_sad_hopeless": 0.75, "mc_anxious": 0.15, "mc_irritable": 0.05, "mc_no": 0.05},
    ("depressive_disorder_somatic_fatigue", "severe"): {"mc_sad_hopeless": 0.85, "mc_anxious": 0.10, "mc_irritable": 0.03, "mc_no": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("WKN-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"sc_insomnia": 0.20, "sc_excessive": 0.10, "sc_no_change": 0.70},
    "moderate": {"sc_insomnia": 0.35, "sc_excessive": 0.15, "sc_no_change": 0.50},
    "severe": {"sc_insomnia": 0.50, "sc_excessive": 0.20, "sc_no_change": 0.30},
}, overrides={
    ("depressive_disorder_somatic_fatigue", "moderate"): {"sc_insomnia": 0.70, "sc_excessive": 0.20, "sc_no_change": 0.10},
    ("depressive_disorder_somatic_fatigue", "severe"): {"sc_insomnia": 0.80, "sc_excessive": 0.15, "sc_no_change": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_tb_screen_entries(
    CONDITION_IDS, SEVERITIES,
    tb_conditions=("tuberculosis_constitutional_debility",),
    source_type="IND-PROG", source="Nikshay India TB programme",
)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("tuberculosis_constitutional_debility",),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
