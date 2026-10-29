"""E55: Eigen's error threshold on the blueprint channel.

The message is imprinted (hold 2/rho so R adopts it), the tissue then
settles into its OWN RENDITION (1/rho) — the fixed ancestral pattern.
Lineages run `cycles` fissions with copy noise R += sigma_R * noise;
fidelity = amplitude-thresholded sign-match of V to the ancestor
rendition on regrown cells (the mid-wave amendment's strict channel =
cells regrown >= 2 times; singly-regrown superset reported). The
threshold is where sigma-induced loss exceeds the sigma_R = 0
intrinsic floor. Selection arm: tournament on ancestor-fidelity at
matched rendition complexity (review #5)."""

from __future__ import annotations

import json
import time

import numpy as np
from scipy import ndimage, optimize

from blueprint_web.config import BlueprintConfig
from blueprint_web.engine import blueprint_step
from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from ladder_web.config import LadderConfig
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import posterior_mask, tissue_config
from voltage_web.engine import launch_pattern, make_thresholds

from .config import COMPLEXITIES, EigenConfig, SIGMA_GRID, results_root


def stripe_message(tissue, k: int) -> np.ndarray:
    """Area-balanced k-domain message (vertical stripes, k even)."""
    w = tissue.width
    cols = (np.arange(w) * k // w) % 2
    return np.where(cols[None, :] == 0, 1.0, -1.0) * np.ones(
        (tissue.height, 1))


def fission_with_mask(V, Rf, tissue, rng):
    """voltage_web.fission (mode='fragment') reproduced draw-for-draw,
    returning the regrown mask (the frozen fission jitters the whole
    offspring, so exact-value detection finds nothing — E54 round-1
    lesson, shared fix)."""
    batch = V.shape[0]
    offspring = np.full_like(V, tissue.resting)
    axis = rng.integers(0, 2, batch)
    side = rng.integers(0, 2, batch)
    kept = np.zeros(V.shape, dtype=bool)
    half_h, half_w = tissue.height // 2, tissue.width // 2
    for b in range(batch):
        if axis[b] == 0:
            rows = slice(0, half_h) if side[b] == 0 else slice(half_h, None)
            offspring[b, rows, :] = V[b, rows, :]
            kept[b, rows, :] = True
        else:
            cols = slice(0, half_w) if side[b] == 0 else slice(half_w, None)
            offspring[b, :, cols] = V[b, :, cols]
            kept[b, :, cols] = True
    offspring = offspring + tissue.copy_jitter * rng.standard_normal(
        offspring.shape)
    return offspring, (Rf.copy() if Rf is not None else None), ~kept


def count_domains(field: np.ndarray) -> int:
    total = 0
    for sign in (field > 0, field < 0):
        _, n = ndimage.label(sign)
        total += n
    return total


def _free(V, ema, Rf, theta, tissue, ladder, bp, rng, sweeps, c_m=None):
    for _ in range(sweeps):
        V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder, bp,
                                    "T", rng, c_m=c_m)
    return V, ema, Rf


def prepare_ancestor(config: EigenConfig, tissue, theta, bp, ladder, rng,
                     k: int):
    """Settle, imprint the k-domain message for 2/rho, render for 1/rho."""
    V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema, Rf = V.copy(), V.copy()
    V, ema, Rf = _free(V, ema, Rf, theta, tissue, ladder, bp, rng,
                       config.settle_sweeps)
    hold = stripe_message(tissue, k) * config.imprint_hold
    for _ in range(config.imprint_hold_sweeps):
        V = np.where(np.abs(hold)[None] > 0, hold[None], V)
        V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder, bp,
                                    "T", rng)
    V, ema, Rf = _free(V, ema, Rf, theta, tissue, ladder, bp, rng,
                       config.render_sweeps)
    rendition = np.sign(V)
    rendition[rendition == 0] = 1.0
    return V, ema, Rf, rendition


