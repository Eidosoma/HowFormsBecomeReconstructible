"""Outcome-known retained audit for L19's incorruptible-reference claim."""

from __future__ import annotations

from collections import Counter
import csv
import io
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .l17_audit import audit_e55
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E64_injury_clock": "4c99442c230f0b2150a2f7f2699f0f56ad3fd12d85e9b09fd21e8f848beaffc5",
    "E65_teaching": "1f30524f09da9001192f2c9a6b559f63f888c41a14e7a2a93a0a18f72c961ee4",
    "E66_writable_landlord": "9def6662a2533a853811cbbcac8f0a069e35f6d1f9ef57da2f04ff193d63d982",
}

TRACKED_PACKAGES = (
    "injury_clock",
    "teaching",
    "writable_landlord",
    "error_threshold",
    "blueprint_web",
    "voltage_web",
    "setpoint_rewrite",
    "ladder_web",
    "contract_bridge",
    "assimilation",
    "two_headed_final",
)

E64_REGIMES = (
    "injury_fast",
    "injury_mid",
    "injury_slow",
    "static",
    "drift",
)
INJURY_INTERVALS = {
    "injury_fast": 150,
    "injury_mid": 300,
    "injury_slow": 600,
}
E65_WINDOWS = (50, 200, 500)
E65_SIGMAS = (0.1, 0.5, 1.1, 2.4)


