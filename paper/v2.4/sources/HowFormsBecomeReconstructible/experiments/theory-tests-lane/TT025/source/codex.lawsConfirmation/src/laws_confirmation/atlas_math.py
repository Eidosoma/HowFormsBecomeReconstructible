"""Transparent atlas calculations shared by the L03 retained audit.

The functions in this module deliberately avoid importing historical
experiment packages. Historical arrays are inputs; clustering summaries,
placement distances, nulls, and metric comparisons are rebuilt here.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import math
from typing import Hashable, Mapping, Sequence

import numpy as np

from .eca_math import seed_rng
from .stats import spearman


def hash_fraction(tag: str, value: int) -> float:
    """Match the repository's frozen SHA-256 split without importing it."""

    digest = hashlib.sha256(f"{tag}:{value}".encode()).digest()
    return int.from_bytes(digest[:8], "little") / 2**64


def average_rank_array(values: np.ndarray) -> np.ndarray:
    """One-based average ranks matching scipy ``rankdata(method='average')``."""

    vector = np.asarray(values)
    if vector.ndim != 1:
        raise ValueError("average_rank_array expects one dimension")
    order = np.argsort(vector, kind="stable")
    ranks = np.empty(len(vector), dtype=np.float64)
    start = 0
    while start < len(order):
        end = start + 1
        value = vector[order[start]]
        while end < len(order) and vector[order[end]] == value:
            end += 1
        ranks[order[start:end]] = ((start + 1) + end) / 2.0
        start = end
    return ranks


def rank_cdf_columns(raw: np.ndarray) -> np.ndarray:
    """Rank-CDF normalize every column with average ties."""

    matrix = np.asarray(raw, dtype=np.float64)
    if matrix.ndim != 2 or not len(matrix):
        raise ValueError("rank_cdf_columns expects a non-empty matrix")
    result = np.empty_like(matrix)
    for column in range(matrix.shape[1]):
        result[:, column] = (average_rank_array(matrix[:, column]) - 0.5) / len(matrix)
    return result


def pca_shape(cloud: np.ndarray) -> dict[str, object]:
    """Recalculate the source PCA spectrum and participation ratio."""

    matrix = np.asarray(cloud, dtype=np.float64)
    centered = matrix - matrix.mean(axis=0)
    eigenvalues = np.linalg.svd(centered, compute_uv=False) ** 2
    shares = eigenvalues / eigenvalues.sum()
    return {
        "variance_shares": [float(value) for value in shares],
        "participation_ratio": float(1.0 / np.sum(shares**2)),
    }


def two_nn_dimension(
    cloud: np.ndarray,
    *,
    tag: str,
    sample: int = 2_000,
    block_size: int = 128,
) -> dict[str, float | int]:
    """Rebuild the Facco two-NN estimate with bounded temporary memory."""

    matrix = np.asarray(cloud, dtype=np.float64)
    rng = seed_rng(tag, len(matrix))
    if len(matrix) > sample:
        matrix = matrix[rng.choice(len(matrix), sample, replace=False)]
    nearest: list[np.ndarray] = []
    for start in range(0, len(matrix), block_size):
        block = matrix[start : start + block_size]
        squared = np.sum((block[:, None, :] - matrix[None, :, :]) ** 2, axis=2)
        first_three = np.partition(squared, 2, axis=1)[:, :3]
        first_three.sort(axis=1)
        nearest.append(np.sqrt(first_three[:, 1:3]))
    distances = np.vstack(nearest)
    valid = distances[:, 0] > 0
    ratios = distances[valid, 1] / distances[valid, 0]
    return {
        "dimension": float(len(ratios) / np.sum(np.log(ratios))),
        "sample_size": int(len(matrix)),
        "valid_rows": int(valid.sum()),
        "zero_nearest_rows_excluded": int((~valid).sum()),
    }


