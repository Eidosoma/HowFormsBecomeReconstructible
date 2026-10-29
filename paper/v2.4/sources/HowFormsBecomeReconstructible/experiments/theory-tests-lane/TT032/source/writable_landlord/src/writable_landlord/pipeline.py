"""E66: the writable landlord. The cascade V -> R -> theta (per-future
theta, norm-projected each sweep, inherited whole at fission — the
DECLARED hypothesized channel). Arms: writable {rho/2, rho/10} /
frozen / GAIN-MATCHED (review #3, the load-bearing control). Probes:
per-group consensus correlation, the three-way swap with the decisive
CROSS-LINEAGE transplant (futures 0-2 imprint target A, 3-5 target B),
freedom cost, end-of-run knife pair, quantitative repertoire audit,
and the imprint's single confirmatory shot."""

from __future__ import annotations

import json
import time

import numpy as np

from blueprint_web.config import BlueprintConfig
from blueprint_web.engine import blueprint_step
from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from ladder_web.config import LadderConfig
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import posterior_mask, tissue_config
from voltage_web.engine import launch_pattern, make_thresholds

from .config import (CAPACITY_NORMS, GAIN_GRID, LAMBDA_FRACS,
                     LandlordConfig, results_root)

RHO = BlueprintConfig().rho          # 0.002 frozen
CM = BlueprintConfig().c_m           # 0.2 frozen


def project_theta(theta: np.ndarray, norm: float) -> np.ndarray:
    t = theta - theta.mean(axis=(-2, -1), keepdims=True)
    s = t.std(axis=(-2, -1), keepdims=True)
    return t * (norm / np.maximum(s, 1e-9))


def cascade_step(V, ema, Rf, theta, tissue, ladder, bp, rng, lam, norm,
                 c_m=None, clamp=None):
    """One sweep of the full cascade; lam = 0 freezes theta."""
    V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder, bp,
                                "T", rng, c_m=c_m, clamp=clamp)
    if lam > 0:
        theta = project_theta((1.0 - lam) * theta + lam * np.tanh(Rf),
                              norm)
    return V, ema, Rf, theta


def capacity_gate(config: LandlordConfig) -> dict:
    """Step 0 (review #6): does a fully ALIGNED theta at each norm pin
    an instance at all? Static, cheap, runs first."""
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    ladder = LadderConfig()
    bp = BlueprintConfig()
    target = launch_pattern(1, tissue)
    rows = []
    chosen = None
    for norm in CAPACITY_NORMS:
        theta = project_theta(np.tanh(1.5 * target)[None], norm)
        rng = seed_rng(config.trajectory_seed_tag, "capacity", norm)
        V = 0.2 * rng.standard_normal((4, tissue.height, tissue.width))
        ema, Rf = V.copy(), V.copy()
        for _ in range(config.capacity_settle):
            V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder,
                                        bp, "T", rng, c_m=0.0)
        pin = float(((V > 0) == (target > 0)[None]).mean())
        rows.append({"norm": norm, "pin": pin})
        if chosen is None and pin >= config.capacity_bar:
            chosen = norm
    return {"rows": rows, "chosen": chosen}


