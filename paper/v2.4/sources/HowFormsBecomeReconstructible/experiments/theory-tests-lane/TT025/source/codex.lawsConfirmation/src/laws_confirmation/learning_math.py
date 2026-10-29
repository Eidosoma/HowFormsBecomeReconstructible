"""Transparent retained-mask calculations for the L07 audit."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .stats import mean, median


def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Return a finite ratio, infinity for a positive/zero ratio, or None."""

    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return math.inf if numerator > 0 else None
    return float(numerator) / float(denominator)


def percentile_interval(values: Sequence[float]) -> list[float | None]:
    finite = np.asarray([float(value) for value in values if math.isfinite(value)])
    if finite.size == 0:
        return [None, None]
    return [
        float(np.percentile(finite, 2.5)),
        float(np.percentile(finite, 97.5)),
    ]


def exact_sign_flip_test(effects: Sequence[float]) -> dict[str, Any]:
    """Enumerate a two-sided sign-flip null for a paired tissue mean.

    This is a diagnostic randomisation calculation. Its validity requires
    exchangeable signs / a symmetric paired-effect null; the audit reports
    that assumption rather than presenting the result as confirmatory.
    """

    values = np.asarray([float(value) for value in effects], dtype=float)
    n = int(values.size)
    if n == 0:
        return {
            "n_tissues": 0,
            "n_assignments": 0,
            "observed_mean": None,
            "two_sided_p": None,
        }
    if n > 20:
        raise ValueError("exact sign-flip enumeration is limited to 20 tissues")
    observed = abs(float(values.mean()))
    extreme = 0
    assignments = 1 << n
    # Chunking keeps the helper safe at its declared n=20 ceiling.
    for start in range(0, assignments, 65536):
        stop = min(start + 65536, assignments)
        codes = np.arange(start, stop, dtype=np.uint64)[:, None]
        bits = (codes >> np.arange(n, dtype=np.uint64)[None, :]) & 1
        signs = np.where(bits == 1, 1.0, -1.0)
        null_means = (signs * values[None, :]).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(null_means) >= observed - 1e-15))
    return {
        "n_tissues": n,
        "n_assignments": assignments,
        "observed_mean": float(values.mean()),
        "two_sided_p": extreme / assignments,
        "extreme_assignments": extreme,
        "assumption": "paired tissue effects are sign-exchangeable under a symmetric null",
    }


def _boolean_mask(entry: Mapping[str, Any], field: str) -> np.ndarray:
    raw = entry.get(field)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"missing/non-list {field} for entry {entry.get('tissue')}")
    if any(type(value) is not bool for value in raw):
        raise ValueError(f"non-Boolean value in {field} for entry {entry.get('tissue')}")
    return np.asarray(raw, dtype=bool)


