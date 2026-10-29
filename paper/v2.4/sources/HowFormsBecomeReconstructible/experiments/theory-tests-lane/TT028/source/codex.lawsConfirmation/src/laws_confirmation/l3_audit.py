"""Outcome-known retained-artifact audit for L03.

No scientific trajectories are generated here. The audit rebuilds statistics
from historical lower-level shards and treats historical source as read-only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker, audit_e19, audit_e24
from .atlas_math import (
    centroids,
    cluster_category_stats,
    pca_shape,
    placement_nulls,
    rank_cdf_columns,
    scale_universe_statistics,
    two_nn_dimension,
    world_label_permutation_null,
)
from .eca_math import seed_rng
from .io import canonical_digest
from .stats import close


GARD_WORLDS = ("g1_3sp_m4", "g2_4sp_m4", "g3_3sp_m5", "g4_4sp_m5")
FORMALISM_BY_WORLD = {
    "g1_3sp_m4": "gard_chemistry",
    "g2_4sp_m4": "gard_chemistry",
    "g3_3sp_m5": "gard_chemistry",
    "g4_4sp_m5": "gard_chemistry",
    "grn_geneweb": "gene_web",
    "xeno_polymer": "binary_polymer",
}

SCALE_SPECS = (
    {
        "name": "u1_3sp_m4",
        "n_types": 3,
        "beta_levels": (0.0, 1.0, 4.0),
        "n_min": 4,
        "n_max": 8,
        "complete": True,
        "sample_centers": 0,
    },
    {
        "name": "u2_4sp_m4",
        "n_types": 4,
        "beta_levels": (0.0, 4.0),
        "n_min": 4,
        "n_max": 8,
        "complete": True,
        "sample_centers": 0,
    },
    {
        "name": "u3_3sp_m5",
        "n_types": 3,
        "beta_levels": (0.0, 1.0, 4.0),
        "n_min": 5,
        "n_max": 10,
        "complete": True,
        "sample_centers": 0,
    },
    {
        "name": "u4_4sp_m5",
        "n_types": 4,
        "beta_levels": (0.0, 4.0),
        "n_min": 5,
        "n_max": 10,
        "complete": True,
        "sample_centers": 0,
    },
    {
        "name": "u5_5sp_m4",
        "n_types": 5,
        "beta_levels": (0.0, 4.0),
        "n_min": 4,
        "n_max": 8,
        "complete": False,
        "sample_centers": 384,
    },
)


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def _track_package(tracker: InputTracker, root: Path) -> None:
    tracker.add(root / "EXPECTATIONS.md")
    for path in sorted((root / "src").rglob("*.py")):
        tracker.add(path)


def _load_npz(
    tracker: InputTracker, path: Path, required: Iterable[str]
) -> dict[str, np.ndarray]:
    source = tracker.add(path)
    with np.load(source, allow_pickle=False) as payload:
        missing = [name for name in required if name not in payload]
        if missing:
            raise ValueError(f"missing arrays {missing} in {source}")
        return {name: payload[name].copy() for name in required}


def _npz_digest(value: np.ndarray) -> str:
    return str(value.item() if value.ndim == 0 else value)


def _recursive_close(left: Any, right: Any, tolerance: float = 1e-11) -> bool:
    numeric = (int, float, np.integer, np.floating)
    if left is None and isinstance(right, numeric) and np.isnan(right):
        return True
    if right is None and isinstance(left, numeric) and np.isnan(left):
        return True
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _recursive_close(left[key], right[key], tolerance) for key in left
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            _recursive_close(a, b, tolerance) for a, b in zip(left, right)
        )
    if isinstance(left, (bool, np.bool_)) or isinstance(right, (bool, np.bool_)):
        return bool(left) == bool(right)
    if isinstance(left, numeric) and isinstance(right, numeric):
        return close(float(left), float(right), tolerance)
    return left == right


def source_config_digests() -> dict[str, str]:
    """Canonical hashes of source-default configs, transcribed independently."""

    rosetta = {
        "mode": "full",
        "rules_per_gard_world": 64,
        "curve_g": 8,
        "strict_census_bound": 250_000,
        "strict_mc_futures": 8_192,
        "alien_tables": 8,
        "alien_futures": 256,
        "linkage": "average",
        "cluster_threshold": 0.35,
        "min_worlds_for_archetype": 3,
        "selection_seed_tag": "rosetta-select-v1",
    }
    eca_bridge = {
        "mode": "full",
        "curve_g": 8,
        "futures": 128,
        "n_eca_rules_per_phase": 8,
        "n_gard_rules": 16,
        "n_random_nulls": 64,
        "n_null_draws": 512,
        "xeno_futures": 256,
        "n_xeno_tables": 8,
        "split_tag": "eca-bridge-split-v1",
        "select_tag": "eca-bridge-select-v1",
        "placement_traj_tag": "eca-place-v1",
        "dev_traj_tag": "eca-bridge-dev-v1",
        "confirm_traj_tag": "eca-bridge-confirm-v1",
        "transit_traj_tag": "eca-transit-v1",
    }
    life_family = {
        "mode": "full",
        "height": 16,
        "width": 16,
        "flip_noise": 0.002,
        "copy_error": 0.005,
        "activity_budget": 48,
        "t_min_sweeps": 4,
        "t_max_sweeps": 64,
        "inherit_threshold": 0.9,
        "coherence_threshold": 0.9,
        "distinct_threshold": 0.85,
        "strict_run": 8,
        "strict_horizon": 32,
        "mass_quantile": 0.75,
        "n_rules": 1024,
        "n_anchors": 256,
        "neighbors_per_anchor": 3,
        "n_seeds": 8,
        "futures": 64,
        "strict_band": (0.005, 0.5),
        "sample_tag": "life-family-sample-v1",
        "trajectory_seed_tag": "life-family-traj-v1",
    }
    morpho = {
        "mode": "full",
        "regions": ("posterior", "anterior", "center"),
        "signs": (1.0, -1.0),
        "durations": (4, 8),
        "n_gps_tissues": 24,
        "futures": 48,
        "horizon": 20,
        "zap_generation": 3,
        "n_targets": 6,
        "mass_quantile": 0.75,
        "placement_tissues": 48,
        "placement_seeds": 16,
        "placement_futures": 32,
        "n_null_draws": 256,
        "fidelity_seeds": 4,
        "fidelity_futures": 32,
        "dev_tag": "gps-dev-v1",
        "truth_tag": "gps-truth-v1",
    }
    sealed2 = {
        "mode": "full",
        "eca_futures": 128,
        "worm_tissues": 24,
        "placement_tissues": 48,
        "placement_futures": 32,
    }
    scale = {
        "mode": "scale",
        "break_window": 8,
        "occupancy_horizon": 8,
        "mass_quantile": 0.5,
        "max_support": 12,
        "dev_split_tag": "bridge-dev-eval-v1",
        "sample_seed_tag": "atlas-scale-sample-v1",
        "metric_seed_tag": "atlas-scale-metric-v1",
        "metric_pair_count": 2048,
        "correspondence_shuffles": 128,
        "shard_size": 64,
        "universes": SCALE_SPECS,
    }
    return {
        name: canonical_digest(config)
        for name, config in {
            "rosetta_atlas": rosetta,
            "eca_bridge": eca_bridge,
            "life_family": life_family,
            "morpho_gps": morpho,
            "sealed_battery_2": sealed2,
            "form_atlas_scale": scale,
        }.items()
    }


def audit_e13(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "rosetta_atlas")
    _track_package(tracker, root)
    result_root = root / "results/full"
    summary = tracker.json(result_root / "rosetta_summary.json")
    entities = tracker.csv(result_root / "entities.csv")
    archetype_rows = tracker.csv(result_root / "archetypes.csv")
    embedding = _load_npz(
        tracker,
        result_root / "embedding.npz",
        ("config_digest", "cloud", "archetype", "world", "labels"),
    )
    cloud = np.asarray(embedding["cloud"], dtype=np.float64)
    clusters = np.asarray(embedding["archetype"], dtype=np.int64)
    worlds = np.asarray(embedding["world"]).astype(str)
    labels = np.asarray(embedding["labels"]).astype(str)
    expected_digest = source_config_digests()["rosetta_atlas"]

    pca = pca_shape(cloud)
    twonn = two_nn_dimension(cloud, tag="rosetta-dim-v1")
    category = cluster_category_stats(clusters, worlds, FORMALISM_BY_WORLD)
    source_cross = category["categories"]["source_at_least_3_worlds"]

    unique_clusters = np.unique(clusters)
    cluster_world_counts = {
        int(cluster): len(set(worlds[clusters == cluster])) for cluster in unique_clusters
    }
    recalculated_archetypes = {
        int(cluster): {
            "n": int(np.sum(clusters == cluster)),
            "n_worlds": int(cluster_world_counts[int(cluster)]),
        }
        for cluster in unique_clusters
    }
    retained_archetypes = {
        int(row["archetype"]): {"n": int(row["n"]), "n_worlds": int(row["n_worlds"])}
        for row in archetype_rows
    }
    privacy = {
        world: float(
            np.mean(
                [cluster_world_counts[int(cluster)] == 1 for cluster in clusters[worlds == world]]
            )
        )
        for world in sorted(set(worlds))
    }
    reported_projection = {
        "n_entities": summary["n_entities"],
        "n_archetypes": summary["n_archetypes"],
        "cross_world_archetypes": summary["cross_world_archetypes"],
        "cross_world_mass_fraction": summary["cross_world_mass_fraction"],
        "pca_variance_shares": summary["pca_variance_shares"],
        "participation_ratio": summary["participation_ratio"],
        "two_nn_dimension": summary["two_nn_dimension"],
        "world_privacy_fraction": summary["world_privacy_fraction"],
        "gates": summary["gates"],
    }
    calculated_projection = {
        "n_entities": int(len(cloud)),
        "n_archetypes": int(len(unique_clusters)),
        "cross_world_archetypes": int(source_cross["n_clusters"]),
        "cross_world_mass_fraction": float(source_cross["entity_weighted_mass"]),
        "pca_variance_shares": pca["variance_shares"],
        "participation_ratio": pca["participation_ratio"],
        "two_nn_dimension": twonn["dimension"],
        "world_privacy_fraction": privacy,
        "gates": {
            "low_dimension": bool(float(twonn["dimension"]) <= 4.0),
            "cross_world_mass": bool(float(source_cross["entity_weighted_mass"]) >= 1 / 3),
        },
    }
    permutation = world_label_permutation_null(
        clusters,
        worlds,
        FORMALISM_BY_WORLD,
        draws=4_096,
        tag="l03-e13-world-label-null-v1",
    )
    return {
        "integrity": {
            "expected_source_config_digest": expected_digest,
            "summary_config_digest": summary.get("config_digest"),
            "embedding_config_digest": _npz_digest(embedding["config_digest"]),
            "config_digest_matches_source_default": summary.get("config_digest")
            == expected_digest,
            "embedding_digest_matches_summary": _npz_digest(embedding["config_digest"])
            == summary.get("config_digest"),
            "cloud_shape": list(cloud.shape),
            "entity_csv_rows": len(entities),
            "entity_csv_matches_embedding": bool(
                len(entities) == len(cloud)
                and all(row["label"] == label for row, label in zip(entities, labels))
                and all(row["world"] == world for row, world in zip(entities, worlds))
                and all(int(row["archetype"]) == cluster for row, cluster in zip(entities, clusters))
            ),
            "archetype_csv_matches_embedding": recalculated_archetypes == retained_archetypes,
        },
        "calculated": calculated_projection,
        "reported": reported_projection,
        "all_reported_fields_match": _recursive_close(calculated_projection, reported_projection),
        "two_nn_detail": twonn,
        "sharing_definitions": category,
        "world_label_permutation_diagnostic": permutation,
        "interpretation": {
            "per_world_rank_normalization": (
                "all six coordinate marginals are rank-CDF normalized separately within each world"
            ),
            "source_cross_world_definition": "cluster contains at least 3 of 6 worlds",
            "source_definition_can_be_gard_only": True,
            "baseline_entity_fraction_gard": float(np.mean(np.isin(worlds, GARD_WORLDS))),
        },
    }


def _profile_rows(entry: Mapping[str, Any], profile_key: str | None = None) -> list[list[float]]:
    profile = entry[profile_key] if profile_key else entry
    hazard = np.asarray(profile["hazard"], dtype=np.float64)
    inherited = np.asarray(profile["inherit_run"], dtype=np.float64)
    time_values = np.asarray(profile["time"], dtype=np.float64)
    strict = np.asarray(profile["strict"], dtype=np.float64)
    if hazard.ndim != 2 or inherited.shape != hazard.shape:
        raise ValueError("profile curve shapes do not agree")
    if len(strict) != len(time_values) or len(strict) != len(hazard):
        raise ValueError("profile launch dimensions do not agree")
    last = hazard.shape[1] - 1
    return [
        [
            float(hazard[row, min(1, last)]),
            float(hazard[row, min(3, last)]),
            float(hazard[row, last]),
            float(inherited[row, last]),
            float(np.log1p(max(time_values[row], 0.0))),
            float(strict[row]),
        ]
        for row in range(len(strict))
    ]


def _placement_clouds(
    plastic_root: Path, tracker: InputTracker
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    clouds: dict[str, np.ndarray] = {}
    integrity: dict[str, dict[str, Any]] = {}
    digests = source_config_digests()

    e20 = _experiment_root(plastic_root, "eca_bridge")
    _track_package(tracker, e20)
    e20_paths = sorted((e20 / "results/full/work").glob("placement_shard_*_of_04.json"))
    if len(e20_paths) != 4:
        raise ValueError(f"expected four E20 placement shards, found {len(e20_paths)}")
    e20_payloads = [tracker.json(path) for path in e20_paths]
    e20_entries = [entry for payload in e20_payloads for entry in payload["entries"]]
    e20_entries.sort(key=lambda entry: int(entry["rule"]))
    e20_raw = np.asarray([row for entry in e20_entries for row in _profile_rows(entry)])
    clouds["eca_e20"] = rank_cdf_columns(e20_raw)
    integrity["eca_e20"] = {
        "n_shards": len(e20_paths),
        "shard_ids": sorted(int(payload["shard"]) for payload in e20_payloads),
        "n_rules": len(e20_entries),
        "n_entities": len(e20_raw),
        "one_config_digest": len({payload.get("config_digest") for payload in e20_payloads})
        == 1,
        "config_matches_source_default": all(
            payload.get("config_digest") == digests["eca_bridge"] for payload in e20_payloads
        ),
    }

    e24 = _experiment_root(plastic_root, "life_family")
    _track_package(tracker, e24)
    e24_paths = sorted((e24 / "results/full/work").glob("family_shard_*_of_32.json"))
    if len(e24_paths) != 32:
        raise ValueError(f"expected 32 E24 family shards, found {len(e24_paths)}")
    e24_payloads = [tracker.json(path) for path in e24_paths]
    e24_entries = [entry for payload in e24_payloads for entry in payload["entries"]]
    e24_raw = np.asarray(
        [row for entry in e24_entries for row in _profile_rows(entry, "profile")]
    )
    clouds["life_e24"] = rank_cdf_columns(e24_raw)
    integrity["life_e24"] = {
        "n_shards": len(e24_paths),
        "shard_ids": sorted(int(payload["shard"]) for payload in e24_payloads),
        "n_rules": len(e24_entries),
        "n_entities": len(e24_raw),
        "one_config_digest": len({payload.get("config_digest") for payload in e24_payloads})
        == 1,
        "config_matches_source_default": all(
            payload.get("config_digest") == digests["life_family"] for payload in e24_payloads
        ),
    }

    e29 = _experiment_root(plastic_root, "morpho_gps")
    _track_package(tracker, e29)
    e29_paths = sorted((e29 / "results/full/work").glob("placement_shard_*_of_04.json"))
    if len(e29_paths) != 4:
        raise ValueError(f"expected four E29 placement shards, found {len(e29_paths)}")
    e29_payloads = [tracker.json(path) for path in e29_paths]
    e29_raw = np.asarray([row for payload in e29_payloads for row in payload["rows"]])
    clouds["tissue_e29"] = rank_cdf_columns(e29_raw)
    integrity["tissue_e29"] = {
        "n_shards": len(e29_paths),
        "n_entities": len(e29_raw),
        "one_config_digest": len({payload.get("config_digest") for payload in e29_payloads})
        == 1,
        "config_matches_source_default": all(
            payload.get("config_digest") == digests["morpho_gps"] for payload in e29_payloads
        ),
    }
    return clouds, integrity


def audit_placements(
    plastic_root: Path,
    tracker: InputTracker,
    e13: Mapping[str, Any],
) -> dict[str, Any]:
    rosetta_root = _experiment_root(plastic_root, "rosetta_atlas") / "results/full"
    embedding = _load_npz(
        tracker,
        rosetta_root / "embedding.npz",
        ("cloud", "archetype", "world"),
    )
    reference_cloud = np.asarray(embedding["cloud"], dtype=np.float64)
    reference_clusters = np.asarray(embedding["archetype"], dtype=np.int64)
    reference_worlds = np.asarray(embedding["world"]).astype(str)
    centroid_modes = {
        mode: centroids(
            reference_cloud,
            reference_clusters,
            reference_worlds,
            mode=mode,
            gard_worlds=GARD_WORLDS,
        )
        for mode in ("source_entity_weighted", "equal_world_weighted", "gard_only")
    }
    clouds, cloud_integrity = _placement_clouds(plastic_root, tracker)
    source_design = {
        "eca_e20": ("eca_bridge", "eca-placement-null-v1", 512),
        "life_e24": ("life_family", "life-family-placement-null-v1", 256),
        "tissue_e29": ("morpho_gps", "gps-placement-null-v1", 256),
    }
    records = {}
    for name, cloud in clouds.items():
        package, namespace, draws = source_design[name]
        _, source_centroids = centroid_modes["source_entity_weighted"]
        source_result = placement_nulls(
            cloud,
            source_centroids,
            draws=draws,
            tag=namespace,
            seed_parts=(len(cloud),),
        )
        package_root = _experiment_root(plastic_root, package)
        reported = tracker.json(package_root / "results/full/placement.json")
        reported_projection = {
            "n_entities": int(reported["n_entities"]),
            "observed": float(
                reported.get("observed", reported.get("observed_mean_nearest_archetype_distance"))
            ),
            "random_null_q05": float(reported["random_null_q05"]),
            "shuffled_null_q05": float(reported["shuffled_null_q05"]),
            "placement_beats_random_null": bool(reported["gates"]["placement_beats_random_null"]),
            "placement_beats_shuffled_null": bool(
                reported["gates"]["placement_beats_shuffled_null"]
            ),
        }
        calculated_projection = {
            key: source_result[key]
            for key in (
                "n_entities",
                "observed",
                "random_null_q05",
                "shuffled_null_q05",
                "placement_beats_random_null",
                "placement_beats_shuffled_null",
            )
        }
        stress = {}
        for mode in ("equal_world_weighted", "gard_only"):
            _, alternative_centroids = centroid_modes[mode]
            stress[mode] = placement_nulls(
                cloud,
                alternative_centroids,
                draws=1_024,
                tag="l03-placement-stress-v1",
                seed_parts=(name, mode, len(cloud)),
            )
        records[name] = {
            "integrity": cloud_integrity[name],
            "coordinate_means_after_rank_cdf": [float(value) for value in cloud.mean(axis=0)],
            "source_recalculation": source_result,
            "reported_projection": reported_projection,
            "all_reported_fields_match": _recursive_close(
                calculated_projection, reported_projection, tolerance=5e-11
            ),
            "centroid_dependence_stress": stress,
            "prospective_status": (
                "descriptive in EXPECTATIONS.md"
                if name == "life_e24"
                else "predeclared placement gate"
            ),
        }

    sealed_root = _experiment_root(plastic_root, "sealed_battery_2")
    _track_package(tracker, sealed_root)
    sealed = tracker.json(sealed_root / "results/full/component_placements.json")
    battery = tracker.json(sealed_root / "results/full/battery_verdict.json")
    source_text = tracker.add(sealed_root / "src/sealed_battery_2/battery.py").read_text(
        encoding="utf-8"
    )
    sealed_recalculated = {}
    exploratory_pairs = {
        "eca": records["eca_e20"]["source_recalculation"]["observed"],
        "tissue": records["tissue_e29"]["source_recalculation"]["observed"],
    }
    for substrate in ("eca", "tissue"):
        row = sealed[substrate]
        gate = bool(row["observed"] < row["random_q05"] and row["observed"] < row["shuffled_q05"])
        sealed_recalculated[substrate] = {
            "gate_from_aggregates": gate,
            "stored_gate_matches": gate == bool(row["gate"]),
            "exploratory_observed": float(exploratory_pairs[substrate]),
            "sealed_observed": float(row["observed"]),
            "absolute_difference": abs(
                float(exploratory_pairs[substrate]) - float(row["observed"])
            ),
            "difference_below_0.001": abs(
                float(exploratory_pairs[substrate]) - float(row["observed"])
            )
            < 0.001,
            "same_to_three_decimals": round(float(exploratory_pairs[substrate]), 3)
            == round(float(row["observed"]), 3),
            "lower_level_rows_retained": False,
        }
    return {
        "reference_atlas": {
            "n_entities": e13["calculated"]["n_entities"],
            "n_source_centroids": len(centroid_modes["source_entity_weighted"][0]),
            "n_equal_world_centroids": len(centroid_modes["equal_world_weighted"][0]),
            "n_gard_only_centroids": len(centroid_modes["gard_only"][0]),
            "shared_dependency": "all placements use the same E13 embedding and archetype labels",
        },
        "placements": records,
        "sealed_e34": {
            "expected_source_config_digest": source_config_digests()["sealed_battery_2"],
            "stored_config_digest": sealed.get("config_digest"),
            "config_matches_source_default": sealed.get("config_digest")
            == source_config_digests()["sealed_battery_2"],
            "component_gate": bool(sealed["gate"]),
            "battery_gate": bool(battery["verdict"]["placements"]),
            "component_and_battery_agree": bool(sealed["gate"])
            == bool(battery["verdict"]["placements"]),
            "substrates": sealed_recalculated,
            "fresh_namespaces_present_in_source": {
                "eca": "sealed2-eca-place-v1" in source_text,
                "tissue": "sealed2-tissue-place-v1" in source_text,
            },
            "evidence_limit": (
                "aggregate distances and null quantiles only; E34 retains no entity rows"
            ),
        },
    }


def _bridge_phase_recalculation(payload: Mapping[str, Any]) -> dict[str, Any]:
    pairs = payload["pairs"]
    occupancy = np.asarray([bool(row["beats_occupancy"]) for row in pairs])
    shuffled = np.asarray([bool(row["beats_shuffled"]) for row in pairs])
    random_median = np.asarray([bool(row["beats_random_median"]) for row in pairs])
    all_nulls = occupancy & shuffled & random_median
    rng = seed_rng("eca-bridge-boot-v1", len(pairs))
    draws = rng.integers(0, len(pairs), size=(4_096, len(pairs)))
    interval = [
        float(np.quantile(all_nulls[draws].mean(axis=1), quantile))
        for quantile in (0.025, 0.975)
    ]
    result = {
        "n_pairs": len(pairs),
        "beats_occupancy_fraction": float(occupancy.mean()),
        "beats_shuffled_fraction": float(shuffled.mean()),
        "beats_random_median_fraction": float(random_median.mean()),
        "beats_all_nulls_fraction": float(all_nulls.mean()),
        "beats_all_nulls_ci95": interval,
    }
    if payload["summary"]["phase"] == "confirm":
        result["gate_bridge"] = bool(
            result["beats_all_nulls_fraction"] >= 0.85 and interval[0] > 2 / 3
        )
    return result


def _e20_transitivity_gate(gates: Mapping[str, Any]) -> dict[str, bool]:
    gate1 = bool(
        gates["composed_beats_all_nulls_fraction"] >= 2 / 3
        and gates["composed_beats_ci_low"] > 0.5
    )
    gate2 = bool(
        gates["mean_agreement_direct_vs_composed"]
        >= gates["mean_shuffled_agreement"] + 0.25
        and gates["retains_direct_advantage_fraction"] >= 0.5
    )
    return {"gate1": gate1, "gate2": gate2, "transitivity_confirmed": gate1 and gate2}


def _e12_transitivity_gate(gates: Mapping[str, Any]) -> dict[str, bool]:
    gate1 = bool(
        gates["composed_beats_all_nulls_fraction"] >= 2 / 3
        and gates["composed_beats_ci_low"] > 0.5
    )
    gate2 = bool(
        gates["mean_agreement_direct_vs_composed"]
        > gates["shuffled_agreement_baseline"] + 0.1
        and gates["retains_direct_advantage_fraction"] >= 2 / 3
    )
    return {"gate1": gate1, "gate2": gate2, "transitivity_confirmed": gate1 and gate2}


def audit_dictionaries(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    e20_root = _experiment_root(plastic_root, "eca_bridge")
    _track_package(tracker, e20_root)
    dev = tracker.json(e20_root / "results/full/bridge_dev.json")
    confirm = tracker.json(e20_root / "results/full/bridge_confirm.json")
    transit = tracker.json(e20_root / "results/full/transitivity_confirm.json")
    transit_dev = tracker.json(e20_root / "results/full/transitivity_dev.json")
    dev_calc = _bridge_phase_recalculation(dev)
    confirm_calc = _bridge_phase_recalculation(confirm)
    fields = tuple(dev_calc)
    e20_transit_calc = _e20_transitivity_gate(transit["gates"])

    e12_root = _experiment_root(plastic_root, "xeno_grn")
    _track_package(tracker, e12_root)
    e12 = tracker.json(e12_root / "results/full/transitivity_summary.json")
    e12_calc = _e12_transitivity_gate(e12["gates"])

    e18_root = _experiment_root(plastic_root, "sealed_battery")
    _track_package(tracker, e18_root)
    e18_component = tracker.json(e18_root / "results/full/component_transitivity.json")
    e18_summary = tracker.json(e18_root / "results/full/sealed_transitivity_summary.json")
    e18_battery = tracker.json(e18_root / "results/full/battery_verdict.json")
    e18_gate = bool(
        e18_component["composed_beats_fraction"] >= 0.85
        and e18_component["agreement"] >= e18_component["shuffled_agreement"] + 0.25
        and e18_component["retains_fraction"] >= 2 / 3
    )

    e20_source = tracker.add(e20_root / "src/eca_bridge/transitivity.py").read_text(
        encoding="utf-8"
    )
    e12_source = tracker.add(e12_root / "src/xeno_grn/campaign.py").read_text(
        encoding="utf-8"
    )
    return {
        "e20_direct_gard_eca_bridge": {
            "integrity": {
                "expected_config_digest": source_config_digests()["eca_bridge"],
                "all_result_digests_match": all(
                    payload.get("config_digest") == source_config_digests()["eca_bridge"]
                    for payload in (dev, confirm, transit, transit_dev)
                ),
                "dev_and_confirm_rule_sets_disjoint": set(dev["summary"]["eca_rules"]).isdisjoint(
                    confirm["summary"]["eca_rules"]
                ),
                "confirm_uses_dev_scaler": dev["summary"]["scaler"]
                == confirm["summary"]["scaler"],
            },
            "dev_recalculated": dev_calc,
            "dev_reported_matches": _recursive_close(
                dev_calc, {key: dev["summary"][key] for key in fields}
            ),
            "confirm_recalculated": confirm_calc,
            "confirm_reported_matches": _recursive_close(
                confirm_calc, {key: confirm["summary"][key] for key in confirm_calc}
            ),
            "prospective_gate_passes": bool(confirm_calc["gate_bridge"]),
        },
        "e20_eca_gard_xeno_composition": {
            "reported": transit["gates"],
            "recalculated_gates": e20_transit_calc,
            "stored_gates_match": {
                "gate1": e20_transit_calc["gate1"]
                == bool(transit["gates"]["gate1_composed_bridge_works"]),
                "gate2": e20_transit_calc["gate2"]
                == bool(transit["gates"]["gate2_composed_matches_direct"]),
                "overall": e20_transit_calc["transitivity_confirmed"]
                == bool(transit["gates"]["transitivity_confirmed"]),
            },
            "pair_level_records_retained": False,
            "composition_uses_direct_map": "direct" in e20_source.split("def _composed", 1)[1].split(
                "def _phase_records", 1
            )[0],
        },
        "e12_xeno_gard_grn_composition": {
            "reported": e12["gates"],
            "recalculated_gates": e12_calc,
            "stored_gates_match": {
                "gate1": e12_calc["gate1"] == bool(e12["gates"]["gate1_composed_bridge_works"]),
                "gate2": e12_calc["gate2"] == bool(e12["gates"]["gate2_composed_matches_direct"]),
                "overall": e12_calc["transitivity_confirmed"]
                == bool(e12["gates"]["transitivity_confirmed"]),
            },
            "pair_level_records_retained": False,
            "composition_uses_direct_map": "direct" in e12_source.split(
                "def _composed_coupling", 1
            )[1].split("def run_transitivity", 1)[0],
        },
        "e18_sealed_three_formalism_composition": {
            "component": e18_component,
            "summary": e18_summary["gates"],
            "gate_recalculated": e18_gate,
            "component_gate_matches": e18_gate == bool(e18_component["gate"]),
            "battery_gate_matches": e18_gate
            == bool(e18_battery["verdict_table"]["transitivity"]),
            "pair_level_records_retained": False,
        },
        "dependency_interpretation": {
            "composition": (
                "pair-specific early-behaviour nearest-neighbour maps are multiplied through "
                "16 frozen GARD mediator profiles and averaged"
            ),
            "development_fit": "held-out score-block scales are fitted on development pairs",
            "confirm_information": (
                "confirm profiles supply early-behaviour fingerprints used to construct each map"
            ),
            "direct_comparator": (
                "a direct confirm-pair nearest-neighbour map is computed for agreement and retained-advantage scoring"
            ),
            "accurate_narrow_reading_of_without_direct_fitting": (
                "the composed map does not use the direct endpoint-to-endpoint map in its construction"
            ),
            "inaccurate_expansions": [
                "no fitting anywhere",
                "no confirm-set information",
                "no reused mediator",
                "independent implementation",
            ],
        },
    }


def _load_scale_universe(
    tracker: InputTracker,
    root: Path,
    spec: Mapping[str, Any],
    expected_digest: str,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    universe_root = root / "work/scale" / str(spec["name"])
    edge_payload = _load_npz(tracker, universe_root / "edges.npz", ("config_digest", "edges", "rule_ids"))
    paths = sorted(universe_root.glob("forms_*.npz"))
    if not paths:
        raise FileNotFoundError(f"no scale shards in {universe_root}")
    keys = ("config_digest", "rule_ids", "features", "break_prob", "supports", "support_sizes")
    shards = [_load_npz(tracker, path, keys) for path in paths]
    digests = {_npz_digest(shard["config_digest"]) for shard in shards}
    digests.add(_npz_digest(edge_payload["config_digest"]))
    merged = {
        key: np.concatenate([shard[key] for shard in shards], axis=0)
        for key in ("rule_ids", "features", "break_prob", "supports", "support_sizes")
    }
    order = np.argsort(merged["rule_ids"], kind="stable")
    merged = {key: value[order] for key, value in merged.items()}
    merged["edges"] = edge_payload["edges"]
    integrity = {
        "n_shards": len(paths),
        "one_config_digest": len(digests) == 1,
        "config_digest": next(iter(digests)) if len(digests) == 1 else sorted(digests),
        "config_matches_source_default": digests == {expected_digest},
        "n_rules": int(len(merged["rule_ids"])),
        "unique_rules": int(len(np.unique(merged["rule_ids"]))),
        "edge_rule_ids_match": np.array_equal(
            np.sort(np.asarray(edge_payload["rule_ids"])), np.sort(merged["rule_ids"])
        ),
    }
    return merged, integrity


def audit_atlas_laws(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    scale_root = _experiment_root(plastic_root, "form_atlas")
    tracker.add(scale_root / "EXPECTATIONS_SCALE.md")
    tracker.add(scale_root / "EXPECTATIONS.md")
    for path in sorted((scale_root / "src").rglob("*.py")):
        tracker.add(path)
    result_root = scale_root / "results/scale"
    summary = tracker.json(result_root / "scale_summary.json")
    manifest = tracker.json(result_root / "scale_manifest.json")
    tracker.add(result_root / "scaling_table.csv")
    e6_summary = tracker.json(scale_root / "results/full/atlas_summary.json")
    expected_digest = source_config_digests()["form_atlas_scale"]
    reported_rows = {row["universe"]: row for row in summary["scaling_table"]}

    primary = {}
    sealed = {}
    lower_level: dict[str, dict[str, np.ndarray]] = {}
    for spec in SCALE_SPECS:
        name = str(spec["name"])
        arrays, integrity = _load_scale_universe(tracker, scale_root, spec, expected_digest)
        lower_level[name] = arrays
        calculated = scale_universe_statistics(
            arrays["rule_ids"],
            arrays["features"],
            arrays["supports"],
            arrays["support_sizes"],
            arrays["edges"],
            n_types=int(spec["n_types"]),
            n_min=int(spec["n_min"]),
            beta_levels=len(spec["beta_levels"]),
            metric_seed_tag="atlas-scale-metric-v1",
            dev_split_tag="bridge-dev-eval-v1",
            metric_pair_count=2_048,
        )
        reported = reported_rows[name]
        projection_calculated = {
            "n_rules": calculated["n_rules"],
            "n_launch": calculated["n_launch"],
            "n_forms": calculated["n_forms"],
            "heavy_tail_top_decile_share": calculated["heavy_tail_top_decile_share"],
            "adjacent_mean_jaccard": calculated["adjacent_mean_jaccard"],
            "random_mean_jaccard": calculated["random_mean_jaccard"],
            "smoothness_ratio": calculated["smoothness_ratio"],
            "mean_library_size": calculated["mean_library_size"],
            "metric_eval_spearman_learned": calculated["metric"]["eval_spearman_learned"],
            "metric_eval_spearman_hamming": calculated["metric"]["eval_spearman_hamming"],
            "metric_improvement": calculated["metric"]["improvement"],
        }
        projection_reported = {key: reported[key] for key in projection_calculated}
        primary[name] = {
            "complete": bool(spec["complete"]),
            "integrity": integrity,
            "calculated": calculated,
            "reported_projection": projection_reported,
            "all_reported_fields_match": _recursive_close(
                projection_calculated, projection_reported, tolerance=2e-10
            ),
        }
        if name in ("u3_3sp_m5", "u4_4sp_m5"):
            sealed[name] = scale_universe_statistics(
                arrays["rule_ids"],
                arrays["features"],
                arrays["supports"],
                arrays["support_sizes"],
                arrays["edges"],
                n_types=int(spec["n_types"]),
                n_min=int(spec["n_min"]),
                beta_levels=len(spec["beta_levels"]),
                metric_seed_tag="atlas-scale-metric-sealed-v1",
                dev_split_tag="sealed-split-v1",
                metric_pair_count=2_048,
            )

    e18_root = _experiment_root(plastic_root, "sealed_battery")
    _track_package(tracker, e18_root)
    e18_atlas = tracker.json(e18_root / "results/full/component_atlas_laws.json")
    sealed_projection = {
        name: {
            "smoothness": sealed[name]["smoothness_ratio"],
            "heavy_tail": sealed[name]["heavy_tail_top_decile_share"],
            "metric_improvement": sealed[name]["metric"]["improvement"],
        }
        for name in sealed
    }
    sealed_gate = bool(
        sealed_projection["u3_3sp_m5"]["smoothness"] >= 2.5
        and sealed_projection["u4_4sp_m5"]["smoothness"] >= 2.5
        and sealed_projection["u3_3sp_m5"]["heavy_tail"] >= 0.35
        and sealed_projection["u3_3sp_m5"]["metric_improvement"] > 0
    )

    e19 = audit_e19(plastic_root, tracker)
    e24 = audit_e24(plastic_root, tracker)
    comparable = {
        **{
            f"E7_{name}": {
                "smoothness": row["calculated"]["smoothness_ratio"],
                "heavy_tail": row["calculated"]["heavy_tail_top_decile_share"],
                "metric_improvement": row["calculated"]["metric"]["improvement"],
            }
            for name, row in primary.items()
            if row["complete"]
        },
        "E19_ECA": {
            "smoothness": e19["calculated"]["smoothness_ratio"],
            "heavy_tail": e19["calculated"]["heavy_tail_share"],
            "metric_improvement": e19["calculated"]["metric_rho_descriptors"]
            - e19["calculated"]["metric_rho_hamming"],
        },
        "E24_Life_family": {
            "smoothness": e24["calculated"]["smoothness_ratio"],
            "heavy_tail": e24["calculated"]["heavy_tail_share"],
            "metric_improvement": None,
        },
    }
    literal_range_checks = {
        name: {
            "smoothness_in_3_to_7": bool(3.0 <= row["smoothness"] <= 7.0),
            "heavy_tail_in_0.6_to_0.7": bool(0.6 <= row["heavy_tail"] <= 0.7),
            "qualitative_smoothness_ge_2": bool(row["smoothness"] >= 2.0),
            "qualitative_tail_ge_0.35": bool(row["heavy_tail"] >= 0.35),
        }
        for name, row in comparable.items()
    }
    metric_rows = {
        name: row["metric_improvement"]
        for name, row in comparable.items()
        if row["metric_improvement"] is not None
    }
    return {
        "integrity": {
            "expected_scale_config_digest": expected_digest,
            "summary_config_digest": summary.get("config_digest"),
            "manifest_config_digest": manifest.get("config_digest"),
            "summary_and_manifest_match_source_default": summary.get("config_digest")
            == manifest.get("config_digest")
            == expected_digest,
        },
        "e6_original_atlas_reported": {
            "smoothness": e6_summary["smoothness"]["jaccard_ratio"],
            "heavy_tail": e6_summary["heavy_tail_top_decile_share"],
            "metric_improvement": e6_summary["metric"]["improvement"],
            "note": "same u1 universe; E7 supplies a lower-level rebuild with a different frozen random draw",
        },
        "e7_primary_recalculation": primary,
        "e18_sealed_recalculation": {
            "calculated": sealed_projection,
            "reported": {
                name: {
                    "smoothness": e18_atlas[name]["smoothness"],
                    "heavy_tail": e18_atlas[name]["heavy_tail"],
                    "metric_improvement": e18_atlas[name]["metric_improvement"],
                }
                for name in sealed_projection
            },
            "all_reported_fields_match": _recursive_close(
                sealed_projection,
                {
                    name: {
                        "smoothness": e18_atlas[name]["smoothness"],
                        "heavy_tail": e18_atlas[name]["heavy_tail"],
                        "metric_improvement": e18_atlas[name]["metric_improvement"],
                    }
                    for name in sealed_projection
                },
                tolerance=2e-10,
            ),
            "gate_recalculated": sealed_gate,
            "stored_gate_matches": sealed_gate == bool(e18_atlas["gate"]),
            "freshness_limit": "fresh splits and pair draws over reused exact deterministic shards",
        },
        "e19_reused_lower_level_audit": {
            "calculated": e19["calculated"],
            "null_sensitivity": e19["null_sensitivity"],
            "metric_sensitivity": e19["metric_sensitivity"],
            "all_reported_fields_match": all(e19["reported_match"].values()),
        },
        "e24_reused_lower_level_audit": {
            "calculated": e24["calculated"],
            "null_sensitivity": e24["null_sensitivity"],
            "all_reported_fields_match": all(e24["reported_match"].values()),
        },
        "comparable_complete_atlases": comparable,
        "literal_and_qualitative_range_checks": literal_range_checks,
        "all_complete_in_literal_smoothness_range": all(
            row["smoothness_in_3_to_7"] for row in literal_range_checks.values()
        ),
        "all_complete_in_literal_tail_range": all(
            row["heavy_tail_in_0.6_to_0.7"] for row in literal_range_checks.values()
        ),
        "all_complete_pass_qualitative_smoothness": all(
            row["qualitative_smoothness_ge_2"] for row in literal_range_checks.values()
        ),
        "all_complete_pass_qualitative_tail": all(
            row["qualitative_tail_ge_0.35"] for row in literal_range_checks.values()
        ),
        "metric_summary": {
            "primary_comparisons": metric_rows,
            "positive_count": sum(value > 0 for value in metric_rows.values()),
            "tested_count": len(metric_rows),
            "gard_learned_metric_includes_hamming": True,
            "eca_descriptors_only_comparator": True,
        },
        "sampled_frontier": {
            "name": "E7_u5_5sp_m4",
            "complete": False,
            "excluded_from_literal_range_adjudication": True,
            "smoothness": primary["u5_5sp_m4"]["calculated"]["smoothness_ratio"],
            "heavy_tail": primary["u5_5sp_m4"]["calculated"][
                "heavy_tail_top_decile_share"
            ],
        },
    }


def run_l3_retained_audit(plastic_root: Path) -> tuple[dict[str, Any], set[Path]]:
    plastic_root = plastic_root.resolve()
    tracker = InputTracker()
    tracker.add(plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md")
    ideas = plastic_root / IDEAS_RELATIVE
    tracker.add(ideas / "LAWS.md")
    tracker.add(ideas / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md")
    e13 = audit_e13(plastic_root, tracker)
    audit = {
        "schema_version": 1,
        "scope": "L03 retained atlas, placement, dictionary, and atlas-law audit",
        "outcome_blinding": "none; historical outcomes were known before this audit",
        "scientific_futures_generated": 0,
        "plastic_heredity_root": str(plastic_root),
        "e13": e13,
        "placements": audit_placements(plastic_root, tracker, e13),
        "dictionaries": audit_dictionaries(plastic_root, tracker),
        "atlas_laws": audit_atlas_laws(plastic_root, tracker),
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, tracker.paths


def markdown_report(audit: Mapping[str, Any]) -> str:
    def fmt(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    e13 = audit["e13"]
    categories = e13["sharing_definitions"]["categories"]
    label_null = e13["world_label_permutation_diagnostic"]
    placements = audit["placements"]
    dictionaries = audit["dictionaries"]
    laws = audit["atlas_laws"]
    lines = [
        "# L03 retained atlas and translation audit v1",
        "",
        "This is an outcome-known recalculation of retained artefacts, not a fresh simulation replication.",
        "",
        "## Integrity",
        "",
        f"- Input files hashed: {audit['input_file_count']}",
        f"- New scientific futures: {audit['scientific_futures_generated']}",
        f"- E13 summary fields rebuilt exactly: {e13['all_reported_fields_match']}",
        f"- E13 CSV/NPZ entity agreement: {e13['integrity']['entity_csv_matches_embedding']}",
        f"- E7 scale config/source digest agreement: {laws['integrity']['summary_and_manifest_match_source_default']}",
        "",
        "## E13: what `cross-world` means",
        "",
        f"- Source >=3-of-6-world mass: {fmt(categories['source_at_least_3_worlds']['entity_weighted_mass'])}",
        f"- Mass in clusters containing all three baseline formalisms: {fmt(categories['all_3_baseline_formalisms']['entity_weighted_mass'])}",
        f"- Equal-world version of all-three-formalism mass: {fmt(categories['all_3_baseline_formalisms']['equal_world_weighted_mass'])}",
        f"- Mass in clusters containing all six baseline worlds: {fmt(categories['all_6_baseline_worlds']['entity_weighted_mass'])}",
        f"- GARD share of E13 entities: {fmt(e13['interpretation']['baseline_entity_fraction_gard'])}",
        f"- Source sharing null mean / observed / upper-tail p: {fmt(label_null['source_at_least_3_worlds']['null_mean'])} / {fmt(label_null['source_at_least_3_worlds']['observed'])} / {fmt(label_null['source_at_least_3_worlds']['upper_tail_p'])}",
        f"- All-formalism sharing null mean / observed / upper-tail p: {fmt(label_null['all_3_baseline_formalisms']['null_mean'])} / {fmt(label_null['all_3_baseline_formalisms']['observed'])} / {fmt(label_null['all_3_baseline_formalisms']['upper_tail_p'])}",
        "- The source sharing gate has no comparable label null; its near-one value is expected from coarse clusters and world counts.",
        "",
        "## Prospective placement chain",
        "",
    ]
    for name, label in (
        ("eca_e20", "E20 ECA"),
        ("life_e24", "E24 Life-like family"),
        ("tissue_e29", "E29 voltage tissue"),
    ):
        row = placements["placements"][name]
        source = row["source_recalculation"]
        equal = row["centroid_dependence_stress"]["equal_world_weighted"]
        gard = row["centroid_dependence_stress"]["gard_only"]
        lines.extend(
            [
                f"- {label}: source {fmt(source['observed'])} vs random/shuffled q05 {fmt(source['random_null_q05'])}/{fmt(source['shuffled_null_q05'])}; rebuilt={row['all_reported_fields_match']}; equal-world gate={equal['placement_beats_random_null'] and equal['placement_beats_shuffled_null']}; GARD-only gate={gard['placement_beats_random_null'] and gard['placement_beats_shuffled_null']} ({row['prospective_status']})",
            ]
        )
    sealed = placements["sealed_e34"]
    lines.extend(
        [
            f"- E34 aggregate placement gate reproduces: {sealed['component_and_battery_agree']}; ECA/tissue differences from exploratory are {fmt(sealed['substrates']['eca']['absolute_difference'])}/{fmt(sealed['substrates']['tissue']['absolute_difference'])} (both <0.001), but conventional three-decimal strings are not identical.",
            "- E34 retains no entity-level placement rows, so its inequalities are verified at E2 rather than rebuilt at E3.",
            "",
            "## Translation dictionaries",
            "",
            f"- E12 three-formalism composition gate: {dictionaries['e12_xeno_gard_grn_composition']['recalculated_gates']['transitivity_confirmed']}",
            f"- E18 sealed three-formalism composition gate: {dictionaries['e18_sealed_three_formalism_composition']['gate_recalculated']}",
            f"- E20 extension composition gate: {dictionaries['e20_eca_gard_xeno_composition']['recalculated_gates']['transitivity_confirmed']}",
            f"- E20 direct prospective GARD-ECA bridge: {dictionaries['e20_direct_gard_eca_bridge']['confirm_recalculated']['beats_all_nulls_fraction']:.3f}, CI {dictionaries['e20_direct_gard_eca_bridge']['confirm_recalculated']['beats_all_nulls_ci95']}; gate={dictionaries['e20_direct_gard_eca_bridge']['prospective_gate_passes']}.",
            "- `Without direct fitting` is accurate only narrowly: the composed map does not consume the direct endpoint map. It still uses confirm-pair fingerprints, reused GARD mediators, and a dev-fitted score scaler; a direct map is computed as comparator.",
            "",
            "## Atlas-law ranges",
            "",
        ]
    )
    for name, row in laws["comparable_complete_atlases"].items():
        lines.append(
            f"- {name}: smoothness {fmt(row['smoothness'])}; top-decile share {fmt(row['heavy_tail'])}; metric improvement {fmt(row['metric_improvement'])}"
        )
    lines.extend(
        [
            f"- Every complete atlas passes qualitative smoothness >=2: {laws['all_complete_pass_qualitative_smoothness']}",
            f"- Every complete atlas passes the programme's concentration bar >=0.35: {laws['all_complete_pass_qualitative_tail']}",
            f"- Every complete atlas lies in literal 3-7x range: {laws['all_complete_in_literal_smoothness_range']}",
            f"- Every complete atlas lies in literal 0.6-0.7 range: {laws['all_complete_in_literal_tail_range']}",
            f"- Positive metric comparisons: {laws['metric_summary']['positive_count']}/{laws['metric_summary']['tested_count']}; GARD's learned comparator includes Hamming as one of its inputs.",
            "",
            "## First-pass clause verdict",
            "",
            "- Six-model placement: substantial and reproducible at the operational six-coordinate level, but `one catalogue` is too strong without qualification. The baseline overlap gate is non-discriminating, E24 placement was descriptive, and all placements inherit E13's representation.",
            "- Three-formalism composition: confirmed with narrower wording by E12 and fresh E18 aggregates; pair-level records were not retained, and the result is an ensemble-level early-behaviour map, not ontological identity.",
            "- Numerical atlas ranges: not confirmed as written. The broader qualitative smoothness/concentration claims survive the retained complete atlases.",
            "- Metric law: mixed and least portable; not a general law on this record.",
            "- E34: seals fresh ECA and tissue placement only, not all of L3.",
            "",
        ]
    )
    return "\n".join(lines)
