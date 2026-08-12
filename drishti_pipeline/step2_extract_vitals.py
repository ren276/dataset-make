"""
drishti_pipeline/step2_extract_vitals.py
=========================================
Reads Synthea's observations.csv, extracts the 6 vital sign LOINC codes,
pivots to one row per (PATIENT, ENCOUNTER, DATE), joins with patients.csv
for age and sex, and filters to MIN_AGE ≤ age ≤ MAX_AGE.

Output: drishti_pipeline/scratch/vitals_raw_{seed}.csv

Column schema of output:
  patient_id, encounter_date, age_at_encounter, sex,
  bp_systolic, bp_diastolic, pulse, spo2, bmi, glucose
  (bmi and glucose may be NaN for some encounters — rows with NaN bmi/glucose
   are kept; all 6 vitals are NOT required, but rows with < 3 vitals are
   dropped. glucose is deliberately NOT imputed when missing -- see
   impute_missing_vitals -- it's an opportunistic lab, not a routine check.)

Usage (direct):
  python step2_extract_vitals.py --seed 42
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drishti_pipeline import config

# Minimum number of vitals required per row to keep it
MIN_VITALS_PER_ROW = 3


def load_observations() -> pd.DataFrame:
    obs_path = config.SYNTHEA_OUTPUT_DIR / "observations.csv"
    if not obs_path.exists():
        raise FileNotFoundError(f"observations.csv not found: {obs_path}")
    # Only load columns we need
    df = pd.read_csv(obs_path, usecols=["PATIENT", "ENCOUNTER", "DATE", "CODE", "VALUE"],
                     dtype={"CODE": str, "VALUE": str})
    return df


def load_patients() -> pd.DataFrame:
    pat_path = config.SYNTHEA_OUTPUT_DIR / "patients.csv"
    if not pat_path.exists():
        raise FileNotFoundError(f"patients.csv not found: {pat_path}")
    df = pd.read_csv(pat_path, usecols=["Id", "BIRTHDATE", "GENDER"],
                     dtype={"Id": str, "GENDER": str})
    df = df.rename(columns={"Id": "PATIENT", "BIRTHDATE": "birthdate", "GENDER": "sex"})
    df["birthdate"] = pd.to_datetime(df["birthdate"], errors="coerce")
    # Normalize sex to single char M/F
    df["sex"] = df["sex"].str.strip().str.upper().str[0]
    return df


def filter_vital_loincs(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows whose CODE is one of our 5 vital LOINC codes."""
    wanted = set(config.VITAL_LOINCS.keys())
    df = df[df["CODE"].isin(wanted)].copy()
    df["vital_name"] = df["CODE"].map(config.VITAL_LOINCS)
    df["value_num"] = pd.to_numeric(df["VALUE"], errors="coerce")
    return df


