"""
drishti_pipeline/step2b_demographic_reweight.py
=================================================
Post-hoc demographic reweighting (Rev 6).

Synthea's default demographic generator draws age/sex from a US-pattern
distribution (merely clipped to config.MIN_AGE-MAX_AGE via step1's -a flag).
No India demographics/geography module exists in synthea-international/in
(only biometrics.yml, which recalibrates vital/lab RANGES conditioned on
age/sex, not the age/sex draw itself). This step resamples the ACCUMULATED
pool of scratch/vitals_raw_*.csv files to approximate a target Indian
age-sex distribution (see config.TARGET_AGE_SEX_DISTRIBUTION /
config.TARGET_SEX_SHARE, both approximate Census 2011-derived figures).

Operates on the accumulated pool across many Synthea seeds, not per-pass --
a single ~500-row pass has too few rows per age-decade x sex cell to
resample meaningfully without excessive with-replacement duplication.

Usage (direct):
  python step2b_demographic_reweight.py --pool-size 100000 --seed 7
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drishti_pipeline import config


def load_accumulated_pool() -> pd.DataFrame:
    """Concatenate all scratch/vitals_raw_*.csv files into one pool."""
    paths = sorted(config.PIPELINE_SCRATCH_DIR.glob("vitals_raw_*.csv"))
    if not paths:
        raise FileNotFoundError(
            f"No vitals_raw_*.csv files found in {config.PIPELINE_SCRATCH_DIR} "
            "-- run step1+step2 accumulation first"
        )
    frames = [pd.read_csv(p, dtype={"patient_id": str, "sex": str}) for p in paths]
    pool = pd.concat(frames, ignore_index=True)
    print(f"  [step2b] Loaded accumulated pool: {len(pool)} rows from {len(paths)} files")
    return pool


def _age_band(age) -> tuple:
    """Map an age to its (lo, hi) band key in config.TARGET_AGE_SEX_DISTRIBUTION."""
    bands = list(config.TARGET_AGE_SEX_DISTRIBUTION.keys())
    for (lo, hi) in bands:
        if lo <= age <= hi:
            return (lo, hi)
    # Defensive clamp -- shouldn't trigger since step2 already filters to
    # config.MIN_AGE..MAX_AGE, which the bands fully cover.
    return bands[0] if age < bands[0][0] else bands[-1]


def reweight(pool: pd.DataFrame, pool_size: int, seed: int) -> pd.DataFrame:
    """
    Resample `pool` to ~pool_size rows matching
    config.TARGET_AGE_SEX_DISTRIBUTION x config.TARGET_SEX_SHARE.
    Cells with fewer natural rows than their target are resampled WITH
    replacement (flagged in the printed report); cells with more are
    downsampled without replacement.
    """
    df = pool.copy()
    df["_age_band"] = df["age_at_encounter"].apply(_age_band)
    df["sex"] = df["sex"].astype(str).str.upper().str[0]

    rng = np.random.default_rng(seed)
    parts = []
    report_rows = []

    for band, age_share in config.TARGET_AGE_SEX_DISTRIBUTION.items():
        for sex, sex_share in config.TARGET_SEX_SHARE.items():
            cell_target = round(pool_size * age_share * sex_share)
            cell_pool = df[(df["_age_band"] == band) & (df["sex"] == sex)]
            natural_n = len(cell_pool)

            if natural_n == 0 or cell_target == 0:
                report_rows.append((band, sex, natural_n, cell_target, "NO DONOR ROWS — skipped" if natural_n == 0 else "zero target"))
                continue

            replace = natural_n < cell_target
            sampled = cell_pool.sample(
                n=cell_target, replace=replace, random_state=int(rng.integers(0, 2**31 - 1))
            )
            parts.append(sampled)
            note = f"resampled WITH replacement ({natural_n} -> {cell_target})" if replace else "downsampled"
            report_rows.append((band, sex, natural_n, cell_target, note))

    result = pd.concat(parts, ignore_index=True) if parts else df.head(0)
    result = result.drop(columns=["_age_band"], errors="ignore")

    print("\n  [step2b] Demographic reweighting report (age-band, sex, natural_n -> target_n):")
    for band, sex, natural_n, target_n, note in report_rows:
        print(f"    {band[0]:>2}-{band[1]:<2} {sex}: natural={natural_n:>6} target={target_n:>6}  {note}")

    print(f"\n  [step2b] Before: {len(pool)} rows -> After reweighting: {len(result)} rows")
    return result


def run(pool_size: int, seed: int = 7) -> Path:
    pool = load_accumulated_pool()
    reweighted = reweight(pool, pool_size, seed)

    config.PIPELINE_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PIPELINE_SCRATCH_DIR / "vitals_pool_reweighted.csv"
    reweighted.to_csv(out_path, index=False)
    print(f"  [step2b] Wrote {len(reweighted)} rows -> {out_path.name}")
    return out_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Step 2b: Demographic reweighting")
    parser.add_argument("--pool-size", type=int, required=True,
                        help="Target row count of the reweighted pool")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    run(pool_size=args.pool_size, seed=args.seed)
