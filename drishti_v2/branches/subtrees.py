"""
drishti_v2/branches/subtrees.py
=================================
Shared sub-trees (questionnaire-tree-design-memo.md section 5,
branch-authoring-batch-1-memo.md section 6, batch-2-memo section 1 & 8).

Five shared sub-trees:
1. RASH-MORPH v1.0.0-draft (RSH-03 through RSH-09)
2. FEVER-QUAL v1.1-draft (FQ-00 through FQ-03, FQ-G1, FQ-RETURN)
3. TB-SCREEN v1.0.0-draft (TBS-01 through TBS-04, TBS-RETURN)
4. DEHYDRATION v1.0.0-draft (DEH-01 through DEH-05, DEH-G1, DEH-RETURN)
5. EXPOSURE-CONTEXT-FEVER v1.0.0-draft (ECF-01, ECF-RETURN)

Cross-links are references, never copies. Each sub-tree is a fixed DAG
ending at its own TerminalNode.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..answer_model import AnswerModelEntry
from ..schema import (
    AnswerOption, GatewayNode, QuestionNode, TerminalNode,
    any_of, contains, equals, value_of
)
from .authoring import expand_entries


_ASSUMED = {"sourceType": "ASSUMED", "source": "No Indian unknown-rate survey exists; "
            "declared low and flat across nodes.", "declaredOn": "2026-09-06"}

def _no_unknown(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED)


# ---------------------------------------------------------------------------
# 1. RASH-MORPH
# ---------------------------------------------------------------------------

def _gw_rsh_emg1(fields, ctx):
    return equals(fields, "rash_morphology", "rm_purple_spots")


def _gw_rsh_emg2(fields, ctx):
    return equals(fields, "rash_morphology", "rm_fluid_blister") and equals(fields, "new_drug_2_weeks", "nd_yes")


def _gw_rsh_urg1(fields, ctx):
    return (equals(fields, "rash_symptom", "rs_numb")
            or equals(fields, "hypopigmented_patch_sensation", "hp_reduced"))


def make_rash_morph_nodes() -> dict:
    return {
        "RSH-03": QuestionNode(
            nodeId="RSH-03", fieldId="rash_distribution", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("rdst_face_neck", "Face or neck first", next="RSH-04"),
                AnswerOption("rdst_trunk", "Chest, back, or belly", next="RSH-04"),
                AnswerOption("rdst_hands_feet", "Hands, feet, or between fingers", next="RSH-04"),
                AnswerOption("rdst_generalised", "All over the body at once", next="RSH-04"),
                AnswerOption("rdst_one_patch", "One patch or a few patches only", next="RSH-04"),
            ],
            default_next="RSH-04", unknown_option="rdst_unknown", **_no_unknown(0.05),
        ),
        "RSH-04": QuestionNode(
            nodeId="RSH-04", fieldId="rash_morphology", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("rm_flat_red", "Flat red spots", next="RSH-05"),
                AnswerOption("rm_raised", "Raised bumps", next="RSH-05"),
                AnswerOption("rm_fluid_blister", "Fluid-filled blisters", next="RSH-G1"),
                AnswerOption("rm_pustular", "Pus-filled spots", next="RSH-05"),
                AnswerOption("rm_scaly_patch", "Dry, scaly patch", next="RSH-05"),
                AnswerOption("rm_pale_patch", "Pale / lighter-coloured patch", next="RSH-06"),
                AnswerOption("rm_purple_spots", "Purple or red spots that do not fade", next="RSH-G1"),
            ],
            default_next="RSH-05", unknown_option="rm_unknown", **_no_unknown(0.04),
        ),
        "RSH-G1": GatewayNode("RSH-G1", "GW-RSH-EMG-1", _gw_rsh_emg1, next="RSH-G1b",
                               raisesTo="REFER_EMERGENCY",
                               severeConditions=["meningococcaemia", "severe dengue"]),
        "RSH-G1b": GatewayNode("RSH-G1b", "GW-RSH-EMG-2", _gw_rsh_emg2, next="RSH-05",
                                raisesTo="REFER_EMERGENCY", severeConditions=["SJS / TEN"]),
        "RSH-05": QuestionNode(
            nodeId="RSH-05", fieldId="rash_symptom", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("rs_itchy", "Itchy", next="RSH-07"),
                AnswerOption("rs_painful", "Painful", next="RSH-07"),
                AnswerOption("rs_burning", "Burning", next="RSH-07"),
                AnswerOption("rs_numb", "No feeling in it", next="RSH-G2"),
                AnswerOption("rs_none", "Neither", next="RSH-07"),
            ],
            default_next="RSH-07", unknown_option="rs_unknown", **_no_unknown(0.04),
        ),
        "RSH-G2": GatewayNode("RSH-G2", "GW-RSH-URG-1", _gw_rsh_urg1, next="RSH-07",
                               raisesTo="REFER_URGENT", severeConditions=["leprosy"]),
        "RSH-06": QuestionNode(
            nodeId="RSH-06", fieldId="hypopigmented_patch_sensation", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("hp_normal_sensation", "Feels the same", next="RSH-07"),
                AnswerOption("hp_reduced", "Feels less, or nothing", next="RSH-G2"),
            ],
            default_next="RSH-07", unknown_option="hp_unknown", **_no_unknown(0.06),
            guard=lambda fields: equals(fields, "rash_morphology", "rm_pale_patch"),
        ),
        "RSH-07": QuestionNode(
            nodeId="RSH-07", fieldId="new_drug_2_weeks", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("nd_yes", "Yes", next="RSH-G3"),
                AnswerOption("nd_no", "No", next="RSH-08"),
            ],
            default_next="RSH-08", unknown_option="nd_unknown", **_no_unknown(0.03),
        ),
        "RSH-G3": GatewayNode("RSH-G3", "GW-RSH-EMG-2", _gw_rsh_emg2, next="RSH-08",
                               raisesTo="REFER_EMERGENCY", severeConditions=["SJS / TEN"]),
        "RSH-08": QuestionNode(
            nodeId="RSH-08", fieldId="household_others_affected", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("ho_yes", "Yes", next="RSH-09"),
                AnswerOption("ho_no", "No", next="RSH-09"),
            ],
            default_next="RSH-09", unknown_option="ho_unknown", **_no_unknown(0.05),
        ),
        "RSH-09": QuestionNode(
            nodeId="RSH-09", fieldId="attachment_photo_present", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("ph_taken", "Photo taken", next="RSH-END"),
                AnswerOption("ph_declined", "Patient did not consent", next="RSH-END"),
                AnswerOption("ph_not_possible", "Cannot take a photo now", next="RSH-END"),
            ],
            default_next="RSH-END", unknown_option="ph_not_possible", **_no_unknown(0.0),
        ),
        "RSH-END": TerminalNode("RSH-END"),
    }


RASH_MORPH_NODES = make_rash_morph_nodes()


# ---------------------------------------------------------------------------
# 2. FEVER-QUAL v1.1 (absorbs fever_present FQ-00, fpat_* options)
# ---------------------------------------------------------------------------

def _gw_fev_emg3_bleeding_only(fields, ctx):
    return not (value_of(fields, "bleeding_manifestation") in (None, frozenset({"bl_none"}), frozenset({"bl_unknown"})))


def make_fever_qual_nodes() -> dict:
    return {
        "FQ-00": QuestionNode(
            nodeId="FQ-00", fieldId="fever_present", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("fp_yes", "Yes", next="FQ-01"),
                AnswerOption("fp_no", "No", next="FQ-RETURN"),
            ],
            default_next="FQ-RETURN", unknown_option="fp_unknown", **_no_unknown(0.02),
        ),
        "FQ-01": QuestionNode(
            nodeId="FQ-01", fieldId="fever_duration_band", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("fd_today", "Today only", next="FQ-02"),
                AnswerOption("fd_1_3", "1 to 3 days", next="FQ-02"),
                AnswerOption("fd_4_7", "4 to 7 days", next="FQ-02"),
                AnswerOption("fd_8_14", "8 to 14 days", next="FQ-02"),
                AnswerOption("fd_gt_14", "More than 14 days", next="FQ-02"),
            ],
            default_next="FQ-02", unknown_option="fd_unknown", **_no_unknown(0.03),
            guard=lambda fields: equals(fields, "fever_present", "fp_yes"),
        ),
        "FQ-02": QuestionNode(
            nodeId="FQ-02", fieldId="fever_pattern", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("fpat_stepladder", "Rising a little more each day, does not fully settle",
                             next="FQ-03", valueToken="stepladder fever"),
                AnswerOption("fpat_cyclical", "Comes and goes, with shaking chills",
                             next="FQ-03", valueToken="cyclical high fever with chills"),
                AnswerOption("fpat_evening", "Rises in the evening or at night",
                             next="FQ-03", valueToken="evening fever"),
                AnswerOption("fpat_continuous", "High and continuous, no clear pattern",
                             next="FQ-03", valueToken="high fever"),
                AnswerOption("fpat_mild", "Low-grade throughout", next="FQ-03", valueToken="mild fever"),
            ],
            default_next="FQ-03", unknown_option="fpat_unknown", **_no_unknown(0.03),
            guard=lambda fields: equals(fields, "fever_present", "fp_yes"),
        ),
        "FQ-03": QuestionNode(
            nodeId="FQ-03", fieldId="bleeding_manifestation", answerType="MULTI_CHOICE",
            options=[
                AnswerOption("bl_gums", "Bleeding gums", next="FQ-G1"),
                AnswerOption("bl_nose", "Nose bleed", next="FQ-G1"),
                AnswerOption("bl_skin", "Red or purple spots under skin", next="FQ-G1"),
                AnswerOption("bl_vomit", "Blood in vomit", next="FQ-G1"),
                AnswerOption("bl_stool", "Black or bloody stool", next="FQ-G1"),
                AnswerOption("bl_urine", "Blood in urine", next="FQ-G1"),
            ],
            default_next="FQ-G1", unknown_option="bl_unknown", none_option="bl_none",
            **_no_unknown(0.02),
            guard=lambda fields: equals(fields, "fever_present", "fp_yes"),
        ),
        "FQ-G1": GatewayNode("FQ-G1", "GW-FEV-EMG-3", _gw_fev_emg3_bleeding_only,
                              next="FQ-RETURN", routeTo="emergency_heavy_bleeding",
                              severeConditions=["severe dengue", "sepsis with DIC"]),
        "FQ-RETURN": TerminalNode("FQ-RETURN"),
    }


FEVER_QUAL_NODES = make_fever_qual_nodes()


# ---------------------------------------------------------------------------
# 3. TB-SCREEN v1.0.0-draft
# ---------------------------------------------------------------------------

def make_tb_screen_nodes() -> dict:
    return {
        "TBS-01": QuestionNode(
            nodeId="TBS-01", fieldId="cough_ge_2_weeks", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("c2_yes", "Yes", next="TBS-02"),
                AnswerOption("c2_no", "No", next="TBS-02"),
            ],
            default_next="TBS-02", unknown_option="c2_unknown", **_no_unknown(0.02),
        ),
        "TBS-02": QuestionNode(
            nodeId="TBS-02", fieldId="weight_loss_present", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("wl_yes", "Yes", next="TBS-03"),
                AnswerOption("wl_no", "No", next="TBS-03"),
            ],
            default_next="TBS-03", unknown_option="wl_unknown", **_no_unknown(0.02),
        ),
        "TBS-03": QuestionNode(
            nodeId="TBS-03", fieldId="night_sweats", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("ns_yes", "Yes", next="TBS-04"),
                AnswerOption("ns_no", "No", next="TBS-04"),
            ],
            default_next="TBS-04", unknown_option="ns_unknown", **_no_unknown(0.02),
        ),
        "TBS-04": QuestionNode(
            nodeId="TBS-04", fieldId="tb_contact", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("tbc_yes", "Yes", next="TBS-RETURN"),
                AnswerOption("tbc_no", "No", next="TBS-RETURN"),
            ],
            default_next="TBS-RETURN", unknown_option="tbc_unknown", **_no_unknown(0.03),
        ),
        "TBS-RETURN": TerminalNode("TBS-RETURN"),
    }


TB_SCREEN_NODES = make_tb_screen_nodes()


# ---------------------------------------------------------------------------
# 4. DEHYDRATION v1.0.0-draft
# ---------------------------------------------------------------------------

def _gw_deh_urg1(fields, ctx):
    thirst = value_of(fields, "dehydration_thirst")
    eyes = value_of(fields, "dehydration_eyes")
    pinch = value_of(fields, "skin_pinch")
    urine = value_of(fields, "urine_output_reduced")
    gen = value_of(fields, "general_condition")
    return (thirst in ("dt_poor", "dt_unable")
            or pinch == "sp_very_slow"
            or urine == "uo_none_since_yesterday"
            or gen == "gc_lethargic")


def make_dehydration_nodes() -> dict:
    return {
        "DEH-01": QuestionNode(
            nodeId="DEH-01", fieldId="dehydration_thirst", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("dt_normal", "Drinks normally", next="DEH-02"),
                AnswerOption("dt_eager", "Thirsty, drinks eagerly", next="DEH-02"),
                AnswerOption("dt_poor", "Drinks poorly", next="DEH-02"),
                AnswerOption("dt_unable", "Not able to drink at all", next="DEH-02"),
            ],
            default_next="DEH-02", unknown_option="dt_unknown", **_no_unknown(0.03),
        ),
        "DEH-02": QuestionNode(
            nodeId="DEH-02", fieldId="dehydration_eyes", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("de_yes", "Yes", next="DEH-03"),
                AnswerOption("de_no", "No", next="DEH-03"),
            ],
            default_next="DEH-03", unknown_option="de_unknown", **_no_unknown(0.03),
        ),
        "DEH-03": QuestionNode(
            nodeId="DEH-03", fieldId="skin_pinch", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("sp_immediate", "Goes back at once", next="DEH-04"),
                AnswerOption("sp_slow", "Goes back slowly", next="DEH-04"),
                AnswerOption("sp_very_slow", "Takes more than 2 seconds", next="DEH-04"),
            ],
            default_next="DEH-04", unknown_option="sp_unknown", **_no_unknown(0.03),
        ),
        "DEH-04": QuestionNode(
            nodeId="DEH-04", fieldId="urine_output_reduced", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("uo_normal", "Passing urine as usual", next="DEH-05"),
                AnswerOption("uo_reduced", "Less than usual", next="DEH-05"),
                AnswerOption("uo_none_since_yesterday", "Has not passed urine since yesterday", next="DEH-05"),
            ],
            default_next="DEH-05", unknown_option="uo_unknown", **_no_unknown(0.03),
        ),
        "DEH-05": QuestionNode(
            nodeId="DEH-05", fieldId="general_condition", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("gc_alert", "Alert and behaving normally", next="DEH-G1"),
                AnswerOption("gc_restless", "Restless or irritable", next="DEH-G1"),
                AnswerOption("gc_lethargic", "Sleepy, difficult to wake", next="DEH-G1"),
            ],
            default_next="DEH-G1", unknown_option="gc_unknown", **_no_unknown(0.03),
        ),
        "DEH-G1": GatewayNode("DEH-G1", "GW-DEH-URG-1", _gw_deh_urg1, next="DEH-RETURN",
                               raisesTo="REFER_URGENT", severeConditions=["dehydration"]),
        "DEH-RETURN": TerminalNode("DEH-RETURN"),
    }


DEHYDRATION_NODES = make_dehydration_nodes()


# ---------------------------------------------------------------------------
# 5. EXPOSURE-CONTEXT-FEVER v1.0.0-draft (minus ex_tb_contact per G-10)
# ---------------------------------------------------------------------------

def make_exposure_context_fever_nodes() -> dict:
    return {
        "ECF-01": QuestionNode(
            nodeId="ECF-01", fieldId="exposure_context", answerType="MULTI_CHOICE",
            options=[
                AnswerOption("ex_mosquito", "Mosquitoes or standing water at home", next="ECF-RETURN"),
                AnswerOption("ex_household", "Someone else at home has fever", next="ECF-RETURN"),
                AnswerOption("ex_travel", "Travelled in the last month", next="ECF-RETURN"),
                AnswerOption("ex_water_soil", "Works in paddy field / flood water / with animals", next="ECF-RETURN"),
            ],
            default_next="ECF-RETURN", unknown_option="ex_unknown", none_option="ex_none",
            **_no_unknown(0.03),
        ),
        "ECF-RETURN": TerminalNode("ECF-RETURN"),
    }


EXPOSURE_CONTEXT_FEVER_NODES = make_exposure_context_fever_nodes()


# ---------------------------------------------------------------------------
# Answer Model Helpers for Sub-trees
# ---------------------------------------------------------------------------

def expand_tb_screen_entries(conditions: List[str], severities: List[str],
                             tb_conditions: Tuple[str, ...] = ("tuberculosis", "pulmonary_tuberculosis"),
                             source_type: str = "IND-PROG",
                             source: str = "National TB elimination programme Nikshay") -> List[AnswerModelEntry]:
    entries: List[AnswerModelEntry] = []
    _c2_base = {"mild": {"c2_yes": 0.05, "c2_no": 0.95},
                "moderate": {"c2_yes": 0.12, "c2_no": 0.88},
                "severe": {"c2_yes": 0.25, "c2_no": 0.75}}
    _c2_over = {(c, s): {"c2_yes": 0.85, "c2_no": 0.15} for c in tb_conditions for s in severities}
    entries += expand_entries("TBS-01", "categorical", conditions, severities, _c2_base,
                              overrides=_c2_over, source_type=source_type, source=source)

    _wl_base = {"mild": {"wl_yes": 0.04, "wl_no": 0.96},
                "moderate": {"wl_yes": 0.10, "wl_no": 0.90},
                "severe": {"wl_yes": 0.20, "wl_no": 0.80}}
    _wl_over = {(c, s): {"wl_yes": 0.80, "wl_no": 0.20} for c in tb_conditions for s in severities}
    entries += expand_entries("TBS-02", "categorical", conditions, severities, _wl_base,
                              overrides=_wl_over, source_type=source_type, source=source)

    _ns_base = {"mild": {"ns_yes": 0.03, "ns_no": 0.97},
                "moderate": {"ns_yes": 0.08, "ns_no": 0.92},
                "severe": {"ns_yes": 0.15, "ns_no": 0.85}}
    _ns_over = {(c, s): {"ns_yes": 0.75, "ns_no": 0.25} for c in tb_conditions for s in severities}
    entries += expand_entries("TBS-03", "categorical", conditions, severities, _ns_base,
                              overrides=_ns_over, source_type=source_type, source=source)

    _tbc_base = {s: {"tbc_yes": 0.04, "tbc_no": 0.96} for s in severities}
    _tbc_over = {(c, s): {"tbc_yes": 0.40, "tbc_no": 0.60} for c in tb_conditions for s in severities}
    entries += expand_entries("TBS-04", "categorical", conditions, severities, _tbc_base,
                              overrides=_tbc_over, source_type=source_type, source=source)
    return entries


def expand_dehydration_entries(conditions: List[str], severities: List[str],
                               dehydration_conditions: Tuple[str, ...] = ("dehydration", "cholera", "gastroenteritis"),
                               source_type: str = "WORLD",
                               source: str = "WHO IMCI dehydration assessment guideline") -> List[AnswerModelEntry]:
    entries: List[AnswerModelEntry] = []
    _dt_base = {
        "mild": {"dt_normal": 0.80, "dt_eager": 0.15, "dt_poor": 0.04, "dt_unable": 0.01},
        "moderate": {"dt_normal": 0.40, "dt_eager": 0.45, "dt_poor": 0.12, "dt_unable": 0.03},
        "severe": {"dt_normal": 0.15, "dt_eager": 0.35, "dt_poor": 0.35, "dt_unable": 0.15},
    }
    _dt_over = {}
    for c in dehydration_conditions:
        _dt_over[(c, "severe")] = {"dt_normal": 0.05, "dt_eager": 0.25, "dt_poor": 0.40, "dt_unable": 0.30}
    entries += expand_entries("DEH-01", "categorical", conditions, severities, _dt_base,
                              overrides=_dt_over, source_type=source_type, source=source)

    _de_base = {
        "mild": {"de_yes": 0.05, "de_no": 0.95},
        "moderate": {"de_yes": 0.30, "de_no": 0.70},
        "severe": {"de_yes": 0.70, "de_no": 0.30},
    }
    entries += expand_entries("DEH-02", "categorical", conditions, severities, _de_base,
                              source_type=source_type, source=source)

    _sp_base = {
        "mild": {"sp_immediate": 0.90, "sp_slow": 0.09, "sp_very_slow": 0.01},
        "moderate": {"sp_immediate": 0.50, "sp_slow": 0.42, "sp_very_slow": 0.08},
        "severe": {"sp_immediate": 0.20, "sp_slow": 0.45, "sp_very_slow": 0.35},
    }
    entries += expand_entries("DEH-03", "categorical", conditions, severities, _sp_base,
                              source_type=source_type, source=source)

    _uo_base = {
        "mild": {"uo_normal": 0.85, "uo_reduced": 0.13, "uo_none_since_yesterday": 0.02},
        "moderate": {"uo_normal": 0.45, "uo_reduced": 0.45, "uo_none_since_yesterday": 0.10},
        "severe": {"uo_normal": 0.15, "uo_reduced": 0.50, "uo_none_since_yesterday": 0.35},
    }
    entries += expand_entries("DEH-04", "categorical", conditions, severities, _uo_base,
                              source_type=source_type, source=source)

    _gc_base = {
        "mild": {"gc_alert": 0.90, "gc_restless": 0.08, "gc_lethargic": 0.02},
        "moderate": {"gc_alert": 0.60, "gc_restless": 0.32, "gc_lethargic": 0.08},
        "severe": {"gc_alert": 0.25, "gc_restless": 0.40, "gc_lethargic": 0.35},
    }
    entries += expand_entries("DEH-05", "categorical", conditions, severities, _gc_base,
                              source_type=source_type, source=source)
    return entries


def expand_fever_qual_entries(conditions: List[str], severities: List[str],
                              fever_conditions: Tuple[str, ...] = (),
                              bleeding_conditions: Tuple[str, ...] = (),
                              source_type: str = "ASSUMED",
                              source: str = "Clinical presentation distribution") -> List[AnswerModelEntry]:
    entries: List[AnswerModelEntry] = []
    _fp_base = {
        "mild": {"fp_yes": 0.15, "fp_no": 0.85},
        "moderate": {"fp_yes": 0.30, "fp_no": 0.70},
        "severe": {"fp_yes": 0.45, "fp_no": 0.55},
    }
    _fp_over = {}
    for c in fever_conditions:
        for s in severities:
            _fp_over[(c, s)] = {"fp_yes": 0.90, "fp_no": 0.10}
    entries += expand_entries("FQ-00", "categorical", conditions, severities, _fp_base,
                              overrides=_fp_over, source_type=source_type, source=source)

    _fd_base = {s: {"fd_today": 0.25, "fd_1_3": 0.45, "fd_4_7": 0.20, "fd_8_14": 0.07, "fd_gt_14": 0.03}
                for s in severities}
    entries += expand_entries("FQ-01", "categorical", conditions, severities, _fd_base,
                              source_type=source_type, source=source)

    _fpat_base = {s: {"fpat_mild": 0.40, "fpat_continuous": 0.30, "fpat_evening": 0.12,
                      "fpat_cyclical": 0.10, "fpat_stepladder": 0.08} for s in severities}
    entries += expand_entries("FQ-02", "categorical", conditions, severities, _fpat_base,
                              source_type=source_type, source=source)

    _bl_base = {
        "mild": {"bl_gums": 0.002, "bl_nose": 0.002, "bl_skin": 0.002, "bl_vomit": 0.001,
                 "bl_stool": 0.001, "bl_urine": 0.001},
        "moderate": {"bl_gums": 0.01, "bl_nose": 0.01, "bl_skin": 0.02, "bl_vomit": 0.005,
                     "bl_stool": 0.005, "bl_urine": 0.005},
        "severe": {"bl_gums": 0.04, "bl_nose": 0.04, "bl_skin": 0.06, "bl_vomit": 0.02,
                   "bl_stool": 0.02, "bl_urine": 0.02},
    }
    _bl_over = {}
    for c in bleeding_conditions:
        _bl_over[(c, "severe")] = {"bl_gums": 0.20, "bl_nose": 0.15, "bl_skin": 0.45,
                                   "bl_vomit": 0.10, "bl_stool": 0.10, "bl_urine": 0.05}
    entries += expand_entries("FQ-03", "multi_bernoulli", conditions, severities, _bl_base,
                              overrides=_bl_over, source_type=source_type, source=source)
    return entries


def expand_exposure_context_entries(conditions: List[str], severities: List[str],
                                    source_type: str = "ASSUMED",
                                    source: str = "Regional exposure baseline") -> List[AnswerModelEntry]:
    return expand_entries("ECF-01", "multi_bernoulli", conditions, severities, {
        s: {"ex_mosquito": 0.25, "ex_household": 0.15, "ex_travel": 0.08, "ex_water_soil": 0.12}
        for s in severities
    }, source_type=source_type, source=source)
