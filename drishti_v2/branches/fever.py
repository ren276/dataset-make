"""
drishti_v2/branches/fever.py
==============================
The `fever` branch (questionnaire-tree-design-memo.md section 3) and its
condition catalog (dataset-regeneration-design-memo.md section 2, stage 2).

Condition shares below are ASSUMED. The category memo's AUFI figures
(malaria 17%, dengue 16%, scrub typhus 10%, enteric 8%x35%, leptospirosis
7%, chikungunya 6%) are explicitly named "for the fever gateway's condition
list, not for its share" because AUFI is a hospitalised, severity-shifted
cohort. This module uses AUFI only to pick which severe conditions exist in
the catalog; the shares themselves are declared low (self_limited_fever
dominates PHC-level fever, matching the Odisha/POSEIDON picture of fever as
overwhelmingly a benign presenting complaint) with the severe conditions
kept just large enough that GATE-EMERGENCY's minimum-row-count floors are
reachable at the ~20k row volume this category gets. A physician setting
real shares is the section 6.3 fill-in step this build does not perform.
"""

from __future__ import annotations

from ..schema import (AnswerOption, BranchDef, GatewayNode, QuestionNode, TerminalNode,
                       SubtreeRefNode, any_of, contains, equals, value_of)
from ..vitals import VitalSpec, baseline_vitals
from .authoring import expand_entries, peaked
from .spec import CategorySpec, ConditionSpec
from .subtrees import RASH_MORPH_NODES, make_tb_screen_nodes, make_exposure_context_fever_nodes, expand_tb_screen_entries, expand_exposure_context_entries

CATEGORY_ID = "fever"
BRANCH_VERSION = "1.0.1-draft"
REQUIRED_DISPOSITION = "PHYSICIAN_REVIEW_MANDATORY"

CONDITIONS = {
    "self_limited_fever": ConditionSpec("self_limited_fever", 0.68, "ASSUMED",
        "Residual/background: most PHC fever presentations are benign and self-limited. "
        "No Indian source gives a direct share; POSEIDON/Odisha only establish fever's "
        "overall category share (35.5%/commonest-everywhere), not its internal condition mix."),
    "dengue": ConditionSpec("dengue", 0.07, "WORLD",
        "AUFI (hospitalised cohort) dengue 16% used only to justify inclusion; share scaled "
        "down heavily (community-scaling ASSUMED) because AUFI is severity-shifted.",
        severeConditions=("dengue",)),
    "severe_dengue": ConditionSpec("severe_dengue", 0.015, "ASSUMED",
        "Severe/haemorrhagic subtype of dengue, kept as its own condition so GATE-EMERGENCY's "
        "bleeding-route floor is reachable; AUFI does not split severe from non-severe dengue.",
        severeConditions=("severe dengue",)),
    "malaria": ConditionSpec("malaria", 0.05, "WORLD",
        "AUFI malaria 17% (community-scaled down, ASSUMED); NVBDCP notes MP as a tribal "
        "high-burden focus state.", severeConditions=("malaria",)),
    "malaria_falciparum_severe": ConditionSpec("malaria_falciparum_severe", 0.01, "ASSUMED",
        "Falciparum-severe subtype, kept distinct for the unconscious-route gateway.",
        severeConditions=("falciparum malaria",)),
    "typhoid_enteric": ConditionSpec("typhoid_enteric", 0.04, "WORLD",
        "AUFI bacteraemia 8% of which 35% enteric (community-scaled down, ASSUMED).",
        severeConditions=("typhoid",)),
    "scrub_typhus": ConditionSpec("scrub_typhus", 0.03, "WORLD",
        "AUFI scrub typhus 10% (community-scaled down, ASSUMED).", severeConditions=("scrub typhus",)),
    "leptospirosis": ConditionSpec("leptospirosis", 0.02, "WORLD",
        "AUFI leptospirosis 7% (community-scaled down, ASSUMED).", severeConditions=("leptospirosis",)),
    "chikungunya": ConditionSpec("chikungunya", 0.04, "WORLD",
        "AUFI chikungunya 6% (community-scaled down, ASSUMED).", severeConditions=("chikungunya",)),
    "tuberculosis_fever": ConditionSpec("tuberculosis_fever", 0.03, "IND-PROG",
        "India TB incidence 187/lakh, MP 4th-highest burden (Nikshay); fever-presenting TB "
        "share within the fever category is still ASSUMED.", severeConditions=("tuberculosis",)),
    "sepsis_or_meningitis_emergency": ConditionSpec("sepsis_or_meningitis_emergency", 0.015, "ASSUMED",
        "Kept as its own condition purely so the convulsion/unconscious/neck-stiffness "
        "Tier-0 routes have rows to exercise at all.", severeConditions=("sepsis", "meningitis")),
}

