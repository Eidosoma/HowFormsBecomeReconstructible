"""E27: rewrite gates across tissues and coupling cohorts."""

from __future__ import annotations

import json
import time

import numpy as np

from contract_bridge.artifacts import atomic_json, environment_manifest, seed_rng

from .config import RewriteConfig, results_root
from .runner import detect_rewrites, run_trajectory, score_recovery, tissue_config


def _lesion_mask(tissue, rng) -> np.ndarray:
    mask = np.zeros((tissue.height, tissue.width), dtype=bool)
    top = rng.integers(0, tissue.height // 2)
    left = rng.integers(0, tissue.width // 2)
    mask[top:top + tissue.height // 2, left:left + tissue.width // 2] = True
    return mask


def run_tissue(config: RewriteConfig, cohort: str, index: int) -> dict:
    coupling = {
        "band": config.coupling_band,
        "under": config.coupling_under,
        "over": config.coupling_over,
    }[cohort]
    tissue = tissue_config(index, coupling, config)
    lesion = _lesion_mask(tissue, seed_rng("rewrite-lesion-v1", index))
    tag = f"{config.trajectory_seed_tag}-{cohort}"
    rows, masks = {}, {}
    for arm, zap in (("control", False), ("zapped", True)):
        traj = run_trajectory(
            tissue, config, seed_rng(tag, index), zap=zap, lesion_mask=lesion
        )
        rewrites = detect_rewrites(traj, config)
        recovery = score_recovery(traj, config, rewrites)
        eligible = rewrites["wild_alive"]
        rewritten = rewrites["rewritten"]
        wild_like = eligible & ~rewritten
        masks[arm] = {"eligible": eligible, "rewritten": rewritten}
        rows[arm] = {
            "eligible": int(eligible.sum()),
            "rewrite_fraction": float(rewritten[eligible].mean()) if eligible.any() else 0.0,
            "wild_recovery": float(
                recovery["recovered"][wild_like].mean()
            ) if wild_like.any() else None,
            "rewritten_recovery": float(
                (recovery["recovered"] & recovery["still_distinct"])[rewritten].mean()
            ) if rewritten.any() else None,
            "n_rewritten": int(rewritten.sum()),
        }
    # Paired causal effect over shared-stream futures.
    both = masks["control"]["eligible"] & masks["zapped"]["eligible"]
    z, c = masks["zapped"]["rewritten"], masks["control"]["rewritten"]
    conversion = float((z & ~c)[both].mean()) if both.any() else 0.0
    reverse = float((~z & c)[both].mean()) if both.any() else 0.0
    return {
        "cohort": cohort, "tissue": index,
        "conversion": conversion, "reverse": reverse,
        "n_paired": int(both.sum()),
        **{f"{k}_{kk}": vv for k, v in rows.items() for kk, vv in v.items()},
    }


def run_shard(config: RewriteConfig, shard: int, n_shards: int) -> dict:
    started = time.time()
    work = results_root(config) / "work"
    work.mkdir(parents=True, exist_ok=True)
    target = work / f"rewrite_shard_{shard:02d}_of_{n_shards:02d}.json"
    if target.exists():
        cached = json.loads(target.read_text())
        if cached.get("config_digest") == config.digest():
            return cached
    jobs = (
        [("band", i) for i in range(config.n_tissues)]
        + [("under", i) for i in range(config.off_band_tissues)]
        + [("over", i) for i in range(config.off_band_tissues)]
    )
    entries = [run_tissue(config, cohort, index) for cohort, index in jobs[shard::n_shards]]
    payload = {
        "config_digest": config.digest(),
        "shard": shard,
        "entries": entries,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(target, payload)
    return payload


def run_gates(config: RewriteConfig, *, n_shards: int = 1) -> dict:
    started = time.time()
    entries = []
    for shard in range(n_shards):
        entries.extend(run_shard(config, shard, n_shards)["entries"])

    def cohort_rows(name):
        return [e for e in entries if e["cohort"] == name]

    def mean_fraction(rows, key):
        values = [r[key] for r in rows if r[key] is not None]
        return float(np.mean(values)) if values else 0.0

    band = cohort_rows("band")
    zap_frac = mean_fraction(band, "zapped_rewrite_fraction")
    control_frac = mean_fraction(band, "control_rewrite_fraction")
    conversion = mean_fraction(band, "conversion")
    reverse = mean_fraction(band, "reverse")
    under_conv = mean_fraction(cohort_rows("under"), "conversion")
    over_conv = mean_fraction(cohort_rows("over"), "conversion")
    wild_recovery = mean_fraction(band, "zapped_wild_recovery")
    rewritten_recovery = mean_fraction(
        [r for r in band if r["zapped_n_rewritten"] >= 3], "zapped_rewritten_recovery"
    )
    per_tissue_rewrite = {
        r["tissue"]: r["zapped_rewrite_fraction"] for r in band
    }
    gates = {
        "zapped_rewrite_fraction": zap_frac,
        "control_rewrite_fraction": control_frac,
        "paired_conversion": conversion,
        "paired_reverse": reverse,
        "gate_rewrite_exists": bool(
            conversion >= 0.02 and conversion >= 3 * max(reverse, 1e-9)
        ),
        "under_conversion": under_conv,
        "over_conversion": over_conv,
        "gate_regime_dependence": bool(
            conversion >= 2 * max(under_conv, 1e-9) and conversion >= 2 * max(over_conv, 1e-9)
        ),
        "wild_recovery": wild_recovery,
        "rewritten_recovery": rewritten_recovery,
        "gate_two_setpoints_canalized": bool(
            wild_recovery >= 0.7 and rewritten_recovery >= 0.7
        ),
        "per_tissue_rewrite_fraction": per_tissue_rewrite,
        "n_band_tissues_with_rewrites": int(
            sum(1 for r in band if r["zapped_n_rewritten"] >= 3)
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
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "rewrite_summary.json", payload)
    return payload
