"""
drishti_v2/branches/itching.py
The `itching` branch (branch-authoring-batch-4-memo.md section 4).
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
from .subtrees import make_rash_morph_nodes

CATEGORY_ID = "itching"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "scabies_infestation_household_spread": ConditionSpec(
        "scabies_infestation_household_spread", 0.40, "IND-POP",
        "Sarcoptes scabiei infestation with nocturnal itch and web space lesions",
        severeConditions=("scabies (household outbreak)",)
    ),
    "allergic_contact_dermatitis_or_eczema": ConditionSpec(
        "allergic_contact_dermatitis_or_eczema", 0.25, "IND-POP",
        "Atopic eczema, contact dermatitis, or lichen simplex chronicus"
    ),
    "urticaria_or_drug_induced_pruritus": ConditionSpec(
        "urticaria_or_drug_induced_pruritus", 0.15, "IND-POP",
        "Acute urticaria or drug-induced hypersensitivity pruritus",
        severeConditions=("drug reaction",)
    ),
    "senile_pruritus_or_xerosis_cutis": ConditionSpec(
        "senile_pruritus_or_xerosis_cutis", 0.10, "IND-POP",
        "Dry skin pruritus, winter itch, or senile pruritus in the elderly"
    ),
    "systemic_pruritus_liver_or_renal_disease": ConditionSpec(
        "systemic_pruritus_liver_or_renal_disease", 0.05, "IND-POP",
        "Cholestatic or uraemic generalised pruritus without primary rash",
        severeConditions=("liver/renal disease",)
    ),
    "pruritus_secondary_to_undiagnosed_diabetes": ConditionSpec(
        "pruritus_secondary_to_undiagnosed_diabetes", 0.05, "IND-POP",
        "Generalised or anogenital pruritus secondary to hyperglycemia/candidiasis",
        severeConditions=("diabetes",)
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "scabies_infestation_household_spread": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "allergic_contact_dermatitis_or_eczema": {"mild": 0.50, "moderate": 0.40, "severe": 0.10},
    "urticaria_or_drug_induced_pruritus": {"mild": 0.35, "moderate": 0.45, "severe": 0.20},
    "senile_pruritus_or_xerosis_cutis": {"mild": 0.60, "moderate": 0.35, "severe": 0.05},
    "systemic_pruritus_liver_or_renal_disease": {"mild": 0.25, "moderate": 0.50, "severe": 0.25},
    "pruritus_secondary_to_undiagnosed_diabetes": {"mild": 0.45, "moderate": 0.45, "severe": 0.10},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_ich_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_ich_emg2(fields, ctx):
    anaphylaxis = contains(fields, "danger_signs", "ds_swollen_face") and contains(fields, "danger_signs", "ds_breathless")
    peeling = contains(fields, "danger_signs", "ds_skin_peeling")
    return anaphylaxis or peeling

def _gw_ich_emg3(fields, ctx):
    age_band = ctx.get("age_band", "")
    return (
        age_band in ("infant", "child")
        and contains(fields, "danger_signs", "ds_cannot_feed")
    )

def _gw_ich_urg4_jaundice(fields, ctx):
    return contains(fields, "danger_signs", "ds_jaundice")

def _gw_ich_urg3_liver_renal(fields, ctx):
    lr = value_of(fields, "known_liver_renal_disease")
    return lr in ("lr_liver", "lr_renal")

def _gw_ich_urg2_scabies(fields, ctx):
    return equals(fields, "household_others_affected", "ho_yes") and equals(fields, "itch_worse_at_night", "in_yes")

_NODES = {
    "ICH-00": QuestionNode(
        nodeId="ICH-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_swollen_face", "Swollen face, lips or tongue", next="ICH-G1a"),
            AnswerOption("ds_breathless", "Difficulty breathing", next="ICH-G1a"),
            AnswerOption("ds_skin_peeling", "Skin peeling off or large blisters", next="ICH-G1a"),
            AnswerOption("ds_mucosal_sores", "Sores in mouth, eyes or genitals", next="ICH-G1a"),
            AnswerOption("ds_jaundice", "Eyes or skin look yellow", next="ICH-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="ICH-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="ICH-G1a"),
            AnswerOption("ds_none", "None of these", next="ICH-01"),
        ],
        default_next="ICH-G1a", none_option="ds_none", unknown_option="ds_unknown", **_nu(0.01)
    ),
    "ICH-G1a": GatewayNode("ICH-G1a", "GW-ICH-EMG-1", _gw_ich_emg1, next="ICH-G1b",
                           routeTo="emergency_unconscious"),
    "ICH-G1b": GatewayNode("ICH-G1b", "GW-ICH-EMG-2", _gw_ich_emg2, next="ICH-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["anaphylaxis", "SJS/TEN"]),
    "ICH-G1c": GatewayNode("ICH-G1c", "GW-ICH-EMG-3", _gw_ich_emg3, next="ICH-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),
    "ICH-G1d": GatewayNode("ICH-G1d", "GW-ICH-URG-4", _gw_ich_urg4_jaundice, next="ICH-01",
                           raisesTo="REFER_URGENT", severeConditions=["liver disease"]),

    "ICH-01": QuestionNode(
        nodeId="ICH-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Getting better", next="ICH-02"),
            AnswerOption("pr_same", "About the same", next="ICH-02"),
            AnswerOption("pr_worse", "Getting worse", next="ICH-02"),
        ],
        default_next="ICH-02", unknown_option="pr_unknown", **_nu(0.02)
    ),
    "ICH-02": QuestionNode(
        nodeId="ICH-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies", next="ICH-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy / shop", next="ICH-03"),
            AnswerOption("pt_ayush", "Ayurvedic / homeopathic / traditional medicine", next="ICH-03"),
            AnswerOption("pt_prescribed_prior", "Prescription medicine from another doctor", next="ICH-03"),
            AnswerOption("pt_other", "Other treatment", next="ICH-03"),
            AnswerOption("pt_none", "No prior treatment", next="ICH-03"),
        ],
        default_next="ICH-03", none_option="pt_none", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "ICH-03": QuestionNode(
        nodeId="ICH-03", fieldId="itch_site", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("is_web_spaces", "Between fingers, wrists, folds", next="ICH-04"),
            AnswerOption("is_all_over", "All over the body", next="ICH-04"),
            AnswerOption("is_scalp", "Scalp", next="ICH-04"),
            AnswerOption("is_groin", "Groin, buttocks, or private parts", next="ICH-04"),
            AnswerOption("is_one_area", "One patch or area only", next="ICH-04"),
        ],
        default_next="ICH-04", unknown_option="is_unknown", **_nu(0.02)
    ),
    "ICH-04": QuestionNode(
        nodeId="ICH-04", fieldId="itch_worse_at_night", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("in_yes", "Yes — much worse at night", next="ICH-05"),
            AnswerOption("in_no", "No — same day and night", next="ICH-05"),
        ],
        default_next="ICH-05", unknown_option="in_unknown", **_nu(0.03)
    ),
    "ICH-05": QuestionNode(
        nodeId="ICH-05", fieldId="household_others_affected", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ho_yes", "Yes", next="ICH-06"),
            AnswerOption("ho_no", "No", next="ICH-06"),
        ],
        default_next="ICH-06", unknown_option="ho_unknown", **_nu(0.03)
    ),
    "ICH-06": QuestionNode(
        nodeId="ICH-06", fieldId="visible_burrows_or_lesions", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vb_burrows", "Yes — tiny lines (like scratches)", next="ICH-07"),
            AnswerOption("vb_bumps", "Yes — small bumps or blisters", next="ICH-07"),
            AnswerOption("vb_none", "No — skin looks normal but itchy", next="ICH-07"),
        ],
        default_next="ICH-07", unknown_option="vb_unknown", **_nu(0.03)
    ),
    "ICH-07": QuestionNode(
        nodeId="ICH-07", fieldId="known_liver_renal_disease", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("lr_liver", "Yes — liver disease", next="ICH-G2"),
            AnswerOption("lr_renal", "Yes — kidney disease", next="ICH-G2"),
            AnswerOption("lr_no", "No", next="ICH-08"),
        ],
        default_next="ICH-08", unknown_option="lr_unknown", **_nu(0.03)
    ),
    "ICH-G2": GatewayNode("ICH-G2", "GW-ICH-URG-3", _gw_ich_urg3_liver_renal, next="ICH-08",
                          raisesTo="REFER_URGENT", severeConditions=["liver/renal disease"]),

    "ICH-08": QuestionNode(
        nodeId="ICH-08", fieldId="new_drug_2_weeks", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("nd_yes", "Yes", next="ICH-S1"),
            AnswerOption("nd_no", "No", next="ICH-S1"),
        ],
        default_next="ICH-S1", unknown_option="nd_unknown", **_nu(0.03)
    ),

    "ICH-S1": SubtreeRefNode("ICH-S1", subtree_nodes=make_rash_morph_nodes(), entry="RSH-03", returnNext="ICH-G3"),
    "ICH-G3": GatewayNode("ICH-G3", "GW-ICH-URG-2", _gw_ich_urg2_scabies, next="ICH-END",
                          raisesTo="REFER_URGENT", severeConditions=["scabies"]),
    "ICH-END": TerminalNode("ICH-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="ICH-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Itching clinical distribution"

_entries = []

_entries += expand_entries("ICH-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_swollen_face": 0.01, "ds_breathless": 0.005, "ds_skin_peeling": 0.005,
             "ds_mucosal_sores": 0.005, "ds_jaundice": 0.01, "ds_unconscious": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_swollen_face": 0.05, "ds_breathless": 0.02, "ds_skin_peeling": 0.02,
                "ds_mucosal_sores": 0.02, "ds_jaundice": 0.04, "ds_unconscious": 0.002, "ds_cannot_feed": 0.005},
    "severe": {"ds_swollen_face": 0.20, "ds_breathless": 0.10, "ds_skin_peeling": 0.15,
               "ds_mucosal_sores": 0.10, "ds_jaundice": 0.15, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05},
}, overrides={
    ("urticaria_or_drug_induced_pruritus", "moderate"): {
        "ds_swollen_face": 0.25, "ds_breathless": 0.10, "ds_skin_peeling": 0.05,
        "ds_mucosal_sores": 0.05, "ds_jaundice": 0.00, "ds_unconscious": 0.00, "ds_cannot_feed": 0.01
    },
    ("urticaria_or_drug_induced_pruritus", "severe"): {
        "ds_swollen_face": 0.65, "ds_breathless": 0.45, "ds_skin_peeling": 0.35,
        "ds_mucosal_sores": 0.25, "ds_jaundice": 0.00, "ds_unconscious": 0.02, "ds_cannot_feed": 0.05
    },
    ("systemic_pruritus_liver_or_renal_disease", "moderate"): {
        "ds_swollen_face": 0.02, "ds_breathless": 0.02, "ds_skin_peeling": 0.01,
        "ds_mucosal_sores": 0.01, "ds_jaundice": 0.45, "ds_unconscious": 0.01, "ds_cannot_feed": 0.02
    },
    ("systemic_pruritus_liver_or_renal_disease", "severe"): {
        "ds_swollen_face": 0.05, "ds_breathless": 0.05, "ds_skin_peeling": 0.02,
        "ds_mucosal_sores": 0.02, "ds_jaundice": 0.75, "ds_unconscious": 0.05, "ds_cannot_feed": 0.05
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.25, "pr_same": 0.60, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.10, "pr_same": 0.50, "pr_worse": 0.40},
    "severe": {"pr_better": 0.02, "pr_same": 0.25, "pr_worse": 0.73},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.45, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.15,
        "pt_prescribed_prior": 0.20, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"is_web_spaces": 0.25, "is_all_over": 0.35, "is_scalp": 0.10, "is_groin": 0.15, "is_one_area": 0.15}
    for s in SEVERITIES
}, overrides={
    ("scabies_infestation_household_spread", "mild"): {"is_web_spaces": 0.75, "is_all_over": 0.10, "is_scalp": 0.02, "is_groin": 0.10, "is_one_area": 0.03},
    ("scabies_infestation_household_spread", "moderate"): {"is_web_spaces": 0.70, "is_all_over": 0.15, "is_scalp": 0.02, "is_groin": 0.10, "is_one_area": 0.03},
    ("scabies_infestation_household_spread", "severe"): {"is_web_spaces": 0.60, "is_all_over": 0.25, "is_scalp": 0.02, "is_groin": 0.10, "is_one_area": 0.03},
    ("systemic_pruritus_liver_or_renal_disease", "mild"): {"is_web_spaces": 0.05, "is_all_over": 0.85, "is_scalp": 0.02, "is_groin": 0.05, "is_one_area": 0.03},
    ("systemic_pruritus_liver_or_renal_disease", "moderate"): {"is_web_spaces": 0.02, "is_all_over": 0.92, "is_scalp": 0.02, "is_groin": 0.02, "is_one_area": 0.02},
    ("systemic_pruritus_liver_or_renal_disease", "severe"): {"is_web_spaces": 0.01, "is_all_over": 0.95, "is_scalp": 0.01, "is_groin": 0.02, "is_one_area": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-04", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"in_yes": 0.35, "in_no": 0.65}
    for s in SEVERITIES
}, overrides={
    ("scabies_infestation_household_spread", "mild"): {"in_yes": 0.85, "in_no": 0.15},
    ("scabies_infestation_household_spread", "moderate"): {"in_yes": 0.92, "in_no": 0.08},
    ("scabies_infestation_household_spread", "severe"): {"in_yes": 0.95, "in_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-05", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ho_yes": 0.20, "ho_no": 0.80}
    for s in SEVERITIES
}, overrides={
    ("scabies_infestation_household_spread", "mild"): {"ho_yes": 0.70, "ho_no": 0.30},
    ("scabies_infestation_household_spread", "moderate"): {"ho_yes": 0.85, "ho_no": 0.15},
    ("scabies_infestation_household_spread", "severe"): {"ho_yes": 0.90, "ho_no": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"vb_burrows": 0.15, "vb_bumps": 0.45, "vb_none": 0.40}
    for s in SEVERITIES
}, overrides={
    ("scabies_infestation_household_spread", "mild"): {"vb_burrows": 0.60, "vb_bumps": 0.35, "vb_none": 0.05},
    ("scabies_infestation_household_spread", "moderate"): {"vb_burrows": 0.75, "vb_bumps": 0.22, "vb_none": 0.03},
    ("scabies_infestation_household_spread", "severe"): {"vb_burrows": 0.80, "vb_bumps": 0.18, "vb_none": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-07", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"lr_liver": 0.03, "lr_renal": 0.02, "lr_no": 0.95}
    for s in SEVERITIES
}, overrides={
    ("systemic_pruritus_liver_or_renal_disease", "mild"): {"lr_liver": 0.50, "lr_renal": 0.40, "lr_no": 0.10},
    ("systemic_pruritus_liver_or_renal_disease", "moderate"): {"lr_liver": 0.55, "lr_renal": 0.40, "lr_no": 0.05},
    ("systemic_pruritus_liver_or_renal_disease", "severe"): {"lr_liver": 0.60, "lr_renal": 0.38, "lr_no": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ICH-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"nd_yes": 0.10, "nd_no": 0.90}
    for s in SEVERITIES
}, overrides={
    ("urticaria_or_drug_induced_pruritus", "mild"): {"nd_yes": 0.60, "nd_no": 0.40},
    ("urticaria_or_drug_induced_pruritus", "moderate"): {"nd_yes": 0.75, "nd_no": 0.25},
    ("urticaria_or_drug_induced_pruritus", "severe"): {"nd_yes": 0.85, "nd_no": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

# RASH-MORPH nodes
_dist_base = {s: {"rdst_face_neck": 0.10, "rdst_trunk": 0.25, "rdst_hands_feet": 0.35,
                  "rdst_generalised": 0.20, "rdst_one_patch": 0.10}
              for s in SEVERITIES}
_entries += expand_entries("RSH-03", "categorical", CONDITION_IDS, SEVERITIES, _dist_base, source_type=_SRC, source=_SRC_TEXT)

_morph_base = {s: {"rm_flat_red": 0.25, "rm_raised": 0.35, "rm_fluid_blister": 0.10, "rm_pustular": 0.05,
                   "rm_scaly_patch": 0.15, "rm_pale_patch": 0.05, "rm_purple_spots": 0.05}
               for s in SEVERITIES}
_entries += expand_entries("RSH-04", "categorical", CONDITION_IDS, SEVERITIES, _morph_base, source_type=_SRC, source=_SRC_TEXT)

_symptom_base = {s: {"rs_itchy": 0.90, "rs_painful": 0.03, "rs_burning": 0.05, "rs_numb": 0.01, "rs_none": 0.01}
                 for s in SEVERITIES}
_entries += expand_entries("RSH-05", "categorical", CONDITION_IDS, SEVERITIES, _symptom_base, source_type=_SRC, source=_SRC_TEXT)

_hp_base = {s: {"hp_normal_sensation": 0.95, "hp_reduced": 0.05} for s in SEVERITIES}
_entries += expand_entries("RSH-06", "categorical", CONDITION_IDS, SEVERITIES, _hp_base, source_type=_SRC, source=_SRC_TEXT)

_nd_base = {s: {"nd_yes": 0.10, "nd_no": 0.90} for s in SEVERITIES}
_entries += expand_entries("RSH-07", "categorical", CONDITION_IDS, SEVERITIES, _nd_base, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("RSH-08", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"ho_yes": 0.20, "ho_no": 0.80} for s in SEVERITIES}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("RSH-09", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"ph_taken": 0.70, "ph_declined": 0.10, "ph_not_possible": 0.20} for s in SEVERITIES}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