def validate_training_entries(
    entries: Iterable[Mapping[str, Any]], *, expected_futures: int = 96
) -> dict[str, Any]:
    """Validate E33's complete 16 x 8 retained condition grid and masks."""

    rows = list(entries)
    keys: set[tuple[int, bool, str, int]] = set()
    tissues: set[int] = set()
    mask_failures: list[str] = []
    for entry in rows:
        key = (
            int(entry["tissue"]),
            bool(entry["trained"]),
            str(entry["test_region"]),
            int(entry["delay"]),
        )
        if key in keys:
            raise ValueError(f"duplicate E33 condition arm: {key}")
        keys.add(key)
        tissues.add(key[0])
        eligible = _boolean_mask(entry, "eligible_mask")
        converted = _boolean_mask(entry, "converted_mask")
        if eligible.size != expected_futures or converted.size != expected_futures:
            mask_failures.append(f"{key}: mask length")
        if int(eligible.sum()) != int(entry["eligible"]):
            mask_failures.append(f"{key}: eligible count")
        if int(converted.sum()) != int(entry["converted"]):
            mask_failures.append(f"{key}: converted count")
        if np.any(converted & ~eligible):
            mask_failures.append(f"{key}: converted outside eligible")
        expected_fraction = (
            float(converted[eligible].mean()) if eligible.any() else 0.0
        )
        if not math.isclose(
            expected_fraction,
            float(entry["fraction"]),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            mask_failures.append(f"{key}: fraction")

    expected_tissues = set(range(16))
    expected_keys = {
        (tissue, trained, "same", delay)
        for tissue in expected_tissues
        for trained in (True, False)
        for delay in (0, 3, 6)
    } | {
        (tissue, trained, "other", 0)
        for tissue in expected_tissues
        for trained in (True, False)
    }
    missing = sorted(expected_keys - keys)
    unexpected = sorted(keys - expected_keys)
    return {
        "n_entries": len(rows),
        "n_unique_keys": len(keys),
        "tissues": sorted(tissues),
        "n_tissues": len(tissues),
        "expected_futures_per_arm": expected_futures,
        "missing_keys": [list(key) for key in missing],
        "unexpected_keys": [list(key) for key in unexpected],
        "mask_failures": mask_failures,
        "passes": (
            len(rows) == 128
            and tissues == expected_tissues
            and not missing
            and not unexpected
            and not mask_failures
        ),
    }


def paired_condition(
    entries: Iterable[Mapping[str, Any]],
    *,
    region: str,
    delay: int,
    rng: np.random.Generator,
    bootstrap_draws: int = 4096,
    minimum_common: int = 8,
) -> dict[str, Any]:
    """Recalculate one E33 trained/naive pair at the tissue cluster unit."""

    selected = [
        entry
        for entry in entries
        if str(entry["test_region"]) == region and int(entry["delay"]) == delay
    ]
    by_tissue: dict[int, dict[bool, Mapping[str, Any]]] = {}
    for entry in selected:
        tissue = int(entry["tissue"])
        trained = bool(entry["trained"])
        if trained in by_tissue.setdefault(tissue, {}):
            raise ValueError(f"duplicate arm for tissue {tissue}, {region}, {delay}")
        by_tissue[tissue][trained] = entry

    tissue_rows: list[dict[str, Any]] = []
    excluded: list[dict[str, int]] = []
    arm_totals = {
        "trained": {"eligible": 0, "converted": 0, "pre_rewritten": 0},
        "naive": {"eligible": 0, "converted": 0, "pre_rewritten": 0},
    }
    for tissue in sorted(by_tissue):
        arms = by_tissue[tissue]
        if set(arms) != {True, False}:
            raise ValueError(f"incomplete arms for tissue {tissue}, {region}, {delay}")
        for flag, label in ((True, "trained"), (False, "naive")):
            arm_totals[label]["eligible"] += int(arms[flag]["eligible"])
            arm_totals[label]["converted"] += int(arms[flag]["converted"])
            arm_totals[label]["pre_rewritten"] += int(arms[flag]["pre_rewritten"])

        trained_eligible = _boolean_mask(arms[True], "eligible_mask")
        naive_eligible = _boolean_mask(arms[False], "eligible_mask")
        trained_converted = _boolean_mask(arms[True], "converted_mask")
        naive_converted = _boolean_mask(arms[False], "converted_mask")
        common = trained_eligible & naive_eligible
        n_common = int(common.sum())
        if n_common < minimum_common:
            excluded.append({"tissue": tissue, "common_eligible": n_common})
            continue
        trained_n = int(trained_converted[common].sum())
        naive_n = int(naive_converted[common].sum())
        trained_rate = trained_n / n_common
        naive_rate = naive_n / n_common
        tissue_rows.append(
            {
                "tissue": tissue,
                "common_eligible": n_common,
                "common_fraction": n_common / trained_eligible.size,
                "trained_converted": trained_n,
                "naive_converted": naive_n,
                "trained_rate": trained_rate,
                "naive_rate": naive_rate,
                "effect": trained_rate - naive_rate,
                "ratio": safe_ratio(trained_rate, naive_rate),
                "eligible_trained": int(trained_eligible.sum()),
                "eligible_naive": int(naive_eligible.sum()),
                "pre_rewritten_trained": int(arms[True]["pre_rewritten"]),
                "pre_rewritten_naive": int(arms[False]["pre_rewritten"]),
            }
        )

    if not tissue_rows:
        raise ValueError(f"no eligible tissues for {region}, delay {delay}")
    trained_rates = [row["trained_rate"] for row in tissue_rows]
    naive_rates = [row["naive_rate"] for row in tissue_rows]
    effects = [row["effect"] for row in tissue_rows]
    common_total = sum(int(row["common_eligible"]) for row in tissue_rows)
    trained_common = sum(int(row["trained_converted"]) for row in tissue_rows)
    naive_common = sum(int(row["naive_converted"]) for row in tissue_rows)
    source_trained = mean(trained_rates)
    source_naive = mean(naive_rates)
    source_effect = source_trained - source_naive
    pooled_trained = trained_common / common_total
    pooled_naive = naive_common / common_total

    indices = rng.integers(
        0, len(tissue_rows), size=(bootstrap_draws, len(tissue_rows))
    )
    effect_array = np.asarray(effects)
    boot = effect_array[indices].mean(axis=1)
    positive = sum(effect > 1e-15 for effect in effects)
    zero = sum(abs(effect) <= 1e-15 for effect in effects)
    negative = sum(effect < -1e-15 for effect in effects)

    return {
        "region": region,
        "delay": delay,
        "n_nominal_arms": len(selected),
        "n_included_tissues": len(tissue_rows),
        "excluded_tissues": excluded,
        "arm_totals_before_common_intersection": arm_totals,
        "common_eligible_total": common_total,
        "common_fraction_of_nominal_slots": common_total
        / (len(tissue_rows) * len(_boolean_mask(selected[0], "eligible_mask"))),
        "source_equal_tissue": {
            "trained_rate": source_trained,
            "naive_rate": source_naive,
            "effect": source_effect,
            "ratio": safe_ratio(source_trained, source_naive),
        },
        "pooled_common_eligible": {
            "trained_converted": trained_common,
            "naive_converted": naive_common,
            "denominator_per_arm": common_total,
            "trained_rate": pooled_trained,
            "naive_rate": pooled_naive,
            "effect": pooled_trained - pooled_naive,
            "ratio": safe_ratio(pooled_trained, pooled_naive),
        },
        "tissue_effect_summary": {
            "mean": mean(effects),
            "median": median(effects),
            "sample_sd": float(np.std(effects, ddof=1)) if len(effects) > 1 else None,
            "minimum": min(effects),
            "maximum": max(effects),
            "positive": positive,
            "zero": zero,
            "negative": negative,
            "bootstrap_draws": bootstrap_draws,
            "bootstrap_seed_is_managed_by_caller": True,
            "bootstrap_95_percentile_interval": percentile_interval(boot.tolist()),
            "exact_sign_flip": exact_sign_flip_test(effects),
        },
        "tissue_rows": tissue_rows,
    }


def training_gate_projection(
    conditions: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Project E33's registered gates from independent condition summaries."""

    same0 = conditions["same_delay_0"]["source_equal_tissue"]
    other0 = conditions["other_delay_0"]["source_equal_tissue"]
    delay_effects = {
        str(delay): conditions[f"same_delay_{delay}"]["source_equal_tissue"]["effect"]
        for delay in (0, 3, 6)
    }
    values = [float(delay_effects[str(delay)]) for delay in (0, 3, 6)]
    sensitisation = bool(
        float(same0["trained_rate"]) >= 1.5 * max(float(same0["naive_rate"]), 1e-9)
        and float(same0["effect"]) >= 0.02
    )
    return {
        "trained_conversion": same0["trained_rate"],
        "naive_conversion": same0["naive_rate"],
        "training_effect": same0["effect"],
        "training_ratio": safe_ratio(
            float(same0["trained_rate"]), float(same0["naive_rate"])
        ),
        "gate_sensitization": sensitisation,
        "habituation_instead": bool(
            float(same0["naive_rate"]) - float(same0["trained_rate"]) >= 0.02
        ),
        "effect_trained_site": same0["effect"],
        "effect_untrained_site": other0["effect"],
        "gate_site_specificity": bool(
            float(same0["effect"]) > float(other0["effect"])
        ),
        "effect_by_delay": delay_effects,
        "gate_decay": all(
            values[index] >= values[index + 1]
            for index in range(len(values) - 1)
        ),
    }


def detector_opportunities(
    *, horizon: int, run_length: int, test_generation: int
) -> dict[str, Any]:
    """Count E33 detector starts admitted after a test at a fixed horizon."""

    first_start = test_generation + 1
    last_start = horizon - run_length
    starts = list(range(first_start, last_start + 1)) if first_start <= last_start else []
    return {
        "horizon": horizon,
        "run_length": run_length,
        "test_generation": test_generation,
        "first_allowed_start": first_start,
        "last_allowed_start": last_start,
        "allowed_starts": starts,
        "n_allowed_starts": len(starts),
        "latest_run_ends_at_generation_index": (
            starts[-1] + run_length - 1 if starts else None
        ),
    }


def aggregate_speedup(
    naive: float | None,
    preexposed: float | None,
    *,
    relative_bar: float,
) -> dict[str, Any]:
    """Recalculate a retained median-arrival speedup and its source gate."""

    speedup = safe_ratio(naive, preexposed)
    relative_reduction = (
        1.0 - float(preexposed) / float(naive)
        if naive not in (None, 0) and preexposed is not None
        else None
    )
    gate = bool(
        naive is not None
        and preexposed is not None
        and naive != 0
        and float(preexposed) <= relative_bar * float(naive)
    )
    return {
        "naive_median_arrival": naive,
        "preexposed_median_arrival": preexposed,
        "speedup": speedup,
        "relative_time_reduction": relative_reduction,
        "relative_bar": relative_bar,
        "gate": gate,
    }
