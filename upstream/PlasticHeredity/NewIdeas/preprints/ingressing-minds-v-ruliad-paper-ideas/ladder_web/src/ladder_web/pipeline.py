"""E35: per-rung heredity screens + the light cone measurement."""

from __future__ import annotations

import json
import time

import numpy as np

from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import tissue_config
from voltage_web.engine import launch_pattern, make_thresholds

from .config import RUNGS, LadderConfig, results_root
from .engine import ladder_step, tissue_fields


def _cos(u, v):
    d = np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1)
    return np.where(d > 0, (u * v).sum(axis=-1) / np.maximum(d, 1e-300), 0.0)


def rung_screen(config: LadderConfig, rung: str) -> dict:
    """The E26 heredity criteria must survive each machinery addition."""
    from .engine import run_lineage

    rc = RewriteConfig.tiny() if config.mode == "tiny" else RewriteConfig()
    h_all, survivals = [], []
    for index in range(min(config.n_tissues, 6)):
        tissue = tissue_config(index, rc.coupling_band, rc)
        out = run_lineage(
            tissue, config, rung,
            seed_rng(config.trajectory_seed_tag + "-screen", rung, index),
            horizon=12, n_futures=32,
        )
        censuses, alive = out["censuses"], out["alive"]
        for t in range(2, 12):
            both = alive[t] & alive[t - 1]
            if both.sum() >= 4:
                h_all.append(_cos(censuses[t - 1][both], censuses[t][both]))
        survivals.append(float(alive[8].mean()) if alive.shape[0] > 8 else 0.0)
    h = np.concatenate(h_all) if h_all else np.zeros(0)
    criteria = {
        "h_above": float((h > 0.9).mean()) if h.size else 0.0,
        "h_below": float((h < 0.85).mean()) if h.size else 0.0,
        "survival_8": float(np.median(survivals)),
        "pass": bool(
            h.size and (h > 0.9).mean() >= 0.3 and (h < 0.85).mean() >= 0.02
            and np.median(survivals) >= 0.3
        ),
    }
    return criteria


def _settled_sheet(tissue, config, rung, rng, sweeps=40):
    theta = make_thresholds(tissue)
    anchors = tissue_fields(tissue, config, rung)
    V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema = V.copy()
    for _ in range(sweeps):
        V, ema, _ = ladder_step(V, ema, theta, tissue, config, rung, rng, anchors)
    return V, ema, theta, anchors


def spatial_cone(config: LadderConfig, rung: str, index: int) -> dict:
    """Largest displacement distance restored to POSITION."""
    rc = RewriteConfig.tiny() if config.mode == "tiny" else RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    rng = seed_rng(config.trajectory_seed_tag + "-space", rung, index)
    V, ema, theta, anchors = _settled_sheet(tissue, config, rung, rng)
    ref_profile = V.mean(axis=1)
    out = {}
    for d in config.displacement_ladder:
        x0 = tissue.width // 4
        ins = V.copy()
        ins[:, :, x0:x0 + 2] -= config.displacement_magnitude
        ins[:, :, (x0 + d) % tissue.width:(x0 + d) % tissue.width + 2] += config.displacement_magnitude
        ema_i = ins.copy()
        err0 = np.abs(ins.mean(axis=1) - ref_profile).mean()
        for _ in range(config.recovery_sweeps):
            ins, ema_i, _ = ladder_step(ins, ema_i, theta, tissue, config, rung, rng, anchors)
        err_end = np.abs(ins.mean(axis=1) - ref_profile).mean()
        out[str(d)] = {
            "recovery_fraction": float(1.0 - err_end / max(err0, 1e-9)),
        }
    cone = 0
    for d in config.displacement_ladder:
        if out[str(d)]["recovery_fraction"] >= 0.5:
            cone = d
    out["spatial_cone"] = cone
    return out


def temporal_cone(config: LadderConfig, rung: str, index: int) -> dict:
    """Generations until census identity decays below the inherit bar."""
    from .engine import run_lineage

    rc = RewriteConfig.tiny() if config.mode == "tiny" else RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    out = run_lineage(
        tissue, config, rung,
        seed_rng(config.trajectory_seed_tag + "-time", rung, index),
        horizon=config.persistence_horizon,
    )
    censuses, alive = out["censuses"], out["alive"]
    ref = censuses[2]
    ref_alive = alive[2]
    horizon = 0
    for t in range(3, config.persistence_horizon):
        live = alive[t] & ref_alive
        if live.sum() < 8:
            break
        if float(np.median(_cos(censuses[t][live], ref[live]))) > 0.9:
            horizon = t - 2
        else:
            break
    return {"temporal_cone_generations": horizon}


