# DATASET_REPOSITORY_AUDIT.md
# dataset-make Repository — Complete Audit

**Audit date:** 2026-08-11  
**Purpose:** Architecture discovery prior to extending this repository to generate a full longitudinal clinical dataset and LLM instruction dataset for PHC SaMD.  
**Auditor:** Automated deep-read of all source files.

---

## 1. Repository Structure

```
dataset-make/
├── .git/                              # 2 commits (see §12 Reproducibility)
├── docs/
│   └── PIPELINE_REGENERATION_PLAN.md  # 341-line design document (pre-Rev6 plan)
├── drishti_dataset/                   # Final classifier dataset outputs
│   ├── README.md                      # Schema + usage documentation
│   ├── canonical_dataset.csv          # 22,215 rows × 30 columns (POST-noise)
│   ├── canonical_dataset_prenoise.csv # 22,215 rows × 30 columns (PRE-noise)
│   ├── metadata.json                  # Machine-readable provenance (ISO 14971)
│   ├── noise_log.json                 # Noise seed + parameters applied 2026-07-23
│   └── _archive/
│       └── pre_regen_2026-07-23/      # Earlier ~20k-row dataset (pre-Rev6)
│           ├── canonical_dataset.csv
│           └── canonical_dataset_prenoise.csv
├── drishti_pipeline/                  # Python pipeline (all post-processing)
│   ├── __init__.py
│   ├── config.py                      # 1349-line single source of truth
│   ├── patch_config.py                # One-off regex patching script (historical, stale)
│   ├── preflight_check.py             # Pre-run reachability checker
│   ├── requirements.txt               # pandas>=2.0, numpy>=1.24, pyyaml>=6.0
│   ├── run_pipeline.py                # Master orchestrator (Phase 1-3 + spot checks)
│   ├── step1_generate.py              # Invokes Synthea via gradlew
│   ├── step2_extract_vitals.py        # observations.csv + patients.csv -> vitals_raw
│   ├── step2b_demographic_reweight.py # Census 2011 age-sex resampling
│   ├── step3_tiered_generator.py      # Threshold assessment, tiering, ICD labeling
│   ├── step4_symptom_pairing.py       # Symptom/drug sampling from condition pools
│   ├── step5_aggregate.py             # Schema enforcement, dedup, canonical CSV write
│   ├── step6_noise_injection.py       # Gaussian noise injection (post-label)
│   ├── README.md
│   └── scratch/                       # Intermediate per-seed files (not committed)
│       ├── vitals_raw_{seed}.csv      # One per Synthea run (seeds 42-54 + 9990-9994)
│       ├── vitals_pool_reweighted.csv # After step2b
│       ├── tiered_global.csv          # After step3 global run
│       ├── tiered_with_symptoms_*.csv # After step4 (seeds 46, 58 present)
│       ├── _archive/                  # Earlier scratch runs
│       └── *.py                       # Debug/sanity-check one-off scripts
├── output_india/                      # Synthea raw output (most recent run)
│   ├── csv/                           # 16 CSV files from last Synthea run
│   └── fhir/                          # FHIR bundles (hospital + practitioner info, US data)
│       ├── hospitalInformation*.json  # ~350+ FHIR JSON files (US hospital data)
│       └── practitionerInformation*.json
├── synthea/                           # Synthea source (git-committed copy)
│   ├── build.gradle                   # Gradle 8.14 / Java 17 / shadow plugin 8.3.9
│   ├── gradlew + gradlew.bat
│   ├── src/main/resources/
│   │   ├── synthea.properties         # Default config (FHIR on, CSV off)
│   │   ├── biometrics.yml             # US default (overridden at runtime by step1)
│   │   ├── biometrics_original.yml    # Backup created by step1 (US biometrics)
│   │   ├── version.txt                # "4be782f" -- git commit hash, not semver
│   │   ├── modules/                   # US disease modules (all standard modules)
│   │   ├── geography/                 # US demographics/zipcodes/timezones
│   │   ├── providers/                 # US hospital/clinic/VA provider lists
│   │   ├── payers/                    # US Medicare/Medicaid/insurance plans
│   │   └── costs/                     # US-specific procedure/medication costs
│   └── config/simulations/            # YAML physiology simulation configs
├── synthea-international/             # International biometrics overrides
│   └── in/src/main/resources/
│       └── biometrics.yml             # India-calibrated vital/lab ranges (only India file)
├── synthea_india_run.properties       # 26-line Synthea run override (CSV on, FHIR off)
├── patch_config.py                    # Root-level copy (dead code)
└── test_step4.py                      # Minimal smoke test for step4
```