_SEVERE = {"mild": 0.05, "moderate": 0.25, "severe": 0.70}
_MODERATE_RISK = {"mild": 0.30, "moderate": 0.50, "severe": 0.20}
_BENIGN = {"mild": 0.60, "moderate": 0.35, "severe": 0.05}

SEVERITY_DIST = {
    "self_limited_fever": _BENIGN,
    "dengue": _MODERATE_RISK,
    "severe_dengue": _SEVERE,
    "malaria": _MODERATE_RISK,
    "malaria_falciparum_severe": _SEVERE,
    "typhoid_enteric": _MODERATE_RISK,
    "scrub_typhus": _MODERATE_RISK,
    "leptospirosis": _MODERATE_RISK,
    "chikungunya": _MODERATE_RISK,
    "tuberculosis_fever": _MODERATE_RISK,
    "sepsis_or_meningitis_emergency": _SEVERE,
}

CONDITION_IDS = list(CONDITIONS.keys())
SEVERITIES = ("mild", "moderate", "severe")


# ---------------------------------------------------------------------------
# Vitals profile: baseline + fever-specific deltas, severe severities seeded
# into the danger band so Path 1 (emergency.py) fires by construction rather
# than by post-hoc editing (memo section 6.4).
# ---------------------------------------------------------------------------

def vitals_fn(rng, age_years, sex, age_band, condition_id, severity_band):
    specs = dict(baseline_vitals(age_years))
    base_temp = specs["temperature"]
    base_pulse = specs["pulse"]
    base_rr = specs["respiratory_rate"]
    base_spo2 = specs["spo2"]
    base_sbp = specs["bp_systolic"]

    if severity_band == "mild":
        specs["temperature"] = VitalSpec(base_temp.mean + 1.0, 0.4, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + 10, base_pulse.sd, base_pulse.clip_lo, base_pulse.clip_hi)
    elif severity_band == "moderate":
        specs["temperature"] = VitalSpec(base_temp.mean + 1.8, 0.5, 34, 41)
        specs["pulse"] = VitalSpec(base_pulse.mean + 22, base_pulse.sd, base_pulse.clip_lo, base_pulse.clip_hi)
        specs["respiratory_rate"] = VitalSpec(base_rr.mean + 4, base_rr.sd, base_rr.clip_lo, base_rr.clip_hi)
    else:  # severe -- seed toward the Path-1 danger band for the emergency conditions
        is_emergency_condition = condition_id in (
            "severe_dengue", "malaria_falciparum_severe", "sepsis_or_meningitis_emergency")
        specs["temperature"] = VitalSpec(base_temp.mean + 2.5, 0.6, 34, 41)
        specs["pulse"] = VitalSpec(140.0 if is_emergency_condition else base_pulse.mean + 30, 10.0, 35, 220)
        specs["respiratory_rate"] = VitalSpec(32.0 if is_emergency_condition else base_rr.mean + 8, 4.0, 5, 90)
        if is_emergency_condition:
            specs["spo2"] = VitalSpec(88.0, 3.0, 60, 100)
            # Stress hyperglycaemia and hypoglycaemia both occur in critical
            # illness (sepsis, severe malaria); widened SD lets both GATE-RANGE
            # tails populate from a clinically real mechanism rather than a
            # fabricated diabetes storyline. ASSUMED magnitude.
            specs["glucose"] = VitalSpec(160.0, 90.0, 20, 700)
            if condition_id == "severe_dengue":
                specs["bp_systolic"] = VitalSpec(80.0, 8.0, 60, 220)
        else:
            specs["spo2"] = VitalSpec(base_spo2.mean - 2, 2.0, 60, 100)

    if condition_id == "tuberculosis_fever":
        specs["temperature"] = VitalSpec(specs["temperature"].mean - 0.5, specs["temperature"].sd, 34, 41)
    return specs


