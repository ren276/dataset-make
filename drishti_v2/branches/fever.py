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
from .authoring import expand_entries
from .spec import CategorySpec, ConditionSpec
from .subtrees import RASH_MORPH_NODES

CATEGORY_ID = "fever"
BRANCH_VERSION = "1.0.0-draft"
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
            or contains(fields, "exposure_context", "ex_tb_contact"))


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
        default_next="FV-01", unknown_option="ds_unknown", none_option="ds_none",
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
    "FV-G1e": GatewayNode("FV-G1e", "GW-FEV-EMG-5", _gw_emg5, next="FV-01",
                           raisesTo="REFER_EMERGENCY", severeConditions=["IMCI general danger sign"]),

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
        default_next="FV-08", unknown_option="as_unknown", none_option="as_none",
        **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-08": QuestionNode(
        nodeId="FV-08", fieldId="cough_ge_2_weeks", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("c2_yes", "Yes", next="FV-G2b"),
            AnswerOption("c2_no", "No", next="FV-09A"),
        ],
        default_next="FV-09A", unknown_option="c2_unknown", guard=_guard_cough_asked,
        **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-G2b": GatewayNode("FV-G2b", "GW-FEV-URG-1", _gw_urg1_tb, next="FV-09A", raisesTo="REFER_URGENT",
                           severeConditions=["pulmonary TB"]),

    "FV-09A": QuestionNode(
        nodeId="FV-09A", fieldId="weight_loss_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("wl_yes", "Losing weight", next="FV-G2c"),
            AnswerOption("wl_no", "No", next="FV-09B"),
        ],
        default_next="FV-09B", unknown_option="wl_unknown", **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-G2c": GatewayNode("FV-G2c", "GW-FEV-URG-1", _gw_urg1_tb, next="FV-09B", raisesTo="REFER_URGENT",
                           severeConditions=["pulmonary TB"]),
    "FV-09B": QuestionNode(
        nodeId="FV-09B", fieldId="night_sweats", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ns_yes", "Night sweats", next="FV-10"),
            AnswerOption("ns_no", "No", next="FV-10"),
        ],
        default_next="FV-10", unknown_option="ns_unknown", **_no_unknown(0.03, "Flat, low."),
    ),

    "FV-10": QuestionNode(
        nodeId="FV-10", fieldId="exposure_context", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("ex_mosquito", "Mosquitoes or standing water at home"),
            AnswerOption("ex_household", "Someone else at home has fever"),
            AnswerOption("ex_travel", "Travelled in the last month"),
            AnswerOption("ex_tb_contact", "Close contact with a TB patient", next="FV-G2e"),
            AnswerOption("ex_water_soil", "Works in paddy field / flood water / with animals"),
        ],
        default_next="FV-11", unknown_option="ex_unknown", none_option="ex_none",
        **_no_unknown(0.03, "Flat, low."),
    ),
    "FV-G2e": GatewayNode("FV-G2e", "GW-FEV-URG-1", _gw_urg1_tb, next="FV-11", raisesTo="REFER_URGENT",
                           severeConditions=["pulmonary TB"]),

    "FV-11": QuestionNode(
        nodeId="FV-11", fieldId="prior_treatment_taken", answerType="MULTI_CHOICE",
        options=[
            AnswerOption("pt_home_remedy", "Home remedy"),
            AnswerOption("pt_pharmacy_medicine", "Pharmacy medicine"),
            AnswerOption("pt_ayush", "AYUSH / traditional medicine"),
            AnswerOption("pt_other_facility", "Treated at another facility"),
        ],
        default_next="FV-12", unknown_option="pt_unknown", none_option="pt_none",
        **_no_unknown(0.03, "Flat, low."),
    ),
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