---

## 2. Synthea Version and Invocation

### Version
- **Source:** `synthea/src/main/resources/version.txt` -> `4be782f`
- This is a **git commit hash**, not a semantic version tag.
- The Synthea directory is a committed copy of source (not a submodule).
- **Build system:** Gradle 8.14, Java source/target compatibility 17, shadow plugin 8.3.9.
- **No semantic version is recorded.** This is a **reproducibility gap.**

### How Synthea is invoked
In `step1_generate.py`, Synthea is invoked via:
```bash
./gradlew run -Params="['-s','<seed>','-p','<pop>','-a','5-80','-c','<props_path>']"
```
Arguments:
- `-s <seed>` — random seed
- `-p <pop>` — population count per run (default 500)
- `-a 5-80` — age range (from `config.MIN_AGE`/`config.MAX_AGE`)
- `-c <synthea_india_run.properties>` — override properties file

**Run directory:** `synthea/` (cwd set to `config.SYNTHEA_ROOT`)

### Does the pipeline modify Synthea itself?
**No.** The pipeline only consumes Synthea output. The one exception is a temporary file swap: `step1_generate.py` replaces `synthea/src/main/resources/biometrics.yml` with the India version before invoking Synthea, then restores the original from `biometrics_original.yml` afterward (always, even on failure via `try/finally`). No Java source is modified.

---

## 3. Synthea Configuration

### Runtime override: `synthea_india_run.properties`
```properties
exporter.csv.export = true
exporter.fhir.export = false          # All FHIR variants disabled
exporter.fhir.r4.export = false
# ... all other exporters = false
exporter.baseDirectory = ../output_india
synthea.log.level = warn
generate.payers.insurance_companies.default_file = generic/payers/insurance_companies.csv
```

Only CSV export is enabled. Output goes to `output_india/csv/`.

**Note:** The existing `output_india/fhir/` files were generated by an earlier Synthea run with FHIR enabled, outside of the standard pipeline invocation.

### Default config `synthea.properties` (key settings)
```properties
generate.geography.country_code = US
generate.demographics.default_file = geography/demographics.csv   # US demographics
generate.geography.zipcodes.default_file = geography/zipcodes.csv
generate.providers.hospitals.default_file = providers/hospitals.csv
generate.insurance.mandate.year = 2006    # Massachusetts individual mandate
exporter.fhir.use_us_core_ig = true
```

The default config is entirely US-oriented. The runtime override does not touch geography or demographics.

### Biometrics override: `synthea-international/in/src/main/resources/biometrics.yml`
The **only India-specific Synthea configuration file.** It recalibrates:
- Blood pressure normal/hypertensive ranges (IHCI-aligned: systolic 100-129 normal, 140-200 hypertensive)
- Glucose bins (random/non-fasting — widened in Rev 6 to `[70, 100, 145, 220]` from fasting-style `[70, 100, 126, 200]`)
- Lipid panel (lower HDL floor for South Asian phenotype)
- SpO2 normal range (tightened floor to 95%)
- Weight management BMI start threshold (23 vs US 30)
- Twin rate, adult weight gain rates

It does **not** affect: age/sex distributions, geography, names, providers, insurance, or clinical disease module selection.

---

## 4. Disease Modules

