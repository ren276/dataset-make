# drishti_v2

New synthetic dataset generator, built against
`scratchpad/dataset-regeneration-design-memo.md`,
`scratchpad/questionnaire-tree-design-memo.md`, and
`scratchpad/reason-for-encounter-category-system-memo.md` (all in the SaMDApp
repo). The old `drishti_pipeline/` is left untouched for reference; this is a
clean, independent module with no import dependency on it.

Scope: full 33-branch clinical questionnaire tree (build-2) -- 26 core condition
branches, 1 fallback branch (`other_not_in_list`), and 6 Tier-0 emergency router
branches (`emergency_convulsions`, `emergency_unconscious`, `emergency_bite_sting`,
`emergency_poisoning`, `emergency_heavy_bleeding`, `emergency_pregnancy_danger`),
along with shared subtrees (`TB-SCREEN`, `DEHYDRATION`, `FEVER-QUAL v1.1`,
`EXPOSURE-CONTEXT-FEVER`, `RASH-MORPH`). Zero deferred branches.

## Running it

```
python -m drishti_v2.run_generation --n-rows 23000 --out-dir drishti_v2_output
```

Writes `corpus.csv`, `generation_manifest.json`, and
`perturbation_eval_set.csv` -- but only if all eight build gates pass. On any
gate failure nothing is written and the process exits non-zero with the gate
detail printed (memo section 7.5).

Tests: `python -m pytest drishti_v2/tests/`

## Known downstream dependencies (not built here)

1. **App-side precondition (out of scope for this build).**
   `RetrofitEvaluateSource.kt:38-66` still fabricates `bmi=22.0`,
   `systolicBp=120.0`, `diastolicBp=80.0`, `heartRate=72.0`, `spo2=98.0` when
   real vitals are absent, and `EvaluateRequestDto` types those fields as
   non-null `Double`, which is why the defaults exist. Per the regeneration
   memo section 5.3: **while those defaults exist, this corpus is invalid in
   the field** -- the model would train on honest absence
   (`NOT_MEASURED`/null) and be served fabricated normals at inference, a
   training/serving skew on exactly the feature the emergency path depends
   on. Removing the defaults and widening the DTO to nullable-plus-provenance
   is a separate, already-scoped app-side track (regeneration memo section
   10) and was not touched by this build.

2. **CBAC/IMCI/IHCI threshold reconciliation (build-time requirement, not
   performed).** `emergency.py`'s two-path thresholds (`THRESHOLD_TABLE_VERSION
   = "ews_provisional-0.1.0"`) are international early-warning-score-derived
   numbers, not an Indian clinical standard, and are marked PROVISIONAL
   throughout the manifest and per-row `threshold_table_version` column. The
   memo (section 6.3) names reconciling them against CBAC (Indian NCD
   screening), IMCI (paediatric protocol), and IHCI (140/90 hypertension
   threshold, already correctly used instead of AHA's 130) as a build-time
   requirement, physician-reviewed, before this corpus can back a
   regulatory claim. Not done here.

3. **Per-branch physician review (deferred, tree memo section 6.3).** Every
   answer-model entry is provenance-typed (`sourceType`/`source`/`declaredOn`),
   but `reviewedBy` is honestly set to the sentinel
   `PENDING_PHYSICIAN_REVIEW` throughout -- no clinician has signed any entry
   in this build. The condition catalogs, severity distributions, and most
   per-node answer distributions are `ASSUMED` infra-proving placeholders,
   coarser than a physician-authored branch would produce. This is stated
   loudly in `branches/authoring.py` and repeated here so the corpus is never
   mistaken for a clinically reviewed release.

4. **Real OOD eval set (category memo section 8.2).** `perturbation.py`
   builds the perturbation/robustness eval set (memo section 8.1) in full.
   The out-of-distribution/abstention eval set is explicitly a real-encounter
   collection task gated on consent and ethics approval and is out of scope
   for a generator -- not attempted here, and no synthetic proxy is produced
   (the memo permits a synthetic Tier-2 proxy for development only, labelled
   as a proxy; this build does not produce even that, to avoid any risk of
   it being mistaken for the real thing).

5. **Layer 1 normalization lexicon.** `narrative_terms` is a reserved column,
   not a populated one -- the lexicon that would populate it from free
   narrative is a separate artifact (architecture memo section 6.3: no Indic
   clinical text corpus with usable provenance exists yet).

## Build decisions not fully specified by the memos (stated, not buried)

- **MULTI_CHOICE answer-model shape.** The memo specifies a categorical
  (sums-to-1.0) distribution shape for the answer model but does not specify
  a shape for MULTI_CHOICE nodes. This build uses independent per-option
  Bernoulli inclusion probabilities (`kind="multi_bernoulli"` in
  `answer_model.py`), each still individually provenance-typed.
- **UNKNOWN nuisance channel.** Implemented as a flat per-node
  `unknown_rate`, independent of condition/severity by construction (never
  looked up from the condition-conditioned answer model), per memo section
  2.4's requirement that it never depend on the latent condition.
- **pregnancy_status for `known_hypertension`.** The tree memo's own section
  4 node table does not show a pregnancy question for this branch, yet
  `GW-HTN-URG-2` needs one to fire on an observable field rather than the
  hidden condition_id. `HTN-07B` was added (documented in
  `branches/known_hypertension.py`) using the same fieldId/options/guard as
  fever's FV-12.
- **GATE-DECLARED/GATE-MARGINAL tolerance.** Not numerically specified by the
  memo. Implemented as `TOLERANCE_Z=4` binomial standard errors around the
  declared proportion (with a small absolute floor for near-zero targets)
  rather than a flat relative percentage, because a flat tolerance under-
  counts sampling noise on the rarer severity-band cells (a few hundred
  rows). This is a statistical correction to an under-specified check, not a
  weakening of what the memo asked the gate to verify.
- **GATE-LEAK's pregnancy_status check excludes Tier-0-routed rows** from its
  denominator. A row a Tier-0 gateway routed away before reaching the
  pregnancy question is NOT_ASKED for a reason that is genuinely
  path-determined (fever has Tier-0 routing gateways ahead of that node;
  known_hypertension has none) -- exactly the "legitimate path-determined
  correlation" the memo says a properly stratified test must not flag.
- **GATE-LEAK's MI_MAX is Bonferroni-adjusted** across however many
  (field, stratum) checks the corpus actually runs, not a single flat
  percentile applied per check, to keep the gate's overall false-positive
  budget stable regardless of how many checks exist.
