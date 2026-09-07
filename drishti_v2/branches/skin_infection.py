"""
drishti_v2/branches/skin_infection.py
The `skin_infection` branch (branch-authoring-batch-4-memo.md section 5, Operator Decision G-19).
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

CATEGORY_ID = "skin_infection"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_URGENT"

CONDITIONS = {
    "bacterial_cellulitis_or_erysipelas": ConditionSpec(
        "bacterial_cellulitis_or_erysipelas", 0.35, "IND-POP",
        "Acute spreading bacterial dermis/hypodermis infection (cellulitis)",
        severeConditions=("cellulitis",)
    ),
    "cutaneous_abscess_boil_furuncle": ConditionSpec(
        "cutaneous_abscess_boil_furuncle", 0.30, "IND-POP",
        "Localized collection of pus, furuncle, carbuncle, or subcutaneous abscess",
        severeConditions=("abscess",)
    ),
    "infected_wound_or_traumatic_ulcer": ConditionSpec(
        "infected_wound_or_traumatic_ulcer", 0.15, "IND-POP",
        "Secondary bacterial infection of laceration, abrasion, or traumatic wound",
        severeConditions=("tetanus-prone wound",)
    ),
    "diabetic_foot_ulcer_complicated": ConditionSpec(
        "diabetic_foot_ulcer_complicated", 0.10, "IND-POP",
        "Infected neuropathic or ischemic ulcer in a diabetic patient",
        severeConditions=("diabetic foot",)
    ),
    "necrotising_soft_tissue_infection": ConditionSpec(
        "necrotising_soft_tissue_infection", 0.05, "IND-POP",
        "Fulminant necrotising fasciitis, gas gangrene, or synergic bacterial gangrene",
        severeConditions=("necrotising infection",)
    ),
    "superficial_pyoderma_impetigo_folliculitis": ConditionSpec(
        "superficial_pyoderma_impetigo_folliculitis", 0.05, "IND-POP",
        "Superficial bacterial pyoderma, impetigo contagiosa, or folliculitis"
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "bacterial_cellulitis_or_erysipelas": {"mild": 0.30, "moderate": 0.45, "severe": 0.25},
    "cutaneous_abscess_boil_furuncle": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "infected_wound_or_traumatic_ulcer": {"mild": 0.35, "moderate": 0.45, "severe": 0.20},
    "diabetic_foot_ulcer_complicated": {"mild": 0.15, "moderate": 0.45, "severe": 0.40},
    "necrotising_soft_tissue_infection": {"mild": 0.05, "moderate": 0.25, "severe": 0.70},
    "superficial_pyoderma_impetigo_folliculitis": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_temp = specs["temperature"]

    if condition_id in ("bacterial_cellulitis_or_erysipelas", "necrotising_soft_tissue_infection"):
        specs["temperature"] = VitalSpec(base_temp.mean + 1.2, 0.5, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + 18, 9.0, 40, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_ski_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_ski_emg2(fields, ctx):
    return (
        contains(fields, "danger_signs", "ds_crepitus")
        or contains(fields, "danger_signs", "ds_wound_gas")
    )

def _gw_ski_emg3(fields, ctx):
    return (
        contains(fields, "danger_signs", "ds_high_fever_inf")
        and contains(fields, "danger_signs", "ds_confusion")
    )

def _gw_ski_emg4(fields, ctx):
    age_band = ctx.get("age_band", "")
    return (
        age_band in ("infant", "child")
        and contains(fields, "danger_signs", "ds_cannot_feed")
    )

def _gw_ski_urg1_spread(fields, ctx):
    return equals(fields, "spreading_redness", "sr_yes_rapid")

def _gw_ski_urg2_diabetic(fields, ctx):
    kd = equals(fields, "known_diabetes_flag", "kd_yes")
    foot = equals(fields, "lesion_site", "ls_foot")
    neuropathy = equals(fields, "foot_sensation_loss", "fs_reduced")
    return (kd and foot) or neuropathy

_NODES = {
    "SKI-00": QuestionNode(
        nodeId="SKI-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_spreading_red", "Red area spreading rapidly (mark the edge and check again)", next="SKI-G1a"),
            AnswerOption("ds_crepitus", "Skin feels crackly or makes a sound when touched", next="SKI-G1a"),
            AnswerOption("ds_wound_gas", "Foul-smelling wound with bubbles or gas", next="SKI-G1a"),
            AnswerOption("ds_high_fever_inf", "High fever with the infection", next="SKI-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="SKI-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="SKI-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="SKI-G1a"),
            AnswerOption("ds_none", "None of these", next="SKI-01"),
        ],
        default_next="SKI-G1a", none_option="ds_none", unknown_option="ds_unknown", **_nu(0.01)
    ),
    "SKI-G1a": GatewayNode("SKI-G1a", "GW-SKI-EMG-1", _gw_ski_emg1, next="SKI-G1b",
                           routeTo="emergency_unconscious"),
    "SKI-G1b": GatewayNode("SKI-G1b", "GW-SKI-EMG-2", _gw_ski_emg2, next="SKI-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["necrotising fasciitis / gas gangrene"]),
    "SKI-G1c": GatewayNode("SKI-G1c", "GW-SKI-EMG-3", _gw_ski_emg3, next="SKI-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["sepsis"]),
    "SKI-G1d": GatewayNode("SKI-G1d", "GW-SKI-EMG-4", _gw_ski_emg4, next="SKI-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "SKI-01": QuestionNode(
        nodeId="SKI-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Getting better", next="SKI-02"),
            AnswerOption("pr_same", "About the same", next="SKI-02"),
            AnswerOption("pr_worse", "Getting worse", next="SKI-02"),
        ],
        default_next="SKI-02", unknown_option="pr_unknown", **_nu(0.02)
    ),
    "SKI-02": QuestionNode(
        nodeId="SKI-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies", next="SKI-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy / shop", next="SKI-03"),
            AnswerOption("pt_ayush", "Ayurvedic / homeopathic / traditional medicine", next="SKI-03"),
            AnswerOption("pt_prescribed_prior", "Prescription medicine from another doctor", next="SKI-03"),
            AnswerOption("pt_other", "Other treatment", next="SKI-03"),
            AnswerOption("pt_none", "No prior treatment", next="SKI-03"),
        ],
        default_next="SKI-03", none_option="pt_none", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "SKI-03": QuestionNode(
        nodeId="SKI-03", fieldId="lesion_type", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("lt_boil", "Boil or lump with pus", next="SKI-04"),
            AnswerOption("lt_wound", "Open wound or cut", next="SKI-04"),
            AnswerOption("lt_ulcer", "Non-healing sore or ulcer", next="SKI-04"),
            AnswerOption("lt_red_swollen", "Red, swollen, warm area", next="SKI-04"),
            AnswerOption("lt_other", "Something else", next="SKI-04"),
        ],
        default_next="SKI-04", unknown_option="lt_unknown", **_nu(0.02)
    ),
    "SKI-04": QuestionNode(
        nodeId="SKI-04", fieldId="lesion_site", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ls_foot", "Foot or lower leg", next="SKI-05"),
            AnswerOption("ls_hand", "Hand or arm", next="SKI-05"),
            AnswerOption("ls_face", "Face or scalp", next="SKI-05"),
            AnswerOption("ls_trunk", "Chest, back or stomach", next="SKI-05"),
            AnswerOption("ls_groin", "Groin or buttocks", next="SKI-05"),
            AnswerOption("ls_other", "Somewhere else", next="SKI-05"),
        ],
        default_next="SKI-05", unknown_option="ls_unknown", **_nu(0.02)
    ),
    "SKI-05": QuestionNode(
        nodeId="SKI-05", fieldId="spreading_redness", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("sr_yes_rapid", "Yes — noticeably bigger in hours", next="SKI-G2"),
            AnswerOption("sr_yes_slow", "Yes — slowly over days", next="SKI-G2"),
            AnswerOption("sr_no", "No — same size", next="SKI-G2"),
        ],
        default_next="SKI-G2", unknown_option="sr_unknown", **_nu(0.03)
    ),
    "SKI-G2": GatewayNode("SKI-G2", "GW-SKI-URG-1", _gw_ski_urg1_spread, next="SKI-06",
                          raisesTo="REFER_URGENT", severeConditions=["cellulitis (aggressive)"]),

    "SKI-06": QuestionNode(
        nodeId="SKI-06", fieldId="pus_discharge", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pd_yes", "Yes", next="SKI-07"),
            AnswerOption("pd_no", "No", next="SKI-07"),
        ],
        default_next="SKI-07", unknown_option="pd_unknown", **_nu(0.03)
    ),
    "SKI-07": QuestionNode(
        nodeId="SKI-07", fieldId="known_diabetes_flag", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("kd_yes", "Yes", next="SKI-08"),
            AnswerOption("kd_no", "No", next="SKI-09"),
        ],
        default_next="SKI-09", unknown_option="kd_unknown", **_nu(0.03)
    ),
    "SKI-08": QuestionNode(
        nodeId="SKI-08", fieldId="foot_sensation_loss", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fs_yes", "Yes — feels normal", next="SKI-G3"),
            AnswerOption("fs_reduced", "No — feeling is reduced or absent", next="SKI-G3"),
        ],
        default_next="SKI-G3", unknown_option="fs_unknown", **_nu(0.03)
    ),
    "SKI-G3": GatewayNode("SKI-G3", "GW-SKI-URG-2", _gw_ski_urg2_diabetic, next="SKI-09",
                          raisesTo="REFER_URGENT", severeConditions=["diabetic foot", "diabetic neuropathic ulcer"]),

    "SKI-09": QuestionNode(
        nodeId="SKI-09", fieldId="tetanus_status", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ts_within_5y", "Within the last 5 years", next="SKI-10"),
            AnswerOption("ts_gt_5y", "More than 5 years ago", next="SKI-10"),
            AnswerOption("ts_never", "Never had it / not known", next="SKI-10"),
        ],
        default_next="SKI-10", unknown_option="ts_unknown", **_nu(0.03)
    ),
    # G-19: Standalone photo prompt node instead of full RASH-MORPH chain
    "SKI-10": QuestionNode(
        nodeId="SKI-10", fieldId="attachment_photo_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ph_taken", "Photo of infected area taken", next="SKI-S2"),
            AnswerOption("ph_declined", "Patient declined photo", next="SKI-S2"),
            AnswerOption("ph_not_possible", "Not possible to photograph", next="SKI-S2"),
        ],
        default_next="SKI-S2", unknown_option="ph_unknown", **_nu(0.03)
    ),

    "SKI-S2": SubtreeRefNode("SKI-S2", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="SKI-END"),
    "SKI-END": TerminalNode("SKI-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="SKI-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Skin infection clinical distribution"

_entries = []

_entries += expand_entries("SKI-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_spreading_red": 0.05, "ds_crepitus": 0.001, "ds_wound_gas": 0.001,
             "ds_high_fever_inf": 0.02, "ds_confusion": 0.002, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_spreading_red": 0.20, "ds_crepitus": 0.005, "ds_wound_gas": 0.005,
                "ds_high_fever_inf": 0.10, "ds_confusion": 0.01, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_spreading_red": 0.50, "ds_crepitus": 0.08, "ds_wound_gas": 0.08,
               "ds_high_fever_inf": 0.40, "ds_confusion": 0.10, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, overrides={
    ("necrotising_soft_tissue_infection", "moderate"): {
        "ds_spreading_red": 0.60, "ds_crepitus": 0.45, "ds_wound_gas": 0.40,
        "ds_high_fever_inf": 0.35, "ds_confusion": 0.10, "ds_unconscious": 0.01, "ds_cannot_feed": 0.05
    },
    ("necrotising_soft_tissue_infection", "severe"): {
        "ds_spreading_red": 0.90, "ds_crepitus": 0.80, "ds_wound_gas": 0.75,
        "ds_high_fever_inf": 0.70, "ds_confusion": 0.40, "ds_unconscious": 0.10, "ds_cannot_feed": 0.15
    },
    ("bacterial_cellulitis_or_erysipelas", "moderate"): {
        "ds_spreading_red": 0.55, "ds_crepitus": 0.00, "ds_wound_gas": 0.00,
        "ds_high_fever_inf": 0.20, "ds_confusion": 0.01, "ds_unconscious": 0.00, "ds_cannot_feed": 0.01
    },
    ("bacterial_cellulitis_or_erysipelas", "severe"): {
        "ds_spreading_red": 0.85, "ds_crepitus": 0.00, "ds_wound_gas": 0.00,
        "ds_high_fever_inf": 0.60, "ds_confusion": 0.08, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.25, "pr_same": 0.55, "pr_worse": 0.20},
    "moderate": {"pr_better": 0.10, "pr_same": 0.45, "pr_worse": 0.45},
    "severe": {"pr_better": 0.02, "pr_same": 0.20, "pr_worse": 0.78},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.45, "pt_ayush": 0.10,
        "pt_prescribed_prior": 0.20, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"lt_boil": 0.35, "lt_wound": 0.25, "lt_ulcer": 0.15, "lt_red_swollen": 0.20, "lt_other": 0.05}
    for s in SEVERITIES
}, overrides={
    ("bacterial_cellulitis_or_erysipelas", "mild"): {"lt_boil": 0.05, "lt_wound": 0.05, "lt_ulcer": 0.05, "lt_red_swollen": 0.80, "lt_other": 0.05},
    ("bacterial_cellulitis_or_erysipelas", "moderate"): {"lt_boil": 0.02, "lt_wound": 0.03, "lt_ulcer": 0.05, "lt_red_swollen": 0.88, "lt_other": 0.02},
    ("bacterial_cellulitis_or_erysipelas", "severe"): {"lt_boil": 0.01, "lt_wound": 0.02, "lt_ulcer": 0.02, "lt_red_swollen": 0.94, "lt_other": 0.01},
    ("cutaneous_abscess_boil_furuncle", "mild"): {"lt_boil": 0.85, "lt_wound": 0.02, "lt_ulcer": 0.03, "lt_red_swollen": 0.08, "lt_other": 0.02},
    ("cutaneous_abscess_boil_furuncle", "moderate"): {"lt_boil": 0.90, "lt_wound": 0.01, "lt_ulcer": 0.02, "lt_red_swollen": 0.06, "lt_other": 0.01},
    ("cutaneous_abscess_boil_furuncle", "severe"): {"lt_boil": 0.90, "lt_wound": 0.01, "lt_ulcer": 0.02, "lt_red_swollen": 0.06, "lt_other": 0.01},
    ("diabetic_foot_ulcer_complicated", "mild"): {"lt_boil": 0.02, "lt_wound": 0.10, "lt_ulcer": 0.80, "lt_red_swollen": 0.05, "lt_other": 0.03},
    ("diabetic_foot_ulcer_complicated", "moderate"): {"lt_boil": 0.01, "lt_wound": 0.05, "lt_ulcer": 0.88, "lt_red_swollen": 0.04, "lt_other": 0.02},
    ("diabetic_foot_ulcer_complicated", "severe"): {"lt_boil": 0.01, "lt_wound": 0.03, "lt_ulcer": 0.92, "lt_red_swollen": 0.03, "lt_other": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-04", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ls_foot": 0.35, "ls_hand": 0.25, "ls_face": 0.15, "ls_trunk": 0.10, "ls_groin": 0.08, "ls_other": 0.07}
    for s in SEVERITIES
}, overrides={
    ("diabetic_foot_ulcer_complicated", "mild"): {"ls_foot": 0.95, "ls_hand": 0.02, "ls_face": 0.00, "ls_trunk": 0.01, "ls_groin": 0.01, "ls_other": 0.01},
    ("diabetic_foot_ulcer_complicated", "moderate"): {"ls_foot": 0.98, "ls_hand": 0.01, "ls_face": 0.00, "ls_trunk": 0.00, "ls_groin": 0.00, "ls_other": 0.01},
    ("diabetic_foot_ulcer_complicated", "severe"): {"ls_foot": 0.99, "ls_hand": 0.01, "ls_face": 0.00, "ls_trunk": 0.00, "ls_groin": 0.00, "ls_other": 0.00},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"sr_yes_rapid": 0.05, "sr_yes_slow": 0.35, "sr_no": 0.60},
    "moderate": {"sr_yes_rapid": 0.20, "sr_yes_slow": 0.50, "sr_no": 0.30},
    "severe": {"sr_yes_rapid": 0.55, "sr_yes_slow": 0.35, "sr_no": 0.10},
}, overrides={
    ("bacterial_cellulitis_or_erysipelas", "moderate"): {"sr_yes_rapid": 0.45, "sr_yes_slow": 0.45, "sr_no": 0.10},
    ("bacterial_cellulitis_or_erysipelas", "severe"): {"sr_yes_rapid": 0.80, "sr_yes_slow": 0.18, "sr_no": 0.02},
    ("necrotising_soft_tissue_infection", "severe"): {"sr_yes_rapid": 0.90, "sr_yes_slow": 0.09, "sr_no": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"pd_yes": 0.45, "pd_no": 0.55}
    for s in SEVERITIES
}, overrides={
    ("cutaneous_abscess_boil_furuncle", "mild"): {"pd_yes": 0.85, "pd_no": 0.15},
    ("cutaneous_abscess_boil_furuncle", "moderate"): {"pd_yes": 0.92, "pd_no": 0.08},
    ("cutaneous_abscess_boil_furuncle", "severe"): {"pd_yes": 0.95, "pd_no": 0.05},
    ("bacterial_cellulitis_or_erysipelas", "mild"): {"pd_yes": 0.10, "pd_no": 0.90},
    ("bacterial_cellulitis_or_erysipelas", "moderate"): {"pd_yes": 0.15, "pd_no": 0.85},
    ("bacterial_cellulitis_or_erysipelas", "severe"): {"pd_yes": 0.20, "pd_no": 0.80},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"kd_yes": 0.12, "kd_no": 0.88}
    for s in SEVERITIES
}, overrides={
    ("diabetic_foot_ulcer_complicated", "mild"): {"kd_yes": 0.95, "kd_no": 0.05},
    ("diabetic_foot_ulcer_complicated", "moderate"): {"kd_yes": 0.98, "kd_no": 0.02},
    ("diabetic_foot_ulcer_complicated", "severe"): {"kd_yes": 0.99, "kd_no": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"fs_yes": 0.70, "fs_reduced": 0.30}
    for s in SEVERITIES
}, overrides={
    ("diabetic_foot_ulcer_complicated", "mild"): {"fs_yes": 0.25, "fs_reduced": 0.75},
    ("diabetic_foot_ulcer_complicated", "moderate"): {"fs_yes": 0.12, "fs_reduced": 0.88},
    ("diabetic_foot_ulcer_complicated", "severe"): {"fs_yes": 0.05, "fs_reduced": 0.95},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-09", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ts_within_5y": 0.40, "ts_gt_5y": 0.35, "ts_never": 0.25}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("SKI-10", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ph_taken": 0.75, "ph_declined": 0.10, "ph_not_possible": 0.15}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("bacterial_cellulitis_or_erysipelas", "necrotising_soft_tissue_infection"),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
