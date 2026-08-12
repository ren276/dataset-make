# DATASET_ARCHITECTURE_CURRENT.md
# Current Pipeline Architecture

**As of:** 2026-08-11 (Rev 6, post-refactor)  
**Output:** `drishti_dataset/canonical_dataset.csv` — 22,215 rows × 30 columns (classifier dataset)

---

## Architecture Overview

The pipeline is a **batch, multi-pass accumulation → single-pass global transformation** process:

```
Phase 1: ACCUMULATION
  [Synthea × N passes]  ->  N × vitals_raw_{seed}.csv  (scratch/)

Phase 2: GLOBAL TRANSFORM
  vitals_pool_reweighted.csv
    -> tiered_global.csv
    -> tiered_with_symptoms.csv (passed in-memory, not written per-pass in production)
    -> canonical_dataset.csv     (PRE-noise)

Phase 3: NOISE
  canonical_dataset.csv (pre-noise)
    -> canonical_dataset_prenoise.csv  (backup, write-once)
    -> canonical_dataset.csv           (POST-noise, with *_observed columns)
```

---

## Component Interaction Diagram

```
config.py
  |-- VITAL_LOINCS         --> step2_extract_vitals.py
  |-- MIN_AGE, MAX_AGE     --> step1_generate.py, step2
  |-- ADULT_THRESHOLDS     --> step3_tiered_generator.py (assess_row)
  |-- get_bp_threshold()   --> step3 (Narang formula for age<18, IHCI for age>=18)
  |-- assess_fever_pattern()--> step3 (SHA-256 hash, base_rate=0.08, monsoon=0.22)
  |-- ICD_MAPPING          --> step3, step4 (resolve_condition)
  |-- FALLBACK_ENTRY       --> step3, step4 (resolve_condition fallback)
  |-- resolve_condition()  --> step3 (labeling), step4 (symptom/drug sampling)
  |-- GLOBAL_TIER_TARGET_RATIOS --> step3 (run_global quota allocation)
  |-- TARGET_AGE_SEX_DISTRIBUTION --> step2b_demographic_reweight
  |-- TARGET_SEX_SHARE     --> step2b
  |-- RAW_POOL_MULTIPLIER  --> run_pipeline.py (accumulation stopping condition)
  |-- MIN_GLUCOSE_HIGH_FLOOR --> run_pipeline.py
  |-- RARE_DISEASE_CODES   --> run_pipeline.py
  |-- NOISE_PARAMS         --> step6_noise_injection.py
  |-- CANONICAL_COLUMNS    --> step5_aggregate.py
  |-- VALID_SIGNAL_STRENGTHS --> step4, step5
  |-- SYNTHEA_ROOT         --> step1
  |-- SYNTHEA_BIOMETRICS   --> step1 (path to biometrics.yml to swap)
  |-- INDIA_BIOMETRICS_SRC --> step1 (path to India biometrics.yml)
  |-- SYNTHEA_RUN_PROPS    --> step1 (path to .properties file)
  |-- SYNTHEA_OUTPUT_DIR   --> step1 (verify output), step2 (load output)
  |-- PIPELINE_SCRATCH_DIR --> step2, step2b, step3, step4
  |-- DATASET_OUTPUT_DIR   --> step5, step6

run_pipeline.py (orchestrator)
  |-- Phase 1 loop: calls step1.run() + step2.run() per seed
  |   |-- stopping: pool_size >= target * RAW_POOL_MULTIPLIER
  |   |             AND glucose_high >= MIN_GLUCOSE_HIGH_FLOOR
  |   |             AND rare disease floors met
  |-- Phase 2: calls step2b.run(), then step3.run_global(), step4.run(), step5.run()
  |-- Phase 3: calls step6.run()
  |-- run_spot_checks(): verifies pediatric invariant + schema post-generation
```

---

## Data Shape at Each Stage

### Stage 0: Synthea raw output (per pass)
- `observations.csv`: ~50,000-200,000 rows per 500-patient run
  - Columns: PATIENT (UUID), ENCOUNTER (UUID), DATE, CODE (LOINC), VALUE (string), ...
  - Contains all LOINC observation codes for all conditions Synthea simulated
- `patients.csv`: ~500 rows per run
  - Columns: Id, BIRTHDATE, DEATHDATE, SSN, GENDER, RACE, ADDRESS, CITY, STATE, ...
  - All encounters are Massachusetts, US

