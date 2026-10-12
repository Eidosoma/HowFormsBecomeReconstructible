"""Human-readable GRE pilot reports and deterministic figures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import write_json


def _format_interval(value: dict[str, Any]) -> str:
    lower, upper = value["interval"]
    return f"{value['mean_log_loss_gain']:.4f} [{lower:.4f}, {upper:.4f}]"


def render_report(
    analysis: dict[str, Any],
    registry: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    is_v2 = "history_contrast" in analysis
    lines = [
        "# GRE simulation report",
        "",
        f"- Cohort: `{analysis['cohort_id']}`",
        f"- Protocol: `{analysis['protocol_format']}`",
        f"- Futures: {analysis['futures']:,}",
        f"- Runtime: {manifest['elapsed_seconds']:.2f} seconds",
        f"- Replay/checksum status at creation: complete",
        "",
    ]
    if manifest["mode"] == "stage-a":
        lines.extend(
            [
                "> This is a design-validation cohort. Outcome signs cannot support "
                "a scientific claim or determine Stage B readiness.",
                "",
            ]
        )
    elif manifest["mode"] != "pilot":
        lines.extend(
            [
                "> This is an engineering quick run, not a scientific pilot or confirmation.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "> This is an exploratory pilot. Its advancement gate was frozen in the protocol, but it is not confirmatory evidence.",
                "",
            ]
        )

    lines.extend(
        [
            "## Primary destination-committor endpoint",
            "",
            (
                "The primary cell is acute rulebook mismatch with full expression-state "
                "carryover. Audit and hierarchically shrunk committors are reported "
                "separately for self and donor-shuffled inheritance. Positive values "
                "mean better held-out log loss than the selected dynamical baseline."
                if is_v2
                else "The primary cell is acute rulebook mismatch with full "
                "expression-state carryover. Positive values mean the state-specific "
                "split-half committor improves held-out log loss over the "
                "cross-rulebook-selected dynamical baseline."
            ),
            "",
            "| Engine/cohort | Rulebooks | Gain and exploratory interval | Point gate | Interval gate |",
            "|---|---:|---:|:---:|:---:|",
        ]
    )
    for name, value in sorted(analysis["primary"].items()):
        lines.append(
            f"| {name} | {value['rulebooks']} | {_format_interval(value)} | "
            f"{'pass' if value['point_gate'] else 'fail'} | "
            f"{'pass' if value['interval_gate'] else 'fail'} |"
        )
    lines.extend(
        [
            "",
            f"**Advance to confirmation:** {'yes' if analysis['advance_to_confirmation'] else 'no'}.",
            "",
            analysis["gate_note"],
            "",
            "![Primary committor gains](figures/primary_committor_gain.png)",
            "",
        ]
    )
    if is_v2:
        lines.extend(
            [
                "## Own-history contrast",
                "",
                "Positive values mean preserving each lineage's own adult history helped more than inheriting from its fixed donor. The comparison uses shared random noise.",
                "",
                "| Engine/cohort/estimator | Rulebooks | Self minus donor gain |",
                "|---|---:|---:|",
            ]
        )
        for name, value in sorted(analysis["history_contrast"].items()):
            lower, upper = value["interval"]
            lines.append(
                f"| {name} | {value['rulebooks']} | "
                f"{value['mean_self_minus_donor_gain']:.4f} "
                f"[{lower:.4f}, {upper:.4f}] |"
            )
        lines.extend(
            [
                "",
                "## Mismatch-control contrasts",
                "",
                "Positive values mean acute mismatch produced strict switching more often than the named control.",
                "",
                "| Contrast | Rulebooks | Strict-rate difference |",
                "|---|---:|---:|",
            ]
        )
        for name, value in sorted(analysis["control_contrasts"].items()):
            lower, upper = value["interval"]
            lines.append(
                f"| {name} | {value['rulebooks']} | "
                f"{value['mean_strict_rate_difference']:.4f} "
                f"[{lower:.4f}, {upper:.4f}] |"
            )
        lines.extend(
            [
                "",
                "The hierarchical strength was selected only inside each mapping half, "
                "with the evaluated rulebook and opposite future half excluded. With "
                "one rulebook per quick-run stratum, the safe fallback is zero shrinkage.",
                "",
            ]
        )
    lines.extend(["## Split-half destination reliability", ""])
    for name, value in sorted(analysis["split_half_destination_reliability"].items()):
        lines.append(f"- {name}: {value:.4f}")

    lines.extend(
        [
            "",
            "## Selected secondary outcomes",
            "",
            "| Cell | Futures | Strict rate | Active capture | Old return |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name, value in sorted(analysis["secondary"].items()):
        if ".natural." not in name and ".acute_mismatch." not in name:
            continue
        lines.append(
            f"| {name} | {value['futures']} | {value['strict_rate']:.4f} | "
            f"{value['active_capture_rate']:.4f} | {value['old_return_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "![Strict-event rates](figures/strict_event_rates.png)",
            "",
            (
                "`single_attractor` is a forced-convergence detector check, not a "
                "negative specificity control."
                if is_v2
                else ""
            ),
            "",
            "## Cohort generation and exclusions",
            "",
            "```json",
        ]
    )
    import json

    lines.append(json.dumps(registry["generation"], indent=2, sort_keys=True))
    lines.extend(
        [
            "```",
            "",
            "![Evolution fitness traces](figures/evolution_fitness.png)",
            "",
            "Every failed generation, eligibility attempt, endpoint gate, and exact replay identifier remains in the run artifacts. Sampled and evolved strata are never pooled.",
            "",
        ]
    )
    return "\n".join(lines)


def write_figures(
    directory: Path,
    analysis: dict[str, Any],
    registry: dict[str, Any],
) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gre-mpl-") as cache:
        os.environ.setdefault("MPLCONFIGDIR", cache)
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        names = sorted(analysis["primary"])
        means = [analysis["primary"][name]["mean_log_loss_gain"] for name in names]
        lower = [analysis["primary"][name]["interval"][0] for name in names]
        upper = [analysis["primary"][name]["interval"][1] for name in names]
        errors = np.asarray(
            [[mean - low for mean, low in zip(means, lower)], [high - mean for mean, high in zip(means, upper)]]
        )
        figure, axis = plt.subplots(figsize=(8, 4.5))
        positions = np.arange(len(names))
        axis.bar(positions, means, color="#4472c4", yerr=errors, capsize=3)
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.set_xticks(positions, names, rotation=25, ha="right")
        axis.set_ylabel("Held-out log-loss gain (nats)")
        axis.set_title("Destination committor versus frozen baseline")
        figure.tight_layout()
        figure.savefig(directory / "primary_committor_gain.png", dpi=160)
        plt.close(figure)

        selected = [
            (name, value)
            for name, value in sorted(analysis["secondary"].items())
            if (".natural." in name or ".acute_mismatch." in name)
        ]
        figure, axis = plt.subplots(figsize=(11, 5))
        axis.bar(
            np.arange(len(selected)),
            [value["strict_rate"] for _, value in selected],
            color=["#70ad47" if ".natural." in name else "#ed7d31" for name, _ in selected],
        )
        axis.set_xticks(
            np.arange(len(selected)), [name for name, _ in selected], rotation=70, ha="right"
        )
        axis.set_ylabel("Strict rehoming rate")
        axis.set_title("Secondary strict-event occurrence")
        figure.tight_layout()
        figure.savefig(directory / "strict_event_rates.png", dpi=160)
        plt.close(figure)

        figure, axis = plt.subplots(figsize=(8, 4.5))
        plotted = 0
        for engine, populations in sorted(registry.get("evolution", {}).items()):
            traces = [
                item["trace"]
                for item in populations
                if item.get("status") == "eligible" and item.get("trace")
            ]
            if not traces:
                continue
            maximum = min(len(trace) for trace in traces)
            generations = np.arange(maximum)
            means = np.mean(
                [[entry["mean_fitness"] for entry in trace[:maximum]] for trace in traces],
                axis=0,
            )
            best = np.mean(
                [[entry["best_fitness"] for entry in trace[:maximum]] for trace in traces],
                axis=0,
            )
            axis.plot(generations, means, label=f"{engine} mean")
            axis.plot(generations, best, linestyle="--", label=f"{engine} best")
            plotted += 1
        if plotted:
            axis.legend()
        else:
            axis.text(0.5, 0.5, "No evolution cohort", ha="center", va="center")
        axis.set_xlabel("Generation")
        axis.set_ylabel("Fitness")
        axis.set_title("Independent evolution cohorts")
        figure.tight_layout()
        figure.savefig(directory / "evolution_fitness.png", dpi=160)
        plt.close(figure)
    return [
        "figures/primary_committor_gain.png",
        "figures/strict_event_rates.png",
        "figures/evolution_fitness.png",
    ]
