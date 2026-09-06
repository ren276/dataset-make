"""
drishti_v2/vitals.py
======================
The per-vital triple (dataset-regeneration-design-memo.md section 5.1):

    <vital>_true          generator ground truth, audit/label-construction only, never a feature
    <vital>                the reading the device/worker actually saw, or null
    <vital>_provenance     DEVICE_MEASURED | MANUAL_ENTERED | NOT_MEASURED | DEVICE_ERROR

There is no DEFAULTED value and this module cannot emit one.

Eight vitals are first-class (D2 adds temperature and respiratory_rate to the
six drishti_pipeline already extracted): bp_systolic, bp_diastolic, pulse,
spo2, bmi, glucose, temperature, respiratory_rate.

Availability (NOT_MEASURED) and manual-vs-device split are drawn from a
facility_tier covariate that is independent of the latent condition by
construction (section 2.4) -- facility_tier is drawn once per row before the
condition-conditioned vitals_true values are drawn, and the availability
model never receives condition_id as an input. That is what makes GATE-LEAK
pass for vitals rather than merely for tree fields.

Numeric distributions below (means/SDs, availability rates, plausibility
bounds) are ASSUMED except where an IHCI/WHO-Asian/NFHS-5/pediatric-BP
citation is named -- those four are carried over from
drishti_pipeline/config.py's ADULT_THRESHOLDS and pediatric formulas
(Narang et al., Indian Pediatrics), redeclared here rather than imported, so
this module has no dependency on the old pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Optional, Tuple

DEVICE_MEASURED = "DEVICE_MEASURED"
MANUAL_ENTERED = "MANUAL_ENTERED"
NOT_MEASURED = "NOT_MEASURED"
DEVICE_ERROR = "DEVICE_ERROR"
PROVENANCE_VALUES = (DEVICE_MEASURED, MANUAL_ENTERED, NOT_MEASURED, DEVICE_ERROR)

VITALS = ("bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi", "glucose",
          "temperature", "respiratory_rate")

PEDIATRIC_BMI_STRATEGY = "B2"  # bmi marked NOT_MEASURED (not-assessed) for age < 18

# ---------------------------------------------------------------------------
# Adult thresholds carried over from drishti_pipeline/config.py (IHCI / WHO
# Asian BMI / ICMR-INDIAB). Redeclared, not imported -- drishti_v2 does not
# depend on the old pipeline.
# ---------------------------------------------------------------------------
IHCI_SBP_STAGE1 = 140.0
IHCI_DBP_STAGE1 = 90.0
WHO_ASIAN_BMI_OBESE_MIN = 25.0
WHO_ASIAN_BMI_NORMAL_MAX = 22.9


def sbp_95th_pediatric(age: int, sex: str) -> float:
    return 110.0 + 1.6 * age + (1.0 if sex.upper() == "F" else 0.0)


def dbp_95th_pediatric(age: int, sex: str) -> float:
    return 79.0 + 0.7 * age + (1.0 if sex.upper() == "F" else 0.0)


# ---------------------------------------------------------------------------
# Facility tier -- the covariate the availability model is allowed to depend
# on. Drawn once per row, independent of category/condition.
# ---------------------------------------------------------------------------
FACILITY_TIERS = ("LOW", "MEDIUM", "HIGH")
FACILITY_TIER_SHARE = (0.35, 0.45, 0.20)  # ASSUMED: rural PHC capability skew
FACILITY_TIER_PROVENANCE = {
    "sourceType": "ASSUMED",
    "source": "Rural PHC capability is skewed toward lower-resourced facilities; no Indian "
              "facility-tier census was retrieved this session. Declared, not silent.",
    "declaredOn": "2026-09-06",
}


def draw_facility_tier(rng) -> str:
    return rng.choice("vitals::facility_tier", FACILITY_TIERS, FACILITY_TIER_SHARE)


# NOT_MEASURED probability per vital per facility tier. Never a function of
# condition_id. ASSUMED throughout -- device/consumable availability at rural
# Indian PHCs was not measured in this session.
AVAILABILITY_RATE: Dict[str, Dict[str, float]] = {
    "bp_systolic":       {"LOW": 0.10, "MEDIUM": 0.04, "HIGH": 0.01},
    "bp_diastolic":      {"LOW": 0.10, "MEDIUM": 0.04, "HIGH": 0.01},
    "pulse":             {"LOW": 0.08, "MEDIUM": 0.03, "HIGH": 0.01},
    "spo2":              {"LOW": 0.30, "MEDIUM": 0.10, "HIGH": 0.02},
    "bmi":               {"LOW": 0.25, "MEDIUM": 0.12, "HIGH": 0.05},
    "glucose":           {"LOW": 0.55, "MEDIUM": 0.25, "HIGH": 0.08},
    "temperature":       {"LOW": 0.12, "MEDIUM": 0.05, "HIGH": 0.01},
    "respiratory_rate":  {"LOW": 0.20, "MEDIUM": 0.10, "HIGH": 0.03},
}
DEVICE_ERROR_RATE: Dict[str, float] = {v: 0.005 for v in VITALS}
MANUAL_SHARE: Dict[str, float] = {
    # probability a *measured* reading was MANUAL_ENTERED rather than DEVICE_MEASURED
    "bp_systolic": 0.35, "bp_diastolic": 0.35, "pulse": 0.40, "spo2": 0.05,
    "bmi": 0.30, "glucose": 0.05, "temperature": 0.45, "respiratory_rate": 0.60,
}
AVAILABILITY_PROVENANCE = {
    "sourceType": "ASSUMED",
    "source": "No Indian PHC device/consumable-availability survey was retrieved this "
              "session. Ordinal skew (glucometer scarcer than a thermometer; oximeter "
              "scarcer at LOW tier) reflects general rural-PHC equipment literature, not "
              "a cited rate table. Declared per D5.1 rule 4.",
    "declaredOn": "2026-09-06",
}

# Measurement-error SD applied to the true value when a reading is measured.
NOISE_SD: Dict[str, float] = {
    "bp_systolic": 4.0, "bp_diastolic": 3.0, "pulse": 3.0, "spo2": 1.0,
    "bmi": 0.5, "glucose": 6.0, "temperature": 0.2, "respiratory_rate": 1.5,
}

# GATE-PLAUSIBLE: physiologically-possible-in-an-ambulatory-patient bounds,
# per vital per broad age band. A row outside these is rejected as
# implausible; a row inside them but in the danger band (section 6.4 note)
# is not rejected -- plausible-but-severe is not the same as impossible.
PLAUSIBILITY_RANGES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "bp_systolic":      {"0_4": (50, 140), "5_14": (60, 160), "15_29": (70, 220),
                          "30_44": (70, 220), "45_59": (70, 230), "60_plus": (70, 230)},
    "bp_diastolic":     {"0_4": (30, 90), "5_14": (35, 100), "15_29": (40, 140),
                          "30_44": (40, 140), "45_59": (40, 140), "60_plus": (40, 140)},
    "pulse":            {"0_4": (70, 200), "5_14": (50, 180), "15_29": (35, 200),
                          "30_44": (35, 200), "45_59": (35, 200), "60_plus": (35, 200)},
    "spo2":             {"0_4": (60, 100), "5_14": (60, 100), "15_29": (60, 100),
                          "30_44": (60, 100), "45_59": (60, 100), "60_plus": (60, 100)},
    "bmi":              {"0_4": (8, 25), "5_14": (10, 35), "15_29": (12, 55),
                          "30_44": (12, 55), "45_59": (12, 55), "60_plus": (12, 55)},
    "glucose":          {"0_4": (20, 600), "5_14": (20, 600), "15_29": (20, 700),
                          "30_44": (20, 700), "45_59": (20, 700), "60_plus": (20, 700)},
    "temperature":      {"0_4": (30, 42), "5_14": (30, 42), "15_29": (30, 42),
                          "30_44": (30, 42), "45_59": (30, 42), "60_plus": (30, 42)},
    "respiratory_rate": {"0_4": (10, 90), "5_14": (8, 60), "15_29": (5, 50),
                          "30_44": (5, 50), "45_59": (5, 50), "60_plus": (5, 50)},
}

ENCOUNTER_WINDOW_MONTHS = 24
GENERATION_DATE = date(2026, 9, 6)


def draw_encounter_date(rng, row_id: str) -> str:
    window_start = GENERATION_DATE - timedelta(days=ENCOUNTER_WINDOW_MONTHS * 30)
    span_days = (GENERATION_DATE - window_start).days
    offset = int(rng.uniform("encounter_date", 0, span_days))
    d = window_start + timedelta(days=offset)
    return d.isoformat()


@dataclass(frozen=True)
class VitalSpec:
    mean: float
    sd: float
    clip_lo: float
    clip_hi: float


@dataclass(frozen=True)
class VitalTriple:
    true_value: float
    observed_value: Optional[float]
    provenance: str


def draw_vital_true(rng, vital: str, spec: VitalSpec) -> float:
    v = rng.normal(f"vital_true::{vital}", spec.mean, spec.sd)
    return max(spec.clip_lo, min(spec.clip_hi, v))


def baseline_vitals(age_years: int) -> Dict[str, VitalSpec]:
    """
    Population-normal vitals by age, independent of category/condition. Branch
    condition profiles start from this and apply their own declared deltas
    (fever raises temperature and pulse, hypotension drops bp_systolic, etc).
    Pulse and BP baselines are age-shaped (children run faster/lower-BP than
    adults); the shape is ASSUMED and not re-derived from a pediatric-vitals
    table this session.
    """
    if age_years < 1:
        pulse_mean, rr_mean = 130.0, 40.0
    elif age_years < 5:
        pulse_mean, rr_mean = 110.0, 28.0
    elif age_years < 15:
        pulse_mean, rr_mean = 90.0, 20.0
    else:
        pulse_mean, rr_mean = 78.0, 16.0

    if age_years < 18:
        sbp_mean = sbp_95th_pediatric(age_years, "M") * 0.78
        dbp_mean = dbp_95th_pediatric(age_years, "M") * 0.78
    else:
        sbp_mean, dbp_mean = 118.0, 76.0

    return {
        "bp_systolic": VitalSpec(sbp_mean, 8.0, 70, 220),
        "bp_diastolic": VitalSpec(dbp_mean, 6.0, 40, 140),
        "pulse": VitalSpec(pulse_mean, 8.0, 35, 220),
        "spo2": VitalSpec(98.0, 1.0, 60, 100),
        "bmi": population_bmi_spec(age_years),
        "glucose": VitalSpec(105.0, 12.0, 20, 700),
        "temperature": VitalSpec(37.0, 0.3, 30, 42),
        "respiratory_rate": VitalSpec(rr_mean, 2.5, 5, 90),
    }


def population_bmi_spec(age_years: int) -> VitalSpec:
    """
    One population BMI distribution, independent of category and condition by
    construction (D4: BMI is never a route to the label). ASSUMED shaped
    toward NFHS-5-reported Indian adult BMI (mean in the low-20s, WHO-Asian
    overweight cutoff at 23); not re-derived from an NFHS-5 table cell this
    session.
    """
    if age_years < 18:
        return VitalSpec(16.5, 2.5, 10, 30)
    return VitalSpec(21.5, 3.8, 13, 42)


def generate_vitals(rng, age_years: int, age_band: str, facility_tier: str,
                     specs: Dict[str, VitalSpec]) -> Dict[str, VitalTriple]:
    """
    specs: one VitalSpec per vital, already conditioned on (condition, severity,
    age, sex) by the caller (a branch's condition profile). This function only
    handles the true-value draw, the availability/provenance model and
    measurement noise -- the clinical content lives in the branch's profile.
    """
    out: Dict[str, VitalTriple] = {}
    for vital in VITALS:
        spec = specs[vital]
        true_value = draw_vital_true(rng, vital, spec)

        if vital == "bmi" and age_years < 18:
            out[vital] = VitalTriple(true_value, None, NOT_MEASURED)  # B2: not-assessed
            continue

        if rng.bernoulli(f"device_error::{vital}", DEVICE_ERROR_RATE[vital]):
            out[vital] = VitalTriple(true_value, None, DEVICE_ERROR)
            continue

        p_not_measured = AVAILABILITY_RATE[vital][facility_tier]
        if rng.bernoulli(f"not_measured::{vital}", p_not_measured):
            out[vital] = VitalTriple(true_value, None, NOT_MEASURED)
            continue

        observed = rng.normal(f"noise::{vital}", true_value, NOISE_SD[vital])
        lo, hi = PLAUSIBILITY_RANGES[vital][age_band]
        observed = max(lo, min(hi, observed))
        provenance = MANUAL_ENTERED if rng.bernoulli(f"manual::{vital}", MANUAL_SHARE[vital]) else DEVICE_MEASURED
        out[vital] = VitalTriple(true_value, observed, provenance)
    return out
