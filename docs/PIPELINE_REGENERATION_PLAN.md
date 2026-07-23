# DRISHTI Dataset Regeneration + AI Kernel Roadmap

## Context

This repo (`E:\dataset make\drishti_pipeline`) generates a synthetic Indian patient-vitals
dataset (`drishti_dataset/canonical_dataset.csv`) that bootstraps a two-layer AI diagnostic
kernel for a PHC health-consultation product (DRISHTI/SaMD, IIT Indore). A separate repo,
`E:\SaMD\SaMDAI\SaMDClassifier`, trains an XGBoost "Layer 1" classifier on a *copy* of this
dataset, and a mobile app (`E:\SaMD\SaMDapp\SaMD-App`) will eventually call it.

Investigation this session (3 research passes + code reads of `config.py`, `step3`, `step4`,
`run_pipeline.py`) found the live dataset has regressed and is too narrow to be useful:

1. **Regression**: `canonical_dataset.csv` (20,124 rows) is missing `drug_name`, `drug_dosage`,
   `pediatric_referral_flag` even though `config.py`/`step4.py`/`step5.py` already fully
   implement them (confirmed present in `scratch/tiered_with_symptoms_*.csv`). Root cause: only
   `step6` (noise injection) was re-run after these fields were added to code — steps 1-5 were
   never re-run end-to-end. **Pure regeneration fix, no code bug here.**
2. **Disease coverage too narrow**: only 3 ICD chapters ever realize in the data (Circulatory,
   Nutritional/metabolic, Respiratory). Vector-borne diseases (malaria/dengue/typhoid/
   chikungunya) exist only as `differential_candidates` text, gated behind a monsoon-season
   60%-probability promotion that has **never actually fired** in the current dataset (zero
   infectious-chapter rows exist).
3. **No glucose vital** — Synthea already generates India-calibrated glucose observations
   (LOINC `2339-0`, confirmed present in `output_india/csv/observations.csv`) but step2 never
   extracts it, so diabetes can only ever be an inferred BMI differential, never a real signal.
4. **Demographics are not India-realistic** — age/sex distribution is Synthea's default
   (US-pattern) generator, merely clipped to age 5-80. The India `biometrics.yml` override only
   recalibrates vital/lab *ranges*, not the age/sex generator itself. Confirmed no India
   demographics/geography module exists in `synthea-international/in/` (only `de`, `fr`, `gb`,
   etc. ship one).
5. **Tier imbalance**: Tier 4 (4+ abnormal params) is 0.27% of the dataset (54/20,124 rows)
   because tier quotas are applied *per Synthea pass* and accumulate inconsistently across ~40+
   passes, rather than as global targets. This starves the classifier of minority-class signal.

User decision for **this session**: fix and regenerate the **dataset only** (this doc, Part
A). Classifier retraining, the deterministic drug/dosage runtime table, the symptom-LLM layer,
and kernel JSON wiring are explicitly deferred — captured here as Part B so the work can resume
later without re-deriving the architecture.

