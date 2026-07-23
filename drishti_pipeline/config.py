"""
drishti_pipeline/config.py
==========================
Central configuration for the DRISHTI foundational synthetic vitals pipeline.
All thresholds, formulas, and ICD-10 mapping tables are defined here.

DO NOT modify inline — this file is the single source of clinical truth for
the pipeline. Any threshold change requires updating the README + metadata.json
to maintain ISO 14971 / SaMD traceability.
"""

import hashlib
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent   # e:\dataset make
SYNTHEA_ROOT   = WORKSPACE_ROOT / "synthea"
SYNTHEA_INT_ROOT = WORKSPACE_ROOT / "synthea-international"

INDIA_BIOMETRICS_SRC = SYNTHEA_INT_ROOT / "in" / "src" / "main" / "resources" / "biometrics.yml"
SYNTHEA_BIOMETRICS   = SYNTHEA_ROOT / "src" / "main" / "resources" / "biometrics.yml"
SYNTHEA_BIOMETRICS_BACKUP = SYNTHEA_ROOT / "src" / "main" / "resources" / "biometrics_original.yml"

SYNTHEA_RUN_PROPS    = WORKSPACE_ROOT / "synthea_india_run.properties"
SYNTHEA_OUTPUT_DIR   = WORKSPACE_ROOT / "output_india" / "csv"

PIPELINE_SCRATCH_DIR = WORKSPACE_ROOT / "drishti_pipeline" / "scratch"
DATASET_OUTPUT_DIR   = WORKSPACE_ROOT / "drishti_dataset"

# ---------------------------------------------------------------------------
# Age range (locked: Rev 5)
# ---------------------------------------------------------------------------
MIN_AGE = 5
MAX_AGE = 80

# ---------------------------------------------------------------------------
# Tier targets (Rev 6: global ratios, not per-pass quotas)
# Applied ONCE across the full accumulated+reweighted pool by
# step3.run_global(), not per Synthea seed pass. Superseded the old
# TIER1_COUNT/TIER2_COUNT/TIER3_COUNT per-pass quotas, which accumulated
# inconsistently across ~40+ passes and left Tier 4 at 0.27% of the dataset.
# Tier now spans 1-6 since glucose_high adds a 6th abnormal-param axis.
# ---------------------------------------------------------------------------
GLOBAL_TIER_TARGET_RATIOS = {
    1: 0.35,   # exactly 1 abnormal param
    2: 0.30,   # exactly 2
    3: 0.18,   # exactly 3
    4: 0.10,   # exactly 4 -- soft cap; natural pool is far smaller (~0.05%), so
               #              build_tiers() takes ALL available rows here, not this ratio
    5: 0.05,   # exactly 5 -- soft cap; realistically ~0 rows naturally occur, see below
    6: 0.02,   # exactly 6 (all of bp_systolic, bp_diastolic, pulse_high|low, bmi, spo2,
               # glucose_high) -- soft cap; realistically ~0 rows naturally occur
}
# NOTE: these are upper-bound targets, not guarantees. build_tiers() takes
# min(available, target) per tier, so tiers 4-6 will silently fall short of
# their ratio and just contribute whatever naturally exists -- by design,
# see the Tier 5/6 rarity note below. Do not "fix" a low realized tier 4-6
# share by inflating GLOBAL_TIER_TARGET_RATIOS; the natural pool is the
# limiting factor, not the target.
MIN_GLUCOSE_HIGH_FLOOR = 500  # absolute row-count floor for glucose_high-containing rows

# Tier 5/6 (5-6 simultaneous abnormal vitals) are NOT gated behind a floor.
# Measured on a real 450,998-row accumulated pool during Rev 6 development:
# 1-param=264062, 2-param=27510 (~9.6x rarer), 3-param=5168 (~5.3x rarer),
# 4-param=248 (~20.8x rarer), 5-param=0, 6-param=0. The decay is steep enough
# that a meaningful Tier 5/6 floor (the original design assumed ~800 combined)
# would require tens of millions of accumulated rows -- hours of additional
# Synthea generation chasing a combinatorially-rare-to-nonexistent population
# state. This is also the clinically correct behavior to accept, not a bug to
# work around: patients with 5-6 simultaneously deranged vitals at once are
# genuinely rare, and fabricating artificial abundance of them would work
# against the "realistic, not overfit" goal of this dataset. Take whatever
# Tier 5/6 rows naturally occur (possibly zero) -- see GLOBAL_TIER_TARGET_RATIOS,
# which already degrade gracefully to "all available" when a tier is
# under-supplied relative to its target ratio.

# ---------------------------------------------------------------------------
# Demographic reweighting targets (Rev 6)
# Synthea's default demographic generator is US-pattern; no India
# demographics/geography module exists in synthea-international/in (only
# biometrics.yml, which recalibrates vital/lab ranges, not age/sex draws).
# These are approximate Census 2011 broad age-band population shares,
# renormalized to this pipeline's 5-80 age window. Precision is not required
# for a synthetic/bootstrap dataset -- this is a documented approximation.
# ---------------------------------------------------------------------------
TARGET_AGE_SEX_DISTRIBUTION = {
    (5, 14):  0.19,
    (15, 24): 0.19,
    (25, 34): 0.17,
    (35, 44): 0.14,
    (45, 54): 0.11,
    (55, 64): 0.08,
    (65, 74): 0.07,
    (75, 80): 0.05,
}
TARGET_SEX_SHARE = {"M": 0.515, "F": 0.485}   # Census 2011 sex ratio ~940F:1000M
RAW_POOL_MULTIPLIER = 4   # accumulate ~4x target_rows of raw vitals before reweighting

# ---------------------------------------------------------------------------
# Pediatric BMI strategy (locked: B2)
# B2 = bmi marked not_assessed for age < 18; no IAP table lookup this pass
# ---------------------------------------------------------------------------
PEDIATRIC_BMI_STRATEGY = "B2"

