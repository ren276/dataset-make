"""RNG determinism and stream independence (memo section 7.2)."""

from drishti_v2.rng import RowRng, stream_u


def test_same_row_same_seed_is_identical():
    a = RowRng("seedA", "row_0000001")
    b = RowRng("seedA", "row_0000001")
    assert a.u("category_id") == b.u("category_id")
    assert a.uniform("x", 0, 100) == b.uniform("x", 0, 100)
    assert a.normal("y", 10, 2) == b.normal("y", 10, 2)


def test_different_seed_differs():
    a = RowRng("seedA", "row_0000001")
    b = RowRng("seedB", "row_0000001")
    assert a.u("category_id") != b.u("category_id")


def test_different_row_id_differs():
    a = RowRng("seedA", "row_0000001")
    b = RowRng("seedA", "row_0000002")
    assert a.u("category_id") != b.u("category_id")


def test_order_independence():
    """Row 7412's draws must not depend on what was generated before it --
    there is no shared state, so computing it in isolation must match
    computing it as part of a larger loop."""
    row_id = "row_0007412"
    solo = RowRng("seedA", row_id).u("some_stream")
    # simulate "other rows" being touched first; must not perturb row 7412
    for i in range(50):
        RowRng("seedA", f"row_{i:07d}").u("some_stream")
    after = RowRng("seedA", row_id).u("some_stream")
    assert solo == after


def test_new_stream_does_not_perturb_existing_stream():
    rng = RowRng("seedA", "row_0000001")
    before = rng.u("category_id")
    rng.u("a_brand_new_stream_added_later")
    after = rng.u("category_id")
    assert before == after


def test_choice_is_deterministic_and_respects_weights():
    rng = RowRng("seedA", "row_0000001")
    options = ["x", "y", "z"]
    weights = [0.1, 0.1, 0.8]
    counts = {"x": 0, "y": 0, "z": 0}
    for i in range(2000):
        r = RowRng("seedA", f"row_{i:07d}")
        counts[r.choice("pick", options, weights)] += 1
    total = sum(counts.values())
    assert abs(counts["z"] / total - 0.8) < 0.05


def test_stream_u_matches_manual_hash():
    import hashlib
    master, row, stream = "m", "r1", "s1"
    expected = int(hashlib.sha256(f"{master}|{row}|{stream}".encode()).hexdigest()[:12], 16) / float(16 ** 12)
    assert stream_u(master, row, stream) == expected
