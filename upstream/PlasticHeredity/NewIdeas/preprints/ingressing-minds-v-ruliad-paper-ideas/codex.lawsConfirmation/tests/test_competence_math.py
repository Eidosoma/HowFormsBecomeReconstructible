import math

import pytest

from laws_confirmation.competence_math import (
    axis_diagnostics,
    exact_binomial_two_sided_half,
    recalculate_grafts,
    wilson_interval,
)


def test_exact_binomial_half_is_two_sided_and_symmetric():
    assert exact_binomial_two_sided_half(3, 3) == 0.25
    assert exact_binomial_two_sided_half(0, 3) == 0.25
    assert exact_binomial_two_sided_half(2, 3) == 1.0


def test_wilson_interval_contains_observed_proportion():
    low, high = wilson_interval(48, 75)
    assert low < 48 / 75 < high
    assert 0 <= low < high <= 1


def test_axis_diagnostics_preserves_clustered_rows_and_is_deterministic():
    rows = []
    for tissue in range(4):
        for cohort, shift in (("band", 0.0), ("under", 10.0), ("over", 20.0)):
            rows.append(
                {
                    "cohort": cohort,
                    "tissue": tissue,
                    "fidelity": shift + tissue,
                    "conversion": shift + tissue,
                }
            )
    first = axis_diagnostics(rows, seed=9, draws=32)
    second = axis_diagnostics(rows, seed=9, draws=32)
    assert first == second
    assert first["overall"]["rho"] == pytest.approx(1.0)
    assert first["partial_rank_controlling_cohort"] == pytest.approx(1.0)
    assert first["tissue_cluster_bootstrap"]["n_clusters"] == 4
    assert first["subgroups"]["balanced_triplets_48"]["n"] == 12
    permutation = first["within_cohort_permutation"]
    assert permutation["two_sided_p_plus_one"] == min(
        1.0,
        2
        * min(
            permutation["upper_tail_p_plus_one"],
            permutation["lower_tail_p_plus_one"],
        ),
    )


def test_graft_recalculation_keeps_unresolved_distinct_from_chimeras():
    entries = [
        {
            "tissue": 0,
            "0.35": {"n": 10, "resolved": 3, "rw_wins": 1, "wild_wins": 2, "chimeras": 1},
            "0.5": {"n": 10, "resolved": 4, "rw_wins": 3, "wild_wins": 1, "chimeras": 0},
            "0.65": {"n": 10, "resolved": 2, "rw_wins": 1, "wild_wins": 1, "chimeras": 0},
        },
        {
            "tissue": 1,
            "0.35": {"n": 10, "resolved": 2, "rw_wins": 1, "wild_wins": 1, "chimeras": 0},
            "0.5": {"n": 10, "resolved": 2, "rw_wins": 1, "wild_wins": 1, "chimeras": 0},
            "0.65": {"n": 10, "resolved": 2, "rw_wins": 0, "wild_wins": 2, "chimeras": 0},
        },
    ]
    result = recalculate_grafts(entries, seed=3, draws=32)
    assert result["overall"] == {
        "n": 60,
        "resolved": 15,
        "resolved_rate": 0.25,
        "unresolved": 45,
        "unresolved_rate": 0.75,
        "chimeras": 1,
        "chimera_rate": 1 / 60,
    }
    assert result["source_projection"]["rw_win_rate_5050"] == 4 / 6
    assert result["implemented_column_shares"]["0.35"]["effective_wild_share"] == 0.375
    assert result["implemented_column_shares"]["0.65"]["effective_wild_share"] == 0.625
    assert math.isfinite(
        result["fifty_fifty_resolved_contests"]["tissue_cluster_bootstrap"]
        ["percentile_95"][0]
    )
