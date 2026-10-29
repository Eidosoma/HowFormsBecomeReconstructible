"""Outcome-known retained-artifact and design audit for L07."""

from __future__ import annotations

import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest
from .learning_math import (
    aggregate_speedup,
    detector_opportunities,
    paired_condition,
    safe_ratio,
    training_gate_projection,
    validate_training_entries,
)
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E33_tissue_training": "0cfea626fc339556054e94708b9d1701b29bd2ae0b77f6237e18317318aac577",
    "E38_james_test": "73cc6c7ad0efe66d519b30278138367eb035516b6cdb6743568e62cd28dd0fe4",
    "E42_james_test_2": "95f2f959571d81d7fb9e4732c0e27007f853bc97b9a477b8e93620a0c4fca57d",
    "E46_james_test_3": "23793e8eeffc223a5ae82725a4e596028a47fa688b9354091376cd3975f4bfda",
    "E47_sealed_battery_3": "8a27efba409f1b8e3ca131112a5f3c1535983d33b78da86e99662703df6724ed",
    "E50_james_final": "673ad23f3661725b97aebaf33515850811dbc88d70a9c84209d7d118c66b2728",
    "E58_kuramoto_web": "1cfeb2cd9ea503b5306c3359fcafde391f4837545077a9f3afe2916f0fbc6cac",
    "E59_grayscott_web": "15dd2c065af707c4e33e5138028b3f072ebd9d49b4e47407c8bd6a5f88b2e9a3",
}


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def source_config_digests() -> dict[str, str]:
    """Independently transcribed source defaults, exposed for tests."""

    configs: dict[str, dict[str, Any]] = {
        "E33_tissue_training": {
            "mode": "full",
            "n_tissues": 16,
            "futures": 96,
            "horizon": 26,
            "train_generations": (5, 7, 9),
            "sub_sweeps": 1,
            "train_cols": 1,
            "test_base_generation": 11,
            "delays": (0, 3, 6),
            "test_sweeps": 8,
            "trajectory_seed_tag": "train-traj-v1",
        },
        "E38_james_test": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 32,
            "settle_sweeps": 40,
            "horizon_sweeps": 120,
            "tilt_magnitudes": (0.05, 0.15, 0.4),
            "arrival_cos": 0.9,
            "cessation_window": 3,
            "stress_settle_fraction": 0.2,
            "preexposure_sweeps": 40,
            "decoy_eps": 0.02,
            "decoy_horizon": 200,
            "trajectory_seed_tag": "james-traj-v1",
        },
        "E42_james_test_2": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 24,
            "settle_sweeps": 40,
            "zap_sweeps_ladder": (4, 8, 16),
            "zap_value": 1.5,
            "recovery_horizon": 80,
            "arrival_cos": 0.9,
            "cessation_window": 3,
            "replica_streams": 6,
            "mid_fraction": 0.5,
            "pre_gap": 10,
            "decoy_horizon": 80,
            "backtrack_margin": 0.02,
            "trajectory_seed_tag": "james2-traj-v1",
        },
        "E46_james_test_3": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 16,
            "settle_sweeps": 40,
            "zap_sweeps_ladder": (4, 8, 16),
            "recovery_horizon": 100,
            "arrival_cos": 0.9,
            "activity_window": 10,
            "cessation_lock": 5,
            "replica_streams": 5,
            "pre_gap": 10,
            "trap_horizon": 200,
            "trap_wall_width": 2,
            "backtrack_margin": 2.0,
            "trajectory_seed_tag": "james3-traj-v2",
            "motility_seed_tag": "james3-motility-v2",
        },
        "E47_sealed_battery_3": {
            "mode": "full",
            "base_tissue": 300,
            "n_tissues": 8,
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
        "E58_kuramoto_web": {
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
            "trajectory_seed_tag": "kuramoto-traj-v2-freq",
        },
        "E59_grayscott_web": {
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
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def current_e58_source_default_digest() -> str:
    """Digest the current E58 default, which added an explicit mode field."""

    historical = {
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
        "trajectory_seed_tag": "kuramoto-traj-v2-freq",
    }
    return canonical_digest({**historical, "binarization": "freq"})


def _track_package(tracker: InputTracker, root: Path) -> None:
    for relative in ("EXPECTATIONS.md", "pyproject.toml"):
        if (root / relative).is_file():
            tracker.add(root / relative)
    for directory in ("src", "tests"):
        if (root / directory).is_dir():
            for path in sorted((root / directory).rglob("*.py")):
                tracker.add(path)


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
        return close(left, right)
    return left == right


def _field_matches(
    calculated: Mapping[str, Any], reported: Mapping[str, Any]
) -> dict[str, bool]:
    return {
        field: _recursive_close(calculated[field], reported[field])
        for field in reported
        if field in calculated
    }


def _load_e33(
    root: Path, tracker: InputTracker
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    work = root / "results/full/work"
    paths = sorted(work.glob("train_shard_*_of_08.json"))
    if len(paths) != 8:
        raise ValueError(f"expected eight E33 shards, found {len(paths)}")
    shard_ids = []
    payloads = []
    for path in paths:
        match = re.fullmatch(r"train_shard_(\d+)_of_(\d+)\.json", path.name)
        if match is None:
            raise ValueError(f"unexpected E33 shard name: {path.name}")
        shard_ids.append(int(match.group(1)))
        if int(match.group(2)) != 8:
            raise ValueError(f"unexpected E33 shard denominator: {path.name}")
        payloads.append(tracker.json(path))
    if shard_ids != list(range(8)):
        raise ValueError(f"incomplete E33 shard IDs: {shard_ids}")
    digests = {payload["config_digest"] for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"E33 shard digests differ: {sorted(digests)}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    summary = tracker.json(root / "results/full/train_summary.json")
    return entries, summary, {
        "n_shards": len(paths),
        "shard_ids": shard_ids,
        "config_digest": next(iter(digests)),
        "summary_config_digest": summary.get("config_digest"),
        "n_entries": len(entries),
        "n_stored_arm_future_slots": sum(
            len(entry["eligible_mask"]) for entry in entries
        ),
    }


def _line_evidence(path: Path, needle: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = [index for index, line in enumerate(lines, start=1) if needle in line]
    return {
        "path": str(path.resolve()),
        "needle": needle,
        "line_numbers": hits,
        "found": bool(hits),
    }


def _source_design_audit(roots: Mapping[str, Path]) -> dict[str, Any]:
    e33_runner = roots["tissue_training"] / "src/tissue_training/runner.py"
    voltage_engine = roots["voltage_web"] / "src/voltage_web/engine.py"
    e38_pipeline = roots["james_test"] / "src/james_test/pipeline.py"
    e42_pipeline = roots["james_test_2"] / "src/james_test_2/pipeline.py"
    e46_pipeline = roots["james_test_3"] / "src/james_test_3/pipeline.py"
    e47_battery = roots["sealed_battery_3"] / "src/sealed_battery_3/battery.py"
    e50_pipeline = roots["james_final"] / "src/james_final/pipeline.py"
    evidence = {
        "e33_rng_namespace_omits_trained": _line_evidence(
            e33_runner,
            'seed_rng(config.trajectory_seed_tag, index, test_region, delay)',
        ),
        "e33_runs_only_currently_alive_batch": _line_evidence(
            e33_runner, "V[idx], theta, tissue, rng, clamp, sweeps"
        ),
        "base_generation_draws_on_active_subset": _line_evidence(
            voltage_engine, "V[idx] = sheet_step(V[idx], theta, config, rng, clamping)"
        ),
        "base_fission_draws_on_live_batch": _line_evidence(
            e33_runner, "V[live] = fission(V_final[divided], tissue, rng)"
        ),
        "e38_namespace_includes_preexposure": _line_evidence(
            e38_pipeline, 'preexposure or "naive")'
        ),
        "e42_namespace_omits_pre_zap": _line_evidence(
            e42_pipeline,
            "seed_rng(config.trajectory_seed_tag, arm_name, index, zap_sweeps, replica)",
        ),
        "e42_extra_half_horizon_loop": _line_evidence(
            e42_pipeline, "for sweep in range(config.recovery_horizon // 2):"
        ),
        "e42_extra_gap_loop": _line_evidence(
            e42_pipeline, "for _ in range(config.pre_gap):"
        ),
        "e42_target_after_optional_history": _line_evidence(
            e42_pipeline, "setpoint = _census(V)"
        ),
        "e42_naive_arrivals_filtered_separately": _line_evidence(
            e42_pipeline,
            'if r["median_arrival"] and not r["pre_zap"] and r["replica"] == 0]',
        ),
        "e42_preexposed_arrivals_filtered_separately": _line_evidence(
            e42_pipeline,
            'pre_zap=True) if r["median_arrival"]]',
        ),
        "e46_namespace_includes_pre_zap": _line_evidence(
            e46_pipeline,
            "seed_rng(config.trajectory_seed_tag, arm, index, zap_sweeps, replica, pre_zap)",
        ),
        "e46_motility_namespace_includes_pre_zap": _line_evidence(
            e46_pipeline,
            "seed_rng(config.motility_seed_tag, arm, index, zap_sweeps, replica, pre_zap)",
        ),
        "e46_target_after_optional_history": _line_evidence(
            e46_pipeline, "setpoint = _census(V)"
        ),
        "e46_preexposed_arrivals_filtered_separately": _line_evidence(
            e46_pipeline,
            'pre_zap=True) if r["median_arrival"]]',
        ),
        "e47_imports_e33_runner": _line_evidence(
            e47_battery, "from tissue_training.runner import run_arm"
        ),
        "e47_imports_e42_runner": _line_evidence(
            e47_battery, "from james_test_2.pipeline import zap_recovery"
        ),
        "e47_training_gap_only_gate": _line_evidence(
            e47_battery, '"gap": gap, "gate": bool(gap is not None and gap >= 0.02)'
        ),
        "e47_generalization_requires_both_tissue_medians": _line_evidence(
            e47_battery, 'if a["median_arrival"] and b["median_arrival"]:'
        ),
        "e50_namespace_includes_pre_zap": _line_evidence(
            e50_pipeline,
            "replica, pre_zap)",
        ),
    }
    return {
        "line_evidence": evidence,
        "all_needles_found": all(item["found"] for item in evidence.values()),
        "assessments": {
            "E33_draw_exact_pairing": False,
            "E33_reason": (
                "the launch namespace omits trained, but one mutable batch RNG is consumed "
                "on intervention-dependent active and live subsets; clamps need not draw "
                "directly for downstream draw allocation to diverge"
            ),
            "E33_delay_and_region_are_longitudinal": False,
            "E33_delay_region_reason": (
                "test_region and delay are part of the RNG namespace, so those contrasts "
                "are different stochastic cohorts sharing tissue parameters"
            ),
            "E42_test_phase_stream_paired": False,
            "E42_time_aged_sham_present": False,
            "E42_common_fixed_target": False,
            "E42_extra_pretest_sweeps": 50,
            "E42_arrival_denominators_matched": False,
            "E42_arrival_denominator_counts_retained": False,
            "E46_launch_or_test_stream_paired": False,
            "E46_time_aged_sham_present": False,
            "E46_common_fixed_target": False,
            "E46_extra_pretest_sweeps": 60,
            "E46_arrival_denominators_matched": False,
            "E46_arrival_denominator_counts_retained": False,
            "E47_is_independent_implementation": False,
            "E47_reason": "the battery directly imports and invokes E33 and E42 runners",
            "E38_stream_paired_as_claimed": False,
            "preexposure_uses_novel_insult_class": False,
            "preexposure_novelty_reason": "anterior and posterior use the same clamp/zap class at different sites",
            "bulk_trace_carrier_measured_or_ablated": False,
            "cognition_operationalized": False,
        },
    }


def _appearance_registry(
    training: Mapping[str, Any],
    e42: Mapping[str, Any],
    e46: Mapping[str, Any],
    sealed_training: Mapping[str, Any],
    sealed_generalization: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [
        {
            "appearance": 1,
            "experiment": "E33",
            "contrast": "same-site delay 0",
            "effect": training["conditions"]["same_delay_0"]["source_equal_tissue"]["effect"],
            "registered_status": "FAILED compound sensitisation gate",
            "data_group": "E33",
            "protocol_template": "rewrite conversion after three one-column clamps",
            "endpoint_family": "rewrite conversion",
            "base_substrate_family": "conserved voltage sheet",
        },
        {
            "appearance": 2,
            "experiment": "E33",
            "contrast": "other-site delay 0",
            "effect": training["conditions"]["other_delay_0"]["source_equal_tissue"]["effect"],
            "registered_status": "contributed to REVERSED site-specificity gate",
            "data_group": "E33",
            "protocol_template": "rewrite conversion after three one-column clamps",
            "endpoint_family": "rewrite conversion",
            "base_substrate_family": "conserved voltage sheet",
        },
        {
            "appearance": 3,
            "experiment": "E33",
            "contrast": "same-site delay 3",
            "effect": training["conditions"]["same_delay_3"]["source_equal_tissue"]["effect"],
            "registered_status": "contributed to FAILED monotonic-decay gate",
            "data_group": "E33",
            "protocol_template": "rewrite conversion after three one-column clamps",
            "endpoint_family": "rewrite conversion",
            "base_substrate_family": "conserved voltage sheet",
        },
        {
            "appearance": 4,
            "experiment": "E42",
            "contrast": "anterior pre-zap / posterior test-zap arrival",
            "effect": e42["recalculated"]["relative_time_reduction"],
            "registered_status": "FULFILLED aggregate gate",
            "data_group": "E42",
            "protocol_template": "pre-zap recovery then test-zap recovery",
            "endpoint_family": "median recovery arrival",
            "base_substrate_family": "conserved voltage sheet",
        },
        {
            "appearance": 5,
            "experiment": "E47 training seal",
            "contrast": "fresh-index delay-0 training gap",
            "effect": sealed_training["recalculated_gap"],
            "registered_status": "FULFILLED weakened absolute-gap gate; original E33 ratio fails",
            "data_group": "E47",
            "protocol_template": "rewrite conversion after three one-column clamps",
            "endpoint_family": "rewrite conversion",
            "base_substrate_family": "conserved voltage sheet",
        },
        {
            "appearance": 6,
            "experiment": "E47 generalisation seal",
            "contrast": "fresh-index E42 median-arrival speedup",
            "effect": sealed_generalization["recalculated"]["relative_time_reduction"],
            "registered_status": "FULFILLED sealed aggregate gate",
            "data_group": "E47",
            "protocol_template": "pre-zap recovery then test-zap recovery",
            "endpoint_family": "median recovery arrival",
            "base_substrate_family": "conserved voltage sheet",
        },
        {
            "appearance": 7,
            "experiment": "E46",
            "contrast": "motile anterior pre-zap / posterior test-zap arrival",
            "effect": e46["recalculated"]["relative_time_reduction"],
            "registered_status": "FULFILLED aggregate gate",
            "data_group": "E46",
            "protocol_template": "motile pre-zap recovery then test-zap recovery",
            "endpoint_family": "median recovery arrival",
            "base_substrate_family": "conserved voltage sheet",
        },
    ]
    return {
        "status": "charitable reconstruction; source never provides a seven-row ledger",
        "ordering_basis": "E46 is explicitly called the seventh appearance in the discovery log",
        "rows": rows,
        "counts": {
            "n_narrative_rows": len(rows),
            "n_distinct_experiment_numbers": len({row["data_group"] for row in rows}),
            "n_protocol_templates": len({row["protocol_template"] for row in rows}),
            "n_endpoint_families": len({row["endpoint_family"] for row in rows}),
            "n_base_substrate_families": len({row["base_substrate_family"] for row in rows}),
            "n_rows_from_E33_single_dataset": sum(row["data_group"] == "E33" for row in rows),
            "n_E47_direct_code_reruns": 2,
            "n_rows_with_fulfilled_prospective_or_sealed_gate": 4,
            "n_rows_derived_from_failed_or_reversed_E33_gates": 3,
        },
        "unlisted_positive_E33_delay_6": {
            "effect": training["conditions"]["same_delay_6"]["source_equal_tissue"]["effect"],
            "would_change_count_if_any_positive_point_estimate_counted": True,
        },
        "seven_independent_appearances": False,
    }


def run_l7_retained_audit(plastic_root: Path) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    ideas = plastic_root / IDEAS_RELATIVE
    roots = {
        name: _experiment_root(plastic_root, name)
        for name in (
            "tissue_training",
            "james_test",
            "james_test_2",
            "james_test_3",
            "james_final",
            "sealed_battery_3",
            "kuramoto_web",
            "grayscott_web",
            "voltage_web",
        )
    }
    for root in roots.values():
        _track_package(tracker, root)
    for name in (
        "LAWS.md",
        "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        "WAVE7_PROPHECIES.md",
        "WAVE8_PROPHECIES.md",
        "WAVE9_PROPHECIES.md",
        "WAVE10_PROPHECIES.md",
        "WAVE11_PROPHECIES.md",
        "WAVE13_PROPHECIES.md",
    ):
        tracker.add(ideas / name)
    tracker.add(plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md")

    digests = source_config_digests()
    config_digest_checks = {
        name: {
            "calculated": digests[name],
            "expected": EXPECTED_CONFIG_DIGESTS[name],
            "matches": digests[name] == EXPECTED_CONFIG_DIGESTS[name],
        }
        for name in EXPECTED_CONFIG_DIGESTS
    }
    config_digest_checks["E58_kuramoto_web"].update(
        {
            "calculated_represents": "retained historical default before explicit binarization field was added",
            "current_source_default": current_e58_source_default_digest(),
            "current_source_default_matches_retained": (
                current_e58_source_default_digest()
                == EXPECTED_CONFIG_DIGESTS["E58_kuramoto_web"]
            ),
            "provenance_note": (
                "the retained screen digest matches the otherwise-identical historical "
                "configuration without the current explicit binarization='freq' field"
            ),
        }
    )
    if not all(check["matches"] for check in config_digest_checks.values()):
        raise ValueError(f"source config transcription mismatch: {config_digest_checks}")

    entries, e33_summary, e33_integrity = _load_e33(
        roots["tissue_training"], tracker
    )
    entry_validation = validate_training_entries(entries)
    if not entry_validation["passes"]:
        raise ValueError(f"E33 entry validation failed: {entry_validation}")
    if e33_integrity["config_digest"] != EXPECTED_CONFIG_DIGESTS["E33_tissue_training"]:
        raise ValueError("E33 shard config digest mismatch")
    if e33_summary.get("config_digest") != e33_integrity["config_digest"]:
        raise ValueError("E33 summary/shard config digest mismatch")

    rng = np.random.default_rng(2026090207)
    condition_order = (
        ("same_delay_0", "same", 0),
        ("same_delay_3", "same", 3),
        ("same_delay_6", "same", 6),
        ("other_delay_0", "other", 0),
    )
    conditions = {
        name: paired_condition(
            entries,
            region=region,
            delay=delay,
            rng=rng,
            bootstrap_draws=4096,
        )
        for name, region, delay in condition_order
    }
    projection = training_gate_projection(conditions)
    e33_matches = _field_matches(projection, e33_summary["gates"])
    horizons = {
        f"delay_{delay}": detector_opportunities(
            horizon=26, run_length=8, test_generation=11 + delay
        )
        for delay in (0, 3, 6)
    }
    pretest_horizons = {
        f"delay_{delay}": detector_opportunities(
            horizon=11 + delay, run_length=8, test_generation=5
        )
        for delay in (0, 3, 6)
    }
    e33 = {
        "integrity": e33_integrity,
        "entry_validation": entry_validation,
        "diagnostic_rng_seed": 2026090207,
        "bootstrap_condition_order": [name for name, _region, _delay in condition_order],
        "conditions": conditions,
        "gate_projection": projection,
        "reported_gates": e33_summary["gates"],
        "reported_field_matches": e33_matches,
        "all_reported_fields_match": (
            set(e33_matches) == set(e33_summary["gates"])
            and all(e33_matches.values())
        ),
        "detector_opportunities": horizons,
        "pretest_exclusion_detector_opportunities": pretest_horizons,
        "equal_followup_across_delays": False,
        "raw_dev_calibration_artifact_retained": False,
        "raw_dev_calibration_note": (
            "the 1.3% one-column/one-sweep calibration is stated in prose, but the "
            "package retains no calibration rows, script output, or result manifest"
        ),
        "estimand": (
            "equal-tissue test-conversion contrast among future slots eligible under "
            "both simulated histories; earlier training-associated rewrites are excluded"
        ),
    }

    def load_summary(package: str, relative: str) -> dict[str, Any]:
        return tracker.json(roots[package] / relative)

    e38_summary = load_summary("james_test", "results/full/james_summary.json")
    e42_summary = load_summary("james_test_2", "results/full/james2_summary.json")
    e46_summary = load_summary("james_test_3", "results/full/james3_summary.json")
    e46_round1 = load_summary(
        "james_test_3", "results/full/james3_round1_magnitudeE.json"
    )
    e50_summary = load_summary("james_final", "results/full/jamesfinal_summary.json")
    sealed_training_source = load_summary(
        "sealed_battery_3", "results/full/component_training.json"
    )
    sealed_generalization_source = load_summary(
        "sealed_battery_3", "results/full/component_generalization.json"
    )
    sealed_verdict = load_summary(
        "sealed_battery_3", "results/full/battery_verdict.json"
    )
    kuramoto_screen = load_summary("kuramoto_web", "results/full/screen_summary.json")
    kuramoto_battery = load_summary("kuramoto_web", "results/full/battery_summary.json")
    grayscott_screen = load_summary("grayscott_web", "results/full/screen_summary.json")
    grayscott_battery = load_summary("grayscott_web", "results/full/battery_summary.json")

    for name, summary in (
        ("E38_james_test", e38_summary),
        ("E42_james_test_2", e42_summary),
        ("E46_james_test_3", e46_summary),
        ("E50_james_final", e50_summary),
        ("E47_sealed_battery_3", sealed_training_source),
        ("E47_sealed_battery_3", sealed_generalization_source),
        ("E47_sealed_battery_3", sealed_verdict),
        ("E58_kuramoto_web", kuramoto_screen),
        ("E58_kuramoto_web", kuramoto_battery),
        ("E59_grayscott_web", grayscott_screen),
        ("E59_grayscott_web", grayscott_battery),
    ):
        if summary.get("config_digest") != EXPECTED_CONFIG_DIGESTS[name]:
            raise ValueError(f"retained config mismatch for {name}")

    e38_recalculated = aggregate_speedup(
        e38_summary["gates"]["naive_arrival"],
        e38_summary["gates"]["preexposed_arrival"],
        relative_bar=0.8,
    )
    e42_recalculated = aggregate_speedup(
        e42_summary["gates"]["naive_arrival"],
        e42_summary["gates"]["preexposed_arrival"],
        relative_bar=0.8,
    )
    e46_recalculated = aggregate_speedup(
        e46_summary["gates"]["naive_arrival"],
        e46_summary["gates"]["preexposed_arrival"],
        relative_bar=0.8,
    )
    e50_recalculated = aggregate_speedup(
        e50_summary["gates"]["naive_arrival"],
        e50_summary["gates"]["preexposed_arrival"],
        relative_bar=0.8,
    )
    sealed_training = {
        "reported": sealed_training_source,
        "recalculated_gap": (
            float(sealed_training_source["trained"])
            - float(sealed_training_source["naive"])
        ),
        "recalculated_ratio": safe_ratio(
            sealed_training_source["trained"], sealed_training_source["naive"]
        ),
    }
    sealed_training["sealed_gap_gate"] = bool(
        sealed_training["recalculated_gap"] >= 0.02
    )
    sealed_training["original_E33_compound_gate"] = bool(
        sealed_training["recalculated_gap"] >= 0.02
        and float(sealed_training_source["trained"])
        >= 1.5 * max(float(sealed_training_source["naive"]), 1e-9)
    )
    sealed_training["reported_matches"] = {
        "gap": close(sealed_training["recalculated_gap"], sealed_training_source["gap"]),
        "gate": sealed_training["sealed_gap_gate"] is sealed_training_source["gate"],
    }
    sealed_generalization_recalculated = aggregate_speedup(
        sealed_generalization_source["naive"],
        sealed_generalization_source["pre"],
        relative_bar=1 / 1.5,
    )
    sealed_generalization = {
        "reported": sealed_generalization_source,
        "recalculated": sealed_generalization_recalculated,
        "reported_matches": {
            "speedup": close(
                sealed_generalization_recalculated["speedup"],
                sealed_generalization_source["speedup"],
            ),
            "gate": (
                sealed_generalization_recalculated["gate"]
                is sealed_generalization_source["gate"]
            ),
        },
    }

    generalization = {
        "E38": {
            "reported": e38_summary["gates"],
            "recalculated": e38_recalculated,
            "reported_gate_matches": (
                e38_recalculated["gate"]
                is e38_summary["gates"]["gate_p38_3_generalization"]
            ),
            "lower_level_rows_retained": False,
            "source_verdict": "FAILED (void)",
        },
        "E42": {
            "reported": e42_summary["gates"],
            "recalculated": e42_recalculated,
            "reported_gate_matches": (
                e42_recalculated["gate"]
                is e42_summary["gates"]["gate_p42_3_generalization"]
            ),
            "lower_level_rows_retained": False,
        },
        "E46": {
            "reported": e46_summary["gates"],
            "recalculated": e46_recalculated,
            "reported_gate_matches": (
                e46_recalculated["gate"]
                is e46_summary["gates"]["gate_p46_3_generalization"]
            ),
            "round1_aggregate": e46_round1,
            "lower_level_rows_retained": False,
        },
        "E47_training": sealed_training,
        "E47_generalization": sealed_generalization,
        "E50": {
            "reported": e50_summary["gates"],
            "recalculated": e50_recalculated,
            "reported_gate_matches": (
                e50_recalculated["gate"]
                is e50_summary["gates"]["gate_p50_3_generalization"]
            ),
            "lower_level_rows_retained": False,
            "source_verdict": "FAILED (void)",
        },
    }
    appearances = _appearance_registry(
        e33,
        generalization["E42"],
        generalization["E46"],
        sealed_training,
        sealed_generalization,
    )
    adverse_attempts = [
        {
            "experiment": "E38",
            "test": "horizontal pre-exposure -> vertical tilt",
            "outcome": "naive 1, pre-exposed 1; gate false",
            "classification": "FAILED/void",
            "effect_absence_established": False,
        },
        {
            "experiment": "E50",
            "test": "explicit eighth generalisation appearance",
            "outcome": "naive arrival undefined, pre-exposed 17",
            "classification": "FAILED/void",
            "effect_absence_established": False,
        },
        {
            "experiment": "E58 Kuramoto",
            "test": "preregistered eighth training appearance",
            "outcome": "no operating point; battery uninstrumented",
            "classification": "VOID",
            "effect_absence_established": False,
        },
        {
            "experiment": "E59 Gray-Scott",
            "test": "preregistered ninth training appearance",
            "outcome": "no operating point; battery uninstrumented",
            "classification": "VOID",
            "effect_absence_established": False,
        },
    ]
    portability = {
        "E58": {
            "screen_chosen": kuramoto_screen["chosen"],
            "battery_uninstrumented": kuramoto_battery.get("uninstrumented"),
        },
        "E59": {
            "screen_chosen": grayscott_screen["chosen"],
            "battery_uninstrumented": grayscott_battery.get("uninstrumented"),
        },
        "resolved_cross_substrate_training_tests": 0,
        "portable_effect_established": False,
    }
    source_design = _source_design_audit(roots)
    if not source_design["all_needles_found"]:
        raise ValueError("one or more static source checks no longer match")

    clause_adjudication = [
        {
            "claim": "Subthreshold experience changes later response probability in E33",
            "verdict": "MIXED",
            "basis": (
                "the retained common-eligible delay-0 contrast is positive and exactly "
                "reconstructs, but the compound registered gate failed, draw-exact pairing "
                "is not guaranteed, and raw subthreshold calibration is absent"
            ),
        },
        {
            "claim": "The trace is global, peaks at three generations, and dies on a six-cycle identity clock",
            "verdict": "NOT_CONFIRMED",
            "basis": (
                "far-site response does not localise a carrier, only three cohort points "
                "were tested, and detector opportunities shrink from 7 to 4 to 1"
            ),
        },
        {
            "claim": "Prior insults speed recovery from novel ones in E42/E46/E47",
            "verdict": "MIXED",
            "basis": (
                "reported aggregate medians and gates recalculate, but arms differ in age, "
                "test RNG and/or target and retain no lower-level rows"
            ),
        },
        {
            "claim": "The effect appears in every substrate family/protocol as seven independent appearances",
            "verdict": "NOT_CONFIRMED",
            "basis": (
                "seven is a post-hoc condition/rerun tally from four experiment numbers and "
                "one base substrate family; E38 failed/void and E50/E58/E59 were void"
            ),
        },
        {
            "claim": "These outcomes establish learning, memory, and cognition",
            "verdict": "NOT_CONFIRMED",
            "basis": (
                "the designs do not separate history dependence from residual state, age, "
                "target drift, selection, or stochastic mismatch, and cognition has no test"
            ),
        },
        {
            "claim": "Bioelectric sensitisation should be global, delayed-peaking, and decaying",
            "verdict": "NOT_TESTED",
            "basis": "all evidence is in silico and manuscript v2.3 supplies no such bench result",
        },
    ]
    audit = {
        "schema_version": 1,
        "law": "L07",
        "audit_type": "outcome-known retained-data and source-design audit",
        "scientific_futures_generated": 0,
        "historical_futures_replayed": 0,
        "workers": 1,
        "config_digest_checks": config_digest_checks,
        "E33_training": e33,
        "generalization_and_seals": generalization,
        "source_design_audit": source_design,
        "appearance_registry": appearances,
        "adverse_and_void_attempts": adverse_attempts,
        "portability": portability,
        "evidence_retention": {
            "E33": "128 raw arm records with 96-slot eligible/converted masks",
            "E38": "aggregate summary only",
            "E42": "aggregate summary only",
            "E46": "round-1 and round-2 aggregates only",
            "E47": "component aggregates only",
            "E50": "aggregate summary only",
            "E58_E59": "screen rows retained; training batteries never ran because chosen operating point was null",
        },
        "clause_adjudication": clause_adjudication,
        "overall_verdict": "MIXED",
        "replacement_wording": (
            "In one conserved-voltage-sheet model, E33's retained masks show a positive "
            "delay-0 history-dependent rewrite contrast among common-eligible trajectories, "
            "although its registered compound sensitisation gate failed. E42, E46, and two "
            "direct E47 reruns retain aggregate pre-exposure associations, but their unmatched "
            "age, target, and stochastic histories do not isolate learning. The claimed seven "
            "appearances are seven selected contrasts/reruns from one base substrate family, "
            "not seven independent confirmations. Incubation, trace mortality, cognition, "
            "cross-substrate universality, and the biological prediction remain unconfirmed."
        ),
    }
    return audit, sorted(tracker.paths)


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf"
        return f"{value:.{digits}f}"
    return str(value)


def markdown_report(audit: Mapping[str, Any]) -> str:
    e33 = audit["E33_training"]
    lines = [
        "# L07 retained learning/history-dependence audit",
        "",
        f"**Overall verdict: {audit['overall_verdict']}**",
        "",
        "This is an outcome-known retained-data and code-design audit. It generated and replayed zero simulator futures.",
        "",
        "## E33 reconstruction",
        "",
        "| Condition | Trained | Naive | Effect | Ratio | Common n | Tissue directions +/0/- | 95% tissue bootstrap | Sign-flip p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("same_delay_0", "same_delay_3", "same_delay_6", "other_delay_0"):
        row = e33["conditions"][name]
        source = row["source_equal_tissue"]
        tissue = row["tissue_effect_summary"]
        interval = tissue["bootstrap_95_percentile_interval"]
        lines.append(
            "| "
            + " | ".join(
                (
                    name,
                    _fmt(source["trained_rate"]),
                    _fmt(source["naive_rate"]),
                    _fmt(source["effect"]),
                    _fmt(source["ratio"]),
                    str(row["common_eligible_total"]),
                    f"{tissue['positive']}/{tissue['zero']}/{tissue['negative']}",
                    f"[{_fmt(interval[0])}, {_fmt(interval[1])}]",
                    _fmt(tissue["exact_sign_flip"]["two_sided_p"]),
                )
            )
            + " |"
        )
    projection = e33["gate_projection"]
    lines += [
        "",
        f"All retained source fields reproduce: **{e33['all_reported_fields_match']}**.",
        "",
        "- Original sensitisation gate: " + _fmt(projection["gate_sensitization"]),
        "- Site-specificity gate: " + _fmt(projection["gate_site_specificity"]),
        "- Monotonic-decay gate: " + _fmt(projection["gate_decay"]),
        "- Delay-0 ratio: " + _fmt(projection["training_ratio"]),
        "",
        "The fixed horizon admits 7, 4, and 1 possible eight-generation rewrite-run starts after delay-0, delay-3, and delay-6 tests. Conversely, the pre-test exclusion detector has 0, 1, and 4 possible starts. Both the outcome opportunity and selected population therefore change with delay.",
        "",
        "## Prior-insult aggregates",
        "",
        "| Experiment | Naive arrival | Pre-exposed arrival | Speedup | Relative reduction | Source gate | Raw rows retained |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("E38", "E42", "E46", "E50"):
        row = audit["generalization_and_seals"][name]
        calc = row["recalculated"]
        lines.append(
            f"| {name} | {_fmt(calc['naive_median_arrival'])} | "
            f"{_fmt(calc['preexposed_median_arrival'])} | {_fmt(calc['speedup'])} | "
            f"{_fmt(calc['relative_time_reduction'])} | {_fmt(calc['gate'])} | "
            f"{_fmt(row['lower_level_rows_retained'])} |"
        )
    seal_t = audit["generalization_and_seals"]["E47_training"]
    seal_g = audit["generalization_and_seals"]["E47_generalization"]
    lines += [
        "",
        f"E47 training reproduces gap `{_fmt(seal_t['recalculated_gap'])}` and ratio `{_fmt(seal_t['recalculated_ratio'])}`. Its weakened gap-only gate passes; E33's original compound gate does **not**.",
        f"E47 generalisation reproduces speedup `{_fmt(seal_g['recalculated']['speedup'])}`.",
        "",
        "E42 adds 50 stochastic sweeps before the pre-exposed test arm; E46 adds 60. Both define each arm's target after that optional history, neither has a time-aged sham, and E46 uses different voltage and motility namespaces from launch. Both source summaries also filter successful-arrival medians separately without retaining the arm denominators. Their aggregate differences are not controlled causal learning effects.",
        "",
        "## Seven-appearance audit",
        "",
        "| # | Source | Selected contrast | Registered status |",
        "|---:|---|---|---|",
    ]
    for row in audit["appearance_registry"]["rows"]:
        lines.append(
            f"| {row['appearance']} | {row['experiment']} | {row['contrast']} | {row['registered_status']} |"
        )
    counts = audit["appearance_registry"]["counts"]
    lines += [
        "",
        f"The charitable tally has seven rows but only {counts['n_distinct_experiment_numbers']} experiment groups, {counts['n_protocol_templates']} protocol templates, {counts['n_endpoint_families']} endpoint families, and {counts['n_base_substrate_families']} base substrate family. Three rows come from E33's one dataset; two are direct E47 code reruns.",
        "",
        "Adverse denominator: E38 failed/was void; E50's explicitly named eighth appearance was void; Kuramoto and Gray-Scott training were void because their screens chose no operating point. Void is not evidence of no effect, but it is not an appearance and contradicts the literal `every protocol tried` wording.",
        "",
        "## Clause verdicts",
        "",
        "| Claim | Verdict | Basis |",
        "|---|---|---|",
    ]
    for row in audit["clause_adjudication"]:
        lines.append(f"| {row['claim']} | **{row['verdict']}** | {row['basis']} |")
    lines += [
        "",
        "## Replacement wording",
        "",
        "> " + audit["replacement_wording"],
        "",
    ]
    return "\n".join(lines)
