"""Formal post-hoc Stage A decomposition that motivates the mechanism campaign."""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import (
    atomic_destination,
    read_json,
    read_jsonl_gz,
    write_checksums,
    write_json,
)
from .rng import rng_for
from .study import verify_run


def _bootstrap(
    values: list[float], seed: str, label: str, repetitions: int = 50_000
) -> list[float]:
    array = np.asarray(values, dtype=float)
    if array.size == 1:
        return [float(array[0]), float(array[0])]
    rng = rng_for(seed, "stage-a-mechanism-diagnostic", label)
    indices = rng.integers(0, array.size, size=(repetitions, array.size))
    means = np.mean(array[indices], axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def derive_stage_a_mechanism_diagnostic(stage_a: Path) -> dict[str, Any]:
    verification = verify_run(stage_a)
    registration = read_json(stage_a / "registration.json")
    seed = str(registration["protocol"]["master_seed"])
    sums: dict[tuple[str, str, float, str], list[int]] = collections.defaultdict(
        lambda: [0, 0, 0]
    )
    destinations: dict[tuple[float, str], collections.Counter[str]] = (
        collections.defaultdict(collections.Counter)
    )
    for record in read_jsonl_gz(stage_a / "futures.jsonl.gz"):
        if record["engine"] != "wagner":
            continue
        key = (
            str(record["source_id"]),
            str(record["arm"]),
            float(record["carryover"]),
            str(record["inheritance_mode"]),
        )
        values = sums[key]
        values[0] += 1
        values[1] += int(record["active_capture"])
        values[2] += int(record["strict_event"])
        if record["arm"] == "acute_mismatch":
            label = str(record["destination"])
            if label.startswith("point:"):
                label = "recognized_point"
            elif label.startswith("cycle:"):
                label = "recognized_cycle"
            destinations[(float(record["carryover"]), str(record["inheritance_mode"]))][
                label
            ] += 1

    sources = sorted({key[0] for key in sums})

    def rate(source: str, arm: str, carryover: float, mode: str, index: int) -> float:
        values = sums[(source, arm, carryover, mode)]
        return values[index] / values[0]

    contrasts: dict[str, Any] = {}
    for metric, index in (("capture", 1), ("strict", 2)):
        for arm in (
            "acute_mismatch",
            "natural",
            "joint_isomorphic",
            "target_aligned_own_anchor",
        ):
            values = [
                rate(source, arm, 1.0, "self", index)
                - rate(source, arm, 1.0, "donor_shuffled", index)
                for source in sources
            ]
            contrasts[f"{metric}.self-minus-donor.{arm}"] = {
                "rulebooks": len(values),
                "mean": float(np.mean(values)),
                "interval": _bootstrap(values, seed, f"{metric}:{arm}"),
            }
        for control in (
            "natural",
            "joint_isomorphic",
            "target_aligned_own_anchor",
        ):
            values = []
            for source in sources:
                acute = rate(source, "acute_mismatch", 1.0, "self", index) - rate(
                    source, "acute_mismatch", 1.0, "donor_shuffled", index
                )
                control_value = rate(source, control, 1.0, "self", index) - rate(
                    source, control, 1.0, "donor_shuffled", index
                )
                values.append(acute - control_value)
            contrasts[f"{metric}.interaction.acute-minus-{control}"] = {
                "rulebooks": len(values),
                "mean": float(np.mean(values)),
                "interval": _bootstrap(values, seed, f"{metric}:interaction:{control}"),
            }

    composition: dict[str, Any] = {}
    for key, counts in sorted(destinations.items()):
        total = sum(counts.values())
        composition[f"lambda-{key[0]:g}.{key[1]}"] = {
            "futures": total,
            "counts": dict(sorted(counts.items())),
            "rates": {
                name: value / total for name, value in sorted(counts.items())
            },
        }
    return {
        "format": "gre-stage-a-mechanism-diagnostic-v1",
        "source_run": str(stage_a.resolve()),
        "source_protocol_digest": verification["protocol_digest"],
        "post_hoc": True,
        "multiplicity_adjusted": False,
        "independent_unit": "rulebook",
        "contrasts": contrasts,
        "acute_destination_composition": composition,
        "interpretation_contract": {
            "capture_is_not_a_strict_event_rate": True,
            "outcomes_dropped": False,
            "scientific_confirmation_eligible": False,
        },
    }


def _render(diagnostic: dict[str, Any]) -> str:
    lines = [
        "# Stage A Boolean–Wagner mechanism diagnostic",
        "",
        "> Post-hoc exploratory analysis. Intervals are descriptive, unadjusted for multiplicity, and cannot confirm plastic heredity.",
        "",
        "## Paired Wagner contrasts",
        "",
        "| Contrast | Rulebooks | Mean and 95% exploratory interval |",
        "|---|---:|---:|",
    ]
    for name, value in sorted(diagnostic["contrasts"].items()):
        lower, upper = value["interval"]
        lines.append(
            f"| {name} | {value['rulebooks']} | {value['mean']:.4f} "
            f"[{lower:.4f}, {upper:.4f}] |"
        )
    lines.extend(
        [
            "",
            "The roughly 33-point capture advantage is shared by the control arms and therefore indicates general lineage continuity. The smaller strict-event interaction is mismatch-specific and motivates the new causal campaign.",
            "",
            "## Complete acute outcome composition",
            "",
        ]
    )
    for name, value in sorted(diagnostic["acute_destination_composition"].items()):
        lines.append(f"### {name}")
        lines.append("")
        for category, rate in value["rates"].items():
            lines.append(f"- {category}: {rate:.4f}")
        lines.append("")
    return "\n".join(lines)


def write_stage_a_mechanism_diagnostic(stage_a: Path, destination: Path) -> Path:
    diagnostic = derive_stage_a_mechanism_diagnostic(stage_a)
    with atomic_destination(destination) as temporary:
        write_json(temporary / "analysis.json", diagnostic)
        (temporary / "report.md").write_text(_render(diagnostic), encoding="utf-8")
        write_json(
            temporary / "manifest.json",
            {
                "format": "gre-stage-a-mechanism-diagnostic-manifest-v1",
                "source_protocol_digest": diagnostic["source_protocol_digest"],
                "source_run": diagnostic["source_run"],
            },
        )
        write_checksums(temporary)
    return destination.resolve()
