"""
drishti_v2/category_marginal.py
=================================
The stage-1 target marginal (dataset-regeneration-design-memo.md section 3,
reason-for-encounter-category-system-memo.md section 7). category_id is
drawn FIRST from this distribution -- it is an input to generation, not an
emergent property of a quota (rule 4).

Three operator-locked overrides, applied in this order and each written into
the manifest exactly as decided:

1. urinary_symptoms anchor switch -- one constant, two values. Default
   Odisha primary (0.27%); URINARY_MODE="aiims" switches to the AIIMS
   Bhopal sensitivity value (8.1%). Per the memo: "generate a declared
   sensitivity corpus... from the same manifest with one constant changed" --
   implemented literally as one constant substitution followed by a
   renormalization of the whole vector (nothing else is edited by hand).
2. pallor_anaemia declared floor, 2.0%, taken proportionally from the rest
   of the (already urinary-adjusted) marginal.
3. other_not_in_list declared floor, 6.0%, taken proportionally from
   everything except the categories already floored above.

This build generates rows for three categories only (fever,
known_hypertension, rash) -- the operator's locked scope. The full 27-way
marginal is still constructed and recorded in the manifest in full (that is
what the floors and the switch are declared against), and a second,
renormalized marginal restricted to the three built categories is what this
run actually draws from and what GATE-MARGINAL checks the realized output
against. Both are written to generation_manifest.json side by side so a
future fill-in run has the untouched full target to draw against.
"""

from __future__ import annotations

from typing import Dict

RESCALE_FACTOR_TABLE2_TO_PHC = 0.6749  # memo section 3.2, declared not silent

# Raw category shares (percent), exactly as constructed in the memo's section
# 3.2 table, at the Odisha urinary anchor and before the pallor/other floors.
_BASE_MARGINAL_PCT: Dict[str, float] = {
    "fever": 36.03, "weakness_unwell": 4.56, "body_ache": 3.19,
    "weight_loss": 0.91, "oedema": 0.91,
    "abdominal_pain": 7.08, "acidity_heartburn": 4.96, "diarrhoea": 3.54,
    "vomiting_nausea": 2.12,
    "joint_pain": 5.40, "back_neck_pain": 3.60, "injury": 3.00,
    "cough": 3.07, "cold_sore_throat": 2.73, "breathlessness": 1.02,
    "known_hypertension": 3.12, "chest_pain": 1.34,
    "rash": 1.54, "itching": 1.35, "skin_infection": 0.96,
    "antenatal_visit": 3.37,
    "headache": 1.34, "dizziness": 0.61,
    "known_diabetes": 0.88,
    "urinary_symptoms": 0.27,   # Odisha primary anchor -- the switch target
    "pallor_anaemia": 0.07,     # the floor target
    "other_not_in_list": 3.05,  # N-chapter residual (0.49) + deferred chapters (2.56)
}

URINARY_ODISHA_PCT = 0.27
URINARY_AIIMS_PCT = 8.1

PALLOR_FLOOR_PCT = 2.0
OTHER_NOT_IN_LIST_FLOOR_PCT = 6.0

THREE_BUILT_CATEGORIES = ("fever", "known_hypertension", "rash")


def _renormalize(marginal: Dict[str, float]) -> Dict[str, float]:
    total = sum(marginal.values())
    return {k: v / total for k, v in marginal.items()}


def _apply_floor(marginal: Dict[str, float], category: str, floor_frac: float,
                  locked: set) -> Dict[str, float]:
    """Raise `category` to `floor_frac` of the total, taking the deficit
    proportionally from every category not already locked by a prior floor."""
    current = marginal[category]
    if current >= floor_frac:
        locked.add(category)
        return marginal
    deficit = floor_frac - current
    donors = {k: v for k, v in marginal.items() if k not in locked and k != category}
    donor_total = sum(donors.values())
    scale = (donor_total - deficit) / donor_total
    out = dict(marginal)
    for k in donors:
        out[k] = marginal[k] * scale
    out[category] = floor_frac
    locked.add(category)
    return out


def build_full_target_marginal(urinary_mode: str = "odisha") -> Dict[str, float]:
    """Returns the full 27-category (25 named here; emergency Tier-0 and the
    fully-deferred Tier-2 set are outside this label space per the category
    memo) target marginal as fractions summing to 1.0, overrides applied."""
    if urinary_mode not in ("odisha", "aiims"):
        raise ValueError(f"urinary_mode must be 'odisha' or 'aiims', got {urinary_mode!r}")

    marginal_pct = dict(_BASE_MARGINAL_PCT)
    marginal_pct["urinary_symptoms"] = URINARY_ODISHA_PCT if urinary_mode == "odisha" else URINARY_AIIMS_PCT
    marginal = _renormalize(marginal_pct)

    locked: set = set()
    marginal = _apply_floor(marginal, "pallor_anaemia", PALLOR_FLOOR_PCT / 100.0, locked)
    marginal = _apply_floor(marginal, "other_not_in_list", OTHER_NOT_IN_LIST_FLOOR_PCT / 100.0, locked)
    return marginal


def three_branch_marginal(urinary_mode: str = "odisha") -> Dict[str, float]:
    """The renormalized subset actually drawn from in this build (scope:
    fever, known_hypertension, rash only)."""
    full = build_full_target_marginal(urinary_mode)
    subset = {k: full[k] for k in THREE_BUILT_CATEGORIES}
    return _renormalize(subset)


def draw_category(rng, urinary_mode: str = "odisha") -> str:
    marginal = build_full_target_marginal(urinary_mode)
    cats = list(marginal.keys())
    weights = [marginal[c] for c in cats]
    return rng.choice("category_id", cats, weights)
