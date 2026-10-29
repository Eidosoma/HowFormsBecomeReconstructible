"""Small transparent statistical helpers used by the artefact audit."""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def mean(values: Iterable[float]) -> float:
    data = [float(value) for value in values]
    return sum(data) / len(data) if data else math.nan


def median(values: Iterable[float]) -> float:
    data = sorted(float(value) for value in values)
    if not data:
        return math.nan
    middle = len(data) // 2
    if len(data) % 2:
        return data[middle]
    return (data[middle - 1] + data[middle]) / 2.0


def average_ranks(values: Sequence[float], *, descending: bool = False) -> list[float]:
    """One-based average ranks, matching scipy/pandas tie semantics."""

    order = sorted(range(len(values)), key=lambda index: values[index], reverse=descending)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        value = values[order[start]]
        while end < len(order) and values[order[end]] == value:
            end += 1
        average = ((start + 1) + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average
        start = end
    return ranks


def minimum_ranks(values: Sequence[float], *, descending: bool = False) -> list[int]:
    """One-based minimum ranks, matching pandas method='min'."""

    order = sorted(range(len(values)), key=lambda index: values[index], reverse=descending)
    ranks = [0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        value = values[order[start]]
        while end < len(order) and values[order[end]] == value:
            end += 1
        rank = start + 1
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return math.nan
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_ss = sum((a - left_mean) ** 2 for a in left)
    right_ss = sum((b - right_mean) ** 2 for b in right)
    denominator = math.sqrt(left_ss * right_ss)
    return numerator / denominator if denominator else math.nan


def spearman(left: Sequence[float], right: Sequence[float]) -> float:
    return pearson(average_ranks(left), average_ranks(right))


def close(left: float | int | None, right: float | int | None, tolerance: float = 1e-12) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)

