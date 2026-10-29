"""Outcome-known retained audit for L17's development/heredity split."""

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
from .l16_audit import audit_e54, audit_e56, audit_e57
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E54_repertoire": "a53c62d5e27dabead75c6659189d3e38a60db08d31773f1b6e162bf670646920",
    "E55_error_threshold": "26e403f2e841da5a1fd5d2cb15fedf678174644be094e14a5c1a54de38a57f54",
    "E56_scaffold": "fe2a28f7c0dae8e904d3e05f0b799a1ad4c96b7a7accff5c8d8af7534487a22b",
    "E57_assimilation": "a1aeadeb82501d395b22596dd6ea543f6c17564ea16963c17fe2255af30f40c2",
    "E61_alien_blueprint": "c1cb6bc49e026813c7d918f33b20d591e5ca5f90bd5ad993e48e481f5296e289",
}

TRACKED_PACKAGES = (
    "repertoire",
    "error_threshold",
    "scaffold",
    "assimilation",
    "alien_blueprint",
    "blueprint_web",
    "voltage_web",
    "setpoint_rewrite",
    "ladder_web",
    "contract_bridge",
    "kuramoto_web",
    "glider_test",
    "triangle_final",
    "james_final",
)

COMPLEXITIES = (2, 4, 8, 16)
SIGMA_GRID = (0.0, 0.02, 0.045, 0.1, 0.22, 0.5, 1.1, 2.4, 5.0)
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
        result_commit = _first_commit(
            repository_root, root / "results/full" / result_name
        )
        packages[package] = {
            "expectations_first_commit": expectation_commit,
            "selected_result_first_commit": result_commit,
            "same_first_commit_snapshot": (
                expectation_commit is not None and expectation_commit == result_commit
            ),
            "prose_date_is_git_verified_temporal_seal": False,
        }
    return {
        "repository_root": str(repository_root),
        "packages": packages,
        "same_snapshot_count": sum(
            row["same_first_commit_snapshot"] for row in packages.values()
        ),
        "package_count": len(packages),
    }


