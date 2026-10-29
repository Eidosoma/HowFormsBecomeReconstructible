"""E68: the error threshold at the cascade's base, redesigned per
review #6. Sweep coordinate = realized parent-daughter theta
correlation; writing ON throughout (the restoring loop IS the
selection-analog); PRIMARY = the zero crossing c* of the per-cycle
fidelity trend, against its prediction from the measured one-cycle
restoration curve; an unbounded (no-projection) arm shows the cap
does not set c*."""

from __future__ import annotations

import json
import time

import numpy as np

from blueprint_web.config import BlueprintConfig
from blueprint_web.engine import blueprint_step
from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from ladder_web.config import LadderConfig
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import tissue_config
from voltage_web.engine import launch_pattern, make_thresholds
from writable_landlord.pipeline import project_theta
from assimilation.pipeline import fission_with_mask

from .config import CORR_GRID, DeepEigenConfig, PREROUND_CORRS, results_root


def _corr(a, b) -> float:
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def mix_theta(theta, c_target, rng, norm, project=True):
    """theta' = c*theta_hat + sqrt(1-c^2)*noise_hat, rescaled.
    Realized correlation ~ c_target in expectation; measured and
    returned. project=False is the unbounded arm."""
    out = np.empty_like(theta)
    realized = []
    for b in range(theta.shape[0]):
        t = theta[b] - theta[b].mean()
        t_hat = t / max(np.linalg.norm(t), 1e-12)
        n = rng.standard_normal(t.shape)
        n = n - n.mean()
        n -= (n * t_hat).sum() * t_hat
        n_hat = n / max(np.linalg.norm(n), 1e-12)
        mixed = c_target * t_hat + np.sqrt(max(0.0, 1 - c_target ** 2)) * n_hat
        mixed = mixed * np.linalg.norm(t)
        out[b] = mixed
        realized.append(_corr(mixed, theta[b]))
    if project:
        out = project_theta(out, norm)
    return out, float(np.mean(realized))


def cascade_sweep(V, ema, Rf, theta, tissue, ladder, bp, rng, lam, norm):
    V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder, bp,
                                "T", rng)
    theta = project_theta((1 - lam) * theta + lam * np.tanh(Rf), norm)
    return V, ema, Rf, theta