# ---------------------------------------------------------------------------
# LOINC codes for vital sign extraction
# ---------------------------------------------------------------------------
VITAL_LOINCS = {
    "8867-4":  "pulse",        # Heart rate (bpm)
    "59408-5": "spo2",         # Oxygen saturation (%)
    "2708-6":  "spo2",         # Oxygen saturation in Arterial blood (Synthea default)
    "8480-6":  "bp_systolic",  # BP systolic (mmHg)
    "8462-4":  "bp_diastolic", # BP diastolic (mmHg)
    "39156-5": "bmi",          # BMI (kg/m²)
    "2339-0":  "glucose",      # Glucose [Mass/volume] in Blood, random/non-fasting (mg/dL)
}

# ---------------------------------------------------------------------------
# Adult thresholds — IHCI / ICMR-INDIAB / WHO Asian cutoffs
# Source: ihci.in (IHCI 2019), ICMR-INDIAB, WHO Asian BMI 2004
# NOTE: AHA 2017 ≥130 cutoff is explicitly NOT used. IHCI ≥140 is the source.
# ---------------------------------------------------------------------------
ADULT_THRESHOLDS = {
    "bp_systolic": {
        "normal_max":    129,   # IHCI: <130 normal
        "elevated_max":  139,   # IHCI: 130-139 elevated
        "stage1_min":    140,   # IHCI Stage 1 HTN
        "stage2_min":    160,   # IHCI Stage 2 HTN
    },
    "bp_diastolic": {
        "normal_max":    84,    # IHCI: <85 normal
        "stage1_min":    90,    # IHCI Stage 1 HTN
        "stage2_min":    100,   # IHCI Stage 2 HTN
    },
    "spo2": {
        "normal_min":    95.0,  # SpO2 ≥95% = normal
        "abnormal_max":  94.9,  # <95% = hypoxemia flag
    },
    "bmi": {
        "normal_max":    22.9,  # WHO Asian: <23 normal
        "overweight_min": 23.0, # WHO Asian: ≥23 overweight
        "obese_min":     25.0,  # WHO Asian: ≥25 obese (note: not 30)
    },
    "pulse": {
        "brady_max":    59,     # <60 = bradycardia
        "normal_min":   60,
        "normal_max":   100,
        "tachy_min":    101,    # >100 = tachycardia
    },
    "glucose": {
        "normal_max":      139,  # <140 mg/dL random/non-fasting = normal
        "prediabetes_min": 140,  # 140-199 mg/dL = abnormal, needs confirmation
                                  # (RSSDI / ICMR-INDIAB random-glucose screening
                                  # criterion -- distinct from the FASTING cutoffs
                                  # (100/126) already used to calibrate biometrics.yml)
        "diabetes_min":    200,  # >=200 mg/dL + symptoms = diabetes mellitus
                                  # (WHO/ADA criterion, adopted in ICMR-INDIAB
                                  # opportunistic screening). Applied uniformly
                                  # age 5-80, no age-gating (unlike BP).
    },
}

# ---------------------------------------------------------------------------
# Pediatric BP thresholds — Narang et al., AIIMS, Indian Pediatrics
# Formula: SBP 95th pct = 110 + 1.6×age (+1 for female)
#          DBP 95th pct =  79 + 0.7×age (+1 for female)
# Staging (IAP/AAP-aligned, Indian rural-BP study):
#   Stage 1: 95th pct to 95th+12 mmHg  (or 130/80-139/89 for age ≥13)
#   Stage 2: above Stage 1 upper        (or ≥140/90 for age ≥13)
# Anchor values: ~120/80 at age 5, ~125/85 at age 10, ~135/90 at age 15
# ---------------------------------------------------------------------------

def sbp_95th_pediatric(age: int, sex: str) -> float:
    """
    SBP hypertension threshold (95th percentile) for age < 18.
    sex: 'M' (male) or 'F' (female).
    Source: Narang et al., Indian Pediatrics.
    """
    return 110.0 + 1.6 * age + (1.0 if sex.upper() == "F" else 0.0)


def dbp_95th_pediatric(age: int, sex: str) -> float:
    """
    DBP hypertension threshold (95th percentile) for age < 18.
    sex: 'M' (male) or 'F' (female).
    Source: Narang et al., Indian Pediatrics.
    """
    return 79.0 + 0.7 * age + (1.0 if sex.upper() == "F" else 0.0)


def get_bp_threshold(age: int, sex: str) -> dict:
    """
    Age-gated BP threshold dispatcher.
    Returns {'sbp': float, 'dbp': float} — minimum values for hypertension flag.
    Adults (age >= 18): IHCI flat values.
    Pediatric (5 <= age < 18): Narang formula.
    """
    if age >= 18:
        return {
            "sbp": float(ADULT_THRESHOLDS["bp_systolic"]["stage1_min"]),
            "dbp": float(ADULT_THRESHOLDS["bp_diastolic"]["stage1_min"]),
        }
    else:
        return {
            "sbp": sbp_95th_pediatric(age, sex),
            "dbp": dbp_95th_pediatric(age, sex),
        }


# ---------------------------------------------------------------------------
# Synthetic epidemiological signal: fever_pattern (Rev 6)
#
# This is NOT a measured vital. A 6-vital system (BP x2, pulse, SpO2, BMI,
# glucose) has no temperature/CBC/serology channel to carry infectious-disease
# signal, so malaria/dengue/typhoid/chikungunya/UTI/gastroenteritis/TB/LRTI
# would otherwise be permanently locked inside differential_candidates text
# and never realize as a primary icd_candidate. fever_pattern is a
# deterministic, hash-based routing flag standing in for "this encounter
# presents with a fever/infectious pattern" -- it does NOT count toward tier
# or _param_count (tier measures physiological derangement severity, not
# epidemiological routing).
# ---------------------------------------------------------------------------
FEVER_PATTERN_BASE_RATE    = 0.08   # ~8% of all encounters, year-round
FEVER_PATTERN_MONSOON_RATE = 0.22   # ~22% Jun-Sep (India vector-borne + water-borne season)


