"""
drishti_v2/manifest.py
=========================
generation_manifest.json (dataset-regeneration-design-memo.md section 7.1):
one artifact carrying everything needed to rebuild the corpus, target and
realized marginals side by side, and every gate's declared tolerance.
"""

from __future__ import annotations

import json
import sys
from typing import Dict

from .category_marginal import (OTHER_NOT_IN_LIST_FLOOR_PCT, PALLOR_FLOOR_PCT, RESCALE_FACTOR_TABLE2_TO_PHC,
                                 URINARY_AIIMS_PCT, URINARY_ODISHA_PCT, build_full_target_marginal,
                                 three_branch_marginal)
from .emergency import (ADULT_DANGER, AGGREGATE_EMERGENCY_MIN, AGGREGATE_URGENT_MIN, CHILD_SPO2_MIN,
                         THRESHOLD_TABLE_VERSION)
from .gates import ABS_TOLERANCE_FLOOR, MI_MAX_PERCENTILE, MIN_GLUCOSE_TAIL_ROWS, MIN_PATH1_ADULT_ROWS, \
    MIN_REFER_URGENT_ROWS, MIN_TIER0_ROUTE_ROWS, NULL_RUN_SHUFFLES, TOLERANCE_Z
from .vitals import ENCOUNTER_WINDOW_MONTHS, GENERATION_DATE


def build_manifest(n_rows: int, master_seed: str, urinary_mode: str, generator_commit: str,
                    answer_model_version: str, category_registry_version: str,
                    gate_results: Dict[str, dict], row_volume_per_category: Dict[str, int]) -> dict:
    return {
        "master_seed": master_seed,
        "n_rows": n_rows,
        "generator_commit": generator_commit,
        "generator_module": "drishti_v2",
        "answer_model_version": answer_model_version,
        "category_registry_version": category_registry_version,
        "threshold_table_version": THRESHOLD_TABLE_VERSION,
        "threshold_table_status": "PROVISIONAL -- early-warning-score-derived, NOT an Indian "
                                   "clinical standard. CBAC/IMCI/IHCI reconciliation is a named "
                                   "build-time requirement (memo section 6.3) not performed in "
                                   "this build.",
        "scope": {
            "built_branches": ["fever", "known_hypertension", "rash"],
            "deferred_branches": "the remaining 24 Tier-1 branches + 6 Tier-0 rule-based branches, "
                                  "per tree memo section 6.5's authoring order",
        },
        "rng": {
            "scheme": "sha256(master_seed|row_id|stream_name)[:12] -> [0,1)",
            "module_level_rng_state": "none -- every draw goes through RowRng scoped to one row_id",
        },
        "category_marginal": {
            "rescale_factor_table2_to_phc": RESCALE_FACTOR_TABLE2_TO_PHC,
            "urinary_anchor_mode": urinary_mode,
            "urinary_anchor_odisha_pct": URINARY_ODISHA_PCT,
            "urinary_anchor_aiims_pct": URINARY_AIIMS_PCT,
            "pallor_anaemia_floor_pct": PALLOR_FLOOR_PCT,
            "other_not_in_list_floor_pct": OTHER_NOT_IN_LIST_FLOOR_PCT,
            "target_marginal_full_label_space": build_full_target_marginal(urinary_mode),
            "target_marginal_this_build": three_branch_marginal(urinary_mode),
        },
        "row_volume_per_category": row_volume_per_category,
        "emergency_paths": {
            "path1_adult_danger_bands": ADULT_DANGER,
            "path1_child_spo2_min": CHILD_SPO2_MIN,
            "path2_aggregate_urgent_min": AGGREGATE_URGENT_MIN,
            "path2_aggregate_emergency_min": AGGREGATE_EMERGENCY_MIN,
        },
        "encounter_window": {
            "months": ENCOUNTER_WINDOW_MONTHS,
            "generation_date": GENERATION_DATE.isoformat(),
        },
        "gate_tolerances": {
            "GATE-MARGINAL/GATE-DECLARED": {"tolerance_z_binomial_se": TOLERANCE_Z,
                                              "abs_tolerance_floor": ABS_TOLERANCE_FLOOR},
            "GATE-RANGE": {"min_tail_rows": MIN_GLUCOSE_TAIL_ROWS},
            "GATE-EMERGENCY": {"min_path1_adult_rows": MIN_PATH1_ADULT_ROWS,
                                "min_tier0_route_rows": MIN_TIER0_ROUTE_ROWS,
                                "min_refer_urgent_rows": MIN_REFER_URGENT_ROWS},
            "GATE-LEAK": {"mi_max_percentile": MI_MAX_PERCENTILE, "null_run_shuffles": NULL_RUN_SHUFFLES,
                          "mi_max_is_a_calibrated_manifest_constant": True},
        },
        "python_version": sys.version,
        "library_versions": _library_versions(),
        "gate_results": gate_results,
    }


def _library_versions() -> dict:
    versions = {}
    for name in ("pandas", "numpy", "scipy", "sklearn"):
        try:
            mod = __import__(name)
            versions[name] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[name] = "not installed"
    return versions


def write_manifest(path: str, manifest: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
