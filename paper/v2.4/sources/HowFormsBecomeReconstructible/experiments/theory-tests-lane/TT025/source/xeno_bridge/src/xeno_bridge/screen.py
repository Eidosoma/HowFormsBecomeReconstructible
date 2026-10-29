"""Dev-only operating-point screen for a hereditary regime.

Uses dev-seed-tag tables only. Confirmation tables come from the disjoint
confirm seed tag and are generated only after the operating point,
thresholds, and budgets are frozen — screening never inspects them.
"""

from __future__ import annotations

from dataclasses import replace
import time

import numpy as np

from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng

from .chemistry import build_chemistry, sample_table
from .config import XenoConfig, results_root
from .lineage import run_seed


def _point_metrics(config: XenoConfig, n_tables: int, n_seeds: int, futures: int) -> dict:
    chemistry = build_chemistry(config)
    table_stats = []
    h_all = []
    break_by_8 = []
    for table_index in range(n_tables):
        table = sample_table(
            chemistry, config, seed_rng(config.dev_table_seed_tag, table_index)
        )
        strict = []
        for seed_index in range(n_seeds):
            stats = run_seed(
                table,
                seed_index,
                chemistry,
                config,
                seed_rng(config.trajectory_seed_tag, table_index, seed_index),
                n_futures=futures,
            )
            strict.append(stats.strict_probability)
            h_all.append(stats.h_values)
            valid_break = (stats.first_break >= 0) & (stats.first_break < 8)
            break_by_8.append(float(valid_break.mean()))
        table_stats.append(
            {
                "table": table_index,
                "mean_strict": float(np.mean(strict)),
                "max_strict": float(np.max(strict)),
                "turnover": stats.mean_catalyzed_per_molecule,
                "repair_fraction": stats.repair_fraction,
                "events_per_generation": stats.mean_events_per_generation,
                "survival_8": float((stats.survival_generation >= 8).mean()),
                "first_generation_time": float(np.median(stats.first_generation_time)),
            }
        )
    h = np.concatenate(h_all) if h_all else np.zeros(0)
    quartiles = np.quantile(break_by_8, (0.25, 0.75)) if break_by_8 else (0.0, 0.0)
    metrics = {
        "h_fraction_above_inherit": float((h > config.inherit_threshold).mean()) if h.size else 0.0,
        "h_fraction_below_distinct": float((h < config.distinct_threshold).mean()) if h.size else 0.0,
        "h_median": float(np.median(h)) if h.size else 0.0,
        "break_by_8_iqr": float(quartiles[1] - quartiles[0]),
        "tables": table_stats,
    }
    strict_values = [t["mean_strict"] for t in table_stats]
    metrics["criteria"] = {
        "h_straddles_thresholds": bool(
            metrics["h_fraction_above_inherit"] >= 0.10
            and metrics["h_fraction_below_distinct"] >= 0.10
        ),
        "strict_in_band": bool(any(0.005 <= v <= 0.5 for v in strict_values)),
        "break_dispersion": bool(metrics["break_by_8_iqr"] > 0.10),
        "viable": bool(np.mean([t["survival_8"] for t in table_stats]) >= 0.5),
        "turnover_reasonable": bool(
            0.2 <= np.mean([t["turnover"] for t in table_stats]) <= 10.0
        ),
    }
    metrics["criteria"]["pass"] = all(metrics["criteria"].values())
    return metrics


def run_screen(
    config: XenoConfig,
    *,
    n_tables: int = 2,
    n_seeds: int = 4,
    futures: int = 64,
) -> dict:
    config.validate()
    started = time.time()
    grid = []
    if config.mode == "tiny":
        variations = [dict()]
    else:
        # Round 3 grid. Round 1 (weak boosts): single-basin, no strict
        # events. Round 2 (gamma to 1000 + self-loops): first strict events
        # but fidelity overshot — breaks nearly vanished because ~100-molecule
        # compartments split too smoothly. GARD's break regime comes from
        # small-assembly division noise (n_max = 8 molecules), so round 3
        # shrinks the compartment at the strong-catalysis operating point.
        variations = [
            {"gamma": 1000.0, "k_lig0": 3.0e-2, "p_self": 0.3, "mass_max": 60, "mass_dead": 6},
            {"gamma": 1000.0, "k_lig0": 3.0e-2, "p_self": 0.3, "mass_max": 96, "mass_dead": 6},
            {"gamma": 1000.0, "k_lig0": 3.0e-2, "p_self": 0.3, "mass_max": 144, "mass_dead": 8},
            {"gamma": 300.0, "k_lig0": 3.0e-2, "p_self": 0.3, "mass_max": 60, "mass_dead": 6},
            {"gamma": 300.0, "k_lig0": 3.0e-2, "p_self": 0.3, "mass_max": 96, "mass_dead": 6},
            {"gamma": 1000.0, "k_lig0": 3.0e-2, "p_self": 0.3, "mass_max": 60, "mass_dead": 6, "dilution": 0.01},
            {"gamma": 1000.0, "k_lig0": 3.0e-2, "p_self": 0.3, "mass_max": 96, "mass_dead": 6, "dilution": 0.01},
            {"gamma": 1000.0, "k_lig0": 3.0e-2, "p_self": 0.5, "mass_max": 60, "mass_dead": 6},
        ]
    for overrides in variations:
        point_config = replace(config, **overrides)
        entry = {
            "overrides": overrides,
            "metrics": _point_metrics(point_config, n_tables, n_seeds, futures),
        }
        grid.append(entry)

    passing = [g for g in grid if g["metrics"]["criteria"]["pass"]]
    payload = {
        "config": config.as_dict(),
        "config_digest": config.digest(),
        "n_tables": n_tables,
        "n_seeds": n_seeds,
        "futures": futures,
        "grid": grid,
        "n_passing": len(passing),
        "best": passing[0]["overrides"] if passing else None,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(config)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "screen.json", payload)
    return payload