# ---------------------------------------------------------------------------
# Gateway rules
# ---------------------------------------------------------------------------

def _gw_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_convulsion")


def _gw_emg2(fields, ctx):
    return contains(fields, "danger_signs", "ds_unconscious")


def _gw_emg3_partial(fields, ctx):
    return contains(fields, "danger_signs", "ds_bleeding")


def _gw_emg3_full(fields, ctx):
    bleeding = value_of(fields, "bleeding_manifestation")
    real_bleeding = bool(bleeding) and bleeding not in (frozenset({"bl_none"}), frozenset({"bl_unknown"}))
    return contains(fields, "danger_signs", "ds_bleeding") or real_bleeding


def _gw_emg4(fields, ctx):
    return any_of(fields, "danger_signs", ["ds_breathing", "ds_no_urine", "ds_neck_stiff"])


def _gw_emg5(fields, ctx):
    return ctx.get("age_years", 99) < 5 and contains(fields, "danger_signs", "ds_cannot_feed")


def _gw_urg1_tb(fields, ctx):
    return (equals(fields, "fever_duration_band", "fd_gt_14")
            or equals(fields, "cough_ge_2_weeks", "c2_yes")
            or equals(fields, "weight_loss_present", "wl_yes")
            or equals(fields, "night_sweats", "ns_yes")
            or equals(fields, "tb_contact", "tbc_yes"))


def _gw_urg2_pregnancy(fields, ctx):
    return equals(fields, "pregnancy_status", "pg_yes")


def _guard_cough_asked(fields):
    return contains(fields, "fever_associated_symptoms", "as_cough")


def _guard_pregnancy_asked(fields):
    sex = fields.get("_sex")  # injected covariate, see generate.py
    age = fields.get("_age_years")
    return sex is not None and age is not None and sex.value == "F" and 15 <= age.value <= 49


def _no_unknown(rate, source):
    return dict(unknown_rate=rate, unknown_provenance={
        "sourceType": "ASSUMED", "source": source, "declaredOn": "2026-09-06"})