def source_config_digests() -> dict[str, str]:
    """Digest independently transcribed current E54--E57/E61 defaults."""

    configs: dict[str, dict[str, Any]] = {
        "E54_repertoire": {
            "mode": "full",
            "n_tissues": 3,
            "futures": 8,
            "harvest_settle": 1000,
            "verify_sweeps": 200,
            "verify_tolerance": 0.05,
            "verify_min": 0.5,
            "n_targets_per_class": 4,
            "doses": [8, 50, 200, 500],
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
        "E55_error_threshold": {
            "mode": "full",
            "n_tissues": 2,
            "futures": 6,
            "settle_sweeps": 120,
            "imprint_hold_sweeps": 1000,
            "imprint_hold": 1.2,
            "render_sweeps": 500,
            "cycles": 12,
            "inter_fission": 1000,
            "amp_threshold": 0.2,
            "selection_complexity": 4,
            "tournament": 3,
            "zap_sweeps": 8,
            "zap_recover": 300,
            "freedom_bar": 0.10,
            "trajectory_seed_tag": "eigen-v1",
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
            "rho_init": [0.002, 0.05],
            "rho_range": [0.002, 0.05],
            "cm_init": [0.1, 0.8],
            "cm_range": [0.05, 1.6],
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
        "E61_alien_blueprint": {
            "mode": "full",
            "futures": 16,
            "n_tissues": 4,
            "settle_gens": 8,
            "transport_shift": 8,
            "transport_recover_gens": 2,
            "retention_track_factor": 5,
            "inheritance_gens": 6,
            "pi_trap_bar": 2.5,
            "trajectory_seed_tag": "alien-bp-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def _half_life(curve: Sequence[float], stride: int) -> float | None:
    if not curve:
        return None
    start = float(curve[0])
    if start <= 0.5:
        return 0.0
    bar = 0.5 + 0.5 * (start - 0.5)
    for index, value in enumerate(curve):
        if float(value) <= bar:
            return float((index + 1) * stride)
    return None


def audit_e56_clock(
    root: Path, tracker: InputTracker, base_audit: Mapping[str, Any]
) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="scaffold_shard", expected_shards=3
    )
    summary = tracker.json(root / "results/full/scaffold_summary.json")
    runs = [entry for entry in entries if entry["kind"] == "run"]
    knives = [entry for entry in entries if entry["kind"] == "knife"]
    primary = sorted(
        (
            row
            for row in runs
            if row["schedule"] == "gradual"
            and int(row["t_anneal"]) == 1000
            and not row["lesioned"]
        ),
        key=lambda row: int(row["tissue"]),
    )
    rows = []
    for row in primary:
        recalculated = _half_life(row["curve"], 50)
        if not _recursive_close(recalculated, row["half_life"]):
            raise ValueError("E56 retained half-life does not match its curve")
        rows.append(
            {
                "tissue": int(row["tissue"]),
                "retention_at_scaffold_gone": float(
                    row["retention_at_scaffold_gone"]
                ),
                "first_sample_retention_at_50_sweeps": float(row["curve"][0]),
                "halfway_bar_anchored_to_first_sample": float(
                    0.5 + 0.5 * (row["curve"][0] - 0.5)
                ),
                "half_life_sweeps": recalculated,
                "curve_samples": len(row["curve"]),
            }
        )
    mean_half = float(np.mean([row["half_life_sweeps"] for row in rows]))
    rho = 0.002
    tau = 1.0 / rho
    integrity.update(
        {
            "kind_counts": dict(Counter(entry["kind"] for entry in entries)),
            "expected_20_runs": len(runs) == 20,
            "expected_2_knives": len(knives) == 2,
            "two_primary_tissues": len(rows) == 2,
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )
    return {
        "integrity": integrity,
        "full_summary_recalculation": dict(base_audit),
        "primary_rows": rows,
        "mean_half_life_sweeps": mean_half,
        "rho_from_current_shared_blueprint_default": rho,
        "tau_sweeps": tau,
        "mean_half_life_over_tau": mean_half / tau,
        "rho_values_tested_for_this_clock": [rho],
        "rho_scaling_identified": False,
        "half_life_resolution_sweeps": 50,
        "threshold_uses_release_time_retention": False,
        "threshold_uses_first_sample_at_50_sweeps": True,
        "shared_blueprint_defaults_included_in_E56_config_digest": False,
        "E50_same_clock": {
            "common_configured_rho": rho,
            "E50_observed_expiration_or_half_life": False,
            "measured_same_clock_confirmed": False,
        },
    }


def audit_e54_flagship(
    root: Path, tracker: InputTracker, base_audit: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="rep_shard", expected_shards=3
    )
    steering = sorted(
        (entry for entry in entries if entry["kind"] == "steering"),
        key=lambda row: int(row["tissue"]),
    )
    rows: list[dict[str, Any]] = []
    found_differences = []
    for entry in steering:
        flag = entry["flagship"]
        row = {
            "tissue": int(entry["tissue"]),
            "found": bool(flag.get("found")),
            "target_seed": flag.get("target_seed"),
            "n_plus_domains": flag.get("n_plus_domains"),
            "live": None,
            "knife_cm_zero": None,
            "wild_floor": None,
            "live_minus_knife": None,
        }
        if flag.get("found"):
            row.update(
                {
                    "live": float(flag["live"]["final_inheritance"]),
                    "knife_cm_zero": float(flag["knife"]["final_inheritance"]),
                    "wild_floor": float(flag["wild_floor"]["final_inheritance"]),
                    "live_minus_knife": float(
                        flag["live"]["final_inheritance"]
                        - flag["knife"]["final_inheritance"]
                    ),
                }
            )
            found_differences.append(row["live_minus_knife"])
        rows.append(row)
    source = _read(tracker, root / "src/repertoire/pipeline.py")
    targets_source = _read(tracker, root / "src/repertoire/targets.py")
    contrast = _contrast(found_differences, seed=20260903171, unit="tissue")
    headline = base_audit["recalculated_gates"]["flagship"]
    integrity.update(
        {
            "kind_counts": dict(Counter(entry["kind"] for entry in entries)),
            "expected_two_conditionally_found": sum(row["found"] for row in rows)
            == 2,
            "three_tissues_examined": len(rows) == 3,
        }
    )
    return {
        "integrity": integrity,
        "full_summary_recalculation": dict(base_audit),
        "headline": headline,
        "flagship_rows": rows,
        "live_minus_knife_contrast": contrast,
        "intervention_audit": {
            "R_copied_wholesale_in_live": "Rf.copy()" in targets_source,
            "R_copied_wholesale_in_knife": "Rf.copy()" in targets_source,
            "knife_sets_c_m_zero": '("live", None), ("knife", 0.0)' in source,
            "knife_deletes_R": False,
            "knife_prevents_R_to_V_feedback": True,
            "R_continues_updating_when_c_m_zero": True,
            "copy_versus_reset_control_present": False,
            "arm_is_in_rng_namespace": (
                '"flagship", index, arm' in source
            ),
            "common_random_number_arms": False,
        },
        "observer_audit": {
            "target_expression": "np.sign(R_start[0])",
            "uses_batch_member_zero_target_for_all_futures": (
                "np.sign(R_start[0])" in source
            ),
            "scores_each_future_against_its_own_R_start": False,
            "region": "cumulative ever-regrown cells",
            "amplitude_threshold": 0.2,
            "cycles": 8,
        },
        "interpretation": {
            "supports_active_feedback_benefit_in_selected_flagships": False,
            "supports_R_copy_versus_reset_causal_claim": False,
            "supports_exact_zero_effect": False,
            "conditional_on_flagship_discovery": True,
        },
    }, rows


def _tail_mean(row: Mapping[str, Any], key: str) -> float | None:
    values = [value for value in row[key][-3:] if value is not None]
    return float(np.mean(values)) if values else None


def audit_e55(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="eigen_shard", expected_shards=5
    )
    summary = tracker.json(root / "results/full/eigen_summary.json")
    source = _read(tracker, root / "src/error_threshold/pipeline.py")
    sweeps = [entry for entry in entries if entry["kind"] == "sweep"]
    selections = [entry for entry in entries if entry["kind"] == "selection"]
    jobs = [(int(entry["tissue"]), int(entry["k"])) for entry in sweeps]
    expected_jobs = {
        (tissue, complexity)
        for tissue in range(2)
        for complexity in COMPLEXITIES
    }
    row_lengths_ok = all(
        len(entry["rows"]) == len(SIGMA_GRID)
        and {float(row["sigma"]) for row in entry["rows"]} == set(SIGMA_GRID)
        and all(
            len(row["ancestor_fid_regrown1"]) == 12
            and len(row["ancestor_fid_regrown2"]) == 12
            and len(row["parent_fid"]) == 12
            for row in entry["rows"]
        )
        for entry in sweeps
    )
    integrity.update(
        {
            "kind_counts": dict(Counter(entry["kind"] for entry in entries)),
            "complete_sweep_jobs": set(jobs) == expected_jobs,
            "no_duplicate_sweep_jobs": len(jobs) == len(set(jobs)),
            "two_selection_jobs": len(selections) == 2,
            "nine_noise_rows_and_twelve_generations_each": row_lengths_ok,
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    curves: dict[str, dict[str, float | None]] = {}
    curve_rows: list[dict[str, Any]] = []
    for complexity in COMPLEXITIES:
        curves[str(complexity)] = {}
        for sigma in SIGMA_GRID:
            matching = [
                row
                for entry in sweeps
                if int(entry["k"]) == complexity
                for row in entry["rows"]
                if float(row["sigma"]) == sigma
            ]
            values = [_tail_mean(row, "ancestor_fid_regrown2") for row in matching]
            clean = [value for value in values if value is not None]
            mean_value = float(np.mean(clean)) if clean else None
            curves[str(complexity)][str(float(sigma))] = mean_value
            curve_rows.append(
                {
                    "k": complexity,
                    "sigma_R": sigma,
                    "fixed_ancestor_strict_tail_mean": mean_value,
                    "n_tissues": len(clean),
                    "tissue_values": clean,
                }
            )

    selection_curves = {}
    for sigma in SIGMA_GRID:
        values = [
            float(row["final_fid"])
            for entry in selections
            for row in entry["rows"]
            if float(row["sigma"]) == sigma
        ]
        selection_curves[str(float(sigma))] = float(np.mean(values)) if values else None

    primary = curves["4"]
    floor = primary["0.0"]
    losses = [
        max(0.0, float(floor) - float(primary[str(float(sigma))]))
        for sigma in SIGMA_GRID
    ]
    flat_threshold_branch = max(losses) <= 0.02
    sigma_star = None if flat_threshold_branch else "unexpected_nonflat_branch"
    width = None if flat_threshold_branch else "unexpected_nonflat_branch"
    selection_floor = selection_curves["0.0"]
    selection_losses = [
        max(0.0, float(selection_floor) - float(selection_curves[str(float(sigma))]))
        for sigma in SIGMA_GRID
    ]
    selection_flat_branch = max(selection_losses) <= 0.02
    sigma_star_selected = None if selection_flat_branch else "unexpected_nonflat_branch"
    capacity = {}
    for complexity in COMPLEXITIES:
        curve = curves[str(complexity)]
        k_floor = curve["0.0"]
        tolerated = [
            sigma
            for sigma in SIGMA_GRID
            if sigma > 0
            and curve[str(float(sigma))] is not None
            and float(curve[str(float(sigma))]) >= float(k_floor or 0) - 0.1
        ]
        capacity[str(complexity)] = float(max(tolerated)) if tolerated else 0.0
    rendition_domains = {
        str(complexity): int(
            np.median(
                [
                    int(entry["rendition_domains"])
                    for entry in sweeps
                    if int(entry["k"]) == complexity
                ]
            )
        )
        for complexity in COMPLEXITIES
    }
    cap_values = [capacity[str(complexity)] for complexity in COMPLEXITIES]
    monotone = all(
        cap_values[index] >= cap_values[index + 1] - 1e-9
        for index in range(len(cap_values) - 1)
    )
    distinct = len({round(value, 4) for value in cap_values}) >= 2
    calculated_gates = {
        "curves": curves,
        "capacity": capacity,
        "rendition_domains": rendition_domains,
        "sigma_star": sigma_star,
        "transition_width_decades": width,
        "sigma_star_selected": sigma_star_selected,
        "selection_shift": None,
        "selection_curves": selection_curves,
        "freedom": None,
        "gate_p55_1_sharp_threshold": False,
        "gate_p55_2_quasispecies_rescue": False,
        "gate_p55_3_capacity_law": bool(monotone and distinct),
        "gate_p55_4_freedom": False,
    }
    if sigma_star == "unexpected_nonflat_branch" or sigma_star_selected == "unexpected_nonflat_branch":
        raise ValueError("E55 entered an unregistered non-flat reconstruction branch")

    exact_blocks: dict[tuple[int, int], Mapping[str, Any]] = {}
    largest_noise_blocks: dict[tuple[int, int], Mapping[str, Any]] = {}
    generation_rows: list[dict[str, Any]] = []
    for entry in sorted(sweeps, key=lambda item: (item["tissue"], item["k"])):
        exact = next(row for row in entry["rows"] if float(row["sigma"]) == 0.0)
        largest = next(row for row in entry["rows"] if float(row["sigma"]) == 5.0)
        key = (int(entry["tissue"]), int(entry["k"]))
        exact_blocks[key] = exact
        largest_noise_blocks[key] = largest
        for generation in range(12):
            generation_rows.append(
                {
                    "tissue": key[0],
                    "k": key[1],
                    "rendition_domains": int(entry["rendition_domains"]),
                    "final_domains": int(exact["final_domains"]),
                    "generation": generation + 1,
                    "ancestor_fid_regrown1": float(
                        exact["ancestor_fid_regrown1"][generation]
                    ),
                    "ancestor_fid_regrown2_strict": (
                        None
                        if exact["ancestor_fid_regrown2"][generation] is None
                        else float(exact["ancestor_fid_regrown2"][generation])
                    ),
                    "immediate_parent_fid_regrown1": float(
                        exact["parent_fid"][generation]
                    ),
                }
            )

    pooled_trajectory = []
    for generation in range(12):
        rows_g = [row for row in generation_rows if row["generation"] == generation + 1]
        strict = [
            row["ancestor_fid_regrown2_strict"]
            for row in rows_g
            if row["ancestor_fid_regrown2_strict"] is not None
        ]
        pooled_trajectory.append(
            {
                "generation": generation + 1,
                "ancestor_regrown1_mean": float(
                    np.mean([row["ancestor_fid_regrown1"] for row in rows_g])
                ),
                "ancestor_strict_regrown2_mean": (
                    float(np.mean(strict)) if strict else None
                ),
                "immediate_parent_regrown1_mean": float(
                    np.mean([row["immediate_parent_fid_regrown1"] for row in rows_g])
                ),
            }
        )

    tissue_summaries = []
    for tissue in range(2):
        keys = [(tissue, complexity) for complexity in COMPLEXITIES]
        fixed = float(
            np.mean(
                [
                    _tail_mean(exact_blocks[key], "ancestor_fid_regrown2")
                    for key in keys
                ]
            )
        )
        parent = float(
            np.mean([_tail_mean(exact_blocks[key], "parent_fid") for key in keys])
        )
        largest = float(
            np.mean(
                [
                    _tail_mean(
                        largest_noise_blocks[key], "ancestor_fid_regrown2"
                    )
                    for key in keys
                ]
            )
        )
        tissue_summaries.append(
            {
                "tissue": tissue,
                "exact_copy_fixed_ancestor_strict_tail": fixed,
                "exact_copy_immediate_parent_tail": parent,
                "parent_minus_fixed_ancestor": parent - fixed,
                "sigma_5_fixed_ancestor_strict_tail": largest,
                "sigma_5_minus_exact_copy": largest - fixed,
                "rendition_domains_by_k": [
                    next(
                        int(entry["rendition_domains"])
                        for entry in sweeps
                        if int(entry["tissue"]) == tissue
                        and int(entry["k"]) == complexity
                    )
                    for complexity in COMPLEXITIES
                ],
                "exact_copy_final_domains_by_k": [
                    int(exact_blocks[key]["final_domains"]) for key in keys
                ],
            }
        )
    parent_contrast = _contrast(
        [row["parent_minus_fixed_ancestor"] for row in tissue_summaries],
        seed=20260903172,
        unit="tissue",
    )
    noise_contrast = _contrast(
        [row["sigma_5_minus_exact_copy"] for row in tissue_summaries],
        seed=20260903173,
        unit="tissue",
    )

    exact_tail = float(
        np.mean(
            [
                _tail_mean(row, "ancestor_fid_regrown2")
                for row in exact_blocks.values()
            ]
        )
    )
    parent_tail = float(
        np.mean([_tail_mean(row, "parent_fid") for row in exact_blocks.values()])
    )
    largest_tail = float(
        np.mean(
            [
                _tail_mean(row, "ancestor_fid_regrown2")
                for row in largest_noise_blocks.values()
            ]
        )
    )
    rendition_raw = [
        int(entry["rendition_domains"])
        for entry in sorted(sweeps, key=lambda item: (item["tissue"], item["k"]))
    ]
    final_raw = [int(exact_blocks[key]["final_domains"]) for key in sorted(exact_blocks)]
    return {
        "integrity": integrity,
        "retained_config_digest": summary["config_digest"],
        "recalculated_gates": calculated_gates,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated_gates, summary["gates"]
        ),
        "threshold_reconstruction": {
            "primary_complexity": 4,
            "primary_floor": floor,
            "maximum_nonnegative_loss_from_floor": max(losses),
            "flat_branch_at_loss_at_or_below_0_02": flat_threshold_branch,
            "selection_flat_branch": selection_flat_branch,
            "all_registered_gates_false": not any(
                calculated_gates[key]
                for key in (
                    "gate_p55_1_sharp_threshold",
                    "gate_p55_2_quasispecies_rescue",
                    "gate_p55_3_capacity_law",
                    "gate_p55_4_freedom",
                )
            ),
        },
        "exact_copy_channel": {
            "generation_1_ancestor_regrown_at_least_once": pooled_trajectory[0][
                "ancestor_regrown1_mean"
            ],
            "generation_1_strict_ancestor_is_undefined": pooled_trajectory[0][
                "ancestor_strict_regrown2_mean"
            ]
            is None,
            "generation_2_strict_ancestor": pooled_trajectory[1][
                "ancestor_strict_regrown2_mean"
            ],
            "generation_3_strict_ancestor": pooled_trajectory[2][
                "ancestor_strict_regrown2_mean"
            ],
            "generation_10_to_12_strict_ancestor_mean": exact_tail,
            "generation_10_to_12_immediate_parent_mean": parent_tail,
            "sigma_5_generation_10_to_12_strict_ancestor_mean": largest_tail,
            "pooled_generation_trajectory": pooled_trajectory,
            "tissue_summaries": tissue_summaries,
            "parent_minus_fixed_ancestor": parent_contrast,
            "sigma_5_minus_exact_copy": noise_contrast,
        },
        "domain_counts": {
            "post_imprint_rendition_raw": rendition_raw,
            "post_imprint_rendition_min": min(rendition_raw),
            "post_imprint_rendition_max": max(rendition_raw),
            "reported_truncated_medians_by_k": rendition_domains,
            "exact_copy_final_raw": final_raw,
            "exact_copy_final_min": min(final_raw),
            "exact_copy_final_max": max(final_raw),
            "exact_copy_final_median": float(np.median(final_raw)),
            "domain_count_is_alphabet_capacity": False,
        },
        "copy_intervention": {
            "R_is_whole_array_copied": "Rf.copy()" in source,
            "V_is_fragmented_and_jittered": (
                "offspring = offspring + tissue.copy_jitter" in source
            ),
            "R_copy_versus_reset_arm_present": False,
            "sigma_zero_is_exact_R_copy": True,
            "sigma_changes_R_only_after_fission": True,
        },
        "observer_and_null_audit": {
            "fixed_target_is_each_futures_own_post_render_rendition": (
                "(rendition > 0)" in source
            ),
            "strict_region": "cells regrown at least twice",
            "amplitude_threshold": 0.2,
            "shuffle_or_random_reference_null_retained": False,
            "target_and_output_sign_marginals_retained": False,
            "chance_value_0_5_calibrated": False,
            "near_0_5_is_descriptive_chance_like": True,
            "immediate_parent_tail_shows_observer_can_exceed_0_5": parent_tail
            > 0.9,
            "immediate_parent_similarity_identifies_R_transmission": False,
        },
        "selection_control": {
            "selection_curve_zero_through_sigma_2_4": all(
                selection_curves[str(float(sigma))] == 0.0
                for sigma in SIGMA_GRID
                if sigma <= 2.4
            ),
            "selection_curve_at_sigma_5": selection_curves["5.0"],
            "successful_positive_control": False,
            "freedom_check_ran": calculated_gates["freedom"] is not None,
        },
        "capacity_interpretation": {
            "reported_capacity_values": capacity,
            "capacity_is_largest_noise_within_0_1_of_own_floor": True,
            "floor_is_already_chance_like": True,
            "substantive_zero_capacity_established": False,
            "fixed_ancestor_loss_under_this_protocol_established": True,
        },
        "independent_unit": "tissue",
        "n_independent_tissues": 2,
        "complexities_nested_within_tissue": 4,
    }, curve_rows, generation_rows


def audit_e57_injury(
    root: Path, tracker: InputTracker, base_audit: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_shards(
        root, tracker, prefix="assim_shard", expected_shards=6
    )
    source = _read(tracker, root / "src/assimilation/pipeline.py")
    summary = tracker.json(root / "results/full/assimilation_summary.json")
    rows = []
    for entry in sorted(
        entries, key=lambda item: (E57_REGIMES.index(item["regime"]), item["repeat"])
    ):
        live = float(entry["transport"]["none"])
        knife = float(entry["transport"]["cm_zero"])
        rows.append(
            {
                "regime": str(entry["regime"]),
                "repeat": int(entry["repeat"]),
                "live": live,
                "knife_cm_zero": knife,
                "live_minus_knife": live - knife,
                "median_rho": float(entry["median_rho"]),
                "median_cm": float(entry["median_cm"]),
                "champion_rho": float(entry["champion"]["rho"]),
                "champion_cm": float(entry["champion"]["cm"]),
            }
        )
    contrasts = {}
    for regime, seed in (("static", 20260903174), ("switching_k4", 20260903175)):
        contrasts[regime] = _contrast(
            [row["live_minus_knife"] for row in rows if row["regime"] == regime],
            seed=seed,
            unit="repeat",
        )
    selected = [row for row in rows if row["regime"] != "drift"]
    exact_corner = [row for row in selected if close(row["champion_rho"], 0.002)]
    near_joint_corner = [
        row
        for row in exact_corner
        if abs(row["champion_cm"] - 0.2) <= 0.05
    ]
    integrity.update(
        {
            "unique_regime_repeat_jobs": len(
                {(entry["regime"], entry["repeat"]) for entry in entries}
            ),
            "complete_24_jobs": len(entries) == 24,
            "all_trajectories_have_16_generations": all(
                len(entry["trajectory"]) == 16 for entry in entries
            ),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )
    return {
        "integrity": integrity,
        "full_summary_recalculation": dict(base_audit),
        "transport_rows": rows,
        "transport_contrasts": contrasts,
        "source_design_audit": {
            "one_transport_rng_created_before_arm_loop": (
                'trng = seed_rng(config.trajectory_seed_tag + "-transport"' in source
                and 'for knife in ("none", "cm_zero")' in source
            ),
            "live_arm_consumes_rng_before_knife_arm": True,
            "fresh_starting_V_constructed_inside_each_arm": True,
            "same_pre_state_shared_across_arms": False,
            "common_random_number_arms": False,
            "fixed_arm_order": ["none", "cm_zero"],
            "each_arm_scored_against_its_own_pre_state": True,
            "knife_deletes_R": False,
            "knife_sets_c_m_zero": True,
            "R_continues_updating_when_c_m_zero": True,
        },
        "mechanism_observability": {
            "final_V_restoration_retained": True,
            "R_to_injury_similarity_retained": False,
            "R_time_course_retained": False,
            "injury_adoption_time_retained": False,
            "later_reinjury_defense_assay_present": False,
            "memorizes_then_defends_injury_identified": False,
            "negative_gap_is_consistent_with_harmful_feedback": True,
        },
        "speed_identification": {
            "champions_vary_rho_cm_and_theta_together": True,
            "rho_randomized_or_factored_in_transport": False,
            "slower_than_recovery_only_if_tested": False,
            "selected_champion_count": len(selected),
            "selected_champions_at_exact_rho_0_002": len(exact_corner),
            "selected_champions_at_rho_0_002_and_within_0_05_of_cm_0_2": len(
                near_joint_corner
            ),
            "corner_rows": exact_corner,
            "literal_no_selection_ever_visits_slow_rho_corner": False,
        },
    }, rows


def audit_e61(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/alienbp_summary.json")
    source = _read(tracker, root / "src/alien_blueprint/pipeline.py")
    gates = summary["gates"]
    transport = gates["transport"]
    retention = gates["retention"]
    inheritance = gates["inheritance"]
    slow_gap = float(transport["slow"]["fidelity"] - transport["slow_knife"]["fidelity"])
    fast_gap = float(transport["fast"]["fidelity"] - transport["fast_knife"]["fidelity"])

    def clock_ok(label: str) -> bool:
        row = retention[label]
        if row["half_life_steps"] is None:
            return False
        ratio = row["half_life_steps"] / row["tau_steps"]
        return bool(0.5 <= ratio <= 2.0)

    reset_live = inheritance["reset|live"]
    reset_knife = inheritance["reset|knife"]
    calculated = {
        "operating_point": dict(gates["operating_point"]),
        "census_void": bool(gates["census_void"]),
        "freedom_square": list(gates["freedom_square"]),
        "freedom_pass_exists": None,
        "transport": transport,
        "transport_slow_gap": slow_gap,
        "transport_fast_gap": fast_gap,
        "retention": retention,
        "inheritance": inheritance,
        "gate_e1_freedom": None,
        "gate_e2_transport_slow": bool(slow_gap > 0.05),
        "gate_e3_fast_reversal": bool(fast_gap < slow_gap - 0.05),
        "gate_e4_retention_clock": bool(clock_ok("slow") and clock_ok("fast")),
        "gate_e5_no_cross_fission": bool(
            abs(float(reset_live) - float(reset_knife)) < 0.05
        ),
        "instrument_memory": float(inheritance["copy|live"] - reset_live),
    }
    work = root / "results/full/work"
    lower_files = sorted(path for path in work.rglob("*") if path.is_file()) if work.is_dir() else []
    return {
        "retained_config_digest": summary["config_digest"],
        "recalculated_gates": calculated,
        "all_reported_gates_and_summaries_match": _recursive_close(
            calculated, gates
        ),
        "retention": {
            "conditions": retention,
            "all_four_half_lives_censored": all(
                row["half_life_steps"] is None for row in retention.values()
            ),
            "track_horizon_tau": 5,
            "feedback_off_retention_control": False,
            "R_reset_retention_control": False,
            "attributes_persistence_to_R_vault": False,
            "retained_full_curves": False,
            "retained_only_first_five_samples": True,
        },
        "inheritance": {
            "cells": inheritance,
            "live_values": {
                mode: inheritance[f"{mode}|live"]
                for mode in ("copy", "reset", "random")
            },
            "copy_live_minus_reset_live": calculated["instrument_memory"],
            "registered_gate_compares": "reset|live versus reset|knife",
            "registered_gate_is_copy_versus_reset": False,
            "copy_result_is_separate_aggregate_observation": True,
            "tissue_or_future_rows_retained": False,
            "uncertainty_reconstructable": False,
            "shuffle_null_or_sign_marginals_retained": False,
            "chance_value_0_5_calibrated": False,
            "values_are_descriptively_chance_like": True,
        },
        "transport": {
            "slow_gap": slow_gap,
            "fast_gap": fast_gap,
            "slow_gate_passed": calculated["gate_e2_transport_slow"],
            "fast_reversal_gate_passed": calculated["gate_e3_fast_reversal"],
        },
        "implementation": {
            "copy_leaves_Z_unchanged_at_fission": True,
            "reset_sets_Z_from_post_fission_theta": "Z = np.exp(1j * theta)" in source,
            "random_randomizes_Z": "rng.uniform(0, TWO_PI, theta.shape)" in source,
            "reference_is_first_generation_rerun_from_same_seed": (
                '"inherit", r_mode, arm, i' in source
            ),
            "score_region": "ever-regrown cells",
            "fixed_ancestor_horizon_generations": 6,
        },
        "retained_resolution": "aggregate summary only",
        "lower_level_files": [str(path.relative_to(root)) for path in lower_files],
        "evidence_level": "E2",
        "historical_elapsed_seconds": float(summary["elapsed_seconds"]),
        "distinct_simulated_substrate": True,
        "independent_investigator_or_protocol_replication": False,
    }


CHANNEL_TABLE_FIELDS = (
    "experiment",
    "substrate",
    "lineage_target",
    "R_fission_operation",
    "R_to_state_feedback",
    "comparison",
    "horizon",
    "score",
    "region",
    "amplitude_rule",
    "independent_unit",
    "retained_resolution",
    "value",
    "calibrated_null",
    "evidence_level",
    "note",
)


def _channel_table(
    e54: Mapping[str, Any],
    e55: Mapping[str, Any],
    e56: Mapping[str, Any],
    e57: Mapping[str, Any],
    e61: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(**kwargs: Any) -> None:
        missing = set(CHANNEL_TABLE_FIELDS) - set(kwargs)
        if missing:
            raise ValueError(f"channel row missing fields: {sorted(missing)}")
        rows.append(kwargs)

    add(
        experiment="E56",
        substrate="conserved bioelectric sheet",
        lineage_target="engineered four-domain stripe after scaffold removal",
        R_fission_operation="no fission in retention assay",
        R_to_state_feedback="active default c_m",
        comparison="decay from first sampled post-release score",
        horizon="2,500 sweeps; sampled every 50",
        score="halfway-to-0.5 crossing time",
        region="whole sheet",
        amplitude_rule="abs(V) > 0.2",
        independent_unit="tissue (2)",
        retained_resolution="tissue curves",
        value=e56["mean_half_life_sweeps"],
        calibrated_null="0.5 assumed by definition",
        evidence_level="E3",
        note="One rho only; this is not a rho-scaling test.",
    )
    for arm, value in (
        ("live", e54["headline"]["live"]),
        ("c_m=0", e54["headline"]["knife"]),
    ):
        add(
            experiment="E54",
            substrate="conserved bioelectric sheet",
            lineage_target="sign(R_start[0]) fixed at imprint end",
            R_fission_operation="whole R copied",
            R_to_state_feedback="active" if arm == "live" else "disabled",
            comparison=arm,
            horizon="8 fission cycles; 250 sweeps each",
            score="positional sign fidelity",
            region="cumulative ever-regrown cells",
            amplitude_rule="abs(V) > 0.2",
            independent_unit="conditionally found tissue (2)",
            retained_resolution="tissue aggregate and generation means",
            value=value,
            calibrated_null="no",
            evidence_level="E3",
            note="Both arms copy R; targets use batch member zero.",
        )
    for comparison, target, value in (
        (
            "sigma_R=0 exact R copy",
            "fixed post-render ancestor",
            e55["exact_copy_channel"]["generation_10_to_12_strict_ancestor_mean"],
        ),
        (
            "sigma_R=0 exact R copy",
            "immediate pre-fission parent",
            e55["exact_copy_channel"]["generation_10_to_12_immediate_parent_mean"],
        ),
        (
            "sigma_R=5 noisy R copy",
            "fixed post-render ancestor",
            e55["exact_copy_channel"][
                "sigma_5_generation_10_to_12_strict_ancestor_mean"
            ],
        ),
    ):
        add(
            experiment="E55",
            substrate="conserved bioelectric sheet",
            lineage_target=target,
            R_fission_operation=comparison,
            R_to_state_feedback="active default c_m",
            comparison=comparison,
            horizon="12 fissions; 1,000 sweeps between fissions",
            score="positional sign fidelity",
            region="regrown >=2 for fixed ancestor; >=1 for parent",
            amplitude_rule="abs(V) > 0.2",
            independent_unit="tissue (2); four nested k messages",
            retained_resolution="block by generation means",
            value=value,
            calibrated_null="no",
            evidence_level="E3",
            note="Fixed-ancestor and rolling-parent targets answer different questions.",
        )
    for regime in ("static", "switching_k4"):
        add(
            experiment="E57",
            substrate="conserved bioelectric sheet",
            lineage_target="each arm's own pre-displacement V",
            R_fission_operation="no fission in transport probe",
            R_to_state_feedback="live minus c_m=0",
            comparison=f"{regime} live-minus-knife",
            horizon="300 recovery sweeps",
            score="positional restoration difference",
            region="displaced quarter",
            amplitude_rule="abs(V) > 0.2",
            independent_unit="repeat/tissue (6)",
            retained_resolution="repeat endpoint",
            value=e57["transport_contrasts"][regime]["mean_difference"],
            calibrated_null="not applicable",
            evidence_level="E3",
            note="Sequential RNG, separate starts, no R-injury trajectory.",
        )
    for mode in ("copy", "reset", "random"):
        add(
            experiment="E61",
            substrate="Kuramoto phase lattice",
            lineage_target="first-generation binarized phase pattern",
            R_fission_operation=f"{mode} complex accumulator Z",
            R_to_state_feedback="active c_m=0.3",
            comparison=f"{mode}|live",
            horizon="6 generations",
            score="binary positional fidelity",
            region="ever-regrown cells",
            amplitude_rule="none; pi-trapped cells excluded only in transport",
            independent_unit="not retained (configured 4 tissues, 16 futures)",
            retained_resolution="aggregate summary only",
            value=e61["inheritance"]["live_values"][mode],
            calibrated_null="no",
            evidence_level="E2",
            note="No lower rows or sign marginals remain.",
        )
    return rows


def run_l17_audit(
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
    narrative = (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas_root / "LAWS.md",
        ideas_root / "WAVE12_PROPHECIES.md",
        ideas_root / "WAVE13_PROPHECIES.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        workspace / "SOURCE_BASELINE.md",
        workspace / "REVIEW_PROTOCOL.md",
        workspace / "protocols/L17_DEVELOPMENT_HEREDITY_AUDIT_V1.md",
        workspace / "laws/L17_development_not_heredity.md",
        workspace / "reviews/L15_TIMESCALE_AUDIT_2026-09-02.md",
        workspace / "reviews/L16_LANDLORD_TENANT_AUDIT_2026-09-02.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    repertoire_root = _experiment_root(plastic_root, "repertoire")
    scaffold_root = _experiment_root(plastic_root, "scaffold")
    assimilation_root = _experiment_root(plastic_root, "assimilation")
    base_e54, _ = audit_e54(repertoire_root, tracker)
    base_e56 = audit_e56(scaffold_root, tracker)
    base_e57, _ = audit_e57(assimilation_root, tracker)
    e54, e54_rows = audit_e54_flagship(repertoire_root, tracker, base_e54)
    e55, e55_curves, e55_generations = audit_e55(
        _experiment_root(plastic_root, "error_threshold"), tracker
    )
    e56 = audit_e56_clock(scaffold_root, tracker, base_e56)
    e57, e57_rows = audit_e57_injury(
        assimilation_root, tracker, base_e57
    )
    e61 = audit_e61(_experiment_root(plastic_root, "alien_blueprint"), tracker)

    current_digests = source_config_digests()
    retained_digests = {
        "E54_repertoire": e54["integrity"]["config_digest"],
        "E55_error_threshold": e55["retained_config_digest"],
        "E56_scaffold": e56["integrity"]["config_digest"],
        "E57_assimilation": e57["integrity"]["config_digest"],
        "E61_alien_blueprint": e61["retained_config_digest"],
    }
    digest_matches = {
        name: current_digests[name] == EXPECTED_CONFIG_DIGESTS[name]
        and current_digests[name] == retained_digests[name]
        for name in current_digests
    }
    provenance = _git_provenance(
        plastic_root,
        {
            "repertoire": "repertoire_summary.json",
            "error_threshold": "eigen_summary.json",
            "scaffold": "scaffold_summary.json",
            "assimilation": "assimilation_summary.json",
            "alien_blueprint": "alienbp_summary.json",
        },
    )
    channel_rows = _channel_table(e54, e55, e56, e57, e61)
    claims = [
        {
            "claim": "E56's post-scaffold memory is one time-constant and shares E50's grief clock",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "The two primary E56 tissues cross the coded halfway threshold at 550 and 600 sweeps "
                "(mean 575, or 1.15 times 1/rho). Only rho=0.002 was tested, the threshold is anchored "
                "to the first 50-sweep sample, and E50 observed no expiration, so scaling and a measured common clock do not follow."
            ),
        },
        {
            "claim": "Whole-R inheritance adds zero positional fidelity in E54",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "In two conditionally found flagships, live-minus-c_m=0 is -0.003337, with one "
                "positive and one negative tissue. Both arms copy all of R; the contrast disables "
                "feedback rather than inheritance, uses separate RNG namespaces, and scores all futures against R_start[0]."
            ),
        },
        {
            "claim": "At sigma_R=0, E55 loses the fixed post-render ancestor over 12 fissions",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "Across two tissues and four nested stripe inputs, the strict generation-10-to-12 "
                "fixed-ancestor mean is about 0.494 despite exact whole-R copying. This is a bounded "
                "loss result under 1,000-sweep inter-fission intervals and this observer."
            ),
        },
        {
            "claim": "The E55 channel has nil noiseless capacity and transmits nothing across lives",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "No calibrated chance null or copy-versus-reset arm exists. The reported capacity is "
                "noise tolerance relative to an already chance-like floor, while immediate-parent "
                "tail fidelity is about 0.941. That rolling score does not identify R transmission, "
                "but it defeats the inference from fixed-ancestor loss to literal zero signal."
            ),
        },
        {
            "claim": "E57 shows fast R memorizes a displacement and later defends the injury",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "The final static and switching-k4 gaps reproduce at -0.1263 and -0.09245, but no R-to-injury "
                "state or trajectory is retained. Arms use sequential RNG consumption, separate starts, and their own pre states; rho, c_m, and theta also vary together."
            ),
        },
        {
            "claim": "No selected lineage ever visits E49's slow-rho corner",
            "verdict": "REFUTED",
            "evidence_level": "E3",
            "reason": (
                "One selected switching-k2 champion is exactly at rho=0.002 with c_m=0.1525, within "
                "0.05 of E49's c_m=0.2. This does not establish the E49 mechanism, but it is a direct counterexample to the literal never-visits statement."
            ),
        },
        {
            "claim": "The fixed-ancestor null recurs on the Kuramoto phase lattice",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "E61's aggregate copy-live score is 0.49471 and copy-live minus reset-live is -0.00708. "
                "The distinct simulated substrate supports a bounded recurrence, but lower rows, uncertainty, "
                "and a calibrated chance null were not retained; the registered gate actually compares reset-live with reset-knife."
            ),
        },
        {
            "claim": "Three independent measurements establish development is not heredity",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2/E3",
            "reason": (
                "E54--E57 share the conserved-sheet engine and constructed R machinery, and E56 is a "
                "within-life retention assay rather than another inheritance test. E61 changes the substrate "
                "but retains an analogous designed R/fission/observer framework and aggregate-only evidence."
            ),
        },
        {
            "claim": "In this physics, fine anatomy is never heritable and only the landscape is",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2/E3",
            "reason": (
                "The experiments bound failure to preserve selected fixed positional targets at stated horizons. "
                "They do not exhaust encodings, readout schedules, target classes, transmission routes, or observers, and do not measure landscape as the exclusive inherited quantity."
            ),
        },
    ]
    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L17",
        "audit_kind": "outcome-known retained recalculation and source-level channel audit",
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
            "law_contains_575_sweeps": "575 sweeps" in texts["LAWS.md"],
            "law_contains_E54_live_knife_values": (
                "live 0.574 = knife 0.577" in texts["LAWS.md"]
            ),
            "law_contains_noiseless_capacity_nil": (
                "noiseless capacity over 12 fission cycles is" in texts["LAWS.md"]
            ),
            "law_contains_only_landscape": "ONLY THE LANDSCAPE" in texts["LAWS.md"],
            "wave12_records_E55_void": "Eigen" in texts["WAVE12_PROPHECIES.md"],
            "wave13_records_E61_predictions": "P61.5" in texts["WAVE13_PROPHECIES.md"],
            "manuscript_v2_3_independent_support": False,
        },
        "E54_whole_R_flagship": e54,
        "E55_error_threshold": e55,
        "E56_post_scaffold_clock": e56,
        "E57_injury_corollary": e57,
        "E61_alien_blueprint": e61,
        "channel_table": channel_rows,
        "claim_assessment": claims,
        "development_and_heredity_are_operational_labels_not_directly_measured_categories": True,
        "strongest_supported_wording": (
            "In this conserved-sheet implementation, E56's two target-aligned scaffold runs cross "
            "their coded post-release halfway threshold at 550 and 600 sweeps when rho=0.002. In E55, "
            "exact whole-R copying across twelve fissions does not maintain the fixed post-render ancestor: "
            "the strict final-three-generation mean is about 0.494, although immediate-parent similarity "
            "is about 0.941. E54 detects no active-feedback advantage in two selected flagships, and E61 "
            "reports a 0.495 copied-reference score with no aggregate advantage over reset on a Kuramoto "
            "lattice. These bounded results support loss of the tested fixed positional instances at the "
            "tested horizons; they do not establish zero channel capacity, a universal separation of "
            "development from heredity, exclusive landscape inheritance, or E57's injury-memory mechanism."
        ),
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        channel_rows,
        e54_rows,
        e55_curves,
        e55_generations,
        e57_rows,
        frozen_hashes,
    )


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e54 = audit["E54_whole_R_flagship"]
    e55 = audit["E55_error_threshold"]
    e56 = audit["E56_post_scaffold_clock"]
    e57 = audit["E57_injury_corollary"]
    e61 = audit["E61_alien_blueprint"]
    exact = e55["exact_copy_channel"]
    lines = [
        "# L17 retained development/heredity audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained recalculation and source-level channel audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "A narrow result survives: these experiments do not preserve their chosen fixed ancestral positional pattern across long fission lineages, even when R is copied exactly. The broader claim that nothing is transmitted does not survive the same audit.",
        "",
        f"E55's exact-copy fixed-ancestor score falls to {_fmt(exact['generation_10_to_12_strict_ancestor_mean'], 6)} over generations 10–12. Yet its immediate-parent score over the same tail is {_fmt(exact['generation_10_to_12_immediate_parent_mean'], 6)}. That high rolling similarity does not prove R carried information—it may reflect convergence to a simple landscape attractor—but it shows why loss of one fixed ancestor is not equivalent to zero continuity or zero channel capacity.",
        "",
        f"E54's live-minus-feedback-off difference is {_fmt(e54['live_minus_knife_contrast']['mean_difference'], 6)} in only two conditionally found tissues. Both arms copy R wholesale; the knife only prevents R from acting on V. E61 adds a genuinely different simulated substrate, where copied-reference fidelity is {_fmt(e61['inheritance']['live_values']['copy'], 6)}, but only aggregate values remain and 0.5 was not calibrated as the null for the actual maps.",
        "",
        "The injury story is not directly measured. E57 reproduces negative final restoration contrasts, but it stores no evidence that R moved toward the displaced pattern or later defended it. Its two arms also start separately and consume one random stream in fixed sequence.",
        "",
        "## Recalculated headline values",
        "",
        "| Experiment and endpoint | Value | What it establishes |",
        "|---|---:|---|",
        f"| E56 post-scaffold half-life, tissues | 550, 600 sweeps | Mean 575 at one rho; not rho scaling |",
        f"| E56 mean / `1/rho` | {_fmt(e56['mean_half_life_over_tau'], 3)} | Numerical proximity at rho=0.002 |",
        f"| E54 live flagship | {_fmt(e54['headline']['live'])} | Active-feedback arm |",
        f"| E54 `c_m=0` flagship | {_fmt(e54['headline']['knife'])} | R copied and updated but unread |",
        f"| E55 exact-copy fixed ancestor, generations 10–12 | {_fmt(exact['generation_10_to_12_strict_ancestor_mean'])} | Fixed positional identity is not maintained |",
        f"| E55 exact-copy immediate parent, generations 10–12 | {_fmt(exact['generation_10_to_12_immediate_parent_mean'])} | High rolling continuity; carrier not identified |",
        f"| E55 sigma_R=5 fixed ancestor, generations 10–12 | {_fmt(exact['sigma_5_generation_10_to_12_strict_ancestor_mean'])} | No degradation from an already floor-like score |",
        f"| E61 copy-live | {_fmt(e61['inheritance']['live_values']['copy'])} | Aggregate fixed-pattern null on Kuramoto |",
        f"| E61 copy-live minus reset-live | {_fmt(e61['inheritance']['copy_live_minus_reset_live'])} | No aggregate copied-R advantage |",
        "",
        "## E55 separates ancestor identity from parent continuity",
        "",
        "| Generation | Fixed ancestor, regrown >=1 | Fixed ancestor, strict regrown >=2 | Immediate parent |",
        "|---:|---:|---:|---:|",
    ]
    for row in exact["pooled_generation_trajectory"]:
        lines.append(
            f"| {row['generation']} | {_fmt(row['ancestor_regrown1_mean'])} | "
            f"{_fmt(row['ancestor_strict_regrown2_mean'])} | "
            f"{_fmt(row['immediate_parent_regrown1_mean'])} |"
        )
    parent_ci = exact["parent_minus_fixed_ancestor"]["paired_tissue_bootstrap_95"]
    noise_ci = exact["sigma_5_minus_exact_copy"]["paired_tissue_bootstrap_95"]
    lines.extend(
        [
            "",
            f"After collapsing the four k messages within each tissue, parent-minus-fixed-ancestor tail fidelity is {_fmt(exact['parent_minus_fixed_ancestor']['mean_difference'])}, with a descriptive two-tissue bootstrap interval [{_fmt(parent_ci[0])}, {_fmt(parent_ci[1])}]. Sigma-5-minus-exact-copy fixed-ancestor fidelity is {_fmt(exact['sigma_5_minus_exact_copy']['mean_difference'])}, interval [{_fmt(noise_ci[0])}, {_fmt(noise_ci[1])}].",
            "",
            f"Post-imprint rendition counts span {e55['domain_counts']['post_imprint_rendition_min']}–{e55['domain_counts']['post_imprint_rendition_max']} domains in the raw eight blocks. Exact-copy final counts span {e55['domain_counts']['exact_copy_final_min']}–{e55['domain_counts']['exact_copy_final_max']} with median {_fmt(e55['domain_counts']['exact_copy_final_median'], 1)}. Domain counts do not by themselves define an alphabet or measure its information capacity.",
            "",
            "The summary's four capacity values are all 5.0 only because capacity is defined as the largest tested noise whose score remains within 0.1 of its own sigma-zero floor. Since that floor is already near 0.5, this is a vacuous tolerance value rather than evidence of high or zero capacity. All four registered E55 gates remain false. The selection arm is zero through sigma=2.4 and therefore supplies no successful positive control.",
            "",
            "## E54 intervention boundary",
            "",
            "| Tissue | Found | Live | `c_m=0` | Wild floor | Live - knife |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in e54["flagship_rows"]:
        lines.append(
            f"| {row['tissue']} | {row['found']} | {_fmt(row['live'])} | "
            f"{_fmt(row['knife_cm_zero'])} | {_fmt(row['wild_floor'])} | "
            f"{_fmt(row['live_minus_knife'])} |"
        )
    e54_ci = e54["live_minus_knife_contrast"]["paired_tissue_bootstrap_95"]
    e54_dirs = e54["live_minus_knife_contrast"]["directions"]
    lines.extend(
        [
            "",
            f"The descriptive two-tissue interval is [{_fmt(e54_ci[0])}, {_fmt(e54_ci[1])}], with directions + / = / - = {e54_dirs['positive']} / {e54_dirs['tied']} / {e54_dirs['negative']}. The source uses the arm label in the RNG namespace and uses `sign(R_start[0])` as the target for all futures. The result supports no detectable active-feedback benefit in this tiny conditional panel; it is not a copy-versus-reset inheritance experiment.",
            "",
            "## E57 final contrasts do not observe injury memory",
            "",
            "| Regime | Mean live - `c_m=0` | Descriptive repeat-bootstrap 95% | Directions + / = / - |",
            "|---|---:|---:|---:|",
        ]
    )
    for regime in ("static", "switching_k4"):
        contrast = e57["transport_contrasts"][regime]
        interval = contrast["paired_repeat_bootstrap_95"]
        directions = contrast["directions"]
        lines.append(
            f"| {regime} | {_fmt(contrast['mean_difference'])} | "
            f"[{_fmt(interval[0])}, {_fmt(interval[1])}] | "
            f"{directions['positive']} / {directions['tied']} / {directions['negative']} |"
        )
    lines.extend(
        [
            "",
            "Negative final gaps are consistent with active feedback harming restoration, but the mechanism is underdetermined. R-to-injury similarity, its time course, adoption, and defense under a later challenge were never retained. A single RNG is consumed through the live arm and then the knife arm, with a new start and a new pre-displacement reference inside each arm.",
            "",
            f"The literal claim that selection never visits the slow corner is false: {e57['speed_identification']['selected_champions_at_exact_rho_0_002']} selected champion reaches rho=0.002, and its c_m is within 0.05 of E49's 0.2. This is not proof of E49-like transport; it is only a counterexample to `never visits`.",
            "",
            "## E61 portability boundary",
            "",
            "| R-at-fission mode | Live | Knife |",
            "|---|---:|---:|",
        ]
    )
    for mode in ("copy", "reset", "random"):
        lines.append(
            f"| {mode} | {_fmt(e61['inheritance']['cells'][mode + '|live'])} | "
            f"{_fmt(e61['inheritance']['cells'][mode + '|knife'])} |"
        )
    lines.extend(
        [
            "",
            f"The registered no-cross-fission gate passes because reset-live and reset-knife differ by less than 0.05; it is not a copy-versus-reset gate. The copied-R value and its {_fmt(e61['inheritance']['copy_live_minus_reset_live'])} difference from reset are supporting aggregates. With no tissue/future rows or sign marginals, uncertainty and the actual chance null cannot be reconstructed.",
            "",
            f"All four retention half-lives are censored beyond five tau. There is no feedback-off or R-reset retention control, so this shows persistence in the full phase-lattice system, not that R is a vault. The slow and fast transport gaps are positive ({_fmt(e61['transport']['slow_gap'])}, {_fmt(e61['transport']['fast_gap'])}); both relevant registered transport gates fail.",
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
            f"- All five independently transcribed current configurations match retained digests: `{audit['all_source_config_digests_match']}`.",
            f"- Hashed inputs: {audit['input_file_count']}.",
            "- E54 has three shards and two conditionally found flagship rows; E55 has five shards, eight complete sweep blocks, and two selection blocks; E56 has 20 runs and two knife blocks; E57 has 24 complete repeat rows; E61 is aggregate only.",
            f"- Git first-appearance audit: {audit['git_provenance']['same_snapshot_count']}/{audit['git_provenance']['package_count']} selected expectation/result pairs first appear in the same snapshot. Same-snapshot appearance is not prospective sealing.",
            "- Bootstrap intervals use the retained tissue/repeat clusters, 4,096 resamples, and frozen seeds. With only two or six clusters, they are panel descriptions rather than population validation.",
            "- No historical simulator path was replayed and no new scientific future was generated.",
            "",
        ]
    )
    return "\n".join(lines)


def _csv_text(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(fields), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        cooked = {
            field: (
                ""
                if row.get(field) is None
                else ";".join(str(value) for value in row[field])
                if isinstance(row.get(field), list)
                else row.get(field)
            )
            for field in fields
        }
        writer.writerow(cooked)
    return stream.getvalue()


def channel_table_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv_text(rows, CHANNEL_TABLE_FIELDS)


def e54_flagship_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv_text(
        rows,
        (
            "tissue",
            "found",
            "target_seed",
            "n_plus_domains",
            "live",
            "knife_cm_zero",
            "wild_floor",
            "live_minus_knife",
        ),
    )


def e55_channel_curves_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv_text(
        rows,
        (
            "k",
            "sigma_R",
            "fixed_ancestor_strict_tail_mean",
            "n_tissues",
            "tissue_values",
        ),
    )


def e55_generation_trace_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv_text(
        rows,
        (
            "tissue",
            "k",
            "rendition_domains",
            "final_domains",
            "generation",
            "ancestor_fid_regrown1",
            "ancestor_fid_regrown2_strict",
            "immediate_parent_fid_regrown1",
        ),
    )


def e57_transport_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv_text(
        rows,
        (
            "regime",
            "repeat",
            "live",
            "knife_cm_zero",
            "live_minus_knife",
            "median_rho",
            "median_cm",
            "champion_rho",
            "champion_cm",
        ),
    )
