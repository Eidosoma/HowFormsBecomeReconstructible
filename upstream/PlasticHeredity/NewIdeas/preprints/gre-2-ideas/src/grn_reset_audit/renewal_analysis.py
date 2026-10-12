"""Descriptive analysis for the latent-memory renewal campaign."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .artifacts import atomic_write_text, read_jsonl, write_json


def _rows(path: Path) -> list[dict[str, Any]]:
    return list(read_jsonl(path)) if path.is_file() else []


def _median(rows: list[dict[str, Any]], endpoint: str) -> float | None:
    values = [
        float(row[endpoint]["learned_margin"])
        for row in rows
        if row.get("valid") and row.get(endpoint, {}).get("learned_margin") is not None
    ]
    return None if not values else float(np.median(values))


def _native_summary(decision: Mapping[str, Any]) -> dict[str, Any]:
    selected = decision.get("selected_boundary")
    return {
        "assay_valid": bool(decision.get("assay_valid")),
        "native_pass": bool(decision.get("native_pass")),
        "branch": decision.get("branch"),
        "selected_boundary": selected,
        "zero_carryover_identity": decision.get("zero_carryover_identity"),
        "trained_control_memory_count": decision.get("trained_control_memory_count"),
        "trained_control_model_count": decision.get("trained_control_model_count"),
    }


def _carrier_summary(
    screen: list[dict[str, Any]],
    recurrence: list[dict[str, Any]],
    nominations: list[dict[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    compact = [row for row in nominations if row.get("compact_gate_pass")]
    task_results: list[dict[str, Any]] = []
    for nomination in nominations:
        task = nomination["memory_task_id"]
        endpoint = nomination["endpoint"]
        base = {
            row["condition"].removeprefix("full-"): row
            for row in screen
            if row["memory_task_id"] == task and row["condition"].startswith("full-")
        }
        if not all(arm in base for arm in ("naive", "trained_no_reset", "combined_reset")):
            continue
        naive = float(base["naive"][endpoint]["learned_margin"])
        reference = max(
            abs(float(base["trained_no_reset"][endpoint]["learned_margin"]) - naive),
            1e-8,
        )
        rows = [
            row
            for row in recurrence
            if row["memory_task_id"] == task and int(row["generation"]) == 4
        ]
        values = {
            arm: _median([row for row in rows if row["arm"] == arm], endpoint)
            for arm in {
                "intact",
                "renewal_off",
                "erase",
                "rescue",
                "control_donor",
                "paired_donor",
            }
        }
        full = 0.0 if values["intact"] is None else abs(values["intact"] - naive)
        erase_removal = None if values["erase"] is None else 1.0 - abs(values["erase"] - naive) / max(full, 1e-8)
        rescue_restore = None if values["rescue"] is None else abs(values["rescue"] - naive) / max(full, 1e-8)
        renewal = None if values["renewal_off"] is None or values["intact"] is None else abs(values["intact"] - values["renewal_off"]) / reference
        control_specific = None if values["control_donor"] is None or values["intact"] is None else abs(values["intact"] - values["control_donor"]) / reference
        recurrent = bool(
            values["intact"] is not None
            and full / reference >= float(config["reference_effect_fraction"])
            and control_specific is not None
            and control_specific >= float(config["reference_effect_fraction"])
        )
        controls_pass = bool(
            erase_removal is not None
            and erase_removal >= float(config["carrier_ablation_fraction"])
            and rescue_restore is not None
            and rescue_restore >= float(config["carrier_transfer_fraction"])
        )
        task_results.append(
            {
                "memory_task_id": task,
                "model_id": nomination["model_id"],
                "selected_nodes": nomination["selected_nodes"],
                "compact_gate_pass": nomination["compact_gate_pass"],
                "generation4_recurrent": recurrent,
                "controls_pass": controls_pass,
                "renewal_dependence_ratio": renewal,
                "active_renewal": bool(
                    renewal is not None
                    and renewal >= float(config["renewal_dependence_fraction"])
                ),
                "erase_removal_fraction": erase_removal,
                "rescue_restore_fraction": rescue_restore,
                "control_specific_ratio": control_specific,
            }
        )
    recurrent = [row for row in task_results if row["generation4_recurrent"] and row["controls_pass"]]
    active = [row for row in recurrent if row["active_renewal"]]
    return {
        "nomination_count": len(nominations),
        "compact_carrier_count": len(compact),
        "recurrent_causal_count": len(recurrent),
        "active_renewal_count": len(active),
        "supporting_models": sorted({row["model_id"] for row in recurrent}),
        "task_results": task_results,
    }


def _mark_validation_summary(
    rows: list[dict[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    task_results: list[dict[str, Any]] = []
    tasks = sorted({row["memory_task_id"] for row in rows})
    for task in tasks:
        generation = [
            row
            for row in rows
            if row["memory_task_id"] == task and int(row["generation"]) == 4
        ]
        endpoint_results: dict[str, Any] = {}
        best_endpoint = None
        best_score = -math.inf
        for endpoint in ("recall", "relearn"):
            intact = {
                arm: _median(
                    [
                        row
                        for row in generation
                        if row["control"] == "intact" and row["history"] == arm
                    ],
                    endpoint,
                )
                for arm in ("naive", "trained_no_reset", "combined_reset", "control_only")
            }
            if any(value is None for value in intact.values()):
                rn = rc = consistency = 0.0
            else:
                reference = max(abs(intact["trained_no_reset"] - intact["naive"]), 1e-8)
                rn = abs(intact["combined_reset"] - intact["naive"]) / reference
                rc = abs(intact["combined_reset"] - intact["control_only"]) / reference
                reset_rows = [
                    row
                    for row in generation
                    if row["control"] == "intact" and row["history"] == "combined_reset" and row["valid"]
                ]
                naive_rows = [
                    row
                    for row in generation
                    if row["control"] == "intact" and row["history"] == "naive" and row["valid"]
                ]
                n = min(len(reset_rows), len(naive_rows))
                differences = np.asarray(
                    [
                        float(reset_rows[i][endpoint]["learned_margin"])
                        - float(naive_rows[i][endpoint]["learned_margin"])
                        for i in range(n)
                    ]
                )
                median = float(np.median(differences)) if n else 0.0
                consistency = 0.0 if not n or abs(median) <= 1e-12 else float(np.mean(np.sign(differences) == np.sign(median)))
            score = min(rn, rc)
            if score > best_score:
                best_score = score
                best_endpoint = endpoint
            endpoint_results[endpoint] = {
                "reset_naive_ratio": rn,
                "reset_control_ratio": rc,
                "direction_consistency": consistency,
                "signal": bool(
                    rn >= float(config["reference_effect_fraction"])
                    and rc >= float(config["reference_effect_fraction"])
                    and consistency >= float(config["direction_consistency_fraction"])
                ),
            }
        endpoint = str(best_endpoint)
        intact_naive = _median(
            [row for row in generation if row["control"] == "intact" and row["history"] == "naive"], endpoint
        )
        intact_reset = _median(
            [row for row in generation if row["control"] == "intact" and row["history"] == "combined_reset"], endpoint
        )
        trained = _median(
            [row for row in generation if row["control"] == "intact" and row["history"] == "trained_no_reset"], endpoint
        )
        full = 0.0 if intact_naive is None or intact_reset is None else abs(intact_reset - intact_naive)
        reference = 1e-8 if intact_naive is None or trained is None else max(abs(trained - intact_naive), 1e-8)
        controls: dict[str, Any] = {}
        for control in ("founder_write_off", "reader_off", "erase", "renewal_off", "rescue", "shuffle", "paired_donor", "sign_reverse"):
            value = _median([row for row in generation if row["control"] == control], endpoint)
            controls[control] = {
                "value": value,
                "effect_fraction": None if value is None or intact_naive is None else abs(value - intact_naive) / max(full, 1e-8),
            }
        removal_controls = ("founder_write_off", "reader_off", "erase")
        removal_pass = all(
            controls[name]["effect_fraction"] is not None
            and 1.0 - controls[name]["effect_fraction"]
            >= float(config["mark_control_removal_fraction"])
            for name in removal_controls
        )
        rescue_pass = bool(
            controls["rescue"]["effect_fraction"] is not None
            and controls["rescue"]["effect_fraction"]
            >= float(config["mark_rescue_fraction"])
        )
        renewal_ratio = None
        if controls["renewal_off"]["value"] is not None and intact_reset is not None:
            renewal_ratio = abs(intact_reset - controls["renewal_off"]["value"]) / reference
        signal = bool(any(row["signal"] for row in endpoint_results.values()))
        controls_pass = bool(removal_pass and rescue_pass)
        task_results.append(
            {
                "memory_task_id": task,
                "model_id": int(task.split("-")[0]),
                "signal": signal,
                "controls_pass": controls_pass,
                "pass": signal and controls_pass,
                "selected_endpoint": endpoint,
                "endpoints": endpoint_results,
                "renewal_dependence_ratio": renewal_ratio,
                "active_renewal": bool(
                    renewal_ratio is not None
                    and renewal_ratio >= float(config["renewal_dependence_fraction"])
                ),
                "controls": controls,
            }
        )
    passed = [row for row in task_results if row["pass"]]
    models = sorted({row["model_id"] for row in passed})
    return {
        "pass": bool(
            len(passed) >= int(config["mark_min_validation_memories"])
            and models == sorted(int(value) for value in config["mark_validation_models"])
        ),
        "pass_count": len(passed),
        "supporting_models": models,
        "active_renewal_count": sum(row["active_renewal"] for row in passed),
        "task_results": task_results,
    }


def analyze_renewal(output: Path, final_status: str = "completed") -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    decision_path = output / "branch-decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8")) if decision_path.is_file() else {}
    native = _rows(output / "native-renewal.jsonl")
    branch = decision.get("branch", "not-reached")
    carrier = None
    mark = None
    if branch == "native-carrier":
        nominations_path = output / "carrier-nominations.json"
        nominations = (
            json.loads(nominations_path.read_text(encoding="utf-8"))["nominations"]
            if nominations_path.is_file()
            else []
        )
        carrier = _carrier_summary(
            _rows(output / "carrier-screen.jsonl"),
            _rows(output / "native-recurrence.jsonl"),
            nominations,
            config,
        )
    elif branch == "engineered-mark":
        selection_path = output / "mark-selection.json"
        selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.is_file() else {"pass": False}
        validation = _rows(output / "mark-validation.jsonl")
        mark = {
            "selection": selection,
            "validation": _mark_validation_summary(validation, config) if validation else None,
        }
    expected_native = 928 if registration["profile"] == "full" else 544
    counts = {
        name: len(_rows(output / f"{name}.jsonl"))
        for name in ("native-renewal", "carrier-screen", "native-recurrence", "mark-grid", "mark-validation")
    }
    branch_complete = False
    if branch == "native-carrier":
        branch_complete = bool(
            counts["carrier-screen"]
            and counts["native-recurrence"] == 1536
            and carrier
            and carrier["nomination_count"] == 8
        )
    elif branch == "engineered-mark":
        selection = None if mark is None else mark["selection"]
        expected_grid = 2304 if registration["profile"] == "full" else 1152
        expected_validation = 1248 if registration["profile"] == "full" else 624
        branch_complete = bool(
            counts["mark-grid"] == expected_grid
            and selection is not None
            and (
                not selection.get("pass")
                or counts["mark-validation"] == expected_validation
            )
        )
    minimum_completion = bool(
        final_status == "completed"
        and len(native) == expected_native
        and decision.get("assay_valid")
        and branch_complete
    )
    if branch == "native-carrier":
        verdict = "native-renewal-candidate" if carrier and carrier["recurrent_causal_count"] else "native-screen-pass-without-causal-recurrence"
    elif branch == "engineered-mark":
        verdict = "engineered-renewable-mark-candidate" if mark and mark.get("validation") and mark["validation"]["pass"] else "no-engineered-mark-validation"
    else:
        verdict = "invalid-or-incomplete"
    hypotheses = [
        {
            "rank": 1,
            "hypothesis": verdict,
            "next_prediction": (
                "The nominated carrier survives a fresh model-held-out renewal assay."
                if branch == "native-carrier"
                else "A target-blind slow mark transfers task-specific relearning bias on fresh BioModels."
            ),
        },
        {
            "rank": 2,
            "hypothesis": "generic-state-carryover",
            "next_prediction": "Combined-reset and control-only lineages remain interchangeable after renewal.",
        },
    ]
    analysis = {
        "run_status": final_status,
        "scope": config["analysis_scope"],
        "cohort_size": 8,
        "model_count": 4,
        "record_counts": counts,
        "native": _native_summary(decision),
        "carrier": carrier,
        "mark": mark,
        "minimum_completion_gate": minimum_completion,
        "verdict": verdict,
        "hypotheses": hypotheses,
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    write_json(output / "hypotheses.json", {"scope": config["analysis_scope"], "ranking": hypotheses})
    lines = [
        "# Latent Memory Carrier x Renewal V1 report",
        "",
        f"**Run status:** `{final_status}`  ",
        f"**Minimum completion gate:** `{'PASS' if minimum_completion else 'FAIL'}`  ",
        f"**Executed branch:** `{branch}`  ",
        f"**Exploratory verdict:** `{verdict}`",
        "",
        "## Native renewal",
        "",
        f"- Assay valid: {bool(decision.get('assay_valid'))}.",
        f"- Native cohort gate: {bool(decision.get('native_pass'))}.",
        f"- Selected boundary: `{decision.get('selected_boundary')}`.",
    ]
    if carrier is not None:
        lines.extend(
            [
                "",
                "## Native carrier branch",
                "",
                f"- Compact carrier nominations: {carrier['compact_carrier_count']}/8.",
                f"- Causal generation-4 recurrence: {carrier['recurrent_causal_count']}/8.",
                f"- Active-renewal candidates: {carrier['active_renewal_count']}/8.",
            ]
        )
    if mark is not None:
        validation = mark.get("validation")
        lines.extend(
            [
                "",
                "## Engineered mark branch",
                "",
                f"- Discovery nomination: {mark['selection'].get('selected')}.",
                f"- Held-out validation pass: {None if validation is None else validation['pass']}.",
                f"- Held-out passing memories: {0 if validation is None else validation['pass_count']}/4.",
            ]
        )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            config["claim_boundary"],
            "Native expression copying is persistence unless bottleneck, causal, recurrence, and renewal-dependence controls also pass.",
        ]
    )
    atomic_write_text(output / "report.md", "\n".join(lines) + "\n")
    return analysis
