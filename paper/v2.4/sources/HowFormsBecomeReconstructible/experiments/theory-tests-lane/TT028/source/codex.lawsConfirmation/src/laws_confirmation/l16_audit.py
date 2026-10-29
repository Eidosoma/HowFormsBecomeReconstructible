"""Outcome-known retained audit for L16's landlord/tenant role split."""

from __future__ import annotations

from collections import Counter
import csv
import io
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E51_two_headed_final": "8dd8669dab6c560337fd1a09bbdd4257011fadd8a62bc0d0392fe23c53753da6",
    "E52_origin_of_development": "764afdc72db6f897b1a6d0556b6499ca719099d29d42f5d797dcf10466955610",
    "E53_hidden_genome": "46a00eebd4ed079dbd5aa3ee15df5bd4c94ac535cbde4d1c3b9c87ea173f4ebc",
    "E54_repertoire": "a53c62d5e27dabead75c6659189d3e38a60db08d31773f1b6e162bf670646920",
    "E56_scaffold": "fe2a28f7c0dae8e904d3e05f0b799a1ad4c96b7a7accff5c8d8af7534487a22b",
    "E57_assimilation": "a1aeadeb82501d395b22596dd6ea543f6c17564ea16963c17fe2255af30f40c2",
    "E66_writable_landlord": "9def6662a2533a853811cbbcac8f0a069e35f6d1f9ef57da2f04ff193d63d982",
}

TRACKED_PACKAGES = (
    "blueprint_web",
    "two_headed_final",
    "origin_of_development",
    "hidden_genome",
    "repertoire",
    "scaffold",
    "assimilation",
    "writable_landlord",
    "voltage_web",
    "setpoint_rewrite",
    "ladder_web",
    "contract_bridge",
)

E52_REGIMES = ("anatomy", "plasticity", "both", "drift")
E53_R_ARMS = ("R_on", "R_off")
E53_CONTEXT_ARMS = ("intact", "reset", "transplant")
E53_THETA_ARMS = ("intact", "scrambled", "zeroed")
E54_CLASSES = ("in_repertoire", "translated", "surrogate", "cross_tissue")
E54_DOSES = (8, 50, 200, 500)
E56_ANNEAL_SWEEPS = (250, 500, 1000, 2000)
E56_KNIFE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
E57_REGIMES = ("static", "switching_k2", "switching_k4", "drift")


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
    entries = [entry for payload in payloads for entry in payload["entries"]]
    return entries, {
        "n_shards": len(paths),
        "shard_ids_inferred_from_filenames": list(range(expected_shards)),
        "shard_ids_stored_in_payloads": False,
        "config_digest": next(iter(digests)),
        "n_entries": len(entries),
    }


def _bootstrap_mean_interval(
    values: Sequence[float], *, seed: int, draws: int = 4096
) -> list[float]:
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("cannot bootstrap an empty contrast")
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(data), size=(draws, len(data)))
    return [float(x) for x in np.quantile(data[picks].mean(axis=1), (0.025, 0.975))]


def _directions(values: Sequence[float], *, tolerance: float = 1e-12) -> dict[str, int]:
    return {
        "positive": sum(float(value) > tolerance for value in values),
        "tied": sum(abs(float(value)) <= tolerance for value in values),
        "negative": sum(float(value) < -tolerance for value in values),
    }


