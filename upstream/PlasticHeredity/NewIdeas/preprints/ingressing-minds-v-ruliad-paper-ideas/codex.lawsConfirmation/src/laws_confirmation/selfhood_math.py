"""Transparent retained-data calculations for the L05 audit.

The functions in this module intentionally consume only retained JSON fields.
They do not import or call any of the source experiments' adjudicators.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .stats import close, mean, median


BOOTSTRAP_DRAWS = 4096
BOOTSTRAP_SEED = 2026090205
PERTURBATIONS = (
    "patch_shuffle",
    "region_roll",
    "swap_regions",
    "gradient_tilt",
    "sign_mirror",
    "checkerboard_swap",
)


def direction_counts(values: Iterable[float]) -> dict[str, int]:
    """Count positive, zero, and negative values without hiding ties."""

    data = [float(value) for value in values]
    return {
        "positive": sum(value > 0 for value in data),
        "ties": sum(value == 0 for value in data),
        "negative": sum(value < 0 for value in data),
        "n": len(data),
    }


def bootstrap_mean_interval(
    values: Sequence[float],
    *,
    seed: int = BOOTSTRAP_SEED,
    draws: int = BOOTSTRAP_DRAWS,
) -> dict[str, Any]:
    """Descriptive percentile interval from row-level resampling."""

    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1 or data.size == 0:
        raise ValueError("bootstrap values must be a non-empty one-dimensional sequence")
    if draws < 1:
        raise ValueError("bootstrap draws must be positive")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, data.size, size=(draws, data.size))
    sampled = data[indices].mean(axis=1)
    return {
        "unit": "retained tissue row",
        "n_units": int(data.size),
        "draws": int(draws),
        "rng": f"numpy.random.default_rng({seed})",
        "mean": float(data.mean()),
        "median": float(np.median(data)),
        "percentile_95": [
            float(np.quantile(sampled, 0.025)),
            float(np.quantile(sampled, 0.975)),
        ],
    }


def _stored_screen_criteria(row: Mapping[str, Any]) -> dict[str, bool]:
    return {key: bool(value) for key, value in row["criteria"].items()}


def screen_row_recalculation(row: Mapping[str, Any]) -> dict[str, Any]:
    """Recalculate every screen component recoverable from its row.

    The archived rows omit the per-seed break rates and clock distribution,
    so ``break_dispersion`` and ``clock_alive`` cannot be reconstructed from
    retained lower-level values. Their stored booleans are still sufficient
    to check that the recorded composite ``pass`` is their conjunction.
    """

    stored = _stored_screen_criteria(row)
    calculated = {
        "h_straddles": bool(
            float(row["h_above"]) >= 0.30 and float(row["h_below"]) >= 0.05
        ),
        "multi_attractor": int(row["distinct_pairs"]) >= 3,
        "survival": float(row["median_survival"]) >= 0.3,
        "parental_inheritance": bool(
            float(row["fragment_h"]) >= float(row["random_fragment_h"]) + 0.02
        ),
    }
    component_names = tuple(key for key in stored if key != "pass")
    pass_from_components = all(stored[key] for key in component_names)
    return {
        "calculated_components": calculated,
        "calculated_components_match": {
            key: value == stored[key] for key, value in calculated.items()
        },
        "not_reconstructable_from_retained_row": [
            "break_dispersion",
            "clock_alive",
        ],
        "stored_pass": stored["pass"],
        "pass_from_stored_components": pass_from_components,
        "stored_pass_matches_component_conjunction": (
            stored["pass"] == pass_from_components
        ),
    }


def recalculate_e26_screen(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild the E26 grid-level gates from retained screen rows."""

    grid = list(payload["grid"])
    if not grid:
        raise ValueError("E26 screen grid is empty")
    row_checks = [screen_row_recalculation(row) for row in grid]
    passing = [row for row in grid if bool(row["criteria"]["pass"])]

    columns: dict[tuple[float, int], dict[float, bool]] = {}
    for row in grid:
        overrides = row["overrides"]
        key = (float(overrides["sigma"]), int(overrides["activity_budget"]))
        column = columns.setdefault(key, {})
        coupling = float(overrides["coupling"])
        if coupling in column:
            raise ValueError(f"duplicate E26 screen cell {(key, coupling)}")
        column[coupling] = bool(row["criteria"]["pass"])

    sweet_columns = []
    for (sigma, budget), column in sorted(columns.items()):
        couplings = sorted(column)
        interior = [
            coupling
            for coupling in couplings[1:-1]
            if column[coupling]
        ]
        if (
            any(column.values())
            and not column[couplings[0]]
            and not column[couplings[-1]]
            and interior
        ):
            sweet_columns.append(
                {
                    "sigma": sigma,
                    "activity_budget": budget,
                    "passing_interior_couplings": interior,
                }
            )

    calculated = {
        "n_passing": len(passing),
        "gate_regime_exists": bool(passing),
        "gate_coupling_sweet_spot": bool(sweet_columns),
        "best": passing[0]["overrides"] if passing else None,
    }
    stored = {
        key: payload.get(key)
        for key in (
            "n_passing",
            "gate_regime_exists",
            "gate_coupling_sweet_spot",
            "best",
        )
    }
    return {
        "grid_rows": len(grid),
        "passing_cells": [row["overrides"] for row in passing],
        "sweet_spot_columns": sweet_columns,
        "calculated": calculated,
        "stored": stored,
        "stored_grid_gates_match": calculated == stored,
        "row_reconstruction": {
            "reconstructable_component_checks": 4 * len(grid),
            "reconstructable_component_matches": sum(
                sum(check["calculated_components_match"].values())
                for check in row_checks
            ),
            "pass_conjunction_matches": sum(
                check["stored_pass_matches_component_conjunction"]
                for check in row_checks
            ),
            "rows": len(grid),
            "missing_lower_level_fields": [
                "per-seed break rates (needed for break dispersion)",
                "per-seed first-generation clocks (needed for clock IQR)",
            ],
        },
    }


