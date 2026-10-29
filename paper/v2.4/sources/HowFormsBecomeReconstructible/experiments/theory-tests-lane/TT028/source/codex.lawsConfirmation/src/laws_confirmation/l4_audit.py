"""Outcome-known retained/replay audit for L04.

The only simulations here replay E28's historical namespace through the
post-hoc generation-2/4/6 horizon plus a generation-10 control. No fresh seed
domain is generated.
"""

from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .eca_math import CLASS_3_CORE, seed_rng
from .io import canonical_digest
from .observer_math import (
    coverage_diagnostics,
    e25_gate_recalculation,
    e28_gate_recalculation,
    e63_criteria,
    in_band,
    nearest_centroid_accuracy,
    screen_census,
)
from .stats import close


CLASS4 = (110, 54, 41, 106)
CHAMPIONS = (35, 43, 11, 57, 184)
STRICT_BAND = (0.005, 0.5)
E28_POSTHOC_HORIZONS = (2, 4, 6)
E28_CONTROL_GENERATION = 10
E28_HORIZONS = E28_POSTHOC_HORIZONS + (E28_CONTROL_GENERATION,)
E28_REPLAY_TRAJECTORIES = 12 * 6 * 64


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def _track_package(tracker: InputTracker, root: Path) -> None:
    tracker.add(root / "EXPECTATIONS.md")
    for path in sorted((root / "src").rglob("*.py")):
        tracker.add(path)


def _config_digests() -> dict[str, str]:
    particle = {
        "mode": "full",
        "dict_seeds": 4,
        "burn_in_sweeps": 64,
        "collect_sweeps": 16,
        "coverage_target": 0.9,
        "max_dict_codes": 64,
        "futures": 128,
        "strict_band": (0.005, 0.5),
        "dict_seed_tag": "particle-dict-v1",
        "trajectory_seed_tag": "particle-traj-v1",
    }
    figure = {
        "mode": "full",
        "settle_sweeps": 200,
        "collect_sweeps": 20,
        "dict_seeds": 2,
        "coverage_target": 0.9,
        "max_dict_codes": 64,
        "gate1_seeds": 6,
        "gate1_futures": 64,
        "snapshot_generation": 10,
        "gate2_seeds": 4,
        "gate2_futures": 32,
        "patch_sides": (0, 4, 8, 12),
        "gate3_futures": 64,
        "gate3_horizon": 16,
        "dict_seed_tag": "figure-dict-v1",
        "trajectory_seed_tag": "figure-traj-v1",
    }
    position = {
        "mode": "full",
        "home_side": 32,
        "n_tissues": 6,
        "lineages_per_tissue": 4,
        "generations": 6,
        "futures": 8,
        "settle_sweeps": 120,
        "sweeps_per_gen": 60,
        "consensus_seeds": 6,
        "consensus_low_bar": 0.5,
        "clone_dt_gens": 1,
        "clone_noise": 0.05,
        "pilot_pairs": 30,
        "max_pairs": 200,
        "target_delta": 0.03,
        "gauge_offsets": 16,
        "smooth_steps": 10,
        "max_shift": 3,
        "trajectory_seed_tag": "position-obs-v3",
    }
    kuramoto = {
        "mode": "full",
        "height": 32,
        "width": 32,
        "dt": 0.1,
        "omega_spread": 0.5,
        "steps_per_generation": 40,
        "futures": 24,
        "n_tissues": 6,
        "screen_horizon": 12,
        "strict_horizon": 32,
        "n_launch_seeds": 12,
        "null_pairs": 200,
        "alive_window": 3,
        "alive_null_samples": 2000,
        "survival_bar": 0.3,
        "zap_generation": 3,
        "hold_generations": 8,
        "train_generations": (5, 7, 9),
        "test_generation": 11,
        "probe_settle_gens": 8,
        "probe_horizon_gens": 20,
        "consensus_launches": 6,
        "tissue_tag": "kuramoto-omega-v1",
        "binarization": "freq",
        "trajectory_seed_tag": "kuramoto-traj-v2-freq",
    }
    gray_scott = {
        "mode": "full",
        "height": 32,
        "width": 32,
        "du": 0.16,
        "dv": 0.08,
        "dt": 1.0,
        "v_noise": 0.002,
        "f_jitter": 0.004,
        "embryo_steps": 2000,
        "steps_per_generation": 400,
        "census_stride": 10,
        "futures": 24,
        "n_tissues": 6,
        "screen_horizon": 12,
        "n_launch_seeds": 12,
        "reseed_v_noise": 0.02,
        "alive_eps": 0.05,
        "null_pairs": 200,
        "survival_bar": 0.3,
        "zap_generation": 3,
        "hold_generations": 8,
        "train_generations": (5, 7, 9),
        "test_generation": 11,
        "probe_settle_gens": 4,
        "probe_horizon_gens": 10,
        "consensus_launches": 6,
        "spectral_tripwire": 0.10,
        "tissue_tag": "grayscott-jitter-v1",
        "trajectory_seed_tag": "grayscott-traj-v1",
    }
    return {
        name: canonical_digest(value)
        for name, value in {
            "particle_observer": particle,
            "figure_ground_voltage": figure,
            "position_observer": position,
            "kuramoto_web": kuramoto,
            "grayscott_web": gray_scott,
        }.items()
    }


