"""
drishti_v2/branches/authoring.py
==================================
A compact way to author the ~13 nodes x ~10 conditions x 3 severities
answer-model entries a branch needs, without hand-typing every cell.

expand_entries() takes a per-severity baseline distribution plus a sparse
set of per-(condition, severity) overrides for the nodes where the
condition genuinely changes the answer (fever_pattern is the clearest
case -- it is the one node the audit measured as decisive) and fills every
other cell from the baseline. Every cell still becomes a real, validated
AnswerModelEntry with its own provenance; nothing is left undeclared.

This is a build-time authoring convenience, not a memo requirement, and it
is why the per-condition clinical content here is coarser than a
physician-authored branch would be -- section 6.3 of the tree memo is
explicit that per-branch clinical review is a separate, deferred step. What
this module guarantees is the *machine*: every node reachable for every
condition/severity this build declares has a typed, sourced-or-ASSUMED,
dated entry, which is what GATE-DECLARED and the module-load assertion
actually check.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..answer_model import AnswerModelEntry

DECLARED_ON = "2026-09-06"


def peaked(options: List[str], peak: str, peak_p: float) -> Dict[str, float]:
    """A categorical distribution over `options` putting peak_p on `peak` and
    splitting the remainder evenly over the rest. Sums to 1.0 exactly by
    construction -- the safe way to write a condition override without
    hand-summing a partial dict edit."""
    rest = [o for o in options if o != peak]
    rest_p = (1.0 - peak_p) / len(rest)
    d = {o: rest_p for o in rest}
    d[peak] = peak_p
    return d


def expand_entries(node_id: str, kind: str, conditions: List[str], severities: List[str],
                    base_by_severity: Dict[str, Dict[str, float]],
                    overrides: Dict[Tuple[str, str], Dict[str, float]] = None,
                    source_type: str = "ASSUMED", source: str = "") -> List[AnswerModelEntry]:
    overrides = overrides or {}
    entries = []
    for c in conditions:
        for s in severities:
            dist = overrides.get((c, s), base_by_severity[s])
            entries.append(AnswerModelEntry(
                nodeId=node_id, conditionId=c, severityBand=s, kind=kind,
                distribution=dict(dist), sourceType=source_type, source=source,
                declaredOn=DECLARED_ON,
            ))
    return entries
