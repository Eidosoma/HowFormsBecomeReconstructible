"""Outcome-known retained/replay audit for L08 amplifier claims."""

from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import re
import sys
from typing import Any, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E37_persuadability": "11248c303c3519d0242d220a28a78a8721736a73087d8222052035262043a766",
    "E38_james_test": "73cc6c7ad0efe66d519b30278138367eb035516b6cdb6743568e62cd28dd0fe4",
    "E39_excitable_web": "4ddce03ee08f12048be258346d32e8f08606f235409d3979dd24c79e3f0feb64",
    "E40_lightcone_2": "56f7a9be7a8d96236bf59f3d25e7d6b37b651635584ab11c39665a582fd1034f",
    "E41_persuadability_2": "19d4cc8669e9ff0922ee90800680afccbd08799b897da130f126be1a35d98105",
    "E42_james_test_2": "95f2f959571d81d7fb9e4732c0e27007f853bc97b9a477b8e93620a0c4fca57d",
    "E47_sealed_battery_3": "8a27efba409f1b8e3ca131112a5f3c1535983d33b78da86e99662703df6724ed",
}

RUNGS = ("A", "B", "C", "D")
LEVERS = ("L1_rewire", "L2_inject", "L3_reinforce", "L4_inform")
LADDERS: dict[str, tuple[float | int, ...]] = {
    "L1_rewire": (0.02, 0.05, 0.1, 0.2),
    "L2_inject": (4, 8, 16, 32),
    "L3_reinforce": (0.5, 1.0, 2.0, 4.0),
    "L4_inform": (0.005, 0.01, 0.02, 0.04),
}
E39_REPLAY_ARM_PATHS = 24


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


def _track_package(tracker: InputTracker, root: Path) -> None:
    for relative in ("EXPECTATIONS.md", "pyproject.toml"):
        if (root / relative).is_file():
            tracker.add(root / relative)
    for directory in ("src", "tests"):
        if (root / directory).is_dir():
            for path in sorted((root / directory).rglob("*.py")):
                tracker.add(path)