def pivot_vitals(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot so each encounter has one row with columns per vital."""
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce").dt.date
    pivot = df.pivot_table(
        index=["PATIENT", "ENCOUNTER", "DATE"],
        columns="vital_name",
        values="value_num",
        aggfunc="first",   # if duplicate LOINCs per encounter, take first
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={
        "PATIENT":   "patient_id",
        "ENCOUNTER": "encounter_id",
        "DATE":      "encounter_date",
    })
    # Ensure all vital columns exist even if no data
    for vital in ["bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi", "glucose"]:
        if vital not in pivot.columns:
            pivot[vital] = float("nan")
    return pivot


def compute_age(encounter_date, birthdate) -> int:
    """Compute age at encounter in whole years."""
    if pd.isnull(encounter_date) or pd.isnull(birthdate):
        return -1
    ed = pd.Timestamp(encounter_date)
    bd = pd.Timestamp(birthdate)
    age = (ed - bd).days // 365
    return int(age)


def join_patients(pivot: pd.DataFrame, patients: pd.DataFrame) -> pd.DataFrame:
    merged = pivot.merge(patients, on="PATIENT", how="left")
    merged = merged.rename(columns={"PATIENT": "patient_id_raw"})
    # Compute age
    merged["age_at_encounter"] = merged.apply(
        lambda r: compute_age(r["encounter_date"], r["birthdate"]), axis=1
    )
    # Drop helper columns
    merged = merged.drop(columns=["encounter_id", "patient_id_raw", "birthdate"], errors="ignore")
    # Reorder
    cols = ["patient_id", "encounter_date", "age_at_encounter", "sex",
            "bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi"]
    # patient_id column exists from pivot rename? Let's re-check
    if "patient_id" not in merged.columns:
        merged = merged.rename(columns={"PATIENT": "patient_id"})
    return merged[[c for c in cols if c in merged.columns]]


def filter_age(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to config.MIN_AGE ≤ age ≤ config.MAX_AGE."""
    before = len(df)
    df = df[(df["age_at_encounter"] >= config.MIN_AGE) &
            (df["age_at_encounter"] <= config.MAX_AGE)].copy()
    after = len(df)
    print(f"  [step2] Age filter ({config.MIN_AGE}–{config.MAX_AGE}): {before} -> {after} rows")
    return df


def drop_sparse_rows(df: pd.DataFrame, min_vitals: int = MIN_VITALS_PER_ROW) -> pd.DataFrame:
    """Drop rows where fewer than min_vitals of the 6 vital columns have data.

    MIN_VITALS_PER_ROW stays an absolute floor of 3, not scaled up for the
    6th (glucose) column -- glucose is the sparsest column by far (an
    opportunistic lab, not a routine check), so scaling the requirement up
    would start dropping otherwise-good BP/pulse/spo2/bmi rows purely for
    lacking a glucose reading.
    """
    vital_cols = ["bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi", "glucose"]
    available = [c for c in vital_cols if c in df.columns]
    vital_count = df[available].notna().sum(axis=1)
    before = len(df)
    df = df[vital_count >= min_vitals].copy()
    after = len(df)
    print(f"  [step2] Sparse-row drop (< {min_vitals} vitals): {before} -> {after} rows")
    return df


def impute_missing_vitals(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Impute missing SpO2 and Pulse with normal baseline values.

    Deliberately does NOT impute bmi or glucose -- both are opportunistic
    labs/measurements, not routine checks taken at every encounter.
    Fabricating a "normal" glucose reading for rows with no lab drawn would
    be more misleading than the spo2/pulse imputation below (those two are
    near-universal PHC vitals; glucose is not). This asymmetry is
    intentional -- do not "fix" it into consistency.
    """
    rng = np.random.RandomState(seed)
    
    if "spo2" in df.columns:
        null_mask = df["spo2"].isna()
        if null_mask.sum() > 0:
            df.loc[null_mask, "spo2"] = rng.uniform(95.0, 100.0, size=null_mask.sum())
            df["spo2"] = df["spo2"].round(1)
            
    if "pulse" in df.columns:
        null_mask = df["pulse"].isna()
        if null_mask.sum() > 0:
            df.loc[null_mask, "pulse"] = rng.uniform(60.0, 100.0, size=null_mask.sum())
            df["pulse"] = df["pulse"].round(1)
            
    return df



def run(seed: int) -> Path:
    """
    Full step2 pipeline. Returns path to vitals_raw_{seed}.csv.
    """
    print(f"  [step2] Extracting vitals for seed={seed}")
    obs = load_observations()
    patients = load_patients()

    vitals = filter_vital_loincs(obs)
    pivot = pivot_vitals(vitals)

    # patient_id came from pivot; need to re-join for age/sex
    # pivot has patient_id column; patients has PATIENT column
    pivot_for_join = pivot.rename(columns={"patient_id": "PATIENT"})
    merged = pivot_for_join.merge(patients, on="PATIENT", how="left")
    merged["age_at_encounter"] = merged.apply(
        lambda r: compute_age(r["encounter_date"], r["birthdate"]), axis=1
    )
    merged = merged.rename(columns={"PATIENT": "patient_id"})
    merged = merged.drop(columns=["encounter_id", "birthdate"], errors="ignore")

    # Reorder columns
    vital_cols = ["bp_systolic", "bp_diastolic", "pulse", "spo2", "bmi", "glucose"]
    base_cols = ["patient_id", "encounter_date", "age_at_encounter", "sex"]
    ordered = base_cols + [c for c in vital_cols if c in merged.columns]
    merged = merged[[c for c in ordered if c in merged.columns]]

    merged = filter_age(merged)
    merged = impute_missing_vitals(merged, seed=seed)
    merged = drop_sparse_rows(merged)

    if merged.empty:
        print(f"  [step2] WARNING: No usable rows after filtering for seed={seed}")

    # Write output
    config.PIPELINE_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PIPELINE_SCRATCH_DIR / f"vitals_raw_{seed}.csv"
    merged.to_csv(out_path, index=False)
    print(f"  [step2] Wrote {len(merged)} rows -> {out_path.name}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2: Extract vitals from Synthea output")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    run(seed=args.seed)
