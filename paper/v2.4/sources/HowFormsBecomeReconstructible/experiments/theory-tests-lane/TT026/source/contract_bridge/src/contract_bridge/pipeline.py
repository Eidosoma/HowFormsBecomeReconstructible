"""Campaign stages: build, strict-mc, freeze, analyze."""

from __future__ import annotations

import csv
import itertools
import multiprocessing as mp
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from finite_gard_ruliad.combinatorics import RuleCodec
from finite_gard_ruliad.kernels import make_state_spaces, solve_absorption
from finite_gard_ruliad.observers import predictive_signatures
from finite_gard_ruliad.quotients import (
    adjusted_rand,
    normalized_variation_information,
    quantized_partition,
)
from finite_gard_ruliad.strict8 import exact_strict_probabilities

from .artifacts import (
    atomic_json,
    atomic_npz,
    environment_manifest,
    hash_fraction,
    progress,
    seed_rng,
    sha256_file,
    valid_npz,
    write_checksums,
)
from .config import (
    SEALED_BINOMIAL_CSV_SHA256,
    BridgeConfig,
    results_root,
    sibling_root,
    work_root,
)
from .estimator_calibration import gate_operating_characteristics, rank_reliability
from .ordinal_quotients import fast_partition_distortion, offset_fractions, rank_partition
from .physics import build_bundle, closed_kernel, expected_physical_time, gauge_beta
from .recalibration import (
    MonotoneMap,
    conditional_residual_model,
    pav_isotonic_fit,
    quantile_map_fit,
    removable_fraction,
)
from .scoring import BLOCK_NAMES, BlockScaler, candidate_maps, score_map
from .strict_binomial import (
    ForwardBudgetExceeded,
    automaton_census,
    exact_strict_probabilities_any,
    forward_reference_any,
    simulate_strict_paths,
)

_WILSON_Z = 1.959963984540054

_ENV: dict[str, dict] = {}


def _env(config: BridgeConfig) -> dict:
    key = config.digest()
    if key not in _ENV:
        atlas = config.atlas()
        spaces = make_state_spaces(atlas)
        _ENV[key] = {
            "atlas": atlas,
            "spaces": spaces,
            "codec": RuleCodec(atlas),
            "launch_rows": np.asarray(
                [
                    idx
                    for idx, state in enumerate(spaces.all_nonzero)
                    if sum(state) == atlas.n_min
                ],
                dtype=np.int64,
            ),
        }
    return _ENV[key]


