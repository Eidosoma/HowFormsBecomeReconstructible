"""Outcome-known retained audit for L24's slow-writing/germline claim."""

from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGEST = (
    "dab0529cc12c564526ed1cb413f13c092da4171edce09a5154f86925eaf3158f"
)
REGIMES = ("damage", "clean", "damage_noinherit", "drift")
TRACKED_PACKAGES = (
    "assimilation",
    "blueprint_web",
    "contract_bridge",
    "ladder_web",
    "setpoint_rewrite",
    "voltage_web",
    "weismann",
    "writable_landlord",
)


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


def _normalized(text: str) -> str:
    return " ".join(text.split())


def source_config() -> dict[str, Any]:
    """Independent transcription of the current E70 defaults."""

    return {
        "mode": "full",
        "population": 12,
        "generations": 16,
        "n_repeats": 5,
        "tournament": 3,
        "u_box": [0.001, 1.0],
        "ts_box": [0.2, 0.8],
        "mutation_sigma": 0.3,
        "ts_mutation": 0.05,
        "settle_sweeps": 120,
        "cycles": 8,
        "inter_fission": 500,
        "zap_at_fraction": 0.9,
        "zap_sweeps": 8,
        "amp_threshold": 0.2,
        "norm": 0.3,
        "rho": 0.002,
        "trajectory_seed_tag": "weismann-v1",
    }


def source_config_digest() -> str:
    return canonical_digest(source_config())


