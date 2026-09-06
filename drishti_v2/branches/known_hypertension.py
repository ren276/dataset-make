"""
drishti_v2/branches/known_hypertension.py
============================================
The `known_hypertension` branch (questionnaire-tree-design-memo.md section
4) -- the chronic/follow-up shape, proving the schema against a branch that
detects decompensation and non-adherence rather than narrowing a complaint.

One declared deviation from the memo's printed node list, stated here: the
memo's section 4 node table does not show a pregnancy_status question for
this branch, yet GW-HTN-URG-2 (pre-eclampsia) is defined to read
pregnancy_status. Section 2.1 classifies pregnancy_status as "shared,
prefilled, never asked by the tree", but nothing upstream of this branch
actually prefills it, and a gateway must read an observable field, never
the hidden latent condition_id -- reading condition_id directly would let
the device "know" ground truth it can never have in the field. This build
adds HTN-07B, a small ask node with the same fieldId/options fever's FV-12
uses, guarded the same way (sex==F, age in [15,49]), so GW-HTN-URG-2 has a
real observable signal to fire on. This is a build decision filling a gap
the memo left open, not a memo requirement.
"""

from __future__ import annotations

from ..schema import AnswerOption, BranchDef, GatewayNode, QuestionNode, TerminalNode, any_of, equals
from ..vitals import VitalSpec, baseline_vitals, IHCI_SBP_STAGE1, IHCI_DBP_STAGE1
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec

CATEGORY_ID = "known_hypertension"
BRANCH_VERSION = "1.0.0-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "controlled_htn": ConditionSpec("controlled_htn", 0.45, "ASSUMED",
        "Routine follow-up is the modal reason for this category (Odisha: hypertension is "
        "one of only three things primary facilities actually handle); most such visits are "
        "for a controlled, stable patient."),
    "uncontrolled_htn_no_symptoms": ConditionSpec("uncontrolled_htn_no_symptoms", 0.30, "ASSUMED",
        "Non-adherence and undertreatment are common in chronic NCD care in rural India; "
        "no Indian source gives a direct share."),
    "uncontrolled_htn_with_symptoms": ConditionSpec("uncontrolled_htn_with_symptoms", 0.15, "ASSUMED", ""),
    "hypertensive_emergency": ConditionSpec("hypertensive_emergency", 0.03, "ASSUMED",
        "Kept small and non-zero purely so GATE-EMERGENCY's minimum-row-count floor is reachable.",
        severeConditions=("hypertensive emergency", "stroke")),
    "htn_in_pregnancy_preeclampsia_risk": ConditionSpec("htn_in_pregnancy_preeclampsia_risk", 0.07, "ASSUMED",
        "Cross-links antenatal_visit per the memo; kept non-trivial so GW-HTN-URG-2 fires.",
        severeConditions=("pre-eclampsia",)),
}
CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")

SEVERITY_DIST = {
    "controlled_htn": {"mild": 0.70, "moderate": 0.25, "severe": 0.05},
    "uncontrolled_htn_no_symptoms": {"mild": 0.30, "moderate": 0.55, "severe": 0.15},
    "uncontrolled_htn_with_symptoms": {"mild": 0.15, "moderate": 0.55, "severe": 0.30},
    "hypertensive_emergency": {"mild": 0.05, "moderate": 0.15, "severe": 0.80},
    "htn_in_pregnancy_preeclampsia_risk": {"mild": 0.20, "moderate": 0.50, "severe": 0.30},
}

_SBP_DBP_BY_CONDITION_SEVERITY = {
    ("controlled_htn", "mild"): (122, 78), ("controlled_htn", "moderate"): (132, 84),
    ("controlled_htn", "severe"): (138, 88),
    ("uncontrolled_htn_no_symptoms", "mild"): (145, 90), ("uncontrolled_htn_no_symptoms", "moderate"): (158, 96),
    ("uncontrolled_htn_no_symptoms", "severe"): (168, 102),
    ("uncontrolled_htn_with_symptoms", "mild"): (150, 92), ("uncontrolled_htn_with_symptoms", "moderate"): (165, 100),
    ("uncontrolled_htn_with_symptoms", "severe"): (178, 108),
    ("hypertensive_emergency", "mild"): (170, 105), ("hypertensive_emergency", "moderate"): (185, 112),
    ("hypertensive_emergency", "severe"): (205, 122),
    ("htn_in_pregnancy_preeclampsia_risk", "mild"): (135, 86), ("htn_in_pregnancy_preeclampsia_risk", "moderate"): (148, 94),
    ("htn_in_pregnancy_preeclampsia_risk", "severe"): (165, 108),
}