### Which modules are selected?
**None explicitly.** Synthea runs with all default modules enabled (the standard US disease module library). The pipeline then **discards all Synthea-generated disease diagnoses and conditions** — it only reads `observations.csv` (vital signs) and `patients.csv` (demographics).

**Labels are NOT derived from Synthea's disease modules.** They come entirely from `config.py:ICD_MAPPING`.

The Synthea `-k` (keep-module) flag is **not used**. No module filtering is applied.

---

## 5. Patient Generation

- Seeds: start at `start_seed` (default 42), increment by 1 per pass
- Population per run: 500 (default `--pop-per-run`)
- Age range: `5-80` (via `-a 5-80` flag)
- Location: **Massachusetts, US** (Synthea default — not overridden)
- Accumulation loop runs until:
  - Raw pool size >= `target_rows × RAW_POOL_MULTIPLIER` (4×)
  - `glucose_high` rows >= `MIN_GLUCOSE_HIGH_FLOOR` (500)
  - Rare disease floors met (300 rows each for B54, D50, E05.9, F41.0, A92.0, A15)
- Existing run: seeds 42-54 + 9990-9994 (18 passes visible from scratch/ files) × 500 pop = ~9,000 Synthea patients

---

## 6. Random Seeds

| Component | Seed | Source |
|---|---|---|
| Synthea generation | 42, 43, 44, ... (incrementing) | `--start-seed 42` |
| Demographic reweighting (step2b) | `next_seed + 1` | `run_pipeline.py` internal logic |
| Tiering + ICD labeling (step3) | `next_seed + 2` | `run_pipeline.py` internal logic |
| Symptom/drug pairing (step4) | `next_seed + 3` | `run_pipeline.py` internal logic |
| Noise injection (step6) | **999** (fixed) | `--noise-seed 999` default |
| ICD condition resolution | SHA-256 hash of `(patient_id, encounter_date, salt)` | `config._stable_unit_interval()` |
| SpO2/pulse imputation (step2) | **None — unseeded `np.random`** | `step2::impute_missing_vitals()` |

**Reproducibility gap:** SpO2 and pulse imputation in step2 uses `np.random.uniform()` without seeding.

**Reproducibility gap:** The exact seed list used across passes is printed to console only — not written to any log file.

---

## 7. Demographic Configuration

### Age distribution
Synthea generates with age range 5-80 (`-a 5-80`). The internal draw within 5-80 follows Synthea's US demographic distribution.

**Step 2b reweighting** corrects this post-hoc:
```python
TARGET_AGE_SEX_DISTRIBUTION = {
    (5, 14):  0.19, (15, 24): 0.19, (25, 34): 0.17, (35, 44): 0.14,
    (45, 54): 0.11, (55, 64): 0.08, (65, 74): 0.07, (75, 80): 0.05,
}
TARGET_SEX_SHARE = {"M": 0.515, "F": 0.485}   # Census 2011 ~940F:1000M
```

Under-represented cells (typically elderly) are resampled **with replacement**; over-represented cells are downsampled.

### Actual dataset demographics (measured from 22,215 rows)
- Age: mean=35.96, median=34, min=5, max=79
- Sex: M=51.8%, F=48.2% — close to Census 2011 target
- Age <18: 5,906 rows (26.6%)

### Names / addresses
Patients have US-format names and Massachusetts addresses. All encounter addresses are Massachusetts. These fields are fully discarded by step2 (only UUID, birthdate, gender are used).

---

## 8. FHIR / CSV / JSON Exports

### What Synthea exports for this pipeline
With `synthea_india_run.properties`, only CSV is exported (16 files in `output_india/csv/`):
```
allergies.csv    conditions.csv   encounters.csv   immunizations.csv
careplans.csv    devices.csv      imaging_studies.csv  medications.csv
claims.csv       observations.csv organizations.csv    patients.csv
payer_transitions.csv  payers.csv  procedures.csv  providers.csv
supplies.csv
```

### What the pipeline actually reads
- `observations.csv` — LOINC codes + numeric values (step2)
- `patients.csv` — UUID, birthdate, gender (step2)