_NODES = {
    "FV-00": QuestionNode(
        nodeId="FV-00", fieldId="danger_signs", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ds_convulsion", "Fits or convulsions", next="FV-G1a"),
            AnswerOption("ds_unconscious", "Unconscious, or very drowsy / hard to wake", next="FV-G1a"),
            AnswerOption("ds_bleeding", "Bleeding from anywhere", next="FV-G1a"),
            AnswerOption("ds_breathing", "Difficulty breathing, or breathing fast", next="FV-G1a"),
            AnswerOption("ds_no_urine", "Has not passed urine since yesterday", next="FV-G1a"),
            AnswerOption("ds_neck_stiff", "Neck stiffness, or cannot bend the neck", next="FV-G1a"),
            AnswerOption("ds_cannot_feed", "Unable to drink or feed", next="FV-G1a"),
        ],
        default_next="FV-00B", unknown_option="ds_unknown", none_option="ds_none",
        **_no_unknown(0.02, "Danger-sign screens are rarely marked unknown in practice; low flat rate."),
    ),
    "FV-G1a": GatewayNode("FV-G1a", "GW-FEV-EMG-1", _gw_emg1, next="FV-G1b",
                           routeTo="emergency_convulsions",
                           severeConditions=["cerebral malaria", "meningitis", "febrile seizure"]),
    "FV-G1b": GatewayNode("FV-G1b", "GW-FEV-EMG-2", _gw_emg2, next="FV-G1c",
                           routeTo="emergency_unconscious",
                           severeConditions=["cerebral malaria", "meningitis", "sepsis", "hypoglycaemia"]),
    "FV-G1c": GatewayNode("FV-G1c", "GW-FEV-EMG-3", _gw_emg3_partial, next="FV-G1d",
                           routeTo="emergency_heavy_bleeding",
                           severeConditions=["severe dengue", "sepsis with DIC", "enteric perforation"]),
    "FV-G1d": GatewayNode("FV-G1d", "GW-FEV-EMG-4", _gw_emg4, next="FV-G1e",
                           raisesTo="REFER_EMERGENCY",
                           severeConditions=["sepsis", "meningitis", "severe malaria", "severe dengue"]),
    "FV-G1e": GatewayNode("FV-G1e", "GW-FEV-EMG-5", _gw_emg5, next="FV-00B",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

    "FV-00B": QuestionNode(
        nodeId="FV-00B", fieldId="progression", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pr_better", "Better", next="FV-00C"),
            AnswerOption("pr_same", "About the same", next="FV-00C"),
            AnswerOption("pr_worse", "Worse", next="FV-00C"),
        ],
        default_next="FV-00C", unknown_option="pr_unknown",
        **_no_unknown(0.03, "Progression knowable; low flat rate."),
    ),
    "FV-00C": QuestionNode(
        nodeId="FV-00C", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedy", next="FV-01"),
            AnswerOption("pt_pharmacy_medicine", "Pharmacy medicine", next="FV-01"),
            AnswerOption("pt_ayush", "AYUSH / traditional medicine", next="FV-01"),
            AnswerOption("pt_other_facility", "Treated at another facility", next="FV-01"),
        ],
        default_next="FV-01", unknown_option="pt_unknown", none_option="pt_none",
        **_no_unknown(0.03, "Flat, low."),
    ),

    "FV-01": QuestionNode(
        nodeId="FV-01", fieldId="fever_duration_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fd_today", "Today only", next="FV-02"),
            AnswerOption("fd_1_3", "1 to 3 days", next="FV-02"),
            AnswerOption("fd_4_7", "4 to 7 days", next="FV-02"),
            AnswerOption("fd_8_14", "8 to 14 days", next="FV-02"),
            AnswerOption("fd_gt_14", "More than 14 days", next="FV-G2a"),
        ],
        default_next="FV-02", unknown_option="fd_unknown",
        **_no_unknown(0.03, "Duration is usually knowable; low flat rate."),
    ),
    "FV-G2a": GatewayNode("FV-G2a", "GW-FEV-URG-1", _gw_urg1_tb, next="FV-02", raisesTo="REFER_URGENT",
                           severeConditions=["pulmonary TB"]),

    "FV-02": QuestionNode(
        nodeId="FV-02", fieldId="fever_pattern", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("fp_stepladder", "Rising a little more each day, does not fully settle",
                         next="FV-03", valueToken="stepladder fever"),
            AnswerOption("fp_cyclical", "Comes and goes, with shaking chills",
                         next="FV-03", valueToken="cyclical high fever with chills"),
            AnswerOption("fp_evening", "Rises in the evening or at night", next="FV-03",
                         valueToken="evening fever"),
            AnswerOption("fp_continuous", "High and continuous, no clear pattern", next="FV-03",
                         valueToken="high fever"),
            AnswerOption("fp_mild", "Low-grade throughout", next="FV-03", valueToken="mild fever"),
        ],
        default_next="FV-03", unknown_option="fp_unknown",
        **_no_unknown(0.03, "The most clinically load-bearing node; kept a low flat unknown rate."),
    ),

    "FV-03": QuestionNode(
        nodeId="FV-03", fieldId="fever_max_band", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ft_lt_38", "Below 38C / 100.4F", next="FV-04"),
            AnswerOption("ft_38_39", "38 to 39C", next="FV-04"),
            AnswerOption("ft_gt_39", "Above 39C / 102F", next="FV-04"),
            AnswerOption("ft_not_meas", "Not measured - feels hot", next="FV-04"),
        ],
        default_next="FV-04", unknown_option="ft_unknown", prefillFrom="temperature",
        **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-04": QuestionNode(
        nodeId="FV-04", fieldId="chills_rigors", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ch_rigors", "Yes - shaking, teeth chattering", next="FV-05"),
            AnswerOption("ch_cold_only", "Feels cold, but no shaking", next="FV-05"),
            AnswerOption("ch_no", "No", next="FV-05"),
        ],
        default_next="FV-05", unknown_option="ch_unknown", **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-05": QuestionNode(
        nodeId="FV-05", fieldId="rash_with_fever", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rf_yes", "Yes", next="FV-S1"),
            AnswerOption("rf_no", "No rash seen", next="FV-06"),
        ],
        default_next="FV-06", unknown_option="rf_unknown", **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-S1": SubtreeRefNode("FV-S1", RASH_MORPH_NODES, entry="RSH-03", returnNext="FV-06"),

    "FV-06": QuestionNode(
        nodeId="FV-06", fieldId="bleeding_manifestation", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("bl_gums", "Bleeding gums", next="FV-G3"),
            AnswerOption("bl_nose", "Nose bleed", next="FV-G3"),
            AnswerOption("bl_skin", "Red or purple spots under skin", next="FV-G3"),
            AnswerOption("bl_vomit", "Blood in vomit", next="FV-G3"),
            AnswerOption("bl_stool", "Black or bloody stool", next="FV-G3"),
            AnswerOption("bl_urine", "Blood in urine", next="FV-G3"),
        ],
        default_next="FV-07", unknown_option="bl_unknown", none_option="bl_none",
        **_no_unknown(0.02, "Flat, low."),
    ),
    "FV-G3": GatewayNode("FV-G3", "GW-FEV-EMG-3", _gw_emg3_full, next="FV-07",
                          routeTo="emergency_heavy_bleeding",
                          severeConditions=["severe dengue", "sepsis with DIC", "enteric perforation"]),

    "FV-07": QuestionNode(
        nodeId="FV-07", fieldId="fever_associated_symptoms", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("as_body_ache_severe", "Severe body ache all over", valueToken="severe body ache"),
            AnswerOption("as_retro_orbital", "Pain behind the eyes", valueToken="retro-orbital pain"),
            AnswerOption("as_joint_pain", "Joint pain", valueToken="joint pain"),
            AnswerOption("as_headache", "Headache", valueToken="headache"),
            AnswerOption("as_vomiting", "Vomiting"),
            AnswerOption("as_loose_motions", "Loose motions"),
            AnswerOption("as_abdominal_pain", "Stomach pain"),
            AnswerOption("as_burning_urine", "Burning urination"),
            AnswerOption("as_cough", "Cough"),
        ],
        default_next="FV-S2", unknown_option="as_unknown", none_option="as_none",
        **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-S2": SubtreeRefNode("FV-S2", make_tb_screen_nodes(), entry="TBS-01", returnNext="FV-G2b"),
    "FV-G2b": GatewayNode("FV-G2b", "GW-FEV-URG-1", _gw_urg1_tb, next="FV-S3", raisesTo="REFER_URGENT",
                           severeConditions=["pulmonary TB"]),
    "FV-S3": SubtreeRefNode("FV-S3", make_exposure_context_fever_nodes(), entry="ECF-01", returnNext="FV-12"),
    "FV-12": QuestionNode(
        nodeId="FV-12", fieldId="pregnancy_status", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("pg_yes", "Yes", next="FV-G4"),
            AnswerOption("pg_no", "No", next="FV-END"),
        ],
        default_next="FV-END", unknown_option="pg_unknown", guard=_guard_pregnancy_asked,
        **_no_unknown(0.02, "Flat, low."),
    ),
    "FV-G4": GatewayNode("FV-G4", "GW-FEV-URG-2", _gw_urg2_pregnancy, next="FV-END",
                          raisesTo="REFER_URGENT",
                          severeConditions=["malaria in pregnancy", "sepsis", "pre-eclampsia"]),
    "FV-END": TerminalNode("FV-END"),
}

