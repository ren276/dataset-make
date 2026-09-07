"""
drishti_v2/branches/vomiting_nausea.py
The `vomiting_nausea` branch (branch-authoring-batch-3-memo.md section 2).
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
    make_dehydration_nodes, make_fever_qual_nodes,
    expand_dehydration_entries, expand_fever_qual_entries
)

CATEGORY_ID = "vomiting_nausea"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "acute_gastritis_gastroenteritis_vomiting": ConditionSpec("acute_gastritis_gastroenteritis_vomiting", 0.55, "IND-PRESENT",
        "Acute viral/food-borne gastroenteritis or gastritis"),
    "hyperemesis_or_early_pregnancy_vomiting": ConditionSpec("hyperemesis_or_early_pregnancy_vomiting", 0.15, "IND-PRESENT",
        "Nausea and vomiting of pregnancy / hyperemesis", severeConditions=("pregnancy (hyperemesis / ectopic)",)),
    "bowel_obstruction_vomiting": ConditionSpec("bowel_obstruction_vomiting", 0.10, "WORLD",
        "Mechanical intestinal obstruction", severeConditions=("obstruction",)),
    "acute_poisoning_toxic_ingestion": ConditionSpec("acute_poisoning_toxic_ingestion", 0.08, "IND-PRESENT",
        "Toxic ingestion / chemical or pesticide poisoning", severeConditions=("poisoning",)),
    "diabetic_ketoacidosis_vomiting": ConditionSpec("diabetic_ketoacidosis_vomiting", 0.06, "ASSUMED",
        "DKA presenting primarily with vomiting", severeConditions=("DKA",)),
    "raised_intracranial_pressure_vomiting": ConditionSpec("raised_intracranial_pressure_vomiting", 0.06, "ASSUMED",
        "Raised ICP from CNS infection, trauma or lesion", severeConditions=("raised intracranial pressure",)),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "acute_gastritis_gastroenteritis_vomiting": {"mild": 0.65, "moderate": 0.25, "severe": 0.10},
    "hyperemesis_or_early_pregnancy_vomiting": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "bowel_obstruction_vomiting": {"mild": 0.05, "moderate": 0.35, "severe": 0.60},
    "acute_poisoning_toxic_ingestion": {"mild": 0.10, "moderate": 0.40, "severe": 0.50},
    "diabetic_ketoacidosis_vomiting": {"mild": 0.05, "moderate": 0.35, "severe": 0.60},
    "raised_intracranial_pressure_vomiting": {"mild": 0.10, "moderate": 0.40, "severe": 0.50},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_pulse = specs["pulse"]
    base_sbp = specs["bp_systolic"]
    base_dbp = specs["bp_diastolic"]
    base_temp = specs["temperature"]

    if severity_band == "severe":
        specs["pulse"] = VitalSpec(base_pulse.mean + 20, 10.0, 35, 220)
        specs["bp_systolic"] = VitalSpec(base_sbp.mean - 15, 8.0, 50, 200)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_vmt_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_convulsion")

def _gw_vmt_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")

def _gw_vmt_emg3(fields, ctx):
    return any_of(fields, "poisoning_suspected", ["ps_medicine", "ps_pesticide", "ps_other"])

def _gw_vmt_emg4(fields, ctx):
    return contains(fields, "danger_signs", "ds_vomiting_blood") or equals(fields, "vomit_content", "vc_blood")

def _gw_vmt_emg5(fields, ctx):
    return contains(fields, "danger_signs", "ds_severe_headache") and contains(fields, "danger_signs", "ds_confusion")

def _gw_vmt_emg6_infant(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")

def _gw_vmt_urg1_obstruction(fields, ctx):
    return (equals(fields, "vomit_content", "vc_bile") and equals(fields, "bowels_open", "bo_nothing")) or (
        contains(fields, "danger_signs", "ds_abdomen_rigid") and contains(fields, "danger_signs", "ds_vomiting_every")
    )

def _gw_vmt_urg2_dka(fields, ctx):
    return contains(fields, "relevant_history", "diabetes") and contains(fields, "danger_signs", "ds_vomiting_every")

def _gw_vmt_urg3_pregnancy(fields, ctx):
    return any_of(fields, "lmp_known", ["lmp_late_or_missed", "lmp_gt_3_months"]) and (
        contains(fields, "danger_signs", "ds_vomiting_every") or equals(fields, "vomit_frequency_band", "vf_gt_10")
    )

def _gw_vmt_urg4_dehydration(fields, ctx):
    return any_of(fields, "dehydration_thirst", ["dt_poor", "dt_unable"]) or equals(fields, "skin_pinch", "sp_very_slow") or equals(fields, "urine_output_reduced", "uo_none_since_yesterday") or equals(fields, "general_condition", "gc_lethargic")

_NODES = {
    "VMT-00": QuestionNode(
        nodeId="VMT-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_vomiting_blood", "Vomiting blood or dark material like coffee grounds", next="VMT-G1a"),
            AnswerOption("ds_vomiting_every", "Cannot keep any fluids down at all", next="VMT-G1a"),
            AnswerOption("ds_abdomen_rigid", "Abdomen is hard and very tender", next="VMT-G1a"),
            AnswerOption("ds_confusion", "Confused, or behaviour unusual", next="VMT-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="VMT-G1a"),
            AnswerOption("ds_convulsion", "Fits or convulsions", next="VMT-G1a"),
            AnswerOption("ds_severe_headache", "Severe headache that came on suddenly", next="VMT-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="VMT-G1a"),
        ],
        default_next="VMT-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02)
    ),
    "VMT-G1a": GatewayNode("VMT-G1a", "GW-VMT-EMG-1", _gw_vmt_emg1, next="VMT-G1b",
                           routeTo="emergency_convulsions", severeConditions=["eclampsia", "meningitis", "cerebral malaria"]),
    "VMT-G1b": GatewayNode("VMT-G1b", "GW-VMT-EMG-2", _gw_vmt_emg2, next="VMT-G1c",
                           routeTo="emergency_unconscious", severeConditions=["DKA", "poisoning", "raised ICP"]),
    "VMT-G1c": GatewayNode("VMT-G1c", "GW-VMT-EMG-4", _gw_vmt_emg4, next="VMT-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["upper GI haemorrhage", "variceal bleeding"]),
    "VMT-G1d": GatewayNode("VMT-G1d", "GW-VMT-EMG-5", _gw_vmt_emg5, next="VMT-G1e",
                           raisesTo="REFER_EMERGENCY", severeConditions=["raised intracranial pressure", "stroke", "meningitis"]),
    "VMT-G1e": GatewayNode("VMT-G1e", "GW-VMT-EMG-6", _gw_vmt_emg6_infant, next="VMT-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "VMT-01": QuestionNode(
        nodeId="VMT-01", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="VMT-02"),
            AnswerOption("pr_same", "About the same", next="VMT-02"),
            AnswerOption("pr_worse", "Worse", next="VMT-02"),
        ],
        default_next="VMT-02", unknown_option="pr_unknown", **_nu(0.03)
    ),
    "VMT-02": QuestionNode(
        nodeId="VMT-02", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies or rest", next="VMT-03"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy or shop", next="VMT-03"),
            AnswerOption("pt_ayush", "Traditional or AYUSH remedy", next="VMT-03"),
            AnswerOption("pt_prescribed_prior", "Previously prescribed medicine for this condition", next="VMT-03"),
            AnswerOption("pt_other", "Other treatment", next="VMT-03"),
        ],
        default_next="VMT-03", unknown_option="pt_unknown", none_option="pt_none", **_nu(0.03)
    ),

    "VMT-03": QuestionNode(
        nodeId="VMT-03", fieldId="vomit_frequency_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vf_1_3", "1 to 3 times", next="VMT-04"),
            AnswerOption("vf_4_10", "4 to 10 times", next="VMT-04"),
            AnswerOption("vf_gt_10", "More than 10 times", next="VMT-04"),
        ],
        default_next="VMT-04", unknown_option="vf_unknown", **_nu(0.03)
    ),
    "VMT-04": QuestionNode(
        nodeId="VMT-04", fieldId="vomit_content", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vc_food", "Food only", next="VMT-05"),
            AnswerOption("vc_bile", "Green or yellow (bile)", next="VMT-05"),
            AnswerOption("vc_blood", "Blood or dark material", next="VMT-05"),
            AnswerOption("vc_clear", "Clear fluid or water", next="VMT-05"),
        ],
        default_next="VMT-05", unknown_option="vc_unknown", **_nu(0.03)
    ),
    "VMT-05": QuestionNode(
        nodeId="VMT-05", fieldId="vomiting_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vm_yes_keeping_fluids", "Yes — keeping some fluids down", next="VMT-06"),
            AnswerOption("vm_yes_everything", "Yes — vomiting everything", next="VMT-06"),
            AnswerOption("vm_no", "No vomiting", next="VMT-06"),
        ],
        default_next="VMT-06", unknown_option="vm_unknown", **_nu(0.03)
    ),
    "VMT-06": QuestionNode(
        nodeId="VMT-06", fieldId="poisoning_suspected", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ps_medicine", "Yes — too many tablets or wrong medicine", next="VMT-G_poi"),
            AnswerOption("ps_pesticide", "Yes — pesticide, rat poison, or chemical", next="VMT-G_poi"),
            AnswerOption("ps_other", "Yes — something else", next="VMT-G_poi"),
            AnswerOption("ps_no", "No", next="VMT-07"),
        ],
        default_next="VMT-07", unknown_option="ps_unknown", **_nu(0.03)
    ),
    "VMT-G_poi": GatewayNode("VMT-G_poi", "GW-VMT-EMG-3", _gw_vmt_emg3, next="VMT-07",
                             routeTo="emergency_poisoning", severeConditions=["poisoning"]),
    "VMT-07": QuestionNode(
        nodeId="VMT-07", fieldId="bowels_open", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("bo_normal", "Yes — normal stool", next="VMT-08"),
            AnswerOption("bo_loose", "Yes — loose stool", next="VMT-08"),
            AnswerOption("bo_nothing", "No — nothing passed", next="VMT-08"),
        ],
        default_next="VMT-08", unknown_option="bo_unknown", **_nu(0.03)
    ),
    "VMT-08": QuestionNode(
        nodeId="VMT-08", fieldId="lmp_known", answerType="SINGLE_CHOICE",
        guard=lambda fields: fields.get("_sex") is not None and fields["_sex"].value == "F" and fields.get("_age_years") is not None and 15 <= fields["_age_years"].value <= 49,
        options=[
            AnswerOption("lmp_within_4wk", "Within the last 4 weeks", next="VMT-S1"),
            AnswerOption("lmp_late_or_missed", "Late, or missed altogether", next="VMT-S1"),
            AnswerOption("lmp_gt_3_months", "More than 3 months ago", next="VMT-S1"),
            AnswerOption("lmp_not_applicable", "Does not apply", next="VMT-S1"),
        ],
        default_next="VMT-S1", unknown_option="lmp_unknown", **_nu(0.03)
    ),

    "VMT-S1": SubtreeRefNode("VMT-S1", subtree_nodes=make_dehydration_nodes(), entry="DEH-01", returnNext="VMT-G3"),
    "VMT-G3": GatewayNode("VMT-G3", "GW-VMT-URG-4", _gw_vmt_urg4_dehydration, next="VMT-S2",
                          raisesTo="REFER_URGENT", severeConditions=["dehydration"]),
    "VMT-S2": SubtreeRefNode("VMT-S2", subtree_nodes=make_fever_qual_nodes(), entry="FQ-00", returnNext="VMT-G2"),
    "VMT-G2": GatewayNode("VMT-G2", "GW-VMT-URG-1", _gw_vmt_urg1_obstruction, next="VMT-G4",
                          raisesTo="REFER_URGENT", severeConditions=["bowel obstruction", "strangulation"]),
    "VMT-G4": GatewayNode("VMT-G4", "GW-VMT-URG-2", _gw_vmt_urg2_dka, next="VMT-G5",
                          raisesTo="REFER_URGENT", severeConditions=["DKA"]),
    "VMT-G5": GatewayNode("VMT-G5", "GW-VMT-URG-3", _gw_vmt_urg3_pregnancy, next="VMT-END",
                          raisesTo="REFER_URGENT", severeConditions=["hyperemesis gravidarum", "ectopic pregnancy"]),
    "VMT-END": TerminalNode("VMT-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="VMT-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Vomiting nausea clinical distribution"

_entries = []

_entries += expand_entries("VMT-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_vomiting_blood": 0.005, "ds_vomiting_every": 0.02, "ds_abdomen_rigid": 0.005,
             "ds_confusion": 0.002, "ds_unconscious": 0.001, "ds_convulsion": 0.001,
             "ds_severe_headache": 0.01, "ds_cannot_feed": 0.005},
    "moderate": {"ds_vomiting_blood": 0.02, "ds_vomiting_every": 0.10, "ds_abdomen_rigid": 0.02,
                "ds_confusion": 0.01, "ds_unconscious": 0.005, "ds_convulsion": 0.002,
                "ds_severe_headache": 0.03, "ds_cannot_feed": 0.02},
    "severe": {"ds_vomiting_blood": 0.15, "ds_vomiting_every": 0.45, "ds_abdomen_rigid": 0.15,
               "ds_confusion": 0.10, "ds_unconscious": 0.05, "ds_convulsion": 0.03,
               "ds_severe_headache": 0.15, "ds_cannot_feed": 0.10},
}, overrides={
    ("bowel_obstruction_vomiting", "severe"): {"ds_vomiting_blood": 0.05, "ds_vomiting_every": 0.70, "ds_abdomen_rigid": 0.55,
                                              "ds_confusion": 0.05, "ds_unconscious": 0.02, "ds_convulsion": 0.01,
                                              "ds_severe_headache": 0.02, "ds_cannot_feed": 0.10},
    ("raised_intracranial_pressure_vomiting", "severe"): {"ds_vomiting_blood": 0.01, "ds_vomiting_every": 0.50, "ds_abdomen_rigid": 0.01,
                                                         "ds_confusion": 0.50, "ds_unconscious": 0.20, "ds_convulsion": 0.25,
                                                         "ds_severe_headache": 0.85, "ds_cannot_feed": 0.05},
    ("diabetic_ketoacidosis_vomiting", "severe"): {"ds_vomiting_blood": 0.02, "ds_vomiting_every": 0.75, "ds_abdomen_rigid": 0.10,
                                                  "ds_confusion": 0.60, "ds_unconscious": 0.20, "ds_convulsion": 0.05,
                                                  "ds_severe_headache": 0.10, "ds_cannot_feed": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.35, "pr_same": 0.50, "pr_worse": 0.15},
    "moderate": {"pr_better": 0.15, "pr_same": 0.50, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-02", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.40, "pt_pharmacy_medicine": 0.40, "pt_ayush": 0.08,
        "pt_prescribed_prior": 0.15, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-03", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vf_1_3": 0.70, "vf_4_10": 0.25, "vf_gt_10": 0.05},
    "moderate": {"vf_1_3": 0.30, "vf_4_10": 0.55, "vf_gt_10": 0.15},
    "severe": {"vf_1_3": 0.10, "vf_4_10": 0.45, "vf_gt_10": 0.45},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-04", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vc_food": 0.60, "vc_bile": 0.08, "vc_blood": 0.01, "vc_clear": 0.31},
    "moderate": {"vc_food": 0.40, "vc_bile": 0.25, "vc_blood": 0.03, "vc_clear": 0.32},
    "severe": {"vc_food": 0.20, "vc_bile": 0.45, "vc_blood": 0.15, "vc_clear": 0.20},
}, overrides={
    ("bowel_obstruction_vomiting", "moderate"): {"vc_food": 0.20, "vc_bile": 0.65, "vc_blood": 0.02, "vc_clear": 0.13},
    ("bowel_obstruction_vomiting", "severe"): {"vc_food": 0.05, "vc_bile": 0.85, "vc_blood": 0.05, "vc_clear": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-05", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"vm_yes_keeping_fluids": 0.90, "vm_yes_everything": 0.08, "vm_no": 0.02},
    "moderate": {"vm_yes_keeping_fluids": 0.65, "vm_yes_everything": 0.32, "vm_no": 0.03},
    "severe": {"vm_yes_keeping_fluids": 0.25, "vm_yes_everything": 0.73, "vm_no": 0.02},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-06", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"ps_medicine": 0.02, "ps_pesticide": 0.01, "ps_other": 0.01, "ps_no": 0.96}
    for s in SEVERITIES
}, overrides={
    ("acute_poisoning_toxic_ingestion", s): {"ps_medicine": 0.40, "ps_pesticide": 0.45, "ps_other": 0.12, "ps_no": 0.03}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-07", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"bo_normal": 0.70, "bo_loose": 0.25, "bo_nothing": 0.05},
    "moderate": {"bo_normal": 0.45, "bo_loose": 0.40, "bo_nothing": 0.15},
    "severe": {"bo_normal": 0.25, "bo_loose": 0.45, "bo_nothing": 0.30},
}, overrides={
    ("bowel_obstruction_vomiting", "moderate"): {"bo_normal": 0.10, "bo_loose": 0.05, "bo_nothing": 0.85},
    ("bowel_obstruction_vomiting", "severe"): {"bo_normal": 0.02, "bo_loose": 0.03, "bo_nothing": 0.95},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("VMT-08", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"lmp_within_4wk": 0.70, "lmp_late_or_missed": 0.10, "lmp_gt_3_months": 0.10, "lmp_not_applicable": 0.10}
    for s in SEVERITIES
}, overrides={
    ("hyperemesis_or_early_pregnancy_vomiting", s): {"lmp_within_4wk": 0.05, "lmp_late_or_missed": 0.75, "lmp_gt_3_months": 0.18, "lmp_not_applicable": 0.02}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_dehydration_entries(
    CONDITION_IDS, SEVERITIES,
    dehydration_conditions=("bowel_obstruction_vomiting", "acute_gastritis_gastroenteritis_vomiting", "acute_poisoning_toxic_ingestion"),
    source_type=_SRC, source=_SRC_TEXT,
)

_entries += expand_fever_qual_entries(
    CONDITION_IDS, SEVERITIES,
    fever_conditions=("acute_gastritis_gastroenteritis_vomiting", "raised_intracranial_pressure_vomiting"),
    bleeding_conditions=(),
    source_type=_SRC, source=_SRC_TEXT,
)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
