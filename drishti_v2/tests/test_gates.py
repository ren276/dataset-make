"""Unit tests for gate logic (memo section 7.5), using small synthetic
frames rather than a full generation run -- these test the CHECK, not the
generator's clinical content."""

import numpy as np
import pandas as pd

from drishti_v2 import gates
from drishti_v2.vitals import GENERATION_DATE, VITALS


def _base_vitals_columns(n):
    cols = {}
    for v in VITALS:
        cols[f"{v}_true"] = np.full(n, 100.0)
        cols[v] = np.full(n, 100.0)
        cols[f"{v}_provenance"] = ["DEVICE_MEASURED"] * n
    return cols


def test_gate_range_fails_without_tails():
    n = 100
    df = pd.DataFrame({"glucose_true": np.full(n, 105.0)})
    r = gates.gate_range(df)
    assert not r.passed


def test_gate_range_passes_with_both_tails():
    n = 100
    vals = [105.0] * (n - 10) + [40.0] * 5 + [350.0] * 5
    df = pd.DataFrame({"glucose_true": vals})
    r = gates.gate_range(df)
    assert r.passed


def test_gate_window_fails_on_out_of_range_date():
    df = pd.DataFrame({"encounter_date": [GENERATION_DATE.isoformat(), "2020-01-01"]})
    r = gates.gate_window(df)
    assert not r.passed
    assert r.detail["out_of_window_rows"] == 1


def test_gate_window_passes_within_range():
    df = pd.DataFrame({"encounter_date": [GENERATION_DATE.isoformat()] * 5})
    r = gates.gate_window(df)
    assert r.passed


_SAFE_DEFAULT = {"bp_systolic": 120.0, "bp_diastolic": 80.0, "pulse": 80.0, "bmi": 22.0,
                 "glucose": 100.0, "temperature": 37.0, "respiratory_rate": 16.0}


def _plausible_frame(n, spo2_values):
    cols = {"age_band": ["15_29"] * n, "spo2": spo2_values}
    for v in VITALS:
        if v != "spo2":
            cols[v] = np.full(n, _SAFE_DEFAULT[v])
    return pd.DataFrame(cols)


def test_gate_plausible_fails_on_impossible_value():
    df = _plausible_frame(5, [98, 97, 99, 5.0, 98])
    r = gates.gate_plausible(df)
    assert not r.passed
    assert r.detail["violations"]["spo2"] == 1


def test_gate_plausible_passes_on_normal_values():
    df = _plausible_frame(5, [98, 97, 99, 96, 98])
    r = gates.gate_plausible(df)
    assert r.passed


def test_gate_marginal_fails_on_wrong_mix():
    n = 100
    df = pd.DataFrame({"category_id": ["known_hypertension"] * n})  # 100%, way off ~7.7% target
    r = gates.gate_marginal(df, "odisha")
    assert not r.passed


def test_gate_leak_flags_a_real_leak():
    rng = np.random.default_rng(0)
    n = 4000
    category = rng.choice(["fever", "known_hypertension", "rash"], size=n, p=[0.6, 0.25, 0.15])
    # Construct a deliberate leak: danger_signs__status is UNKNOWN far more
    # often for one category than the others, unconditionally (not explained
    # by any legitimate gating covariate).
    status = np.where(
        category == "rash",
        rng.choice(["ANSWERED", "UNKNOWN"], size=n, p=[0.5, 0.5]),
        rng.choice(["ANSWERED", "UNKNOWN"], size=n, p=[0.99, 0.01]),
    )
    sex = rng.choice(["M", "F"], size=n)
    age = rng.integers(1, 80, size=n)
    df = pd.DataFrame({
        "category_id": category, "danger_signs__status": status,
        "pregnancy_status__status": np.where((sex == "F") & (age >= 15) & (age <= 49), "ANSWERED", "NOT_ASKED"),
        "sex": sex, "age_at_encounter": age, "facility_tier": rng.choice(["LOW", "MEDIUM", "HIGH"], size=n),
        "routed_to": [""] * n,
    })
    for v in VITALS:
        df[f"{v}_provenance"] = "DEVICE_MEASURED"
    r = gates.gate_leak(df, seed=1)
    assert not r.passed, "a deliberately injected category-correlated status leak should be caught"


def test_gate_leak_passes_when_status_is_independent_of_category():
    rng = np.random.default_rng(0)
    n = 4000
    category = rng.choice(["fever", "known_hypertension", "rash"], size=n, p=[0.6, 0.25, 0.15])
    status = rng.choice(["ANSWERED", "UNKNOWN"], size=n, p=[0.97, 0.03])  # same rate regardless of category
    sex = rng.choice(["M", "F"], size=n)
    age = rng.integers(1, 80, size=n)
    facility = rng.choice(["LOW", "MEDIUM", "HIGH"], size=n)
    not_measured_rate = {"LOW": 0.3, "MEDIUM": 0.1, "HIGH": 0.02}
    df = pd.DataFrame({
        "category_id": category, "danger_signs__status": status,
        "pregnancy_status__status": np.where((sex == "F") & (age >= 15) & (age <= 49), "ANSWERED", "NOT_ASKED"),
        "sex": sex, "age_at_encounter": age, "facility_tier": facility, "routed_to": [""] * n,
    })
    for v in VITALS:
        p = np.array([not_measured_rate[f] for f in facility])
        is_not_measured = rng.random(n) < p
        df[f"{v}_provenance"] = np.where(is_not_measured, "NOT_MEASURED", "DEVICE_MEASURED")
    r = gates.gate_leak(df, seed=1)
    assert r.passed
