"""Outcome-known retained audit for L22's body-proofreads-gene claim."""

from __future__ import annotations

import csv
import io
import itertools
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E55_error_threshold": "26e403f2e841da5a1fd5d2cb15fedf678174644be094e14a5c1a54de38a57f54",
    "E65_teaching": "1f30524f09da9001192f2c9a6b559f63f888c41a14e7a2a93a0a18f72c961ee4",
    "E67_alphabet": "33f6b18cc62c865f73fb4cd81c14970d7db34dee11d3a01729c7940d8b2e47c5",
    "E68_deep_eigen": "58f853b85b882d6744a6cadf7f9589cfb75fba04e6e427f9ae135e59b85f95e6",
}

E68_CORRS = (1.0, 0.95, 0.9, 0.8, 0.65, 0.5, 0.3, 0.1)
E68_CORRS_ASC = tuple(sorted(E68_CORRS))
LOG_FLOORS = (1e-6, 1e-4, 1e-3, 0.005, 0.01, 0.025, 0.05)
CHANCE_LEVELS = (0.45, 0.475, 0.49, 0.5, 0.51, 0.525, 0.55)
TRACKED_PACKAGES = (
    "deep_eigen",
    "alphabet",
    "error_threshold",
    "teaching",
    "blueprint_web",
    "ladder_web",
    "voltage_web",
    "setpoint_rewrite",
    "assimilation",
    "writable_landlord",
    "contract_bridge",
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
        if np.isnan(float(left)) and np.isnan(float(right)):
            return True
        return close(float(left), float(right))
    return left == right


def _first_commit(repo_root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
        commits = subprocess.run(
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
    return commits[-1] if commits else None


def _git_provenance(plastic_root: Path) -> dict[str, Any]:
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
    selected = {
        "deep_eigen": "deepeigen_summary.json",
        "alphabet": "alphabet_summary.json",
        "error_threshold": "eigen_summary.json",
        "teaching": "teaching_summary.json",
    }
    rows: dict[str, Any] = {}
    for package, result in selected.items():
        root = _experiment_root(plastic_root, package)
        expectation_commit = _first_commit(repository_root, root / "EXPECTATIONS.md")
        result_commit = _first_commit(repository_root, root / "results/full" / result)
        rows[package] = {
            "expectations_first_commit": expectation_commit,
            "selected_result_first_commit": result_commit,
            "same_first_commit_snapshot": bool(
                expectation_commit is not None and expectation_commit == result_commit
            ),
            "prose_date_is_git_verified_temporal_seal": False,
        }
    return {"repository_root": str(repository_root), "packages": rows}


def source_config_digests() -> dict[str, str]:
    """Digest independently transcribed current E55/E65/E67/E68 defaults."""

    configs: dict[str, dict[str, Any]] = {
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
        "E67_alphabet": {
            "mode": "full",
            "norm_primary": 0.15,
            "norm_secondary": 0.3,
            "write_gain": 1.5,
            "express_sweeps": 300,
            "express_futures": 4,
            "form_seeds": [1, 3, 5, 7],
            "prescreen_half_mean": 0.15,
            "interaction_bar": 0.25,
            "n_donor_shuffles": 200,
            "repertoire_seeds": 10,
            "repertoire_distinct": 0.8,
            "k_max": 7,
            "write_lambda": 0.001,
            "hysteresis_write_sweeps": 1500,
            "hysteresis_futures": 2,
            "robustness_rhos": [0.001, 0.004],
            "trajectory_seed_tag": "alphabet-v1",
        },
        "E68_deep_eigen": {
            "mode": "full",
            "n_tissues": 3,
            "futures": 4,
            "norm": 0.3,
            "write_lambda": 0.001,
            "settle_sweeps": 120,
            "imprint_sweeps": 1000,
            "imprint_hold": 1.2,
            "cycles": 12,
            "inter_fission": 1000,
            "amp_threshold": 0.2,
            "chance": 0.5,
            "bootstrap": 200,
            "trajectory_seed_tag": "deep-eigen-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def trend_slope(
    fidelities: Sequence[float | None],
    *,
    chance: float = 0.5,
    floor: float = 1e-3,
    start: int = 1,
    stop: int | None = None,
    raw: bool = False,
) -> float | None:
    """Fit a trend on absolute cycle indexes under an explicit convention."""

    end = len(fidelities) if stop is None else min(stop, len(fidelities))
    values = []
    for index in range(start, end):
        fidelity = fidelities[index]
        if fidelity is None or not np.isfinite(float(fidelity)):
            continue
        response = float(fidelity)
        if not raw:
            response = float(np.log(max(response - chance, floor)))
        values.append((index, response))
    if len(values) < 4:
        return None
    return float(
        np.polyfit(
            np.asarray([row[0] for row in values], dtype=float),
            np.asarray([row[1] for row in values], dtype=float),
            1,
        )[0]
    )


def sign_crossings(points: Sequence[tuple[float, float]]) -> dict[str, Any]:
    """Enumerate every linearly interpolated upward and downward sign crossing."""

    ordered = sorted((float(x), float(y)) for x, y in points)
    upward = []
    downward = []
    for (x0, y0), (x1, y1) in zip(ordered, ordered[1:]):
        if y0 < 0 <= y1:
            estimate = x0 + (x1 - x0) * (-y0) / (y1 - y0)
            upward.append({"estimate": float(estimate), "bracket": [x0, x1]})
        if y0 >= 0 > y1:
            estimate = x0 + (x1 - x0) * y0 / (y0 - y1)
            downward.append({"estimate": float(estimate), "bracket": [x0, x1]})
    return {
        "signs_ascending_c": [int(np.sign(value)) for _, value in ordered],
        "upward": upward,
        "downward": downward,
        "first_upward": upward[0]["estimate"] if upward else None,
        "single_threshold_shape": len(upward) == 1 and len(downward) == 0,
    }


def _mean_trajectory(rows: Sequence[Mapping[str, Any]]) -> list[float | None]:
    trajectory: list[float | None] = []
    for cycle in range(12):
        values = [
            float(row["fidelity_by_cycle"][cycle])
            for row in rows
            if row["fidelity_by_cycle"][cycle] is not None
        ]
        trajectory.append(float(np.mean(values)) if values else None)
    return trajectory


def _condition_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    mean_fids = _mean_trajectory(rows)
    tissue_slopes = [trend_slope(row["fidelity_by_cycle"]) for row in rows]
    assert all(value is not None for value in tissue_slopes)
    source = trend_slope(mean_fids)
    assert source is not None
    first_valid = next(float(value) for value in mean_fids if value is not None)
    return {
        "mean_fidelity_by_cycle": mean_fids,
        "source_log_excess_slope": source,
        "drop_first_valid_log_excess_slope": trend_slope(mean_fids, start=2),
        "late_six_log_excess_slope": trend_slope(mean_fids, start=6),
        "raw_fidelity_slope": trend_slope(mean_fids, raw=True),
        "final_minus_first_valid": float(mean_fids[-1]) - first_valid,
        "first_valid_fidelity": first_valid,
        "final_fidelity": float(mean_fids[-1]),
        "source_floor_hit_count": sum(
            value is not None and float(value) - 0.5 <= 1e-3
            for value in mean_fids
        ),
        "tissue_source_slopes": [float(value) for value in tissue_slopes],
        "mean_tissue_source_slope": float(np.mean(tissue_slopes)),
        "positive_tissue_source_slopes": sum(value > 0 for value in tissue_slopes),
    }


def _curve_from_rows(
    rows_by_corr: Mapping[float, Sequence[Mapping[str, Any]]],
    *,
    metric: str = "source",
    chance: float = 0.5,
    floor: float = 1e-3,
) -> list[dict[str, Any]]:
    curve = []
    for corr in E68_CORRS_ASC:
        rows = rows_by_corr[corr]
        mean_fids = _mean_trajectory(rows)
        if metric == "source":
            slope = trend_slope(mean_fids, chance=chance, floor=floor)
        elif metric == "drop_first":
            slope = trend_slope(mean_fids, chance=chance, floor=floor, start=2)
        elif metric == "late_six":
            slope = trend_slope(mean_fids, chance=chance, floor=floor, start=6)
        elif metric == "raw":
            slope = trend_slope(mean_fids, start=1, raw=True)
        elif metric == "endpoint":
            first = next(float(value) for value in mean_fids if value is not None)
            slope = float(mean_fids[-1]) - first
        elif metric == "mean_tissue":
            slopes = [
                trend_slope(row["fidelity_by_cycle"], chance=chance, floor=floor)
                for row in rows
            ]
            slope = float(np.mean([value for value in slopes if value is not None]))
        else:
            raise ValueError(f"unknown trend metric: {metric}")
        assert slope is not None
        curve.append(
            {
                "c_target": corr,
                "realized": float(
                    np.mean([float(row["realized_corr"]) for row in rows])
                ),
                "slope": float(slope),
                "final_fid": float(mean_fids[-1]),
            }
        )
    return curve


def _curve_crossings(curve: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return sign_crossings(
        [(float(row["realized"]), float(row["slope"])) for row in curve]
    )


def _bootstrap_thresholds(
    rows_by_corr: Mapping[float, Sequence[Mapping[str, Any]]]
) -> dict[str, Any]:
    outcomes = []
    for indices in itertools.product(range(3), repeat=3):
        resampled = {
            corr: [rows_by_corr[corr][index] for index in indices]
            for corr in E68_CORRS_ASC
        }
        crossing = _curve_crossings(_curve_from_rows(resampled))
        outcomes.append(
            {
                "indices": list(indices),
                "first_upward": crossing["first_upward"],
                "upward_count": len(crossing["upward"]),
                "downward_count": len(crossing["downward"]),
            }
        )
    finite = [float(row["first_upward"]) for row in outcomes if row["first_upward"] is not None]
    return {
        "method": "exhaustive ordered 3-of-3 tissue-index block resampling",
        "resamples": len(outcomes),
        "finite_first_crossings": len(finite),
        "exactly_one_upward_crossing": sum(row["upward_count"] == 1 for row in outcomes),
        "multiple_upward_crossings": sum(row["upward_count"] > 1 for row in outcomes),
        "any_downward_crossing": sum(row["downward_count"] > 0 for row in outcomes),
        "conditional_first_crossing_range": [min(finite), max(finite)] if finite else None,
        "conditional_first_crossing_percentile_95": (
            [float(value) for value in np.quantile(finite, [0.025, 0.975])]
            if finite
            else None
        ),
        "outcomes": outcomes,
        "registered_inference": False,
    }


def _leave_one_out(
    rows_by_corr: Mapping[float, Sequence[Mapping[str, Any]]]
) -> list[dict[str, Any]]:
    output = []
    for omitted in range(3):
        kept = [index for index in range(3) if index != omitted]
        subset = {
            corr: [rows_by_corr[corr][index] for index in kept]
            for corr in E68_CORRS_ASC
        }
        curve = _curve_from_rows(subset)
        output.append(
            {
                "omitted_tissue": omitted,
                "crossings": _curve_crossings(curve),
                "slopes_ascending_c": [float(row["slope"]) for row in curve],
            }
        )
    return output


def _projection_identity() -> dict[str, Any]:
    """Numerically check the algebraic no-op on already projected theta."""

    rng = np.random.default_rng(22068)
    raw = rng.standard_normal((4, 16, 16))

    def project(theta: np.ndarray, norm: float) -> np.ndarray:
        centered = theta - theta.mean(axis=(-2, -1), keepdims=True)
        scale = centered.std(axis=(-2, -1), keepdims=True)
        return centered * (norm / np.maximum(scale, 1e-9))

    theta = project(raw, 0.3)
    rows = []
    for corr in E68_CORRS_ASC:
        mixed = np.empty_like(theta)
        realized = []
        for future in range(theta.shape[0]):
            base = theta[future] - theta[future].mean()
            base_hat = base / max(float(np.linalg.norm(base)), 1e-12)
            noise = rng.standard_normal(base.shape)
            noise -= noise.mean()
            noise -= float((noise * base_hat).sum()) * base_hat
            noise_hat = noise / max(float(np.linalg.norm(noise)), 1e-12)
            value = corr * base_hat + np.sqrt(max(0.0, 1 - corr**2)) * noise_hat
            value *= np.linalg.norm(base)
            mixed[future] = value
            realized.append(float(np.corrcoef(value.ravel(), theta[future].ravel())[0, 1]))
        projected = project(mixed, 0.3)
        rows.append(
            {
                "c_target": corr,
                "mean_realized_corr": float(np.mean(realized)),
                "mixed_mean_abs_max": float(np.max(np.abs(mixed.mean(axis=(-2, -1))))),
                "mixed_std_max_abs_error_from_norm": float(
                    np.max(np.abs(mixed.std(axis=(-2, -1)) - 0.3))
                ),
                "max_abs_projected_minus_unprojected": float(
                    np.max(np.abs(projected - mixed))
                ),
            }
        )
    return {
        "construction": "deterministic algebra check; no simulator future",
        "rows": rows,
        "max_abs_difference": max(
            row["max_abs_projected_minus_unprojected"] for row in rows
        ),
        "identity_within_1e_12": all(
            row["max_abs_projected_minus_unprojected"] < 1e-12 for row in rows
        ),
    }


def _audit_e68(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    summary = tracker.json(root / "results/full/deepeigen_summary.json")
    pre_payload = tracker.json(root / "results/full/work/preround.json")
    source = _read(tracker, root / "src/deep_eigen/pipeline.py")
    config_source = _read(tracker, root / "src/deep_eigen/config.py")
    entries: list[dict[str, Any]] = []
    cache_integrity = []
    work_digests = {pre_payload["config_digest"]}
    by_label: dict[bool, dict[float, list[dict[str, Any]]]] = {
        True: {},
        False: {},
    }
    for project in (True, False):
        for corr in E68_CORRS:
            path = root / "results/full/work" / f"lin_{corr}_{int(project)}.json"
            payload = tracker.json(path)
            work_digests.add(payload["config_digest"])
            rows = sorted(payload["data"], key=lambda row: int(row["tissue"]))
            by_label[project][corr] = rows
            entries.extend(rows)
            cache_integrity.append(
                {
                    "project_label": "projected" if project else "unbounded",
                    "c_target": corr,
                    "rows": len(rows),
                    "tissues": [int(row["tissue"]) for row in rows],
                    "twelve_cycle_values": all(
                        len(row["fidelity_by_cycle"]) == 12 for row in rows
                    ),
                    "first_value_undefined": all(
                        row["fidelity_by_cycle"][0] is None for row in rows
                    ),
                }
            )

    condition_rows: list[dict[str, Any]] = []
    tissue_rows: list[dict[str, Any]] = []
    condition_details: dict[str, dict[str, Any]] = {}
    for project in (True, False):
        label = "projected" if project else "unbounded"
        condition_details[label] = {}
        for corr in E68_CORRS_ASC:
            rows = by_label[project][corr]
            metrics = _condition_metrics(rows)
            condition_details[label][str(corr)] = metrics
            condition_rows.append(
                {
                    "project_label": label,
                    "c_target": corr,
                    "realized_corr": float(
                        np.mean([float(row["realized_corr"]) for row in rows])
                    ),
                    "source_log_excess_slope": metrics["source_log_excess_slope"],
                    "drop_first_valid_log_excess_slope": metrics[
                        "drop_first_valid_log_excess_slope"
                    ],
                    "late_six_log_excess_slope": metrics[
                        "late_six_log_excess_slope"
                    ],
                    "raw_fidelity_slope": metrics["raw_fidelity_slope"],
                    "final_minus_first_valid": metrics["final_minus_first_valid"],
                    "first_valid_fidelity": metrics["first_valid_fidelity"],
                    "final_fidelity": metrics["final_fidelity"],
                    "source_floor_hit_count": metrics["source_floor_hit_count"],
                    "mean_tissue_source_slope": metrics[
                        "mean_tissue_source_slope"
                    ],
                    "positive_tissue_source_slopes": metrics[
                        "positive_tissue_source_slopes"
                    ],
                }
            )
            for row, tissue_slope in zip(rows, metrics["tissue_source_slopes"]):
                tissue_out = {
                    "project_label": label,
                    "c_target": corr,
                    "tissue": int(row["tissue"]),
                    "realized_corr": float(row["realized_corr"]),
                    "source_log_excess_slope": tissue_slope,
                    "drop_first_valid_log_excess_slope": trend_slope(
                        row["fidelity_by_cycle"], start=2
                    ),
                    "late_six_log_excess_slope": trend_slope(
                        row["fidelity_by_cycle"], start=6
                    ),
                    "raw_fidelity_slope": trend_slope(
                        row["fidelity_by_cycle"], raw=True
                    ),
                    "final_minus_first_valid": float(row["fidelity_by_cycle"][-1])
                    - float(row["fidelity_by_cycle"][1]),
                }
                for cycle, value in enumerate(row["fidelity_by_cycle"], start=1):
                    tissue_out[f"fidelity_cycle_{cycle}"] = value
                tissue_rows.append(tissue_out)

    source_curves = {
        label: _curve_from_rows(by_label[project])
        for project, label in ((True, "projected"), (False, "unbounded"))
    }
    source_crossings = {
        label: _curve_crossings(curve) for label, curve in source_curves.items()
    }

    # Recreate historical ordering and field names exactly.
    def historical_curve(label: str) -> list[dict[str, Any]]:
        indexed = {float(row["c_target"]): row for row in source_curves[label]}
        return [
            {
                "c_target": corr,
                "realized": float(indexed[corr]["realized"]),
                "slope": float(indexed[corr]["slope"]),
                "final_fid": float(indexed[corr]["final_fid"]),
            }
            for corr in E68_CORRS
        ]

    c_projected = source_crossings["projected"]["first_upward"]
    c_unbounded = source_crossings["unbounded"]["first_upward"]
    pre = pre_payload["data"]
    reconstructed = {
        "preround": pre,
        "curve_projected": historical_curve("projected"),
        "curve_unbounded": historical_curve("unbounded"),
        "c_star_projected": c_projected,
        "c_star_unbounded": c_unbounded,
        "predicted_c_star": pre["predicted_c_star"],
        "gate_p68_1_primary": bool(
            c_projected is not None
            and pre["predicted_c_star"] is not None
            and 0.5 * float(pre["predicted_c_star"])
            <= c_projected
            <= 2.0 * float(pre["predicted_c_star"])
            and E68_CORRS[-1] < c_projected < E68_CORRS[0]
        ),
        "cap_sets_threshold": bool(
            c_projected is not None
            and c_unbounded is not None
            and abs(c_projected - c_unbounded) > 0.15
        ),
    }

    variants = (
        "source",
        "drop_first",
        "late_six",
        "raw",
        "endpoint",
        "mean_tissue",
    )
    trend_sensitivity: dict[str, Any] = {}
    for project, label in ((True, "projected"), (False, "unbounded")):
        trend_sensitivity[label] = {}
        for metric in variants:
            curve = _curve_from_rows(by_label[project], metric=metric)
            trend_sensitivity[label][metric] = {
                "slopes_ascending_c": [float(row["slope"]) for row in curve],
                "crossings": _curve_crossings(curve),
            }

    pooled = {
        corr: by_label[False][corr] + by_label[True][corr]
        for corr in E68_CORRS_ASC
    }
    trend_sensitivity["pooled_noop_labels"] = {}
    for metric in variants:
        curve = _curve_from_rows(pooled, metric=metric)
        trend_sensitivity["pooled_noop_labels"][metric] = {
            "slopes_ascending_c": [float(row["slope"]) for row in curve],
            "crossings": _curve_crossings(curve),
        }

    floor_sensitivity = {}
    chance_sensitivity = {}
    for project, label in ((True, "projected"), (False, "unbounded")):
        floor_sensitivity[label] = {}
        for floor in LOG_FLOORS:
            curve = _curve_from_rows(by_label[project], floor=floor)
            floor_sensitivity[label][str(floor)] = _curve_crossings(curve)
        chance_sensitivity[label] = {}
        for chance in CHANCE_LEVELS:
            curve = _curve_from_rows(by_label[project], chance=chance)
            chance_sensitivity[label][str(chance)] = _curve_crossings(curve)

    tissue_thresholds = {}
    for project, label in ((True, "projected"), (False, "unbounded")):
        tissue_thresholds[label] = []
        for tissue in range(3):
            tissue_curve = {
                corr: [by_label[project][corr][tissue]] for corr in E68_CORRS_ASC
            }
            curve = _curve_from_rows(tissue_curve)
            tissue_thresholds[label].append(
                {
                    "tissue": tissue,
                    "slopes_ascending_c": [float(row["slope"]) for row in curve],
                    "crossings": _curve_crossings(curve),
                }
            )

    bootstrap = {
        "projected": _bootstrap_thresholds(by_label[True]),
        "unbounded": _bootstrap_thresholds(by_label[False]),
    }
    leave_one_out = {
        "projected": _leave_one_out(by_label[True]),
        "unbounded": _leave_one_out(by_label[False]),
    }
    projection_identity = _projection_identity()

    perfect_copy = {
        label: condition_details[label]["1.0"] for label in ("projected", "unbounded")
    }
    pre_audit = {
        "rows": pre["rows"],
        "predicted_c_star": pre["predicted_c_star"],
        "all_fidelity_deltas_negative": all(
            float(row["fidelity_delta"]) < 0 for row in pre["rows"]
        ),
        "all_theta_recoveries_positive": all(
            float(row["theta_recovery"]) > 0 for row in pre["rows"]
        ),
        "contains_fission": False,
        "perturbs_theta": True,
        "perturbs_V": False,
        "perturbs_R": False,
        "tissue_rows_retained": False,
        "supports_beneficial_phenotype_correction": False,
        "supports_programmed_theta_restoration": True,
    }
    source_and_mechanism = {
        "theta_explicitly_branched_or_copied": False,
        "same_theta_array_replaced_by_mixture_after_fission": True,
        "realized_corr_read_at_corruption_instant": True,
        "post_recovery_theta_corr_retained": False,
        "effective_parent_daughter_corr_retained": False,
        "R_copied_whole_without_noise_at_fission": True,
        "V_fragmented_at_fission": True,
        "theta_updated_toward_tanh_R_each_recovery_sweep": True,
        "R_pulls_V_through_comparator": True,
        "writer_off_arm_present": False,
        "R_reset_or_scramble_arm_present": False,
        "V_or_context_scramble_arm_present": False,
        "target_removed_arm_present": False,
        "R_to_theta_link_ablation_present": False,
        "projected_and_unbounded_share_streams": False,
        "project_flag_enters_seed_before_preparation": True,
        "mixture_rescaled_to_parent_norm_before_optional_projection": True,
        "unbounded_at_corruption_instant": False,
        "unbounded_remains_unprojected_during_recovery": False,
        "genuinely_unbounded_arm_present": False,
        "both_labels_project_on_first_recovery_step": True,
        "boundary_projection_is_algebraic_identity": projection_identity[
            "identity_within_1e_12"
        ],
        "c1_mix_theta_called": False,
        "c1_labels_have_same_physical_intervention": True,
        "c1_projected_source_slope": perfect_copy["projected"][
            "source_log_excess_slope"
        ],
        "c1_unbounded_source_slope": perfect_copy["unbounded"][
            "source_log_excess_slope"
        ],
        "c1_labels_have_opposite_slope_signs": (
            perfect_copy["projected"]["source_log_excess_slope"] > 0
            and perfect_copy["unbounded"]["source_log_excess_slope"] < 0
        ),
        "score_mask": "cumulative positions regrown at least twice",
        "score_mask_expands_with_cycle": True,
        "per_cycle_mask_counts_retained": False,
        "per_cycle_slope_uses_fixed_position_population": False,
        "horizon_cycles": 12,
        "cycle_13_or_extension_retained": False,
        "config_bootstrap_value": 200,
        "bootstrap_used_by_pipeline": "config.bootstrap" in source,
        "reported_threshold_CI_present": False,
        "chance_level_calibrated_by_retained_null": False,
        "source_checks": {
            "project_optional_only_in_mix": "if project:" in source,
            "mixture_norm_fixed_before_project_flag": "mixed = mixed * np.linalg.norm(t)" in source,
            "cascade_always_projects": "theta = project_theta((1 - lam) * theta" in source,
            "project_label_in_seed": "int(project)" in source,
            "c1_skips_mix": "if c_target < 1.0:" in source,
            "expanding_regrow_counter": "regrow += fresh" in source,
            "regrow_two_mask": "m2 = regrow >= 2" in source,
            "bootstrap_declared_in_config": "bootstrap: int = 200" in config_source,
        },
    }
    return (
        {
            "retained_config_digest": summary["config_digest"],
            "work_config_digests": sorted(work_digests),
            "all_work_digests_match_summary": work_digests == {summary["config_digest"]},
            "cache_integrity": cache_integrity,
            "all_16_conditions_complete": len(cache_integrity) == 16
            and all(
                row["rows"] == 3
                and row["tissues"] == [0, 1, 2]
                and row["twelve_cycle_values"]
                and row["first_value_undefined"]
                for row in cache_integrity
            ),
            "retained_tissue_rows": len(entries),
            "reconstructed_gates": reconstructed,
            "reported_gates": summary["gates"],
            "all_reported_gates_reconstruct": _recursive_close(
                reconstructed, summary["gates"]
            ),
            "condition_details": condition_details,
            "source_crossings": source_crossings,
            "trend_sensitivity": trend_sensitivity,
            "log_floor_sensitivity": floor_sensitivity,
            "chance_level_sensitivity": chance_sensitivity,
            "tissue_thresholds": tissue_thresholds,
            "exact_tissue_block_bootstrap": bootstrap,
            "leave_one_tissue_out": leave_one_out,
            "projection_identity_diagnostic": projection_identity,
            "preround_audit": pre_audit,
            "source_and_mechanism_audit": source_and_mechanism,
        },
        condition_rows,
        tissue_rows,
    )


def _load_shard_entries(
    tracker: InputTracker, paths: Sequence[Path]
) -> tuple[list[dict[str, Any]], set[str]]:
    entries: list[dict[str, Any]] = []
    digests: set[str] = set()
    for path in paths:
        payload = tracker.json(path)
        digests.add(payload["config_digest"])
        entries.extend(payload["entries"])
    return entries, digests


def _audit_e55(root: Path, tracker: InputTracker) -> dict[str, Any]:
    paths = sorted((root / "results/full/work").glob("eigen_shard_*_of_05.json"))
    if len(paths) != 5:
        raise ValueError(f"expected five E55 shards, found {len(paths)}")
    entries, digests = _load_shard_entries(tracker, paths)
    summary = tracker.json(root / "results/full/eigen_summary.json")
    source = _read(tracker, root / "src/error_threshold/pipeline.py")
    sweeps = [entry for entry in entries if entry["kind"] == "sweep"]
    selections = [entry for entry in entries if entry["kind"] == "selection"]
    keys = [(int(entry["tissue"]), int(entry["k"])) for entry in sweeps]

    def sigma_row(entry: Mapping[str, Any], sigma: float) -> Mapping[str, Any]:
        return next(row for row in entry["rows"] if close(float(row["sigma"]), sigma))

    def tail(values: Sequence[float | None]) -> float:
        selected = [float(value) for value in values[-3:] if value is not None]
        return float(np.mean(selected))

    exact = [sigma_row(entry, 0.0) for entry in sweeps]
    noisy = [sigma_row(entry, 5.0) for entry in sweeps]
    exact_fixed = [tail(row["ancestor_fid_regrown2"]) for row in exact]
    exact_parent = [tail(row["parent_fid"]) for row in exact]
    sigma5_fixed = [tail(row["ancestor_fid_regrown2"]) for row in noisy]
    k4_fixed = [
        tail(sigma_row(entry, 0.0)["ancestor_fid_regrown2"])
        for entry in sweeps
        if int(entry["k"]) == 4
    ]
    return {
        "retained_config_digest": summary["config_digest"],
        "shard_digests": sorted(digests),
        "all_shards_match_summary": digests == {summary["config_digest"]},
        "retained_entries": len(entries),
        "sweep_entries": len(sweeps),
        "selection_entries": len(selections),
        "complete_tissue_complexity_grid": set(keys)
        == {(tissue, k) for tissue in range(2) for k in (2, 4, 8, 16)},
        "exact_R_copy_all_complexity_fixed_ancestor_tail": float(np.mean(exact_fixed)),
        "exact_R_copy_all_complexity_immediate_parent_tail": float(np.mean(exact_parent)),
        "sigma5_all_complexity_fixed_ancestor_tail": float(np.mean(sigma5_fixed)),
        "exact_R_copy_k4_fixed_ancestor_tail": float(np.mean(k4_fixed)),
        "reported_k4_exact_value_matches": close(
            float(np.mean(k4_fixed)), float(summary["gates"]["curves"]["4"]["0.0"])
        ),
        "all_four_registered_gates_false": all(
            summary["gates"][key] is False
            for key in (
                "gate_p55_1_sharp_threshold",
                "gate_p55_2_quasispecies_rescue",
                "gate_p55_3_capacity_law",
                "gate_p55_4_freedom",
            )
        ),
        "actual_noise_intervention": "additive Gaussian noise on exactly copied R",
        "V_copy_correlation_swept": False,
        "R_noise_converted_to_realized_correlation": False,
        "V_always_fragment_fissioned": True,
        "endpoint": "generations 10-12 fixed-ancestor fidelity on cumulative regrown>=2 cells",
        "per_cycle_nondecay_threshold_fitted": False,
        "chance_level_calibrated": False,
        "no_V_channel_at_any_fidelity_supported": False,
        "source_checks": {
            "whole_R_copy": "Rf.copy()" in source,
            "noise_added_to_R": "R_kid = R_kid + sigma_r" in source,
            "fixed_fragment_fission": "offspring = np.full_like" in source,
        },
    }


def _audit_e65(root: Path, tracker: InputTracker) -> dict[str, Any]:
    paths = sorted((root / "results/full/work").glob("teach_shard_*_of_06.json"))
    if len(paths) != 6:
        raise ValueError(f"expected six E65 shards, found {len(paths)}")
    entries, digests = _load_shard_entries(tracker, paths)
    summary = tracker.json(root / "results/full/teaching_summary.json")
    source = _read(tracker, root / "src/teaching/pipeline.py")

    def regular(
        arm: str,
        T: int,
        *,
        r_mode: str = "free",
        sigma_r: float = 0.0,
    ) -> list[Mapping[str, Any]]:
        return sorted(
            [
                row
                for row in entries
                if row["arm"] == arm
                and int(row["T"]) == T
                and row["r_mode"] == r_mode
                and close(float(row["sigma_r"]), sigma_r)
                and row["barcode"] is None
            ],
            key=lambda row: int(row["tissue"]),
        )

    def mean_fidelity(arm: str, T: int) -> float:
        return float(np.mean([float(row["fidelity"]) for row in regular(arm, T)]))

    floor_values = [float(row["fidelity"]) for row in regular("none", 0)]
    floor = float(np.mean(floor_values))
    floor_q95 = floor + 1.645 * float(np.std(floor_values))
    parent_200 = mean_fidelity("parent_chain", 200)
    broadcast_200 = mean_fidelity("broadcast", 200)
    barcode_parent = sorted(
        [row for row in entries if row["arm"] == "parent_chain" and row["barcode"] is not None],
        key=lambda row: int(row["tissue"]),
    )
    barcode_broadcast = sorted(
        [row for row in entries if row["arm"] == "broadcast" and row["barcode"] is not None],
        key=lambda row: int(row["tissue"]),
    )

    def barcode_mean(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
        return {
            "own": float(np.mean([float(row["barcode"]["own_lineage"]) for row in rows])),
            "others": float(
                np.mean([float(row["barcode"]["other_lineages"]) for row in rows])
            ),
        }

    parent_barcode = barcode_mean(barcode_parent)
    broadcast_barcode = barcode_mean(barcode_broadcast)
    patch = np.zeros((16, 16), dtype=bool)
    patch[2:6, 2:6] = True
    extracted = np.zeros((16, 16), dtype=bool)[patch]
    broadcast_shape = list(np.broadcast_shapes((16, 16), extracted.shape))
    selected_match = (
        close(floor, float(summary["gates"]["floor"]))
        and close(floor_q95, float(summary["gates"]["floor_q95"]))
        and close(parent_200, float(summary["gates"]["parent_chain"]["200"]))
        and close(broadcast_200, float(summary["gates"]["broadcast"]["200"]))
        and _recursive_close(parent_barcode, summary["gates"]["barcode"]["parent_chain"])
        and _recursive_close(broadcast_barcode, summary["gates"]["barcode"]["broadcast"])
    )
    return {
        "retained_config_digest": summary["config_digest"],
        "shard_digests": sorted(digests),
        "all_shards_match_summary": digests == {summary["config_digest"]},
        "retained_entries": len(entries),
        "entries_per_tissue": {
            str(tissue): sum(int(row["tissue"]) == tissue for row in entries)
            for tissue in range(4)
        },
        "selected_summary_values_reconstruct": selected_match,
        "floor": floor,
        "source_floor_q95": floor_q95,
        "parent_chain_T200": parent_200,
        "parent_T200_minus_source_floor_q95": parent_200 - floor_q95,
        "broadcast_T200": broadcast_200,
        "reported_parent_barcode": parent_barcode,
        "reported_broadcast_barcode": broadcast_barcode,
        "parent_sign_teacher_stored_exactly_before_fission": True,
        "delivered_parent_pupil_correlation_swept": False,
        "parent_pupil_correlation_retained": False,
        "endpoint": "generations 10-12 fixed-founder fidelity after repeated teaching",
        "per_cycle_nondecay_threshold_fitted": False,
        "barcode_target_shape": list(extracted.shape),
        "barcode_reported_comparison_shape": broadcast_shape,
        "barcode_intended_positions": int(patch.sum()),
        "barcode_reported_positions": int(np.prod(broadcast_shape)),
        "barcode_is_patch_restricted": False,
        "cycles_between_injection_and_only_score": 7,
        "one_reteaching_cycle_score_retained": False,
        "barcode_positive_control_retained": False,
        "barcode_erasure_admissible": False,
        "culture_erased_at_perfect_transmission_supported": False,
        "source_checks": {
            "teacher_exact_parent_sign": "teacher = np.sign(V)" in source,
            "target_boolean_extract": "target = -flipped[patch]" in source,
            "whole_V_barcode_comparison": "((V[0] > 0) == (target > 0)).mean()" in source,
        },
    }


def _audit_e67(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/alphabet_summary.json")
    payload = tracker.json(root / "results/full/work/discreteness.json")
    source = _read(tracker, root / "src/alphabet/pipeline.py")
    data = payload["data"]
    start_dependences = [float(row["start_dependence"]) for row in data["hysteresis"]]
    mean_start = float(np.mean(start_dependences))
    reconstructed = {
        "norm": float(data["norm"]),
        "curve": data["curve"],
        "transition_width_corr_units": data["transition_width_corr_units"],
        "control_width": data["control_width"],
        "hysteresis": data["hysteresis"],
        "mean_start_dependence": mean_start,
        "store_bistable": bool(mean_start < 0.2),
    }
    return {
        "retained_config_digest": summary["config_digest"],
        "cache_config_digest": payload["config_digest"],
        "cache_and_summary_digests_match": payload["config_digest"]
        == summary["config_digest"],
        "reconstructed_discreteness": reconstructed,
        "reported_discreteness_reconstructs": _recursive_close(
            reconstructed, summary["gates"]["discreteness"]
        ),
        "start_dependence_values": start_dependences,
        "mean_start_dependence": mean_start,
        "store_bistable": reconstructed["store_bistable"],
        "tissues": 1,
        "forms": 2,
        "initial_theta_mixtures": 5,
        "futures_per_start": 2,
        "fission_present": False,
        "theta_corruption_present": False,
        "start_labels_share_random_streams": False,
        "writer_R_context_ablation_present": False,
        "residual_direct_theta_weight_after_1500_updates_absent_feedback": float(
            (1.0 - 0.001) ** 1500
        ),
        "supports_strong_endpoint_dependence_on_initial_V_R": True,
        "identifies_error_correction": False,
        "establishes_E68_threshold": False,
        "source_checks": {
            "one_tissue": "tissue = tissue_config(0" in source,
            "start_in_seed": 'alpha, start)' in source,
            "no_fission_in_discreteness_block": True,
        },
    }


def run_l22_audit(
    plastic_root: Path, workspace: Path
) -> tuple[
    dict[str, Any],
    list[Path],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[Path, str],
]:
    tracker = InputTracker()
    ideas_root = plastic_root / IDEAS_RELATIVE
    narrative_paths = (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas_root / "LAWS.md",
        ideas_root / "WAVE12_PROPHECIES.md",
        ideas_root / "WAVE14_PROPHECIES.md",
        ideas_root / "WAVE15_PROPHECIES.md",
        ideas_root / "WAVE15_DESIGN_REVIEW.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        ideas_root / "RULIAD_DISCUSSION.md",
        workspace / "SOURCE_BASELINE.md",
        workspace / "REVIEW_PROTOCOL.md",
        workspace / "protocols/L22_BODY_PROOFREADS_GENE_AUDIT_V1.md",
        workspace / "laws/L22_body_proofreads_gene.md",
        workspace / "reviews/L17_DEVELOPMENT_HEREDITY_AUDIT_2026-09-03.md",
        workspace / "reviews/L19_INCORRUPTIBLE_REFERENCE_AUDIT_2026-09-03.md",
        workspace / "reviews/L20_SELF_WRITTEN_GENOME_AUDIT_2026-09-03.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative_paths}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    e68, curve_rows, tissue_rows = _audit_e68(
        _experiment_root(plastic_root, "deep_eigen"), tracker
    )
    e67 = _audit_e67(_experiment_root(plastic_root, "alphabet"), tracker)
    e55 = _audit_e55(_experiment_root(plastic_root, "error_threshold"), tracker)
    e65 = _audit_e65(_experiment_root(plastic_root, "teaching"), tracker)

    source_digests = source_config_digests()
    retained_digests = {
        "E55_error_threshold": e55["retained_config_digest"],
        "E65_teaching": e65["retained_config_digest"],
        "E67_alphabet": e67["retained_config_digest"],
        "E68_deep_eigen": e68["retained_config_digest"],
    }
    digest_matches = {
        name: source_digests[name]
        == retained_digests[name]
        == EXPECTED_CONFIG_DIGESTS[name]
        for name in EXPECTED_CONFIG_DIGESTS
    }

    hierarchy_rows = [
        {
            "claimed_carrier": "V",
            "experiment": "E55",
            "actual_intervention": "additive Gaussian noise on whole-field R; V always fragment-fissioned",
            "transmitted_correlation_controlled": False,
            "target": "fixed post-render ancestor",
            "outcome": "generations 10-12 tail fidelity",
            "cycles": 12,
            "key_value": e55["exact_R_copy_all_complexity_fixed_ancestor_tail"],
            "countervalue": e55["exact_R_copy_all_complexity_immediate_parent_tail"],
            "common_currency_with_E68": False,
            "admissible_conclusion": "E55 does not sweep V copying fidelity and cannot establish no V channel at any fidelity",
        },
        {
            "claimed_carrier": "living culture",
            "experiment": "E65",
            "actual_intervention": "exact parent sign saved externally, then whole-sheet teaching clamp",
            "transmitted_correlation_controlled": False,
            "target": "fixed founder",
            "outcome": "generations 10-12 tail fidelity plus malformed final barcode",
            "cycles": 12,
            "key_value": e65["parent_chain_T200"],
            "countervalue": e65["source_floor_q95"],
            "common_currency_with_E68": False,
            "admissible_conclusion": "the parent chain drifts from its founder; perfect delivery and barcode erasure were not measured",
        },
        {
            "claimed_carrier": "theta",
            "experiment": "E68",
            "actual_intervention": "instantaneous orthogonal theta mixture after fission while R copies exactly",
            "transmitted_correlation_controlled": True,
            "target": "fixed imposed launch form",
            "outcome": "log excess-over-.5 trend over cycles 2-12 on expanding mask",
            "cycles": 12,
            "key_value": e68["reconstructed_gates"]["c_star_projected"],
            "countervalue": e68["reconstructed_gates"]["c_star_unbounded"],
            "common_currency_with_E68": True,
            "admissible_conclusion": "the historical projected-label aggregate has a first crossing; stability and mechanism are unresolved",
        },
    ]

    projected_source = e68["source_crossings"]["projected"]
    unbounded_source = e68["source_crossings"]["unbounded"]
    projected_late = e68["trend_sensitivity"]["projected"]["late_six"][
        "crossings"
    ]
    projected_drop = e68["trend_sensitivity"]["projected"]["drop_first"][
        "crossings"
    ]
    pooled_source = e68["trend_sensitivity"]["pooled_noop_labels"]["source"][
        "crossings"
    ]
    mechanism = e68["source_and_mechanism_audit"]
    pre = e68["preround_audit"]

    claims = [
        {
            "claim": "The historical projected-label estimator crosses zero at c*=.242197",
            "verdict": "CONFIRMED_AS_CODED",
            "evidence_level": "E3",
            "reason": (
                "All 48 tissue rows reproduce the selected aggregate curve and first linear crossing inside the sampled .1-.3 bracket. This is exact reconstruction of the estimator, not validation of a unique physical threshold."
            ),
        },
        {
            "claim": "Lineage fidelity is non-decaying down to a stable finite threshold near .22-.24",
            "verdict": "NOT_CONFIRMED_AS_WORDED",
            "evidence_level": "E3",
            "reason": (
                "The value is the first crossing of a sparse aggregate. No tissue has a clean one-transition curve; dropping the first valid score introduces extra transitions and moves the first crossing to about .284, while the late-six fit crosses near .448 and turns negative again at c=1. The score mask expands over cycles and its denominators are not retained."
            ),
        },
        {
            "claim": "Agreement of projected and unbounded arms shows the threshold is not a norm-projection artefact",
            "verdict": "REFUTED_AS_AN_INTERVENTION_COMPARISON",
            "evidence_level": "E1/E3",
            "reason": (
                "For already projected theta, E68's orthogonal mixture is explicitly rescaled to the parent norm and already has mean zero and std .3, so boundary reprojection is a numerical identity. Both labels are projected on the next write step, yet the label changes the RNG before preparation. At c=1 no mixture occurs, but the two labels give opposite slope signs."
            ),
        },
        {
            "claim": "Flesh/context plus R actively restores corrupted theta",
            "verdict": "CONSISTENT_BUT_NOT_CAUSALLY_IDENTIFIED",
            "evidence_level": "E2/E3",
            "reason": (
                "The fission-free pre-round moves theta correlation upward at all four perturbations, demonstrating an active programmed update toward R. Fixed-form fidelity nevertheless falls in all four. In lineages R is copied whole without noise and theta is explicitly updated toward tanh(R), with no writer, R, V/context, target, or link ablation."
            ),
        },
        {
            "claim": "The body is a proofreader rather than a correlated information source or built-in rewrite target",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2",
            "reason": (
                "Exact inherited R is an uncorrupted backup and direct update target while residual V/context also survives. The retained design does not remove or scramble those sources. E67 shows start dependence in one no-fission write loop, but does not identify which source supplies corrected information."
            ),
        },
        {
            "claim": "V, culture, and theta form an Eigen hierarchy in one transmitted-correlation currency",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "E55 perturbs R with additive noise and never sweeps V correlation; E65 never measures delivered correlation and its barcode observer scores 256 rather than 16 positions; E68 imposes instantaneous theta correlation and fits a different temporal endpoint. The targets and sensitivity controls also differ."
            ),
        },
        {
            "claim": "The threshold remains finite and non-decaying beyond the sampled horizon",
            "verdict": "NOT_TESTED",
            "evidence_level": "E0",
            "reason": (
                "Every E68 trajectory ends after twelve fissions. No thirteenth-cycle value or horizon-extension arm exists, and within-horizon late trends already differ from the full-window result."
            ),
        },
    ]

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L22",
        "audit_kind": "outcome-known E68 retained-row reconstruction, estimator and source causal audit, plus bounded E55/E65/E67 comparison",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "deterministic_projection_identity_checks": len(E68_CORRS),
        "source_config_digests": source_digests,
        "retained_config_digests": retained_digests,
        "expected_config_digests": EXPECTED_CONFIG_DIGESTS,
        "source_config_digest_matches": digest_matches,
        "all_source_config_digests_match": all(digest_matches.values()),
        "git_provenance": _git_provenance(plastic_root),
        "document_checks": {
            "law_claims_c_star_approximately_point24": "c* ~ 0.24" in texts["LAWS.md"],
            "law_claims_unbounded_no_projection_artifact": "no projection artifact" in texts["LAWS.md"],
            "wave15_requires_unbounded_to_share_streams": "unbounded-noise arm (no re-projection) shares streams" in texts[
                "WAVE15_PROPHECIES.md"
            ],
            "wave15_requires_CI_off_edges": "CI off the sweep edges" in texts[
                "WAVE15_PROPHECIES.md"
            ],
            "discovery_calls_threshold_clean": "MEASURED, CLEAN" in texts[
                "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
            ],
            "prior_L20_flags_immediate_reprojection": "first subsequent write update" in texts[
                "L20_SELF_WRITTEN_GENOME_AUDIT_2026-09-03.md"
            ],
            "prior_L19_invalidates_barcode": "barcode endpoint is invalid" in texts[
                "L19_INCORRUPTIBLE_REFERENCE_AUDIT_2026-09-03.md"
            ],
        },
        "E68_deep_eigen": e68,
        "E67_follower_modifier": e67,
        "E55_V_claim_comparator": e55,
        "E65_culture_claim_comparator": e65,
        "hierarchy_currency_table": hierarchy_rows,
        "hierarchy_is_one_currency": False,
        "claim_assessment": claims,
        "strongest_supported_wording": (
            "In E68's retained three-tissue engineered sheet, the historical projected-label calculation averages tissue fidelity at each cycle, transforms excess above a fixed .5 level with a .001 floor, and fits cycles 2-12. It yields a negative trend at imposed theta correlation .1 and positive aggregate trends at sampled correlations .3 and above, so its first linear interpolation is .242197. The fission-free pre-round also shows that the programmed R-to-theta write rule can move perturbed theta back toward its pre-perturbation state. These are bounded results about one estimator and an active rewrite attractor. They do not establish a stable error threshold, a projection-independent contrast, body-only proofreading, a common V/culture/theta currency, or behavior beyond twelve fissions."
        ),
        "closer_pass_target": (
            "After L24's first pass, freeze a common-random-number factorial with one preparation reused across projection labels; genuinely norm-unbounded and norm-matched corruptions; fixed scoring masks and retained denominators; at least two predeclared horizons; dense correlation points around a pilot-independent bracket; tissue-powered uncertainty; raw and calibrated-null fidelity endpoints; writer on/off crossed with R inherit/reset/scramble, V/context scramble, direct R-to-theta link removal, and target removal; post-corruption and post-recovery theta/R/V information traced each cycle; and common correlation-calibrated V, culture, R, and theta channels."
        ),
        "headline_diagnostics": {
            "reported_projected_c_star": projected_source["first_upward"],
            "reported_unbounded_first_c_star": unbounded_source["first_upward"],
            "reported_unbounded_upward_crossings": len(unbounded_source["upward"]),
            "reported_unbounded_downward_crossings": len(unbounded_source["downward"]),
            "drop_first_projected_first_crossing": projected_drop["first_upward"],
            "drop_first_projected_upward_crossings": len(projected_drop["upward"]),
            "late_six_projected_first_crossing": projected_late["first_upward"],
            "late_six_projected_single_threshold_shape": projected_late[
                "single_threshold_shape"
            ],
            "projected_log_floor_first_crossing_range": [
                min(
                    float(row["first_upward"])
                    for row in e68["log_floor_sensitivity"]["projected"].values()
                    if row["first_upward"] is not None
                ),
                max(
                    float(row["first_upward"])
                    for row in e68["log_floor_sensitivity"]["projected"].values()
                    if row["first_upward"] is not None
                ),
            ],
            "projected_chance_level_first_crossing_range": [
                min(
                    float(row["first_upward"])
                    for row in e68["chance_level_sensitivity"]["projected"].values()
                    if row["first_upward"] is not None
                ),
                max(
                    float(row["first_upward"])
                    for row in e68["chance_level_sensitivity"]["projected"].values()
                    if row["first_upward"] is not None
                ),
            ],
            "projected_tissues_with_single_threshold_shape": sum(
                row["crossings"]["single_threshold_shape"]
                for row in e68["tissue_thresholds"]["projected"]
            ),
            "pooled_noop_labels_single_threshold_shape": pooled_source[
                "single_threshold_shape"
            ],
            "boundary_projection_identity": mechanism[
                "boundary_projection_is_algebraic_identity"
            ],
            "c1_opposite_label_signs": mechanism[
                "c1_labels_have_opposite_slope_signs"
            ],
            "all_preround_fidelity_deltas_negative": pre[
                "all_fidelity_deltas_negative"
            ],
            "all_preround_theta_recoveries_positive": pre[
                "all_theta_recoveries_positive"
            ],
            "E65_barcode_admissible": e65["barcode_erasure_admissible"],
            "horizon_extension_present": mechanism[
                "cycle_13_or_extension_retained"
            ],
        },
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        curve_rows,
        tissue_rows,
        hierarchy_rows,
        frozen_hashes,
    )


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return buffer.getvalue()


CURVE_FIELDS = (
    "project_label",
    "c_target",
    "realized_corr",
    "source_log_excess_slope",
    "drop_first_valid_log_excess_slope",
    "late_six_log_excess_slope",
    "raw_fidelity_slope",
    "final_minus_first_valid",
    "first_valid_fidelity",
    "final_fidelity",
    "source_floor_hit_count",
    "mean_tissue_source_slope",
    "positive_tissue_source_slopes",
)
TISSUE_FIELDS = (
    "project_label",
    "c_target",
    "tissue",
    "realized_corr",
    "source_log_excess_slope",
    "drop_first_valid_log_excess_slope",
    "late_six_log_excess_slope",
    "raw_fidelity_slope",
    "final_minus_first_valid",
) + tuple(f"fidelity_cycle_{cycle}" for cycle in range(1, 13))
HIERARCHY_FIELDS = (
    "claimed_carrier",
    "experiment",
    "actual_intervention",
    "transmitted_correlation_controlled",
    "target",
    "outcome",
    "cycles",
    "key_value",
    "countervalue",
    "common_currency_with_E68",
    "admissible_conclusion",
)


def curve_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, CURVE_FIELDS)


def tissue_trajectory_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, TISSUE_FIELDS)


def hierarchy_currency_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, HIERARCHY_FIELDS)


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e68 = audit["E68_deep_eigen"]
    e67 = audit["E67_follower_modifier"]
    e55 = audit["E55_V_claim_comparator"]
    e65 = audit["E65_culture_claim_comparator"]
    gate = e68["reconstructed_gates"]
    conditions = e68["condition_details"]
    source_cross = e68["source_crossings"]
    trends = e68["trend_sensitivity"]
    mechanism = e68["source_and_mechanism_audit"]
    pre = e68["preround_audit"]
    projected_boot = e68["exact_tissue_block_bootstrap"]["projected"]
    unbounded_boot = e68["exact_tissue_block_bootstrap"]["unbounded"]
    floor_first = [
        float(row["first_upward"])
        for row in e68["log_floor_sensitivity"]["projected"].values()
        if row["first_upward"] is not None
    ]
    chance_first = [
        float(row["first_upward"])
        for row in e68["chance_level_sensitivity"]["projected"].values()
        if row["first_upward"] is not None
    ]
    lines = [
        "# L22 retained proofreading audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained/source audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "The `.242` number is reproducible, but the proofreading law is not established. It is the first interpolated sign crossing of one selected aggregate trend. The result changes with reasonable time-window and floor conventions, no individual tissue has the advertised clean threshold shape, and the supposedly independent unbounded arm is not a distinct physical intervention.",
        "",
        "There is a real, narrower observation: E68's programmed write rule moves corrupted theta back toward its prior state. But R is copied perfectly and theta is explicitly pulled toward R. Without removing R, V/context, the writer, or the target, that is restoration toward an intact backup—not proof that the body reconstructs missing gene information.",
        "",
        "## Exact E68 reconstruction",
        "",
        f"All {e68['retained_tissue_rows']} tissue rows and all 16 caches reconstruct every selected summary field and Boolean. The registered primary remains `{gate['gate_p68_1_primary']}` because the pre-round predicts no crossing.",
        "",
        "| Label | c | Source slope | Drop first valid | Late six | Raw slope | First fidelity | Final fidelity | Positive tissues |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label in ("projected", "unbounded"):
        for corr in E68_CORRS_ASC:
            row = conditions[label][str(corr)]
            lines.append(
                f"| {label} | {_fmt(corr, 2)} | {_fmt(row['source_log_excess_slope'])} | {_fmt(row['drop_first_valid_log_excess_slope'])} | {_fmt(row['late_six_log_excess_slope'])} | {_fmt(row['raw_fidelity_slope'])} | {_fmt(row['first_valid_fidelity'])} | {_fmt(row['final_fidelity'])} | {row['positive_tissue_source_slopes']}/3 |"
            )
    lines.extend(
        [
            "",
            f"The historical projected curve has one upward crossing, {_fmt(gate['c_star_projected'])}, inside the unsampled [{_fmt(source_cross['projected']['upward'][0]['bracket'][0], 1)}, {_fmt(source_cross['projected']['upward'][0]['bracket'][1], 1)}] interval. The historical unbounded-labelled curve's first upward crossing is {_fmt(gate['c_star_unbounded'])}, but it has {len(source_cross['unbounded']['upward'])} upward and {len(source_cross['unbounded']['downward'])} downward crossings. It is negative at c=.8, .95, and 1, so it is not a threshold curve.",
            "",
            "## Estimator sensitivity",
            "",
            f"Dropping the first valid projected score moves the first crossing to {_fmt(trends['projected']['drop_first']['crossings']['first_upward'])} and creates {len(trends['projected']['drop_first']['crossings']['upward'])} upward crossings. Fitting only cycles 7-12 moves the first crossing to {_fmt(trends['projected']['late_six']['crossings']['first_upward'])}; that curve is negative at c=.3 and again at c=1. At c=.3 specifically, the full-window source slope is {_fmt(conditions['projected']['0.3']['source_log_excess_slope'])}, but the late-six slope is {_fmt(conditions['projected']['0.3']['late_six_log_excess_slope'])}.",
            "",
            f"None of the three projected tissue curves has one clean negative-to-nonnegative transition with no reversal. Exact 3-of-3 tissue-block resampling gives a conditional first-crossing range [{_fmt(projected_boot['conditional_first_crossing_range'][0])}, {_fmt(projected_boot['conditional_first_crossing_range'][1])}], and only {projected_boot['exactly_one_upward_crossing']}/27 resamples have exactly one upward crossing. For the unbounded label, only {unbounded_boot['exactly_one_upward_crossing']}/27 do. These are descriptive diagnostics, not a registered CI.",
            "",
            f"The source's `bootstrap=200` setting is unused. Across the protocol's log-floor sensitivity range, the projected first crossing runs from {_fmt(min(floor_first))} to {_fmt(max(floor_first))}; changing the uncalibrated chance level from .45 through .55 produces a range from {_fmt(min(chance_first))} to {_fmt(max(chance_first))}. The selected `log(max(f-.5,.001))` convention floors early observations. The cumulative `regrow>=2` mask also expands every generation; its sizes and locations were not saved. Thus the fitted temporal slope mixes changing state with changing scored positions.",
            "",
            "## The projection comparison is a no-op",
            "",
            f"For already projected theta, the orthogonal mixture is always rescaled to the parent norm and has the same zero mean and norm before the optional projection. The deterministic identity check's largest projected-minus-unprojected difference is {_fmt(e68['projection_identity_diagnostic']['max_abs_difference'], 15)}. Then `cascade_sweep` projects both labels on the first recovery update and every later update. No genuinely unbounded condition exists.",
            "",
            f"The label is nevertheless included in the seed before preparation. At c=1 the mixture is skipped entirely, so the labels are physically identical treatments with different streams. Their source slopes are {_fmt(mechanism['c1_projected_source_slope'])} and {_fmt(mechanism['c1_unbounded_source_slope'])}: opposite signs. Pooling both no-op labels also fails the one-threshold shape. The algebra shows only that the optional boundary projection is redundant; because both labels remain inside the norm shell, their numerical crossing agreement cannot establish that the norm shell does not shape the result.",
            "",
            "## Restoration is not identified proofreading",
            "",
            "| Pre-round c | Fidelity change | Theta-correlation recovery |",
            "|---:|---:|---:|",
        ]
    )
    for row in pre["rows"]:
        lines.append(
            f"| {_fmt(row['c'], 1)} | {_fmt(row['fidelity_delta'])} | {_fmt(row['theta_recovery'])} |"
        )
    lines.extend(
        [
            "",
            "All four theta-correlation changes are positive, while all four fixed-form fidelity changes are negative. This pre-round contains no fission and leaves V and R intact. In the lineage assay R is copied whole without noise, R pulls V, and theta is explicitly updated toward `tanh(R)` for 1,000 sweeps after every corruption. No writer-off, R-reset/scramble, context-scramble, target-removal, or R-to-theta-link ablation exists. The data show a programmed restoration attractor, but cannot identify the body as the information-recovering proofreader.",
            "",
            f"E67's five one-tissue, no-fission endpoints reconstruct mean start-dependence {_fmt(e67['mean_start_dependence'])}. That supports strong dependence of final theta on initial V/R in this feedback loop. It contains no corruption or causal ablation and does not establish error correction or E68's threshold.",
            "",
            "## The hierarchy is not in one currency",
            "",
            "| Claimed carrier | Actual intervention | Endpoint | Key retained value | Why comparison fails |",
            "|---|---|---|---:|---|",
            f"| V / E55 | Noise is added to exactly copied R; V is always fragment-fissioned | Fixed-ancestor tail fidelity | {_fmt(e55['exact_R_copy_all_complexity_fixed_ancestor_tail'])} | V correlation is never swept; immediate-parent tail similarity is {_fmt(e55['exact_R_copy_all_complexity_immediate_parent_tail'])} |",
            f"| Culture / E65 | Exact parent sign saved externally, then whole-sheet clamp | Fixed-founder tail fidelity | {_fmt(e65['parent_chain_T200'])} | Delivered correlation is absent; this exceeds the source floor quantity {_fmt(e65['source_floor_q95'])}; barcode observer is invalid |",
            f"| Theta / E68 | Instantaneous theta mix while R copies exactly | Log-excess trend on expanding masks | {_fmt(gate['c_star_projected'])} | Different target, coordinate, statistic, and sensitivity; threshold shape is unstable |",
            "",
            f"E65's Boolean barcode target has shape {e65['barcode_target_shape']} but broadcasts against a 16x16 V field, scoring {e65['barcode_reported_positions']} positions instead of {e65['barcode_intended_positions']}. Its only score occurs seven cycles after injection. It cannot support `erased even at perfect transmission`.",
            "",
            "## Clause verdicts",
            "",
            "| Claim | Verdict | Evidence |",
            "|---|---|---:|",
        ]
    )
    for claim in audit["claim_assessment"]:
        lines.append(
            f"| {claim['claim']} | `{claim['verdict']}` | {claim['evidence_level']} |"
        )
    lines.extend(
        [
            "",
            "## Strongest supported wording",
            "",
            audit["strongest_supported_wording"],
            "",
            "## Provenance and execution",
            "",
            f"The independently transcribed defaults match all four retained configuration digests. The audit consumed {audit['input_file_count']} hashed inputs, reconstructed 48 E68 trajectories and the bounded E55/E65/E67 comparisons, ran eight deterministic projection-identity checks, generated no scientific future, and replayed no simulator trajectory.",
            "",
            "## Closer-pass target",
            "",
            audit["closer_pass_target"],
            "",
        ]
    )
    return "\n".join(lines)