### Stage 1: vitals_raw_{seed}.csv (step2 output)
- **Rows per pass:** ~150-300 rows (filtered from ~500 patients × multiple encounters)
- **Columns:** `patient_id, encounter_date, age_at_encounter, sex, bp_systolic, bp_diastolic, pulse, spo2, bmi, glucose`
- **Key transformation:** wide pivot from LOINC rows → one row per encounter
- **Filtering:** age 5-80; min 3 vitals present; SpO2/pulse imputed if missing (using unseeded np.random)
- **Glucose coverage:** ~30-50% of rows have a non-null glucose value (opportunistic lab)
- **BMI coverage:** ~60-80% of rows have non-null BMI

### Stage 2: vitals_pool_reweighted.csv (step2b output)
- **Rows:** `target_rows × RAW_POOL_MULTIPLIER` (e.g., 108,000 for 27,000 target × 4)
- **Same columns as vitals_raw**
- **Distribution:** age/sex reweighted to Census 2011 targets
- Cells with insufficient natural rows are resampled WITH replacement (reported in step2b output)

### Stage 3: tiered_global.csv (step3 output)
- **Rows:** ~27,000 (target_rows, after per-tier quota application)
- **New columns added:** `tier, abnormal_params, fever_pattern_flag, icd_chapter, icd_block, icd_candidate, differential_candidates`
- **Internal columns dropped:** `_abnormal_list, _param_count, _tier_bucket, _bmi_assessed`
- **Tier allocation:** applied globally once across all rows, balanced within each tier by `abnormal_params` diversity

### Stage 4: tiered_with_symptoms_{seed}.csv (step4 output)
- **Rows:** same as tiered_global.csv (~27,000)
- **New columns added:** `symptom_string, symptom_signal_strength, drug_name, drug_dosage, pediatric_referral_flag`
- **Pediatric override:** any row with `age_at_encounter < 18` gets `drug_name="None"`, `drug_dosage="None"`, `pediatric_referral_flag=True`

### Stage 5: canonical_dataset.csv PRE-NOISE (step5 output)
- **Rows:** 22,215 (27,000 target was not fully reached with seeds 42-54; dedup also removes some)
- **Columns:** 24 (all canonical columns minus the 6 *_observed columns added in step6)
- **Added columns:** `synthetic=True`, `source="synthea_india"`
- **Schema enforcement:** canonical column ordering, type coercions, icd_candidate None->null

### Stage 6: canonical_dataset.csv POST-NOISE (step6 output)
- **Rows:** 22,215 (unchanged)
- **Columns:** 30 (+ 6 `*_observed` columns added for each vital)
- **Labels NOT recalculated:** `abnormal_params`, `tier`, `icd_*`, `symptom_signal_strength` remain based on pre-noise values
- **noise_seed:** 999 (recorded in `noise_log.json`)

---

## Configuration Surface Map

`config.py` is the **single source of truth** for all clinical knowledge. It has these configurable sections:

### 1. Paths (auto-resolved from __file__)
```python
REPO_ROOT          = Path(__file__).resolve().parent.parent
SYNTHEA_ROOT       = REPO_ROOT / "synthea"
SYNTHEA_BIOMETRICS = SYNTHEA_ROOT / "src/main/resources/biometrics.yml"
SYNTHEA_BIOMETRICS_BACKUP = SYNTHEA_ROOT / "src/main/resources/biometrics_original.yml"
INDIA_BIOMETRICS_SRC = REPO_ROOT / "synthea-international/in/src/main/resources/biometrics.yml"
SYNTHEA_RUN_PROPS  = REPO_ROOT / "synthea_india_run.properties"
SYNTHEA_OUTPUT_DIR = REPO_ROOT / "output_india/csv"
PIPELINE_SCRATCH_DIR = REPO_ROOT / "drishti_pipeline/scratch"
DATASET_OUTPUT_DIR = REPO_ROOT / "drishti_dataset"
```

### 2. Age range
```python
MIN_AGE = 5
MAX_AGE = 80
```

### 3. Vital LOINC codes
```python
VITAL_LOINCS = {
    "8867-4":  "pulse",
    "59408-5": "spo2",
    "2708-6":  "spo2",      # secondary SpO2 LOINC
    "8480-6":  "bp_systolic",
    "8462-4":  "bp_diastolic",
    "39156-5": "bmi",
    "2339-0":  "glucose",   # random/non-fasting blood glucose
}
```

