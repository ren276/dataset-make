"""
drishti_pipeline/run_pipeline.py
=================================
Master orchestration for the DRISHTI foundational synthetic vitals pipeline.

Usage:
  python run_pipeline.py --target-rows 27000 [--start-seed 42] [--pop-per-run 500]
  python run_pipeline.py --target-rows 500   # smoke test

Rev 6 restructure — ONE BATCH RUN, not incremental/resumable by row count
(intentional behavior change from the old per-seed-append model). Three
phases, each running once across the whole dataset instead of per Synthea
pass:

  Phase 1 (accumulate): loop Step 1 (Synthea gen) + Step 2 (vitals
    extraction) until the accumulated raw pool reaches
    target_rows * config.RAW_POOL_MULTIPLIER AND the glucose_high rare-class
    floor is met (Tier 5/6 is deliberately NOT floor-gated -- see
    config.MIN_GLUCOSE_HIGH_FLOOR comment; 5-6 simultaneous abnormal vitals
    decays far too steeply to reach a meaningful floor in reasonable time,
    and forcing artificial abundance of it would work against the
    "realistic, not overfit" goal).
  Phase 2 (reweight): Step 2b resamples the accumulated pool once to
    approximate a target Indian age-sex distribution.
  Phase 3 (label+aggregate): Step 3's run_global() tiers + ICD-labels the
    whole reweighted pool at once using config.GLOBAL_TIER_TARGET_RATIOS,
    then Step 4 (symptom/drug pairing) and Step 5 (aggregate) each run once.

  Step 6 (noise injection) runs once at the end, as before.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from drishti_pipeline import config
import drishti_pipeline.step1_generate as step1
import drishti_pipeline.step2_extract_vitals as step2
import drishti_pipeline.step2b_demographic_reweight as step2b
import drishti_pipeline.step3_tiered_generator as step3
import drishti_pipeline.step4_symptom_pairing as step4
import drishti_pipeline.step5_aggregate as step5
import drishti_pipeline.step6_noise_injection as step6

import pandas as pd


def accumulate_raw_pool(target_rows: int, pop_per_run: int, start_seed: int) -> int:
    """
    Phase 1: loop Step 1 + Step 2 until the accumulated scratch/vitals_raw_*
    pool reaches target_rows * config.RAW_POOL_MULTIPLIER AND the
    MIN_GLUCOSE_HIGH_FLOOR rare-class floor is met. Peeks at the pool's
    abnormal-param breakdown each iteration via step3.assess_dataframe
    (cheap: no sampling/labeling, just the abnormality assessment).

    Tier 5/6 (5-6 simultaneous abnormal vitals) is intentionally NOT gated on
    a floor -- see the comment above config.MIN_GLUCOSE_HIGH_FLOOR in
    config.py. It decays far too steeply (measured: 4-param already only
    ~0.055% of pool, 5/6-param ~0%) for any floor in the hundreds to be
    reachable without hours of extra Synthea generation chasing a
    combinatorially-rare-to-nonexistent state. Its count is only logged here
    for visibility.

    Returns the next unused seed (for logging/reproducibility only).
    """
    seed = start_seed
    pass_num = 0
    raw_target = target_rows * config.RAW_POOL_MULTIPLIER
    estimated_total = max(10, raw_target // max(1, pop_per_run * 5))
    safety_cap = estimated_total * 10 + 50

    while True:
        pass_num += 1
        print(f"\n--- [Phase 1: accumulate] [seed={seed}] Pass {pass_num}/~{estimated_total} ---")

        print("[Step 1] Synthea generation...")
        ok = step1.run(seed=seed, pop_size=pop_per_run)
        if not ok:
            print(f"  [!]  Step 1 failed for seed={seed} — skipping to next seed")
            seed += 1
            if pass_num > safety_cap:
                break
            continue

        print("[Step 2] Vitals extraction...")
        try:
            step2.run(seed=seed)
        except Exception as e:
            print(f"  [!]  Step 2 error for seed={seed}: {e} — skipping")
            seed += 1
            if pass_num > safety_cap:
                break
            continue

        # Peek at accumulated pool to check stopping conditions
        pool = step2b.load_accumulated_pool()
        total_rows = len(pool)
        assessed = step3.assess_dataframe(pool)
        tier56 = int((assessed["_param_count"] >= 5).sum())
        glucose_high = int(assessed["abnormal_params"].fillna("").str.contains("glucose_high").sum())

        print(f"  [accumulate] pool={total_rows}/{raw_target} rows, "
              f"tier5+6={tier56} (no floor -- logged for visibility only), "
              f"glucose_high={glucose_high}/{config.MIN_GLUCOSE_HIGH_FLOOR}")

        seed += 1
        floors_met = glucose_high >= config.MIN_GLUCOSE_HIGH_FLOOR

        if total_rows >= raw_target and floors_met:
            print(f"\n  [ok] Phase 1 complete: {total_rows} rows, floors met, after {pass_num} passes "
                  f"(tier5+6 naturally at {tier56} rows)")
            break

        if pass_num > safety_cap:
            print(f"\n  [!]  WARNING: Exceeded {safety_cap} passes without meeting all "
                  f"targets/floors. Proceeding with what was accumulated "
                  f"({total_rows} rows, tier5+6={tier56}, glucose_high={glucose_high}).")
            break

    return seed


def run_pipeline(target_rows: int, start_seed: int, pop_per_run: int, noise_seed: int):
    print(f"\n{'='*60}")
    print(f"  DRISHTI Vitals Pipeline (Rev 6 — global-target batch run)")
    print(f"  Target: {target_rows} rows | Start seed: {start_seed} | Pop/run: {pop_per_run}")
    print(f"{'='*60}\n")

    # Pre-flight checks
    if not config.SYNTHEA_ROOT.exists():
        print(f"ERROR: Synthea root not found: {config.SYNTHEA_ROOT}", file=sys.stderr)
        sys.exit(1)
    if not config.INDIA_BIOMETRICS_SRC.exists():
        print(f"ERROR: India biometrics.yml not found: {config.INDIA_BIOMETRICS_SRC}", file=sys.stderr)
        sys.exit(1)

    print("[Phase 1] Accumulating raw vitals pool...")
    next_seed = accumulate_raw_pool(target_rows, pop_per_run, start_seed)

    print("\n[Phase 2] Demographic reweighting...")
    reweight_pool_size = target_rows * config.RAW_POOL_MULTIPLIER
    reweighted_path = step2b.run(pool_size=reweight_pool_size, seed=next_seed + 1)

    print("\n[Phase 3] Global tiering + ICD labeling...")
    tiered_df = step3.run_global(reweighted_path, target_rows=target_rows, seed=next_seed + 2)
    if tiered_df is None or tiered_df.empty:
        print("ERROR: Phase 3 produced no tiered rows — check accumulated pool quality", file=sys.stderr)
        sys.exit(1)

    print("\n[Step 4] Symptom + drug pairing...")
    symptom_df = step4.run(tiered_df, seed=next_seed + 3)

    print("\n[Step 5] Aggregating to canonical...")
    canonical = step5.run(symptom_df)

    print(f"\n{'='*60}")
    print(f"  [ok] Dataset build complete: {len(canonical)} rows (target was {target_rows})")
    print(f"{'='*60}")

    # Step 6: Noise injection (once, on the final canonical dataset)
    print("\n[Step 6] Applying noise injection...")
    try:
        step6.run(noise_seed=noise_seed)
    except Exception as e:
        print(f"  [!]  Step 6 error: {e}", file=sys.stderr)

    print(f"\n  Pipeline complete. Output: {step5.CANONICAL_PATH}")
    print(f"  Prenoise backup: {step6.PRENOISE_PATH}")
    print(f"  Noise log: {step6.NOISE_LOG_PATH}")


def run_spot_checks():
    """
    Post-run spot checks (assertion-based).
    Run after pipeline completes to verify key data quality properties.
    """
    path = step5.CANONICAL_PATH
    if not path.exists():
        print("  [check] canonical_dataset.csv not found — skipping spot checks")
        return

    print("\n--- Spot Checks ---")
    df = pd.read_csv(path, dtype={"patient_id": str})
    errors = []

    # Check 0 (Rev 6, hard fail): schema presence -- directly verifies the
    # drug_name/drug_dosage/pediatric_referral_flag regression is fixed and
    # the new glucose/fever_pattern_flag columns exist.
    required_cols = {
        "drug_name", "drug_dosage", "pediatric_referral_flag",
        "glucose", "glucose_observed", "fever_pattern_flag",
    }
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise AssertionError(f"HARD FAIL: canonical_dataset.csv missing required columns: {sorted(missing_cols)}")
    else:
        print(f"  [check] [ok]  all required Rev 6 columns present: {sorted(required_cols)}")

    # Check 1: Tier-1 bp_systolic rows -> SBP ≥ 140 (IHCI adult threshold)
    t1_sbp_only = df[(df["tier"] == 1) & (df["abnormal_params"] == "bp_systolic") &
                     (df["age_at_encounter"] >= 18)]
    if len(t1_sbp_only) > 0:
        sample = t1_sbp_only.sample(min(10, len(t1_sbp_only)), random_state=42)
        fail = (sample["bp_systolic"] < 140).sum()
        if fail > 0:
            errors.append(f"THRESHOLD CHECK: {fail}/10 sampled bp_systolic rows have SBP < 140 (IHCI)")
        else:
            print(f"  [check] [ok]  bp_systolic Tier-1 adult: all sampled rows SBP >= 140")

    # Check 2: Tier-1 bmi-only rows (adult) -> BMI >= 23 (WHO Asian)
    t1_bmi_only = df[(df["tier"] == 1) & (df["abnormal_params"] == "bmi") &
                     (df["age_at_encounter"] >= 18) & df["bmi"].notna()]
    if len(t1_bmi_only) > 0:
        sample = t1_bmi_only.sample(min(10, len(t1_bmi_only)), random_state=42)
        fail = (sample["bmi"] < 23).sum()
        if fail > 0:
            errors.append(f"THRESHOLD CHECK: {fail}/10 sampled bmi rows have BMI < 23 (WHO Asian)")
        else:
            print(f"  [check] [ok]  bmi Tier-1 adult: all sampled rows BMI >= 23")

    # Check 3: synthetic=True on all rows
    if "synthetic" in df.columns:
        not_synthetic = (~df["synthetic"].astype(str).str.lower().isin(["true", "1"])).sum()
        if not_synthetic > 0:
            errors.append(f"SYNTHETIC FLAG: {not_synthetic} rows missing synthetic=True")
        else:
            print(f"  [check] [ok]  synthetic=True on all {len(df)} rows")

    # Check 4: icd_candidate null rate
    if "icd_candidate" in df.columns:
        null_rate = df["icd_candidate"].isna().mean()
        if null_rate < 0.10 or null_rate > 0.90:
            errors.append(f"ICD_CANDIDATE NULL RATE: {null_rate:.1%} (expected 10–90%)")
        else:
            print(f"  [check] [ok]  icd_candidate null rate {null_rate:.1%} in expected range")

    # Check 5: differential_candidates has 2–4 pipe-separated entries
    if "differential_candidates" in df.columns:
        bad_diff = df["differential_candidates"].apply(
            lambda x: len(str(x).split("|")) < 2 if pd.notna(x) else True
        ).sum()
        if bad_diff > 0:
            errors.append(f"DIFFERENTIAL_CANDIDATES: {bad_diff} rows with < 2 entries")
        else:
            print(f"  [check] [ok]  differential_candidates: >=2 entries on all rows")

    # Check 6 (Rev 6, warn only — RNG/pool-size dependent, not a hard fail):
    # every newly-added disease should actually realize as a primary
    # icd_candidate, not just exist dormant in config.py like before.
    expected_new_codes = [
        "B54", "A90", "A91", "A01.0", "A92.0", "D50", "E03.9", "E05.9",
        "E11", "A15", "J22", "A09", "N39.0", "F41.0", "G43.9", "M17",
    ]
    if "icd_candidate" in df.columns:
        realized = set(df["icd_candidate"].dropna().unique())
        zero_realized = [c for c in expected_new_codes if c not in realized]
        if zero_realized:
            print(f"  [check] [!]  WARNING: {len(zero_realized)} new disease codes have ZERO "
                  f"realized rows: {zero_realized} — consider more Phase-1 accumulation passes.")
        else:
            print(f"  [check] [ok]  all {len(expected_new_codes)} new disease codes realized "
                  f"with >0 rows")

    # Check 7 (Rev 6, informational only): tier distribution. Tier 5/6 is
    # NOT expected to hit any particular share -- 5-6 simultaneous abnormal
    # vitals is combinatorially rare (measured near-0% even in a 450k-row
    # accumulated pool during development). This is printed for visibility,
    # not compared against a target.
    if "tier" in df.columns:
        tier_dist = df["tier"].value_counts(normalize=True).sort_index()
        print(f"\n  [check] Tier distribution:\n{tier_dist}")
        tier56_share = tier_dist.reindex([5, 6]).fillna(0).sum()
        print(f"  [check] Tier 5+6 combined = {tier56_share:.1%} (informational -- naturally rare, no target)")

    # Check 8 (Rev 6): glucose sparsity/realization sanity check
    if "glucose" in df.columns:
        glucose_notna_rate = df["glucose"].notna().mean()
        glucose_high_rows = df["abnormal_params"].fillna("").str.contains("glucose_high").sum()
        print(f"\n  [check] glucose non-null rate: {glucose_notna_rate:.1%}; "
              f"glucose_high rows: {glucose_high_rows}")
        if glucose_high_rows == 0:
            print(f"  [check] [!]  WARNING: zero glucose_high rows — biometrics.yml realization "
                  f"fix may not have taken effect, or MIN_GLUCOSE_HIGH_FLOOR wasn't met.")

    # Check 9 (Rev 6, warn only): age/sex distribution vs. reweighting target
    if "age_at_encounter" in df.columns and "sex" in df.columns:
        print("\n  [check] Age/sex distribution vs. target (Census 2011 approx):")
        for (lo, hi), age_share in config.TARGET_AGE_SEX_DISTRIBUTION.items():
            for sex, sex_share in config.TARGET_SEX_SHARE.items():
                target_pct = age_share * sex_share
                actual_pct = ((df["age_at_encounter"].between(lo, hi)) &
                              (df["sex"].astype(str).str.upper().str[0] == sex)).mean()
                diff = abs(actual_pct - target_pct)
                flag = "  [!]" if diff > 0.05 else ""
                print(f"    {lo:>2}-{hi:<2} {sex}: target={target_pct:.1%} actual={actual_pct:.1%}{flag}")

    if errors:
        print("\n  Spot check FAILURES:")
        for e in errors:
            print(f"    [X] {e}")
    else:
        print("  All spot checks passed [ok]")

    print("\n--- Final Validation Summary ---")
    print(f"Total Row Count: {len(df)}")
    
    under_18 = df[df["age_at_encounter"] < 18]
    print(f"\nAge Distribution:")
    print(df["age_at_encounter"].describe())
    print(f"Explicit Under-18 Count: {len(under_18)}")
    
    pediatric_drugs = under_18[(under_18["drug_name"].notna()) & (under_18["drug_name"] != "None")]
    if len(pediatric_drugs) > 0:
        raise AssertionError(f"HARD FAIL: {len(pediatric_drugs)} under-18 rows have a non-null drug_name.")
    else:
        print("Pediatric Drug Check: PASSED (0 under-18 rows have drugs).")
        
    print("\nICD Candidate Value Counts:")
    print(df["icd_candidate"].value_counts(dropna=False))
    
    print("\nAbnormal Params Value Counts:")
    print(df["abnormal_params"].value_counts(dropna=False))
    
    print("\nDrug Name cross-tabbed against ICD Candidate:")
    if "icd_candidate" in df.columns and "drug_name" in df.columns:
        print(pd.crosstab(df["drug_name"], df["icd_candidate"], dropna=False))



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DRISHTI Vitals Pipeline — master orchestration loop"
    )
    parser.add_argument("--target-rows", type=int, default=20000,
                        help="Target row count for canonical dataset (default: 20000)")
    parser.add_argument("--start-seed",  type=int, default=42,
                        help="Starting random seed (default: 42, increments each run)")
    parser.add_argument("--pop-per-run", type=int, default=500,
                        help="Synthea population per run (default: 500)")
    parser.add_argument("--noise-seed",  type=int, default=999,
                        help="Seed for noise injection (default: 999)")
    parser.add_argument("--spot-checks", action="store_true",
                        help="Run post-pipeline spot checks after completion")
    args = parser.parse_args()

    run_pipeline(
        target_rows=args.target_rows,
        start_seed=args.start_seed,
        pop_per_run=args.pop_per_run,
        noise_seed=args.noise_seed,
    )

    if args.spot_checks:
        run_spot_checks()