_entries += expand_entries("FV-00", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"ds_convulsion": 0.001, "ds_unconscious": 0.001, "ds_bleeding": 0.003,
             "ds_breathing": 0.005, "ds_no_urine": 0.005, "ds_neck_stiff": 0.002, "ds_cannot_feed": 0.01},
    "moderate": {"ds_convulsion": 0.01, "ds_unconscious": 0.01, "ds_bleeding": 0.02,
                 "ds_breathing": 0.03, "ds_no_urine": 0.02, "ds_neck_stiff": 0.01, "ds_cannot_feed": 0.03},
    "severe": {"ds_convulsion": 0.10, "ds_unconscious": 0.15, "ds_bleeding": 0.12,
               "ds_breathing": 0.25, "ds_no_urine": 0.15, "ds_neck_stiff": 0.08, "ds_cannot_feed": 0.20},
}, overrides={
    ("severe_dengue", "severe"): {"ds_convulsion": 0.02, "ds_unconscious": 0.10, "ds_bleeding": 0.55,
                                   "ds_breathing": 0.15, "ds_no_urine": 0.10, "ds_neck_stiff": 0.02,
                                   "ds_cannot_feed": 0.10},
    ("sepsis_or_meningitis_emergency", "severe"): {"ds_convulsion": 0.30, "ds_unconscious": 0.45,
                                                    "ds_bleeding": 0.08, "ds_breathing": 0.30,
                                                    "ds_no_urine": 0.20, "ds_neck_stiff": 0.40,
                                                    "ds_cannot_feed": 0.15},
    ("malaria_falciparum_severe", "severe"): {"ds_convulsion": 0.20, "ds_unconscious": 0.35,
                                               "ds_bleeding": 0.05, "ds_breathing": 0.15,
                                               "ds_no_urine": 0.10, "ds_neck_stiff": 0.05,
                                               "ds_cannot_feed": 0.10},
}, source_type=_SRC, source=_SRC_TEXT)

_fd_base = {
    "mild": {"fd_today": 0.30, "fd_1_3": 0.35, "fd_4_7": 0.25, "fd_8_14": 0.08, "fd_gt_14": 0.02},
    "moderate": {"fd_today": 0.15, "fd_1_3": 0.30, "fd_4_7": 0.30, "fd_8_14": 0.18, "fd_gt_14": 0.07},
    "severe": {"fd_today": 0.10, "fd_1_3": 0.20, "fd_4_7": 0.30, "fd_8_14": 0.25, "fd_gt_14": 0.15},
}
_fd_chronic = {
    "mild": {"fd_today": 0.05, "fd_1_3": 0.10, "fd_4_7": 0.20, "fd_8_14": 0.30, "fd_gt_14": 0.35},
    "moderate": {"fd_today": 0.03, "fd_1_3": 0.07, "fd_4_7": 0.15, "fd_8_14": 0.30, "fd_gt_14": 0.45},
    "severe": {"fd_today": 0.02, "fd_1_3": 0.05, "fd_4_7": 0.13, "fd_8_14": 0.30, "fd_gt_14": 0.50},
}
_fd_overrides = {}
for c in ("tuberculosis_fever", "typhoid_enteric"):
    for s in SEVERITIES:
        _fd_overrides[(c, s)] = _fd_chronic[s]
_entries += expand_entries("FV-01", "categorical", CONDITION_IDS, SEVERITIES, _fd_base,
                            overrides=_fd_overrides, source_type=_SRC, source=_SRC_TEXT)

_FP_OPTS = ["fp_stepladder", "fp_cyclical", "fp_evening", "fp_continuous", "fp_mild"]
_fp_base = {s: _peaked(_FP_OPTS, "fp_mild", 0.40) if s == "mild" else
               (_peaked(_FP_OPTS, "fp_continuous", 0.35) if s == "moderate" else
                _peaked(_FP_OPTS, "fp_continuous", 0.40)) for s in SEVERITIES}
_fp_overrides = {}
for s in SEVERITIES:
    _fp_overrides[("typhoid_enteric", s)] = _peaked(_FP_OPTS, "fp_stepladder", 0.70)
    _fp_overrides[("malaria", s)] = _peaked(_FP_OPTS, "fp_cyclical", 0.65)
    _fp_overrides[("malaria_falciparum_severe", s)] = _peaked(_FP_OPTS, "fp_cyclical", 0.70)
    _fp_overrides[("tuberculosis_fever", s)] = _peaked(_FP_OPTS, "fp_evening", 0.60)
    _fp_overrides[("dengue", s)] = _peaked(_FP_OPTS, "fp_continuous", 0.60)
    _fp_overrides[("severe_dengue", s)] = _peaked(_FP_OPTS, "fp_continuous", 0.65)
_entries += expand_entries("FV-02", "categorical", CONDITION_IDS, SEVERITIES, _fp_base,
                            overrides=_fp_overrides, source_type="ASSUMED",
                            source="Mapping (stepladder->typhoid, cyclical-chills->malaria, "
                                   "evening->TB, continuous/high->dengue) is grounded in the "
                                   "measured classifier valueToken flips (tree memo section 3.3); "
                                   "the per-condition peak weights themselves are ASSUMED.")

