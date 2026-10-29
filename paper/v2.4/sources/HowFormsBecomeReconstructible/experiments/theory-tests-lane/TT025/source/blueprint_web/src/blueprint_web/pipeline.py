"""E48: the freedom-calibration square and the substrate gates."""

from __future__ import annotations

from dataclasses import replace
import json
import time

import numpy as np

from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from glider_test.life import block_counts
from ladder_web.config import LadderConfig
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import detect_rewrites, posterior_mask, tissue_config
from voltage_web.engine import launch_pattern, make_thresholds

from .config import BlueprintConfig, results_root
from .engine import blueprint_fission, blueprint_step, settle_with_blueprint


def _cos(u, v):
    d = np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1)
    return np.where(d > 0, (u * v).sum(axis=-1) / np.maximum(d, 1e-300), 0.0)


def run_lineage_bp(tissue, bp: BlueprintConfig, rung: str, rng, mrng, *,
                   horizon, n_futures, seed_index=0, c_m=None,
                   zap=None):
    """Lineage with blueprint threading; zap = {generation, mask, sweeps}."""
    ladder = LadderConfig()
    theta = make_thresholds(tissue)
    V = np.tile(launch_pattern(seed_index, tissue), (n_futures, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema = V.copy()
    Rf = V.copy() if rung != "A" else None
    censuses = np.zeros((horizon, n_futures, 15))
    alive_log = np.zeros((horizon, n_futures), dtype=bool)
    alive = np.ones(n_futures, dtype=bool)
    for generation in range(horizon):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        Vg, emag = V.copy(), ema.copy()
        binary = (Vg > 0).astype(np.uint8)
        activity = np.zeros(n_futures, dtype=np.int64)
        sweeps = np.zeros(n_futures, dtype=np.int64)
        active = alive.copy()
        divided = np.zeros(n_futures, dtype=bool)
        census_acc = np.zeros((n_futures, 15))
        zap_now = zap is not None and generation == zap["generation"]
        for sweep in range(tissue.t_max_sweeps):
            if not active.any():
                break
            sub = np.flatnonzero(active)
            clamp = zap["mask"] if (zap_now and sweep < zap["sweeps"]) else None
            Vg_s, ema_s, Rf_s = blueprint_step(
                Vg[sub], emag[sub], (Rf[sub] if Rf is not None else None),
                theta, tissue, LadderConfig(), bp, rung, rng, mrng,
                clamp=clamp, c_m=c_m,
            )
            Vg[sub], emag[sub] = Vg_s, ema_s
            if Rf is not None:
                Rf[sub] = Rf_s
            updated = (Vg[sub] > 0).astype(np.uint8)
            activity[sub] += (updated != binary[sub]).sum(axis=(-2, -1))
            binary[sub] = updated
            census_acc[sub] += block_counts(updated)
            sweeps[sub] += 1
            done = (activity[sub] >= tissue.activity_budget) & (sweeps[sub] >= tissue.t_min_sweeps)
            divided[sub[done]] = True
            active[sub[done]] = False
        spectrum = census_acc / np.maximum(census_acc.sum(axis=1, keepdims=True), 1.0)
        total = binary.sum(axis=(-2, -1))
        divided = divided & (total > 0) & (total < tissue.cells)
        alive = alive & divided
        live = np.flatnonzero(alive)
        if live.size == 0:
            continue
        censuses[generation, live] = spectrum[live]
        alive_log[generation, live] = True
        kids, R_kid = blueprint_fission(Vg[live], (Rf[live] if Rf is not None else None),
                                        tissue, rng)
        V = Vg
        V[live] = kids
        ema[live] = V[live]
        if Rf is not None and R_kid is not None:
            Rf[live] = R_kid
    return {"censuses": censuses, "alive": alive_log}


def freedom_point(bp: BlueprintConfig, rung: str, tag: str) -> dict:
    """Heredity screen + zap-conversion at one (rho, c_m) point."""
    rc = RewriteConfig()
    h_all, survivals = [], []
    conversions = []
    for index in range(4):
        tissue = tissue_config(index, rc.coupling_band, rc)
        out = run_lineage_bp(
            tissue, bp, rung,
            seed_rng(tag + "-screen", rung, index),
            seed_rng(tag + "-m", rung, index),
            horizon=12, n_futures=32,
        )
        censuses, alive = out["censuses"], out["alive"]
        for t in range(2, 12):
            both = alive[t] & alive[t - 1]
            if both.sum() >= 4:
                h_all.append(_cos(censuses[t - 1][both], censuses[t][both]))
        survivals.append(float(alive[8].mean()))
        # Freedom: paired zap conversion (E27 protocol, shared streams).
        zmask = posterior_mask(tissue)
        rcz = replace(rc, futures=32, horizon=14, zap_generation=3,
                      lesion_generation=14)
        arms = {}
        for zap_on in (True, False):
            traj = run_lineage_bp(
                tissue, bp, rung,
                seed_rng(tag + "-zap", rung, index),
                seed_rng(tag + "-zap-m", rung, index),
                horizon=14, n_futures=32,
                zap=({"generation": 3, "mask": zmask, "sweeps": 8} if zap_on else None),
            )
            arms[zap_on] = detect_rewrites(traj, rcz)
        both = arms[True]["wild_alive"] & arms[False]["wild_alive"]
        z = arms[True]["rewritten"] & ~arms[False]["rewritten"]
        conversions.append(float(z[both].mean()) if both.any() else 0.0)
    h = np.concatenate(h_all) if h_all else np.zeros(0)
    return {
        "h_above": float((h > 0.9).mean()) if h.size else 0.0,
        "h_below": float((h < 0.85).mean()) if h.size else 0.0,
        "survival_8": float(np.median(survivals)),
        "conversion": float(np.mean(conversions)),
        "screen_pass": bool(
            h.size and (h > 0.9).mean() >= 0.3 and (h < 0.85).mean() >= 0.02
            and np.median(survivals) >= 0.3
        ),
        "freedom_pass": bool(np.mean(conversions) >= 0.10),
    }


def run_calibration(bp_base: BlueprintConfig) -> dict:
    started = time.time()
    square = {}
    for rho in (0.002, 0.01, 0.05):
        for c_m in (0.2, 0.4, 0.8):
            bp = replace(bp_base, rho=rho, c_m=c_m,
                         trajectory_seed_tag=f"bp-calib-{rho}-{c_m}")
            square[f"{rho}|{c_m}"] = freedom_point(bp, "T", bp.trajectory_seed_tag)
    passing = {k: v for k, v in square.items()
               if v["screen_pass"] and v["freedom_pass"]}
    best = max(passing, key=lambda k: float(k.split("|")[1])) if passing else None
    payload = {
        "config_digest": bp_base.digest(),
        "square": square,
        "passing": sorted(passing),
        "chosen": best,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(bp_base)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "calibration_square.json", payload)
    return payload
