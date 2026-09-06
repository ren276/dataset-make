"""
drishti_v2/branches/rash.py
==============================
The `rash` branch (questionnaire-tree-design-memo.md section 5) -- the
skin/visual shape, proving sub-tree reuse: RSH-03..RSH-09 (RASH_MORPH_NODES,
authored once in subtrees.py) is this branch's own tail AND the object
spliced into `fever` at FV-S1. RSH-02 (fever_present==yes) splices in
FEVER_QUAL the same way in the other direction.
"""

from __future__ import annotations

from ..schema import AnswerOption, BranchDef, GatewayNode, QuestionNode, SubtreeRefNode, TerminalNode
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries, peaked
from .spec import CategorySpec, ConditionSpec
from .subtrees import RASH_MORPH_NODES, make_fever_qual_nodes, _gw_rsh_emg1, _gw_rsh_emg2

CATEGORY_ID = "rash"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "benign_dermatitis_or_fungal": ConditionSpec("benign_dermatitis_or_fungal", 0.55, "ASSUMED",
        "Background: most rash presentations at a PHC are benign dermatitis/fungal; the Odisha "
        "authors flag skin as high-burden and diagnosed mostly by visual inspection, but no "
        "source splits the within-chapter condition mix."),
    "viral_exanthem_with_fever": ConditionSpec("viral_exanthem_with_fever", 0.20, "ASSUMED",
        "Measles/dengue-rash-shaped fever+rash presentation.", severeConditions=("measles", "dengue rash")),
    "drug_reaction_mild": ConditionSpec("drug_reaction_mild", 0.12, "ASSUMED", ""),
    "drug_reaction_sjs_ten_severe": ConditionSpec("drug_reaction_sjs_ten_severe", 0.02, "ASSUMED",
        "Kept small and non-zero so GW-RSH-EMG-2's minimum-row-count floor is reachable.",
        severeConditions=("SJS/TEN",)),
    "leprosy_hypopigmented_patch": ConditionSpec("leprosy_hypopigmented_patch", 0.06, "IND-PROG",
        "National leprosy notification programme exists; within-rash share is ASSUMED.",
        severeConditions=("leprosy",)),
    "meningococcaemia_purpura": ConditionSpec("meningococcaemia_purpura", 0.05, "ASSUMED",
        "Kept small and non-zero so GW-RSH-EMG-1's minimum-row-count floor is reachable.",
        severeConditions=("meningococcaemia",)),
}
CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "benign_dermatitis_or_fungal": {"mild": 0.75, "moderate": 0.20, "severe": 0.05},
    "viral_exanthem_with_fever": {"mild": 0.30, "moderate": 0.55, "severe": 0.15},
    "drug_reaction_mild": {"mild": 0.50, "moderate": 0.40, "severe": 0.10},
    "drug_reaction_sjs_ten_severe": {"mild": 0.05, "moderate": 0.15, "severe": 0.80},
    "leprosy_hypopigmented_patch": {"mild": 0.55, "moderate": 0.35, "severe": 0.10},
    "meningococcaemia_purpura": {"mild": 0.05, "moderate": 0.15, "severe": 0.80},
}


def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    if condition_id in ("viral_exanthem_with_fever",):
        bump = {"mild": 0.8, "moderate": 1.5, "severe": 2.2}[severity_band]
        specs["temperature"] = VitalSpec(specs["temperature"].mean + bump, 0.4, 34, 41)
        specs["pulse"] = VitalSpec(specs["pulse"].mean + 15 * bump, specs["pulse"].sd,
                                    specs["pulse"].clip_lo, specs["pulse"].clip_hi)
    if condition_id in ("meningococcaemia_purpura", "drug_reaction_sjs_ten_severe") and severity_band == "severe":
        specs["temperature"] = VitalSpec(38.8, 0.6, 34, 41)
        specs["pulse"] = VitalSpec(138.0, 10.0, 35, 220)
        specs["respiratory_rate"] = VitalSpec(30.0, 4.0, 5, 90)
        specs["spo2"] = VitalSpec(89.0, 3.0, 60, 100)
        specs["bp_systolic"] = VitalSpec(82.0, 8.0, 60, 220)
        specs["glucose"] = VitalSpec(160.0, 90.0, 20, 700)  # stress response; see fever.py note
    return specs