### What is discarded
Everything else: conditions, medications, claims, providers, payers, immunizations, imaging studies, procedures, allergies, careplans, devices, supplies. Generated but never read.

### FHIR files in `output_india/fhir/`
Hundreds of `hospitalInformation*.json` and `practitionerInformation*.json` FHIR bundles exist from a prior Synthea invocation with FHIR enabled. These contain **US hospital data** and are **not used by the pipeline at all**.

---

## 9. Transformation: Synthea Output -> Classifier Dataset

### Complete code path (traced from source)

```
biometrics.yml  (backed up, India version installed by step1)
  + synthea_india_run.properties
  -> gradlew run -Params=['-s',seed,'-p',500,'-a','5-80','-c',props_path]
  -> output_india/csv/observations.csv  (all LOINC observations)
  -> output_india/csv/patients.csv      (UUID, birthdate, gender)

[step2_extract_vitals.py]
  1. Load observations.csv, filter to 6 LOINC codes:
       "8867-4"    -> pulse
       "59408-5"   -> spo2  (also "2708-6" as secondary)
       "8480-6"    -> bp_systolic
       "8462-4"    -> bp_diastolic
       "39156-5"   -> bmi
       "2339-0"    -> glucose
  2. Pivot: one row per (PATIENT, ENCOUNTER, DATE)
  3. Join with patients.csv for age (birthdate computation) and sex
  4. Filter: MIN_AGE(5) <= age <= MAX_AGE(80)
  5. Impute missing SpO2 (np.random.uniform(95,100)) and pulse (np.random.uniform(60,100))
  6. Drop rows with <3 vitals (MIN_VITALS_PER_ROW=3)
  -> scratch/vitals_raw_{seed}.csv

[step2b_demographic_reweight.py]  (once, after all accumulation passes)
  1. Concatenate all scratch/vitals_raw_*.csv
  2. Resample per (age-band x sex) cell to match Census 2011 targets
  -> scratch/vitals_pool_reweighted.csv

[step3_tiered_generator.py :: run_global()]
  1. Assess each row for abnormalities:
       - bp_systolic: abnormal if >= 140 (adults); Narang formula (age<18)
       - bp_diastolic: abnormal if >= 90 (adults); Narang formula (age<18)
       - spo2: abnormal if < 95%
       - bmi: abnormal if >= 23.0 (adults; B2 strategy: not assessed for age<18)
       - pulse_high: if > 100 bpm; pulse_low: if < 60 bpm
       - glucose_high: if >= 140 mg/dL (no age-gating)
       - fever_pattern: synthetic hash flag (~8% base, ~22% monsoon Jun-Sep)
  2. _param_count = count of abnormal params (EXCLUDING fever_pattern)
     _tier_bucket = min(4, _param_count + 1)
  3. Build tiers with global targets (GLOBAL_TIER_TARGET_RATIOS × target_rows):
       Tier 1: 35% (0 abnormal params)
       Tier 2: 57% (1 abnormal param)
       Tier 3:  6.5% (2 abnormal params)
       Tier 4:  1.5% (3+ abnormal params)
  4. ICD labeling: config.resolve_condition(frozenset(abnormals), patient_id, date)
       -> deterministic SHA-256 candidate selection
       -> icd_chapter, icd_block, icd_candidate, differential_candidates
  -> scratch/tiered_global.csv

[step4_symptom_pairing.py :: run()]
  1. For each row: config.resolve_condition() [SAME deterministic result as step3]
  2. Sample 2-4 symptoms from condition's symptom_pool
     (10% distractor injection, 20% synonym substitution)
  3. Sample 1 drug/dosage from condition's prescription_pool
  4. For age < 18: drug_name="None", drug_dosage="None", pediatric_referral_flag=True
  -> tiered_df + symptom_string, symptom_signal_strength, drug_name, drug_dosage

[step5_aggregate.py :: run()]
  1. Add synthetic=True, source="synthea_india"
  2. Enforce canonical column order (30 columns)
  3. Deduplicate on (patient_id, encounter_date)
  4. Schema validation (non-nullables, icd_candidate sentinels, signal_strength enum)
  5. Hard-fail AssertionError if any age<18 row has non-null drug_name
  -> drishti_dataset/canonical_dataset.csv  (pre-noise)

[step6_noise_injection.py :: run()]
  1. Save canonical_dataset_prenoise.csv (never overwritten)
  2. Apply Gaussian noise per vital (* -> *_observed columns):
       bp_systolic:  sigma=4.0,  clip=15.0, floor=60.0
       bp_diastolic: sigma=3.0,  clip=15.0, floor=30.0
       pulse:        sigma=3.0,  clip=15.0, floor=30.0
       bmi:          sigma=0.5,  clip=2.0,  floor=10.0
       spo2:         sigma=1.0,  clip=5.0,  floor=70.0, ceil=100.0
       glucose:      sigma=10.0, clip=30.0, floor=40.0
     Labels NOT recalculated post-noise
  3. Write noise_log.json
  -> drishti_dataset/canonical_dataset.csv  (post-noise, with *_observed columns)
```

