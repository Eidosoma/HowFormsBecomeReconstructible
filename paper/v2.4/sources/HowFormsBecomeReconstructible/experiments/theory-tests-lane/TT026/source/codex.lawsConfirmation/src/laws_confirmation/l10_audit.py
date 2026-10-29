"""Outcome-known retained/replay audit for L10's honest-stress claim."""

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E38_james_test": "73cc6c7ad0efe66d519b30278138367eb035516b6cdb6743568e62cd28dd0fe4",
    "E42_james_test_2": "95f2f959571d81d7fb9e4732c0e27007f853bc97b9a477b8e93620a0c4fca57d",
    "E46_round2_james_test_3": "23793e8eeffc223a5ae82725a4e596028a47fa688b9354091376cd3975f4bfda",
    "E50_james_final": "673ad23f3661725b97aebaf33515850811dbc88d70a9c84209d7d118c66b2728",
}

E46_ROUND1_DIGEST = "b1d144c12f8084ae79f444133390d1b129ebb83dee845ddcbd2ebcad6af299c2"
REPLAY_FUTURES = {
    "E42_james_test_2": 80 * 24,
    "E46_round2_james_test_3": 70 * 16,
    "E50_james_final": 70 * 16,
}


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


def source_config_digests() -> dict[str, str]:
    """Independently transcribed defaults used by the four final summaries."""

    configs: dict[str, dict[str, Any]] = {
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
        "E46_round2_james_test_3": {
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
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def ema_response(rho: float = 0.002) -> dict[str, Any]:
    """Exact fixed-V response of the discrete EMA used by blueprint_step."""

    if not 0.0 < rho < 1.0:
        raise ValueError("rho must lie strictly between zero and one")
    decay = 1.0 - rho
    times = (100, 200, 500, 800, 1200)
    thresholds = {
        "50_percent": 0.5,
        "one_over_e": math.exp(-1.0),
        "20_percent": 0.2,
        "5_percent": 0.05,
        "1_percent": 0.01,
    }
    first_sweeps = {
        name: int(math.ceil(math.log(level) / math.log(decay)))
        for name, level in thresholds.items()
    }
    return {
        "rho": rho,
        "one_over_rho": 1.0 / rho,
        "exact_discrete_e_folding_sweeps": -1.0 / math.log(decay),
        "residual_fraction": {str(t): decay**t for t in times},
        "first_integer_sweep_at_or_below": first_sweeps,
        "residual_after_one_over_rho": decay ** int(round(1.0 / rho)),
        "one_time_constant_is_expiration": False,
        "fixed_V_special_case_only": True,
    }


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


def _distribution(values: Iterable[float | int | None]) -> dict[str, Any]:
    data = np.asarray([float(value) for value in values if value is not None], dtype=float)
    if data.size == 0:
        return {"n": 0, "min": None, "q25": None, "median": None,
                "mean": None, "q75": None, "max": None}
    quantiles = np.quantile(data, (0.25, 0.5, 0.75))
    return {
        "n": int(data.size),
        "min": float(data.min()),
        "q25": float(quantiles[0]),
        "median": float(quantiles[1]),
        "mean": float(data.mean()),
        "q75": float(quantiles[2]),
        "max": float(data.max()),
    }


def _truthy(value: Any) -> bool:
    """Match the historical adjudicators' `if value` eligibility rule."""

    return bool(value)


def _registered_fields(
    rows: list[dict[str, Any]], *, settle_key: str, include_chronic: bool = False
) -> dict[str, Any]:
    arrivals_by_zap: dict[str, float | None] = {}
    for zap in (4, 8, 16):
        values = [
            row["median_arrival"]
            for row in rows
            if row["zap_sweeps"] == zap
            and row["replica"] == 0
            and not row.get("pre_zap", False)
            and _truthy(row["median_arrival"])
        ]
        arrivals_by_zap[str(zap)] = float(np.median(values)) if values else None
    locks = [
        abs(float(row[settle_key]) - float(row["median_arrival"]))
        for row in rows
        if not row.get("pre_zap", False)
        and _truthy(row["median_arrival"])
        and _truthy(row[settle_key])
    ]
    valid = [value for value in arrivals_by_zap.values() if _truthy(value)]
    result: dict[str, Any] = {
        "arrival_by_zap": arrivals_by_zap,
        "arrival_spread": (
            float(max(valid) / max(min(valid), 1e-9)) if len(valid) >= 2 else None
        ),
        "median_lock": float(np.median(locks)) if locks else None,
    }
    if include_chronic:
        chronic = [
            float(row["chronic_excess"])
            for row in rows
            if not row.get("pre_zap", False) and row["chronic_excess"] is not None
        ]
        result["chronic_excess_mean"] = float(np.mean(chronic)) if chronic else None
    return result


def _bootstrap_lock_interval(
    rows: list[dict[str, Any]], *, settle_key: str, seed: int, draws: int = 4096
) -> list[float] | None:
    by_tissue: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        if _truthy(row.get("median_arrival")) and _truthy(row.get(settle_key)):
            by_tissue[int(row["tissue"])].append(
                abs(float(row[settle_key]) - float(row["median_arrival"]))
            )
    tissues = sorted({int(row["tissue"]) for row in rows})
    if not tissues or not any(by_tissue.values()):
        return None
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(draws):
        selected = rng.choice(tissues, size=len(tissues), replace=True)
        values = [value for tissue in selected for value in by_tissue[int(tissue)]]
        if values:
            stats.append(float(np.median(values)))
    if not stats:
        return None
    return [float(x) for x in np.quantile(stats, (0.025, 0.975))]


def summarize_replay_rows(
    rows: list[dict[str, Any]],
    *,
    settle_key: str,
    futures_per_row: int,
    horizon: int,
    bootstrap_seed: int,
    include_chronic: bool = False,
) -> dict[str, Any]:
    """Recalculate the registered lock and disclose its censoring/weighting."""

    registered = _registered_fields(
        rows, settle_key=settle_key, include_chronic=include_chronic
    )

    def summarize_group(group: list[dict[str, Any]]) -> dict[str, Any]:
        arrivals = [row["median_arrival"] for row in group if _truthy(row["median_arrival"])]
        settles = [row[settle_key] for row in group if _truthy(row[settle_key])]
        eligible = [
            row for row in group
            if _truthy(row["median_arrival"]) and _truthy(row[settle_key])
        ]
        signed = [
            float(row[settle_key]) - float(row["median_arrival"])
            for row in eligible
        ]
        locks = [abs(value) for value in signed]
        arrived_futures = int(round(sum(
            float(row["recovery_rate"]) * futures_per_row for row in group
        )))
        result: dict[str, Any] = {
            "rows": len(group),
            "futures": len(group) * futures_per_row,
            "arrived_futures": arrived_futures,
            "nonarrival_futures": len(group) * futures_per_row - arrived_futures,
            "arrival_eligible_rows": len(arrivals),
            "settling_eligible_rows": len(settles),
            "lock_eligible_rows": len(eligible),
            "excluded_from_lock_rows": len(group) - len(eligible),
            "recovery_rate": _distribution([row["recovery_rate"] for row in group]),
            "median_arrival": _distribution(arrivals),
            "cessation_sweep": _distribution(settles),
            "signed_cessation_minus_arrival": _distribution(signed),
            "cessation_chronology": {
                "before_arrival": sum(value < 0 for value in signed),
                "at_arrival": sum(value == 0 for value in signed),
                "after_arrival": sum(value > 0 for value in signed),
            },
            "absolute_lock": _distribution(locks),
            "cessation_at_horizon_rows": sum(
                row[settle_key] == horizon for row in group if row[settle_key] is not None
            ),
            "cessation_at_first_admissible_zap_plus_4_rows": sum(
                row[settle_key] == row["zap_sweeps"] + 4
                for row in group if row[settle_key] is not None
            ),
        }
        if include_chronic:
            result["chronic_excess"] = _distribution(
                [row.get("chronic_excess") for row in group]
            )
        return result

    by_zap = {
        str(zap): summarize_group([row for row in rows if row["zap_sweeps"] == zap])
        for zap in (4, 8, 16)
    }
    replica_zero = [row for row in rows if row["replica"] == 0]
    base_locks = [
        abs(float(row[settle_key]) - float(row["median_arrival"]))
        for row in replica_zero
        if _truthy(row["median_arrival"]) and _truthy(row[settle_key])
    ]
    replica_zero_zap_medians: dict[str, float | None] = {}
    for zap in (4, 8, 16):
        values = [
            abs(float(row[settle_key]) - float(row["median_arrival"]))
            for row in replica_zero
            if row["zap_sweeps"] == zap
            and _truthy(row["median_arrival"])
            and _truthy(row[settle_key])
        ]
        replica_zero_zap_medians[str(zap)] = (
            float(np.median(values)) if values else None
        )
    zap_medians = [
        value for value in replica_zero_zap_medians.values() if value is not None
    ]
    compact_rows = [
        {
            key: row.get(key)
            for key in (
                "tissue", "zap_sweeps", "replica", "recovery_rate",
                "median_arrival", settle_key, "total_fires", "chronic_excess",
            )
            if key in row
        }
        for row in rows
    ]
    return {
        "registered": registered,
        "overall": summarize_group(rows),
        "by_zap": by_zap,
        "weighting": {
            "rows_by_zap": {str(zap): sum(row["zap_sweeps"] == zap for row in rows)
                            for zap in (4, 8, 16)},
            "registered_median_all_rows": registered["median_lock"],
            "replica_zero_tissue_zap_median": (
                float(np.median(base_locks)) if base_locks else None
            ),
            "replica_zero_median_by_zap": replica_zero_zap_medians,
            "median_of_zap_specific_replica_zero_medians": (
                float(np.median(zap_medians)) if zap_medians else None
            ),
            "longest_zap_is_replica_overweighted": (
                sum(row["zap_sweeps"] == 16 for row in rows)
                > sum(row["zap_sweeps"] == 8 for row in rows)
            ),
        },
        "tissue_bootstrap_95_registered_median": _bootstrap_lock_interval(
            rows, settle_key=settle_key, seed=bootstrap_seed
        ),
        "rows": compact_rows,
    }


def _replay_e42() -> tuple[list[dict[str, Any]], float]:
    from james_test_2.config import James2Config
    from james_test_2.pipeline import zap_recovery

    config = James2Config()
    started = time.monotonic()
    rows = []
    for tissue in range(config.n_tissues):
        for zap in config.zap_sweeps_ladder:
            rows.append(zap_recovery(config, "F", "F", None, tissue, zap))
    for tissue in range(config.n_tissues):
        for replica in range(1, config.replica_streams):
            rows.append(zap_recovery(
                config, "F", "F", None, tissue,
                config.zap_sweeps_ladder[-1], replica,
            ))
    return rows, time.monotonic() - started


def _replay_e46() -> tuple[list[dict[str, Any]], float]:
    from james_test_3.config import James3Config
    from james_test_3.pipeline import zap_run

    config = James3Config()
    started = time.monotonic()
    rows = []
    for tissue in range(config.n_tissues):
        for zap in config.zap_sweeps_ladder:
            rows.append(zap_run(config, "H", tissue, zap))
    for tissue in range(config.n_tissues):
        for replica in range(1, config.replica_streams):
            rows.append(zap_run(
                config, "H", tissue, config.zap_sweeps_ladder[-1], replica
            ))
    return rows, time.monotonic() - started


def _replay_e50() -> tuple[list[dict[str, Any]], float]:
    from james_final.config import JamesFinalConfig
    from james_final.pipeline import zap_run

    config = JamesFinalConfig()
    started = time.monotonic()
    rows = []
    for tissue in range(config.n_tissues):
        for zap in config.zap_sweeps_ladder:
            rows.append(zap_run(config, "T", tissue, zap))
    for tissue in range(config.n_tissues):
        for replica in range(1, config.replica_streams):
            rows.append(zap_run(
                config, "T", tissue, config.zap_sweeps_ladder[-1], replica
            ))
    return rows, time.monotonic() - started


def _replay_all(retained: Mapping[str, Any]) -> dict[str, Any]:
    e42_rows, e42_seconds = _replay_e42()
    e42 = summarize_replay_rows(
        e42_rows,
        settle_key="last_fire_sweep",
        futures_per_row=24,
        horizon=80,
        bootstrap_seed=2026090210,
    )
    e42_expected = {
        "arrival_by_zap": retained["E42"]["gates"]["arrival_by_zap"],
        "arrival_spread": retained["E42"]["gates"]["arrival_spread"],
        "median_lock": retained["E42"]["gates"]["median_fire_arrival_lock"],
    }
    e42["elapsed_seconds"] = e42_seconds
    e42["retained_cessation_fields"] = e42_expected
    e42["reconstructs_retained_cessation_fields"] = _recursive_close(
        e42["registered"], e42_expected
    )

    e46_rows, e46_seconds = _replay_e46()
    e46 = summarize_replay_rows(
        e46_rows,
        settle_key="activity_settle_sweep",
        futures_per_row=16,
        horizon=100,
        bootstrap_seed=2026090211,
    )
    e46_expected = {
        "arrival_by_zap": retained["E46_round2"]["gates"]["arrival_by_zap"],
        "arrival_spread": retained["E46_round2"]["gates"]["arrival_spread"],
        "median_lock": retained["E46_round2"]["gates"]["median_activity_arrival_lock"],
    }
    e46["elapsed_seconds"] = e46_seconds
    e46["retained_cessation_fields"] = e46_expected
    e46["reconstructs_retained_cessation_fields"] = _recursive_close(
        e46["registered"], e46_expected
    )

    e50_rows, e50_seconds = _replay_e50()
    e50 = summarize_replay_rows(
        e50_rows,
        settle_key="stress_settle_sweep",
        futures_per_row=16,
        horizon=100,
        bootstrap_seed=2026090212,
        include_chronic=True,
    )
    e50_expected = {
        "arrival_by_zap": {"4": None, "8": None, "16": None},
        "arrival_spread": retained["E50"]["gates"]["arrival_spread"],
        "median_lock": retained["E50"]["gates"]["median_stress_arrival_lock"],
        "chronic_excess_mean": retained["E50"]["gates"]["chronic_excess_mean"],
    }
    e50["elapsed_seconds"] = e50_seconds
    e50["retained_cessation_fields"] = e50_expected
    e50["reconstructs_retained_cessation_fields"] = _recursive_close(
        e50["registered"], e50_expected
    )
    return {
        "E42": e42,
        "E46_round2": e46,
        "E50": e50,
        "all_retained_cessation_fields_reconstruct": all(
            item["reconstructs_retained_cessation_fields"]
            for item in (e42, e46, e50)
        ),
        "elapsed_seconds": e42_seconds + e46_seconds + e50_seconds,
        "historical_rows_replayed": len(e42_rows) + len(e46_rows) + len(e50_rows),
        "historical_simulator_futures_replayed": sum(REPLAY_FUTURES.values()),
    }


def _adoption_curve(root: Path, tracker: InputTracker) -> dict[str, Any]:
    payloads = [
        tracker.json(root / "results/full/work" / f"triangle_shard_{i:02d}_of_04.json")
        for i in range(4)
    ]
    entries = [entry for payload in payloads for entry in payload["entries"]]
    curves = [entry["adoption_curve"] for entry in entries if entry["kind"] == "adoption"]
    means = np.asarray(curves, dtype=float).mean(axis=0)
    return {
        "n_tissues": len(curves),
        "sweeps": [200, 400, 600, 800, 1000, 1200],
        "mean_R_sign_agreement_with_initial_imposed_target": [float(x) for x in means],
        "is_abs_R_minus_V_stress_trajectory": False,
        "V_target_held_after_initialization": False,
        "supports_exact_expiration_at_500_sweeps": False,
    }


def run_l10_audit(
    plastic_root: Path, *, replay: bool = True
) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    workspace = Path(__file__).resolve().parents[2]
    ideas = plastic_root / IDEAS_RELATIVE
    roots = {
        name: _experiment_root(plastic_root, name)
        for name in (
            "james_test", "james_test_2", "james_test_3", "james_final",
            "ladder_web", "excitable_web", "growing_web", "blueprint_web",
            "triangle_final", "setpoint_rewrite", "voltage_web",
            "glider_test", "contract_bridge",
        )
    }
    for root in roots.values():
        _track_package(tracker, root)

    documents = {
        "LAWS": ideas / "LAWS.md",
        "WAVE8": ideas / "WAVE8_PROPHECIES.md",
        "WAVE9": ideas / "WAVE9_PROPHECIES.md",
        "WAVE10": ideas / "WAVE10_PROPHECIES.md",
        "WAVE11": ideas / "WAVE11_PROPHECIES.md",
        "DISCOVERY": ideas / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        "DISCUSSION": ideas / "RULIAD_DISCUSSION.md",
        "MANUSCRIPT": plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        "PROTOCOL": workspace / "protocols/L10_RETAINED_REPLAY_AUDIT_V1.md",
        "LAW_CASE": workspace / "laws/L10_honest_stress_currency.md",
        "L07_REVIEW": workspace / "reviews/L07_RETAINED_AUDIT_2026-09-02.md",
        "L08_REVIEW": workspace / "reviews/L08_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        "L09_REVIEW": workspace / "reviews/L09_RETAINED_AUDIT_2026-09-02.md",
    }
    texts = {name: _read(tracker, path) for name, path in documents.items()}
    source_texts = {
        "E38": _read(tracker, roots["james_test"] / "src/james_test/pipeline.py"),
        "E42": _read(tracker, roots["james_test_2"] / "src/james_test_2/pipeline.py"),
        "E46": _read(tracker, roots["james_test_3"] / "src/james_test_3/pipeline.py"),
        "E50": _read(tracker, roots["james_final"] / "src/james_final/pipeline.py"),
        "BLUEPRINT": _read(tracker, roots["blueprint_web"] / "src/blueprint_web/engine.py"),
    }

    result_paths = {
        "E38": roots["james_test"] / "results/full/james_summary.json",
        "E42": roots["james_test_2"] / "results/full/james2_summary.json",
        "E46_round1": roots["james_test_3"] / "results/full/james3_round1_magnitudeE.json",
        "E46_round2": roots["james_test_3"] / "results/full/james3_summary.json",
        "E50": roots["james_final"] / "results/full/jamesfinal_summary.json",
    }
    retained = {name: tracker.json(path) for name, path in result_paths.items()}
    digests = source_config_digests()
    config_matches = {
        name: digests[name] == EXPECTED_CONFIG_DIGESTS[name] for name in digests
    }

    sequence = [
        {
            "datum": "field-error predecessor",
            "experiment": "E38 final",
            "retained_lock": retained["E38"]["gates"]["median_stress_arrival_lock"],
            "signal": "batch-mean baseline-corrected smoothed abs(E-V)",
            "arrival": "per-future normalized 15-bin census cosine > 0.9",
            "horizon": 120,
            "futures_per_row": 32,
            "gate_passed": retained["E38"]["gates"]["gate_p38_2_cessation"],
            "qualification": "arrival spread is 1 and the tilt task was void",
            "included_in_claimed_30_15_6_5_sequence": False,
        },
        {
            "datum": "30",
            "experiment": "E42 final",
            "retained_lock": retained["E42"]["gates"]["median_fire_arrival_lock"],
            "signal": "last sweep any future in a 24-future batch fires an FHN channel",
            "arrival": "per-future normalized 15-bin census cosine > 0.9 after release",
            "horizon": 80,
            "futures_per_row": 24,
            "gate_passed": retained["E42"]["gates"]["gate_p42_2_cessation"],
            "source_law_label": "field-error stress",
            "code_level_signal_label": "error-triggered wave firing",
        },
        {
            "datum": "15",
            "experiment": "E46 round 1",
            "retained_lock": retained["E46_round1"]["gates"]["median_activity_arrival_lock"],
            "signal": "batch-mean accepted-swap activity; first threshold crossing",
            "arrival": "per-future normalized 15-bin census cosine > 0.9 after release",
            "horizon": 100,
            "futures_per_row": 16,
            "gate_passed": retained["E46_round1"]["gates"]["gate_p46_2_cessation"],
            "development_round": "magnitude-E chemotaxis",
            "exact_source_tree_retained": False,
        },
        {
            "datum": "6.5",
            "experiment": "E46 round 2",
            "retained_lock": retained["E46_round2"]["gates"]["median_activity_arrival_lock"],
            "signal": "batch-mean accepted-swap activity; first threshold crossing",
            "arrival": "per-future normalized 15-bin census cosine > 0.9 after release",
            "horizon": 100,
            "futures_per_row": 16,
            "gate_passed": retained["E46_round2"]["gates"]["gate_p46_2_cessation"],
            "development_round": "sign-E chemotaxis with new trajectory and motility tags",
            "same_experiment_and_signal_as_15": True,
        },
        {
            "datum": "completion attempt",
            "experiment": "E50 final",
            "retained_lock": retained["E50"]["gates"]["median_stress_arrival_lock"],
            "signal": "batch-mean abs(R-V)",
            "arrival": "per-future positional sign match > 0.8 to pre-zap map",
            "horizon": 100,
            "futures_per_row": 16,
            "gate_passed": retained["E50"]["gates"]["gate_p50_1_cessation"],
            "qualification": "no naive arrivals; chronic excess 0.596",
        },
    ]

    source_audit = {
        "headline_has_three_comparable_signal_levels": False,
        "actual_field_error_E38_lock": retained["E38"]["gates"]["median_stress_arrival_lock"],
        "headline_30_is_E42_error_triggered_wave_firing": True,
        "headline_15_and_6_5_are_two_rounds_of_E46_swap_activity": True,
        "wave_firing_value_15_found": False,
        "currency_match_variable_declared_or_manipulated": False,
        "common_signal_definition": False,
        "common_arrival_observer_across_E42_E46_E50": False,
        "common_horizon": False,
        "shared_random_streams_across_sequence": False,
        "all_headline_cessation_gates_pass": False,
        "E42_last_fire_is_union_over_batch": (
            "fire_series.append(int(fired.sum()))" in source_texts["E42"]
            and "if f > 0" in source_texts["E42"]
        ),
        "E46_baseline_is_collected_during_zap": (
            "if sweep <= zap_sweeps" in source_texts["E46"]
        ),
        "E46_settling_is_first_threshold_crossing": (
            "settle_sweep = zap_sweeps + i + 1" in source_texts["E46"]
            and "break" in source_texts["E46"]
        ),
        "E46_settling_requires_remaining_below_threshold": (
            "all(" in source_texts["E46"][
                source_texts["E46"].find("# Activity cessation"):
                source_texts["E46"].find("return {", source_texts["E46"].find("# Activity cessation"))
            ]
        ),
        "E50_stress_is_batch_mean_abs_R_minus_V": (
            "float(np.abs(Rf - V).mean())" in source_texts["E50"]
        ),
        "blueprint_rho_is_direct_update_coefficient": (
            "Rf = Rf + bp.rho * (V - Rf)" in source_texts["BLUEPRINT"]
        ),
        "conditional_rows_are_missing_at_random": False,
        "causal_monotone_currency_trend_identified": False,
    }

    ema = ema_response(0.002)
    adoption = _adoption_curve(roots["triangle_final"], tracker)
    replay_result = _replay_all(retained) if replay else {
        "status": "NOT_RUN",
        "historical_rows_replayed": 0,
        "historical_simulator_futures_replayed": 0,
    }
    replay_matches = bool(
        replay and replay_result["all_retained_cessation_fields_reconstruct"]
    )

    claim_assessment = {
        "currency_match_monotonically_improves_goal_locked_cessation": {
            "status": "NOT_CONFIRMED",
            "reason": (
                "No currency-match variable is manipulated. The headline mixes E42 "
                "wave firing with two development rounds of E46 swap activity."
            ),
        },
        "reported_30_15_6_5_values_are_comparable": {
            "status": "REFUTED_BY_SOURCE_TRACE",
            "reason": (
                "Signal reduction, development round, horizon, baseline, and row "
                "weighting differ; the law's field/wave/swap labels do not match "
                "the retained experiment record."
            ),
        },
        "unreachable_goals_cause_persistent_stress": {
            "status": "NOT_CONFIRMED_AS_CAUSAL_OR_GENERAL",
            "reason": (
                "E42 supplies one persistent error-triggered firing case but no "
                "reachability test or matched reachable-reference intervention."
            ),
        },
        "E42_persistent_batch_level_firing": {
            "status": "CONFIRMED_CURRENT_SOURCE_REPLAY" if replay_matches else "NOT_CONFIRMED",
            "reason": (
                "The retained aggregate is reproduced, but last-fire is the union "
                "over a batch and locks exclude rows without both events."
            ),
        },
        "self_written_reference_expires_at_exactly_one_time_constant": {
            "status": "NOT_MEASURED_AND_EXACT_EXPIRATION_FALSE",
            "reason": (
                "E50 ends at 100 sweeps, versus 1/rho=500, and reports chronic "
                "excess 0.596. Under fixed V, one time constant leaves about "
                "36.8% of the initial error."
            ),
        },
        "EMA_has_a_slow_exponential_tracking_scale": {
            "status": "CONFIRMED_ANALYTICALLY_FOR_FIXED_V",
            "reason": "The implemented recurrence gives residual (1-rho)^t exactly when V is fixed.",
        },
        "clock_is_an_emergent_measurement": {
            "status": "REFUTED",
            "reason": (
                "The cited 1/rho scale is built into the update coefficient and was "
                "not measured by E50 over a sufficient horizon."
            ),
        },
        "biological_reprogramming_prediction": {
            "status": "NOT_CONFIRMED",
            "reason": "No biological experiment tests the proposed stress signature.",
        },
    }

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L10",
        "audit_kind": "outcome-known retained-source audit with focused historical replays",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed": (
            replay_result["historical_simulator_futures_replayed"]
        ),
        "source_config_digests": digests,
        "source_config_digest_matches": config_matches,
        "all_final_source_config_digests_match": all(config_matches.values()),
        "E46_round1": {
            "retained_config_digest": retained["E46_round1"]["config_digest"],
            "expected_digest": E46_ROUND1_DIGEST,
            "digest_matches_retained_record": (
                retained["E46_round1"]["config_digest"] == E46_ROUND1_DIGEST
            ),
            "current_round2_source_digest": digests["E46_round2_james_test_3"],
            "current_source_is_round1_source": (
                digests["E46_round2_james_test_3"] == E46_ROUND1_DIGEST
            ),
            "lower_rows_retained": False,
        },
        "retained_gate_summaries": {
            name: value["gates"] for name, value in retained.items()
        },
        "signal_and_clock_inventory": sequence,
        "source_comparability_audit": source_audit,
        "focused_replay": replay_result,
        "EMA_fixed_V_analysis": ema,
        "E49_adoption_curve_context": adoption,
        "E50_clock_claim_audit": {
            "rho": 0.002,
            "recovery_horizon": 100,
            "one_over_rho": 500,
            "horizon_fraction_of_one_over_rho": 0.2,
            "retained_naive_arrival": retained["E50"]["gates"]["naive_arrival"],
            "retained_lock": retained["E50"]["gates"]["median_stress_arrival_lock"],
            "retained_chronic_excess": retained["E50"]["gates"]["chronic_excess_mean"],
            "expiration_observed": False,
            "exact_one_time_constant_inferred_from_update_dial": True,
        },
        "claim_assessment": claim_assessment,
        "overall_verdict": "MIXED" if replay_matches else "NOT_CONFIRMED",
        "replacement_wording": (
            "In the current lattice implementations, E42 shows persistent "
            "batch-level error-triggered wave firing after a census-based recovery "
            "endpoint, while E46's final motility round shows a shorter conditional "
            "swap-activity lock. These values use different signals and do not "
            "identify a causal currency law. A self-written EMA reference has a "
            "built-in exponential tracking scale; E50 does not observe its "
            "expiration or establish an exact one-time-constant stress transient."
        ),
        "manuscript_v2_3_independent_support": any(
            phrase in texts["MANUSCRIPT"].lower()
            for phrase in ("honest stress", "blueprint mourns", "stress currency")
        ),
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, sorted(tracker.paths)


def markdown_report(audit: Mapping[str, Any]) -> str:
    replay = audit["focused_replay"]
    ema = audit["EMA_fixed_V_analysis"]
    lines = [
        "# L10 retained/replay honest-stress audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`.",
        "",
        "The repository preserves real model-local observations, but not a causal "
        "currency law. The advertised sequence mixes error-triggered wave firing "
        "with two development rounds of the same swap-activity experiment, and its "
        "field/wave/swap labels do not match the executable record.",
        "",
        "## Claimed clock sequence",
        "",
        "| Record | Lock | Actual signal | Gate |",
        "|---|---:|---|---|",
    ]
    for row in audit["signal_and_clock_inventory"]:
        lock = "undefined" if row["retained_lock"] is None else str(row["retained_lock"])
        lines.append(
            f"| {row['experiment']} | {lock} | {row['signal']} | "
            f"{'pass' if row['gate_passed'] else 'fail'} |"
        )
    if replay.get("status") != "NOT_RUN":
        lines.extend([
            "",
            "## Focused replay and censoring",
            "",
            "| Experiment | Registered lock | Eligible / rows | Arrived futures | "
            "Replica-0 median | Reconstructs? |",
            "|---|---:|---:|---:|---:|---|",
        ])
        for key in ("E42", "E46_round2", "E50"):
            item = replay[key]
            overall = item["overall"]
            lock = item["registered"]["median_lock"]
            base = item["weighting"]["replica_zero_tissue_zap_median"]
            lines.append(
                f"| {key} | {lock if lock is not None else 'undefined'} | "
                f"{overall['lock_eligible_rows']} / {overall['rows']} | "
                f"{overall['arrived_futures']} / {overall['futures']} | "
                f"{base if base is not None else 'undefined'} | "
                f"{item['reconstructs_retained_cessation_fields']} |"
            )
    lines.extend([
        "",
        "## EMA calculation",
        "",
        f"At `rho={ema['rho']}`, `1/rho={ema['one_over_rho']:.0f}` sweeps, while "
        f"the exact discrete e-folding time is "
        f"`{ema['exact_discrete_e_folding_sweeps']:.6f}` sweeps. After 500 sweeps "
        f"the fixed-V recurrence retains "
        f"`{ema['residual_after_one_over_rho']:.6f}` of the initial error; it has "
        "not expired.",
        "",
        "| Target residual | First sweep at/below |",
        "|---|---:|",
    ])
    for name, sweep in ema["first_integer_sweep_at_or_below"].items():
        lines.append(f"| {name.replace('_', ' ')} | {sweep} |")
    lines.extend([
        "",
        "## Claim verdicts",
        "",
        "| Claim | Verdict |",
        "|---|---|",
    ])
    for claim, finding in audit["claim_assessment"].items():
        lines.append(f"| {claim.replace('_', ' ')} | `{finding['status']}` |")
    lines.extend([
        "",
        "## Replacement wording",
        "",
        str(audit["replacement_wording"]),
        "",
        "## Reproducibility",
        "",
        f"- Inputs hashed: {audit['input_file_count']}",
        f"- Final config digests match: {audit['all_final_source_config_digests_match']}",
        f"- Retained cessation fields replay: "
        f"{replay.get('all_retained_cessation_fields_reconstruct', False)}",
        "- Fresh scientific futures: 0",
        f"- Historical simulator futures replayed: "
        f"{audit['historical_simulator_futures_replayed']}",
        "",
    ])
    return "\n".join(lines)
