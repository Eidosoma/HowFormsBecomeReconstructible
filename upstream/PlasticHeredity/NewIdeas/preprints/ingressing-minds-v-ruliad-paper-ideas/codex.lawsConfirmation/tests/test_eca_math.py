import math

from laws_confirmation.eca_math import (
    atlas_null_variants,
    canonical_rule,
    canonical_rules,
    eca_edges,
    jaccard,
    unimodal,
)


def test_canonical_rule_contract():
    assert len(canonical_rules()) == 88
    assert canonical_rule(110) == 110
    assert {rule for rule in (110, 124, 137, 193) if canonical_rule(rule) == 110} == {
        110,
        124,
        137,
        193,
    }


def test_jaccard_empty_convention_is_explicit():
    assert jaccard(set(), set()) == 1.0
    assert jaccard(set(), set(), empty_empty=0.0) == 0.0
    assert jaccard({1, 2}, {2, 3}) == 1 / 3


def test_unimodal_tolerance_changes_small_reversal():
    values = [0.1, 0.2, 0.195, 0.21]
    assert not unimodal(values, 0.0)
    assert unimodal(values, 0.01)


def test_null_variants_do_not_hide_empty_pairs():
    libraries = {0: set(), 1: set(), 2: {1}, 3: {1}}
    strict = {rule: 0.0 for rule in libraries}
    edges = ((0, 1), (2, 3))
    source_pairs = ((0, 1), (0, 2))
    result = atlas_null_variants(
        libraries, edges, tuple(libraries), source_pairs, strict
    )
    assert result["source_convention"]["adjacent_mean"] == 1.0
    assert result["exclude_empty_empty"]["adjacent_mean"] == 1.0
    assert result["both_nonempty"]["adjacent_mean"] == 1.0
    assert result["pair_counts"]["edges_excluding_empty_empty"] == 1