def _wilson(p_hat: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    z2 = _WILSON_Z**2
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denom
    margin = (_WILSON_Z / denom) * np.sqrt(p_hat * (1 - p_hat) / n + z2 / (4 * n**2))
    return np.maximum(0.0, center - margin), np.minimum(1.0, center + margin)


def _chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _orbit_table(config: BridgeConfig) -> tuple[np.ndarray, np.ndarray]:
    path = work_root(config) / "orbits.npz"
    if valid_npz(path, config.digest(), ("rule_ids", "orbit_sizes")):
        with np.load(path) as data:
            return data["rule_ids"].copy(), data["orbit_sizes"].copy()
    codec = _env(config)["codec"]
    orbits = codec.rule_orbits()
    rule_ids = np.asarray([orbit.canonical_id for orbit in orbits], dtype=np.int64)
    sizes = np.asarray([len(orbit.members) for orbit in orbits], dtype=np.int64)
    atomic_npz(
        path,
        config_digest=np.asarray(config.digest()),
        rule_ids=rule_ids,
        orbit_sizes=sizes,
    )
    return rule_ids, sizes


def _hash_selection(tag: str, rule_ids: np.ndarray, count: int) -> np.ndarray:
    order = np.argsort([hash_fraction(tag, int(r)) for r in rule_ids], kind="stable")
    return rule_ids[order[:count]]


# ---------------------------------------------------------------------------
# Stage: build
# ---------------------------------------------------------------------------

_BUILD_KEYS = (
    "rule_ids",
    "orbit_sizes",
    "strict_equal",
    "equal_features",
    "binomial_features",
    "shape_h8",
    "physical_time",
    "gauge_error",
)


def _build_shard(task: tuple) -> tuple[str, int]:
    config, rule_ids, orbit_sizes, path_str = task
    path = Path(path_str)
    if valid_npz(path, config.digest(), _BUILD_KEYS):
        return path_str, 0
    env = _env(config)
    atlas, spaces, codec = env["atlas"], env["spaces"], env["codec"]
    launch_rows = env["launch_rows"]
    strict_rows = []
    eq_rows = []
    bin_rows = []
    shape_rows = []
    time_rows = []
    gauge_rows = []
    feature_names: tuple[str, ...] | None = None
    for rule_id in rule_ids:
        beta = codec.matrix(int(rule_id))
        absorption = solve_absorption(int(rule_id), beta, atlas, spaces)
        equal_closed = closed_kernel(int(rule_id), beta, "equal", atlas, spaces, absorption)
        strict_rows.append(exact_strict_probabilities(equal_closed, atlas).probabilities)
        eq_sig = predictive_signatures(equal_closed, atlas)
        binomial_closed = closed_kernel(
            int(rule_id), beta, "binomial", atlas, spaces, absorption
        )
        bin_sig = predictive_signatures(binomial_closed, atlas, launch_mass=atlas.n_min)
        if feature_names is None:
            feature_names = eq_sig.feature_names
        eq_rows.append(eq_sig.values)
        bin_rows.append(bin_sig.values)
        shape_rows.append(eq_sig.shape_h8)
        time_rows.append(expected_physical_time(beta, atlas, spaces)[launch_rows])
        gauged = solve_absorption(
            int(rule_id), gauge_beta(beta, config.gauge_factor), atlas, spaces
        )
        gauge_rows.append(
            float(np.max(np.abs(gauged.probabilities - absorption.probabilities)))
        )
    atomic_npz(
        path,
        config_digest=np.asarray(config.digest()),
        rule_ids=np.asarray(rule_ids, dtype=np.int64),
        orbit_sizes=np.asarray(orbit_sizes, dtype=np.int64),
        strict_equal=np.asarray(strict_rows),
        equal_features=np.asarray(eq_rows),
        binomial_features=np.asarray(bin_rows),
        shape_h8=np.asarray(shape_rows),
        physical_time=np.asarray(time_rows),
        gauge_error=np.asarray(gauge_rows),
        feature_names=np.asarray(feature_names),
    )
    return path_str, len(rule_ids)


def run_census(config: BridgeConfig) -> dict:
    env = _env(config)
    atlas, spaces, codec = env["atlas"], env["spaces"], env["codec"]
    beta = codec.matrix(0)
    payload = {"config_digest": config.digest()}
    for contract in ("equal", "binomial"):
        kernel = closed_kernel(0, beta, contract, atlas, spaces)
        census = automaton_census(
            kernel,
            atlas,
            state_bound=config.census_state_bound,
            seconds_budget=config.census_seconds_budget,
        )
        payload[contract] = census.as_dict()
    payload["exact_binomial_feasible"] = payload["binomial"]["within_bound"]
    atomic_json(results_root(config) / "strict_feasibility.json", payload)
    return payload


def build_bridge(config: BridgeConfig, jobs: int = 8) -> dict:
    config.validate()
    started = time.time()
    rule_ids, orbit_sizes = _orbit_table(config)
    shard_dir = work_root(config) / "build"
    tasks = []
    for index, chunk in enumerate(_chunks(list(range(len(rule_ids))), config.shard_size)):
        tasks.append(
            (
                config,
                tuple(int(rule_ids[i]) for i in chunk),
                tuple(int(orbit_sizes[i]) for i in chunk),
                str(shard_dir / f"build_{index:05d}.npz"),
            )
        )
    progress_path = work_root(config) / "progress.json"
    completed = 0
    if jobs <= 1:
        for task in tasks:
            _build_shard(task)
            completed += 1
            progress(progress_path, stage="build", completed=completed, total=len(tasks), started=started)
    else:
        with mp.Pool(processes=jobs) as pool:
            for _ in pool.imap_unordered(_build_shard, tasks):
                completed += 1
                progress(progress_path, stage="build", completed=completed, total=len(tasks), started=started)
    census = run_census(config)
    manifest = {
        "config": config.as_dict(),
        "config_digest": config.digest(),
        "n_rule_orbits": int(len(rule_ids)),
        "n_shards": len(tasks),
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
        "exact_binomial_feasible": census["exact_binomial_feasible"],
    }
    atomic_json(results_root(config) / "build_manifest.json", manifest)
    return manifest


def _load_build(config: BridgeConfig) -> dict:
    shard_dir = work_root(config) / "build"
    paths = sorted(shard_dir.glob("build_*.npz"))
    if not paths:
        raise FileNotFoundError("no build shards found; run the build stage first")
    chunks: dict[str, list[np.ndarray]] = {key: [] for key in _BUILD_KEYS}
    feature_names: tuple[str, ...] | None = None
    for path in paths:
        if not valid_npz(path, config.digest(), _BUILD_KEYS):
            raise RuntimeError(f"stale or invalid build shard: {path}")
        with np.load(path) as data:
            for key in _BUILD_KEYS:
                chunks[key].append(data[key].copy())
            if feature_names is None:
                feature_names = tuple(str(v) for v in data["feature_names"])
    out = {key: np.concatenate(chunks[key], axis=0) for key in _BUILD_KEYS}
    order = np.argsort(out["rule_ids"], kind="stable")
    for key in _BUILD_KEYS:
        out[key] = out[key][order]
    out["feature_names"] = feature_names
    return out


# ---------------------------------------------------------------------------
# Stage: strict-mc
# ---------------------------------------------------------------------------

_MC_KEYS = ("rule_id", "probability", "half_a", "half_b", "success_counts", "n_futures")


def _mc_orbit(task: tuple) -> tuple[int, int]:
    config, rule_id, exact_ok, path_str = task
    path = Path(path_str)
    if valid_npz(path, config.digest(), _MC_KEYS):
        return rule_id, 0
    env = _env(config)
    atlas, spaces, codec = env["atlas"], env["spaces"], env["codec"]
    beta = codec.matrix(int(rule_id))
    kernel = closed_kernel(int(rule_id), beta, "binomial", atlas, spaces)
    diagnostic = simulate_strict_paths(
        kernel,
        atlas,
        rule_key=int(rule_id),
        n_futures=config.mc_futures,
        seed_tag=config.mc_seed_tag,
    )
    n_launch = len(diagnostic.launch_states)
    success_counts = np.zeros((n_launch, atlas.strict_horizon), dtype=np.int32)
    for row in range(n_launch):
        steps = diagnostic.success_step[row]
        hits = steps[steps >= 0]
        if hits.size:
            np.add.at(success_counts[row], hits.astype(np.int64), 1)
    arrays = {
        "config_digest": np.asarray(config.digest()),
        "rule_id": np.asarray(int(rule_id)),
        "probability": diagnostic.probability,
        "half_a": diagnostic.half_a,
        "half_b": diagnostic.half_b,
        "success_counts": success_counts,
        "n_futures": np.asarray(diagnostic.n_futures),
        "exact_available": np.asarray(bool(exact_ok)),
    }
    if exact_ok:
        exact = exact_strict_probabilities_any(
            kernel,
            atlas,
            launch_mass=atlas.n_min,
            precheck_state_bound=config.census_state_bound,
        )
        arrays["exact_probability"] = exact.probabilities
    atomic_npz(path, **arrays)
    return rule_id, 1


def _sampler_equal_check(config: BridgeConfig, rule_ids: np.ndarray) -> dict:
    env = _env(config)
    atlas, spaces, codec = env["atlas"], env["spaces"], env["codec"]
    selected = _hash_selection("bridge-samplercheck", rule_ids, config.sampler_check_rules)
    n = config.sampler_check_futures
    max_z = 0.0
    max_abs = 0.0
    cells = 0
    within = 0
    for rule_id in selected:
        beta = codec.matrix(int(rule_id))
        kernel = closed_kernel(int(rule_id), beta, "equal", atlas, spaces)
        exact = exact_strict_probabilities(kernel, atlas).probabilities
        sampled = simulate_strict_paths(
            kernel,
            atlas,
            rule_key=int(rule_id),
            n_futures=n,
            seed_tag=config.mc_seed_tag + "-equalcheck",
        ).probability
        se = np.sqrt(np.maximum(exact * (1 - exact), 1e-12) / n)
        z = np.abs(sampled - exact) / se
        max_z = max(max_z, float(z.max()))
        max_abs = max(max_abs, float(np.max(np.abs(sampled - exact))))
        cells += len(exact)
        within += int((z <= 5.0).sum())
    return {
        "rules": [int(r) for r in selected],
        "futures": n,
        "cells": cells,
        "within_5_se": within,
        "max_z": max_z,
        "max_abs_error": max_abs,
    }


def _truncated_forward_check(config: BridgeConfig, rule_ids: np.ndarray) -> dict:
    env = _env(config)
    atlas, spaces, codec = env["atlas"], env["spaces"], env["codec"]
    selected = _hash_selection("bridge-forwardcheck", rule_ids, config.forward_check_orbits)
    horizon = min(config.forward_check_horizon, atlas.strict_horizon)
    entries = []
    for rule_id in selected:
        record = {"rule": int(rule_id), "horizon": horizon}
        mc_path = work_root(config) / "strict_mc" / f"orbit_{int(rule_id):07d}.npz"
        with np.load(mc_path) as data:
            counts = data["success_counts"].copy()
            n_futures = int(data["n_futures"])
        beta = codec.matrix(int(rule_id))
        kernel = closed_kernel(int(rule_id), beta, "binomial", atlas, spaces)
        try:
            forward = forward_reference_any(
                kernel,
                atlas,
                launch_mass=atlas.n_min,
                horizon=horizon,
                key_budget=config.forward_check_key_budget,
            )
        except ForwardBudgetExceeded as error:
            record["status"] = "skipped"
            record["reason"] = str(error)
            entries.append(record)
            continue
        exact_cumulative = forward.success_by_step[horizon - 1]
        mc_cumulative = counts[:, :horizon].sum(axis=1) / n_futures
        se = np.sqrt(np.maximum(exact_cumulative * (1 - exact_cumulative), 1e-12) / n_futures)
        z = np.abs(mc_cumulative - exact_cumulative) / se
        record.update(
            {
                "status": "compared",
                "peak_keys": forward.peak_keys,
                "max_z": float(z.max()),
                "max_abs_error": float(np.max(np.abs(mc_cumulative - exact_cumulative))),
            }
        )
        entries.append(record)
    return {"horizon": horizon, "entries": entries}


def run_strict_mc(config: BridgeConfig, jobs: int = 8) -> dict:
    config.validate()
    started = time.time()
    feasibility_path = results_root(config) / "strict_feasibility.json"
    if not feasibility_path.exists():
        run_census(config)
    import json

    feasibility = json.loads(feasibility_path.read_text())
    exact_ok = bool(feasibility["exact_binomial_feasible"])
    rule_ids, _ = _orbit_table(config)
    mc_dir = work_root(config) / "strict_mc"
    tasks = [
        (config, int(rule_id), exact_ok, str(mc_dir / f"orbit_{int(rule_id):07d}.npz"))
        for rule_id in rule_ids
    ]
    progress_path = work_root(config) / "progress.json"
    completed = 0
    if jobs <= 1:
        for task in tasks:
            _mc_orbit(task)
            completed += 1
            if completed % 16 == 0 or completed == len(tasks):
                progress(progress_path, stage="strict-mc", completed=completed, total=len(tasks), started=started)
    else:
        with mp.Pool(processes=jobs) as pool:
            for _ in pool.imap_unordered(_mc_orbit, tasks, chunksize=4):
                completed += 1
                if completed % 16 == 0 or completed == len(tasks):
                    progress(progress_path, stage="strict-mc", completed=completed, total=len(tasks), started=started)
    sampler_check = _sampler_equal_check(config, rule_ids)
    forward_check = _truncated_forward_check(config, rule_ids)
    manifest = {
        "config_digest": config.digest(),
        "n_orbits": len(tasks),
        "mc_futures": config.mc_futures,
        "exact_binomial_feasible": exact_ok,
        "sampler_equal_check": sampler_check,
        "truncated_forward_check": forward_check,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(results_root(config) / "mc_manifest.json", manifest)
    return manifest


def _load_mc(config: BridgeConfig, rule_ids: np.ndarray) -> dict:
    mc_dir = work_root(config) / "strict_mc"
    probability = []
    half_a = []
    half_b = []
    exact_rows = []
    exact_available = None
    n_futures = None
    for rule_id in rule_ids:
        path = mc_dir / f"orbit_{int(rule_id):07d}.npz"
        if not valid_npz(path, config.digest(), _MC_KEYS):
            raise RuntimeError(f"missing or stale strict-mc orbit file: {path}")
        with np.load(path) as data:
            probability.append(data["probability"].copy())
            half_a.append(data["half_a"].copy())
            half_b.append(data["half_b"].copy())
            available = bool(data["exact_available"])
            if exact_available is None:
                exact_available = available
            if available:
                exact_rows.append(data["exact_probability"].copy())
            n_futures = int(data["n_futures"])
    out = {
        "probability": np.asarray(probability),
        "half_a": np.asarray(half_a),
        "half_b": np.asarray(half_b),
        "exact_available": bool(exact_available),
        "n_futures": n_futures,
    }
    if exact_available:
        out["exact_probability"] = np.asarray(exact_rows)
    return out


# ---------------------------------------------------------------------------
# Translator ladder (shared by freeze and analyze)
# ---------------------------------------------------------------------------


def _nontrivial_permutation(n: int, rng: np.random.Generator) -> tuple[int, ...]:
    identity = tuple(range(n))
    while True:
        perm = tuple(int(v) for v in rng.permutation(n))
        if perm != identity:
            return perm


def _ladder_rows(
    config: BridgeConfig,
    rule_ids: list[int],
    outlook_pairs: list[tuple[int, int]],
    strict_bin: dict[int, np.ndarray],
    recal_maps: dict[str, MonotoneMap] | None,
    half: str,
) -> list[dict]:
    env = _env(config)
    atlas, spaces, codec = env["atlas"], env["spaces"], env["codec"]
    regularization = config.sinkhorn_regularization
    rows: list[dict] = []

    def emit(rung, rule_a, rule_b, maps, bundle_a, bundle_b, extra=None):
        for map_name, coupling in maps.items():
            scores = score_map(bundle_a, bundle_b, coupling)
            row = {
                "half": half,
                "rung": rung,
                "rule_a": rule_a,
                "rule_b": rule_b,
                "map": map_name,
                **scores,
            }
            if extra and map_name == "identity":
                row.update(extra)
            rows.append(row)

    def equal_bundle(rule_id: int, beta=None):
        beta = codec.matrix(rule_id) if beta is None else beta
        absorption = solve_absorption(rule_id, beta, atlas, spaces)
        kernel = closed_kernel(rule_id, beta, "equal", atlas, spaces, absorption)
        strict = exact_strict_probabilities(kernel, atlas).probabilities
        return (
            build_bundle(rule_id, beta, "equal", atlas, spaces, strict=strict, absorption=absorption),
            beta,
            strict,
            absorption,
        )

    for rule_id in rule_ids:
        bundle_a, beta, strict_eq, absorption = equal_bundle(rule_id)
        rng = seed_rng(config.ladder_seed_tag, rule_id)
        perm = _nontrivial_permutation(atlas.n_types, rng)

        relabeled_rule = codec.permute_rule(rule_id, perm)
        bundle_b, beta_b, _, _ = equal_bundle(relabeled_rule)
        maps = candidate_maps(
            bundle_a,
            bundle_b,
            beta,
            beta_b,
            regularization=regularization,
            random_permutation=_nontrivial_permutation(atlas.n_types, rng),
            exact_permutation=perm,
        )
        emit("exact_relabel", rule_id, relabeled_rule, maps, bundle_a, bundle_b)

        gauged = gauge_beta(beta, config.gauge_factor)
        gauge_bundle = build_bundle(
            rule_id, gauged, "equal", atlas, spaces, strict=strict_eq
        )
        maps = candidate_maps(
            bundle_a,
            gauge_bundle,
            beta,
            gauged,
            regularization=regularization,
            random_permutation=_nontrivial_permutation(atlas.n_types, rng),
        )
        emit("clock_gauge", rule_id, rule_id, maps, bundle_a, gauge_bundle)

        binomial_bundle = build_bundle(
            rule_id,
            beta,
            "binomial",
            atlas,
            spaces,
            strict=strict_bin[rule_id],
            absorption=absorption,
        )
        extra = {}
        if recal_maps:
            for kind, mapping in recal_maps.items():
                extra[f"strict_mae_recal_{kind}"] = float(
                    np.mean(np.abs(mapping.apply(strict_eq) - strict_bin[rule_id]))
                )
        maps = candidate_maps(
            bundle_a,
            binomial_bundle,
            beta,
            beta,
            regularization=regularization,
            random_permutation=_nontrivial_permutation(atlas.n_types, rng),
        )
        emit("contract", rule_id, rule_id, maps, bundle_a, binomial_bundle, extra=extra)

    for rule_a, rule_b in outlook_pairs:
        bundle_a, beta_a, _, _ = equal_bundle(rule_a)
        bundle_b, beta_b, _, _ = equal_bundle(rule_b)
        rng = seed_rng(config.ladder_seed_tag, rule_a, rule_b)
        maps = candidate_maps(
            bundle_a,
            bundle_b,
            beta_a,
            beta_b,
            regularization=regularization,
            random_permutation=_nontrivial_permutation(atlas.n_types, rng),
        )
        emit("nonisomorphic_outlook", rule_a, rule_b, maps, bundle_a, bundle_b)

    return rows


def _ladder_selection(
    config: BridgeConfig, rule_ids: np.ndarray, dev_mask: np.ndarray, half: str
) -> tuple[list[int], list[tuple[int, int]]]:
    pool = rule_ids[dev_mask] if half == "dev" else rule_ids[~dev_mask]
    selected = _hash_selection(config.ladder_seed_tag, pool, config.ladder_rules)
    outlook_pool = _hash_selection(
        config.ladder_seed_tag + "-outlook", pool, 2 * config.outlook_pairs
    )
    pairs = [
        (int(outlook_pool[2 * i]), int(outlook_pool[2 * i + 1]))
        for i in range(len(outlook_pool) // 2)
    ]
    return [int(r) for r in selected], pairs


# ---------------------------------------------------------------------------
# Stage: freeze
# ---------------------------------------------------------------------------


def _dev_mask(config: BridgeConfig, rule_ids: np.ndarray) -> np.ndarray:
    return np.asarray(
        [hash_fraction(config.dev_split_tag, int(r)) < 0.5 for r in rule_ids], dtype=bool
    )


def _feature_matrices(build: dict, mc: dict) -> tuple[np.ndarray, np.ndarray]:
    n_rules, n_states, n_features = build["equal_features"].shape
    equal = np.concatenate(
        [
            build["equal_features"].reshape(n_rules * n_states, n_features),
            build["strict_equal"].reshape(-1, 1),
        ],
        axis=1,
    )
    binomial = np.concatenate(
        [
            build["binomial_features"].reshape(n_rules * n_states, n_features),
            mc["probability"].reshape(-1, 1),
        ],
        axis=1,
    )
    return equal, binomial


def _frontier_rows(
    config: BridgeConfig,
    equal_values: np.ndarray,
    binomial_values: np.ndarray,
    shapes: np.ndarray,
    *,
    variant: str,
) -> list[dict]:
    rows = []
    specs = []
    for eps in config.epsilon_grid:
        for offset in (0.0, 0.5):
            specs.append(("epsilon", float(eps), float(offset)))
    for quantiles in config.ordinal_quantile_grid:
        for offset in offset_fractions(config.ordinal_offsets):
            specs.append(("rank", float(quantiles), float(offset)))
    for family, resolution, offset in specs:
        if family == "epsilon":
            labels_eq = quantized_partition(equal_values, resolution, offset)
            labels_bin = quantized_partition(binomial_values, resolution, offset)
        else:
            labels_eq = rank_partition(equal_values, int(resolution), offset)
            labels_bin = rank_partition(binomial_values, int(resolution), offset)
        distortion = fast_partition_distortion(labels_eq, equal_values, shapes)
        rows.append(
            {
                "variant": variant,
                "family": family,
                "resolution": resolution,
                "offset": offset,
                **distortion,
                "cross_contract_ari": adjusted_rand(labels_eq, labels_bin),
                "cross_contract_nvi": normalized_variation_information(labels_eq, labels_bin),
            }
        )
    return rows


def _recommend_quotient(rows: list[dict]) -> dict:
    candidates = [
        row
        for row in rows
        if row["family"] == "rank" and row["cross_contract_ari"] >= 0.8
    ]
    if not candidates:
        candidates = [row for row in rows if row["family"] == "rank"]
    best = max(candidates, key=lambda row: (row["compression"], row["cross_contract_ari"]))
    return {key: best[key] for key in ("family", "resolution", "offset", "compression", "cross_contract_ari")}


def freeze_components(config: BridgeConfig) -> dict:
    config.validate()
    rule_ids, orbit_sizes = _orbit_table(config)
    build = _load_build(config)
    mc = _load_mc(config, build["rule_ids"])
    dev_rules = _dev_mask(config, build["rule_ids"])
    n_states = build["strict_equal"].shape[1]
    dev_cells = np.repeat(dev_rules, n_states)
    cell_weights = np.repeat(build["orbit_sizes"], n_states).astype(np.float64)

    p_eq = build["strict_equal"].reshape(-1)
    p_bin = (
        mc["exact_probability"] if mc["exact_available"] else mc["probability"]
    ).reshape(-1)

    isotonic = pav_isotonic_fit(p_eq[dev_cells], p_bin[dev_cells], cell_weights[dev_cells])
    quantile = quantile_map_fit(p_eq[dev_cells], p_bin[dev_cells], config.quantile_map_knots)
    recal_maps = {"isotonic": isotonic, "quantile": quantile}

    ladder_rules, outlook_pairs = _ladder_selection(config, build["rule_ids"], dev_rules, "dev")
    strict_bin = {
        int(rule): p_bin.reshape(-1, n_states)[index]
        for index, rule in enumerate(build["rule_ids"])
    }
    dev_rows = _ladder_rows(config, ladder_rules, outlook_pairs, strict_bin, recal_maps, "dev")
    scaler = BlockScaler.fit([{name: row[name] for name in BLOCK_NAMES} for row in dev_rows])
    for row in dev_rows:
        row["composite"] = scaler.composite({name: row[name] for name in BLOCK_NAMES})

    equal_values, binomial_values = _feature_matrices(build, mc)
    shapes = build["shape_h8"].reshape(equal_values.shape[0], -1)
    dev_frontier = _frontier_rows(
        config,
        equal_values[dev_cells],
        binomial_values[dev_cells],
        shapes[dev_cells],
        variant="dev_raw",
    )
    recommended = _recommend_quotient(dev_frontier)

    payload = {
        "config_digest": config.digest(),
        "dev_split_tag": config.dev_split_tag,
        "n_dev_rules": int(dev_rules.sum()),
        "n_eval_rules": int((~dev_rules).sum()),
        "recalibration_maps": {kind: m.as_dict() for kind, m in recal_maps.items()},
        "block_scaler": scaler.as_dict(),
        "block_names": list(BLOCK_NAMES),
        "ladder_dev_rules": ladder_rules,
        "ladder_dev_outlook_pairs": outlook_pairs,
        "recommended_quotient": recommended,
        "truth_source": "exact_dp" if mc["exact_available"] else f"mc{mc['n_futures']}",
        "environment": environment_manifest(),
    }
    atomic_json(results_root(config) / "frozen_components.json", payload)
    pd.DataFrame(dev_rows).to_csv(
        work_root(config) / "ladder_dev_rows.csv", index=False
    )
    return payload


# ---------------------------------------------------------------------------
# Stage: analyze
# ---------------------------------------------------------------------------


def _load_frozen(config: BridgeConfig) -> dict:
    import json

    path = results_root(config) / "frozen_components.json"
    if not path.exists():
        raise FileNotFoundError("frozen_components.json missing; run the freeze stage first")
    payload = json.loads(path.read_text())
    if payload["config_digest"] != config.digest():
        raise RuntimeError("frozen components were fitted under a different configuration")
    return payload


def _rule_architecture(config: BridgeConfig, rule_ids: np.ndarray) -> pd.DataFrame:
    env = _env(config)
    codec = env["codec"]
    atlas = env["atlas"]
    n = atlas.n_types
    top_level = len(atlas.beta_levels) - 1
    rows = []
    for rule_id in rule_ids:
        digits = np.asarray(codec.digits(int(rule_id)), dtype=np.int64).reshape(n, n)
        levels = np.asarray(atlas.beta_levels)[digits]
        rows.append(
            {
                "canonical_rule": int(rule_id),
                "diagonal_nonzero": int((np.diag(digits) > 0).sum()),
                "diagonal_top": int((np.diag(digits) == top_level).sum()),
                "total_strength": float(levels.sum()),
                "nonzero_entries": int((digits > 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def _sealed_csv_check(config: BridgeConfig, atlas_frame: pd.DataFrame) -> dict:
    if config.mode != "full":
        return {"status": "skipped", "reason": "sealed comparison is a full-mode check"}
    path = sibling_root("finite_gard_ruliad") / "results" / "full" / "binomial_strict_diagnostic.csv"
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    digest = sha256_file(path)
    if digest != SEALED_BINOMIAL_CSV_SHA256:
        return {"status": "hash_mismatch", "observed": digest}
    sealed = pd.read_csv(path)
    ours = atlas_frame.set_index(["canonical_rule", "state"])
    covered = 0
    compared = 0
    sealed_values = []
    our_values = []
    for record in sealed.itertuples(index=False):
        key = (int(record.canonical_rule), str(record.launch))
        if key not in ours.index:
            continue
        value = float(ours.loc[key, "p_binomial"])
        compared += 1
        sealed_values.append(float(record.probability))
        our_values.append(value)
        if float(record.wilson_low) <= value <= float(record.wilson_high):
            covered += 1
    rho = float(spearmanr(sealed_values, our_values).statistic) if compared > 2 else None
    return {
        "status": "compared",
        "cells_compared": compared,
        "coverage_fraction": covered / compared if compared else None,
        "spearman_vs_sealed": rho,
    }


def analyze_bridge(config: BridgeConfig, jobs: int = 1) -> dict:
    import json

    config.validate()
    frozen = _load_frozen(config)
    build = _load_build(config)
    mc = _load_mc(config, build["rule_ids"])
    results = results_root(config)
    env = _env(config)
    atlas, spaces = env["atlas"], env["spaces"]
    n_states = build["strict_equal"].shape[1]
    launch_states = [
        state for state in spaces.all_nonzero if sum(state) == atlas.n_min
    ]

    dev_rules = _dev_mask(config, build["rule_ids"])
    dev_cells = np.repeat(dev_rules, n_states)
    p_eq = build["strict_equal"].reshape(-1)
    truth_is_exact = mc["exact_available"]
    p_bin = (mc["exact_probability"] if truth_is_exact else mc["probability"]).reshape(-1)
    p_bin_mc = mc["probability"].reshape(-1)
    wilson_lo, wilson_hi = _wilson(p_bin_mc, mc["n_futures"])

    # ---- Part A: atlas table and contract-shift summary -------------------
    atlas_frame = pd.DataFrame(
        {
            "canonical_rule": np.repeat(build["rule_ids"], n_states),
            "state": [str(tuple(state)) for _ in range(len(build["rule_ids"])) for state in launch_states],
            "state_id": list(range(n_states)) * len(build["rule_ids"]),
            "orbit_size": np.repeat(build["orbit_sizes"], n_states),
            "half": np.where(dev_cells, "dev", "eval"),
            "p_equal_exact": p_eq,
            "p_binomial": p_bin,
            "truth_source": "exact_dp" if truth_is_exact else f"mc{mc['n_futures']}",
            "p_binomial_mc": p_bin_mc,
            "mc_wilson_low": wilson_lo,
            "mc_wilson_high": wilson_hi,
            "mc_half_a": mc["half_a"].reshape(-1),
            "mc_half_b": mc["half_b"].reshape(-1),
        }
    )
    atlas_frame.to_csv(results / "binomial_strict_atlas.csv", index=False)

    rule_mean_eq = build["strict_equal"].mean(axis=1)
    rule_mean_bin = p_bin.reshape(-1, n_states).mean(axis=1)
    se_bin = np.sqrt(np.maximum(p_bin_mc * (1 - p_bin_mc), 1e-12) / mc["n_futures"])
    diff = p_bin - p_eq
    architecture = _rule_architecture(config, build["rule_ids"])
    architecture["mean_strict_equal"] = rule_mean_eq
    architecture["mean_strict_binomial"] = rule_mean_bin

    mc_manifest_path = results / "mc_manifest.json"
    mc_manifest = json.loads(mc_manifest_path.read_text()) if mc_manifest_path.exists() else {}

    weights = np.repeat(build["orbit_sizes"], n_states).astype(np.float64)
    summary_a = {
        "n_cells": int(len(p_eq)),
        "n_rule_orbits": int(len(build["rule_ids"])),
        "truth_source": "exact_dp" if truth_is_exact else f"mc{mc['n_futures']}",
        "mc_futures": mc["n_futures"],
        "weighted_mean_equal": float(np.average(p_eq, weights=weights)),
        "weighted_mean_binomial": float(np.average(p_bin, weights=weights)),
        "cell_spearman": float(spearmanr(p_eq, p_bin).statistic),
        "cell_pearson": float(pearsonr(p_eq, p_bin).statistic),
        "rule_spearman": float(spearmanr(rule_mean_eq, rule_mean_bin).statistic),
        "rule_pearson": float(pearsonr(rule_mean_eq, rule_mean_bin).statistic),
        "sign_flip_fraction_raw": float(np.average(diff > 0, weights=weights)),
        "sign_flip_fraction_significant": float(
            np.average((diff > 2 * se_bin), weights=weights)
        ),
        "mean_abs_shift": float(np.average(np.abs(diff), weights=weights)),
        "architecture": {
            "diag_spearman_equal": float(
                spearmanr(architecture["diagonal_nonzero"], rule_mean_eq).statistic
            ),
            "diag_spearman_binomial": float(
                spearmanr(architecture["diagonal_nonzero"], rule_mean_bin).statistic
            ),
            "strength_spearman_equal": float(
                spearmanr(architecture["total_strength"], rule_mean_eq).statistic
            ),
            "strength_spearman_binomial": float(
                spearmanr(architecture["total_strength"], rule_mean_bin).statistic
            ),
        },
        "observed_mc_split_half_spearman": float(
            spearmanr(mc["half_a"].reshape(-1), mc["half_b"].reshape(-1)).statistic
        ),
        "sealed_e1b_check": _sealed_csv_check(config, atlas_frame),
        "sampler_equal_check": mc_manifest.get("sampler_equal_check"),
        "truncated_forward_check": mc_manifest.get("truncated_forward_check"),
    }
    atomic_json(results / "contract_shift_summary.json", summary_a)

    # ---- Part B: recalibration on the eval half ---------------------------
    recal_maps = {
        kind: MonotoneMap.from_dict(payload)
        for kind, payload in frozen["recalibration_maps"].items()
    }
    eval_cells = ~dev_cells
    recal_rows = []
    for kind, mapping in recal_maps.items():
        for half_name, mask in (("dev", dev_cells), ("eval", eval_cells)):
            metrics = removable_fraction(p_eq, p_bin, mapping, mask, weights)
            metrics["half"] = half_name
            recal_rows.append(metrics)
    pd.DataFrame(recal_rows).to_csv(results / "recalibration_metrics.csv", index=False)

    feature_columns = ("diagonal_nonzero", "diagonal_top", "total_strength", "nonzero_entries")
    rule_features = architecture[list(feature_columns)].to_numpy(dtype=np.float64)
    cell_features = np.repeat(rule_features, n_states, axis=0)
    conditional = conditional_residual_model(
        p_eq,
        p_bin,
        recal_maps["quantile"],
        cell_features,
        feature_columns,
        dev_cells,
        eval_cells,
    )
    controls = {
        "gauge_max_absorption_error": float(build["gauge_error"].max()),
        "gauge_factor": config.gauge_factor,
        "conditional_residual_model": conditional,
    }
    atomic_json(results / "recalibration_controls.json", controls)

    # ---- Part C: translator ladder on the eval half -----------------------
    scaler = BlockScaler.from_dict(frozen["block_scaler"])
    eval_rules_list, eval_pairs = _ladder_selection(config, build["rule_ids"], dev_rules, "eval")
    strict_bin = {
        int(rule): p_bin.reshape(-1, n_states)[index]
        for index, rule in enumerate(build["rule_ids"])
    }
    eval_rows = _ladder_rows(config, eval_rules_list, eval_pairs, strict_bin, recal_maps, "eval")
    for row in eval_rows:
        row["composite"] = scaler.composite({name: row[name] for name in BLOCK_NAMES})
    dev_rows_path = work_root(config) / "ladder_dev_rows.csv"
    ladder_frame = pd.DataFrame(eval_rows)
    if dev_rows_path.exists():
        ladder_frame = pd.concat([pd.read_csv(dev_rows_path), ladder_frame], ignore_index=True)
    ladder_frame.to_csv(results / "translator_ladder.csv", index=False)

    ladder_summary = (
        ladder_frame.groupby(["half", "rung", "map"])["composite"]
        .median()
        .reset_index()
        .to_dict(orient="records")
    )
    eval_frame = ladder_frame[ladder_frame["half"] == "eval"]
    checks = {
        "exact_relabel_max_composite": float(
            eval_frame[
                (eval_frame["rung"] == "exact_relabel") & (eval_frame["map"] == "exact")
            ]["composite"].max()
        ),
        "clock_gauge_identity_event_blocks_max": float(
            eval_frame[
                (eval_frame["rung"] == "clock_gauge") & (eval_frame["map"] == "identity")
            ][["kernel_js_1", "kernel_js_2", "kernel_js_4", "kernel_js_8", "strict_mae", "destination_mae"]]
            .to_numpy()
            .max()
        ),
        "clock_gauge_identity_time_block_min": float(
            eval_frame[
                (eval_frame["rung"] == "clock_gauge") & (eval_frame["map"] == "identity")
            ]["time_log_mae"].min()
        ),
    }
    atomic_json(
        results / "translator_summary.json",
        {"medians": ladder_summary, "checks": checks},
    )

    # ---- Part D: ordinal frontier -----------------------------------------
    equal_values, binomial_values = _feature_matrices(build, mc)
    shapes = build["shape_h8"].reshape(equal_values.shape[0], -1)
    frontier = _frontier_rows(config, equal_values, binomial_values, shapes, variant="raw")
    recal_equal = equal_values.copy()
    recal_equal[:, -1] = recal_maps["quantile"].apply(recal_equal[:, -1])
    frontier += _frontier_rows(config, recal_equal, binomial_values, shapes, variant="recalibrated")
    frontier_frame = pd.DataFrame(frontier)
    frontier_frame.to_csv(results / "ordinal_frontier.csv", index=False)

    recommended = frozen["recommended_quotient"]
    eval_equal = equal_values[eval_cells]
    eval_binomial = binomial_values[eval_cells]
    labels_eq = rank_partition(eval_equal, int(recommended["resolution"]), recommended["offset"])
    labels_bin = rank_partition(eval_binomial, int(recommended["resolution"]), recommended["offset"])
    recommended_eval = {
        **{key: recommended[key] for key in ("family", "resolution", "offset")},
        **fast_partition_distortion(labels_eq, eval_equal, shapes[eval_cells]),
        "cross_contract_ari": adjusted_rand(labels_eq, labels_bin),
        "cross_contract_nvi": normalized_variation_information(labels_eq, labels_bin),
    }

    # ---- Part E: estimator calibration ------------------------------------
    group = np.repeat(np.arange(len(build["rule_ids"])), n_states)
    reliability = rank_reliability(
        p_eq,
        config.estimator_budgets,
        config.estimator_replicates,
        config.estimator_seed_tag,
        group=group,
    )
    pd.DataFrame(reliability).to_csv(results / "estimator_rank_reliability.csv", index=False)
    gates = gate_operating_characteristics(p_eq, config.estimator_budgets, config.gate_grid)
    pd.DataFrame(gates).to_csv(results / "estimator_gate_oc.csv", index=False)

    metrics = {
        "config_digest": config.digest(),
        "part_a": {
            key: summary_a[key]
            for key in (
                "cell_spearman",
                "rule_spearman",
                "sign_flip_fraction_raw",
                "weighted_mean_equal",
                "weighted_mean_binomial",
            )
        },
        "part_a_sealed_check": summary_a["sealed_e1b_check"],
        "part_b_eval": [row for row in recal_rows if row["half"] == "eval"],
        "part_c_checks": checks,
        "part_d_recommended_quotient_eval": recommended_eval,
        "part_e_observed_split_half": summary_a["observed_mc_split_half_spearman"],
        "environment": environment_manifest(),
    }
    atomic_json(results / "METRICS.json", metrics)
    return metrics


def finalize_results(config: BridgeConfig) -> None:
    results = results_root(config)
    write_checksums(results, results / "SHA256SUMS")
