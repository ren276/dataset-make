"""
drishti_pipeline/step3_tiered_generator.py
===========================================
Assesses vitals against Indian thresholds, assigns tier (1-6), and adds
ICD-10 hierarchy + differential columns.

Abnormality assessment:
  - bp_systolic, bp_diastolic: age-gated (Narang formula for <18, IHCI for ≥18)
  - spo2:     low if < 95%
  - bmi:      high if ≥ 23 (adults only; "not_assessed" for age < 18 per B2)
  - pulse:    "pulse_high" if > 100 bpm, "pulse_low" if < 60 bpm
  - glucose:  "glucose_high" if ≥ 140 mg/dL random/non-fasting (no age-gating)
  - fever_pattern: synthetic epidemiological routing signal (not a measured
    vital), excluded from tier/_param_count -- see config.assess_fever_pattern

Tier assignment (Rev 6, global targets — see run_global()):
  - Tier 1-6: exactly N abnormal params (of bp_systolic, bp_diastolic,
    pulse_high|low, bmi, glucose_high, spo2), balanced-sampled down to
    config.GLOBAL_TIER_TARGET_RATIOS × target_rows across the WHOLE pool,
    not per-Synthea-pass quotas.

Output adds columns: tier, abnormal_params, fever_pattern_flag, icd_chapter,
                     icd_block, icd_candidate, differential_candidates
(symptom_string and symptom_signal_strength added in step4)

Two entry points:
  - run(seed): standalone/smoke-test path, operates on a single seed's
    vitals_raw_{seed}.csv, keeps all rows per tier uncapped (no quota).
  - run_global(input_path, target_rows): production path, operates on the
    full demographic-reweighted pool once, applies global tier ratios.
"""

import sys
from pathlib import Path
from itertools import combinations
from typing import List, Set

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drishti_pipeline import config


# ---------------------------------------------------------------------------
# Abnormality assessment
# ---------------------------------------------------------------------------

def assess_row(row: pd.Series) -> List[str]:
    """
    Return a sorted list of abnormal parameter names for a single row.
    Pediatric BMI (age < 18) -> "bmi_not_assessed" is noted but not included
    in abnormal_params (B2 strategy).
    """
    age = int(row.get("age_at_encounter", 18))
    sex = str(row.get("sex", "M")).strip().upper()
    if not sex or sex[0] not in ("M", "F"):
        sex = "M"

    abnormal = []
    thresholds = config.get_bp_threshold(age, sex)

    # BP systolic
    sbp = row.get("bp_systolic")
    if pd.notna(sbp) and sbp >= thresholds["sbp"]:
        abnormal.append("bp_systolic")

    # BP diastolic
    dbp = row.get("bp_diastolic")
    if pd.notna(dbp) and dbp >= thresholds["dbp"]:
        abnormal.append("bp_diastolic")

    # SpO2
    spo2 = row.get("spo2")
    if pd.notna(spo2) and spo2 < config.ADULT_THRESHOLDS["spo2"]["normal_min"]:
        abnormal.append("spo2")

    # BMI — B2: skip for pediatric
    bmi = row.get("bmi")
    if age >= 18:
        if pd.notna(bmi) and bmi >= config.ADULT_THRESHOLDS["bmi"]["overweight_min"]:
            abnormal.append("bmi")
    # else: B2 — bmi assessment deferred, not added to abnormal list

    # Pulse direction
    pulse = row.get("pulse")
    if pd.notna(pulse):
        if pulse > config.ADULT_THRESHOLDS["pulse"]["normal_max"]:
            abnormal.append("pulse_high")
        elif pulse < config.ADULT_THRESHOLDS["pulse"]["normal_min"]:
            abnormal.append("pulse_low")

    # Glucose (random/non-fasting) — no age-gating, sparse/nullable like bmi
    glucose = row.get("glucose")
    if pd.notna(glucose) and glucose >= config.ADULT_THRESHOLDS["glucose"]["prediabetes_min"]:
        abnormal.append("glucose_high")

    # fever_pattern: synthetic epidemiological routing signal, NOT a measured
    # vital. Deliberately appended after all real vitals and excluded from
    # _param_count (see assess_dataframe) -- tier reflects physiological
    # derangement severity only.
    patient_id = str(row.get("patient_id", ""))
    encounter_date = str(row.get("encounter_date", ""))
    if config.assess_fever_pattern(patient_id, encounter_date):
        abnormal.append("fever_pattern")

    return sorted(abnormal)


# Abnormal-param names that count toward tier/_param_count (physiological
# derangement axes). fever_pattern is excluded -- it's an epidemiological
# routing signal used only for ICD/symptom resolution.
TIER_COUNTING_PARAMS = {
    "bp_systolic", "bp_diastolic", "pulse_high", "pulse_low", "bmi", "glucose_high", "spo2",
}


