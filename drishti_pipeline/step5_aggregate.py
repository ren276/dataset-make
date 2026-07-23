"""
drishti_pipeline/step5_aggregate.py
=====================================
Merges the current pass's tiered+symptom DataFrame into the running
canonical_dataset.csv.

Operations per call:
  1. Adds synthetic=True and source="synthea_india" columns
  2. Enforces canonical column order and types
  3. Deduplicates on (patient_id, encounter_date)
  4. Validates non-nullable columns
  5. Validates icd_candidate is null or non-empty string (no empty-string sentinels)
  6. Validates symptom_signal_strength enum
  7. Appends to / creates canonical_dataset.csv
  8. Reports icd_candidate null rate

ISO 14971 / SaMD schema note:
  icd_chapter, icd_block, icd_candidate, and symptom_signal_strength are
  kept as distinct queryable columns (not collapsed) to support H-01–H-10
  risk documentation: a chapter-only + nonspecific record is a materially
  different risk case from a block-level + strong-support record.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drishti_pipeline import config

CANONICAL_PATH = config.DATASET_OUTPUT_DIR / "canonical_dataset.csv"

# Non-nullable columns — these must be present and non-null on every row
NON_NULLABLE = [
    "patient_id", "encounter_date", "age_at_encounter", "sex",
    "bp_systolic", "bp_diastolic", "pulse", "spo2",
    "tier", "abnormal_params", "fever_pattern_flag",
    "symptom_string", "symptom_signal_strength",
    "drug_name", "drug_dosage", "pediatric_referral_flag",
    "icd_chapter", "icd_block", "differential_candidates",
    "synthetic", "source",
]
# Note: bmi, glucose, and icd_candidate are nullable (bmi/glucose may be NaN
#       for some encounters — both are opportunistic labs, not routine
#       checks; icd_candidate is intentionally null where the combination
#       doesn't narrow below block level)


def add_synthetic_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["synthetic"] = True
    df["source"] = "synthea_india"
    return df


def enforce_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce canonical column order and coerce types.
    Missing columns are added with appropriate null values.
    """
    df = df.copy()

    # Ensure all canonical columns exist
    for col in config.CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Reorder to canonical column order
    df = df[[c for c in config.CANONICAL_COLUMNS if c in df.columns]]

    # Type coercions (best-effort)
    int_cols = ["age_at_encounter", "tier"]
    float_cols = ["bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi", "glucose"]
    str_cols = ["patient_id", "encounter_date", "sex", "abnormal_params",
                "symptom_string", "symptom_signal_strength", "drug_name", "drug_dosage",
                "icd_chapter", "icd_block", "differential_candidates", "source"]

    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int32")
    for c in float_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    for c in str_cols:
        if c in df.columns:
            df[c] = df[c].astype(str)
            
    if "pediatric_referral_flag" in df.columns:
        df["pediatric_referral_flag"] = df["pediatric_referral_flag"].astype(bool)

    if "fever_pattern_flag" in df.columns:
        df["fever_pattern_flag"] = df["fever_pattern_flag"].astype(bool)

    # icd_candidate: keep as object (nullable string)
    if "icd_candidate" in df.columns:
        df["icd_candidate"] = df["icd_candidate"].where(
            df["icd_candidate"].notna() & (df["icd_candidate"] != "None") & (df["icd_candidate"] != ""),
            other=None
        )

    return df


def validate(df: pd.DataFrame) -> list:
    """
    Run schema assertions. Returns list of error messages (empty = all clear).
    """
    errors = []

    # 1. Non-nullable columns
    for col in NON_NULLABLE:
        if col not in df.columns:
            errors.append(f"MISSING COLUMN: {col}")
            continue
        null_count = df[col].isna().sum()
        if null_count > 0:
            errors.append(f"NULL VALUES in non-nullable '{col}': {null_count} rows")

    # 2. icd_candidate: must be null or non-empty string (no empty string sentinels)
    if "icd_candidate" in df.columns:
        empty_sentinel = df["icd_candidate"].apply(
            lambda x: x == "" if isinstance(x, str) else False
        ).sum()
        if empty_sentinel > 0:
            errors.append(f"EMPTY STRING in icd_candidate: {empty_sentinel} rows — use None/NaN")

    # 3. symptom_signal_strength enum
    if "symptom_signal_strength" in df.columns:
        invalid = ~df["symptom_signal_strength"].isin(config.VALID_SIGNAL_STRENGTHS)
        if invalid.sum() > 0:
            errors.append(f"INVALID symptom_signal_strength: {invalid.sum()} rows")

    # 4. Vital columns — no all-null rows across all 6 vitals
    vital_cols = [c for c in ["bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi", "glucose"]
                  if c in df.columns]
    all_null_vitals = df[vital_cols].isna().all(axis=1).sum()
    if all_null_vitals > 0:
        errors.append(f"ALL-NULL VITAL ROWS: {all_null_vitals}")

    # 5. Confirm single output — no per-condition file splits
    # (this is enforced structurally; just note it in validation output)
    # No check needed — the output is always canonical_dataset.csv

    return errors


