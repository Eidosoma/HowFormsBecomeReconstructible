"""Trajectory-recording lineage runner over the frozen voltage_web engine.

Control and zapped runs share the SAME rng stream: the clamp replaces
values without consuming draws, so all differences are causal."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from contract_bridge.artifacts import seed_rng
from voltage_web.config import VoltageConfig
from voltage_web.engine import fission, launch_pattern, make_thresholds, run_generation

from .config import RewriteConfig


def tissue_config(index: int, coupling: float, config: RewriteConfig) -> VoltageConfig:
    """Per-tissue jitter of (well asymmetry, spread) + its own theta draw."""
    base = VoltageConfig.tiny() if config.mode == "tiny" else VoltageConfig()
    rng = seed_rng(config.tissue_param_tag, index)
    return replace(
        base,
        tissue_index=index,
        coupling=coupling,
        well_asym=float(rng.uniform(-0.05, 0.05)),
        threshold_spread=float(rng.uniform(0.15, 0.30)),
    )


def posterior_mask(voltage: VoltageConfig) -> np.ndarray:
    mask = np.zeros((voltage.height, voltage.width), dtype=bool)
    mask[:, -max(voltage.width // 4, 1):] = True
    return mask


def run_trajectory(
    tissue: VoltageConfig, config: RewriteConfig, rng: np.random.Generator,
    *, zap: bool, lesion_mask: np.ndarray | None = None,
) -> dict:
    """Seed-0 (one-head) lineage; returns per-generation censuses.

    Output: censuses (G, B, 15), alive (G, B) — census rows are zero for
    futures dead (or undivided) at that generation."""
    n = config.futures
    theta = make_thresholds(tissue)
    V = np.tile(launch_pattern(0, tissue), (n, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    zmask = posterior_mask(tissue)
    alive = np.ones(n, dtype=bool)
    censuses = np.zeros((config.horizon, n, 15))
    alive_log = np.zeros((config.horizon, n), dtype=bool)
    for generation in range(config.horizon):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        if lesion_mask is not None and generation == config.lesion_generation:
            V[np.ix_(idx)] = np.where(
                lesion_mask[None, :, :], tissue.resting, V[idx]
            )
        clamp, sweeps = (zmask, config.zap_sweeps) if (
            zap and generation == config.zap_generation
        ) else (None, 0)
        spectra, _sw, divided, V_final = run_generation(
            V[idx], theta, tissue, rng, clamp, sweeps
        )
        died = idx[~divided]
        alive[died] = False
        live = idx[divided]
        if live.size == 0:
            continue
        censuses[generation, live] = spectra[divided]
        alive_log[generation, live] = True
        V[live] = fission(V_final[divided], tissue, rng)
    return {"censuses": censuses, "alive": alive_log}


def _cos(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    d = np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1)
    return np.where(d > 0, (u * v).sum(axis=-1) / np.maximum(d, 1e-300), 0.0)


def detect_rewrites(traj: dict, config: RewriteConfig) -> dict:
    """Per future: an ABRUPT, held switch — the generation before the run
    is still wild-like (cos > distinct), then `run_length` consecutive live
    generations, pairwise-coherent, ALL distinct from the wild census.

    Dev round 1 (recorded): without the abruptness requirement, slow
    census drift at sigma = 0.3 scores as "rewrite" in ~39%% of CONTROL
    futures — drift is not a switch. Causal attribution is paired: control
    and zapped runs share streams, so the zap effect is the excess of
    switched-when-zapped over switched-when-not."""
    censuses, alive = traj["censuses"], traj["alive"]
    horizon, n, _ = censuses.shape
    w0, w1 = config.wild_window
    wild_alive = alive[w0] & alive[w1]
    wild = censuses[w0:w1 + 1].mean(axis=0)
    first_rewrite = np.full(n, -1, dtype=np.int16)
    last_start = min(config.lesion_generation, horizon) - config.run_length
    for start in range(config.zap_generation + 1, max(last_start + 1, 0)):
        window = censuses[start:start + config.run_length]
        live = alive[start:start + config.run_length].all(axis=0) & wild_alive
        if not live.any():
            continue
        ok = live.copy()
        ok &= alive[start - 1] & (_cos(censuses[start - 1], wild) > config.distinct)
        for a in range(config.run_length):
            ok &= _cos(window[a], wild) <= config.distinct
            for b in range(a + 1, config.run_length):
                ok &= _cos(window[a], window[b]) > config.coherence
        fresh = ok & (first_rewrite < 0)
        first_rewrite[fresh] = start
    return {
        "rewritten": first_rewrite >= 0,
        "first_rewrite": first_rewrite,
        "wild": wild,
        "wild_alive": wild_alive,
    }


def score_recovery(traj: dict, config: RewriteConfig, rewrites: dict) -> dict:
    """Lesion recovery, each lineage to its OWN pre-lesion pattern."""
    censuses, alive = traj["censuses"], traj["alive"]
    m = config.lesion_generation
    pre = censuses[m - 3:m].mean(axis=0)
    pre_alive = alive[m - 3:m].all(axis=0)
    horizon = censuses.shape[0]
    recovered = np.zeros(censuses.shape[1], dtype=bool)
    for t in range(m, min(m + 4, horizon)):
        recovered |= (_cos(censuses[t], pre) > config.inherit) & alive[t] & pre_alive
    # Specificity for rewritten lineages: recovery must NOT be a relapse
    # to wild type.
    wild = rewrites["wild"]
    still_distinct = np.zeros_like(recovered)
    for t in range(m, min(m + 4, horizon)):
        still_distinct |= (_cos(censuses[t], wild) <= config.distinct) & alive[t]
    return {"recovered": recovered, "still_distinct": still_distinct, "pre_alive": pre_alive}
