"""
drishti_v2/branches/spec.py
=============================
CategorySpec bundles everything the five-stage pipeline (generate.py) needs
for one category_id: the condition catalog with its declared, provenance-
typed share-among-category-encounters, the severity distribution per
condition, the vitals_true profile function, the branch DAG, and the answer
model entries that DAG's nodes need.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from ..answer_model import AnswerModelEntry
from ..schema import BranchDef
from ..vitals import VitalSpec

SEVERITY_BANDS = ("mild", "moderate", "severe")


@dataclass(frozen=True)
class ConditionSpec:
    conditionId: str
    share: float          # of this category's encounters
    sourceType: str
    source: str
    severeConditions: tuple = ()


@dataclass(frozen=True)
class CategorySpec:
    categoryId: str
    branch: BranchDef
    conditions: Dict[str, ConditionSpec]
    severity_dist: Dict[str, Dict[str, float]]  # conditionId -> {severity_band: prob}
    vitals_fn: Callable  # (rng, age_years, sex, age_band, condition_id, severity_band) -> Dict[str, VitalSpec]
    answer_model_entries: List[AnswerModelEntry]

    def __post_init__(self):
        total = sum(c.share for c in self.conditions.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"{self.categoryId}: condition shares sum to {total}, not 1.0")
        for cid, dist in self.severity_dist.items():
            t = sum(dist.values())
            if abs(t - 1.0) > 1e-6:
                raise ValueError(f"{self.categoryId}/{cid}: severity dist sums to {t}, not 1.0")
            if set(dist.keys()) != set(SEVERITY_BANDS):
                raise ValueError(f"{self.categoryId}/{cid}: severity dist keys {set(dist.keys())} "
                                  f"!= {set(SEVERITY_BANDS)}")

    def draw_condition(self, rng) -> str:
        ids = list(self.conditions.keys())
        weights = [self.conditions[i].share for i in ids]
        return rng.choice(f"condition::{self.categoryId}", ids, weights)

    def draw_severity(self, rng, condition_id: str) -> str:
        dist = self.severity_dist[condition_id]
        bands = list(dist.keys())
        weights = [dist[b] for b in bands]
        return rng.choice(f"severity::{self.categoryId}::{condition_id}", bands, weights)