def cluster_category_stats(
    clusters: np.ndarray,
    worlds: np.ndarray,
    formalism_by_world: Mapping[str, str],
) -> dict[str, object]:
    """Report source and stricter meanings of cross-world sharing."""

    clusters = np.asarray(clusters)
    worlds = np.asarray(worlds).astype(str)
    if len(clusters) != len(worlds):
        raise ValueError("cluster/world length mismatch")
    unique_clusters = np.unique(clusters)
    unique_worlds = sorted(set(worlds))
    unique_formalisms = sorted({formalism_by_world[world] for world in unique_worlds})
    cluster_worlds = {
        int(cluster): set(worlds[clusters == cluster]) for cluster in unique_clusters
    }
    cluster_formalisms = {
        cluster: {formalism_by_world[world] for world in members}
        for cluster, members in cluster_worlds.items()
    }

    predicates = {
        "source_at_least_3_worlds": lambda cluster: len(cluster_worlds[cluster]) >= 3,
        "cross_formalism_at_least_2": lambda cluster: len(cluster_formalisms[cluster]) >= 2,
        "all_3_baseline_formalisms": lambda cluster: (
            len(cluster_formalisms[cluster]) == len(unique_formalisms)
        ),
        "all_6_baseline_worlds": lambda cluster: (
            len(cluster_worlds[cluster]) == len(unique_worlds)
        ),
    }
    categories: dict[str, object] = {}
    for name, predicate in predicates.items():
        qualifying = {int(cluster) for cluster in unique_clusters if predicate(int(cluster))}
        entity_mask = np.asarray([int(cluster) in qualifying for cluster in clusters])
        by_world = {
            world: float(entity_mask[worlds == world].mean()) for world in unique_worlds
        }
        categories[name] = {
            "n_clusters": len(qualifying),
            "entity_weighted_mass": float(entity_mask.mean()),
            "equal_world_weighted_mass": float(np.mean(list(by_world.values()))),
            "fraction_by_world": by_world,
        }
    return {
        "n_clusters": int(len(unique_clusters)),
        "worlds": unique_worlds,
        "formalisms": unique_formalisms,
        "categories": categories,
    }


def _null_distribution_summary(values: Sequence[float], observed: float) -> dict[str, object]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "observed": float(observed),
        "null_mean": float(array.mean()),
        "null_quantiles": {
            "q025": float(np.quantile(array, 0.025)),
            "q05": float(np.quantile(array, 0.05)),
            "q50": float(np.quantile(array, 0.5)),
            "q95": float(np.quantile(array, 0.95)),
            "q975": float(np.quantile(array, 0.975)),
        },
        "upper_tail_p": float((1 + np.sum(array >= observed)) / (len(array) + 1)),
        "lower_tail_p": float((1 + np.sum(array <= observed)) / (len(array) + 1)),
    }


def world_label_permutation_null(
    clusters: np.ndarray,
    worlds: np.ndarray,
    formalism_by_world: Mapping[str, str],
    *,
    draws: int,
    tag: str,
) -> dict[str, object]:
    """Permute world labels conditional on cluster and world sizes."""

    raw_clusters = np.asarray(clusters)
    world_names = np.asarray(worlds).astype(str)
    _, cluster_index = np.unique(raw_clusters, return_inverse=True)
    unique_worlds = sorted(set(world_names))
    world_lookup = {world: index for index, world in enumerate(unique_worlds)}
    world_index = np.asarray([world_lookup[world] for world in world_names], dtype=np.int16)
    formalisms = sorted({formalism_by_world[world] for world in unique_worlds})
    formalism_world_indices = [
        [world_lookup[world] for world in unique_worlds if formalism_by_world[world] == formalism]
        for formalism in formalisms
    ]
    observed_stats = cluster_category_stats(raw_clusters, world_names, formalism_by_world)
    observed_source = observed_stats["categories"]["source_at_least_3_worlds"][  # type: ignore[index]
        "entity_weighted_mass"
    ]
    observed_all_formalisms = observed_stats["categories"]["all_3_baseline_formalisms"][  # type: ignore[index]
        "entity_weighted_mass"
    ]
    observed_all_worlds = observed_stats["categories"]["all_6_baseline_worlds"][  # type: ignore[index]
        "entity_weighted_mass"
    ]

    rng = seed_rng(tag, len(cluster_index), draws)
    n_clusters = int(cluster_index.max()) + 1
    source_values: list[float] = []
    all_formalism_values: list[float] = []
    all_world_values: list[float] = []
    for _ in range(draws):
        permuted = rng.permutation(world_index)
        presence = np.stack(
            [
                np.bincount(
                    cluster_index,
                    weights=(permuted == world),
                    minlength=n_clusters,
                )
                > 0
                for world in range(len(unique_worlds))
            ]
        )
        n_worlds = presence.sum(axis=0)
        formalism_presence = np.stack(
            [presence[indices].any(axis=0) for indices in formalism_world_indices]
        )
        source_values.append(float((n_worlds[cluster_index] >= 3).mean()))
        all_world_values.append(float((n_worlds[cluster_index] == len(unique_worlds)).mean()))
        all_formalism_values.append(
            float((formalism_presence.sum(axis=0)[cluster_index] == len(formalisms)).mean())
        )
    return {
        "draws": draws,
        "namespace": tag,
        "source_at_least_3_worlds": _null_distribution_summary(
            source_values, float(observed_source)
        ),
        "all_3_baseline_formalisms": _null_distribution_summary(
            all_formalism_values, float(observed_all_formalisms)
        ),
        "all_6_baseline_worlds": _null_distribution_summary(
            all_world_values, float(observed_all_worlds)
        ),
    }