BRANCH = BranchDef(categoryId=CATEGORY_ID, version=BRANCH_VERSION,
                    requiredDisposition=REQUIRED_DISPOSITION, nodes=_NODES, entry="FV-00")


# ---------------------------------------------------------------------------
# Answer model entries
# ---------------------------------------------------------------------------

def _uniform(options):
    p = 1.0 / len(options)
    return {o: p for o in options}


def _peaked(options, peak, peak_p):
    rest = [o for o in options if o != peak]
    rest_p = (1.0 - peak_p) / len(rest)
    d = {o: rest_p for o in rest}
    d[peak] = peak_p
    return d


_SRC = "ASSUMED"
_SRC_TEXT = ("Coarse infra-build distribution proving the machine; not physician-reviewed. "
             "Section 6.3 fill-in is a separate, deferred step.")

_entries = []

_entries += expand_entries("FV-00B", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"pr_better": 0.40, "pr_same": 0.40, "pr_worse": 0.20},
    "moderate": {"pr_better": 0.20, "pr_same": 0.45, "pr_worse": 0.35},
    "severe": {"pr_better": 0.05, "pr_same": 0.25, "pr_worse": 0.70},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("FV-00C", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    s: {"pt_home_remedy": 0.25, "pt_pharmacy_medicine": 0.35, "pt_ayush": 0.08, "pt_other_facility": 0.05}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("FV-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_convulsion": 0.001, "ds_unconscious": 0.001, "ds_bleeding": 0.001,
             "ds_breathing": 0.005, "ds_no_urine": 0.002, "ds_neck_stiff": 0.001, "ds_cannot_feed": 0.002},
    "moderate": {"ds_convulsion": 0.005, "ds_unconscious": 0.005, "ds_bleeding": 0.008,
                 "ds_breathing": 0.02, "ds_no_urine": 0.01, "ds_neck_stiff": 0.005, "ds_cannot_feed": 0.01},
    "severe": {"ds_convulsion": 0.08, "ds_unconscious": 0.08, "ds_bleeding": 0.08,
               "ds_breathing": 0.15, "ds_no_urine": 0.08, "ds_neck_stiff": 0.08, "ds_cannot_feed": 0.10},
}, overrides={
    ("malaria_falciparum_severe", "severe"): {
        "ds_convulsion": 0.35, "ds_unconscious": 0.45, "ds_bleeding": 0.05,
        "ds_breathing": 0.15, "ds_no_urine": 0.10, "ds_neck_stiff": 0.05, "ds_cannot_feed": 0.20},
    ("sepsis_or_meningitis_emergency", "severe"): {
        "ds_convulsion": 0.25, "ds_unconscious": 0.40, "ds_bleeding": 0.10,
        "ds_breathing": 0.20, "ds_no_urine": 0.15, "ds_neck_stiff": 0.50, "ds_cannot_feed": 0.25},
    ("severe_dengue", "severe"): {
        "ds_convulsion": 0.02, "ds_unconscious": 0.15, "ds_bleeding": 0.50,
        "ds_breathing": 0.20, "ds_no_urine": 0.10, "ds_neck_stiff": 0.02, "ds_cannot_feed": 0.15},
}, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("FV-01", "categorical", CONDITION_IDS, SEVERITIES, {
    "mild": {"fd_today": 0.35, "fd_1_3": 0.45, "fd_4_7": 0.15, "fd_8_14": 0.04, "fd_gt_14": 0.01},
    "moderate": {"fd_today": 0.20, "fd_1_3": 0.45, "fd_4_7": 0.25, "fd_8_14": 0.07, "fd_gt_14": 0.03},
    "severe": {"fd_today": 0.10, "fd_1_3": 0.35, "fd_4_7": 0.35, "fd_8_14": 0.12, "fd_gt_14": 0.08},
}, overrides={
    ("tuberculosis_fever", s): {"fd_today": 0.02, "fd_1_3": 0.08, "fd_4_7": 0.20, "fd_8_14": 0.30, "fd_gt_14": 0.40}
    for s in SEVERITIES
}, source_type=_SRC, source=_SRC_TEXT)

