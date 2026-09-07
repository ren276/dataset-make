"""
drishti_v2/branches/injury.py
The `injury` branch (branch-authoring-batch-2-memo.md section 6).
"""
from __future__ import annotations
from typing import Dict, List
from ..schema import (
    AnswerOption, BranchDef, GatewayNode, QuestionNode, TerminalNode,
    any_of, contains, equals, value_of
)
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries, peaked
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "injury"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "REFER_URGENT"

CONDITIONS = {
    "minor_contusion_or_abrasion": ConditionSpec("minor_contusion_or_abrasion", 0.45, "IND-PRESENT",
        "Minor superficial injury, scrape or blunt contusion"),
    "closed_fracture_or_severe_sprain": ConditionSpec("closed_fracture_or_severe_sprain", 0.22, "IND-PRESENT",
        "Limb bone fracture or joint sprain", severeConditions=("fracture",)),
    "open_laceration_requiring_suture": ConditionSpec("open_laceration_requiring_suture", 0.15, "IND-PRESENT",
        "Skin laceration requiring primary closure / tetanus"),
    "head_injury_concussion": ConditionSpec("head_injury_concussion", 0.08, "IND-PRESENT",
        "Closed head injury / concussion / subdural risk", severeConditions=("head injury",)),
    "animal_bite_rabies_risk": ConditionSpec("animal_bite_rabies_risk", 0.06, "IND-PRESENT",
        "Animal bite requiring post-exposure prophylaxis", severeConditions=("tetanus-prone wound",)),
    "burn_thermal_or_chemical": ConditionSpec("burn_thermal_or_chemical", 0.04, "IND-PRESENT",
        "Thermal or scalding burn", severeConditions=("burn",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "minor_contusion_or_abrasion": {"mild": 0.75, "moderate": 0.22, "severe": 0.03},
    "closed_fracture_or_severe_sprain": {"mild": 0.20, "moderate": 0.55, "severe": 0.25},
    "open_laceration_requiring_suture": {"mild": 0.30, "moderate": 0.50, "severe": 0.20},
    "head_injury_concussion": {"mild": 0.15, "moderate": 0.45, "severe": 0.40},
    "animal_bite_rabies_risk": {"mild": 0.35, "moderate": 0.45, "severe": 0.20},
    "burn_thermal_or_chemical": {"mild": 0.20, "moderate": 0.45, "severe": 0.35},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sbp = specs["bp_systolic"]

    if condition_id in ("head_injury_concussion", "burn_thermal_or_chemical") and severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 20, 12.0, 35, 220)
        specs["bp_systolic"] = VitalSpec(base_sbp.mean - 12, 10.0, 50, 200)
    elif severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 10, base_pulse.sd, 35, 220)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_inj_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_inj_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_heavy_bleeding")

def _gw_inj_emg3_stage_a(fields, ctx):
    return contains(fields, "danger_signs", "ds_head_injury_signs")

def _gw_inj_emg4_stage_a(fields, ctx):
    return contains(fields, "danger_signs", "ds_deformity") and contains(fields, "danger_signs", "ds_cannot_move_limb")

def _gw_inj_emg5_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_inj_emg3_full(fields, ctx):
    return contains(fields, "danger_signs", "ds_head_injury_signs") or equals(fields, "head_injury_features", "hi_yes_confusion")

def _gw_inj_emg4_full(fields, ctx):
    return any_of(fields, "injury_mechanism", ["im_road", "im_assault"]) or (
        contains(fields, "danger_signs", "ds_deformity") and contains(fields, "danger_signs", "ds_cannot_move_limb")
    )

def _gw_inj_urg1_fracture(fields, ctx):
    return any_of(fields, "deformity_or_unable_to_move", ["dm_deformity", "dm_no_move", "dm_both"]) or contains(fields, "danger_signs", "ds_deformity") or contains(fields, "danger_signs", "ds_cannot_move_limb")

def _gw_inj_urg2_tetanus(fields, ctx):
    return (any_of(fields, "wound_type", ["wt_puncture", "wt_crush"]) and any_of(fields, "tetanus_status", ["ts_no", "ts_unknown"])) or (
        equals(fields, "injury_mechanism", "im_animal") and any_of(fields, "tetanus_status", ["ts_no", "ts_unknown"])
    )

def _gw_inj_urg3_burn(fields, ctx):
    return contains(fields, "danger_signs", "ds_burn_large") or equals(fields, "wound_type", "wt_burn_wound") or equals(fields, "injury_mechanism", "im_burn")

def _gw_inj_urg4_rabies(fields, ctx):
    return equals(fields, "injury_mechanism", "im_animal")

_NODES = {
    "INJ-00": QuestionNode(
        nodeId="INJ-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_heavy_bleeding", "Bleeding that will not stop with pressure", next="INJ-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="INJ-G1a"),
            AnswerOption("ds_deformity", "Obvious deformity of a limb", next="INJ-G1a"),
            AnswerOption("ds_cannot_move_limb", "Cannot move an arm or leg at all", next="INJ-G1a"),
            AnswerOption("ds_wound_deep", "A deep wound — fat or bone visible", next="INJ-G1a"),
            AnswerOption("ds_head_injury_signs", "Hit on the head and now confused or vomiting", next="INJ-G1a"),
            AnswerOption("ds_burn_large", "A burn larger than the patient's palm", next="INJ-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="INJ-G1a"),
        ],
        default_next="INJ-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "INJ-G1a": GatewayNode("INJ-G1a", "GW-INJ-EMG-1", _gw_inj_emg1, next="INJ-G1b",
                           routeTo="emergency_unconscious", severeConditions=["head injury", "haemorrhagic shock"]),
    "INJ-G1b": GatewayNode("INJ-G1b", "GW-INJ-EMG-2", _gw_inj_emg2, next="INJ-G1c",
                           routeTo="emergency_heavy_bleeding", severeConditions=["haemorrhage"]),
    "INJ-G1c": GatewayNode("INJ-G1c", "GW-INJ-EMG-3", _gw_inj_emg3_stage_a, next="INJ-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["head injury with raised ICP", "subdural haematoma"]),
    "INJ-G1d": GatewayNode("INJ-G1d", "GW-INJ-EMG-4", _gw_inj_emg4_stage_a, next="INJ-G1e",
                           raisesTo="REFER_EMERGENCY", severeConditions=["open fracture", "internal haemorrhage", "polytrauma"]),
    "INJ-G1e": GatewayNode("INJ-G1e", "GW-INJ-EMG-5", _gw_inj_emg5_infant, next="INJ-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "INJ-01": QuestionNode(
        nodeId="INJ-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="INJ-02"),
            AnswerOption("pr_same", "About the same", next="INJ-02"),
            AnswerOption("pr_worse", "Worse", next="INJ-02"),
        ],
        default_next="INJ-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "INJ-02": QuestionNode(
        nodeId="INJ-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="INJ-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="INJ-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="INJ-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="INJ-03"),
            AnswerOption("pt_other", "Other treatment", next="INJ-03"),
        ],
        default_next="INJ-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "INJ-03": QuestionNode(
        nodeId="INJ-03", fieldId="injury_mechanism", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("im_fall", "Fall", next="INJ-04"),
            AnswerOption("im_road", "Road accident", next="INJ-04"),
            AnswerOption("im_hit_object", "Hit by or against an object", next="INJ-04"),
            AnswerOption("im_cut_sharp", "Cut by a sharp object", next="INJ-04"),
            AnswerOption("im_burn", "Burn — fire, hot liquid, or chemical", next="INJ-04"),
            AnswerOption("im_animal", "Animal bite or scratch", next="INJ-04"),
            AnswerOption("im_assault", "Assault or violence", next="INJ-04"),
            AnswerOption("im_other", "Something else", next="INJ-04"),
        ],
        default_next="INJ-04", unknown_option="im_unknown", **_nu(0.03)
    ),
    "INJ-04": QuestionNode(
        nodeId="INJ-04", fieldId="time_since_injury", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ti_lt_1hr", "Less than 1 hour", next="INJ-05"),
            AnswerOption("ti_1_6hr", "1 to 6 hours", next="INJ-05"),
            AnswerOption("ti_6_24hr", "6 to 24 hours", next="INJ-05"),
            AnswerOption("ti_gt_24hr", "More than 24 hours ago", next="INJ-05"),
        ],
        default_next="INJ-05", unknown_option="ti_unknown", **_nu(0.03)
    ),
    "INJ-05": QuestionNode(
        nodeId="INJ-05", fieldId="wound_type", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("wt_abrasion", "Scrape or graze", next="INJ-06"),
            AnswerOption("wt_laceration", "A cut or tear with edges that could be brought together", next="INJ-06"),
            AnswerOption("wt_puncture", "A small deep hole — nail, thorn, bite", next="INJ-06"),
            AnswerOption("wt_crush", "Crushed tissue — heavy object fell on it", next="INJ-06"),
            AnswerOption("wt_burn_wound", "A burn — red, blistered or charred", next="INJ-06"),
            AnswerOption("wt_no_wound", "No open wound — bruise or swelling only", next="INJ-06"),
        ],
        default_next="INJ-06", unknown_option="wt_unknown", **_nu(0.03)
    ),
    "INJ-06": QuestionNode(
        nodeId="INJ-06", fieldId="tetanus_status", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ts_yes", "Yes", next="INJ-07"),
            AnswerOption("ts_no", "No", next="INJ-07"),
        ],
        default_next="INJ-07", unknown_option="ts_unknown", **_nu(0.03)
    ),
    "INJ-07": QuestionNode(
        nodeId="INJ-07", fieldId="deformity_or_unable_to_move", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("dm_deformity", "Yes — the limb looks bent or out of shape", next="INJ-08"),
            AnswerOption("dm_no_move", "Cannot move it at all", next="INJ-08"),
            AnswerOption("dm_both", "Both", next="INJ-08"),
            AnswerOption("dm_no", "No deformity, can move it", next="INJ-08"),
        ],
        default_next="INJ-08", unknown_option="dm_unknown", **_nu(0.03)
    ),
    "INJ-08": QuestionNode(
        nodeId="INJ-08", fieldId="head_injury_features", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hi_yes_confusion", "Yes — now confused, or vomited since", next="INJ-G2a"),
            AnswerOption("hi_yes_no_signs", "Hit on the head, but alert and no vomiting", next="INJ-G2a"),
            AnswerOption("hi_no", "Head was not hit", next="INJ-G2a"),
        ],
        default_next="INJ-G2a", unknown_option="hi_unknown", **_nu(0.03)
    ),

    "INJ-G2a": GatewayNode("INJ-G2a", "GW-INJ-EMG-3", _gw_inj_emg3_full, next="INJ-G2b",
                           raisesTo="REFER_EMERGENCY", severeConditions=["head injury with raised ICP", "subdural haematoma"]),
    "INJ-G2b": GatewayNode("INJ-G2b", "GW-INJ-EMG-4", _gw_inj_emg4_full, next="INJ-G2c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["open fracture", "internal haemorrhage", "polytrauma"]),
    "INJ-G2c": GatewayNode("INJ-G2c", "GW-INJ-URG-1", _gw_inj_urg1_fracture, next="INJ-G2d",
                           raisesTo="REFER_URGENT", severeConditions=["fracture", "dislocation"]),
    "INJ-G2d": GatewayNode("INJ-G2d", "GW-INJ-URG-2", _gw_inj_urg2_tetanus, next="INJ-G2e",
                           raisesTo="REFER_URGENT", severeConditions=["tetanus-prone wound"]),
    "INJ-G2e": GatewayNode("INJ-G2e", "GW-INJ-URG-3", _gw_inj_urg3_burn, next="INJ-G2f",
                           raisesTo="REFER_URGENT", severeConditions=["burn requiring specialized care"]),
    "INJ-G2f": GatewayNode("INJ-G2f", "GW-INJ-URG-4", _gw_inj_urg4_rabies, next="INJ-END",
                           raisesTo="REFER_URGENT", severeConditions=["rabies", "wound infection"]),
    "INJ-END": TerminalNode("INJ-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="INJ-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Injury clinical distribution"

_entries = []

_entries += expand_entries("INJ-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_heavy_bleeding": 0.005, "ds_unconscious": 0.001, "ds_deformity": 0.005,
             "ds_cannot_move_limb": 0.01, "ds_wound_deep": 0.005, "ds_head_injury_signs": 0.005,
             "ds_burn_large": 0.002, "ds_cannot_feed": 0.002},
    "moderate": {"ds_heavy_bleeding": 0.05, "ds_unconscious": 0.005, "ds_deformity": 0.08,
                "ds_cannot_move_limb": 0.08, "ds_wound_deep": 0.05, "ds_head_injury_signs": 0.03,
                "ds_burn_large": 0.02, "ds_cannot_feed": 0.01},
    "severe": {"ds_heavy_bleeding": 0.20, "ds_unconscious": 0.05, "ds_deformity": 0.35,
               "ds_cannot_move_limb": 0.35, "ds_wound_deep": 0.20, "ds_head_injury_signs": 0.20,
               "ds_burn_large": 0.15, "ds_cannot_feed": 0.05},
}, overrides={
    ("closed_fracture_or_severe_sprain", "severe"): {"ds_heavy_bleeding": 0.02, "ds_unconscious": 0.01, "ds_deformity": 0.85,
                                                    "ds_cannot_move_limb": 0.85, "ds_wound_deep": 0.05, "ds_head_injury_signs": 0.01,
                                                    "ds_burn_large": 0.00, "ds_cannot_feed": 0.01},
    ("head_injury_concussion", "severe"): {"ds_heavy_bleeding": 0.05, "ds_unconscious": 0.25, "ds_deformity": 0.02,
                                          "ds_cannot_move_limb": 0.05, "ds_wound_deep": 0.10, "ds_head_injury_signs": 0.85,
                                          "ds_burn_large": 0.00, "ds_cannot_feed": 0.05},
    ("burn_thermal_or_chemical", "severe"): {"ds_heavy_bleeding": 0.00, "ds_unconscious": 0.05, "ds_deformity": 0.01,
                                            "ds_cannot_move_limb": 0.05, "ds_wound_deep": 0.10, "ds_head_injury_signs": 0.01,
                                            "ds_burn_large": 0.85, "ds_cannot_feed": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.40, "pr_same": 0.50, "pr_worse": 0.10},
    "moderate": {"pr_better": 0.15, "pr_same": 0.55, "pr_worse": 0.30},
    "severe": {"pr_better": 0.05, "pr_same": 0.30, "pr_worse": 0.65},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.35, "pt_ayush": 0.05,
        "pt_prescribed_prior": 0.10, "pt_other": 0.10}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"im_fall": 0.45, "im_road": 0.10, "im_hit_object": 0.20, "im_cut_sharp": 0.15, "im_burn": 0.03, "im_animal": 0.03, "im_assault": 0.02, "im_other": 0.02},
    "moderate": {"im_fall": 0.40, "im_road": 0.20, "im_hit_object": 0.15, "im_cut_sharp": 0.12, "im_burn": 0.05, "im_animal": 0.04, "im_assault": 0.02, "im_other": 0.02},
    "severe": {"im_fall": 0.35, "im_road": 0.30, "im_hit_object": 0.12, "im_cut_sharp": 0.08, "im_burn": 0.06, "im_animal": 0.04, "im_assault": 0.03, "im_other": 0.02},
}, overrides={
    ("burn_thermal_or_chemical", "mild"): {"im_fall": 0.01, "im_road": 0.00, "im_hit_object": 0.00, "im_cut_sharp": 0.00, "im_burn": 0.98, "im_animal": 0.00, "im_assault": 0.00, "im_other": 0.01},
    ("burn_thermal_or_chemical", "moderate"): {"im_fall": 0.01, "im_road": 0.00, "im_hit_object": 0.00, "im_cut_sharp": 0.00, "im_burn": 0.98, "im_animal": 0.00, "im_assault": 0.00, "im_other": 0.01},
    ("burn_thermal_or_chemical", "severe"): {"im_fall": 0.01, "im_road": 0.00, "im_hit_object": 0.00, "im_cut_sharp": 0.00, "im_burn": 0.98, "im_animal": 0.00, "im_assault": 0.00, "im_other": 0.01},
    ("animal_bite_rabies_risk", "moderate"): {"im_fall": 0.00, "im_road": 0.00, "im_hit_object": 0.00, "im_cut_sharp": 0.00, "im_burn": 0.00, "im_animal": 0.99, "im_assault": 0.00, "im_other": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-04", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ti_lt_1hr": 0.25, "ti_1_6hr": 0.40, "ti_6_24hr": 0.25, "ti_gt_24hr": 0.10}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"wt_abrasion": 0.45, "wt_laceration": 0.15, "wt_puncture": 0.05, "wt_crush": 0.02, "wt_burn_wound": 0.03, "wt_no_wound": 0.30},
    "moderate": {"wt_abrasion": 0.25, "wt_laceration": 0.35, "wt_puncture": 0.08, "wt_crush": 0.05, "wt_burn_wound": 0.05, "wt_no_wound": 0.22},
    "severe": {"wt_abrasion": 0.10, "wt_laceration": 0.40, "wt_puncture": 0.10, "wt_crush": 0.12, "wt_burn_wound": 0.08, "wt_no_wound": 0.20},
}, overrides={
    ("closed_fracture_or_severe_sprain", "moderate"): {"wt_abrasion": 0.15, "wt_laceration": 0.05, "wt_puncture": 0.01, "wt_crush": 0.05, "wt_burn_wound": 0.00, "wt_no_wound": 0.74},
    ("closed_fracture_or_severe_sprain", "severe"): {"wt_abrasion": 0.10, "wt_laceration": 0.10, "wt_puncture": 0.01, "wt_crush": 0.10, "wt_burn_wound": 0.00, "wt_no_wound": 0.69},
    ("open_laceration_requiring_suture", "moderate"): {"wt_abrasion": 0.05, "wt_laceration": 0.85, "wt_puncture": 0.05, "wt_crush": 0.03, "wt_burn_wound": 0.00, "wt_no_wound": 0.02},
    ("burn_thermal_or_chemical", "moderate"): {"wt_abrasion": 0.01, "wt_laceration": 0.00, "wt_puncture": 0.00, "wt_crush": 0.00, "wt_burn_wound": 0.98, "wt_no_wound": 0.01},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ts_yes": 0.50, "ts_no": 0.50} for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"dm_deformity": 0.02, "dm_no_move": 0.03, "dm_both": 0.01, "dm_no": 0.94},
    "moderate": {"dm_deformity": 0.10, "dm_no_move": 0.15, "dm_both": 0.05, "dm_no": 0.70},
    "severe": {"dm_deformity": 0.30, "dm_no_move": 0.35, "dm_both": 0.20, "dm_no": 0.15},
}, overrides={
    ("closed_fracture_or_severe_sprain", "moderate"): {"dm_deformity": 0.25, "dm_no_move": 0.40, "dm_both": 0.15, "dm_no": 0.20},
    ("closed_fracture_or_severe_sprain", "severe"): {"dm_deformity": 0.40, "dm_no_move": 0.30, "dm_both": 0.25, "dm_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("INJ-08", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"hi_yes_confusion": 0.01, "hi_yes_no_signs": 0.10, "hi_no": 0.89},
    "moderate": {"hi_yes_confusion": 0.05, "hi_yes_no_signs": 0.18, "hi_no": 0.77},
    "severe": {"hi_yes_confusion": 0.20, "hi_yes_no_signs": 0.25, "hi_no": 0.55},
}, overrides={
    ("head_injury_concussion", "moderate"): {"hi_yes_confusion": 0.35, "hi_yes_no_signs": 0.55, "hi_no": 0.10},
    ("head_injury_concussion", "severe"): {"hi_yes_confusion": 0.75, "hi_yes_no_signs": 0.20, "hi_no": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
