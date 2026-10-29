"""The machinery ladder. Mirrors the frozen `voltage_web.engine.sheet_step`
physics (conserved double-well sheet) and ADDS, rung by rung:

  B  anchors    — niche cells clamped to wild-pattern values (a positional
                  reference; conservation is declared bulk-only at rung B+,
                  anchors are open boundaries like organizer cells),
  C  morphogen  — a fast long-range field M = smoothed binarized V feeding
                  back as c_m * (M - sheet mean),
  D  stress     — surprise s = |V - EMA(V)| diffused into S, which raises
                  local coupling (x(1+a_g S)) and local noise (x(1+a_s S)):
                  unhappy tissue is more coupled and more plastic.

Nothing in the frozen capsules is edited."""

from __future__ import annotations

import numpy as np

from contract_bridge.artifacts import seed_rng
from glider_test.life import block_counts
from voltage_web.config import VoltageConfig
from voltage_web.engine import launch_pattern, make_thresholds

from .config import LadderConfig


def _smooth(field: np.ndarray, passes: int) -> np.ndarray:
    for _ in range(passes):
        neighbors = (
            np.roll(field, 1, -2) + np.roll(field, -1, -2)
            + np.roll(field, 1, -1) + np.roll(field, -1, -1)
        ) / 4.0
        field = 0.5 * field + 0.5 * neighbors
    return field


def anchor_layout(tissue: VoltageConfig, config: LadderConfig):
    """Hash-fixed anchor cells + their wild-pattern values (tissue property)."""
    rng = seed_rng(config.anchor_tag, tissue.tissue_index)
    flat = rng.choice(tissue.height * tissue.width, size=config.n_anchors, replace=False)
    rows, cols = np.unravel_index(flat, (tissue.height, tissue.width))
    values = launch_pattern(0, tissue)[rows, cols]
    return rows, cols, values


def expectation_field(tissue: VoltageConfig, config: LadderConfig,
                      anchors) -> np.ndarray:
    """Rung-C round 2 (recorded): the ORGANIZER FIELD. Round 1 sourced the
    morphogen from the sheet's own current state — a broadcast of the
    status quo, which can never be a restoring force (E36 round 1: stress
    ANTI-correlated with positional error at -0.4; surprise is not error).
    Round 2 diffuses the anchors' clamped values into a static positional
    EXPECTATION field E (harmonic-style interpolation), the way organizer
    cells source real morphogen gradients. Rung C compares V to E; rung D
    reads |E - V| as TRUE error."""
    rows, cols, values = anchors
    M = np.zeros((tissue.height, tissue.width))
    for _ in range(40):
        M[rows, cols] = values
        M = (
            np.roll(M, 1, 0) + np.roll(M, -1, 0)
            + np.roll(M, 1, 1) + np.roll(M, -1, 1)
        ) / 4.0 * 0.5 + 0.5 * M
    M[rows, cols] = values
    return M


def ladder_step(V, ema, theta, tissue: VoltageConfig, config: LadderConfig,
                rung: str, rng, anchors=None, clamp=None):
    """One sweep on batched (B, H, W) sheets; returns (V, ema, S)."""
    S = None
    g_local, sigma_local = tissue.coupling, tissue.sigma
    expectation = anchors[3] if (anchors is not None and len(anchors) > 3) else None
    baseline = anchors[4] if (anchors is not None and len(anchors) > 4) else None
    if rung == "D" and expectation is not None:
        s = _smooth(np.abs(expectation[None] - V), config.stress_passes)
        # Round 4 (recorded): |E - V| has a large settled BASELINE (E is a
        # smooth interpolation, V is bimodal), which left stress always-on
        # and shifted the operating point into the over-coupled maintainer
        # regime (rung-D screen H< 0.008). A thermostat needs a calibrated
        # zero: stress = error beyond the settled baseline.
        S = np.clip(s - (baseline[None] if baseline is not None else 0.0), 0.0, None)
        g_local = tissue.coupling * (1.0 + config.alpha_g * S)
        sigma_local = tissue.sigma * (1.0 + config.alpha_sigma * S)
    m_term = 0.0
    if rung in ("C", "D") and expectation is not None:
        m_term = config.morphogen_gain * (expectation[None] - V)
    neighbors = (
        np.roll(V, 1, -2) + np.roll(V, -1, -2) + np.roll(V, 1, -1) + np.roll(V, -1, -1)
    ) / 4.0
    drift = V - V ** 3 + tissue.well_asym + theta + g_local * (neighbors - V) + m_term
    drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
    if np.isscalar(sigma_local):
        noise = sigma_local * rng.standard_normal(V.shape)
    else:
        noise = sigma_local * rng.standard_normal(V.shape)
    noise = noise - noise.mean(axis=(-2, -1), keepdims=True)
    V = np.clip(V + tissue.dt * drift + noise, -2.0, 2.0)
    if rung in ("B", "C", "D") and anchors is not None:
        rows, cols, values = anchors[0], anchors[1], anchors[2]
        V[:, rows, cols] = values[None, :]
    if clamp is not None:
        V = np.where(clamp[None, :, :], 1.5, V)
    ema = (1.0 - config.ema_rate) * ema + config.ema_rate * V
    return V, ema, S