def _measure_pullback(config, tissue, ladder, bp, theta0, lam, norm,
                      c_m, tag) -> float:
    """Recovery slope after a standardized posterior-quarter flip."""
    rng = seed_rng(config.trajectory_seed_tag, "pull", tag)
    B = 4
    V = np.tile(launch_pattern(0, tissue), (B, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema, Rf = V.copy(), V.copy()
    theta = np.tile(theta0, (B, 1, 1)) if theta0.ndim == 2 else theta0
    for _ in range(config.settle_sweeps):
        V, ema, Rf, theta = cascade_step(V, ema, Rf, theta, tissue,
                                         ladder, bp, rng, lam, norm,
                                         c_m=c_m)
    pre = V.copy()
    zone = posterior_mask(tissue)
    V = np.where(zone[None], -V, V)
    ema = V.copy()
    agree0 = float(((V > 0) == (pre > 0))[:, zone].mean())
    for _ in range(config.pullback_window):
        V, ema, Rf, theta = cascade_step(V, ema, Rf, theta, tissue,
                                         ladder, bp, rng, lam, norm,
                                         c_m=c_m)
    agree1 = float(((V > 0) == (pre > 0))[:, zone].mean())
    return (agree1 - agree0) / config.pullback_window


def gain_match(config: LandlordConfig, norm: float) -> dict:
    """Review #3: find the frozen-theta c_m whose measured pull-back
    matches the writable arm's."""
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    ladder = LadderConfig()
    bp = BlueprintConfig()
    native = make_thresholds(tissue)
    lam = LAMBDA_FRACS[0] * RHO
    target_rate = _measure_pullback(config, tissue, ladder, bp, native,
                                    lam, norm, None, "writable")
    rows = []
    for cm in GAIN_GRID:
        rate = _measure_pullback(config, tissue, ladder, bp, native, 0.0,
                                 norm, cm, f"cm{cm}")
        rows.append({"c_m": cm, "rate": rate})
    best = min(rows, key=lambda r: abs(r["rate"] - target_rate))
    return {"writable_rate": target_rate, "rows": rows,
            "matched_cm": best["c_m"]}


def landlord_lineage(config: LandlordConfig, index: int, arm: str,
                     norm: float, matched_cm: float,
                     pattern_override=None, cycles=None) -> dict:
    """One lineage batch: futures 0-2 imprint target A, 3-5 target B
    (or all futures the override pattern). Arms: writable_fast /
    writable_slow / frozen / gain_matched."""
    from assimilation.pipeline import fission_with_mask
    rc = RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    ladder = LadderConfig()
    bp = BlueprintConfig()
    native = make_thresholds(tissue)
    lam = {"writable_fast": LAMBDA_FRACS[0] * RHO,
           "writable_slow": LAMBDA_FRACS[1] * RHO,
           "frozen": 0.0, "gain_matched": 0.0}[arm]
    c_m = matched_cm if arm == "gain_matched" else None
    rng = seed_rng(config.trajectory_seed_tag, "lineage", arm, index,
                   int(pattern_override is not None))
    B = config.futures
    if pattern_override is not None:
        targets = np.tile(pattern_override, (B, 1, 1))
    else:
        tA = launch_pattern(1, tissue)
        tB = launch_pattern(3, tissue)
        targets = np.stack([tA] * (B // 2) + [tB] * (B - B // 2))
    theta = np.tile(native, (B, 1, 1))
    if lam > 0:
        theta = project_theta(theta, norm)
    V = np.tile(launch_pattern(0, tissue), (B, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema, Rf = V.copy(), V.copy()
    for _ in range(config.settle_sweeps):
        V, ema, Rf, theta = cascade_step(V, ema, Rf, theta, tissue,
                                         ladder, bp, rng, lam, norm,
                                         c_m=c_m)
    hold = targets * config.imprint_hold
    for _ in range(config.imprint_sweeps):
        V = np.where(np.abs(hold) > 0, hold, V)
        V, ema, Rf, theta = cascade_step(V, ema, Rf, theta, tissue,
                                         ladder, bp, rng, lam, norm,
                                         c_m=c_m)
    regrow_count = np.zeros(V.shape, dtype=np.int32)
    fid_tail = []
    n_cycles = cycles or config.cycles
    for cycle in range(n_cycles):
        V, Rf, fresh = fission_with_mask(V, Rf, tissue, rng)
        regrow_count += fresh
        ema = V.copy()
        for _ in range(config.inter_fission):
            V, ema, Rf, theta = cascade_step(V, ema, Rf, theta, tissue,
                                             ladder, bp, rng, lam, norm,
                                             c_m=c_m)
        if cycle >= n_cycles - 3:
            ok = ((V > 0) == (targets > 0)) \
                & (np.abs(V) > config.amp_threshold)
            m2 = regrow_count >= 2
            vals = [ok[b][m2[b]].mean() for b in range(B) if m2[b].any()]
            if vals:
                fid_tail.append(float(np.mean(vals)))
    # Freedom cost: post-lineage zap plasticity (survivor change).
    zone = posterior_mask(tissue)
    pre = V > 0
    zrng = seed_rng(config.trajectory_seed_tag, "freedom", arm, index)
    Vz, emaz, Rz, thz = V.copy(), ema.copy(), Rf.copy(), theta.copy()
    for sweep in range(config.zap_recover):
        clamp = zone if sweep < 8 else None
        Vz, emaz, Rz, thz = cascade_step(Vz, emaz, Rz, thz, tissue,
                                         ladder, bp, zrng, lam, norm,
                                         c_m=c_m, clamp=clamp)
    alive = np.abs(Vz).mean(axis=(-2, -1)) > 0.2
    freedom = float((1.0 - ((Vz > 0) == pre).mean(axis=(-2, -1)))[alive]
                    .mean()) if alive.any() else 0.0
    return {"tissue": index, "arm": arm,
            "fidelity": float(np.mean(fid_tail)) if fid_tail else None,
            "freedom": freedom,
            "theta_final": theta, "targets": targets, "tissue_obj": tissue}


def transplant_probe(config, run, norm) -> dict:
    """(c) of the three-way swap: a fresh organism under future-0's
    written theta should express target A over target B (and future
    -1's theta the reverse)."""
    tissue = run["tissue_obj"]
    ladder = LadderConfig()
    bp = BlueprintConfig()
    theta = run["theta_final"]
    targets = run["targets"]
    out = {}
    for b, label in ((0, "groupA"), (config.futures - 1, "groupB")):
        rng = seed_rng(config.trajectory_seed_tag, "transplant",
                       run["arm"], run["tissue"], b)
        V = 0.2 * rng.standard_normal((2, tissue.height, tissue.width))
        ema, Rf = V.copy(), V.copy()
        th = np.tile(theta[b], (2, 1, 1))
        for _ in range(config.consensus_settle):
            V, ema, Rf = blueprint_step(V, ema, Rf, th, tissue, ladder,
                                        bp, "T", rng, c_m=0.0)
        mA = float(((V > 0) == (targets[0] > 0)[None]).mean())
        mB = float(((V > 0) == (targets[-1] > 0)[None]).mean())
        out[label] = {"match_A": mA, "match_B": mB}
    own = (out["groupA"]["match_A"] - out["groupA"]["match_B"]
           + out["groupB"]["match_B"] - out["groupB"]["match_A"]) / 2
    out["own_target_margin"] = float(own)
    return out


def repertoire_audit(config, run) -> dict:
    """Distinct settled classes under written vs native theta."""
    tissue = run["tissue_obj"]
    ladder = LadderConfig()
    bp = BlueprintConfig()
    native = make_thresholds(tissue)

    def classes(theta2d, tag):
        finals = []
        for s in range(config.repertoire_seeds):
            rng = seed_rng(config.trajectory_seed_tag, "audit", tag, s)
            V = np.tile(launch_pattern(s % 12, tissue), (2, 1, 1))
            V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
            ema, Rf = V.copy(), V.copy()
            th = np.tile(theta2d, (2, 1, 1))
            for _ in range(config.consensus_settle):
                V, ema, Rf = blueprint_step(V, ema, Rf, th, tissue,
                                            ladder, bp, "T", rng, c_m=0.0)
            finals.append(np.sign(V[0]))
        reps = []
        for f in finals:
            if not any(float((f == r).mean()) > config.repertoire_distinct
                       for r in reps):
                reps.append(f)
        return len(reps)

    n_native = classes(native, "native")
    n_written = classes(run["theta_final"][0], f"written-{run['arm']}")
    return {"native_classes": n_native, "written_classes": n_written,
            "collapsed": bool(n_written <= 0.5 * n_native)}


def run_gates(config: LandlordConfig) -> dict:
    started = time.time()
    work = results_root(config) / "work"
    work.mkdir(parents=True, exist_ok=True)
    cap = capacity_gate(config)
    if cap["chosen"] is None:
        payload = {"config_digest": config.digest(), "capacity": cap,
                   "verdict": "VOID — no norm pins an aligned instance",
                   "elapsed_seconds": time.time() - started}
        atomic_json(results_root(config) / "landlord_summary.json", payload)
        return payload
    norm = cap["chosen"]
    gm = gain_match(config, norm)
    arms = ("writable_fast", "writable_slow", "frozen", "gain_matched")
    rows = {arm: [] for arm in arms}
    probes = {}
    for arm in arms:
        for i in range(config.n_tissues):
            run = landlord_lineage(config, i, arm, norm, gm["matched_cm"])
            rows[arm].append({k: run[k] for k in
                              ("tissue", "fidelity", "freedom")})
            if i == 0:
                probes[arm] = {
                    "transplant": transplant_probe(config, run, norm),
                    "repertoire": repertoire_audit(config, run),
                }
    # The single confirmatory imprint shot (two-headed, writable_fast).
    from two_headed_final.pipeline import two_headed_pattern
    rc = RewriteConfig()
    t0 = tissue_config(0, rc.coupling_band, rc)
    shot = landlord_lineage(config, 0, "writable_fast", norm,
                            gm["matched_cm"],
                            pattern_override=two_headed_pattern(t0),
                            cycles=config.imprint_gate_cycles)

    def fid(arm):
        vals = [r["fidelity"] for r in rows[arm]
                if r["fidelity"] is not None]
        return float(np.mean(vals)) if vals else None

    def freedom(arm):
        return float(np.mean([r["freedom"] for r in rows[arm]]))

    f_w, f_gm = fid("writable_fast"), fid("gain_matched")
    fr_w, fr_gm = freedom("writable_fast"), freedom("gain_matched")
    spread = float(np.std([r["fidelity"] for r in rows["frozen"]
                           if r["fidelity"] is not None]) or 0.02)
    margin = probes["writable_fast"]["transplant"]["own_target_margin"]
    gates = {
        "capacity": cap, "gain_match": gm, "norm": norm,
        "fidelity": {arm: fid(arm) for arm in arms},
        "freedom_cost": {arm: freedom(arm) for arm in arms},
        "transplant": {arm: probes[arm]["transplant"]["own_target_margin"]
                       for arm in arms},
        "repertoire": {arm: probes[arm]["repertoire"] for arm in arms},
        "imprint_shot_fidelity": shot["fidelity"],
        "gate_p66_1_primary": bool(
            f_w is not None and f_gm is not None
            and f_w > f_gm + 1.645 * spread
            and fr_w >= fr_gm - 0.05
            and margin > 0.1),
        "gate_p66_3_imprint": bool(
            shot["fidelity"] is not None
            and shot["fidelity"] >= config.imprint_gate_bar),
        "cm_in_disguise": bool(
            f_w is not None and f_gm is not None
            and f_w > (fid("frozen") or 0) and f_w <= f_gm + 1.645 * spread),
    }
    payload = {
        "config_digest": config.digest(),
        "gates": gates,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(results_root(config) / "landlord_summary.json", payload)
    return payload
