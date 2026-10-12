from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from fep_surprise_25 import analysis as base_analysis
from fep_surprise_25.config import ARMS, Campaign25Config
from fep_surprise_25.interventions import LAUNCH_METRIC_NAMES
from fep_surprise_25.worker import BASELINE_FEATURE_NAMES
from plastic_heredity.seeds import derive_seed

from .config import AMENDMENT_LABEL
from .worker import TERMINAL_CAUSE_CODES, load_design, load_futures


def _loss(y: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    probability = np.clip(prediction, 1e-12, 1.0 - 1e-12)
    return -(y * np.log(probability) + (1 - y) * np.log(1 - probability))


def _gain(
    data: dict[str, np.ndarray],
    mask: np.ndarray,
    labels: np.ndarray,
    baseline: np.ndarray,
    enhanced: np.ndarray,
    config: Campaign25Config,
    domain: str,
) -> dict[str, Any]:
    y = labels[mask].astype(np.int8)
    groups = data["matrix"][mask].astype(np.int64)
    base_prediction = base_analysis._crossfit(
        baseline[mask], y, groups, config.crossfit_folds, config.predictor_c
    )
    enhanced_prediction = base_analysis._crossfit(
        enhanced[mask], y, groups, config.crossfit_folds, config.predictor_c
    )
    local = {key: value[mask] for key, value in data.items()}
    _, values = base_analysis._matrix_values(
        local,
        np.ones(mask.sum(), dtype=bool),
        _loss(y, base_prediction) - _loss(y, enhanced_prediction),
    )
    result = base_analysis._paired_inference(
        values,
        config.bootstrap_repetitions,
        derive_seed(config.master_seed, domain),
    )
    result["prevalence"] = float(y.mean()) if len(y) else None
    result["rows"] = int(len(y))
    return result


def _completion_surprise(
    data: dict[str, np.ndarray], config: Campaign25Config
) -> dict[str, Any]:
    blocks: dict[str, dict[str, Any]] = {}
    pilot = np.stack(data["pilot"])
    for candidate in ("02", "03"):
        for branch_half in ("A", "B"):
            mask = (data["candidate"] == candidate) & (
                data["branch_half"] == branch_half
            )
            block = f"c{candidate}_half{branch_half}"
            blocks[block] = {}
            for half in range(2):
                result = _gain(
                    data,
                    mask,
                    data["complete"],
                    pilot,
                    np.stack(data[f"shelf_{half}"]),
                    config,
                    f"experiment25a.analysis.completion-surprise.{block}.{half}",
                )
                blocks[block][f"shelf_half{half}_gain"] = result
    family = {
        f"{block}_atlas{half}": values[f"shelf_half{half}_gain"]
        for block, values in blocks.items()
        for half in range(2)
    }
    base_analysis._apply_holm(family)
    return {
        "blocks": blocks,
        "all_blocks": bool(family and all(value["pass"] for value in family.values())),
    }


def _goldilocks_surface(
    data: dict[str, np.ndarray], config: Campaign25Config
) -> dict[str, Any]:
    pilot = np.stack(data["pilot"])
    regime = np.stack(data["regime"])
    physical_width = len(BASELINE_FEATURE_NAMES) + len(LAUNCH_METRIC_NAMES) + len(ARMS)
    source_break = regime[:, physical_width]
    target_sigma = pilot[:, len(BASELINE_FEATURE_NAMES)]
    source_centered = source_break - 0.5
    sigma_centered = target_sigma - 3.25
    engineered = np.column_stack(
        [
            source_centered**2,
            sigma_centered**2,
            source_centered * sigma_centered,
            source_centered**2 * sigma_centered,
            source_centered * sigma_centered**2,
        ]
    )
    surface = np.column_stack([pilot, engineered])
    output: dict[str, Any] = {
        "features": [
            "(source_break_probability-0.5)^2",
            "(target_log_beta_sigma-3.25)^2",
            "source_centered*target_centered",
            "source_centered^2*target_centered",
            "source_centered*target_centered^2",
        ],
        "outcomes": {},
    }
    for outcome in ("strict8", "complete"):
        blocks: dict[str, dict[str, Any]] = {}
        for candidate in ("02", "03"):
            for branch_half in ("A", "B"):
                mask = (data["candidate"] == candidate) & (
                    data["branch_half"] == branch_half
                )
                block = f"c{candidate}_half{branch_half}"
                blocks[block] = _gain(
                    data,
                    mask,
                    data[outcome],
                    pilot,
                    surface,
                    config,
                    f"experiment25a.analysis.goldilocks-surface.{outcome}.{block}",
                )
        base_analysis._apply_holm(blocks)
        output["outcomes"][outcome] = {
            "blocks": blocks,
            "all_blocks": bool(blocks and all(value["pass"] for value in blocks.values())),
        }
    return output


def _viability_boundary(cells: Path) -> dict[str, Any]:
    references: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    futures: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    reverse_codes = {value: key for key, value in TERMINAL_CAUSE_CODES.items()}
    for design_path in sorted(cells.glob("cell_*_design.joblib")):
        design = load_design(design_path)
        metadata = design["metadata"]
        prefix = f"{metadata['stratum']}::c{metadata['candidate']}"
        for atlas, values in metadata["reference"].items():
            key = f"{prefix}::{atlas}"
            references[key]["requested_lineages"] += int(values["requested_lineages"])
            references[key]["complete_lineages"] += int(values["complete_lineages"])
            references[key]["terminal_prefixes"] += int(values["terminal_prefixes"])
            references[key]["raw_retained_states"] += int(values["raw_retained_states"])
            references[key]["cells"] += 1
            references[key]["dominant_fraction_sum"] += float(
                values["mean_dominant_molecule_fraction"]
            )
            references[key]["effective_species_sum"] += float(
                values["mean_effective_species"]
            )
            for cause, count in values["terminal_causes"].items():
                references[key][f"terminal_{cause.lower()}"] += int(count)
        future = load_futures(
            design_path.with_name(design_path.name.replace("_design.joblib", "_futures.joblib"))
        )
        for arm_index, arm in enumerate(ARMS):
            key = f"{prefix}::{arm}"
            complete = np.asarray(future["complete"][:, arm_index])
            causes = np.asarray(future["terminal_cause"][:, arm_index])
            futures[key]["branches"] += int(complete.size)
            futures[key]["complete"] += int(complete.sum())
            for code, name in reverse_codes.items():
                if code:
                    futures[key][f"terminal_{name.lower()}"] += int(np.count_nonzero(causes == code))
    reference_output = {}
    for key, values in references.items():
        total = max(values["requested_lineages"], 1.0)
        reference_output[key] = {
            **{
                name: int(value)
                for name, value in values.items()
                if not name.endswith("_sum")
            },
            "completion_fraction": float(values["complete_lineages"] / total),
            "mean_dominant_molecule_fraction": float(
                values["dominant_fraction_sum"] / max(values["cells"], 1.0)
            ),
            "mean_effective_species": float(
                values["effective_species_sum"] / max(values["cells"], 1.0)
            ),
        }
    future_output = {}
    for key, values in futures.items():
        total = max(values["branches"], 1.0)
        future_output[key] = {
            **{name: int(value) for name, value in values.items()},
            "completion_fraction": float(values["complete"] / total),
        }
    return {"reference": reference_output, "main": future_output}


def analyze_confirmation(
    cells: Path,
    config: Campaign25Config,
    destination: Path,
    integrity: dict[str, bool],
) -> dict[str, Any]:
    metrics = base_analysis.analyze_confirmation(cells, config, destination, integrity)
    data = base_analysis._rows(cells)
    completion = _completion_surprise(data, config)
    surface = _goldilocks_surface(data, config)
    viability = _viability_boundary(cells)
    strict_incremental = bool(metrics["prediction"]["shelf_surprise_all_blocks"])
    completion_incremental = bool(completion["all_blocks"])
    if config.profile != "full":
        classification = "NONSCIENTIFIC_PROFILE"
    elif strict_incremental and not completion_incremental:
        classification = "REHOMING_SPECIFIC_INFORMATION"
    elif completion_incremental and not strict_incremental:
        classification = "GENERAL_VIABILITY_INFORMATION"
    elif strict_incremental and completion_incremental:
        classification = "BROAD_DYNAMIC_INFORMATION"
    else:
        classification = "NO_INCREMENTAL_INFORMATION"
    metrics["format"] = "fep-surprise-25a-metrics-v1"
    metrics["decision"]["integrity_verdict"] = (
        "VALID_WITH_PREOUTCOME_AMENDMENT"
        if all(integrity.values())
        else "INVALID"
    )
    metrics["decision"]["secondary_information_classification"] = classification
    metrics["decision"]["amendment_secondary_not_a_primary_rescue"] = True
    metrics["decision"]["claim_boundary"] = (
        "Simulator-specific viability, regime-gated rehoming, and calibrated-surprise "
        "results only; no variational-free-energy, active-inference, autonomy, cognition, "
        "prebiotic-chemistry, universal-origin, or Platonic-causation claim."
    )
    metrics["amendment"] = {
        "label": AMENDMENT_LABEL,
        "completion_surprise": completion,
        "goldilocks_surface": surface,
        "viability_boundary": viability,
    }
    (destination / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    decision = metrics["decision"]
    report = (
        "# Experiment 2.5a — Goldilocks Boundary report\n\n"
        f"- Integrity: **{decision['integrity_verdict']}**\n"
        f"- Original regime gate: **{decision['regime_verdict']}**\n"
        f"- Dynamic prediction: **{decision['dynamic_prediction_verdict']}**\n"
        f"- Strict-8 conditional surprise: **{decision['fep_incremental_verdict']}**\n"
        f"- Secondary viability classification: **{classification}**\n"
        f"- Durability: **{decision['durability_verdict']}**\n\n"
        "The amendment-born viability and continuous Goldilocks analyses are secondary and "
        "cannot rescue an original primary gate. The claim boundary in `metrics.json` is "
        "part of this adjudication.\n"
    )
    (destination / "REPORT.md").write_text(report, encoding="utf-8")
    return metrics


__all__ = ["analyze_confirmation"]
