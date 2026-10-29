"""E43: lineage runner with motility, heredity screens, sorting gate."""

from __future__ import annotations

import time

import numpy as np

from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from glider_test.life import block_counts
from ladder_web.config import LadderConfig
from ladder_web.engine import ladder_fission, tissue_fields
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import tissue_config
from voltage_web.engine import launch_pattern, make_thresholds

from .config import GrowConfig, results_root
from .engine import growing_step, interface_length


def _cos(u, v):
    d = np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1)
    return np.where(d > 0, (u * v).sum(axis=-1) / np.maximum(d, 1e-300), 0.0)


def run_lineage_grow(tissue, ladder, grow: GrowConfig, rung, rng, mrng, *,
                     horizon, n_futures, seed_index=0, motility_on=True):
    theta = make_thresholds(tissue)
    fields = tissue_fields(tissue, ladder, "D")
    V = np.tile(launch_pattern(seed_index, tissue), (n_futures, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema = V.copy()
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
        for _ in range(tissue.t_max_sweeps):
            if not active.any():
                break
            sub = np.flatnonzero(active)
            Vg[sub], emag[sub], _ = growing_step(
                Vg[sub], emag[sub], theta, tissue, ladder, grow, rung,
                rng, mrng, fields, motility_on=motility_on,
            )
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
        V = Vg
        V[live] = ladder_fission(Vg[live], tissue, ladder, "D", rng, fields)
        ema[live] = V[live]
    return {"censuses": censuses, "alive": alive_log}


def rung_screen_grow(ladder, grow: GrowConfig, rung: str) -> dict:
    rc = RewriteConfig()
    h_all, survivals = [], []
    for index in range(6):
        tissue = tissue_config(index, rc.coupling_band, rc)
        out = run_lineage_grow(
            tissue, ladder, grow, rung,
            seed_rng(grow.trajectory_seed_tag + "-screen", rung, index),
            seed_rng(grow.motility_seed_tag + "-screen", rung, index),
            horizon=12, n_futures=32,
        )
        censuses, alive = out["censuses"], out["alive"]
        for t in range(2, 12):
            both = alive[t] & alive[t - 1]
            if both.sum() >= 4:
                h_all.append(_cos(censuses[t - 1][both], censuses[t][both]))
        survivals.append(float(alive[8].mean()))
    h = np.concatenate(h_all) if h_all else np.zeros(0)
    return {
        "h_above": float((h > 0.9).mean()) if h.size else 0.0,
        "h_below": float((h < 0.85).mean()) if h.size else 0.0,
        "survival_8": float(np.median(survivals)),
        "pass": bool(
            h.size and (h > 0.9).mean() >= 0.3 and (h < 0.85).mean() >= 0.02
            and np.median(survivals) >= 0.3
        ),
    }


def sorting_gate(grow: GrowConfig) -> dict:
    """Interface length under rung-G motility vs motility-off, mixed start."""
    rows = {}
    for label, on in (("motile", True), ("off", False)):
        finals = []
        for k in range(4):
            rng = seed_rng("grow-sort-v1", label, k)
            mrng = seed_rng("grow-sort-motility-v1", k)
            V = np.where(rng.random((4, 16, 16)) < 0.5, 1.0, -1.0)
            if on:
                from .engine import motility_phase

                for _ in range(1000):
                    V = motility_phase(V, None, grow, "G", mrng)
            finals.append(float(interface_length(V).mean()))
        rows[label] = float(np.mean(finals))
    return {
        "interface_motile": rows["motile"],
        "interface_off": rows["off"],
        "gate_sorting": bool(rows["motile"] <= 0.5 * rows["off"]),
    }


def run_gates(grow: GrowConfig) -> dict:
    started = time.time()
    ladder = LadderConfig()
    screens = {rung: rung_screen_grow(ladder, grow, rung) for rung in ("G", "H")}
    sorting = sorting_gate(grow)
    payload = {
        "config_digest": grow.digest(),
        "screens": screens,
        "sorting": sorting,
        "gates": {
            "gate_p43_1_sorting": sorting["gate_sorting"],
            "gate_p43_2_heredity": bool(all(s["pass"] for s in screens.values())),
        },
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(grow)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "grow_summary.json", payload)
    return payload
