"""Outcome-known retained audit for L23's compositional-code claim."""

from __future__ import annotations

import csv
import hashlib
import io
import itertools
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGEST = (
    "33f6b18cc62c865f73fb4cd81c14970d7db34dee11d3a01729c7940d8b2e47c5"
)
FORM_SEEDS = dict(zip("ABCD", (1, 3, 5, 7)))
TRACKED_PACKAGES = (
    "alphabet",
    "blueprint_web",
    "contract_bridge",
    "ladder_web",
    "setpoint_rewrite",
    "voltage_web",
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


def source_config_digest() -> str:
    """Digest an independent transcription of current E67 defaults."""

    config = {
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
    }
    return canonical_digest(config)


def _seed_rng(tag: str, *parts: object) -> np.random.Generator:
    payload = tag + ":" + ":".join(map(str, parts))
    digest = hashlib.sha256(payload.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "little"))


def launch_pattern(seed_index: int, *, height: int = 16, width: int = 16) -> np.ndarray:
    """Independent transcription of the deterministic voltage launch recipe."""

    field = np.full((height, width), -1.0)
    if seed_index == 0:
        field[:, : width // 2] = 1.0
    elif seed_index == 1:
        field[: height // 2, :] = 1.0
    elif seed_index in (2, 3):
        period = 4 if seed_index == 2 else 8
        for column in range(width):
            if (column // (period // 2)) % 2 == 0:
                field[:, column] = 1.0
    elif seed_index in (4, 5):
        rng = _seed_rng("voltage-spots-v1", seed_index)
        for _ in range(2 + seed_index - 3):
            center_y, center_x = rng.integers(0, height), rng.integers(0, width)
            radius = 2 + int(seed_index == 5)
            yy, xx = np.ogrid[:height, :width]
            distance_squared = (
                np.minimum(np.abs(yy - center_y), height - np.abs(yy - center_y))
                ** 2
                + np.minimum(
                    np.abs(xx - center_x), width - np.abs(xx - center_x)
                )
                ** 2
            )
            field[distance_squared <= radius**2] = 1.0
    else:
        density = 0.2 + 0.4 * (seed_index - 6) / 9
        rng = _seed_rng("voltage-density-v1", seed_index)
        field = np.where(rng.random((height, width)) < density, 1.0, -1.0)
    return field


def _project_theta(theta: np.ndarray, norm: float) -> np.ndarray:
    centered = theta - theta.mean(axis=(-2, -1), keepdims=True)
    scale = centered.std(axis=(-2, -1), keepdims=True)
    return centered * (norm / np.maximum(scale, 1e-9))


def _write_form(form: np.ndarray, norm: float, gain: float = 1.5) -> np.ndarray:
    return _project_theta(np.tanh(gain * form)[None], norm)[0]


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    a = left.ravel().astype(float)
    b = right.ravel().astype(float)
    a -= a.mean()
    b -= b.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a @ b / denominator) if denominator else 0.0


def reconstruct_form_and_pair_ledgers(
    threshold: float = 0.15,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, np.ndarray]]:
    forms = {name: launch_pattern(seed) for name, seed in FORM_SEEDS.items()}
    left = np.zeros((16, 16), dtype=bool)
    left[:, :8] = True
    right = ~left
    form_rows = []
    for name in "ABCD":
        form = forms[name]
        left_mean = float(form[left].mean())
        right_mean = float(form[right].mean())
        form_rows.append(
            {
                "form": name,
                "seed": FORM_SEEDS[name],
                "positive_cells": int((form > 0).sum()),
                "whole_mean": float(form.mean()),
                "left_half_mean": left_mean,
                "right_half_mean": right_mean,
                "left_role_eligible": abs(left_mean) < threshold,
                "right_role_eligible": abs(right_mean) < threshold,
            }
        )

    pair_rows = []
    for left_name, right_name in itertools.permutations("ABCD", 2):
        left_mean = float(forms[left_name][left].mean())
        right_mean = float(forms[right_name][right].mean())
        composite_mean = 0.5 * (left_mean + right_mean)
        left_pass = abs(left_mean) < threshold
        right_pass = abs(right_mean) < threshold
        composite_pass = abs(composite_mean) < threshold
        eligible = left_pass and right_pass and composite_pass
        failures = []
        if not left_pass:
            failures.append("left_half")
        if not right_pass:
            failures.append("right_half")
        if not composite_pass:
            failures.append("composite_mean")
        pair_rows.append(
            {
                "pair": left_name + right_name,
                "left_donor": left_name,
                "right_donor": right_name,
                "left_half_mean": left_mean,
                "right_half_mean": right_mean,
                "composite_mean": composite_mean,
                "left_pass": left_pass,
                "right_pass": right_pass,
                "composite_pass": composite_pass,
                "eligible": eligible,
                "pre_screen_failures": ";".join(failures),
                "expression_simulated": eligible,
                "expected_aggregate_score_rows": 8 if eligible else 0,
                "retained_raw_score_rows": 0,
            }
        )
    return form_rows, pair_rows, forms


def _minimum_cross_group_gap(
    high_mean: float,
    high_n: int,
    low_mean: float,
    low_n: int,
    residual_ss: float,
) -> float:
    """Lower-bound every high observation minus every low observation.

    For a group of n with a fixed mean, displacing one observation by x costs
    at least n*x^2/(n-1) in within-group sum of squares. Spending the complete
    retained residual sum of squares adversarially across two groups gives the
    bound below. Other groups can only make the true bound tighter.
    """

    high_cost = high_n / (high_n - 1)
    low_cost = low_n / (low_n - 1)
    maximum_gap_erosion = np.sqrt(
        residual_ss * (1.0 / high_cost + 1.0 / low_cost)
    )
    return float(high_mean - low_mean - maximum_gap_erosion)


def composition_fit_diagnostics(panel: Mapping[str, Any]) -> dict[str, Any]:
    fit = panel["fit"]
    mu = float(fit["mu"])
    own_mean = mu + float(fit["a_own"])
    other_mean = mu + float(fit["b_other"])
    neither_mean = mu
    counts = {"own": 4, "other": 4, "neither": 8}
    grand_mean = (
        counts["own"] * own_mean
        + counts["other"] * other_mean
        + counts["neither"] * neither_mean
    ) / 16
    explained_ss = (
        counts["own"] * (own_mean - grand_mean) ** 2
        + counts["other"] * (other_mean - grand_mean) ** 2
        + counts["neither"] * (neither_mean - grand_mean) ** 2
    )
    residual_share = float(fit["interaction_share"])
    total_ss = explained_ss / (1.0 - residual_share)
    residual_ss = total_ss - explained_ss
    own_vs_other = _minimum_cross_group_gap(
        own_mean, counts["own"], other_mean, counts["other"], residual_ss
    )
    own_vs_neither = _minimum_cross_group_gap(
        own_mean, counts["own"], neither_mean, counts["neither"], residual_ss
    )
    own_individual_lower = max(0.0, counts["own"] * own_mean - 3.0)
    gate = bool(
        float(fit["a_own"]) > float(panel["null_a_q95"])
        and float(fit["a_own"]) > float(fit["b_other"])
        and residual_share < 0.25
    )
    return {
        "rows": 16,
        "group_counts": counts,
        "neither_mean": neither_mean,
        "own_mean": own_mean,
        "other_mean": other_mean,
        "grand_mean": grand_mean,
        "explained_ss": float(explained_ss),
        "residual_ss": float(residual_ss),
        "total_ss": float(total_ss),
        "residual_share_of_total": residual_share,
        "residual_to_explained_ratio": float(residual_ss / explained_ss),
        "residual_rms_over_16_rows": float(np.sqrt(residual_ss / 16)),
        "minimum_possible_individual_own_score": own_individual_lower,
        "minimum_own_minus_any_other_group_row": own_vs_other,
        "minimum_own_minus_any_neither_group_row": own_vs_neither,
        "minimum_own_minus_any_nonown_row": min(own_vs_other, own_vs_neither),
        "all_four_own_rows_must_exceed_every_nonown_row": min(
            own_vs_other, own_vs_neither
        )
        > 0,
        "reported_gate_reconstructs_from_retained_aggregates": gate
        == bool(panel["compositional"]),
        "reported_gate_value": gate,
        "design_contains_explicit_interaction_column": False,
        "interaction_share_is_residual_ss_over_total_ss": True,
        "interaction_share_is_share_of_explained_variance": False,
        "null_share_q05_used_in_gate": False,
        "raw_rows_available_for_independent_fit": False,
        "null_draws_available_for_independent_quantile": False,
    }


def _input_corr(alpha: float) -> float:
    return float((1.0 - alpha) / np.sqrt((1.0 - alpha) ** 2 + alpha**2))


def discreteness_diagnostics(
    data: Mapping[str, Any], forms: Mapping[str, np.ndarray]
) -> dict[str, Any]:
    curve = data["curve"]
    xs = np.asarray([_input_corr(float(row["alpha"])) for row in curve])
    ms = np.asarray([float(row["m"]) for row in curve])
    span = float(ms.max() - ms.min())
    high = float(ms.max() - 0.25 * span)
    low = float(ms.min() + 0.25 * span)
    interior_indices = np.flatnonzero((ms < high) & (ms > low))
    width = (
        float(xs[interior_indices].max() - xs[interior_indices].min())
        if len(interior_indices)
        else 0.0
    )
    crossings = []
    for index in range(len(curve) - 1):
        m0, m1 = ms[index], ms[index + 1]
        if (m0 >= 0 > m1) or (m0 < 0 <= m1):
            fraction = float(-m0 / (m1 - m0))
            crossings.append(
                {
                    "alpha": float(curve[index]["alpha"])
                    + fraction
                    * (
                        float(curve[index + 1]["alpha"])
                        - float(curve[index]["alpha"])
                    ),
                    "input_corr_A": float(xs[index] + fraction * (xs[index + 1] - xs[index])),
                    "alpha_bracket": [
                        float(curve[index]["alpha"]),
                        float(curve[index + 1]["alpha"]),
                    ],
                    "input_corr_bracket": [float(xs[index]), float(xs[index + 1])],
                    "local_corr_grid_spacing": abs(float(xs[index + 1] - xs[index])),
                }
            )

    theta_a = _write_form(forms["A"], float(data["norm"]))
    theta_b = _write_form(forms["B"], float(data["norm"]))
    coordinate_errors = []
    for row in curve:
        alpha = float(row["alpha"])
        mixed = _project_theta(
            ((1.0 - alpha) * theta_a + alpha * theta_b)[None],
            float(data["norm"]),
        )[0]
        coordinate_errors.append(abs(_corr(mixed, theta_a) - float(row["input_corr_A"])))

    hysteresis = data["hysteresis"]
    start_dependences = [float(row["start_dependence"]) for row in hysteresis]
    fresh = [float(row["fresh"]) for row in hysteresis]
    return {
        "reconstructed_transition_width": width,
        "reported_transition_width": float(data["transition_width_corr_units"]),
        "transition_width_reconstructs": close(
            width, float(data["transition_width_corr_units"])
        ),
        "curve_span": span,
        "central_50_percent_low": low,
        "central_50_percent_high": high,
        "interior_grid_point_count": int(len(interior_indices)),
        "interior_alphas": [float(curve[index]["alpha"]) for index in interior_indices],
        "zero_width_is_single_point_resolution_artifact": len(interior_indices) == 1
        and close(width, 0.0),
        "m_strictly_decreases_on_grid": bool(np.all(np.diff(ms) < 0)),
        "sign_crossings": crossings,
        "control_width": float(data["control_width"]),
        "reader_width_strictly_beats_control": float(
            data["transition_width_corr_units"]
        )
        < float(data["control_width"]),
        "reader_and_control_width_tie": close(
            float(data["transition_width_corr_units"]),
            float(data["control_width"]),
        ),
        "control_curve_rows_retained": 0,
        "A_B_form_correlation": _corr(forms["A"], forms["B"]),
        "theta_A_B_correlation": _corr(theta_a, theta_b),
        "max_input_coordinate_error": max(coordinate_errors),
        "input_coordinate_exact_for_tested_A_B_pair": max(coordinate_errors) < 1e-12,
        "mean_start_dependence_reconstructed": float(np.mean(start_dependences)),
        "mean_start_dependence_reported": float(data["mean_start_dependence"]),
        "store_bistable_reconstructed": bool(np.mean(start_dependences) < 0.2),
        "store_bistable_reported": bool(data["store_bistable"]),
        "fresh_endpoint_sequence": fresh,
        "fresh_endpoint_adjacent_changes": [
            float(right - left) for left, right in zip(fresh, fresh[1:])
        ],
        "fresh_endpoint_strictly_decreases": bool(np.all(np.diff(fresh) < 0)),
        "forward_reverse_alpha_continuation_loop_present": False,
        "independent_run_per_alpha_and_start": True,
        "theta_V_and_R_coevolve_during_assay": True,
        "futures_per_start": 2,
        "tissues": 1,
        "raw_future_endpoints_retained": 0,
        "supports_theta_endpoint_dependence_on_initial_V_R": True,
        "proves_analog_storage": False,
        "localizes_all_discreteness_to_reader": False,
    }


def capacity_diagnostics(data: Mapping[str, Any]) -> dict[str, Any]:
    rows = data["rows"]
    ks = np.asarray([int(row["K"]) for row in rows], dtype=float)
    own = np.asarray([float(row["within_channel_own"]) for row in rows])
    band_sizes = {
        str(int(k)): [len(chunk) for chunk in np.array_split(np.arange(16), int(k))]
        for k in ks
    }
    return {
        "retained_rows": [dict(row) for row in rows],
        "reported_ceiling": int(data["ceiling"]),
        "candidate_starts": 10,
        "candidate_futures_per_start": 2,
        "candidate_future_indices_used_for_repertoire": [0],
        "observed_pairwise_distinct_representatives": int(data["ceiling"]),
        "representative_rule": "greedy in seed order; join on agreement > .8 with any existing representative",
        "representative_search_is_order_dependent": True,
        "reported_ceiling_is_empirical_upper_bound": False,
        "reported_ceiling_is_observed_repertoire_count": True,
        "raw_candidate_final_states_retained": 0,
        "tested_K_values": [int(value) for value in ks],
        "all_reported_kway_accuracies_one": all(
            close(float(row["kway_accuracy"]), 1.0) for row in rows
        ),
        "largest_tested_K": int(max(ks)),
        "all_nine_representatives_tested_together": bool(
            max(ks) == int(data["ceiling"])
        ),
        "class_batch_decisions_across_K": int(sum(ks)),
        "class_batch_decisions_at_K7": 7,
        "expression_futures_averaged_before_each_argmax": 4,
        "per_future_predictions_retained": 0,
        "score_margins_retained": 0,
        "confusion_matrices_retained": 0,
        "held_out_classes_tested": 0,
        "supports_engineered_seven_prototype_batch_discrimination": True,
        "supports_capacity_of_at_least_nine_written_classes": False,
        "within_channel_values": own.tolist(),
        "within_channel_K7_minus_K2": float(own[-1] - own[0]),
        "within_channel_range": float(own.max() - own.min()),
        "within_channel_linear_slope_per_K": float(np.polyfit(ks, own, 1)[0]),
        "within_channel_monotonically_decreases": bool(np.all(np.diff(own) <= 0)),
        "band_row_sizes": band_sizes,
        "unequal_band_sizes_present": any(len(set(sizes)) > 1 for sizes in band_sizes.values()),
        "band_scores_weighted_equally_not_by_cell_count": True,
        "composite_multiband_theta_reprojected": False,
        "matched_single_form_band_controls_present": False,
        "cross_band_confusion_retained": False,
        "raw_band_scores_retained": 0,
        "absence_of_interference_identified": False,
    }


def _first_commit(repository_root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(repository_root.resolve())
        commits = subprocess.run(
            [
                "git",
                "-C",
                str(repository_root),
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


def _git_provenance(plastic_root: Path, alphabet_root: Path) -> dict[str, Any]:
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
    expectation = _first_commit(repository_root, alphabet_root / "EXPECTATIONS.md")
    result = _first_commit(
        repository_root, alphabet_root / "results/full/alphabet_summary.json"
    )
    return {
        "repository_root": str(repository_root),
        "expectations_first_commit": expectation,
        "selected_result_first_commit": result,
        "same_first_commit_snapshot": expectation is not None and expectation == result,
        "prose_date_is_independent_temporal_seal": False,
    }


def run_l23_audit(
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
        "ruliad": ideas_root / "RULIAD_DISCUSSION.md",
        "baseline": workspace / "SOURCE_BASELINE.md",
        "review_protocol": workspace / "REVIEW_PROTOCOL.md",
        "protocol": workspace / "protocols/L23_WORDS_BALANCE_BOOKS_AUDIT_V1.md",
        "law_case": workspace / "laws/L23_words_balance_books.md",
        "l20_review": workspace / "reviews/L20_SELF_WRITTEN_GENOME_AUDIT_2026-09-03.md",
        "l22_review": workspace / "reviews/L22_BODY_PROOFREADS_GENE_AUDIT_2026-09-03.md",
    }
    texts = {name: _read(tracker, path) for name, path in narrative_paths.items()}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    alphabet_root = _experiment_root(plastic_root, "alphabet")
    result_root = alphabet_root / "results/full"
    result_files = sorted(path for path in result_root.rglob("*") if path.is_file())
    for path in result_files:
        tracker.add(path)
    summary = tracker.json(result_root / "alphabet_summary.json")
    part_payloads = {
        name: tracker.json(result_root / "work" / f"{name}.json")
        for name in ("composition", "capacity", "discreteness", "robustness")
    }
    parts = {name: payload["data"] for name, payload in part_payloads.items()}
    reconstructed_gates = {
        **parts,
        "gate_p67_1_primary": bool(parts["composition"]["primary"]["compositional"]),
        "interaction_share": float(
            parts["composition"]["primary"]["fit"]["interaction_share"]
        ),
    }

    form_rows, pair_rows, forms = reconstruct_form_and_pair_ledgers()
    passing = [row for row in pair_rows if row["eligible"]]
    unique_unordered = {"".join(sorted(row["pair"])) for row in passing}
    composition = parts["composition"]
    composition_diagnostics = {
        label: composition_fit_diagnostics(composition[label])
        for label in ("primary", "secondary")
    }
    capacity = capacity_diagnostics(parts["capacity"])
    discreteness = discreteness_diagnostics(parts["discreteness"], forms)

    capacity_rows = []
    for row in parts["capacity"]["rows"]:
        k = int(row["K"])
        capacity_rows.append(
            {
                **row,
                "band_row_sizes": ";".join(map(str, capacity["band_row_sizes"][str(k)])),
                "class_batch_decisions": k,
                "futures_averaged_per_decision": 4,
                "per_future_predictions_retained": 0,
                "score_margins_retained": 0,
                "matched_no_interference_control": False,
            }
        )
    curve_rows = []
    for row in parts["discreteness"]["curve"]:
        span = discreteness["curve_span"]
        inside = (
            float(row["m"]) < discreteness["central_50_percent_high"]
            and float(row["m"]) > discreteness["central_50_percent_low"]
        )
        curve_rows.append({**row, "central_50_percent_interior": inside, "span": span})
    hysteresis_rows = [dict(row) for row in parts["discreteness"]["hysteresis"]]

    claims = [
        {
            "claim": "The two eligible half compositions express their intended donor in each half",
            "verdict": "CONFIRMED_AS_CODED",
            "evidence_level": "E2",
            "reason": (
                "The only pairs are AB and BA. Raw rows were discarded, but the retained OLS group means and total residual sum of squares imply that each of the four own-donor scores exceeds every non-own score, with a conservative primary-norm margin above .034."
            ),
        },
        {
            "claim": "The .365 own effect, .127 interaction share, and .132 null establish additive composition",
            "verdict": "NOT_CONFIRMED_AS_WORDED",
            "evidence_level": "E2",
            "reason": (
                "The cached numbers and Boolean are internally consistent, but no raw score or null-draw rows survive. The model has only intercept, own, and other columns; .127 is unexplained/total variance, not an estimated interaction term or a share of explained interaction."
            ),
        },
        {
            "claim": "Conservation causally prevents ten of twelve compositions and supplies a grammar rule",
            "verdict": "NOT_CONFIRMED_AS_CAUSAL",
            "evidence_level": "E3/E2",
            "reason": (
                "The deterministic pre-screen does exclude ten pairs, but none is expressed. A and B are exactly half-balanced; C and D are not. The composite-mean check is redundant once both half checks pass, so the result demonstrates selection by a balance rule, not failure caused by conservation."
            ),
        },
        {
            "claim": "The store has nine distinguishable classes and perfect seven-way discrimination",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "The cache reports nine greedy representatives among ten native-substrate candidate starts and 1.0 accuracy for K=2..7. The latter is one argmax per class after averaging four futures, using ideal writes of the first seven prototypes; it does not test all nine, held-out classes, per-future accuracy, or a capacity ceiling."
            ),
        },
        {
            "claim": "There is no relevant interference across seven bands",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2",
            "reason": (
                "Own-band agreement ranges roughly .785-.824 and does not decline monotonically, but K changes forms, streams, unequal band sizes, and an un-reprojected composite theta. There is no matched single-form band control, cross-band confusion table, raw band score, or uncertainty."
            ),
        },
        {
            "claim": "Theta is analog and all discreteness lies in the bistable reader",
            "verdict": "NOT_CONFIRMED_AS_WORDED",
            "evidence_level": "E2/E3",
            "reason": (
                "The theta endpoint strongly follows initial V/R and store_bistable=False reconstructs under the source definition. But reader and continuous-control widths both equal zero, the reader width comes from only one central grid point, and the so-called hysteresis block contains no forward/reverse loop. This does not localize all discreteness."
            ),
        },
        {
            "claim": "E67 establishes a proto-genetic code inverse to DNA's division of labour",
            "verdict": "NOT_EMPIRICAL",
            "evidence_level": "E0",
            "reason": (
                "E67 uses one simulated tissue, experimenter-built ideal theta fields, no fission or copying, and no biological data. Code and DNA language is an analogy beyond the bounded expression assay."
            ),
        },
    ]

    part_digest_matches = {
        name: payload.get("config_digest") == EXPECTED_CONFIG_DIGEST
        for name, payload in part_payloads.items()
    }
    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L23",
        "audit_kind": "outcome-known E67 retained-part reconstruction, deterministic eligibility audit, and source/estimator review",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "static_launch_forms_reconstructed": 4,
        "source_config_digest": source_config_digest(),
        "retained_config_digest": summary["config_digest"],
        "expected_config_digest": EXPECTED_CONFIG_DIGEST,
        "source_and_retained_config_digest_match": source_config_digest()
        == summary["config_digest"]
        == EXPECTED_CONFIG_DIGEST,
        "part_config_digest_matches": part_digest_matches,
        "all_part_config_digests_match": all(part_digest_matches.values()),
        "selected_summary_reconstructs_from_part_caches": _recursive_close(
            reconstructed_gates, summary["gates"]
        ),
        "git_provenance": _git_provenance(plastic_root, alphabet_root),
        "retention_inventory": {
            "result_files": [str(path.relative_to(alphabet_root)) for path in result_files],
            "result_file_count": len(result_files),
            "composition_score_rows_expected": 16,
            "composition_score_rows_retained": 0,
            "donor_shuffle_draws_run": 200,
            "donor_shuffle_draws_retained": 0,
            "capacity_candidate_states_retained": 0,
            "kway_score_vectors_retained": 0,
            "individual_future_classifications_retained": 0,
            "within_channel_band_scores_retained": 0,
            "continuous_control_curve_rows_retained": 0,
            "hysteresis_future_endpoints_retained": 0,
        },
        "document_checks": {
            "expectation_was_8_to_12_passing_pairs": "expect 8-12 of 12 pairs to pass"
            in texts["discovery"]
            or "expect 8-12 of 12 pairs to pass" in _read(
                tracker, alphabet_root / "EXPECTATIONS.md"
            ),
            "register_declares_partition_control": "Partition control (checkerboard support)"
            in texts["wave15"],
            "design_review_requires_matched_control_beaten": "matched continuous control that must be beaten"
            in texts["design_review"],
            "discovery_acknowledges_control_tie_and_resolution_limit": "control also saturated — resolution-limited"
            in texts["discovery"],
            "v23_has_no_E67_overlap": "bioelectric-sheet, blueprint"
            in texts["baseline"],
        },
        "form_rows": form_rows,
        "pair_eligibility": {
            "rows": pair_rows,
            "passing_pairs": [row["pair"] for row in passing],
            "passing_ordered_pairs": len(passing),
            "passing_unordered_pair_count": len(unique_unordered),
            "passing_unordered_pairs": sorted(unique_unordered),
            "rejected_before_expression": len(pair_rows) - len(passing),
            "rejected_expression_outcomes_observed": 0,
            "third_composite_condition_redundant_given_half_conditions": True,
            "redundancy_proof": "|(.5)*(left+right)| <= .5*(|left|+|right|) < threshold when both absolute half means are below threshold",
            "prospective_expected_range": [8, 12],
            "prospective_expectation_met": 8 <= len(passing) <= 12,
            "partition_checkerboard_control_present": False,
            "balanced_unbalanced_expression_counterfactual_present": False,
            "conservation_causal_effect_identified": False,
        },
        "composition": {
            "reported": composition,
            "diagnostics": composition_diagnostics,
            "tissues": 1,
            "forms_in_source_alphabet": 4,
            "forms_surviving_in_both_roles": 2,
            "ordered_pairs_simulated": len(passing),
            "unordered_pair_combinations_simulated": len(unique_unordered),
            "expression_sweeps": 300,
            "futures_per_pair": 4,
            "theta_fields_are_ideal_hand_constructed_writes": True,
            "endogenous_write_process_tested": False,
            "fission_or_copying_present": False,
            "explicit_pair_factor_in_regression": False,
            "explicit_half_factor_in_regression": False,
            "explicit_interaction_factor_in_regression": False,
            "null_quantiles_independently_reconstructible": False,
            "general_four_form_composition_supported": False,
        },
        "capacity": capacity,
        "discreteness": discreteness,
        "robustness_part_retained_but_not_used_for_L23_verdict": parts["robustness"],
        "source_checks": {
            "source_says_ideal_writes": "storage properties are tested on ideal writes"
            in _read(tracker, alphabet_root / "src/alphabet/pipeline.py"),
            "source_fit_has_three_columns": "np.stack([np.ones_like(ys), d, o], axis=1)"
            in _read(tracker, alphabet_root / "src/alphabet/pipeline.py"),
            "source_interaction_share_is_one_minus_r2": '"interaction_share": 1.0 - r2'
            in _read(tracker, alphabet_root / "src/alphabet/pipeline.py"),
            "source_uses_only_first_ceiling_future": "finals.append(np.sign(V[0]))"
            in _read(tracker, alphabet_root / "src/alphabet/pipeline.py"),
            "source_averages_future_scores_before_argmax": "scores = [agree(V, f) for f in forms]"
            in _read(tracker, alphabet_root / "src/alphabet/pipeline.py"),
            "source_reprojects_multiband_theta": False,
            "source_contains_checkerboard_partition_control": "checkerboard"
            in _read(tracker, alphabet_root / "src/alphabet/pipeline.py"),
            "source_contains_fission_call": "fission(" in _read(
                tracker, alphabet_root / "src/alphabet/pipeline.py"
            ),
        },
        "claim_assessment": claims,
        "strongest_supported_wording": (
            "In one 16x16 tissue, the deterministic balance pre-screen selects only AB and BA—the two orientations of one exactly half-balanced A/B combination. Under ideal hand-constructed theta fields, the retained aggregate fit is strong enough to guarantee that each of the four selected halves scores its own donor above every non-donor form. Separately, the assay reports nine greedy native-substrate representatives among ten starts, and ideal writes of the first seven yield correct class-batch argmax decisions through K=7. The within-channel own-band aggregate remains between .785 and .824, and theta endpoints depend strongly on initial V/R. These are bounded expression and start-dependence results; they do not establish general additive composition, conservation causation, a capacity ceiling, no interference, reader-only discreteness, heredity, or a DNA-inverting code."
        ),
        "closer_pass_target": (
            "After L24's first pass, freeze a common-stream multi-tissue design that crosses balance with donor identity and partition geometry, expresses every pair rather than excluding unbalanced cases, adds reservoir/mean-restoration interventions and checkerboard/rotated seams, retains future-by-half scores, and fits an explicit pair/half/interaction model. Separately use held-out prototype classes and per-future confusion/margins for capacity; matched single-form, shuffled-band, and globally reprojected controls for interference; and a dense common-stream reader curve plus true forward/reverse writer-frozen hysteresis loops for discreteness localization."
        ),
        "headline_diagnostics": {
            "passing_pairs": [row["pair"] for row in passing],
            "passing_unordered_pairs": len(unique_unordered),
            "primary_own_mean": composition_diagnostics["primary"]["own_mean"],
            "primary_minimum_own_nonown_margin": composition_diagnostics["primary"][
                "minimum_own_minus_any_nonown_row"
            ],
            "interaction_term_in_model": False,
            "rejected_pairs_expressed": 0,
            "reported_ceiling_is_upper_bound": capacity[
                "reported_ceiling_is_empirical_upper_bound"
            ],
            "all_nine_tested_together": capacity[
                "all_nine_representatives_tested_together"
            ],
            "K7_minus_K2_within_channel": capacity["within_channel_K7_minus_K2"],
            "matched_interference_control_present": capacity[
                "matched_single_form_band_controls_present"
            ],
            "reader_width": discreteness["reported_transition_width"],
            "control_width": discreteness["control_width"],
            "reader_beats_control": discreteness[
                "reader_width_strictly_beats_control"
            ],
            "central_transition_interior_points": discreteness[
                "interior_grid_point_count"
            ],
            "true_hysteresis_loop_present": discreteness[
                "forward_reverse_alpha_continuation_loop_present"
            ],
        },
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        form_rows,
        pair_rows,
        capacity_rows,
        curve_rows,
        hysteresis_rows,
        frozen_hashes,
    )


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return buffer.getvalue()


FORM_FIELDS = (
    "form",
    "seed",
    "positive_cells",
    "whole_mean",
    "left_half_mean",
    "right_half_mean",
    "left_role_eligible",
    "right_role_eligible",
)
PAIR_FIELDS = (
    "pair",
    "left_donor",
    "right_donor",
    "left_half_mean",
    "right_half_mean",
    "composite_mean",
    "left_pass",
    "right_pass",
    "composite_pass",
    "eligible",
    "pre_screen_failures",
    "expression_simulated",
    "expected_aggregate_score_rows",
    "retained_raw_score_rows",
)
CAPACITY_FIELDS = (
    "K",
    "chance",
    "kway_accuracy",
    "within_channel_own",
    "band_row_sizes",
    "class_batch_decisions",
    "futures_averaged_per_decision",
    "per_future_predictions_retained",
    "score_margins_retained",
    "matched_no_interference_control",
)
CURVE_FIELDS = (
    "alpha",
    "input_corr_A",
    "m",
    "central_50_percent_interior",
    "span",
)
HYSTERESIS_FIELDS = (
    "alpha",
    "fresh",
    "A",
    "B",
    "start_dependence",
)


def form_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, FORM_FIELDS)


def pair_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, PAIR_FIELDS)