def recalculate_e26_regeneration(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild E26's full fragment-versus-random regeneration gate."""

    fragment = [float(value) for value in payload["fragment"]["per_seed_h"]]
    random_fragment = [
        float(value) for value in payload["random_fragment"]["per_seed_h"]
    ]
    if len(fragment) != len(random_fragment) or not fragment:
        raise ValueError("E26 regeneration seed vectors must have equal non-zero length")
    fragment_mean = mean(fragment)
    random_mean = mean(random_fragment)
    differences = [left - right for left, right in zip(fragment, random_fragment)]
    calculated_gate = fragment_mean > 0.9 and fragment_mean > random_mean
    return {
        "n_seed_indices": len(fragment),
        "calculated_fragment_mean": fragment_mean,
        "stored_fragment_mean": float(payload["fragment"]["mean_h"]),
        "fragment_mean_matches": close(fragment_mean, payload["fragment"]["mean_h"]),
        "calculated_random_fragment_mean": random_mean,
        "stored_random_fragment_mean": float(payload["random_fragment"]["mean_h"]),
        "random_fragment_mean_matches": close(
            random_mean, payload["random_fragment"]["mean_h"]
        ),
        "fragment_minus_random_mean": fragment_mean - random_mean,
        "per_seed_index_fragment_minus_random": differences,
        "per_seed_index_directions": direction_counts(differences),
        "paired_trajectory_streams": False,
        "calculated_gate_regeneration": calculated_gate,
        "stored_gate_regeneration": bool(payload["gate_regeneration"]),
        "stored_gate_matches": calculated_gate == bool(payload["gate_regeneration"]),
        "fragment_survival_8": float(payload["fragment"]["survival_8"]),
        "random_fragment_survival_8": float(
            payload["random_fragment"]["survival_8"]
        ),
    }


def _nonnull_mean(rows: Iterable[Mapping[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return mean(values) if values else 0.0


def _success_count(rate: float, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("a retained recovery rate must have a positive denominator")
    successes = int(round(float(rate) * denominator))
    if not close(successes / denominator, rate, tolerance=1e-10):
        raise ValueError(
            f"retained rate {rate} is not an integer count over denominator {denominator}"
        )
    return successes


def _pooled_recovery(
    rows: Sequence[Mapping[str, Any]],
    *,
    group: str,
    eligibility_threshold: int = 1,
) -> dict[str, Any]:
    successes = 0
    total = 0
    used = 0
    for row in rows:
        if group == "rewritten":
            denominator = int(row["zapped_n_rewritten"])
            key = "zapped_rewritten_recovery"
        elif group == "wild":
            denominator = int(row["zapped_eligible"]) - int(row["zapped_n_rewritten"])
            key = "zapped_wild_recovery"
        else:
            raise ValueError(group)
        rate = row.get(key)
        if rate is None or denominator < eligibility_threshold:
            continue
        successes += _success_count(float(rate), denominator)
        total += denominator
        used += 1
    return {
        "successes": successes,
        "futures": total,
        "tissues": used,
        "rate": successes / total if total else math.nan,
    }


def recalculate_e27(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Rebuild E27 gates and outcome-known recovery diagnostics."""

    keys = [(str(row["cohort"]), int(row["tissue"])) for row in entries]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate E27 cohort/tissue rows")
    expected = (
        {("band", tissue) for tissue in range(48)}
        | {("under", tissue) for tissue in range(16)}
        | {("over", tissue) for tissue in range(16)}
    )
    if set(keys) != expected:
        missing = sorted(expected - set(keys))
        extra = sorted(set(keys) - expected)
        raise ValueError(f"unexpected E27 row census; missing={missing}, extra={extra}")

    band = sorted(
        (row for row in entries if row["cohort"] == "band"),
        key=lambda row: int(row["tissue"]),
    )
    under = [row for row in entries if row["cohort"] == "under"]
    over = [row for row in entries if row["cohort"] == "over"]
    zapped_fraction = _nonnull_mean(band, "zapped_rewrite_fraction")
    control_fraction = _nonnull_mean(band, "control_rewrite_fraction")
    conversion = _nonnull_mean(band, "conversion")
    reverse = _nonnull_mean(band, "reverse")
    under_conversion = _nonnull_mean(under, "conversion")
    over_conversion = _nonnull_mean(over, "conversion")
    wild_recovery = _nonnull_mean(band, "zapped_wild_recovery")
    rewritten_rows = [row for row in band if int(row["zapped_n_rewritten"]) >= 3]
    rewritten_recovery = _nonnull_mean(
        rewritten_rows, "zapped_rewritten_recovery"
    )
    per_tissue = {
        str(int(row["tissue"])): float(row["zapped_rewrite_fraction"])
        for row in band
    }
    source_projection = {
        "zapped_rewrite_fraction": zapped_fraction,
        "control_rewrite_fraction": control_fraction,
        "paired_conversion": conversion,
        "paired_reverse": reverse,
        "gate_rewrite_exists": bool(
            conversion >= 0.02 and conversion >= 3 * max(reverse, 1e-9)
        ),
        "under_conversion": under_conversion,
        "over_conversion": over_conversion,
        "gate_regime_dependence": bool(
            conversion >= 2 * max(under_conversion, 1e-9)
            and conversion >= 2 * max(over_conversion, 1e-9)
        ),
        "wild_recovery": wild_recovery,
        "rewritten_recovery": rewritten_recovery,
        "gate_two_setpoints_canalized": bool(
            wild_recovery >= 0.7 and rewritten_recovery >= 0.7
        ),
        "per_tissue_rewrite_fraction": per_tissue,
        "n_band_tissues_with_rewrites": len(rewritten_rows),
    }

    differences = [
        float(row["zapped_rewritten_recovery"])
        - float(row["zapped_wild_recovery"])
        for row in rewritten_rows
        if row.get("zapped_rewritten_recovery") is not None
        and row.get("zapped_wild_recovery") is not None
    ]
    rewritten_pooled = _pooled_recovery(
        band, group="rewritten", eligibility_threshold=3
    )
    wild_pooled = _pooled_recovery(band, group="wild", eligibility_threshold=1)
    return {
        "row_census": {
            "total": len(entries),
            "band": len(band),
            "under": len(under),
            "over": len(over),
            "unique": len(set(keys)),
        },
        "source_projection": source_projection,
        "declared_expectations_two_setpoint_gate": {
            "wild_bar": 0.6,
            "rewritten_bar": 0.7,
            "calculated": bool(
                wild_recovery >= 0.6 and rewritten_recovery >= 0.7
            ),
        },
        "implemented_two_setpoint_gate": {
            "wild_bar": 0.7,
            "rewritten_bar": 0.7,
            "calculated": source_projection["gate_two_setpoints_canalized"],
        },
        "recovery_contrast": {
            "equal_tissue_rewritten_minus_wild": mean(differences),
            "median_tissue_difference": median(differences),
            "directions": direction_counts(differences),
            "per_tissue_rewritten_minus_wild": differences,
            "bootstrap": bootstrap_mean_interval(differences),
            "pooled_rewritten": rewritten_pooled,
            "pooled_wild": wild_pooled,
            "pooled_rewritten_minus_wild": (
                rewritten_pooled["rate"] - wild_pooled["rate"]
            ),
            "groups_defined_after_observing_zap_response": True,
            "causal_basin_depth_contrast": False,
        },
    }


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(left @ right / denominator) if denominator > 0 else 0.0


def _dispersion(vectors: Sequence[Sequence[float]]) -> float:
    array = np.asarray(vectors, dtype=np.float64)
    if len(array) < 2:
        return math.nan
    distances = [
        1.0 - _cosine(array[left], array[right])
        for left in range(len(array))
        for right in range(left + 1, len(array))
    ]
    return mean(distances)


def _homeo_rate(
    rows: Sequence[Mapping[str, Any]], perturbation: str, group: str
) -> float | None:
    values = [
        float(row[f"{group}_recovery"])
        for row in rows
        if row["perturbation"] == perturbation
        and row.get(f"{group}_recovery") is not None
        and int(row[f"{group}_n"]) >= 3
    ]
    return mean(values) if values else None


def _pooled_homeo(
    rows: Sequence[Mapping[str, Any]], group: str
) -> dict[str, Any]:
    successes = 0
    futures = 0
    tissues = 0
    for row in rows:
        denominator = int(row[f"{group}_n"])
        rate = row.get(f"{group}_recovery")
        if denominator < 3 or rate is None:
            continue
        successes += _success_count(float(rate), denominator)
        futures += denominator
        tissues += 1
    return {
        "successes": successes,
        "futures": futures,
        "tissue_type_rows": tissues,
        "rate": successes / futures if futures else math.nan,
    }


def recalculate_e30(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Rebuild E30 gates and outcome-known rewritten/wild diagnostics."""

    keys = [
        (int(row["tissue"]), str(row["perturbation"]), int(row["side"]))
        for row in entries
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate E30 tissue/perturbation/side rows")
    expected = {
        (tissue, perturbation, 8)
        for tissue in range(16)
        for perturbation in PERTURBATIONS
    } | {
        (tissue, "patch_shuffle", side)
        for tissue in range(16)
        for side in (4, 12)
    }
    if set(keys) != expected:
        missing = sorted(expected - set(keys))
        extra = sorted(set(keys) - expected)
        raise ValueError(f"unexpected E30 row census; missing={missing}, extra={extra}")

    gate_rows = [row for row in entries if int(row["side"]) == 8]
    per_type = {
        perturbation: {
            "rewritten": _homeo_rate(gate_rows, perturbation, "rewritten"),
            "wild": _homeo_rate(gate_rows, perturbation, "wild"),
        }
        for perturbation in PERTURBATIONS
    }
    passing = [
        name
        for name, values in per_type.items()
        if values["rewritten"] is not None and values["rewritten"] >= 0.6
    ]
    rewritten_rates = [
        float(values["rewritten"])
        for values in per_type.values()
        if values["rewritten"] is not None
    ]
    wild_rates = [
        float(values["wild"])
        for values in per_type.values()
        if values["wild"] is not None
    ]

    endpoint_dispersions = []
    midpath_dispersions = []
    for tissue in range(16):
        endpoints = []
        midpaths = []
        for row in gate_rows:
            if int(row["tissue"]) != tissue or not row["end_censuses"]:
                continue
            endpoints.append(
                np.asarray(row["end_censuses"], dtype=np.float64).mean(axis=0)
            )
            midpaths.append(
                np.asarray(row["mid_censuses"], dtype=np.float64).mean(axis=0)
            )
        if len(endpoints) >= 3:
            endpoint_dispersions.append(_dispersion(endpoints))
            midpath_dispersions.append(_dispersion(midpaths))
    endpoint_mean = mean(endpoint_dispersions) if endpoint_dispersions else None
    midpath_mean = mean(midpath_dispersions) if midpath_dispersions else None

    dose = {}
    for side in (4, 8, 12):
        values = [
            float(row["rewritten_recovery"])
            for row in entries
            if int(row["side"]) == side
            and row["perturbation"] == "patch_shuffle"
            and row.get("rewritten_recovery") is not None
        ]
        dose[str(side)] = mean(values)

    rewritten_mean = mean(rewritten_rates)
    wild_mean = mean(wild_rates)
    source_projection = {
        "per_type": per_type,
        "n_types_passing": len(passing),
        "gate_recovery": len(passing) >= 4,
        "rewritten_mean": rewritten_mean,
        "wild_mean": wild_mean,
        "gate_asymmetry": rewritten_mean > wild_mean,
        "endpoint_dispersion": endpoint_mean,
        "midpath_dispersion": midpath_mean,
        "gate_equifinality": bool(
            endpoint_mean is not None
            and midpath_mean is not None
            and endpoint_mean < 0.5 * midpath_mean
        ),
        "dose_response_shuffle": dose,
    }

    tissue_differences = []
    tissue_coverage = {}
    for tissue in range(16):
        selected = [
            row
            for row in gate_rows
            if int(row["tissue"]) == tissue
            and row.get("rewritten_recovery") is not None
            and row.get("wild_recovery") is not None
            and int(row["rewritten_n"]) >= 3
            and int(row["wild_n"]) >= 3
        ]
        values = [
            float(row["rewritten_recovery"]) - float(row["wild_recovery"])
            for row in selected
        ]
        tissue_coverage[str(tissue)] = len(values)
        if values:
            tissue_differences.append(mean(values))

    rewritten_pooled = _pooled_homeo(gate_rows, "rewritten")
    wild_pooled = _pooled_homeo(gate_rows, "wild")
    per_type_differences = [
        float(values["rewritten"]) - float(values["wild"])
        for values in per_type.values()
        if values["rewritten"] is not None and values["wild"] is not None
    ]
    return {
        "row_census": {
            "total": len(entries),
            "gate_rows": len(gate_rows),
            "unique": len(set(keys)),
            "dose_only_rows": len(entries) - len(gate_rows),
        },
        "source_projection": source_projection,
        "recovery_contrast": {
            "per_type_rewritten_minus_wild": per_type_differences,
            "per_type_directions": direction_counts(per_type_differences),
            "paired_tissue_mean_rewritten_minus_wild": mean(tissue_differences),
            "median_tissue_difference": median(tissue_differences),
            "per_tissue_mean_rewritten_minus_wild": tissue_differences,
            "per_tissue_type_coverage": tissue_coverage,
            "tissue_directions": direction_counts(tissue_differences),
            "bootstrap": bootstrap_mean_interval(tissue_differences),
            "pooled_rewritten": rewritten_pooled,
            "pooled_wild": wild_pooled,
            "pooled_rewritten_minus_wild": (
                rewritten_pooled["rate"] - wild_pooled["rate"]
            ),
            "groups_defined_after_observing_zap_response": True,
            "causal_basin_depth_contrast": False,
        },
        "dispersion_detail": {
            "tissues_contributing": len(endpoint_dispersions),
            "endpoint_by_tissue": endpoint_dispersions,
            "midpath_by_tissue": midpath_dispersions,
        },
    }