def centroids(
    cloud: np.ndarray,
    clusters: np.ndarray,
    worlds: np.ndarray,
    *,
    mode: str,
    gard_worlds: Sequence[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Build source, equal-world, or GARD-only reference centroids."""

    matrix = np.asarray(cloud, dtype=np.float64)
    clusters = np.asarray(clusters)
    worlds = np.asarray(worlds).astype(str)
    ids: list[int] = []
    rows: list[np.ndarray] = []
    for cluster in np.unique(clusters):
        mask = clusters == cluster
        if mode == "source_entity_weighted":
            value = matrix[mask].mean(axis=0)
        elif mode == "equal_world_weighted":
            value = np.mean(
                [matrix[mask & (worlds == world)].mean(axis=0) for world in sorted(set(worlds[mask]))],
                axis=0,
            )
        elif mode == "gard_only":
            gard_mask = mask & np.isin(worlds, list(gard_worlds))
            if not gard_mask.any():
                continue
            value = matrix[gard_mask].mean(axis=0)
        else:
            raise ValueError(f"unknown centroid mode: {mode}")
        ids.append(int(cluster))
        rows.append(np.asarray(value, dtype=np.float64))
    return np.asarray(ids, dtype=np.int64), np.vstack(rows)


def mean_nearest_distance(points: np.ndarray, reference_centroids: np.ndarray) -> float:
    """Mean Euclidean distance to the nearest centroid."""

    points = np.asarray(points, dtype=np.float64)
    reference = np.asarray(reference_centroids, dtype=np.float64)
    squared = (
        np.sum(points**2, axis=1)[:, None]
        + np.sum(reference**2, axis=1)[None, :]
        - 2.0 * points @ reference.T
    )
    np.maximum(squared, 0.0, out=squared)
    return float(np.sqrt(squared.min(axis=1)).mean())


def placement_nulls(
    cloud: np.ndarray,
    reference_centroids: np.ndarray,
    *,
    draws: int,
    tag: str,
    seed_parts: Sequence[Hashable],
) -> dict[str, object]:
    """Reproduce the source random-point and column-shuffle placement nulls."""

    matrix = np.asarray(cloud, dtype=np.float64)
    observed = mean_nearest_distance(matrix, reference_centroids)
    rng = seed_rng(tag, *seed_parts)
    random_values = np.asarray(
        [
            mean_nearest_distance(rng.random(matrix.shape), reference_centroids)
            for _ in range(draws)
        ]
    )
    shuffled_values = []
    for _ in range(draws):
        shuffled = matrix.copy()
        for column in range(shuffled.shape[1]):
            rng.shuffle(shuffled[:, column])
        shuffled_values.append(mean_nearest_distance(shuffled, reference_centroids))
    shuffled_array = np.asarray(shuffled_values)
    random_q05 = float(np.quantile(random_values, 0.05))
    shuffled_q05 = float(np.quantile(shuffled_array, 0.05))
    return {
        "n_entities": int(len(matrix)),
        "n_centroids": int(len(reference_centroids)),
        "draws": draws,
        "namespace": tag,
        "seed_parts": [str(part) for part in seed_parts],
        "observed": observed,
        "random_null_q05": random_q05,
        "shuffled_null_q05": shuffled_q05,
        "random_null_mean": float(random_values.mean()),
        "shuffled_null_mean": float(shuffled_array.mean()),
        "placement_beats_random_null": bool(observed < random_q05),
        "placement_beats_shuffled_null": bool(observed < shuffled_q05),
    }


def library_jaccard(left: set[tuple[int, ...]], right: set[tuple[int, ...]]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def libraries_from_supports(
    supports: np.ndarray, sizes: np.ndarray
) -> tuple[list[set[tuple[int, ...]]], Counter[tuple[int, ...]]]:
    """Rebuild non-empty libraries and assignment census from scale shards."""

    libraries: list[set[tuple[int, ...]]] = []
    census: Counter[tuple[int, ...]] = Counter()
    for rule in range(supports.shape[0]):
        library: set[tuple[int, ...]] = set()
        for launch in range(supports.shape[1]):
            size = int(sizes[rule, launch])
            form = tuple(int(value) for value in supports[rule, launch, :size])
            if form:
                library.add(form)
                census[form] += 1
        libraries.append(library)
    return libraries, census


def base_k_digits(rule: int, *, entries: int, base: int) -> np.ndarray:
    """Decode the repository's little-endian row-major rule identifier."""

    value = int(rule)
    result = np.empty(entries, dtype=np.int16)
    for index in range(entries):
        result[index] = value % base
        value //= base
    if value:
        raise ValueError("rule identifier exceeds requested digit width")
    return result


def scale_metric_comparison(
    rule_ids: np.ndarray,
    features: np.ndarray,
    libraries: Sequence[set[tuple[int, ...]]],
    *,
    n_types: int,
    n_min: int,
    beta_levels: int,
    dev_split_tag: str,
    metric_seed_tag: str,
    pair_count: int,
) -> dict[str, object]:
    """Rebuild the E7 learned-composite versus Hamming eval comparison."""

    rule_ids = np.asarray(rule_ids, dtype=np.int64)
    features = np.asarray(features, dtype=np.float64)
    digits = np.asarray(
        [
            base_k_digits(int(rule), entries=n_types * n_types, base=beta_levels)
            for rule in rule_ids
        ]
    )
    dev_mask = np.asarray(
        [hash_fraction(dev_split_tag, int(rule)) < 0.5 for rule in rule_ids]
    )
    rng = seed_rng(metric_seed_tag, n_types, n_min)

    def sample(mask: np.ndarray) -> list[tuple[int, int]]:
        eligible = np.flatnonzero(mask)
        if len(eligible) < 2:
            eligible = np.arange(len(rule_ids))
        return [
            tuple(int(value) for value in rng.choice(eligible, 2, replace=False))
            for _ in range(pair_count)
        ]

    def design(pairs: Sequence[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
        rows = []
        targets = []
        for left, right in pairs:
            digits_left, digits_right = digits[left], digits[right]
            hamming = float(np.sum(digits_left != digits_right))
            feature_gap = float(np.linalg.norm(features[left] - features[right]))
            support_left, support_right = digits_left > 0, digits_right > 0
            union = int(np.sum(support_left | support_right))
            support_distance = 1.0 - (
                float(np.sum(support_left & support_right) / union) if union else 1.0
            )
            diag_left = int(np.sum(np.diag(digits_left.reshape(n_types, n_types)) > 0))
            diag_right = int(np.sum(np.diag(digits_right.reshape(n_types, n_types)) > 0))
            rows.append([hamming, feature_gap, support_distance, abs(diag_left - diag_right)])
            targets.append(1.0 - library_jaccard(libraries[left], libraries[right]))
        return np.asarray(rows), np.asarray(targets)

    dev_pairs = sample(dev_mask)
    eval_pairs = sample(~dev_mask)
    x_dev, y_dev = design(dev_pairs)
    scale = np.maximum(x_dev.std(axis=0), 1e-12)
    weights, *_ = np.linalg.lstsq(
        np.column_stack([np.ones(len(x_dev)), x_dev / scale]), y_dev, rcond=None
    )
    x_eval, y_eval = design(eval_pairs)
    if np.ptp(y_eval) == 0:
        learned_rho = None
        hamming_rho = None
        improvement = None
    else:
        learned = np.column_stack([np.ones(len(x_eval)), x_eval / scale]) @ weights
        learned_rho = float(spearman(list(learned), list(y_eval)))
        hamming_rho = float(spearman(list(x_eval[:, 0]), list(y_eval)))
        improvement = float(learned_rho - hamming_rho)
    return {
        "pair_count_dev": pair_count,
        "pair_count_eval": pair_count,
        "n_dev_rules": int(dev_mask.sum()),
        "n_eval_rules": int((~dev_mask).sum()),
        "eval_spearman_learned": learned_rho,
        "eval_spearman_hamming": hamming_rho,
        "improvement": improvement,
        "weights_intercept_then_scaled_coordinates": [float(value) for value in weights],
        "coordinates": ["hamming", "feature_gap", "support_distance", "diag_gap"],
    }


def scale_universe_statistics(
    rule_ids: np.ndarray,
    features: np.ndarray,
    supports: np.ndarray,
    support_sizes: np.ndarray,
    edges: np.ndarray,
    *,
    n_types: int,
    n_min: int,
    beta_levels: int,
    metric_seed_tag: str,
    dev_split_tag: str,
    metric_pair_count: int,
) -> dict[str, object]:
    """Rebuild E7/E18 atlas laws from one universe's lower-level arrays."""

    rule_ids = np.asarray(rule_ids, dtype=np.int64)
    order = np.argsort(rule_ids, kind="stable")
    rule_ids = rule_ids[order]
    features = np.asarray(features)[order]
    supports = np.asarray(supports)[order]
    support_sizes = np.asarray(support_sizes)[order]
    libraries, census = libraries_from_supports(supports, support_sizes)
    index = {int(rule): position for position, rule in enumerate(rule_ids)}
    adjacent = [
        library_jaccard(libraries[index[int(left)]], libraries[index[int(right)]])
        for left, right in np.asarray(edges)
        if int(left) in index and int(right) in index
    ]
    rng = seed_rng(metric_seed_tag + "-random", n_types, n_min)
    random_values = []
    for _ in range(max(len(adjacent), 256)):
        left, right = rng.integers(0, len(rule_ids), 2)
        if left != right:
            random_values.append(library_jaccard(libraries[int(left)], libraries[int(right)]))
    adjacent_mean = float(np.mean(adjacent)) if adjacent else 0.0
    random_mean = float(np.mean(random_values)) if random_values else 0.0
    ordered_census = sorted(census.values(), reverse=True)
    take = max(1, len(ordered_census) // 10)
    tail = float(sum(ordered_census[:take]) / max(sum(ordered_census), 1))

    metric = scale_metric_comparison(
        rule_ids,
        features,
        libraries,
        n_types=n_types,
        n_min=n_min,
        beta_levels=beta_levels,
        dev_split_tag=dev_split_tag,
        metric_seed_tag=metric_seed_tag,
        pair_count=metric_pair_count,
    )
    return {
        "n_rules": int(len(rule_ids)),
        "n_launch": int(supports.shape[1]),
        "n_forms": int(len(census)),
        "adjacent_pairs": int(len(adjacent)),
        "random_pairs_retained": int(len(random_values)),
        "adjacent_mean_jaccard": adjacent_mean,
        "random_mean_jaccard": random_mean,
        "smoothness_ratio": float(adjacent_mean / random_mean) if random_mean > 0 else math.inf,
        "heavy_tail_top_decile_share": tail,
        "mean_library_size": float(np.mean([len(library) for library in libraries])),
        "metric": metric,
    }