def run_generation_ladder(V, ema, theta, tissue, config, rung, rng,
                          anchors=None, clamp=None, clamp_sweeps=0):
    V = V.copy(); ema = ema.copy()
    batch = V.shape[0]
    binary = (V > 0).astype(np.uint8)
    activity = np.zeros(batch, dtype=np.int64)
    sweeps = np.zeros(batch, dtype=np.int64)
    active = np.ones(batch, dtype=bool)
    divided = np.zeros(batch, dtype=bool)
    census = np.zeros((batch, 15))
    for sweep in range(tissue.t_max_sweeps):
        if not active.any():
            break
        idx = np.flatnonzero(active)
        clamping = clamp if sweep < clamp_sweeps else None
        V[idx], ema[idx], _ = ladder_step(
            V[idx], ema[idx], theta, tissue, config, rung, rng, anchors, clamping
        )
        updated = (V[idx] > 0).astype(np.uint8)
        activity[idx] += (updated != binary[idx]).sum(axis=(-2, -1))
        binary[idx] = updated
        census[idx] += block_counts(updated)
        sweeps[idx] += 1
        done = (activity[idx] >= tissue.activity_budget) & (sweeps[idx] >= tissue.t_min_sweeps)
        divided[idx[done]] = True
        active[idx[done]] = False
    spectrum = census / np.maximum(census.sum(axis=1, keepdims=True), 1.0)
    total = binary.sum(axis=(-2, -1))
    divided = divided & (total > 0) & (total < tissue.cells)
    return spectrum, sweeps, divided, V, ema


def ladder_fission(V, tissue, config, rung, rng, anchors=None):
    from voltage_web.engine import fission

    kids = fission(V, tissue, rng)
    if rung in ("B", "C", "D") and anchors is not None:
        rows, cols, values = anchors[0], anchors[1], anchors[2]
        kids[:, rows, cols] = values[None, :]
    return kids


def tissue_fields(tissue, config: LadderConfig, rung: str):
    """Anchors (+ expectation field on C/D, + stress baseline on D)."""
    if rung == "A":
        return None
    base = anchor_layout(tissue, config)
    if rung == "B":
        return base
    E = expectation_field(tissue, config, base)
    if rung == "C":
        return (base[0], base[1], base[2], E)
    # Rung D: calibrate the stress zero — settle noiselessly under the
    # comparator and record the residual |E - V| field as baseline.
    from dataclasses import replace as _replace

    quiet = _replace(tissue, sigma=0.0, copy_jitter=0.0)
    theta = make_thresholds(quiet)
    V = launch_pattern(0, quiet)[None].copy()
    ema = V.copy()
    rng0 = np.random.default_rng(0)
    fields_c = (base[0], base[1], base[2], E)
    for _ in range(60):
        V, ema, _ = ladder_step(V, ema, theta, quiet, config, "C", rng0, fields_c)
    S0 = _smooth(np.abs(E[None] - V), config.stress_passes)[0]
    return (base[0], base[1], base[2], E, S0)


def run_lineage(tissue, config: LadderConfig, rung: str, rng, *,
                horizon: int, n_futures: int | None = None,
                seed_index: int = 0) -> dict:
    n = config.futures if n_futures is None else n_futures
    theta = make_thresholds(tissue)
    anchors = tissue_fields(tissue, config, rung)
    V = np.tile(launch_pattern(seed_index, tissue), (n, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema = V.copy()
    censuses = np.zeros((horizon, n, 15))
    alive_log = np.zeros((horizon, n), dtype=bool)
    alive = np.ones(n, dtype=bool)
    final_V = V.copy()
    for generation in range(horizon):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        spectra, _sw, divided, V_out, ema_out = run_generation_ladder(
            V[idx], ema[idx], theta, tissue, config, rung, rng, anchors
        )
        died = idx[~divided]
        alive[died] = False
        live = idx[divided]
        if live.size == 0:
            continue
        censuses[generation, live] = spectra[divided]
        alive_log[generation, live] = True
        final_V[live] = V_out[divided]
        V[live] = ladder_fission(V_out[divided], tissue, config, rung, rng, anchors)
        ema[live] = V[live]
    return {"censuses": censuses, "alive": alive_log, "final_V": final_V}