def _load_retained_shards(
    tracker: InputTracker, work: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(work.glob("weis_shard_*_of_10.json"))
    if len(paths) != 10:
        raise ValueError(f"expected ten E70 shards, found {len(paths)}")
    ids = []
    payloads = []
    entries: list[dict[str, Any]] = []
    for path in paths:
        match = re.fullmatch(r"weis_shard_(\d\d)_of_10\.json", path.name)
        if match is None:
            raise ValueError(f"unexpected E70 shard name: {path.name}")
        ids.append(int(match.group(1)))
        payload = tracker.json(path)
        payloads.append(payload)
        entries.extend(payload["entries"])
    if ids != list(range(10)):
        raise ValueError(f"non-complete E70 shard IDs: {ids}")
    keys = [(str(row["regime"]), int(row["repeat"])) for row in entries]
    expected = {(regime, repeat) for regime in REGIMES for repeat in range(5)}
    if len(keys) != 20 or len(set(keys)) != 20 or set(keys) != expected:
        raise ValueError("E70 shard entries do not form the complete 4x5 panel")
    digests = {payload.get("config_digest") for payload in payloads}
    return entries, {
        "paths": [str(path) for path in paths],
        "shard_ids": ids,
        "n_shards": len(paths),
        "entries": len(entries),
        "unique_entries": len(set(keys)),
        "config_digests": sorted(str(value) for value in digests),
        "all_config_digests_match": digests == {EXPECTED_CONFIG_DIGEST},
        "elapsed_seconds_sum": float(
            sum(float(payload["elapsed_seconds"]) for payload in payloads)
        ),
        "elapsed_seconds_max": float(
            max(float(payload["elapsed_seconds"]) for payload in payloads)
        ),
        "entries_per_shard": [len(payload["entries"]) for payload in payloads],
    }


def _ratios(
    entries: Sequence[Mapping[str, Any]], regime: str
) -> dict[int, float]:
    return {
        int(row["repeat"]): float(row["final_mean_log_ratio"])
        for row in entries
        if row["regime"] == regime
    }


def reconstruct_selected_gates(
    entries: Sequence[Mapping[str, Any]], pre: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recombine shards without importing or calling the E70 pipeline."""

    ratio_maps = {regime: _ratios(entries, regime) for regime in REGIMES}
    paired = [
        ratio_maps["damage"][repeat] - ratio_maps["clean"][repeat]
        for repeat in range(5)
    ]
    drift = [ratio_maps["drift"][repeat] for repeat in range(5)]
    contrast = float(np.mean(paired))
    directionality = all(
        float(row["final_mean_ll"]) < float(row["final_mean_le"])
        for row in entries
        if row["regime"] == "damage"
    )
    final_log_ratio = {
        regime: float(np.mean(list(ratio_maps[regime].values())))
        for regime in REGIMES
    }
    marginals = {
        regime: {
            "le": float(
                np.mean(
                    [
                        float(row["final_mean_le"])
                        for row in entries
                        if row["regime"] == regime
                    ]
                )
            ),
            "ll": float(
                np.mean(
                    [
                        float(row["final_mean_ll"])
                        for row in entries
                        if row["regime"] == regime
                    ]
                )
            ),
        }
        for regime in REGIMES
    }
    source_gate = bool(
        contrast < 0
        and sum(value < 0 for value in paired) >= max(4, len(paired) - 1)
        and directionality
    )
    attribution = bool(
        abs(final_log_ratio["damage_noinherit"] - final_log_ratio["damage"])
        < 0.3
    )
    selected = {
        "preround": dict(pre),
        "final_log_ratio": final_log_ratio,
        "marginals": marginals,
        "paired_damage_minus_clean": paired,
        "contrast": contrast,
        "drift_log_ratio_distribution": drift,
        "directionality_ll_drops": directionality,
        "gate_p70_1_primary": source_gate,
        "attribution_noinherit_seals_too": attribution,
    }
    extras = {
        "drift_q05": float(np.quantile(drift, 0.05)),
        "contrast_below_registered_drift_q05": contrast
        < float(np.quantile(drift, 0.05)),
        "negative_pair_count": sum(value < 0 for value in paired),
        "positive_pair_count": sum(value > 0 for value in paired),
        "registered_four_of_five_direction_met": sum(value < 0 for value in paired)
        >= 4,
        "source_directionality_predicate_met": directionality,
        "registered_complete_primary_met": bool(
            contrast < float(np.quantile(drift, 0.05))
            and sum(value < 0 for value in paired) >= 4
            and directionality
        ),
    }
    return selected, extras


def _evolution_ledgers(
    entries: Sequence[Mapping[str, Any]], selected: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    center = math.sqrt(0.001)
    ordered = sorted(
        entries, key=lambda row: (REGIMES.index(str(row["regime"])), int(row["repeat"]))
    )
    evolution_rows = []
    trajectory_rows = []
    by_key = {}
    for row in ordered:
        regime = str(row["regime"])
        repeat = int(row["repeat"])
        by_key[(regime, repeat)] = row
        trajectory = row["trajectory"]
        first = trajectory[0]
        last = trajectory[-1]
        evolution_rows.append(
            {
                "regime": regime,
                "repeat": repeat,
                "final_mean_log_ratio": float(row["final_mean_log_ratio"]),
                "final_mean_le": float(row["final_mean_le"]),
                "final_mean_ll": float(row["final_mean_ll"]),
                "final_geometric_ll_over_le": math.exp(
                    float(row["final_mean_log_ratio"])
                ),
                "final_ll_less_than_final_le": float(row["final_mean_ll"])
                < float(row["final_mean_le"]),
                "final_le_less_than_initial_center": float(row["final_mean_le"])
                < center,
                "final_ll_less_than_initial_center": float(row["final_mean_ll"])
                < center,
                "initial_mean_le": float(first["mean_le"]),
                "initial_mean_ll": float(first["mean_ll"]),
                "final_mean_fit": float(last["mean_fit"]),
                "trajectory_generations_retained": len(trajectory),
                "mean_ts_retained": False,
            }
        )
        for point in trajectory:
            trajectory_rows.append(
                {
                    "regime": regime,
                    "repeat": repeat,
                    "gen": int(point["gen"]),
                    "mean_log_ratio": float(point["mean_log_ratio"]),
                    "mean_le": float(point["mean_le"]),
                    "mean_ll": float(point["mean_ll"]),
                    "mean_fit": float(point["mean_fit"]),
                    "mean_ts_retained": False,
                }
            )

    paired_rows = []
    for repeat in range(5):
        damage = float(by_key[("damage", repeat)]["final_mean_log_ratio"])
        clean = float(by_key[("clean", repeat)]["final_mean_log_ratio"])
        noinherit = float(
            by_key[("damage_noinherit", repeat)]["final_mean_log_ratio"]
        )
        drift = float(by_key[("drift", repeat)]["final_mean_log_ratio"])
        drow = by_key[("damage", repeat)]
        paired_rows.append(
            {
                "repeat": repeat,
                "damage": damage,
                "clean": clean,
                "damage_noinherit": noinherit,
                "drift": drift,
                "damage_minus_clean": damage - clean,
                "noinherit_minus_clean": noinherit - clean,
                "noinherit_minus_damage": noinherit - damage,
                "damage_pair_negative": damage - clean < 0,
                "damage_final_ll_less_le": float(drow["final_mean_ll"])
                < float(drow["final_mean_le"]),
                "damage_final_ll_less_initial": float(drow["final_mean_ll"])
                < center,
            }
        )
    if not _recursive_close(
        [row["damage_minus_clean"] for row in paired_rows],
        selected["paired_damage_minus_clean"],
    ):
        raise ValueError("paired evolution ledger does not match selected gates")
    return evolution_rows, trajectory_rows, paired_rows


def exact_block_diagnostics(values: Sequence[float]) -> dict[str, Any]:
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n != 5:
        raise ValueError("E70 exact diagnostics require five paired blocks")
    bootstrap = np.asarray(
        [float(np.mean(x[list(indices)])) for indices in itertools.product(range(n), repeat=n)]
    )
    sign_flips = np.asarray(
        [
            float(
                np.mean(
                    x
                    * np.asarray(
                        [(-1.0 if (mask >> index) & 1 else 1.0) for index in range(n)]
                    )
                )
            )
            for mask in range(2**n)
        ]
    )
    mean = float(np.mean(x))
    sample_sd = float(np.std(x, ddof=1))
    standard_error = sample_sd / math.sqrt(n)
    t_critical_df4_975 = 2.7764451051977987
    return {
        "n_blocks": n,
        "mean": mean,
        "median": float(np.median(x)),
        "sample_sd": sample_sd,
        "standard_error": standard_error,
        "t_df": 4,
        "t_95_interval": [
            mean - t_critical_df4_975 * standard_error,
            mean + t_critical_df4_975 * standard_error,
        ],
        "negative_count": int(np.sum(x < 0)),
        "positive_count": int(np.sum(x > 0)),
        "zero_count": int(np.sum(x == 0)),
        "exact_equal_weight_bootstrap_resamples": int(bootstrap.size),
        "bootstrap_quantiles": {
            str(q): float(np.quantile(bootstrap, q))
            for q in (0.025, 0.05, 0.5, 0.95, 0.975)
        },
        "bootstrap_fraction_below_zero": float(np.mean(bootstrap < 0)),
        "exact_sign_flip_assignments": int(sign_flips.size),
        "sign_flip_two_sided_p_inclusive": float(
            np.mean(np.abs(sign_flips) >= abs(mean) - 1e-15)
        ),
        "sign_flip_one_sided_lower_p_inclusive": float(
            np.mean(sign_flips <= mean + 1e-15)
        ),
        "leave_one_block_out_means": [
            float(np.mean(np.delete(x, index))) for index in range(n)
        ],
        "leave_one_block_out_min": float(
            min(np.mean(np.delete(x, index)) for index in range(n))
        ),
        "leave_one_block_out_max": float(
            max(np.mean(np.delete(x, index)) for index in range(n))
        ),
        "outcome_known_sensitivity_not_confirmatory_inference": True,
    }


def _clock_rows(config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rho = float(config["rho"])
    inter = int(config["inter_fission"])
    zap_step = int(float(config["zap_at_fraction"]) * inter)
    post_zap = inter - zap_step
    center = math.sqrt(float(config["u_box"][0]) * float(config["u_box"][1]))
    values = (float(config["u_box"][0]), center, 0.5, float(config["u_box"][1]))
    rows = []
    for u in values:
        lam = u * rho / 2.0
        rows.append(
            {
                "u": u,
                "lambda": lam,
                "discrete_e_folding_sweeps": -1.0 / math.log1p(-lam),
                "preprojection_weight_after_50": 1.0 - (1.0 - lam) ** post_zap,
                "preprojection_weight_after_one_500_sweep_cycle": 1.0
                - (1.0 - lam) ** inter,
                "preprojection_weight_after_all_8_cycles_if_target_fixed": 1.0
                - (1.0 - lam) ** (inter * int(config["cycles"])),
            }
        )
    r_weight = 1.0 - (1.0 - rho) ** post_zap
    return rows, {
        "inter_fission_sweeps": inter,
        "zap_step_zero_based": zap_step,
        "post_zap_updates_before_score_and_next_fission": post_zap,
        "switch_step_min": int(float(config["ts_box"][0]) * inter),
        "switch_step_max": int(float(config["ts_box"][1]) * inter),
        "zap_is_always_in_late_phase": zap_step
        > int(float(config["ts_box"][1]) * inter),
        "cycles_per_lineage_evaluation": int(config["cycles"]),
        "updates_per_lineage_evaluation_excluding_settle": inter
        * int(config["cycles"]),
        "held_unsealed_u": 0.5,
        "held_unsealed_post_zap_weight": next(
            row["preprojection_weight_after_50"] for row in rows if row["u"] == 0.5
        ),
        "box_max_post_zap_weight": rows[-1]["preprojection_weight_after_50"],
        "reference_R_update_weight_after_50_if_V_fixed": r_weight,
        "reference_R_discrete_e_folding_sweeps": -1.0 / math.log1p(-rho),
        "weights_are_linear_preprojection_coefficients_not_causal_attribution": True,
    }


def _first_commit(repository_root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(repository_root.resolve())
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository_root),
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                str(relative),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None
    rows = [row for row in result.stdout.splitlines() if row]
    return rows[-1] if rows else None


def _git_provenance(plastic_root: Path, experiment_root: Path) -> dict[str, Any]:
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
    expectation = _first_commit(repository_root, experiment_root / "EXPECTATIONS.md")
    result = _first_commit(
        repository_root, experiment_root / "results/full/weismann_summary.json"
    )
    return {
        "repository_root": str(repository_root),
        "expectations_first_commit": expectation,
        "selected_result_first_commit": result,
        "same_first_commit_snapshot": expectation is not None and expectation == result,
        "git_proves_expectations_preceded_selected_result": bool(
            expectation is not None and result is not None and expectation != result
        ),
        "prose_date_is_independent_temporal_seal": False,
    }


def run_l24_audit(
    plastic_root: Path, workspace: Path
) -> tuple[
    dict[str, Any],
    list[Path],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[Path, str],
]:
    tracker = InputTracker()
    ideas_root = plastic_root / IDEAS_RELATIVE
    narrative_paths = {
        "manuscript": plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        "laws": ideas_root / "LAWS.md",
        "wave15": ideas_root / "WAVE15_PROPHECIES.md",
        "design_review": ideas_root / "WAVE15_DESIGN_REVIEW.md",
        "discovery": ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        "baseline": workspace / "SOURCE_BASELINE.md",
        "review_protocol": workspace / "REVIEW_PROTOCOL.md",
        "protocol": workspace / "protocols/L24_SLOW_WRITING_GERMLINE_BARRIER_AUDIT_V1.md",
        "law_case": workspace / "laws/L24_slow_writing_germline_barrier.md",
        "l20_review": workspace / "reviews/L20_SELF_WRITTEN_GENOME_AUDIT_2026-09-03.md",
        "l22_review": workspace / "reviews/L22_BODY_PROOFREADS_GENE_AUDIT_2026-09-03.md",
    }
    texts = {name: _read(tracker, path) for name, path in narrative_paths.items()}
    normalized = {name: _normalized(text) for name, text in texts.items()}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    experiment_root = _experiment_root(plastic_root, "weismann")
    result_root = experiment_root / "results/full"
    result_files = sorted(path for path in result_root.rglob("*") if path.is_file())
    for path in result_files:
        tracker.add(path)
    summary = tracker.json(result_root / "weismann_summary.json")
    pre_payload = tracker.json(result_root / "work/preround.json")
    pre = pre_payload["data"]
    entries, shard_integrity = _load_retained_shards(tracker, result_root / "work")
    selected, primary_extras = reconstruct_selected_gates(entries, pre)
    evolution_rows, trajectory_rows, paired_rows = _evolution_ledgers(entries, selected)
    clock_rows, clock = _clock_rows(source_config())
    paired_diagnostics = exact_block_diagnostics(
        selected["paired_damage_minus_clean"]
    )
    noinherit_clean_diagnostics = exact_block_diagnostics(
        [row["noinherit_minus_clean"] for row in paired_rows]
    )

    pipeline_text = _read(tracker, experiment_root / "src/weismann/pipeline.py")
    config_text = _read(tracker, experiment_root / "src/weismann/config.py")
    assimilation_text = _read(
        tracker, _experiment_root(plastic_root, "assimilation") / "src/assimilation/pipeline.py"
    )
    blueprint_text = _read(
        tracker, _experiment_root(plastic_root, "blueprint_web") / "src/blueprint_web/engine.py"
    )
    expectation_text = _read(tracker, experiment_root / "EXPECTATIONS.md")
    normalized_expectation = _normalized(expectation_text)

    pre_observation_slots = 3 * 3 * 64
    pre_diagnostics = {
        "reported": pre,
        "sealed_advantage": float(pre["sealed_advantage"]),
        "s_min": float(pre["s_min"]),
        "advantage_minus_s_min": float(pre["sealed_advantage"])
        - float(pre["s_min"]),
        "literal_registered_void_inequality_met": float(pre["sealed_advantage"])
        < float(pre["s_min"]),
        "literal_threshold_clear": float(pre["sealed_advantage"])
        >= float(pre["s_min"]),
        "expected_advantage_range": [0.04, 0.08],
        "expected_range_upper_below_s_min": 0.08 < float(pre["s_min"]),
        "expected_range_upper_shortfall": float(pre["s_min"]) - 0.08,
        "registered_population": 16,
        "coded_population": 12,
        "registered_one_over_population": 1.0 / 16.0,
        "coded_one_over_population": 1.0 / 12.0,
        "advantage_below_registered_one_over_population_too": float(
            pre["sealed_advantage"]
        )
        < 1.0 / 16.0,
        "lineage_evaluations": 9,
        "fission_cycles_per_lineage_evaluation": 8,
        "total_fission_cycles_executed": 72,
        "scored_cycles_per_lineage_evaluation": 3,
        "raw_lineage_values_retained": 0,
        "raw_cycle_values_retained": 0,
        "called_one_generation_in_register_but_eight_cycles_in_code": True,
        "unsealed_leak": float(pre["unsealed"]["leak"]),
        "sealed_leak": float(pre["sealed"]["leak"]),
        "unsealed_minus_sealed_leak": float(pre["unsealed"]["leak"])
        - float(pre["sealed"]["leak"]),
        "fixed_leak_observation_slots_per_condition": pre_observation_slots,
        "unsealed_total_agreements_reconstruct": int(
            round(float(pre["unsealed"]["leak"]) * pre_observation_slots)
        ),
        "sealed_total_agreements_reconstruct": int(
            round(float(pre["sealed"]["leak"]) * pre_observation_slots)
        ),
        "unsealed_minus_sealed_agreement_count": int(
            round(
                (float(pre["unsealed"]["leak"]) - float(pre["sealed"]["leak"]))
                * pre_observation_slots
            )
        ),
        "leak_raw_allocation_across_evaluations_and_cycles_retained": False,
        "sampling_uncertainty_calculable_from_retained_units": False,
        "unsealed_and_sealed_use_common_random_streams": False,
        "scrambled_condition_retains_leak": False,
        "scrambled_condition_has_sealed_counterpart": False,
        "clean_preround_condition_present": False,
        "positive_fast_writer_leak_control_present": False,
        "both_sealed_and_unsealed_inherit_theta": True,
        "sealed_gene": [0.5, 0.001, 0.5],
        "unsealed_gene": [0.5, 0.5, 0.5],
        "explicit_germline_sequestration_varied_in_preround": False,
        "one_over_N_is_power_or_minimum_detectable_effect_calculation": False,
        "effective_population_size_estimated": False,
        "evaluation_variance_used_in_threshold": False,
        "tournament_selection_uses_absolute_fitness_difference": False,
    }

    damage_rows = [row for row in evolution_rows if row["regime"] == "damage"]
    center = math.sqrt(0.001)
    directionality = {
        "initial_geometric_center": center,
        "source_predicate_description": "all final arithmetic mean ll < final arithmetic mean le",
        "source_predicate_is_temporal_drop": False,
        "damage_repeats_final_ll_less_final_le": sum(
            row["final_ll_less_than_final_le"] for row in damage_rows
        ),
        "damage_repeats_final_ll_below_initial": sum(
            row["final_ll_less_than_initial_center"] for row in damage_rows
        ),
        "damage_repeats_final_le_below_initial": sum(
            row["final_le_less_than_initial_center"] for row in damage_rows
        ),
        "damage_aggregate_final_le": float(selected["marginals"]["damage"]["le"]),
        "damage_aggregate_final_ll": float(selected["marginals"]["damage"]["ll"]),
        "damage_aggregate_le_fold_initial": float(
            selected["marginals"]["damage"]["le"] / center
        ),
        "damage_aggregate_ll_fold_initial": float(
            selected["marginals"]["damage"]["ll"] / center
        ),
        "damage_aggregate_ll_temporally_drops": float(
            selected["marginals"]["damage"]["ll"]
        )
        < center,
        "damage_aggregate_le_rises_more_than_ll": float(
            selected["marginals"]["damage"]["le"]
        )
        > float(selected["marginals"]["damage"]["ll"]),
    }

    source_gate_block = pipeline_text.split('"gate_p70_1_primary": bool(', 1)[1].split(
        '"attribution_noinherit_seals_too"', 1
    )[0]
    source_checks = {
        "preround_cached_before_jobs": "pre = preround(config)" in pipeline_text
        and "jobs = [(regime, repeat)" in pipeline_text,
        "run_gates_contains_pre_evolution_void_return": "sealed_advantage" in source_gate_block
        or "s_min" in source_gate_block,
        "evolution_was_computed_despite_failed_preround": len(entries) == 20,
        "drift_q05_is_computed": "drift_q05 =" in pipeline_text,
        "drift_q05_is_retained_in_selected_gates": "drift_q05" in selected,
        "drift_q05_is_used_in_source_primary": "drift_q05" in source_gate_block,
        "source_primary_reconstructed": selected["gate_p70_1_primary"]
        == summary["gates"]["gate_p70_1_primary"],
        "ll_drop_source_is_final_cross_gene_comparison": 'r["final_mean_ll"] < r["final_mean_le"]'
        in pipeline_text,
        "zap_sweeps_configured": "zap_sweeps: int = 8" in config_text,
        "zap_sweeps_consumed_by_pipeline": "config.zap_sweeps" in pipeline_text,
        "leak_scored_after_same_cycle_step_loop": "for step in range(config.inter_fission)" in pipeline_text
        and "if cycle >= config.cycles - 3:" in pipeline_text,
        "fission_occurs_at_cycle_start": "for cycle in range(config.cycles):\n        V, Rf, fresh = fission_with_mask"
        in pipeline_text,
        "R_is_copied_whole_at_fission": "Rf.copy() if Rf is not None else None"
        in assimilation_text,
        "R_drives_V_through_comparator": "drift = c_m * (Rf - V)" in blueprint_text,
        "R_is_updated_from_V": "Rf = Rf + bp.rho * (V - Rf)" in blueprint_text,
        "noinherit_resets_theta_only": "if not inherit_theta:\n            theta = project_theta(native[None].copy(), config.norm)"
        in pipeline_text,
        "founder_target_is_fresh_per_gene_evaluation": "founder = np.sign(V)" in pipeline_text,
        "registered_common_held_ll_secondary_implemented": False,
        "individual_ts_trajectory_retained": False,
    }

    retention = {
        "result_files": [str(path.relative_to(experiment_root)) for path in result_files],
        "result_file_count": len(result_files),
        "summary_files": 1,
        "preround_cache_files": 1,
        "shard_files": 10,
        "generation_aggregate_rows_retained": len(trajectory_rows),
        "expected_generation_aggregate_rows": 4 * 5 * 16,
        "individual_population_gene_rows_retained": 0,
        "individual_population_fitness_rows_retained": 0,
        "individual_ts_values_retained": 0,
        "selection_parentage_rows_retained": 0,
        "life_fitness_evaluation_rows_retained": 0,
        "pre_round_unit_rows_retained": 0,
        "pre_round_cycle_leak_rows_retained": 0,
        "V_R_theta_states_retained": 0,
        "historical_non_drift_evolution_life_fitness_calls": 3 * 5 * 12 * 16,
        "historical_preround_life_fitness_calls": 9,
        "historical_total_life_fitness_calls": 3 * 5 * 12 * 16 + 9,
    }

    document_checks = {
        "register_says_void_before_compute": "s >> 1/N_e or the experiment is VOID before compute"
        in normalized["wave15"],
        "expectations_say_underpowered_before_evolution": "the advantage must clear it or the run is declared underpowered BEFORE evolution"
        in normalized_expectation,
        "closeout_says_implementation_ran_anyway": "the implementation recorded it but ran anyway"
        in normalized["discovery"],
        "closeout_calls_void_retroactively_honored": "VOID DECLARED, retroactively honored"
        in texts["discovery"],
        "law_labels_candidate_pending_fast_test": "candidate pending a fast-writing test"
        in normalized["laws"],
        "register_population": 16,
        "register_generations": 24,
        "register_inter_fission": 1000,
        "coded_population": int(source_config()["population"]),
        "coded_generations": int(source_config()["generations"]),
        "coded_inter_fission": int(source_config()["inter_fission"]),
        "frozen_wave_constants_match_code": False,
        "formal_amendment_located": False,
        "v23_is_independent_E70_replication": False,
    }

    channel_audit = {
        "cycle_order": [
            "fission",
            "late zap at step 450",
            "50 coupled updates",
            "same-life score",
        ],
        "undamaged_descendant_between_zap_and_leak_score": False,
        "leak_target_replaced_at_each_cycle_zap": True,
        "leak_is_clean_inherited_damage_endpoint": False,
        "theta_persists_at_fission_when_inherit_theta_true": True,
        "theta_resets_to_native_when_inherit_theta_false": True,
        "V_is_halved_and_jittered": True,
        "R_is_copied_whole_and_exact": True,
        "R_remains_soma_to_descendant_state_in_noinherit_arm": True,
        "noinherit_is_complete_transmission_barrier": False,
        "fast_writer_condition_run": False,
        "speed_by_sequestration_factorial_run": False,
        "explicit_sequestration_manipulation_at_common_writer_speed_run": False,
    }

    noinherit = {
        "reported_attribution_flag": bool(selected["attribution_noinherit_seals_too"]),
        "source_absolute_difference_threshold": 0.3,
        "damage_noinherit_minus_damage_aggregate": float(
            selected["final_log_ratio"]["damage_noinherit"]
            - selected["final_log_ratio"]["damage"]
        ),
        "damage_noinherit_minus_clean_aggregate": float(
            selected["final_log_ratio"]["damage_noinherit"]
            - selected["final_log_ratio"]["clean"]
        ),
        "damage_noinherit_minus_clean_pairs": [
            row["noinherit_minus_clean"] for row in paired_rows
        ],
        "damage_noinherit_minus_damage_pairs": [
            row["noinherit_minus_damage"] for row in paired_rows
        ],
        "noinherit_minus_clean_diagnostics": noinherit_clean_diagnostics,
        "source_threshold_declared_in_config_or_expectations": False,
        "common_random_evaluation_streams_across_regimes": False,
        "tissue_index_paired_across_regimes": True,
        "same_founder_realization_across_regimes_and_genes": False,
        "clean_germline_attribution_identified": False,
    }

    claims = [
        {
            "claim": "E70's pre-round declares the evolution void because .044 is below .083",
            "verdict": "CONFIRMED_AS_REGISTERED_ARITHMETIC",
            "evidence_level": "E2/E3",
            "reason": (
                "The cache exactly gives .0442708 < 1/12=.0833333, and the prospective text says to stop before evolution. But the pipeline did not stop, the closeout honored the rule retrospectively, and 1/N is not a power/MDE or effective-population calculation for noisy rank-tournament selection."
            ),
        },
        {
            "claim": "At the tested slow clock, late damage causes no detectable additional inherited leak",
            "verdict": "NOT_TESTED_AS_WORDED",
            "evidence_level": "E2/E3",
            "reason": (
                "The retained aggregates are unsealed .15625 and sealed .16840, an opposite-signed difference of -7/576 agreements. Raw units and uncertainty are absent, and leak is scored 50 updates after the latest zap in the same life, before another fission; it is not an undamaged-descendant inheritance endpoint."
            ),
        },
        {
            "claim": "Clock mismatch rather than endpoint insensitivity or another channel explains E70's null",
            "verdict": "CONSISTENT_BUT_NOT_IDENTIFIED",
            "evidence_level": "E3/E2",
            "reason": (
                "At u=.5 the pre-projection theta mixing weight in 50 updates is only .02470, and even the box maximum gives .04879, so the manipulation is structurally weak. But no fast positive control is run, global projection intervenes, the endpoint is same-life, and exact full-field R inheritance remains active. The evolution also fails its sign, drift, and directionality requirements."
            ),
        },
        {
            "claim": "A faster soma-to-heritable channel would leak and gain from explicit sequestration",
            "verdict": "NOT_TESTED",
            "evidence_level": "E0",
            "reason": (
                "The current box never exceeds u=1, no fast-writer positive control is present, and no common-speed transmission-boundary intervention crosses theta and R. The claim is a useful experiment proposal, not an E70 result."
            ),
        },
        {
            "claim": "Biological germline sequestration tracks channel speed rather than channel existence",
            "verdict": "NOT_EMPIRICAL_HERE",
            "evidence_level": "E0",
            "reason": (
                "E70 is one engineered 16x16 simulation and contains no comparative biological lineages, germline phenotypes, channel-speed measurements, or phylogenetic control."
            ),
        },
    ]

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L24",
        "audit_kind": "outcome-known E70 pre-round, retained-shard, observer, channel, and source audit",
        "work_state": "RECALCULATED",
        "overall_verdict": "NOT_CONFIRMED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "source_config": source_config(),
        "source_config_digest": source_config_digest(),
        "retained_config_digest": summary["config_digest"],
        "expected_config_digest": EXPECTED_CONFIG_DIGEST,
        "source_summary_preround_and_shard_digests_match": bool(
            source_config_digest()
            == summary["config_digest"]
            == pre_payload["config_digest"]
            == EXPECTED_CONFIG_DIGEST
            and shard_integrity["all_config_digests_match"]
        ),
        "selected_summary_reconstructs_from_preround_and_shards": _recursive_close(
            selected, summary["gates"]
        ),
        "git_provenance": _git_provenance(plastic_root, experiment_root),
        "shard_integrity": shard_integrity,
        "retention_inventory": retention,
        "document_checks": document_checks,
        "source_checks": source_checks,
        "preround": pre_diagnostics,
        "clock": clock,
        "clock_rows": clock_rows,
        "channel_audit": channel_audit,
        "selected_gates_reconstructed": selected,
        "registered_primary_diagnostics": primary_extras,
        "directionality_audit": directionality,
        "paired_damage_minus_clean_diagnostics": paired_diagnostics,
        "noinherit_attribution_audit": noinherit,
        "evolution_rows": evolution_rows,
        "paired_rows": paired_rows,
        "claim_assessment": claims,
        "strongest_supported_wording": (
            "E70's retained pre-round reports a sealed-minus-unsealed fitness difference of .04427, below its prospectively stated .08333 stop threshold, so its evolutionary phase is void under its own rule. The configured timing leaves only 50 updates after each late zap; at held u=.5 the unprojected theta update can mix at most 2.47% of a fixed target during that window (4.88% at the coded box maximum). This makes weak late writing a plausible design diagnosis. It is not a demonstrated germline barrier: the leak score is taken in the damaged life before the next fission, R is copied whole, no fast-writer positive control exists, and the completed evolutionary primary fails its sign-count, drift-quantile, and directionality requirements."
        ),
        "closer_pass_target": (
            "Freeze a positive-control-first speed x transmission-boundary factorial. Zap a parent once, fission afterward, withdraw damage, and score an undamaged daughter before any new zap. Span theta rates that give prespecified 50-step write fractions, and independently cross theta persist/reset with R copy/reset/scramble while matching founder states and random streams. Include clean, immediate-post-zap, scrambled-target, and somatic-cost endpoints; retain unit trajectories; size blocks from pilot variance with a declared effect scale rather than 1/N. Run evolution only after the descendant-leak positive control and assay sensitivity pass. Treat the biological comparative prediction as a separate phylogenetically controlled study."
        ),
        "headline_diagnostics": {
            "sealed_advantage": pre_diagnostics["sealed_advantage"],
            "s_min": pre_diagnostics["s_min"],
            "literal_void": pre_diagnostics["literal_registered_void_inequality_met"],
            "evolution_stopped_before_compute": False,
            "unsealed_minus_sealed_leak": pre_diagnostics[
                "unsealed_minus_sealed_leak"
            ],
            "leak_is_inherited_endpoint": False,
            "held_unsealed_post_zap_theta_weight": clock[
                "held_unsealed_post_zap_weight"
            ],
            "box_max_post_zap_theta_weight": clock["box_max_post_zap_weight"],
            "R_copied_whole": True,
            "damage_minus_clean_contrast": selected["contrast"],
            "negative_pairs": primary_extras["negative_pair_count"],
            "drift_q05": primary_extras["drift_q05"],
            "contrast_below_drift_q05": primary_extras[
                "contrast_below_registered_drift_q05"
            ],
            "source_primary_gate": selected["gate_p70_1_primary"],
            "fast_writer_test_run": False,
        },
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        evolution_rows,
        paired_rows,
        trajectory_rows,
        clock_rows,
        [
            {
                "condition": "unsealed",
                "le": 0.5,
                "ll": 0.5,
                "ts": 0.5,
                "scrambled_zap": False,
                "lineage_evaluations": 3,
                "cycles_per_evaluation": 8,
                "fitness": float(pre["unsealed"]["fitness"]),
                "leak": float(pre["unsealed"]["leak"]),
                "raw_units_retained": 0,
            },
            {
                "condition": "sealed",
                "le": 0.5,
                "ll": 0.001,
                "ts": 0.5,
                "scrambled_zap": False,
                "lineage_evaluations": 3,
                "cycles_per_evaluation": 8,
                "fitness": float(pre["sealed"]["fitness"]),
                "leak": float(pre["sealed"]["leak"]),
                "raw_units_retained": 0,
            },
            {
                "condition": "unsealed_scrambled",
                "le": 0.5,
                "ll": 0.5,
                "ts": 0.5,
                "scrambled_zap": True,
                "lineage_evaluations": 3,
                "cycles_per_evaluation": 8,
                "fitness": float(pre["unsealed_scrambled"]["fitness"]),
                "leak": None,
                "raw_units_retained": 0,
            },
        ],
        frozen_hashes,
    )


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return buffer.getvalue()


EVOLUTION_FIELDS = (
    "regime",
    "repeat",
    "final_mean_log_ratio",
    "final_mean_le",
    "final_mean_ll",
    "final_geometric_ll_over_le",
    "final_ll_less_than_final_le",
    "final_le_less_than_initial_center",
    "final_ll_less_than_initial_center",
    "initial_mean_le",
    "initial_mean_ll",
    "final_mean_fit",
    "trajectory_generations_retained",
    "mean_ts_retained",
)
PAIRED_FIELDS = (
    "repeat",
    "damage",
    "clean",
    "damage_noinherit",
    "drift",
    "damage_minus_clean",
    "noinherit_minus_clean",
    "noinherit_minus_damage",
    "damage_pair_negative",
    "damage_final_ll_less_le",
    "damage_final_ll_less_initial",
)
TRAJECTORY_FIELDS = (
    "regime",
    "repeat",
    "gen",
    "mean_log_ratio",
    "mean_le",
    "mean_ll",
    "mean_fit",
    "mean_ts_retained",
)
CLOCK_FIELDS = (
    "u",
    "lambda",
    "discrete_e_folding_sweeps",
    "preprojection_weight_after_50",
    "preprojection_weight_after_one_500_sweep_cycle",
    "preprojection_weight_after_all_8_cycles_if_target_fixed",
)
PREROUND_FIELDS = (
    "condition",
    "le",
    "ll",
    "ts",
    "scrambled_zap",
    "lineage_evaluations",
    "cycles_per_evaluation",
    "fitness",
    "leak",
    "raw_units_retained",
)


def evolution_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, EVOLUTION_FIELDS)


def paired_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, PAIRED_FIELDS)


def trajectory_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, TRAJECTORY_FIELDS)


def clock_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, CLOCK_FIELDS)


def preround_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, PREROUND_FIELDS)


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    pre = audit["preround"]
    selected = audit["selected_gates_reconstructed"]
    primary = audit["registered_primary_diagnostics"]
    direction = audit["directionality_audit"]
    paired = audit["paired_damage_minus_clean_diagnostics"]
    channel = audit["channel_audit"]
    lines = [
        "# L24 retained slow-writing/germline-barrier audit",
        "",
        f"**Verdict:** `{audit['overall_verdict']}`  ",
        "**Work state:** `RECALCULATED`  ",
        "**Design:** outcome-known retained-shard and source audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Bottom line",
        "",
        "The void arithmetic survives; the law does not. E70's cached sealed-minus-unsealed fitness difference is "
        + f"`{_fmt(pre['sealed_advantage'])}`, below its coded `1/N={_fmt(pre['s_min'])}` threshold. The prospective text says this should void E70 before evolution. The implementation merely cached the pre-round and ran all twenty evolution jobs; the later closeout calls that decision retroactive. Moreover, `1/N` is not a minimum-detectable-effect calculation here: no effective N, evaluation variance, power, or tournament-selection mapping was estimated.",
        "",
        "The leak result cannot establish inherited sealing. `leak` is scored 50 updates after the latest zap in the same life, before the next fission. The two aggregates are unsealed "
        + f"`{_fmt(pre['unsealed_leak'])}` and sealed `{_fmt(pre['sealed_leak'])}`—an opposite-signed difference of `{_fmt(pre['unsealed_minus_sealed_leak'])}`, or -7 agreements across 576 fixed score slots. The per-evaluation and per-cycle values are gone, no uncertainty was run, and there is no fast-writer positive control. Both conditions inherit theta; “sealed” only changes late u from .5 to .001.",
        "",
        "Timing does make weak manipulation plausible. At u=.5, theta's linear update before global projection can mix only 2.47% of a fixed target during the 50 post-zap updates; even u=1 reaches only 4.88%. But that is a design diagnosis, not causal proof. Each evaluation repeats eight fission/zap cycles, projection changes the mixture, and R is updated from V, drives V, and is copied whole at fission—even in the theta-no-inheritance arm.",
        "",
        "The completed evolution supplies no rescue. Damage-minus-clean averages "
        + f"`{_fmt(selected['contrast'])}`, but only {primary['negative_pair_count']}/5 pairs are negative, its t interval spans `{_fmt(paired['t_95_interval'][0])}` to `{_fmt(paired['t_95_interval'][1])}`, and the contrast does not fall below the registered drift 5th percentile `{_fmt(primary['drift_q05'])}`. The source computes that quantile but omits it from the saved gate and Boolean. Its directionality guard also fails—and the variable called `ll_drop` compares final ll with final le rather than with the initial ll.",
        "",
        "## Pre-round audit",
        "",
        "| Quantity | Retained / reconstructed | Reading |",
        "|---|---:|---|",
        f"| Unsealed fitness | {_fmt(pre['reported']['unsealed']['fitness'])} | 3 aggregate lineage evaluations |",
        f"| Sealed fitness | {_fmt(pre['reported']['sealed']['fitness'])} | 3 aggregate lineage evaluations |",
        f"| Sealed advantage | {_fmt(pre['sealed_advantage'])} | Inside the forecast .04-.08 |",
        f"| Coded threshold | {_fmt(pre['s_min'])} | `1/12`, not an estimated MDE |",
        f"| Advantage-threshold margin | {_fmt(pre['advantage_minus_s_min'])} | Fails literal stop rule |",
        f"| Unsealed leak | {_fmt(pre['unsealed_leak'])} | Same-life post-zap endpoint |",
        f"| Sealed leak | {_fmt(pre['sealed_leak'])} | Same-life post-zap endpoint |",
        "",
        "The register calls this a one-generation pre-round. Code runs eight fission cycles per `life_fitness` call, repeats the zap in every cycle, and averages the final three cycles. Across the three conditions, the nine calls therefore execute 72 fission cycles. Only condition means survive. The stated expected advantage range `.04-.08` is itself wholly below the coded `.08333` threshold, so the design prospectively expected an effect too small for its own rule.",
        "",
        "The frozen Wave-15 constants were population 16, 24 generations, and 1,000 sweeps per life. E70 uses 12, 16, and 500; no formal amendment was located. The observed advantage also fails `1/16=.0625`, so this discrepancy does not change the literal void outcome.",
        "",
        "## Clock and channel audit",
        "",
        "| u | actual lambda | e-fold sweeps | 50-step weight | 500-step weight |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in audit["clock_rows"]:
        lines.append(
            f"| {_fmt(row['u'])} | {_fmt(row['lambda'], 8)} | {_fmt(row['discrete_e_folding_sweeps'], 1)} | {_fmt(row['preprojection_weight_after_50'])} | {_fmt(row['preprojection_weight_after_one_500_sweep_cycle'])} |"
        )
    lines.extend(
        [
            "",
            "These are coefficients for the linear theta update before norm projection, assuming a fixed target; they are not measured damage fractions. The maximum t_s puts the switch at step 400, so the step-450 zap always lands in the late phase. The configured `zap_sweeps=8` is never read by E70's pipeline: the intervention is one instantaneous posterior flip, followed by dynamics.",
            "",
            "Cycle order is fission -> zap late in the new life -> 50 updates -> score. A descendant is not generated after the scored zap. Earlier damage may persist across the repeated cycles, but the target is replaced by the newest zap, so the endpoint does not isolate inherited damage. A valid inherited-leak observer would zap a parent once, fission afterward, withdraw damage, then score an undamaged daughter before another zap.",
            "",
            f"R's own 50-step EMA weight would be `{_fmt(audit['clock']['reference_R_update_weight_after_50_if_V_fixed'])}` if V were fixed, and its e-fold time is `{_fmt(audit['clock']['reference_R_discrete_e_folding_sweeps'], 1)}` sweeps. More importantly, R is copied whole and exactly at fission. Resetting theta therefore leaves an active inherited reference channel and cannot isolate a complete Weismann barrier.",
            "",
            "## Evolution reconstruction",
            "",
            "| Repeat | Damage | Clean | Damage-clean | No-theta-inherit | Drift |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in audit["paired_rows"]:
        lines.append(
            f"| {row['repeat']} | {_fmt(row['damage'])} | {_fmt(row['clean'])} | {_fmt(row['damage_minus_clean'])} | {_fmt(row['damage_noinherit'])} | {_fmt(row['drift'])} |"
        )
    lines.extend(
        [
            "",
            f"The five paired values have median `{_fmt(paired['median'])}`, sample SD `{_fmt(paired['sample_sd'])}`, and exact equal-weight bootstrap 95% interval `{_fmt(paired['bootstrap_quantiles']['0.025'])}` to `{_fmt(paired['bootstrap_quantiles']['0.975'])}`. All 32 sign flips give an inclusive two-sided diagnostic p of `{_fmt(paired['sign_flip_two_sided_p_inclusive'])}`. Leave-one-block means range `{_fmt(paired['leave_one_block_out_min'])}` to `{_fmt(paired['leave_one_block_out_max'])}`. These outcome-known sensitivity calculations describe instability; they are not a new confirmatory analysis.",
            "",
            "The source guard `all(final_mean_ll < final_mean_le)` holds in only "
            + f"{direction['damage_repeats_final_ll_less_final_le']}/5 damage repeats. It is not a temporal drop. Against the common `.031623` start, final ll drops in only {direction['damage_repeats_final_ll_below_initial']}/5 repeats and final le in {direction['damage_repeats_final_le_below_initial']}/5. Aggregated damage le and ll both rise, to `{_fmt(direction['damage_aggregate_final_le'])}` and `{_fmt(direction['damage_aggregate_final_ll'])}` respectively.",
            "",
            "The no-theta-inheritance aggregate is only `.154479` above clean but `.792427` above damage, with mixed repeat signs. Its source flag uses an undeclared absolute `.3` cutoff. Separate evaluation streams, fresh gene-dependent founder targets, theta-only reset, and exact R inheritance prevent a clean germline-versus-somatic attribution.",
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
            str(audit["strongest_supported_wording"]),
            "",
            "## Closer pass",
            "",
            str(audit["closer_pass_target"]),
            "",
            "## Provenance and run boundary",
            "",
            f"The independently transcribed config, selected summary, pre-round cache, and ten shard digests all match `{audit['expected_config_digest']}`. Recombining the pre-round and twenty unique 4x5 evolution entries reproduces the selected `gates` object exactly: `{audit['selected_summary_reconstructs_from_preround_and_shards']}`. All 320 generation-level aggregate rows are retained and exported; individual genes, fitnesses, t_s, parents, and V/R/theta states are not. The historical shard elapsed times sum to `{_fmt(audit['shard_integrity']['elapsed_seconds_sum'], 3)}` seconds (maximum shard `{_fmt(audit['shard_integrity']['elapsed_seconds_max'], 3)}`); the selected summary's `.025` seconds is cache recombination, not the campaign runtime.",
            "",
            f"This audit consumed {audit['input_file_count']} hashed inputs and generated zero scientific futures and zero simulator replays. E70 ran no fast-writer condition (`{channel['fast_writer_condition_run']}`) and no speed-by-sequestration factorial (`{channel['speed_by_sequestration_factorial_run']}`).",
            "",
        ]
    )
    return "\n".join(lines)
