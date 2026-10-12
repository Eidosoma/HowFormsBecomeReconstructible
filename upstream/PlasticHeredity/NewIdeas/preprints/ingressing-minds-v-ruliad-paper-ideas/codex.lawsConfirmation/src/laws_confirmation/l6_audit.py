"""Outcome-known retained/replay audit for L06 competence-axis claims."""

from __future__ import annotations

import math
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .competence_math import axis_diagnostics, recalculate_grafts
from .eca_math import seed_rng
from .io import canonical_digest
from .stats import close, median, spearman


E29_EXPECTED_DIGEST = "2b95f98e2ae2eb2f092cf8a1f46868ba4879f093e88027513f02d3bbe9ffc4fc"
E32_EXPECTED_DIGEST = "df5a1aa7256335390c18260a60ebe704c0d445e229547a2a093f50d3d2166a93"
E27_EXPECTED_DIGEST = "48ac009655861e57fbcf6da4c08c982092f43910ed7828b170436dbf7391eee1"
E29_CONFIGS = 80
E29_FIDELITY_SEEDS = 4
E29_FIDELITY_FUTURES = 32
E29_HISTORICAL_FUTURES = E29_CONFIGS * E29_FIDELITY_SEEDS * E29_FIDELITY_FUTURES


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def _track_package(tracker: InputTracker, root: Path) -> None:
    for relative in ("EXPECTATIONS.md", "pyproject.toml"):
        path = root / relative
        if path.is_file():
            tracker.add(path)
    for directory in ("src", "tests"):
        if (root / directory).is_dir():
            for path in sorted((root / directory).rglob("*.py")):
                tracker.add(path)


def _config_digests() -> dict[str, str]:
    gps = {
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
    graft = {
        "mode": "full",
        "n_tissues": 16,
        "harvest_futures": 96,
        "harvest_generation": 13,
        "zap_generation": 3,
        "grafts_per_share": 32,
        "shares": (0.35, 0.5, 0.65),
        "graft_horizon": 12,
        "hold_generations": 4,
        "coherence": 0.9,
        "distinct": 0.85,
        "chimera_run": 8,
        "trajectory_seed_tag": "graft-traj-v1",
    }
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
    return {
        "morpho_gps": canonical_digest(gps),
        "collective_decision": canonical_digest(graft),
        "setpoint_rewrite": canonical_digest(rewrite),
    }


def source_config_digests() -> dict[str, str]:
    """Expose independently transcribed source defaults for tests."""

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
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return close(left, right)
    return left == right


def _install_source_paths(plastic_root: Path) -> None:
    ideas = plastic_root / IDEAS_RELATIVE
    packages = (
        "contract_bridge",
        "glider_test",
        "xeno_bridge",
        "voltage_web",
        "setpoint_rewrite",
    )
    for name in reversed(packages):
        source = str((ideas / name / "src").resolve())
        if source not in sys.path:
            sys.path.insert(0, source)


def _load_e27_conversions(
    plastic_root: Path, tracker: InputTracker
) -> tuple[dict[tuple[str, int], tuple[float, float]], dict[str, Any]]:
    root = _experiment_root(plastic_root, "setpoint_rewrite")
    paths = sorted(
        (root / "results/full/work").glob("rewrite_shard_*_of_08.json")
    )
    if len(paths) != 8:
        raise ValueError(f"expected 8 E27 shards, found {len(paths)}")
    payloads = [tracker.json(path) for path in paths]
    shard_ids = sorted(int(payload["shard"]) for payload in payloads)
    if shard_ids != list(range(8)):
        raise ValueError(f"incomplete E27 shard IDs: {shard_ids}")
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"E27 shard digests differ: {sorted(digests)}")
    coupling = {"band": 1.0, "under": 0.25, "over": 4.0}
    conversions: dict[tuple[str, int], tuple[float, float]] = {}
    for payload in payloads:
        for entry in payload["entries"]:
            key = (str(entry["cohort"]), int(entry["tissue"]))
            if key in conversions:
                raise ValueError(f"duplicate E27 conversion row: {key}")
            conversions[key] = (
                coupling[key[0]],
                float(entry["conversion"]),
            )
    counts = {
        cohort: sum(key[0] == cohort for key in conversions)
        for cohort in ("band", "under", "over")
    }
    if len(conversions) != E29_CONFIGS or counts != {
        "band": 48,
        "under": 16,
        "over": 16,
    }:
        raise ValueError(f"unexpected E27 conversion census: {counts}")
    return conversions, {
        "n_shards": len(paths),
        "shard_ids": shard_ids,
        "config_digest": next(iter(digests)),
        "n_rows": len(conversions),
        "cohort_counts": counts,
    }