_ft_base = {
    "mild": {"ft_lt_38": 0.35, "ft_38_39": 0.40, "ft_gt_39": 0.10, "ft_not_meas": 0.15},
    "moderate": {"ft_lt_38": 0.15, "ft_38_39": 0.45, "ft_gt_39": 0.30, "ft_not_meas": 0.10},
    "severe": {"ft_lt_38": 0.05, "ft_38_39": 0.30, "ft_gt_39": 0.55, "ft_not_meas": 0.10},
}
_entries += expand_entries("FV-03", "categorical", CONDITION_IDS, SEVERITIES, _ft_base,
                            source_type=_SRC, source=_SRC_TEXT)

_ch_base = {
    "mild": {"ch_rigors": 0.10, "ch_cold_only": 0.30, "ch_no": 0.60},
    "moderate": {"ch_rigors": 0.25, "ch_cold_only": 0.35, "ch_no": 0.40},
    "severe": {"ch_rigors": 0.35, "ch_cold_only": 0.35, "ch_no": 0.30},
}
_ch_malaria = {s: {"ch_rigors": 0.75, "ch_cold_only": 0.15, "ch_no": 0.10} for s in SEVERITIES}
_ch_overrides = {}
for c in ("malaria", "malaria_falciparum_severe"):
    for s in SEVERITIES:
        _ch_overrides[(c, s)] = _ch_malaria[s]
_entries += expand_entries("FV-04", "categorical", CONDITION_IDS, SEVERITIES, _ch_base,
                            overrides=_ch_overrides, source_type=_SRC, source=_SRC_TEXT)

_rf_base = {s: {"rf_yes": 0.06, "rf_no": 0.94} for s in SEVERITIES}
_rf_dengue = {s: {"rf_yes": 0.35, "rf_no": 0.65} for s in SEVERITIES}
_rf_overrides = {}
for c in ("dengue", "severe_dengue"):
    for s in SEVERITIES:
        _rf_overrides[(c, s)] = _rf_dengue[s]
_entries += expand_entries("FV-05", "categorical", CONDITION_IDS, SEVERITIES, _rf_base,
                            overrides=_rf_overrides, source_type=_SRC, source=_SRC_TEXT)

_entries += expand_entries("FV-06", "multi_bernoulli", CONDITION_IDS, SEVERITIES, {
    "mild": {"bl_gums": 0.002, "bl_nose": 0.002, "bl_skin": 0.002, "bl_vomit": 0.001,
             "bl_stool": 0.001, "bl_urine": 0.001},
    "moderate": {"bl_gums": 0.01, "bl_nose": 0.01, "bl_skin": 0.01, "bl_vomit": 0.005,
                 "bl_stool": 0.005, "bl_urine": 0.005},
    "severe": {"bl_gums": 0.05, "bl_nose": 0.05, "bl_skin": 0.05, "bl_vomit": 0.03,
               "bl_stool": 0.03, "bl_urine": 0.02},
}, overrides={
    ("severe_dengue", "severe"): {"bl_gums": 0.35, "bl_nose": 0.30, "bl_skin": 0.40,
                                   "bl_vomit": 0.25, "bl_stool": 0.15, "bl_urine": 0.08},
    ("severe_dengue", "moderate"): {"bl_gums": 0.15, "bl_nose": 0.12, "bl_skin": 0.18,
                                     "bl_vomit": 0.08, "bl_stool": 0.05, "bl_urine": 0.03},
}, source_type=_SRC, source=_SRC_TEXT)

_fas_base = {
    "mild": {"as_body_ache_severe": 0.05, "as_retro_orbital": 0.02, "as_joint_pain": 0.05,
             "as_headache": 0.30, "as_vomiting": 0.10, "as_loose_motions": 0.08,
             "as_abdominal_pain": 0.10, "as_burning_urine": 0.03, "as_cough": 0.15},
    "moderate": {"as_body_ache_severe": 0.20, "as_retro_orbital": 0.08, "as_joint_pain": 0.12,
                 "as_headache": 0.40, "as_vomiting": 0.18, "as_loose_motions": 0.12,
                 "as_abdominal_pain": 0.15, "as_burning_urine": 0.04, "as_cough": 0.18},
    "severe": {"as_body_ache_severe": 0.40, "as_retro_orbital": 0.15, "as_joint_pain": 0.15,
               "as_headache": 0.45, "as_vomiting": 0.30, "as_loose_motions": 0.18,
               "as_abdominal_pain": 0.22, "as_burning_urine": 0.05, "as_cough": 0.20},
}
_fas_overrides = {}
for s in SEVERITIES:
    _fas_overrides[("tuberculosis_fever", s)] = dict(_fas_base[s], as_cough=0.85)
    _fas_overrides[("chikungunya", s)] = dict(_fas_base[s], as_joint_pain=0.75)
    _fas_overrides[("dengue", s)] = dict(_fas_base[s], as_retro_orbital=0.55, as_body_ache_severe=0.50)
    _fas_overrides[("severe_dengue", s)] = dict(_fas_base[s], as_retro_orbital=0.60, as_body_ache_severe=0.55)
    _fas_overrides[("typhoid_enteric", s)] = dict(_fas_base[s], as_abdominal_pain=0.45, as_loose_motions=0.35)
