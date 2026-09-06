"""
drishti_v2/answer_model.py
===========================
The answer model (dataset-regeneration-design-memo.md section 2.3): the only
place clinical knowledge enters generation. For each (nodeId, conditionId,
severityBand) it is a declared distribution over that node's fixed option
set, and every entry carries provenance.

Two entry kinds, both provenance-typed identically. The memo specifies the
categorical shape explicitly (weights summing to 1.0) for SINGLE_CHOICE
nodes. It does not specify a MULTI_CHOICE shape, so this module declares one:
MULTI_CHOICE nodes carry an independent per-option inclusion probability
(a "multi_bernoulli" entry), because a MULTI answer is naturally a small
subset draw, not a single pick from a closed list. This is a build decision,
not a memo requirement, and is stated here so it is not mistaken for one.

sourceType is one of IND-PRESENT | IND-POP | IND-PROG | WORLD | ASSUMED
(reason-for-encounter-category-system-memo.md section 2). ASSUMED is a legal
value; the module-load assertion requires it be present and reasoned, never
silent.

No physician has signed any entry in this build -- this is infrastructure,
not clinical authoring. reviewedBy is honestly set to the sentinel
"PENDING_PHYSICIAN_REVIEW" rather than a fabricated name. Every branch's
README/docstring repeats this; the corpus this generator produces must not
be mistaken for a physician-reviewed release.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional

VALID_SOURCE_TYPES = {"IND-PRESENT", "IND-POP", "IND-PROG", "WORLD", "ASSUMED"}
PENDING_REVIEW = "PENDING_PHYSICIAN_REVIEW"
_EPS = 1e-6


@dataclass(frozen=True)
class AnswerModelEntry:
    nodeId: str
    conditionId: str
    severityBand: str
    kind: str  # "categorical" | "multi_bernoulli"
    distribution: Dict[str, float]
    sourceType: str
    source: str
    declaredOn: str
    reviewedBy: str = PENDING_REVIEW

    def key(self):
        return (self.nodeId, self.conditionId, self.severityBand)

    def validate(self) -> None:
        if not self.nodeId or not self.conditionId or not self.severityBand:
            raise ValueError(f"AnswerModelEntry missing key fields: {self}")
        if self.sourceType not in VALID_SOURCE_TYPES:
            raise ValueError(f"{self.nodeId}/{self.conditionId}/{self.severityBand}: "
                              f"invalid sourceType {self.sourceType!r}")
        if not self.source or not self.source.strip():
            raise ValueError(f"{self.nodeId}/{self.conditionId}/{self.severityBand}: "
                              f"empty source (ASSUMED still requires the reasoning as 'source')")
        if not self.declaredOn or not self.declaredOn.strip():
            raise ValueError(f"{self.nodeId}/{self.conditionId}/{self.severityBand}: empty declaredOn")
        if not self.reviewedBy or not self.reviewedBy.strip():
            raise ValueError(f"{self.nodeId}/{self.conditionId}/{self.severityBand}: empty reviewedBy")
        if not self.distribution:
            raise ValueError(f"{self.nodeId}/{self.conditionId}/{self.severityBand}: empty distribution")
        if self.kind == "categorical":
            total = sum(self.distribution.values())
            if abs(total - 1.0) > _EPS:
                raise ValueError(
                    f"{self.nodeId}/{self.conditionId}/{self.severityBand}: "
                    f"categorical distribution sums to {total}, not 1.0")
        elif self.kind == "multi_bernoulli":
            for opt, p in self.distribution.items():
                if not (0.0 <= p <= 1.0):
                    raise ValueError(
                        f"{self.nodeId}/{self.conditionId}/{self.severityBand}: "
                        f"multi_bernoulli option {opt!r} probability {p} out of [0,1]")
        else:
            raise ValueError(f"{self.nodeId}: unknown answer model entry kind {self.kind!r}")


class AnswerModel:
    """Registry of AnswerModelEntry, loaded once per generation run."""

    def __init__(self, entries: List[AnswerModelEntry]):
        self._entries: Dict[tuple, AnswerModelEntry] = {}
        for e in entries:
            e.validate()
            if e.key() in self._entries:
                raise ValueError(f"duplicate answer model entry for {e.key()}")
            self._entries[e.key()] = e

    def get(self, node_id: str, condition_id: str, severity_band: str) -> AnswerModelEntry:
        key = (node_id, condition_id, severity_band)
        if key not in self._entries:
            raise KeyError(
                f"no answer model entry for nodeId={node_id!r} conditionId={condition_id!r} "
                f"severityBand={severity_band!r} -- every node reachable for this condition/severity "
                f"must have a declared entry (ASSUMED is legal; missing is not)")
        return self._entries[key]

    def draw_categorical(self, rng, node_id: str, condition_id: str, severity_band: str,
                          stream_name: str) -> str:
        entry = self.get(node_id, condition_id, severity_band)
        if entry.kind != "categorical":
            raise ValueError(f"{node_id}: expected categorical entry, got {entry.kind}")
        options = list(entry.distribution.keys())
        weights = [entry.distribution[o] for o in options]
        return rng.choice(stream_name, options, weights)

    def draw_multi(self, rng, node_id: str, condition_id: str, severity_band: str,
                    stream_name: str) -> FrozenSet[str]:
        entry = self.get(node_id, condition_id, severity_band)
        if entry.kind != "multi_bernoulli":
            raise ValueError(f"{node_id}: expected multi_bernoulli entry, got {entry.kind}")
        selected = set()
        for opt, p in entry.distribution.items():
            if rng.bernoulli(f"{stream_name}::{opt}", p):
                selected.add(opt)
        return frozenset(selected)

    def all_entries(self) -> List[AnswerModelEntry]:
        return list(self._entries.values())