---

## 10. Labels and ICD Mapping

### Source of labels
Labels come **entirely from `config.py:ICD_MAPPING`**, not from Synthea's disease modules.

`ICD_MAPPING` maps `frozenset(abnormal_params)` to condition definitions. Example entries:
- `frozenset({"bp_systolic", "bp_diastolic"})` -> I10 (essential hypertension)
- `frozenset({"glucose_high"})` -> E11 (type-2 diabetes)
- `frozenset({"fever_pattern"})` -> weighted candidates (dengue/malaria/UTI/viral fever/etc.)
- `frozenset()` (fallback) -> general wellness/check-up label

### Multi-candidate resolution (Rev 6)
Some frozensets map to a `candidates` list with weights + optional monsoon weights. `config.resolve_condition()` uses SHA-256 hash of `(patient_id, encounter_date, salt)` to deterministically pick one candidate. Both step3 (labeling) and step4 (symptom/drug sampling) call this same resolver — label/symptom/drug can never silently disagree for a given row.

### 22 conditions covered across 4 tiers + fever_pattern axis
```
ICD Chapter IX  (Circulatory):    I10 (essential HTN), I10 (white-coat, null candidate)
ICD Chapter X   (Respiratory):    J22 (LRTI)
ICD Chapter I   (Infectious):     B54 (malaria), A90/A91 (dengue/DHF), A01.0 (typhoid),
                                   A92.0 (chikungunya), A09 (gastroenteritis), A15 (pulm. TB)
ICD Chapter IV  (Endocrine):      E11 (T2DM), E03.9 (hypothyroidism), E05.9 (hyperthyroid),
                                   E66 (obesity), metabolic syndrome (null)
ICD Chapter XIII (Musculoskeletal): M17 (osteoarthritis)
ICD Chapter VI  (Neurological):   G43.9 (migraine)
ICD Chapter XIV (Genitourinary):  N39.0 (UTI)
ICD Chapter V   (Mental health):  F41.0 (anxiety/panic disorder)
ICD Chapter III (Haematological): D50 (anemia)
```

### Tier distribution in current dataset (22,215 rows)
| Tier | Description | Count | % |
|---|---|---|---|
| 1 | 0 abnormal vitals | 7,766 | 34.9% |
| 2 | 1 abnormal vital | 12,676 | 57.0% |
| 3 | 2 abnormal vitals | 1,450 | 6.5% |
| 4 | 3+ abnormal vitals | 333 | 1.5% |

### Top icd_candidate values
```
NaN (null by design): 7,110 rows (32.0%)
E66 (obesity):        6,317 rows (28.4%)
M17 (osteoarthritis): 3,499 rows (15.7%)
I10 (hypertension):   1,283 rows (5.8%)
N39.0 (UTI):            556 rows (2.5%)
A09 (gastroenteritis):  538 rows (2.4%)
A01.0 (typhoid):        446 rows (2.0%)
B54 (malaria):          445 rows (2.0%)
A90 (dengue):           429 rows (1.9%)
A92.0 (chikungunya):    315 rows (1.4%)
```