def lineage_fidelity(config: EigenConfig, tissue, theta, bp, ladder, rng,
                     V, Rf, rendition, sigma_r: float) -> dict:
    """One noisy lineage; per-generation ancestor fidelity on regrown
    cells (>=1 and the strict >=2 channel)."""
    ema = V.copy()
    regrow_count = np.zeros(V.shape, dtype=np.int32)
    fid1, fid2, parent_fid = [], [], []
    for _ in range(config.cycles):
        parent_sign = np.sign(V)
        kids, R_kid, fresh = fission_with_mask(V, Rf, tissue, rng)
        regrow_count += fresh
        if sigma_r > 0:
            R_kid = R_kid + sigma_r * rng.standard_normal(R_kid.shape)
        V, Rf = kids, R_kid
        ema = V.copy()
        V, ema, Rf = _free(V, ema, Rf, theta, tissue, ladder, bp, rng,
                           config.inter_fission)
        ok_anc = ((V > 0) == (rendition > 0)) & (np.abs(V) > config.amp_threshold)
        ok_par = ((V > 0) == (parent_sign > 0)) & (np.abs(V) > config.amp_threshold)
        m1 = regrow_count >= 1
        m2 = regrow_count >= 2
        fid1.append(float(np.mean([ok_anc[b][m1[b]].mean()
                                   for b in range(V.shape[0]) if m1[b].any()])))
        fid2.append(float(np.mean([ok_anc[b][m2[b]].mean()
                                   for b in range(V.shape[0]) if m2[b].any()]))
                    if m2.any() else None)
        parent_fid.append(float(np.mean([ok_par[b][m1[b]].mean()
                                         for b in range(V.shape[0])
                                         if m1[b].any()])))
    return {"ancestor_fid_regrown1": fid1, "ancestor_fid_regrown2": fid2,
            "parent_fid": parent_fid,
            "final_domains": int(np.median([count_domains(np.sign(V[b]))
                                            for b in range(V.shape[0])]))}


def sweep_run(config: EigenConfig, index: int, k: int) -> dict:
    bp = BlueprintConfig()
    rc = RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    theta = make_thresholds(tissue)
    ladder = LadderConfig()
    arng = seed_rng(config.trajectory_seed_tag, "ancestor", index, k)
    V0, ema0, R0, rendition = prepare_ancestor(config, tissue, theta, bp,
                                               ladder, arng, k)
    rendition_domains = int(np.median([count_domains(rendition[b])
                                       for b in range(config.futures)]))
    rows = []
    for sigma in SIGMA_GRID:
        rng = seed_rng(config.trajectory_seed_tag, "lineage", index, k,
                       float(sigma))
        out = lineage_fidelity(config, tissue, theta, bp, ladder, rng,
                               V0.copy(), R0.copy(), rendition, sigma)
        rows.append({"sigma": float(sigma), **out})
    return {"tissue": index, "k": k,
            "rendition_domains": rendition_domains, "rows": rows}


def selection_run(config: EigenConfig, index: int) -> dict:
    """Quasispecies rescue at matched complexity: tournament on
    ancestor-fidelity among the batch's lineages each cycle; lineages
    whose rendition complexity drifts by more than 1 domain-pair score
    zero (review #5)."""
    bp = BlueprintConfig()
    rc = RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    theta = make_thresholds(tissue)
    ladder = LadderConfig()
    k = config.selection_complexity
    arng = seed_rng(config.trajectory_seed_tag, "sel-ancestor", index, k)
    V0, ema0, R0, rendition = prepare_ancestor(config, tissue, theta, bp,
                                               ladder, arng, k)
    base_domains = int(np.median([count_domains(rendition[b])
                                  for b in range(config.futures)]))
    rows = []
    for sigma in SIGMA_GRID:
        rng = seed_rng(config.trajectory_seed_tag, "sel", index, k,
                       float(sigma))
        V, Rf = V0.copy(), R0.copy()
        ema = V.copy()
        regrow_count = np.zeros(V.shape, dtype=np.int32)
        fid_final = None
        for _ in range(config.cycles):
            kids, R_kid, fresh = fission_with_mask(V, Rf, tissue, rng)
            regrow_count += fresh
            if sigma > 0:
                R_kid = R_kid + sigma * rng.standard_normal(R_kid.shape)
            V, Rf = kids, R_kid
            ema = V.copy()
            V, ema, Rf = _free(V, ema, Rf, theta, tissue, ladder, bp, rng,
                               config.inter_fission)
            ok = ((V > 0) == (rendition > 0)) & (np.abs(V) > config.amp_threshold)
            m1 = regrow_count >= 1
            fits = np.array([ok[b][m1[b]].mean() if m1[b].any() else 0.0
                             for b in range(V.shape[0])])
            doms = np.array([count_domains(np.sign(V[b]))
                             for b in range(V.shape[0])])
            fits = np.where(np.abs(doms - base_domains) <= 2, fits, 0.0)
            # Tournament: each next-lineage copies a selected parent's
            # full state (V, R, regrow history).
            picks = []
            for _ in range(V.shape[0]):
                cand = rng.integers(0, V.shape[0], config.tournament)
                picks.append(int(cand[np.argmax(fits[cand])]))
            V = V[picks].copy()
            Rf = Rf[picks].copy()
            ema = ema[picks].copy()
            regrow_count = regrow_count[picks].copy()
            fid_final = float(np.mean(fits[picks]))
        rows.append({"sigma": float(sigma), "final_fid": fid_final})
    return {"tissue": index, "base_domains": base_domains, "rows": rows}