def _stable_unit_interval(patient_id: str, encounter_date: str, salt: str) -> float:
    """
    Deterministic pseudo-random float in [0,1) from a stable hash of
    (patient_id, encounter_date, salt). Same row -> same value every time
    this is called, whether from step3 or step4, in any pass order. This is
    what lets step3 (labeling) and step4 (symptom/drug sampling) independently
    re-resolve the SAME condition for a given row without passing python
    objects through the scratch CSV files.
    """
    h = hashlib.sha256(f"{patient_id}|{encounter_date}|{salt}".encode()).hexdigest()
    return int(h[:12], 16) / float(16 ** 12)


def is_monsoon(encounter_date: str) -> bool:
    try:
        month = int(str(encounter_date)[5:7])
        return 6 <= month <= 9
    except (ValueError, IndexError):
        return False


def assess_fever_pattern(patient_id: str, encounter_date: str) -> bool:
    rate = FEVER_PATTERN_MONSOON_RATE if is_monsoon(encounter_date) else FEVER_PATTERN_BASE_RATE
    return _stable_unit_interval(patient_id, encounter_date, "fever_pattern") < rate


# ---------------------------------------------------------------------------
# Noise injection parameters (applied in step6, AFTER tiering/labeling)
# σ and clip_range are per-vital. Labels are based on pre-noise values.
# These SDs approximate typical manual-cuff/pulse-oximeter/scale measurement 
# error at PHC level — flag as a placeholder pending a real India-specific 
# device-accuracy source if one is found later.
# ---------------------------------------------------------------------------
NOISE_PARAMS = {
    "bp_systolic":  {"sigma": 4.0, "clip": 15.0, "floor": 60.0},
    "bp_diastolic": {"sigma": 3.0, "clip": 15.0, "floor": 30.0},
    "pulse":        {"sigma": 3.0, "clip": 15.0, "floor": 30.0},
    "bmi":          {"sigma": 0.5, "clip": 2.0, "floor": 10.0},
    "spo2":         {"sigma": 1.0, "clip": 5.0, "floor": 70.0, "ceil": 100.0},
    "glucose":      {"sigma": 10.0, "clip": 30.0, "floor": 40.0},
    # Glucometer/point-of-care measurement error ~10-15% or ~10-15 mg/dL per
    # ISO 15197 accuracy band at typical PHC device accuracy. sigma=10 mg/dL
    # is the conservative end of that band; clip=~3x sigma (consistent with
    # the ratio used for bp/bmi/spo2 above); floor=40 mg/dL (severe-
    # hypoglycemia clinical floor -- a "noised" reading below this is not
    # physiologically meaningful to report as observed). No ceiling --
    # meters commonly read to 500-600 mg/dL, no need to cap.
}

# ---------------------------------------------------------------------------
# Canonical output schema — column order and types
# symptom_signal_strength: strong / supportive / nonspecific
# icd_candidate: nullable — None means LLM/retrieval layer handles this row
# ---------------------------------------------------------------------------
CANONICAL_COLUMNS = [
    "patient_id",
    "encounter_date",
    "age_at_encounter",
    "sex",
    "bp_systolic",
    "bp_diastolic",
    "pulse",
    "spo2",
    "bmi",
    "glucose",
    "bp_systolic_observed",
    "bp_diastolic_observed",
    "pulse_observed",
    "spo2_observed",
    "bmi_observed",
    "glucose_observed",
    "tier",
    "abnormal_params",
    "fever_pattern_flag",
    "symptom_string",
    "symptom_signal_strength",
    "drug_name",
    "drug_dosage",
    "icd_chapter",
    "icd_block",
    "icd_candidate",
    "differential_candidates",
    "pediatric_referral_flag",
    "synthetic",
    "source",
]

CANONICAL_DTYPES = {
    "patient_id":            "string",
    "encounter_date":        "string",
    "age_at_encounter":      "int32",
    "sex":                   "string",
    "bp_systolic":           "float32",
    "bp_diastolic":          "float32",
    "pulse":                 "float32",
    "spo2":                  "float32",
    "bmi":                   "float32",
    "glucose":               "float32",  # nullable -- sparse, opportunistic lab like bmi
    "bp_systolic_observed":  "float32",
    "bp_diastolic_observed": "float32",
    "pulse_observed":        "float32",
    "spo2_observed":         "float32",
    "bmi_observed":          "float32",
    "glucose_observed":      "float32",
    "tier":                  "int8",
    "abnormal_params":       "string",
    "fever_pattern_flag":    "boolean",  # synthetic epidemiological signal, not a measured vital
    "symptom_string":        "string",
    "symptom_signal_strength": "string",
    "drug_name":             "string",
    "drug_dosage":           "string",
    "icd_chapter":           "string",
    "icd_block":             "string",
    "icd_candidate":         "string",   # nullable — None/NaN for rows below block precision
    "differential_candidates": "string",
    "pediatric_referral_flag": "boolean",
    "synthetic":             "boolean",
    "source":                "string",
}

VALID_SIGNAL_STRENGTHS = {"strong", "supportive", "nonspecific"}

# ---------------------------------------------------------------------------
# ICD-10 + Symptom Mapping Table
# Keyed by frozenset of abnormal_param names.
# Each entry:
#   icd_chapter       : ICD-10 chapter name (str, always populated)
#   icd_block         : ICD-10 block range  (str, always populated)
#   icd_candidate     : specific ICD-10 code (str or None)
#   differential_candidates : list of str (ranked, 2-4, block granularity)
#   symptom_pool      : list of (symptom_text, signal_strength) tuples
#
# IMPORTANT: Pulse direction matters.
#   "pulse_high" = tachycardia (HR > 100 bpm)
#   "pulse_low"  = bradycardia (HR < 60 bpm)
#
# Table is ordered: more-specific (larger frozensets) first.
# Lookup in step3/4: try exact match → fall back to best partial match.
# Unmapped combinations → FALLBACK_ENTRY below.
# ---------------------------------------------------------------------------