def _no_unknown(rate):
    return dict(unknown_rate=rate, unknown_provenance={
        "sourceType": "ASSUMED", "source": "Flat low unknown rate; no Indian survey used.",
        "declaredOn": "2026-09-06"})


_NODES = {
    "RSH-00": QuestionNode(
        nodeId="RSH-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_mucosal", "Sores in mouth, eyes or genitals", next="RSH-G1a"),
            AnswerOption("ds_skin_peeling", "Skin peeling or blistering", next="RSH-G1a"),
            AnswerOption("ds_purpura", "Purple spots that do not fade on press", next="RSH-G1a"),
            AnswerOption("ds_fever_high", "High fever with the rash", next="RSH-G1a"),
            AnswerOption("ds_swollen_face", "Swollen face, lips or tongue", next="RSH-G1a"),
        ],
        default_next="RSH-01", unknown_option="ds_unknown", none_option="ds_none", **_no_unknown(0.02),
    ),
    "RSH-G1a": GatewayNode("RSH-G1a", "GW-RSH-EMG-1", _gw_rsh_emg1, next="RSH-G1b",
                            raisesTo="REFER_EMERGENCY", severeConditions=["meningococcaemia", "severe dengue"]),
    "RSH-G1b": GatewayNode("RSH-G1b", "GW-RSH-EMG-2", _gw_rsh_emg2, next="RSH-01",
                            raisesTo="REFER_EMERGENCY", severeConditions=["SJS / TEN"]),
    "RSH-01": QuestionNode(
        nodeId="RSH-01", fieldId="rash_duration_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rd_today", "Today only", next="RSH-02"),
            AnswerOption("rd_1_3", "1 to 3 days", next="RSH-02"),
            AnswerOption("rd_4_7", "4 to 7 days", next="RSH-02"),
            AnswerOption("rd_gt_7", "More than 7 days", next="RSH-02"),
            AnswerOption("rd_months", "Months", next="RSH-02"),
        ],
        default_next="RSH-02", unknown_option="rd_unknown", **_no_unknown(0.03),
    ),
    "RSH-02": QuestionNode(
        nodeId="RSH-02", fieldId="fever_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fp_yes", "Yes", next="RSH-S1"),
            AnswerOption("fp_no", "No", next="RSH-03"),
        ],
        default_next="RSH-03", unknown_option="fp_unknown", **_no_unknown(0.03),
    ),
    "RSH-S1": SubtreeRefNode("RSH-S1", make_fever_qual_nodes(),
                              entry="FV-01", returnNext="RSH-03"),
}
_NODES.update(RASH_MORPH_NODES)

BRANCH = BranchDef(categoryId=CATEGORY_ID, version=BRANCH_VERSION,
                    requiredDisposition=REQUIRED_DISPOSITION, nodes=_NODES, entry="RSH-00")

_SRC = "ASSUMED"
_SRC_TEXT = ("Coarse infra-build distribution proving the machine; not physician-reviewed "
             "(tree memo section 6.3 fill-in is deferred).")

