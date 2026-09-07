"""
drishti_v2/branches/pallor_anaemia.py
The `pallor_anaemia` branch (branch-authoring-batch-4-memo.md section 2).
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
    make_fever_qual_nodes, expand_fever_qual_entries
)

CATEGORY_ID = "pallor_anaemia"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "nutritional_iron_deficiency_anaemia": ConditionSpec(
        "nutritional_iron_deficiency_anaemia", 0.55, "IND-POP",
        "Nutritional iron deficiency anaemia (dietary deficit or menstrual loss)",
        severeConditions=("severe anaemia requiring transfusion",)
    ),
    "anaemia_of_chronic_disease_or_infection": ConditionSpec(
        "anaemia_of_chronic_disease_or_infection", 0.15, "IND-POP",
        "Anaemia of chronic inflammation, renal failure, or chronic infection"
    ),
    "hookworm_or_intestinal_helminthiasis_anaemia": ConditionSpec(
        "hookworm_or_intestinal_helminthiasis_anaemia", 0.10, "IND-POP",
        "Microcytic hypochromic anaemia secondary to chronic hookworm blood loss",
        severeConditions=("hookworm",)
    ),
    "haemoglobinopathy_thalassemia_or_sickle_cell": ConditionSpec(
        "haemoglobinopathy_thalassemia_or_sickle_cell", 0.08, "IND-POP",
        "Inherited haemoglobinopathy (beta thalassemia trait/major, sickle cell trait/disease)",
        severeConditions=("haemoglobinopathy",)
    ),
    "occult_gastrointestinal_bleeding_anaemia": ConditionSpec(
        "occult_gastrointestinal_bleeding_anaemia", 0.07, "IND-POP",
        "Chronic occult GI blood loss from ulcer, polyp, or malignancy",
        severeConditions=("occult GI bleeding",)
    ),
    "haematological_malignancy_or_aplasia": ConditionSpec(
        "haematological_malignancy_or_aplasia", 0.05, "IND-POP",
        "Bone marrow failure, leukaemia, or aplastic anaemia",
        severeConditions=("malignancy",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "nutritional_iron_deficiency_anaemia": {"mild": 0.45, "moderate": 0.40, "severe": 0.15},
    "anaemia_of_chronic_disease_or_infection": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "hookworm_or_intestinal_helminthiasis_anaemia": {"mild": 0.35, "moderate": 0.45, "severe": 0.20},
    "haemoglobinopathy_thalassemia_or_sickle_cell": {"mild": 0.30, "moderate": 0.45, "severe": 0.25},
    "occult_gastrointestinal_bleeding_anaemia": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "haematological_malignancy_or_aplasia": {"mild": 0.10, "moderate": 0.40, "severe": 0.50},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]

    if severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 22, 9.0, 40, 220)
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + 4, 2.5, 10, 50)
    elif severity_band == "moderate":
        specs["pulse"] = VitalSpec(base_pulse.mean + 10, 7.0, 40, 200)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_pal_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_pal_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_bleeding_now")

def _gw_pal_emg3(fields, ctx):
    return (
        contains(fields, "danger_signs", "ds_severe_pallor")
        and contains(fields, "danger_signs", "ds_breathless_rest")
    )

def _gw_pal_emg4(fields, ctx):
    age_band = ctx.get("age_band", "")
    return (
        age_band in ("infant", "child")
        and contains(fields, "danger_signs", "ds_cannot_feed")
    )

def _gw_pal_urg2_pulse(fields, ctx):
    return contains(fields, "danger_signs", "ds_rapid_pulse")

def _gw_pal_urg1_gibleed(fields, ctx):
    bs = value_of(fields, "blood_in_stool")
    return (bs in ("bs_frank", "bs_black")) or contains(fields, "danger_signs", "ds_black_tarry")

def _gw_pal_urg3_malaria(fields, ctx):
    return equals(fields, "fever_present", "fp_yes")

_NODES = {
    "PAL-00": QuestionNode(
        nodeId="PAL-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_severe_pallor", "Palms, nails and inside of eyelids are very white", next="PAL-G1a"),
            AnswerOption("ds_breathless_rest", "Breathless at rest", next="PAL-G1a"),
            AnswerOption("ds_rapid_pulse", "Pulse very fast (more than 120)", next="PAL-G1a"),
            AnswerOption("ds_bleeding_now", "Bleeding from any site right now", next="PAL-G1a"),
            AnswerOption("ds_black_tarry", "Black or tarry stools", next="PAL-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="PAL-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="PAL-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="PAL-G1a"),
            AnswerOption("ds_none", "None of these", next="PAL-01"),
        ],
        default_next="PAL-G1a", none_option="ds_none", unknown_option="ds_unknown", **_nu(0.01)
    ),
    "PAL-G1a": GatewayNode("PAL-G1a", "GW-PAL-EMG-1", _gw_pal_emg1, next="PAL-G1b",
                           routeTo="emergency_unconscious"),
    "PAL-G1b": GatewayNode("PAL-G1b", "GW-PAL-EMG-2", _gw_pal_emg2, next="PAL-G1c",
                           routeTo="emergency_heavy_bleeding"),
    "PAL-G1c": GatewayNode("PAL-G1c", "GW-PAL-EMG-3", _gw_pal_emg3, next="PAL-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["severe anaemia requiring transfusion"]),
    "PAL-G1d": GatewayNode("PAL-G1d", "GW-PAL-EMG-4", _gw_pal_emg4, next="PAL-G1e",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),
    "PAL-G1e": GatewayNode("PAL-G1e", "GW-PAL-URG-2", _gw_pal_urg2_pulse, next="PAL-01",
                           raisesTo="REFER_URGENT", severeConditions=["haemodynamic compromise"]),

    "PAL-01": QuestionNode(
        nodeId="PAL-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Getting better", next="PAL-02"),
            AnswerOption("pr_same", "About the same", next="PAL-02"),
            AnswerOption("pr_worse", "Getting worse", next="PAL-02"),
        ],
        default_next="PAL-02", unknown_option="pr_unknown", **_nu(0.02)
    ),
    "PAL-02": QuestionNode(
        nodeId="PAL-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies", next="PAL-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy / shop", next="PAL-03"),
            AnswerOption("pt_ayush", "Ayurvedic / homeopathic / traditional medicine", next="PAL-03"),
            AnswerOption("pt_prescribed_prior", "Prescription medicine from another doctor", next="PAL-03"),
            AnswerOption("pt_other", "Other treatment", next="PAL-03"),
            AnswerOption("pt_none", "No prior treatment", next="PAL-03"),
        ],
        default_next="PAL-03", none_option="pt_none", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "PAL-03": QuestionNode(
        nodeId="PAL-03", fieldId="pallor_site_observed", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("po_palms", "Palms are pale", next="PAL-04"),
            AnswerOption("po_nails", "Nail beds are pale", next="PAL-04"),
            AnswerOption("po_conjunctiva", "Inside of lower eyelid is pale", next="PAL-04"),
            AnswerOption("po_tongue", "Tongue is pale", next="PAL-04"),
            AnswerOption("po_face", "Face looks pale", next="PAL-04"),
            AnswerOption("po_none", "None of these — family reports pallor", next="PAL-04"),
        ],
        default_next="PAL-04", none_option="po_none", unknown_option="po_unknown", **_nu(0.02)
    ),
    "PAL-04": QuestionNode(
        nodeId="PAL-04", fieldId="pica", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pi_yes", "Yes", next="PAL-05"),
            AnswerOption("pi_no", "No", next="PAL-05"),
        ],
        default_next="PAL-05", unknown_option="pi_unknown", **_nu(0.03)
    ),
    "PAL-05": QuestionNode(
        nodeId="PAL-05", fieldId="heavy_menstrual_bleeding", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hm_yes", "Yes — heavy or prolonged", next="PAL-06"),
            AnswerOption("hm_no", "No", next="PAL-06"),
        ],
        default_next="PAL-06", unknown_option="hm_unknown", **_nu(0.03)
    ),
    "PAL-06": QuestionNode(
        nodeId="PAL-06", fieldId="blood_in_stool", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bs_frank", "Bright red blood", next="PAL-G2"),
            AnswerOption("bs_streaks", "Streaks of blood", next="PAL-G2"),
            AnswerOption("bs_black", "Black / dark sticky stool", next="PAL-G2"),
            AnswerOption("bs_no", "No blood in stool", next="PAL-G2"),
        ],
        default_next="PAL-G2", unknown_option="bs_unknown", **_nu(0.03)
    ),
    "PAL-G2": GatewayNode("PAL-G2", "GW-PAL-URG-1", _gw_pal_urg1_gibleed, next="PAL-07",
                          raisesTo="REFER_URGENT", severeConditions=["occult GI bleeding"]),

    "PAL-07": QuestionNode(
        nodeId="PAL-07", fieldId="worm_treatment_history", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("wt_yes", "Yes", next="PAL-08"),
            AnswerOption("wt_no", "No", next="PAL-08"),
        ],
        default_next="PAL-08", unknown_option="wt_unknown", **_nu(0.03)
    ),
    "PAL-08": QuestionNode(
        nodeId="PAL-08", fieldId="dietary_pattern", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("dp_mixed", "Mixed — includes meat, eggs, fish", next="PAL-09"),
            AnswerOption("dp_vegetarian", "Vegetarian — milk, dal, vegetables", next="PAL-09"),
            AnswerOption("dp_restricted", "Very limited — mostly rice/roti only", next="PAL-09"),
        ],
        default_next="PAL-09", unknown_option="dp_unknown", **_nu(0.03)
    ),
    "PAL-09": QuestionNode(
        nodeId="PAL-09", fieldId="appetite_change", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ac_decreased", "Decreased", next="PAL-S1"),
            AnswerOption("ac_increased", "Increased", next="PAL-S1"),
            AnswerOption("ac_no_change", "No change", next="PAL-S1"),
        ],
        default_next="PAL-S1", unknown_option="ac_unknown", **_nu(0.03)
    ),

    "PAL-S1": SubtreeRefNode("PAL-S1", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="PAL-G3"),
    "PAL-G3": GatewayNode("PAL-G3", "GW-PAL-URG-3", _gw_pal_urg3_malaria, next="PAL-END",
                          raisesTo="REFER_URGENT", severeConditions=["malaria with anaemia"]),
    "PAL-END": TerminalNode("PAL-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="PAL-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Pallor anaemia clinical distribution"

_entries = []

_entries += expand_entries("PAL-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_severe_pallor": 0.05, "ds_breathless_rest": 0.01, "ds_rapid_pulse": 0.02,
             "ds_bleeding_now": 0.005, "ds_black_tarry": 0.01, "ds_confusion": 0.001, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_severe_pallor": 0.20, "ds_breathless_rest": 0.05, "ds_rapid_pulse": 0.10,
                "ds_bleeding_now": 0.01, "ds_black_tarry": 0.03, "ds_confusion": 0.005, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_severe_pallor": 0.70, "ds_breathless_rest": 0.35, "ds_rapid_pulse": 0.40,
               "ds_bleeding_now": 0.05, "ds_black_tarry": 0.10, "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, overrides={
    ("occult_gastrointestinal_bleeding_anaemia", "moderate"): {
        "ds_severe_pallor": 0.25, "ds_breathless_rest": 0.05, "ds_rapid_pulse": 0.10,
        "ds_bleeding_now": 0.05, "ds_black_tarry": 0.40, "ds_confusion": 0.00, "ds_unconscious": 0.00, "ds_cannot_feed": 0.01
    },
    ("occult_gastrointestinal_bleeding_anaemia", "severe"): {
        "ds_severe_pallor": 0.75, "ds_breathless_rest": 0.40, "ds_rapid_pulse": 0.45,
        "ds_bleeding_now": 0.15, "ds_black_tarry": 0.70, "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.20, "pr_same": 0.65, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.10, "pr_same": 0.55, "pr_worse": 0.35},
    "severe": {"pr_better": 0.02, "pr_same": 0.28, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.35, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.20, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-03", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"po_palms": 0.35, "po_nails": 0.45, "po_conjunctiva": 0.50, "po_tongue": 0.20, "po_face": 0.25},
    "moderate": {"po_palms": 0.65, "po_nails": 0.75, "po_conjunctiva": 0.80, "po_tongue": 0.45, "po_face": 0.50},
    "severe": {"po_palms": 0.90, "po_nails": 0.95, "po_conjunctiva": 0.95, "po_tongue": 0.80, "po_face": 0.85},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pi_yes": 0.05, "pi_no": 0.95},
    "moderate": {"pi_yes": 0.15, "pi_no": 0.85},
    "severe": {"pi_yes": 0.30, "pi_no": 0.70},
}, overrides={
    ("nutritional_iron_deficiency_anaemia", "moderate"): {"pi_yes": 0.30, "pi_no": 0.70},
    ("nutritional_iron_deficiency_anaemia", "severe"): {"pi_yes": 0.55, "pi_no": 0.45},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-05", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"hm_yes": 0.25, "hm_no": 0.75}
    for s in SEVERITIES
}, overrides={
    ("nutritional_iron_deficiency_anaemia", "moderate"): {"hm_yes": 0.50, "hm_no": 0.50},
    ("nutritional_iron_deficiency_anaemia", "severe"): {"hm_yes": 0.65, "hm_no": 0.35},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"bs_frank": 0.01, "bs_streaks": 0.02, "bs_black": 0.01, "bs_no": 0.96}
    for s in SEVERITIES
}, overrides={
    ("occult_gastrointestinal_bleeding_anaemia", "mild"): {"bs_frank": 0.05, "bs_streaks": 0.10, "bs_black": 0.40, "bs_no": 0.45},
    ("occult_gastrointestinal_bleeding_anaemia", "moderate"): {"bs_frank": 0.10, "bs_streaks": 0.10, "bs_black": 0.65, "bs_no": 0.15},
    ("occult_gastrointestinal_bleeding_anaemia", "severe"): {"bs_frank": 0.15, "bs_streaks": 0.05, "bs_black": 0.75, "bs_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"wt_yes": 0.35, "wt_no": 0.65}
    for s in SEVERITIES
}, overrides={
    ("hookworm_or_intestinal_helminthiasis_anaemia", "mild"): {"wt_yes": 0.05, "wt_no": 0.95},
    ("hookworm_or_intestinal_helminthiasis_anaemia", "moderate"): {"wt_yes": 0.02, "wt_no": 0.98},
    ("hookworm_or_intestinal_helminthiasis_anaemia", "severe"): {"wt_yes": 0.01, "wt_no": 0.99},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"dp_mixed": 0.30, "dp_vegetarian": 0.50, "dp_restricted": 0.20}
    for s in SEVERITIES
}, overrides={
    ("nutritional_iron_deficiency_anaemia", "moderate"): {"dp_mixed": 0.15, "dp_vegetarian": 0.55, "dp_restricted": 0.30},
    ("nutritional_iron_deficiency_anaemia", "severe"): {"dp_mixed": 0.05, "dp_vegetarian": 0.50, "dp_restricted": 0.45},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("PAL-09", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ac_decreased": 0.25, "ac_increased": 0.05, "ac_no_change": 0.70},
    "moderate": {"ac_decreased": 0.45, "ac_increased": 0.05, "ac_no_change": 0.50},
    "severe": {"ac_decreased": 0.70, "ac_increased": 0.02, "ac_no_change": 0.28},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=(),
    bleeding_conditions=("haematological_malignancy_or_aplasia",),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
