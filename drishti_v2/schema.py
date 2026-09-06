"""
drishti_v2/schema.py
=====================
The branch schema and tree-walk engine (questionnaire-tree-design-memo.md
section 1, dataset-regeneration-design-memo.md section 2.2 stage 3).

Three node types, matching the memo exactly: QuestionNode, GatewayNode,
TerminalNode. A fourth, SubtreeRefNode, is added here as the mechanism for
"cross-links are references, never copies" (tree memo section 5, point 1) --
it is not a new node type in the clinical sense, it is how one fixed DAG
splices into another without duplicating it.

Two build decisions not spelled out node-by-node in the memo, stated here:

1. The UNKNOWN nuisance channel (memo section 2.4) is a per-node constant
   rate (`unknown_rate`), declared with its own provenance, independent of
   condition/severity by construction -- it is never looked up from the
   condition-conditioned answer model, so it cannot leak by accident.
2. A node may carry a `guard`: a callable over already-collected fields that
   decides whether the node is even reached (e.g. FV-08 cough_ge_2_weeks is
   only asked when FV-07 included as_cough; FV-12 pregnancy_status only when
   sex==F and age in [15,49]). When the guard is false the field resolves to
   NOT_ASKED and no RNG stream is drawn for it -- this is what keeps
   NOT_ASKED "a deterministic function of prior answers" (tree memo 1.5)
   rather than a coin flip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Union

DISPOSITIONS = ("PHYSICIAN_REVIEW_MANDATORY", "REFER_URGENT", "REFER_EMERGENCY")
_RANK = {name: i for i, name in enumerate(DISPOSITIONS)}


def max_disposition(a: str, b: str) -> str:
    return DISPOSITIONS[max(_RANK[a], _RANK[b])]


@dataclass(frozen=True)
class FieldValue:
    fieldId: str
    status: str  # ANSWERED | UNKNOWN | NOT_ASKED
    value: object
    provenance: Optional[str]  # TAP | PREFILL_MEASURED | VOICE_CONFIRMED | VOICE_EDITED | None


@dataclass(frozen=True)
class AnswerOption:
    optionId: str
    displayText: str
    next: Optional[str] = None       # None => use node.default_next (BR-1: real options set this explicitly)
    raisesTo: Optional[str] = None
    valueToken: Optional[str] = None


@dataclass(frozen=True)
class QuestionNode:
    nodeId: str
    fieldId: str
    answerType: str  # SINGLE_CHOICE | MULTI_CHOICE
    options: List[AnswerOption]
    default_next: str
    unknown_option: str
    unknown_rate: float
    unknown_provenance: dict
    none_option: Optional[str] = None       # MULTI_CHOICE only (BR-2)
    prefillFrom: Optional[str] = None
    guard: Optional[Callable[[Dict[str, FieldValue]], bool]] = None

    def __post_init__(self):
        if self.answerType not in ("SINGLE_CHOICE", "MULTI_CHOICE"):
            raise ValueError(f"{self.nodeId}: unsupported answerType {self.answerType!r}")
        if self.answerType == "MULTI_CHOICE" and not self.none_option:
            raise ValueError(f"{self.nodeId}: MULTI_CHOICE requires none_option (BR-2)")
        if not (0.0 <= self.unknown_rate <= 1.0):
            raise ValueError(f"{self.nodeId}: unknown_rate {self.unknown_rate} out of [0,1]")
        prov = self.unknown_provenance or {}
        for k in ("sourceType", "source", "declaredOn"):
            if not prov.get(k):
                raise ValueError(f"{self.nodeId}: unknown_provenance missing {k!r}")


@dataclass(frozen=True)
class GatewayNode:
    nodeId: str
    gatewayId: str
    rule: Callable[[Dict[str, FieldValue], dict], bool]
    next: str
    raisesTo: Optional[str] = None
    routeTo: Optional[str] = None
    severeConditions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class TerminalNode:
    nodeId: str


@dataclass(frozen=True)
class SubtreeRefNode:
    nodeId: str
    subtree_nodes: Dict[str, object]
    entry: str
    returnNext: str


Node = Union[QuestionNode, GatewayNode, TerminalNode, SubtreeRefNode]


@dataclass(frozen=True)
class BranchOutput:
    categoryId: str
    branchVersion: str
    pathTaken: List[str]
    fields: Dict[str, FieldValue]
    dispositionFloor: str
    firedGateways: List[dict]
    routedTo: Optional[str]
    attachments: List[dict]


@dataclass(frozen=True)
class BranchDef:
    categoryId: str
    version: str
    requiredDisposition: str
    nodes: Dict[str, Node]
    entry: str

    def all_field_ids(self) -> List[str]:
        out = []
        def walk(nodes):
            for n in nodes.values():
                if isinstance(n, QuestionNode) and n.fieldId not in out:
                    out.append(n.fieldId)
                elif isinstance(n, SubtreeRefNode):
                    walk(n.subtree_nodes)
        walk(self.nodes)
        return out


# ---- field-access helpers for gateway rules -------------------------------

def value_of(fields: Dict[str, FieldValue], field_id: str):
    fv = fields.get(field_id)
    return fv.value if fv is not None else None


def equals(fields: Dict[str, FieldValue], field_id: str, val) -> bool:
    return value_of(fields, field_id) == val


def contains(fields: Dict[str, FieldValue], field_id: str, opt) -> bool:
    v = value_of(fields, field_id)
    if v is None:
        return False
    if isinstance(v, (frozenset, set)):
        return opt in v
    return v == opt


def any_of(fields: Dict[str, FieldValue], field_id: str, opts) -> bool:
    return any(contains(fields, field_id, o) for o in opts)


def not_in(fields: Dict[str, FieldValue], field_id: str, excluded) -> bool:
    v = value_of(fields, field_id)
    if v is None:
        return False
    if isinstance(v, (frozenset, set)):
        return len(v - set(excluded)) > 0
    return v not in excluded


def collect_multi_fields(branch: BranchDef) -> Dict[str, List[str]]:
    """fieldId -> real optionIds (excluding none/unknown sentinels), for every
    MULTI_CHOICE node in the branch (including spliced subtrees). Used to
    expand a MULTI field into one boolean column per optionId (memo 7.1)."""
    out: Dict[str, List[str]] = {}

    def walk(nodes):
        for n in nodes.values():
            if isinstance(n, QuestionNode) and n.answerType == "MULTI_CHOICE":
                out[n.fieldId] = [o.optionId for o in n.options]
            elif isinstance(n, SubtreeRefNode):
                walk(n.subtree_nodes)

    walk(branch.nodes)
    return out


# ---- the walker -------------------------------------------------------------

def _option_next(node: QuestionNode, chosen_ids) -> Optional[str]:
    """chosen_ids: a single optionId (SINGLE_CHOICE) or an iterable (MULTI_CHOICE)."""
    if isinstance(chosen_ids, (frozenset, set)):
        for opt in node.options:
            if opt.optionId in chosen_ids and opt.next:
                return opt.next
        return None
    for opt in node.options:
        if opt.optionId == chosen_ids:
            return opt.next
    return None


def walk_branch(branch: BranchDef, condition_id: str, severity_band: str, answer_model,
                 rng, context: dict, prefilled_fields: Optional[Dict[str, FieldValue]] = None) -> BranchOutput:
    """
    context: a per-row dict available to every GatewayNode.rule(fields, context)
    call. Carries {"vitals": Dict[str, VitalTriple], "age_years": int, "sex": str,
    "facility_tier": str, ...} -- whatever covariates the branch's gateways need
    that are not themselves tree fields.
    """
    fields: Dict[str, FieldValue] = dict(prefilled_fields or {})
    disposition = branch.requiredDisposition
    path: List[str] = []
    fired_gateways: List[dict] = []
    routed_to: Optional[str] = None
    attachments: List[dict] = []

    stack = []  # (node_dict, return_next)
    node_dict: Dict[str, Node] = branch.nodes
    current = branch.entry

    _MAX_STEPS = 200  # a well-formed DAG never needs this many; a runaway is a bug, not a slow path
    for _step in range(_MAX_STEPS):
        node = node_dict[current]
        path.append(node.nodeId)

        if isinstance(node, TerminalNode):
            if stack:
                node_dict, current = stack.pop()
                continue
            break

        if isinstance(node, SubtreeRefNode):
            stack.append((node_dict, node.returnNext))
            node_dict = node.subtree_nodes
            current = node.entry
            continue

        if isinstance(node, GatewayNode):
            fires = bool(node.rule(fields, context))
            if fires:
                if node.raisesTo:
                    disposition = max_disposition(disposition, node.raisesTo)
                fired_gateways.append({
                    "gatewayId": node.gatewayId,
                    "ruleAsEvaluated": True,
                    "severeConditions": list(node.severeConditions),
                })
                if node.routeTo:
                    routed_to = node.routeTo
                    break
            current = node.next
            continue

        # QuestionNode
        if node.guard is not None and not node.guard(fields):
            fields[node.fieldId] = FieldValue(node.fieldId, "NOT_ASKED", None, None)
            current = node.default_next
            continue

        if node.prefillFrom is not None and node.prefillFrom in fields \
                and fields[node.prefillFrom].status == "ANSWERED":
            current = node.default_next
            continue

        is_unknown = rng.bernoulli(f"unknown::{node.nodeId}", node.unknown_rate)

        if node.answerType == "SINGLE_CHOICE":
            if is_unknown:
                value, status = node.unknown_option, "UNKNOWN"
            else:
                value = answer_model.draw_categorical(
                    rng, node.nodeId, condition_id, severity_band, f"answer::{node.nodeId}")
                status = "ANSWERED"
            fields[node.fieldId] = FieldValue(node.fieldId, status, value, "TAP")
            if node.fieldId == "attachment_photo_present" and value == "ph_taken":
                attachments.append({"type": "AFFECTED_AREA_PHOTO"})
            current = _option_next(node, value) or node.default_next
        else:  # MULTI_CHOICE
            if is_unknown:
                selected, status = frozenset({node.unknown_option}), "UNKNOWN"
            else:
                selected = answer_model.draw_multi(
                    rng, node.nodeId, condition_id, severity_band, f"answer::{node.nodeId}")
                if not selected:
                    selected = frozenset({node.none_option})
                status = "ANSWERED"
            fields[node.fieldId] = FieldValue(node.fieldId, status, selected, "TAP")
            current = _option_next(node, selected) or node.default_next
    else:
        raise RuntimeError(f"walk_branch exceeded {_MAX_STEPS} steps for category "
                            f"{branch.categoryId!r} (condition={condition_id!r}, "
                            f"severity={severity_band!r}) -- likely a cycle in the branch DAG. "
                            f"path so far: {path}")

    for fid in branch.all_field_ids():
        if fid not in fields:
            fields[fid] = FieldValue(fid, "NOT_ASKED", None, None)

    return BranchOutput(branch.categoryId, branch.version, path, fields,
                         disposition, fired_gateways, routed_to, attachments)