def _contrast(values: Sequence[float], *, seed: int, unit: str = "tissue") -> dict[str, Any]:
    data = [float(value) for value in values]
    return {
        f"n_{unit}s": len(data),
        "mean_difference": float(np.mean(data)),
        f"paired_{unit}_bootstrap_95": _bootstrap_mean_interval(data, seed=seed),
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


def source_config_digests() -> dict[str, str]:
    """Independently transcribed current defaults for E51--E57 and E66."""

    configs: dict[str, dict[str, Any]] = {
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
        "E52_origin_of_development": {
            "mode": "full",
            "population": 16,
            "generations": 30,
            "n_repeats": 8,
            "tournament": 3,
            "mutation_sigma": 0.3,
            "rho_range": (0.0005, 0.2),
            "cm_range": (0.05, 1.6),
            "init_rho": (0.002, 0.05),
            "init_cm": (0.1, 0.8),
            "body_sweeps": 30,
            "eval_sweeps": 40,
            "band_cm": (0.1, 0.3),
            "trajectory_seed_tag": "origin-traj-v1",
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
        "E56_scaffold": {
            "mode": "full",
            "n_tissues": 2,
            "futures": 6,
            "pattern_domains": 4,
            "scaffold_era": 1000,
            "retention_horizon": 2500,
            "retention_stride": 50,
            "amp_threshold": 0.2,
            "calibration_settle": 300,
            "calibration_bar": 0.9,
            "zap_at": 1000,
            "zap_sweeps": 8,
            "zap_recover": 300,
            "knife_horizon": 1000,
            "trajectory_seed_tag": "scaffold-v1",
        },
        "E57_assimilation": {
            "mode": "full",
            "population": 10,
            "generations": 16,
            "n_repeats": 6,
            "futures": 2,
            "tournament": 3,
            "rho_init": (0.002, 0.05),
            "rho_range": (0.002, 0.05),
            "cm_init": (0.1, 0.8),
            "cm_range": (0.05, 1.6),
            "mutation_sigma": 0.3,
            "theta_mutation": 0.05,
            "theta_norm": 0.3,
            "eval_settle": 100,
            "eval_instruct": 200,
            "eval_free": 200,
            "eval_regrow": 250,
            "eval_cycles": 2,
            "imprint_hold": 1.2,
            "amp_threshold": 0.2,
            "n_targets": 3,
            "target_settle": 400,
            "assay_evals": 2,
            "consensus_launches": 4,
            "readopt_horizon": 1000,
            "transport_shift": 8,
            "transport_recover": 300,
            "trajectory_seed_tag": "assimilation-v1",
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


def audit_e48(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/calibration_square.json")
    expectations = _read(tracker, root / "EXPECTATIONS.md")
    result_files = sorted(
        path for path in (root / "results/full").rglob("*") if path.is_file()
    )
    return {
        "retained_config_digest": summary["config_digest"],
        "retained_files": [str(path.relative_to(root)) for path in result_files],
        "reported_regrowth_live": 0.711,
        "reported_regrowth_ablated": 0.543,
        "reported_difference_from_rounded_values": 0.711 - 0.543,
        "reported_values_present_in_expectations": (
            "0.711 vs 0.543" in expectations
        ),
        "reported_values_machine_readable_in_retained_result": False,
        "repair_lower_level_rows_retained": False,
        "evidence_level_for_repair_values": "E1/E2-current-test",
        "not_the_source_of_E53_exact_0_171875": True,
    }


def audit_e51(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="worm_shard", expected_shards=4
    )
    summary = tracker.json(root / "results/full/worm_summary.json")
    source = _read(tracker, root / "src/two_headed_final/pipeline.py")
    keys = [
        (str(row["setpoint"]), int(row["tissue"]), bool(row["lesioned_arm"]))
        for row in entries
    ]
    expected = {
        *(("wild", tissue, False) for tissue in range(10)),
        *(("two_headed", tissue, False) for tissue in range(10)),
        *(("two_headed", tissue, True) for tissue in range(10)),
    }
    integrity.update(
        {
            "expected_entries": 30,
            "unique_jobs": len(set(keys)),
            "complete_expected_jobs": set(keys) == expected,
            "no_duplicate_jobs": len(keys) == len(set(keys)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def stat(setpoint: str, lesioned: bool, field: str) -> float | None:
        rows = [
            row
            for row in entries
            if row["setpoint"] == setpoint
            and bool(row["lesioned_arm"]) == lesioned
        ]
        return float(np.mean([row[field] for row in rows])) if rows else None

    calculated: dict[str, Any] = {
        metric: {
            "wild": stat("wild", False, metric),
            "two_headed": stat("two_headed", False, metric),
            "two_headed_lesioned": stat("two_headed", True, metric),
        }
        for metric in ("inheritance", "regeneration", "quarter_wholeness")
    }
    inheritance = calculated["inheritance"]
    regeneration = calculated["regeneration"]
    quarter = calculated["quarter_wholeness"]
    calculated.update(
        {
            "gate_p51_1_inheritance": bool(
                inheritance["wild"] >= 0.75
                and inheritance["two_headed"] >= 0.75
            ),
            "gate_p51_2_regeneration": bool(
                regeneration["wild"] >= 0.85
                and regeneration["two_headed"] >= 0.85
            ),
            "gate_p51_3_quarter_wholeness": bool(
                quarter["two_headed"] >= 0.75
            ),
            "gate_p51_4_knife": bool(
                inheritance["two_headed"]
                >= inheritance["two_headed_lesioned"] + 0.1
            ),
        }
    )
    indexed = {
        (str(row["setpoint"]), int(row["tissue"]), bool(row["lesioned_arm"])): row
        for row in entries
    }
    tissue_rows: list[dict[str, Any]] = []
    for tissue in range(10):
        wild = indexed[("wild", tissue, False)]
        live = indexed[("two_headed", tissue, False)]
        lesion = indexed[("two_headed", tissue, True)]
        tissue_rows.append(
            {
                "tissue": tissue,
                "wild_regeneration": float(wild["regeneration"]),
                "two_headed_regeneration": float(live["regeneration"]),
                "two_headed_cm_zero_regeneration": float(lesion["regeneration"]),
                "live_minus_cm_zero_regeneration": float(
                    live["regeneration"] - lesion["regeneration"]
                ),
                "two_headed_inheritance": float(live["inheritance"]),
                "two_headed_cm_zero_inheritance": float(lesion["inheritance"]),
            }
        )

    round1_entries, round1_integrity = _load_shards(
        root, tracker, prefix="round1_worm_shard", expected_shards=4
    )
    round1_summary = tracker.json(
        root / "results/full/worm_round1_launchmetric.json"
    )
    round1_integrity.update(
        {
            "n_entries": len(round1_entries),
            "summary_digest_matches_shards": (
                round1_summary["config_digest"] == round1_integrity["config_digest"]
            ),
        }
    )
    diffs = [row["live_minus_cm_zero_regeneration"] for row in tissue_rows]
    return {
        "integrity": integrity,
        "retained_config_digest": summary["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, summary["gates"]
        ),
        "regeneration_feedback_contrast": {
            "mean_difference": float(np.mean(diffs)),
            "directions": _directions(diffs),
            "tissue_differences": diffs,
            "arm_label_in_rng_namespace": (
                '"lesion" if c_m == 0.0 else "live"' in source
            ),
            "stream_paired": False,
        },
        "metric_contract": {
            "horizon_sweeps": 100,
            "region": "regrown quarter only",
            "metric": "positional sign agreement",
            "amplitude_threshold": None,
            "target": "pre-lesion V sign pattern after eight cut/regrow cycles",
        },
        "round1_archive": {
            "integrity": round1_integrity,
            "summary_digest": round1_summary["config_digest"],
            "mixed_into_final_estimate": False,
        },
    }, tissue_rows


def audit_e52(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="origin_shard", expected_shards=8
    )
    summary = tracker.json(root / "results/full/origin_summary.json")
    keys = [(str(row["regime"]), int(row["repeat"])) for row in entries]
    expected = {
        (regime, repeat)
        for regime in E52_REGIMES
        for repeat in range(8)
    }
    integrity.update(
        {
            "expected_entries": 32,
            "unique_jobs": len(set(keys)),
            "complete_expected_jobs": set(keys) == expected,
            "no_duplicate_jobs": len(keys) == len(set(keys)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def regime_rows(regime: str) -> list[dict[str, Any]]:
        return [row for row in entries if row["regime"] == regime]

    def med(regime: str, field: str) -> float:
        return float(np.median([row[field] for row in regime_rows(regime)]))

    lo, hi = 0.1, 0.3
    both_in_band = float(
        np.mean([lo <= row["median_cm"] <= hi for row in regime_rows("both")])
    )
    drift_in_band = float(
        np.mean([lo <= row["median_cm"] <= hi for row in regime_rows("drift")])
    )
    calculated = {
        "median_genes": {
            regime: {
                "rho": med(regime, "median_rho"),
                "cm": med(regime, "median_cm"),
            }
            for regime in E52_REGIMES
        },
        "gate_p52_1_anatomy_corner": bool(
            med("anatomy", "median_cm") > med("drift", "median_cm")
            and med("anatomy", "median_rho") < med("drift", "median_rho")
        ),
        "gate_p52_2_plasticity_corner": bool(
            med("plasticity", "median_cm") < med("anatomy", "median_cm")
        ),
        "both_repeats_in_band": both_in_band,
        "drift_repeats_in_band": drift_in_band,
        "gate_p52_3_origin_of_development": bool(
            both_in_band >= 0.5 and both_in_band >= drift_in_band + 0.25
        ),
    }
    return {
        "integrity": integrity,
        "retained_config_digest": summary["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, summary["gates"]
        ),
        "both_regime_median_rho": calculated["median_genes"]["both"]["rho"],
        "rho_range": [0.0005, 0.2],
        "fitness_horizon": {
            "body_settle_sweeps": 30,
            "per_component_evaluation_sweeps": 40,
            "both_uses_separate_anatomy_and_plasticity_simulations": True,
        },
    }


def audit_e53(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="knife_shard", expected_shards=3
    )
    summary = tracker.json(root / "results/full/knife_summary.json")
    source = _read(tracker, root / "src/hidden_genome/pipeline.py")
    knife_source = _read(tracker, root / "src/hidden_genome/knives.py")
    blueprint_source = _read(
        tracker,
        root.parent / "blueprint_web/src/blueprint_web/engine.py",
    )
    tissues = [int(row["tissue"]) for row in entries]
    expected_factor_keys = {
        f"{r_arm}|{context}|{theta}"
        for r_arm in E53_R_ARMS
        for context in E53_CONTEXT_ARMS
        for theta in E53_THETA_ARMS
    }
    integrity.update(
        {
            "expected_entries": 6,
            "unique_tissues": len(set(tissues)),
            "complete_tissues": set(tissues) == set(range(6)),
            "no_duplicate_tissues": len(tissues) == len(set(tissues)),
            "all_rows_have_complete_factorial": all(
                set(row["fidelity"]) == expected_factor_keys
                and set(row["fidelity_vs_alt"]) == expected_factor_keys
                for row in entries
            ),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )
    entries = sorted(entries, key=lambda row: int(row["tissue"]))

    def mean_key(table: str, key: str) -> float:
        return float(np.mean([row[table][key] for row in entries]))

    fidelity = {key: mean_key("fidelity", key) for key in sorted(expected_factor_keys)}
    fidelity_alt = {
        key: mean_key("fidelity_vs_alt", key) for key in sorted(expected_factor_keys)
    }
    floor = {
        arm: float(np.mean([row["floor"][arm] for row in entries]))
        for arm in E53_R_ARMS
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
    transplant_follow = {
        "toward_pre_R_off": fidelity["R_off|transplant|intact"],
        "toward_alt_R_off": fidelity_alt["R_off|transplant|intact"],
        "toward_pre_R_on": fidelity["R_on|transplant|intact"],
        "toward_alt_R_on": fidelity_alt["R_on|transplant|intact"],
    }
    reconstructed = {
        "fidelity": fidelity,
        "fidelity_vs_alt": fidelity_alt,
        "floor": floor,
        "drops": drops,
        "winner": winner,
        "winner_drop": winner_drop,
        "loser_drop": loser_drop,
        "r_marginal": r_marginal,
        "transplant_follow": transplant_follow,
    }
    reported = summary["gates"]
    tissue_rows: list[dict[str, Any]] = []
    for row in entries:
        row_base = float(row["fidelity"]["R_on|intact|intact"])
        context = row_base - float(row["fidelity"]["R_on|reset|intact"])
        scramble = row_base - float(row["fidelity"]["R_on|intact|scrambled"])
        zero = row_base - float(row["fidelity"]["R_on|intact|zeroed"])
        feedback = row_base - float(row["fidelity"]["R_off|intact|intact"])
        alt_minus_pre = (
            float(row["fidelity_vs_alt"]["R_off|transplant|intact"])
            - float(row["fidelity"]["R_off|transplant|intact"])
        )
        tissue_rows.append(
            {
                "tissue": int(row["tissue"]),
                "baseline_fidelity": row_base,
                "context_reset_fidelity": float(
                    row["fidelity"]["R_on|reset|intact"]
                ),
                "context_reset_drop": context,
                "theta_scramble_fidelity": float(
                    row["fidelity"]["R_on|intact|scrambled"]
                ),
                "theta_scramble_drop": scramble,
                "theta_zero_fidelity": float(
                    row["fidelity"]["R_on|intact|zeroed"]
                ),
                "theta_zero_drop": zero,
                "feedback_off_fidelity": float(
                    row["fidelity"]["R_off|intact|intact"]
                ),
                "feedback_increment": feedback,
                "transplant_pre_fidelity_feedback_off": float(
                    row["fidelity"]["R_off|transplant|intact"]
                ),
                "transplant_alt_fidelity_feedback_off": float(
                    row["fidelity_vs_alt"]["R_off|transplant|intact"]
                ),
                "transplant_alt_minus_pre_feedback_off": alt_minus_pre,
                "floor_feedback_on": float(row["floor"]["R_on"]),
                "floor_feedback_off": float(row["floor"]["R_off"]),
            }
        )
    contrasts = {
        "context_reset_drop": _contrast(
            [row["context_reset_drop"] for row in tissue_rows], seed=20260902161
        ),
        "theta_scramble_drop": _contrast(
            [row["theta_scramble_drop"] for row in tissue_rows], seed=20260902162
        ),
        "theta_zero_drop": _contrast(
            [row["theta_zero_drop"] for row in tissue_rows], seed=20260902163
        ),
        "feedback_increment": _contrast(
            [row["feedback_increment"] for row in tissue_rows], seed=20260902164
        ),
        "transplant_alt_minus_pre_feedback_off": _contrast(
            [row["transplant_alt_minus_pre_feedback_off"] for row in tissue_rows],
            seed=20260902165,
        ),
    }
    probe = reported["probe"]
    probe_says_theta = (
        probe["mean_effect"] > 0.05 and probe["fraction_positive"] >= 0.75
    )
    aggregate_gate_recalculation = {
        "gate_p53_1_double_dissociation": bool(
            winner_drop >= 0.25 and loser_drop < 0.10
        ),
        "gate_p53_2_probe_agrees": bool((winner == "theta") == probe_says_theta),
        "gate_p53_3_r_marginal": bool(abs(r_marginal - 0.17) <= 0.10),
    }
    return {
        "integrity": integrity,
        "retained_config_digest": summary["config_digest"],
        "reconstructed_from_shards": reconstructed,
        "all_shard_derived_reported_fields_match": all(
            _recursive_close(reconstructed[key], reported[key])
            for key in reconstructed
        ),
        "aggregate_gate_recalculation": aggregate_gate_recalculation,
        "all_reported_gate_booleans_match": all(
            aggregate_gate_recalculation[key] == reported[key]
            for key in aggregate_gate_recalculation
        ),
        "tissue_contrasts": contrasts,
        "tissue_threshold_consistency": {
            "context_drop_at_least_0_25": sum(
                row["context_reset_drop"] >= 0.25 for row in tissue_rows
            ),
            "max_theta_drop_below_0_10": sum(
                max(row["theta_scramble_drop"], row["theta_zero_drop"]) < 0.10
                for row in tissue_rows
            ),
            "context_drop_exceeds_both_theta_drops": sum(
                row["context_reset_drop"] > row["theta_scramble_drop"]
                and row["context_reset_drop"] > row["theta_zero_drop"]
                for row in tissue_rows
            ),
            "feedback_increment_positive": sum(
                row["feedback_increment"] > 0 for row in tissue_rows
            ),
            "n_tissues": len(tissue_rows),
        },
        "intervention_audit": {
            "R_off_actually_sets_c_m_zero": "c_m = None if r_arm == \"R_on\" else 0.0" in source,
            "R_still_passed_to_regrow_in_feedback_off_arm": (
                "_regrow(V0, Rf.copy(), perm_theta[th]" in source
            ),
            "R_still_updates_when_c_m_zero": (
                'if rung in ("T", "Y", "TM") and Rf is not None:' in blueprint_source
                and "Rf = Rf + bp.rho * (V - Rf)" in blueprint_source
                and "and c_m > 0:" in blueprint_source
            ),
            "context_reset_sets_complement_to_resting": (
                "out[:, comp] = resting" in knife_source
            ),
            "baseline_already_sets_lesioned_quarter_to_resting": (
                "V0 = np.where(region[None], tissue.resting, pre)" in source
            ),
            "context_reset_leaves_any_original_V_fabric": False,
            "context_reset_cochanges_surviving_area_and_conserved_bulk": True,
            "theta_knives_are_local_to_lesioned_quarter": (
                "out[region] = 0.0" in knife_source
                and "out[region] = krng.permutation(vals)" in knife_source
            ),
        },
        "metric_contract": {
            "horizon_sweeps": 240,
            "region": "lesioned quarter only",
            "metric": "positional sign agreement with sub-threshold cells failing",
            "amplitude_threshold": 0.2,
            "target": "pre-lesion V or alternative settled V",
            "raw_differences_used_by_gate": True,
            "drift_floor_used_in_gate_arithmetic": False,
        },
        "content_transfer_control": {
            "contrast": "alternative minus pre fidelity, feedback-off transplant",
            "mean": contrasts["transplant_alt_minus_pre_feedback_off"][
                "mean_difference"
            ],
            "directions": contrasts["transplant_alt_minus_pre_feedback_off"][
                "directions"
            ],
            "favors_alternative_target": (
                contrasts["transplant_alt_minus_pre_feedback_off"][
                    "mean_difference"
                ]
                > 0
            ),
        },
        "long_run_probe": {
            **probe,
            "retained_resolution": "aggregate only",
            "pair_rows_retained": False,
            "consensus_maps_retained": False,
            "independently_reconstructed_this_audit": False,
            "evidence_level": "E2",
            "ordered_pairs_share_four_tissues": True,
        },
    }, tissue_rows


def audit_e54(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="rep_shard", expected_shards=3
    )
    summary = tracker.json(root / "results/full/repertoire_summary.json")
    keys = [(str(row["kind"]), int(row["tissue"])) for row in entries]
    expected_blocks = {
        (kind, tissue)
        for kind in ("adoption", "steering")
        for tissue in range(3)
    }
    adoption_blocks = [row for row in entries if row["kind"] == "adoption"]
    steering_blocks = [
        row
        for row in entries
        if row["kind"] == "steering" and row.get("steering") is not None
    ]
    runs = [run for block in adoption_blocks for run in block["runs"]]
    run_keys = [
        (
            int(block["tissue"]),
            str(run["class"]),
            int(run["target"]),
            int(run["dose"]),
        )
        for block in adoption_blocks
        for run in block["runs"]
    ]
    expected_runs = {
        (tissue, cls, target, dose)
        for tissue in range(3)
        for cls in E54_CLASSES
        for target in range(4)
        for dose in E54_DOSES
    }
    integrity.update(
        {
            "expected_entries": 6,
            "kind_counts": dict(Counter(key[0] for key in keys)),
            "unique_blocks": len(set(keys)),
            "complete_blocks": set(keys) == expected_blocks,
            "no_duplicate_blocks": len(keys) == len(set(keys)),
            "adoption_rows": len(runs),
            "unique_adoption_jobs": len(set(run_keys)),
            "complete_adoption_jobs": set(run_keys) == expected_runs,
            "no_duplicate_adoption_jobs": len(run_keys) == len(set(run_keys)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def selected(cls: str, dose: int, field: str) -> list[Any]:
        return [
            run[field]
            for run in runs
            if run["class"] == cls and int(run["dose"]) == dose
        ]

    adoption_table = {
        cls: {
            str(dose): {
                "delta": float(np.mean(selected(cls, dose, "delta"))),
                "exit_frac": float(np.mean(selected(cls, dose, "basin_exit"))),
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
            > adoption_table[control][str(dose)]["delta"]
            for control in E54_CLASSES
            if control != "in_repertoire"
        )
        and adoption_table["in_repertoire"][str(dose)]["exit_frac"] >= 0.5
    )
    order_mean = {
        cls: float(
            np.mean(
                [adoption_table[cls][str(dose)]["delta"] for dose in top2]
            )
        )
        for cls in E54_CLASSES
    }
    steering = {
        arm: float(
            np.mean([block["steering"][arm]["fraction_held"] for block in steering_blocks])
        )
        for arm in ("in_repertoire", "translated", "knife", "floor")
    }
    flagships = [
        block["flagship"]
        for block in steering_blocks
        if block["flagship"].get("found")
    ]
    flagship = {
        "n_found": len(flagships),
        "live": (
            float(np.mean([flag["live"]["final_inheritance"] for flag in flagships]))
            if flagships
            else None
        ),
        "knife": (
            float(np.mean([flag["knife"]["final_inheritance"] for flag in flagships]))
            if flagships
            else None
        ),
        "wild_floor": (
            float(
                np.mean([flag["wild_floor"]["final_inheritance"] for flag in flagships])
            )
            if flagships
            else None
        ),
    }
    calculated = {
        "adoption_table": adoption_table,
        "order_mean_top2": order_mean,
        "exit_bar_mean": float(np.mean([block["exit_bar"] for block in adoption_blocks])),
        "drift_floor_self": float(
            np.mean([block["drift_floor_self"] for block in adoption_blocks])
        ),
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

    block_by_tissue = {int(block["tissue"]): block for block in adoption_blocks}
    class_dose_rows: list[dict[str, Any]] = []
    tissue_lookup: dict[tuple[int, str, int], float] = {}
    for tissue in range(3):
        block_runs = block_by_tissue[tissue]["runs"]
        for cls in E54_CLASSES:
            for dose in E54_DOSES:
                rows = [
                    run
                    for run in block_runs
                    if run["class"] == cls and int(run["dose"]) == dose
                ]
                mean_delta = float(np.mean([row["delta"] for row in rows]))
                tissue_lookup[(tissue, cls, dose)] = mean_delta
                class_dose_rows.append(
                    {
                        "tissue": tissue,
                        "class": cls,
                        "dose": dose,
                        "n_targets": len(rows),
                        "mean_pre": float(np.mean([row["pre"] for row in rows])),
                        "mean_final": float(np.mean([row["final"] for row in rows])),
                        "mean_delta": mean_delta,
                        "basin_exit_fraction": float(
                            np.mean([row["basin_exit"] for row in rows])
                        ),
                        "mean_r_final": float(np.mean([row["r_final"] for row in rows])),
                    }
                )
    dose_seeds = dict(zip(E54_CLASSES, range(20260902171, 20260902175)))
    dose_contrasts = {
        cls: _contrast(
            [
                tissue_lookup[(tissue, cls, 500)]
                - tissue_lookup[(tissue, cls, 8)]
                for tissue in range(3)
            ],
            seed=dose_seeds[cls],
        )
        for cls in E54_CLASSES
    }
    control_seeds = {
        "cross_tissue": 20260902175,
        "surrogate": 20260902176,
        "translated": 20260902177,
    }
    class_contrasts = {}
    for control, seed in control_seeds.items():
        values = []
        for tissue in range(3):
            inrep = float(
                np.mean(
                    [tissue_lookup[(tissue, "in_repertoire", dose)] for dose in top2]
                )
            )
            other = float(
                np.mean([tissue_lookup[(tissue, control, dose)] for dose in top2])
            )
            values.append(inrep - other)
        class_contrasts[f"in_repertoire_minus_{control}_top2"] = _contrast(
            values, seed=seed
        )

    return {
        "integrity": integrity,
        "retained_config_digest": summary["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, summary["gates"]
        ),
        "registered_in_repertoire_winning_doses": inrep_wins,
        "dose_500_minus_8_by_class": dose_contrasts,
        "top2_class_contrasts": class_contrasts,
        "aggregate_delta_monotone_non_decreasing_by_class": {
            cls: all(
                adoption_table[cls][str(left)]["delta"]
                <= adoption_table[cls][str(right)]["delta"]
                for left, right in zip(E54_DOSES, E54_DOSES[1:])
            )
            for cls in E54_CLASSES
        },
        "equivalence_audit": {
            "registered_equivalence_margin": None,
            "equivalence_power_analysis": False,
            "failure_of_ordering_proves_equal_classes": False,
            "class_blindness_confirmed": False,
            "supported_reading": (
                "the registered same-tissue in-repertoire privilege failed on three tissues; "
                "cross-tissue was slightly highest in the top-two-dose aggregate"
            ),
        },
        "positive_control_audit": {
            "all_lineage_steering_rates_zero_including_floor": all(
                value == 0.0 for value in steering.values()
            ),
            "flagship_live_minus_knife": (
                flagship["live"] - flagship["knife"]
                if flagship["live"] is not None and flagship["knife"] is not None
                else None
            ),
            "successful_lineage_steering_positive_control": False,
        },
        "independent_unit": "tissue",
        "n_independent_tissues": 3,
        "targets_nested_per_class_dose_tissue": 4,
    }, class_dose_rows


def _half_life(curve: Sequence[float], stride: int) -> float | None:
    if not curve:
        return None
    initial = float(curve[0])
    bar = 0.5 + 0.5 * (initial - 0.5)
    if initial <= 0.5:
        return 0.0
    for index, value in enumerate(curve):
        if float(value) <= bar:
            return float((index + 1) * stride)
    return None


def audit_e56(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="scaffold_shard", expected_shards=3
    )
    summary = tracker.json(root / "results/full/scaffold_summary.json")
    runs = [row for row in entries if row["kind"] == "run"]
    knives = [row for row in entries if row["kind"] == "knife"]
    run_keys = [
        (
            int(row["tissue"]),
            str(row["schedule"]),
            int(row["t_anneal"]),
            bool(row["lesioned"]),
        )
        for row in runs
    ]
    expected_run_keys = {
        (tissue, schedule, t_anneal, False)
        for tissue in range(2)
        for schedule in ("gradual", "instant")
        for t_anneal in E56_ANNEAL_SWEEPS
    } | {
        (tissue, schedule, 1000, True)
        for tissue in range(2)
        for schedule in ("gradual", "instant")
    }
    knife_tissues = [int(row["tissue"]) for row in knives]
    half_life_matches = [
        _recursive_close(_half_life(row["curve"], 50), row["half_life"])
        for row in runs
    ]
    integrity.update(
        {
            "expected_entries": 22,
            "kind_counts": dict(Counter(str(row["kind"]) for row in entries)),
            "run_count": len(runs),
            "knife_count": len(knives),
            "complete_run_jobs": set(run_keys) == expected_run_keys,
            "no_duplicate_run_jobs": len(run_keys) == len(set(run_keys)),
            "complete_knife_tissues": set(knife_tissues) == {0, 1},
            "no_duplicate_knife_tissues": len(knife_tissues) == len(set(knife_tissues)),
            "all_stored_half_lives_recalculate_from_curves": all(half_life_matches),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )
    horizon = 2500.0

    def half_life_mean(schedule: str, t_anneal: int, lesioned: bool) -> float | None:
        rows = [
            row
            for row in runs
            if row["schedule"] == schedule
            and int(row["t_anneal"]) == t_anneal
            and bool(row["lesioned"]) == lesioned
        ]
        values = [
            float(row["half_life"]) if row["half_life"] is not None else horizon
            for row in rows
        ]
        return float(np.mean(values)) if values else None

    mid = 1000
    gradual = half_life_mean("gradual", mid, False)
    gradual_lesion = half_life_mean("gradual", mid, True)
    instant = half_life_mean("instant", mid, False)
    zaps = [
        row["zap"]
        for row in runs
        if row["schedule"] == "gradual"
        and int(row["t_anneal"]) == mid
        and not row["lesioned"]
    ]
    zaps_lesion = [
        row["zap"]
        for row in runs
        if row["schedule"] == "gradual"
        and int(row["t_anneal"]) == mid
        and row["lesioned"]
    ]

    def source_zap_recovery(rows: Sequence[Mapping[str, float]]) -> float | None:
        if not rows:
            return None
        return float(
            np.mean(
                [
                    (row["recovered"] - row["post"])
                    / max(row["pre"] - row["post"], 1e-9)
                    for row in rows
                ]
            )
        )

    anneal_curve = {
        str(t_anneal): half_life_mean("gradual", t_anneal, False)
        for t_anneal in E56_ANNEAL_SWEEPS
    }
    knife_curve = {}
    for fraction in E56_KNIFE_FRACTIONS:
        rows = [
            row
            for knife in knives
            for row in knife["rows"]
            if float(row["fraction"]) == fraction
        ]
        knife_curve[str(fraction)] = {
            "theta_lethality": float(np.mean([row["theta_lethality"] for row in rows])),
            "cm_lethality": float(np.mean([row["cm_lethality"] for row in rows])),
        }
    diffs = [
        knife_curve[str(fraction)]["theta_lethality"]
        - knife_curve[str(fraction)]["cm_lethality"]
        for fraction in E56_KNIFE_FRACTIONS
    ]
    crossing = None
    for left, right in zip(range(len(diffs) - 1), range(1, len(diffs))):
        if diffs[left] > 0 >= diffs[right] or diffs[left] >= 0 > diffs[right]:
            crossing = 0.5 * (
                E56_KNIFE_FRACTIONS[left] + E56_KNIFE_FRACTIONS[right]
            )
            break
    ratio = gradual / gradual_lesion if gradual and gradual_lesion else None
    anneal_values = [anneal_curve[str(value)] for value in E56_ANNEAL_SWEEPS]
    monotone = all(
        anneal_values[index] <= anneal_values[index + 1] + 1e-9
        for index in range(len(anneal_values) - 1)
    )
    calibration = summary["gates"]["calibration"]
    chosen = next(
        (
            row["amplitude"]
            for row in calibration["rows"]
            if row["pin"] >= 0.9 and row["clipped_frac"] < 0.05
        ),
        None,
    )
    calculated = {
        "calibration": calibration,
        "amplitude": chosen,
        "half_life": {
            "gradual": gradual,
            "gradual_lesion": gradual_lesion,
            "instant_equalized": instant,
            "by_t_anneal": anneal_curve,
        },
        "zap_recovery": {
            "live": source_zap_recovery(zaps),
            "lesion": source_zap_recovery(zaps_lesion),
        },
        "knife_curves": knife_curve,
        "crossing_fraction": crossing,
        "gate_p56_1_takeover": bool(
            ratio is not None
            and ratio >= 3.0
            and source_zap_recovery(zaps) is not None
            and source_zap_recovery(zaps_lesion) is not None
            and source_zap_recovery(zaps) >= source_zap_recovery(zaps_lesion) + 0.25
        ),
        "gate_p56_2_overlap_era": bool(
            gradual and instant is not None and instant < 0.5 * gradual
        ),
        "gate_p56_3_knives_cross": bool(
            crossing is not None and 0.0 < crossing < 1.0
        ),
        "gate_p56_4_anneal_rate": bool(monotone),
    }
    all_zaps = zaps + zaps_lesion
    return {
        "integrity": integrity,
        "retained_config_digest": summary["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, summary["gates"]
        ),
        "calibration_retention": {
            "retained_resolution": "aggregate only",
            "underlying_future_rows_retained": False,
            "chosen_amplitude_arithmetic_recalculates": chosen == calibration["chosen"],
            "chosen_amplitude": chosen,
            "pin_at_chosen": next(
                row["pin"] for row in calibration["rows"] if row["amplitude"] == chosen
            ),
            "evidence_level_for_pin": "E2",
        },
        "theta_scale": {
            "construction": "balanced target stripe multiplied by amplitude",
            "standard_deviation_at_chosen_amplitude": float(chosen),
            "target_aligned": True,
            "native_nominal_threshold_spread_range": [0.15, 0.30],
            "super_norm_relative_to_E57_fixed_0_3": bool(chosen > 0.3),
        },
        "zap_ratio_audit": {
            "source_denominator": "max(pre-post, 1e-9)",
            "rows_with_nonpositive_measured_drop": sum(
                row["pre"] - row["post"] <= 0 for row in all_zaps
            ),
            "rows_total": len(all_zaps),
            "live_raw_mean_pre_minus_post": float(
                np.mean([row["pre"] - row["post"] for row in zaps])
            ),
            "lesion_raw_mean_pre_minus_post": float(
                np.mean([row["pre"] - row["post"] for row in zaps_lesion])
            ),
            "reported_ratios_are_interpretable_recovery_fractions": False,
        },
        "per_tissue_mid_rows": [
            {
                "tissue": int(row["tissue"]),
                "schedule": str(row["schedule"]),
                "lesioned": bool(row["lesioned"]),
                "retention_at_scaffold_gone": float(row["retention_at_scaffold_gone"]),
                "half_life": row["half_life"],
                "zap": row["zap"],
            }
            for row in sorted(
                (row for row in runs if int(row["t_anneal"]) == mid),
                key=lambda row: (
                    int(row["tissue"]),
                    str(row["schedule"]),
                    bool(row["lesioned"]),
                ),
            )
        ],
    }


def audit_e57(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="assim_shard", expected_shards=6
    )
    summary = tracker.json(root / "results/full/assimilation_summary.json")
    keys = [(str(row["regime"]), int(row["repeat"])) for row in entries]
    expected = {
        (regime, repeat)
        for regime in E57_REGIMES
        for repeat in range(6)
    }
    integrity.update(
        {
            "expected_entries": 24,
            "unique_jobs": len(set(keys)),
            "complete_expected_jobs": set(keys) == expected,
            "no_duplicate_jobs": len(keys) == len(set(keys)),
            "all_trajectories_have_16_generations": all(
                len(row["trajectory"]) == 16 for row in entries
            ),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    def regime_rows(regime: str) -> list[dict[str, Any]]:
        return sorted(
            (row for row in entries if row["regime"] == regime),
            key=lambda row: int(row["repeat"]),
        )

    def med(regime: str, field: str) -> float:
        return float(np.median([row[field] for row in regime_rows(regime)]))

    switching = "switching_k4"
    band = (0.1, 0.3)
    switching_in_band = float(
        np.mean(
            [
                band[0] <= row["median_cm"] <= band[1]
                for row in regime_rows(switching)
            ]
        )
    )
    drift_in_band = float(
        np.mean(
            [
                band[0] <= row["median_cm"] <= band[1]
                for row in regime_rows("drift")
            ]
        )
    )
    static_cm = med("static", "median_cm")
    switching_cm = med(switching, "median_cm")
    selected_regimes = ("static", "switching_k2", "switching_k4")
    max_selected_median_rho = max(med(regime, "median_rho") for regime in selected_regimes)

    def lethality(regime: str, knife: str) -> float:
        return float(
            np.mean(
                [
                    row["knife"]["none"] - row["knife"][knife]
                    for row in regime_rows(regime)
                ]
            )
        )

    static_theta = lethality("static", "theta_scramble")
    static_cm_lethality = lethality("static", "cm_zero")
    switching_theta = lethality(switching, "theta_scramble")
    switching_cm_lethality = lethality(switching, "cm_zero")
    interaction = (
        (static_theta - static_cm_lethality)
        - (switching_theta - switching_cm_lethality)
    )

    def corr_gain(regime: str, reducer) -> float:
        values = []
        for row in regime_rows(regime):
            evolved = reducer(row["theta_target_corr"])
            native = reducer(row["native_target_corr"])
            values.append(evolved - native)
        return float(np.mean(values))

    static_corr_gain = corr_gain("static", lambda values: values[0])
    switching_corr_gain = corr_gain(switching, max)
    readoption = float(
        np.mean([row["readoption"] for row in regime_rows(switching)])
    )

    def transport_gap(regime: str) -> float:
        return float(
            np.mean(
                [
                    row["transport"]["none"] - row["transport"]["cm_zero"]
                    for row in regime_rows(regime)
                ]
            )
        )

    calculated = {
        "medians": {
            regime: {
                "rho": med(regime, "median_rho"),
                "cm": med(regime, "median_cm"),
            }
            for regime in E57_REGIMES
        },
        "switching_in_band": switching_in_band,
        "drift_in_band": drift_in_band,
        "knife_lethality": {
            "static": {"theta": static_theta, "cm": static_cm_lethality},
            "switching": {
                "theta": switching_theta,
                "cm": switching_cm_lethality,
            },
            "interaction": interaction,
        },
        "theta_corr_gain": {
            "static": static_corr_gain,
            "switching": switching_corr_gain,
        },
        "readoption_switching": readoption,
        "transport_gap": {
            "static": transport_gap("static"),
            "switching": transport_gap(switching),
        },
        "gate_p57_1_horizon_law": bool(
            (
                static_cm / max(switching_cm, 1e-9) >= 1.5
                or switching_cm / max(static_cm, 1e-9) >= 1.5
            )
            and switching_in_band >= 0.5
            and switching_in_band >= drift_in_band + 0.25
            and max_selected_median_rho <= 0.02
        ),
        "gate_p57_2_assimilation": bool(
            static_corr_gain > 0.2 and interaction > 0.1
        ),
        "gate_p57_3_plasticity_retained": bool(
            switching_cm_lethality > switching_theta and readoption >= 0.5
        ),
        "gate_p57_4_transport": bool(
            transport_gap("static") > 0.1 and transport_gap(switching) > 0.1
        ),
    }

    repeat_rows: list[dict[str, Any]] = []
    for row in sorted(entries, key=lambda item: (E57_REGIMES.index(item["regime"]), item["repeat"])):
        initial = row["trajectory"][0]
        final = row["trajectory"][-1]
        repeat_rows.append(
            {
                "regime": str(row["regime"]),
                "repeat": int(row["repeat"]),
                "initial_median_rho": float(initial["median_rho"]),
                "final_median_rho": float(row["median_rho"]),
                "rho_final_over_initial": float(
                    row["median_rho"] / initial["median_rho"]
                ),
                "initial_median_cm": float(initial["median_cm"]),
                "final_median_cm": float(row["median_cm"]),
                "cm_final_over_initial": float(row["median_cm"] / initial["median_cm"]),
                "champion_rho": float(row["champion"]["rho"]),
                "champion_cm": float(row["champion"]["cm"]),
                "rho_above_0_02": bool(row["median_rho"] > 0.02),
                "readoption": float(row["readoption"]),
                "transport_gap": float(
                    row["transport"]["none"] - row["transport"]["cm_zero"]
                ),
            }
        )
        if not _recursive_close(final["median_rho"], row["median_rho"]):
            raise ValueError("E57 final trajectory rho differs from retained row")
        if not _recursive_close(final["median_cm"], row["median_cm"]):
            raise ValueError("E57 final trajectory c_m differs from retained row")

    selected_repeat_rows = [
        row for row in repeat_rows if row["regime"] in selected_regimes
    ]
    return {
        "integrity": integrity,
        "retained_config_digest": summary["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, summary["gates"]
        ),
        "horizon_clause": {
            "coded_threshold": 0.02,
            "max_selected_regime_median_rho": max_selected_median_rho,
            "coded_no_fast_clause_passes": max_selected_median_rho <= 0.02,
            "literal_law_threshold": 0.016,
            "literal_unrounded_rho_at_or_below_0_016": (
                max_selected_median_rho <= 0.016
            ),
            "rounded_to_three_decimals": round(max_selected_median_rho, 3),
            "selected_repeat_medians_above_0_02": sum(
                row["rho_above_0_02"] for row in selected_repeat_rows
            ),
            "selected_repeat_count": len(selected_repeat_rows),
            "regime_median_is_not_every_repeat": True,
            "fitness_sweeps": 1000,
            "two_over_rho_min": 1000,
        },
        "initialization_audit": {
            regime: {
                "median_initial_rho": float(
                    np.median(
                        [
                            row["initial_median_rho"]
                            for row in repeat_rows
                            if row["regime"] == regime
                        ]
                    )
                ),
                "median_final_rho": med(regime, "median_rho"),
                "median_final_over_initial_within_repeat": float(
                    np.median(
                        [
                            row["rho_final_over_initial"]
                            for row in repeat_rows
                            if row["regime"] == regime
                        ]
                    )
                ),
            }
            for regime in E57_REGIMES
        },
        "horizon_identification": {
            "rho_range": [0.002, 0.05],
            "short_horizon_common_design_present": False,
            "horizon_randomized_or_factored": False,
            "horizon_isolated": False,
            "registered_compound_gate_passed": calculated[
                "gate_p57_1_horizon_law"
            ],
        },
    }, repeat_rows


def audit_e66(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/landlord_summary.json")
    source = _read(tracker, root / "src/writable_landlord/pipeline.py")
    gates = summary["gates"]
    capacity = gates["capacity"]
    chosen = next(
        (row["norm"] for row in capacity["rows"] if row["pin"] >= 0.8),
        None,
    )
    work = root / "results/full/work"
    lower_files = sorted(path for path in work.rglob("*") if path.is_file()) if work.is_dir() else []
    return {
        "retained_config_digest": summary["config_digest"],
        "capacity": capacity,
        "chosen_norm_recalculated_from_aggregate_rows": chosen,
        "chosen_norm_matches_reported": chosen == capacity["chosen"] == gates["norm"],
        "pin_at_chosen": next(
            row["pin"] for row in capacity["rows"] if row["norm"] == chosen
        ),
        "capacity_metric": {
            "target": "launch_pattern(1)",
            "theta_construction": "project_theta(tanh(1.5 * target), norm)",
            "target_aligned": True,
            "norm_is_per-field_standard_deviation": True,
            "chosen_norm": chosen,
            "horizon_sweeps": 300,
            "tissues": 1,
            "futures": 4,
            "R_present_but_feedback_gain": 0.0,
            "metric": "whole-sheet positional sign agreement",
            "amplitude_threshold": None,
            "source_checks_sign_only": (
                "pin = float(((V > 0) == (target > 0)[None]).mean())" in source
            ),
        },
        "retention": {
            "lower_level_files": [str(path.relative_to(root)) for path in lower_files],
            "capacity_future_rows_retained": False,
            "lineage_tissue_rows_retained": False,
            "retained_resolution": "aggregate summary only",
            "evidence_level_for_pin": "E2",
        },
        "static_capacity_is": {
            "engineered_target_aligned_sufficiency": True,
            "acquired_instance_memory": False,
            "lineage_heredity": False,
            "controlled_alignment_effect": False,
        },
        "imprint_boundary": {
            "reported_fidelity": gates["imprint_shot_fidelity"],
            "registered_bar": 0.75,
            "reported_gate": gates["gate_p66_3_imprint"],
            "passes": gates["imprint_shot_fidelity"] >= 0.75,
        },
        "wave14_to_implemented_lambda_change": {
            "wave14_registered_fractions": [0.1, 0.02],
            "implemented_fractions": [0.5, 0.1],
            "capacity_gate_depends_on_lambda": False,
            "change_recorded_in_current_expectations": True,
        },
    }


ROLE_TABLE_FIELDS = (
    "experiment",
    "assay",
    "target",
    "context",
    "r_present",
    "r_to_v_feedback",
    "theta_construction",
    "theta_alignment",
    "theta_scale_std_or_nominal",
    "horizon_sweeps",
    "score_name",
    "score_region",
    "amplitude_rule",
    "independent_unit",
    "retained_resolution",
    "value",
    "evidence_level",
    "directly_comparable_group",
    "note",
)


def rows_csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return handle.getvalue()


def role_table_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(rows, ROLE_TABLE_FIELDS)


def e53_tissue_contrasts_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "tissue",
            "baseline_fidelity",
            "context_reset_fidelity",
            "context_reset_drop",
            "theta_scramble_fidelity",
            "theta_scramble_drop",
            "theta_zero_fidelity",
            "theta_zero_drop",
            "feedback_off_fidelity",
            "feedback_increment",
            "transplant_pre_fidelity_feedback_off",
            "transplant_alt_fidelity_feedback_off",
            "transplant_alt_minus_pre_feedback_off",
            "floor_feedback_on",
            "floor_feedback_off",
        ),
    )


def e54_class_dose_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "tissue",
            "class",
            "dose",
            "n_targets",
            "mean_pre",
            "mean_final",
            "mean_delta",
            "basin_exit_fraction",
            "mean_r_final",
        ),
    )


def e57_regime_repeats_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "regime",
            "repeat",
            "initial_median_rho",
            "final_median_rho",
            "rho_final_over_initial",
            "initial_median_cm",
            "final_median_cm",
            "cm_final_over_initial",
            "champion_rho",
            "champion_cm",
            "rho_above_0_02",
            "readoption",
            "transport_gap",
        ),
    )


def _role_table(
    e48: Mapping[str, Any],
    e51: Mapping[str, Any],
    e52: Mapping[str, Any],
    e53: Mapping[str, Any],
    e54: Mapping[str, Any],
    e56: Mapping[str, Any],
    e57: Mapping[str, Any],
    e66: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(**values: Any) -> None:
        row = {field: None for field in ROLE_TABLE_FIELDS}
        row.update(values)
        rows.append(row)

    add(
        experiment="E48",
        assay="reported repair contrast",
        target="pre-lesion morphology",
        context="historical report; exact intervention row not retained",
        r_present="live versus ablated",
        r_to_v_feedback="contrast label only",
        theta_construction="native quenched field",
        theta_alignment="not target-aligned",
        theta_scale_std_or_nominal="nominal tissue field",
        horizon_sweeps="not recoverable from retained repair row",
        score_name="reported regrowth difference",
        score_region="not machine-recoverable",
        amplitude_rule="not machine-recoverable",
        independent_unit="not retained",
        retained_resolution="narrative/current-test only",
        value=e48["reported_difference_from_rounded_values"],
        evidence_level=e48["evidence_level_for_repair_values"],
        directly_comparable_group="E48_report_only",
        note="Rounded 0.711 minus 0.543; not the source of E53's exact 0.171875.",
    )
    e51_regeneration = e51["recalculated_gates"]["regeneration"]
    for arm, feedback, value in (
        ("two_headed_live", "on", e51_regeneration["two_headed"]),
        ("two_headed_c_m_zero", "off; c_m=0", e51_regeneration["two_headed_lesioned"]),
    ):
        add(
            experiment="E51",
            assay=f"regeneration {arm}",
            target="pre-lesion V sign pattern after eight lineage cycles",
            context="surviving three quarters retained",
            r_present=True,
            r_to_v_feedback=feedback,
            theta_construction="native quenched threshold field",
            theta_alignment="not instance-target-aligned",
            theta_scale_std_or_nominal="nominal 0.15-0.30 spread",
            horizon_sweeps=100,
            score_name="positional sign agreement",
            score_region="regrown quarter",
            amplitude_rule="none",
            independent_unit="tissue (10)",
            retained_resolution="tissue aggregate over futures",
            value=value,
            evidence_level="E3",
            directly_comparable_group="E51_regeneration",
            note="Arm labels enter RNG namespaces, so the descriptive tissue contrast is not stream-paired.",
        )

    e53_fidelity = e53["reconstructed_from_shards"]["fidelity"]
    e53_conditions = (
        ("baseline", "surviving complement retained", "on", "native intact", e53_fidelity["R_on|intact|intact"]),
        ("context_reset", "entire V sheet set to resting", "on", "native intact", e53_fidelity["R_on|reset|intact"]),
        ("theta_scramble", "surviving complement retained", "on", "local quarter scrambled", e53_fidelity["R_on|intact|scrambled"]),
        ("theta_zero", "surviving complement retained", "on", "local quarter zeroed", e53_fidelity["R_on|intact|zeroed"]),
        ("feedback_off", "surviving complement retained", "off; c_m=0", "native intact", e53_fidelity["R_off|intact|intact"]),
    )
    for assay, context, feedback, theta, value in e53_conditions:
        add(
            experiment="E53",
            assay=f"repair factorial: {assay}",
            target="pre-lesion settled V",
            context=context,
            r_present=True,
            r_to_v_feedback=feedback,
            theta_construction=theta,
            theta_alignment="native; not instance-target-aligned",
            theta_scale_std_or_nominal="nominal 0.15-0.30 spread",
            horizon_sweeps=240,
            score_name="amplitude-qualified positional sign fidelity",
            score_region="lesioned quarter",
            amplitude_rule="abs(V)>0.2; sub-threshold cells fail",
            independent_unit="tissue (6)",
            retained_resolution="tissue aggregate over 8 futures",
            value=value,
            evidence_level="E3",
            directly_comparable_group="E53_repair_factorial",
            note="All arms reuse a named regrow stream; intervention semantics come from current source.",
        )
    probe = e53["long_run_probe"]
    add(
        experiment="E53",
        assay="long-run theta transplant probe",
        target="donor theta's consensus map relative to non-donor maps",
        context="recipient tissue retained; donor theta substituted",
        r_present=True,
        r_to_v_feedback="off; c_m=0",
        theta_construction="native quenched field from donor tissue",
        theta_alignment="aligned to donor ensemble only, not a chosen instance",
        theta_scale_std_or_nominal="nominal 0.15-0.30 spread",
        horizon_sweeps=1000,
        score_name="centered-correlation donor advantage over median null",
        score_region="whole sheet",
        amplitude_rule="sign profile; no amplitude floor in correlation",
        independent_unit="12 ordered tissue pairs nested in 4 tissues",
        retained_resolution="aggregate only",
        value=probe["mean_effect"],
        evidence_level="E2",
        directly_comparable_group="E53_probe_only",
        note="All 12 effects were reported positive; pair rows and consensus maps were not retained.",
    )

    order = e54["recalculated_gates"]["order_mean_top2"]
    for cls in E54_CLASSES:
        add(
            experiment="E54",
            assay=f"adoption top-two-dose mean: {cls}",
            target=f"four nested {cls} targets per tissue",
            context="home state retained before imposed hold",
            r_present=True,
            r_to_v_feedback="on",
            theta_construction="native quenched threshold field",
            theta_alignment="class-dependent; not manipulated as an alignment factor",
            theta_scale_std_or_nominal="nominal 0.15-0.30 spread",
            horizon_sweeps=1200,
            score_name="post-free target fidelity minus pre-hold fidelity",
            score_region="whole sheet",
            amplitude_rule="abs(V)>0.2; sub-threshold cells fail",
            independent_unit="tissue (3); targets nested",
            retained_resolution="target x dose rows",
            value=order[cls],
            evidence_level="E3",
            directly_comparable_group="E54_adoption_top2",
            note="The registered privileged ordering failed; this is not an equivalence design.",
        )

    add(
        experiment="E56",
        assay="static scaffold capacity calibration",
        target="balanced four-domain stripe",
        context="random V launch",
        r_present=True,
        r_to_v_feedback="off; c_m=0",
        theta_construction="target stripe multiplied by amplitude",
        theta_alignment="exactly target-aligned",
        theta_scale_std_or_nominal=e56["calibration_retention"]["chosen_amplitude"],
        horizon_sweeps=300,
        score_name="amplitude-qualified positional sign retention",
        score_region="whole sheet",
        amplitude_rule="abs(V)>0.2; sub-threshold cells fail",
        independent_unit="one calibration tissue; 6 futures aggregated",
        retained_resolution="aggregate calibration row only",
        value=e56["calibration_retention"]["pin_at_chosen"],
        evidence_level="E2",
        directly_comparable_group="E56_capacity_only",
        note="Engineered sufficiency at amplitude 0.5; no future rows retained.",
    )
    add(
        experiment="E66",
        assay="static writable-landlord capacity calibration",
        target="launch_pattern(1)",
        context="random V launch",
        r_present=True,
        r_to_v_feedback="off; c_m=0",
        theta_construction="project_theta(tanh(1.5*target), norm)",
        theta_alignment="exactly target-aligned",
        theta_scale_std_or_nominal=e66["capacity_metric"]["chosen_norm"],
        horizon_sweeps=300,
        score_name="positional sign agreement",
        score_region="whole sheet",
        amplitude_rule="none",
        independent_unit="one tissue; 4 futures aggregated",
        retained_resolution="aggregate calibration row only",
        value=e66["pin_at_chosen"],
        evidence_level="E2",
        directly_comparable_group="E66_capacity_only",
        note="Static engineered sufficiency, not acquired memory or lineage heredity.",
    )
    add(
        experiment="E66",
        assay="imprint-shot lineage gate",
        target="imposed target after lineage writing",
        context="writable theta lineage protocol",
        r_present=True,
        r_to_v_feedback="on during lineage protocol",
        theta_construction="dynamically written and norm-projected",
        theta_alignment="acquired alignment candidate",
        theta_scale_std_or_nominal=e66["capacity_metric"]["chosen_norm"],
        horizon_sweeps="multi-cycle; not commensurate with capacity calibration",
        score_name="imprint-shot fidelity",
        score_region="lineage endpoint",
        amplitude_rule="experiment-specific",
        independent_unit="aggregate only",
        retained_resolution="aggregate summary only",
        value=e66["imprint_boundary"]["reported_fidelity"],
        evidence_level="E2",
        directly_comparable_group="E66_imprint_only",
        note="0.6274 misses the registered 0.75 bar.",
    )

    add(
        experiment="E52",
        assay="evolved BOTH-regime memory rate",
        target="anatomy plus plasticity fitness components",
        context="short campaign; fixed native theta",
        r_present=True,
        r_to_v_feedback="evolved c_m",
        theta_construction="native fixed",
        theta_alignment="not evolved toward target",
        theta_scale_std_or_nominal="native",
        horizon_sweeps="30 settle plus separate 40-sweep component evaluations",
        score_name="median evolved rho",
        score_region="population parameter",
        amplitude_rule="not a morphology score",
        independent_unit="repeat (8)",
        retained_resolution="repeat rows",
        value=e52["both_regime_median_rho"],
        evidence_level="E3",
        directly_comparable_group="E52_gene_selection_only",
        note="E52 permits rho up to 0.2.",
    )
    e57_medians = e57["recalculated_gates"]["medians"]
    for regime in ("static", "switching_k2", "switching_k4"):
        add(
            experiment="E57",
            assay=f"evolved {regime} memory rate",
            target="three-target assimilation fitness",
            context="1,000-sweep compound fitness campaign",
            r_present=True,
            r_to_v_feedback="evolved c_m",
            theta_construction="evolving field projected to norm 0.3",
            theta_alignment="emergent; assessed by later consensus correlation",
            theta_scale_std_or_nominal=0.3,
            horizon_sweeps=1000,
            score_name="median evolved rho",
            score_region="population parameter",
            amplitude_rule="not a morphology score",
            independent_unit="repeat (6)",
            retained_resolution="repeat rows and generation trajectories",
            value=e57_medians[regime]["rho"],
            evidence_level="E3",
            directly_comparable_group="E57_gene_selection",
            note="E57 constrains rho to 0.002-0.05; seven of 18 selected-regime repeat medians exceed 0.02.",
        )
    return rows


def _git_provenance(
    plastic_root: Path,
    package_results: Mapping[str, str],
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
    rows: dict[str, Any] = {}
    for package, result_name in package_results.items():
        root = _experiment_root(plastic_root, package)
        expectations = root / "EXPECTATIONS.md"
        result = root / "results/full" / result_name
        expectation_commit = _first_commit(repository_root, expectations)
        result_commit = _first_commit(repository_root, result)
        rows[package] = {
            "expectations_first_commit": expectation_commit,
            "selected_result_first_commit": result_commit,
            "same_first_commit_snapshot": (
                expectation_commit is not None and expectation_commit == result_commit
            ),
            "prose_date_is_git_verified_temporal_seal": False,
        }
    return {
        "repository_root": str(repository_root),
        "packages": rows,
        "same_snapshot_count": sum(
            row["same_first_commit_snapshot"] for row in rows.values()
        ),
        "package_count": len(rows),
    }


def run_l16_audit(
    plastic_root: Path,
    workspace: Path,
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
        ideas_root / "WAVE11_PROPHECIES.md",
        ideas_root / "WAVE12_PROPHECIES.md",
        ideas_root / "WAVE14_PROPHECIES.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        workspace / "SOURCE_BASELINE.md",
        workspace / "REVIEW_PROTOCOL.md",
        workspace / "protocols/L16_LANDLORD_TENANT_AUDIT_V1.md",
        workspace / "laws/L16_landlord_tenant.md",
        workspace / "reviews/L09_RETAINED_AUDIT_2026-09-02.md",
        workspace / "reviews/L11_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        workspace / "reviews/L15_TIMESCALE_AUDIT_2026-09-02.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    e48 = audit_e48(_experiment_root(plastic_root, "blueprint_web"), tracker)
    e51, e51_rows = audit_e51(
        _experiment_root(plastic_root, "two_headed_final"), tracker
    )
    e52 = audit_e52(_experiment_root(plastic_root, "origin_of_development"), tracker)
    e53, e53_rows = audit_e53(
        _experiment_root(plastic_root, "hidden_genome"), tracker
    )
    e54, e54_rows = audit_e54(
        _experiment_root(plastic_root, "repertoire"), tracker
    )
    e56 = audit_e56(_experiment_root(plastic_root, "scaffold"), tracker)
    e57, e57_rows = audit_e57(
        _experiment_root(plastic_root, "assimilation"), tracker
    )
    e66 = audit_e66(
        _experiment_root(plastic_root, "writable_landlord"), tracker
    )

    current_digests = source_config_digests()
    retained_digests = {
        "E51_two_headed_final": e51["retained_config_digest"],
        "E52_origin_of_development": e52["retained_config_digest"],
        "E53_hidden_genome": e53["retained_config_digest"],
        "E54_repertoire": e54["retained_config_digest"],
        "E56_scaffold": e56["retained_config_digest"],
        "E57_assimilation": e57["retained_config_digest"],
        "E66_writable_landlord": e66["retained_config_digest"],
    }
    digest_matches = {
        name: current_digests[name] == EXPECTED_CONFIG_DIGESTS[name]
        and current_digests[name] == retained_digests[name]
        for name in current_digests
    }
    role_rows = _role_table(e48, e51, e52, e53, e54, e56, e57, e66)

    provenance = _git_provenance(
        plastic_root,
        {
            "blueprint_web": "calibration_square.json",
            "two_headed_final": "worm_summary.json",
            "origin_of_development": "origin_summary.json",
            "hidden_genome": "knife_summary.json",
            "repertoire": "repertoire_summary.json",
            "scaffold": "scaffold_summary.json",
            "assimilation": "assimilation_summary.json",
            "writable_landlord": "landlord_summary.json",
        },
    )
    horizon_comparison = {
        "E52_both_median_rho": e52["both_regime_median_rho"],
        "E52_rho_range": e52["rho_range"],
        "E57_max_selected_regime_median_rho": e57["horizon_clause"][
            "max_selected_regime_median_rho"
        ],
        "E57_rho_range": e57["horizon_identification"]["rho_range"],
        "E57_coded_clause_at_0_02_passes": e57["horizon_clause"][
            "coded_no_fast_clause_passes"
        ],
        "E57_literal_law_clause_at_0_016_passes": e57["horizon_clause"][
            "literal_unrounded_rho_at_or_below_0_016"
        ],
        "E52_value_permitted_by_E57_search_range": (
            e57["horizon_identification"]["rho_range"][0]
            <= e52["both_regime_median_rho"]
            <= e57["horizon_identification"]["rho_range"][1]
        ),
        "E57_registered_compound_horizon_gate": e57["recalculated_gates"][
            "gate_p57_1_horizon_law"
        ],
        "campaign_differences": [
            "rho bounds",
            "population",
            "generations",
            "repeat and future counts",
            "theta evolution",
            "fitness definition",
            "target schedule",
            "tissue schedule",
            "observer",
        ],
        "horizon_randomized_or_factored_within_common_design": False,
        "horizon_causally_isolated": False,
    }
    comparability = {
        "role_table_is_common_metadata_contract": True,
        "role_table_is_common_numerical_observer": False,
        "all_cross_experiment_scores_directly_comparable": False,
        "E51_and_E53_directly_comparable": False,
        "E56_and_E66_directly_comparable": False,
        "aggregate_retention_allows_common_rescoring": False,
        "differences_blocking_common_score": [
            "target",
            "prehistory and initial condition",
            "horizon",
            "region",
            "amplitude rule",
            "tissue panel",
            "future count",
            "retained resolution",
        ],
        "alignment_scale_design": {
            "E53": "native, unaligned, nominal spread 0.15-0.30",
            "E56": "exactly target-aligned, standard deviation 0.5",
            "E57": "evolving, projected standard deviation 0.3",
            "E66_capacity": "exactly target-aligned, standard deviation 0.3",
        },
        "controlled_alignment_by_norm_factorial_present": False,
        "supported_cross_study_inference": (
            "alignment is a plausible modifier of theta capacity, but its causal effect is not isolated"
        ),
    }
    claims = [
        {
            "claim": "Surviving fabric/context carries the instance pattern on the repair timescale",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "E53 context reset lowers 240-sweep fidelity by 0.34668 in the six-tissue mean "
                "and in every tissue. The intervention erases all original V, not context alone, "
                "and cochanges surviving area and conserved bulk; the feedback-off transplant "
                "does not favor the alternative target. Dependence is supported, exclusivity is not."
            ),
        },
        {
            "claim": "The R ledger adds the reported repair increment",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "The exact E53 increment is 0.171875 and is positive in all six tissues. "
                "But R remains present and continues updating in both arms; the knife sets c_m=0. "
                "The identified contribution is active R-to-V feedback, not mere ledger presence."
            ),
        },
        {
            "claim": "Native-strength unaligned theta carries negligible instance information",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "Local scrambling and zeroing change E53's aggregate repair score by only 0.01986 "
                "and 0.03841, much less than context reset. Two of six tissues nevertheless miss "
                "the strict under-0.10 condition, and a local reachability assay cannot prove zero information."
            ),
        },
        {
            "claim": "Transplanted theta controls long-run ensemble statistics",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "E53 reports a 0.95402 donor-consensus advantage with 12/12 ordered pairs positive "
                "after theta transplant. The pair rows and maps were not retained, so the statistic "
                "is internally reported rather than independently recalculated and supports ensemble bias, not unique control."
            ),
        },
        {
            "claim": "Aligned native-norm theta can pin an instance despite the earlier null",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "E66's aggregate capacity calibration gives 0.97363 at projected norm 0.3; E56 gives "
                "0.96680 at aligned standard deviation 0.5. These are engineered static sufficiency "
                "tests with different observers, not demonstrations of acquired memory or heredity."
            ),
        },
        {
            "claim": "Native theta encodes a repertoire or landscape rather than individual memories",
            "verdict": "NOT_CONFIRMED_AS_WRITTEN",
            "evidence_level": "E2/E3",
            "reason": (
                "The E53 aggregate supports donor-dependent long-run bias and E54 refutes the registered "
                "in-repertoire ordering on three tissues. E54 registered no equivalence margin and all "
                "steering rates, including its floor, are zero; neither class blindness nor the exclusion of instance information follows."
            ),
        },
        {
            "claim": "Honest horizons remove E52's fast-memoryless corner",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "E57's selected-regime median clause passes at the coded 0.02 threshold, but its maximum "
                "is 0.0160855 and therefore not literally at or below 0.016; 7/18 repeat medians exceed 0.02 "
                "and P57.1 fails. E52's 0.1742 is impossible under E57's 0.05 upper bound, while many other design features change."
            ),
        },
    ]

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L16",
        "audit_kind": "outcome-known retained recalculation and source-level intervention audit",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "source_config_digests": current_digests,
        "retained_config_digests": retained_digests,
        "expected_config_digests": EXPECTED_CONFIG_DIGESTS,
        "source_config_digest_matches": digest_matches,
        "all_source_config_digests_match": all(digest_matches.values()),
        "git_provenance": provenance,
        "document_checks": {
            "law_contains_context_drop": "0.347" in texts["LAWS.md"],
            "law_contains_feedback_increment": "+0.172" in texts["LAWS.md"],
            "law_contains_probe_effect": "0.954" in texts["LAWS.md"],
            "wave12_records_p53_2_failure": "FAILED -> the two-timescale discovery" in texts["WAVE12_PROPHECIES.md"],
            "wave12_records_p57_1_failure": "FAILED AS CODED" in texts["WAVE12_PROPHECIES.md"],
            "manuscript_v2_3_independent_support": False,
        },
        "E48_historical_repair": e48,
        "E51_regeneration": e51,
        "E51_tissue_rows": e51_rows,
        "E52_origin_of_development": e52,
        "E53_hidden_genome": e53,
        "E53_tissue_rows": e53_rows,
        "E54_repertoire": e54,
        "E54_class_dose_rows": e54_rows,
        "E56_scaffold": e56,
        "E57_assimilation": e57,
        "E57_repeat_rows": e57_rows,
        "E66_alignment_modifier": e66,
        "role_table": role_rows,
        "metric_comparability": comparability,
        "E52_E57_horizon_comparison": horizon_comparison,
        "claim_assessment": claims,
        "landlord_tenant_labels_are_operational_metaphors_not_measured_variables": True,
        "strongest_supported_wording": (
            "Within E53's six-tissue, 240-sweep repair assay, erasing the remaining V fabric "
            "lowered amplitude-qualified fidelity by 0.3467, local native-theta scrambling or "
            "zeroing changed the aggregate score by 0.0199 or 0.0384, and disabling R-to-V "
            "feedback lowered it by 0.171875. E53 additionally reports a large donor-theta "
            "long-run ensemble effect. Separately, exactly target-aligned theta statically pins "
            "the tested targets at norm 0.3-0.5. These results support assay-, alignment-, and "
            "timescale-dependent roles in this implementation; they do not establish exclusive "
            "information carriers, class-blind repertoire, acquired theta memory or heredity, "
            "or a causal horizon law."
        ),
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        role_rows,
        e53_rows,
        e54_rows,
        e57_rows,
        frozen_hashes,
    )


def _fmt(value: float | int | None, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e51 = audit["E51_regeneration"]
    e53 = audit["E53_hidden_genome"]
    e54 = audit["E54_repertoire"]
    e56 = audit["E56_scaffold"]
    e57 = audit["E57_assimilation"]
    e66 = audit["E66_alignment_modifier"]
    lines = [
        "# L16 retained landlord/tenant audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained recalculation and source-level intervention audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "There is a real two-timescale pattern, but the landlord/tenant story assigns cleaner roles than the experiments identify.",
        "",
        "On E53's 240-sweep repair assay, resetting the surviving voltage fabric has the largest effect: fidelity falls by 0.3467. "
        "Local native-theta scrambling and zeroing have small aggregate effects of 0.0199 and 0.0384. "
        "Turning off the comparator lowers fidelity by exactly 0.171875. The important code-level correction is that this arm does not remove R: it sets `c_m=0`, while R remains present and continues updating.",
        "",
        "At the longer horizon, E53 reports a very large donor-theta ensemble effect, 0.9540 with all 12 ordered tissue pairs positive. "
        "Those pair rows and maps were discarded, so this is E2 aggregate evidence rather than an independently reconstructed result. "
        "E56 and E66 further show that deliberately target-aligned theta can statically pin a target. That is engineered sufficiency, not evidence that native theta acquired and inherited an individual memory.",
        "",
        "E54 does not establish class blindness: it only shows that its registered in-repertoire ordering failed on three tissues, with no equivalence margin and no successful steering positive control. "
        "E57 likewise does not isolate horizon. Its coded 0.02 median-rho clause passes, but the law's literal 0.016 bound fails before rounding, the compound P57.1 gate fails, and E52's 0.1742 value lies outside E57's allowed rho range.",
        "",
        "## Recalculated headline values",
        "",
        "| Evidence | Recalculated or retained value | Reading |",
        "|---|---:|---|",
        f"| E51 live regeneration | {_fmt(e51['recalculated_gates']['regeneration']['two_headed'], 6)} | High with active feedback |",
        f"| E51 `c_m=0` regeneration | {_fmt(e51['recalculated_gates']['regeneration']['two_headed_lesioned'], 6)} | Also high; E51 does not locate the carrier |",
        f"| E53 context-reset drop | {_fmt(e53['reconstructed_from_shards']['drops']['context_reset'], 6)} | Largest local repair contrast |",
        f"| E53 theta-scramble drop | {_fmt(e53['reconstructed_from_shards']['drops']['theta_scrambled'], 6)} | Small aggregate local effect |",
        f"| E53 theta-zero drop | {_fmt(e53['reconstructed_from_shards']['drops']['theta_zeroed'], 6)} | Small aggregate local effect |",
        f"| E53 feedback increment | {_fmt(e53['reconstructed_from_shards']['r_marginal'], 6)} | Active R-to-V comparator contribution |",
        f"| E53 long-run donor-theta effect | {_fmt(e53['long_run_probe']['mean_effect'], 6)} | Aggregate-only; 12/12 positive reported |",
        f"| E56 aligned pin, std 0.5 | {_fmt(e56['calibration_retention']['pin_at_chosen'], 6)} | Static engineered sufficiency |",
        f"| E66 aligned pin, std 0.3 | {_fmt(e66['pin_at_chosen'], 6)} | Static engineered sufficiency |",
        f"| E66 imprint shot | {_fmt(e66['imprint_boundary']['reported_fidelity'], 6)} | Fails registered 0.75 bar |",
        "",
        "## E53 tissue-level intervention audit",
        "",
        "| Contrast | Mean | Descriptive tissue-bootstrap 95% | Directions + / = / - |",
        "|---|---:|---:|---:|",
    ]
    for name, label in (
        ("context_reset_drop", "Context reset"),
        ("theta_scramble_drop", "Theta scramble"),
        ("theta_zero_drop", "Theta zero"),
        ("feedback_increment", "Active feedback"),
        ("transplant_alt_minus_pre_feedback_off", "Transplant alt minus pre, feedback off"),
    ):
        contrast = e53["tissue_contrasts"][name]
        interval = contrast["paired_tissue_bootstrap_95"]
        directions = contrast["directions"]
        lines.append(
            f"| {label} | {_fmt(contrast['mean_difference'], 6)} | "
            f"[{_fmt(interval[0], 6)}, {_fmt(interval[1], 6)}] | "
            f"{directions['positive']} / {directions['tied']} / {directions['negative']} |"
        )
    lines.extend(
        [
            "",
            "The context intervention first lesions one quarter and then resets the complementary three quarters, so no original V remains. "
            "It also changes surviving area and the conserved bulk state. Its effect supports dependence on surviving fabric, but the failed alternative-content contrast does not establish that fabric as the exclusive information carrier.",
            "",
            "## E54 is an ordering failure, not equivalence",
            "",
            "| Target class | Mean adoption delta at doses 200 and 500 |",
            "|---|---:|",
        ]
    )
    for cls, value in sorted(
        e54["recalculated_gates"]["order_mean_top2"].items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        lines.append(f"| {cls} | {_fmt(value, 6)} |")
    lines.extend(
        [
            "",
            "Cross-tissue targets are numerically highest, followed by in-repertoire, surrogate, and translated targets. "
            "The registered privilege gate fails. No equivalence margin or power calculation was registered, and all lineage-steering fractions—including the floor—are zero. The defensible conclusion is failure of the proposed ordering on this panel, not proof that all classes are equal.",
            "",
            "## Alignment and metric boundary",
            "",
            "| Experiment | Theta condition | Scale | Endpoint | Retention |",
            "|---|---|---:|---|---|",
            "| E53 repair | Native, unaligned; local knife | nominal 0.15–0.30 | quarter, 240 sweeps, amplitude-qualified sign | six tissue rows |",
            "| E53 probe | Native donor field | nominal 0.15–0.30 | donor consensus-correlation advantage, 1,000 post-transplant sweeps | aggregate only |",
            "| E56 capacity | Exactly target-aligned stripe | 0.5 | whole-sheet amplitude-qualified sign, 300 sweeps | aggregate only |",
            "| E66 capacity | Exactly target-aligned projection | 0.3 | whole-sheet sign, 300 sweeps | aggregate only |",
            "",
            "The E56/E66 scores cannot be normalized into an E53 effect: target, starting state, region, amplitude rule, tissue, future count, and retained resolution differ. The cross-study pattern makes alignment a plausible modifier but does not isolate it in a factorial experiment.",
            "",
            "E56's enormous reported zap recovery ratios are not interpretable recovery fractions. Three of four rows have a nonpositive measured `pre-post` drop, while the implementation floors that denominator at `1e-9`.",
            "",
            "## Horizon comparison",
            "",
            "| Quantity | Value |",
            "|---|---:|",
            f"| E52 BOTH median rho | {_fmt(audit['E52_E57_horizon_comparison']['E52_both_median_rho'], 7)} |",
            f"| E57 largest selected-regime median rho | {_fmt(e57['horizon_clause']['max_selected_regime_median_rho'], 7)} |",
            f"| E57 selected repeats above 0.02 | {e57['horizon_clause']['selected_repeat_medians_above_0_02']}/{e57['horizon_clause']['selected_repeat_count']} |",
            f"| E57 coded <=0.02 clause | {e57['horizon_clause']['coded_no_fast_clause_passes']} |",
            f"| L16 literal <=0.016 clause | {e57['horizon_clause']['literal_unrounded_rho_at_or_below_0_016']} |",
            f"| Registered compound P57.1 | {e57['recalculated_gates']['gate_p57_1_horizon_law']} |",
            "",
            "E52 allows rho through 0.2; E57 caps it at 0.05. Their population sizes, generations, repeats, futures, theta evolution, fitness, target schedules, and observers also differ. The missing high-rho corner therefore cannot be assigned uniquely to a longer or more honest horizon.",
            "",
            "## Clause verdicts",
            "",
            "| Atomic claim | Verdict | Evidence | Why |",
            "|---|---|---|---|",
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
            "## Reproducibility notes",
            "",
            f"- All seven independently transcribed current configurations match retained digests: `{audit['all_source_config_digests_match']}`.",
            f"- Hashed inputs: {audit['input_file_count']}.",
            "- E51 final inventory: 30 rows in four shards; E52: 32 in eight; E53: six complete factorial tissue rows in three; E54: 192 adoption rows plus three steering blocks; E56: 20 runs plus two knife blocks; E57: 24 repeat rows with 16 generations each; E66: aggregate only.",
            f"- Git first-appearance audit: {audit['git_provenance']['same_snapshot_count']}/{audit['git_provenance']['package_count']} selected expectation/result pairs first appear in the same snapshot. Same-snapshot appearance is not prospective sealing.",
            "- Bootstrap intervals use tissues as clusters, 4,096 resamples, and the frozen seeds. They describe these small panels rather than a population.",
            "- No historical simulator path was replayed and no new scientific future was generated.",
            "",
        ]
    )
    return "\n".join(lines)