### 4. Clinical thresholds (India-calibrated)
```python
ADULT_THRESHOLDS = {
    "bp_systolic":  {"htn_stage1": 140},        # IHCI 2019 (not AHA 130)
    "bp_diastolic": {"htn_stage1": 90},         # IHCI 2019
    "spo2":         {"normal_min": 95.0},       # Standard
    "bmi":          {"overweight_min": 23.0, "obese_min": 25.0},  # WHO Asian
    "pulse":        {"normal_max": 100, "normal_min": 60},
    "glucose":      {"prediabetes_min": 140, "diabetes_min": 200}, # RSSDI random/non-fasting
}

# Pediatric BP: Narang et al. (AIIMS) age-sex formula
def get_bp_threshold(age, sex):
    if age >= 18:
        return {"sbp": 140, "dbp": 90}
    sbp = 110 + 1.6 * age + (1 if sex == "F" else 0)
    dbp = 79 + 0.7 * age + (1 if sex == "F" else 0)
    return {"sbp": sbp, "dbp": dbp}
```

### 5. Fever pattern signal
```python
# SHA-256 hash of (patient_id, encounter_date, salt) -> stable float in [0,1]
FEVER_PATTERN_BASE_RATE = 0.08    # ~8% year-round
FEVER_PATTERN_MONSOON_RATE = 0.22 # ~22% Jun-Sep (months 6,7,8,9)
FEVER_PATTERN_SALT = "fever_v1"
```

### 6. ICD_MAPPING structure
Each entry is a dict with:
- `"params"`: `frozenset` of abnormal parameter names (the lookup key)
- For **flat entries** (single condition): `"condition_tag"`, `"icd_chapter"`, `"icd_block"`, `"icd_candidate"`, `"differential_candidates"`, `"symptom_pool"`, `"prescription_pool"`
- For **multi-candidate entries**: `"candidates"` list where each candidate has `"condition_tag"`, `"weight"`, optionally `"monsoon_weight"`, plus the same medical fields

### 7. Tier ratios and accumulation controls
```python
GLOBAL_TIER_TARGET_RATIOS = {1: 0.35, 2: 0.57, 3: 0.065, 4: 0.015}
RAW_POOL_MULTIPLIER = 4         # Raw pool = target_rows × 4
MIN_GLUCOSE_HIGH_FLOOR = 500    # Min glucose_high rows in pool
RARE_DISEASE_CODES = {"B54", "D50", "E05.9", "F41.0", "A92.0", "A15"}
MIN_RARE_DISEASE_FLOOR = 300    # Min rows per rare disease code in pool
```

### 8. Noise parameters
```python
NOISE_PARAMS = {
    "bp_systolic":  {"sigma": 4.0,  "clip": 15.0, "floor": 60.0},
    "bp_diastolic": {"sigma": 3.0,  "clip": 15.0, "floor": 30.0},
    "pulse":        {"sigma": 3.0,  "clip": 15.0, "floor": 30.0},
    "bmi":          {"sigma": 0.5,  "clip": 2.0,  "floor": 10.0},
    "spo2":         {"sigma": 1.0,  "clip": 5.0,  "floor": 70.0, "ceil": 100.0},
    "glucose":      {"sigma": 10.0, "clip": 30.0, "floor": 40.0},
}
```

### 9. Canonical output schema
```python
CANONICAL_COLUMNS = [
    "patient_id", "encounter_date", "age_at_encounter", "sex",
    "bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi", "glucose",
    "bp_systolic_observed", "bp_diastolic_observed", "pulse_observed",
    "spo2_observed", "bmi_observed", "glucose_observed",
    "tier", "abnormal_params", "fever_pattern_flag",
    "symptom_string", "symptom_signal_strength",
    "drug_name", "drug_dosage",
    "icd_chapter", "icd_block", "icd_candidate", "differential_candidates",
    "pediatric_referral_flag", "synthetic", "source",
]
VALID_SIGNAL_STRENGTHS = {"strong", "supportive", "nonspecific"}
```

---

## Critical Design Invariants

### 1. Label/symptom consistency (step3 + step4 must agree)
Both `step3_tiered_generator.py::add_icd_labels()` and `step4_symptom_pairing.py::sample_symptom()` call **the same** `config.resolve_condition(abnormal_params_set, patient_id, encounter_date)`. Same inputs always produce the same condition selection (SHA-256-based). Without this, step3 could label a row "dengue" while step4 independently samples symptoms/drugs from "malaria".

