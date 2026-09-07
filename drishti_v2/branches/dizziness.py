"""
drishti_v2/branches/dizziness.py
The `dizziness` branch (branch-authoring-batch-4-memo.md section 3).
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

CATEGORY_ID = "dizziness"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "benign_paroxysmal_positional_vertigo_or_vestibular_disorder": ConditionSpec(
        "benign_paroxysmal_positional_vertigo_or_vestibular_disorder", 0.40, "IND-POP",
        "Peripheral vestibular vertigo (BPPV, labyrinthitis, Meniere's)"
    ),
    "orthostatic_hypotension_volume_depletion": ConditionSpec(
        "orthostatic_hypotension_volume_depletion", 0.25, "IND-POP",
        "Postural orthostatic lightheadedness or volume depletion",
        severeConditions=("orthostatic hypotension",)
    ),
    "anaemia_related_lightheadedness": ConditionSpec(
        "anaemia_related_lightheadedness", 0.15, "IND-POP",
        "Cerebral hypoperfusion / lightheadedness secondary to anaemia",
        severeConditions=("severe anaemia",)
    ),
    "cardiac_arrhythmia_or_palpitations": ConditionSpec(
        "cardiac_arrhythmia_or_palpitations", 0.10, "IND-POP",
        "Cardiogenic presyncope / dizziness due to arrhythmia or conduction defect",
        severeConditions=("arrhythmia",)
    ),
    "cerebrovascular_event_or_transient_ischaemic_attack": ConditionSpec(
        "cerebrovascular_event_or_transient_ischaemic_attack", 0.05, "IND-POP",
        "Posterior circulation TIA, stroke, or vertebrobasilar insufficiency",
        severeConditions=("stroke",)
    ),
    "hypoglycaemic_episode_in_diabetic": ConditionSpec(
        "hypoglycaemic_episode_in_diabetic", 0.05, "IND-POP",
        "Acute neuroglycopaenic dizziness or hypoglycaemic reaction",
        severeConditions=("hypoglycaemia",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "benign_paroxysmal_positional_vertigo_or_vestibular_disorder": {"mild": 0.50, "moderate": 0.40, "severe": 0.10},
    "orthostatic_hypotension_volume_depletion": {"mild": 0.45, "moderate": 0.40, "severe": 0.15},
    "anaemia_related_lightheadedness": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "cardiac_arrhythmia_or_palpitations": {"mild": 0.25, "moderate": 0.45, "severe": 0.30},
    "cerebrovascular_event_or_transient_ischaemic_attack": {"mild": 0.15, "moderate": 0.45, "severe": 0.40},
    "hypoglycaemic_episode_in_diabetic": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sys = specs["bp_systolic"]
    base_dia = specs["bp_diastolic"]

    if condition_id == "cardiac_arrhythmia_or_palpitations":
        specs["pulse"] = VitalSpec(base_pulse.mean + 30, 15.0, 35, 230)
    elif condition_id == "orthostatic_hypotension_volume_depletion":
        specs["bp_systolic"] = VitalSpec(max(60, base_sys.mean - 20), 8.0, 50, 160)
        specs["bp_diastolic"] = VitalSpec(max(40, base_dia.mean - 12), 6.0, 30, 100)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_dzz_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_dzz_emg2(fields, ctx):
    return (
        contains(fields, "danger_signs", "ds_one_side_weak")
        or contains(fields, "danger_signs", "ds_speech_change")
    )

def _gw_dzz_emg3(fields, ctx):
    return contains(fields, "danger_signs", "ds_severe_pallor")

def _gw_dzz_emg4(fields, ctx):
    age_band = ctx.get("age_band", "")
    return (
        age_band in ("infant", "child")
        and contains(fields, "danger_signs", "ds_cannot_feed")
    )

def _gw_dzz_urg3_chest_pain(fields, ctx):
    return contains(fields, "danger_signs", "ds_chest_pain")

def _gw_dzz_urg1_palp(fields, ctx):
    return equals(fields, "palpitations", "pal_yes")

def _gw_dzz_urg2_stroke(fields, ctx):
    return equals(fields, "focal_weakness", "fw_one_side")

_NODES = {
    "DZZ-00": QuestionNode(
        nodeId="DZZ-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_one_side_weak", "One side of body — face, arm or leg — suddenly weak or numb", next="DZZ-G1a"),
            AnswerOption("ds_speech_change", "Sudden difficulty speaking or understanding speech", next="DZZ-G1a"),
            AnswerOption("ds_chest_pain", "Chest pain or palpitations that are not stopping", next="DZZ-G1a"),
            AnswerOption("ds_severe_pallor", "Palms, nails and inside of eyelids are very white", next="DZZ-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="DZZ-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="DZZ-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="DZZ-G1a"),
            AnswerOption("ds_none", "None of these", next="DZZ-01"),
        ],
        default_next="DZZ-G1a", none_option="ds_none", unknown_option="ds_unknown", **_nu(0.01)
    ),
    "DZZ-G1a": GatewayNode("DZZ-G1a", "GW-DZZ-EMG-1", _gw_dzz_emg1, next="DZZ-G1b",
                           routeTo="emergency_unconscious"),
    "DZZ-G1b": GatewayNode("DZZ-G1b", "GW-DZZ-EMG-2", _gw_dzz_emg2, next="DZZ-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["stroke"]),
    "DZZ-G1c": GatewayNode("DZZ-G1c", "GW-DZZ-EMG-3", _gw_dzz_emg3, next="DZZ-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["severe anaemia"]),
    "DZZ-G1d": GatewayNode("DZZ-G1d", "GW-DZZ-EMG-4", _gw_dzz_emg4, next="DZZ-G1e",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),
    "DZZ-G1e": GatewayNode("DZZ-G1e", "GW-DZZ-URG-3", _gw_dzz_urg3_chest_pain, next="DZZ-01",
                           raisesTo="REFER_URGENT", severeConditions=["arrhythmia", "MI"]),

    "DZZ-01": QuestionNode(
        nodeId="DZZ-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Getting better", next="DZZ-02"),
            AnswerOption("pr_same", "About the same", next="DZZ-02"),
            AnswerOption("pr_worse", "Getting worse", next="DZZ-02"),
        ],
        default_next="DZZ-02", unknown_option="pr_unknown", **_nu(0.02)
    ),
    "DZZ-02": QuestionNode(
        nodeId="DZZ-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies", next="DZZ-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy / shop", next="DZZ-03"),
            AnswerOption("pt_ayush", "Ayurvedic / homeopathic / traditional medicine", next="DZZ-03"),
            AnswerOption("pt_prescribed_prior", "Prescription medicine from another doctor", next="DZZ-03"),
            AnswerOption("pt_other", "Other treatment", next="DZZ-03"),
            AnswerOption("pt_none", "No prior treatment", next="DZZ-03"),
        ],
        default_next="DZZ-03", none_option="pt_none", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "DZZ-03": QuestionNode(
        nodeId="DZZ-03", fieldId="dizziness_type", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("dzt_spinning", "Room spinning or things moving", next="DZZ-04"),
            AnswerOption("dzt_lightheaded", "Feels faint or lightheaded", next="DZZ-04"),
            AnswerOption("dzt_unsteady", "Unsteady on feet, off-balance", next="DZZ-04"),
        ],
        default_next="DZZ-04", unknown_option="dzt_unknown", **_nu(0.03)
    ),
    "DZZ-04": QuestionNode(
        nodeId="DZZ-04", fieldId="on_standing", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("os_yes", "Yes — mainly on standing", next="DZZ-05"),
            AnswerOption("os_sometimes", "Sometimes", next="DZZ-05"),
            AnswerOption("os_no", "No", next="DZZ-05"),
        ],
        default_next="DZZ-05", unknown_option="os_unknown", **_nu(0.03)
    ),
    "DZZ-05": QuestionNode(
        nodeId="DZZ-05", fieldId="palpitations", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pal_yes", "Yes", next="DZZ-G2"),
            AnswerOption("pal_no", "No", next="DZZ-G2"),
        ],
        default_next="DZZ-G2", unknown_option="pal_unknown", **_nu(0.03)
    ),
    "DZZ-G2": GatewayNode("DZZ-G2", "GW-DZZ-URG-1", _gw_dzz_urg1_palp, next="DZZ-06",
                          raisesTo="REFER_URGENT", severeConditions=["arrhythmia"]),

    "DZZ-06": QuestionNode(
        nodeId="DZZ-06", fieldId="hearing_change", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hc_hearing_loss", "Hearing has become worse", next="DZZ-07"),
            AnswerOption("hc_ringing", "Ringing or buzzing in ears", next="DZZ-07"),
            AnswerOption("hc_both", "Both — worse hearing and ringing", next="DZZ-07"),
            AnswerOption("hc_no", "No change", next="DZZ-07"),
        ],
        default_next="DZZ-07", unknown_option="hc_unknown", **_nu(0.03)
    ),
    "DZZ-07": QuestionNode(
        nodeId="DZZ-07", fieldId="focal_weakness", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fw_one_side", "Yes — on one side of the body", next="DZZ-G3"),
            AnswerOption("fw_both_sides", "Yes — both sides or all limbs", next="DZZ-G3"),
            AnswerOption("fw_no", "No", next="DZZ-G3"),
        ],
        default_next="DZZ-G3", unknown_option="fw_unknown", **_nu(0.03)
    ),
    "DZZ-G3": GatewayNode("DZZ-G3", "GW-DZZ-URG-2", _gw_dzz_urg2_stroke, next="DZZ-08",
                          raisesTo="REFER_URGENT", severeConditions=["stroke"]),

    "DZZ-08": SubtreeRefNode("DZZ-08", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="DZZ-END"),
    "DZZ-END": TerminalNode("DZZ-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="DZZ-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Dizziness clinical distribution"

_entries = []

_entries += expand_entries("DZZ-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_one_side_weak": 0.005, "ds_speech_change": 0.005, "ds_chest_pain": 0.02,
             "ds_severe_pallor": 0.02, "ds_confusion": 0.005, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_one_side_weak": 0.02, "ds_speech_change": 0.02, "ds_chest_pain": 0.06,
                "ds_severe_pallor": 0.06, "ds_confusion": 0.02, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_one_side_weak": 0.15, "ds_speech_change": 0.15, "ds_chest_pain": 0.20,
               "ds_severe_pallor": 0.20, "ds_confusion": 0.10, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, overrides={
    ("cerebrovascular_event_or_transient_ischaemic_attack", "moderate"): {
        "ds_one_side_weak": 0.50, "ds_speech_change": 0.40, "ds_chest_pain": 0.02,
        "ds_severe_pallor": 0.02, "ds_confusion": 0.15, "ds_unconscious": 0.01, "ds_cannot_feed": 0.02
    },
    ("cerebrovascular_event_or_transient_ischaemic_attack", "severe"): {
        "ds_one_side_weak": 0.85, "ds_speech_change": 0.75, "ds_chest_pain": 0.05,
        "ds_severe_pallor": 0.05, "ds_confusion": 0.35, "ds_unconscious": 0.05, "ds_cannot_feed": 0.10
    },
    ("cardiac_arrhythmia_or_palpitations", "severe"): {
        "ds_one_side_weak": 0.01, "ds_speech_change": 0.01, "ds_chest_pain": 0.75,
        "ds_severe_pallor": 0.05, "ds_confusion": 0.10, "ds_unconscious": 0.03, "ds_cannot_feed": 0.02
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DZZ-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.30, "pr_same": 0.55, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.30, "pr_worse": 0.65},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DZZ-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.35, "pt_pharmacy_medicine": 0.35, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.25, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DZZ-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"dzt_spinning": 0.45, "dzt_lightheaded": 0.40, "dzt_unsteady": 0.15}
    for s in SEVERITIES
}, overrides={
    ("benign_paroxysmal_positional_vertigo_or_vestibular_disorder", "mild"): {"dzt_spinning": 0.85, "dzt_lightheaded": 0.10, "dzt_unsteady": 0.05},
    ("benign_paroxysmal_positional_vertigo_or_vestibular_disorder", "moderate"): {"dzt_spinning": 0.90, "dzt_lightheaded": 0.05, "dzt_unsteady": 0.05},
    ("benign_paroxysmal_positional_vertigo_or_vestibular_disorder", "severe"): {"dzt_spinning": 0.85, "dzt_lightheaded": 0.05, "dzt_unsteady": 0.10},
    ("orthostatic_hypotension_volume_depletion", "mild"): {"dzt_spinning": 0.05, "dzt_lightheaded": 0.85, "dzt_unsteady": 0.10},
    ("orthostatic_hypotension_volume_depletion", "moderate"): {"dzt_spinning": 0.05, "dzt_lightheaded": 0.85, "dzt_unsteady": 0.10},
    ("orthostatic_hypotension_volume_depletion", "severe"): {"dzt_spinning": 0.05, "dzt_lightheaded": 0.80, "dzt_unsteady": 0.15},
    ("anaemia_related_lightheadedness", "mild"): {"dzt_spinning": 0.05, "dzt_lightheaded": 0.85, "dzt_unsteady": 0.10},
    ("anaemia_related_lightheadedness", "moderate"): {"dzt_spinning": 0.05, "dzt_lightheaded": 0.85, "dzt_unsteady": 0.10},
    ("anaemia_related_lightheadedness", "severe"): {"dzt_spinning": 0.05, "dzt_lightheaded": 0.80, "dzt_unsteady": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DZZ-04", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"os_yes": 0.25, "os_sometimes": 0.35, "os_no": 0.40}
    for s in SEVERITIES
}, overrides={
    ("orthostatic_hypotension_volume_depletion", "mild"): {"os_yes": 0.80, "os_sometimes": 0.15, "os_no": 0.05},
    ("orthostatic_hypotension_volume_depletion", "moderate"): {"os_yes": 0.90, "os_sometimes": 0.08, "os_no": 0.02},
    ("orthostatic_hypotension_volume_depletion", "severe"): {"os_yes": 0.95, "os_sometimes": 0.04, "os_no": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DZZ-05", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pal_yes": 0.15, "pal_no": 0.85}
    for s in SEVERITIES
}, overrides={
    ("cardiac_arrhythmia_or_palpitations", "mild"): {"pal_yes": 0.75, "pal_no": 0.25},
    ("cardiac_arrhythmia_or_palpitations", "moderate"): {"pal_yes": 0.88, "pal_no": 0.12},
    ("cardiac_arrhythmia_or_palpitations", "severe"): {"pal_yes": 0.95, "pal_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DZZ-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"hc_hearing_loss": 0.05, "hc_ringing": 0.10, "hc_both": 0.05, "hc_no": 0.80}
    for s in SEVERITIES
}, overrides={
    ("benign_paroxysmal_positional_vertigo_or_vestibular_disorder", "mild"): {"hc_hearing_loss": 0.10, "hc_ringing": 0.25, "hc_both": 0.15, "hc_no": 0.50},
    ("benign_paroxysmal_positional_vertigo_or_vestibular_disorder", "moderate"): {"hc_hearing_loss": 0.15, "hc_ringing": 0.35, "hc_both": 0.20, "hc_no": 0.30},
    ("benign_paroxysmal_positional_vertigo_or_vestibular_disorder", "severe"): {"hc_hearing_loss": 0.20, "hc_ringing": 0.40, "hc_both": 0.25, "hc_no": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("DZZ-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"fw_one_side": 0.02, "fw_both_sides": 0.05, "fw_no": 0.93}
    for s in SEVERITIES
}, overrides={
    ("cerebrovascular_event_or_transient_ischaemic_attack", "mild"): {"fw_one_side": 0.50, "fw_both_sides": 0.10, "fw_no": 0.40},
    ("cerebrovascular_event_or_transient_ischaemic_attack", "moderate"): {"fw_one_side": 0.75, "fw_both_sides": 0.05, "fw_no": 0.20},
    ("cerebrovascular_event_or_transient_ischaemic_attack", "severe"): {"fw_one_side": 0.90, "fw_both_sides": 0.02, "fw_no": 0.08},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=(),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