def source_config_digests() -> dict[str, str]:
    """Expose independently transcribed defaults for unit tests."""

    return _config_digests()


def _standardize_e25(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rule": int(row["rule"]),
        "coverage": float(row["dict_coverage"]),
        "dictionary_size": int(row["dict_dict_size"]),
        "strict": float(row["strict"]),
    }


def audit_e25(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "particle_observer")
    _track_package(tracker, root)
    dev = tracker.json(root / "results/full/dev_round.json")
    gates = tracker.json(root / "results/full/particle_gates.json")
    expected_digest = _config_digests()["particle_observer"]
    recalculated = e25_gate_recalculation(
        gates["rows"], class4=CLASS4, core3=sorted(CLASS_3_CORE),
        champions=CHAMPIONS, band=STRICT_BAND,
    )
    stored_projection = {
        key: gates["gates"][key]
        for key in (
            "gate_redemption_110",
            "gate_chaos_stays_chaos",
            "gate_champions_stable",
            "class4_strict",
            "core3_strict_max",
            "champions_strict",
        )
    }
    calculated_projection = {
        key: recalculated[key]
        for key in stored_projection
    }
    selected = [_standardize_e25(row) for row in gates["rows"]]
    all_rows = selected + [_standardize_e25(row) for row in dev["rows"]]
    return {
        "integrity": {
            "expected_config_digest": expected_digest,
            "gate_config_digest": gates.get("config_digest"),
            "dev_config_digest": dev.get("config_digest"),
            "config_matches_source_default": (
                gates.get("config_digest") == expected_digest
                and dev.get("config_digest") == expected_digest
            ),
            "gate_rows": len(gates["rows"]),
            "dev_rows": len(dev["rows"]),
            "unique_gate_rules": len({int(row["rule"]) for row in gates["rows"]}),
        },
        "calculated_gates": recalculated,
        "stored_gate_projection": stored_projection,
        "stored_gates_match": calculated_projection == stored_projection,
        "coverage_diagnostics_selected_gate_rows": coverage_diagnostics(selected),
        "coverage_diagnostics_gate_plus_dev_rows": coverage_diagnostics(all_rows),
        "interpretation": {
            "coverage_test_preregistered_in_e25": False,
            "rule_population_random_or_exhaustive": False,
            "dictionary_is_rule_conditioned": True,
            "compressibility_is_necessary_gate_in_observer_code": False,
        },
    }


def _a1_condition_map(result: Mapping[str, Any], observer: str) -> dict[tuple[int, int, float], dict]:
    rows: dict[tuple[int, int, float], dict] = {}
    for panel in result["panels"]:
        if panel["observer"] != observer:
            continue
        for condition in panel["conditions"]:
            key = (int(panel["rule"]), int(panel["width"]), float(condition["flip_noise"]))
            if key in rows:
                raise ValueError(f"duplicate A1 cell {key}")
            rows[key] = {"panel": panel, "condition": condition}
    return rows