def prepare_organism(config, index, rng):
    rc = RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    ladder = LadderConfig()
    bp = BlueprintConfig()
    native = make_thresholds(tissue)
    B = config.futures
    theta = project_theta(np.tile(native, (B, 1, 1)), config.norm)
    form = launch_pattern(1, tissue)
    V = np.tile(launch_pattern(0, tissue), (B, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema, Rf = V.copy(), V.copy()
    for _ in range(config.settle_sweeps):
        V, ema, Rf, theta = cascade_sweep(V, ema, Rf, theta, tissue,
                                          ladder, bp, rng,
                                          config.write_lambda, config.norm)
    hold = form * config.imprint_hold
    for _ in range(config.imprint_sweeps):
        V = np.where(np.abs(hold)[None] > 0, hold[None], V)
        V, ema, Rf, theta = cascade_sweep(V, ema, Rf, theta, tissue,
                                          ladder, bp, rng,
                                          config.write_lambda, config.norm)
    return tissue, ladder, bp, V, ema, Rf, theta, form


def restoration_preround(config: DeepEigenConfig) -> dict:
    """One-cycle fidelity delta at hand-set perturbation correlations
    -> the PREDICTED c* (interpolated zero crossing)."""
    rows = []
    for c in PREROUND_CORRS:
        deltas, theta_recoveries = [], []
        for i in range(config.n_tissues):
            rng = seed_rng(config.trajectory_seed_tag, "pre", c, i)
            tissue, ladder, bp, V, ema, Rf, theta, form = \
                prepare_organism(config, i, rng)
            fid0 = float((((V > 0) == (form > 0)[None])
                          & (np.abs(V) > config.amp_threshold)).mean())
            theta_p, realized = mix_theta(theta, c, rng, config.norm)
            c_before = float(np.mean([_corr(theta_p[b], theta[b])
                                      for b in range(theta.shape[0])]))
            th = theta_p
            for _ in range(config.inter_fission):
                V, ema, Rf, th = cascade_sweep(V, ema, Rf, th, tissue,
                                               ladder, bp, rng,
                                               config.write_lambda,
                                               config.norm)
            fid1 = float((((V > 0) == (form > 0)[None])
                          & (np.abs(V) > config.amp_threshold)).mean())
            c_after = float(np.mean([_corr(th[b], theta[b])
                                     for b in range(theta.shape[0])]))
            deltas.append(fid1 - fid0)
            theta_recoveries.append(c_after - c_before)
        rows.append({"c": c, "fidelity_delta": float(np.mean(deltas)),
                     "theta_recovery": float(np.mean(theta_recoveries))})
    # Predicted c*: zero crossing of fidelity_delta vs c.
    cs = np.array([r["c"] for r in rows])
    ds = np.array([r["fidelity_delta"] for r in rows])
    order = np.argsort(cs)
    cs, ds = cs[order], ds[order]
    pred = None
    for a in range(len(cs) - 1):
        if ds[a] < 0 <= ds[a + 1] or ds[a] <= 0 < ds[a + 1]:
            frac = -ds[a] / (ds[a + 1] - ds[a])
            pred = float(cs[a] + frac * (cs[a + 1] - cs[a]))
            break
    return {"rows": rows, "predicted_c_star": pred}


def lineage_at(config, index, c_target, project) -> dict:
    rng = seed_rng(config.trajectory_seed_tag, "lin", c_target, index,
                   int(project))
    tissue, ladder, bp, V, ema, Rf, theta, form = \
        prepare_organism(config, index, rng)
    regrow = np.zeros(V.shape, dtype=np.int32)
    fids, realized_all = [], []
    for cycle in range(config.cycles):
        V, Rf, fresh = fission_with_mask(V, Rf, tissue, rng)
        regrow += fresh
        ema = V.copy()
        if c_target < 1.0:
            theta, realized = mix_theta(theta, c_target, rng, config.norm,
                                        project=project)
            realized_all.append(realized)
        for _ in range(config.inter_fission):
            V, ema, Rf, theta = cascade_sweep(V, ema, Rf, theta, tissue,
                                              ladder, bp, rng,
                                              config.write_lambda,
                                              config.norm)
        ok = ((V > 0) == (form > 0)[None]) \
            & (np.abs(V) > config.amp_threshold)
        m2 = regrow >= 2
        vals = [ok[b][m2[b]].mean() for b in range(V.shape[0])
                if m2[b].any()]
        fids.append(float(np.mean(vals)) if vals else None)
    return {"tissue": index, "c_target": c_target, "project": project,
            "realized_corr": (float(np.mean(realized_all))
                              if realized_all else 1.0),
            "fidelity_by_cycle": fids}


def _slope(fids, chance):
    ys = [(i, np.log(max(f - chance, 1e-3)))
          for i, f in enumerate(fids[1:], start=1) if f is not None]
    if len(ys) < 4:
        return None
    xs = np.array([x for x, _ in ys])
    ls = np.array([l for _, l in ys])
    return float(np.polyfit(xs, ls, 1)[0])


def run_gates(config: DeepEigenConfig, *, part: str | None = None) -> dict:
    started = time.time()
    work = results_root(config) / "work"
    work.mkdir(parents=True, exist_ok=True)
    pre_cache = work / "preround.json"
    if pre_cache.exists() and json.loads(pre_cache.read_text()).get(
            "config_digest") == config.digest():
        pre = json.loads(pre_cache.read_text())["data"]
    else:
        pre = restoration_preround(config)
        atomic_json(pre_cache, {"config_digest": config.digest(),
                                "data": pre})
    entries = []
    for project in (True, False):
        for c in CORR_GRID:
            cache = work / f"lin_{c}_{int(project)}.json"
            if cache.exists() and json.loads(cache.read_text()).get(
                    "config_digest") == config.digest():
                entries.extend(json.loads(cache.read_text())["data"])
                continue
            rows = [lineage_at(config, i, c, project)
                    for i in range(config.n_tissues)]
            atomic_json(cache, {"config_digest": config.digest(),
                                "data": rows})
            entries.extend(rows)

    def curve(project):
        out = []
        for c in CORR_GRID:
            rows = [e for e in entries if e["c_target"] == c
                    and e["project"] == project]
            fid_mat = [r["fidelity_by_cycle"] for r in rows]
            mean_fids = [float(np.mean([f[i] for f in fid_mat
                                        if f[i] is not None]))
                         for i in range(config.cycles)]
            out.append({"c_target": c,
                        "realized": float(np.mean([r["realized_corr"]
                                                   for r in rows])),
                        "slope": _slope(mean_fids, config.chance),
                        "final_fid": mean_fids[-1]})
        return out

    proj = curve(True)
    unb = curve(False)

    def c_star(rows):
        pts = [(r["realized"], r["slope"]) for r in rows
               if r["slope"] is not None]
        pts.sort()
        for a in range(len(pts) - 1):
            if pts[a][1] < 0 <= pts[a + 1][1]:
                x0, s0 = pts[a]
                x1, s1 = pts[a + 1]
                return float(x0 + (x1 - x0) * (-s0) / (s1 - s0))
        return None

    cs_proj = c_star(proj)
    cs_unb = c_star(unb)
    pred = pre["predicted_c_star"]
    gates = {
        "preround": pre,
        "curve_projected": proj,
        "curve_unbounded": unb,
        "c_star_projected": cs_proj,
        "c_star_unbounded": cs_unb,
        "predicted_c_star": pred,
        "gate_p68_1_primary": bool(
            cs_proj is not None and pred is not None
            and 0.5 * pred <= cs_proj <= 2.0 * pred
            and CORR_GRID[-1] < cs_proj < CORR_GRID[0]),
        "cap_sets_threshold": bool(
            cs_proj is not None and cs_unb is not None
            and abs(cs_proj - cs_unb) > 0.15),
    }
    payload = {
        "config_digest": config.digest(),
        "gates": gates,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(results_root(config) / "deepeigen_summary.json", payload)
    return payload
