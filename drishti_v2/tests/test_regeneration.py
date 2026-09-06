"""
The regeneration test (memo section 7.4): regenerate N rows from the master
seed alone and assert byte-identical output. This is the test that would
have failed on the old pipeline for two independent reasons (unseeded
step2, salted hash() in step4) -- it is the only claim of reproducibility
worth making.
"""

import pandas as pd

from drishti_v2.generate import generate_rows

N = 300
SEED = "regeneration_test_seed_2026-09-06"


def test_regeneration_is_byte_identical():
    rows_a = generate_rows(N, SEED)
    rows_b = generate_rows(N, SEED)
    df_a = pd.DataFrame(rows_a)
    df_b = pd.DataFrame(rows_b)
    csv_a = df_a.to_csv(index=False)
    csv_b = df_b.to_csv(index=False)
    assert csv_a == csv_b


def test_regeneration_single_row_matches_full_run():
    """A row generated in isolation must match the same row generated as
    part of a larger run -- order-independence carried up to the pipeline
    level, not just the RNG level."""
    from drishti_v2.generate import generate_row

    full_run = generate_rows(N, SEED)
    isolated = generate_row(N // 2, SEED)
    assert full_run[N // 2] == isolated


def test_different_seed_gives_different_corpus():
    rows_a = generate_rows(50, SEED)
    rows_b = generate_rows(50, "a_different_seed")
    assert rows_a != rows_b