ICD_MAPPING = [
    # ---- 4-param combos (most specific first) ----
    {
        "params": frozenset({"bp_systolic", "bp_diastolic", "bmi", "pulse_high"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": None,
        "differential_candidates": ["metabolic_syndrome_advanced", "hypertensive_crisis"],
        "symptom_pool": [
            ("multi-system distress", "strong"),
            ("chest tightness", "strong"),
            ("breathlessness", "strong"),
        ],
        "prescription_pool": [("Amlodipine + Telmisartan", "10mg + 80mg"), ("Metoprolol + Amlodipine", "100mg + 10mg")],
    },
    # ---- 3-param combos ----
    {
        "params": frozenset({"bp_systolic", "bp_diastolic", "spo2"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": None,
        "differential_candidates": ["hypertensive_emergency_with_hypoxia", "acute_LVF"],
        "symptom_pool": [
            ("chest tightness", "strong"),
            ("breathlessness", "strong"),
            ("confusion", "supportive"),
            ("altered sensorium", "strong"),
        ],
        "prescription_pool": [("Furosemide", "40mg"), ("Nitroglycerin", "0.4mg")],
    },
    {
        "params": frozenset({"bp_systolic", "bp_diastolic", "bmi"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": None,
        "differential_candidates": ["obesity_related_htn", "metabolic_syndrome"],
        "symptom_pool": [
            ("severe headache", "strong"),
            ("fatigue", "nonspecific"),
            ("exertional dyspnoea", "supportive"),
            ("knee pain", "supportive"),
        ],
        "prescription_pool": [("Telmisartan", "40mg"), ("Amlodipine", "5mg"), ("Metformin", "500mg")],
    },
    {
        "params": frozenset({"bp_systolic", "spo2", "pulse_high"}),
        "icd_chapter": "Respiratory",
        "icd_block": "J96-J99",
        "icd_candidate": None,
        "differential_candidates": ["respiratory_failure", "severe_pneumonia", "sepsis_with_hypertension"],
        "symptom_pool": [
            ("breathlessness", "strong"),
            ("palpitations", "supportive"),
            ("dizziness", "supportive"),
            ("confusion", "supportive"),
        ],
        "prescription_pool": [("Oxygen + Salbutamol", "2L/min + 100mcg"), ("Oxygen + Amlodipine", "2L/min + 5mg")],
    },
    {
        "params": frozenset({"spo2", "pulse_high", "bmi"}),
        "icd_chapter": "Respiratory",
        "icd_block": "J96-J99",
        "icd_candidate": None,
        "differential_candidates": ["sleep_apnoea_with_hypoxia", "obesity_hypoventilation"],
        "symptom_pool": [
            ("breathlessness", "strong"),
            ("snoring", "supportive"),
            ("morning headache", "supportive"),
            ("fatigue", "nonspecific"),
        ],
        "prescription_pool": [("Oxygen", "2L/min"), ("CPAP", "Nightly"), ("Metformin", "500mg")],
    },
    # ---- 2-param combos ----
    {
        "params": frozenset({"bp_systolic", "bp_diastolic"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": "I10",
        "differential_candidates": ["essential_hypertension_stage2", "hypertensive_urgency"],
        "symptom_pool": [
            ("severe headache", "strong"),
            ("neck stiffness", "supportive"),
            ("dizziness", "supportive"),
        ],
        "prescription_pool": [("Amlodipine + Telmisartan", "10mg + 80mg"), ("Losartan", "100mg")],
    },
    {
        "params": frozenset({"bp_systolic", "spo2"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I50-I52",
        "icd_candidate": None,
        "differential_candidates": ["hypertensive_heart_failure", "acute_pulmonary_oedema"],
        "symptom_pool": [
            ("severe breathlessness", "strong"),
            ("dizziness", "supportive"),
            ("chest tightness", "strong"),
        ],
        "prescription_pool": [("Furosemide", "40mg"), ("Oxygen", "2L/min")],
    },
    {
        "params": frozenset({"bp_systolic", "bmi"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": None,
        "differential_candidates": ["obesity_related_htn", "metabolic_syndrome"],
        "symptom_pool": [
            ("headache", "supportive"),
            ("fatigue", "nonspecific"),
            ("knee pain", "supportive"),
            ("exertional dyspnoea", "supportive"),
        ],
        "prescription_pool": [("Amlodipine", "5mg"), ("Metformin", "500mg")],
    },
    {
        "params": frozenset({"bp_systolic", "pulse_high"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": None,
        "differential_candidates": ["hypertensive_emergency", "anxiety_induced_htn"],
        "symptom_pool": [
            ("severe headache", "strong"),
            ("palpitations", "strong"),
            ("chest tightness", "supportive"),
        ],
        "prescription_pool": [("Metoprolol", "50mg"), ("Atenolol", "25mg")],
    },
    {
        "params": frozenset({"bp_diastolic", "spo2"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I50-I52",
        "icd_candidate": None,
        "differential_candidates": ["diastolic_heart_failure", "hypertensive_heart_failure"],
        "symptom_pool": [
            ("breathlessness", "strong"),
            ("chest discomfort", "supportive"),
            ("fatigue", "nonspecific"),
        ],
        "prescription_pool": [("Furosemide", "20mg"), ("Oxygen", "2L/min")],
    },
    {
        "params": frozenset({"bp_diastolic", "bmi"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": None,
        "differential_candidates": ["obesity_related_diastolic_htn", "metabolic_syndrome"],
        "symptom_pool": [
            ("headache", "supportive"),
            ("fatigue", "nonspecific"),
            ("exertional dyspnoea", "supportive"),
        ],
        "prescription_pool": [("Telmisartan", "40mg"), ("Atorvastatin", "10mg")],
    },
    {
        "params": frozenset({"spo2", "pulse_high"}),
        "icd_chapter": "Respiratory",
        "icd_block": "J96-J99",
        "icd_candidate": None,
        "differential_candidates": ["pneumonia", "dengue_fever", "malaria", "typhoid", "chikungunya", "lower_respiratory_tract_infection"],
        "symptom_pool": [
            ("breathlessness", "strong"),
            ("palpitations", "supportive"),
            ("high fever", "strong"),
            ("confusion", "supportive"),
        ],
        "prescription_pool": [("Oxygen", "2L/min"), ("Paracetamol", "650mg"), ("Salbutamol", "100mcg")],
    },
    {
        "params": frozenset({"spo2", "bmi"}),
        "icd_chapter": "Respiratory",
        "icd_block": "J96-J99",
        "icd_candidate": None,
        "differential_candidates": ["obesity_hypoventilation", "sleep_apnoea"],
        "symptom_pool": [
            ("breathlessness", "strong"),
            ("snoring", "supportive"),
            ("morning headache", "supportive"),
        ],
        "prescription_pool": [("Oxygen", "2L/min"), ("CPAP", "Nightly")],
    },
    {
        "params": frozenset({"bmi", "pulse_high"}),
        "icd_chapter": "Nutritional/metabolic",
        "icd_block": "E65-E68",
        "icd_candidate": None,
        "differential_candidates": ["metabolic_syndrome", "sleep_apnoea"],
        "symptom_pool": [
            ("fatigue", "nonspecific"),
            ("snoring", "supportive"),
            ("morning headache", "supportive"),
        ],
        "prescription_pool": [("Metformin", "500mg"), ("Metoprolol", "25mg")],
    },
    {
        "params": frozenset({"pulse_high", "pulse_low"}),
        # can't actually co-occur; fallback entry for safety
        "icd_chapter": "Circulatory system",
        "icd_block": "I44-I49",
        "icd_candidate": None,
        "differential_candidates": ["arrhythmia_NOS"],
        "symptom_pool": [
            ("palpitations", "strong"),
            ("dizziness", "supportive"),
        ],
        "prescription_pool": [("Amiodarone", "200mg"), ("None", "None")],
    },
    # ---- 1-param combos ----
    {
        # Multi-candidate (Rev 6): stage-1 HTN is dominant but not the only
        # thing an isolated systolic reading can mean at this signal
        # resolution -- migraine and white-coat HTN are clinically plausible
        # siblings with no distinguishable vital fingerprint of their own.
        "params": frozenset({"bp_systolic"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "candidates": [
            {
                "weight": 0.70, "condition_tag": "essential_hypertension_stage1", "icd_candidate": "I10",
                "symptom_pool": [
                    ("headache", "supportive"),
                    ("dizziness", "supportive"),
                    ("blurred vision", "supportive"),
                    ("epistaxis", "supportive"),
                    ("no symptoms", "nonspecific"),
                ],
                "prescription_pool": [("Amlodipine", "5mg"), ("Telmisartan", "40mg"), ("Losartan", "50mg")],
            },
            {
                "weight": 0.15, "condition_tag": "white_coat_htn", "icd_candidate": None,
                "symptom_pool": [
                    ("no symptoms", "nonspecific"),
                    ("mild anxiety", "nonspecific"),
                ],
                "prescription_pool": [("Lifestyle Modification", "Diet/Exercise")],
            },
            {
                "weight": 0.15, "condition_tag": "migraine",
                "icd_chapter": "Diseases of the nervous system", "icd_block": "G43", "icd_candidate": "G43.9",
                "symptom_pool": [
                    ("unilateral throbbing headache", "strong"),
                    ("photophobia", "strong"),
                    ("nausea", "supportive"),
                    ("visual aura", "supportive"),
                ],
                "prescription_pool": [("Rizatriptan", "10mg"), ("Paracetamol", "650mg")],
            },
        ],
    },
    {
        "params": frozenset({"bp_diastolic"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I10-I15",
        "icd_candidate": None,
        "differential_candidates": ["essential_hypertension", "isolated_diastolic_htn"],
        "symptom_pool": [
            ("headache", "supportive"),
            ("fatigue", "nonspecific"),
            ("chest discomfort", "supportive"),
            ("no symptoms", "nonspecific"),
        ],
        "prescription_pool": [("Telmisartan", "40mg"), ("Losartan", "50mg")],
    },
    {
        "params": frozenset({"spo2"}),
        "icd_chapter": "Respiratory",
        "icd_block": "J96-J99",
        "icd_candidate": None,
        "differential_candidates": ["hypoxia_NOS", "upper_respiratory_tract_infection", "pneumonia"],
        "symptom_pool": [
            ("breathlessness", "strong"),
            ("cyanosis", "strong"),
            ("confusion", "supportive"),
            ("fatigue", "nonspecific"),
        ],
        "prescription_pool": [("Oxygen", "2L/min"), ("Salbutamol", "100mcg")],
    },
    {
        # Multi-candidate (Rev 6): osteoarthritis added as a sibling of
        # obesity for an isolated raised-BMI reading.
        "params": frozenset({"bmi"}),
        "icd_chapter": "Nutritional/metabolic",
        "icd_block": "E65-E68",
        "candidates": [
            {
                "weight": 0.65, "condition_tag": "obesity", "icd_candidate": "E66",
                "symptom_pool": [
                    ("fatigue", "nonspecific"),
                    ("joint pain", "supportive"),
                    ("exertional dyspnoea", "supportive"),
                    ("no symptoms", "nonspecific"),
                ],
                "prescription_pool": [("Metformin", "500mg"), ("Atorvastatin", "10mg"), ("Lifestyle Modification", "Diet/Exercise")],
            },
            {
                "weight": 0.35, "condition_tag": "osteoarthritis",
                "icd_chapter": "Diseases of the musculoskeletal system", "icd_block": "M15-M19", "icd_candidate": "M17",
                "symptom_pool": [
                    ("knee pain on weight-bearing", "strong"),
                    ("morning stiffness under 30 minutes", "supportive"),
                    ("joint swelling", "supportive"),
                    ("reduced mobility", "supportive"),
                ],
                "prescription_pool": [("Paracetamol", "650mg"), ("Diclofenac Gel", "Topical"), ("Physiotherapy Referral", "N/A")],
            },
        ],
    },
    {
        # Multi-candidate (Rev 6): vector-borne fevers were previously stuck
        # inside differential_candidates text, gated behind a monsoon-season
        # RNG promotion in step3 that never actually fired. Moved to the
        # fever_pattern-anchored entries below; this key now covers the
        # non-infectious tachycardia differentials.
        "params": frozenset({"pulse_high"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I47-I49",
        "candidates": [
            {
                "weight": 0.45, "condition_tag": "sinus_tachycardia", "icd_candidate": None,
                "symptom_pool": [
                    ("palpitations", "strong"),
                    ("fatigue", "nonspecific"),
                    ("no symptoms", "nonspecific"),
                ],
                "prescription_pool": [("Propranolol", "10mg"), ("Metoprolol", "25mg")],
            },
            {
                "weight": 0.20, "condition_tag": "anxiety_panic_disorder",
                "icd_chapter": "Mental and behavioural disorders", "icd_block": "F40-F48", "icd_candidate": "F41.0",
                "symptom_pool": [
                    ("palpitations", "strong"),
                    ("sense of impending doom", "strong"),
                    ("sweating", "supportive"),
                    ("chest tightness", "supportive"),
                ],
                "prescription_pool": [("Escitalopram", "5mg"), ("Propranolol", "10mg"), ("Counselling Referral", "N/A")],
            },
            {
                "weight": 0.20, "condition_tag": "anemia",
                "icd_chapter": "Diseases of the blood", "icd_block": "D50-D53", "icd_candidate": "D50",
                "symptom_pool": [
                    ("fatigue", "strong"),
                    ("pallor", "strong"),
                    ("breathlessness on exertion", "supportive"),
                    ("dizziness", "supportive"),
                ],
                "prescription_pool": [("Ferrous Sulphate + Folic Acid", "200mg + 5mg"), ("Iron Sucrose IV", "200mg")],
            },
            {
                "weight": 0.15, "condition_tag": "hyperthyroidism",
                "icd_chapter": "Endocrine/metabolic", "icd_block": "E05", "icd_candidate": "E05.9",
                "symptom_pool": [
                    ("heat intolerance", "strong"),
                    ("palpitations", "strong"),
                    ("unexplained weight loss", "supportive"),
                    ("tremors", "supportive"),
                ],
                "prescription_pool": [("Carbimazole", "10mg"), ("Propranolol", "20mg")],
            },
        ],
    },
    {
        "params": frozenset({"pulse_low"}),
        "icd_chapter": "Circulatory system",
        "icd_block": "I44-I45",
        "icd_candidate": None,
        "differential_candidates": ["sinus_bradycardia", "hypothyroidism"],
        "symptom_pool": [
            ("dizziness", "supportive"),
            ("syncope", "strong"),
            ("fatigue", "nonspecific"),
            ("cold extremities", "supportive"),
        ],
        "prescription_pool": [("Atropine", "0.5mg"), ("None", "None")],
    },
    # ---- New (Rev 6): hypothyroidism with a real vital fingerprint ----
    {
        "params": frozenset({"pulse_low", "bmi"}),
        "icd_chapter": "Endocrine/metabolic",
        "icd_block": "E00-E03",
        "icd_candidate": "E03.9",
        "differential_candidates": ["hypothyroidism", "sinus_bradycardia", "obesity_with_bradycardia"],
        "symptom_pool": [
            ("cold intolerance", "strong"),
            ("weight gain", "supportive"),
            ("fatigue", "nonspecific"),
            ("constipation", "supportive"),
            ("dry skin", "supportive"),
        ],
        "prescription_pool": [("Levothyroxine", "50mcg"), ("Levothyroxine", "100mcg")],
    },
    # ---- New (Rev 6): glucose-based entries ----
    {
        "params": frozenset({"glucose_high"}),
        "icd_chapter": "Endocrine/metabolic",
        "icd_block": "E10-E14",
        "icd_candidate": "E11",
        "differential_candidates": ["type_2_diabetes_mellitus", "impaired_glucose_tolerance", "stress_hyperglycemia"],
        "symptom_pool": [
            ("excessive thirst", "strong"),
            ("frequent urination", "strong"),
            ("unexplained weight loss", "supportive"),
            ("fatigue", "nonspecific"),
            ("blurred vision", "supportive"),
            ("no symptoms", "nonspecific"),
        ],
        "prescription_pool": [("Metformin", "500mg"), ("Metformin", "1000mg"), ("Glimepiride + Metformin", "1mg + 500mg")],
    },
    {
        "params": frozenset({"glucose_high", "bmi"}),
        "icd_chapter": "Endocrine/metabolic",
        "icd_block": "E70-E88",
        "icd_candidate": None,
        "differential_candidates": ["metabolic_syndrome", "type_2_diabetes_mellitus", "obesity_with_dysglycemia"],
        "symptom_pool": [
            ("fatigue", "nonspecific"),
            ("excessive thirst", "strong"),
            ("joint pain", "supportive"),
            ("exertional dyspnoea", "supportive"),
        ],
        "prescription_pool": [("Metformin", "500mg"), ("Metformin", "1000mg"), ("Lifestyle Modification", "Diet/Exercise")],
    },
    {
        "params": frozenset({"glucose_high", "bp_systolic", "bp_diastolic"}),
        "icd_chapter": "Endocrine/metabolic",
        "icd_block": "E10-E14",
        "icd_candidate": "E11",
        "differential_candidates": ["diabetes_with_hypertension", "metabolic_syndrome"],
        "symptom_pool": [
            ("excessive thirst", "strong"),
            ("headache", "supportive"),
            ("fatigue", "nonspecific"),
        ],
        "prescription_pool": [("Metformin + Telmisartan", "500mg + 40mg"), ("Metformin + Amlodipine", "500mg + 5mg")],
    },
    # ---- New (Rev 6): fever_pattern-anchored infectious/PHC-burden entries ----
    # fever_pattern is a synthetic epidemiological routing signal (see
    # assess_fever_pattern() above), not a measured vital. These entries are
    # what let malaria/dengue/typhoid/chikungunya/TB/UTI/gastroenteritis
    # actually realize as primary icd_candidates instead of being permanently
    # locked inside differential_candidates text.
    {
        "params": frozenset({"fever_pattern"}),
        "icd_chapter": "Certain infectious and parasitic diseases",
        "icd_block": "A00-B99",
        "candidates": [
            {
                "weight": 0.30, "condition_tag": "nonspecific_viral_fever", "icd_candidate": None,
                "symptom_pool": [
                    ("mild fever", "supportive"),
                    ("body ache", "supportive"),
                    ("fatigue", "nonspecific"),
                ],
                "prescription_pool": [("Paracetamol", "650mg")],
            },
            {
                "weight": 0.25, "condition_tag": "urinary_tract_infection",
                "icd_chapter": "Diseases of the genitourinary system", "icd_block": "N30-N39", "icd_candidate": "N39.0",
                "symptom_pool": [
                    ("burning micturition", "strong"),
                    ("increased urinary frequency", "strong"),
                    ("lower abdominal pain", "supportive"),
                    ("fever", "supportive"),
                    ("no symptoms", "nonspecific"),
                ],
                "prescription_pool": [("Nitrofurantoin", "100mg"), ("Fosfomycin", "3g single dose")],
            },
            {
                "weight": 0.20, "condition_tag": "acute_gastroenteritis",
                "icd_block": "A00-A09", "icd_candidate": "A09",
                "symptom_pool": [
                    ("loose stools", "strong"),
                    ("vomiting", "strong"),
                    ("abdominal cramps", "supportive"),
                    ("fever", "supportive"),
                ],
                "prescription_pool": [("ORS + Zinc", "1 sachet + 20mg"), ("Ofloxacin + Ornidazole", "200mg + 500mg")],
            },
            {
                "weight": 0.15, "condition_tag": "typhoid", "monsoon_weight": 0.25,
                "icd_block": "A00-A09", "icd_candidate": "A01.0",
                "symptom_pool": [
                    ("stepladder fever", "strong"),
                    ("abdominal pain", "supportive"),
                    ("constipation or diarrhoea", "supportive"),
                    ("rose spots", "supportive"),
                ],
                "prescription_pool": [("Ceftriaxone", "1g IV"), ("Azithromycin", "500mg")],
            },
            {
                "weight": 0.10, "condition_tag": "dengue_fever", "monsoon_weight": 0.20,
                "icd_block": "A90-A99", "icd_candidate": "A90",
                "symptom_pool": [
                    ("high fever", "strong"),
                    ("severe body ache", "strong"),
                    ("retro-orbital pain", "strong"),
                    ("skin rash", "supportive"),
                ],
                # NOTE: avoid NSAIDs in dengue -- symptomatic Paracetamol + fluids only.
                "prescription_pool": [("Paracetamol", "650mg"), ("IV Fluids", "per protocol")],
            },
        ],
    },
    {
        "params": frozenset({"fever_pattern", "pulse_high"}),
        "icd_chapter": "Certain infectious and parasitic diseases",
        "icd_block": "A90-A99",
        "candidates": [
            {
                "weight": 0.30, "condition_tag": "dengue_fever",
                "icd_block": "A90-A99", "icd_candidate": "A90",
                "symptom_pool": [
                    ("high fever", "strong"),
                    ("severe body ache", "strong"),
                    ("retro-orbital pain", "strong"),
                    ("bleeding gums", "strong"),
                ],
                "prescription_pool": [("Paracetamol", "650mg"), ("IV Fluids", "per protocol")],
            },
            {
                "weight": 0.25, "condition_tag": "malaria",
                "icd_block": "B50-B54", "icd_candidate": "B54",
                "symptom_pool": [
                    ("cyclical high fever with chills", "strong"),
                    ("rigors", "strong"),
                    ("body ache", "supportive"),
                    ("vomiting", "supportive"),
                ],
                "prescription_pool": [("Artemether-Lumefantrine", "20mg + 120mg"), ("Chloroquine", "250mg")],
            },
            {
                "weight": 0.20, "condition_tag": "typhoid",
                "icd_block": "A00-A09", "icd_candidate": "A01.0",
                "symptom_pool": [
                    ("stepladder fever", "strong"),
                    ("relative bradycardia", "supportive"),
                    ("abdominal pain", "supportive"),
                ],
                "prescription_pool": [("Ceftriaxone", "1g IV"), ("Azithromycin", "500mg")],
            },
            {
                "weight": 0.10, "condition_tag": "chikungunya",
                "icd_block": "A92", "icd_candidate": "A92.0",
                "symptom_pool": [
                    ("severe joint pain", "strong"),
                    ("high fever", "strong"),
                    ("skin rash", "supportive"),
                ],
                "prescription_pool": [("Paracetamol", "650mg"), ("Physiotherapy", "N/A")],
            },
            {
                "weight": 0.15, "condition_tag": "acute_gastroenteritis_with_dehydration",
                "icd_block": "A00-A09", "icd_candidate": "A09",
                "symptom_pool": [
                    ("loose stools", "strong"),
                    ("dehydration signs", "strong"),
                    ("fever", "supportive"),
                ],
                "prescription_pool": [("ORS + Zinc", "1 sachet + 20mg")],
            },
        ],
    },
    {
        "params": frozenset({"fever_pattern", "spo2"}),
        "icd_chapter": "Respiratory",
        "icd_block": "J20-J22",
        "candidates": [
            {
                "weight": 0.45, "condition_tag": "lower_respiratory_tract_infection",
                "icd_block": "J20-J22", "icd_candidate": "J22",
                "symptom_pool": [
                    ("productive cough", "strong"),
                    ("fever", "supportive"),
                    ("breathlessness", "strong"),
                    ("chest pain on breathing", "supportive"),
                ],
                "prescription_pool": [("Amoxicillin-Clavulanate", "625mg"), ("Azithromycin", "500mg")],
            },
            {
                "weight": 0.30, "condition_tag": "pulmonary_tuberculosis",
                "icd_chapter": "Certain infectious and parasitic diseases", "icd_block": "A15-A19", "icd_candidate": "A15",
                "symptom_pool": [
                    ("chronic cough over 2 weeks", "strong"),
                    ("evening fever", "strong"),
                    ("night sweats", "supportive"),
                    ("weight loss", "supportive"),
                    ("hemoptysis", "strong"),
                ],
                "prescription_pool": [("HRZE (RNTCP Cat-I ATT)", "Weight-band per RNTCP"), ("Referral to DOTS center", "N/A")],
            },
            {
                "weight": 0.25, "condition_tag": "dengue_fever_with_warning_signs",
                "icd_chapter": "Certain infectious and parasitic diseases", "icd_block": "A90-A99", "icd_candidate": "A91",
                "symptom_pool": [
                    ("high fever", "strong"),
                    ("bleeding gums", "strong"),
                    ("breathlessness", "strong"),
                ],
                "prescription_pool": [("IV Fluids", "per protocol"), ("Referral - Inpatient", "N/A")],
            },
        ],
    },
    {
        "params": frozenset({"fever_pattern", "spo2", "pulse_high"}),
        "icd_chapter": "Respiratory",
        "icd_block": "J96-J99",
        "candidates": [
            {
                "weight": 0.50, "condition_tag": "severe_pneumonia_with_sepsis", "icd_candidate": None,
                "symptom_pool": [
                    ("severe breathlessness", "strong"),
                    ("confusion", "strong"),
                    ("high fever", "strong"),
                ],
                "prescription_pool": [("Oxygen", "2L/min"), ("Ceftriaxone", "1g IV"), ("Referral - Emergency", "N/A")],
            },
            {
                "weight": 0.30, "condition_tag": "dengue_hemorrhagic_fever",
                "icd_chapter": "Certain infectious and parasitic diseases", "icd_block": "A90-A99", "icd_candidate": "A91",
                "symptom_pool": [
                    ("bleeding gums", "strong"),
                    ("severe breathlessness", "strong"),
                    ("high fever", "strong"),
                ],
                "prescription_pool": [("IV Fluids", "per protocol"), ("Referral - Emergency", "N/A")],
            },
            {
                "weight": 0.20, "condition_tag": "severe_malaria",
                "icd_chapter": "Certain infectious and parasitic diseases", "icd_block": "B50-B54", "icd_candidate": "B50",
                "symptom_pool": [
                    ("cyclical high fever with chills", "strong"),
                    ("confusion", "supportive"),
                ],
                "prescription_pool": [("IV Artesunate", "2.4mg/kg"), ("Referral - Emergency", "N/A")],
            },
        ],
    },
]

# Fallback for combinations not explicitly in the table above.
# Routes to general/observation category — correct by design (LLM layer handles these).
FALLBACK_ENTRY = {
    "icd_chapter": "General/nonspecific",
    "icd_block": "Z00-Z13",
    "icd_candidate": None,
    "differential_candidates": ["observation_NOS"],
    "symptom_pool": [
        ("no specific symptom", "nonspecific"),
    ],
}


def lookup_icd_entry(abnormal_params_set: frozenset) -> dict:
    """
    Look up the ICD mapping entry for a given set of abnormal params.
    Strategy:
      1. Exact match on frozenset
      2. Best partial match (largest subset of the params that has a mapping)
      3. FALLBACK_ENTRY
    Returns a copy of the matching entry dict.
    """
    if not abnormal_params_set:
        return FALLBACK_ENTRY.copy()

    # 1. Exact match
    for entry in ICD_MAPPING:
        if entry["params"] == abnormal_params_set:
            return entry.copy()

    # 2. Best partial match — largest entry["params"] that is a subset of abnormal_params_set
    best = None
    best_size = 0
    for entry in ICD_MAPPING:
        if entry["params"].issubset(abnormal_params_set):
            size = len(entry["params"])
            if size > best_size:
                best = entry
                best_size = size

    if best:
        return best.copy()

    return FALLBACK_ENTRY.copy()


def resolve_condition(abnormal_params_set: frozenset, patient_id: str, encounter_date: str) -> dict:
    """
    Deterministically resolve a frozenset of abnormal params to ONE concrete
    condition. Same (abnormal_params_set, patient_id, encounter_date) always
    returns the same result -- this is what lets step3 (labeling) and step4
    (symptom/drug sampling) independently re-resolve the SAME condition for a
    given row without passing python objects through the scratch CSV files.

    Returns a dict with: icd_chapter, icd_block, icd_candidate, condition_tag,
    differential_candidates, symptom_pool, prescription_pool.
    """
    entry = lookup_icd_entry(abnormal_params_set)

    if "candidates" not in entry:
        # Legacy flat entry -- identical behavior to before Rev 6.
        result = dict(entry)
        result.setdefault(
            "condition_tag",
            entry.get("icd_candidate") or (entry.get("differential_candidates") or ["unspecified"])[0],
        )
        return result

    monsoon = is_monsoon(encounter_date)
    key_str = ",".join(sorted(abnormal_params_set)) if abnormal_params_set else "normal"
    r = _stable_unit_interval(patient_id, encounter_date, f"disease_select::{key_str}")

    candidates = entry["candidates"]
    cumulative = 0.0
    selected = candidates[-1]
    for c in candidates:
        weight = c.get("monsoon_weight", c["weight"]) if monsoon else c["weight"]
        cumulative += weight
        if r < cumulative:
            selected = c
            break

    result = dict(selected)
    result.setdefault("icd_chapter", entry.get("icd_chapter"))
    result.setdefault("icd_block", entry.get("icd_block"))
    if "differential_candidates" not in result:
        siblings = [c["condition_tag"] for c in candidates if c is not selected]
        result["differential_candidates"] = siblings[:4] if len(siblings) >= 2 else siblings + ["observation_NOS"]
    return result