def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    sbp_mean, dbp_mean = _SBP_DBP_BY_CONDITION_SEVERITY[(condition_id, severity_band)]
    specs["bp_systolic"] = VitalSpec(float(sbp_mean), 6.0, 70, 230)
    specs["bp_diastolic"] = VitalSpec(float(dbp_mean), 5.0, 40, 140)
    if condition_id == "hypertensive_emergency" and severity_band == "severe":
        specs["pulse"] = VitalSpec(105.0, 10.0, 35, 220)
        specs["glucose"] = VitalSpec(160.0, 90.0, 20, 700)  # stress response; see fever.py note
    return specs


def _gw_emg1(fields, ctx):
    return any_of(fields, "danger_signs",
                  ["ds_chest_pain", "ds_breathless", "ds_weakness", "ds_speech", "ds_vision", "ds_severe_head"])


def _gw_adh1(fields, ctx):
    return equals(fields, "bp_medication_adherence", "ad_stopped") or equals(
        fields, "bp_medication_adherence", "ad_none_given")


def _true(ctx, name):
    t = ctx.get("vitals", {}).get(name)
    return t.true_value if t is not None else None


def _gw_urg1_vitals(fields, ctx):
    sbp, dbp = _true(ctx, "bp_systolic"), _true(ctx, "bp_diastolic")
    return (sbp is not None and sbp >= 180) or (dbp is not None and dbp >= 110)


def _gw_urg2_preeclampsia(fields, ctx):
    if not equals(fields, "pregnancy_status", "pg_yes"):
        return False
    sbp, dbp = _true(ctx, "bp_systolic"), _true(ctx, "bp_diastolic")
    return (sbp is not None and sbp >= 140) or (dbp is not None and dbp >= 90)


def _guard_pregnancy_asked(fields):
    sex = fields.get("_sex")
    age = fields.get("_age_years")
    return sex is not None and age is not None and sex.value == "F" and 15 <= age.value <= 49


def _nu(rate):
    return dict(unknown_rate=rate, unknown_provenance={
        "sourceType": "ASSUMED", "source": "Flat low unknown rate; no Indian survey used.",
        "declaredOn": "2026-09-06"})


