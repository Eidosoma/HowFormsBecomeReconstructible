"""Independent ECA rule-space and atlas calculations.

These functions intentionally do not import any historical experiment package.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import itertools
import math
from typing import Iterable, Mapping, Sequence

import numpy as np

from .stats import mean, spearman


CLASS_1 = frozenset({0, 8, 32, 40, 128, 136, 160, 168})
CLASS_3_CORE = frozenset({18, 22, 30, 45, 60, 90, 105, 122, 126, 146, 150})
CLASS_4 = frozenset({41, 54, 106, 110})
DISPUTED = frozenset({26, 41, 54, 73, 106, 154})


def reflect_rule(rule: int) -> int:
    reflected = 0
    for neighbourhood in range(8):
        reverse = (
            ((neighbourhood & 1) << 2)
            | (neighbourhood & 2)
            | ((neighbourhood & 4) >> 2)
        )
        reflected |= ((rule >> reverse) & 1) << neighbourhood
    return reflected


def conjugate_rule(rule: int) -> int:
    conjugated = 0
    for neighbourhood in range(8):
        output = 1 - ((rule >> (7 - neighbourhood)) & 1)
        conjugated |= output << neighbourhood
    return conjugated


def canonical_rule(rule: int) -> int:
    reflected = reflect_rule(rule)
    conjugated = conjugate_rule(rule)
    return min(rule, reflected, conjugated, reflect_rule(conjugated))


def canonical_rules() -> tuple[int, ...]:
    return tuple(sorted({canonical_rule(rule) for rule in range(256)}))


def wolfram_class(rule: int) -> int:
    representative = canonical_rule(rule)
    if representative in CLASS_1:
        return 1
    if representative in CLASS_3_CORE:
        return 3
    if representative in CLASS_4:
        return 4
    return 2


def seed_rng(tag: str, *parts: int) -> np.random.Generator:
    digest = hashlib.sha256((tag + ":" + ":".join(map(str, parts))).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "little"))


def jaccard(left: set[int], right: set[int], *, empty_empty: float = 1.0) -> float:
    union = left | right
    return len(left & right) / len(union) if union else float(empty_empty)


def eca_edges(rules: Sequence[int]) -> tuple[tuple[int, int], ...]:
    rule_set = set(rules)
    edges = set()
    for rule in rules:
        for bit in range(8):
            neighbour = canonical_rule(rule ^ (1 << bit))
            if neighbour != rule and neighbour in rule_set:
                edges.add((min(rule, neighbour), max(rule, neighbour)))
    return tuple(sorted(edges))


def life_edges(rules: Sequence[int], n_bits: int = 17) -> tuple[tuple[int, int], ...]:
    rule_set = set(rules)
    edges = {
        (min(rule, rule ^ (1 << bit)), max(rule, rule ^ (1 << bit)))
        for rule in rules
        for bit in range(n_bits)
        if (rule ^ (1 << bit)) in rule_set and (rule ^ (1 << bit)) != rule
    }
    return tuple(sorted(edges))


def rule_descriptors(rule: int) -> tuple[float, float, float, float]:
    bits = tuple((rule >> index) & 1 for index in range(8))
    reflected = reflect_rule(rule)
    lambda_value = sum(bits) / 8.0
    asymmetry = (rule ^ reflected).bit_count() / 8.0
    quiescent = float(bits[0])
    sensitivity = 0
    for index in range(8):
        for bit in (4, 2, 1):
            sensitivity += bits[index] != bits[index ^ bit]
    return lambda_value, asymmetry, quiescent, sensitivity / 24.0


def euclidean(left: Sequence[float], right: Sequence[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def source_random_pairs(
    rules: Sequence[int], tag: str, seed_part: int, count: int
) -> tuple[tuple[int, int], ...]:
    rng = seed_rng(tag, seed_part)
    return draw_pairs(rules, rng, count)


def draw_pairs(
    rules: Sequence[int], rng: np.random.Generator, count: int
) -> tuple[tuple[int, int], ...]:
    pairs = []
    for _ in range(count):
        selected = rng.choice(len(rules), 2, replace=False)
        pairs.append((rules[int(selected[0])], rules[int(selected[1])]))
    return tuple(pairs)


def atlas_null_variants(
    libraries: Mapping[int, set[int]],
    edges: Sequence[tuple[int, int]],
    rules: Sequence[int],
    source_pairs: Sequence[tuple[int, int]],
    strict_by_rule: Mapping[int, float],
    strict_band: tuple[float, float] = (0.005, 0.5),
) -> dict:
    all_pairs = tuple(itertools.combinations(rules, 2))

    def pair_mean(pairs: Iterable[tuple[int, int]], *, empty_empty: float = 1.0) -> float:
        return mean(jaccard(libraries[a], libraries[b], empty_empty=empty_empty) for a, b in pairs)

    source_adjacent = pair_mean(edges)
    source_random = pair_mean(source_pairs)

    no_empty_empty_edges = [
        pair for pair in edges if libraries[pair[0]] or libraries[pair[1]]
    ]
    no_empty_empty_pairs = [
        pair for pair in all_pairs if libraries[pair[0]] or libraries[pair[1]]
    ]
    both_nonempty_edges = [
        pair for pair in edges if libraries[pair[0]] and libraries[pair[1]]
    ]
    both_nonempty_pairs = [
        pair for pair in all_pairs if libraries[pair[0]] and libraries[pair[1]]
    ]

    lo, hi = strict_band

    def capable(rule: int) -> bool:
        return lo <= strict_by_rule[rule] <= hi

    strata: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for pair in both_nonempty_pairs:
        strata[int(capable(pair[0])) + int(capable(pair[1]))].append(pair)
    stratum_means = {count: pair_mean(pairs) for count, pairs in strata.items()}
    matched_edges = [pair for pair in both_nonempty_edges if int(capable(pair[0])) + int(capable(pair[1])) in stratum_means]
    matched_null = mean(
        stratum_means[int(capable(a)) + int(capable(b))] for a, b in matched_edges
    )
    matched_adjacent = pair_mean(matched_edges)

    def ratio(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator and not math.isnan(denominator) else math.nan

    exhaustive_random = pair_mean(all_pairs)
    no_empty_random = pair_mean(no_empty_empty_pairs)
    both_nonempty_random = pair_mean(both_nonempty_pairs)
    return {
        "pair_counts": {
            "edges": len(edges),
            "source_random_draws": len(source_pairs),
            "all_pairs": len(all_pairs),
            "edges_excluding_empty_empty": len(no_empty_empty_edges),
            "pairs_excluding_empty_empty": len(no_empty_empty_pairs),
            "edges_both_nonempty": len(both_nonempty_edges),
            "pairs_both_nonempty": len(both_nonempty_pairs),
            "matched_edges_both_nonempty": len(matched_edges),
        },
        "source_convention": {
            "adjacent_mean": source_adjacent,
            "random_mean": source_random,
            "ratio": ratio(source_adjacent, source_random),
        },
        "exhaustive_all_pairs": {
            "adjacent_mean": source_adjacent,
            "random_mean": exhaustive_random,
            "ratio": ratio(source_adjacent, exhaustive_random),
        },
        "exclude_empty_empty": {
            "adjacent_mean": pair_mean(no_empty_empty_edges),
            "random_mean": no_empty_random,
            "ratio": ratio(pair_mean(no_empty_empty_edges), no_empty_random),
        },
        "both_nonempty": {
            "adjacent_mean": pair_mean(both_nonempty_edges),
            "random_mean": both_nonempty_random,
            "ratio": ratio(pair_mean(both_nonempty_edges), both_nonempty_random),
        },
        "both_nonempty_capability_matched": {
            "adjacent_mean": matched_adjacent,
            "random_mean": matched_null,
            "ratio": ratio(matched_adjacent, matched_null),
            "null_stratum_means": {str(key): value for key, value in sorted(stratum_means.items())},
        },
    }


def source_metric_association(
    rules: Sequence[int],
    libraries: Mapping[int, set[int]],
    *,
    rng: np.random.Generator,
    count: int = 1024,
) -> dict[str, float]:
    hamming: list[float] = []
    descriptor_gap: list[float] = []
    target: list[float] = []
    for _ in range(count):
        selected = rng.choice(len(rules), 2, replace=False)
        left, right = rules[int(selected[0])], rules[int(selected[1])]
        hamming.append(float((left ^ right).bit_count()))
        descriptor_gap.append(euclidean(rule_descriptors(left), rule_descriptors(right)))
        target.append(1.0 - jaccard(libraries[left], libraries[right]))
    return {
        "rho_hamming": spearman(hamming, target),
        "rho_descriptors": spearman(descriptor_gap, target),
    }


def exhaustive_metric_association(
    rules: Sequence[int], libraries: Mapping[int, set[int]], *, exclude_empty_empty: bool
) -> dict[str, float | int]:
    hamming: list[float] = []
    descriptor_gap: list[float] = []
    target: list[float] = []
    for left, right in itertools.combinations(rules, 2):
        if exclude_empty_empty and not libraries[left] and not libraries[right]:
            continue
        hamming.append(float((left ^ right).bit_count()))
        descriptor_gap.append(euclidean(rule_descriptors(left), rule_descriptors(right)))
        target.append(1.0 - jaccard(libraries[left], libraries[right]))
    return {
        "n_pairs": len(target),
        "rho_hamming": spearman(hamming, target),
        "rho_descriptors": spearman(descriptor_gap, target),
    }


def unimodal(values: Sequence[float], tolerance: float) -> bool:
    values = list(values)
    peak = max(range(len(values)), key=values.__getitem__)
    falls_before = any(
        values[index + 1] - values[index] < -tolerance for index in range(peak)
    )
    rises_after = any(
        values[index + 1] - values[index] > tolerance
        for index in range(peak, len(values) - 1)
    )
    return not (falls_before or rises_after)