def assess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add abnormal_params column (comma-separated sorted string) and param_count."""
    df = df.copy()
    abnormal_lists = df.apply(assess_row, axis=1)
    df["_abnormal_list"] = abnormal_lists
    df["abnormal_params"] = abnormal_lists.apply(
        lambda lst: ",".join(lst) if lst else "normal"
    )
    # _param_count drives the TIER NUMBER and excludes fever_pattern
    # (epidemiological routing signal, not a physiological derangement axis).
    df["_param_count"] = abnormal_lists.apply(
        lambda lst: sum(1 for p in lst if p in TIER_COUNTING_PARAMS)
    )
    df["fever_pattern_flag"] = abnormal_lists.apply(lambda lst: "fever_pattern" in lst)

    # _tier_bucket drives which rows ENTER tiering.
    # We now use a collapsed 4-tier schema reflecting the realistic 
    # distribution of abnormal vitals natively generated by Synthea in
    # ambulatory PHC contexts:
    # Tier 1 = 0 abnormal params
    # Tier 2 = 1 abnormal param
    # Tier 3 = 2 abnormal params
    # Tier 4 = 3+ abnormal params (High Acuity)
    df["_tier_bucket"] = df["_param_count"].apply(
        lambda x: min(4, x + 1)
    )

    # For pediatric rows, mark bmi as not_assessed in a separate annotation
    df["_bmi_assessed"] = df["age_at_encounter"].apply(lambda a: a >= 18)
    return df


# ---------------------------------------------------------------------------
# ICD / label enrichment
# ---------------------------------------------------------------------------

def add_icd_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add icd_chapter, icd_block, icd_candidate, differential_candidates columns.

    Rev 6: uses config.resolve_condition() -- the same deterministic resolver
    step4 calls for symptom/drug sampling -- instead of the old sequential-RNG
    monsoon promotion (which almost never fired: rare abnormal-param combo AND
    monsoon month AND a 60% roll, all in series). Same (abnormal_params,
    patient_id, encounter_date) always resolves to the same condition in both
    steps, so labels and symptoms/drugs never disagree.
    """
    df = df.copy()

    icd_chapters = []
    icd_blocks = []
    icd_candidates = []
    differentials = []

    for _, row in df.iterrows():
        abn_list = row["_abnormal_list"]
        abn_set = frozenset(abn_list) if abn_list else frozenset()
        resolved = config.resolve_condition(
            abn_set, str(row.get("patient_id", "")), str(row.get("encounter_date", ""))
        )

        icd_chapters.append(resolved.get("icd_chapter"))
        icd_blocks.append(resolved.get("icd_block"))
        icd_candidates.append(resolved.get("icd_candidate"))
        differentials.append("|".join(resolved.get("differential_candidates", [])))

    df["icd_chapter"] = icd_chapters
    df["icd_block"] = icd_blocks
    df["icd_candidate"] = icd_candidates
    df["differential_candidates"] = differentials
    return df


# ---------------------------------------------------------------------------
# Tier construction helpers
# ---------------------------------------------------------------------------