def _experiment_root(plastic_root: Path, package: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / package


def _track_package(tracker: InputTracker, root: Path) -> None:
    for relative in ("EXPECTATIONS.md", "pyproject.toml"):
        path = root / relative
        if path.is_file():
            tracker.add(path)
    for directory in ("src", "tests"):
        source = root / directory
        if source.is_dir():
            for path in sorted(source.rglob("*.py")):
                tracker.add(path)


def _read(tracker: InputTracker, path: Path) -> str:
    return tracker.add(path).read_text(encoding="utf-8")


def _recursive_close(left: Any, right: Any) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _recursive_close(left[key], right[key]) for key in left
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            _recursive_close(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return close(float(left), float(right))
    return left == right


def _load_shards(
    root: Path,
    tracker: InputTracker,
    *,
    prefix: str,
    expected_shards: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = [
        root / "results/full/work" / f"{prefix}_{index:02d}_of_{expected_shards:02d}.json"
        for index in range(expected_shards)
    ]
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"shard config digests differ for {prefix}: {digests}")
    return [entry for payload in payloads for entry in payload["entries"]], {
        "n_shards": len(paths),
        "config_digest": next(iter(digests)),
        "n_entries": sum(len(payload["entries"]) for payload in payloads),
        "shard_ids_inferred_from_filenames": list(range(expected_shards)),
        "shard_ids_stored_in_payloads": False,
    }


def _bootstrap_mean_interval(
    values: Sequence[float], *, seed: int, draws: int = 4096
) -> list[float]:
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("cannot bootstrap an empty contrast")
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, data.size, size=(draws, data.size))
    return [float(x) for x in np.quantile(data[picks].mean(axis=1), (0.025, 0.975))]


def _directions(values: Sequence[float], *, tolerance: float = 1e-12) -> dict[str, int]:
    return {
        "positive": sum(float(value) > tolerance for value in values),
        "tied": sum(abs(float(value)) <= tolerance for value in values),
        "negative": sum(float(value) < -tolerance for value in values),
    }


def _contrast(values: Sequence[float], *, seed: int, unit: str) -> dict[str, Any]:
    data = [float(value) for value in values]
    return {
        f"n_{unit}s": len(data),
        "mean_difference": float(np.mean(data)),
        f"{unit}_bootstrap_95": _bootstrap_mean_interval(data, seed=seed),
        "bootstrap_draws": 4096,
        "bootstrap_seed": seed,
        "directions": _directions(data),
        f"{unit}_differences": data,
    }


def _first_commit(repo_root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
        rows = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                "--follow",
                "--format=%H",
                "--",
                str(relative),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None
    return rows[-1] if rows else None


def _git_provenance(
    plastic_root: Path, package_results: Mapping[str, str]
) -> dict[str, Any]:
    try:
        repository_root = Path(
            subprocess.run(
                ["git", "-C", str(plastic_root), "rev-parse", "--show-toplevel"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        repository_root = plastic_root.parent
    packages: dict[str, Any] = {}
    for package, result_name in package_results.items():
        root = _experiment_root(plastic_root, package)
        expectation_commit = _first_commit(repository_root, root / "EXPECTATIONS.md")
        result_commit = _first_commit(repository_root, root / "results/full" / result_name)
        packages[package] = {
            "expectations_first_commit": expectation_commit,
            "selected_result_first_commit": result_commit,
            "same_first_commit_snapshot": (
                expectation_commit is not None and expectation_commit == result_commit
            ),
            "prose_date_is_git_verified_temporal_seal": False,
        }
    return {"repository_root": str(repository_root), "packages": packages}


def source_config_digests() -> dict[str, str]:
    """Digest independently transcribed current E64--E66 defaults."""

    configs: dict[str, dict[str, Any]] = {
        "E64_injury_clock": {
            "mode": "full",
            "population": 10,
            "generations": 16,
            "n_repeats": 5,
            "futures": 2,
            "tournament": 3,
            "rho_range": [0.002, 0.05],
            "cm_range": [0.05, 1.6],
            "rho_init": [0.002, 0.05],
            "cm_init": [0.1, 0.8],
            "mutation_sigma": 0.3,
            "n_insults": 4,
            "score_lag": 150,
            "displacement_frac": 0.25,
            "burn_in_taus": 3,
            "burn_in_cap": 1500,
            "consensus_seeds": 4,
            "consensus_settle": 300,
            "audit_generations": [5, 10, 15],
            "audit_members": 3,
            "solvable_bar": 0.6,
            "trajectory_seed_tag": "injury-clock-v1",
        },
        "E65_teaching": {
            "mode": "full",
            "n_tissues": 4,
            "futures": 8,
            "settle_sweeps": 120,
            "render_sweeps": 500,
            "cycles": 12,
            "free_sweeps": 1000,
            "teach_hold": 1.2,
            "amp_threshold": 0.2,
            "barcode_cycle": 4,
            "barcode_side": 4,
            "trajectory_seed_tag": "teaching-v1",
        },
        "E66_writable_landlord": {
            "mode": "full",
            "n_tissues": 4,
            "futures": 6,
            "settle_sweeps": 120,
            "imprint_sweeps": 1000,
            "imprint_hold": 1.2,
            "cycles": 12,
            "inter_fission": 1000,
            "amp_threshold": 0.2,
            "capacity_settle": 300,
            "capacity_bar": 0.8,
            "pullback_zap_sweeps": 8,
            "pullback_window": 50,
            "consensus_launches": 4,
            "consensus_settle": 300,
            "repertoire_seeds": 8,
            "repertoire_distinct": 0.8,
            "zap_recover": 300,
            "imprint_gate_cycles": 8,
            "imprint_gate_bar": 0.75,
            "trajectory_seed_tag": "writable-landlord-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def _audit_e64(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="injury_shard", expected_shards=8
    )
    summary = tracker.json(root / "results/full/injury_summary.json")
    corner_payload = tracker.json(root / "results/full/work/corner_table.json")
    source = _read(tracker, root / "src/injury_clock/pipeline.py")
    keys = [(entry["regime"], int(entry["repeat"])) for entry in entries]
    expected = {
        (regime, repeat) for regime in E64_REGIMES for repeat in range(5)
    }
    trajectory_ok = all(
        [int(row["gen"]) for row in entry["trajectory"]] == list(range(16))
        for entry in entries
    )
    audit_ok = all(
        ([int(row["gen"]) for row in entry["audits"]] == [5, 10, 15])
        if entry["regime"] != "drift"
        else not entry["audits"]
        for entry in entries
    )
    integrity.update(
        {
            "complete_regime_repeat_grid": set(keys) == expected,
            "no_duplicate_regime_repeat_rows": len(keys) == len(set(keys)),
            "sixteen_generations_each": trajectory_ok,
            "declared_audit_generations_complete": audit_ok,
            "corner_digest_matches_shards": (
                corner_payload["config_digest"] == integrity["config_digest"]
            ),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def med(regime: str, key: str) -> float:
        return float(np.median([entry[key] for entry in entries if entry["regime"] == regime]))

    def audit_final(regime: str) -> float | None:
        values = [
            row["live_minus_knife"]
            for entry in entries
            if entry["regime"] == regime
            for row in entry["audits"]
            if row["gen"] == 15
        ]
        return float(np.mean(values)) if values else None

    corner = corner_payload["table"]
    rho_mid = med("injury_mid", "median_rho")
    rho_static = med("static", "median_rho")
    mid_audit = audit_final("injury_mid")
    resonance = {
        regime: med(regime, "median_rho")
        for regime in ("injury_fast", "injury_mid", "injury_slow")
    }
    calculated = {
        "corner_table": corner,
        "medians": {
            regime: {
                "rho": med(regime, "median_rho"),
                "cm": med(regime, "median_cm"),
            }
            for regime in E64_REGIMES
        },
        "population_audit_live_minus_knife": {
            regime: audit_final(regime)
            for regime in ("injury_fast", "injury_mid", "injury_slow", "static")
        },
        "resonance_rho": resonance,
        "rho_at_box_floor": bool(rho_mid <= 0.002 * 1.2),
        "gate_p64_1_primary": bool(
            rho_mid <= 0.005
            and rho_mid < 0.5 * rho_static
            and mid_audit is not None
            and mid_audit > 0.1
        ),
        "gate_p64_2_resonance": bool(
            resonance["injury_mid"] <= resonance["injury_fast"]
            and resonance["injury_mid"] <= resonance["injury_slow"]
        ),
        "failure_reading": (
            "landlord-assisted (rho drops, live-knife ~0) — FAILS"
            if rho_mid <= 0.005 and (mid_audit or 0) <= 0.1
            else None
        ),
    }

    repeat_rows: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda item: (E64_REGIMES.index(item["regime"]), item["repeat"])):
        trajectory = entry["trajectory"]
        audits = {int(row["gen"]): float(row["live_minus_knife"]) for row in entry["audits"]}
        interval = INJURY_INTERVALS.get(entry["regime"], 300)
        repeat_rows.append(
            {
                "regime": entry["regime"],
                "repeat": int(entry["repeat"]),
                "selection_interval": interval,
                "selection_has_displacement": entry["regime"].startswith("injury"),
                "selection_score_lag": 150 if entry["regime"] != "drift" else None,
                "initial_median_rho": float(trajectory[0]["median_rho"]),
                "final_median_rho": float(entry["median_rho"]),
                "rho_change": float(entry["median_rho"] - trajectory[0]["median_rho"]),
                "final_tau_reciprocal_rho": float(1.0 / entry["median_rho"]),
                "initial_median_cm": float(trajectory[0]["median_cm"]),
                "final_median_cm": float(entry["median_cm"]),
                "cm_change": float(entry["median_cm"] - trajectory[0]["median_cm"]),
                "champion_rho": float(entry["champion"]["rho"]),
                "champion_cm": float(entry["champion"]["cm"]),
                "audit_gen5": audits.get(5),
                "audit_gen10": audits.get(10),
                "audit_gen15": audits.get(15),
            }
        )

    corner_rows = [dict(row) for row in corner["rows"]]
    by_regime = {
        regime: sorted(
            [row for row in repeat_rows if row["regime"] == regime],
            key=lambda row: row["repeat"],
        )
        for regime in E64_REGIMES
    }
    regime_summary: dict[str, Any] = {}
    for regime in E64_REGIMES:
        rows = by_regime[regime]
        final_rho = med(regime, "median_rho")
        interval = INJURY_INTERVALS.get(regime)
        regime_summary[regime] = {
            "median_initial_rho": float(np.median([row["initial_median_rho"] for row in rows])),
            "median_final_rho": final_rho,
            "tau_from_median_final_rho": float(1.0 / final_rho),
            "mean_within_repeat_rho_change": float(np.mean([row["rho_change"] for row in rows])),
            "rho_change_directions": _directions([row["rho_change"] for row in rows]),
            "injury_interval": interval,
            "interval_times_median_rho": (
                float(interval * final_rho) if interval is not None else None
            ),
            "interval_over_five": float(interval / 5) if interval is not None else None,
            "tau_relative_error_from_interval_over_five": (
                float((1.0 / final_rho - interval / 5) / (interval / 5))
                if interval is not None
                else None
            ),
        }

    def paired_difference(left: str, right: str) -> list[float]:
        return [
            by_regime[left][index]["final_median_rho"]
            - by_regime[right][index]["final_median_rho"]
            for index in range(5)
        ]

    injury_taus = np.asarray(
        [regime_summary[regime]["tau_from_median_final_rho"] for regime in INJURY_INTERVALS],
        dtype=float,
    )
    interval_values = np.asarray(list(INJURY_INTERVALS.values()), dtype=float)
    slope = float(np.polyfit(np.log(interval_values), np.log(injury_taus), 1)[0])
    clock = {
        "aggregate_rho_strictly_decreases_with_interval": bool(
            resonance["injury_fast"] > resonance["injury_mid"] > resonance["injury_slow"]
        ),
        "aggregate_tau_strictly_increases_with_interval": bool(
            injury_taus[0] < injury_taus[1] < injury_taus[2]
        ),
        "three_point_rank_correlation": 1.0,
        "three_point_log_log_slope_tau_on_interval": slope,
        "proportional_law_slope_would_be": 1.0,
        "interval_times_rho_values": [
            regime_summary[regime]["interval_times_median_rho"]
            for regime in INJURY_INTERVALS
        ],
        "tau_within_20_percent_of_interval_over_five": sum(
            abs(regime_summary[regime]["tau_relative_error_from_interval_over_five"]) <= 0.2
            for regime in INJURY_INTERVALS
        ),
        "fast_minus_mid_rho": _contrast(
            paired_difference("injury_fast", "injury_mid"),
            seed=20260903194,
            unit="repeat",
        ),
        "mid_minus_slow_rho": _contrast(
            paired_difference("injury_mid", "injury_slow"),
            seed=20260903195,
            unit="repeat",
        ),
        "fast_minus_slow_rho": _contrast(
            paired_difference("injury_fast", "injury_slow"),
            seed=20260903196,
            unit="repeat",
        ),
        "strict_fast_gt_mid_gt_slow_repeat_count": sum(
            by_regime["injury_fast"][index]["final_median_rho"]
            > by_regime["injury_mid"][index]["final_median_rho"]
            > by_regime["injury_slow"][index]["final_median_rho"]
            for index in range(5)
        ),
        "repeat_indices_share_tissue_index_but_not_rng_or_founder_population": True,
    }

    objective = {
        "fitness_target": "each insult's immediate pre-state",
        "fitness_target_age_at_score_sweeps": 150,
        "fitness_target_age_varied_across_injury_regimes": False,
        "injury_recurrence_interval_varied": True,
        "total_post_burn_evaluation_sweeps": {str(value): 4 * value for value in INJURY_INTERVALS.values()},
        "unscored_post_score_sweeps_per_insult": {str(value): value - 150 for value in INJURY_INTERVALS.values()},
        "distant_ancestor_fitness_arm_implemented": False,
        "ancestor_referenced_secondary_promised_in_register": True,
        "discovery_log_explicitly_says_ancestor_experiment_not_run": True,
        "static_selection_displaces_V": False,
        "static_selection_still_scores_150_sweep_immediate_pre_state_retention": True,
        "population_audit_for_static_injects_injuries_despite_static_selection": True,
        "selection_and_audit_semantics_match_for_static": False,
        "dissonant_spatial_mask": "left half",
        "registered_label": "quarter cells",
        "displacement_distance": "one quarter of sheet width",
        "mask_is_quarter_of_cells": False,
        "audit_samples_random_population_members_not_champion": True,
        "live_and_knife_audits_use_distinct_random_streams": True,
        "source_checks": {
            "immediate_pre_state": "pre = V.copy()" in source,
            "fixed_score_lag": "sweep == config.score_lag - 1" in source,
            "left_half_mask": "q[:, : tissue.width // 2] = True" in source,
            "static_audit_forces_insults": "with_insults=True" in source,
        },
    }
    deviations = {
        "wave14_registered_repeats": 6,
        "implemented_repeats": 5,
        "wave14_registered_dimensions": [32, 32],
        "implemented_dimensions": [16, 16],
        "wave14_registered_burn_in": "at least 3 tau_max",
        "implemented_burn_in": "min(1500, int(3/rho_candidate))",
        "ancestor_referenced_secondary_implemented": False,
        "quenched_swap_injury_arm_implemented": False,
        "champion_transport_probe_implemented": False,
    }
    return {
        "integrity": integrity,
        "retained_config_digest": integrity["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, summary["gates"]
        ),
        "regime_summary": regime_summary,
        "clock_association": clock,
        "objective_audit": objective,
        "register_implementation_deviations": deviations,
    }, repeat_rows, corner_rows


def _e65_regular_rows(
    entries: Sequence[Mapping[str, Any]],
    *,
    arm: str,
    T: int,
    r_mode: str = "free",
    sigma_r: float = 0.0,
) -> list[Mapping[str, Any]]:
    return sorted(
        [
            entry
            for entry in entries
            if entry["arm"] == arm
            and int(entry["T"]) == T
            and entry["r_mode"] == r_mode
            and close(float(entry["sigma_r"]), sigma_r)
            and entry["barcode"] is None
        ],
        key=lambda entry: int(entry["tissue"]),
    )


def barcode_observer_geometry(height: int, width: int, side: int) -> dict[str, Any]:
    """Reproduce the shapes induced by E65's Boolean-index barcode observer."""

    patch = np.zeros((height, width), dtype=bool)
    patch[2 : 2 + side, 2 : 2 + side] = True
    target = np.zeros((height, width), dtype=bool)[patch]
    try:
        reported_shape = list(np.broadcast_shapes((height, width), target.shape))
        compatible = True
    except ValueError:
        reported_shape = None
        compatible = False
    return {
        "sheet_shape": [height, width],
        "patch_shape": [side, side],
        "boolean_extracted_target_shape": list(target.shape),
        "reported_comparison_shape_after_broadcast": reported_shape,
        "broadcast_compatible": compatible,
        "reported_positions_scored_per_lineage": (
            int(np.prod(reported_shape)) if reported_shape is not None else None
        ),
        "intended_patch_positions": int(patch.sum()),
    }


def _audit_e65(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="teach_shard", expected_shards=6
    )
    summary = tracker.json(root / "results/full/teaching_summary.json")
    source = _read(tracker, root / "src/teaching/pipeline.py")
    signatures = [
        (
            int(entry["tissue"]),
            entry["arm"],
            int(entry["T"]),
            entry["r_mode"],
            float(entry["sigma_r"]),
            entry["barcode"] is not None,
        )
        for entry in entries
    ]
    per_tissue = Counter(signature[0] for signature in signatures)
    integrity.update(
        {
            "summary_digest_matches_shards": summary["config_digest"] == integrity["config_digest"],
            "sixty_entries": len(entries) == 60,
            "fifteen_entries_per_tissue": dict(per_tissue) == {0: 15, 1: 15, 2: 15, 3: 15},
            "no_duplicate_tissue_arm_configuration_rows": len(signatures) == len(set(signatures)),
        }
    )

    def values(arm: str, T: int, r_mode: str = "free", sigma_r: float = 0.0) -> list[float]:
        return [
            float(row["fidelity"])
            for row in _e65_regular_rows(
                entries, arm=arm, T=T, r_mode=r_mode, sigma_r=sigma_r
            )
        ]

    def mean_fid(arm: str, T: int, r_mode: str = "free", sigma_r: float = 0.0) -> float:
        return float(np.mean(values(arm, T, r_mode, sigma_r)))

    floor_values = values("none", 0)
    floor = float(np.mean(floor_values))
    floor_q95 = float(floor + 1.645 * np.std(floor_values))
    parent = {str(T): mean_fid("parent_chain", T) for T in E65_WINDOWS}
    broadcast = {str(T): mean_fid("broadcast", T) for T in E65_WINDOWS}
    random_200 = mean_fid("random", 200)
    reset_200 = mean_fid("parent_chain", 200, r_mode="reset")

    parent_200_rows = _e65_regular_rows(entries, arm="parent_chain", T=200)
    broadcast_200_rows = _e65_regular_rows(entries, arm="broadcast", T=200)
    divergence_parent = float(np.mean([row["divergence"] for row in parent_200_rows]))
    divergence_broadcast = float(np.mean([row["divergence"] for row in broadcast_200_rows]))
    barcode_parent_rows = sorted(
        [entry for entry in entries if entry["arm"] == "parent_chain" and entry["barcode"] is not None],
        key=lambda entry: int(entry["tissue"]),
    )
    barcode_broadcast_rows = sorted(
        [entry for entry in entries if entry["arm"] == "broadcast" and entry["barcode"] is not None],
        key=lambda entry: int(entry["tissue"]),
    )

    def barcode_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
        return {
            "own": float(np.mean([row["barcode"]["own_lineage"] for row in rows])),
            "others": float(np.mean([row["barcode"]["other_lineages"] for row in rows])),
        }

    bar_parent = barcode_summary(barcode_parent_rows)
    bar_broadcast = barcode_summary(barcode_broadcast_rows)
    barcode_propagates = bar_parent["own"] > bar_parent["others"] + 0.1
    eigen = {str(sigma): mean_fid("parent_chain", 200, sigma_r=sigma) for sigma in E65_SIGMAS}
    calculated = {
        "floor": floor,
        "floor_q95": floor_q95,
        "parent_chain": parent,
        "broadcast": broadcast,
        "random_teacher": random_200,
        "r_reset": reset_200,
        "divergence": {
            "parent_chain": divergence_parent,
            "broadcast": divergence_broadcast,
        },
        "barcode": {
            "parent_chain": bar_parent,
            "broadcast": bar_broadcast,
        },
        "eigen_sweep": eigen,
        "gate_p65_1_primary": bool(
            parent["200"] > floor_q95
            and divergence_parent > divergence_broadcast
            and barcode_propagates
        ),
        "gate_p65_2_parent_beats_random": bool(parent["200"] > random_200),
        "instruction_not_culture": bool(
            broadcast["200"] > floor_q95 and not barcode_propagates
        ),
    }

    rows_out: list[dict[str, Any]] = []
    for entry in sorted(
        entries,
        key=lambda item: (
            int(item["tissue"]),
            item["arm"],
            int(item["T"]),
            item["r_mode"],
            float(item["sigma_r"]),
            item["barcode"] is not None,
        ),
    ):
        barcode = entry["barcode"]
        rows_out.append(
            {
                "tissue": int(entry["tissue"]),
                "arm": entry["arm"],
                "T": int(entry["T"]),
                "r_mode": entry["r_mode"],
                "sigma_r": float(entry["sigma_r"]),
                "barcode_run": barcode is not None,
                "fidelity": float(entry["fidelity"]),
                "divergence": float(entry["divergence"]),
                "barcode_own_lineage": None if barcode is None else float(barcode["own_lineage"]),
                "barcode_other_lineages": None if barcode is None else float(barcode["other_lineages"]),
            }
        )

    def paired(left: Sequence[float], right: Sequence[float], seed: int) -> dict[str, Any]:
        return _contrast(
            [float(a - b) for a, b in zip(left, right)], seed=seed, unit="tissue"
        )

    comparisons: dict[str, Any] = {}
    for offset, T in enumerate(E65_WINDOWS):
        comparisons[str(T)] = {
            "broadcast_minus_floor": paired(values("broadcast", T), floor_values, 20260903197 + offset),
            "parent_minus_floor": paired(values("parent_chain", T), floor_values, 20260903200 + offset),
            "broadcast_minus_parent": paired(
                values("broadcast", T), values("parent_chain", T), 20260903203 + offset
            ),
        }
    comparisons["broadcast_dose"] = {
        "200_minus_50": paired(values("broadcast", 200), values("broadcast", 50), 20260903206),
        "500_minus_200": paired(values("broadcast", 500), values("broadcast", 200), 20260903207),
        "500_minus_50": paired(values("broadcast", 500), values("broadcast", 50), 20260903208),
    }
    comparisons["parent_dose"] = {
        "200_minus_50": paired(values("parent_chain", 200), values("parent_chain", 50), 20260903209),
        "500_minus_200": paired(values("parent_chain", 500), values("parent_chain", 200), 20260903210),
        "500_minus_50": paired(values("parent_chain", 500), values("parent_chain", 50), 20260903211),
    }
    comparisons["parent_minus_random_200"] = paired(
        values("parent_chain", 200), values("random", 200), 20260903212
    )
    comparisons["reset_minus_free_parent_200"] = paired(
        values("parent_chain", 200, r_mode="reset"),
        values("parent_chain", 200),
        20260903213,
    )
    comparisons["parent_minus_broadcast_divergence_200"] = paired(
        [float(row["divergence"]) for row in parent_200_rows],
        [float(row["divergence"]) for row in broadcast_200_rows],
        20260903214,
    )

    actual_geometry = barcode_observer_geometry(16, 16, 4)
    registered_geometry = barcode_observer_geometry(32, 32, 4)
    barcode_geometry = {
        "actual_sheet_shape": actual_geometry["sheet_shape"],
        "patch_shape": actual_geometry["patch_shape"],
        "boolean_extracted_target_shape": actual_geometry[
            "boolean_extracted_target_shape"
        ],
        "reported_comparison_shape_after_broadcast": actual_geometry[
            "reported_comparison_shape_after_broadcast"
        ],
        "reported_positions_scored_per_lineage": actual_geometry[
            "reported_positions_scored_per_lineage"
        ],
        "intended_patch_positions": actual_geometry["intended_patch_positions"],
        "reported_to_intended_position_ratio": 16.0,
        "reported_score_is_patch_restricted": False,
        "silent_broadcast_requires_width_equal_patch_area": True,
        "registered_32_by_32_shape_would_be_compatible": registered_geometry[
            "broadcast_compatible"
        ],
        "cycles_after_injection_before_only_barcode_score": 7,
        "one_reteaching_cycle_barcode_score_retained": False,
        "validated_barcode_positive_control_present": False,
        "reported_parent_own_minus_others": bar_parent["own"] - bar_parent["others"],
        "reported_broadcast_own_minus_others": bar_broadcast["own"] - bar_broadcast["others"],
        "reported_values_admissible_for_patch_propagation": False,
        "source_checks": {
            "target_boolean_extract": "target = -flipped[patch]" in source,
            "whole_array_comparison": "((V[0] > 0) == (target > 0)).mean()" in source,
        },
    }
    intervention = {
        "broadcast_template_source": "each future's own frozen founder sign field",
        "broadcast_template_external_to_lineage_dynamics": True,
        "single_common_template_for_all_futures": False,
        "broadcast_reapplied_after_every_fission": True,
        "teacher_clamps_entire_sheet_every_teaching_sweep": True,
        "broadcast_withdrawal_arm_present": False,
        "broadcast_alone_transmitted_by_organism": False,
        "R_copied_whole_at_fission": True,
        "r_reset_restores_post_fission_pre_teaching_R_at_release": True,
        "r_reset_removes_R_during_teaching": False,
        "r_reset_turns_off_R_to_V_feedback_during_teaching": False,
        "c_m_zero_gap_closure_arm_present": False,
        "arms_use_common_random_numbers": False,
        "source_floor_q95_formula": "mean(four tissue floors) + 1.645 * population SD(four tissue floors)",
        "source_floor_q95_is_empirical_matched_null_quantile": False,
        "parent_200_exceeds_source_floor_q95": parent["200"] > floor_q95,
        "parent_200_minus_source_floor_q95": parent["200"] - floor_q95,
        "source_primary_fidelity_clause_passes": parent["200"] > floor_q95,
        "source_primary_divergence_clause_passes": divergence_parent > divergence_broadcast,
        "source_primary_barcode_clause_passes": barcode_propagates,
        "registered_three_class_diagnostic_implemented": False,
        "divergence_ordering_substituted": True,
        "registered_R_parent_correlation_manipulation_check_retained": False,
        "registered_AIC_sigmoid_vs_linear_test_implemented": False,
        "random_teacher_alignment_statistic_retained": False,
    }
    deviations = {
        "wave14_registered_dimensions": [32, 32],
        "implemented_dimensions": [16, 16],
        "wave14_sigma_zero_listed": True,
        "implemented_sigma_zero_represented_by_base_parent_arm": True,
        "three_class_diagnostic_implemented": False,
        "R_parent_correlation_manipulation_check_implemented": False,
        "c_m_knife_gap_closure_implemented": False,
        "AIC_threshold_model_implemented": False,
    }
    return {
        "integrity": integrity,
        "retained_config_digest": integrity["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(calculated, summary["gates"]),
        "paired_tissue_comparisons": comparisons,
        "barcode_observer_audit": barcode_geometry,
        "intervention_and_null_audit": intervention,
        "register_implementation_deviations": deviations,
    }, rows_out


def _audit_e66(root: Path, tracker: InputTracker, assimilation_source: str) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/landlord_summary.json")
    source = _read(tracker, root / "src/writable_landlord/pipeline.py")
    gates = summary["gates"]
    capacity = gates["capacity"]
    chosen = next((row["norm"] for row in capacity["rows"] if row["pin"] >= 0.8), None)
    gain = gates["gain_match"]
    gain_choice = min(gain["rows"], key=lambda row: abs(row["rate"] - gain["writable_rate"]))
    fidelity = gates["fidelity"]
    freedom = gates["freedom_cost"]
    transplant = gates["transplant"]
    f_delta = float(fidelity["writable_fast"] - fidelity["gain_matched"])
    freedom_delta = float(freedom["writable_fast"] - freedom["gain_matched"])
    work = root / "results/full/work"
    lower_files = sorted(path for path in work.rglob("*") if path.is_file()) if work.is_dir() else []
    return {
        "retained_config_digest": summary["config_digest"],
        "aggregate_summary": gates,
        "capacity_recalculation": {
            "chosen_norm": chosen,
            "matches_reported": chosen == capacity["chosen"] == gates["norm"],
            "pin_at_chosen": next(row["pin"] for row in capacity["rows"] if row["norm"] == chosen),
            "one_tissue": True,
            "four_nested_futures": True,
            "metric": "whole-sheet sign agreement without amplitude threshold",
            "static_engineered_target_alignment": True,
            "acquisition_or_lineage_test": False,
        },
        "gain_match_recalculation": {
            "recalculated_nearest_cm": gain_choice["c_m"],
            "matches_reported": gain_choice["c_m"] == gain["matched_cm"],
            "writable_rate": gain["writable_rate"],
            "matched_rate": gain_choice["rate"],
            "absolute_rate_gap": abs(gain_choice["rate"] - gain["writable_rate"]),
            "relative_rate_gap": abs(gain_choice["rate"] - gain["writable_rate"]) / abs(gain["writable_rate"]),
            "matched_cm_equals_native_default": close(gain_choice["c_m"], 0.2),
            "one_tissue_one_stream_per_condition": True,
            "nested_futures_per_condition": 4,
            "match_is_one_50_sweep_pullback_assay_not_all_lineage_restoring_force": True,
            "configured_pullback_zap_sweeps_used_by_measurement": False,
        },
        "aggregate_effects": {
            "writable_fast_minus_gain_matched_fidelity": f_delta,
            "writable_fast_minus_frozen_fidelity": float(fidelity["writable_fast"] - fidelity["frozen"]),
            "writable_slow_minus_gain_matched_fidelity": float(fidelity["writable_slow"] - fidelity["gain_matched"]),
            "writable_fast_minus_writable_slow_fidelity": float(fidelity["writable_fast"] - fidelity["writable_slow"]),
            "writable_fast_minus_gain_matched_freedom": freedom_delta,
            "freedom_tolerance": -0.05,
            "freedom_clause_slack": float(freedom_delta + 0.05),
            "fast_absolute_transplant_margin": float(transplant["writable_fast"]),
            "slow_absolute_transplant_margin": float(transplant["writable_slow"]),
            "frozen_absolute_transplant_margin": float(transplant["frozen"]),
            "gain_matched_absolute_transplant_margin": float(transplant["gain_matched"]),
            "fast_minus_frozen_transplant_margin": float(transplant["writable_fast"] - transplant["frozen"]),
            "fast_minus_gain_matched_transplant_margin": float(transplant["writable_fast"] - transplant["gain_matched"]),
            "fast_margin_above_absolute_0_1_gate": float(transplant["writable_fast"] - 0.1),
            "frozen_margin_as_fraction_of_fast_margin": float(transplant["frozen"] / transplant["writable_fast"]),
            "imprint_shot_minus_registered_bar": float(gates["imprint_shot_fidelity"] - 0.75),
        },
        "timescale_and_update_audit": {
            "rho": 0.002,
            "R_raw_reciprocal_update_clock": 500.0,
            "writable_fast_lambda": 0.001,
            "writable_slow_lambda": 0.0002,
            "fast_lambda_over_rho": 0.5,
            "slow_lambda_over_rho": 0.1,
            "fast_raw_reciprocal_update_clock": 1000.0,
            "slow_raw_reciprocal_update_clock": 5000.0,
            "theta_to_R_raw_clock_ratios": {"writable_fast": 2.0, "writable_slow": 10.0},
            "theta_projected_to_fixed_norm_after_every_update": True,
            "raw_EMA_clock_is_complete_frequency_or_noise_response_measurement": False,
            "layer_cleanliness_or_copy_error_directly_measured": False,
            "writable_fast_fidelity_exceeds_writable_slow": fidelity["writable_fast"] > fidelity["writable_slow"],
            "source_checks": {
                "update_from_R": "lam * np.tanh(Rf)" in source,
                "norm_projection": "theta = project_theta" in source,
            },
        },
        "inheritance_and_control_audit": {
            "theta_is_per_future": True,
            "fission_function_arguments_include_theta": False,
            "theta_persists_unchanged_across_fission_call_then_resumes_updating": True,
            "theta_copy_noise_or_reset_factorial_present": False,
            "branching_parent_daughter_copy_assayed": False,
            "R_is_whole_array_copied": "Rf.copy()" in assimilation_source,
            "writable_initial_theta_is_norm_projected": True,
            "frozen_and_gain_matched_initial_theta_is_unprojected_native": True,
            "writable_and_controls_have_identical_initial_theta_preprocessing": False,
            "registered_written_theta_reseeded_VR_swap_present": False,
            "registered_virgin_theta_kept_VR_swap_present": False,
            "only_cross_lineage_transplant_component_present": True,
        },
        "transplant_audit": {
            "tissues_retained": 1,
            "donor_theta_fields": 2,
            "fresh_recipient_futures_per_donor": 2,
            "component_match_A_and_match_B_retained": False,
            "only_aggregate_symmetric_margin_retained": True,
            "group_A_and_group_B_use_common_recipient_random_stream": False,
            "frozen_identical_theta_negative_control_margin": float(transplant["frozen"]),
            "primary_gate_compares_fast_margin_to_frozen_margin": False,
            "primary_gate_uses_absolute_margin_over_0_1": True,
            "replicate_variance_or_interval_available": False,
            "robust_lineage_content_proven": False,
        },
        "primary_gate_retention_audit": {
            "reported_gate": gates["gate_p66_1_primary"],
            "frozen_tissue_spread_used_by_gate_retained": False,
            "maximum_spread_compatible_with_reported_fidelity_clause": f_delta / 1.645,
            "full_gate_independently_reconstructable": False,
            "visible_freedom_clause_passes": freedom_delta >= -0.05,
            "visible_absolute_transplant_clause_passes": transplant["writable_fast"] > 0.1,
        },
        "retention": {
            "lower_level_files": [str(path.relative_to(root)) for path in lower_files],
            "lineage_tissue_rows_retained": False,
            "capacity_future_rows_retained": False,
            "gain_match_future_rows_retained": False,
            "transplant_components_retained": False,
            "retained_resolution": "aggregate summary only",
            "evidence_level": "E2",
        },
        "register_implementation_deviations": {
            "wave14_registered_dimensions": [32, 32],
            "implemented_dimensions": [16, 16],
            "wave14_registered_lambda_fractions": [0.1, 0.02],
            "implemented_lambda_fractions": [0.5, 0.1],
            "lambda_change_described_in_current_expectations": True,
            "registered_three_way_swap_fully_implemented": False,
            "registered_consensus_correlation_secondary_implemented": False,
            "registered_end_of_run_knife_pair_implemented": False,
        },
    }


def _architecture_inventory(e55: Mapping[str, Any]) -> list[dict[str, Any]]:
    exact = e55["exact_copy_channel"]
    return [
        {
            "experiment": "E64",
            "arm": "injury intervals 150/300/600",
            "form_source": "immediate pre-insult V",
            "candidate_reference": "R with evolved rho/c_m; native fixed theta",
            "fission_treatment": "none",
            "endpoint": "150-sweep dissonant-cell retention",
            "result": "aggregate median rho ordered with interval",
            "decisive_limit": "target age fixed; this is parameter, not architecture, search",
        },
        {
            "experiment": "E64",
            "arm": "static",
            "form_source": "immediate pre-state V",
            "candidate_reference": "R with evolved rho/c_m; native fixed theta",
            "fission_treatment": "none",
            "endpoint": "150-sweep retention without displacement",
            "result": "slowest aggregate median rho",
            "decisive_limit": "different objective; no ancestry target",
        },
        {
            "experiment": "E65",
            "arm": "parent chain",
            "form_source": "previous cycle's live V",
            "candidate_reference": "living teacher plus exactly copied R",
            "fission_treatment": "half V retained; all R copied",
            "endpoint": "fixed-founder fidelity over 12 cycles",
            "result": "0.507/0.507/0.512 at T=50/200/500",
            "decisive_limit": "small finite implementation; barcode observer invalid",
        },
        {
            "experiment": "E65",
            "arm": "broadcast",
            "form_source": "externally frozen per-future founder",
            "candidate_reference": "outside simulation lineage",
            "fission_treatment": "full V overwritten after every fission",
            "endpoint": "fixed-founder fidelity over 12 cycles",
            "result": "0.559/0.637/0.689; monotone in all four tissues",
            "decisive_limit": "repeated instruction, not organism-carried heredity",
        },
        {
            "experiment": "E65",
            "arm": "random teacher / R reset / R noise",
            "form_source": "settled alternate or parent",
            "candidate_reference": "small teacher/control menu",
            "fission_treatment": "half V retained; all R copied before manipulation",
            "endpoint": "fixed-founder fidelity",
            "result": "control means near 0.48-0.51",
            "decisive_limit": "no consensus/error-corrected culture or broadcast withdrawal",
        },
        {
            "experiment": "E66",
            "arm": "writable fast/slow",
            "form_source": "1000-sweep full-body imprint through V then R",
            "candidate_reference": "theta <- projected EMA of tanh(R)",
            "fission_treatment": "theta array persists; half V and all R copied",
            "endpoint": "fixed-target tail fidelity over 12 cycles",
            "result": "aggregate 0.603/0.600",
            "decisive_limit": "one engineered cascade; no lower lineage rows or copy-noise arm",
        },
        {
            "experiment": "E66",
            "arm": "frozen / gain matched",
            "form_source": "same initial imprint, theta not writable",
            "candidate_reference": "native frozen theta; c_m grid match",
            "fission_treatment": "half V and all R copied",
            "endpoint": "fixed-target tail fidelity over 12 cycles",
            "result": "aggregate 0.480/0.484",
            "decisive_limit": "gain match is one early pullback scalar, not architecture exhaustion",
        },
        {
            "experiment": "E55",
            "arm": "sigma-zero exact R copy",
            "form_source": "rolling parent V/R; no refreshed instance template",
            "candidate_reference": "whole copied R plus generic native theta",
            "fission_treatment": "half V retained; all R copied",
            "endpoint": "rolling-parent versus fixed-founder similarity",
            "result": f"parent {exact['generation_10_to_12_immediate_parent_mean']:.6f}; founder {exact['generation_10_to_12_strict_ancestor_mean']:.6f}",
            "decisive_limit": "counterexample only if rolling continuity counts as heritable instance anatomy",
        },
    ]


def run_l19_audit(
    plastic_root: Path, workspace: Path
) -> tuple[
    dict[str, Any],
    list[Path],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[Path, str],
]:
    tracker = InputTracker()
    ideas_root = plastic_root / IDEAS_RELATIVE
    narrative = (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas_root / "LAWS.md",
        ideas_root / "WAVE14_PROPHECIES.md",
        ideas_root / "WAVE14_DESIGN_REVIEW.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        workspace / "SOURCE_BASELINE.md",
        workspace / "REVIEW_PROTOCOL.md",
        workspace / "protocols/L19_INCORRUPTIBLE_REFERENCE_AUDIT_V1.md",
        workspace / "laws/L19_incorruptible_reference.md",
        workspace / "reviews/L17_DEVELOPMENT_HEREDITY_AUDIT_2026-09-03.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    e64, e64_rows, corner_rows = _audit_e64(
        _experiment_root(plastic_root, "injury_clock"), tracker
    )
    e65, e65_rows = _audit_e65(
        _experiment_root(plastic_root, "teaching"), tracker
    )
    assimilation_source = _read(
        tracker,
        _experiment_root(plastic_root, "assimilation") / "src/assimilation/pipeline.py",
    )
    e66 = _audit_e66(
        _experiment_root(plastic_root, "writable_landlord"),
        tracker,
        assimilation_source,
    )
    e55, _e55_curve_rows, _e55_generation_rows = audit_e55(
        _experiment_root(plastic_root, "error_threshold"), tracker
    )

    source_digests = source_config_digests()
    retained_digests = {
        "E64_injury_clock": e64["retained_config_digest"],
        "E65_teaching": e65["retained_config_digest"],
        "E66_writable_landlord": e66["retained_config_digest"],
    }
    digest_matches = {
        name: source_digests[name]
        == retained_digests[name]
        == EXPECTED_CONFIG_DIGESTS[name]
        for name in EXPECTED_CONFIG_DIGESTS
    }
    provenance = _git_provenance(
        plastic_root,
        {
            "injury_clock": "injury_summary.json",
            "teaching": "teaching_summary.json",
            "writable_landlord": "landlord_summary.json",
        },
    )
    architectures = _architecture_inventory(e55)
    exact = e55["exact_copy_channel"]
    counterexample = {
        "candidate": "E55 sigma-zero exact-R-copy lineage",
        "generation_10_to_12_immediate_parent_similarity": exact[
            "generation_10_to_12_immediate_parent_mean"
        ],
        "generation_10_to_12_fixed_ancestor_similarity": exact[
            "generation_10_to_12_strict_ancestor_mean"
        ],
        "rolling_parent_similarity_above_0_9": exact[
            "generation_10_to_12_immediate_parent_mean"
        ]
        > 0.9,
        "fixed_ancestor_similarity_above_0_75": exact[
            "generation_10_to_12_strict_ancestor_mean"
        ]
        > 0.75,
        "externally_refreshed_instance_template_present": False,
        "R_copied_whole": e55["copy_intervention"]["R_is_whole_array_copied"],
        "counterexamples_broad_rolling_continuity_reading": True,
        "counterexamples_narrow_fixed_ancestor_instance_reading": False,
        "screen_is_exhaustive_architecture_search": False,
        "untested_plausible_classes": [
            "redundant or consensus living teachers",
            "error-corrected copying",
            "delayed or recurrent internal templates",
            "alternative slow carriers",
            "broadcast followed by withdrawal",
            "theta copying with controlled noise or reset",
            "cascade link ablations such as direct V-to-theta writing",
            "selected architecture search rather than parameter search",
        ],
    }
    universe = {
        "E64_is_architecture_search": False,
        "E64_evolves_only_rho_and_c_m": True,
        "E65_teacher_source_classes": ["none", "living parent", "external frozen founder", "settled alternate"],
        "E65_additional_manipulations": ["teaching duration", "R restore at release", "R noise"],
        "E66_architecture_classes": ["one writable V-to-R-to-theta cascade", "frozen theta", "one scalar gain-matched control"],
        "alternative_slow_carriers_tested": 0,
        "error_corrected_or_redundant_living_teacher_architectures_tested": 0,
        "architecture_menu_exhaustive": False,
        "necessity_identified": False,
        "uniqueness_identified": False,
    }

    claims = [
        {
            "claim": "Selected memory timescale tracks the time depth used by the E64 fitness target",
            "verdict": "NOT_CONFIRMED_AS_WORDED",
            "evidence_level": "E3",
            "reason": (
                "The three aggregate injury medians are monotone, but the target is always the immediate pre-state scored 150 sweeps later. "
                "E64 varies recurrence interval, unscored relaxation, and total horizon, never distant-ancestor target depth; only one of three aggregate tau values is within 20% of interval/5."
            ),
        },
        {
            "claim": "A fixed ancestral broadcast supplies cross-generation instance fidelity while a living teacher chain does not in E65",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "Repeated full-sheet external broadcast reaches .6885 at T=500 and rises with dose in all four tissues, while the parent chain stays near .51 and far below broadcast. "
                "The intervention is re-instruction, not lineage-carried heredity; parent T=200 actually exceeds the source's own ad hoc floor-q95 quantity, and the barcode evidence is invalid because it scores a broadcasted 16-vector over all 256 cells."
            ),
        },
        {
            "claim": "The V-to-R-to-theta cascade supplies a slower, heritable reference in E66",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "The engineered theta update has raw clocks 2x and 10x the R clock, its per-future array persists across fission, and the retained aggregate fidelity is .6032 versus .4837 gain-matched. "
                "Only aggregate rows remain; theta persistence has no copy-noise branch, the transplant is one tissue with different recipient streams, and neither filtering cleanliness nor robust lineage content is independently established."
            ),
        },
        {
            "claim": "A reference outside the fast drift loop is necessary for heritable instance anatomy in this model family",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2/E3",
            "reason": (
                "No matched reference-present/reference-absent factorial spans a defined architecture family. E64 does not manipulate ancestry, E65 tests a small teacher menu, and E66 tests one designed cascade. "
                "E55's .941 rolling-parent similarity also counterexamples a broad continuity reading, although its fixed-ancestor score .494 does not defeat a narrow fixed-instance reading."
            ),
        },
        {
            "claim": "The tested reference is the only working architecture class",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2/E3",
            "reason": (
                "E64 is only a rho/c_m parameter search; E65 and E66 sample a finite hand-designed menu. Redundant or error-corrected culture, delayed internal templates, alternative carriers, cascade ablations, copy noise, and broadcast withdrawal were not searched."
            ),
        },
        {
            "claim": "The simulation explains why biological genomes had to exist",
            "verdict": "NOT_CONFIRMED_AND_OUT_OF_SCOPE",
            "evidence_level": "E0",
            "reason": (
                "These engineered numerical interventions neither exhaust biological inheritance architectures nor test evolutionary history, chemistry, population processes, or alternative genomic and non-genomic mechanisms. They motivate a design analogy, not historical necessity."
            ),
        },
    ]

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L19",
        "audit_kind": "outcome-known retained recalculation, source audit, and bounded counterexample screen",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "source_config_digests": source_digests,
        "retained_config_digests": retained_digests,
        "expected_config_digests": EXPECTED_CONFIG_DIGESTS,
        "source_config_digest_matches": digest_matches,
        "all_source_config_digests_match": all(digest_matches.values()),
        "git_provenance": provenance,
        "document_checks": {
            "law_claims_tau_interval_over_five": "tau ≈\ninterval/5" in texts["LAWS.md"] or "τ ≈\ninterval/5" in texts["LAWS.md"],
            "law_calls_broadcast_cross_generation_channel": "working cross-generation anatomy channel" in texts["LAWS.md"],
            "law_claims_only_architecture_class": "only architecture class that works" in texts["LAWS.md"],
            "discovery_log_says_ancestor_experiment_not_run": "experiment that\nwould close this (ancestor-referenced injury fitness) is named for\nthe Endgame, not run here" in texts["DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"],
            "design_review_calls_broadcast_instruction_not_heredity": "cannot distinguish HEREDITY from INSTRUCTION" in texts["WAVE14_DESIGN_REVIEW.md"],
        },
        "E64_injury_clock": e64,
        "E65_teaching": e65,
        "E66_writable_landlord": e66,
        "counterexample_screen": counterexample,
        "architecture_search_space": universe,
        "architecture_inventory": architectures,
        "claim_assessment": claims,
        "strongest_supported_wording": (
            "Across five retained tissue/repeat rows, E64's three aggregate median rho values decrease as injury recurrence intervals lengthen, but its fitness always scores the immediate pre-state after 150 sweeps and therefore does not test distant-past target depth or establish tau=interval/5. "
            "In E65, an externally preserved per-lineage founder pattern repeatedly clamped over the whole body after every fission produces dose-ordered fixed-founder fidelity up to .689, whereas the tested living-parent chain remains near .51 and far below broadcast; this is repeated instruction, and the barcode endpoint is invalid. "
            "E66's engineered writable theta persists through fissions, updates more slowly than R by its raw coefficients, and has aggregate fixed-target fidelity .603 versus .484 for its one-point gain-matched control. "
            "Together these are bounded evidence that slow or external references can help preserve a chosen form, not that such a reference is necessary, unique, intrinsically incorruptible, or an explanation of why biological genomes had to exist."
        ),
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        e64_rows,
        corner_rows,
        e65_rows,
        architectures,
        frozen_hashes,
    )


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return buffer.getvalue()


E64_FIELDS = (
    "regime",
    "repeat",
    "selection_interval",
    "selection_has_displacement",
    "selection_score_lag",
    "initial_median_rho",
    "final_median_rho",
    "rho_change",
    "final_tau_reciprocal_rho",
    "initial_median_cm",
    "final_median_cm",
    "cm_change",
    "champion_rho",
    "champion_cm",
    "audit_gen5",
    "audit_gen10",
    "audit_gen15",
)
CORNER_FIELDS = ("rho", "cm", "fitness", "knife_fitness", "live_minus_knife")
E65_FIELDS = (
    "tissue",
    "arm",
    "T",
    "r_mode",
    "sigma_r",
    "barcode_run",
    "fidelity",
    "divergence",
    "barcode_own_lineage",
    "barcode_other_lineages",
)
ARCHITECTURE_FIELDS = (
    "experiment",
    "arm",
    "form_source",
    "candidate_reference",
    "fission_treatment",
    "endpoint",
    "result",
    "decisive_limit",
)


def e64_regime_repeats_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, E64_FIELDS)


def e64_corner_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, CORNER_FIELDS)


def e65_arm_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, E65_FIELDS)


def architecture_inventory_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, ARCHITECTURE_FIELDS)


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def _interval(contrast: Mapping[str, Any], unit: str) -> str:
    low, high = contrast[f"{unit}_bootstrap_95"]
    return f"[{_fmt(low)}, {_fmt(high)}]"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e64 = audit["E64_injury_clock"]
    e65 = audit["E65_teaching"]
    e66 = audit["E66_writable_landlord"]
    clock = e64["clock_association"]
    teach = e65["recalculated_gates"]
    effects = e66["aggregate_effects"]
    exact = audit["counterexample_screen"]
    lines = [
        "# L19 retained incorruptible-reference audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained recalculation and source audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "The useful core is real but smaller than the law. An external founder copy can repeatedly instruct descendants, and E66's engineered writable theta is a slower state whose aggregate lineage score beats one gain-matched control. The experiments do not show that either device is necessary, unique, incorruptible, or equivalent to biological genome evolution.",
        "",
        "E64 is not the advertised distant-past comparison: all three injury worlds score the state immediately before each insult, always 150 sweeps later. E65's broadcast is not inherited by the organism: it is stored outside the lineage and overwrites the entire body after every fission. Its barcode result cannot rescue the culture claim because the code accidentally scores 256 cells using a length-16 patch vector, rather than the 16 injected cells.",
        "",
        "## E64: recurrence association, not target-depth law",
        "",
        "| Regime | Interval | Median final rho | tau=1/rho | interval/5 | interval*rho | Relative tau error |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for regime in ("injury_fast", "injury_mid", "injury_slow"):
        row = e64["regime_summary"][regime]
        lines.append(
            f"| {regime} | {row['injury_interval']} | {_fmt(row['median_final_rho'])} | {_fmt(row['tau_from_median_final_rho'], 3)} | {_fmt(row['interval_over_five'], 1)} | {_fmt(row['interval_times_median_rho'], 3)} | {_fmt(row['tau_relative_error_from_interval_over_five'], 3)} |"
        )
    static = e64["regime_summary"]["static"]
    lines.extend(
        [
            "",
            f"The aggregate medians are monotone and the three-point log-log slope of tau on interval is {_fmt(clock['three_point_log_log_slope_tau_on_interval'], 3)}, versus 1 for exact proportionality. But only {clock['tau_within_20_percent_of_interval_over_five']}/3 points lie within 20% of `interval/5`; the dimensionless products are {', '.join(_fmt(value, 3) for value in clock['interval_times_rho_values'])}, not approximately constant at 5 across the panel.",
            "",
            f"The ordering is weaker below the aggregate. Fast rho exceeds mid in {clock['fast_minus_mid_rho']['directions']['positive']}/5 tissue-index contrasts, mid exceeds slow in {clock['mid_minus_slow_rho']['directions']['positive']}/5, and fast exceeds slow in {clock['fast_minus_slow_rho']['directions']['positive']}/5. Only {clock['strict_fast_gt_mid_gt_slow_repeat_count']}/5 individual indices have the full fast > mid > slow order. Regime RNGs and starting populations differ, so even these pairings are descriptive.",
            "",
            f"Static ends slower still (median rho {_fmt(static['median_final_rho'])}), but it is a no-displacement 150-sweep retention objective, not a distant-ancestor world. The injury score's target age is fixed at 150 in every arm. Intervals 150/300/600 instead change the unscored relaxation after that readout to 0/150/450 sweeps and the total post-burn horizon to 600/1200/2400. Target age, recurrence, and exposure cannot be conflated.",
            "",
            "The Wave-14 register named an ancestor-referenced secondary, a quenched-swap injury arm, and a champion transport probe. None appears in the implementation. The discovery log itself says the ancestor experiment was not run. E64 therefore motivates that experiment; it cannot report its result.",
            "",
            "There are further literal mismatches: the registered six repeats became five; the registered 32x32 sheet is 16x16; and the 'quarter-cell' fitness mask is the entire left half. The quarter value in code is the displacement distance, not the scored area.",
            "",
            "## E65: effective external instruction",
            "",
            "| Teaching T | Parent chain | Broadcast | Broadcast - parent | Directions | Broadcast - floor |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for T in E65_WINDOWS:
        comparison = e65["paired_tissue_comparisons"][str(T)]
        bp = comparison["broadcast_minus_parent"]
        bf = comparison["broadcast_minus_floor"]
        lines.append(
            f"| {T} | {_fmt(teach['parent_chain'][str(T)])} | {_fmt(teach['broadcast'][str(T)])} | {_fmt(bp['mean_difference'])} | {bp['directions']['positive']} / {bp['directions']['tied']} / {bp['directions']['negative']} | {_fmt(bf['mean_difference'])} |"
        )
    broadcast_dose = e65["paired_tissue_comparisons"]["broadcast_dose"]["500_minus_50"]
    parent200 = e65["intervention_and_null_audit"]
    barcode = e65["barcode_observer_audit"]
    lines.extend(
        [
            "",
            f"Broadcast rises from {_fmt(teach['broadcast']['50'])} to {_fmt(teach['broadcast']['500'])}; the T500-minus-T50 change is {_fmt(broadcast_dose['mean_difference'])} and is positive in {broadcast_dose['directions']['positive']}/4 tissues. Parent-chain means remain {_fmt(teach['parent_chain']['50'])}, {_fmt(teach['parent_chain']['200'])}, and {_fmt(teach['parent_chain']['500'])}. This is strong bounded evidence for the external intervention's dose response and its advantage over this parent-chain implementation.",
            "",
            "It is nevertheless instruction, exactly as the adversarial design review warned. Each future has its own founder sign field saved outside the lineage. After every fission, every cell is clamped to that field on every teaching sweep, followed by 1,000 free sweeps. There is no broadcast-withdrawal generation in which descendants must carry the information themselves.",
            "",
            f"The phrase 'parent-chain at chance' also overstates the retained rule. Its T=200 mean {_fmt(teach['parent_chain']['200'])} exceeds the source's own `floor_q95` {_fmt(teach['floor_q95'])} by {_fmt(parent200['parent_200_minus_source_floor_q95'])}; the fidelity and divergence components of P65.1 pass. That `floor_q95` is merely mean plus 1.645 population SD across four floor tissues, not a retained matched-null quantile. The primary fails on its barcode clause.",
            "",
            f"But the barcode clause is not validly observed. Boolean indexing extracts the 4x4 patch as a length-16 vector; comparing it with a 16x16 V array broadcasts those values across rows and scores {barcode['reported_positions_scored_per_lineage']} cells instead of {barcode['intended_patch_positions']}. At the registered 32x32 size the shapes would not broadcast at all. The only score is seven cycles after injection, so 'erased within one re-teaching' is not measured.",
            "",
            "The registered three-class diagnostic, R-parent-correlation manipulation check, c_m=0 gap-closure arm, and AIC threshold comparison are absent. `r_mode=reset` restores R to its post-fission/pre-teaching value only after teaching; it does not remove R or disable R-to-V feedback during the clamp.",
            "",
            "## E66: one engineered slow state",
            "",
            "| Quantity | Retained aggregate |",
            "|---|---:|",
            f"| Writable-fast fidelity | {_fmt(e66['aggregate_summary']['fidelity']['writable_fast'])} |",
            f"| Gain-matched fidelity | {_fmt(e66['aggregate_summary']['fidelity']['gain_matched'])} |",
            f"| Difference | {_fmt(effects['writable_fast_minus_gain_matched_fidelity'])} |",
            f"| Writable-fast freedom | {_fmt(e66['aggregate_summary']['freedom_cost']['writable_fast'])} |",
            f"| Gain-matched freedom | {_fmt(e66['aggregate_summary']['freedom_cost']['gain_matched'])} |",
            f"| Freedom difference | {_fmt(effects['writable_fast_minus_gain_matched_freedom'])} |",
            f"| Fast absolute transplant margin | {_fmt(effects['fast_absolute_transplant_margin'])} |",
            f"| Frozen absolute transplant margin | {_fmt(effects['frozen_absolute_transplant_margin'])} |",
            f"| Fast minus frozen transplant margin | {_fmt(effects['fast_minus_frozen_transplant_margin'])} |",
            f"| Imprint shot | {_fmt(e66['aggregate_summary']['imprint_shot_fidelity'])} |",
            "",
            "At rho=.002, R's reciprocal coefficient clock is 500 sweeps. Implemented theta lambdas are .001 and .0002, giving raw clocks 1,000 and 5,000 sweeps—2x and 10x slower. The fast arm is lambda=rho/2, not `lambda << rho` in any quantified asymptotic sense. Norm projection after every update is nonlinear, and neither frequency response nor declining copy-error variance was measured. The nearly equal fast/slow fidelities (.6032/.5999) do not establish that the slower layer is cleaner.",
            "",
            f"The aggregate fidelity advantage is {_fmt(effects['writable_fast_minus_gain_matched_fidelity'])}, a valuable engineered result. Theta persists as a per-future array while fission acts only on V and R, then continues updating. But no theta copy noise, reset, or branching parent-daughter assay exists, and writable theta is norm-projected at initialization while frozen controls retain unprojected native theta.",
            "",
            f"Gain matching chose native c_m=.2 and matches one tissue's 50-sweep pullback rate within {_fmt(e66['gain_match_recalculation']['absolute_rate_gap'], 8)}. That does not prove total restoring force is matched throughout 12 evolving cycles. Freedom is worse by {_fmt(effects['writable_fast_minus_gain_matched_freedom'])} and clears the allowed -.05 boundary by only {_fmt(effects['freedom_clause_slack'])}.",
            "",
            f"The fast transplant margin {_fmt(effects['fast_absolute_transplant_margin'])} clears the absolute .1 gate by {_fmt(effects['fast_margin_above_absolute_0_1_gate'])}, but the frozen identical-theta negative control itself gives {_fmt(effects['frozen_absolute_transplant_margin'])}. Fast exceeds frozen by only {_fmt(effects['fast_minus_frozen_transplant_margin'])}. Only tissue 0 was probed, group A and B used different recipient RNGs, component matches and replicate variance were discarded, and the gate never compares fast with frozen. This is compatible with lineage content, not robust proof of it.",
            "",
            "Only the aggregate summary survives for E66. Its primary gate also uses the unretained across-tissue spread of frozen fidelity, so the stored true Boolean cannot be independently reconstructed. Two registered swap components—written theta with reseeded V/R and virgin theta with retained V/R—are absent. The capacity result (.974 at norm .3) is static engineered sufficiency, not acquired memory.",
            "",
            "## Necessity, uniqueness, and counterexample screen",
            "",
            "E64 searches two scalar genes inside one architecture. E65 samples four teacher sources plus duration, R restoration, and R noise. E66 samples one declared cascade at two rates against frozen and one gain-matched control. That is a useful engineering menu, not an exhaustive architecture space.",
            "",
            f"The existing-data counterexample screen makes the definition problem visible. E55's exact-R-copy branch has generation-10–12 immediate-parent similarity {_fmt(exact['generation_10_to_12_immediate_parent_similarity'])} without an externally refreshed instance template, but fixed-ancestor similarity is only {_fmt(exact['generation_10_to_12_fixed_ancestor_similarity'])}. It refutes a broad claim that all cross-generation anatomical continuity needs an external fixed reference; it does not refute the narrower claim about maintaining one founder's exact positional form.",
            "",
            "No screen included redundant/consensus teachers, error-corrected copying, recurrent delay stores, other slow carriers, broadcast withdrawal, theta copy noise, cascade-link ablations, or architecture evolution. Failure to find a narrow counterexample among the retained hand-built arms cannot establish 'requires' or 'only.' A numerical model also cannot identify the historical necessity of biological genomes.",
            "",
            "## Clause adjudication",
            "",
            "| Atomic claim | Verdict | Evidence | Finding |",
            "|---|---|---:|---|",
        ]
    )
    for claim in audit["claim_assessment"]:
        lines.append(
            f"| {claim['claim']} | `{claim['verdict']}` | {claim['evidence_level']} | {claim['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Strongest supported wording",
            "",
            audit["strongest_supported_wording"],
            "",
            "## Closer-pass target",
            "",
            "After all 24 laws receive a first pass, run a prospectively frozen common 16x16 design that independently factors target age, injury recurrence, and exposure; repairs the barcode observer and retains every generation; includes broadcast withdrawal, common RNGs, and a calibrated null; retains all E66 tissue and transplant rows; pairs donor theta on identical recipient streams; adds theta copy-noise/reset and complete V/R/theta swap arms; and compares the cascade with redundant/error-corrected living teachers and alternative internal stores. Necessity or uniqueness should remain off the table unless a declared architecture universe and counterexample search are both defensible. L20 is next.",
            "",
        ]
    )
    return "\n".join(lines)