_FPAT_OPTIONS = ["fpat_stepladder", "fpat_cyclical", "fpat_evening", "fpat_continuous", "fpat_mild"]
_fpat_base = {
    "mild": {"fpat_mild": 0.55, "fpat_continuous": 0.20, "fpat_cyclical": 0.10, "fpat_evening": 0.10, "fpat_stepladder": 0.05},
    "moderate": {"fpat_mild": 0.20, "fpat_continuous": 0.40, "fpat_cyclical": 0.15, "fpat_evening": 0.15, "fpat_stepladder": 0.10},
    "severe": {"fpat_mild": 0.05, "fpat_continuous": 0.55, "fpat_cyclical": 0.15, "fpat_evening": 0.15, "fpat_stepladder": 0.10},
}
_fpat_overrides = {}
for s in SEVERITIES:
    _fpat_overrides[("malaria", s)] = peaked(_FPAT_OPTIONS, "fpat_cyclical", 0.65)
    _fpat_overrides[("malaria_falciparum_severe", s)] = peaked(_FPAT_OPTIONS, "fpat_continuous", 0.55)
    _fpat_overrides[("typhoid_enteric", s)] = peaked(_FPAT_OPTIONS, "fpat_stepladder", 0.70)
    _fpat_overrides[("tuberculosis_fever", s)] = peaked(_FPAT_OPTIONS, "fpat_evening", 0.65)
    _fpat_overrides[("dengue", s)] = peaked(_FPAT_OPTIONS, "fpat_continuous", 0.60)
    _fpat_overrides[("severe_dengue", s)] = peaked(_FPAT_OPTIONS, "fpat_continuous", 0.70)