def audit_fresh_a1(external_root: Path, tracker: InputTracker) -> dict[str, Any]:
    run_id = "l01_l02_stage_d_a1_v1"
    output = external_root / "outputs" / run_id
    run = external_root / "runs" / run_id
    result = tracker.json(output / "RESULTS.json")
    manifest = tracker.json(run / "MANIFEST.json")
    status = tracker.json(run / "STATUS.json")
    tracker.add(output / "REPORT.md")
    tracker.add(output / "checkpoint_hashes.sha256")
    particle = _a1_condition_map(result, "particle4")
    raw = _a1_condition_map(result, "raw4")

    def rates(rule: int, width: int, eta: float, observer_rows: Mapping) -> dict[str, float]:
        cell = observer_rows[(rule, width, eta)]["condition"]["partitions"]
        return {name: float(cell[name]["strict"]["rate"])
                for name in ("combined", "primary", "holdout")}

    anchor = {}
    for rule in CLASS4:
        particle_rates = rates(rule, 64, 0.01, particle)
        raw_rates = rates(rule, 64, 0.01, raw)
        anchor[str(rule)] = {
            "particle": particle_rates,
            "raw": raw_rates,
            "particle_in_band": {
                name: in_band(value, STRICT_BAND)
                for name, value in particle_rates.items()
            },
            "particle_minus_raw": {
                name: particle_rates[name] - raw_rates[name]
                for name in particle_rates
            },
        }

    width_stress = {}
    for width in (63, 64, 65, 128):
        per_rule = {}
        for rule in CLASS4:
            values = rates(rule, width, 0.01, particle)
            per_rule[str(rule)] = {
                "rates": values,
                "combined_in_band": in_band(values["combined"], STRICT_BAND),
                "both_halves_in_band": all(
                    in_band(values[name], STRICT_BAND)
                    for name in ("primary", "holdout")
                ),
            }
        width_stress[str(width)] = {
            "rules": per_rule,
            "combined_count_in_band": sum(
                row["combined_in_band"] for row in per_rule.values()
            ),
            "split_count_in_band": sum(
                row["both_halves_in_band"] for row in per_rule.values()
            ),
        }

    noise_stress = {}
    for eta in (0.0025, 0.005, 0.01, 0.02, 0.03, 0.04, 0.08):
        values = {str(rule): rates(rule, 64, eta, particle) for rule in CLASS4}
        noise_stress[str(eta)] = {
            "rules": values,
            "combined_count_in_band": sum(
                in_band(value["combined"], STRICT_BAND) for value in values.values()
            ),
            "split_count_in_band": sum(
                all(in_band(value[name], STRICT_BAND)
                    for name in ("primary", "holdout"))
                for value in values.values()
            ),
        }

    coverage_by_width = {}
    for width in (63, 64, 65, 128):
        rows = []
        for panel in result["panels"]:
            if panel["observer"] != "particle4" or int(panel["width"]) != width:
                continue
            condition = next(
                item for item in panel["conditions"]
                if close(float(item["flip_noise"]), 0.01)
            )
            rows.append({
                "rule": int(panel["rule"]),
                "coverage": float(panel["dictionary"]["coverage"]),
                "dictionary_size": int(panel["dictionary"]["dictionary_size"]),
                "strict": float(condition["partitions"]["combined"]["strict"]["rate"]),
            })
        coverage_by_width[str(width)] = coverage_diagnostics(rows)

    return {
        "integrity": {
            "run_id": result.get("run_id"),
            "result_and_manifest_contract_match": (
                result.get("contract_digest") == manifest.get("contract_digest")
            ),
            "status_complete": status.get("status") == "COMPLETE",
            "replay_integrity": result.get("replay_integrity"),
            "scientific_future_count": result.get("scientific_future_count"),
            "particle_rules": len(result["design"]["particle_rules"]),
        },
        "class4_anchor_width64_eta001": anchor,
        "all_four_anchor_combined": all(
            row["particle_in_band"]["combined"] for row in anchor.values()
        ),
        "all_four_anchor_both_halves": all(
            row["particle_in_band"]["primary"]
            and row["particle_in_band"]["holdout"] for row in anchor.values()
        ),
        "width_stress": width_stress,
        "noise_stress_width64": noise_stress,
        "coverage_diagnostics_at_eta001": coverage_by_width,
        "interpretation": {
            "a1_contract_frozen_before_l4_review": True,
            "l4_reuse_outcome_known": True,
            "fresh_seed_domain_for_original_observer_contrasts": True,
            "fresh_compressibility_gate": False,
        },
    }