### 2. Noise is applied after labels
Labels (`abnormal_params`, `tier`, `icd_*`, `symptom_signal_strength`) are set from pre-noise vital values and are **never recalculated** after noise injection. The `*_observed` columns carry the noised values. This is intentional: labels reflect the "true" clinical state, observed values reflect measurement error.

### 3. Pediatric drug safety invariant (hard-enforced at two points)
```
age_at_encounter < 18  =>  drug_name = "None" AND drug_dosage = "None" AND pediatric_referral_flag = True
```
Enforced in:
1. `step4_symptom_pairing.py::run()` — blanket override regardless of resolved condition
2. `step5_aggregate.py::run()` — `AssertionError` if any violation found
3. `run_pipeline.py::run_spot_checks()` — post-generation spot check

### 4. `fever_pattern` is excluded from tier counting
`fever_pattern` is an epidemiological routing signal, not a physiological derangement. It is appended to `abnormal_params` for ICD/symptom routing purposes but **does not contribute to `_param_count`** (which drives tier assignment).

### 5. `icd_candidate` null is valid and expected
32% of rows have `icd_candidate = null`. This is by design — it means the vital-sign combination does not narrow below block level. Null rows are the ones the LLM/retrieval Layer 2 is meant to handle. Do not fabricate values to fill them.

---

## Data Flow: One Encounter from Synthea to Final Row

Example trace for a patient with high BMI + fever pattern:

```
Synthea generates patient:
  PATIENT = "abc123..."
  GENDER = "F"
  BIRTHDATE = "1985-06-15"

Synthea generates observations including:
  PATIENT=abc123, ENCOUNTER=enc456, DATE=2023-08-15, CODE="39156-5", VALUE="25.3"  (BMI)
  PATIENT=abc123, ENCOUNTER=enc456, DATE=2023-08-15, CODE="8480-6",  VALUE="138"   (SBP)
  PATIENT=abc123, ENCOUNTER=enc456, DATE=2023-08-15, CODE="8462-4",  VALUE="87"    (DBP)
  PATIENT=abc123, ENCOUNTER=enc456, DATE=2023-08-15, CODE="8867-4",  VALUE="88"    (pulse)
  PATIENT=abc123, ENCOUNTER=enc456, DATE=2023-08-15, CODE="59408-5", VALUE="97"    (SpO2)

step2 pivots -> one row:
  patient_id=abc123, encounter_date=2023-08-15, age_at_encounter=38, sex=F
  bp_systolic=138.0, bp_diastolic=87.0, pulse=88.0, spo2=97.0, bmi=25.3, glucose=NaN

step3 assesses:
  bp_systolic: 138 < 140 -> NORMAL (IHCI adult threshold)
  bp_diastolic: 87 < 90 -> NORMAL
  spo2: 97 >= 95 -> NORMAL
  bmi: 25.3 >= 23.0 -> ABNORMAL (WHO Asian adult threshold)
  pulse: 88 in [60,100] -> NORMAL
  glucose: NaN -> not assessed

  fever_pattern: SHA-256("abc123", "2023-08-15", "fever_v1") -> 0.71
    month=8 (August, monsoon) -> threshold=0.22 -> 0.71 > 0.22 -> NO FEVER PATTERN
    (Actually: fever_pattern fires when hash < threshold, so 0.71 < 0.22 is False -> no fever)

  abnormal_params = ["bmi"]
  _param_count = 1, _tier_bucket = 2, tier = 2

step3 ICD lookup:
  frozenset({"bmi"}) -> ICD_MAPPING entry with candidates: [obesity, osteoarthritis]
  config.resolve_condition({"bmi"}, "abc123", "2023-08-15")
    SHA-256("abc123|2023-08-15|icd_v1") -> 0.43
    obesity has weight=0.55, osteoarthritis has weight=0.45
    cumulative: 0.55 -> 0.43 < 0.55 -> selects obesity
  icd_chapter = "Endocrine, nutritional and metabolic diseases"
  icd_block = "E65-E68"
  icd_candidate = "E66"
  differential_candidates = "E66|M17"

step4 symptom sampling:
  Same resolve_condition call -> obesity again
  obesity.symptom_pool has [("abdominal discomfort", "supportive"), ("fatigue", "supportive"), ...]
  r = random.Random(hash("bmi") + row_index)
  chosen = r.sample(pool, 3) -> ["abdominal discomfort", "fatigue", "joint pain"]
  symptom_string = "abdominal discomfort | fatigue | joint pain"
  symptom_signal_strength = "supportive"
  drug: obesity.prescription_pool -> ("Metformin", "500mg")
  age=38 >= 18 -> drug_name="Metformin", drug_dosage="500mg", pediatric_referral_flag=False

step5 canonicalizes:
  synthetic=True, source="synthea_india"
  All 30 column positions enforced

step6 noise:
  bp_systolic_observed = 138.0 + N(0, 4.0) clipped to ±15, floor=60 = ~140.2
  bp_diastolic_observed = 87.0 + N(0, 3.0) clipped to ±15, floor=30 = ~85.8
  ... etc.

Final row (30 columns):
  patient_id=abc123, encounter_date=2023-08-15, age_at_encounter=38, sex=F
  bp_systolic=138.0, bp_diastolic=87.0, pulse=88.0, spo2=97.0, bmi=25.3, glucose=NaN
  bp_systolic_observed=140.2, bp_diastolic_observed=85.8, pulse_observed=90.1,
  spo2_observed=96.5, bmi_observed=25.7, glucose_observed=NaN
  tier=2, abnormal_params="bmi", fever_pattern_flag=False
  symptom_string="abdominal discomfort | fatigue | joint pain"
  symptom_signal_strength="supportive"
  drug_name="Metformin", drug_dosage="500mg"
  icd_chapter="Endocrine, nutritional and metabolic diseases"
  icd_block="E65-E68", icd_candidate="E66"
  differential_candidates="E66|M17"
  pediatric_referral_flag=False, synthetic=True, source="synthea_india"
```