---

## 11. Output Schema

### `canonical_dataset.csv` — 30 columns
```
patient_id              [str,   non-null]  UUID from Synthea
encounter_date          [str,   non-null]  ISO-8601 date string
age_at_encounter        [int,   non-null]  years, range 5-79
sex                     [str,   non-null]  "M" or "F"
bp_systolic             [float, non-null]  mmHg (pre-noise "true" value)
bp_diastolic            [float, non-null]  mmHg (pre-noise)
pulse                   [float, non-null]  bpm (pre-noise, may be imputed)
spo2                    [float, non-null]  % (pre-noise, may be imputed)
bmi                     [float, NULLABLE]  kg/m2 (NaN if not measured)
glucose                 [float, NULLABLE]  mg/dL random (NaN if not drawn; not imputed)
bp_systolic_observed    [float, non-null]  mmHg (post-noise)
bp_diastolic_observed   [float, non-null]  mmHg (post-noise)
pulse_observed          [float, non-null]  bpm (post-noise)
spo2_observed           [float, non-null]  % (post-noise)
bmi_observed            [float, NULLABLE]  kg/m2 (post-noise, NaN where bmi is NaN)
glucose_observed        [float, NULLABLE]  mg/dL (post-noise, NaN where glucose is NaN)
tier                    [int,   non-null]  1-4
abnormal_params         [str,   non-null]  comma-sep sorted names; "normal" if none
fever_pattern_flag      [bool,  non-null]  synthetic epidemiological routing signal
symptom_string          [str,   non-null]  "symptom1 | symptom2 | ..." (2-4 symptoms)
symptom_signal_strength [str,   non-null]  "strong" / "supportive" / "nonspecific"
drug_name               [str,   non-null]  India-appropriate drug; "None" for age<18
drug_dosage             [str,   non-null]  dosage string; "None" for age<18
icd_chapter             [str,   non-null]  ICD-10 chapter name
icd_block               [str,   non-null]  ICD-10 block range (e.g. "I10-I15")
icd_candidate           [str,   NULLABLE]  specific ICD-10 code or null (null by design)
differential_candidates [str,   non-null]  pipe-sep ranked list (2-4 entries)
pediatric_referral_flag [bool,  non-null]  True for age < 18
synthetic               [bool,  non-null]  Always True
source                  [str,   non-null]  Always "synthea_india"
```

**No train/validation/test split exists in this repository.**

---

## 12. Reproducibility

### What is documented / preserved
| Item | Status |
|---|---|
| noise_seed=999 | checkmark Written to `noise_log.json` |
| noise parameters (sigma, clip, floor/ceil) | checkmark Written to `noise_log.json` |
| biometrics.yml override | checkmark Committed in `synthea-international/in/` |
| config.py thresholds + ICD mapping | checkmark Committed |
| Target row count (27,000) | checkmark In `metadata.json` |
| Age range (5-80) | checkmark In `config.py` |
| Demographic targets (Census 2011) | checkmark In `config.py` |
| Pre-noise dataset backup | checkmark `canonical_dataset_prenoise.csv` |
| Tier ratios | checkmark In `config.py::GLOBAL_TIER_TARGET_RATIOS` |

### Reproducibility gaps
| Item | Gap |
|---|---|
| Synthea version | WARN Only a commit hash `4be782f`, no semantic version |
| Exact seed list per run | WARN Printed to console only -- not saved to file |
| SpO2/pulse imputation seed | GAP `np.random.uniform()` without seeding -- non-deterministic |
| Demographic reweight seed | WARN Passed as `next_seed + 1` (not independently logged) |
| Python version | WARN Not documented anywhere |
| Java/Gradle version | WARN build.gradle requires Java 17 but actual JVM version not recorded |
| Pipeline dependency versions | WARN requirements.txt has ranges (>=), not pinned versions |
| Reference date | WARN Synthea uses system clock -- encounter dates vary by when pipeline ran |
| Number of accumulation passes | WARN Not logged to any file |

