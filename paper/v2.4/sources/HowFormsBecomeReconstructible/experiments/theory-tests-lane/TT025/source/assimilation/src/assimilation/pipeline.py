"""E57: where does a lineage store its anatomy? Heritable theta (fixed-
norm shell) + heritable (rho, c_m), fitness = adopt-the-instructed-
target then defend it through two cuts (a plasticity component in EVERY
arm, review #3), horizon 1000 sweeps = 2/rho_min (review #16), regrown-
region-scored (review #10). Environments: static / switching (k swept) /
drift. Assimilation measured on theta's own channel — the operational
consensus map (the mid-wave amendment)."""

from __future__ import annotations

import json
import time

import numpy as np

from blueprint_web.config import BlueprintConfig
from blueprint_web.engine import blueprint_step
from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from dataclasses import replace
from ladder_web.config import LadderConfig
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import tissue_config
from voltage_web.engine import launch_pattern, make_thresholds

from .config import AssimilationConfig, REGIMES, results_root


def project_theta(theta: np.ndarray, norm: float) -> np.ndarray:
    t = theta - theta.mean()
    s = t.std()
    return t * (norm / s) if s > 0 else t


def fission_with_mask(V, Rf, tissue, rng):
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


def _step(V, ema, Rf, theta, tissue, ladder, bp, rng, c_m=None, clamp=None):
    return blueprint_step(V, ema, Rf, theta, tissue, ladder, bp, "T", rng,
                          c_m=c_m, clamp=clamp)


def harvest_targets(config: AssimilationConfig, tissue) -> list:
    """The environment's menu: attractor sign-patterns of the NATIVE-
    theta tissue, frozen before evolution begins."""
    theta = make_thresholds(tissue)
    bp = BlueprintConfig()
    ladder = LadderConfig()
    targets = []
    for s in range(config.n_targets):
        rng = seed_rng(config.trajectory_seed_tag, "target", tissue.tissue_index, s)
        V = np.tile(launch_pattern(s, tissue), (config.futures, 1, 1))
        V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
        ema, Rf = V.copy(), V.copy()
        for _ in range(config.target_settle):
            V, ema, Rf = _step(V, ema, Rf, theta, tissue, ladder, bp, rng,
                               c_m=0.0)
        t = np.sign(V[0])
        t[t == 0] = 1.0
        targets.append(t)
    return targets


def eval_fitness(config: AssimilationConfig, tissue, ladder, gene,
                 target, rng, knife: str = "none") -> float:
    """Adopt the instructed target, then defend it through two cuts.
    Regrown-region amplitude-thresholded match to the target."""
    rho, c_m_gene, theta = gene
    if knife == "theta_scramble":
        theta = rng.permutation(theta.ravel()).reshape(theta.shape)
    bp = replace(BlueprintConfig(), rho=rho, c_m=c_m_gene)
    c_m = 0.0 if knife == "cm_zero" else None
    V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema, Rf = V.copy(), V.copy()
    for _ in range(config.eval_settle):
        V, ema, Rf = _step(V, ema, Rf, theta, tissue, ladder, bp, rng, c_m=c_m)
    hold = target * config.imprint_hold
    for _ in range(config.eval_instruct):
        V = np.where(np.abs(hold)[None] > 0, hold[None], V)
        V, ema, Rf = _step(V, ema, Rf, theta, tissue, ladder, bp, rng, c_m=c_m)
    for _ in range(config.eval_free):
        V, ema, Rf = _step(V, ema, Rf, theta, tissue, ladder, bp, rng, c_m=c_m)
    regrown = np.zeros(V.shape, dtype=bool)
    for _ in range(config.eval_cycles):
        V, Rf, fresh = fission_with_mask(V, Rf, tissue, rng)
        regrown |= fresh
        ema = V.copy()
        for _ in range(config.eval_regrow):
            V, ema, Rf = _step(V, ema, Rf, theta, tissue, ladder, bp, rng,
                               c_m=c_m)
    ok = ((V > 0) == (target > 0)[None]) & (np.abs(V) > config.amp_threshold)
    vals = [ok[b][regrown[b]].mean() for b in range(V.shape[0])
            if regrown[b].any()]
    return float(np.mean(vals)) if vals else 0.0