---

## Existing Pipeline Execution Points

| Script | Entry Point | Invocation |
|---|---|---|
| `run_pipeline.py` | `main()` | `python run_pipeline.py --target-rows 27000 --pop-per-run 500 --start-seed 42 --noise-seed 999` |
| `step1_generate.py` | `run(seed, pop_size)` | Direct: `python step1_generate.py --seed 42 --pop 500` |
| `step2_extract_vitals.py` | `run(seed)` | Direct: `python step2_extract_vitals.py --seed 42` |
| `step2b_demographic_reweight.py` | `run(pool_size, seed)` | Direct: `python step2b_demographic_reweight.py --pool-size 100000 --seed 7` |
| `step3_tiered_generator.py` | `run(seed)` or `run_global(input_path, target_rows, seed)` | Direct: `python step3_tiered_generator.py --seed 42` |
| `step4_symptom_pairing.py` | `run(tiered_df, seed)` | Direct: `python step4_symptom_pairing.py --seed 42` |
| `step5_aggregate.py` | `run(new_rows_df)` | Direct: `python step5_aggregate.py --seed 42` |
| `step6_noise_injection.py` | `run(noise_seed)` | Direct: `python step6_noise_injection.py --noise-seed 999` |
| `preflight_check.py` | `run_preflight(pop_per_seed, num_seeds)` | Direct: `python preflight_check.py --pop-per-seed 1000 --num-seeds 5` |

All scripts add the parent directory to `sys.path` and import `from drishti_pipeline import config`.

---

## Extension Points for Longitudinal / LLM Dataset

### What the current pipeline does NOT produce (and will need for the extension)
1. **FHIR bundles with clinical content** — The run properties file disables FHIR. A new `synthea_india_fhir.properties` needs to enable FHIR R4 export alongside CSV.
2. **Patient-level longitudinal ordering** — Encounters are stored independently. No grouping by patient, no timeline sorting.
3. **Clinical history / progression** — No mechanism to model HTN → CKD progression, T2DM complications, etc.
4. **India-specific clinical context in FHIR** — Conditions, medications, and providers in FHIR bundles use US names and US coding systems.
5. **LLM instruction format** — No instruction templating, no system/user/assistant conversation format, no quality scoring.
6. **Train/validation/test splits** — Not implemented anywhere.