Also confirmed and locked in via user Q&A this session:
- Disease breadth target: ~15-20 conditions, recommended PHC set (see Part A, Section 2).
- Add random blood glucose as a 6th vital (Recommended option chosen).
- Future kernel JSON contract should reuse the Android app's existing `KernelPayload` /
  `KernelReportOutput` Kotlin data classes (`E:\SaMD\SaMDapp\SaMD-App\...\domain\model\`) rather
  than a fresh design — captured in Part B, Phase 4.

---

## Part A — Execute now: dataset regeneration (`drishti_pipeline`)

### A1. Regression fix
No code fix needed. Resolved automatically by the full regeneration in A6 — verify afterward
that `canonical_dataset.csv`'s header includes `drug_name`, `drug_dosage`,
`pediatric_referral_flag`.

### A2. Disease coverage expansion — `config.py`

Several requested conditions (anemia, hyperthyroidism, anxiety/panic, migraine,
osteoarthritis, and the 4 vector-borne fevers) have no clinically-distinguishable vital-sign
fingerprint from each other in a 6-7-signal system. Extend `ICD_MAPPING` so a frozenset key can
map to a **weighted list of candidate conditions**, deterministically resolved per row (more
clinically honest than fabricating fake unique combos, and the only way to make rare diseases
realize at a controllable, nonzero, reproducible frequency). Conditions with a real vital
fingerprint (type-2 diabetes via glucose, hypothyroidism via pulse_low+bmi) get clean flat
single-candidate entries as before.

- **New synthetic signal `fever_pattern`** (config.py): a deterministic hash-based flag —
  `_stable_unit_interval(patient_id, encounter_date, salt)` (sha256-based, same row always
  yields the same value) drives an ~8% base rate / ~22% monsoon (Jun-Sep) rate. This replaces
  the old sequential-RNG monsoon promotion that never fired in practice. Document loudly in code
  + README that this is an epidemiological routing signal, not a measured vital, and that it
  must **not** count toward `tier`/`_param_count` (tier reflects physiological derangement
  severity only). Keep `_param_count` computed over `{bp_systolic, bp_diastolic, pulse_high,
  pulse_low, bmi, glucose_high, spo2}` only.
- **Shared resolver `config.resolve_condition(abnormal_params_set, patient_id, encounter_date)`**:
  wraps `lookup_icd_entry`; for legacy flat entries behaves identically to today; for new
  multi-candidate entries, deterministically picks one candidate via the same stable-hash
  technique (weights, with a monsoon-specific weight override per candidate). **Critical
  correctness requirement**: both `step3_tiered_generator.py` (labeling) and
  `step4_symptom_pairing.py` (symptom/drug sampling) must call this *same* resolver with the
  *same* `(patient_id, encounter_date)` inputs, or step3 could label a row "dengue" while step4
  independently re-rolls "malaria" symptoms/drugs for it — a silent label/symptom mismatch. This
  requires changing `step4.sample_symptom()`'s signature to take `patient_id`/`encounter_date`
  instead of re-deriving everything from just the abnormal-params string + a row-index seed.
- **Modify 3 existing flat entries → multi-candidate**: `{"pulse_high"}` (add anxiety/panic,
  anemia, hyperthyroidism as siblings of sinus_tachycardia), `{"bp_systolic"}` (add migraine and
  white-coat-HTN as siblings of stage-1 HTN), `{"bmi"}` (add osteoarthritis as sibling of
  obesity).
- **New flat entries**: `{"pulse_low","bmi"}` → hypothyroidism; `{"glucose_high"}` → type-2
  diabetes; `{"glucose_high","bmi"}` → metabolic syndrome; `{"glucose_high","bp_systolic",
  "bp_diastolic"}` → diabetes+hypertension combo.
- **New `fever_pattern`-anchored multi-candidate entries**: `{"fever_pattern"}` (viral fever,
  UTI, gastroenteritis, typhoid, dengue — weighted, monsoon-boosted); `{"fever_pattern",
  "pulse_high"}` (dengue, malaria, typhoid, chikungunya, GE-with-dehydration);
  `{"fever_pattern","spo2"}` (LRTI, pulmonary TB, dengue-with-warning-signs);
  `{"fever_pattern","spo2","pulse_high"}` (severe pneumonia/sepsis, dengue hemorrhagic fever,
  severe malaria).
- Every new/modified entry needs its own `symptom_pool` (3-5 `(text, strength)` tuples) and
  `prescription_pool` (India-appropriate drug/dose pairs — e.g. Artemether-Lumefantrine for
  malaria, HRZE/RNTCP referral for TB, ORS+Zinc for gastroenteritis, Ferrous Sulphate+Folic Acid
  for anemia).
- Net result: ~19 distinct `condition_tag`/`icd_candidate` values across 6 new + 3 modified + 4
  new flat keys — within the agreed ~15-20 target, all deterministically reproducible and
  actually realized in output (verified via A7 checks), not just defined-but-dormant like today.
- Delete the old ad-hoc "Seasonality check for Vector-Borne diseases" block in
  `step3_tiered_generator.py::add_icd_labels()` (lines ~130-154) — replaced by the
  `resolve_condition()` call.
- Fix `E:\dataset make\test_step4.py` — stale hard-coded Linux path and old 1-arg
  `sample_symptom()` call signature; update or delete since it's not part of the pipeline proper.

### A3. Add glucose as 6th vital

- `config.VITAL_LOINCS`: add `"2339-0": "glucose"`.
- `step2_extract_vitals.py`: extend the vital-columns loop to include `glucose`. **Do not**
  add it to `impute_missing_vitals()` — keep it nullable/sparse like `bmi` (it's an opportunistic
  lab, not a routine check; fabricating "normal" glucose would be more misleading than the
  existing spo2/pulse imputation — this asymmetry is intentional, comment it clearly). Keep
  `MIN_VITALS_PER_ROW = 3` as an absolute floor, not scaled up, so glucose sparsity doesn't start
  dropping otherwise-good rows.
- `config.ADULT_THRESHOLDS["glucose"]`: normal <140, prediabetes 140-199, diabetes ≥200 mg/dL
  (RSSDI / ICMR-INDIAB **random/non-fasting** glucose screening criteria — explicitly distinct
  from the fasting cutoffs already baked into `biometrics.yml`). Applied uniformly age 5-80, no
  age-gating (unlike BP).
- `step3.assess_row()`: add `glucose_high` to `abnormal` if `glucose >= 140`.
- **Realization-rate fix is required, not optional** — measured during research: only ~1.1% of
  Synthea's current glucose draws land ≥126 and 0% ≥200 under the existing `biometrics.yml` bins
  (`[70, 100, 126, 200]`, tied to Synthea's own US-epidemiology-driven `diabetes_severity`
  tagging). Widen the bins in
  `synthea-international/in/src/main/resources/biometrics.yml` to `[70, 100, 145, 220]` so more
  of the already-tagged pre-diabetic/diabetic population actually crosses the 140 mg/dL random-
  glucose threshold. This doesn't fully fix prevalence (Synthea's core disease-tagging module is
  out of scope to edit) — pair with the "keep generating extra passes until a floor is met"
  mechanism in A5 for `glucose_high` specifically (target floor: ~500 rows).
- Schema: add `glucose`, `glucose_observed` to `CANONICAL_COLUMNS`/`CANONICAL_DTYPES` (float32,
  nullable); add `fever_pattern_flag` (boolean, non-nullable) too.
- `step5_aggregate.py`: add `glucose` to float coercion list; cast `fever_pattern_flag` to bool
  like the existing `pediatric_referral_flag` cast; do **not** add `glucose` to `NON_NULLABLE`
  (it's meant to be sparse).
- `step6_noise_injection.py` / `config.NOISE_PARAMS`: add
  `"glucose": {"sigma": 10.0, "clip": 30.0, "floor": 40.0}` — sigma approximates glucometer
  point-of-care measurement error (~10 mg/dL, ISO 15197 conservative band), floor is the
  clinical severe-hypoglycemia cutoff below which a "noised" reading isn't physiologically
  meaningful, no ceiling needed (meters read to 500-600 mg/dL).

### A4. India-realistic demographics — new post-hoc reweighting step

Confirmed no native India demographics/geography module exists in Synthea to swap in, so this
must be a **post-hoc reweighting step**, not a Synthea-side fix:

- New file `drishti_pipeline/step2b_demographic_reweight.py`: reads the *accumulated* pool of
  `scratch/vitals_raw_*.csv` (not per-pass — too few rows per age×sex bucket in a single 500-row
  pass to resample meaningfully), bins rows into age-decade × sex cells, and resamples
  (with replacement for under-represented cells, e.g. elderly 75-80; downsample for
  over-represented ones) to match a hardcoded approximate Indian age-sex distribution.
- `config.TARGET_AGE_SEX_DISTRIBUTION`: per-decade shares from Census 2011 broad age-band
  structure, renormalized to the pipeline's 5-80 window (5-14: 19%, 15-24: 19%, 25-34: 17%,
  35-44: 14%, 45-54: 11%, 55-64: 8%, 65-74: 7%, 75-80: 5%); `TARGET_SEX_SHARE = {"M": 0.515,
  "F": 0.485}` (Census 2011 sex ratio). Precision isn't required for a synthetic bootstrap
  dataset — cite the source in a comment and move on.
- `config.RAW_POOL_MULTIPLIER = 4`: accumulate ~4x the target row count of raw vitals before
  reweighting so under-represented buckets have enough natural donor rows and don't need
  excessive with-replacement duplication. Print a before/after distribution table and flag any
  cell needing heavy oversampling.

### A5. Restructure `run_pipeline.py` — global targets instead of per-pass accumulation

The current per-seed loop (step1→2→3→4→5 each pass, incrementally appended) is incompatible with
global reweighting (A4) and global tier balancing (needed to fix the Tier-4 starvation problem).
Restructure into three phases:

1. **Accumulate raw pool**: loop step1+step2 only, until `raw_pool_size >= target_rows *
   RAW_POOL_MULTIPLIER` AND the rare-class floors are met (peek at `_param_count`/glucose columns
   of the accumulating pool each iteration using step3's `assess_row` logic to check floors
   without fully committing labels yet).
2. **Reweight once**: `step2b.run()` → `vitals_pool_reweighted.csv`.
3. **Global tier/label/aggregate once**: new `step3.run_global(path)` entry point (reads the
   reweighted pool directly instead of a per-seed file), then `step4.run(...)`,
   `step5.run(...)` as single calls, not per-seed.

`config.GLOBAL_TIER_TARGET_RATIOS`: replaces `TIER1_COUNT`/`TIER2_COUNT`/`TIER3_COUNT` with
global ratios across the *whole* final dataset, extended to 6 tiers now that glucose adds a 6th
abnormal-param axis: `{1: 0.35, 2: 0.30, 3: 0.18, 4: 0.10, 5: 0.05, 6: 0.02}`. Tier 4 and 5 become
exact-count buckets (`==4`, `==5`) instead of the old "4+" catch-all; Tier 6 = all 6 abnormal.
Add `MIN_TIER5_6_FLOOR = 800` and `MIN_GLUCOSE_HIGH_FLOOR = 500` as absolute floors gating phase-1
accumulation, with a hard cap on extra passes (mirror the existing `pass_num > estimated_total *
10` safety valve) so it can't loop forever if a floor is genuinely unreachable — log a clear
warning and proceed with whatever was accumulated.

This changes `run_pipeline.py` from "incremental, resumable by row count" to "one batch
regeneration run" — an intentional, documented behavior change for this regeneration.

### A6. Regeneration procedure

1. **Archive, don't delete** (for before/after comparison):
   `drishti_dataset/canonical_dataset.csv`, `canonical_dataset_prenoise.csv`, `noise_log.json`,
   and all `drishti_pipeline/scratch/*.csv` → a dated archive folder, e.g.
   `drishti_dataset/_archive/pre_regen_2026-07-23/` and
   `drishti_pipeline/scratch/_archive/pre_regen_2026-07-23/`.
2. **Clear the live paths** before running — required, not optional.
   `step6_noise_injection.py` never overwrites an existing `canonical_dataset_prenoise.csv` by
   design (audit trail); if left in place it will silently pair the *old* 20,124-row prenoise
   file against the *new* ~25-30k-row canonical, masked by the existing row-count-mismatch
   warning instead of giving a clean new baseline. This is the single most important gotcha.
3. Apply all A2-A5 code changes.
4. Bump `--target-rows` from 20,000 to ~25,000-30,000 (existing CLI flag) — the richer taxonomy
   needs bigger minority-class counts.
5. Run: `python -m drishti_pipeline.run_pipeline --target-rows 27000 --start-seed 42
   --pop-per-run 500 --noise-seed 999 --spot-checks`.
6. Confirm `canonical_dataset_prenoise.csv` is freshly written with no row-count-mismatch warning
   from step6.

### A7. Validation — extend `run_spot_checks()` in `run_pipeline.py`

All existing checks stay and must still pass (SBP≥140 sanity, BMI≥23 sanity, synthetic=True,
icd_candidate null-rate 10-90%, differential_candidates ≥2 entries, **hard pediatric-drug
assertion**). Add:

1. **Schema presence** (hard fail): `{"drug_name","drug_dosage","pediatric_referral_flag",
   "glucose","glucose_observed","fever_pattern_flag"}` ⊆ `df.columns`.
2. **Disease realization** (warn, don't hard-fail — RNG/pool-size dependent): each new
   `icd_candidate` code (B54 malaria, A90/A91 dengue, A01.0 typhoid, A92.0 chikungunya, D50
   anemia, E03.9 hypothyroid, E05.9 hyperthyroid, E11 diabetes, A15 TB, J22 LRTI, A09 GE, N39.0
   UTI, F41.0 anxiety, G43.9 migraine, M17 osteoarthritis) appears with count > 0 in
   `icd_candidate.value_counts()`.
3. **Tier distribution**: print `tier.value_counts(normalize=True)`; warn if Tier 5+6 combined
   < 4% (target ≥5%, small RNG variance tolerated).
4. **Pediatric hard-fail** — re-confirm it still passes given the new entries (all route through
   step4's single blanket `age<18 → drug=None` override, no per-entry pediatric logic needed).
5. **Glucose sparsity sanity check**: print `glucose.notna().mean()` and `glucose_high` row
   count, confirming the biometrics.yml realization-rate fix worked (compare against the ~1%
   pre-fix baseline measured this session).
6. **Age/sex distribution check**: cross-tab against `TARGET_AGE_SEX_DISTRIBUTION`; warn if any
   bucket is off by >5 points from target after reweighting.

### A8. Docs updates

- `drishti_dataset/README.md`: add glucose to the clinical-threshold-sources table (explicitly
  labeled "random/non-fasting", distinct from the existing fasting-126 entry already documented
  elsewhere); add `glucose`/`glucose_observed`/`fever_pattern_flag` to the schema table
  (`fever_pattern_flag` explicitly annotated as a synthetic epidemiological signal, not a
  measured vital); new subsection explaining the weighted multi-candidate resolution mechanism
  and why it exists (most important thing for a future maintainer/auditor to understand); update
  tier description from 1-4 to 1-6 with new global ratios; update age/sex section to describe
  the reweighting methodology + Census 2011 citation + resampling caveat; update target row
  count.
- `drishti_dataset/metadata.json`: add glucose threshold entry, new column entries, updated
  tiers object (1-6 + ratios), new `demographics_reweighting` object, new `disease_coverage`
  object listing all new `condition_tag`/`icd_candidate` pairs and which resolve via
  weighted-multi-candidate vs. flat keys (ISO 14971 traceability, matching the existing
  rationale already in `config.py`'s header).

### Critical files (Part A)
- `E:\dataset make\drishti_pipeline\config.py`
- `E:\dataset make\drishti_pipeline\step2_extract_vitals.py`
- `E:\dataset make\drishti_pipeline\step3_tiered_generator.py`
- `E:\dataset make\drishti_pipeline\step4_symptom_pairing.py`
- `E:\dataset make\drishti_pipeline\step5_aggregate.py`
- `E:\dataset make\drishti_pipeline\step6_noise_injection.py`
- `E:\dataset make\drishti_pipeline\run_pipeline.py`
- `E:\dataset make\drishti_pipeline\step2b_demographic_reweight.py` (new)
- `E:\dataset make\synthea-international\in\src\main\resources\biometrics.yml`
- `E:\dataset make\drishti_dataset\README.md`, `metadata.json`
- `E:\dataset make\test_step4.py` (fix or remove — stale)

### Verification (today's scope)
1. Run the pipeline command in A6 step 5 with `--spot-checks`.
2. Confirm no `AssertionError` (pediatric hard-fail) and no schema-presence failure.
3. Manually inspect printed `icd_candidate.value_counts()` and `tier.value_counts()` against A7's
   targets; if any new disease has zero realized rows, increase phase-1 accumulation passes for
   that specific combo before declaring done.
4. Diff row/column counts against the archived pre-regen files from A6 step 1 as a sanity gut-
   check (expect ~25-30k rows, 27 → ~30 columns, 3 → ~9+ icd_chapters).

---

## Part B — Deferred to a future session (roadmap only, not built today)

Captured here so a future session can resume without re-deriving the architecture. Confirmed
with the user this session; do not re-litigate these decisions, just execute when picked up.

### B1. XGBoost classifier retrain (`E:\SaMD\SaMDAI\SaMDClassifier`)
- Point `train_model.py` at the regenerated dataset (fix the drift: classifier currently trains
  on a stale local copy, `dataset/canonical_dataset.csv`, that doesn't match
  `E:\dataset make\drishti_dataset\canonical_dataset.csv` — different row counts/hashes).
  Establish an explicit sync step (copy script or symlink) so this can't silently drift again.
- Switch training input from pre-noise vitals to the `_observed` columns (that's the actual
  point of the noise-injection fix — training on ground truth defeats it).
- Add glucose as a real feature (currently `random_glucose` is accepted by the FastAPI app but
  silently unused — comment in `train_model.py` explicitly notes "canonical dataset does not
  contain glucose", which A3 fixes).
- Fix the calibration mismatch bug found this session: `train_model.py` evaluates a
  `CalibratedClassifierCV`-wrapped model (reporting 95.9% accuracy / 95.5% F1-macro) but saves
  and serves the *raw uncalibrated* model in `model.json` — decide whether to persist/serve the
  calibrated wrapper instead, or re-evaluate on the raw model so reported metrics match what's
  actually served.
- Add explicit overfitting checks beyond a single stratified 80/20 split — e.g. k-fold CV score
  reporting (not just inside `RandomizedSearchCV`'s internal cv=3), and a train-vs-test score
  comparison printed and logged (currently nothing is persisted from a training run except the
  final `model_meta.json` numbers — no historical log).
- Extend the label space beyond the current 3-class tier collapse (`low/moderate/high_risk`,
  tiers 3+4 merged) to make use of the new 1-6 tier granularity and the new icd_chapter/candidate
  columns, per the two-layer design in B2-B3.

### B2. Deterministic drug/dosage protocol table (runtime layer, separate from dataset generation)
- The dataset's `prescription_pool` sampling (built in Part A) is for *training data
  generation* only — it stays as-is. This is about a **separate, serving-time lookup table**
  that the AI kernel consults at inference time, keyed by resolved ailment + severity/tier,
  structured the same way as `config.py`'s clinical-threshold-sources pattern (deterministic,
  auditable, no ML).
- Must include an explicit pediatric/comorbidity safety branch that outputs a referral flag,
  never a computed dose, for age <18 — mirroring the dataset-generation pipeline's existing
  blanket pediatric override (A2/A3's `age<18 → drug=None + pediatric_referral_flag=True`), so
  the same safety invariant holds at both training-data-generation time and serving time.

### B3. Symptom-text LLM layer + Triangulator
- Vitals (numeric) → XGBoost tier/risk classifier (B1) stays as one input.
- Chief complaint / symptom text → an LLM (MedGemma or similar) → structured symptom vector +
  candidate-ailment shortlist. Not started — needs a model-hosting decision first.
- A "Triangulator" step combines both into a final ailment/differential with confidence — not
  designed in detail yet, needs its own planning pass once B1 and the LLM layer both exist.

### B4. Kernel JSON API — reuse Android app schema
- Build the kernel's JSON input/output around the **existing** Android app data classes rather
  than a fresh schema, so the already-built (currently fully-mocked) client can plug in without
  rework:
  - Input: `KernelPayload` (`E:\SaMD\SaMDapp\SaMD-App\...\domain\model\KernelPayload.kt`) —
    `caseToken`, `vitals`, `chiefComplaint`, `durationBucket`, `severityScore`,
    `relevantHistory`, `transcription`, `attachments`. Deliberately excludes patient-identifying
    fields (name/Aadhaar/ABHA/phone/address) — preserve that.
  - Output: `KernelReportOutput` — `predictedCondition`, `confidenceScore`,
    `differentials`, `reasoningSummary`, `evidenceFor`/`evidenceAgainst`, `modelVersion`,
    `icdCode`, `riskCategory`, `urgencyLevel`, `requiredHumanVerification` — will need
    **extending** with drug/dosage/prescription fields since the current Android schema has no
    dosage-table representation yet (confirmed: `SaMD-App` only has a doctor-authored
    `Prescription`/`MedicationLine` model on the *receiving* side, nothing for a kernel-generated
    dosage).
  - The classifier repo's current `POST /v1/assess` endpoint (`app.py`) uses a different,
    narrower ad-hoc schema (`PatientVitalsRequest`/dict response) — this will need to be
    replaced or wrapped to match `KernelPayload`/`KernelReportOutput` before real integration.