def replay_e29_axis(
    plastic_root: Path,
    conversions: Mapping[tuple[str, int], tuple[float, float]],
    *,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Replay exactly E29's historical fidelity and null namespaces."""

    _install_source_paths(plastic_root)
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config
    from voltage_web.engine import run_seed

    rewrite = RewriteConfig()
    rows = []
    ordered = sorted(conversions.items())
    for completed, ((cohort, index), (coupling, conversion)) in enumerate(
        ordered, start=1
    ):
        tissue = tissue_config(index, coupling, rewrite)
        seed_fidelity = []
        seed_h_counts = []
        for seed_index in range(E29_FIDELITY_SEEDS):
            result = run_seed(
                seed_index,
                tissue,
                seed_rng("gps-axis-v1", cohort, index, seed_index),
                n_futures=E29_FIDELITY_FUTURES,
            )
            seed_h_counts.append(int(result.h_values.size))
            if result.h_values.size:
                seed_fidelity.append(float(result.h_values.mean()))
        rows.append(
            {
                "cohort": cohort,
                "tissue": index,
                "coupling": coupling,
                "conversion": conversion,
                "fidelity": float(np.mean(seed_fidelity)) if seed_fidelity else 0.0,
                "seed_fidelity": seed_fidelity,
                "seed_h_observation_counts": seed_h_counts,
            }
        )
        if progress is not None:
            progress(completed, len(ordered))

    fidelity = [float(row["fidelity"]) for row in rows]
    conversion = [float(row["conversion"]) for row in rows]
    rho = spearman(fidelity, conversion)
    rng = seed_rng("gps-axis-null-v1", len(rows))
    null = []
    for _ in range(512):
        shuffled = np.asarray(conversion)
        rng.shuffle(shuffled)
        null.append(spearman(fidelity, shuffled.tolist()))
    q05 = float(np.quantile(null, 0.05))
    return {
        "rows": rows,
        "rho_fidelity_vs_rewritability": rho,
        "null_q05": q05,
        "gate_maintainer_switcher_tradeoff": bool(rho < q05),
        "n_configs": len(rows),
        "source_null": {
            "namespace": "gps-axis-null-v1:80",
            "draws": len(null),
            "minimum": min(null),
            "median": median(null),
            "maximum": max(null),
        },
        "historical_namespace_futures_replayed": E29_HISTORICAL_FUTURES,
        "fresh_seed_domain": False,
    }


def audit_e29(
    plastic_root: Path,
    tracker: InputTracker,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    ideas = plastic_root / IDEAS_RELATIVE
    root = ideas / "morpho_gps"
    for package in (
        "morpho_gps",
        "setpoint_rewrite",
        "voltage_web",
        "contract_bridge",
        "glider_test",
        "xeno_bridge",
    ):
        _track_package(tracker, ideas / package)
    retained = tracker.json(root / "results/full/axis.json")
    conversions, conversion_integrity = _load_e27_conversions(plastic_root, tracker)
    replay = replay_e29_axis(plastic_root, conversions, progress=progress)
    diagnostics = axis_diagnostics(replay["rows"])
    source = tracker.add(root / "src/morpho_gps/pipeline.py").read_text(
        encoding="utf-8"
    )
    expectations = tracker.add(root / "EXPECTATIONS.md").read_text(
        encoding="utf-8"
    )
    retained_projection = {
        key: retained[key]
        for key in (
            "rho_fidelity_vs_rewritability",
            "null_q05",
            "gate_maintainer_switcher_tradeoff",
            "n_configs",
        )
    }
    replay_projection = {key: replay[key] for key in retained_projection}
    digests = _config_digests()
    return {
        "integrity": {
            "expected_config_digest": digests["morpho_gps"],
            "retained_config_digest": retained.get("config_digest"),
            "config_matches_source_default": (
                retained.get("config_digest") == digests["morpho_gps"]
                == E29_EXPECTED_DIGEST
            ),
            "e27_conversion_shards": conversion_integrity,
            "e27_config_matches_source_default": (
                conversion_integrity["config_digest"]
                == digests["setpoint_rewrite"]
                == E27_EXPECTED_DIGEST
            ),
            "historical_replay_matches_all_retained_fields": _recursive_close(
                replay_projection, retained_projection
            ),
            "field_matches": {
                key: _recursive_close(replay_projection[key], retained_projection[key])
                for key in retained_projection
            },
        },
        "registered_test": {
            "hypothesis": "negative maintainer/switcher trade-off",
            "reported_gate": bool(retained["gate_maintainer_switcher_tradeoff"]),
            "replayed_gate": bool(replay["gate_maintainer_switcher_tradeoff"]),
            "passes": bool(replay["gate_maintainer_switcher_tradeoff"]),
            "positive_threshold_preregistered": False,
            "reversal_named_as_risk_before_full_run": (
                "if fidelity and rewritability turn out" in expectations
                and '"competence axis"' in expectations
            ),
        },
        "historical_replay": replay,
        "fixed_diagnostics": diagnostics,
        "design": {
            "fidelity_source": "mean parent-daughter H across a historical 4 x 32 future stream",
            "rewritability_source": "E27 paired conversion fraction",
            "fidelity_stream_separate_from_e27_conversion_stream": True,
            "coupling_exactly_determined_by_cohort": True,
            "same_tissue_parameters_shared_across_three_cohorts_only_for_indices_0_to_15": True,
            "band_only_tissue_indices_16_to_47": True,
            "unbalanced_rows_by_cohort": True,
            "source_implements_factor_or_latent_variable_model": (
                "factor_analy" in source.lower() or "latent" in source.lower()
            ),
            "number_of_axis_observables": 2,
            "one_factor_model_identified": False,
            "held_out_positive_axis_test": False,
        },
    }


def _load_e32_entries(
    root: Path, tracker: InputTracker
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(
        (root / "results/full/work").glob("graft_shard_*_of_04.json")
    )
    if len(paths) != 4:
        raise ValueError(f"expected 4 E32 shards, found {len(paths)}")
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"E32 shard digests differ: {sorted(digests)}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    tissues = [int(entry["tissue"]) for entry in entries]
    if len(entries) != 16 or sorted(tissues) != list(range(16)):
        raise ValueError(f"unexpected E32 tissue census: {sorted(tissues)}")
    return entries, {
        "n_shards": len(paths),
        "config_digest": next(iter(digests)),
        "n_entries": len(entries),
        "unique_tissues": len(set(tissues)),
    }


def audit_e32(plastic_root: Path, tracker: InputTracker) -> dict[str, Any]:
    root = _experiment_root(plastic_root, "collective_decision")
    _track_package(tracker, root)
    retained = tracker.json(root / "results/full/graft_summary.json")
    entries, shard_integrity = _load_e32_entries(root, tracker)
    recalculated = recalculate_grafts(entries)
    config_digest = _config_digests()["collective_decision"]
    runner = tracker.add(root / "src/collective_decision/runner.py").read_text(
        encoding="utf-8"
    )
    pipeline = tracker.add(root / "src/collective_decision/pipeline.py").read_text(
        encoding="utf-8"
    )
    expectations = tracker.add(root / "EXPECTATIONS.md").read_text(
        encoding="utf-8"
    )
    source_projection = recalculated["source_projection"]
    return {
        "integrity": {
            "expected_config_digest": config_digest,
            "retained_config_digest": retained.get("config_digest"),
            "shard_config_digest": shard_integrity["config_digest"],
            "config_matches_source_default": (
                config_digest == E32_EXPECTED_DIGEST
                and retained.get("config_digest") == config_digest
                and shard_integrity["config_digest"] == config_digest
            ),
            "shards": shard_integrity,
            "summary_n_entries": int(retained["n_entries"]),
            "all_summary_gates_and_scalars_match": _recursive_close(
                source_projection, retained["gates"]
            ),
        },
        "recalculation": recalculated,
        "registered_gates": {
            "depth_wins": bool(source_projection["gate_depth_wins"]),
            "share_ladder": bool(source_projection["gate_share_ladder"]),
            "chimeras": bool(source_projection["gate_chimeras"]),
            "all_three_pass": all(
                bool(source_projection[key])
                for key in ("gate_depth_wins", "gate_share_ladder", "gate_chimeras")
            ),
        },
        "measurement_audit": {
            "winner_is_only_relative_closeness": (
                '> _cos(censuses[t, k], grafts["wild_ref"][k])' in runner
                and '> _cos(censuses[t, k], grafts["rw_ref"][k])' in runner
            ),
            "winner_has_absolute_parent_similarity_floor": False,
            "chimera_requires_distinct_from_both_not_close_to_both": (
                "distinct from BOTH parents" in runner
                and "config.distinct" in runner
            ),
            "compromise_or_intermediate_classifier_implemented": (
                "compromise" in runner.lower() or "intermediate" in runner.lower()
            ),
            "alive_counts_retained": False,
            "individual_scores_or_trajectories_retained": False,
            "analog_parent_or_graft_charge_retained": False,
            "unresolved_outcomes_classifiable_as_stable_compromise": False,
            "threshold_sensitivity_reconstructable": False,
        },
        "confounds": {
            "nominal_share_implemented_by_rounded_columns": (
                "cols = int(round(share * tissue.width))" in runner
            ),
            "wild_always_left": 'grafts[k, :, :cols] = h["V"][wi, :, :cols]' in runner,
            "rewritten_always_right": 'grafts[k, :, cols:] = h["V"][ri, :, cols:]' in runner,
            "orientation_counterbalanced": False,
            "parent_identity_randomized": False,
            "same_harvest_pool_reused_within_tissue": True,
            "grafts_independent_within_tissue": False,
            "share_effect_separable_from_position": False,
            "bulk_average_prediction_quantitatively_tested": False,
        },
        "chronology": {
            "known_bulk_charge_compromise_risk_recorded": (
                "bulk charge is the mean" in expectations
            ),
            "source_comment_calls_texture_contest_compositional": (
                "COMPOSITIONAL homeostat" in expectations
            ),
            "pipeline_aggregates_only_counts": "def totals(share)" in pipeline,
        },
    }


def run_l6_audit(
    plastic_root: Path,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    manuscript = tracker.add(plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md")
    manuscript_text = manuscript.read_text(encoding="utf-8").lower()
    e29 = audit_e29(plastic_root, tracker, progress=progress)
    e32 = audit_e32(plastic_root, tracker)
    audit = {
        "schema_version": 1,
        "scope": "L06 retained E32 audit plus E29 historical-namespace replay",
        "outcome_blinding": "none; retained aggregate outcomes known",
        "fresh_scientific_futures_generated": 0,
        "historical_namespace_futures_replayed": E29_HISTORICAL_FUTURES,
        "e29": e29,
        "e32": e32,
        "claim_assessment": {
            "positive_covariance_reproduced": e29["integrity"][
                "historical_replay_matches_all_retained_fields"
            ]
            and float(e29["historical_replay"]["rho_fidelity_vs_rewritability"])
            > 0,
            "registered_negative_tradeoff_passed": e29["registered_test"]["passes"],
            "single_latent_competence_axis_identified": False,
            "graft_compromise_measured": False,
            "graft_compromise_main_resolution_supported": False,
            "graft_result_free_of_position_share_threshold_confounding": False,
            "real_organism_regeneration_reprogrammability_covariance_tested": False,
            "manuscript_v2_3_contains_morpho_gps_or_collective_decision": (
                "morpho_gps" in manuscript_text
                or "collective_decision" in manuscript_text
            ),
        },
        "first_pass_verdict": "MIXED",
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, sorted(tracker.paths)
