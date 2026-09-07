"""
drishti_v2/branches/back_neck_pain.py
The `back_neck_pain` branch (branch-authoring-batch-2-memo.md section 3).
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

CATEGORY_ID = "back_neck_pain"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "mechanical_low_back_or_neck_pain": ConditionSpec("mechanical_low_back_or_neck_pain", 0.60, "IND-POP",
        "Mechanical / postural spine strain or lumbago"),
    "lumbar_cervical_spondylosis": ConditionSpec("lumbar_cervical_spondylosis", 0.20, "IND-POP",
        "Degenerative disc disease / spondylosis"),
    "radiculopathy_sciatica": ConditionSpec("radiculopathy_sciatica", 0.10, "IND-PRESENT",
        "Nerve root compression / sciatica"),
    "vertebral_fracture": ConditionSpec("vertebral_fracture", 0.04, "ASSUMED",
        "Osteoporotic or traumatic vertebral compression fracture", severeConditions=("vertebral fracture",)),
    "spinal_tuberculosis_potts": ConditionSpec("spinal_tuberculosis_potts", 0.04, "IND-PROG",
        "Spinal tuberculosis (Pott's spine)", severeConditions=("spinal TB (Pott's)",)),
    "cauda_equina_or_cord_compression": ConditionSpec("cauda_equina_or_cord_compression", 0.02, "ASSUMED",
        "Cauda equina syndrome or spinal cord compression", severeConditions=("cauda equina",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "mechanical_low_back_or_neck_pain": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
    "lumbar_cervical_spondylosis": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "radiculopathy_sciatica": {"mild": 0.25, "moderate": 0.50, "severe": 0.25},
    "vertebral_fracture": {"mild": 0.10, "moderate": 0.40, "severe": 0.50},
    "spinal_tuberculosis_potts": {"mild": 0.15, "moderate": 0.50, "severe": 0.35},
    "cauda_equina_or_cord_compression": {"mild": 0.05, "moderate": 0.25, "severe": 0.70},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    if condition_id == "spinal_tuberculosis_potts":
        specs["temperature"] = VitalSpec(base_temp.mean + 0.8, 0.4, 34, 41)
    elif severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 12, base_pulse.sd, 35, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_bnp_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_bnp_emg2_stage_a(fields, ctx):
    return any_of(fields, "danger_signs", ["ds_loss_bladder_bowel", "ds_numbness_saddle", "ds_both_legs_weak"])

def _gw_bnp_emg3(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_bnp_emg2_full(fields, ctx):
    return _gw_bnp_emg2_stage_a(fields, ctx) or (
        equals(fields, "radiation_to_leg", "rl_both_legs") and any_of(fields, "numbness_weakness_limb", ["nw_weakness", "nw_both"])
    ) or any_of(fields, "bladder_bowel_disturbance", ["bb_difficulty", "bb_leaking"])

def _gw_bnp_urg1_fracture(fields, ctx):
    return contains(fields, "danger_signs", "ds_pain_after_fall") or any_of(fields, "trauma_history", ["th_fall_recent", "th_injury_recent"])

def _gw_bnp_urg2_redflags(fields, ctx):
    return equals(fields, "night_pain", "np_yes") or any_of(fields, "numbness_weakness_limb", ["nw_weakness", "nw_both"]) or (
        value_of(fields, "duration_bucket") in ("month_plus", "chronic") and equals(fields, "weight_loss_present", "wl_yes")
    )

def _gw_bnp_urg3_tb(fields, ctx):
    return equals(fields, "tb_contact", "tbc_yes") or (
        equals(fields, "fever_present", "fp_yes") and value_of(fields, "duration_bucket") in ("week_plus", "month_plus", "chronic")
    )

_NODES = {
    "BNP-00": QuestionNode(
        nodeId="BNP-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_loss_bladder_bowel", "Lost control of bladder or bowels", next="BNP-G1a"),
            AnswerOption("ds_numbness_saddle", "Numbness around the bottom or genitals", next="BNP-G1a"),
            AnswerOption("ds_both_legs_weak", "Both legs suddenly weak or numb", next="BNP-G1a"),
            AnswerOption("ds_pain_after_fall", "The pain started after a fall or injury", next="BNP-G1a"),
            AnswerOption("ds_pain_worst_lying", "Pain worse at night or when lying flat", next="BNP-G1a"),
            AnswerOption("ds_fever_with_spine", "Fever with the back or neck pain", next="BNP-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="BNP-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="BNP-G1a"),
        ],
        default_next="BNP-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "BNP-G1a": GatewayNode("BNP-G1a", "GW-BNP-EMG-1", _gw_bnp_emg1, next="BNP-G1b",
                           routeTo="emergency_unconscious", severeConditions=["spinal cord injury", "sepsis"]),
    "BNP-G1b": GatewayNode("BNP-G1b", "GW-BNP-EMG-2", _gw_bnp_emg2_stage_a, next="BNP-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["cauda equina syndrome", "spinal cord compression"]),
    "BNP-G1c": GatewayNode("BNP-G1c", "GW-BNP-EMG-3", _gw_bnp_emg3, next="BNP-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),
    "BNP-G1d": GatewayNode("BNP-G1d", "GW-BNP-URG-1", _gw_bnp_urg1_fracture, next="BNP-01",
                           raisesTo="REFER_URGENT", severeConditions=["vertebral fracture", "spinal cord injury"]),

    "BNP-01": QuestionNode(
        nodeId="BNP-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="BNP-02"),
            AnswerOption("pr_same", "About the same", next="BNP-02"),
            AnswerOption("pr_worse", "Worse", next="BNP-02"),
        ],
        default_next="BNP-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "BNP-02": QuestionNode(
        nodeId="BNP-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="BNP-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="BNP-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="BNP-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="BNP-03"),
            AnswerOption("pt_other", "Other treatment", next="BNP-03"),
        ],
        default_next="BNP-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "BNP-03": QuestionNode(
        nodeId="BNP-03", fieldId="pain_site_spine", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pss_neck", "Neck", next="BNP-04"),
            AnswerOption("pss_upper_back", "Upper back, between the shoulder blades", next="BNP-04"),
            AnswerOption("pss_lower_back", "Lower back", next="BNP-04"),
            AnswerOption("pss_whole_spine", "All along the back", next="BNP-04"),
        ],
        default_next="BNP-04", unknown_option="pss_unknown", **_nu(0.03)
    ),
    "BNP-04": QuestionNode(
        nodeId="BNP-04", fieldId="radiation_to_leg", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rl_one_leg", "Yes — down one leg", next="BNP-05"),
            AnswerOption("rl_both_legs", "Yes — both legs", next="BNP-05"),
            AnswerOption("rl_to_groin", "Yes — down to the groin", next="BNP-05"),
            AnswerOption("rl_no", "No", next="BNP-05"),
        ],
        default_next="BNP-05", unknown_option="rl_unknown", **_nu(0.03)
    ),
    "BNP-05": QuestionNode(
        nodeId="BNP-05", fieldId="numbness_weakness_limb", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("nw_numbness", "Numbness or tingling", next="BNP-06"),
            AnswerOption("nw_weakness", "Weakness — cannot lift or grip", next="BNP-06"),
            AnswerOption("nw_both", "Both", next="BNP-06"),
            AnswerOption("nw_no", "No", next="BNP-06"),
        ],
        default_next="BNP-06", unknown_option="nw_unknown", **_nu(0.03)
    ),
    "BNP-06": QuestionNode(
        nodeId="BNP-06", fieldId="night_pain", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("np_yes", "Yes — wakes from sleep", next="BNP-07"),
            AnswerOption("np_no", "No — pain is better at rest", next="BNP-07"),
        ],
        default_next="BNP-07", unknown_option="np_unknown", **_nu(0.03)
    ),
    "BNP-07": QuestionNode(
        nodeId="BNP-07", fieldId="bladder_bowel_disturbance", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bb_difficulty", "Difficulty starting or stopping urine", next="BNP-08"),
            AnswerOption("bb_leaking", "Leaking urine or stool", next="BNP-08"),
            AnswerOption("bb_no", "No trouble", next="BNP-08"),
        ],
        default_next="BNP-08", unknown_option="bb_unknown", **_nu(0.03)
    ),
    "BNP-08": QuestionNode(
        nodeId="BNP-08", fieldId="trauma_history", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("th_fall_recent", "Yes — a fall in the last 2 weeks", next="BNP-S1"),
            AnswerOption("th_injury_recent", "Yes — another type of injury recently", next="BNP-S1"),
            AnswerOption("th_old_injury", "Yes — an old injury, months or years ago", next="BNP-S1"),
            AnswerOption("th_no", "No", next="BNP-S1"),
        ],
        default_next="BNP-S1", unknown_option="th_unknown", **_nu(0.03)
    ),

    "BNP-S1": SubtreeRefNode("BNP-S1", subtree_nodes=make_tb_screen_nodes(), entry="TBS-01", returnNext="BNP-G3"),
    "BNP-G3": GatewayNode("BNP-G3", "GW-BNP-URG-3", _gw_bnp_urg3_tb, next="BNP-S2",
                          raisesTo="REFER_URGENT", severeConditions=["spinal TB (Pott's)", "spinal abscess"]),
    "BNP-S2": SubtreeRefNode("BNP-S2", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="BNP-G2"),
    "BNP-G2": GatewayNode("BNP-G2", "GW-BNP-EMG-2", _gw_bnp_emg2_full, next="BNP-G4",
                          raisesTo="REFER_EMERGENCY", severeConditions=["cauda equina syndrome", "spinal cord compression"]),
    "BNP-G4": GatewayNode("BNP-G4", "GW-BNP-URG-2", _gw_bnp_urg2_redflags, next="BNP-END",
                          raisesTo="REFER_URGENT", severeConditions=["malignancy", "spinal TB", "chronic infection"]),
    "BNP-END": TerminalNode("BNP-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="BNP-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Back and neck pain clinical distribution"

_entries = []

_entries += expand_entries("BNP-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_loss_bladder_bowel": 0.001, "ds_numbness_saddle": 0.002, "ds_both_legs_weak": 0.005,
             "ds_pain_after_fall": 0.02, "ds_pain_worst_lying": 0.03, "ds_fever_with_spine": 0.005,
             "ds_unconscious": 0.001, "ds_cannot_feed": 0.005},
    "moderate": {"ds_loss_bladder_bowel": 0.01, "ds_numbness_saddle": 0.01, "ds_both_legs_weak": 0.03,
                "ds_pain_after_fall": 0.08, "ds_pain_worst_lying": 0.08, "ds_fever_with_spine": 0.02,
                "ds_unconscious": 0.002, "ds_cannot_feed": 0.01},
    "severe": {"ds_loss_bladder_bowel": 0.08, "ds_numbness_saddle": 0.10, "ds_both_legs_weak": 0.15,
               "ds_pain_after_fall": 0.20, "ds_pain_worst_lying": 0.25, "ds_fever_with_spine": 0.08,
               "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, overrides={
    ("cauda_equina_or_cord_compression", "severe"): {"ds_loss_bladder_bowel": 0.80, "ds_numbness_saddle": 0.85, "ds_both_legs_weak": 0.75,
                                                    "ds_pain_after_fall": 0.10, "ds_pain_worst_lying": 0.40, "ds_fever_with_spine": 0.02,
                                                    "ds_unconscious": 0.02, "ds_cannot_feed": 0.02},
    ("vertebral_fracture", "severe"): {"ds_loss_bladder_bowel": 0.05, "ds_numbness_saddle": 0.05, "ds_both_legs_weak": 0.15,
                                      "ds_pain_after_fall": 0.75, "ds_pain_worst_lying": 0.35, "ds_fever_with_spine": 0.01,
                                      "ds_unconscious": 0.01, "ds_cannot_feed": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.30, "pr_same": 0.55, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.45, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.15,
        "pt_prescribed_prior": 0.25, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pss_neck": 0.25, "pss_upper_back": 0.10, "pss_lower_back": 0.55, "pss_whole_spine": 0.10}
    for s in SEVERITIES
}, overrides={
    ("mechanical_low_back_or_neck_pain", s): {"pss_neck": 0.20, "pss_upper_back": 0.05, "pss_lower_back": 0.70, "pss_whole_spine": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"rl_one_leg": 0.15, "rl_both_legs": 0.02, "rl_to_groin": 0.03, "rl_no": 0.80},
    "moderate": {"rl_one_leg": 0.30, "rl_both_legs": 0.05, "rl_to_groin": 0.05, "rl_no": 0.60},
    "severe": {"rl_one_leg": 0.45, "rl_both_legs": 0.15, "rl_to_groin": 0.05, "rl_no": 0.35},
}, overrides={
    ("radiculopathy_sciatica", "moderate"): {"rl_one_leg": 0.75, "rl_both_legs": 0.05, "rl_to_groin": 0.02, "rl_no": 0.18},
    ("radiculopathy_sciatica", "severe"): {"rl_one_leg": 0.80, "rl_both_legs": 0.10, "rl_to_groin": 0.02, "rl_no": 0.08},
    ("cauda_equina_or_cord_compression", "severe"): {"rl_one_leg": 0.15, "rl_both_legs": 0.75, "rl_to_groin": 0.02, "rl_no": 0.08},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"nw_numbness": 0.10, "nw_weakness": 0.02, "nw_both": 0.01, "nw_no": 0.87},
    "moderate": {"nw_numbness": 0.25, "nw_weakness": 0.08, "nw_both": 0.05, "nw_no": 0.62},
    "severe": {"nw_numbness": 0.30, "nw_weakness": 0.20, "nw_both": 0.20, "nw_no": 0.30},
}, overrides={
    ("cauda_equina_or_cord_compression", "severe"): {"nw_numbness": 0.10, "nw_weakness": 0.20, "nw_both": 0.65, "nw_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-06", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"np_yes": 0.10, "np_no": 0.90},
    "moderate": {"np_yes": 0.25, "np_no": 0.75},
    "severe": {"np_yes": 0.45, "np_no": 0.55},
}, overrides={
    ("spinal_tuberculosis_potts", "moderate"): {"np_yes": 0.70, "np_no": 0.30},
    ("spinal_tuberculosis_potts", "severe"): {"np_yes": 0.85, "np_no": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bb_difficulty": 0.02, "bb_leaking": 0.01, "bb_no": 0.97},
    "moderate": {"bb_difficulty": 0.05, "bb_leaking": 0.02, "bb_no": 0.93},
    "severe": {"bb_difficulty": 0.12, "bb_leaking": 0.05, "bb_no": 0.83},
}, overrides={
    ("cauda_equina_or_cord_compression", "severe"): {"bb_difficulty": 0.45, "bb_leaking": 0.50, "bb_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("BNP-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"th_fall_recent": 0.08, "th_injury_recent": 0.05, "th_old_injury": 0.15, "th_no": 0.72}
    for s in SEVERITIES
}, overrides={
    ("vertebral_fracture", s): {"th_fall_recent": 0.65, "th_injury_recent": 0.15, "th_old_injury": 0.05, "th_no": 0.15}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_tb_screen_entries(
    CONDITION_IDS, SEVERITIES,
    tb_conditions=("spinal_tuberculosis_potts",),
    source_type="IND-PROG", source="Nikshay India TB programme",
)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("spinal_tuberculosis_potts",),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