def _install_source_paths(plastic_root: Path) -> None:
    ideas = plastic_root / IDEAS_RELATIVE
    packages = (
        "contract_bridge",
        "xeno_bridge",
        "glider_test",
        "voltage_web",
        "setpoint_rewrite",
        "figure_ground_voltage",
    )
    for name in reversed(packages):
        source = str((ideas / name / "src").resolve())
        if source not in sys.path:
            sys.path.insert(0, source)


def replay_e28_horizons(plastic_root: Path) -> dict[str, Any]:
    """Replay the retained post-hoc snapshot sweep with an independent scorer."""

    _install_source_paths(plastic_root)
    from figure_ground_voltage.config import FigureConfig
    from figure_ground_voltage.observer import (
        build_dictionary,
        census15,
        figure_mask,
        run_snapshot_lineage,
    )
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config

    config = FigureConfig()
    rewrite = RewriteConfig()
    by_horizon: dict[int, dict[str, list[float]]] = {
        generation: {"raw": [], "figure": []} for generation in E28_HORIZONS
    }
    for index in range(12):
        tissue = tissue_config(index, rewrite.coupling_band, rewrite)
        dictionary, _ = build_dictionary(tissue, config)
        stored: dict[int, dict[str, list[np.ndarray]]] = {
            generation: {"raw": [], "figure": [], "labels": []}
            for generation in E28_HORIZONS
        }
        for seed in range(config.gate1_seeds):
            out = run_snapshot_lineage(
                seed,
                tissue,
                config,
                seed_rng(config.trajectory_seed_tag, index, seed),
                config.gate1_futures,
                max(E28_HORIZONS) + 1,
            )
            for generation in E28_HORIZONS:
                live = out["alive"][generation]
                grids = out["grids"][generation][live]
                if len(grids) < 8:
                    continue
                stored[generation]["raw"].append(census15(grids))
                stored[generation]["figure"].append(
                    census15(figure_mask(grids, dictionary))
                )
                stored[generation]["labels"].append(
                    np.full(len(grids), seed, dtype=np.int64)
                )
        for generation in E28_HORIZONS:
            labels = np.concatenate(stored[generation]["labels"])
            raw_features = np.vstack(stored[generation]["raw"])
            figure_features = np.vstack(stored[generation]["figure"])
            train = seed_rng("figure-split-v1", index).random(len(labels)) < 0.5
            by_horizon[generation]["raw"].append(
                nearest_centroid_accuracy(raw_features, labels, train)
            )
            by_horizon[generation]["figure"].append(
                nearest_centroid_accuracy(figure_features, labels, train)
            )
    return {
        str(generation): {
            "raw": float(np.mean(values["raw"])),
            "figure": float(np.mean(values["figure"])),
            "per_tissue_raw": values["raw"],
            "per_tissue_figure": values["figure"],
        }
        for generation, values in by_horizon.items()
    }