_entries += expand_entries("FV-02", "categorical", CONDITION_IDS, SEVERITIES, _fpat_base,
                            overrides=_fpat_overrides, source_type="IND-PRESENT",
                            source="canonical_dataset fever pattern audit")

_cr_base = {s: {"cr_none": 0.75, "cr_chills_only": 0.15, "cr_rigors": 0.10} for s in SEVERITIES}
_cr_malaria = {s: {"cr_none": 0.05, "cr_chills_only": 0.25, "cr_rigors": 0.70} for s in SEVERITIES}
_entries += expand_entries("FV-03", "categorical", CONDITION_IDS, SEVERITIES, _cr_base,
                            overrides={("malaria", s): _cr_malaria[s] for s in SEVERITIES},
                            source_type=_SRC, source=_SRC_TEXT)

_rf_base = {s: {"rf_yes": 0.05, "rf_no": 0.95} for s in SEVERITIES}
_rf_dengue = {s: {"rf_yes": 0.40, "rf_no": 0.60} for s in SEVERITIES}
_entries += expand_entries("FV-04", "categorical", CONDITION_IDS, SEVERITIES, _rf_base,
                            overrides={("dengue", s): _rf_dengue[s] for s in SEVERITIES},
                            source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("FV-05", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"tmax_under_100": 0.35, "tmax_100_102": 0.45, "tmax_gt_102": 0.20} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("FV-06", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"bl_gums": 0.002, "bl_nose": 0.002, "bl_skin": 0.002, "bl_vomit": 0.001,
             "bl_stool": 0.001, "bl_urine": 0.001},
    "moderate": {"bl_gums": 0.01, "bl_nose": 0.01, "bl_skin": 0.02, "bl_vomit": 0.005,
                 "bl_stool": 0.005, "bl_urine": 0.005},
    "severe": {"bl_gums": 0.05, "bl_nose": 0.05, "bl_skin": 0.08, "bl_vomit": 0.03,
               "bl_stool": 0.03, "bl_urine": 0.02},
}, overrides={
    ("severe_dengue", "severe"): {"bl_gums": 0.35, "bl_nose": 0.25, "bl_skin": 0.45,
                                  "bl_vomit": 0.15, "bl_stool": 0.10, "bl_urine": 0.05},
}, source_type=_SRC, source=_SRC_TEXT)

