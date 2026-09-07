"""
drishti_v2/branches/antenatal_visit.py
The `antenatal_visit` branch (branch-authoring-batch-4-memo.md section 6).
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

CATEGORY_ID = "antenatal_visit"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "routine_low_risk_antenatal_care": ConditionSpec(
        "routine_low_risk_antenatal_care", 0.60, "IND-PRESENT",
        "Normal pregnancy check-up without acute obstetric complications"
    ),
    "mild_to_moderate_gestational_anaemia": ConditionSpec(
        "mild_to_moderate_gestational_anaemia", 0.20, "IND-POP",
        "Physiological or iron-deficiency anaemia complicating pregnancy",
        severeConditions=("anaemia in pregnancy",)
    ),
    "gestational_hypertension_or_pre_eclampsia": ConditionSpec(
        "gestational_hypertension_or_pre_eclampsia", 0.08, "IND-POP",
        "Pre-eclampsia or gestational hypertension requiring specialist review",
        severeConditions=("pre-eclampsia",)
    ),
    "previous_caesarean_or_high_risk_obstetric_history": ConditionSpec(
        "previous_caesarean_or_high_risk_obstetric_history", 0.05, "IND-POP",
        "High-risk multipara with past obstetric complications or scar"
    ),
    "threatened_preterm_labour_or_leaking_liquor": ConditionSpec(
        "threatened_preterm_labour_or_leaking_liquor", 0.04, "IND-POP",
        "Preterm rupture of membranes, APH, or early labour signs",
        severeConditions=("APH",)
    ),
    "fetal_growth_restriction_or_compromise": ConditionSpec(
        "fetal_growth_restriction_or_compromise", 0.03, "IND-POP",
        "Reduced fetal movements, malpresentation, or intrauterine compromise",
        severeConditions=("malpresentation", "fetal compromise")
    ),
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "routine_low_risk_antenatal_care": {"mild": 0.85, "moderate": 0.15, "severe": 0.00},
    "mild_to_moderate_gestational_anaemia": {"mild": 0.50, "moderate": 0.40, "severe": 0.10},
    "gestational_hypertension_or_pre_eclampsia": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
    "previous_caesarean_or_high_risk_obstetric_history": {"mild": 0.40, "moderate": 0.45, "severe": 0.15},
    "threatened_preterm_labour_or_leaking_liquor": {"mild": 0.15, "moderate": 0.45, "severe": 0.40},
    "fetal_growth_restriction_or_compromise": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
}

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_sys = specs["bp_systolic"]
    base_dia = specs["bp_diastolic"]

    if condition_id == "gestational_hypertension_or_pre_eclampsia":
        specs["bp_systolic"] = VitalSpec(base_sys.mean + 35, 12.0, 70, 240)
        specs["bp_diastolic"] = VitalSpec(base_dia.mean + 20, 8.0, 40, 150)
    return specs

_ASSUMED_PROV = {"sourceType": "ASSUMED", "source": "Standard unknown rate", "declaredOn": "2026-09-06"}
def _nu(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED_PROV)

def _gw_anc_emg1(fields, ctx):
    return (
        contains(fields, "danger_signs_pregnancy", "ds_vaginal_bleed")
        or contains(fields, "danger_signs_pregnancy", "ds_convulsion")
        or contains(fields, "danger_signs_pregnancy", "ds_unconscious")
    )

def _gw_anc_emg2(fields, ctx):
    return (
        contains(fields, "danger_signs_pregnancy", "ds_severe_headache")
        or contains(fields, "danger_signs_pregnancy", "ds_blurred_vision")
        or contains(fields, "danger_signs_pregnancy", "ds_swollen_face_h")
    )

def _gw_anc_emg3(fields, ctx):
    return contains(fields, "danger_signs_pregnancy", "ds_no_fetal_move")

def _gw_anc_urg4(fields, ctx):
    return (
        contains(fields, "danger_signs_pregnancy", "ds_fever_preg")
        or contains(fields, "danger_signs_pregnancy", "ds_water_break")
        or contains(fields, "danger_signs_pregnancy", "ds_severe_abd_pain")
    )

def _gw_anc_fetal_move(fields, ctx):
    fm = value_of(fields, "fetal_movement")
    return fm in ("fm_reduced", "fm_none")

def _gw_anc_urg_history_pallor(fields, ctx):
    pc = (
        contains(fields, "previous_pregnancy_complication", "pc_stillbirth")
        or contains(fields, "previous_pregnancy_complication", "pc_preeclampsia")
    )
    pal = (
        contains(fields, "pallor_site_observed", "po_palms")
        or contains(fields, "pallor_site_observed", "po_conjunctiva")
    )
    return pc or pal

_NODES = {
    "ANC-00": QuestionNode(
        nodeId="ANC-00", fieldId="danger_signs_pregnancy", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_vaginal_bleed", "Vaginal bleeding", next="ANC-G1a"),
            AnswerOption("ds_severe_headache", "Severe headache that will not go away", next="ANC-G1a"),
            AnswerOption("ds_blurred_vision", "Blurred or disturbed vision", next="ANC-G1a"),
            AnswerOption("ds_convulsion", "Fits or convulsions", next="ANC-G1a"),
            AnswerOption("ds_swollen_face_h", "Face or hands suddenly swollen", next="ANC-G1a"),
            AnswerOption("ds_severe_abd_pain", "Severe abdominal pain", next="ANC-G1a"),
            AnswerOption("ds_no_fetal_move", "Baby has not moved for more than 12 hours", next="ANC-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="ANC-G1a"),
            AnswerOption("ds_fever_preg", "High fever", next="ANC-G1a"),
            AnswerOption("ds_water_break", "Water has broken / leaking fluid", next="ANC-G1a"),
            AnswerOption("ds_none", "None of these", next="ANC-01"),
        ],
        default_next="ANC-G1a", none_option="ds_none", unknown_option="ds_unknown", **_nu(0.01)
    ),
    "ANC-G1a": GatewayNode("ANC-G1a", "GW-ANC-EMG-1", _gw_anc_emg1, next="ANC-G1b",
                           routeTo="emergency_pregnancy_danger"),
    "ANC-G1b": GatewayNode("ANC-G1b", "GW-ANC-EMG-2", _gw_anc_emg2, next="ANC-G1c",
                           raisesTo="REFER_EMERGENCY", severeConditions=["pre-eclampsia / imminent eclampsia"]),
    "ANC-G1c": GatewayNode("ANC-G1c", "GW-ANC-EMG-3", _gw_anc_emg3, next="ANC-G1d",
                           raisesTo="REFER_EMERGENCY", severeConditions=["fetal distress / intrauterine death"]),
    "ANC-G1d": GatewayNode("ANC-G1d", "GW-ANC-URG-4", _gw_anc_urg4, next="ANC-01",
                           raisesTo="REFER_URGENT", severeConditions=["infection", "PPROM", "placental abruption"]),

    "ANC-01": QuestionNode(
        nodeId="ANC-01", fieldId="gestational_weeks_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("gw_lt_12", "Less than 12 weeks (first trimester)", next="ANC-02"),
            AnswerOption("gw_12_28", "12 to 28 weeks (second trimester)", next="ANC-02"),
            AnswerOption("gw_28_36", "28 to 36 weeks (third trimester)", next="ANC-02"),
            AnswerOption("gw_gt_36", "More than 36 weeks (close to due date)", next="ANC-02"),
        ],
        default_next="ANC-02", unknown_option="gw_unknown", **_nu(0.02)
    ),
    "ANC-02": QuestionNode(
        nodeId="ANC-02", fieldId="gravida_para", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("gp_primi", "First pregnancy", next="ANC-03"),
            AnswerOption("gp_multi", "Has been pregnant before", next="ANC-03"),
        ],
        default_next="ANC-03", unknown_option="gp_unknown", **_nu(0.02)
    ),
    "ANC-03": QuestionNode(
        nodeId="ANC-03", fieldId="anc_visit_number", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("av_first", "First visit", next="ANC-04"),
            AnswerOption("av_second", "Second", next="ANC-04"),
            AnswerOption("av_third", "Third", next="ANC-04"),
            AnswerOption("av_fourth_plus", "Fourth or more", next="ANC-04"),
        ],
        default_next="ANC-04", unknown_option="av_unknown", **_nu(0.02)
    ),
    "ANC-04": QuestionNode(
        nodeId="ANC-04", fieldId="fetal_movement", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fm_good", "Yes — moving as usual", next="ANC-G2"),
            AnswerOption("fm_reduced", "Less than usual", next="ANC-G2"),
            AnswerOption("fm_none", "No movement felt", next="ANC-G2"),
        ],
        default_next="ANC-G2", unknown_option="fm_unknown", **_nu(0.03)
    ),
    "ANC-G2": GatewayNode("ANC-G2", "GW-ANC-FETAL", _gw_anc_fetal_move, next="ANC-05",
                          raisesTo="REFER_URGENT", severeConditions=["fetal distress", "fetal compromise"]),

    "ANC-05": QuestionNode(
        nodeId="ANC-05", fieldId="previous_pregnancy_complication", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pc_stillbirth", "Stillbirth or baby died soon after birth", next="ANC-06"),
            AnswerOption("pc_cs", "Caesarean section", next="ANC-06"),
            AnswerOption("pc_preeclampsia", "High BP or fits during pregnancy", next="ANC-06"),
            AnswerOption("pc_bleeding", "Heavy bleeding during delivery", next="ANC-06"),
            AnswerOption("pc_preterm", "Baby born too early", next="ANC-06"),
            AnswerOption("pc_none", "None of these", next="ANC-06"),
        ],
        default_next="ANC-06", none_option="pc_none", unknown_option="pc_unknown", **_nu(0.03)
    ),
    "ANC-06": QuestionNode(
        nodeId="ANC-06", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedies", next="ANC-07"),
            AnswerOption("pt_pharmacy_medicine", "Medicine from a pharmacy / shop", next="ANC-07"),
            AnswerOption("pt_ayush", "Ayurvedic / homeopathic / traditional medicine", next="ANC-07"),
            AnswerOption("pt_prescribed_prior", "Prescription medicine from another doctor", next="ANC-07"),
            AnswerOption("pt_other", "Other treatment", next="ANC-07"),
            AnswerOption("pt_none", "No prior treatment", next="ANC-07"),
        ],
        default_next="ANC-07", none_option="pt_none", unknown_option="pt_unknown", **_nu(0.02)
    ),
    "ANC-07": QuestionNode(
        nodeId="ANC-07", fieldId="relevant_history", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("rh_hypertension", "High blood pressure", next="ANC-08"),
            AnswerOption("rh_diabetes", "Diabetes", next="ANC-08"),
            AnswerOption("rh_heart_disease", "Heart disease", next="ANC-08"),
            AnswerOption("rh_asthma", "Asthma or lung problem", next="ANC-08"),
            AnswerOption("rh_other", "Other long-term illness", next="ANC-08"),
            AnswerOption("rh_none", "No known medical conditions", next="ANC-08"),
        ],
        default_next="ANC-08", none_option="rh_none", unknown_option="rh_unknown", **_nu(0.02)
    ),
    "ANC-08": QuestionNode(
        nodeId="ANC-08", fieldId="pallor_site_observed", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("po_palms", "Palms are pale", next="ANC-G3"),
            AnswerOption("po_nails", "Nail beds are pale", next="ANC-G3"),
            AnswerOption("po_conjunctiva", "Inside of lower eyelid is pale", next="ANC-G3"),
            AnswerOption("po_tongue", "Tongue is pale", next="ANC-G3"),
            AnswerOption("po_face", "Face looks pale", next="ANC-G3"),
            AnswerOption("po_none", "None of these — family reports pallor", next="ANC-G3"),
        ],
        default_next="ANC-G3", none_option="po_none", unknown_option="po_unknown", **_nu(0.02)
    ),
    "ANC-G3": GatewayNode("ANC-G3", "GW-ANC-URG-3", _gw_anc_urg_history_pallor, next="ANC-END",
                          raisesTo="REFER_URGENT", severeConditions=["high-risk pregnancy", "anaemia in pregnancy"]),
    "ANC-END": TerminalNode("ANC-END"),
}

BRANCH = BranchDef(
    categoryId=CATEGORY_ID,
    version=BRANCH_VERSION,
    requiredDisposition=REQUIRED_DISPOSITION,
    nodes=_NODES,
    entry="ANC-00",
)

_SRC = "ASSUMED"
_SRC_TEXT = "Antenatal visit clinical distribution"

_entries = []

_entries += expand_entries("ANC-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_vaginal_bleed": 0.005, "ds_severe_headache": 0.01, "ds_blurred_vision": 0.005,
             "ds_convulsion": 0.001, "ds_swollen_face_h": 0.02, "ds_severe_abd_pain": 0.01,
             "ds_no_fetal_move": 0.005, "ds_unconscious": 0.001, "ds_fever_preg": 0.01, "ds_water_break": 0.01},
    "moderate": {"ds_vaginal_bleed": 0.02, "ds_severe_headache": 0.05, "ds_blurred_vision": 0.02,
                "ds_convulsion": 0.002, "ds_swollen_face_h": 0.08, "ds_severe_abd_pain": 0.04,
                "ds_no_fetal_move": 0.02, "ds_unconscious": 0.002, "ds_fever_preg": 0.03, "ds_water_break": 0.03},
    "severe": {"ds_vaginal_bleed": 0.15, "ds_severe_headache": 0.20, "ds_blurred_vision": 0.15,
               "ds_convulsion": 0.05, "ds_swollen_face_h": 0.25, "ds_severe_abd_pain": 0.15,
               "ds_no_fetal_move": 0.15, "ds_unconscious": 0.02, "ds_fever_preg": 0.10, "ds_water_break": 0.15},
}, overrides={
    ("gestational_hypertension_or_pre_eclampsia", "moderate"): {
        "ds_vaginal_bleed": 0.01, "ds_severe_headache": 0.40, "ds_blurred_vision": 0.30,
        "ds_convulsion": 0.02, "ds_swollen_face_h": 0.55, "ds_severe_abd_pain": 0.10,
        "ds_no_fetal_move": 0.05, "ds_unconscious": 0.01, "ds_fever_preg": 0.01, "ds_water_break": 0.01
    },
    ("gestational_hypertension_or_pre_eclampsia", "severe"): {
        "ds_vaginal_bleed": 0.05, "ds_severe_headache": 0.75, "ds_blurred_vision": 0.65,
        "ds_convulsion": 0.18, "ds_swollen_face_h": 0.85, "ds_severe_abd_pain": 0.30,
        "ds_no_fetal_move": 0.15, "ds_unconscious": 0.08, "ds_fever_preg": 0.02, "ds_water_break": 0.02
    },
    ("threatened_preterm_labour_or_leaking_liquor", "severe"): {
        "ds_vaginal_bleed": 0.60, "ds_severe_headache": 0.05, "ds_blurred_vision": 0.02,
        "ds_convulsion": 0.00, "ds_swollen_face_h": 0.05, "ds_severe_abd_pain": 0.70,
        "ds_no_fetal_move": 0.15, "ds_unconscious": 0.01, "ds_fever_preg": 0.05, "ds_water_break": 0.80
    },
    ("fetal_growth_restriction_or_compromise", "severe"): {
        "ds_vaginal_bleed": 0.05, "ds_severe_headache": 0.05, "ds_blurred_vision": 0.02,
        "ds_convulsion": 0.00, "ds_swollen_face_h": 0.05, "ds_severe_abd_pain": 0.10,
        "ds_no_fetal_move": 0.75, "ds_unconscious": 0.01, "ds_fever_preg": 0.02, "ds_water_break": 0.05
    },
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-01", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"gw_lt_12": 0.15, "gw_12_28": 0.40, "gw_28_36": 0.30, "gw_gt_36": 0.15}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-02", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"gp_primi": 0.45, "gp_multi": 0.55}
    for s in SEVERITIES
}, overrides={
    ("previous_caesarean_or_high_risk_obstetric_history", "mild"): {"gp_primi": 0.00, "gp_multi": 1.00},
    ("previous_caesarean_or_high_risk_obstetric_history", "moderate"): {"gp_primi": 0.00, "gp_multi": 1.00},
    ("previous_caesarean_or_high_risk_obstetric_history", "severe"): {"gp_primi": 0.00, "gp_multi": 1.00},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-03", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"av_first": 0.30, "av_second": 0.35, "av_third": 0.20, "av_fourth_plus": 0.15}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-04", "categorical", CONDITION_IDS, SEVERITIES, {
    s: {"fm_good": 0.85, "fm_reduced": 0.12, "fm_none": 0.03}
    for s in SEVERITIES
}, overrides={
    ("fetal_growth_restriction_or_compromise", "mild"): {"fm_good": 0.45, "fm_reduced": 0.45, "fm_none": 0.10},
    ("fetal_growth_restriction_or_compromise", "moderate"): {"fm_good": 0.20, "fm_reduced": 0.60, "fm_none": 0.20},
    ("fetal_growth_restriction_or_compromise", "severe"): {"fm_good": 0.05, "fm_reduced": 0.35, "fm_none": 0.60},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-05", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pc_stillbirth": 0.02, "pc_cs": 0.15, "pc_preeclampsia": 0.04, "pc_bleeding": 0.03, "pc_preterm": 0.05}
    for s in SEVERITIES
}, overrides={
    ("previous_caesarean_or_high_risk_obstetric_history", "mild"): {"pc_stillbirth": 0.10, "pc_cs": 0.85, "pc_preeclampsia": 0.10, "pc_bleeding": 0.05, "pc_preterm": 0.10},
    ("previous_caesarean_or_high_risk_obstetric_history", "moderate"): {"pc_stillbirth": 0.15, "pc_cs": 0.90, "pc_preeclampsia": 0.15, "pc_bleeding": 0.10, "pc_preterm": 0.15},
    ("previous_caesarean_or_high_risk_obstetric_history", "severe"): {"pc_stillbirth": 0.25, "pc_cs": 0.95, "pc_preeclampsia": 0.25, "pc_bleeding": 0.15, "pc_preterm": 0.20},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-06", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.15, "pt_pharmacy_medicine": 0.60, "pt_ayush": 0.05,
        "pt_prescribed_prior": 0.45, "pt_other": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-07", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"rh_hypertension": 0.05, "rh_diabetes": 0.04, "rh_heart_disease": 0.01,
        "rh_asthma": 0.02, "rh_other": 0.03}
    for s in SEVERITIES
}, overrides={
    ("gestational_hypertension_or_pre_eclampsia", "moderate"): {"rh_hypertension": 0.35, "rh_diabetes": 0.10, "rh_heart_disease": 0.02, "rh_asthma": 0.02, "rh_other": 0.05},
    ("gestational_hypertension_or_pre_eclampsia", "severe"): {"rh_hypertension": 0.60, "rh_diabetes": 0.15, "rh_heart_disease": 0.05, "rh_asthma": 0.02, "rh_other": 0.08},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("ANC-08", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"po_palms": 0.15, "po_nails": 0.20, "po_conjunctiva": 0.25, "po_tongue": 0.10, "po_face": 0.10},
    "moderate": {"po_palms": 0.45, "po_nails": 0.55, "po_conjunctiva": 0.60, "po_tongue": 0.30, "po_face": 0.35},
    "severe": {"po_palms": 0.80, "po_nails": 0.85, "po_conjunctiva": 0.90, "po_tongue": 0.65, "po_face": 0.70},
}, overrides={
    ("mild_to_moderate_gestational_anaemia", "moderate"): {"po_palms": 0.65, "po_nails": 0.70, "po_conjunctiva": 0.85, "po_tongue": 0.45, "po_face": 0.50},
    ("mild_to_moderate_gestational_anaemia", "severe"): {"po_palms": 0.90, "po_nails": 0.95, "po_conjunctiva": 0.98, "po_tongue": 0.80, "po_face": 0.85},
}, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