---

## 13. US-Specific Assumptions

### Hard-wired in Synthea (not overridden)
| Category | Location | Details |
|---|---|---|
| **State: Massachusetts** | `output_india/metadata/*.json` filenames | Every metadata file includes "Massachusetts" |
| **Country: US** | `synthea.properties` | `generate.geography.country_code = US` |
| **US demographics** | `geography/demographics.csv` | US city/county population drives age/sex draws |
| **US zip codes** | `geography/zipcodes.csv` | Massachusetts zip codes |
| **US addresses** | Synthea patient generator | All patient ADDRESS, CITY, STATE are Massachusetts |
| **US hospitals/providers** | `providers/` directory | US hospital names, locations, providers |
| **US insurance/payers** | `payers/` directory | Medicare, Medicaid, US commercial insurance |
| **US insurance mandate** | `synthea.properties` | `generate.insurance.mandate.year = 2006` |
| **US medication costs** | `costs/` directory | Procedure/medication costs in USD |
| **FHIR US Core IG** | `synthea.properties` | `exporter.fhir.use_us_core_ig = true` |
| **US patient names** | `names.yml` | US name distributions |
| **US disease prevalences** | Synthea disease modules | US epidemiology drives which patients get flagged as hypertensive/diabetic by Synthea internally |

### Mitigated at pipeline level
| Category | Mitigation |
|---|---|
| US-pattern age/sex draws | step2b Census 2011 reweighting |
| US BP thresholds (AHA 130/80) | IHCI 140/90 in config.py |
| US BMI threshold (30) | WHO Asian 23/25 in config.py |
| US biometrics ranges | India biometrics.yml installed at runtime |
| US glucose cutoffs (126 fasting) | Widened to [70,100,145,220] for random/non-fasting |

### Assessment
The US-specific assumptions are **mostly benign for the existing pipeline** because step2 discards nearly everything Synthea generates except raw vital sign numeric values. The India calibration applies via: (1) biometrics.yml (numeric ranges), (2) config.py thresholds (abnormality rules), (3) step2b (demographics correction). Names, addresses, providers, insurance, and US diagnoses are never read after step2.

**For the LLM dataset extension (which will read FHIR bundles and patient history):** the US-specific context will become a problem. Patient names, addresses, conditions (using US disease module prevalences), and clinical notes will all be US-flavored. A FHIR India adaptation layer will be required.

---

## 14. Component Classification

### KEEP UNCHANGED
| Component | Reason |
|---|---|
| `step1_generate.py` | Clean Synthea invocation wrapper. India biometrics swap is exactly right. |
| `synthea-international/in/src/main/resources/biometrics.yml` | India-calibrated vital/lab ranges. Well-documented. |
| `synthea/` (entire Synthea source) | Not modified by pipeline. Stable base. |
| `synthea_india_run.properties` | Correct run config for vitals-only CSV extraction. |
| `step6_noise_injection.py` | Clean noise injection. Prenoise backup logic is correct. |
| `canonical_dataset_prenoise.csv` | Canonical pre-noise reference. |
| `noise_log.json` | Reproducibility record. |

### SAFE TO EXTEND
| Component | Extension Points |
|---|---|
| `config.py` | Add new clinical thresholds, extend ICD_MAPPING, new vital types, India drug/symptom pools |
| `step2_extract_vitals.py` | Add new LOINC codes to VITAL_LOINCS dict; add new output columns |
| `step2b_demographic_reweight.py` | Update demographic targets (Census 2021, finer age bands) |
| `step3_tiered_generator.py` | Add new abnormal parameter types; modular assess_row() |
| `step4_symptom_pairing.py` | Add new condition-specific pools in config.py; extend SYNONYMS |
| `step5_aggregate.py` | Add new canonical columns, update validation rules |
| `run_pipeline.py` | Add new phases, extend accumulation stopping conditions |
| `preflight_check.py` | Add new reachability checks for new condition types |
| `drishti_dataset/metadata.json` | Extend with new schema/provenance fields |