def consensus_corr(config: AssimilationConfig, tissue, ladder, theta,
                   target, rng) -> float:
    """theta's operational preference (the E53 probe instrument): plain
    settles from neutral launches; consensus sign map vs the target."""
    bp = BlueprintConfig()
    signs = []
    for s in range(config.consensus_launches):
        V = np.tile(launch_pattern(6 + s, tissue), (config.futures, 1, 1))
        V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
        ema, Rf = V.copy(), V.copy()
        for _ in range(config.target_settle):
            V, ema, Rf = _step(V, ema, Rf, theta, tissue, ladder, bp, rng,
                               c_m=0.0)
        signs.append(np.sign(V).mean(axis=0))
    profile = np.mean(signs, axis=0)
    a = profile - profile.mean()
    b = target - target.mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / denom) if denom > 0 else 0.0


def run_regime(config: AssimilationConfig, regime: str, repeat: int) -> dict:
    rc = RewriteConfig()
    tissue = tissue_config(repeat, rc.coupling_band, rc)
    ladder = LadderConfig()
    targets = harvest_targets(config, tissue)
    native = make_thresholds(tissue)
    rng = seed_rng(config.trajectory_seed_tag, regime, repeat)
    lo_r, hi_r = np.log(config.rho_init[0]), np.log(config.rho_init[1])
    lo_c, hi_c = np.log(config.cm_init[0]), np.log(config.cm_init[1])
    genes = []
    for _ in range(config.population):
        theta0 = project_theta(
            native + 0.02 * rng.standard_normal(native.shape),
            config.theta_norm)
        genes.append((float(np.exp(rng.uniform(lo_r, hi_r))),
                      float(np.exp(rng.uniform(lo_c, hi_c))),
                      theta0))
    k = {"switching_k2": 2, "switching_k4": 4}.get(regime)
    trajectory = []
    fits = [0.0] * config.population
    for gen in range(config.generations):
        if regime == "static":
            target = targets[0]
        elif k is not None:
            target = targets[(gen // k) % len(targets)]
        else:
            target = targets[0]
        if regime == "drift":
            fits = [0.0] * config.population
        else:
            fits = []
            for gi, gene in enumerate(genes):
                erng = seed_rng(config.trajectory_seed_tag + "-eval",
                                regime, repeat, gen, gi)
                fits.append(eval_fitness(config, tissue, ladder, gene,
                                         target, erng))
        trajectory.append({
            "gen": gen,
            "median_rho": float(np.median([g[0] for g in genes])),
            "median_cm": float(np.median([g[1] for g in genes])),
            "mean_fit": float(np.mean(fits)) if fits else 0.0,
        })
        next_genes = []
        for _ in range(config.population):
            if regime == "drift":
                parent = genes[int(rng.integers(config.population))]
            else:
                cand = rng.integers(0, config.population, config.tournament)
                parent = genes[int(max(cand, key=lambda i: fits[int(i)]))]
            rho = float(np.clip(
                parent[0] * np.exp(config.mutation_sigma * rng.standard_normal()),
                *config.rho_range))
            c_m = float(np.clip(
                parent[1] * np.exp(config.mutation_sigma * rng.standard_normal()),
                *config.cm_range))
            theta = project_theta(
                parent[2] + config.theta_mutation * rng.standard_normal(
                    parent[2].shape), config.theta_norm)
            next_genes.append((rho, c_m, theta))
        prev_genes = genes
        genes = next_genes
        prev_fits = fits
    champ_idx = (int(np.argmax(prev_fits)) if regime != "drift"
                 else int(rng.integers(config.population)))
    champion = prev_genes[champ_idx]
    # Post-evolution assays (fresh streams).
    assay_target = targets[0]
    knife_rows = {}
    for knife in ("none", "theta_scramble", "cm_zero"):
        vals = []
        for a in range(config.assay_evals):
            arng = seed_rng(config.trajectory_seed_tag + "-assay",
                            regime, repeat, knife, a)
            vals.append(eval_fitness(config, tissue, ladder, champion,
                                     assay_target, arng, knife=knife))
        knife_rows[knife] = float(np.mean(vals))
    crng = seed_rng(config.trajectory_seed_tag + "-consensus", regime, repeat)
    theta_corrs = [consensus_corr(config, tissue, ladder, champion[2], t,
                                  crng) for t in targets]
    nrng = seed_rng(config.trajectory_seed_tag + "-native", regime, repeat)
    native_corrs = [consensus_corr(config, tissue, ladder,
                                   project_theta(native, config.theta_norm),
                                   t, nrng) for t in targets]
    # Re-adoption probe (switching's P57.3): instruct a NON-current
    # target, measure adoption on the champion within 2/rho_min.
    rrng = seed_rng(config.trajectory_seed_tag + "-readopt", regime, repeat)
    other = targets[1]
    bp_c = replace(BlueprintConfig(), rho=champion[0], c_m=champion[1])
    V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
    V = V + tissue.copy_jitter * rrng.standard_normal(V.shape)
    ema, Rf = V.copy(), V.copy()
    for _ in range(config.eval_settle):
        V, ema, Rf = _step(V, ema, Rf, champion[2], tissue, ladder, bp_c, rrng)
    hold = other * config.imprint_hold
    for _ in range(config.eval_instruct):
        V = np.where(np.abs(hold)[None] > 0, hold[None], V)
        V, ema, Rf = _step(V, ema, Rf, champion[2], tissue, ladder, bp_c, rrng)
    for _ in range(config.readopt_horizon):
        V, ema, Rf = _step(V, ema, Rf, champion[2], tissue, ladder, bp_c, rrng)
    ok = ((V > 0) == (other > 0)[None]) & (np.abs(V) > config.amp_threshold)
    readopt = float(ok.mean(axis=(-2, -1)).mean())
    # Transport probe (P57.4, displacement-family protocol at the
    # champion's own parameters).
    trng = seed_rng(config.trajectory_seed_tag + "-transport", regime, repeat)
    transport = {}
    for knife in ("none", "cm_zero"):
        c_m = 0.0 if knife == "cm_zero" else None
        V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
        V = V + tissue.copy_jitter * trng.standard_normal(V.shape)
        ema, Rf = V.copy(), V.copy()
        for _ in range(config.target_settle):
            V, ema, Rf = _step(V, ema, Rf, champion[2], tissue, ladder,
                               bp_c, trng, c_m=c_m)
        pre = V.copy()
        q = np.zeros((tissue.height, tissue.width), dtype=bool)
        q[: tissue.height // 2, : tissue.width // 2] = True
        Vd = V.copy()
        Vd[:, q] = np.roll(V, config.transport_shift, axis=2)[:, q]
        ema = Vd.copy()
        for _ in range(config.transport_recover):
            Vd, ema, Rf = _step(Vd, ema, Rf, champion[2], tissue, ladder,
                                bp_c, trng, c_m=c_m)
        ok = ((Vd > 0) == (pre > 0)) & (np.abs(Vd) > config.amp_threshold)
        transport[knife] = float(ok[:, q].mean(axis=-1).mean())
    return {
        "regime": regime, "repeat": repeat,
        "median_rho": trajectory[-1]["median_rho"],
        "median_cm": trajectory[-1]["median_cm"],
        "trajectory": trajectory,
        "champion": {"rho": champion[0], "cm": champion[1]},
        "knife": knife_rows,
        "theta_target_corr": theta_corrs,
        "native_target_corr": native_corrs,
        "readoption": readopt,
        "transport": transport,
    }


def run_gates(config: AssimilationConfig, *, n_shards: int = 1,
              shard: int | None = None) -> dict:
    started = time.time()
    work = results_root(config) / "work"
    work.mkdir(parents=True, exist_ok=True)
    jobs = [(regime, repeat) for regime in REGIMES
            for repeat in range(config.n_repeats)]
    if shard is not None:
        target = work / f"assim_shard_{shard:02d}_of_{n_shards:02d}.json"
        if target.exists():
            cached = json.loads(target.read_text())
            if cached.get("config_digest") == config.digest():
                return cached
        entries = [run_regime(config, regime, repeat)
                   for regime, repeat in jobs[shard::n_shards]]
        payload = {"config_digest": config.digest(), "entries": entries,
                   "elapsed_seconds": time.time() - started}
        atomic_json(target, payload)
        return payload
    entries = []
    for s in range(n_shards):
        entries.extend(run_gates(config, n_shards=n_shards, shard=s)["entries"])

    def regime_rows(regime):
        return [e for e in entries if e["regime"] == regime]

    def med(regime, key):
        return float(np.median([e[key] for e in regime_rows(regime)]))

    switching = "switching_k4"
    band = (0.1, 0.3)
    sw_in_band = float(np.mean([band[0] <= e["median_cm"] <= band[1]
                                for e in regime_rows(switching)]))
    drift_in_band = float(np.mean([band[0] <= e["median_cm"] <= band[1]
                                   for e in regime_rows("drift")]))
    static_cm = med("static", "median_cm")
    sw_cm = med(switching, "median_cm")
    max_sel_rho = max(med(r, "median_rho")
                      for r in ("static", "switching_k2", switching))

    def lethality(regime, knife):
        rows = regime_rows(regime)
        return float(np.mean([e["knife"]["none"] - e["knife"][knife]
                              for e in rows]))

    static_theta_leth = lethality("static", "theta_scramble")
    static_cm_leth = lethality("static", "cm_zero")
    sw_theta_leth = lethality(switching, "theta_scramble")
    sw_cm_leth = lethality(switching, "cm_zero")
    interaction = ((static_theta_leth - static_cm_leth)
                   - (sw_theta_leth - sw_cm_leth))

    def corr_stat(regime, reducer):
        vals = []
        for e in regime_rows(regime):
            evolved = reducer(e["theta_target_corr"])
            native = reducer(e["native_target_corr"])
            vals.append(evolved - native)
        return float(np.mean(vals))

    static_corr_gain = corr_stat("static", lambda c: c[0])
    sw_corr_gain = corr_stat(switching, lambda c: max(c))
    readopt_sw = float(np.mean([e["readoption"]
                                for e in regime_rows(switching)]))

    def transport_pass(regime):
        rows = regime_rows(regime)
        gaps = [e["transport"]["none"] - e["transport"]["cm_zero"]
                for e in rows]
        return float(np.mean(gaps))

    gates = {
        "medians": {r: {"rho": med(r, "median_rho"),
                        "cm": med(r, "median_cm")} for r in REGIMES},
        "switching_in_band": sw_in_band,
        "drift_in_band": drift_in_band,
        "knife_lethality": {
            "static": {"theta": static_theta_leth, "cm": static_cm_leth},
            "switching": {"theta": sw_theta_leth, "cm": sw_cm_leth},
            "interaction": interaction,
        },
        "theta_corr_gain": {"static": static_corr_gain,
                            "switching": sw_corr_gain},
        "readoption_switching": readopt_sw,
        "transport_gap": {"static": transport_pass("static"),
                          "switching": transport_pass(switching)},
        "gate_p57_1_horizon_law": bool(
            (static_cm / max(sw_cm, 1e-9) >= 1.5
             or sw_cm / max(static_cm, 1e-9) >= 1.5)
            and sw_in_band >= 0.5
            and sw_in_band >= drift_in_band + 0.25
            and max_sel_rho <= 0.02),
        "gate_p57_2_assimilation": bool(
            static_corr_gain > 0.2 and interaction > 0.1),
        "gate_p57_3_plasticity_retained": bool(
            sw_cm_leth > sw_theta_leth and readopt_sw >= 0.5),
        "gate_p57_4_transport": bool(
            transport_pass("static") > 0.1
            and transport_pass(switching) > 0.1),
    }
    payload = {
        "config_digest": config.digest(),
        "gates": gates,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(results_root(config) / "assimilation_summary.json", payload)
    return payload
