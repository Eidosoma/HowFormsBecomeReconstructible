"""Outcome-known retained-artifact audit for L05 conservation-selfhood."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .selfhood_math import (
    PERTURBATIONS,
    recalculate_e26_regeneration,
    recalculate_e26_screen,
    recalculate_e27,
    recalculate_e30,
)
from .stats import close


L4_REUSE_RUN_ID = "l04_retained_audit_v1_attempt2"


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def _track_package(tracker: InputTracker, root: Path) -> None:
    tracker.add(root / "EXPECTATIONS.md")
    for path in sorted((root / "src").rglob("*.py")):
        tracker.add(path)


def _voltage_config(*, screen_base: bool) -> dict[str, Any]:
    return {
        "mode": "full",
        "height": 16,
        "width": 16,
        "dt": 0.2,
        "coupling": 1.0,
        "sigma": 0.10 if screen_base else 0.30,
        "well_asym": 0.0,
        "threshold_spread": 0.2,
        "tissue_tag": "voltage-tissue-v1",
        "tissue_index": 0,
        "resting": -1.0,
        "copy_jitter": 0.05,
        "activity_budget": 512 if screen_base else 64,
        "t_min_sweeps": 4,
        "t_max_sweeps": 64,
        "inherit_threshold": 0.9,
        "coherence_threshold": 0.9,
        "distinct_threshold": 0.85,
        "strict_run": 8,
        "strict_horizon": 32,
        "mass_quantile": 0.75,
        "n_seeds": 16,
        "futures": 64,
        "strict_band": (0.005, 0.5),
        "trajectory_seed_tag": "voltage-traj-v1",
    }


def _config_digests() -> dict[str, str]:
    rewrite = {
        "mode": "full",
        "n_tissues": 48,
        "off_band_tissues": 16,
        "futures": 128,
        "horizon": 32,
        "zap_generation": 3,
        "zap_sweeps": 8,
        "lesion_generation": 14,
        "wild_window": (1, 2),
        "run_length": 8,
        "coherence": 0.9,
        "distinct": 0.85,
        "inherit": 0.9,
        "coupling_band": 1.0,
        "coupling_under": 0.25,
        "coupling_over": 4.0,
        "tissue_param_tag": "voltage-tissue-params-v1",
        "trajectory_seed_tag": "rewrite-traj-v1",
    }
    homeostasis = {
        "mode": "full",
        "n_tissues": 16,
        "futures": 96,
        "horizon": 20,
        "zap_generation": 3,
        "perturb_generation": 15,
        "region_side": 8,
        "dose_ladder": (4, 8, 12),
        "recover_window": 3,
        "inherit": 0.9,
        "trajectory_seed_tag": "homeo-traj-v1",
    }
    battery2 = {
        "mode": "full",
        "eca_futures": 128,
        "worm_tissues": 24,
        "placement_tissues": 48,
        "placement_futures": 32,
    }
    battery3 = {"mode": "full", "base_tissue": 300, "n_tissues": 8}
    return {
        "voltage_web_screen_base": canonical_digest(
            _voltage_config(screen_base=True)
        ),
        "voltage_web_current": canonical_digest(
            _voltage_config(screen_base=False)
        ),
        "setpoint_rewrite": canonical_digest(rewrite),
        "anatomical_homeostasis": canonical_digest(homeostasis),
        "sealed_battery_2": canonical_digest(battery2),
        "sealed_battery_3": canonical_digest(battery3),
    }


def source_config_digests() -> dict[str, str]:
    """Expose independently transcribed source configurations for tests."""

    return _config_digests()


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
        if left is None and isinstance(right, float) and math.isnan(right):
            return True
        if right is None and isinstance(left, float) and math.isnan(left):
            return True
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return close(left, right)
    return left == right


def _load_shards(
    tracker: InputTracker,
    directory: Path,
    pattern: str,
    *,
    expected_shards: int,
    require_payload_shard_ids: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(directory.glob(pattern))
    if len(paths) != expected_shards:
        raise ValueError(
            f"expected {expected_shards} shards matching {directory / pattern}; "
            f"found {len(paths)}"
        )
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"shard config digests differ: {sorted(digests)}")
    shard_ids = None
    if require_payload_shard_ids:
        shard_ids = sorted(int(payload["shard"]) for payload in payloads)
        if shard_ids != list(range(expected_shards)):
            raise ValueError(f"incomplete shard IDs: {shard_ids}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    return entries, {
        "n_shards": len(paths),
        "config_digest": next(iter(digests)),
        "payload_shard_ids": shard_ids,
        "n_entries": len(entries),
    }


def audit_e26(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "voltage_web")
    _track_package(tracker, root)
    tracker.add(root / "tests/test_voltage.py")
    screen = tracker.json(root / "results/full/screen.json")
    regeneration = tracker.json(root / "results/full/regeneration.json")
    rounds = [
        tracker.json(root / f"results/full/screen_round{index}.json")
        for index in range(1, 5)
    ]
    screen_calc = recalculate_e26_screen(screen)
    regeneration_calc = recalculate_e26_regeneration(regeneration)
    digests = _config_digests()
    engine = (root / "src/voltage_web/engine.py").read_text(encoding="utf-8")

    return {
        "integrity": {
            "expected_screen_base_config_digest": digests["voltage_web_screen_base"],
            "retained_screen_config_digest": screen.get("config_digest"),
            "screen_matches_prefreeze_default": (
                screen.get("config_digest") == digests["voltage_web_screen_base"]
            ),
            "expected_current_config_digest": digests["voltage_web_current"],
            "retained_regeneration_config_digest": regeneration.get("config_digest"),
            "regeneration_matches_current_frozen_default": (
                regeneration.get("config_digest") == digests["voltage_web_current"]
            ),
            "screen_base_differs_from_later_frozen_default": (
                digests["voltage_web_screen_base"] != digests["voltage_web_current"]
            ),
            "screen_grid_gate_recalculation_matches": screen_calc[
                "stored_grid_gates_match"
            ],
            "regeneration_gate_recalculation_matches": regeneration_calc[
                "stored_gate_matches"
            ],
        },
        "screen": screen_calc,
        "regeneration": regeneration_calc,
        "development_chronology": {
            "archived_rounds": [
                {
                    "round": index,
                    "grid_rows": len(payload["grid"]),
                    "n_passing": int(payload["n_passing"]),
                    "gate_regime_exists": bool(payload["gate_regime_exists"]),
                    "gate_coupling_sweet_spot": bool(
                        payload["gate_coupling_sweet_spot"]
                    ),
                }
                for index, payload in enumerate(rounds, start=1)
            ],
            "final_grid_rows": len(screen["grid"]),
            "final_n_passing": int(screen["n_passing"]),
            "multiple_engine_or_instrument_changes_between_rounds": True,
            "matched_conservation_only_ablation": False,
            "causal_conservation_inference_supported": False,
        },
        "code_conservation_trace": {
            "drift_mean_centered": "drift = drift - drift.mean" in engine,
            "noise_mean_centered": "noise = noise - noise.mean" in engine,
            "clipping_after_centering": "V = np.clip(V, -2.0, 2.0)" in engine,
            "optional_clamp_overwrites_voltage": (
                "V = np.where(clamp[None, :, :], 1.5, V)" in engine
            ),
            "fission_initializes_daughter_to_resting": (
                "offspring = np.full_like(V, config.resting)" in engine
            ),
            "fission_adds_uncentered_copy_jitter": (
                "offspring = offspring + config.copy_jitter" in engine
            ),
            "exact_mean_conservation_spans_fission": False,
            "exact_mean_conservation_guaranteed_after_clip_or_clamp": False,
        },
    }


def audit_e27(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "setpoint_rewrite")
    _track_package(tracker, root)
    entries, shards = _load_shards(
        tracker,
        root / "results/full/work",
        "rewrite_shard_*_of_08.json",
        expected_shards=8,
        require_payload_shard_ids=True,
    )
    summary = tracker.json(root / "results/full/rewrite_summary.json")
    calculated = recalculate_e27(entries)
    expected_digest = _config_digests()["setpoint_rewrite"]
    expectations = (root / "EXPECTATIONS.md").read_text(encoding="utf-8")
    pipeline = (root / "src/setpoint_rewrite/pipeline.py").read_text(
        encoding="utf-8"
    )
    runner = (root / "src/setpoint_rewrite/runner.py").read_text(encoding="utf-8")
    projection_matches = _recursive_close(
        calculated["source_projection"], summary["gates"]
    )
    return {
        "integrity": {
            "expected_config_digest": expected_digest,
            "summary_config_digest": summary.get("config_digest"),
            "shard_config_digest": shards["config_digest"],
            "config_matches_source_default": (
                summary.get("config_digest") == expected_digest
                and shards["config_digest"] == expected_digest
            ),
            "summary_n_entries": int(summary["n_entries"]),
            "shards": shards,
            "all_summary_gates_and_scalars_match": projection_matches,
        },
        "recalculation": calculated,
        "criterion_discrepancy": {
            "expectations_wild_recovery_bar": 0.6,
            "implemented_wild_recovery_bar": 0.7,
            "expectations_contains_0_6_bar": "≥ 0.6" in expectations,
            "pipeline_contains_0_7_bar": "wild_recovery >= 0.7" in pipeline,
            "declared_gate_passes": calculated[
                "declared_expectations_two_setpoint_gate"
            ]["calculated"],
            "implemented_gate_passes": calculated[
                "implemented_two_setpoint_gate"
            ]["calculated"],
            "verdict_changes_here": (
                calculated["declared_expectations_two_setpoint_gate"]["calculated"]
                != calculated["implemented_two_setpoint_gate"]["calculated"]
            ),
        },
        "design_interpretation": {
            "control_and_zapped_streams_paired_for_conversion": True,
            "rewritten_group_selected_by_observed_post_zap_outcome": (
                'rewritten = rewrites["rewritten"]' in pipeline
            ),
            "wild_group_is_eligible_not_rewritten": (
                "wild_like = eligible & ~rewritten" in pipeline
            ),
            "recovered_ored_across_generations": "recovered |=" in runner,
            "still_distinct_ored_separately_across_generations": (
                "still_distinct |=" in runner
            ),
            "final_score_intersects_separate_ors": (
                '(recovery["recovered"] & recovery["still_distinct"])' in pipeline
            ),
            "same_generation_coincidence_reconstructable_from_aggregates": False,
            "anatomical_heads_measured": False,
            "endpoint": "15-coordinate generation-averaged binary texture census",
        },
    }


def audit_e30(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "anatomical_homeostasis")
    _track_package(tracker, root)
    test_path = tracker.add(root / "tests/test_homeo.py")
    entries, shards = _load_shards(
        tracker,
        root / "results/full/work",
        "homeo_shard_*_of_08.json",
        expected_shards=8,
        require_payload_shard_ids=False,
    )
    summary = tracker.json(root / "results/full/homeo_summary.json")
    sweep_posthoc = tracker.json(root / "results/full/sweep_resolution_posthoc.json")
    position_posthoc = tracker.json(root / "results/full/position_recovery_posthoc.json")
    calculated = recalculate_e30(entries)
    expected_digest = _config_digests()["anatomical_homeostasis"]
    pipeline = (root / "src/anatomical_homeostasis/pipeline.py").read_text(
        encoding="utf-8"
    )
    perturb = (root / "src/anatomical_homeostasis/perturb.py").read_text(
        encoding="utf-8"
    )
    tests = test_path.read_text(encoding="utf-8")
    source_files = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((root / "src").rglob("*.py"))
    )

    position_rows = {}
    for name, row in position_posthoc["rows"].items():
        before = float(row["overlap_right_after_insult"])
        after = float(row["overlap_after_24_sweeps"])
        position_rows[name] = {
            "after_insult": before,
            "after_24_sweeps": after,
            "change": after - before,
            "recovers": after > before,
        }
    return {
        "integrity": {
            "expected_config_digest": expected_digest,
            "summary_config_digest": summary.get("config_digest"),
            "shard_config_digest": shards["config_digest"],
            "config_matches_source_default": (
                summary.get("config_digest") == expected_digest
                and shards["config_digest"] == expected_digest
            ),
            "summary_n_entries": int(summary["n_entries"]),
            "shards": shards,
            "all_summary_gates_and_scalars_match": _recursive_close(
                calculated["source_projection"], summary["gates"]
            ),
        },
        "recalculation": calculated,
        "intervention_validity": {
            "six_named_perturbations": list(PERTURBATIONS),
            "all_branches_intended_charge_neutral": (
                "Every branch is charge-neutral" in perturb
            ),
            "golden_test_checks_analog_sum_and_array_change": (
                "assert_allclose(out.sum" in tests and "not np.allclose(out, V)" in tests
            ),
            "unperturbed_control_arm": False,
            "immediate_pre_and_post_insult_census_retained": False,
            "perturbation_precedes_full_run_generation": (
                "apply_perturbation" in perturb and "run_generation(" in perturb
            ),
            "first_eligible_recovery_census_after_full_generation": True,
            "scored_census_shown_displaced_before_recovery": False,
            "nontrivial_active_repair_established": False,
        },
        "posthoc_sweep_resolution": {
            "payload": sweep_posthoc,
            "generator_present_in_package_source": (
                "sweep_resolution_posthoc" in source_files
            ),
            "raw_trajectory_or_manifest_retained": False,
            "supports_prospective_instant_claim": False,
        },
        "posthoc_position_overlap": {
            "rows": position_rows,
            "all_four_decline": all(not row["recovers"] for row in position_rows.values()),
            "generator_present_in_package_source": (
                "position_recovery_posthoc" in source_files
            ),
            "supports_anatomical_restoration": False,
        },
        "timing_note": {
            "midpath_generation_is_post_dynamics": (
                'row["mid_censuses"] = censuses[p][good].tolist()' in pipeline
            ),
            "instant_is_not_an_immediate_post_insult_measurement": True,
        },
    }


def _verify_hash_manifest(
    tracker: InputTracker, manifest_path: Path
) -> dict[str, Any]:
    path = tracker.add(manifest_path)
    rows = []
    mismatches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, raw_path = line.split(maxsplit=1)
        source = tracker.add(Path(raw_path.strip()))
        actual = sha256_file(source)
        row = {"path": str(source), "expected": expected, "actual": actual}
        rows.append(row)
        if actual != expected:
            mismatches.append(row)
    return {
        "recorded_files": len(rows),
        "matching_files": len(rows) - len(mismatches),
        "all_match": not mismatches,
        "mismatches": mismatches,
    }


def audit_e28_reuse(external_root: Path, tracker: InputTracker) -> dict[str, Any]:
    output = external_root / "outputs" / L4_REUSE_RUN_ID
    run = external_root / "runs" / L4_REUSE_RUN_ID
    prior = tracker.json(output / "audit.json")
    manifest = tracker.json(run / "MANIFEST.json")
    status = tracker.json(run / "STATUS.json")
    tracker.add(output / "audit.md")
    tracker.add(run / "COMPLETE")
    input_integrity = _verify_hash_manifest(tracker, output / "input_hashes.sha256")
    contract_recalculated = canonical_digest(
        {
            "protocols_sha256": manifest["protocols_sha256"],
            "code_sha256": manifest["code_sha256"],
        }
    )
    e28 = prior["e28"]
    paired = e28["retained_gate_recalculation"]["gate1_paired"]
    return {
        "run_id": L4_REUSE_RUN_ID,
        "integrity": {
            "status_complete": status.get("status") == "COMPLETE",
            "manifest_contract_recalculates": (
                contract_recalculated == manifest.get("contract_digest")
            ),
            "audit_contract_matches_manifest": (
                prior.get("contract_digest") == manifest.get("contract_digest")
            ),
            "prior_input_hashes": input_integrity,
            "generation10_control_matches_full_precision": e28[
                "generation10_replay_control"
            ]["all_values_match"],
        },
        "prospective_generation10_memory": {
            "raw_accuracy": float(paired["raw_mean"]),
            "figure_accuracy": float(paired["figure_mean"]),
            "chance": 1 / 6,
            "gate_memory_at_boundaries": bool(
                e28["retained_gate_recalculation"]["calculated"][
                    "gate_memory_at_boundaries"
                ]
            ),
        },
        "posthoc_horizon": {
            "all_six_rounded_values_reproduce": e28["posthoc_horizon"][
                "all_rounded_values_match"
            ],
            "prospective": False,
        },
        "conservation_dependency": e28["conservation_dependency"],
        "reuse_accounting": {
            "fresh_scientific_futures_generated_here": 0,
            "historical_trajectories_replayed_here": 0,
            "historical_trajectories_in_prior_verified_run": int(
                prior["historical_namespace_trajectories_replayed"]
            ),
        },
    }


def _battery2_calculations(components: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ladder = components["ladder"]
    redemption = components["redemption"]
    regime = components["regime"]
    worm = components["worm"]
    placements = components["placements"]
    redemption_in_band = {
        str(rule): 0.005 <= float(value) <= 0.5
        for rule, value in redemption["strict"].items()
    }
    placement_subgates = {
        name: bool(
            float(placements[name]["observed"])
            < float(placements[name]["random_q05"])
            and float(placements[name]["observed"])
            < float(placements[name]["shuffled_q05"])
        )
        for name in ("eca", "tissue")
    }
    return {
        "ladder": bool(
            float(ladder["core3_min_break8"])
            > float(ladder["clean12_median_break8"])
        ),
        "redemption": bool(all(redemption_in_band.values())),
        "regime": bool(
            int(regime["n_band"]) > 0
            and float(regime["band_class2_fraction"]) > 0.5
            and int(regime["core3_in_band"]) == 0
        ),
        "worm": bool(
            float(worm["conversion"]) >= 0.10
            and float(worm["conversion"])
            >= 3 * max(float(worm["reverse"]), 1e-9)
        ),
        "placements": bool(all(placement_subgates.values())),
        "diagnostics": {
            "redemption_in_band": redemption_in_band,
            "placement_subgates": placement_subgates,
        },
    }


def _battery3_calculations(components: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    recovery = components["recovery"]
    training = components["training"]
    equifinality = components["equifinality"]
    amplifier = components["amplifier"]
    generalization = components["generalization"]
    recovery_passing = sum(
        value is not None and float(value) >= 0.6
        for value in recovery["per_type"].values()
    )
    calculated_gap = float(training["trained"]) - float(training["naive"])
    calculated_speedup = float(generalization["naive"]) / max(
        float(generalization["pre"]), 1e-9
    )
    return {
        "recovery": recovery_passing >= 5,
        "training": calculated_gap >= 0.02,
        "equifinality": bool(
            float(equifinality["ratio_D"]) < 0.5
            and float(equifinality["ratio_C"])
            >= float(equifinality["ratio_D"]) + 0.2
        ),
        "amplifier": bool(
            float(amplifier["sub"]) < 1e-6
            and float(amplifier["supra"]) >= 2.5
        ),
        "generalization": calculated_speedup >= 1.5,
        "diagnostics": {
            "recovery_n_passing": recovery_passing,
            "training_gap_recalculated": calculated_gap,
            "training_gap_matches": close(calculated_gap, training["gap"]),
            "generalization_speedup_recalculated": calculated_speedup,
            "generalization_speedup_matches": close(
                calculated_speedup, generalization["speedup"]
            ),
        },
    }


def _load_battery(
    plastic_root: Path,
    tracker: InputTracker,
    package: str,
    component_names: Sequence[str],
) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]]]:
    root = _experiment_root(plastic_root, package)
    _track_package(tracker, root)
    verdict = tracker.json(root / "results/full/battery_verdict.json")
    components = {
        name: tracker.json(root / f"results/full/component_{name}.json")
        for name in component_names
    }
    return root, verdict, components


def audit_sealed_batteries(
    plastic_root: Path, tracker: InputTracker
) -> dict[str, Any]:
    names2 = ("ladder", "redemption", "regime", "worm", "placements")
    _root2, verdict2, components2 = _load_battery(
        plastic_root, tracker, "sealed_battery_2", names2
    )
    names3 = ("recovery", "training", "equifinality", "amplifier", "generalization")
    _root3, verdict3, components3 = _load_battery(
        plastic_root, tracker, "sealed_battery_3", names3
    )
    calculated2 = _battery2_calculations(components2)
    calculated3 = _battery3_calculations(components3)
    gates2 = {name: calculated2[name] for name in names2}
    gates3 = {name: calculated3[name] for name in names3}
    digests = _config_digests()

    return {
        "e34": {
            "integrity": {
                "expected_config_digest": digests["sealed_battery_2"],
                "all_component_config_digests_match": all(
                    payload.get("config_digest") == digests["sealed_battery_2"]
                    for payload in components2.values()
                ),
                "verdict_config_digest_matches": (
                    verdict2.get("config_digest") == digests["sealed_battery_2"]
                ),
                "all_component_gates_recalculate": all(
                    gates2[name] == bool(components2[name]["gate"])
                    for name in names2
                ),
                "battery_rollup_matches": gates2 == verdict2["verdict"],
                "n_survived_matches": sum(gates2.values())
                == int(verdict2["n_survived"]),
            },
            "calculated_gates": gates2,
            "diagnostics": calculated2["diagnostics"],
            "l5_relevant_component": {
                "name": "worm",
                "conversion": float(components2["worm"]["conversion"]),
                "reverse": float(components2["worm"]["reverse"]),
                "gate": gates2["worm"],
                "fresh_tissue_indices": "100-123",
                "tests_rewrite_conversion": True,
                "tests_lesion_recovery": False,
                "tests_rewritten_vs_wild_stability": False,
                "tests_anatomy": False,
                "tests_conservation_ablation": False,
            },
        },
        "e47": {
            "integrity": {
                "expected_config_digest": digests["sealed_battery_3"],
                "all_component_config_digests_match": all(
                    payload.get("config_digest") == digests["sealed_battery_3"]
                    for payload in components3.values()
                ),
                "verdict_config_digest_matches": (
                    verdict3.get("config_digest") == digests["sealed_battery_3"]
                ),
                "all_component_gates_recalculate": all(
                    gates3[name] == bool(components3[name]["gate"])
                    for name in names3
                ),
                "battery_rollup_matches": gates3 == verdict3["verdict"],
                "n_survived_matches": sum(gates3.values())
                == int(verdict3["n_survived"]),
            },
            "calculated_gates": gates3,
            "diagnostics": calculated3["diagnostics"],
            "l5_relevant_component": {
                "name": "recovery",
                "per_type": components3["recovery"]["per_type"],
                "n_passing": calculated3["diagnostics"]["recovery_n_passing"],
                "gate": gates3["recovery"],
                "fresh_tissue_indices": "300-307",
                "tests_post_generation_rewritten_texture_similarity": True,
                "wild_comparator": False,
                "immediate_injury_efficacy_measurement": False,
                "position_sensitive_endpoint": False,
                "tests_conservation_ablation": False,
            },
        },
        "coverage_conclusion": {
            "freshness_applies_to_named_streams_or_tissues": True,
            "e34_reseals_promoted_canalization_clause": False,
            "e47_reseals_nontrivial_instant_repair_clause": False,
            "either_reseals_bulk_memory_clause": False,
            "either_reseals_conservation_causality_clause": False,
            "all_promoted_l5_clauses_independently_retested": False,
        },
    }


def quantity_map(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    ideas = plastic_root / IDEAS_RELATIVE
    voltage = _experiment_root(plastic_root, "voltage_web")
    figure = _experiment_root(plastic_root, "figure_ground_voltage")
    _track_package(tracker, voltage)
    _track_package(tracker, figure)
    engine = (voltage / "src/voltage_web/engine.py").read_text(encoding="utf-8")
    observer = (figure / "src/figure_ground_voltage/observer.py").read_text(
        encoding="utf-8"
    )
    return {
        "Q": {
            "definition": "continuous analog sheet mean/sum of V",
            "physics_protection": "drift and noise are mean-centred within sheet_step",
            "code_trace_found": (
                "drift = drift - drift.mean" in engine
                and "noise = noise - noise.mean" in engine
            ),
            "exactly_preserved_after_clip_clamp_and_fission": False,
            "used_as_e26_e27_e30_similarity_endpoint": False,
            "used_as_e28_seed_classifier": False,
        },
        "C_gen": {
            "definition": (
                "normalized 15-coordinate census of 2x2 binary V>0 blocks, "
                "accumulated across sweeps in a generation"
            ),
            "code_trace_found": (
                "census[idx] += block_counts(updated)" in engine
                and "spectrum = census /" in engine
            ),
            "used_for_e26_inheritance": True,
            "used_for_e27_rewrite_and_recovery": True,
            "used_for_e30_recovery": True,
            "explicitly_conserved_by_sheet_step": False,
        },
        "C_snap": {
            "definition": "normalized 15-coordinate census of one binary V>0 snapshot",
            "code_trace_found": (
                "census15(binary" in observer and "block_counts(binary)" in observer
            ),
            "used_for_e28_raw_seed_classification": True,
            "identical_to_generation_averaged_C_gen": False,
            "identical_to_analog_Q": False,
        },
        "P": {
            "definition": "position-sensitive cell-wise overlap used only post hoc",
            "used_in_registered_e26_e27_e30_gates": False,
            "restored_in_retained_e30_posthoc_rows": False,
        },
        "identity_assessment": {
            "common_numerical_observable_across_inherited_defended_remembered": False,
            "proved_mapping_Q_to_C_gen_or_C_snap": False,
            "same_substrate_is_not_same_quantity": True,
            "law_same_quantity_clause_supported": False,
        },
    }


def _track_context_documents(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    ideas = plastic_root / IDEAS_RELATIVE
    workspace = Path(__file__).resolve().parents[2]
    laws_path = tracker.add(ideas / "LAWS.md")
    discovery_path = tracker.add(ideas / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md")
    wave7_path = tracker.add(ideas / "WAVE7_PROPHECIES.md")
    wave10_path = tracker.add(ideas / "WAVE10_PROPHECIES.md")
    manuscript_path = tracker.add(plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md")
    baseline_path = tracker.add(workspace / "SOURCE_BASELINE.md")
    laws = laws_path.read_text(encoding="utf-8")
    discovery = discovery_path.read_text(encoding="utf-8")
    wave7 = wave7_path.read_text(encoding="utf-8")
    wave10 = wave10_path.read_text(encoding="utf-8")
    baseline = baseline_path.read_text(encoding="utf-8")
    return {
        "l5_source_text_present": "L5 — Conservation-selfhood" in laws,
        "source_later_calls_model_two_textured": "two-TEXTURED worm" in discovery,
        "e34_prophecy_in_wave7": "P34.4 Two-headed worm" in wave7,
        "e47_prophecy_in_wave10": "P47.1 E30 recovery" in wave10,
        "manuscript_v2_3_path": str(manuscript_path),
        "source_baseline_records_no_bioelectric_sheet_evidence": (
            "does not report the bioelectric-sheet" in baseline
        ),
        "manuscript_supplies_independent_l5_confirmation": False,
        "biological_data_in_l5_evidence_chain": False,
    }


def run_l5_audit(
    plastic_root: Path, external_root: Path
) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    context = _track_context_documents(plastic_root, tracker)
    audit = {
        "schema_version": 1,
        "scope": "L05 outcome-known retained conservation-selfhood audit",
        "outcome_blinding": "none; all retained outcomes were known",
        "fresh_scientific_futures_generated": 0,
        "historical_namespace_trajectories_replayed": 0,
        "quantity_map": quantity_map(plastic_root, tracker),
        "e26": audit_e26(plastic_root, tracker),
        "e27": audit_e27(plastic_root, tracker),
        "e28_reuse": audit_e28_reuse(external_root, tracker),
        "e30": audit_e30(plastic_root, tracker),
        "sealed_batteries": audit_sealed_batteries(plastic_root, tracker),
        "document_context": context,
        "first_pass_adjudication": {
            "overall_verdict": "MIXED",
            "same_quantity_clause": "REFUTED_BY_OPERATIONAL_DEFINITIONS",
            "six_neutral_post_generation_similarity_clause": "SUPPORTED_NARROWLY",
            "nontrivial_instant_homeostasis_clause": "NOT_CONFIRMED",
            "induced_setpoints_more_stable_than_originals": "NOT_CONFIRMED",
            "bulk_conserved_quantity_stores_memory": "NOT_CONFIRMED",
            "sealed_batteries_retest_all_promoted_clauses": "REFUTED",
            "biological_bench_prediction": "UNTESTED",
        },
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, sorted(tracker.paths)


def markdown_report(audit: Mapping[str, Any]) -> str:
    e26 = audit["e26"]
    e27 = audit["e27"]
    e28 = audit["e28_reuse"]
    e30 = audit["e30"]
    batteries = audit["sealed_batteries"]
    e27g = e27["recalculation"]["source_projection"]
    e27d = e27["recalculation"]["recovery_contrast"]
    e30g = e30["recalculation"]["source_projection"]
    e30d = e30["recalculation"]["recovery_contrast"]
    lines = [
        "# L05 retained conservation-selfhood audit v1",
        "",
        "This is an outcome-known recalculation of retained artefacts. It generated no scientific trajectories.",
        "",
        "## Integrity",
        "",
        f"- Input files hashed: {audit['input_file_count']}",
        f"- Fresh scientific futures: {audit['fresh_scientific_futures_generated']}",
        f"- Historical trajectories replayed: {audit['historical_namespace_trajectories_replayed']}",
        f"- E26 screen/regeneration calculations match retained gates: {e26['integrity']['screen_grid_gate_recalculation_matches']} / {e26['integrity']['regeneration_gate_recalculation_matches']}",
        f"- E27 all retained scalars/gates reconstruct: {e27['integrity']['all_summary_gates_and_scalars_match']}",
        f"- E30 all retained scalars/gates reconstruct: {e30['integrity']['all_summary_gates_and_scalars_match']}",
        f"- Prior L4/E28 result contract and inputs verify: {e28['integrity']['audit_contract_matches_manifest']} / {e28['integrity']['prior_input_hashes']['all_match']}",
        f"- E34/E47 component gates and roll-ups reconstruct: {batteries['e34']['integrity']['all_component_gates_recalculate']} / {batteries['e47']['integrity']['all_component_gates_recalculate']}",
        "",
        "## The quantities are not the same",
        "",
        "- `Q` is the continuous analog sheet mean/sum. Drift and noise are mean-centred within a step, but clipping and clamps follow, and fission resets half the daughter before adding uncentred jitter.",
        "- `C_gen` is a normalized 15-bin census of binary 2x2 textures averaged over a generation; E26, E27, and E30 score this.",
        "- `C_snap` is a 15-bin census of one binary snapshot; E28 uses this for raw seed classification. `P` is a separate position-sensitive overlap used only post hoc.",
        "- No common observable or proved mapping makes inherited, defended, remembered, and physically conserved quantities numerically identical.",
        "",
        "## E26 and E27",
        "",
        f"- E26 screen passing cells: {e26['screen']['calculated']['n_passing']} of {e26['screen']['grid_rows']}; the sole point is {e26['screen']['calculated']['best']}.",
        f"- Full E26 fragment/random mean similarity: {e26['regeneration']['calculated_fragment_mean']:.6f} / {e26['regeneration']['calculated_random_fragment_mean']:.6f}; difference {e26['regeneration']['fragment_minus_random_mean']:.6f}.",
        "- The E26 development rounds are not a matched conserved-versus-leaky ablation, so they do not isolate conservation as the cause.",
        f"- E27 zap conversion/reverse: {e27g['paired_conversion']:.6f} / {e27g['paired_reverse']:.6f}; rewrite gate {e27g['gate_rewrite_exists']}.",
        f"- E27 band/under/over conversion: {e27g['paired_conversion']:.6f} / {e27g['under_conversion']:.6f} / {e27g['over_conversion']:.6f}; regime gate {e27g['gate_regime_dependence']}.",
        f"- E27 rewritten/wild recovery: {e27g['rewritten_recovery']:.6f} / {e27g['wild_recovery']:.6f}; registered two-setpoint gate {e27g['gate_two_setpoints_canalized']} under both the declared .6/.7 and implemented .7/.7 bars.",
        f"- Rewritten-minus-wild equal-tissue difference: {e27d['equal_tissue_rewritten_minus_wild']:.6f}; descriptive tissue bootstrap 95% interval {e27d['bootstrap']['percentile_95']}; directions {e27d['directions']['positive']}/{e27d['directions']['ties']}/{e27d['directions']['negative']}.",
        "- That recovery comparison is post-treatment: `rewritten` means the lineage was observed to respond to the zap. It is not a randomized basin-depth comparison, and the endpoint is texture rather than anatomy.",
        "",
        "## E30 recovery",
        "",
        f"- Rewritten recovery exceeds .6 for {e30g['n_types_passing']}/6 types; the retained recovery gate is {e30g['gate_recovery']}.",
        f"- Rewritten/wild means are {e30g['rewritten_mean']:.6f} / {e30g['wild_mean']:.6f}; the preregistered asymmetry gate is {e30g['gate_asymmetry']}.",
        f"- Only {e30d['per_type_directions']['positive']}/6 perturbation types favour rewritten tissue; the paired-tissue mean difference is {e30d['paired_tissue_mean_rewritten_minus_wild']:.6f}, bootstrap interval {e30d['bootstrap']['percentile_95']}.",
        f"- Endpoint/midpath dispersion is {e30g['endpoint_dispersion']:.8g} / {e30g['midpath_dispersion']:.8g}; equifinality gate {e30g['gate_equifinality']}.",
        "- The six operations conserve analog sum and change a test array, but no retained measurement shows that the scored census was injured before the first post-generation recovery sample. There is no unperturbed control.",
        f"- All four post-hoc cell-wise overlaps decline: {e30['posthoc_position_overlap']['all_four_decline']}. The aggregate one-sweep claim has no retained generator, raw trajectory, or manifest.",
        "",
        "## E28 and sealed batteries",
        "",
        f"- E28 prospective generation-10 raw/figure seed accuracy is {e28['prospective_generation10_memory']['raw_accuracy']:.6f} / {e28['prospective_generation10_memory']['figure_accuracy']:.6f} versus chance {e28['prospective_generation10_memory']['chance']:.6f}; gate {e28['prospective_generation10_memory']['gate_memory_at_boundaries']}.",
        f"- E28's saved short-horizon table reproduces at all six rounded cells: {e28['posthoc_horizon']['all_six_rounded_values_reproduce']}. No conservation ablation exists.",
        f"- E34 worm reseal: conversion {batteries['e34']['l5_relevant_component']['conversion']:.6f}, reverse {batteries['e34']['l5_relevant_component']['reverse']:.6f}. It does not retest recovery or rewritten-versus-wild stability.",
        f"- E47 recovery reseal: {batteries['e47']['l5_relevant_component']['n_passing']}/6 types. It has no wild comparator, immediate injury measurement, positional endpoint, or conservation ablation.",
        "",
        "## First-pass verdict",
        "",
        "- MIXED. The retained arithmetic supports a bounded zap-induced texture rewrite and high post-generation texture similarity after six charge-neutral transformations.",
        "- The law is not confirmed as written: the conserved, inherited, defended, and remembered observables are different; nontrivial instant repair is not established; the preregistered rewritten-greater-than-wild comparison fails in E30; and E28's prospective memory gate fails.",
        "- The batteries freshly repeat only narrower component endpoints. Neither establishes conservation causality, anatomical two-headed regeneration, or the biological prediction that reprogrammed setpoints outlast wild type.",
        "",
    ]
    return "\n".join(lines)