### Where to hook into for the extension
| Extension Capability | Recommended Hook Point |
|---|---|
| Enable FHIR output | New `synthea_india_fhir.properties` + extend `step1_generate.py` to accept a properties flag |
| Extract FHIR clinical facts | New `step_fhir_extract.py` consuming `output_india/fhir/*.json` patient bundles |
| India adaptation (names, codes) | New `step_india_adapt.py` post-processing FHIR bundles before fact extraction |
| PHC encounter normalization | New `step_phc_normalize.py` applying PHC context rules (resource constraints, referral patterns) |
| Longitudinal patient grouping | New `step_fact_ledger.py` building per-patient fact timelines from extracted data |
| LLM task generation | New `step_llm_task_gen.py` templating instruction/response pairs from fact ledger |
| Dataset validation | New `step_validation.py` validating LLM task format, clinical plausibility |
| SFT/eval split | New `step_split.py` with stratified splitting by tier/condition/age-group |
| Reproducibility logging | Extend `run_pipeline.py` to write `generation_log.json` with seed list + pass counts |
| Seed fixing for step2 imputation | Fix `step2_extract_vitals.py::impute_missing_vitals()` to accept and use a seed |

---

## Validation Checks Currently in the Pipeline

| Check | Location | Failure Mode |
|---|---|---|
| observations.csv and patients.csv exist | `step1::verify_output()` | Returns False; pipeline exits |
| Minimum 3 vitals per encounter row | `step2::drop_sparse_rows()` | Row dropped silently |
| Age filter 5-80 | `step2::filter_age()` | Row dropped silently |
| Non-nullable columns are all present and non-null | `step5::validate()` | Prints error to stderr |
| icd_candidate has no empty-string sentinels | `step5::validate()` | Prints error to stderr |
| symptom_signal_strength is valid enum value | `step4::run()` + `step5::validate()` | Coerced to "nonspecific" in step4, error in step5 |
| Pediatric drug invariant | `step5::run()` | AssertionError (hard fail) |
| Pediatric drug invariant (spot check) | `run_pipeline::run_spot_checks()` | AssertionError (hard fail) |
| All-null vital rows | `step5::validate()` | Prints error to stderr |
| ICD_MAPPING weight sums | `preflight_check.py` | sys.exit(1) |
| Condition reachability | `preflight_check.py` | sys.exit(1) if any condition has 0 realizations in sample |
| Prenoise row count == postprocessed count | `step6::run()` | Warning to stderr |
| icd_candidate null rate 10-90% | `step5::report_icd_candidate_nulls()` | Alert to stdout |
| Noise standard deviation matches target sigma | `step6::run()` | Reported to stdout for human inspection |
| BP/BMI classification flips due to noise | `step6::run()` | Reported to stdout for human inspection |

---

## Key Design Decisions and Rationale

| Decision | Rationale |
|---|---|
| Labels from config.py ICD_MAPPING, not Synthea disease modules | Synthea's US disease module prevalences are not India-calibrated. Deriving labels from vital-sign thresholds gives full control over the label distribution and allows adding India-specific conditions that Synthea does not model. |
| Multi-candidate resolution via SHA-256 hash (not random draw at run time) | A row-local random draw would mean step3 and step4 could independently pick different conditions for the same row. The hash makes the choice deterministic and consistent across all steps, given the same (patient_id, encounter_date). |
| Tier 1 includes "normal" encounters (0 abnormal vitals) | A classifier must learn normal presentations, not just abnormal ones. Without normal rows, the model would only learn to identify abnormalities but not to rule them out. |
| fever_pattern excluded from tier count | Tier is meant to measure physiological vital-sign derangement severity. fever_pattern is a synthetic epidemiological routing signal, not a measured vital. Including it in the tier count would conflate two different concepts. |
| Noise applied AFTER labels | Labels must reflect the clinician's "true" assessment based on actual vitals. The noised *_observed values simulate measurement error (glucometer imprecision, BP cuff variability) — a model should learn to make correct decisions even with slightly noisy inputs. Labels based on pre-noise values are the ground truth. |
| icd_candidate nullable by design | It is clinically honest that "elevated BMI alone" cannot narrow below the block level E65-E68 to a specific code without additional information (patient history, family history, other labs). Forcing a candidate would introduce false precision. |
| Demographic reweighting post-hoc (not via Synthea) | No India demographics module exists in synthea-international/in. The only alternative would be to modify Synthea's Java source — far more brittle. Post-hoc reweighting with a documented census target is reproducible and easy to update when Census 2021 figures become available. |