### REFACTOR REQUIRED
| Component | Reason |
|---|---|
| `step2_extract_vitals.py::impute_missing_vitals()` | Uses unseeded np.random -- breaks reproducibility. Must seed explicitly. |
| Seed tracking | Seeds printed to console only. run_pipeline.py should write a generation_log.json. |
| FHIR export configuration | New properties file needed for FHIR-enabled runs (do not modify existing .properties) |
| `step1_generate.py::run_synthea()` | Gradle -Params syntax is Groovy list format (tested on Windows). Linux gradlew may need different quoting. Platform testing required. |

### DO NOT REUSE
| Component | Reason |
|---|---|
| `drishti_pipeline/patch_config.py` (both copies) | Historical one-shot patcher. Dead code. |
| `drishti_pipeline/scratch/*.py` debug scripts | Ad-hoc debug one-offs. Not pipeline code. |
| `drishti_pipeline/scratch/_archive/` | Historical scratch files. |
| `output_india/fhir/` hospital/practitioner JSON | US hospital data. Not India-relevant. |
| `docs/PIPELINE_REGENERATION_PLAN.md` | Superseded by implemented Rev 6. Historical only. |
| `test_step4.py` | Minimal 9-line smoke test. Not a proper test suite. |
| `drishti_dataset/_archive/pre_regen_2026-07-23/` | Pre-Rev6 dataset. Superseded. |

---

## 15. Existing Weaknesses

1. **No train/validation/test split** anywhere in this repository.
2. **No reproducibility log for seed list or pass count.** Seeds printed to stdout only.
3. **Non-deterministic imputation.** `np.random.uniform()` in step2 for SpO2/pulse is unseeded.
4. **No reference date configuration.** Synthea uses the system clock.
5. **Single flat CSV output only.** No FHIR, no structured patient-level grouping, no longitudinal ordering.
6. **Pediatric BMI is entirely unevaluated (B2 strategy).** IAP 2015 growth chart lookup table is deferred.
7. **Disease coverage is vital-sign-fingerprint-limited.** Many PHC conditions require the multi-candidate mechanism since their vital fingerprints are not unique.
8. **No longitudinal modeling.** Each encounter row is independent. No patient history or progression.
9. **Synthea's US disease prevalences drive vital-sign distributions.** The biometrics.yml adjusts value ranges but not which patients Synthea internally tags as hypertensive/diabetic.
10. **No configurable FHIR export in the pipeline.** FHIR is disabled via the run properties file.
11. **`patch_config.py` is dead code** but exists in two locations — confusing for contributors.
12. **Single `config.py` file (1349 lines) contains all clinical knowledge.** Will become maintenance burden as the LLM extension adds more mappings.

---

## 16. Files to be Created in the Extension Phase

Based on the planned extension to longitudinal clinical + LLM instruction dataset:
```
synthea_india_fhir.properties          # Enable FHIR R4 + CSV simultaneously
drishti_pipeline/data/
  iap_bmi_percentiles.csv              # IAP 2015 BMI percentile lookup (deferred)
longitudinal_pipeline/                 # New pipeline module
  step_fhir_extract.py                 # FHIR bundle -> clinical fact ledger
  step_india_adapt.py                  # India normalization layer
  step_phc_normalize.py                # PHC context normalization
  step_fact_ledger.py                  # Clinical fact ledger builder
  step_llm_task_gen.py                 # LLM instruction generation
  step_validation.py                   # LLM dataset validation
  step_split.py                        # SFT/evaluation dataset splitting
LONGITUDINAL_SCHEMA.md                 # Per-patient longitudinal schema
LLM_DATASET_SCHEMA.md                 # LLM instruction dataset schema
generation_log.json                    # Runtime: seed list, pass counts, stopping conditions
```