_as_base = {
    "mild": {"as_body_ache_severe": 0.10, "as_retro_orbital": 0.05, "as_joint_pain": 0.15,
             "as_headache": 0.25, "as_vomiting": 0.05, "as_loose_motions": 0.05,
             "as_abdominal_pain": 0.05, "as_burning_urine": 0.04, "as_cough": 0.20},
    "moderate": {"as_body_ache_severe": 0.25, "as_retro_orbital": 0.12, "as_joint_pain": 0.30,
                 "as_headache": 0.40, "as_vomiting": 0.12, "as_loose_motions": 0.10,
                 "as_abdominal_pain": 0.10, "as_burning_urine": 0.06, "as_cough": 0.25},
    "severe": {"as_body_ache_severe": 0.45, "as_retro_orbital": 0.20, "as_joint_pain": 0.40,
               "as_headache": 0.50, "as_vomiting": 0.25, "as_loose_motions": 0.15,
               "as_abdominal_pain": 0.20, "as_burning_urine": 0.08, "as_cough": 0.30},
}
_as_over = {}
for s in SEVERITIES:
    _as_over[("dengue", s)] = dict(_as_base[s], as_body_ache_severe=0.70, as_retro_orbital=0.55, as_joint_pain=0.60)
    _as_over[("chikungunya", s)] = dict(_as_base[s], as_joint_pain=0.85, as_body_ache_severe=0.60)
_entries += expand_entries("FV-07", "multi_bernoulli", CONDITION_IDS, SEVERITIES, _as_base,
                            overrides=_as_over, source_type=_SRC, source=_SRC_TEXT)

# Subtrees: TB-SCREEN and EXPOSURE-CONTEXT-FEVER
_entries += expand_tb_screen_entries(CONDITION_IDS, SEVERITIES, tb_conditions=("tuberculosis_fever",))
_entries += expand_exposure_context_entries(CONDITION_IDS, SEVERITIES)

_pg_base = {s: {"pg_yes": 0.05, "pg_no": 0.95} for s in SEVERITIES}
_entries += expand_entries("FV-12", "categorical", CONDITION_IDS, SEVERITIES, _pg_base,
                            source_type=_SRC, source=_SRC_TEXT)

# RASH-MORPH (RSH-03..RSH-09) entries
_entries += expand_entries("RSH-03", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"rdst_face_first": 0.15, "rdst_trunk": 0.30, "rdst_limbs": 0.20,
         "rdst_palms_soles": 0.05, "rdst_whole_body": 0.15, "rdst_one_patch": 0.15} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT + " (fever->rash subtree path, rarely walked)")

_entries += expand_entries("RSH-04", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"rm_flat_red": 0.35, "rm_raised": 0.25, "rm_fluid_blister": 0.05, "rm_pustular": 0.10,
         "rm_scaly_patch": 0.15, "rm_pale_patch": 0.05, "rm_purple_spots": 0.05} for s in SEVERITIES},
    overrides={(c, s): {"rm_flat_red": 0.60, "rm_raised": 0.20, "rm_fluid_blister": 0.03, "rm_pustular": 0.05,
                         "rm_scaly_patch": 0.07, "rm_pale_patch": 0.02, "rm_purple_spots": 0.03}
               for c in ("dengue", "severe_dengue") for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT + " (fever->rash subtree path, rarely walked)")

_entries += expand_entries("RSH-05", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"rs_itchy": 0.40, "rs_painful": 0.15, "rs_burning": 0.10, "rs_numb": 0.05,
         "rs_none": 0.30} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT + " (fever->rash subtree path, rarely walked)")

_entries += expand_entries("RSH-06", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"hp_normal_sensation": 0.90, "hp_reduced": 0.10} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT + " (fever->rash subtree path, rarely walked)")

_entries += expand_entries("RSH-07", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"nd_yes": 0.08, "nd_no": 0.92} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT + " (fever->rash subtree path, rarely walked)")

_entries += expand_entries("RSH-08", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"ho_yes": 0.15, "ho_no": 0.85} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT + " (fever->rash subtree path, rarely walked)")

_entries += expand_entries("RSH-09", "categorical", CONDITION_IDS, SEVERITIES,
    {s: {"ph_taken": 0.70, "ph_declined": 0.10, "ph_not_possible": 0.20} for s in SEVERITIES},
    source_type=_SRC, source=_SRC_TEXT + " (fever->rash subtree path, rarely walked)")
ANSWER_MODEL_ENTRIES = _entries

SPEC = CategorySpec(
    categoryId=CATEGORY_ID, branch=BRANCH, conditions=CONDITIONS,
    severity_dist=SEVERITY_DIST, vitals_fn=vitals_fn, answer_model_entries=ANSWER_MODEL_ENTRIES,
)
