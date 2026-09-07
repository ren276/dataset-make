"""
drishti_v2/run_generation.py
===============================
CLI entry point. Generates the corpus, runs the eight build gates, and
writes the corpus + manifest ONLY if every gate passes. On any gate failure,
nothing is written (dataset-regeneration-design-memo.md section 7.5) and the
process exits non-zero with the gate detail printed.

Usage:
    python -m drishti_v2.run_generation --n-rows 23000 --out-dir drishti_v2_output
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

from .gates import run_all_gates
from .generate import SPECS, generate_rows
from .manifest import build_manifest, write_manifest
from .perturbation import build_perturbation_set

GENERATOR_COMMIT = "drishti_v2-build-2"
ANSWER_MODEL_VERSION = "answer_model-0.1.0-draft"
CATEGORY_REGISTRY_VERSION = "category_registry-0.1.0-draft"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-rows", type=int, default=23000)
    parser.add_argument("--master-seed", type=str, default="drishti_v2_build2_2026-09-07")
    parser.add_argument("--urinary-mode", type=str, default="odisha", choices=["odisha", "aiims"])
    parser.add_argument("--out-dir", type=str, default="drishti_v2_output")
    parser.add_argument("--perturbation-holdout", type=int, default=500)
    args = parser.parse_args(argv)

    print(f"Generating {args.n_rows} rows (master_seed={args.master_seed}, "
          f"urinary_mode={args.urinary_mode})...")
    rows = generate_rows(args.n_rows, args.master_seed, args.urinary_mode)
    df = pd.DataFrame(rows)
    print(f"Generated {len(df)} rows, {len(df.columns)} columns.")

    print("Running build gates...")
    gate_results = run_all_gates(df, SPECS, args.urinary_mode)
    for name, r in gate_results.items():
        print(f"  {name}: {'PASS' if r.passed else 'FAIL'}")

    all_pass = all(r.passed for r in gate_results.values())
    row_volume_per_category = df["category_id"].value_counts().to_dict()

    if not all_pass:
        print("\nOne or more gates FAILED. No corpus written, per section 7.5.")
        print(json.dumps({k: v.to_dict() for k, v in gate_results.items()}, indent=2, default=str))
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    corpus_path = os.path.join(args.out_dir, "corpus.csv")
    df.to_csv(corpus_path, index=False)
    print(f"Corpus written: {corpus_path}")

    manifest = build_manifest(
        n_rows=len(df), master_seed=args.master_seed, urinary_mode=args.urinary_mode,
        generator_commit=GENERATOR_COMMIT, answer_model_version=ANSWER_MODEL_VERSION,
        category_registry_version=CATEGORY_REGISTRY_VERSION,
        gate_results={k: v.to_dict() for k, v in gate_results.items()},
        row_volume_per_category=row_volume_per_category,
    )
    manifest_path = os.path.join(args.out_dir, "generation_manifest.json")
    write_manifest(manifest_path, manifest)
    print(f"Manifest written: {manifest_path}")

    # Section 8.3: the eval set is drawn on its own RNG stream, disjoint from
    # training rows -- a distinct master_seed, not a slice of the training
    # corpus, so it is never seeded from training rows.
    holdout_seed = f"{args.master_seed}::eval_holdout"
    holdout = generate_rows(args.perturbation_holdout, holdout_seed, args.urinary_mode)
    perturb_seed = f"{args.master_seed}::perturbation_eval_set"
    perturbed = build_perturbation_set(holdout, perturb_seed)
    perturb_df = pd.DataFrame(perturbed)
    perturb_path = os.path.join(args.out_dir, "perturbation_eval_set.csv")
    perturb_df.to_csv(perturb_path, index=False)
    print(f"Perturbation eval set written: {perturb_path} ({len(perturb_df)} rows from "
          f"{len(holdout)} held-out base rows)")
    print("NOTE: the OOD eval set (category memo section 8.2 Tier-2 deferred set) is a real-encounter "
          "collection task under consent and is out of scope for this generator.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
