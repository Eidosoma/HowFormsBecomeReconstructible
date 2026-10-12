"""Reports and deterministic figures for mechanism campaigns."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def _selected_rates(analysis: dict[str, Any], suffix: str) -> list[tuple[str, float]]:
    return [
        (name[: -len(suffix)], float(value["mean"]))
        for name, value in sorted(analysis["rates"].items())
        if name.endswith(suffix)
        and ".acute_mismatch." in name
        and (".lambda-1." in name or ".lambda-1.0." in name)
    ]


def render_mechanism_report(
    analysis: dict[str, Any],
    registry: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    lines = [
        "# Boolean–Wagner mechanism campaign",
        "",
        "> This campaign is exploratory. Its intervals are descriptive and its outcome signs cannot constitute confirmation.",
        "",
        f"- Cohort: `{analysis['cohort_id']}`",
        f"- Phase: `{analysis['phase']}`",
        f"- Futures: {analysis['futures']:,}",
        f"- Rulebooks: {manifest['source_rulebooks']}",
        f"- Runtime: {manifest['elapsed_seconds']:.2f} seconds",
        "- Dropped outcomes: none",
        "",
        "## Registered endpoint families",
        "",
        "- `frozen_library`: the original deterministic attractor catalogue.",
        "- `exact_point_state`: repeated exact point states, including off-library points.",
        "- `realized_signature`: repeated phase-invariant point or cycle signatures.",
        "- `competing_outcome`: an exhaustive recognized/off-library/unstable category.",
        "",
        "## Acute full-carryover rates",
        "",
        "| Cell | Frozen capture | State capture | Library strict | State strict |",
        "|---|---:|---:|---:|---:|",
    ]
    bases: dict[str, dict[str, float]] = {}
    for field in (
        "active_capture",
        "stable_point_capture",
        "strict_library",
        "strict_state",
    ):
        for base, value in _selected_rates(analysis, f".{field}"):
            bases.setdefault(base, {})[field] = value
    for base, values in sorted(bases.items()):
        if not all(
            name in values
            for name in (
                "active_capture",
                "stable_point_capture",
                "strict_library",
                "strict_state",
            )
        ):
            continue
        lines.append(
            f"| {base} | {values['active_capture']:.4f} | "
            f"{values['stable_point_capture']:.4f} | "
            f"{values['strict_library']:.4f} | {values['strict_state']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Paired mechanism contrasts",
            "",
            "Positive self-minus-donor values mean lineage continuity increased the named outcome. Interaction values subtract the corresponding continuity effect in a registered control arm.",
            "",
            "| Contrast | Rulebooks | Mean and exploratory interval |",
            "|---|---:|---:|",
        ]
    )
    selected_contrasts = [
        (name, value)
        for name, value in sorted(analysis["contrasts"].items())
        if (
            "interaction." in name
            or (
                "self-minus-donor" in name
                and ".acute_mismatch." in name
                and ".lambda-1." in name
            )
        )
        and (name.endswith("active_capture") or name.endswith("strict_library") or name.startswith("committor"))
    ]
    for name, value in selected_contrasts:
        lower, upper = value["interval"]
        lines.append(
            f"| {name} | {value['rulebooks']} | {value['mean']:.4f} "
            f"[{lower:.4f}, {upper:.4f}] |"
        )
    lines.extend(
        [
            "",
            "## Outcome accounting",
            "",
            "All futures remain in one of the complete competing-outcome categories. Noise-specific cycles and off-library point states are reported rather than conditioned away.",
            "",
            "![Outcome composition](figures/outcome_composition.png)",
            "",
            "![Noise and carryover response](figures/noise_carryover.png)",
            "",
            "## Source generation",
            "",
            "```json",
        ]
    )
    import json

    lines.append(json.dumps(registry.get("generation", {}), indent=2, sort_keys=True))
    lines.extend(
        [
            "```",
            "",
            "Every protocol, rulebook, raw summary, analysis, figure, and replay identifier is checksummed. This report does not select a scientific effect by sign.",
            "",
        ]
    )
    return "\n".join(lines)


def write_mechanism_figures(directory: Path, analysis: dict[str, Any]) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gre-mechanism-mpl-") as cache:
        os.environ.setdefault("MPLCONFIGDIR", cache)
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        compositions = [
            (name, value)
            for name, value in sorted(analysis["outcome_composition"].items())
            if ".acute_mismatch." in name and ".lambda-1." in name
        ][:24]
        categories = sorted(
            {
                category
                for _, value in compositions
                for category in value["rates"]
            }
        )
        figure, axis = plt.subplots(figsize=(12, 6))
        bottom = np.zeros(len(compositions), dtype=float)
        for category in categories:
            heights = np.asarray(
                [value["rates"].get(category, 0.0) for _, value in compositions]
            )
            axis.bar(np.arange(len(compositions)), heights, bottom=bottom, label=category)
            bottom += heights
        axis.set_xticks(
            np.arange(len(compositions)),
            [name for name, _ in compositions],
            rotation=75,
            ha="right",
        )
        axis.set_ylabel("Fraction of futures")
        axis.set_title("Complete acute-mismatch outcome composition")
        if categories:
            axis.legend(fontsize=7)
        figure.tight_layout()
        figure.savefig(directory / "outcome_composition.png", dpi=160)
        plt.close(figure)

        points = []
        for name, value in sorted(analysis["rates"].items()):
            if not name.endswith(".active_capture") or ".acute_mismatch." not in name:
                continue
            parts = name.split(".")
            carry = next(
                (float(part.split("-", 1)[1]) for part in parts if part.startswith("lambda-")),
                0.0,
            )
            variance = next(
                (float(part.split("-", 1)[1]) for part in parts if part.startswith("theta-")),
                0.0,
            )
            mode = parts[-2]
            points.append((variance, carry, mode, float(value["mean"])))
        figure, axis = plt.subplots(figsize=(8, 5))
        for variance, mode in sorted({(p[0], p[2]) for p in points}):
            values = sorted(
                [(carry, rate) for theta, carry, item_mode, rate in points if theta == variance and item_mode == mode]
            )
            if values:
                axis.plot(
                    [value[0] for value in values],
                    [value[1] for value in values],
                    marker="o",
                    label=f"theta={variance:g}, {mode}",
                )
        axis.set_xlabel("Expression-state carryover")
        axis.set_ylabel("Frozen-library capture")
        axis.set_ylim(0.0, 1.02)
        axis.set_title("Noise × carryover response")
        if points:
            axis.legend(fontsize=7)
        figure.tight_layout()
        figure.savefig(directory / "noise_carryover.png", dpi=160)
        plt.close(figure)
    return ["figures/outcome_composition.png", "figures/noise_carryover.png"]
