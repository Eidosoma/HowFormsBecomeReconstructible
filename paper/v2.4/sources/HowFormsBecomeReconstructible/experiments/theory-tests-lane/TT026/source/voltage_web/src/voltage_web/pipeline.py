"""E26: operating-point screen, coupling sweet spot, regeneration gate."""

from __future__ import annotations

from dataclasses import replace
import json
import time

import numpy as np

from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng

from .config import VoltageConfig, results_root
from .engine import run_seed

G_LADDER = (0.1, 0.25, 0.5, 1.0, 2.0, 4.0)
# Dev round 3: sigma 0.3 added (round-2 near-misses broke softly, H< at
# 3-4%% vs the 5%% bar); parental-inheritance criterion added (at g -> 0 the
# quenched theta field, not the parent fragment, determines the regrown
# pattern — inheritance must come FROM THE PARENT to count).
SIGMA_LADDER = (0.05, 0.10, 0.20, 0.30)
# Dev round 2: 1x cells pinned the clock at the sweep cap (median 60-64)
# and spontaneous strict switches never occur (repair is strong; switches
# are E27's induced business) — budgets shrink, and the strict-band
# criterion is replaced by multi-attractor capacity + survival.
BUDGET_FRACTIONS = (0.25, 0.5, 1.0)


def screen_points(config: VoltageConfig) -> list[dict]:
    if config.mode == "tiny":
        return [dict(coupling=g) for g in (0.5, 2.0)]
    return [
        {"coupling": g, "sigma": s, "activity_budget": int(m * config.cells)}
        for g in G_LADDER for s in SIGMA_LADDER for m in BUDGET_FRACTIONS
    ]


def _screen_point(config: VoltageConfig, overrides: dict,
                  n_seeds: int, futures: int) -> dict:
    point = replace(config, **overrides)
    h_all, stricts, breaks, clocks, survivals = [], [], [], [], []
    prebreaks = {}
    for seed in range(min(point.n_seeds, n_seeds)):
        stats, _resettled, prebreak = run_seed(
            seed, point, seed_rng(point.trajectory_seed_tag + "-screen", seed),
            n_futures=futures, collect_forms=True,
        )
        stricts.append(stats.strict_probability)
        breaks.append(float(((stats.first_break >= 0) & (stats.first_break < 8)).mean()))
        survivals.append(float((stats.survival_generation >= 8).mean()))
        if stats.h_values.size:
            h_all.append(stats.h_values)
        clocks.append(float(np.median(stats.first_generation_time)))
        if seed < 6:
            prebreaks[seed] = prebreak
    h = np.concatenate(h_all) if h_all else np.zeros(0)
    stricts_arr = np.asarray(stricts)
    clock_iqr = float(np.subtract(*np.quantile(clocks, [0.75, 0.25])))
    # Multi-attractor capacity: distinct structured seeds hold distinct
    # stable censuses (pairwise cosine below the distinct threshold).
    def _cos(u, v):
        d = np.linalg.norm(u) * np.linalg.norm(v)
        return float(u @ v / d) if d > 0 else 1.0

    keys = [k for k in prebreaks if np.linalg.norm(prebreaks[k]) > 0]
    distinct_pairs = sum(
        _cos(prebreaks[a], prebreaks[b]) < point.distinct_threshold
        for i, a in enumerate(keys) for b in keys[i + 1:]
    )
    # Parental inheritance (mini): fragments must beat random fragments.
    mode_h = {}
    for mode in ("fragment", "random_fragment"):
        values = []
        for seed in range(4):
            s = run_seed(
                seed, point,
                seed_rng(point.trajectory_seed_tag + "-screen-regen-" + mode, seed),
                n_futures=16, fission_mode=mode,
            )
            values.append(float(s.h_values.mean()) if s.h_values.size else 0.0)
        mode_h[mode] = float(np.mean(values))
    criteria = {
        "h_straddles": bool(
            h.size
            and float((h > point.inherit_threshold).mean()) >= 0.30
            and float((h < point.distinct_threshold).mean()) >= 0.05
        ),
        "multi_attractor": bool(distinct_pairs >= 3),
        "survival": bool(np.median(survivals) >= 0.3),
        "break_dispersion": bool(np.ptp(breaks) > 0.02),
        "clock_alive": bool(
            clock_iqr > 0 and point.t_min_sweeps < np.median(clocks) < point.t_max_sweeps
        ),
        "parental_inheritance": bool(
            mode_h["fragment"] >= mode_h["random_fragment"] + 0.02
        ),
    }
    criteria["pass"] = all(criteria.values())
    return {
        "overrides": overrides,
        "criteria": criteria,
        "h_above": float((h > point.inherit_threshold).mean()) if h.size else 0.0,
        "h_below": float((h < point.distinct_threshold).mean()) if h.size else 0.0,
        "distinct_pairs": int(distinct_pairs),
        "median_survival": float(np.median(survivals)),
        "mean_strict": float(stricts_arr.mean()),
        "max_strict": float(stricts_arr.max()),
        "median_clock": float(np.median(clocks)),
        "mean_break8": float(np.mean(breaks)),
        "fragment_h": mode_h["fragment"],
        "random_fragment_h": mode_h["random_fragment"],
    }


