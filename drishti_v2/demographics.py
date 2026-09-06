"""
drishti_v2/demographics.py
============================
Age and sex, drawn from a declared Census/NFHS-5-shaped distribution
independent of category_id (dataset-regeneration-design-memo.md section 9:
"age/sex come from Census/NFHS-5 distributions declared directly, not from
Synthea"). Synthea is not imported anywhere in this package.

The age-band shares below are ASSUMED: they are shaped to the broad rural
Indian age pyramid (Census 2011 structure -- young, child-heavy, tapering
tail) but the exact cell values were not re-derived from a table in this
session. They are declared here rather than left as a silent Synthea
artifact, which is the whole point of D3/section 9. A physician or
demographer replacing them with cited Census/NFHS-5 cells is expected before
this corpus backs any claim -- see the generator README.

The age window opens to 0 (D3): paediatric rows (age < 5, and the IMCI
young-infant band age < 2 months) must be representable for the paediatric
emergency path to be exercisable at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

AGE_BAND_SHARE_PROVENANCE = {
    "sourceType": "ASSUMED",
    "source": ("Shaped to the broad rural-India age pyramid (Census 2011 structure: "
               "youth-heavy, tapering with age). No cell was re-derived from a specific "
               "Census/NFHS-5 table in this build session -- declared ASSUMED rather than "
               "silently reused from Synthea's US lifetime-simulation demographics."),
    "declaredOn": "2026-09-06",
}

# (age_lo, age_hi_inclusive, share)
AGE_BANDS: Tuple[Tuple[int, int, float], ...] = (
    (0, 0, 0.015),       # < 1 year (IMCI young-infant band folds in here; see age_months below)
    (1, 4, 0.065),
    (5, 14, 0.150),
    (15, 29, 0.240),
    (30, 44, 0.200),
    (45, 59, 0.170),
    (60, 74, 0.120),
    (75, 80, 0.040),
)
assert abs(sum(s for _, _, s in AGE_BANDS) - 1.0) < 1e-9

SEX_SHARE_PROVENANCE = {
    "sourceType": "IND-POP",
    "source": "Census 2011 India sex ratio, 943 females per 1000 males -> F share 943/1943.",
    "declaredOn": "2026-09-06",
}
FEMALE_SHARE = 943.0 / 1943.0


@dataclass(frozen=True)
class Demographics:
    age_years: int
    age_months: int  # only meaningful when age_years == 0; else -1
    sex: str         # "M" | "F"

    @property
    def age_band_pediatric(self) -> bool:
        return self.age_years < 5

    @property
    def is_young_infant(self) -> bool:
        return self.age_years == 0 and self.age_months < 2


def draw_demographics(rng) -> Demographics:
    bands = [(lo, hi) for lo, hi, _ in AGE_BANDS]
    shares = [s for _, _, s in AGE_BANDS]
    lo, hi = rng.choice("demographics::age_band", bands, shares)
    age_years = int(rng.uniform("demographics::age_in_band", lo, hi + 1))
    age_years = min(age_years, hi)
    age_months = -1
    if age_years == 0:
        age_months = int(rng.uniform("demographics::infant_months", 0, 12))
    sex = "F" if rng.bernoulli("demographics::sex", FEMALE_SHARE) else "M"
    return Demographics(age_years=age_years, age_months=age_months, sex=sex)


def age_band_label(age_years: int) -> str:
    if age_years < 5:
        return "0_4"
    if age_years < 15:
        return "5_14"
    if age_years < 30:
        return "15_29"
    if age_years < 45:
        return "30_44"
    if age_years < 60:
        return "45_59"
    return "60_plus"