_NODES = {
    "HTN-00": QuestionNode(
        nodeId="HTN-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_chest_pain", "Chest pain or heaviness", next="HTN-G1"),
            AnswerOption("ds_breathless", "Breathless at rest or lying flat", next="HTN-G1"),
            AnswerOption("ds_weakness", "Sudden weakness or drooping on one side", next="HTN-G1"),
            AnswerOption("ds_speech", "Sudden difficulty speaking", next="HTN-G1"),
            AnswerOption("ds_vision", "Sudden vision loss or blurring", next="HTN-G1"),
            AnswerOption("ds_severe_head", "Severe headache, worst ever", next="HTN-G1"),
        ],
        default_next="HTN-01", unknown_option="ds_unknown", none_option="ds_none", **_nu(0.02),
    ),
    "HTN-G1": GatewayNode("HTN-G1", "GW-HTN-EMG-1", _gw_emg1, next="HTN-01", raisesTo="REFER_EMERGENCY",
                           severeConditions=["stroke", "ACS", "hypertensive emergency"]),
    "HTN-01": QuestionNode(
        nodeId="HTN-01", fieldId="visit_reason_subtype", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("vr_refill", "Routine check / medicine refill", next="HTN-02"),
            AnswerOption("vr_new_symptom", "New complaint since last visit", next="HTN-02"),
            AnswerOption("vr_followup", "Follow-up after a referral", next="HTN-02"),
            AnswerOption("vr_first", "First visit for known high BP", next="HTN-02"),
        ],
        default_next="HTN-02", unknown_option="vr_unknown", **_nu(0.02),
    ),
    "HTN-02": QuestionNode(
        nodeId="HTN-02", fieldId="bp_medication_adherence", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ad_daily", "Every day", next="HTN-03"),
            AnswerOption("ad_missed_some", "Misses some days", next="HTN-03"),
            AnswerOption("ad_stopped", "Stopped taking it", next="HTN-G2"),
            AnswerOption("ad_none_given", "Never been given any medicine", next="HTN-G2"),
        ],
        default_next="HTN-03", unknown_option="ad_unknown", **_nu(0.03),
    ),
    "HTN-G2": GatewayNode("HTN-G2", "GW-HTN-ADH-1", _gw_adh1, next="HTN-03", raisesTo=None,
                           severeConditions=[]),
    "HTN-03": QuestionNode(
        nodeId="HTN-03", fieldId="medication_names_known", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("mn_carried", "Carrying the strip or card", next="HTN-04"),
            AnswerOption("mn_named", "Knows the names", next="HTN-04"),
        ],
        default_next="HTN-04", unknown_option="mn_unknown", **_nu(0.05),
    ),
    "HTN-04": QuestionNode(
        nodeId="HTN-04", fieldId="last_bp_reading_known", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("lb_yes_normal", "Yes - was in range", next="HTN-05"),
            AnswerOption("lb_yes_high", "Yes - was high", next="HTN-05"),
        ],
        default_next="HTN-05", unknown_option="lb_no", **_nu(0.10),
    ),
    "HTN-05": QuestionNode(
        nodeId="HTN-05", fieldId="symptoms_since_last_visit", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("sl_headache", "Headaches"),
            AnswerOption("sl_giddiness", "Giddiness"),
            AnswerOption("sl_palpitation", "Palpitations"),
            AnswerOption("sl_ankle_swelling", "Ankle swelling"),
            AnswerOption("sl_breathless_exertion", "Breathless on walking"),
            AnswerOption("sl_nosebleed", "Nose bleeds"),
        ],
        default_next="HTN-06", unknown_option="sl_unknown", none_option="sl_none", **_nu(0.03),
    ),
    "HTN-06": QuestionNode(
        nodeId="HTN-06", fieldId="home_bp_monitoring", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hb_yes", "Yes, checks at home", next="HTN-07"),
            AnswerOption("hb_no", "No", next="HTN-07"),
        ],
        default_next="HTN-07", unknown_option="hb_unknown", **_nu(0.03),
    ),
    "HTN-07": QuestionNode(
        nodeId="HTN-07", fieldId="relevant_history", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("hx_diabetes", "Diabetes"),
            AnswerOption("hx_hypertension", "Family history of hypertension"),
            AnswerOption("hx_heart_disease", "Heart disease"),
            AnswerOption("hx_kidney_disease", "Kidney disease"),
            AnswerOption("hx_asthma_copd", "Asthma / COPD"),
            AnswerOption("hx_tb", "TB history"),
            AnswerOption("hx_surgery", "Past surgery"),
            AnswerOption("hx_allergy", "Known allergy"),
        ],
        default_next="HTN-07B", unknown_option="hx_unknown", none_option="hx_none", **_nu(0.03),
    ),
    "HTN-07B": QuestionNode(
        nodeId="HTN-07B", fieldId="pregnancy_status", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pg_yes", "Yes", next="HTN-G3a"),
            AnswerOption("pg_no", "No", next="HTN-G3a"),
        ],
        default_next="HTN-G3a", unknown_option="pg_unknown", guard=_guard_pregnancy_asked, **_nu(0.02),
    ),
    "HTN-G3a": GatewayNode("HTN-G3a", "GW-HTN-URG-1", _gw_urg1_vitals, next="HTN-G3b", raisesTo="REFER_URGENT",
                            severeConditions=[]),
    "HTN-G3b": GatewayNode("HTN-G3b", "GW-HTN-URG-2", _gw_urg2_preeclampsia, next="HTN-END",
                            raisesTo="REFER_URGENT", severeConditions=["pre-eclampsia"]),
    "HTN-END": TerminalNode("HTN-END"),
}

