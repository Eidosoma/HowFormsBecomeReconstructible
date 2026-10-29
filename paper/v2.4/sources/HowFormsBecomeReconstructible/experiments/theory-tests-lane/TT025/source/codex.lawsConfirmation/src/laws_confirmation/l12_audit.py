"""Outcome-known retained/replay audit for L12's single-road claim."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E42_james_test_2": "95f2f959571d81d7fb9e4732c0e27007f853bc97b9a477b8e93620a0c4fca57d",
    "E46_james_test_3": "23793e8eeffc223a5ae82725a4e596028a47fa688b9354091376cd3975f4bfda",
    "E50_james_final": "673ad23f3661725b97aebaf33515850811dbc88d70a9c84209d7d118c66b2728",
}

REPLAY_ROWS = {"E42": 60, "E46": 50, "E50": 50}
REPLAY_FUTURES = {"E42": 1440, "E46": 800, "E50": 800}
GRID_PIXELS = 16 * 16


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def _read(tracker: InputTracker, path: Path) -> str:
    return tracker.add(path).read_text(encoding="utf-8")


def _track_package(
    tracker: InputTracker,
    root: Path,
    *,
    retained_json: Iterable[str] = (),
) -> None:
    for relative in ("EXPECTATIONS.md", "pyproject.toml"):
        path = root / relative
        if path.is_file():
            tracker.add(path)
    for directory in ("src", "tests"):
        path = root / directory
        if path.is_dir():
            for source in sorted(path.rglob("*.py")):
                tracker.add(source)
    for relative in retained_json:
        path = root / relative
        if path.is_file():
            tracker.add(path)


def source_config_digests() -> dict[str, str]:
    """Digests from an independent transcription of the final defaults."""

    configs: dict[str, dict[str, Any]] = {
        "E42_james_test_2": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 24,
            "settle_sweeps": 40,
            "zap_sweeps_ladder": (4, 8, 16),
            "zap_value": 1.5,
            "recovery_horizon": 80,
            "arrival_cos": 0.9,
            "cessation_window": 3,
            "replica_streams": 6,
            "mid_fraction": 0.5,
            "pre_gap": 10,
            "decoy_horizon": 80,
            "backtrack_margin": 0.02,
            "trajectory_seed_tag": "james2-traj-v1",
        },
        "E46_james_test_3": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 16,
            "settle_sweeps": 40,
            "zap_sweeps_ladder": (4, 8, 16),
            "recovery_horizon": 100,
            "arrival_cos": 0.9,
            "activity_window": 10,
            "cessation_lock": 5,
            "replica_streams": 5,
            "pre_gap": 10,
            "trap_horizon": 200,
            "trap_wall_width": 2,
            "backtrack_margin": 2.0,
            "trajectory_seed_tag": "james3-traj-v2",
            "motility_seed_tag": "james3-motility-v2",
        },
        "E50_james_final": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 16,
            "settle_sweeps": 120,
            "zap_sweeps_ladder": (4, 8, 16),
            "recovery_horizon": 100,
            "arrival_cos_bar": 0.8,
            "cessation_lock": 3,
            "replica_streams": 5,
            "pre_gap": 10,
            "trap_horizon": 200,
            "trap_wall_width": 2,
            "trajectory_seed_tag": "jamesfinal-traj-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def _recursive_close(left: Any, right: Any) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _recursive_close(left[key], right[key]) for key in left
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            _recursive_close(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return close(left, right)
    return left == right


def _distribution(values: Iterable[float | int | None]) -> dict[str, Any]:
    data = np.asarray([float(value) for value in values if value is not None], dtype=float)
    if not data.size:
        return {
            "n": 0,
            "min": None,
            "q25": None,
            "median": None,
            "mean": None,
            "q75": None,
            "max": None,
        }
    q25, median, q75 = np.quantile(data, (0.25, 0.5, 0.75))
    return {
        "n": int(data.size),
        "min": float(data.min()),
        "q25": float(q25),
        "median": float(median),
        "mean": float(data.mean()),
        "q75": float(q75),
        "max": float(data.max()),
    }


def _integer_histogram(values: Iterable[int | float]) -> dict[str, int]:
    counts: dict[int, int] = defaultdict(int)
    for value in values:
        counts[int(value)] += 1
    return {str(key): counts[key] for key in sorted(counts)}


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=float).ravel()
    b = np.asarray(right, dtype=float).ravel()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a @ b / denominator) if denominator > 0 else 0.0


def _centered_cosine(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=float).ravel()
    b = np.asarray(right, dtype=float).ravel()
    a = a - a.mean()
    b = b - b.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a @ b / denominator) if denominator > 0 else 0.0


def _bootstrap_tissue_mean(
    tissue_values: Mapping[int, float], *, seed: int, draws: int = 4096
) -> list[float] | None:
    keys = sorted(tissue_values)
    if not keys:
        return None
    values = np.asarray([tissue_values[key] for key in keys], dtype=float)
    rng = np.random.default_rng(seed)
    estimates = np.empty(draws, dtype=float)
    for draw in range(draws):
        estimates[draw] = rng.choice(values, size=len(values), replace=True).mean()
    return [float(value) for value in np.quantile(estimates, (0.025, 0.975))]


def map_descriptors(maps: np.ndarray) -> dict[str, Any]:
    """Scale/support descriptors for an array ending in H,W."""

    flat = np.asarray(maps, dtype=float).reshape((-1, GRID_PIXELS))
    totals = flat.sum(axis=1)
    support = (flat > 0).sum(axis=1)
    squares = np.square(flat).sum(axis=1)
    effective = np.divide(
        np.square(totals),
        GRID_PIXELS * squares,
        out=np.zeros_like(totals),
        where=squares > 0,
    )
    return {
        "map_count": int(flat.shape[0]),
        "zero_maps": int(np.count_nonzero(totals == 0)),
        "total_activity": _distribution(totals),
        "positive_pixel_fraction": _distribution(support / GRID_PIXELS),
        "normalized_effective_support": _distribution(effective),
    }


def _batch_pairs(
    maps: np.ndarray,
    tissues: np.ndarray,
    *,
    within_tissue: bool,
    exclude_zero: bool,
) -> list[tuple[int, int]]:
    totals = maps.reshape((maps.shape[0], -1)).sum(axis=1)
    pairs: list[tuple[int, int]] = []
    for left in range(len(maps)):
        if exclude_zero and totals[left] <= 0:
            continue
        for right in range(left + 1, len(maps)):
            if exclude_zero and totals[right] <= 0:
                continue
            same = int(tissues[left]) == int(tissues[right])
            if same == within_tissue:
                pairs.append((left, right))
    return pairs


def simple_batch_pair_summary(
    maps: np.ndarray,
    tissues: np.ndarray,
    *,
    exclude_zero: bool,
) -> dict[str, Any]:
    totals = maps.reshape((len(maps), -1)).sum(axis=1)
    pairs = _batch_pairs(
        maps, tissues, within_tissue=True, exclude_zero=exclude_zero
    )
    raw = [_cosine(maps[left], maps[right]) for left, right in pairs]
    centered = [
        _centered_cosine(maps[left], maps[right]) for left, right in pairs
    ]
    by_tissue: dict[int, list[float]] = defaultdict(list)
    for (left, _right), value in zip(pairs, raw):
        by_tissue[int(tissues[left])].append(value)
    all_tissues = sorted(set(int(value) for value in tissues))
    included_by_tissue = {
        tissue: int(
            np.count_nonzero((tissues == tissue) & (totals > 0))
            if exclude_zero
            else np.count_nonzero(tissues == tissue)
        )
        for tissue in all_tissues
    }
    excluded_by_tissue = {
        tissue: int(np.count_nonzero((tissues == tissue) & (totals <= 0)))
        if exclude_zero
        else 0
        for tissue in all_tissues
    }
    pair_counts = {
        tissue: len(by_tissue.get(tissue, [])) for tissue in all_tissues
    }
    tissue_means = {
        tissue: float(np.mean(by_tissue[tissue]))
        for tissue in all_tissues
        if by_tissue.get(tissue)
    }
    return {
        "included_batch_maps": int(
            np.count_nonzero(totals > 0)
            if exclude_zero
            else len(maps)
        ),
        "excluded_zero_batch_maps": int(
            np.count_nonzero(totals <= 0)
            if exclude_zero
            else 0
        ),
        "included_batch_maps_by_tissue": {
            str(key): value for key, value in included_by_tissue.items()
        },
        "excluded_zero_batch_maps_by_tissue": {
            str(key): value for key, value in excluded_by_tissue.items()
        },
        "pair_count": len(pairs),
        "pair_count_by_tissue": {
            str(key): value for key, value in pair_counts.items()
        },
        "tissues_with_at_least_one_pair": len(tissue_means),
        "tissues_without_an_admissible_pair": [
            tissue for tissue in all_tissues if not by_tissue.get(tissue)
        ],
        "zero_cosine_pairs": sum(value == 0 for value in raw),
        "positive_cosine_pairs": sum(value > 0 for value in raw),
        "unit_cosine_pairs": sum(close(value, 1.0) for value in raw),
        "raw_cosine": _distribution(raw),
        "mean_centered_cosine": _distribution(centered),
        "tissue_means": {
            str(tissue): value for tissue, value in sorted(tissue_means.items())
        },
        "equal_eligible_tissue_mean_raw_cosine": (
            float(np.mean(list(tissue_means.values()))) if tissue_means else None
        ),
        "equal_all_tissue_mean_with_missing_as_zero_sensitivity": (
            float(
                np.mean(
                    [tissue_means.get(tissue, 0.0) for tissue in all_tissues]
                )
            )
            if all_tissues
            else None
        ),
    }


def batch_pair_analysis(
    maps: np.ndarray,
    tissues: np.ndarray,
    *,
    exclude_zero: bool,
    bootstrap_seed: int,
) -> dict[str, Any]:
    """Registered pairs, cross-tissue comparator, and exact shift null."""

    primary = simple_batch_pair_summary(
        maps, tissues, exclude_zero=exclude_zero
    )
    within_pairs = _batch_pairs(
        maps, tissues, within_tissue=True, exclude_zero=exclude_zero
    )
    between_pairs = _batch_pairs(
        maps, tissues, within_tissue=False, exclude_zero=exclude_zero
    )
    between_raw = [_cosine(maps[a], maps[b]) for a, b in between_pairs]
    between_centered = [
        _centered_cosine(maps[a], maps[b]) for a, b in between_pairs
    ]

    null_raw: list[float] = []
    null_centered: list[float] = []
    observed_minus_null: list[float] = []
    centered_observed_minus_null: list[float] = []
    tail_fractions: list[float] = []
    above_95 = 0
    difference_by_tissue: dict[int, list[float]] = defaultdict(list)
    for left, right in within_pairs:
        observed = _cosine(maps[left], maps[right])
        observed_centered = _centered_cosine(maps[left], maps[right])
        pair_null = []
        pair_centered_null = []
        for dy in range(maps.shape[-2]):
            for dx in range(maps.shape[-1]):
                if dy == 0 and dx == 0:
                    continue
                shifted = np.roll(maps[right], shift=(dy, dx), axis=(-2, -1))
                pair_null.append(_cosine(maps[left], shifted))
                pair_centered_null.append(_centered_cosine(maps[left], shifted))
        null_raw.extend(pair_null)
        null_centered.extend(pair_centered_null)
        difference = observed - float(np.mean(pair_null))
        centered_difference = observed_centered - float(np.mean(pair_centered_null))
        observed_minus_null.append(difference)
        centered_observed_minus_null.append(centered_difference)
        difference_by_tissue[int(tissues[left])].append(difference)
        tail_fractions.append(float(np.mean(np.asarray(pair_null) >= observed)))
        if observed > float(np.quantile(pair_null, 0.95)):
            above_95 += 1

    tissue_differences = {
        tissue: float(np.mean(values))
        for tissue, values in sorted(difference_by_tissue.items())
    }
    primary["tissue_cluster_bootstrap_95_mean_raw_cosine"] = (
        _bootstrap_tissue_mean(
            {int(k): float(v) for k, v in primary["tissue_means"].items()},
            seed=bootstrap_seed,
        )
    )
    primary["between_tissue"] = {
        "pair_count": len(between_pairs),
        "raw_cosine": _distribution(between_raw),
        "mean_centered_cosine": _distribution(between_centered),
        "within_minus_between_mean_raw": (
            float(primary["raw_cosine"]["mean"] - np.mean(between_raw))
            if between_raw and primary["raw_cosine"]["mean"] is not None
            else None
        ),
    }
    primary["exact_nonzero_toroidal_translation_null"] = {
        "shifts_per_pair": int(maps.shape[-2] * maps.shape[-1] - 1),
        "null_comparisons": len(null_raw),
        "raw_cosine": _distribution(null_raw),
        "mean_centered_cosine": _distribution(null_centered),
        "observed_minus_pair_null_mean_raw": _distribution(observed_minus_null),
        "observed_minus_pair_null_mean_centered": _distribution(
            centered_observed_minus_null
        ),
        "fraction_pairs_observed_above_own_null_q95": (
            float(above_95 / len(within_pairs)) if within_pairs else None
        ),
        "pairwise_fraction_null_at_least_observed": _distribution(tail_fractions),
        "tissue_cluster_bootstrap_95_observed_minus_null_mean": (
            _bootstrap_tissue_mean(
                tissue_differences, seed=bootstrap_seed + 1000
            )
        ),
        "interpretation": (
            "Exact periodic spatial-registration diagnostic; not a general "
            "random-process null."
        ),
    }
    return primary


def _matrix_pair_values(flat: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    norms = np.linalg.norm(flat, axis=1)
    normalized = np.divide(
        flat,
        norms[:, None],
        out=np.zeros_like(flat, dtype=float),
        where=norms[:, None] > 0,
    )
    raw = normalized @ normalized.T
    centered_flat = flat - flat.mean(axis=1, keepdims=True)
    centered_norms = np.linalg.norm(centered_flat, axis=1)
    centered_normalized = np.divide(
        centered_flat,
        centered_norms[:, None],
        out=np.zeros_like(centered_flat, dtype=float),
        where=centered_norms[:, None] > 0,
    )
    centered = centered_normalized @ centered_normalized.T
    return raw, centered, norms


def individual_pair_analysis(
    maps: np.ndarray,
    tissues: np.ndarray,
    replicas: np.ndarray,
    arrived: np.ndarray,
) -> dict[str, Any]:
    """Within-tissue future-level correlations, retaining endpoint classes."""

    futures_per_row = maps.shape[1]
    flat_maps = maps.reshape((-1, GRID_PIXELS)).astype(float)
    future_tissues = np.repeat(tissues, futures_per_row)
    future_replicas = np.repeat(replicas, futures_per_row)
    future_arrived = arrived.reshape(-1).astype(bool)

    buckets: dict[str, dict[str, list[np.ndarray]]] = {
        name: {"raw": [], "centered": [], "nonzero": []}
        for name in (
            "all",
            "same_replica_batch",
            "different_replica_batch",
            "both_arrived",
            "both_nonarrived",
            "discordant_endpoint",
        )
    }

    for tissue in sorted(set(int(value) for value in future_tissues)):
        indexes = np.flatnonzero(future_tissues == tissue)
        local = flat_maps[indexes]
        raw, centered, norms = _matrix_pair_values(local)
        left, right = np.triu_indices(len(indexes), k=1)
        global_left, global_right = indexes[left], indexes[right]
        base_masks = {
            "all": np.ones(len(left), dtype=bool),
            "same_replica_batch": (
                future_replicas[global_left] == future_replicas[global_right]
            ),
            "different_replica_batch": (
                future_replicas[global_left] != future_replicas[global_right]
            ),
            "both_arrived": (
                future_arrived[global_left] & future_arrived[global_right]
            ),
            "both_nonarrived": (
                ~future_arrived[global_left] & ~future_arrived[global_right]
            ),
            "discordant_endpoint": (
                future_arrived[global_left] != future_arrived[global_right]
            ),
        }
        nonzero = (norms[left] > 0) & (norms[right] > 0)
        for name, mask in base_masks.items():
            buckets[name]["raw"].append(raw[left[mask], right[mask]])
            buckets[name]["centered"].append(centered[left[mask], right[mask]])
            buckets[name]["nonzero"].append(nonzero[mask])

    result: dict[str, Any] = {}
    for name, values in buckets.items():
        raw = np.concatenate(values["raw"]) if values["raw"] else np.asarray([])
        centered = (
            np.concatenate(values["centered"])
            if values["centered"]
            else np.asarray([])
        )
        nonzero = (
            np.concatenate(values["nonzero"])
            if values["nonzero"]
            else np.asarray([], dtype=bool)
        )
        result[name] = {
            "pair_count": int(raw.size),
            "nonzero_pair_count": int(np.count_nonzero(nonzero)),
            "raw_cosine_all_maps": _distribution(raw),
            "raw_cosine_nonzero_maps": _distribution(raw[nonzero]),
            "mean_centered_cosine_all_maps": _distribution(centered),
            "mean_centered_cosine_nonzero_maps": _distribution(
                centered[nonzero]
            ),
        }
    result["unit_warning"] = (
        "Future pairs share tissue and maps enter many pairs; these are descriptive "
        "pair summaries, not independent replicate counts."
    )
    return result


def _components_torus(mask: np.ndarray) -> tuple[int, int]:
    height, width = mask.shape
    unseen = {tuple(point) for point in np.argwhere(mask)}
    components = 0
    largest = 0
    while unseen:
        components += 1
        start = unseen.pop()
        stack = [start]
        size = 1
        while stack:
            y, x = stack.pop()
            for neighbour in (
                ((y - 1) % height, x),
                ((y + 1) % height, x),
                (y, (x - 1) % width),
                (y, (x + 1) % width),
            ):
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
                    size += 1
        largest = max(largest, size)
    return components, largest


def e50_scattering_analysis(maps: np.ndarray) -> dict[str, Any]:
    """Describe E50 sign-flip supports without inferring their cause."""

    rows = np.asarray(maps, dtype=float).reshape((-1, 16, 16))
    active_pixels: list[int] = []
    total_flips: list[float] = []
    repeats: list[float | None] = []
    components: list[int] = []
    largest_fraction: list[float | None] = []
    occupied_edges: list[int] = []
    edge_enrichment: list[float | None] = []
    for road in rows:
        support = road > 0
        count = int(support.sum())
        total = float(road.sum())
        component_count, largest = _components_torus(support)
        edges = int(
            np.count_nonzero(support & np.roll(support, -1, axis=0))
            + np.count_nonzero(support & np.roll(support, -1, axis=1))
        )
        expected_edges = (
            512.0 * count * (count - 1) / (GRID_PIXELS * (GRID_PIXELS - 1))
            if count >= 2
            else 0.0
        )
        active_pixels.append(count)
        total_flips.append(total)
        repeats.append(total / count if count else None)
        components.append(component_count)
        largest_fraction.append(largest / count if count else None)
        occupied_edges.append(edges)
        edge_enrichment.append(edges / expected_edges if expected_edges else None)
    return {
        "individual_maps": len(rows),
        "zero_maps": sum(value == 0 for value in active_pixels),
        "nonzero_maps": sum(value > 0 for value in active_pixels),
        "maps_with_at_least_two_active_pixels": sum(
            value >= 2 for value in active_pixels
        ),
        "maps_with_adjacent_active_pixels": sum(value > 0 for value in occupied_edges),
        "active_pixel_histogram": _integer_histogram(active_pixels),
        "total_sign_flip_histogram": _integer_histogram(total_flips),
        "active_pixels": _distribution(active_pixels),
        "total_sign_flips": _distribution(total_flips),
        "sign_flips_per_active_pixel": _distribution(repeats),
        "four_neighbour_toroidal_components": _distribution(components),
        "largest_component_fraction": _distribution(largest_fraction),
        "occupied_neighbour_edges": _distribution(occupied_edges),
        "occupied_edge_enrichment_vs_uniform_same_size_support": _distribution(
            edge_enrichment
        ),
        "causal_noise_classification_identified": False,
        "qualification": (
            "The registered source supplied no pre-outcome threshold for "
            "structured versus noise-scattered maps."
        ),
    }


def _replay_e42() -> dict[str, Any]:
    from contract_bridge.artifacts import seed_rng
    from excitable_web.config import ExConfig
    from excitable_web.engine import excitable_step
    from ladder_web.config import LadderConfig
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config
    from james_test_2.config import James2Config
    from james_test_2.pipeline import _census, _settle, _zap_mask

    config = James2Config()
    ladder, ex, rewrite = LadderConfig(), ExConfig(), RewriteConfig()
    zap = int(config.zap_sweeps_ladder[-1])
    rows, tissues, replicas, arrivals = [], [], [], []
    maps_3, maps_6 = [], []
    started = time.monotonic()
    for tissue_index in range(config.n_tissues):
        tissue = tissue_config(tissue_index, rewrite.coupling_band, rewrite)
        for replica in range(config.replica_streams):
            rng = seed_rng(
                config.trajectory_seed_tag,
                "F",
                tissue_index,
                zap,
                replica,
            )
            V, ema, overlay, theta, fields = _settle(
                tissue, ladder, ex, "F", rng, config.futures, None
            )
            setpoint = _census(V)
            arrival = np.full(config.futures, -1, dtype=int)
            snapshots: dict[int, np.ndarray] = {}
            mask = _zap_mask(tissue)
            for sweep in range(1, config.recovery_horizon + 1):
                clamp = mask if sweep <= zap else None
                V, ema, overlay, _, _ = excitable_step(
                    V,
                    ema,
                    overlay,
                    theta,
                    tissue,
                    ladder,
                    ex,
                    "F",
                    rng,
                    fields,
                    k_u=None,
                    clamp=clamp,
                )
                cosine = np.asarray(_census(V))
                denominator = np.linalg.norm(cosine, axis=-1) * np.linalg.norm(
                    setpoint, axis=-1
                )
                similarity = np.divide(
                    (cosine * setpoint).sum(axis=-1),
                    np.maximum(denominator, 1e-300),
                )
                newly = (
                    (arrival < 0)
                    & (similarity > config.arrival_cos)
                    & (sweep > zap)
                )
                arrival[newly] = sweep
                if sweep in (zap + 3, zap + 6):
                    snapshots[sweep - zap] = (
                        np.maximum(overlay["up"], 0)
                        + np.maximum(overlay["um"], 0)
                    ).copy()
            arrived = arrival > 0
            maps_3.append(snapshots[3])
            maps_6.append(snapshots[6])
            arrivals.append(arrived)
            tissues.append(tissue_index)
            replicas.append(replica)
            rows.append(
                {
                    "tissue": tissue_index,
                    "replica": replica,
                    "recovery_rate": float(arrived.mean()),
                    "median_arrival": (
                        float(np.median(arrival[arrived])) if arrived.any() else None
                    ),
                }
            )
    return {
        "experiment": "E42",
        "rows": rows,
        "tissues": np.asarray(tissues, dtype=np.int16),
        "replicas": np.asarray(replicas, dtype=np.int16),
        "arrived": np.stack(arrivals),
        "maps": {"3": np.stack(maps_3), "6": np.stack(maps_6)},
        "registered_window": "3",
        "exclude_zero_batch_maps": False,
        "elapsed_seconds": time.monotonic() - started,
        "futures_per_row": config.futures,
    }


def _replay_e46() -> dict[str, Any]:
    from contract_bridge.artifacts import seed_rng
    from growing_web.config import GrowConfig
    from ladder_web.config import LadderConfig
    from ladder_web.engine import tissue_fields
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import posterior_mask, tissue_config
    from voltage_web.engine import launch_pattern, make_thresholds
    from james_test_3.config import James3Config
    from james_test_3.pipeline import _census, step_traced

    config = James3Config()
    ladder, grow, rewrite = LadderConfig(), GrowConfig(), RewriteConfig()
    zap = int(config.zap_sweeps_ladder[-1])
    windows = (1, 3, 6, 10)
    maps: dict[int, list[np.ndarray]] = {window: [] for window in windows}
    rows, tissues, replicas, arrivals = [], [], [], []
    started = time.monotonic()
    for tissue_index in range(config.n_tissues):
        tissue = tissue_config(tissue_index, rewrite.coupling_band, rewrite)
        theta = make_thresholds(tissue)
        fields = tissue_fields(tissue, ladder, "D")
        for replica in range(config.replica_streams):
            rng = seed_rng(
                config.trajectory_seed_tag,
                "H",
                tissue_index,
                zap,
                replica,
                False,
            )
            mrng = seed_rng(
                config.motility_seed_tag,
                "H",
                tissue_index,
                zap,
                replica,
                False,
            )
            V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
            V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
            ema = V.copy()
            for _ in range(config.settle_sweeps):
                V, ema, _ = step_traced(
                    V,
                    ema,
                    theta,
                    tissue,
                    ladder,
                    grow,
                    "H",
                    rng,
                    mrng,
                    fields,
                    True,
                )
            setpoint = _census(V)
            arrival = np.full(config.futures, -1, dtype=int)
            cumulative = np.zeros_like(V, dtype=float)
            snapshots: dict[int, np.ndarray] = {}
            mask = posterior_mask(tissue)
            for sweep in range(1, config.recovery_horizon + 1):
                clamp = mask if sweep <= zap else None
                V, ema, swap_map = step_traced(
                    V,
                    ema,
                    theta,
                    tissue,
                    ladder,
                    grow,
                    "H",
                    rng,
                    mrng,
                    fields,
                    True,
                    clamp,
                )
                census = _census(V)
                denominator = np.linalg.norm(census, axis=-1) * np.linalg.norm(
                    setpoint, axis=-1
                )
                similarity = np.divide(
                    (census * setpoint).sum(axis=-1),
                    np.maximum(denominator, 1e-300),
                )
                newly = (
                    (arrival < 0)
                    & (similarity > config.arrival_cos)
                    & (sweep > zap)
                )
                arrival[newly] = sweep
                released = sweep - zap
                if 1 <= released <= 10:
                    cumulative += swap_map
                    if released in windows:
                        snapshots[released] = cumulative.copy()
            arrived = arrival > 0
            for window in windows:
                maps[window].append(snapshots[window])
            arrivals.append(arrived)
            tissues.append(tissue_index)
            replicas.append(replica)
            rows.append(
                {
                    "tissue": tissue_index,
                    "replica": replica,
                    "recovery_rate": float(arrived.mean()),
                    "median_arrival": (
                        float(np.median(arrival[arrived])) if arrived.any() else None
                    ),
                }
            )
    return {
        "experiment": "E46",
        "rows": rows,
        "tissues": np.asarray(tissues, dtype=np.int16),
        "replicas": np.asarray(replicas, dtype=np.int16),
        "arrived": np.stack(arrivals),
        "maps": {str(key): np.stack(value) for key, value in maps.items()},
        "registered_window": "10",
        "exclude_zero_batch_maps": False,
        "elapsed_seconds": time.monotonic() - started,
        "futures_per_row": config.futures,
    }


def _replay_e50() -> dict[str, Any]:
    from blueprint_web.config import BlueprintConfig
    from blueprint_web.engine import blueprint_step, settle_with_blueprint
    from contract_bridge.artifacts import seed_rng
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import posterior_mask, tissue_config
    from james_final.config import JamesFinalConfig

    config = JamesFinalConfig()
    blueprint, rewrite = BlueprintConfig(), RewriteConfig()
    zap = int(config.zap_sweeps_ladder[-1])
    windows = (1, 3, 6, 10)
    maps: dict[int, list[np.ndarray]] = {window: [] for window in windows}
    rows, tissues, replicas, arrivals = [], [], [], []
    started = time.monotonic()
    for tissue_index in range(config.n_tissues):
        tissue = tissue_config(tissue_index, rewrite.coupling_band, rewrite)
        for replica in range(config.replica_streams):
            rng = seed_rng(
                config.trajectory_seed_tag,
                "T",
                tissue_index,
                zap,
                replica,
                False,
            )
            V, ema, reference, theta, ladder = settle_with_blueprint(
                tissue,
                blueprint,
                "T",
                rng,
                None,
                config.futures,
                config.settle_sweeps,
                c_m=None,
            )
            pre_sign = V > 0
            previous_sign = pre_sign.copy()
            arrival = np.full(config.futures, -1, dtype=int)
            cumulative = np.zeros_like(V, dtype=float)
            snapshots: dict[int, np.ndarray] = {}
            mask = posterior_mask(tissue)
            for sweep in range(1, config.recovery_horizon + 1):
                clamp = mask if sweep <= zap else None
                V, ema, reference = blueprint_step(
                    V,
                    ema,
                    reference,
                    theta,
                    tissue,
                    ladder,
                    blueprint,
                    "T",
                    rng,
                    clamp=clamp,
                    c_m=None,
                )
                match = ((V > 0) == pre_sign).mean(axis=(-2, -1))
                newly = (
                    (arrival < 0)
                    & (match > config.arrival_cos_bar)
                    & (sweep > zap)
                )
                arrival[newly] = sweep
                released = sweep - zap
                if 1 <= released <= 10:
                    cumulative += ((V > 0) != previous_sign)
                    if released in windows:
                        snapshots[released] = cumulative.copy()
                previous_sign = V > 0
            arrived = arrival > 0
            for window in windows:
                maps[window].append(snapshots[window])
            arrivals.append(arrived)
            tissues.append(tissue_index)
            replicas.append(replica)
            rows.append(
                {
                    "tissue": tissue_index,
                    "replica": replica,
                    "recovery_rate": float(arrived.mean()),
                    "median_arrival": (
                        float(np.median(arrival[arrived])) if arrived.any() else None
                    ),
                }
            )
    return {
        "experiment": "E50",
        "rows": rows,
        "tissues": np.asarray(tissues, dtype=np.int16),
        "replicas": np.asarray(replicas, dtype=np.int16),
        "arrived": np.stack(arrivals),
        "maps": {str(key): np.stack(value) for key, value in maps.items()},
        "registered_window": "10",
        "exclude_zero_batch_maps": True,
        "elapsed_seconds": time.monotonic() - started,
        "futures_per_row": config.futures,
    }


def _raw_array_bundle(corpora: Mapping[str, Mapping[str, Any]]) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for experiment, corpus in corpora.items():
        prefix = experiment.lower()
        arrays[f"{prefix}_tissue"] = np.asarray(corpus["tissues"])
        arrays[f"{prefix}_replica"] = np.asarray(corpus["replicas"])
        arrays[f"{prefix}_arrived"] = np.asarray(corpus["arrived"], dtype=np.uint8)
        for window, maps in corpus["maps"].items():
            arrays[f"{prefix}_maps_window_{window}"] = np.asarray(maps)
    return arrays


def _analyse_corpus(
    corpus: Mapping[str, Any], *, bootstrap_seed: int
) -> dict[str, Any]:
    registered_window = str(corpus["registered_window"])
    individual_maps = np.asarray(corpus["maps"][registered_window])
    batch_maps = individual_maps.mean(axis=1)
    primary = batch_pair_analysis(
        batch_maps,
        np.asarray(corpus["tissues"]),
        exclude_zero=bool(corpus["exclude_zero_batch_maps"]),
        bootstrap_seed=bootstrap_seed,
    )
    individual = individual_pair_analysis(
        individual_maps,
        np.asarray(corpus["tissues"]),
        np.asarray(corpus["replicas"]),
        np.asarray(corpus["arrived"]),
    )
    different_batch_mean = individual["different_replica_batch"][
        "raw_cosine_all_maps"
    ]["mean"]
    registered_mean = primary["raw_cosine"]["mean"]
    sensitivities = {}
    for window, maps in corpus["maps"].items():
        window_batch = np.asarray(maps).mean(axis=1)
        sensitivities[str(window)] = simple_batch_pair_summary(
            window_batch,
            np.asarray(corpus["tissues"]),
            exclude_zero=bool(corpus["exclude_zero_batch_maps"]),
        )
    return {
        "historical_rows": len(corpus["rows"]),
        "historical_futures": int(
            len(corpus["rows"]) * int(corpus["futures_per_row"])
        ),
        "futures_per_batch_map": int(corpus["futures_per_row"]),
        "registered_window": registered_window,
        "elapsed_seconds": float(corpus["elapsed_seconds"]),
        "endpoint": {
            "arrived_futures": int(np.count_nonzero(corpus["arrived"])),
            "total_futures": int(np.asarray(corpus["arrived"]).size),
            "mean_recovery_rate": float(np.asarray(corpus["arrived"]).mean()),
            "batch_recovery_rate": _distribution(
                [row["recovery_rate"] for row in corpus["rows"]]
            ),
        },
        "individual_map_descriptors": map_descriptors(individual_maps),
        "batch_map_descriptors": map_descriptors(batch_maps),
        "registered_batch_pair_analysis": primary,
        "individual_future_pair_analysis": individual,
        "batch_mean_to_different_batch_individual_mean_cosine_ratio": (
            float(registered_mean / different_batch_mean)
            if registered_mean is not None
            and different_batch_mean is not None
            and different_batch_mean != 0
            else None
        ),
        "window_sensitivity": sensitivities,
    }


def _collect_inputs(
    plastic_root: Path, external_root: Path | None
) -> tuple[
    InputTracker,
    dict[str, Any],
    dict[str, str],
    dict[Path, str],
]:
    tracker = InputTracker()
    ideas = plastic_root / IDEAS_RELATIVE
    workspace = Path(__file__).resolve().parents[2]

    for path in (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas / "LAWS.md",
        ideas / "WAVE9_PROPHECIES.md",
        ideas / "WAVE10_PROPHECIES.md",
        ideas / "WAVE11_PROPHECIES.md",
        ideas / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        ideas / "RULIAD_DISCUSSION.md",
        ideas / "RELATED_PAPERS_THEORY_SYNTHESIS.md",
        workspace / "protocols/L12_RETAINED_REPLAY_AUDIT_V1.md",
        workspace / "protocols/L12_RETAINED_REPLAY_AUDIT_V1_1_AMENDMENT.md",
        workspace / "reviews/L10_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        workspace / "reviews/L11_RETAINED_REPLAY_AUDIT_2026-09-02.md",
    ):
        tracker.add(path)

    packages = {
        "james_test_2": ("results/full/james2_summary.json",),
        "james_test_3": (
            "results/full/james3_summary.json",
            "results/full/james3_round1_magnitudeE.json",
        ),
        "james_final": ("results/full/jamesfinal_summary.json",),
        "excitable_web": ("results/full/excitable_summary.json",),
        "growing_web": ("results/full/grow_summary.json",),
        "blueprint_web": ("results/full/calibration_square.json",),
        "ladder_web": (),
        "voltage_web": (),
        "setpoint_rewrite": (),
        "glider_test": (),
        "contract_bridge": (),
    }
    for name, retained in packages.items():
        _track_package(
            tracker,
            _experiment_root(plastic_root, name),
            retained_json=retained,
        )

    roots = {
        name: _experiment_root(plastic_root, name)
        for name in ("james_test_2", "james_test_3", "james_final")
    }
    retained = {
        "E42": tracker.json(
            roots["james_test_2"] / "results/full/james2_summary.json"
        ),
        "E46": tracker.json(
            roots["james_test_3"] / "results/full/james3_summary.json"
        ),
        "E50": tracker.json(
            roots["james_final"] / "results/full/jamesfinal_summary.json"
        ),
    }
    source_texts = {
        "E42": _read(
            tracker, roots["james_test_2"] / "src/james_test_2/pipeline.py"
        ),
        "E42_expectations": _read(
            tracker, roots["james_test_2"] / "EXPECTATIONS.md"
        ),
        "E46": _read(
            tracker, roots["james_test_3"] / "src/james_test_3/pipeline.py"
        ),
        "E46_expectations": _read(
            tracker, roots["james_test_3"] / "EXPECTATIONS.md"
        ),
        "E50": _read(
            tracker, roots["james_final"] / "src/james_final/pipeline.py"
        ),
        "E50_expectations": _read(
            tracker, roots["james_final"] / "EXPECTATIONS.md"
        ),
        "excitable_engine": _read(
            tracker,
            _experiment_root(plastic_root, "excitable_web")
            / "src/excitable_web/engine.py",
        ),
        "growing_engine": _read(
            tracker,
            _experiment_root(plastic_root, "growing_web")
            / "src/growing_web/engine.py",
        ),
        "blueprint_engine": _read(
            tracker,
            _experiment_root(plastic_root, "blueprint_web")
            / "src/blueprint_web/engine.py",
        ),
    }
    if external_root is not None:
        for relative in (
            "outputs/l10_retained_replay_audit_v1_attempt2/audit.json",
            "outputs/l11_retained_replay_audit_v1/audit.json",
        ):
            path = external_root / relative
            if path.is_file():
                tracker.add(path)
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    return tracker, retained, source_texts, frozen_hashes


def _source_audit(source: Mapping[str, str]) -> dict[str, Any]:
    e42 = source["E42"]
    e46 = source["E46"]
    e50 = source["E50"]
    return {
        "road_definitions_are_common_across_experiments": False,
        "E42": {
            "registered_map_is_batch_mean": (
                "act.mean(axis=0).ravel().tolist()" in e42
            ),
            "registered_map_is_single_time_snapshot": (
                "zap_sweeps + 3" in e42 and "act_maps[sweep]" in e42
            ),
            "registered_map_is_firing_event_history": False,
            "configured_mid_fraction_is_used": "config.mid_fraction" in e42,
            "computed_mid_sweep_selects_registered_map": False,
            "persistent_material_identity_tracked": False,
            "overlay_itself_consumes_rng": "no rng draws" not in source[
                "excitable_engine"
            ].lower(),
            "identity_layer_is_stochastic": "rng" in source["excitable_engine"],
        },
        "E46": {
            "registered_map_is_batch_mean": "swap_map.mean(axis=0)" in e46,
            "registered_map_accumulates_accepted_swap_left_slots": (
                "road += swap_map.mean(axis=0)" in e46
                and "return V_new, do_swap" in e46
            ),
            "both_swap_endpoints_recorded": False,
            "persistent_cell_identity_or_net_displacement_tracked": False,
            "explicit_random_axis_parity_proposal_acceptance": all(
                token in source["growing_engine"]
                for token in (
                    "mrng.random()",
                    "mrng.integers(0, 2)",
                    "proposal_fraction",
                    "mrng.random(V.shape)",
                )
            ),
            "axis_and_parity_draws_shared_by_all_futures_in_a_batch": (
                "axis = -1 if mrng.random() < 0.5 else -2"
                in source["growing_engine"]
                and "parity = int(mrng.integers(0, 2))"
                in source["growing_engine"]
            ),
        },
        "E50": {
            "registered_map_is_batch_mean": (
                "((V > 0) != prev_sign).mean(axis=0)" in e50
                and "road.ravel().tolist()" in e50
            ),
            "registered_map_accumulates_voltage_sign_flips": (
                "((V > 0) != prev_sign).mean(axis=0)" in e50
            ),
            "material_motion_tracked": False,
            "zero_batch_maps_excluded": (
                "if np.asarray(r[\"road\"]).sum() > 0" in e50
            ),
            "varying_means_gate_requires_endpoint_convergence": False,
            "predeclared_noise_scattered_threshold": (
                "noise-scattered" in source["E50_expectations"].lower()
            ),
        },
        "road_gate_varies_insult_location_or_shape": False,
        "road_gate_uses_fixed_posterior_zap": True,
        "error_geometry_causally_identified": False,
        "general_exploration_necessity_tested": False,
    }


def run_l12_audit(
    plastic_root: Path,
    external_root: Path | None = None,
    *,
    replay: bool = False,
) -> tuple[dict[str, Any], list[Path], dict[str, np.ndarray], dict[Path, str]]:
    """Audit L12 and optionally replay its exact historical road corpus."""

    tracker, retained, source_texts, frozen_hashes = _collect_inputs(
        plastic_root, external_root
    )
    calculated_digests = source_config_digests()
    retained_digests = {
        "E42_james_test_2": retained["E42"]["config_digest"],
        "E46_james_test_3": retained["E46"]["config_digest"],
        "E50_james_final": retained["E50"]["config_digest"],
    }
    digest_matches = {
        key: (
            calculated_digests[key]
            == EXPECTED_CONFIG_DIGESTS[key]
            == retained_digests[key]
        )
        for key in EXPECTED_CONFIG_DIGESTS
    }
    source_audit = _source_audit(source_texts)

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L12",
        "audit_kind": (
            "outcome-known retained-source audit with historical road-map "
            "re-instrumentation"
        ),
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed": 0,
        "source_config_digests": calculated_digests,
        "retained_config_digests": retained_digests,
        "config_digest_matches": digest_matches,
        "all_config_digests_match": all(digest_matches.values()),
        "source_audit": source_audit,
        "replay_status": "NOT_RUN",
        "overall_verdict": "NOT_ADJUDICATED_REPLAY_NOT_RUN",
    }
    raw_arrays: dict[str, np.ndarray] = {}

    if replay:
        corpora = {"E42": _replay_e42(), "E46": _replay_e46(), "E50": _replay_e50()}
        analyses = {
            "E42": _analyse_corpus(corpora["E42"], bootstrap_seed=20260902120),
            "E46": _analyse_corpus(corpora["E46"], bootstrap_seed=20260902121),
            "E50": _analyse_corpus(corpora["E50"], bootstrap_seed=20260902122),
        }
        raw_arrays = _raw_array_bundle(corpora)

        calculated = {
            "E42": {
                "mean_replica_map_cos": analyses["E42"][
                    "registered_batch_pair_analysis"
                ]["raw_cosine"]["mean"],
                "mean_endpoint_recovery": analyses["E42"]["endpoint"][
                    "mean_recovery_rate"
                ],
            },
            "E46": {
                "mean_road_cos": analyses["E46"][
                    "registered_batch_pair_analysis"
                ]["raw_cosine"]["mean"],
                "mean_endpoint_recovery": analyses["E46"]["endpoint"][
                    "mean_recovery_rate"
                ],
            },
            "E50": {
                "mean_road_cos": analyses["E50"][
                    "registered_batch_pair_analysis"
                ]["raw_cosine"]["mean"],
            },
        }
        calculated["E42"]["gate_p42_1_varying_means"] = bool(
            calculated["E42"]["mean_replica_map_cos"] < 0.7
            and calculated["E42"]["mean_endpoint_recovery"] >= 0.8
        )
        calculated["E46"]["gate_p46_1_varying_means"] = bool(
            calculated["E46"]["mean_road_cos"] < 0.7
            and calculated["E46"]["mean_endpoint_recovery"] >= 0.8
        )
        calculated["E50"]["gate_p50_4_varying_means"] = bool(
            analyses["E50"]["registered_batch_pair_analysis"]["pair_count"]
            and calculated["E50"]["mean_road_cos"] < 0.8
        )
        expected = {
            "E42": {
                key: retained["E42"]["gates"][key]
                for key in (
                    "mean_replica_map_cos",
                    "mean_endpoint_recovery",
                    "gate_p42_1_varying_means",
                )
            },
            "E46": {
                key: retained["E46"]["gates"][key]
                for key in (
                    "mean_road_cos",
                    "mean_endpoint_recovery",
                    "gate_p46_1_varying_means",
                )
            },
            "E50": {
                key: retained["E50"]["gates"][key]
                for key in ("mean_road_cos", "gate_p50_4_varying_means")
            },
        }
        reconstruction = {
            experiment: {
                "calculated": calculated[experiment],
                "retained": expected[experiment],
                "exact_match": _recursive_close(
                    calculated[experiment], expected[experiment]
                ),
            }
            for experiment in ("E42", "E46", "E50")
        }
        all_reconstruct = all(
            item["exact_match"] for item in reconstruction.values()
        )
        e50_scattering = e50_scattering_analysis(
            corpora["E50"]["maps"][corpora["E50"]["registered_window"]]
        )
        claim_assessment = {
            "reported_replica_correlations_around_0_94_to_0_97": {
                "status": (
                    "CONFIRMED_WITH_NARROWER_WORDING"
                    if reconstruction["E42"]["exact_match"]
                    and reconstruction["E46"]["exact_match"]
                    else "NOT_CONFIRMED"
                ),
                "reason": (
                    "The E42 and E46 retained means reconstruct, but both are "
                    "cosines between future-averaged activity maps, not tracked "
                    "material repair paths. E46's raw value is reproduced by "
                    "toroidal shifts and disappears after spatial centering."
                ),
            },
            "error_geometry_determines_repair_paths": {
                "status": "NOT_CONFIRMED_CAUSALLY",
                "reason": (
                    "The road gate fixes one posterior insult geometry and does "
                    "not independently vary geometry against anatomy, reference, "
                    "boundary conditions, or update physics."
                ),
            },
            "tested_physics_contains_no_structured_exploration_source": {
                "status": "NOT_CONFIRMED_AND_UNDEFINED",
                "reason": (
                    "Structured exploration has no operational criterion; E46 "
                    "explicitly includes random axes, parity, proposals, and "
                    "Metropolis acceptances, whose variation is partly erased by "
                    "averaging futures."
                ),
            },
            "E50_exception_is_not_many_structured_roads_to_one_destination": {
                "status": "CONFIRMED_WITH_NARROWER_WORDING",
                "reason": (
                    "E50's maps are sign-flip activity summaries and no naive "
                    f"future reaches the registered pre-zap destination; "
                    f"{e50_scattering['zero_maps']} of "
                    f"{e50_scattering['individual_maps']} individual maps are "
                    "exactly zero. The stronger causal "
                    "label 'noise-scattered' was not prospectively defined."
                ),
            },
            "many_roads_one_destination_requires_exploration_in_general": {
                "status": "NOT_CONFIRMED_AS_GENERAL_NECESSITY",
                "reason": (
                    "The simulations test fixed protocols only; deterministic "
                    "systems can have multiple paths across initial states, "
                    "perturbations, symmetries, or controls."
                ),
            },
            "biological_repair_path_law": {
                "status": "NOT_CONFIRMED",
                "reason": (
                    "Manuscript v2.3 predates these experiments and no physical or "
                    "biological repair-path experiment is present."
                ),
            },
        }
        audit.update(
            {
                "replay_status": "COMPLETE",
                "historical_rows_replayed": sum(REPLAY_ROWS.values()),
                "historical_simulator_futures_replayed": sum(
                    REPLAY_FUTURES.values()
                ),
                "replay_elapsed_seconds": float(
                    sum(corpus["elapsed_seconds"] for corpus in corpora.values())
                ),
                "retained_reconstruction": reconstruction,
                "all_retained_road_fields_reconstruct": all_reconstruct,
                "road_analyses": analyses,
                "E50_scattering_analysis": e50_scattering,
                "claim_assessment": claim_assessment,
                "overall_verdict": "MIXED" if all_reconstruct else "NOT_CONFIRMED",
                "plain_language_result": (
                    "The published 0.965, 0.942, and 0.115 map correlations are "
                    "reproducible. They compare three different batch-averaged "
                    "activity proxies, not identifiable repair paths. E46's dense "
                    "swap map has the same raw cosine after spatial translation, "
                    "E42 reaches its endpoint in only about half of futures, and "
                    "E50 has sparse sign-flip maps but no arrival at the claimed "
                    "common destination. The runs do not isolate error geometry."
                ),
            }
        )

    changed_inputs = [
        str(path)
        for path, digest in frozen_hashes.items()
        if sha256_file(path) != digest
    ]
    if changed_inputs:
        raise RuntimeError(f"L12 input changed during audit: {changed_inputs}")
    audit["input_integrity"] = {
        "input_file_count": len(frozen_hashes),
        "changed_during_audit": changed_inputs,
        "all_rechecked_unchanged": not changed_inputs,
    }
    return audit, sorted(tracker.paths), raw_arrays, frozen_hashes


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_report(audit: Mapping[str, Any]) -> str:
    """Render the immutable machine-audit companion report."""

    if audit.get("replay_status") != "COMPLETE":
        return "# L12 retained/replay audit\n\nReplay was not run.\n"
    analyses = audit["road_analyses"]
    reconstruction = audit["retained_reconstruction"]
    lines = [
        "# L12 retained/replay single-road audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`.",
        "",
        audit["plain_language_result"],
        "",
        "## Exact retained reconstruction",
        "",
        "| Experiment | Defined road | Batch maps | Map pairs | Mean cosine | Endpoint recovery | Original gate |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    definitions = {
        "E42": "single-time FHN activity, mean of 24 futures",
        "E46": "10-sweep accepted-left-slot swaps, mean of 16 futures",
        "E50": "10-sweep voltage sign flips, mean of 16 futures",
    }
    gate_keys = {
        "E42": "gate_p42_1_varying_means",
        "E46": "gate_p46_1_varying_means",
        "E50": "gate_p50_4_varying_means",
    }
    cosine_keys = {
        "E42": "mean_replica_map_cos",
        "E46": "mean_road_cos",
        "E50": "mean_road_cos",
    }
    for experiment in ("E42", "E46", "E50"):
        analysis = analyses[experiment]
        calculated = reconstruction[experiment]["calculated"]
        lines.append(
            "| "
            + " | ".join(
                (
                    experiment,
                    definitions[experiment],
                    str(analysis["registered_batch_pair_analysis"]["included_batch_maps"]),
                    str(analysis["registered_batch_pair_analysis"]["pair_count"]),
                    _fmt(calculated[cosine_keys[experiment]]),
                    _fmt(analysis["endpoint"]["mean_recovery_rate"]),
                    "PASS" if calculated[gate_keys[experiment]] else "FAIL",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "All registered fields above reconstruct the retained summaries: "
            f"`{_fmt(audit['all_retained_road_fields_reconstruct'])}`.",
            "",
            "## Batch averaging and spatial alignment",
            "",
            "| Experiment | Individual cross-batch raw | Batch raw | Batch centered | Inflation ratio | Shift-null raw | Observed - shift null | Cross-tissue raw |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for experiment in ("E42", "E46", "E50"):
        analysis = analyses[experiment]
        primary = analysis["registered_batch_pair_analysis"]
        individual = analysis["individual_future_pair_analysis"][
            "different_replica_batch"
        ]["raw_cosine_all_maps"]["mean"]
        null = primary["exact_nonzero_toroidal_translation_null"]
        lines.append(
            "| "
            + " | ".join(
                (
                    experiment,
                    _fmt(individual),
                    _fmt(primary["raw_cosine"]["mean"]),
                    _fmt(primary["mean_centered_cosine"]["mean"]),
                    _fmt(
                        analysis[
                            "batch_mean_to_different_batch_individual_mean_cosine_ratio"
                        ]
                    ),
                    _fmt(null["raw_cosine"]["mean"]),
                    _fmt(null["observed_minus_pair_null_mean_raw"]["mean"]),
                    _fmt(primary["between_tissue"]["raw_cosine"]["mean"]),
                )
            )
            + " |"
        )
    e42_analysis = analyses["E42"]
    e46_analysis = analyses["E46"]
    e50_analysis = analyses["E50"]
    e46_primary = e46_analysis["registered_batch_pair_analysis"]
    e46_windows = e46_analysis["window_sensitivity"]
    lines.extend(
        [
            "",
            "The translation comparator preserves every map's amplitudes and local "
            "structure while breaking absolute registration on the periodic grid. "
            "It is a diagnostic, not a universal chance null. Future-pair counts are "
            "also descriptive because pairs share tissues and maps.",
            "",
            f"- E42's batch cosine {_fmt(e42_analysis['registered_batch_pair_analysis']['raw_cosine']['mean'])} "
            f"falls to {_fmt(e42_analysis['individual_future_pair_analysis']['different_replica_batch']['raw_cosine_all_maps']['mean'])} "
            "between individual futures. Its spatial registration is real under the "
            "shift diagnostic, but cross-tissue maps remain highly similar because "
            "every tissue receives the same posterior geometry.",
            f"- Every E46 batch map is positive at all 256 pixels; normalized "
            f"effective support averages {_fmt(e46_analysis['batch_map_descriptors']['normalized_effective_support']['mean'])}. "
            f"Raw cosine is {_fmt(e46_primary['raw_cosine']['mean'])}, centered "
            f"cosine is {_fmt(e46_primary['mean_centered_cosine']['mean'])}, and "
            f"the translated-map null is {_fmt(e46_primary['exact_nonzero_toroidal_translation_null']['raw_cosine']['mean'])}. "
            "The scalar therefore measures dense positive activity more than a "
            "shared spatial route.",
            f"- E46 raw cosine rises from {_fmt(e46_windows['1']['raw_cosine']['mean'])} "
            f"after one released sweep to {_fmt(e46_windows['10']['raw_cosine']['mean'])} "
            "after ten accumulated sweeps, while its centered cosine remains near "
            "zero. The road verdict is window-sensitive.",
            "",
            "## Endpoint and measurement boundary",
            "",
        ]
    )
    for experiment in ("E42", "E46", "E50"):
        endpoint = analyses[experiment]["endpoint"]
        lines.append(
            f"- {experiment}: {endpoint['arrived_futures']} / "
            f"{endpoint['total_futures']} historical futures reach its registered "
            "endpoint."
        )
    scatter = audit["E50_scattering_analysis"]
    e50_primary = e50_analysis["registered_batch_pair_analysis"]
    lines.extend(
        [
            "",
            "E42 records an instantaneous wave-state map; E46 records accepted swap "
            "left-slots; E50 records voltage sign changes. None records persistent "
            "cell identity or a material route. E50 therefore cannot be an example "
            "of many roads to one destination: its naive endpoint is never reached.",
            "",
            "## E50 zero-map exclusion and pair weighting",
            "",
            "| Tissue | Included maps | Excluded zero maps | Included pairs | Tissue mean cosine |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for tissue in range(10):
        tissue_key = str(tissue)
        lines.append(
            "| "
            + " | ".join(
                (
                    tissue_key,
                    str(e50_primary["included_batch_maps_by_tissue"][tissue_key]),
                    str(
                        e50_primary["excluded_zero_batch_maps_by_tissue"][
                            tissue_key
                        ]
                    ),
                    str(e50_primary["pair_count_by_tissue"][tissue_key]),
                    _fmt(e50_primary["tissue_means"].get(tissue_key)),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            f"The retained pooled mean is {_fmt(e50_primary['raw_cosine']['mean'])} "
            f"over {e50_primary['pair_count']} pairs. The equal mean over the "
            f"{e50_primary['tissues_with_at_least_one_pair']} eligible tissues is "
            f"{_fmt(e50_primary['equal_eligible_tissue_mean_raw_cosine'])}; treating "
            f"the no-pair tissue as zero gives "
            f"{_fmt(e50_primary['equal_all_tissue_mean_with_missing_as_zero_sensitivity'])}. "
            f"{e50_primary['zero_cosine_pairs']} of the included pairs have cosine "
            f"zero and {e50_primary['unit_cosine_pairs']} have cosine one. The gate "
            "passes under every listed weighting, but `0.115` is not an equally "
            "weighted ten-tissue estimate.",
            "",
            "## E50 sign-flip scattering",
            "",
            f"- Individual zero maps: {scatter['zero_maps']} / "
            f"{scatter['individual_maps']}.",
            f"- Non-zero maps: {scatter['nonzero_maps']}; maps with at least two "
            f"active pixels: {scatter['maps_with_at_least_two_active_pixels']}; "
            f"maps with any adjacent active pixels: "
            f"{scatter['maps_with_adjacent_active_pixels']}.",
            f"- Active-pixel histogram: {scatter['active_pixel_histogram']}.",
            f"- Among {scatter['largest_component_fraction']['n']} non-zero maps, "
            f"the median largest-component share is "
            f"{_fmt(scatter['largest_component_fraction']['median'])}.",
            f"- Among {scatter['occupied_edge_enrichment_vs_uniform_same_size_support']['n']} "
            "maps for which same-size edge enrichment is defined, the median is "
            f"{_fmt(scatter['occupied_edge_enrichment_vs_uniform_same_size_support']['median'])}.",
            "",
            "These measurements describe spatial scattering. They do not establish "
            "that stochastic noise caused it; no pre-outcome structured/noise "
            "criterion was registered.",
            "",
            "## Source-design asymmetries",
            "",
            "- E42 calls its map mid-repair, but `mid_fraction` does not select it; "
            "the computed `mid_sweep` is unused and the gate always takes the fixed "
            "`zap + 3` snapshot.",
            "- E46 draws one axis and parity for an entire vectorized future batch "
            "during each motility phase. Its futures have separate sitewise proposal "
            "and acceptance draws but share those global movement directions.",
            "- E42 and E46 required endpoint convergence in their varying-means "
            "gates. E50 removed that requirement, then passed on sparse sign flips "
            "despite zero endpoint arrivals.",
            "- The high-correlation single-road interpretation was named after E42 "
            "and E46 failed prospectively registered low-correlation predictions. "
            "It is an outcome-known hypothesis, not an independent confirmation.",
            "",
            "## Clause verdicts",
            "",
            "| Clause | Status | Reason |",
            "|---|---|---|",
        ]
    )
    labels = {
        "reported_replica_correlations_around_0_94_to_0_97": (
            "E42/E46 replica correlations are about 0.94--0.97"
        ),
        "error_geometry_determines_repair_paths": (
            "Error geometry determines repair paths"
        ),
        "tested_physics_contains_no_structured_exploration_source": (
            "No tested physics supplies structured exploration"
        ),
        "E50_exception_is_not_many_structured_roads_to_one_destination": (
            "E50 is not evidence for structured many-road repair"
        ),
        "many_roads_one_destination_requires_exploration_in_general": (
            "Many roads generally require an exploration source"
        ),
        "biological_repair_path_law": "Biological repair-path law",
    }
    for key, label in labels.items():
        assessment = audit["claim_assessment"][key]
        lines.append(
            f"| {label} | `{assessment['status']}` | {assessment['reason']} |"
        )
    integrity = audit["input_integrity"]
    lines.extend(
        [
            "",
            "## Integrity and scope",
            "",
            f"- Input files hashed and rechecked: {integrity['input_file_count']}; "
            f"changed during audit: {len(integrity['changed_during_audit'])}.",
            f"- Historical rows replayed: {audit['historical_rows_replayed']}.",
            f"- Historical simulator futures replayed: "
            f"{audit['historical_simulator_futures_replayed']}.",
            "- Fresh scientific futures generated: 0.",
            "- Numerical threads/workers: one (enforced by the launcher).",
            "",
            "## First-pass conclusion",
            "",
            "The numerical correlations are real under their exact definitions. "
            "The stronger law is not confirmed: the maps are heterogeneous activity "
            "proxies averaged over futures; geometry was not independently varied; "
            "E46's raw cosine is a dense-map accumulation artefact rather than "
            "location-specific agreement; explicit stochasticity exists in the "
            "motile model; and the only low-correlation case has no common endpoint. "
            "The defensible replacement is that fixed posterior insults produced a "
            "repeatable batch-average wave pattern in E42, diffuse accepted-swap "
            "activity in E46, and sparse sign flips without pre-zap recovery in E50.",
            "",
        ]
    )
    return "\n".join(lines)
