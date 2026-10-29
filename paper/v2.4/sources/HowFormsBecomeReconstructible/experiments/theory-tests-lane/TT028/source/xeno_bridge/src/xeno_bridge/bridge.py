"""The cross-formalism bridge: GARD launch states vs XENO launch seeds.

Both sides are reduced to LaunchProfiles — the support-free behavioral
subset (strict, generation clock, break hazard, recovery, inherit-run
curves) plus the rank-normalized fingerprint — and coupled ONLY by the
behavioral family confirmed in the A3 campaign. Identity rungs do not
exist across formalisms; the nulls are occupancy (row-constant), random
one-hot couplings, and shuffled-fingerprint matching.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import time

import numpy as np
from scipy.stats import rankdata

from finite_gard_ruliad.combinatorics import RuleCodec
from finite_gard_ruliad.kernels import make_state_spaces, solve_absorption
from finite_gard_ruliad.strict8 import exact_strict_probabilities

from contract_bridge.artifacts import (
    atomic_json,
    environment_manifest,
    hash_fraction,
    seed_rng,
)
from contract_bridge.physics import closed_kernel

from translator_redux.config import ReduxConfig
from translator_redux.profiles import build_profile
from translator_redux.scoring_q import rank_loss

from .chemistry import build_chemistry, sample_table
from .config import XenoConfig, results_root
from .lineage import SeedStats, run_seed

# The screen-frozen operating point (round 3, best passing point).
BRIDGE_OPERATING_POINT = {
    "gamma": 1000.0,
    "k_lig0": 3.0e-2,
    "p_self": 0.3,
    "mass_max": 96,
    "mass_dead": 6,
}

# Held-out blocks decide the verdict: none of their defining quantities
# enter the matching fingerprint. The in-matching blocks are reported as
# diagnostics only.
HELDOUT_BLOCKS = (
    "strict_rank",
    "hazard_rank",
    "recovery_curve_l1",
    "inherit_run_curve_l1",
)
MATCH_DIAGNOSTIC_BLOCKS = ("time_rank", "hazard_curve_l1")
BRIDGE_BLOCKS = HELDOUT_BLOCKS + MATCH_DIAGNOSTIC_BLOCKS

DEFAULT_CURVE_G = 8


@dataclass(frozen=True)
class LaunchProfile:
    labels: tuple[str, ...]
    strict: np.ndarray  # (n,)
    time: np.ndarray  # (n,) arbitrary units, rank-compared only
    hazard: np.ndarray  # (n, G) P(first break within g)
    recovery: np.ndarray  # (n, G) P(first inherit within r after first break)
    inherit_run: np.ndarray  # (n, G) P(first g divisions all inherited)
    fingerprint: np.ndarray  # (n, F) rank-CDF normalized, side-local


def _rank_cdf_columns(matrix: np.ndarray) -> np.ndarray:
    out = np.empty_like(matrix, dtype=np.float64)
    n = matrix.shape[0]
    for column in range(matrix.shape[1]):
        out[:, column] = (rankdata(matrix[:, column], method="average") - 0.5) / n
    return out


def gard_launch_profile(
    rule_id: int, redux_config: ReduxConfig, curve_g: int = DEFAULT_CURVE_G
) -> LaunchProfile:
    atlas = redux_config.atlas()
    spaces = make_state_spaces(atlas)
    codec = RuleCodec(atlas)
    beta = codec.matrix(rule_id)
    absorption = solve_absorption(rule_id, beta, atlas, spaces)
    kernel = closed_kernel(rule_id, beta, "equal", atlas, spaces, absorption)
    strict = exact_strict_probabilities(kernel, atlas).probabilities
    profile = build_profile(
        rule_id, beta, "equal", redux_config, spaces, strict=strict, absorption=absorption
    )
    launch = profile.launch_rows
    curve_g = min(curve_g, profile.hazard.shape[1])
    last = curve_g - 1
    # EARLY-ONLY matching fingerprint: the dev phase showed that matching on
    # the scored quantities wins trivially, so matching sees only horizons
    # <= 4 and the clock; strict, horizon-G hazard, recovery, and inherit-run
    # stay held out for scoring.
    raw_fingerprint = np.column_stack(
        [
            profile.hazard[:, min(1, last)],
            profile.hazard[:, min(3, last)],
            np.log1p(np.maximum(profile.time[launch], 0.0)),
        ]
    )
    return LaunchProfile(
        labels=tuple(str(tuple(profile.states[i])) for i in launch),
        strict=profile.strict.copy(),
        time=profile.time[launch].copy(),
        hazard=profile.hazard[:, :curve_g].copy(),
        recovery=profile.recovery[:, :curve_g].copy(),
        inherit_run=profile.inherit_run[:, :curve_g].copy(),
        fingerprint=_rank_cdf_columns(raw_fingerprint),
    )


def xeno_launch_profile(
    stats_per_seed: list[SeedStats], curve_g: int = DEFAULT_CURVE_G
) -> LaunchProfile:
    labels, strict, times = [], [], []
    hazard, recovery, inherit_run = [], [], []
    for stats in stats_per_seed:
        labels.append(f"seed{stats.seed_index}")
        strict.append(stats.strict_probability)
        times.append(float(np.median(stats.first_generation_time)))
        broke = stats.first_break >= 0
        hazard.append(
            [float((broke & (stats.first_break < g)).mean()) for g in range(1, curve_g + 1)]
        )
        early_break = broke & (stats.first_break < curve_g)
        if early_break.any():
            lags = stats.first_recovery_lag[early_break]
            recovery.append(
                [float(((lags >= 0) & (lags <= r)).mean()) for r in range(1, curve_g + 1)]
            )
        else:
            recovery.append([0.0] * curve_g)
        inherit_run.append(
            [float((stats.inherit_run_length >= g).mean()) for g in range(1, curve_g + 1)]
        )
    hazard = np.asarray(hazard)
    inherit_run = np.asarray(inherit_run)
    strict = np.asarray(strict)
    times = np.asarray(times)
    raw_fingerprint = np.column_stack(
        [
            hazard[:, min(1, curve_g - 1)],
            hazard[:, min(3, curve_g - 1)],
            np.log1p(np.maximum(times, 0.0)),
        ]
    )
    return LaunchProfile(
        labels=tuple(labels),
        strict=strict,
        time=times,
        hazard=hazard,
        recovery=np.asarray(recovery),
        inherit_run=inherit_run,
        fingerprint=_rank_cdf_columns(raw_fingerprint),
    )


def score_bridge(
    gard: LaunchProfile, xeno: LaunchProfile, coupling: np.ndarray
) -> dict[str, float]:
    """Support-free block subset through a row-stochastic (n_g, n_x) coupling."""
    transported_strict = coupling @ xeno.strict
    transported_time = coupling @ xeno.time
    with np.errstate(divide="raise", over="raise", invalid="raise"):
        return {
            "strict_rank": rank_loss(gard.strict, transported_strict),
            "time_rank": rank_loss(gard.time, transported_time),
            "hazard_rank": rank_loss(gard.hazard[:, -1], coupling @ xeno.hazard[:, -1]),
            "hazard_curve_l1": float(
                np.mean(np.abs(gard.hazard - coupling @ xeno.hazard))
            ),
            "recovery_curve_l1": float(
                np.mean(np.abs(gard.recovery - coupling @ xeno.recovery))
            ),
            "inherit_run_curve_l1": float(
                np.mean(np.abs(gard.inherit_run - coupling @ xeno.inherit_run))
            ),
        }


def behavioral_coupling(
    gard: LaunchProfile, xeno: LaunchProfile, *, permutation: np.ndarray | None = None
) -> np.ndarray:
    """Nearest-fingerprint one-hot coupling (the A3-confirmed family).

    ``permutation`` shuffles the XENO fingerprint rows first — the
    correspondence-destroying null that keeps the matching machinery.
    """
    fingerprint = xeno.fingerprint if permutation is None else xeno.fingerprint[permutation]
    cost = ((gard.fingerprint[:, None, :] - fingerprint[None, :, :]) ** 2).sum(axis=2)
    coupling = np.zeros((len(gard.labels), len(xeno.labels)))
    coupling[np.arange(len(gard.labels)), np.argmin(cost, axis=1)] = 1.0
    return coupling


def occupancy_coupling(gard: LaunchProfile, xeno: LaunchProfile) -> np.ndarray:
    return np.full((len(gard.labels), len(xeno.labels)), 1.0 / len(xeno.labels))


def random_coupling(
    gard: LaunchProfile, xeno: LaunchProfile, rng: np.random.Generator
) -> np.ndarray:
    coupling = np.zeros((len(gard.labels), len(xeno.labels)))
    coupling[np.arange(len(gard.labels)), rng.integers(0, len(xeno.labels), len(gard.labels))] = 1.0
    return coupling


@dataclass(frozen=True)
class BridgeScaler:
    scales: dict

    @classmethod
    def fit(cls, score_dicts: list[dict[str, float]]) -> "BridgeScaler":
        scales = {}
        for name in HELDOUT_BLOCKS:
            values = np.asarray([s[name] for s in score_dicts])
            q25, q75 = np.quantile(values, (0.25, 0.75))
            scale = q75 - q25
            if scale <= 0:
                scale = float(np.median(np.abs(values)))
            scales[name] = float(scale) if scale > 0 else 1.0
        return cls(scales=scales)

    def composite(self, scores: dict[str, float]) -> float:
        return float(np.mean([scores[n] / self.scales[n] for n in HELDOUT_BLOCKS]))


def _bridge_config(base: XenoConfig) -> XenoConfig:
    return replace(base, **BRIDGE_OPERATING_POINT) if base.mode == "full" else base


def run_bridge(
    base_config: XenoConfig,
    *,
    phase: str,
    gard_rules: int = 16,
    n_tables: int = 8,
    futures: int = 512,
    n_random_nulls: int = 64,
    frozen_scaler: dict | None = None,
) -> dict:
    """One bridge phase: 'dev' fits the scaler; 'confirm' applies it frozen."""
    if phase not in ("dev", "confirm"):
        raise ValueError("phase must be 'dev' or 'confirm'")
    started = time.time()
    config = _bridge_config(base_config)
    config.validate()
    chemistry = build_chemistry(config)
    table_tag = (
        config.dev_table_seed_tag if phase == "dev" else config.confirm_table_seed_tag
    )

    redux_config = ReduxConfig.mini() if base_config.mode == "tiny" else ReduxConfig()
    curve_g = min(DEFAULT_CURVE_G, redux_config.curve_horizon, config.strict_horizon)
    atlas = redux_config.atlas()
    codec = RuleCodec(atlas)
    orbit_ids = np.asarray(
        [orbit.canonical_id for orbit in codec.rule_orbits()], dtype=np.int64
    )
    eval_ids = orbit_ids[
        [hash_fraction(redux_config.dev_split_tag, int(r)) >= 0.5 for r in orbit_ids]
    ]
    order = np.argsort(
        [hash_fraction("xeno-bridge-gard-v1", int(r)) for r in eval_ids], kind="stable"
    )
    selected_rules = [int(r) for r in eval_ids[order[:gard_rules]]]
    gard_profiles = {
        r: gard_launch_profile(r, redux_config, curve_g) for r in selected_rules
    }

    xeno_profiles = []
    for table_index in range(n_tables):
        table = sample_table(chemistry, config, seed_rng(table_tag, table_index))
        stats = [
            run_seed(
                table,
                seed_index,
                chemistry,
                config,
                seed_rng(config.trajectory_seed_tag + "-" + phase, table_index, seed_index),
                n_futures=futures,
            )
            for seed_index in range(config.n_seeds)
        ]
        xeno_profiles.append(xeno_launch_profile(stats, curve_g))

    rows = []
    all_scores = []
    for rule_id, gard in gard_profiles.items():
        for table_index, xeno in enumerate(xeno_profiles):
            rng = seed_rng("xeno-bridge-nulls-v1", rule_id, table_index)
            entries = {
                "behavioral": behavioral_coupling(gard, xeno),
                "occupancy": occupancy_coupling(gard, xeno),
                "shuffled": behavioral_coupling(
                    gard, xeno, permutation=rng.permutation(len(xeno.labels))
                ),
            }
            scored = {
                name: score_bridge(gard, xeno, coupling)
                for name, coupling in entries.items()
            }
            random_scores = [
                score_bridge(gard, xeno, random_coupling(gard, xeno, rng))
                for _ in range(n_random_nulls)
            ]
            all_scores.extend(scored.values())
            all_scores.extend(random_scores)
            rows.append(
                {
                    "rule": rule_id,
                    "table": table_index,
                    "scored": scored,
                    "random": random_scores,
                }
            )

    if phase == "dev":
        scaler = BridgeScaler.fit(all_scores)
    else:
        if not frozen_scaler:
            raise ValueError("confirm phase requires the frozen dev scaler")
        scaler = BridgeScaler(scales=dict(frozen_scaler))

    pair_records = []
    for row in rows:
        composites = {name: scaler.composite(s) for name, s in row["scored"].items()}
        random_composites = np.asarray([scaler.composite(s) for s in row["random"]])
        pair_records.append(
            {
                "rule": row["rule"],
                "table": row["table"],
                **composites,
                "random_median": float(np.median(random_composites)),
                "random_percentile_of_behavioral": float(
                    (random_composites < composites["behavioral"]).mean()
                ),
                "beats_occupancy": bool(composites["behavioral"] < composites["occupancy"]),
                "beats_shuffled": bool(composites["behavioral"] < composites["shuffled"]),
                "beats_random_median": bool(
                    composites["behavioral"] < float(np.median(random_composites))
                ),
            }
        )

    beats_occ = np.asarray([p["beats_occupancy"] for p in pair_records])
    beats_shuf = np.asarray([p["beats_shuffled"] for p in pair_records])
    beats_rand = np.asarray([p["beats_random_median"] for p in pair_records])
    percentiles = np.asarray([p["random_percentile_of_behavioral"] for p in pair_records])
    rng = seed_rng("xeno-bridge-boot-v1", len(pair_records))
    draws = rng.integers(0, len(pair_records), size=(4096, len(pair_records)))
    boot_all = (beats_occ & beats_shuf & beats_rand)[draws].mean(axis=1)

    summary = {
        "phase": phase,
        "n_pairs": len(pair_records),
        "beats_occupancy_fraction": float(beats_occ.mean()),
        "beats_shuffled_fraction": float(beats_shuf.mean()),
        "beats_random_median_fraction": float(beats_rand.mean()),
        "beats_all_nulls_fraction": float((beats_occ & beats_shuf & beats_rand).mean()),
        "beats_all_nulls_ci95": [
            float(np.quantile(boot_all, 0.025)),
            float(np.quantile(boot_all, 0.975)),
        ],
        "median_random_percentile": float(np.median(percentiles)),
        "scaler": scaler.scales,
    }
    payload = {
        "config_digest": config.digest(),
        "operating_point": BRIDGE_OPERATING_POINT,
        "gard_rules": selected_rules,
        "n_tables": n_tables,
        "futures": futures,
        "summary": summary,
        "pairs": pair_records,
        "environment": environment_manifest(),
        "elapsed_seconds": time.time() - started,
    }
    out = results_root(base_config)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / f"bridge_{phase}.json", payload)
    return payload
