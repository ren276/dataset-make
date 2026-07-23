"""
drishti_pipeline/step6_noise_injection.py
==========================================
Final post-aggregation step. Applies controlled Gaussian noise to the
canonical dataset AFTER all tiering and labeling is complete.

CRITICAL DESIGN NOTE:
  Noise is applied AFTER labels are assigned. The abnormal_params, icd_*,
  and symptom_signal_strength columns are based on pre-noise values and
  are NOT recalculated post-noise. This is intentional — labels reflect
  structured generation intent, not the jittered output. The prenoise backup
  (canonical_dataset_prenoise.csv) captures the clean pre-noise state.

Noise parameters (from config.NOISE_PARAMS — see that dict for the current
authoritative values/rationale; do not duplicate exact numbers here, they
have drifted out of sync with config.py before):
  - BP systolic/diastolic, pulse, BMI, SpO2, glucose — each has its own
    sigma/clip/floor(/ceil) approximating PHC-level measurement error.

Outputs:
  - canonical_dataset_prenoise.csv  (never overwritten if it exists)
  - canonical_dataset.csv           (overwritten with post-noise values)
  - noise_log.json                  (noise seed + parameters for reproducibility)
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drishti_pipeline import config

CANONICAL_PATH         = config.DATASET_OUTPUT_DIR / "canonical_dataset.csv"
PRENOISE_PATH          = config.DATASET_OUTPUT_DIR / "canonical_dataset_prenoise.csv"
NOISE_LOG_PATH         = config.DATASET_OUTPUT_DIR / "noise_log.json"


def apply_noise(df: pd.DataFrame, noise_seed: int) -> pd.DataFrame:
    """
    Apply Gaussian noise to vital columns per config.NOISE_PARAMS.
    Returns a new DataFrame with noised values.
    """
    rng = np.random.default_rng(noise_seed)
    df = df.copy()

    for col, params in config.NOISE_PARAMS.items():
        if col not in df.columns:
            continue
        sigma     = params["sigma"]
        clip      = params["clip"]
        floor_val = params.get("floor", None)
        ceil_val  = params.get("ceil", None)

        original = df[col].copy().astype(float)
        noise    = rng.normal(0.0, sigma, size=len(df))
        noise    = np.clip(noise, -clip, clip)

        noised = original + noise

        if floor_val is not None:
            noised = np.maximum(noised, floor_val)
        if ceil_val is not None:
            noised = np.minimum(noised, ceil_val)

        # Only update non-NaN rows
        mask = original.notna()
        obs_col = col + "_observed"
        df.loc[mask, obs_col] = noised[mask].astype("float32")

    return df


def write_noise_log(noise_seed: int, row_count: int):
    """Write noise parameters to noise_log.json for reproducibility."""
    log = {
        "noise_seed": noise_seed,
        "applied_at": datetime.utcnow().isoformat() + "Z",
        "row_count": row_count,
        "note": (
            "Noise applied AFTER tiering/labeling. Labels (abnormal_params, icd_*, "
            "symptom_signal_strength) are based on pre-noise values and not recalculated. "
            "Observed noised values are written to _observed columns."
        ),
        "params": {
            col: {k: v for k, v in p.items()}
            for col, p in config.NOISE_PARAMS.items()
        },
    }
    with open(NOISE_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)
    print(f"  [step6] Noise log written -> {NOISE_LOG_PATH.name}")


def get_bp_grades(sys, dia):
    s_grade = np.zeros(len(sys), dtype=int)
    s_grade = np.where((sys >= 130) & (sys < 140), 1, s_grade)
    s_grade = np.where((sys >= 140) & (sys < 160), 2, s_grade)
    s_grade = np.where(sys >= 160, 3, s_grade)
    
    d_grade = np.zeros(len(dia), dtype=int)
    d_grade = np.where((dia >= 85) & (dia < 90), 1, d_grade)
    d_grade = np.where((dia >= 90) & (dia < 100), 2, d_grade)
    d_grade = np.where(dia >= 100, 3, d_grade)
    
    return np.maximum(s_grade, d_grade)


def get_bmi_grades(bmi):
    grade = np.zeros(len(bmi), dtype=int)
    grade = np.where((bmi >= 23.0) & (bmi < 25.0), 1, grade)
    grade = np.where(bmi >= 25.0, 2, grade)
    return grade


def run(noise_seed: int = 999) -> pd.DataFrame:
    """
    Full step6:
      1. Load canonical_dataset.csv
      2. Save prenoise backup (first time only — never overwrite)
      3. Apply noise
      4. Write noise_log.json
      5. Overwrite canonical_dataset.csv with noised values
      Returns the post-noise DataFrame.
    """
    if not CANONICAL_PATH.exists():
        raise FileNotFoundError(f"canonical_dataset.csv not found — run steps 1–5 first")

    df = pd.read_csv(CANONICAL_PATH, dtype={"patient_id": str})
    print(f"  [step6] Loaded {len(df)} rows from canonical_dataset.csv")

    # Save prenoise backup — NEVER overwrite existing prenoise
    if PRENOISE_PATH.exists():
        print(f"  [step6] Prenoise backup already exists ({PRENOISE_PATH.name}) — not overwriting.")
    else:
        df.to_csv(PRENOISE_PATH, index=False)
        print(f"  [step6] Prenoise backup saved -> {PRENOISE_PATH.name}")

    # Verify prenoise row count matches current canonical
    if PRENOISE_PATH.exists():
        prenoise_count = sum(1 for _ in open(PRENOISE_PATH)) - 1  # subtract header
        if prenoise_count != len(df):
            print(f"  [step6] [!]  WARNING: prenoise row count ({prenoise_count}) != "
                  f"canonical row count ({len(df)}) — did canonical grow after first noise run?",
                  file=sys.stderr)

    # Apply noise
    noised = apply_noise(df, noise_seed)

    # Write noise log
    write_noise_log(noise_seed, len(noised))

    # Output validation metrics
    print("\n  [step6] Validation: Observed Noise Standard Deviation (observed - true)")
    for col in config.NOISE_PARAMS:
        obs_col = col + "_observed"
        if col in noised.columns and obs_col in noised.columns:
            mask = noised[col].notna() & noised[obs_col].notna()
            if mask.sum() > 0:
                diff = noised.loc[mask, obs_col] - noised.loc[mask, col]
                print(f"    - {col}: SD = {diff.std():.3f} (target: {config.NOISE_PARAMS[col]['sigma']})")

    adults_mask = (df["age_at_encounter"] >= 18)
    adults = noised[adults_mask]
    if len(adults) > 0:
        print("\n  [step6] Validation: Classification Flips Due to Noise (Adults Only)")
        
        # BP flips
        bp_mask = adults["bp_systolic"].notna() & adults["bp_diastolic"].notna() & adults["bp_systolic_observed"].notna() & adults["bp_diastolic_observed"].notna()
        if bp_mask.sum() > 0:
            true_bp = get_bp_grades(adults.loc[bp_mask, "bp_systolic"].values, adults.loc[bp_mask, "bp_diastolic"].values)
            obs_bp = get_bp_grades(adults.loc[bp_mask, "bp_systolic_observed"].values, adults.loc[bp_mask, "bp_diastolic_observed"].values)
            flips = (true_bp != obs_bp).sum()
            total = bp_mask.sum()
            print(f"    - BP Classification (IHCI) changed in {flips}/{total} adult rows ({flips/total:.1%})")
            
        # BMI flips
        bmi_mask = adults["bmi"].notna() & adults["bmi_observed"].notna()
        if bmi_mask.sum() > 0:
            true_bmi = get_bmi_grades(adults.loc[bmi_mask, "bmi"].values)
            obs_bmi = get_bmi_grades(adults.loc[bmi_mask, "bmi_observed"].values)
            flips = (true_bmi != obs_bmi).sum()
            total = bmi_mask.sum()
            print(f"    - BMI Classification (WHO-Asian) changed in {flips}/{total} adult rows ({flips/total:.1%})")

    # Overwrite canonical with noised values (now includes _observed columns)
    noised.to_csv(CANONICAL_PATH, index=False)
    print(f"\n  [step6] Noise applied (seed={noise_seed}) -> canonical_dataset.csv overwritten with _observed columns")
    print(f"  [step6] Row count check: {len(df)} (pre-noise) == {len(noised)} (post-noise): "
          f"{'[ok]' if len(df) == len(noised) else '[X] MISMATCH'}")
    return noised


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Step 6: Noise injection (run once at end)")
    parser.add_argument("--noise-seed", type=int, default=999,
                        help="Seed for Gaussian noise RNG (default: 999)")
    args = parser.parse_args()
    run(noise_seed=args.noise_seed)
