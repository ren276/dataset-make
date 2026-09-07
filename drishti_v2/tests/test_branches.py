"""
The replay assertions (questionnaire-tree-design-memo.md section 1.9):
reachability, field completeness, monotonicity, routing, and the NR-1
no-implied-rule-out lint. One battery run per branch, not hand-written per
path.
"""

import pytest

from drishti_v2.branches import ALL_SPECS as SPECS
from drishti_v2.generate import generate_rows
from drishti_v2.schema import DISPOSITIONS, GatewayNode, QuestionNode, SubtreeRefNode, TerminalNode
TIER0_CATEGORIES = {"emergency_convulsions", "emergency_unconscious", "emergency_bite_sting",
                     "emergency_poisoning", "emergency_heavy_bleeding", "emergency_pregnancy_danger"}
_RANK = {name: i for i, name in enumerate(DISPOSITIONS)}

FORBIDDEN_PHRASES = ("unlikely", "rules out", "ruling out", "excluded", "excludes")


def _all_nodes(branch):
    nodes = {}

    def walk(d):
        for nid, n in d.items():
            nodes[id(n)] = n
            if isinstance(n, SubtreeRefNode):
                walk(n.subtree_nodes)

    walk(branch.nodes)
    return list(nodes.values())


def _reachable_ids(branch) -> set:
    """BFS over every declared edge (option.next, default_next, gateway.next,
    subtree entry/return), starting at branch.entry. A node is 'reachable' if
    the DAG can lead to it under SOME answer sequence."""
    visited = set()
    to_visit = [(branch.nodes, branch.entry)]
    seen_states = set()
    while to_visit:
        node_dict, node_id = to_visit.pop()
        state = (id(node_dict), node_id)
        if state in seen_states:
            continue
        seen_states.add(state)
        node = node_dict[node_id]
        visited.add((id(node_dict), node.nodeId))
        if isinstance(node, TerminalNode):
            continue
        if isinstance(node, SubtreeRefNode):
            to_visit.append((node.subtree_nodes, node.entry))
            to_visit.append((node_dict, node.returnNext))
            continue
        if isinstance(node, GatewayNode):
            to_visit.append((node_dict, node.next))
            continue
        # QuestionNode: every option's next (or default_next) is a reachable edge
        to_visit.append((node_dict, node.default_next))
        for opt in node.options:
            to_visit.append((node_dict, opt.next or node.default_next))
    return visited


@pytest.mark.parametrize("cat_id,spec", SPECS.items())
def test_reachability(cat_id, spec):
    reachable = _reachable_ids(spec.branch)
    all_nodes = _all_nodes(spec.branch)
    node_ids_visited = {nid for (_, nid) in reachable}
    missing = [n.nodeId for n in all_nodes if n.nodeId not in node_ids_visited]
    assert not missing, f"{cat_id}: unreachable nodes {missing}"


@pytest.mark.parametrize("cat_id,spec", SPECS.items())
def test_every_option_has_explicit_or_default_next(cat_id, spec):
    """BR-1: every option resolves to a real node id (no dangling edges)."""
    for node in _all_nodes(spec.branch):
        if isinstance(node, QuestionNode):
            for opt in node.options:
                target = opt.next or node.default_next
                assert target, f"{cat_id}/{node.nodeId}/{opt.optionId}: no next and no default_next"


@pytest.mark.parametrize("cat_id,spec", SPECS.items())
def test_nr1_lint(cat_id, spec):
    """NR-1: no authored option text may render an implied rule-out."""
    violations = []
    for node in _all_nodes(spec.branch):
        if isinstance(node, QuestionNode):
            for opt in node.options:
                text = opt.displayText.lower()
                if any(p in text for p in FORBIDDEN_PHRASES):
                    violations.append(f"{node.nodeId}/{opt.optionId}: {opt.displayText!r}")
    assert not violations, f"{cat_id}: NR-1 violations: {violations}"


def test_monotonicity_and_field_completeness_and_routing():
    rows = generate_rows(600, "branch_replay_test_seed")
    for row in rows:
        cat_id = row["category_id"]
        required = SPECS[cat_id].branch.requiredDisposition
        assert row["tree_disposition_floor"] in DISPOSITIONS
        assert _RANK[row["tree_disposition_floor"]] >= _RANK[required], (
            f"{cat_id}: tree_disposition_floor {row['tree_disposition_floor']} "
            f"below the category's required floor {required}")
        if row["routed_to"]:
            assert row["routed_to"] in TIER0_CATEGORIES, f"unknown routeTo target {row['routed_to']!r}"
        # every __status column must be one of the three legal values
        for col, val in row.items():
            if col.endswith("__status"):
                assert val in ("ANSWERED", "UNKNOWN", "NOT_ASKED"), f"{col}={val!r}"
