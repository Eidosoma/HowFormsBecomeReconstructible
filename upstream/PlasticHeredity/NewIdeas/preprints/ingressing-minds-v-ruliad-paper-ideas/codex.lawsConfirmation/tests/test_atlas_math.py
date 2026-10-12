import numpy as np

from laws_confirmation.atlas_math import (
    average_rank_array,
    base_k_digits,
    cluster_category_stats,
    mean_nearest_distance,
    rank_cdf_columns,
)


def test_average_ranks_and_rank_cdf_preserve_ties():
    values = np.asarray([4.0, 1.0, 1.0, 9.0])
    assert np.array_equal(average_rank_array(values), [3.0, 1.5, 1.5, 4.0])
    cloud = rank_cdf_columns(np.column_stack([values, values[::-1]]))
    assert np.allclose(cloud.mean(axis=0), 0.5)
    assert cloud[1, 0] == cloud[2, 0]


def test_base_k_digits_use_little_endian_row_major_encoding():
    # 86 = 2 + 1*4 + 1*16 + 1*64 in base four.
    assert np.array_equal(base_k_digits(86, entries=4, base=4), [2, 1, 1, 1])


def test_cluster_categories_se_worlds_from_formalisms():
    clusters = np.asarray([1, 1, 1, 2, 2, 3])
    worlds = np.asarray(["g1", "poly", "grn", "g2", "g3", "poly"])
    mapping = {
        "g1": "gard",
        "g2": "gard",
        "g3": "gard",
        "poly": "polymer",
        "grn": "gene",
    }
    result = cluster_category_stats(clusters, worlds, mapping)
    assert result["categories"]["source_at_least_3_worlds"]["n_clusters"] == 1
    assert result["categories"]["all_3_baseline_formalisms"]["n_clusters"] == 1
    assert result["categories"]["cross_formalism_at_least_2"]["n_clusters"] == 1


def test_mean_nearest_distance_is_euclidean():
    points = np.asarray([[0.0, 0.0], [2.0, 0.0]])
    reference = np.asarray([[0.0, 1.0], [3.0, 0.0]])
    assert mean_nearest_distance(points, reference) == 1.0