def repair_speed(config: LadderConfig, rung: str, index: int) -> dict:
    """Median sweeps to census recovery from a patch-shuffle insult."""
    from anatomical_homeostasis.perturb import apply_perturbation
    from glider_test.life import block_counts

    rc = RewriteConfig.tiny() if config.mode == "tiny" else RewriteConfig()
    tissue = tissue_config(index, rc.coupling_band, rc)
    rng = seed_rng(config.trajectory_seed_tag + "-speed", rung, index)
    V, ema, theta, anchors = _settled_sheet(tissue, config, rung, rng)

    def census(x):
        c = block_counts((x > 0).astype(np.uint8))
        return c / np.maximum(c.sum(axis=1, keepdims=True), 1.0)

    setpoint = census(V)
    ins = apply_perturbation(V, "patch_shuffle", tissue, 8,
                             seed_rng("ladder-speed-p", rung, index))
    ema_i = ins.copy()
    rec = np.full(ins.shape[0], -1)
    for sweep in range(1, 25):
        ins, ema_i, _ = ladder_step(ins, ema_i, theta, tissue, config, rung, rng, anchors)
        c = _cos(census(ins), setpoint)
        newly = (rec < 0) & (c > 0.9)
        rec[newly] = sweep
    recovered = rec > 0
    return {
        "recovery_rate": float(recovered.mean()),
        "median_recovery_sweeps": float(np.median(rec[recovered])) if recovered.any() else None,
    }


def run_lightcone(config: LadderConfig, *, n_shards: int = 1, shard: int | None = None) -> dict:
    started = time.time()
    work = results_root(config) / "work"
    work.mkdir(parents=True, exist_ok=True)
    jobs = [(rung, index) for rung in RUNGS for index in range(config.n_tissues)]
    if shard is not None:
        target = work / f"cone_shard_{shard:02d}_of_{n_shards:02d}.json"
        if target.exists():
            cached = json.loads(target.read_text())
            if cached.get("config_digest") == config.digest():
                return cached
        entries = []
        for rung, index in jobs[shard::n_shards]:
            entries.append({
                "rung": rung, "tissue": index,
                "space": spatial_cone(config, rung, index),
                "time": temporal_cone(config, rung, index),
                "speed": repair_speed(config, rung, index),
            })
        payload = {"config_digest": config.digest(), "entries": entries,
                   "elapsed_seconds": time.time() - started}
        atomic_json(target, payload)
        return payload

    entries = []
    for s in range(n_shards):
        entries.extend(run_lightcone(config, n_shards=n_shards, shard=s)["entries"])

    def rung_stats(rung):
        rows = [e for e in entries if e["rung"] == rung]
        return {
            "spatial_cone_median": float(np.median([e["space"]["spatial_cone"] for e in rows])),
            "temporal_cone_median": float(np.median(
                [e["time"]["temporal_cone_generations"] for e in rows]
            )),
            "recovery_rate": float(np.mean([e["speed"]["recovery_rate"] for e in rows])),
            "median_recovery_sweeps": float(np.median(
                [e["speed"]["median_recovery_sweeps"] for e in rows
                 if e["speed"]["median_recovery_sweeps"] is not None]
            )) if any(e["speed"]["median_recovery_sweeps"] is not None for e in rows) else None,
        }

    cone = {rung: rung_stats(rung) for rung in RUNGS}
    gates = {
        "lightcone": cone,
        "gate_p35_1_rungA_spatial_zero": bool(cone["A"]["spatial_cone_median"] == 0),
        "gate_p35_2_anchors": bool(
            cone["B"]["spatial_cone_median"] >= 2
            and cone["B"]["temporal_cone_median"] >= 2 * max(cone["A"]["temporal_cone_median"], 1)
        ),
        "gate_p35_3_morphogen": bool(
            cone["C"]["spatial_cone_median"] >= 2 * max(cone["B"]["spatial_cone_median"], 1)
        ),
        "gate_p35_4_striving": bool(
            cone["D"]["median_recovery_sweeps"] is not None
            and cone["D"]["median_recovery_sweeps"] >= 5
            and cone["D"]["recovery_rate"] >= 0.8
        ),
    }
    payload = {
        "config_digest": config.digest(),
        "n_entries": len(entries),
        "gates": gates,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(config)
    atomic_json(out / "lightcone_summary.json", payload)
    return payload
