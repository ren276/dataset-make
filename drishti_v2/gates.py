"""
drishti_v2/gates.py
======================
The eight hard-fail build gates (dataset-regeneration-design-memo.md
section 7.5). Every gate returns a GateResult; run_all_gates() fails the
whole run (writes no corpus) if any gate fails -- generate_cli.py enforces
that, this module only computes and reports.

GATE-LEAK is scoped to what is actually testable in a 3-branch build. Most
tree fields are branch-specific and therefore perfectly confounded with
category_id by construction (a `known_hypertension` row can never answer
`fever_pattern` because that branch never asks it) -- the memo is explicit
that an unstratified test flagging this "legitimate path-determined
correlation" would be useless. The genuine cross-category leak surface in
this build is: (a) fields multiple built branches actually ask
(`danger_signs`, `pregnancy_status`), where status should be independent of
category after conditioning on the real gating covariate; (b) vitals
NOT_MEASURED, which must be independent of category after conditioning on
facility_tier. Both are tested below. MI_MAX is calibrated from a null run
(category_id shuffled) rather than intuited, per the memo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.metrics import mutual_info_score

from .category_marginal import three_branch_marginal
from .vitals import (AVAILABILITY_RATE, FACILITY_TIERS, GENERATION_DATE, ENCOUNTER_WINDOW_MONTHS,
                      PLAUSIBILITY_RANGES, VITALS)

ABS_TOLERANCE_FLOOR = 0.006  # 0.6 percentage points, for small shares
TOLERANCE_Z = 4.0  # multiples of binomial SE; a flat relative tolerance under-
                    # counts sampling noise on rare (low-n) severity cells

MIN_PATH1_ADULT_ROWS = 15
MIN_TIER0_ROUTE_ROWS = 3
MIN_REFER_URGENT_ROWS = 5
MIN_GLUCOSE_TAIL_ROWS = 3
NULL_RUN_SHUFFLES = 40
MI_MAX_PERCENTILE = 99.0


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: dict = field(default_factory=dict)

    def to_dict(self):
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _within_tol(realized: float, target: float, n: int) -> bool:
    """A target proportion drawn n times has binomial SE sqrt(p(1-p)/n).
    Tolerance is max(a small absolute floor, TOLERANCE_Z standard errors) --
    a flat relative tolerance was tried first and under-counted sampling
    noise on rare, low-n severity cells (a handful of hundred rows), flagging
    normal binomial variation as a declared-vs-realized mismatch."""
    se = (target * (1 - target) / max(n, 1)) ** 0.5
    tol = max(TOLERANCE_Z * se, ABS_TOLERANCE_FLOOR)
    return abs(realized - target) <= tol


def gate_marginal(df: pd.DataFrame, urinary_mode: str) -> GateResult:
    target = three_branch_marginal(urinary_mode)
    n = len(df)
    realized = df["category_id"].value_counts(normalize=True).to_dict()
    cells = {}
    ok = True
    for cat, tgt in target.items():
        r = realized.get(cat, 0.0)
        cell_ok = _within_tol(r, tgt, n)
        ok = ok and cell_ok
        cells[cat] = {"target": tgt, "realized": r, "ok": cell_ok}
    return GateResult("GATE-MARGINAL", ok, {"cells": cells})


def gate_declared(df: pd.DataFrame, specs: dict) -> GateResult:
    cells = {}
    ok = True
    for cat, spec in specs.items():
        sub = df[df["category_id"] == cat]
        if len(sub) == 0:
            continue
        n_cat = len(sub)
        realized_cond = sub["_condition_id"].value_counts(normalize=True).to_dict()
        for cond_id, cond_spec in spec.conditions.items():
            r = realized_cond.get(cond_id, 0.0)
            cell_ok = _within_tol(r, cond_spec.share, n_cat)
            ok = ok and cell_ok
            cells[f"{cat}/{cond_id}/share"] = {"target": cond_spec.share, "realized": r, "ok": cell_ok}
            cond_sub = sub[sub["_condition_id"] == cond_id]
            n_cond = len(cond_sub)
            if n_cond < 20:
                continue  # too few rows for a stable severity-band estimate
            realized_sev = cond_sub["_severity_band"].value_counts(normalize=True).to_dict()
            for band, tgt in spec.severity_dist[cond_id].items():
                r2 = realized_sev.get(band, 0.0)
                cell_ok2 = _within_tol(r2, tgt, n_cond)
                ok = ok and cell_ok2
                cells[f"{cat}/{cond_id}/severity/{band}"] = {"target": tgt, "realized": r2, "ok": cell_ok2}
    return GateResult("GATE-DECLARED", ok, {"cells": cells})


def gate_bmi(df: pd.DataFrame) -> GateResult:
    adult = df[df["age_at_encounter"] >= 18]
    mean_bmi = float(adult["bmi_true"].mean())
    target_mean = 21.5
    ok = abs(mean_bmi - target_mean) <= 1.5
    overweight_rate = float((adult["bmi_true"] >= 23.0).mean())
    return GateResult("GATE-BMI", ok, {"realized_mean": mean_bmi, "target_mean": target_mean,
                                        "overweight_rate": overweight_rate})


def gate_range(df: pd.DataFrame) -> GateResult:
    hypo = int((df["glucose_true"] < 54).sum())
    dka = int((df["glucose_true"] > 300).sum())
    ok = hypo >= MIN_GLUCOSE_TAIL_ROWS and dka >= MIN_GLUCOSE_TAIL_ROWS
    return GateResult("GATE-RANGE", ok, {"hypoglycaemia_rows": hypo, "dka_range_rows": dka,
                                          "min_required": MIN_GLUCOSE_TAIL_ROWS})


def gate_window(df: pd.DataFrame) -> GateResult:
    dates = pd.to_datetime(df["encounter_date"])
    window_start = pd.Timestamp(GENERATION_DATE) - pd.Timedelta(days=ENCOUNTER_WINDOW_MONTHS * 30)
    window_end = pd.Timestamp(GENERATION_DATE)
    out_of_window = int(((dates < window_start) | (dates > window_end)).sum())
    return GateResult("GATE-WINDOW", out_of_window == 0,
                       {"out_of_window_rows": out_of_window, "window_start": str(window_start.date()),
                        "window_end": str(window_end.date())})


def gate_plausible(df: pd.DataFrame) -> GateResult:
    violations = {}
    for vital in VITALS:
        lo_hi_by_band = PLAUSIBILITY_RANGES[vital]
        bad = 0
        for band, (lo, hi) in lo_hi_by_band.items():
            sub = df[(df["age_band"] == band) & df[vital].notna()]
            bad += int(((sub[vital] < lo) | (sub[vital] > hi)).sum())
        if bad:
            violations[vital] = bad
    return GateResult("GATE-PLAUSIBLE", len(violations) == 0, {"violations": violations})


def gate_emergency(df: pd.DataFrame) -> GateResult:
    adult = df[df["age_at_encounter"] >= 18]
    path1_adult = int(adult["path1_emergency"].sum())
    tier0_routes = int((df["routed_to"] != "").sum())
    refer_urgent = int((df["disposition_floor"] == "REFER_URGENT").sum())
    refer_emergency = int((df["disposition_floor"] == "REFER_EMERGENCY").sum())
    child = df[df["age_at_encounter"] < 18]
    path1_child = int(child["path1_emergency"].sum()) if len(child) else 0

    ok = (path1_adult >= MIN_PATH1_ADULT_ROWS and tier0_routes >= MIN_TIER0_ROUTE_ROWS
          and refer_urgent >= MIN_REFER_URGENT_ROWS)
    return GateResult("GATE-EMERGENCY", ok, {
        "path1_adult_rows": path1_adult, "path1_child_rows": path1_child,
        "tier0_route_rows": tier0_routes, "refer_urgent_rows": refer_urgent,
        "refer_emergency_rows": refer_emergency,
        "min_required": {"path1_adult": MIN_PATH1_ADULT_ROWS, "tier0_routes": MIN_TIER0_ROUTE_ROWS,
                          "refer_urgent": MIN_REFER_URGENT_ROWS},
    })


# ---------------------------------------------------------------------------
# GATE-LEAK
# ---------------------------------------------------------------------------

def _mi_and_p(labels: pd.Series, status: pd.Series) -> Optional[dict]:
    if labels.nunique() < 2 or status.nunique() < 2:
        return None
    ct = pd.crosstab(status, labels)
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return None
    mi = float(mutual_info_score(labels, status))
    try:
        _, p, _, _ = chi2_contingency(ct)
    except ValueError:
        p = float("nan")
    return {"mi": mi, "chi2_p": float(p), "n": int(len(labels))}


def _shared_field_checks(df: pd.DataFrame, test_labels: Optional[pd.Series] = None) -> List[dict]:
    """
    Structural eligibility (does this row's real branch even define this
    field?) always uses df["category_id"], the TRUE category -- that is a
    fact about the branch, not the label being tested. test_labels is what
    gets compared against __status; under a null run it is a shuffled
    Series, but the structural mask must stay real or the shuffle would mix
    in rows that never had the field at all (NaN), corrupting the test.
    """
    labels = test_labels if test_labels is not None else df["category_id"]
    checks = []
    # danger_signs: unconditional Stage A in all three branches, no gating covariate.
    mask = df["danger_signs__status"].notna()
    r = _mi_and_p(labels[mask], df.loc[mask, "danger_signs__status"])
    if r:
        checks.append(dict(r, field="danger_signs__status", stratum="all"))
    # pregnancy_status: gated on sex==F and age in [15,49]; only fever + known_hypertension
    # ask it. Rows a Tier-0 gateway routed away (routed_to != "") never reach the node at
    # all -- that is a legitimate, path-determined NOT_ASKED (fever has Tier-0 routing
    # gateways ahead of FV-12; known_hypertension has none), not a nuisance leak, so those
    # rows are excluded from the denominator rather than left to masquerade as a status
    # difference between categories.
    mask = ((df["sex"] == "F") & (df["age_at_encounter"].between(15, 49))
            & (df["category_id"].isin(["fever", "known_hypertension"]))
            & (df["routed_to"] == ""))
    r = _mi_and_p(labels[mask], df.loc[mask, "pregnancy_status__status"])
    if r:
        checks.append(dict(r, field="pregnancy_status__status", stratum="sex=F,age=15-49"))
    return checks


def _vitals_availability_checks(df: pd.DataFrame, test_labels: Optional[pd.Series] = None) -> List[dict]:
    labels = test_labels if test_labels is not None else df["category_id"]
    checks = []
    for vital in VITALS:
        col = f"{vital}_provenance"
        not_measured = (df[col] == "NOT_MEASURED")
        for tier in FACILITY_TIERS:
            mask = df["facility_tier"] == tier
            if mask.sum() == 0:
                continue
            r = _mi_and_p(labels[mask], not_measured[mask])
            if r:
                checks.append(dict(r, field=f"{vital}_provenance==NOT_MEASURED", stratum=f"facility_tier={tier}"))
    return checks


def _null_run_mi_distribution(df: pd.DataFrame, rng: np.random.Generator, n_shuffles: int) -> List[float]:
    mis = []
    labels_real = df["category_id"].to_numpy()
    for _ in range(n_shuffles):
        shuffled_labels = pd.Series(rng.permutation(labels_real), index=df.index)
        for r in _shared_field_checks(df, shuffled_labels):
            mis.append(r["mi"])
        for r in _vitals_availability_checks(df, shuffled_labels):
            mis.append(r["mi"])
    return mis


def gate_leak(df: pd.DataFrame, seed: int = 0) -> GateResult:
    real_checks = _shared_field_checks(df) + _vitals_availability_checks(df)
    rng = np.random.default_rng(seed)
    null_mis = _null_run_mi_distribution(df, rng, NULL_RUN_SHUFFLES)
    # Bonferroni-adjusted percentile: running many (field, stratum) checks
    # against one flat percentile would fail ~1% of genuinely-clean corpora
    # per check by chance alone (multiple comparisons). Scaling the target
    # percentile by the number of real checks keeps the overall false-positive
    # budget at (100-MI_MAX_PERCENTILE)/100 for the WHOLE gate, not per check.
    alpha = (100.0 - MI_MAX_PERCENTILE) / 100.0
    n_checks = max(1, len(real_checks))
    effective_percentile = 100.0 * (1.0 - alpha / n_checks)
    mi_max = float(np.percentile(null_mis, effective_percentile)) if null_mis else 0.01
    mi_max = max(mi_max, 1e-4)  # floor: a degenerate null (all-zero MI) must not force zero tolerance

    breaches = [c for c in real_checks if c["mi"] > mi_max]
    ok = len(breaches) == 0
    return GateResult("GATE-LEAK", ok, {
        "mi_max": mi_max, "mi_max_percentile": MI_MAX_PERCENTILE, "null_shuffles": NULL_RUN_SHUFFLES,
        "checks": real_checks, "breaches": breaches,
    })


def run_all_gates(df: pd.DataFrame, specs: dict, urinary_mode: str) -> Dict[str, GateResult]:
    results = {}
    for gate in (
        lambda: gate_leak(df),
        lambda: gate_marginal(df, urinary_mode),
        lambda: gate_declared(df, specs),
        lambda: gate_bmi(df),
        lambda: gate_range(df),
        lambda: gate_window(df),
        lambda: gate_plausible(df),
        lambda: gate_emergency(df),
    ):
        r = gate()
        results[r.name] = r
    return results
