from laws_confirmation.stats import average_ranks, minimum_ranks, spearman


def test_rank_ties_match_expected_semantics():
    values = [3.0, 1.0, 1.0, 2.0]
    assert average_ranks(values) == [4.0, 1.5, 1.5, 3.0]
    assert average_ranks(values, descending=True) == [1.0, 3.5, 3.5, 2.0]
    assert minimum_ranks(values, descending=True) == [1, 3, 3, 2]


def test_spearman_handles_ties_and_reversal():
    assert spearman([1, 2, 3], [3, 2, 1]) == -1.0
    assert spearman([1, 1, 2], [3, 3, 4]) == 1.0


def test_minimum_and_average_ranks_make_tie_policy_visible():
    values = [5, 3, 3, 3, 1]
    assert minimum_ranks(values, descending=True)[1] == 2
    assert average_ranks(values, descending=True)[1] == 3.0