def run_screen(config: VoltageConfig, *, point: int | None = None,
               n_seeds: int = 8, futures: int = 32) -> dict:
    started = time.time()
    points = screen_points(config)
    work = results_root(config) / "work"
    work.mkdir(parents=True, exist_ok=True)
    if point is not None:
        entry = _screen_point(config, points[point], n_seeds, futures)
        entry["elapsed_seconds"] = time.time() - started
        atomic_json(work / f"screen_point_{point:02d}.json", entry)
        return entry
    grid = []
    for index, overrides in enumerate(points):
        shard = work / f"screen_point_{index:02d}.json"
        grid.append(
            json.loads(shard.read_text()) if shard.exists()
            else _screen_point(config, overrides, n_seeds, futures)
        )
    passing = [g for g in grid if g["criteria"]["pass"]]
    # Gate 2: the coupling sweet spot — passing g values interior on the
    # ladder at some (sigma, budget) column.
    sweet = False
    if config.mode == "full":
        for s in SIGMA_LADDER:
            for m in BUDGET_FRACTIONS:
                column = {
                    g["overrides"]["coupling"]: g["criteria"]["pass"]
                    for g in grid
                    if g["overrides"]["sigma"] == s
                    and g["overrides"]["activity_budget"] == int(m * config.cells)
                }
                gs = sorted(column)
                if any(column[g] for g in gs) and not column[gs[0]] and not column[gs[-1]]:
                    interior = [g for g in gs[1:-1] if column[g]]
                    if interior:
                        sweet = True
    payload = {
        "config_digest": config.digest(),
        "grid": grid,
        "n_passing": len(passing),
        "gate_regime_exists": bool(passing),
        "gate_coupling_sweet_spot": bool(sweet),
        "best": passing[0]["overrides"] if passing else None,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(config)
    atomic_json(out / "screen.json", payload)
    return payload


def run_regeneration(config: VoltageConfig, overrides: dict | None = None) -> dict:
    """Gate 3: fragments beat density-matched random fragments."""
    started = time.time()
    point = replace(config, **(overrides or {}))
    rows = {}
    for mode in ("fragment", "random_fragment"):
        h_means, survivals = [], []
        for seed in range(point.n_seeds):
            stats = run_seed(
                seed, point,
                seed_rng(point.trajectory_seed_tag + "-regen-" + mode, seed),
                fission_mode=mode,
            )
            h_means.append(
                float(stats.h_values.mean()) if stats.h_values.size else 0.0
            )
            survivals.append(float((stats.survival_generation >= 8).mean()))
        rows[mode] = {
            "mean_h": float(np.mean(h_means)),
            "survival_8": float(np.mean(survivals)),
            "per_seed_h": h_means,
        }
    frag, rand = rows["fragment"], rows["random_fragment"]
    payload = {
        "config_digest": point.digest(),
        "overrides": overrides or {},
        "fragment": frag,
        "random_fragment": rand,
        "gate_regeneration": bool(
            frag["mean_h"] > point.inherit_threshold
            and frag["mean_h"] > rand["mean_h"]
        ),
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(config)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "regeneration.json", payload)
    return payload