def audit_e28(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    ideas = plastic_root / IDEAS_RELATIVE
    root = ideas / "figure_ground_voltage"
    for package in (
        "figure_ground_voltage", "setpoint_rewrite", "voltage_web",
        "contract_bridge", "glider_test", "xeno_bridge",
    ):
        _track_package(tracker, ideas / package)
    summary = tracker.json(root / "results/full/figure_summary.json")
    posthoc = tracker.json(root / "results/full/gate1_posthoc_horizon.json")
    expected_digest = _config_digests()["figure_ground_voltage"]
    recalculated = e28_gate_recalculation(summary)
    replay = replay_e28_horizons(plastic_root)
    rounded_matches = {
        generation: {
            name: round(float(replay[generation][name]), 3)
            == round(float(posthoc["rows"][generation][name]), 3)
            for name in ("raw", "figure")
        }
        for generation in map(str, E28_POSTHOC_HORIZONS)
    }
    control_replay = replay[str(E28_CONTROL_GENERATION)]
    retained_gate1 = summary["gate1"]
    control_matches = {
        "raw_mean": math.isclose(
            float(control_replay["raw"]),
            float(retained_gate1["raw_accuracy"]),
            abs_tol=1e-12,
            rel_tol=0.0,
        ),
        "figure_mean": math.isclose(
            float(control_replay["figure"]),
            float(retained_gate1["figure_accuracy"]),
            abs_tol=1e-12,
            rel_tol=0.0,
        ),
        "per_tissue_raw": (
            len(control_replay["per_tissue_raw"])
            == len(retained_gate1["per_tissue_raw"])
            and all(
                math.isclose(
                    float(actual), float(expected), abs_tol=1e-12, rel_tol=0.0
                )
                for actual, expected in zip(
                    control_replay["per_tissue_raw"],
                    retained_gate1["per_tissue_raw"],
                )
            )
        ),
        "per_tissue_figure": (
            len(control_replay["per_tissue_figure"])
            == len(retained_gate1["per_tissue_figure"])
            and all(
                math.isclose(
                    float(actual), float(expected), abs_tol=1e-12, rel_tol=0.0
                )
                for actual, expected in zip(
                    control_replay["per_tissue_figure"],
                    retained_gate1["per_tissue_figure"],
                )
            )
        ),
    }
    voltage_source = tracker.add(ideas / "voltage_web/src/voltage_web/engine.py").read_text()
    figure_source = tracker.add(
        root / "src/figure_ground_voltage/observer.py"
    ).read_text()
    return {
        "integrity": {
            "expected_config_digest": expected_digest,
            "summary_config_digest": summary.get("config_digest"),
            "config_matches_source_default": summary.get("config_digest") == expected_digest,
            "all_stored_gates_match": recalculated["all_stored_gates_match"],
        },
        "retained_gate_recalculation": recalculated,
        "posthoc_horizon": {
            "retained": posthoc,
            "replay": replay,
            "rounded_three_decimal_matches": rounded_matches,
            "all_rounded_values_match": all(
                all(values.values()) for values in rounded_matches.values()
            ),
            "historical_namespace_trajectories_replayed": E28_REPLAY_TRAJECTORIES,
            "fresh_seed_domain": False,
            "prospective": False,
        },
        "generation10_replay_control": {
            "retained": {
                "raw": float(retained_gate1["raw_accuracy"]),
                "figure": float(retained_gate1["figure_accuracy"]),
                "per_tissue_raw": retained_gate1["per_tissue_raw"],
                "per_tissue_figure": retained_gate1["per_tissue_figure"],
            },
            "replay": control_replay,
            "absolute_tolerance": 1e-12,
            "matches": control_matches,
            "all_values_match": all(control_matches.values()),
        },
        "conservation_dependency": {
            "drift_centered_within_step": "drift = drift - drift.mean" in voltage_source,
            "noise_centered_within_step": "noise = noise - noise.mean" in voltage_source,
            "clip_after_centering": "V = np.clip(V, -2.0, 2.0)" in voltage_source,
            "fission_resets_half_to_resting": "offspring = np.full_like(V, config.resting)" in voltage_source,
            "raw_observer_is_binarized_block_census": (
                "census15(binary" in figure_source and "block_counts(binary)" in figure_source
            ),
            "matched_conserved_vs_nonconserved_ablation": False,
            "causal_because_supported": False,
        },
    }


def audit_alien_screens(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    results = {}
    specs = (
        ("kuramoto", "kuramoto_web"),
        ("grayscott", "grayscott_web"),
    )
    for label, package in specs:
        root = _experiment_root(plastic_root, package)
        _track_package(tracker, root)
        screen = tracker.json(root / "results/full/screen_summary.json")
        battery = tracker.json(root / "results/full/battery_summary.json")
        code = tracker.add(root / f"src/{package}/pipeline.py").read_text()
        row = {
            "integrity": {
                "expected_config_digest": _config_digests()[package],
                "summary_config_digest": screen.get("config_digest"),
                "config_matches_source_default": (
                    screen.get("config_digest") == _config_digests()[package]
                ),
            },
            "screen": screen_census(screen["rows"]),
            "chosen_operating_point": screen.get("chosen"),
            "battery_uninstrumented_label": battery.get("uninstrumented"),
            "battery_label_triggered_by_no_chosen_point": (
                "if chosen is None:" in code and screen.get("chosen") is None
            ),
            "interpretation": (
                "no row passed the combined instrumentation, inheritance, "
                "break, survival, and substrate-validity screen"
            ),
        }
        if label == "kuramoto":
            diagnostic = tracker.json(root / "results/full/identity_diagnostic.json")
            row["snapshot_texture_identity_diagnostic"] = diagnostic
        results[label] = row
    return results


def audit_e63(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "position_observer")
    _track_package(tracker, root)
    summary = tracker.json(root / "results/full/position_summary.json")
    expectations_path = tracker.add(root / "EXPECTATIONS.md")
    pipeline_path = tracker.add(root / "src/position_observer/pipeline.py")
    expectations = expectations_path.read_text(encoding="utf-8")
    pipeline = pipeline_path.read_text(encoding="utf-8")
    expected_digest = _config_digests()["position_observer"]
    rows = summary["gates"]["rows"]
    calculations = {name: e63_criteria(row) for name, row in rows.items()}
    cache_matches = {}
    for name, row in rows.items():
        cache = tracker.json(root / f"results/full/work/pos_{name}.json")
        cache_matches[name] = {
            "config_matches": cache.get("config_digest") == expected_digest,
            "aggregate_row_matches_before_r4_fields": all(
                cache["row"].get(key) == value
                for key, value in row.items()
                if key not in ("instrumented_r4", "individuality_r4")
            ),
            "cache_has_round4_fields": any(
                key in cache["row"] for key in ("instrumented_r4", "individuality_r4")
            ),
        }
    stored_match = {
        name: {
            "registered_instrumented": values["registered"]["instrumented"]
            == bool(rows[name]["instrumented"]),
            "registered_individuality": values["registered"]["individuality"]
            == bool(rows[name]["individuality"]),
            "round4_instrumented": values["round4_revision"]["instrumented"]
            == bool(rows[name]["instrumented_r4"]),
            "round4_individuality": values["round4_revision"]["individuality"]
            == bool(rows[name]["individuality_r4"]),
        }
        for name, values in calculations.items()
    }
    revised = {
        name: values["round4_revision"]["individuality"]
        for name, values in calculations.items()
    }
    registered = {
        name: values["registered"]["individuality"]
        for name, values in calculations.items()
    }
    return {
        "integrity": {
            "expected_config_digest": expected_digest,
            "summary_config_digest": summary.get("config_digest"),
            "config_matches_source_default": summary.get("config_digest") == expected_digest,
            "cached_rows": cache_matches,
            "all_stored_decisions_match": all(
                all(values.values()) for values in stored_match.values()
            ),
            "summary_elapsed_seconds": summary.get("elapsed_seconds"),
        },
        "substrates": calculations,
        "stored_decision_match": stored_match,
        "registered_all_individuality": all(registered.values()),
        "registered_any_individuality": any(registered.values()),
        "round4_all_individuality": all(revised.values()),
        "round4_gate_stored": bool(summary["gates"]["gate_p63_1_primary"]),
        "round4_fork_stored": summary["gates"]["fork"],
        "chronology": {
            "expectations_round_headings": expectations.count("## ROUND"),
            "expectations_records_round1": "## ROUND 1" in expectations,
            "expectations_records_round2": "## ROUND 2" in expectations,
            "expectations_announces_round3": "Round 3 (position-obs-v3)" in expectations,
            "expectations_records_round4": "ROUND 4" in expectations,
            "pipeline_labels_round4_criterion_revision": (
                "Round 4 (recorded criterion revision)" in pipeline
            ),
            "round4_uses_cached_round3_aggregates": all(
                values["aggregate_row_matches_before_r4_fields"]
                and not values["cache_has_round4_fields"]
                for values in cache_matches.values()
            ),
            "round4_prospective": False,
        },
        "uncertainty_audit": {
            "declared_unit": "lineage key",
            "lineage_keys": 6 * 4,
            "within_pairs_per_substrate": int(rows["home"]["n_within"]),
            "draws_keys_with_replacement": "pick = [keys[" in pipeline,
            "uses_membership_not_multiplicity": "if k in pick" in pipeline,
            "conventional_cluster_bootstrap": False,
            "pair_level_scores_retained": False,
            "stored_intervals_reconstructable_without_simulation": False,
        },
        "interpretation": {
            "positive_mean_gaps_in_all_three": all(
                values["within_minus_same_mean"] > 0 for values in calculations.values()
            ),
            "registered_clone_validation_passes_any": any(
                values["registered"]["instrumented"] for values in calculations.values()
            ),
            "round4_is_exploratory_evidence": True,
            "sealed_final_law": False,
        },
    }


def run_l4_audit(
    plastic_root: Path, external_root: Path
) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    audit = {
        "schema_version": 1,
        "scope": "L04 retained observer/compressibility audit plus E28 namespace replay",
        "outcome_blinding": "none; all retained outcomes and A1 result were known",
        "fresh_scientific_futures_generated": 0,
        "historical_namespace_trajectories_replayed": E28_REPLAY_TRAJECTORIES,
        "e25": audit_e25(plastic_root, tracker),
        "fresh_a1_reuse": audit_fresh_a1(external_root, tracker),
        "e28": audit_e28(plastic_root, tracker),
        "alien_census_screens": audit_alien_screens(plastic_root, tracker),
        "e63": audit_e63(plastic_root, tracker),
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, sorted(tracker.paths)


def markdown_report(audit: Mapping[str, Any]) -> str:
    e25 = audit["e25"]
    a1 = audit["fresh_a1_reuse"]
    e28 = audit["e28"]
    e63 = audit["e63"]
    aliens = audit["alien_census_screens"]
    lines = [
        "# L04 retained observer and compressibility audit v1",
        "",
        "This is an outcome-known retained-data audit plus a same-code replay of E28's historical namespace.",
        "",
        "## Integrity",
        "",
        f"- Input files hashed: {audit['input_file_count']}",
        f"- Fresh scientific futures: {audit['fresh_scientific_futures_generated']}",
        f"- Historical E28 trajectories replayed: {audit['historical_namespace_trajectories_replayed']}",
        f"- E25 source config verified: {e25['integrity']['config_matches_source_default']}",
        f"- E28 source config verified: {e28['integrity']['config_matches_source_default']}",
        f"- E63 source config verified: {e63['integrity']['config_matches_source_default']}",
        "",
        "## E25 and fresh A1",
        "",
        f"- E25 Rule 110 gate: {e25['calculated_gates']['gate_redemption_110']}",
        f"- E25 all four class-4 rules in band: {e25['calculated_gates']['all_four_class4_in_band']}",
        f"- E25 chaos control: {e25['calculated_gates']['gate_chaos_stays_chaos']}",
        f"- E25 champion control: {e25['calculated_gates']['gate_champions_stable']}",
        f"- Fresh A1 all four class-4 rules in band at width 64 / eta .01, combined and both halves: {a1['all_four_anchor_combined']} / {a1['all_four_anchor_both_halves']}",
        f"- Fresh A1 class-4 combined in-band counts by width 63/64/65/128: "
        + "/".join(str(a1["width_stress"][str(width)]["combined_count_in_band"])
                   for width in (63, 64, 65, 128)),
        "- The class-4 observer result replicates at the registered anchor but fails as a width-128 universal.",
        "",
        "## Compressibility",
        "",
    ]
    for label, values in (
        ("E25 selected rows", e25["coverage_diagnostics_selected_gate_rows"]),
        ("A1 width 64 / eta .01", a1["coverage_diagnostics_at_eta001"]["64"]),
        ("A1 width 128 / eta .01", a1["coverage_diagnostics_at_eta001"]["128"]),
    ):
        lines.append(
            f"- {label}: coverage/strict rho={values['spearman_coverage_vs_strict']}; "
            f"below-target capable={values['capable_among_target_missed']}/"
            f"{values['n_target_missed']}; above-target capable="
            f"{values['capable_among_target_achieved']}/{values['n_target_achieved']}"
        )
    lines.extend([
        "- Coverage separation is a selected-panel observation, not a causal or universal necessity test.",
        "",
        "## E28",
        "",
        f"- All retained gate booleans reproduce: {e28['integrity']['all_stored_gates_match']}",
        f"- Figure minus raw seed-classification accuracy at generation 10: {e28['retained_gate_recalculation']['gate1_paired']['figure_minus_raw_mean']:.6g}",
        f"- Coverage/capability rho vs null q95: {e28['retained_gate_recalculation']['gate2']['rho']:.6g} vs {e28['retained_gate_recalculation']['gate2']['null_q95']:.6g}",
        f"- Post-hoc generation 2/4/6 replay matches all retained three-decimal values: {e28['posthoc_horizon']['all_rounded_values_match']}",
        f"- Generation-10 replay control matches the retained full-precision gate: {e28['generation10_replay_control']['all_values_match']}",
        "- The brief generation-2 raw-census signal is post-hoc. No conserved/non-conserved ablation tests the causal word `because`.",
        "",
        "## Wave-13 census screens and E63",
        "",
        f"- Kuramoto passing/instrumented screen rows: {aliens['kuramoto']['screen']['n_passing']}/{aliens['kuramoto']['screen']['n_instrumented']} of {aliens['kuramoto']['screen']['n_rows']}",
        f"- Gray-Scott passing/instrumented screen rows: {aliens['grayscott']['screen']['n_passing']}/{aliens['grayscott']['screen']['n_instrumented']} of {aliens['grayscott']['screen']['n_rows']}",
        "- `No chosen point` is a combined-screen outcome; it is not identical to every row being uninstrumented.",
    ])
    for name, values in e63["substrates"].items():
        lines.append(
            f"- E63 {name}: mean gap {values['within_minus_same_mean']:.6g}, "
            f"stored CI {values['reported_ci90']}; registered/revised individuality="
            f"{values['registered']['individuality']}/{values['round4_revision']['individuality']}"
        )
    lines.extend([
        f"- Registered E63 individuality passes any substrate: {e63['registered_any_individuality']}",
        f"- Round-4 revised individuality passes all substrates: {e63['round4_all_individuality']}",
        "- Round 4 reclassifies the same cached rows after the clone criterion failed; it is exploratory, not a sealed prospective result.",
        "- The stated cluster bootstrap discards resampled-key multiplicity, and pair-level scores were not retained for repair.",
        "",
        "## First-pass verdict",
        "",
        "- MIXED. A specified ECA particle map reproducibly exposes events hidden from the raw map, including all four named class-4 rules at the registered anchor.",
        "- `Compressible background required` is not established generally; E28's prospective generalization gate failed.",
        "- Bulk seed information is a short-lived post-hoc observation, and conservation was not causally isolated.",
        "- E63 supplies promising position-sensitive gaps, but the registered test is VOID/failed and the positive classification uses a post-outcome criterion with a nonstandard interval.",
        "- The evidence supports `measurement map changes which lineage distinctions are detected`, not the ontological phrase `the key decides what exists`.",
        "",
    ])
    return "\n".join(lines)