def freedom_check(config: EigenConfig, index: int, sigma: float) -> dict:
    """Zap conversion with copy noise just below threshold: paired
    zap/no-zap positional change (E52's plasticity pattern)."""
    bp = BlueprintConfig()
    rc = RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    theta = make_thresholds(tissue)
    ladder = LadderConfig()
    out = {}
    for arm in ("zap", "control"):
        rng = seed_rng(config.trajectory_seed_tag, "freedom", index,
                       float(sigma))
        V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
        V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
        ema, Rf = V.copy(), V.copy()
        V, ema, Rf = _free(V, ema, Rf, theta, tissue, ladder, bp, rng,
                           config.settle_sweeps)
        kids, R_kid, _ = fission_with_mask(V, Rf, tissue, rng)
        if sigma > 0:
            R_kid = R_kid + sigma * rng.standard_normal(R_kid.shape)
        V, Rf = kids, R_kid
        ema = V.copy()
        pre = V > 0
        zmask = posterior_mask(tissue)
        for sweep in range(config.zap_recover):
            clamp = zmask if (arm == "zap" and sweep < config.zap_sweeps) else None
            V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder,
                                        bp, "T", rng, clamp=clamp)
        alive = np.abs(V).mean(axis=(-2, -1)) > 0.2
        change = 1.0 - ((V > 0) == pre).mean(axis=(-2, -1))
        out[arm] = float(change[alive].mean()) if alive.any() else 0.0
    out["conversion"] = out["zap"] - out["control"]
    return out


def _sigmoid_threshold(sigmas, losses):
    """Fit loss(sigma) = L / (1 + (sigma/s*)^-h); return s*, width."""
    s = np.array([x for x in sigmas if x > 0])
    y = np.array([l for x, l in zip(sigmas, losses) if x > 0])
    if y.max() <= 0.02:
        return None, None
    y = np.clip(y / max(y.max(), 1e-9), 0, 1)

    def f(x, s_star, h):
        return 1.0 / (1.0 + (x / s_star) ** (-h))

    try:
        popt, _ = optimize.curve_fit(f, s, y, p0=[0.5, 2.0],
                                     bounds=([1e-3, 0.2], [10.0, 20.0]),
                                     maxfev=5000)
        s_star, h = popt
        width_decades = float((np.log10(9.0)) * 2.0 / h)
        return float(s_star), width_decades
    except Exception:
        return None, None