def capacity_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, CAPACITY_FIELDS)


def discreteness_curve_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, CURVE_FIELDS)


def hysteresis_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, HYSTERESIS_FIELDS)


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    pair = audit["pair_eligibility"]
    comp = audit["composition"]
    capacity = audit["capacity"]
    discrete = audit["discreteness"]
    primary = comp["diagnostics"]["primary"]
    secondary = comp["diagnostics"]["secondary"]
    crossing = discrete["sign_crossings"][0]
    lines = [
        "# L23 retained composition/capacity audit",
        "",
        f"**Verdict:** `{audit['overall_verdict']}`  ",
        "**Work state:** `RECALCULATED`  ",
        "**Design:** outcome-known retained-part and source audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Bottom line",
        "",
        "The narrow two-composite result survives, more strongly than the aggregate-only retention initially suggests. The pre-screen selects only `AB` and `BA`: reverse orientations of one A/B combination. From the fitted group means and residual sum of squares, every one of their four half-wise own-donor scores must exceed every non-own score. At norm .15 the conservative worst-case separation is still "
        + f"`{_fmt(primary['minimum_own_minus_any_nonown_row'])}`.",
        "",
        "The general law does not follow. Ten pairs were rejected before expression, not observed to fail. A and B are exactly balanced in both halves; C and D are not. The composite-average condition adds no constraint once both half conditions pass. Thus conservation is the selection rule used to construct the tested panel, not a demonstrated cause of failed composition.",
        "",
        "The reported `.127` is also misnamed: the regression has no interaction term. It is residual sum of squares divided by total sum of squares. The sixteen score rows and 200 null draws were discarded, so the coefficients and null quantiles cannot be independently recalculated from lower-level retained data.",
        "",
        "Nine is a greedy repertoire count from ten native-substrate starts, not a measured upper ceiling. Seven-way recognition is real as an aggregate engineering result, but each class decision averages four futures before `argmax`, only the first seven prototypes are tested, and no per-future predictions, margins, or held-out classes survive. The roughly flat band score is not a controlled no-interference contrast. Finally, reader and control widths are tied at zero, with the reader value produced by one interior grid point; start dependence supports a theta endpoint that follows V/R, not the claim that all discreteness resides in flesh.",
        "",
        "## Eligibility ledger",
        "",
        "| Pair | left mean | right mean | composite mean | Eligible | Expressed? |",
        "|---|---:|---:|---:|:---:|:---:|",
    ]
    for row in pair["rows"]:
        lines.append(
            f"| {row['pair']} | {_fmt(row['left_half_mean'])} | {_fmt(row['right_half_mean'])} | {_fmt(row['composite_mean'])} | {'yes' if row['eligible'] else 'no'} | {'yes' if row['expression_simulated'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"Passing ordered pairs: **{pair['passing_ordered_pairs']}/12**. Distinct unordered combinations: **{pair['passing_unordered_pair_count']}**. The prospective 8–12 expectation was missed, and the declared checkerboard partition control is absent.",
            "",
            "## What the aggregate composition fit can and cannot prove",
            "",
            "| Norm | own mean | other mean | neither mean | residual/total | residual/explained | worst-case own−nonown |",
            "|---:|---:|---:|---:|---:|---:|---:|",
            f"| .15 | {_fmt(primary['own_mean'])} | {_fmt(primary['other_mean'])} | {_fmt(primary['neither_mean'])} | {_fmt(primary['residual_share_of_total'])} | {_fmt(primary['residual_to_explained_ratio'])} | {_fmt(primary['minimum_own_minus_any_nonown_row'])} |",
            f"| .30 | {_fmt(secondary['own_mean'])} | {_fmt(secondary['other_mean'])} | {_fmt(secondary['neither_mean'])} | {_fmt(secondary['residual_share_of_total'])} | {_fmt(secondary['residual_to_explained_ratio'])} | {_fmt(secondary['minimum_own_minus_any_nonown_row'])} |",
            "",
            "There are four `own`, four `other`, and eight `neither` rows. OLS makes each coefficient a category-mean contrast. The retained residual share recovers the total residual sum of squares; a fixed-mean variance bound then guarantees all four own rows rank above all twelve non-own rows. This validates half-wise decoding for AB/BA, but cannot recover the individual scores, pair effects, null samples, uncertainty, or an interaction coefficient.",
            "",
            "## Capacity and bands",
            "",
            "| K | batch accuracy | chance | own-band agreement | band row sizes |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for source_row in capacity["retained_rows"]:
        k = int(source_row["K"])
        lines.append(
            f"| {k} | {_fmt(source_row['kway_accuracy'])} | {_fmt(source_row['chance'])} | {_fmt(source_row['within_channel_own'])} | {'/'.join(map(str, capacity['band_row_sizes'][str(k)]))} |"
        )
    lines.extend(
        [
            "",
            f"The own-band curve changes by `{_fmt(capacity['within_channel_K7_minus_K2'])}` from K=2 to K=7, has range `{_fmt(capacity['within_channel_range'])}`, and is not monotone decreasing. That is consistent with no catastrophic loss in this aggregate, but not evidence of zero interference: there is no matched single-form band baseline, and multi-band theta is not globally reprojected.",
            "",
            "## Reader/store diagnostic",
            "",
            f"The A and B ideal writes are orthogonal (`r={_fmt(discrete['theta_A_B_correlation'])}`), so the analytic input-correlation coordinate is exact here. The reader curve crosses zero near alpha `{_fmt(crossing['alpha'])}` (input correlation `{_fmt(crossing['input_corr_A'])}`). Its central-50% width is reported as zero because only alpha .6 lies strictly inside the central band; the local correlation-grid interval around the sign change is `{_fmt(crossing['local_corr_grid_spacing'])}`. The continuous control also reports width zero, so the reader does not beat it.",
            "",
            f"The five start dependences average `{_fmt(discrete['mean_start_dependence_reconstructed'])}` and reproduce `store_bistable=False` under the source's `<.2` rule. Each alpha/start is an independent run, however—there is no forward/reverse continuation loop. V, R, and theta co-evolve, so the clean conclusion is initial-state dependence of theta in this coupled system.",
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
            "## Closer pass after L24",
            "",
            str(audit["closer_pass_target"]),
            "",
            "## Provenance and run boundary",
            "",
            f"The independently transcribed config digest matches `{audit['expected_config_digest']}`. All four part-cache digests match, and their combination reproduces the selected summary: `{audit['selected_summary_reconstructs_from_part_caches']}`. The audit consumed {audit['input_file_count']} hashed files. It generated four static launch forms, zero scientific futures, and zero simulator replays.",
            "",
        ]
    )
    return "\n".join(lines)