def _balanced_sample(df: pd.DataFrame, target_count: int, group_col: str,
                     seed: int) -> pd.DataFrame:
    """
    Sample target_count rows from df, balanced across unique values of group_col.
    If a group has fewer rows than its quota, takes all available.
    """
    groups = df[group_col].unique()
    n_groups = len(groups)
    if n_groups == 0:
        return df.head(0)
    quota_per_group = max(1, target_count // n_groups)
    parts = []
    for g in groups:
        subset = df[df[group_col] == g]
        take = min(len(subset), quota_per_group)
        parts.append(subset.sample(n=take, random_state=seed))
    result = pd.concat(parts, ignore_index=True)
    # If we're under target (because some groups were small), top-up from remainder
    if len(result) < target_count:
        used_idx = result.index
        remaining = df[~df.index.isin(used_idx)]
        shortfall = target_count - len(result)
        extra = remaining.sample(n=min(shortfall, len(remaining)), random_state=seed)
        result = pd.concat([result, extra], ignore_index=True)
    return result.head(target_count)


def build_tiers(df: pd.DataFrame, seed: int, target_counts: dict = None) -> pd.DataFrame:
    """
    Partition df into Tiers 1-4 by exact _tier_bucket.

    If target_counts is given ({tier_n: count}), each tier is balanced-
    sampled down to that count (used by run_global() with
    config.GLOBAL_TIER_TARGET_RATIOS applied across the whole pool). If a
    tier's natural pool is smaller than its target, all available rows are
    kept (no padding/fabrication).

    If target_counts is None, ALL rows in each tier are kept uncapped (used
    by the standalone per-seed run() path for dev/smoke-testing only).

    Returns a DataFrame with a 'tier' column added.
    """
    tier_frames = []

    for tier_n in range(1, 5):
        pool = df[df["_tier_bucket"] == tier_n].copy()
        if pool.empty:
            print(f"  [step3] Tier {tier_n}: pool empty — skipped")
            continue

        target = target_counts.get(tier_n) if target_counts else None
        if target is not None and len(pool) > target:
            sampled = _balanced_sample(pool, target, "abnormal_params", seed)
        else:
            sampled = pool

        sampled = sampled.copy()
        sampled["tier"] = tier_n
        tier_frames.append(sampled)
        target_note = f", target={target}" if target is not None else " (uncapped)"
        print(f"  [step3] Tier {tier_n}: {len(sampled)} records (pool={len(pool)}{target_note})")

    if not tier_frames:
        return pd.DataFrame()

    result = pd.concat(tier_frames, ignore_index=True)
    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(seed: int) -> pd.DataFrame:
    """
    Full step3: read vitals_raw, assess thresholds, tier, add ICD labels.
    Returns DataFrame with tier + ICD columns added.
    Writes tiered_{seed}.csv to scratch.
    """
    input_path = config.PIPELINE_SCRATCH_DIR / f"vitals_raw_{seed}.csv"
    if not input_path.exists():
        raise FileNotFoundError(f"vitals_raw_{seed}.csv not found — run step2 first")

    df = pd.read_csv(input_path, dtype={"patient_id": str, "sex": str})
    print(f"  [step3] Loaded {len(df)} rows from vitals_raw_{seed}.csv")

    df = assess_dataframe(df)

    normal_count = (df["_param_count"] == 0).sum()
    breakdown = ", ".join(f"{n}-param={(df['_param_count'] == n).sum()}" for n in range(1, 7))
    print(f"  [step3] Abnormality breakdown: normal={normal_count}, {breakdown}")

    # Exclude fully normal rows from tiering (a row counts as non-normal if
    # it has a real abnormal vital OR fever_pattern alone -- see _tier_bucket)
    abnormal_df = df[df["_tier_bucket"] >= 1].copy()
    tiered = build_tiers(abnormal_df, seed)

    if tiered.empty:
        print(f"  [step3] WARNING: No tiered records for seed={seed}")
        return pd.DataFrame()

    tiered = add_icd_labels(tiered)

    # Drop internal helper columns
    drop_cols = ["_abnormal_list", "_param_count", "_tier_bucket", "_bmi_assessed"]
    tiered = tiered.drop(columns=[c for c in drop_cols if c in tiered.columns])

    # Write to scratch
    config.PIPELINE_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PIPELINE_SCRATCH_DIR / f"tiered_{seed}.csv"
    tiered.to_csv(out_path, index=False)
    print(f"  [step3] Wrote {len(tiered)} tiered rows -> {out_path.name}")
    return tiered


def run_global(input_path, target_rows: int, seed: int = 0) -> pd.DataFrame:
    """
    Rev 6 production entry point: reads the FULL demographic-reweighted pool
    in one shot and assesses/tiers/labels it ONCE, applying
    config.GLOBAL_TIER_TARGET_RATIOS × target_rows as per-tier quotas instead
    of the old per-Synthea-pass TIER1_COUNT/TIER2_COUNT/TIER3_COUNT (which
    accumulated inconsistently across many passes). Writes tiered_global.csv
    to scratch.
    """
    input_path = Path(input_path)
    df = pd.read_csv(input_path, dtype={"patient_id": str, "sex": str})
    print(f"  [step3] Loaded {len(df)} rows from {input_path.name}")

    df = assess_dataframe(df)

    normal_count = (df["_param_count"] == 0).sum()
    breakdown = ", ".join(f"{n}-param={(df['_param_count'] == n).sum()}" for n in range(1, 7))
    print(f"  [step3] Abnormality breakdown: normal={normal_count}, {breakdown}")
    print(f"  [step3] glucose_high rows: {df['abnormal_params'].str.contains('glucose_high').sum()}")
    print(f"  [step3] fever_pattern rows: {df['fever_pattern_flag'].sum()}")

    abnormal_df = df[df["_tier_bucket"] >= 1].copy()

    target_counts = {
        n: round(ratio * target_rows) for n, ratio in config.GLOBAL_TIER_TARGET_RATIOS.items()
    }
    tiered = build_tiers(abnormal_df, seed, target_counts=target_counts)

    if tiered.empty:
        print("  [step3] WARNING: No tiered records in global pool")
        return pd.DataFrame()

    tiered = add_icd_labels(tiered)

    drop_cols = ["_abnormal_list", "_param_count", "_tier_bucket", "_bmi_assessed"]
    tiered = tiered.drop(columns=[c for c in drop_cols if c in tiered.columns])

    config.PIPELINE_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PIPELINE_SCRATCH_DIR / "tiered_global.csv"
    tiered.to_csv(out_path, index=False)
    print(f"  [step3] Wrote {len(tiered)} tiered rows -> {out_path.name}")
    return tiered


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Step 3: Tiered generator + ICD labeling")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    run(seed=args.seed)