def run_gates(config: EigenConfig, *, n_shards: int = 1,
              shard: int | None = None) -> dict:
    started = time.time()
    work = results_root(config) / "work"
    work.mkdir(parents=True, exist_ok=True)
    jobs = [("sweep", i, k) for i in range(config.n_tissues)
            for k in COMPLEXITIES]
    jobs += [("selection", i, None) for i in range(config.n_tissues)]
    if shard is not None:
        target = work / f"eigen_shard_{shard:02d}_of_{n_shards:02d}.json"
        if target.exists():
            cached = json.loads(target.read_text())
            if cached.get("config_digest") == config.digest():
                return cached
        entries = []
        for kind, i, k in jobs[shard::n_shards]:
            if kind == "sweep":
                entries.append({"kind": "sweep", **sweep_run(config, i, k)})
            else:
                entries.append({"kind": "selection",
                                **selection_run(config, i)})
        payload = {"config_digest": config.digest(), "entries": entries,
                   "elapsed_seconds": time.time() - started}
        atomic_json(target, payload)
        return payload
    entries = []
    for s in range(n_shards):
        entries.extend(run_gates(config, n_shards=n_shards, shard=s)["entries"])
    sweeps = [e for e in entries if e["kind"] == "sweep"]
    sels = [e for e in entries if e["kind"] == "selection"]

    def final_fid(row):
        vals = row["ancestor_fid_regrown2"]
        tail = [v for v in vals[-3:] if v is not None]
        return float(np.mean(tail)) if tail else None

    curves = {}
    for k in COMPLEXITIES:
        rows_k = [r for e in sweeps if e["k"] == k for r in e["rows"]]
        by_sigma = {}
        for sigma in SIGMA_GRID:
            vals = [final_fid(r) for r in rows_k if r["sigma"] == sigma]
            vals = [v for v in vals if v is not None]
            by_sigma[str(sigma)] = float(np.mean(vals)) if vals else None
        curves[str(k)] = by_sigma
    # Threshold on the pooled complexity-4 curve (the register's primary).
    primary = curves[str(config.selection_complexity)]
    floor = primary[str(0.0)]
    sigmas = list(SIGMA_GRID)
    losses = [max(0.0, floor - primary[str(s)])
              if primary[str(s)] is not None else 0.0 for s in sigmas]
    s_star, width = _sigmoid_threshold(sigmas, losses)
    sel_curves = {}
    for sigma in SIGMA_GRID:
        vals = [r["final_fid"] for e in sels for r in e["rows"]
                if r["sigma"] == sigma]
        sel_curves[str(sigma)] = float(np.mean(vals)) if vals else None
    sel_floor = sel_curves[str(0.0)]
    sel_losses = [max(0.0, sel_floor - sel_curves[str(s)])
                  if sel_curves[str(s)] is not None else 0.0 for s in sigmas]
    s_star_sel, _ = _sigmoid_threshold(sigmas, sel_losses)
    # Capacity: for each k, the largest sigma keeping fidelity within
    # 0.1 of that k's floor.
    capacity = {}
    for k in COMPLEXITIES:
        c = curves[str(k)]
        kfloor = c[str(0.0)]
        tol = [s for s in sigmas if s > 0 and c[str(s)] is not None
               and c[str(s)] >= (kfloor or 0) - 0.1]
        capacity[str(k)] = float(max(tol)) if tol else 0.0
    rendition_domains = {str(k): int(np.median(
        [e["rendition_domains"] for e in sweeps if e["k"] == k]))
        for k in COMPLEXITIES}
    freedom = None
    if s_star is not None:
        sub = max([s for s in sigmas if 0 < s < s_star], default=None)
        if sub is not None:
            freedom = {"sigma": sub,
                       **freedom_check(config, 0, sub)}
    cap_vals = [capacity[str(k)] for k in COMPLEXITIES]
    monotone = all(cap_vals[i] >= cap_vals[i + 1] - 1e-9
                   for i in range(len(cap_vals) - 1))
    distinct = len({round(v, 4) for v in cap_vals}) >= 2
    gates = {
        "curves": curves, "capacity": capacity,
        "rendition_domains": rendition_domains,
        "sigma_star": s_star, "transition_width_decades": width,
        "sigma_star_selected": s_star_sel,
        "selection_shift": (s_star_sel / s_star
                            if s_star and s_star_sel else None),
        "selection_curves": sel_curves,
        "freedom": freedom,
        "gate_p55_1_sharp_threshold": bool(
            s_star is not None and width is not None and width < 1.0),
        "gate_p55_2_quasispecies_rescue": bool(
            s_star and s_star_sel and s_star_sel >= 2.0 * s_star),
        "gate_p55_3_capacity_law": bool(monotone and distinct),
        "gate_p55_4_freedom": bool(
            freedom is not None
            and freedom["conversion"] >= config.freedom_bar),
    }
    payload = {
        "config_digest": config.digest(),
        "gates": gates,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(results_root(config) / "eigen_summary.json", payload)
    return payload
