"""Outcome-known retained audit for L09's triangle/resolution claims."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E43_growing_web": "284158760c511ce7633436c9f4f6f0ffe2af0e620a2e681e9ccdab3502889a6d",
    "E44_lightcone_3": "b116172036497e75146b44f82550a53fa0bbdcd9e0c1684ae7b30db86e22c2b1",
    "E45_persuadability_3": "fd35227fda9148d34ba669a8cdce64cfc093b2a9aa2509331155bd691a54485a",
    "E48_blueprint_web": "fec508fdcefb9e7cf4c0eff45ec6f35a9ee25ccf2b4b366f8689af54397cf19b",
    "E49_triangle_final": "e5ecf2e981b236b1c2d9e0becc709013cba7da0d866d30298079bab4daffbd84",
    "E50_james_final": "673ad23f3661725b97aebaf33515850811dbc88d70a9c84209d7d118c66b2728",
    "E51_two_headed_final": "8dd8669dab6c560337fd1a09bbdd4257011fadd8a62bc0d0392fe23c53753da6",
    "E53_hidden_genome": "46a00eebd4ed079dbd5aa3ee15df5bd4c94ac535cbde4d1c3b9c87ea173f4ebc",
    "E54_repertoire": "a53c62d5e27dabead75c6659189d3e38a60db08d31773f1b6e162bf670646920",
}

E44_ARMS = ("D", "G", "H", "H_lesion")
E49_ARMS = ("D", "T", "T_lesion")
E49_DISTANCES = (4, 6, 8)
E49_IMPRINT_GENERATIONS = (2, 4, 8)
E54_CLASSES = ("in_repertoire", "translated", "surrogate", "cross_tissue")
E54_DOSES = (8, 50, 200, 500)


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


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


def _bootstrap_mean_interval(
    values: list[float], *, seed: int, draws: int = 4096
) -> list[float]:
    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    selection = rng.integers(0, len(data), size=(draws, len(data)))
    return [float(x) for x in np.quantile(data[selection].mean(axis=1), (0.025, 0.975))]


def _directions(values: list[float], tolerance: float = 1e-12) -> dict[str, int]:
    return {
        "positive": sum(value > tolerance for value in values),
        "tied": sum(abs(value) <= tolerance for value in values),
        "negative": sum(value < -tolerance for value in values),
    }


def _contrast(values: list[float], *, seed: int) -> dict[str, Any]:
    return {
        "n_tissues": len(values),
        "mean_difference": float(np.mean(values)),
        "paired_tissue_bootstrap_95": _bootstrap_mean_interval(values, seed=seed),
        "directions": _directions(values),
        "tissue_differences": values,
    }


def _load_shards(
    root: Path,
    tracker: InputTracker,
    *,
    prefix: str,
    expected_shards: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = [
        root / "results/full/work" / f"{prefix}_{i:02d}_of_{expected_shards:02d}.json"
        for i in range(expected_shards)
    ]
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"shard config digests differ for {prefix}: {digests}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    return entries, {
        "n_shards": len(paths),
        "shard_ids": list(range(expected_shards)),
        "config_digest": next(iter(digests)),
        "n_entries": len(entries),
    }


def source_config_digests() -> dict[str, str]:
    """Independently transcribed defaults for every final retained package."""

    configs: dict[str, dict[str, Any]] = {
        "E43_growing_web": {
            "mode": "full",
            "adhesion_j": 1.0,
            "chemotaxis_chi": 1.0,
            "temperature": 0.5,
            "phases_per_sweep": 2,
            "proposal_fraction": 0.25,
            "motility_seed_tag": "grow-motility-v1",
            "trajectory_seed_tag": "grow-traj-v1",
        },
        "E44_lightcone_3": {
            "mode": "full",
            "n_tissues": 12,
            "futures": 24,
            "displacement_ladder": (4, 6, 8),
            "strip_width": 3,
            "displacement_magnitude": 0.8,
            "recovery_sweeps": 60,
            "persistence_horizon": 24,
            "trajectory_seed_tag": "cone3-traj-v2",
            "motility_seed_tag": "cone3-motility-v2",
        },
        "E45_persuadability_3": {
            "mode": "full",
            "n_tissues": 8,
            "futures": 24,
            "horizon": 20,
            "hold_generations": 4,
            "target_cos": 0.9,
            "overlay_lambda": 0.3,
            "cue_generations": (3, 7, 11),
            "l2_on_bare_energy": 56.92,
            "trajectory_seed_tag": "persuade3-traj-v2",
            "motility_seed_tag": "persuade3-motility-v2",
        },
        "E48_blueprint_web": {
            "mode": "full",
            "rho": 0.002,
            "c_m": 0.2,
            "seed_side": 4,
            "coarse_weight": 0.5,
            "trajectory_seed_tag": "blueprint-traj-v1",
            "motility_seed_tag": "blueprint-motility-v1",
        },
        "E49_triangle_final": {
            "mode": "full",
            "n_tissues": 12,
            "futures": 16,
            "settle_sweeps": 120,
            "displacement_ladder": (4, 6, 8),
            "strip_width": 3,
            "displacement_magnitude": 0.8,
            "recovery_sweeps": 80,
            "imprint_generations": (2, 4, 8),
            "imprint_hold": 1.2,
            "steer_horizon": 20,
            "steer_bar": 0.75,
            "hold_generations": 4,
            "trajectory_seed_tag": "triangle-traj-v1",
        },
        "E50_james_final": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 16,
            "settle_sweeps": 120,
            "zap_sweeps_ladder": (4, 8, 16),
            "recovery_horizon": 100,
            "arrival_cos_bar": 0.8,
            "cessation_lock": 3,
            "replica_streams": 5,
            "pre_gap": 10,
            "trap_horizon": 200,
            "trap_wall_width": 2,
            "trajectory_seed_tag": "jamesfinal-traj-v1",
        },
        "E51_two_headed_final": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 16,
            "settle_sweeps": 120,
            "imprint_generations": 6,
            "imprint_hold": 1.2,
            "inheritance_cycles": 8,
            "regrow_sweeps": 100,
            "positional_bar": 0.75,
            "regeneration_bar": 0.85,
            "trajectory_seed_tag": "worm-final-v2",
        },
        "E53_hidden_genome": {
            "mode": "full",
            "n_tissues": 6,
            "futures": 8,
            "settle_sweeps": 120,
            "regrow_sweeps": 240,
            "amp_threshold": 0.2,
            "alt_seed_index": 1,
            "base_seed_index": 0,
            "probe_seeds": 6,
            "probe_settle": 600,
            "probe_horizon": 1000,
            "trajectory_seed_tag": "hidden-genome-v1",
        },
        "E54_repertoire": {
            "mode": "full",
            "n_tissues": 3,
            "futures": 8,
            "harvest_settle": 1000,
            "verify_sweeps": 200,
            "verify_tolerance": 0.05,
            "verify_min": 0.5,
            "n_targets_per_class": 4,
            "doses": (8, 50, 200, 500),
            "adoption_horizon": 1200,
            "imprint_hold": 1.2,
            "amp_threshold": 0.2,
            "steer_hold": 1000,
            "steer_generations": 4,
            "inter_fission": 250,
            "flagship_cycles": 8,
            "steer_bar": 0.75,
            "min_domain_area": 0.05,
            "trajectory_seed_tag": "repertoire-v2",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def audit_antecedents(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    roots = {
        "E37": _experiment_root(plastic_root, "persuadability"),
        "E39": _experiment_root(plastic_root, "excitable_web"),
        "E40": _experiment_root(plastic_root, "lightcone_2"),
        "E41": _experiment_root(plastic_root, "persuadability_2"),
    }
    e37 = tracker.json(roots["E37"] / "results/full/persuade_summary.json")
    e39 = tracker.json(roots["E39"] / "results/full/excitable_summary.json")
    e40 = tracker.json(roots["E40"] / "results/full/cone2_summary.json")
    e41 = tracker.json(roots["E41"] / "results/full/persuade2_summary.json")
    return {
        "E37_finite_steering": {
            "cells_above_rung_A_reaching_half": sum(
                cell["rate"] >= 0.5
                for key, ladder in e37["details"].items()
                if not key.startswith("A:")
                for cell in ladder.values()
            ),
            "cells_above_rung_A": sum(
                1
                for key, ladder in e37["details"].items()
                if not key.startswith("A:")
                for _cell in ladder.values()
            ),
            "direct_common_triangle_measurement": False,
        },
        "E39_amplifier_and_screen": {
            "later_absolute_amplifier_gate": bool(e39["gates"]["gate_p39_1_all_or_none"]),
            "E_screen": bool(e39["screens"]["E"]["pass"]),
            "F_screen": bool(e39["screens"]["F"]["pass"]),
            "rich_target_content_measured": False,
        },
        "E40_transport": {
            "spatial_gate": bool(e40["gates"]["gate_p40_1_spatial_on"]),
            "recovery_at_distance_8": {
                arm: float(e40["gates"]["lightcone2"][arm]["transport_recovery_max_d"])
                for arm in ("D", "F", "F_lesion")
            },
        },
        "E41_steering": {
            "information_gate": bool(e41["gates"]["gate_p41_1_information_lever"]),
            "organizer_gate": bool(e41["gates"]["gate_p41_2_organizer_control_panel"]),
            "target_sign_reaches_current_voltage_coupling": False,
            "basis": "L8 source trace: current coupling sums cue channels before actuation",
        },
        "interpretation": (
            "These are finite antecedent failures with heterogeneous endpoints; "
            "none measures all three triangle corners in one common design."
        ),
    }


def audit_e43(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/grow_summary.json")
    engine = _read(tracker, root / "src/growing_web/engine.py")
    pipeline = _read(tracker, root / "src/growing_web/pipeline.py")
    tests = _read(tracker, root / "tests/test_grow.py")
    sorting = summary["sorting"]
    ratio = float(sorting["interface_motile"] / sorting["interface_off"])
    recalculated = {
        "gate_p43_1_sorting": bool(ratio <= 0.5),
        "gate_p43_2_heredity": bool(
            summary["screens"]["G"]["pass"] and summary["screens"]["H"]["pass"]
        ),
    }
    return {
        "config_digest": summary["config_digest"],
        "config_digest_matches_expected": summary["config_digest"]
        == EXPECTED_CONFIG_DIGESTS["E43_growing_web"],
        "sorting_ratio": ratio,
        "screens": summary["screens"],
        "recalculated_gates": recalculated,
        "reported_gates_match": _recursive_close(recalculated, summary["gates"]),
        "carrier_implementation": {
            "motility_swaps_voltage_V": "V = motility_phase(V" in engine,
            "motility_swaps_ema_history": "ema = motility_phase" in engine,
            "motility_swaps_theta": "theta = motility_phase" in engine,
            "motility_tracks_cell_identity_or_provenance": bool(
                re.search(r"cell_id|provenance|particle_id", engine)
            ),
            "only_V_returned_by_motility_phase": "return V_new" in engine,
            "whole_cell_wording_supported_by_all_dynamic_state": False,
            "voltage_sum_conservation_unit_test_present": (
                "test_swaps_conserve_total_v_exactly" in tests
            ),
            "lesion_identity_stream_unit_test_present": (
                "test_zero_couplings_accept_freely_and_lesion_is_identity_stream_exact"
                in tests
            ),
            "synthetic_chemotaxis_test_uses_operating_point": all(
                token in tests
                for token in ("temperature=0.5", "adhesion_j=1.0", "chemotaxis_chi=1.0")
            ),
            "synthetic_chemotaxis_test_removes_adhesion": "adhesion_j=0.0" in tests,
            "E43_gate_contains_addressed_transport_endpoint": "transport" in pipeline,
        },
        "retention_limit": (
            "The retained JSON has sorting and lineage-screen aggregates only; "
            "conservation, chemotaxis, and lesion exactness are test assertions."
        ),
    }


def audit_e44(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="cone3_shard", expected_shards=4
    )
    summary = tracker.json(root / "results/full/cone3_summary.json")
    round1_entries, round1_integrity = _load_shards(
        root, tracker, prefix="round1_cone3_shard", expected_shards=4
    )
    round1_summary = tracker.json(root / "results/full/cone3_round1_magnitudeE.json")
    source = _read(tracker, root / "src/lightcone_3/pipeline.py")

    expected_keys = {(arm, tissue) for arm in E44_ARMS for tissue in range(12)}
    observed_keys = [(str(row["arm"]), int(row["tissue"])) for row in entries]
    integrity.update(
        {
            "expected_entries": 48,
            "unique_keys": len(set(observed_keys)),
            "complete_expected_grid": set(observed_keys) == expected_keys,
            "no_duplicate_keys": len(observed_keys) == len(set(observed_keys)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def stats(arm: str) -> dict[str, Any]:
        rows = [row for row in entries if row["arm"] == arm]
        speeds = [
            float(row["speed"]["median_recovery_sweeps"])
            for row in rows
            if row["speed"]["median_recovery_sweeps"] is not None
        ]
        return {
            "spatial_cone_median": float(np.median([row["space"]["spatial_cone"] for row in rows])),
            "transport_recovery_max_d": float(np.mean([
                row["space"]["recovery_by_distance"]["8"] for row in rows
            ])),
            "temporal_cone_median": float(np.median([row["time"]["temporal_cone"] for row in rows])),
            "recovery_rate": float(np.mean([row["speed"]["recovery_rate"] for row in rows])),
            "median_recovery_sweeps": float(np.median(speeds)) if speeds else None,
        }

    cone = {arm: stats(arm) for arm in E44_ARMS}
    residual = lambda arm: 1.0 - float(cone[arm]["transport_recovery_max_d"])
    gates = {
        "lightcone3": cone,
        "gate_p44_1_spatial_on_H": bool(
            cone["H"]["spatial_cone_median"] >= 4
            and residual("H") <= 0.5 * max(residual("D"), 1e-9)
        ),
        "gate_p44_2_G_partway": bool(
            residual("G") <= 0.75 * max(residual("D"), 1e-9)
        ),
        "gate_p44_3_striving": bool(
            cone["H"]["median_recovery_sweeps"] is not None
            and cone["H"]["median_recovery_sweeps"] >= 5
            and cone["H"]["recovery_rate"] >= 0.8
        ),
        "gate_p44_4_temporal_retained": bool(
            cone["H"]["temporal_cone_median"]
            >= 0.8 * cone["D"]["temporal_cone_median"]
        ),
        "gate_p44_5_knife": bool(cone["H_lesion"]["spatial_cone_median"] == 0),
    }

    by_arm_tissue = {
        (str(row["arm"]), int(row["tissue"])): row for row in entries
    }
    h_minus_d = [
        float(by_arm_tissue[("H", tissue)]["space"]["recovery_by_distance"]["8"])
        - float(by_arm_tissue[("D", tissue)]["space"]["recovery_by_distance"]["8"])
        for tissue in range(12)
    ]
    h_minus_lesion = [
        float(by_arm_tissue[("H", tissue)]["space"]["recovery_by_distance"]["8"])
        - float(by_arm_tissue[("H_lesion", tissue)]["space"]["recovery_by_distance"]["8"])
        for tissue in range(12)
    ]
    distance_means = {
        arm: {
            str(distance): float(np.mean([
                row["space"]["recovery_by_distance"][str(distance)]
                for row in entries if row["arm"] == arm
            ]))
            for distance in E49_DISTANCES
        }
        for arm in E44_ARMS
    }
    return {
        "integrity": integrity,
        "recalculated_gates": gates,
        "all_reported_gates_and_summaries_match": _recursive_close(
            gates, summary["gates"]
        ),
        "distance_recovery_means": distance_means,
        "distance_8_contrasts": {
            "H_minus_D": _contrast(h_minus_d, seed=2026090290),
            "H_minus_H_lesion": _contrast(h_minus_lesion, seed=2026090291),
        },
        "rng_and_design_audit": {
            "trajectory_namespace_contains_arm": (
                'seed_rng(config.trajectory_seed_tag + "-space", arm, index)' in source
            ),
            "motility_namespace_contains_arm": (
                'seed_rng(config.motility_seed_tag + "-space", arm, index)' in source
            ),
            "arms_stream_paired": False,
            "displacement_tracks_material_identity": False,
            "reference_density_varied": False,
        },
        "round1_archive": {
            "integrity": round1_integrity,
            "n_entries": len(round1_entries),
            "summary_digest": round1_summary["config_digest"],
            "mixed_into_final_estimate": False,
        },
    }


def audit_e45(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/persuade3_summary.json")
    round1 = tracker.json(root / "results/full/persuade3_round1_censusmetric.json")
    source = _read(tracker, root / "src/persuadability_3/pipeline.py")
    config = _read(tracker, root / "src/persuadability_3/config.py")
    reported = summary["gates"]
    success = reported["success"]
    gates = {
        "gate_p45_1_organizer_steers": bool(success["H_anchor"] >= 0.5),
        "gate_p45_2_info_lever": bool(
            success["H_info"] >= 0.5
            and reported["info_energy"] <= 0.1 * 56.92
        ),
        "gate_p45_3_stubbornness": bool(success["D_info"] < 0.1),
        "gate_p45_4_knife": bool(
            success["H_info_lesion"] < 0.1
            and success["H_anchor_lesion"] < 0.1
        ),
    }
    return {
        "config_digest": summary["config_digest"],
        "config_digest_matches_expected": (
            summary["config_digest"] == EXPECTED_CONFIG_DIGESTS["E45_persuadability_3"]
        ),
        "success": success,
        "recalculated_gate_booleans": gates,
        "reported_gate_booleans_match": all(
            gates[key] == reported[key] for key in gates
        ),
        "retention": {
            "aggregate_only": True,
            "per_tissue_rows": False,
            "within_life_0_50_to_0_60_probe": False,
            "round1_digest": round1["config_digest"],
        },
        "metric_and_content_audit": {
            "configured_target_cos_0_9_is_used": "config.target_cos" in source,
            "implemented_positional_bar": 0.75,
            "dense_target_overlay_constructed": (
                "E_overlay = (1 - config.overlay_lambda) * E_base + config.overlay_lambda * target_pattern"
                in source
            ),
            "sparse_anchor_arm_also_present": "anchor_layout" in source,
            "active_and_lesion_rng_namespaces_match": False,
            "arm_is_in_both_rng_namespaces": source.count(", arm, index)") >= 2,
            "target_cos_field_declared_but_unused": (
                "target_cos: float = 0.9" in config and "config.target_cos" not in source
            ),
            "knife_is_vacuous_for_both_primary_paths": (
                success["H_info"] == success["H_info_lesion"] == 0
                and success["H_anchor"] == success["H_anchor_lesion"] == 0
            ),
        },
    }


def audit_e48(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/calibration_square.json")
    source = _read(tracker, root / "src/blueprint_web/pipeline.py")
    result_files = sorted((root / "results/full").glob("*.json"))
    square_checks: dict[str, Any] = {}
    for key, cell in summary["square"].items():
        screen = bool(
            cell["h_above"] >= 0.3
            and cell["h_below"] >= 0.02
            and cell["survival_8"] >= 0.3
        )
        freedom = bool(cell["conversion"] >= 0.10)
        square_checks[key] = {
            "screen_recalculated": screen,
            "screen_matches": screen == cell["screen_pass"],
            "freedom_recalculated": freedom,
            "freedom_matches": freedom == cell["freedom_pass"],
        }
    passing = sorted(
        key for key, cell in summary["square"].items()
        if cell["screen_pass"] and cell["freedom_pass"]
    )
    conversion_best = max(passing, key=lambda key: summary["square"][key]["conversion"])
    source_choice = max(passing, key=lambda key: float(key.split("|")[1]))
    gains = sorted({float(key.split("|")[1]) for key in summary["square"]})
    return {
        "retained_config_digest": summary["config_digest"],
        "current_source_config_digest": source_config_digests()["E48_blueprint_web"],
        "retained_digest_matches_recorded_expected": (
            summary["config_digest"] == EXPECTED_CONFIG_DIGESTS["E48_blueprint_web"]
        ),
        "current_source_digest_matches_retained": (
            source_config_digests()["E48_blueprint_web"] == summary["config_digest"]
        ),
        "square": summary["square"],
        "square_checks": square_checks,
        "all_cell_flags_recalculate": all(
            row["screen_matches"] and row["freedom_matches"]
            for row in square_checks.values()
        ),
        "passing_recalculated": passing,
        "passing_matches": passing == summary["passing"],
        "chosen_reported": summary["chosen"],
        "chosen_by_source_rule": source_choice,
        "chosen_by_highest_conversion": conversion_best,
        "choice_matches_both_on_this_table": (
            summary["chosen"] == source_choice == conversion_best
        ),
        "source_choice_criterion": "maximum c_m among passing cells; ties follow insertion order",
        "source_rule_explicitly_optimizes_conversion": False,
        "tested_c_m_values": gains,
        "finite_pass_fail_bracket": [0.2, 0.4],
        "sharpness_or_discontinuity_estimated": False,
        "retention": {
            "result_files": [path.name for path in result_files],
            "calibration_square_machine_readable": True,
            "satisfiability_values_machine_readable": False,
            "regrowth_0_711_vs_0_543_machine_readable": False,
            "whole_R_fission_golden_machine_readable": False,
        },
        "endpoint_warning": (
            "Conversion is a 15-bin lineage rewrite endpoint; it is not "
            "positional target adoption or positional inheritance."
        ),
    }


def audit_e49(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="triangle_shard", expected_shards=4
    )
    summary = tracker.json(root / "results/full/triangle_summary.json")
    source = _read(tracker, root / "src/triangle_final/pipeline.py")
    config_source = _read(tracker, root / "src/triangle_final/config.py")

    kinds = Counter(str(row["kind"]) for row in entries)
    expected_keys: set[tuple[Any, ...]] = set()
    expected_keys.update(("transport", arm, tissue) for arm in E49_ARMS for tissue in range(12))
    expected_keys.update(("adoption", tissue) for tissue in range(6))
    expected_keys.update(
        ("steer", arm, tissue, k)
        for arm in E49_ARMS
        for tissue in range(12)
        for k in E49_IMPRINT_GENERATIONS
    )
    observed_keys = []
    for row in entries:
        if row["kind"] == "transport":
            observed_keys.append(("transport", row["arm"], int(row["tissue"])))
        elif row["kind"] == "adoption":
            observed_keys.append(("adoption", int(row["tissue"])))
        else:
            observed_keys.append(("steer", row["arm"], int(row["tissue"]), int(row["k"])))
    integrity.update(
        {
            "expected_entries": 150,
            "kind_counts": dict(kinds),
            "unique_keys": len(set(observed_keys)),
            "complete_expected_jobs": set(observed_keys) == expected_keys,
            "no_duplicate_jobs": len(observed_keys) == len(set(observed_keys)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    transport_rows = [row for row in entries if row["kind"] == "transport"]
    transport_by_distance: dict[str, dict[str, dict[str, float]]] = {}
    for arm in E49_ARMS:
        rows = [row for row in transport_rows if row["arm"] == arm]
        transport_by_distance[arm] = {}
        for distance in E49_DISTANCES:
            key = str(distance)
            transport_by_distance[arm][key] = {
                "profile_recovery": float(np.mean([
                    row["by_distance"][key]["profile_recovery"] for row in rows
                ])),
                "sign_recovery": float(np.mean([
                    row["by_distance"][key]["sign_recovery"] for row in rows
                ])),
                "cone_median": float(np.median([row["spatial_cone"] for row in rows])),
            }

    def tstats(arm: str) -> dict[str, float]:
        values = transport_by_distance[arm]["8"]
        return {
            "cone": values["cone_median"],
            "profile_recovery": values["profile_recovery"],
            "sign_recovery": values["sign_recovery"],
        }

    t_d, t_t, t_l = tstats("D"), tstats("T"), tstats("T_lesion")
    residual = lambda values: 1.0 - float(values["profile_recovery"])
    adoption_rows = sorted(
        (row for row in entries if row["kind"] == "adoption"),
        key=lambda row: int(row["tissue"]),
    )
    adoption_curves = [list(map(float, row["adoption_curve"])) for row in adoption_rows]
    adoption_mean = np.asarray(adoption_curves).mean(axis=0).tolist()
    adoption_final = float(np.mean([curve[-1] for curve in adoption_curves]))

    steering: dict[str, dict[str, float]] = {}
    for arm in E49_ARMS:
        steering[arm] = {}
        for k in E49_IMPRINT_GENERATIONS:
            rows = [
                row for row in entries
                if row["kind"] == "steer" and row["arm"] == arm and row["k"] == k
            ]
            steering[arm][str(k)] = float(np.mean([row["success_rate"] for row in rows]))
    steer_best = {arm: max(values.values()) for arm, values in steering.items()}
    gates = {
        "transport": {"D": t_d, "T": t_t, "T_lesion": t_l},
        "gate_p49_1_transport": bool(
            residual(t_t) <= 0.5 * max(residual(t_d), 1e-9)
            and t_t["sign_recovery"] >= 0.8
        ),
        "adoption_final_agreement": adoption_final,
        "gate_p49_2_freedom": bool(adoption_final >= 0.8),
        "steer": steer_best,
        "gate_p49_3_imprint_steering": bool(steer_best["T"] >= 0.5),
        "gate_p49_4_knife": bool(
            residual(t_l) >= 0.9 * residual(t_d) and steer_best["T_lesion"] < 0.1
        ),
    }

    indexed = {
        (row["arm"], int(row["tissue"])): row for row in transport_rows
    }

    def paired_values(metric: str, left: str, right: str) -> list[float]:
        return [
            float(indexed[(left, tissue)]["by_distance"]["8"][metric])
            - float(indexed[(right, tissue)]["by_distance"]["8"][metric])
            for tissue in range(12)
        ]

    max_imprint_sweeps = max(E49_IMPRINT_GENERATIONS) * (64 // 2)
    return {
        "integrity": integrity,
        "transport_by_distance": transport_by_distance,
        "adoption": {
            "n_tissues": len(adoption_rows),
            "sample_sweeps": [200, 400, 600, 800, 1000, 1200],
            "mean_curve": adoption_mean,
            "tissue_curves": adoption_curves,
            "final_agreement": adoption_final,
        },
        "steering_rate_by_arm_and_k": steering,
        "recalculated_gates": gates,
        "all_reported_gates_and_summaries_match": _recursive_close(
            gates, summary["gates"]
        ),
        "distance_8_contrasts": {
            "profile_T_minus_D": _contrast(
                paired_values("profile_recovery", "T", "D"), seed=2026090292
            ),
            "profile_T_minus_T_lesion": _contrast(
                paired_values("profile_recovery", "T", "T_lesion"), seed=2026090293
            ),
            "sign_T_minus_D": _contrast(
                paired_values("sign_recovery", "T", "D"), seed=2026090294
            ),
            "sign_T_minus_T_lesion": _contrast(
                paired_values("sign_recovery", "T", "T_lesion"), seed=2026090295
            ),
        },
        "registered_residual_error_ratio_T_over_D": (
            residual(t_t) / residual(t_d)
        ),
        "knife_audit": {
            "implemented_gate_passes": gates["gate_p49_4_knife"],
            "D_and_T_lesion_aggregate_numbers_exactly_equal": _recursive_close(t_d, t_l),
            "arms_stream_paired": False,
            "arm_in_transport_rng_namespace": (
                'seed_rng(config.trajectory_seed_tag + "-transport", arm, index)' in source
            ),
            "heredity_under_knife_measured_in_E49": False,
            "steering_abolition_is_informative": steer_best["T"] > steer_best["T_lesion"],
            "prophecy_stream_exact_and_heredity_claim_fully_tested": False,
        },
        "target_and_dose_audit": {
            "adoption_target": "raw launch_pattern(1)",
            "adoption_target_resettle_verified": False,
            "adoption_target_is_held_after_single_V_overwrite": False,
            "steering_target": "60-sweep harvested seed-1 D pattern",
            "steering_target_long_horizon_verified": False,
            "steering_clamps_full_target_field": "np.where(np.abs(hold)[None] > 0" in source,
            "rho": 0.002,
            "reference_time_constant_sweeps": 500,
            "t_max_sweeps_dependency_default": 64,
            "implemented_sweeps_per_imprint_generation": 32,
            "maximum_imprint_sweeps": max_imprint_sweeps,
            "maximum_imprint_time_constants": max_imprint_sweeps / 500,
            "configuration_imprint_generations_present": "imprint_generations" in config_source,
            "target_class_factorial_present": False,
        },
        "transport_semantics": {
            "endpoint_is_profile_and_sign_restoration": True,
            "material_units_or_cell_ids_tracked": False,
            "comparator_applies_locationwise_R_minus_V": True,
            "literal_cargo_transport_demonstrated": False,
        },
    }


def audit_e50(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/jamesfinal_summary.json")
    gates = summary["gates"]
    return {
        "config_digest": summary["config_digest"],
        "config_digest_matches_expected": (
            summary["config_digest"] == EXPECTED_CONFIG_DIGESTS["E50_james_final"]
        ),
        "naive_arrival": gates["naive_arrival"],
        "preexposed_arrival": gates["preexposed_arrival"],
        "arrival_spread": gates["arrival_spread"],
        "chronic_excess_mean": gates["chronic_excess_mean"],
        "cessation_gate": gates["gate_p50_1_cessation"],
        "repair_adoption_bridge_successfully_measured": False,
        "reason": (
            "No naive recovery arrivals exist under the registered endpoint, "
            "so cessation and generalization are not estimable."
        ),
    }


def audit_e51(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="worm_shard", expected_shards=4
    )
    summary = tracker.json(root / "results/full/worm_summary.json")
    round1_entries, round1_integrity = _load_shards(
        root, tracker, prefix="round1_worm_shard", expected_shards=4
    )
    round1 = tracker.json(root / "results/full/worm_round1_launchmetric.json")
    source = _read(tracker, root / "src/two_headed_final/pipeline.py")
    expected_keys = {
        (setpoint, tissue, lesion)
        for setpoint, lesion in (("wild", False), ("two_headed", False), ("two_headed", True))
        for tissue in range(10)
    }
    observed_keys = [
        (str(row["setpoint"]), int(row["tissue"]), bool(row["lesioned_arm"]))
        for row in entries
    ]
    integrity.update(
        {
            "expected_entries": 30,
            "unique_keys": len(set(observed_keys)),
            "complete_expected_jobs": set(observed_keys) == expected_keys,
            "no_duplicate_jobs": len(observed_keys) == len(set(observed_keys)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def stat(setpoint: str, lesion: bool, key: str) -> float | None:
        rows = [
            row for row in entries
            if row["setpoint"] == setpoint and row["lesioned_arm"] == lesion
        ]
        return float(np.mean([row[key] for row in rows])) if rows else None

    calculated: dict[str, Any] = {
        metric: {
            "wild": stat("wild", False, metric),
            "two_headed": stat("two_headed", False, metric),
            "two_headed_lesioned": stat("two_headed", True, metric),
        }
        for metric in ("inheritance", "regeneration", "quarter_wholeness")
    }
    inh = calculated["inheritance"]
    reg = calculated["regeneration"]
    quart = calculated["quarter_wholeness"]
    calculated.update(
        {
            "gate_p51_1_inheritance": bool(inh["wild"] >= 0.75 and inh["two_headed"] >= 0.75),
            "gate_p51_2_regeneration": bool(reg["wild"] >= 0.85 and reg["two_headed"] >= 0.85),
            "gate_p51_3_quarter_wholeness": bool(quart["two_headed"] >= 0.75),
            "gate_p51_4_knife": bool(inh["two_headed"] >= inh["two_headed_lesioned"] + 0.1),
        }
    )
    return {
        "integrity": integrity,
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, summary["gates"]
        ),
        "causal_read": {
            "two_headed_regeneration_live": reg["two_headed"],
            "two_headed_regeneration_lesion": reg["two_headed_lesioned"],
            "live_minus_lesion": float(reg["two_headed"] - reg["two_headed_lesioned"]),
            "high_both_arms_locates_theta_as_carrier": False,
            "arm_specific_rng_namespace": '"lesion" if c_m == 0.0 else "live"' in source,
            "arms_stream_paired": False,
        },
        "round1_archive": {
            "integrity": round1_integrity,
            "n_entries": len(round1_entries),
            "summary_digest": round1["config_digest"],
            "mixed_into_final_estimate": False,
        },
    }


def audit_e53(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="knife_shard", expected_shards=3
    )
    summary = tracker.json(root / "results/full/knife_summary.json")
    observed = [int(row["tissue"]) for row in entries]
    integrity.update(
        {
            "expected_entries": 6,
            "unique_tissues": len(set(observed)),
            "complete_tissues": set(observed) == set(range(6)),
            "no_duplicate_tissues": len(observed) == len(set(observed)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def mean_key(table: str, key: str) -> float:
        return float(np.mean([row[table][key] for row in entries]))

    fidelity = {key: mean_key("fidelity", key) for key in entries[0]["fidelity"]}
    fidelity_alt = {
        key: mean_key("fidelity_vs_alt", key)
        for key in entries[0]["fidelity_vs_alt"]
    }
    floor = {
        arm: float(np.mean([row["floor"][arm] for row in entries]))
        for arm in ("R_on", "R_off")
    }
    base = fidelity["R_on|intact|intact"]
    drops = {
        "theta_scrambled": base - fidelity["R_on|intact|scrambled"],
        "theta_zeroed": base - fidelity["R_on|intact|zeroed"],
        "context_reset": base - fidelity["R_on|reset|intact"],
    }
    theta_drop = max(drops["theta_scrambled"], drops["theta_zeroed"])
    context_drop = drops["context_reset"]
    winner, winner_drop, loser_drop = (
        ("context", context_drop, theta_drop)
        if context_drop >= theta_drop
        else ("theta", theta_drop, context_drop)
    )
    r_marginal = base - fidelity["R_off|intact|intact"]
    reconstructed = {
        "fidelity": fidelity,
        "fidelity_vs_alt": fidelity_alt,
        "floor": floor,
        "drops": drops,
        "winner": winner,
        "winner_drop": winner_drop,
        "loser_drop": loser_drop,
        "r_marginal": r_marginal,
        "transplant_follow": {
            "toward_pre_R_off": fidelity["R_off|transplant|intact"],
            "toward_alt_R_off": fidelity_alt["R_off|transplant|intact"],
            "toward_pre_R_on": fidelity["R_on|transplant|intact"],
            "toward_alt_R_on": fidelity_alt["R_on|transplant|intact"],
        },
    }
    reported = summary["gates"]
    shard_fields_match = all(
        _recursive_close(reconstructed[key], reported[key]) for key in reconstructed
    )
    return {
        "integrity": integrity,
        "reconstructed_from_shards": reconstructed,
        "all_shard_derived_reported_fields_match": shard_fields_match,
        "recalculated_double_dissociation_gate": bool(
            winner_drop >= 0.25 and loser_drop < 0.10
        ),
        "reported_double_dissociation_gate": reported["gate_p53_1_double_dissociation"],
        "retained_aggregate_probe": reported["probe"],
        "mechanism_update": {
            "repair_timescale_carrier": winner,
            "theta_repair_drop_max": theta_drop,
            "context_repair_drop": context_drop,
            "theta_has_long_run_ensemble_effect": reported["probe"]["mean_effect"] > 0.05,
            "theta_stores_tested_repair_instance": False,
        },
    }


def audit_e54(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="rep_shard", expected_shards=3
    )
    summary = tracker.json(root / "results/full/repertoire_summary.json")
    keys = [(str(row["kind"]), int(row["tissue"])) for row in entries]
    integrity.update(
        {
            "expected_entries": 6,
            "kind_counts": dict(Counter(key[0] for key in keys)),
            "unique_keys": len(set(keys)),
            "complete_jobs": set(keys)
            == {(kind, tissue) for kind in ("adoption", "steering") for tissue in range(3)},
            "no_duplicate_jobs": len(keys) == len(set(keys)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )
    adoption = [row for row in entries if row["kind"] == "adoption"]
    steering_rows = [
        row for row in entries
        if row["kind"] == "steering" and row.get("steering") is not None
    ]
    runs = [run for row in adoption for run in row["runs"]]

    def class_dose(cls: str, dose: int, key: str) -> float | None:
        values = [run[key] for run in runs if run["class"] == cls and run["dose"] == dose]
        return float(np.mean(values)) if values else None

    adoption_table = {
        cls: {
            str(dose): {
                "delta": class_dose(cls, dose, "delta"),
                "exit_frac": class_dose(cls, dose, "basin_exit"),
            }
            for dose in E54_DOSES
        }
        for cls in E54_CLASSES
    }
    top2 = E54_DOSES[-2:]
    inrep_wins = sum(
        1
        for dose in E54_DOSES
        if all(
            adoption_table["in_repertoire"][str(dose)]["delta"]
            > adoption_table[cls][str(dose)]["delta"]
            for cls in E54_CLASSES if cls != "in_repertoire"
        )
        and adoption_table["in_repertoire"][str(dose)]["exit_frac"] >= 0.5
    )
    order_mean = {
        cls: float(np.mean([
            adoption_table[cls][str(dose)]["delta"] for dose in top2
        ]))
        for cls in E54_CLASSES
    }
    steering = {
        arm: float(np.mean([
            row["steering"][arm]["fraction_held"] for row in steering_rows
        ]))
        for arm in ("in_repertoire", "translated", "knife", "floor")
    }
    flags = [row["flagship"] for row in steering_rows if row["flagship"].get("found")]
    flagship = {
        "n_found": len(flags),
        "live": float(np.mean([row["live"]["final_inheritance"] for row in flags])) if flags else None,
        "knife": float(np.mean([row["knife"]["final_inheritance"] for row in flags])) if flags else None,
        "wild_floor": float(np.mean([row["wild_floor"]["final_inheritance"] for row in flags])) if flags else None,
    }
    gates = {
        "adoption_table": adoption_table,
        "order_mean_top2": order_mean,
        "exit_bar_mean": float(np.mean([row["exit_bar"] for row in adoption])),
        "drift_floor_self": float(np.mean([row["drift_floor_self"] for row in adoption])),
        "steering": steering,
        "flagship": flagship,
        "gate_p54_1_adoption_splits": bool(
            inrep_wins >= 2
            and order_mean["in_repertoire"] > order_mean["cross_tissue"]
            > order_mean["surrogate"]
        ),
        "gate_p54_2_steering_on": bool(
            steering["in_repertoire"] >= 0.5
            and steering["in_repertoire"] >= steering["floor"] - 0.10
        ),
        "gate_p54_3_flagship_rescued": bool(
            flagship["live"] is not None and flagship["live"] >= 0.75
        ),
        "gate_p54_4_knife": bool(
            steering["knife"] <= 0.10
            and (
                flagship["knife"] is None
                or flagship["live"] is None
                or flagship["knife"] <= flagship["live"] - 0.10
            )
        ),
    }
    return {
        "integrity": integrity,
        "n_adoption_runs": len(runs),
        "recalculated_gates": gates,
        "all_reported_gates_and_summaries_match": _recursive_close(
            gates, summary["gates"]
        ),
        "mechanism_update": {
            "in_repertoire_top2_mean": order_mean["in_repertoire"],
            "cross_tissue_top2_mean": order_mean["cross_tissue"],
            "in_repertoire_advantage_over_cross_tissue": (
                order_mean["in_repertoire"] - order_mean["cross_tissue"]
            ),
            "all_steering_rates_zero_including_floor": all(
                value == 0.0 for value in steering.values()
            ),
            "frozen_theta_repertoire_attribution_supported": False,
            "interpretation": (
                "Target-class ordering failed and the cross-tissue class was "
                "slightly highest; no arm, including the unsteered floor, met "
                "the lineage steering endpoint."
            ),
        },
    }


def _proof_audit(
    tracker: InputTracker,
    *,
    plastic_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    ideas = plastic_root / IDEAS_RELATIVE
    documents = {
        "LAWS.md": ideas / "LAWS.md",
        "WAVE9_PROPHECIES.md": ideas / "WAVE9_PROPHECIES.md",
        "WAVE10_PROPHECIES.md": ideas / "WAVE10_PROPHECIES.md",
        "WAVE11_PROPHECIES.md": ideas / "WAVE11_PROPHECIES.md",
        "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md": ideas / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        "RULIAD_DISCUSSION.md": ideas / "RULIAD_DISCUSSION.md",
        "L09_triangle_resolution.md": workspace / "laws/L09_triangle_resolution.md",
    }
    texts = {name: _read(tracker, path) for name, path in documents.items()}
    theorem_mentions = {
        name: len(re.findall(r"resolution theorem", text, flags=re.IGNORECASE))
        for name, text in texts.items()
    }
    formal_heading = re.compile(
        r"^#{1,6}\s+(proof|theorem|lemma|proposition)\b", re.IGNORECASE | re.MULTILINE
    )
    return {
        "files_searched": list(documents),
        "resolution_theorem_mentions": theorem_mentions,
        "formal_proof_or_theorem_heading_found": any(
            formal_heading.search(text) for text in texts.values()
        ),
        "defined_quantified_substrate_domain_found": False,
        "exhaustive_case_or_analytic_necessity_argument_found": False,
        "formal_proof_artifact_found": False,
        "status": "NO_FORMAL_PROOF_LOCATED",
        "note": (
            "The searched records repeat a prose inference from three finite "
            "engineered failures; they do not state a mathematical domain and proof."
        ),
    }


def run_l9_audit(plastic_root: Path) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    workspace = Path(__file__).resolve().parents[2]
    ideas = plastic_root / IDEAS_RELATIVE
    roots = {
        name: _experiment_root(plastic_root, name)
        for name in (
            "growing_web",
            "lightcone_3",
            "persuadability_3",
            "blueprint_web",
            "triangle_final",
            "james_final",
            "two_headed_final",
            "hidden_genome",
            "repertoire",
        )
    }
    for root in roots.values():
        _track_package(tracker, root)
    for dependency in (
        "ladder_web",
        "voltage_web",
        "setpoint_rewrite",
        "persuadability",
    ):
        _track_package(tracker, _experiment_root(plastic_root, dependency))

    manuscript_path = plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md"
    for path in (
        manuscript_path,
        workspace / "protocols/L09_RETAINED_AUDIT_V1.md",
        workspace / "reviews/L08_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        workspace / "laws/L09_triangle_resolution.md",
    ):
        tracker.add(path)

    manuscript_text = _read(tracker, manuscript_path)
    digests = source_config_digests()
    config_matches = {
        key: digests[key] == EXPECTED_CONFIG_DIGESTS[key] for key in digests
    }
    antecedents = audit_antecedents(plastic_root, tracker)
    e43 = audit_e43(roots["growing_web"], tracker)
    e44 = audit_e44(roots["lightcone_3"], tracker)
    e45 = audit_e45(roots["persuadability_3"], tracker)
    e48 = audit_e48(roots["blueprint_web"], tracker)
    e49 = audit_e49(roots["triangle_final"], tracker)
    e50 = audit_e50(roots["james_final"], tracker)
    e51 = audit_e51(roots["two_headed_final"], tracker)
    e53 = audit_e53(roots["hidden_genome"], tracker)
    e54 = audit_e54(roots["repertoire"], tracker)
    proof = _proof_audit(tracker, plastic_root=plastic_root, workspace=workspace)

    truth_table = [
        {
            "substrate": "Wave 8 fields/anchors (B/C/D)",
            "rich_positional_content": "NOT_COMMONLY_OPERATIONALIZED",
            "plastic_hereditary_freedom": "NOT_MEASURED_IN_SAME_E37_TASK",
            "strong_goal_enforcement": "FAILED_ON_FINITE_E37_GRID",
            "same_design_all_three": False,
        },
        {
            "substrate": "Wave 9 excitable/license (E/F)",
            "rich_positional_content": "NOT_DELIVERED_BY_CURRENT_E41_COUPLING",
            "plastic_hereditary_freedom": "AGGREGATE_SCREEN_PASS",
            "strong_goal_enforcement": "E40_E41_PRIMARY_GATES_FAIL",
            "same_design_all_three": False,
        },
        {
            "substrate": "Wave 10 motile voltage (G/H)",
            "rich_positional_content": "SPARSE_ANCHOR_OR_TRANSIENT_DENSE_BLEND",
            "plastic_hereditary_freedom": "AGGREGATE_SCREEN_PASS",
            "strong_goal_enforcement": "E44_E45_PRIMARY_GATES_FAIL",
            "same_design_all_three": False,
        },
        {
            "substrate": "Wave 11 self-blueprint T, repair task",
            "rich_positional_content": "FULL_FIELD_R_BY_CONSTRUCTION",
            "plastic_hereditary_freedom": "E48_SCREEN_AND_CONVERSION_PASS",
            "strong_goal_enforcement": "E49_TRANSPORT_GATE_PASS",
            "same_frozen_configuration": True,
            "same_run_and_endpoint": False,
            "all_three_on_source_operationalizations": True,
        },
        {
            "substrate": "Wave 11/12 T, imposed-target lineage task",
            "rich_positional_content": "FULL_FIELD_TARGET_CLAMP",
            "plastic_hereditary_freedom": "NOT_A_COMMON_POSITIONAL_ENDPOINT",
            "strong_goal_enforcement": "E49_AND_E54_STEERING_FAIL",
            "same_design_all_three": False,
        },
    ]

    claim_assessment = {
        "each_tested_substrate_has_at_most_two_corners": {
            "status": "REFUTED_ON_SOURCE_OPERATIONALIZATIONS",
            "reason": (
                "The law itself treats full-field R, E48 freedom, and E49 "
                "transport as all three corners at one frozen T configuration."
            ),
        },
        "three_failures_converge_specifically_on_address_resolution": {
            "status": "NOT_CONFIRMED",
            "reason": (
                "No matched resolution/density factorial exists; E43 moves only V, "
                "E45 includes a dense overlay, and delivery/reachability/observer "
                "alternatives remain."
            ),
        },
        "content_resolution_enforcement_requires_content_resolution_reference": {
            "status": "NOT_CONFIRMED_AS_NECESSITY",
            "reason": "E49 constructs one sufficient local comparator; no exhaustive proof exists.",
        },
        "content_resolution_reference_necessarily_abolishes_freedom": {
            "status": "REFUTED_ON_FINITE_OPERATIONALIZATION",
            "reason": "The full-field T reference coexists with E48's registered freedom pass.",
        },
        "slow_self_reference_escapes_for_repair": {
            "status": "CONFIRMED_WITH_NARROWER_WORDING",
            "reason": (
                "E49's retained distance-8 rows show a large, direction-consistent "
                "profile/sign restoration advantage and the registered gate passes."
            ),
        },
        "tradeoff_remains_for_arbitrary_reprogramming_under_frozen_landscape": {
            "status": "NOT_CONFIRMED_AND_MECHANISM_REFUTED",
            "reason": (
                "The finite E49/E54 steering endpoints fail, but arbitrary targets "
                "are not exhausted; E53/E54 overturn theta-as-instance-carrier and "
                "find no in-repertoire advantage."
            ),
        },
        "finite_results_warrant_theorem": {
            "status": "NOT_CONFIRMED",
            "reason": "No formal proposition/proof was located and the unrestricted claim has its own counterexample.",
        },
    }
    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L09",
        "audit_kind": "outcome-known retained-artifact and source audit",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_paths_replayed": 0,
        "source_config_digests": digests,
        "all_source_config_digests_match": all(config_matches.values()),
        "source_config_digest_matches": config_matches,
        "Wave8_9_antecedents": antecedents,
        "E43_growing_web": e43,
        "E44_lightcone_3": e44,
        "E45_persuadability_3": e45,
        "E48_blueprint_web": e48,
        "E49_triangle_final": e49,
        "E50_james_final": e50,
        "E51_two_headed_final": e51,
        "E53_hidden_genome": e53,
        "E54_repertoire": e54,
        "triangle_truth_table": truth_table,
        "proof_audit": proof,
        "claim_assessment": claim_assessment,
        "overall_verdict": "REFUTED",
        "replacement_wording": (
            "In this lattice implementation, three finite controller designs did "
            "not meet their registered positional tasks. A slow full-field "
            "self-reference at rho=0.002 and c_m=0.2 causally improves one "
            "within-life displacement-restoration task while a separate census "
            "freedom screen passes. The tested imposed-target lineage protocols "
            "do not achieve persistent positional steering. These results neither "
            "form a resolution theorem nor identify frozen theta as the bound."
        ),
        "manuscript_v2_3_independent_support": bool(
            re.search(
                r"resolution theorem|content.freedom.repair triangle|self-written blueprint",
                manuscript_text,
                flags=re.IGNORECASE,
            )
        ),
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, sorted(tracker.paths)


def markdown_report(audit: Mapping[str, Any]) -> str:
    e43 = audit["E43_growing_web"]
    e44 = audit["E44_lightcone_3"]
    e48 = audit["E48_blueprint_web"]
    e49 = audit["E49_triangle_final"]
    e53 = audit["E53_hidden_genome"]
    e54 = audit["E54_repertoire"]
    lines = [
        "# L09 retained triangle/resolution audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`.",
        "",
        "The finite failures and E49 restoration effect are real, but they do not form a theorem. "
        "On the source's own definitions, Wave 11 supplies a full-field reference, a passing "
        "freedom screen, and a passing repair gate at the same frozen configuration. Later E53/E54 "
        "also reverse the claim that frozen theta explains the reprogramming failures.",
        "",
        "## Core numerical checks",
        "",
        "| Check | Recalculated result |",
        "|---|---:|",
        f"| E43 sorting interface ratio | {e43['sorting_ratio']:.6f} |",
        f"| E44 H − D recovery at distance 8 | {e44['distance_8_contrasts']['H_minus_D']['mean_difference']:+.6f} |",
        f"| E44 H − lesion recovery at distance 8 | {e44['distance_8_contrasts']['H_minus_H_lesion']['mean_difference']:+.6f} |",
        f"| E48 chosen conversion | {e48['square'][e48['chosen_reported']]['conversion']:.6f} |",
        f"| E49 residual-error ratio T/D | {e49['registered_residual_error_ratio_T_over_D']:.6f} |",
        f"| E49 profile T − D at distance 8 | {e49['distance_8_contrasts']['profile_T_minus_D']['mean_difference']:+.6f} |",
        f"| E49 sign T − D at distance 8 | {e49['distance_8_contrasts']['sign_T_minus_D']['mean_difference']:+.6f} |",
        f"| E49 adoption at 1200 sweeps | {e49['adoption']['final_agreement']:.6f} |",
        f"| E53 context-reset drop | {e53['mechanism_update']['context_repair_drop']:.6f} |",
        f"| E53 maximum theta drop | {e53['mechanism_update']['theta_repair_drop_max']:.6f} |",
        f"| E54 in-repertoire − cross-tissue top-dose mean | {e54['mechanism_update']['in_repertoire_advantage_over_cross_tissue']:+.6f} |",
        "",
        "## Truth table",
        "",
        "| Substrate/task | Positional content | Freedom | Enforcement | One common design? |",
        "|---|---|---|---|---|",
    ]
    for row in audit["triangle_truth_table"]:
        lines.append(
            f"| {row['substrate']} | {row['rich_positional_content']} | "
            f"{row['plastic_hereditary_freedom']} | {row['strong_goal_enforcement']} | "
            f"{row.get('same_design_all_three', row.get('same_run_and_endpoint', False))} |"
        )
    lines.extend(
        [
            "",
            "## Claim verdicts",
            "",
            "| Claim | Verdict |",
            "|---|---|",
        ]
    )
    for claim, finding in audit["claim_assessment"].items():
        lines.append(f"| {claim.replace('_', ' ')} | `{finding['status']}` |")
    lines.extend(
        [
            "",
            "## Replacement wording",
            "",
            str(audit["replacement_wording"]),
            "",
            "## Reproducibility",
            "",
            f"- Inputs hashed: {audit['input_file_count']}",
            f"- All independently transcribed config digests match: {audit['all_source_config_digests_match']}",
            f"- E44 rows reconstruct: {e44['all_reported_gates_and_summaries_match']}",
            f"- E49 rows reconstruct: {e49['all_reported_gates_and_summaries_match']}",
            f"- E53 shard-derived fields reconstruct: {e53['all_shard_derived_reported_fields_match']}",
            f"- E54 rows reconstruct: {e54['all_reported_gates_and_summaries_match']}",
            "- Fresh scientific futures: 0",
            "- Historical simulator paths replayed: 0",
            "",
        ]
    )
    return "\n".join(lines)