def report_icd_candidate_nulls(df: pd.DataFrame):
    """Print icd_candidate null rate and alert if outside expected range."""
    if "icd_candidate" not in df.columns:
        return
    total = len(df)
    null_count = df["icd_candidate"].isna().sum()
    null_rate = null_count / total if total > 0 else 0
    print(f"  [step5] icd_candidate null rate: {null_count}/{total} = {null_rate:.1%}")
    if null_rate < 0.10:
        print("  [step5] [!]  ALERT: icd_candidate null rate < 10% — suspicious over-precision. "
              "Review ICD mapping table.")
    elif null_rate > 0.90:
        print("  [step5] [!]  ALERT: icd_candidate null rate > 90% — suspicious under-specificity. "
              "Review ICD mapping table.")
    else:
        print(f"  [step5] [ok]  icd_candidate null rate in expected range (10–90%).")


def run(new_rows_df: pd.DataFrame) -> pd.DataFrame:
    """
    Append new_rows_df to canonical_dataset.csv. Returns the full canonical DataFrame.
    """
    print(f"  [step5] Aggregating {len(new_rows_df)} new rows into canonical dataset")

    df = add_synthetic_flags(new_rows_df)
    df = enforce_schema(df)

    # Load existing canonical if it exists, else start fresh
    if CANONICAL_PATH.exists():
        existing = pd.read_csv(CANONICAL_PATH, dtype=str, keep_default_na=False)
        # Re-apply enforce_schema on existing to fix types after reading all as str
        existing = enforce_schema(existing)
        canonical = pd.concat([existing, df], ignore_index=True)
    else:
        config.DATASET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        canonical = df

    # Deduplicate on (patient_id, encounter_date)
    before_dedup = len(canonical)
    canonical = canonical.drop_duplicates(subset=["patient_id", "encounter_date"], keep="first")
    after_dedup = len(canonical)
    if before_dedup != after_dedup:
        print(f"  [step5] Deduplication: {before_dedup} -> {after_dedup} rows "
              f"({before_dedup - after_dedup} duplicates removed)")

    # Validate
    errors = validate(canonical)
    if errors:
        for e in errors:
            print(f"  [step5] [X] VALIDATION ERROR: {e}", file=sys.stderr)
    else:
        print(f"  [step5] [ok]  Schema validation passed")

    # Report icd_candidate null rate
    report_icd_candidate_nulls(canonical)

    # Hard-fail check for pediatric dosing rule (Safety Fix)
    pediatric_violations = canonical[(canonical["age_at_encounter"] < 18) & (canonical["drug_name"].notna()) & (canonical["drug_name"] != "None")]
    if len(pediatric_violations) > 0:
        raise AssertionError(f"Pediatric drug dosing violation detected! {len(pediatric_violations)} rows have a drug assigned.")

    # Write canonical
    canonical.to_csv(CANONICAL_PATH, index=False)
    print(f"  [step5] Canonical dataset: {len(canonical)} total rows -> {CANONICAL_PATH.name}")
    return canonical


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Step 5: Aggregate to canonical dataset")
    parser.add_argument("--seed", type=int, required=True,
                        help="Seed used in previous steps (to load the right scratch file)")
    args = parser.parse_args()

    input_path = config.PIPELINE_SCRATCH_DIR / f"tiered_with_symptoms_{args.seed}.csv"
    if not input_path.exists():
        print(f"ERROR: tiered_with_symptoms_{args.seed}.csv not found", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(input_path, dtype={"patient_id": str})
    run(df)