BRANCH = BranchDef(categoryId=CATEGORY_ID, version=BRANCH_VERSION,
                    requiredDisposition=REQUIRED_DISPOSITION, nodes=_NODES, entry="HTN-00")

_SRC = "ASSUMED"
_SRC_TEXT = ("Coarse infra-build distribution proving the machine; not physician-reviewed "
             "(tree memo section 6.3 fill-in is deferred).")

_entries = []
_entries += expand_entries("HTN-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_chest_pain": 0.005, "ds_breathless": 0.005, "ds_weakness": 0.002,
             "ds_speech": 0.001, "ds_vision": 0.003, "ds_severe_head": 0.01},
    "moderate": {"ds_chest_pain": 0.02, "ds_breathless": 0.02, "ds_weakness": 0.005,
                 "ds_speech": 0.003, "ds_vision": 0.01, "ds_severe_head": 0.03},
    "severe": {"ds_chest_pain": 0.15, "ds_breathless": 0.20, "ds_weakness": 0.10,
               "ds_speech": 0.08, "ds_vision": 0.10, "ds_severe_head": 0.25},
}, overrides={
    ("hypertensive_emergency", "severe"): {"ds_chest_pain": 0.35, "ds_breathless": 0.40, "ds_weakness": 0.20,
                                            "ds_speech": 0.15, "ds_vision": 0.25, "ds_severe_head": 0.45},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HTN-01", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"vr_refill": 0.55, "vr_new_symptom": 0.15, "vr_followup": 0.15, "vr_first": 0.15} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HTN-02", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"ad_daily": 0.75, "ad_missed_some": 0.20, "ad_stopped": 0.03, "ad_none_given": 0.02},
    "moderate": {"ad_daily": 0.40, "ad_missed_some": 0.35, "ad_stopped": 0.15, "ad_none_given": 0.10},
    "severe": {"ad_daily": 0.20, "ad_missed_some": 0.25, "ad_stopped": 0.35, "ad_none_given": 0.20},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HTN-03", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"mn_carried": 0.55, "mn_named": 0.45} for s in SEVERITIES}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HTN-04", "categorical", CONDITION_IDS, SEVERITIES,
    {"mild": {"lb_yes_normal": 0.80, "lb_yes_high": 0.20},
     "moderate": {"lb_yes_normal": 0.45, "lb_yes_high": 0.55},
     "severe": {"lb_yes_normal": 0.25, "lb_yes_high": 0.75}},
    source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HTN-05", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"sl_headache": 0.10, "sl_giddiness": 0.08, "sl_palpitation": 0.05,
             "sl_ankle_swelling": 0.05, "sl_breathless_exertion": 0.05, "sl_nosebleed": 0.02},
    "moderate": {"sl_headache": 0.25, "sl_giddiness": 0.18, "sl_palpitation": 0.12,
                 "sl_ankle_swelling": 0.12, "sl_breathless_exertion": 0.12, "sl_nosebleed": 0.05},
    "severe": {"sl_headache": 0.45, "sl_giddiness": 0.35, "sl_palpitation": 0.25,
               "sl_ankle_swelling": 0.20, "sl_breathless_exertion": 0.30, "sl_nosebleed": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HTN-06", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"hb_yes": 0.30, "hb_no": 0.70} for s in SEVERITIES}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("HTN-07", "multi_bernoulli", CONDITION_IDS, SEVERITIES,
    {s: {"hx_diabetes": 0.20, "hx_hypertension": 0.30, "hx_heart_disease": 0.08, "hx_kidney_disease": 0.04,
         "hx_asthma_copd": 0.05, "hx_tb": 0.02, "hx_surgery": 0.06, "hx_allergy": 0.03} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT)

_pg_base = {s: {"pg_yes": 0.03, "pg_no": 0.97} for s in SEVERITIES}
_pg_overrides = {(c, s): {"pg_yes": 0.85, "pg_no": 0.15} for c in ("htn_in_pregnancy_preeclampsia_risk",)
                 for s in SEVERITIES}
_entries += expand_entries("HTN-07B", "categorical", CONDITION_IDS, SEVERITIES, _pg_base,
                            overrides=_pg_overrides, source_type=_SRC, source=_SRC_TEXT)

ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
