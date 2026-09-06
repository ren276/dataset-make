"""
drishti_v2/perturbation.py
=============================
The perturbation eval set (dataset-regeneration-design-memo.md section 8.1).
Built by applying declared perturbation operators to held-out rows. The
operators do not change clinical content, so category_id is unchanged by
construction -- any prediction change on a perturbed row is a measured
robustness failure, not a new labelling task.

Only the tree-channel operators are implemented here. The narrative-channel
operators (typos, ASR substitutions, synonyms, code-mixing) require the
Layer 1 normalization lexicon, which section 7.3/8 of the memos name as a
separate, not-yet-built artifact -- narrative_terms is a reserved column in
this corpus, not a populated one, so there is no narrative text to perturb
yet. Noted, not silently skipped.

Per section 8.3, this module draws on its own RNG stream (a distinct
master_seed from the training corpus, never derived from training rows) and
never touches the class-balance gates -- a perturbation set is deliberately
not distributed like the training set.
"""

from __future__ import annotations

from typing import Dict, List

from .rng import RowRng
from .vitals import DEVICE_MEASURED, MANUAL_ENTERED, NOISE_SD, VITALS

OPERATORS = (
    "option_order_permutation",
    "answered_to_unknown",
    "single_field_drop",
    "device_to_manual_provenance_flip",
    "measurement_error_resample",
)


def _status_field_ids(row: dict) -> List[str]:
    return [c[: -len("__status")] for c, v in row.items()
            if c.endswith("__status") and v == "ANSWERED"]


def _is_multi(row: dict, field_id: str) -> bool:
    return any(c.startswith(f"{field_id}__") and not c.endswith("__status") for c in row)


def _clear_field(row: dict, field_id: str, new_status: str) -> None:
    row[f"{field_id}__status"] = new_status
    if _is_multi(row, field_id):
        for c in list(row.keys()):
            if c.startswith(f"{field_id}__") and not c.endswith("__status"):
                row[c] = None if new_status == "NOT_ASKED" else False
    elif field_id in row:
        row[field_id] = None


def _perturb_option_order(row: dict, rng: RowRng) -> dict:
    # Documented no-op: this corpus stores chosen optionIds, not display order,
    # so option-order permutation has no representable effect on the flattened
    # feature row. Kept as an explicit, labelled identity transform rather than
    # silently dropped, so the eval report can say why its delta is always zero.
    out = dict(row)
    out["perturbation_note"] = "no representable effect at this schema layer"
    return out


def _perturb_answered_to_unknown(row: dict, rng: RowRng) -> dict:
    out = dict(row)
    candidates = sorted(_status_field_ids(out))
    if not candidates:
        return out
    field_id = rng.choice("perturb::field_pick", candidates)
    _clear_field(out, field_id, "UNKNOWN")
    return out


def _perturb_single_field_drop(row: dict, rng: RowRng) -> dict:
    out = dict(row)
    candidates = sorted(_status_field_ids(out))
    if not candidates:
        return out
    field_id = rng.choice("perturb::drop_field_pick", candidates)
    _clear_field(out, field_id, "NOT_ASKED")
    return out


def _perturb_provenance_flip(row: dict, rng: RowRng) -> dict:
    out = dict(row)
    measured = [v for v in VITALS if out.get(f"{v}_provenance") == DEVICE_MEASURED]
    if not measured:
        return out
    vital = rng.choice("perturb::vital_pick", sorted(measured))
    out[f"{vital}_provenance"] = MANUAL_ENTERED
    return out


def _perturb_measurement_resample(row: dict, rng: RowRng) -> dict:
    out = dict(row)
    measured = [v for v in VITALS if out.get(f"{v}_provenance") in (DEVICE_MEASURED, MANUAL_ENTERED)]
    if not measured:
        return out
    vital = rng.choice("perturb::resample_vital_pick", sorted(measured))
    true_value = out[f"{vital}_true"]
    out[vital] = rng.normal(f"perturb::resample::{vital}", true_value, NOISE_SD[vital])
    return out


_OPS = {
    "option_order_permutation": _perturb_option_order,
    "answered_to_unknown": _perturb_answered_to_unknown,
    "single_field_drop": _perturb_single_field_drop,
    "device_to_manual_provenance_flip": _perturb_provenance_flip,
    "measurement_error_resample": _perturb_measurement_resample,
}


def build_perturbation_set(rows: List[dict], perturb_master_seed: str) -> List[dict]:
    out: List[dict] = []
    for row in rows:
        row_id = row["row_id"]
        for op_name, op_fn in _OPS.items():
            rng = RowRng(perturb_master_seed, f"{row_id}::{op_name}")
            perturbed = op_fn(row, rng)
            perturbed["perturbation_operator"] = op_name
            perturbed["original_row_id"] = row_id
            perturbed["row_id"] = f"{row_id}::perturb::{op_name}"
            perturbed["master_seed"] = perturb_master_seed
            out.append(perturbed)
    return out
