#!/usr/bin/env python3
"""Seal and execute FEP–PH1's constant-correlation analysis amendment.

This module remains outside ``fep_ph1`` so the source tree named by the
original registration stays byte-for-byte unchanged. The amendment is sealed
before this module reads aggregate scientific outcomes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fep_lab.integrity import (  # noqa: E402
    canonical_json_bytes,
    read_json,
    seal_directory,
    sha256_bytes,
    sha256_file,
    verify_seal,
    write_json,
)
from fep_ph1 import analysis as original_analysis  # noqa: E402
from fep_ph1.campaign import (  # noqa: E402
    profile_root,
    registration_path,
    verify_registration,
)
from fep_ph1.config import ExperimentConfig, profile_config  # noqa: E402


AMENDMENT_SCHEMA = "fep-ph1-analysis-amendment-1-v1"
AMENDMENT_DIRECTORY = "amendment-1"
ANALYSIS_DIRECTORY = "analysis-amendment-1"
AMENDMENT_SOURCE_NAMES = (
    "EXPERIMENT_FEP_PH1_ANALYSIS_AMENDMENT_1.md",
    "scripts/amend_fep_ph1_constant_correlation.py",
    "scripts/run_fep_ph1_analysis_amendment.sh",
)


def _source_hashes() -> dict[str, str]:
    paths = {name: PROJECT_ROOT / name for name in AMENDMENT_SOURCE_NAMES}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing amendment sources: {missing}")
    return {name: sha256_file(path) for name, path in sorted(paths.items())}


def _safe_spearman(
    predictor: np.ndarray, outcome: np.ndarray
) -> dict[str, float | int | str | None]:
    left = np.asarray(predictor, dtype=np.float64)
    right = np.asarray(outcome, dtype=np.float64)
    if left.shape != right.shape:
        raise ValueError("Spearman inputs differ in shape")
    mask = np.isfinite(left) & np.isfinite(right)
    left = left[mask]
    right = right[mask]
    pairs = int(left.size)
    reason: str | None = None
    if pairs < 3:
        reason = "insufficient_pairs"
    elif bool(np.all(left == left[0])):
        reason = "constant_probe"
    elif bool(np.all(right == right[0])):
        reason = "constant_outcome"
    if reason is not None:
        return {"rho": None, "p_exploratory": None, "pairs": pairs, "undefined_reason": reason}
    statistic, probability = spearmanr(left, right)
    if not (np.isfinite(statistic) and np.isfinite(probability)):
        return {
            "rho": None,
            "p_exploratory": None,
            "pairs": pairs,
            "undefined_reason": "undefined_by_scipy",
        }
    return {
        "rho": float(statistic),
        "p_exploratory": float(probability),
        "pairs": pairs,
        "undefined_reason": None,
    }


def _number_or_nan(value: Any) -> float:
    return float(value) if value is not None else float("nan")


def amended_dynamic_correlations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["family"],
            row["channel"],
            row["regime"],
            row["controller"],
        ): row
        for row in rows
    }
    groups = sorted(
        {
            (row["candidate"], row["family"], row["channel"], row["regime"])
            for row in rows
        }
    )
    matrix_ids = sorted({int(row["matrix_id"]) for row in rows})
    output: list[dict[str, Any]] = []
    for group in groups:
        probe: list[float] = []
        viability: list[float] = []
        heredity: list[float] = []
        for matrix_id in matrix_ids:
            active = index.get((matrix_id, *group, "ai_pooled"))
            noop = index.get((matrix_id, *group, "noop"))
            if active is None or noop is None:
                continue
            probe.append(_number_or_nan(active.get("amplification_probe")))
            viability.append(
                _number_or_nan(active.get("completion_fraction"))
                - _number_or_nan(noop.get("completion_fraction"))
            )
            heredity.append(
                _number_or_nan(active.get("inherited_fixed_fraction"))
                - _number_or_nan(noop.get("inherited_fixed_fraction"))
            )
        viability_result = _safe_spearman(np.asarray(probe), np.asarray(viability))
        heredity_result = _safe_spearman(np.asarray(probe), np.asarray(heredity))
        output.append(
            {
                "candidate": group[0],
                "family": group[1],
                "channel": group[2],
                "regime": group[3],
                "matrices": len(probe),
                "viability_rho": viability_result["rho"],
                "viability_p_exploratory": viability_result["p_exploratory"],
                "viability_pairs": viability_result["pairs"],
                "viability_undefined_reason": viability_result["undefined_reason"],
                "heredity_rho": heredity_result["rho"],
                "heredity_p_exploratory": heredity_result["p_exploratory"],
                "heredity_pairs": heredity_result["pairs"],
                "heredity_undefined_reason": heredity_result["undefined_reason"],
            }
        )
    return output


def _dependency_state(
    run_root: Path, config: ExperimentConfig
) -> tuple[ExperimentConfig, dict[str, Any]]:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    required = ("fit", "simulation", "replay")
    failed = [name for name in required if not verify_seal(root / name)]
    if failed:
        raise RuntimeError(f"registered dependency seals failed: {failed}")
    replay = read_json(root / "replay" / "replay.json")
    if replay.get("all_exact") is not True:
        raise RuntimeError("registered FEP-PH1 replay is not exact")
    registration = read_json(registration_path(run_root, config.profile))
    simulation_cells = sorted((root / "simulation" / "cells").glob("*.npz"))
    replay_cells = replay.get("cells", [])
    if len(simulation_cells) != 3_072 or len(replay_cells) != 3_072:
        raise RuntimeError(
            "full cell count drift: "
            f"simulation={len(simulation_cells)} replay={len(replay_cells)}"
        )
    if any(
        not bool(item.get("array_exact") and item.get("metadata_exact"))
        for item in replay_cells
    ):
        raise RuntimeError("one or more evaluation cells did not replay exactly")
    return resolved, {
        "registration_id": registration["registration_id"],
        "registration_sha256": sha256_file(
            registration_path(run_root, config.profile)
        ),
        "fit_seal_id": read_json(root / "fit" / "seal.json")["seal_id"],
        "simulation_seal_id": read_json(root / "simulation" / "seal.json")[
            "seal_id"
        ],
        "replay_seal_id": read_json(root / "replay" / "seal.json")["seal_id"],
        "simulation_cells": len(simulation_cells),
        "replay_cells": len(replay_cells),
        "replay_all_exact": True,
    }


def _amendment_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / AMENDMENT_DIRECTORY


def _analysis_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / ANALYSIS_DIRECTORY


def seal_amendment(run_root: Path, config: ExperimentConfig) -> Path:
    destination = _amendment_path(run_root, config.profile)
    if destination.exists():
        verify_amendment(run_root, config)
        return destination
    _resolved, dependencies = _dependency_state(run_root, config)
    root = profile_root(run_root, config.profile)
    original_analysis = root / "analysis"
    if verify_seal(original_analysis):
        raise RuntimeError("original analysis unexpectedly has a valid seal")
    partial_files = {
        str(path.relative_to(original_analysis)): sha256_file(path)
        for path in sorted(original_analysis.rglob("*"))
        if path.is_file()
    }
    runner_log = root / "fep-ph1.log"
    payload: dict[str, Any] = {
        "schema": AMENDMENT_SCHEMA,
        "profile": config.profile,
        "status": "sealed_after_exact_replay_before_aggregate_result_inspection",
        "trigger": {
            "exception": "ValueError: Out of range float values are not JSON compliant: nan",
            "warning": "ConstantInputWarning",
            "failed_stage": "analysis_json_serialization",
            "original_analysis_sealed": False,
            "partial_analysis_files": partial_files,
            "runner_status": (
                (root / "fep-ph1.status").read_text(encoding="utf-8").strip()
                if (root / "fep-ph1.status").is_file()
                else None
            ),
            "runner_log_sha256": sha256_file(runner_log),
        },
        "policy": {
            "finite_pairs_only": True,
            "minimum_pairs": 3,
            "constant_probe_representation": None,
            "constant_outcome_representation": None,
            "undefined_is_not_zero": True,
            "nonconstant_estimator": "scipy.stats.spearmanr",
            "data_regeneration": False,
            "original_failed_analysis_preserved": True,
            "integrity_label": "VALID_WITH_POSTOUTCOME_MECHANICAL_ANALYSIS_AMENDMENT",
        },
        "observation_boundary": (
            "Only process and seal metadata, the traceback and warning, artifact "
            "counts and sizes, and replay exactness were inspected. No aggregate "
            "outcome, contrast, interval, event rate, or correlation direction "
            "was viewed before this amendment seal."
        ),
        "dependencies": dependencies,
        "sources": _source_hashes(),
    }
    payload["amendment_id"] = sha256_bytes(canonical_json_bytes(payload))
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "amendment.json", payload)
    (destination / "README.md").write_text(
        "# Sealed FEP–PH1 analysis amendment 1\n\n"
        f"Amendment ID: `{payload['amendment_id']}`\n\n"
        "Undefined constant-series rank correlations are recorded as null; "
        "the registered data and exact replay remain unchanged.\n",
        encoding="utf-8",
    )
    seal_directory(destination, ("amendment.json", "README.md"))
    return destination


def verify_amendment(
    run_root: Path, config: ExperimentConfig
) -> dict[str, Any]:
    destination = _amendment_path(run_root, config.profile)
    if not verify_seal(destination):
        raise RuntimeError("FEP-PH1 amendment seal verification failed")
    payload = read_json(destination / "amendment.json")
    if payload.get("schema") != AMENDMENT_SCHEMA:
        raise RuntimeError("unsupported FEP-PH1 amendment schema")
    identifier = payload.pop("amendment_id")
    if sha256_bytes(canonical_json_bytes(payload)) != identifier:
        raise RuntimeError("FEP-PH1 amendment identifier mismatch")
    payload["amendment_id"] = identifier
    if payload["sources"] != _source_hashes():
        raise RuntimeError("FEP-PH1 amendment source drifted")
    _resolved, dependencies = _dependency_state(run_root, config)
    if payload["dependencies"] != dependencies:
        raise RuntimeError("FEP-PH1 amendment dependency drifted")
    return payload


def _report(metrics: dict[str, Any], output: Path) -> None:
    decision = metrics["decision"]
    lines = [
        "# FEP–PH Experiment 1 exploratory atlas — amended analysis",
        "",
        f"- Integrity: **{decision['integrity_verdict']}**",
        f"- Scientific status: **{decision['scientific_status']}**",
        f"- Registration: `{metrics['registration_id']}`",
        f"- Amendment: `{metrics['amendment_id']}`",
        f"- Matrix-level controller rows: {metrics['matrix_rows']:,}",
        f"- Descriptive contrasts: {len(metrics['contrasts']):,}",
        "",
        "The registered simulation and exact replay are unchanged. This "
        "post-outcome mechanical amendment records mathematically undefined "
        "constant-series Spearman correlations as null rather than NaN.",
        "",
        "This remains an exploratory atlas with no positive/negative "
        "classifier. F12 and strict-8 are descriptive readouts only.",
        "",
        "A favorable contrast demonstrates engineered steering in reconstructed "
        "GARD, not intrinsic active inference, an emergent Markov blanket, an "
        "inherited controller, prebiotic chemistry, or a universal FEP mechanism.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_amended(run_root: Path, config: ExperimentConfig) -> Path:
    amendment = verify_amendment(run_root, config)
    resolved, dependencies = _dependency_state(run_root, config)
    output = _analysis_path(run_root, config.profile)
    if output.exists():
        if verify_analysis(run_root, config):
            return output
        raise RuntimeError("unsealed amended analysis directory already exists")
    simulation = profile_root(run_root, config.profile) / "simulation"
    rows: list[dict[str, Any]] = []
    for path in sorted((simulation / "cells").glob("*.npz")):
        rows.extend(original_analysis._cell_rows(path, resolved))
    if not rows:
        raise RuntimeError("amended FEP-PH1 analysis found no simulation cells")
    output.mkdir(parents=True, exist_ok=False)
    original_analysis._save_matrix_rows(rows, output / "matrix_metrics.npz")
    summaries = original_analysis._group_summaries(rows, resolved)
    contrasts = original_analysis._contrasts(rows, resolved)
    dynamic = amended_dynamic_correlations(rows)
    decision = {
        "integrity_verdict": "VALID_WITH_POSTOUTCOME_MECHANICAL_ANALYSIS_AMENDMENT",
        "scientific_status": "EXPLORATORY_ATLAS_COMPLETE",
        "positive_negative_classifier": None,
        "strict_events_are_descriptive_only": True,
    }
    metrics = {
        "schema": "fep-ph1-analysis-amendment-1-results-v1",
        "profile": config.profile,
        "registration_id": dependencies["registration_id"],
        "amendment_id": amendment["amendment_id"],
        "replay_seal_id": dependencies["replay_seal_id"],
        "matrix_rows": len(rows),
        "decision": decision,
        "undefined_correlation_policy": amendment["policy"],
        "group_summaries": summaries,
        "contrasts": contrasts,
        "dynamic_regime_correlations": dynamic,
        "claim_boundary": (
            "Engineered active-inference steering map in reconstructed GARD; not "
            "intrinsic GARD inference, emergent blankets, inherited controllers, "
            "prebiotic chemistry, or a universal FEP mechanism."
        ),
    }
    write_json(output / "metrics.json", metrics)
    figures = original_analysis._figures(summaries, contrasts, output / "figures")
    _report(metrics, output / "REPORT.md")
    seal_directory(
        output,
        ("metrics.json", "matrix_metrics.npz", "REPORT.md", *figures),
    )
    return output


def verify_analysis(run_root: Path, config: ExperimentConfig) -> bool:
    output = _analysis_path(run_root, config.profile)
    if not verify_seal(output):
        return False
    amendment = verify_amendment(run_root, config)
    metrics = read_json(output / "metrics.json")
    return bool(
        metrics.get("amendment_id") == amendment["amendment_id"]
        and metrics.get("registration_id")
        == amendment["dependencies"]["registration_id"]
        and metrics.get("replay_seal_id")
        == amendment["dependencies"]["replay_seal_id"]
        and metrics.get("decision", {}).get("scientific_status")
        == "EXPLORATORY_ATLAS_COMPLETE"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seal", "analyze", "verify", "all"))
    parser.add_argument("--profile", choices=("full",), default="full")
    parser.add_argument("--run-root", type=Path, default=Path("runs-fep-ph1"))
    args = parser.parse_args()
    config = profile_config(args.profile)
    if args.command in ("seal", "all"):
        print(f"amendment: {seal_amendment(args.run_root, config)}", flush=True)
    if args.command in ("analyze", "all"):
        print(f"analysis: {analyze_amended(args.run_root, config)}", flush=True)
    if args.command == "verify":
        print(f"amendment: {verify_amendment(args.run_root, config)['amendment_id']}")
        print(f"analysis: {verify_analysis(args.run_root, config)}")


if __name__ == "__main__":
    main()