_entries = []
_entries += expand_entries("RSH-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_mucosal": 0.002, "ds_skin_peeling": 0.001, "ds_purpura": 0.002,
             "ds_fever_high": 0.02, "ds_swollen_face": 0.002},
    "moderate": {"ds_mucosal": 0.01, "ds_skin_peeling": 0.005, "ds_purpura": 0.01,
                 "ds_fever_high": 0.08, "ds_swollen_face": 0.01},
    "severe": {"ds_mucosal": 0.10, "ds_skin_peeling": 0.10, "ds_purpura": 0.15,
               "ds_fever_high": 0.35, "ds_swollen_face": 0.08},
}, overrides={
    ("drug_reaction_sjs_ten_severe", "severe"): {"ds_mucosal": 0.65, "ds_skin_peeling": 0.60,
                                                  "ds_purpura": 0.05, "ds_fever_high": 0.40, "ds_swollen_face": 0.15},
    ("meningococcaemia_purpura", "severe"): {"ds_mucosal": 0.05, "ds_skin_peeling": 0.05,
                                              "ds_purpura": 0.70, "ds_fever_high": 0.60, "ds_swollen_face": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("RSH-01", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"rd_today": 0.15, "rd_1_3": 0.30, "rd_4_7": 0.25, "rd_gt_7": 0.20, "rd_months": 0.10}
     for s in SEVERITIES},
    overrides={("leprosy_hypopigmented_patch", s): {"rd_today": 0.02, "rd_1_3": 0.05, "rd_4_7": 0.08,
                                                      "rd_gt_7": 0.25, "rd_months": 0.60} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT)

_fp_base = {"mild": {"fp_yes": 0.10, "fp_no": 0.90}, "moderate": {"fp_yes": 0.30, "fp_no": 0.70},
            "severe": {"fp_yes": 0.55, "fp_no": 0.45}}
_fp_overrides = {}
for s in SEVERITIES:
    _fp_overrides[("viral_exanthem_with_fever", s)] = {"fp_yes": 0.85, "fp_no": 0.15}
    _fp_overrides[("meningococcaemia_purpura", s)] = {"fp_yes": 0.90, "fp_no": 0.10}
    _fp_overrides[("leprosy_hypopigmented_patch", s)] = {"fp_yes": 0.03, "fp_no": 0.97}
_entries += expand_entries("RSH-02", "categorical", CONDITION_IDS, SEVERITIES, _fp_base,
                            overrides=_fp_overrides, source_type=_SRC, source=_SRC_TEXT)

_DIST_OPTS = ["rdst_face_first", "rdst_trunk", "rdst_limbs", "rdst_palms_soles",
              "rdst_whole_body", "rdst_one_patch"]
_dist_base = {s: {"rdst_face_first": 0.15, "rdst_trunk": 0.30, "rdst_limbs": 0.20,
                  "rdst_palms_soles": 0.05, "rdst_whole_body": 0.15, "rdst_one_patch": 0.15}
              for s in SEVERITIES}
_dist_overrides = {}
for s in SEVERITIES:
    _dist_overrides[("viral_exanthem_with_fever", s)] = peaked(_DIST_OPTS, "rdst_face_first", 0.55)
    _dist_overrides[("leprosy_hypopigmented_patch", s)] = peaked(_DIST_OPTS, "rdst_one_patch", 0.70)
    _dist_overrides[("meningococcaemia_purpura", s)] = peaked(_DIST_OPTS, "rdst_whole_body", 0.60)
_entries += expand_entries("RSH-03", "categorical", CONDITION_IDS, SEVERITIES, _dist_base,
                            overrides=_dist_overrides, source_type=_SRC, source=_SRC_TEXT)

_MORPH_OPTS = ["rm_flat_red", "rm_raised", "rm_fluid_blister", "rm_pustular", "rm_scaly_patch",
               "rm_pale_patch", "rm_purple_spots"]
_morph_base = {s: {"rm_flat_red": 0.30, "rm_raised": 0.25, "rm_fluid_blister": 0.05, "rm_pustular": 0.10,
                   "rm_scaly_patch": 0.20, "rm_pale_patch": 0.05, "rm_purple_spots": 0.05}
               for s in SEVERITIES}
_morph_overrides = {}
for s in SEVERITIES:
    _morph_overrides[("leprosy_hypopigmented_patch", s)] = peaked(_MORPH_OPTS, "rm_pale_patch", 0.86)
    _morph_overrides[("meningococcaemia_purpura", s)] = peaked(_MORPH_OPTS, "rm_purple_spots", 0.86)
    _morph_overrides[("drug_reaction_sjs_ten_severe", s)] = peaked(_MORPH_OPTS, "rm_fluid_blister", 0.80)
    _morph_overrides[("viral_exanthem_with_fever", s)] = peaked(_MORPH_OPTS, "rm_flat_red", 0.55)
_entries += expand_entries("RSH-04", "categorical", CONDITION_IDS, SEVERITIES, _morph_base,
                            overrides=_morph_overrides, source_type=_SRC, source=_SRC_TEXT)

_SYMPTOM_OPTS = ["rs_itchy", "rs_painful", "rs_burning", "rs_numb", "rs_none"]
_symptom_base = {s: {"rs_itchy": 0.45, "rs_painful": 0.15, "rs_burning": 0.12, "rs_numb": 0.03,
                     "rs_none": 0.25} for s in SEVERITIES}
_symptom_overrides = {(c, s): peaked(_SYMPTOM_OPTS, "rs_numb", 0.55)
                       for c in ("leprosy_hypopigmented_patch",) for s in SEVERITIES}
_entries += expand_entries("RSH-05", "categorical", CONDITION_IDS, SEVERITIES, _symptom_base,
                            overrides=_symptom_overrides, source_type=_SRC, source=_SRC_TEXT)

_hp_base = {s: {"hp_normal_sensation": 0.85, "hp_reduced": 0.15} for s in SEVERITIES}
_hp_overrides = {(c, s): {"hp_normal_sensation": 0.20, "hp_reduced": 0.80}
                 for c in ("leprosy_hypopigmented_patch",) for s in SEVERITIES}
_entries += expand_entries("RSH-06", "categorical", CONDITION_IDS, SEVERITIES, _hp_base,
                            overrides=_hp_overrides, source_type=_SRC, source=_SRC_TEXT)

_nd_base = {s: {"nd_yes": 0.08, "nd_no": 0.92} for s in SEVERITIES}
_nd_overrides = {(c, s): {"nd_yes": 0.80, "nd_no": 0.20}
                 for c in ("drug_reaction_mild", "drug_reaction_sjs_ten_severe") for s in SEVERITIES}
_entries += expand_entries("RSH-07", "categorical", CONDITION_IDS, SEVERITIES, _nd_base,
                            overrides=_nd_overrides, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("RSH-08", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"ho_yes": 0.15, "ho_no": 0.85} for s in SEVERITIES},
    overrides={("benign_dermatitis_or_fungal", s): {"ho_yes": 0.35, "ho_no": 0.65} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("RSH-09", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"ph_taken": 0.70, "ph_declined": 0.10, "ph_not_possible": 0.20} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT)

# FEVER-QUAL (FV-01, FV-02, FV-06) is spliced in at RSH-S1 when fever_present==yes.
# Shared nodeIds with the `fever` branch (subtrees.py docstring); the answer
# model is per-category, so rash needs its own entries keyed by rash's own
# condition catalog.
_fq_fd = {s: {"fd_today": 0.25, "fd_1_3": 0.35, "fd_4_7": 0.25, "fd_8_14": 0.10, "fd_gt_14": 0.05}
          for s in SEVERITIES}
_entries += expand_entries("FV-01", "categorical", CONDITION_IDS, SEVERITIES, _fq_fd,
                            source_type=_SRC, source=_SRC_TEXT + " (rash->fever subtree path)")

_FQ_FP_OPTS = ["fp_stepladder", "fp_cyclical", "fp_evening", "fp_continuous", "fp_mild"]
_fq_fp_base = {s: peaked(_FQ_FP_OPTS, "fp_continuous", 0.40) for s in SEVERITIES}
_fq_fp_overrides = {(c, s): peaked(_FQ_FP_OPTS, "fp_continuous", 0.60)
                     for c in ("viral_exanthem_with_fever", "meningococcaemia_purpura") for s in SEVERITIES}
_entries += expand_entries("FV-02", "categorical", CONDITION_IDS, SEVERITIES, _fq_fp_base,
                            overrides=_fq_fp_overrides, source_type=_SRC,
                            source=_SRC_TEXT + " (rash->fever subtree path)")

_entries += expand_entries("FV-06", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"bl_gums": 0.002, "bl_nose": 0.002, "bl_skin": 0.002, "bl_vomit": 0.001,
             "bl_stool": 0.001, "bl_urine": 0.001},
    "moderate": {"bl_gums": 0.01, "bl_nose": 0.01, "bl_skin": 0.02, "bl_vomit": 0.005,
                 "bl_stool": 0.005, "bl_urine": 0.005},
    "severe": {"bl_gums": 0.05, "bl_nose": 0.05, "bl_skin": 0.08, "bl_vomit": 0.03,
               "bl_stool": 0.03, "bl_urine": 0.02},
}, overrides={
    ("meningococcaemia_purpura", "severe"): {"bl_gums": 0.20, "bl_nose": 0.15, "bl_skin": 0.60,
                                              "bl_vomit": 0.10, "bl_stool": 0.05, "bl_urine": 0.03},
}, source_type=_SRC, source=_SRC_TEXT + " (rash->fever subtree path)")

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
