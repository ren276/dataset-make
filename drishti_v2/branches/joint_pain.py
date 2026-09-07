"""
drishti_v2/branches/joint_pain.py
The `joint_pain` branch (branch-authoring-batch-2-memo.md section 2).
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

CATEGORY_ID = "joint_pain"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "osteoarthritis": ConditionSpec("osteoarthritis", 0.50, "IND-POP",
        "Osteoarthritis / degenerative joint disease"),
    "rheumatoid_or_inflammatory_arthritis": ConditionSpec("rheumatoid_or_inflammatory_arthritis", 0.18, "IND-PRESENT",
        "Rheumatoid arthritis / inflammatory polyarthritis"),
    "gout_crystal_arthritis": ConditionSpec("gout_crystal_arthritis", 0.12, "IND-PRESENT",
        "Acute or chronic gout / crystal arthritis", severeConditions=("gout",)),
    "chikungunya_or_viral_arthritis": ConditionSpec("chikungunya_or_viral_arthritis", 0.10, "IND-PRESENT",
        "Post-viral / chikungunya arthritis", severeConditions=("chikungunya",)),
    "septic_arthritis": ConditionSpec("septic_arthritis", 0.05, "ASSUMED",
        "Acute septic arthritis", severeConditions=("septic arthritis",)),
    "tb_of_joint": ConditionSpec("tb_of_joint", 0.05, "IND-PROG",
        "Tuberculous arthritis / cold abscess", severeConditions=("TB of joint",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "osteoarthritis": {"mild": 0.55, "moderate": 0.35, "severe": 0.10},
    "rheumatoid_or_inflammatory_arthritis": {"mild": 0.30, "moderate": 0.50, "severe": 0.20},
    "gout_crystal_arthritis": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "chikungunya_or_viral_arthritis": {"mild": 0.25, "moderate": 0.55, "severe": 0.20},
    "septic_arthritis": {"mild": 0.05, "moderate": 0.30, "severe": 0.65},
    "tb_of_joint": {"mild": 0.25, "moderate": 0.50, "severe": 0.25},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    if condition_id == "septic_arthritis":
        specs["temperature"] = VitalSpec(base_temp.mean + (1.5 if severity_band != "severe" else 2.3), 0.4, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + (15 if severity_band != "severe" else 30), base_pulse.sd, 35, 220)
    elif condition_id in ("chikungunya_or_viral_arthritis", "tb_of_joint"):
        specs["temperature"] = VitalSpec(base_temp.mean + 1.0, 0.4, 34, 41)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_jpn_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_jpn_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_hot_red_swollen") and contains(fields, "danger_signs", "ds_high_fever_joint")

def _gw_jpn_emg3(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_jpn_urg1_septic(fields, ctx):
    return equals(fields, "joint_swelling", "js_yes_hot") or (
        equals(fields, "joints_involved", "ji_one_large") and equals(fields, "fever_present", "fp_yes")
    )

def _gw_jpn_urg2_rheumatic(fields, ctx):
    return equals(fields, "migratory_pattern", "mp_migratory") and equals(fields, "fever_present", "fp_yes")

def _gw_jpn_urg3_tb(fields, ctx):
    return equals(fields, "tb_contact", "tbc_yes") or (
        value_of(fields, "duration_bucket") in ("month_plus", "chronic") and equals(fields, "joint_swelling", "js_yes_cold")
    )

_NODES = {
    "JPN-00": QuestionNode(
        nodeId="JPN-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_hot_red_swollen", "One joint is very hot, red and swollen", next="JPN-G1a"),
            AnswerOption("ds_cannot_bear_weight", "Cannot put any weight on the leg", next="JPN-G1a"),
            AnswerOption("ds_high_fever_joint", "High fever with the joint pain", next="JPN-G1a"),
            AnswerOption("ds_joint_deformity", "Obvious deformity of a limb or joint", next="JPN-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="JPN-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="JPN-G1a"),
        ],
        default_next="JPN-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "JPN-G1a": GatewayNode("JPN-G1a", "GW-JPN-EMG-1", _gw_jpn_emg1, next="JPN-G1b",
                           routeTo="emergency_unconscious", severeConditions=["sepsis", "meningococcaemia"]),
    "JPN-G1b": GatewayNode("JPN-G1b", "GW-JPN-EMG-2", _gw_jpn_emg2, next="JPN-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["septic arthritis", "gonococcal arthritis"]),
    "JPN-G1c": GatewayNode("JPN-G1c", "GW-JPN-EMG-3", _gw_jpn_emg3, next="JPN-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "JPN-01": QuestionNode(
        nodeId="JPN-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="JPN-02"),
            AnswerOption("pr_same", "About the same", next="JPN-02"),
            AnswerOption("pr_worse", "Worse", next="JPN-02"),
        ],
        default_next="JPN-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "JPN-02": QuestionNode(
        nodeId="JPN-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="JPN-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="JPN-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="JPN-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="JPN-03"),
            AnswerOption("pt_other", "Other treatment", next="JPN-03"),
        ],
        default_next="JPN-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "JPN-03": QuestionNode(
        nodeId="JPN-03", fieldId="joints_involved", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ji_one_large", "One large joint (knee, hip, shoulder, elbow, ankle)", next="JPN-04"),
            AnswerOption("ji_few_large", "A few large joints", next="JPN-04"),
            AnswerOption("ji_small_hands", "Small joints of the hands or feet", next="JPN-04"),
            AnswerOption("ji_many_both", "Many joints — both large and small", next="JPN-04"),
            AnswerOption("ji_spine", "The back or neck, not a limb joint", next="JPN-04"),
        ],
        default_next="JPN-04", unknown_option="ji_unknown", **_nu(0.03)
    ),
    "JPN-04": QuestionNode(
        nodeId="JPN-04", fieldId="joint_swelling", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("js_yes_hot", "Yes — swollen and hot or red", next="JPN-05"),
            AnswerOption("js_yes_cold", "Yes — swollen but not hot", next="JPN-05"),
            AnswerOption("js_no", "No swelling seen", next="JPN-05"),
        ],
        default_next="JPN-05", unknown_option="js_unknown", **_nu(0.03)
    ),
    "JPN-05": QuestionNode(
        nodeId="JPN-05", fieldId="morning_stiffness", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ms_gt_30min", "Yes — stiffness lasts more than 30 minutes", next="JPN-06"),
            AnswerOption("ms_lt_30min", "Yes — stiffness lasts less than 30 minutes", next="JPN-06"),
            AnswerOption("ms_no", "No morning stiffness", next="JPN-06"),
        ],
        default_next="JPN-06", unknown_option="ms_unknown", **_nu(0.03)
    ),
    "JPN-06": QuestionNode(
        nodeId="JPN-06", fieldId="pain_on_weight_bearing", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pw_yes", "Yes — worse on weight bearing", next="JPN-07"),
            AnswerOption("pw_no", "No — worse at rest or at night", next="JPN-07"),
            AnswerOption("pw_both", "Both", next="JPN-07"),
        ],
        default_next="JPN-07", unknown_option="pw_unknown", **_nu(0.03)
    ),
    "JPN-07": QuestionNode(
        nodeId="JPN-07", fieldId="migratory_pattern", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("mp_migratory", "Yes — one joint gets better as another starts", next="JPN-08"),
            AnswerOption("mp_additive", "No — more joints are added without the first getting better", next="JPN-08"),
            AnswerOption("mp_fixed", "Stays in the same joint(s)", next="JPN-08"),
        ],
        default_next="JPN-08", unknown_option="mp_unknown", **_nu(0.03)
    ),
    "JPN-08": QuestionNode(
        nodeId="JPN-08", fieldId="recent_injury_to_joint", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ri_yes", "Yes", next="JPN-S1"),
            AnswerOption("ri_no", "No", next="JPN-S1"),
        ],
        default_next="JPN-S1", unknown_option="ri_unknown", **_nu(0.03)
    ),

    "JPN-S1": SubtreeRefNode("JPN-S1", subtree_nodes=make_tb_screen_nodes(), entry="TBS-01", returnNext="JPN-G3"),
    "JPN-G3": GatewayNode("JPN-G3", "GW-JPN-URG-3", _gw_jpn_urg3_tb, next="JPN-S2",
                          raisesTo="REFER_URGENT", severeConditions=["TB of joint", "chronic osteomyelitis"]),
    "JPN-S2": SubtreeRefNode("JPN-S2", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="JPN-G2"),
    "JPN-G2": GatewayNode("JPN-G2", "GW-JPN-URG-1", _gw_jpn_urg1_septic, next="JPN-G4",
                          raisesTo="REFER_URGENT", severeConditions=["septic arthritis", "crystal arthritis (acute gout)"]),
    "JPN-G4": GatewayNode("JPN-G4", "GW-JPN-URG-2", _gw_jpn_urg2_rheumatic, next="JPN-END",
                          raisesTo="REFER_URGENT", severeConditions=["acute rheumatic fever", "chikungunya", "gonococcal arthritis"]),
    "JPN-END": TerminalNode("JPN-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="JPN-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Joint pain clinical distribution"

_entries = []

_entries += expand_entries("JPN-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_hot_red_swollen": 0.01, "ds_cannot_bear_weight": 0.03, "ds_high_fever_joint": 0.01,
             "ds_joint_deformity": 0.02, "ds_unconscious": 0.001, "ds_cannot_feed": 0.005},
    "moderate": {"ds_hot_red_swollen": 0.05, "ds_cannot_bear_weight": 0.15, "ds_high_fever_joint": 0.05,
                "ds_joint_deformity": 0.08, "ds_unconscious": 0.005, "ds_cannot_feed": 0.01},
    "severe": {"ds_hot_red_swollen": 0.20, "ds_cannot_bear_weight": 0.45, "ds_high_fever_joint": 0.20,
               "ds_joint_deformity": 0.18, "ds_unconscious": 0.03, "ds_cannot_feed": 0.05},
}, overrides={
    ("septic_arthritis", "severe"): {"ds_hot_red_swollen": 0.85, "ds_cannot_bear_weight": 0.80, "ds_high_fever_joint": 0.75,
                                    "ds_joint_deformity": 0.05, "ds_unconscious": 0.08, "ds_cannot_feed": 0.05},
    ("gout_crystal_arthritis", "severe"): {"ds_hot_red_swollen": 0.75, "ds_cannot_bear_weight": 0.70, "ds_high_fever_joint": 0.20,
                                          "ds_joint_deformity": 0.15, "ds_unconscious": 0.01, "ds_cannot_feed": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.30, "pr_same": 0.55, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.45, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.15,
        "pt_prescribed_prior": 0.25, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ji_one_large": 0.40, "ji_few_large": 0.25, "ji_small_hands": 0.15, "ji_many_both": 0.10, "ji_spine": 0.10},
    "moderate": {"ji_one_large": 0.35, "ji_few_large": 0.25, "ji_small_hands": 0.18, "ji_many_both": 0.12, "ji_spine": 0.10},
    "severe": {"ji_one_large": 0.30, "ji_few_large": 0.25, "ji_small_hands": 0.20, "ji_many_both": 0.15, "ji_spine": 0.10},
}, overrides={
    ("osteoarthritis", "moderate"): {"ji_one_large": 0.60, "ji_few_large": 0.25, "ji_small_hands": 0.05, "ji_many_both": 0.05, "ji_spine": 0.05},
    ("rheumatoid_or_inflammatory_arthritis", "moderate"): {"ji_one_large": 0.05, "ji_few_large": 0.15, "ji_small_hands": 0.50, "ji_many_both": 0.30, "ji_spine": 0.00},
    ("septic_arthritis", "severe"): {"ji_one_large": 0.85, "ji_few_large": 0.10, "ji_small_hands": 0.02, "ji_many_both": 0.01, "ji_spine": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"js_yes_hot": 0.05, "js_yes_cold": 0.30, "js_no": 0.65},
    "moderate": {"js_yes_hot": 0.15, "js_yes_cold": 0.45, "js_no": 0.40},
    "severe": {"js_yes_hot": 0.35, "js_yes_cold": 0.45, "js_no": 0.20},
}, overrides={
    ("septic_arthritis", "severe"): {"js_yes_hot": 0.90, "js_yes_cold": 0.08, "js_no": 0.02},
    ("tb_of_joint", "moderate"): {"js_yes_hot": 0.05, "js_yes_cold": 0.85, "js_no": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ms_gt_30min": 0.10, "ms_lt_30min": 0.35, "ms_no": 0.55},
    "moderate": {"ms_gt_30min": 0.25, "ms_lt_30min": 0.40, "ms_no": 0.35},
    "severe": {"ms_gt_30min": 0.45, "ms_lt_30min": 0.30, "ms_no": 0.25},
}, overrides={
    ("osteoarthritis", "moderate"): {"ms_gt_30min": 0.08, "ms_lt_30min": 0.70, "ms_no": 0.22},
    ("rheumatoid_or_inflammatory_arthritis", "moderate"): {"ms_gt_30min": 0.75, "ms_lt_30min": 0.20, "ms_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pw_yes": 0.65, "pw_no": 0.15, "pw_both": 0.20},
    "moderate": {"pw_yes": 0.60, "pw_no": 0.15, "pw_both": 0.25},
    "severe": {"pw_yes": 0.50, "pw_no": 0.15, "pw_both": 0.35},
}, overrides={
    ("osteoarthritis", "moderate"): {"pw_yes": 0.85, "pw_no": 0.05, "pw_both": 0.10},
    ("rheumatoid_or_inflammatory_arthritis", "moderate"): {"pw_yes": 0.30, "pw_no": 0.40, "pw_both": 0.30},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"mp_migratory": 0.08, "mp_additive": 0.25, "mp_fixed": 0.67}
    for s in SEVERITIES
}, overrides={
    ("chikungunya_or_viral_arthritis", "moderate"): {"mp_migratory": 0.40, "mp_additive": 0.40, "mp_fixed": 0.20},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("JPN-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ri_yes": 0.15, "ri_no": 0.85}
    for s in SEVERITIES
}, overrides={
    ("osteoarthritis", s): {"ri_yes": 0.25, "ri_no": 0.75} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_tb_screen_entries(
    CONDITION_IDS, SEVERITIES,
    tb_conditions=("tb_of_joint",),
    source_type="IND-PROG", source="Nikshay India TB programme",
)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("septic_arthritis", "chikungunya_or_viral_arthritis"),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
