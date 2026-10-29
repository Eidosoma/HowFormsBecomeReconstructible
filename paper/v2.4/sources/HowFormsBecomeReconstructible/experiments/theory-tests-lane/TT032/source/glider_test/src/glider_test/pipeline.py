"""E21 observer campaign: named objects vs density-matched random seeds."""

from __future__ import annotations

import time
from dataclasses import replace

import numpy as np

from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from form_atlas.scale import support_from_occupancy

from .config import LifeConfig, results_root
from .life import BLOCK, NAMED_OBJECTS, paint, run_lineage


def _random_launch(n_cells: int, config: LifeConfig, rng) -> np.ndarray:
    grid = np.zeros(config.height * config.width, dtype=np.uint8)
    grid[rng.choice(grid.size, size=n_cells, replace=False)] = 1
    return grid.reshape(config.height, config.width)


def _lineage_summary(stats, mean_h, spectra, config: LifeConfig) -> dict:
    live = spectra[spectra.sum(axis=1) > 0]
    ensemble = live.mean(axis=0) if len(live) else np.zeros(15)
    form = support_from_occupancy(ensemble, config.mass_quantile, 15)
    supports = [
        support_from_occupancy(spectrum, config.mass_quantile, 15)
        for spectrum in spectra
    ]
    masks = [sum(1 << i for i in s) if s else 0 for s in supports]
    values, counts = np.unique(np.asarray(masks), return_counts=True)
    modal = int(values[counts.argmax()])
    return {
        "form_support": sum(1 << i for i in form) if form else 0,
        "ensemble_spectrum": ensemble.tolist(),
        "strict": stats.strict_probability,
        "mean_h": float(np.nanmean(mean_h)),
        "break_by_8": float(((stats.first_break >= 0) & (stats.first_break < 8)).mean()),
        "survival_8": float((stats.survival_generation >= 8).mean()),
        "modal_support": modal,
        "modal_support_fraction": float(counts.max() / len(masks)),
    }


def run_observer(config: LifeConfig, *, screen_overrides: dict | None = None) -> dict:
    started = time.time()
    point = replace(config, **(screen_overrides or {}))
    named = {}
    for name, cells in NAMED_OBJECTS.items():
        launch = paint(cells, point.height, point.width)
        stats, mean_h, spectra = run_lineage(
            launch, point, seed_rng(point.trajectory_seed_tag, name), point.n_futures
        )
        named[name] = _lineage_summary(stats, mean_h, spectra, point)
        named[name]["n_cells"] = int(launch.sum())

    matched = {}
    for name, cells in NAMED_OBJECTS.items():
        rows = []
        for k in range(point.n_random_seeds):
            rng = seed_rng(point.trajectory_seed_tag + "-random", name, k)
            launch = _random_launch(len(cells), point, rng)
            stats, mean_h, spectra = run_lineage(
                launch, point, rng, max(point.n_futures // 4, 8)
            )
            rows.append(_lineage_summary(stats, mean_h, spectra, point))
        h_rows = np.asarray([r["mean_h"] for r in rows], dtype=float)
        alive_rows = h_rows[~np.isnan(h_rows)]
        matched[name] = {
            "mean_h": float(alive_rows.mean()) if alive_rows.size else 0.0,
            "mean_h_q95": float(np.quantile(alive_rows, 0.95)) if alive_rows.size else 0.0,
            "died_before_two_divisions_fraction": float(np.isnan(h_rows).mean()),
            "survival_8": float(np.mean([r["survival_8"] for r in rows])),
            "modal_support_fraction": float(
                np.mean([r["modal_support_fraction"] for r in rows])
            ),
            "supports_distinct_from_named": float(
                np.mean([r["modal_support"] != named[name]["modal_support"] for r in rows])
            ),
        }

    block_stats, block_h, block_spectra = run_lineage(
        paint(BLOCK, point.height, point.width), point,
        seed_rng(point.trajectory_seed_tag, "block"), point.n_futures,
    )
    block_row = _lineage_summary(block_stats, block_h, block_spectra, point)

    named_masks = [named[n]["form_support"] for n in NAMED_OBJECTS]
    # Separability: within-object cosine (future-to-future) must exceed
    # between-object cosine for every pair (the frozen atlas form definition:
    # ensemble-mean support; per-future modal masks kept as diagnostics).
    vectors = {
        n: np.asarray(named[n]["ensemble_spectrum"]) for n in NAMED_OBJECTS
    }

    def _cos(u, v):
        d = np.linalg.norm(u) * np.linalg.norm(v)
        return float(u @ v / d) if d > 0 else 0.0

    names = list(NAMED_OBJECTS)
    between = {
        f"{a}|{b}": _cos(vectors[a], vectors[b])
        for i, a in enumerate(names) for b in names[i + 1:]
    }
    gates = {
        "gate_distinct_forms": bool(
            len(set(named_masks)) == len(named_masks)
            and all(v < 0.999 for v in between.values())
        ),
        "between_object_cosines": between,
        "gate_fidelity_absolute": bool(
            all(named[n]["mean_h"] >= 0.9 for n in NAMED_OBJECTS)
        ),
        "gate_persistence": bool(
            all(
                named[n]["survival_8"] > matched[n]["survival_8"] + 0.3
                for n in NAMED_OBJECTS
            )
        ),
        "random_survivor_note": "random seeds that persist do so by becoming ash "
        "(blocks/blinkers) — their fidelity is reported, not gated",
    }
    named = dict(named)
    named["block_descriptive"] = block_row
    payload = {
        "config_digest": point.digest(),
        "overrides": screen_overrides or {},
        "named": named,
        "density_matched_random": matched,
        "gates": gates,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(config)
    out.mkdir(parents=True, exist_ok=True)
    name = "observer.json" if not screen_overrides else "screen_point.json"
    atomic_json(out / name, payload)
    return payload