_entries += expand_entries("FV-07", "multi_bernoulli", CONDITION_IDS, SEVERITIES, _fas_base,
                            overrides=_fas_overrides, source_type=_SRC, source=_SRC_TEXT)

_c2_base = {s: {"c2_yes": 0.03, "c2_no": 0.97} for s in SEVERITIES}
_c2_tb = {s: {"c2_yes": 0.80, "c2_no": 0.20} for s in SEVERITIES}
_entries += expand_entries("FV-08", "categorical", CONDITION_IDS, SEVERITIES, _c2_base,
                            overrides={("tuberculosis_fever", s): _c2_tb[s] for s in SEVERITIES},
                            source_type=_SRC, source=_SRC_TEXT)

_wl_base = {s: {"wl_yes": 0.05, "wl_no": 0.95} for s in SEVERITIES}
_wl_tb = {s: {"wl_yes": 0.75, "wl_no": 0.25} for s in SEVERITIES}
_entries += expand_entries("FV-09A", "categorical", CONDITION_IDS, SEVERITIES, _wl_base,
                            overrides={("tuberculosis_fever", s): _wl_tb[s] for s in SEVERITIES},
                            source_type=_SRC, source=_SRC_TEXT)

_ns_base = {s: {"ns_yes": 0.04, "ns_no": 0.96} for s in SEVERITIES}
_ns_tb = {s: {"ns_yes": 0.70, "ns_no": 0.30} for s in SEVERITIES}
_entries += expand_entries("FV-09B", "categorical", CONDITION_IDS, SEVERITIES, _ns_base,
                            overrides={("tuberculosis_fever", s): _ns_tb[s] for s in SEVERITIES},
                            source_type=_SRC, source=_SRC_TEXT)

_ex_base = {
    "mild": {"ex_mosquito": 0.15, "ex_household": 0.10, "ex_travel": 0.05,
             "ex_tb_contact": 0.02, "ex_water_soil": 0.08},
    "moderate": {"ex_mosquito": 0.20, "ex_household": 0.12, "ex_travel": 0.06,
                 "ex_tb_contact": 0.03, "ex_water_soil": 0.10},
    "severe": {"ex_mosquito": 0.25, "ex_household": 0.15, "ex_travel": 0.07,
               "ex_tb_contact": 0.04, "ex_water_soil": 0.12},
}
_ex_overrides = {}
for s in SEVERITIES:
    for c in ("malaria", "malaria_falciparum_severe", "dengue", "severe_dengue"):
        _ex_overrides[(c, s)] = dict(_ex_base[s], ex_mosquito=0.65)
    _ex_overrides[("tuberculosis_fever", s)] = dict(_ex_base[s], ex_tb_contact=0.55)
    _ex_overrides[("leptospirosis", s)] = dict(_ex_base[s], ex_water_soil=0.60)
    _ex_overrides[("scrub_typhus", s)] = dict(_ex_base[s], ex_water_soil=0.45)
_entries += expand_entries("FV-10", "multi_bernoulli", CONDITION_IDS, SEVERITIES, _ex_base,
                            overrides=_ex_overrides, source_type=_SRC, source=_SRC_TEXT)

_pt_base = {s: {"pt_home_remedy": 0.20, "pt_pharmacy_medicine": 0.30,
                "pt_ayush": 0.08, "pt_other_facility": 0.05} for s in SEVERITIES}
_entries += expand_entries("FV-11", "multi_bernoulli", CONDITION_IDS, SEVERITIES, _pt_base,
                            source_type=_SRC, source=_SRC_TEXT)

_pg_base = {s: {"pg_yes": 0.05, "pg_no": 0.95} for s in SEVERITIES}
_entries += expand_entries("FV-12", "categorical", CONDITION_IDS, SEVERITIES, _pg_base,
                            source_type=_SRC, source=_SRC_TEXT)

# RASH-MORPH (RSH-03..RSH-09) is spliced in at FV-S1 when rash_with_fever==yes.
# The subtree's nodeIds are shared with the `rash` branch (subtrees.py docstring),
# but the answer model is per-category, so fever needs its own entries for these
# nodeIds keyed by fever's condition catalog -- this path is rarely walked
# (rf_yes is a low-probability outcome except for the dengue conditions), so the
# distributions below are deliberately simple baselines.
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