def source_config_digests() -> dict[str, str]:
    """Independently transcribed source defaults, exposed for tests."""

    configs: dict[str, dict[str, Any]] = {
        "E37_persuadability": {
            "mode": "full",
            "n_tissues": 8,
            "futures": 32,
            "horizon": 20,
            "hold_generations": 4,
            "target_cos": 0.9,
            "l1_bias": (0.02, 0.05, 0.1, 0.2),
            "l2_sweeps": (4, 8, 16, 32),
            "l3_punish": (0.5, 1.0, 2.0, 4.0),
            "l4_eps": (0.005, 0.01, 0.02, 0.04),
            "inject_generation": 3,
            "trajectory_seed_tag": "persuade-traj-v1",
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
        "E39_excitable_web": {
            "mode": "full",
            "a_w": 0.7,
            "b_w": 0.8,
            "eps_w": 0.08,
            "dt_u": 0.3,
            "diffusion": 1.0,
            "substeps": 5,
            "u_rest": -1.2,
            "w_rest": -0.62,
            "stim_value": 2.0,
            "ready_margin": 0.25,
            "k_u": 0.5,
            "fire_threshold": 0.35,
            "trajectory_seed_tag": "excite-traj-v1",
        },
        "E40_lightcone_2": {
            "mode": "full",
            "n_tissues": 12,
            "futures": 32,
            "displacement_ladder": (4, 6, 8),
            "strip_width": 3,
            "displacement_magnitude": 0.8,
            "recovery_sweeps": 60,
            "persistence_horizon": 24,
            "trajectory_seed_tag": "cone2-traj-v1",
        },
        "E41_persuadability_2": {
            "mode": "full",
            "n_tissues": 8,
            "futures": 32,
            "horizon": 20,
            "hold_generations": 4,
            "target_cos": 0.9,
            "cue_amplitudes": (0.6, 1.2, 2.4),
            "cue_blocks_per_sign": 4,
            "cue_generations": (3, 7, 11),
            "l2_on_bare_energy": 56.92,
            "trajectory_seed_tag": "persuade2-traj-v1",
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
        "E47_sealed_battery_3": {
            "mode": "full",
            "base_tissue": 300,
            "n_tissues": 8,
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


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


def _intensity_key(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return str(float(value))


def _bootstrap_mean_interval(
    values: list[float], *, seed: int, draws: int = 4096
) -> list[float]:
    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    selected = rng.integers(0, len(data), size=(draws, len(data)))
    means = data[selected].mean(axis=1)
    return [float(x) for x in np.quantile(means, (0.025, 0.975))]


def _directions(values: list[float], tolerance: float = 1e-12) -> dict[str, int]:
    return {
        "positive": sum(value > tolerance for value in values),
        "tied": sum(abs(value) <= tolerance for value in values),
        "negative": sum(value < -tolerance for value in values),
    }


def _load_shards(
    root: Path,
    tracker: InputTracker,
    *,
    prefix: str,
    expected_shards: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    work = root / "results/full/work"
    paths = sorted(work.glob(f"{prefix}_*_of_{expected_shards:02d}.json"))
    if len(paths) != expected_shards:
        raise ValueError(
            f"expected {expected_shards} {prefix} shards, found {len(paths)}"
        )
    ids = []
    payloads = []
    pattern = re.compile(
        rf"{re.escape(prefix)}_(\d+)_of_(\d+)\.json"
    )
    for path in paths:
        match = pattern.fullmatch(path.name)
        if match is None or int(match.group(2)) != expected_shards:
            raise ValueError(f"unexpected shard name: {path.name}")
        ids.append(int(match.group(1)))
        payloads.append(tracker.json(path))
    if ids != list(range(expected_shards)):
        raise ValueError(f"incomplete shard IDs for {prefix}: {ids}")
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"shard config digests differ for {prefix}: {digests}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    return entries, {
        "n_shards": len(paths),
        "shard_ids": ids,
        "config_digest": next(iter(digests)),
        "n_entries": len(entries),
    }


def audit_e37(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="persuade_shard", expected_shards=8
    )
    summary = tracker.json(root / "results/full/persuade_summary.json")
    posthoc = tracker.json(root / "results/full/anchor_rewrite_posthoc.json")
    runner_source = tracker.add(
        root / "src/persuadability/runner.py"
    ).read_text(encoding="utf-8")
    pipeline_source = tracker.add(
        root / "src/persuadability/pipeline.py"
    ).read_text(encoding="utf-8")

    expected_keys = {
        (rung, lever, float(intensity), tissue)
        for rung in RUNGS
        for lever in LEVERS
        for intensity in LADDERS[lever]
        for tissue in range(8)
    }
    observed_keys = [
        (
            str(entry["rung"]),
            str(entry["lever"]),
            float(entry["intensity"]),
            int(entry["tissue"]),
        )
        for entry in entries
    ]
    integrity.update(
        {
            "expected_entries": 512,
            "unique_keys": len(set(observed_keys)),
            "complete_expected_grid": set(observed_keys) == expected_keys,
            "no_duplicate_keys": len(observed_keys) == len(set(observed_keys)),
            "summary_n_entries": int(summary["n_entries"]),
            "summary_digest_matches_shards": (
                summary.get("config_digest") == integrity["config_digest"]
            ),
            "rates_bounded": all(
                0.0 <= float(entry["success_rate"]) <= 1.0 for entry in entries
            ),
            "rates_are_multiples_of_one_over_32": all(
                close(
                    float(entry["success_rate"]) * 32,
                    round(float(entry["success_rate"]) * 32),
                )
                for entry in entries
            ),
            "energies_nonnegative": all(float(entry["energy"]) >= 0 for entry in entries),
        }
    )

    cells: dict[str, dict[str, Any]] = {}
    reported_cell_matches: dict[str, bool] = {}
    cell_index = 0
    for rung in RUNGS:
        for lever in LEVERS:
            for intensity in LADDERS[lever]:
                rows = [
                    entry
                    for entry in entries
                    if entry["rung"] == rung
                    and entry["lever"] == lever
                    and close(entry["intensity"], intensity)
                ]
                if len(rows) != 8:
                    raise ValueError(
                        f"E37 cell {rung}/{lever}/{intensity} has {len(rows)} rows"
                    )
                rows.sort(key=lambda row: int(row["tissue"]))
                rates = [float(row["success_rate"]) for row in rows]
                energies = [float(row["energy"]) for row in rows]
                rate = float(np.mean(rates))
                energy = float(np.mean(energies))
                key = f"{rung}:{lever}:{_intensity_key(intensity)}"
                cells[key] = {
                    "rung": rung,
                    "lever": lever,
                    "intensity": intensity,
                    "n_tissues": len(rows),
                    "nominal_futures_per_tissue": 32,
                    "rate": rate,
                    "energy": energy,
                    "rate_tissue_bootstrap_95": _bootstrap_mean_interval(
                        rates, seed=202609020800 + cell_index
                    ),
                    "tissue_rates": rates,
                    "tissues_relative_to_success_bar": {
                        "above": sum(value > 0.5 for value in rates),
                        "equal": sum(close(value, 0.5) for value in rates),
                        "below": sum(value < 0.5 for value in rates),
                    },
                    "works_by_registered_mean_bar": rate >= 0.5,
                }
                reported = summary["details"][f"{rung}:{lever}"][
                    _intensity_key(intensity)
                ]
                reported_cell_matches[key] = close(rate, reported["rate"]) and close(
                    energy, reported["energy"]
                )
                cell_index += 1

    minimum_energy: dict[str, float | None] = {}
    for rung in RUNGS:
        for lever in LEVERS:
            candidates = [
                cell["energy"]
                for cell in cells.values()
                if cell["rung"] == rung
                and cell["lever"] == lever
                and cell["works_by_registered_mean_bar"]
            ]
            minimum_energy[f"{rung}:{lever}"] = min(candidates) if candidates else None
    l2_a = minimum_energy["A:L2_inject"]
    l4_d = minimum_energy["D:L4_inform"]
    l3_curve = [minimum_energy[f"{rung}:L3_reinforce"] for rung in RUNGS]
    numeric_curve = [value if value is not None else math.inf for value in l3_curve]
    implemented_gates = {
        "min_energy_table": minimum_energy,
        "gate_p37_1_rungA_brute_only": bool(
            (
                minimum_energy["A:L1_rewire"] is not None
                or minimum_energy["A:L2_inject"] is not None
            )
            and minimum_energy["A:L4_inform"] is None
        ),
        "gate_p37_2_information_wins_on_D": bool(
            l4_d is not None and l2_a is not None and l4_d <= 0.1 * l2_a
        ),
        "l3_energy_by_rung": l3_curve,
        "gate_p37_3_reinforcement_cheapens": bool(
            sum(value is not None for value in l3_curve) >= 2
            and all(
                numeric_curve[i] >= numeric_curve[i + 1] - 1e-12
                for i in range(len(numeric_curve) - 1)
            )
        ),
    }
    gate_matches = {
        key: _recursive_close(value, summary["gates"][key])
        for key, value in implemented_gates.items()
    }

    maximum_by_rung = {}
    for rung in RUNGS:
        candidates = [cell for cell in cells.values() if cell["rung"] == rung]
        best = max(candidates, key=lambda cell: cell["rate"])
        maximum_by_rung[rung] = {
            "lever": best["lever"],
            "intensity": best["intensity"],
            "rate": best["rate"],
            "rate_tissue_bootstrap_95": best["rate_tissue_bootstrap_95"],
        }

    l2_energy_by_rung = {
        rung: [
            cells[f"{rung}:L2_inject:{_intensity_key(intensity)}"]["energy"]
            for intensity in LADDERS["L2_inject"]
        ]
        for rung in RUNGS
    }
    return {
        "integrity": integrity,
        "cells": cells,
        "all_64_reported_cells_match": all(reported_cell_matches.values())
        and len(reported_cell_matches) == 64,
        "reported_cell_matches": reported_cell_matches,
        "recalculated_gates": implemented_gates,
        "reported_gates": summary["gates"],
        "all_reported_gates_match": all(gate_matches.values()),
        "gate_matches": gate_matches,
        "finite_search": {
            "rungs": list(RUNGS),
            "named_levers": list(LEVERS),
            "configured_intensities": {
                lever: list(values) for lever, values in LADDERS.items()
            },
            "n_cells": 64,
            "n_tissue_rows": 512,
            "nominal_future_runs": 512 * 32,
            "horizon_generations": 20,
            "success_rule": "census cosine > 0.9 held four generations; equal-tissue mean >= 0.5",
            "target": "the same tissue/rung's separately settled seed-1 census",
            "target_observer": "instantaneous 15-bin block census after 60 sweeps",
            "success_observer": "generation-averaged 15-bin block spectrum",
            "target_and_success_use_identical_time_aggregation": False,
            "full_position_resolved_pattern_is_success_endpoint": False,
            "untreated_control_in_grid": False,
            "input_output_gain_curve_measured": False,
            "equivalence_or_noninferiority_margin": None,
        },
        "maximum_rate_cell_by_rung": maximum_by_rung,
        "all_B_C_D_cell_means_below_half": all(
            cell["rate"] < 0.5
            for cell in cells.values()
            if cell["rung"] in ("B", "C", "D")
        ),
        "number_of_working_cells": sum(
            cell["works_by_registered_mean_bar"] for cell in cells.values()
        ),
        "implementation_audit": {
            "L1_and_L4_have_identical_voltage_update_expression": (
                runner_source.count(
                    "Vg[sub] += tissue.dt * intensity * signed[None]"
                )
                == 2
            ),
            "L1_and_L4_differ_in_configured_range_and_rng_label_not_operator": True,
            "same_point_0_02_rates": {
                rung: {
                    "L1": cells[f"{rung}:L1_rewire:0.02"]["rate"],
                    "L4": cells[f"{rung}:L4_inform:0.02"]["rate"],
                }
                for rung in RUNGS
            },
            "rng_namespace_includes_lever_and_intensity": (
                "rung, index, lever, intensity" in runner_source
            ),
            "cells_share_draw_exact_streams": False,
            "L2_nominal_sweep_ladder": list(LADDERS["L2_inject"]),
            "identity_generation_minimum_sweeps": 4,
            "L2_mean_energy_by_rung": l2_energy_by_rung,
            "L2_energy_identical_across_all_nominal_durations_on_B_C_D": all(
                max(l2_energy_by_rung[rung]) - min(l2_energy_by_rung[rung])
                <= 1e-12
                for rung in ("B", "C", "D")
            ),
            "L3_uses_active_batch_median_reinforcement_multiplier": (
                "np.median(sigma_mult[idx[sub]])" in runner_source
            ),
            "implemented_gate_P37_1_checks_L3_absence": False,
            "implemented_gate_P37_1_uses_L1_or_L2_not_both": (
                'table.get("A:L1_rewire") is not None or l2_on_a is not None'
                in pipeline_source
            ),
            "energy_formulas_share_a_demonstrated_physical_unit": False,
            "energy_note": (
                "L1/L4 price intensity squared without the dt-scaled applied change; "
                "L2 prices the clamped value rather than the actual voltage change; "
                "L3 prices a noise-scale difference."
            ),
        },
        "posthoc_anchor_rewrite": {
            "retained": posthoc,
            "has_config_digest": "config_digest" in posthoc,
            "has_tissue_or_future_rows": False,
            "lowest_evidence_level": "E1/E2 prose-sized aggregate without provenance guard",
        },
    }


def audit_e38(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/james_summary.json")
    pipeline = tracker.add(root / "src/james_test/pipeline.py").read_text(
        encoding="utf-8"
    )
    gates = summary["gates"]
    recalculated = {
        "half_dispersion": float(gates["half_dispersion"]),
        "end_dispersion": float(gates["end_dispersion"]),
        "gate_p38_1_varying_means": bool(
            gates["half_dispersion"] > 2 * gates["end_dispersion"]
        ),
        "median_stress_arrival_lock": float(gates["median_stress_arrival_lock"]),
        "arrival_spread_ratio": float(gates["arrival_spread_ratio"]),
        "gate_p38_2_cessation": bool(
            gates["median_stress_arrival_lock"] <= 3
            and gates["arrival_spread_ratio"] >= 3
        ),
        "naive_arrival": float(gates["naive_arrival"]),
        "preexposed_arrival": float(gates["preexposed_arrival"]),
        "gate_p38_3_generalization": bool(
            gates["preexposed_arrival"] <= 0.8 * gates["naive_arrival"]
        ),
        "escape_A": float(gates["escape_A"]),
        "escape_D": float(gates["escape_D"]),
        "backtrack_D": float(gates["backtrack_D"]),
        "gate_p38_4_delayed_gratification": bool(
            gates["escape_D"] >= 3 * max(gates["escape_A"], 1e-9)
            and gates["backtrack_D"] >= 0.8
        ),
    }
    return {
        "integrity": {
            "config_digest": summary.get("config_digest"),
            "matches_expected_config": (
                summary.get("config_digest")
                == EXPECTED_CONFIG_DIGESTS["E38_james_test"]
            ),
            "retained_result_files": 1,
            "lowest_retained_unit": "one aggregate summary",
        },
        "recalculated_gates": recalculated,
        "all_reported_gate_fields_match": _recursive_close(recalculated, gates),
        "executed_registry": {
            "rungs": ["A", "D"],
            "horizontal_naive_magnitudes": [0.05, 0.15, 0.4],
            "vertical_naive_magnitudes": [0.4],
            "vertical_after_horizontal_preexposure_magnitudes": [0.4],
            "diagonal_function_exists": 'kind == "vertical"' in pipeline
            and "else:  # diagonal" in pipeline,
            "diagonal_called_by_main_run": 'kind="diagonal"' in pipeline,
            "executed_orientation_count": 2,
            "n_tissues": 10,
            "futures_per_run": 32,
            "tilt_horizon_sweeps": 120,
            "nominal_tilt_future_runs": 100 * 32,
            "decoy_future_runs": 20 * 32,
            "untreated_tilt_control": False,
        },
        "retention_limits": {
            "per_tissue_rows": False,
            "per_future_rows": False,
            "arrival_rates": False,
            "no_arrival_denominators": False,
            "census_minimum_or_dip": False,
            "time_series": False,
            "calibration_rows": False,
            "tilt_magnitudes_stored_in_result": False,
            "x80_claim_stored_in_result": False,
            "x80_and_0_89_to_0_93_claim_level": (
                "E1 discovery-log/scorecard prose; no retained calibration artifact"
            ),
        },
        "interpretation": {
            "all_four_registered_gates_failed": all(
                recalculated[key] is False
                for key in recalculated
                if key.startswith("gate_")
            ),
            "median_arrival_one_proves_every_future_was_undisplaced": False,
            "equivalence_to_no_field_effect_tested": False,
            "all_zero_mean_fields_or_all_strengths_tested": False,
            "bounded_voidness_supported": True,
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
        "ladder_web",
        "excitable_web",
    )
    for name in reversed(packages):
        source = str((ideas / name / "src").resolve())
        if source not in sys.path:
            sys.path.insert(0, source)


def replay_current_e39(plastic_root: Path) -> dict[str, Any]:
    """Replay the 24 exact current-source paths frozen in the protocol."""

    _install_source_paths(plastic_root)
    from excitable_web.config import ExConfig
    from excitable_web.engine import _ready, excitable_step, rest_overlay
    from excitable_web.pipeline import amplification
    from ladder_web.config import LadderConfig
    from ladder_web.engine import ladder_step, tissue_fields
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config
    from voltage_web.engine import launch_pattern, make_thresholds

    ex = ExConfig()
    ladder = LadderConfig()
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    theta = make_thresholds(tissue)
    fields = tissue_fields(tissue, ladder, "D")
    V0 = launch_pattern(0, tissue)[None].copy()

    def run_excitable(
        *,
        V_start: np.ndarray,
        tissue_used,
        theta_used,
        fields_used,
        seed: int,
        sweeps: int,
        rung: str = "E",
        cue: np.ndarray | None = None,
        k_u: float | None = None,
    ) -> tuple[np.ndarray, dict[str, np.ndarray], float]:
        V = V_start.copy()
        ema = V.copy()
        overlay = rest_overlay(V.shape)
        rng = np.random.default_rng(seed)
        peak = -math.inf
        for sweep in range(sweeps):
            current_cue = cue if sweep == 0 else None
            V, ema, overlay, _, _ = excitable_step(
                V,
                ema,
                overlay,
                theta_used,
                tissue_used,
                ladder,
                ex,
                rung,
                rng,
                fields_used,
                cue_plus=current_cue,
                k_u=k_u,
            )
            peak = max(peak, float(overlay["up"].max()))
        return V, overlay, peak

    amp = amplification(ladder, ex)

    boolean_cue = np.zeros(V0.shape, dtype=bool)
    boolean_cue[0, 7:10, 7:10] = True
    propagated_V, propagated_overlay, propagated_peak = run_excitable(
        V_start=V0,
        tissue_used=tissue,
        theta_used=theta,
        fields_used=fields,
        seed=0,
        sweeps=30,
        cue=boolean_cue,
    )
    no_cue_V, no_cue_overlay, no_cue_peak = run_excitable(
        V_start=V0,
        tissue_used=tissue,
        theta_used=theta,
        fields_used=fields,
        seed=0,
        sweeps=30,
    )

    lesion_V, _, _ = run_excitable(
        V_start=V0,
        tissue_used=tissue,
        theta_used=theta,
        fields_used=fields,
        seed=7,
        sweeps=20,
        cue=boolean_cue,
        k_u=0.0,
    )
    passive_V = V0.copy()
    passive_ema = passive_V.copy()
    passive_rng = np.random.default_rng(7)
    for _ in range(20):
        passive_V, passive_ema, _ = ladder_step(
            passive_V,
            passive_ema,
            theta,
            tissue,
            ladder,
            "D",
            passive_rng,
            fields,
        )

    refractory_u = np.full((1, 4, 4), 1.5)
    refractory_w = np.full((1, 4, 4), 0.5)
    refractory_ready = bool(_ready(refractory_u, refractory_w, ex).any())

    quiet = replace(tissue, sigma=0.0)
    nofield_wave, _, _ = run_excitable(
        V_start=V0,
        tissue_used=quiet,
        theta_used=theta,
        fields_used=None,
        seed=0,
        sweeps=40,
        cue=boolean_cue,
    )
    nofield_lesion, _, _ = run_excitable(
        V_start=V0,
        tissue_used=quiet,
        theta_used=theta,
        fields_used=None,
        seed=0,
        sweeps=40,
        cue=boolean_cue,
        k_u=0.0,
    )
    field_wave, _, _ = run_excitable(
        V_start=V0,
        tissue_used=quiet,
        theta_used=theta,
        fields_used=fields,
        seed=0,
        sweeps=40,
        cue=boolean_cue,
    )
    field_lesion, _, _ = run_excitable(
        V_start=V0,
        tissue_used=quiet,
        theta_used=theta,
        fields_used=fields,
        seed=0,
        sweeps=40,
        cue=boolean_cue,
        k_u=0.0,
    )

    nofield_max_delta = float(np.max(np.abs(nofield_wave - nofield_lesion)))
    field_max_delta = float(np.max(np.abs(field_wave - field_lesion)))
    return {
        "current_source_amplification": amp,
        "propagation_golden": {
            "peak_up": propagated_peak,
            "far_corner_up": float(propagated_overlay["up"][0, 0, 0]),
            "far_corner_changed": not close(
                propagated_overlay["up"][0, 0, 0], ex.u_rest
            ),
            "far_corner_delta_vs_no_cue": float(
                propagated_overlay["up"][0, 0, 0]
                - no_cue_overlay["up"][0, 0, 0]
            ),
            "no_cue_peak_up": no_cue_peak,
            "no_cue_stays_below_zero": no_cue_peak < 0.0,
            "final_voltage_max_delta_vs_no_cue": float(
                np.max(np.abs(propagated_V - no_cue_V))
            ),
            "passes_source_test_assertions": bool(
                propagated_peak > 0.5
                and not close(propagated_overlay["up"][0, 0, 0], ex.u_rest)
                and no_cue_peak < 0.0
            ),
        },
        "refractory_golden": {
            "any_ready_immediately_after_firing_state": refractory_ready,
            "passes_source_test_assertion": not refractory_ready,
        },
        "lesion_golden": {
            "max_abs_voltage_delta": float(
                np.max(np.abs(lesion_V - passive_V))
            ),
            "allclose_at_1e_12": bool(
                np.allclose(lesion_V, passive_V, atol=1e-12, rtol=1e-7)
            ),
        },
        "conservation_golden": {
            "without_fields": {
                "mean_delta": float(nofield_wave.mean() - nofield_lesion.mean()),
                "max_abs_voltage_delta": nofield_max_delta,
                "wave_did_something": not bool(
                    np.allclose(nofield_wave, nofield_lesion)
                ),
                "source_test_assertions_pass": bool(
                    abs(nofield_wave.mean() - nofield_lesion.mean()) < 1e-12
                    and not np.allclose(nofield_wave, nofield_lesion)
                ),
            },
            "with_fields": {
                "mean_delta": float(field_wave.mean() - field_lesion.mean()),
                "max_abs_voltage_delta": field_max_delta,
                "mean_within_source_1e_2_bar": bool(
                    abs(field_wave.mean() - field_lesion.mean()) < 1e-2
                ),
                "wave_did_something": not bool(
                    np.allclose(field_wave, field_lesion)
                ),
            },
            "all_current_source_test_assertions_pass": bool(
                abs(nofield_wave.mean() - nofield_lesion.mean()) < 1e-12
                and not np.allclose(nofield_wave, nofield_lesion)
                and abs(field_wave.mean() - field_lesion.mean()) < 1e-2
            ),
        },
        "arm_paths_replayed": E39_REPLAY_ARM_PATHS,
        "fresh_seed_domain": False,
    }


def audit_e39(
    plastic_root: Path, root: Path, tracker: InputTracker
) -> dict[str, Any]:
    retained = tracker.json(root / "results/full/excitable_summary.json")
    engine = tracker.add(root / "src/excitable_web/engine.py").read_text(
        encoding="utf-8"
    )
    pipeline = tracker.add(root / "src/excitable_web/pipeline.py").read_text(
        encoding="utf-8"
    )
    expectations = tracker.add(root / "EXPECTATIONS.md").read_text(
        encoding="utf-8"
    )
    replay = replay_current_e39(plastic_root)
    replay_amp = replay["current_source_amplification"]
    screens_pass = all(
        bool(retained["screens"][rung]["pass"]) for rung in ("E", "F")
    )
    later_gate = bool(
        replay_amp["caused_sub"] < 1e-6 and replay_amp["caused_supra"] > 0.5
    )
    return {
        "integrity": {
            "config_digest": retained.get("config_digest"),
            "matches_expected_config": (
                retained.get("config_digest")
                == EXPECTED_CONFIG_DIGESTS["E39_excitable_web"]
            ),
            "lowest_retained_unit": "aggregate amplifier and two aggregate screens",
            "retained_gate_count": len(retained["gates"]),
            "P39_3_retained_as_summary_gate": "gate_p39_3_lesion_exact"
            in retained["gates"],
            "run_manifest_or_source_hash_retained": False,
        },
        "retained": {
            "amplification": retained["amplification"],
            "screens": retained["screens"],
            "gates": retained["gates"],
        },
        "current_source_replay": replay,
        "current_source_amplification_matches_retained": _recursive_close(
            replay_amp, retained["amplification"]
        ),
        "later_absolute_gate": {
            "rule": "caused_sub < 1e-6 and caused_supra > 0.5",
            "replayed_pass": later_gate,
            "reported_pass": bool(retained["gates"]["gate_p39_1_all_or_none"]),
            "replayed_matches_reported": (
                later_gate
                is retained["gates"]["gate_p39_1_all_or_none"]
            ),
        },
        "original_WAVE9_registered_gate": {
            "rule": (
                "sub-threshold response <= 2x passive; supra-threshold "
                "amplification factor >= 10, where factor is caused |Delta V| "
                "energy divided by cue energy"
            ),
            "cue_energy_calculated_in_pipeline": "cue_energy" in pipeline,
            "division_by_cue_energy_implemented": False,
            "passive_response_factor_retained": False,
            "registered_dimensionless_factor_retained": False,
            "status": "NOT_ADJUDICABLE_FROM_RETAINED_RESULT",
            "later_absolute_gate_is_same_estimand": False,
            "scorecard_calling_10_127_tenfold_is_supported_by_stored_units": False,
        },
        "screen_audit": {
            "both_aggregate_screens_pass": screens_pass,
            "P39_2_reported_gate_matches": (
                screens_pass is retained["gates"]["gate_p39_2_heredity"]
            ),
            "tissue_rows_retained": False,
            "future_rows_retained": False,
            "screen_is_absolute_E26_style_not_a_no_overlay_control_contrast": True,
            "E_screen_has_external_cues_during_screen": False,
        },
        "implementation_history_conflict": {
            "WAVE9_and_engine_header_describe_signed_channel_difference": (
                "(act+ - act-)" in engine or "u+ - u-" in engine
            ),
            "expectations_describe_mean_subtracted_signed_nudge": (
                "MEAN-SUBTRACTED nudge" in expectations
            ),
            "current_body_sums_unsigned_channel_activity": (
                "np.maximum(up, 0.0) + np.maximum(um, 0.0)" in engine
            ),
            "current_body_multiplies_organizer_comparator": (
                "act * comparator" in engine
            ),
            "current_body_is_E40_round_2_license_coupling": (
                "Coupling round 2" in engine and "LICENSE local repair" in engine
            ),
            "versioned_pre_E40_engine_retained": False,
            "current_body_matches_original_registered_coupling": False,
        },
        "mechanism_scope": {
            "threshold_engineered_by_positive_part_of_post_wave_u": (
                "np.maximum(up, 0.0)" in engine
            ),
            "analog_sub_cue_amplitude": 0.3,
            "analog_supra_cue_amplitude": 2.4,
            "number_of_amplitudes_in_main_assay": 2,
            "dense_dose_response_or_threshold_interval_measured": False,
            "cue_geometry": "3x3 block despite source docstring saying single-cell",
            "caused_metric": "endpoint sum(abs(V_wave - V_lesion)) over 256 cells",
            "caused_metric_is_energy": False,
            "mean_subtraction_precedes_voltage_clipping": (
                "nudge = nudge - nudge.mean" in engine
                and "np.clip(V + nudge" in engine
            ),
            "exact_final_charge_conservation_guaranteed_under_clipping": False,
            "constructed_nonlinear_amplifier_supported": bool(
                later_gate
                and replay["propagation_golden"]["passes_source_test_assertions"]
                and replay["lesion_golden"]["allclose_at_1e_12"]
            ),
        },
    }


def _e40_stats(entries: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    rows = sorted(
        (entry for entry in entries if entry["arm"] == arm),
        key=lambda entry: int(entry["tissue"]),
    )
    speeds = [
        entry["speed"]["median_recovery_sweeps"]
        for entry in rows
        if entry["speed"]["median_recovery_sweeps"] is not None
    ]
    return {
        "spatial_cone_median": float(
            np.median([entry["space"]["spatial_cone"] for entry in rows])
        ),
        "transport_recovery_max_d": float(
            np.mean(
                [
                    entry["space"]["recovery_by_distance"]["8"]
                    for entry in rows
                ]
            )
        ),
        "temporal_cone_median": float(
            np.median([entry["time"]["temporal_cone"] for entry in rows])
        ),
        "recovery_rate": float(
            np.mean([entry["speed"]["recovery_rate"] for entry in rows])
        ),
        "median_recovery_sweeps": float(np.median(speeds)) if speeds else None,
    }


def audit_e40(root: Path, tracker: InputTracker) -> dict[str, Any]:
    entries, integrity = _load_shards(
        root, tracker, prefix="cone2_shard", expected_shards=4
    )
    summary = tracker.json(root / "results/full/cone2_summary.json")
    pipeline = tracker.add(root / "src/lightcone_2/pipeline.py").read_text(
        encoding="utf-8"
    )
    keys = [(str(entry["arm"]), int(entry["tissue"])) for entry in entries]
    expected = {
        (arm, tissue)
        for arm in ("D", "F", "F_lesion")
        for tissue in range(12)
    }
    integrity.update(
        {
            "expected_entries": 36,
            "unique_keys": len(set(keys)),
            "complete_expected_grid": set(keys) == expected,
            "no_duplicate_keys": len(keys) == len(set(keys)),
            "summary_digest_matches_shards": (
                summary.get("config_digest") == integrity["config_digest"]
            ),
        }
    )
    cone = {arm: _e40_stats(entries, arm) for arm in ("D", "F", "F_lesion")}
    gates = {
        "lightcone2": cone,
        "gate_p40_1_spatial_on": bool(
            cone["F"]["spatial_cone_median"] >= 4
            and (1 - cone["F"]["transport_recovery_max_d"])
            <= 0.5
            * max(1 - cone["D"]["transport_recovery_max_d"], 1e-9)
        ),
        "gate_p40_2_striving": bool(
            cone["F"]["median_recovery_sweeps"] is not None
            and cone["F"]["median_recovery_sweeps"] >= 5
            and cone["F"]["recovery_rate"] >= 0.8
        ),
        "gate_p40_3_temporal_retained": bool(
            cone["F"]["temporal_cone_median"]
            >= 0.8 * cone["D"]["temporal_cone_median"]
        ),
        "gate_p40_4_knife": bool(
            cone["F_lesion"]["spatial_cone_median"] == 0
        ),
    }

    by_key = {(entry["arm"], int(entry["tissue"])): entry for entry in entries}
    diagnostics = {}
    for label, comparison, seed in (
        ("F_minus_D", "D", 2026090240),
        ("F_minus_F_lesion", "F_lesion", 2026090241),
    ):
        differences = [
            float(by_key[("F", tissue)]["space"]["recovery_by_distance"]["8"])
            - float(
                by_key[(comparison, tissue)]["space"]["recovery_by_distance"]["8"]
            )
            for tissue in range(12)
        ]
        diagnostics[label] = {
            "mean_recovery_fraction_difference": float(np.mean(differences)),
            "paired_tissue_bootstrap_95": _bootstrap_mean_interval(
                differences, seed=seed
            ),
            "tissue_directions": _directions(differences),
            "tissue_differences": differences,
            "pairing_level": "same tissue parameter index, not shared trajectory RNG",
        }
    d_residual = 1 - cone["D"]["transport_recovery_max_d"]
    f_residual = 1 - cone["F"]["transport_recovery_max_d"]
    lesion_residual = 1 - cone["F_lesion"]["transport_recovery_max_d"]
    return {
        "integrity": integrity,
        "recalculated_gates": gates,
        "reported_gates": summary["gates"],
        "all_reported_gates_and_summaries_match": _recursive_close(
            gates, summary["gates"]
        ),
        "longest_distance_diagnostics": {
            **diagnostics,
            "aggregate_residual_error": {
                "D": d_residual,
                "F": f_residual,
                "F_lesion": lesion_residual,
            },
            "F_over_D_residual_error_ratio": f_residual / d_residual,
            "F_over_F_lesion_residual_error_ratio": f_residual / lesion_residual,
        },
        "design_audit": {
            "source_rng_namespace_includes_arm": (
                'seed_rng(config.trajectory_seed_tag + "-space", arm, index)'
                in pipeline
            ),
            "F_and_F_lesion_stream_matched_in_spatial_assay": False,
            "F_and_D_stream_matched_in_spatial_assay": False,
            "future_level_rows_retained": False,
            "fired_wave_counts_retained": False,
            "delivered_nudge_or_amplification_retained": False,
            "initial_and_final_absolute_errors_retained": False,
            "only_recovery_fraction_retained": True,
            "speed_assay_checks_immediate_post_insult_displacement": False,
            "median_recovery_one_can_distinguish_repair_from_no_displacement": False,
            "temporal_cone_hits_measurement_ceiling_in_all_arms": all(
                cone[arm]["temporal_cone_median"] == 21
                for arm in ("D", "F", "F_lesion")
            ),
            "P40_4_is_vacuous_because_active_F_cone_is_also_zero": (
                cone["F"]["spatial_cone_median"] == 0
                and cone["F_lesion"]["spatial_cone_median"] == 0
            ),
            "discovery_log_plus_0_08_value_present_in_final_summary": False,
            "retained_final_F_minus_D_recovery_fraction": (
                cone["F"]["transport_recovery_max_d"]
                - cone["D"]["transport_recovery_max_d"]
            ),
            "retained_final_F_minus_lesion_recovery_fraction": (
                cone["F"]["transport_recovery_max_d"]
                - cone["F_lesion"]["transport_recovery_max_d"]
            ),
        },
    }


def audit_e41(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/persuade2_summary.json")
    pipeline = tracker.add(
        root / "src/persuadability_2/pipeline.py"
    ).read_text(encoding="utf-8")
    gates = summary["gates"]
    info = gates["info_by_amplitude"]
    qualifying = [
        (float(amplitude), float(row["energy"]))
        for amplitude, row in info.items()
        if float(row["rate"]) >= 0.5
    ]
    best = min(qualifying, key=lambda pair: pair[1]) if qualifying else None
    recalculated = {
        "info_by_amplitude": info,
        "gate_p41_1_information_lever": bool(
            best is not None and best[1] <= 0.1 * 56.92
        ),
        "anchor_rewrite_success_F": float(gates["anchor_rewrite_success_F"]),
        "gate_p41_2_organizer_control_panel": bool(
            gates["anchor_rewrite_success_F"] >= 0.5
        ),
        "passive_info_success_D": float(gates["passive_info_success_D"]),
        "gate_p41_3_stubbornness_replicates": bool(
            gates["passive_info_success_D"] < 0.1
        ),
        "lesion_info_E": float(gates["lesion_info_E"]),
        "lesion_anchor_F": float(gates["lesion_anchor_F"]),
        "gate_p41_4_knife": bool(
            gates["lesion_info_E"] < 0.1 and gates["lesion_anchor_F"] < 0.1
        ),
    }
    cheap_bar = 0.1 * 56.92
    return {
        "integrity": {
            "config_digest": summary.get("config_digest"),
            "matches_expected_config": (
                summary.get("config_digest")
                == EXPECTED_CONFIG_DIGESTS["E41_persuadability_2"]
            ),
            "lowest_retained_unit": "one aggregate summary",
            "tissue_or_future_rows_retained": False,
        },
        "recalculated_gates": recalculated,
        "all_reported_gate_fields_match": _recursive_close(recalculated, gates),
        "finite_search": {
            "E_info_amplitudes": [0.6, 1.2, 2.4],
            "cue_generations": [3, 7, 11],
            "cue_blocks_requested_per_sign": 4,
            "n_tissues": 8,
            "futures": 32,
            "horizon_generations": 20,
            "nominal_tissue_arm_rows": 56,
            "nominal_future_runs": 56 * 32,
            "cheap_energy_bar": cheap_bar,
            "amplitudes_with_energy_at_or_below_cheap_bar": [
                float(amplitude)
                for amplitude, row in info.items()
                if float(row["energy"]) <= cheap_bar
            ],
            "nominal_successes_implied_by_each_E_info_mean_rate": {
                amplitude: int(round(float(row["rate"]) * 8 * 32))
                for amplitude, row in info.items()
            },
        },
        "knife_diagnostics": {
            "E_info_active_at_2_4": float(info["2.4"]["rate"]),
            "E_info_lesion_at_2_4": float(gates["lesion_info_E"]),
            "E_active_minus_lesion": float(
                info["2.4"]["rate"] - gates["lesion_info_E"]
            ),
            "F_anchor_active": float(gates["anchor_rewrite_success_F"]),
            "F_anchor_lesion": float(gates["lesion_anchor_F"]),
            "F_active_minus_lesion": float(
                gates["anchor_rewrite_success_F"] - gates["lesion_anchor_F"]
            ),
            "demonstrates_abolition_of_positive_active_effect": False,
            "vacuous_absolute_low_rate_gate": True,
        },
        "coupling_and_content_audit": {
            "target_geometry_selects_plus_and_minus_cue_locations": True,
            "current_coupling_sums_plus_and_minus_activity_unsigned": True,
            "current_coupling_transmits_cue_channel_sign_to_voltage": False,
            "E_info_uses_native_D_expectation_not_target_expectation": True,
            "E_info_effect_is_license_times_native_expectation_comparator": True,
            "active_and_lesion_rng_namespaces_share_arm_label": False,
            "active_and_lesion_rng_namespaces_are_distinct": (
                "config.trajectory_seed_tag, arm, index, amplitude" in pipeline
            ),
            "delivered_wave_activity_retained": False,
            "delivered_voltage_nudge_retained": False,
            "matched_amplifier_activation_across_content_conditions": False,
            "reference_density_ladder_tested": False,
            "P41_3_original_all_levers_on_D_implemented": False,
            "P41_3_later_D_info_only_gate_implemented": True,
            "content_insufficiency_discriminated_from_coupling_or_address": False,
        },
    }


def audit_e47(root: Path, tracker: InputTracker) -> dict[str, Any]:
    component = tracker.json(root / "results/full/component_amplifier.json")
    verdict = tracker.json(root / "results/full/battery_verdict.json")
    battery_source = tracker.add(
        root / "src/sealed_battery_3/battery.py"
    ).read_text(encoding="utf-8")
    gate = bool(component["sub"] < 1e-6 and component["supra"] >= 2.5)
    return {
        "integrity": {
            "component_config_digest": component.get("config_digest"),
            "verdict_config_digest": verdict.get("config_digest"),
            "matches_expected_config": (
                component.get("config_digest")
                == verdict.get("config_digest")
                == EXPECTED_CONFIG_DIGESTS["E47_sealed_battery_3"]
            ),
            "lowest_retained_unit": "aggregate across four fresh tissue indices",
            "per_tissue_values_retained": False,
        },
        "retained": {
            "sub": float(component["sub"]),
            "supra": float(component["supra"]),
            "reported_gate": bool(component["gate"]),
            "battery_verdict_amplifier": bool(verdict["verdict"]["amplifier"]),
        },
        "recalculated_gate": gate,
        "all_reported_booleans_match": bool(
            gate is component["gate"] is verdict["verdict"]["amplifier"]
        ),
        "design": {
            "tissue_indices": [300, 301, 302, 303],
            "configured_n_tissues": 8,
            "amplifier_component_tissues_used": 4,
            "separate_registered_rule": "sub < 1e-6 and supra >= 2.5 absolute endpoint L1 difference",
            "same_as_original_WAVE9_factor_gate": False,
            "amplifier_code_copied_into_battery_not_imported_from_pipeline": (
                "def component_amplifier" in battery_source
                and "from excitable_web.pipeline import amplification"
                not in battery_source
            ),
            "uses_current_excitable_engine": (
                "from excitable_web.engine import excitable_step" in battery_source
            ),
            "trajectory_seed_tag_read_by_amplifier_component": False,
            "fresh_tag_changes_deterministic_amplifier_component": False,
            "new_quenched_tissue_parameter_panel": True,
        },
    }


def run_l8_audit(plastic_root: Path) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    ideas = plastic_root / IDEAS_RELATIVE
    roots = {
        name: _experiment_root(plastic_root, name)
        for name in (
            "persuadability",
            "james_test",
            "excitable_web",
            "lightcone_2",
            "persuadability_2",
            "james_test_2",
            "sealed_battery_3",
            "contract_bridge",
            "xeno_bridge",
            "glider_test",
            "voltage_web",
            "setpoint_rewrite",
            "ladder_web",
            "anatomical_homeostasis",
        )
    }
    for root in roots.values():
        _track_package(tracker, root)
    for name in (
        "LAWS.md",
        "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        "WAVE8_PROPHECIES.md",
        "WAVE9_PROPHECIES.md",
        "WAVE10_PROPHECIES.md",
    ):
        tracker.add(ideas / name)
    manuscript = tracker.add(plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md")
    manuscript_text = manuscript.read_text(encoding="utf-8").lower()

    digests = source_config_digests()
    config_checks = {
        name: {
            "calculated": digests[name],
            "expected": expected,
            "matches": digests[name] == expected,
        }
        for name, expected in EXPECTED_CONFIG_DIGESTS.items()
    }
    if not all(check["matches"] for check in config_checks.values()):
        raise ValueError(f"source config transcription mismatch: {config_checks}")

    e37 = audit_e37(roots["persuadability"], tracker)
    e38 = audit_e38(roots["james_test"], tracker)
    e39 = audit_e39(plastic_root, roots["excitable_web"], tracker)
    e40 = audit_e40(roots["lightcone_2"], tracker)
    e41 = audit_e41(roots["persuadability_2"], tracker)
    e47 = audit_e47(roots["sealed_battery_3"], tracker)
    e42 = tracker.json(
        roots["james_test_2"] / "results/full/james2_summary.json"
    )
    if e42.get("config_digest") != EXPECTED_CONFIG_DIGESTS["E42_james_test_2"]:
        raise ValueError("E42 contextual summary config digest mismatch")

    current_replay = e39["current_source_replay"]
    claim_assessment = {
        "finite_E37_above_bare_sheet_cells_all_miss_absolute_half_bar": {
            "status": "SUPPORTED",
            "value": e37["all_B_C_D_cell_means_below_half"],
        },
        "E38_named_tasks_fail_or_are_void_on_executed_grid": {
            "status": "SUPPORTED_WITH_AGGREGATE_ONLY_LIMIT",
            "value": e38["interpretation"]["all_four_registered_gates_failed"],
        },
        "passive_sheet_has_no_amplifier": {
            "status": "NOT_DIRECTLY_TESTED",
            "reason": "E37/E38 measure task success, not an input-output amplification factor",
        },
        "no_field_at_any_strength": {
            "status": "NOT_CONFIRMED",
            "reason": "finite, partly redundant grid; no analytic exclusion or equivalence margin",
        },
        "E39_later_absolute_all_or_none_gate": {
            "status": "REPLAYED" if e39["later_absolute_gate"]["replayed_pass"] else "FAILED",
            "current_source_matches_retained": e39[
                "current_source_amplification_matches_retained"
            ],
        },
        "E39_original_registered_amplification_factor": {
            "status": "NOT_ADJUDICABLE_FROM_RETAINED_RESULT",
            "reason": "cue energy and the registered factor were never calculated or retained",
        },
        "E39_three_of_three_as_originally_registered": {
            "status": "NOT_CONFIRMED",
            "reason": "P39.1 estimand changed and P39.3 is only a test golden, not a retained summary gate",
        },
        "E39_current_source_goldens_all_pass": {
            "status": "SUPPORTED"
            if (
                current_replay["propagation_golden"]["passes_source_test_assertions"]
                and current_replay["refractory_golden"]["passes_source_test_assertion"]
                and current_replay["lesion_golden"]["allclose_at_1e_12"]
                and current_replay["conservation_golden"][
                    "all_current_source_test_assertions_pass"
                ]
            )
            else "FAILED",
        },
        "E47_separate_absolute_amplifier_seal": {
            "status": "SUPPORTED_AS_SEPARATELY_REGISTERED_AGGREGATE",
            "value": e47["recalculated_gate"],
        },
        "E40_E41_primary_competency_gates_did_not_switch_on": {
            "status": "SUPPORTED_FOR_NAMED_GATES",
            "value": bool(
                not e40["recalculated_gates"]["gate_p40_1_spatial_on"]
                and not e40["recalculated_gates"]["gate_p40_2_striving"]
                and not e41["recalculated_gates"]["gate_p41_1_information_lever"]
                and not e41["recalculated_gates"][
                    "gate_p41_2_organizer_control_panel"
                ]
            ),
        },
        "blanket_no_competency_restored_in_WAVE9": {
            "status": "OVERSTATED",
            "reason": "E42 P42.3 is reported true, although L07 found its causal design inadequate",
            "E42_reported_positive_gate": "gate_p42_3_generalization",
            "E42_value": bool(e42["gates"]["gate_p42_3_generalization"]),
        },
        "amplification_without_amplifiable_content_is_identified_mechanism": {
            "status": "NOT_CONFIRMED",
            "reason": (
                "delivered amplification was not retained in E40/E41; E41's current "
                "coupling discards channel sign and multiplies a different expectation; "
                "no matched content-resolution ladder was tested"
            ),
        },
        "biological_bioelectric_prediction": {
            "status": "UNTESTED_BY_SIMULATOR_RECORD",
        },
    }
    audit = {
        "schema_version": 1,
        "scope": "L08 retained field/amplifier audit plus 24-path E39 current-source replay",
        "outcome_blinding": "none; retained outcomes known before audit",
        "fresh_scientific_futures_generated": 0,
        "historical_current_source_arm_paths_replayed": E39_REPLAY_ARM_PATHS,
        "config_digest_checks": config_checks,
        "E37_persuadability": e37,
        "E38_james_test": e38,
        "E39_excitable_web": e39,
        "E40_lightcone_2": e40,
        "E41_persuadability_2": e41,
        "E42_context": {
            "config_digest": e42["config_digest"],
            "reported_gates": e42["gates"],
            "positive_registered_gate": "gate_p42_3_generalization",
            "positive_gate_value": bool(
                e42["gates"]["gate_p42_3_generalization"]
            ),
            "note": "causal limitations were adjudicated in the completed L07 audit",
        },
        "E47_amplifier_seal": e47,
        "claim_assessment": claim_assessment,
        "manuscript_v2_3": {
            "contains_E37_to_E47_package_specific_evidence": any(
                token in manuscript_text
                for token in (
                    "excitable_web",
                    "persuadability_2",
                    "fitzhugh",
                    "experiment 39",
                )
            ),
            "independent_support_for_L08": False,
        },
        "overall_verdict": "MIXED",
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, sorted(tracker.paths)


def markdown_report(audit: Mapping[str, Any]) -> str:
    e37 = audit["E37_persuadability"]
    e38 = audit["E38_james_test"]
    e39 = audit["E39_excitable_web"]
    e40 = audit["E40_lightcone_2"]
    e41 = audit["E41_persuadability_2"]
    e47 = audit["E47_amplifier_seal"]
    amp_retained = e39["retained"]["amplification"]
    amp_replay = e39["current_source_replay"]["current_source_amplification"]
    lines = [
        "# L08 retained field/amplifier audit and E39 replay",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`.",
        "",
        "The finite task failures largely reproduce, and current code still constructs a "
        "thresholded propagating response. The universal field exclusion, original "
        "registered amplification-factor claim, three-of-three label, and missing-content "
        "mechanism do not follow from the retained record.",
        "",
        "## E37 finite steering grid",
        "",
        f"All 512 rows and 64 summary cells match: `{e37['all_64_reported_cells_match']}`. "
        f"All implemented gates match: `{e37['all_reported_gates_match']}`.",
        "",
        "| Rung | Highest cell rate | Lever | Intensity | Descriptive tissue 95% interval |",
        "|---|---:|---|---:|---:|",
    ]
    for rung in RUNGS:
        row = e37["maximum_rate_cell_by_rung"][rung]
        interval = row["rate_tissue_bootstrap_95"]
        lines.append(
            f"| {rung} | {row['rate']:.6f} | {row['lever']} | {row['intensity']} | "
            f"[{interval[0]:.6f}, {interval[1]:.6f}] |"
        )
    lines.extend(
        [
            "",
            "Only two nominal cells cross the mean 0.5 bar, both rung-A L2 settings; "
            "the minimal table therefore contains one working rung/lever. Above A, "
            "the maxima are below 0.5, but this is an absolute-bar result, not "
            "equivalence to no response and not a measured gain curve. L1 and L4 use "
            "the same voltage operator. On B--D, all four nominal L2 durations have "
            "identical mean energy, consistent with the generation stopping rule "
            "collapsing the intended dose ladder.",
            "",
            "## E38 field tasks",
            "",
            f"All four aggregate gates fail: `{e38['interpretation']['all_four_registered_gates_failed']}`. "
            "The main run executes horizontal fields at 0.05/0.15/0.4 and vertical "
            "fields at 0.4; diagonal fields are implemented but never called. The only "
            "retained object is an aggregate summary. It does not retain the alleged "
            "x80 calibration, 0.89--0.93 dip, arrival denominators, or time series.",
            "",
            "## E39 amplifier and registration",
            "",
            "| Quantity | Retained | Current-source replay |",
            "|---|---:|---:|",
            f"| Sub endpoint L1 difference | {amp_retained['caused_sub']:.12g} | {amp_replay['caused_sub']:.12g} |",
            f"| Supra endpoint L1 difference | {amp_retained['caused_supra']:.12g} | {amp_replay['caused_supra']:.12g} |",
            f"| Later absolute gate | {amp_retained['gate_all_or_none']} | {amp_replay['gate_all_or_none']} |",
            "",
            f"Current-source replay matches the retained amplifier aggregate: "
            f"`{e39['current_source_amplification_matches_retained']}`. The propagation "
            f"golden passes `{e39['current_source_replay']['propagation_golden']['passes_source_test_assertions']}` "
            f"and the lesion maximum voltage delta is "
            f"`{e39['current_source_replay']['lesion_golden']['max_abs_voltage_delta']:.3g}`. "
            f"The current conservation test assertions all pass: "
            f"`{e39['current_source_replay']['conservation_golden']['all_current_source_test_assertions_pass']}`.",
            "",
            "The Wave-9 register required an amplification factor divided by cue energy "
            "and a supra factor >=10. The code instead stores an endpoint sum of absolute "
            "voltage differences and gates it at >0.5; it never computes cue energy. "
            "Accordingly the later absolute gate can pass while original P39.1 remains "
            "not adjudicable. The engine header/register describe signed `u+ - u-` "
            "coupling, while the current body contains E40's later unsigned license "
            "coupling. No versioned pre-E40 engine is retained.",
            "",
            "## E40/E41 downstream tests",
            "",
            "| E40 longest-distance comparison | Mean recovery-fraction difference | Tissue 95% interval | Directions +/0/- |",
            "|---|---:|---:|---:|",
        ]
    )
    for label in ("F_minus_D", "F_minus_F_lesion"):
        row = e40["longest_distance_diagnostics"][label]
        interval = row["paired_tissue_bootstrap_95"]
        direction = row["tissue_directions"]
        lines.append(
            f"| {label} | {row['mean_recovery_fraction_difference']:+.6f} | "
            f"[{interval[0]:+.6f}, {interval[1]:+.6f}] | "
            f"{direction['positive']}/{direction['tied']}/{direction['negative']} |"
        )
    lines.extend(
        [
            "",
            "E40's retained final panel has F slightly worse than both D and lesion, not "
            "a retained +0.08 benefit. Its arm name is part of the RNG namespace, and "
            "no firing or delivered-nudge values are retained. P40.1/P40.2 fail; P40.4 "
            "passes vacuously because both active and lesioned spatial cones are zero.",
            "",
            f"E41's active-minus-lesion effects are "
            f"`{e41['knife_diagnostics']['E_active_minus_lesion']:+.6f}` for E-info and "
            f"`{e41['knife_diagnostics']['F_active_minus_lesion']:+.6f}` for F-anchor. "
            "The current E-info path chooses target-signed cue channels but then sums "
            "both channel activities and multiplies the native expectation comparator, "
            "discarding the target sign. Delivered amplification is unrecorded and only "
            "one anchor density is tested. This cannot discriminate insufficient content "
            "from coupling/address/target limitations.",
            "",
            "## E47 and claim boundary",
            "",
            f"E47's separately registered absolute gate recalculates to "
            f"`{e47['recalculated_gate']}` (sub `{e47['retained']['sub']:.6g}`, supra "
            f"`{e47['retained']['supra']:.6g}`). It uses four new tissue indices, but "
            "the amplifier component does not read a fresh trajectory tag and remains "
            "the later absolute endpoint assay, not the original Wave-9 factor.",
            "",
            "E40/E41 do establish failure of their named primary gates. They do not "
            "establish that all competencies are absent: the same Wave-9 scorecard "
            "reports E42's generalization gate as positive, albeit with causal limitations "
            "already documented by the L07 audit.",
            "",
            "## Reproducibility boundary",
            "",
            f"Inputs hashed: {audit['input_file_count']}. Fresh scientific futures: 0. "
            f"Current-source historical arm paths replayed: "
            f"{audit['historical_current_source_arm_paths_replayed']}.",
            "",
        ]
    )
    return "\n".join(lines)
