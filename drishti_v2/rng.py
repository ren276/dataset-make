"""
drishti_v2/rng.py
==================
Counter-based per-row RNG (dataset-regeneration-design-memo.md, section 7.2).

    u(row_id, stream_name) = sha256(f"{master_seed}|{row_id}|{stream_name}") -> [0,1)

Order-independent, parallel-safe, individually reproducible. hash() is banned
in this generator (memo defect 12), as is any module-level / sequential RNG
state (random.Random, numpy default_rng seeded once and reused, etc). Every
caller must go through RowRng, which carries no state beyond the row it was
built for.
"""

from __future__ import annotations

import hashlib
import math


def stream_u(master_seed: str, row_id: str, stream_name: str) -> float:
    digest = hashlib.sha256(f"{master_seed}|{row_id}|{stream_name}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16 ** 12)


class RowRng:
    """
    Deterministic RNG handle scoped to exactly one row. Every draw is named by
    a stream_name so adding a new draw never perturbs any other stream's
    output (memo 7.2: "one named stream per decision").
    """

    __slots__ = ("master_seed", "row_id")

    def __init__(self, master_seed: str, row_id: str):
        self.master_seed = master_seed
        self.row_id = row_id

    def u(self, stream_name: str) -> float:
        return stream_u(self.master_seed, self.row_id, stream_name)

    def bernoulli(self, stream_name: str, p: float) -> bool:
        return self.u(stream_name) < p

    def uniform(self, stream_name: str, lo: float, hi: float) -> float:
        return lo + self.u(stream_name) * (hi - lo)

    def normal(self, stream_name: str, mean: float, sd: float) -> float:
        u1 = min(max(self.u(stream_name + "::n1"), 1e-12), 1.0 - 1e-12)
        u2 = self.u(stream_name + "::n2")
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mean + z * sd

    def choice(self, stream_name: str, options, weights=None):
        """Deterministic weighted choice by CDF over declared weights."""
        options = list(options)
        if not options:
            raise ValueError(f"choice() called with empty options for stream {stream_name!r}")
        if weights is None:
            idx = min(int(self.u(stream_name) * len(options)), len(options) - 1)
            return options[idx]
        weights = list(weights)
        total = sum(weights)
        if total <= 0:
            raise ValueError(f"choice() weights sum to {total} for stream {stream_name!r}")
        target = self.u(stream_name) * total
        acc = 0.0
        for opt, w in zip(options, weights):
            acc += w
            if target < acc:
                return opt
        return options[-1]

    def sub(self, suffix: str) -> "RowRng":
        """A derived handle for a named sub-decision, still keyed off the same row_id."""
        return RowRng(self.master_seed, f"{self.row_id}::{suffix}")
