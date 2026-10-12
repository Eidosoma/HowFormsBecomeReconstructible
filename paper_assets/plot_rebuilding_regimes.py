#!/usr/bin/env python3
"""Plot retained E051/E052 estimates and counters, without new inference.

Inputs are the versioned portable extracts and their already retained summaries.
No experimental code is imported, no trajectory is replayed, and E053 is excluded.
"""
import csv
import hashlib
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "paper_assets/figures"
DATA = ROOT / "paper_assets/data"
SCRIPT = Path(__file__).resolve()
INK, TEAL, AMBER, MUTED = "#123b49", "#087f8c", "#bf740e", "#54636b"
PAIRINGS = [("paired", "Matched", AMBER, "o", .16),
            ("noise_0", "Independent", TEAL, "D", -.16)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = []
    summaries = {}
    for study, extract, archive, campaign, expected in (
        ("E051", "cue-pairing-v0.17.json", "cue-pairing-v0.17-source-records.zip",
         "E051_cue_pairing_robustness",
         "9eb34a04f5295d8e8926ac502b59689b1bf074433f51b0bf644e89d413443521"),
        ("E052", "evidence-update-v0.17.json", "evidence-update-v0.17-source-records.zip",
         "E052_precision_normalization",
         "f611aab5959ccc5c0511db7c2a78941ba112f974554cd03b1dfb0050333c0395"),
    ):
        member = f"experiments/{campaign}/runs/robustness_v1/summary.json"
        with zipfile.ZipFile(DATA / archive) as package:
            payload = package.read(member)
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError(f"Retained native summary changed: {study}")
        summaries[study] = json.loads(payload)
        sources.append({"experiment": study,
                        "extract": str((DATA / extract).relative_to(ROOT)),
                        "extract_sha256": sha(DATA / extract),
                        "archive": str((DATA / archive).relative_to(ROOT)),
                        "archive_sha256": sha(DATA / archive),
                        "summary_member": member, "summary_sha256": expected})

    cue = json.loads((DATA / "cue-pairing-v0.17.json").read_text())
    precision = json.loads((DATA / "evidence-update-v0.17.json").read_text())["E052"]
    terminal = {(row["pairing"], row["policy"]): row for row in cue["terminal_results"]}
    rows = []

    def row(panel, study, pairing, condition, key, reported):
        native = summaries[study]["statistics"][key]
        assert reported["mean"] == native["mean"]
        assert reported["ci95"] == native["ci95"]
        assert len(native["block_means"]) == 32
        result = {"panel": panel, "experiment": study, "pairing": pairing,
                  "condition": condition, "native_statistic_key": key,
                  "mean": native["mean"], "ci95": native["ci95"]}
        rows.append(result)
        return result

    numeric = [
        ("reference", "Reference"),
        ("record32", "Float32 storage only"),
        ("arithmetic32", "Float32 computation\n+ stored values"),
        ("grid_2m16", "Uniform rounding\nto a $2^{-16}$ grid"),
        ("record_noise_1e4", "Nonzero-weight noise\nSD $10^{-4}$"),
        ("floor_1e4", "Reader normalization\nfloor $10^{-4}$"),
    ]
    policies = [
        ("exact_rewrite", "Original writer"),
        ("tolerance_rewrite", "Fixed tolerance\n$10^{-4}$"),
        ("contrast_rewrite", "Pure contrast"),
        ("exact_preserve", "Preserve strong"),
    ]
    points_a, points_b, points_c = {}, {}, {}
    for pairing, *_ in PAIRINGS:
        for condition, _ in numeric:
            key = f"assay/32/{pairing}/{condition}/native/scattered"
            points_a[pairing, condition] = row("A", "E052", pairing, condition, key,
                                                precision["terminal_native_scattered"][key])
        key = f"mechanism/{pairing}/exact_rewrite/ordinary_selected_returning"
        points_b[pairing] = row("B", "E051", pairing, "ordinary fallback", key,
                                cue["selected_native_statistics"][key])
        for policy, _ in policies:
            value = terminal[pairing, policy]
            points_c[pairing, policy] = row("C", "E051", pairing, policy,
                                            value["native_statistic_key"], value)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.spines.left": False,
                         "axes.edgecolor": "#b9c6cb", "text.color": INK,
                         "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": INK})
    fig = plt.figure(figsize=(13.2, 9.6))
    fig.text(.04, .953, "Rebuilding conditions change the mechanism", fontsize=21, weight="bold")
    fig.text(.04, .916, "Completed E051 and E052 studies  |  separate cohorts; no pooled estimate",
             fontsize=12, color=MUTED)
    legend = [Line2D([], [], marker=marker, linestyle="none", color=color,
                     markersize=7, label=f"{label} rebuilding cue noise")
              for _, label, color, marker, _ in PAIRINGS]
    fig.legend(handles=legend, loc="upper center", bbox_to_anchor=(.57, .904),
               frameon=False, ncol=2, fontsize=12, columnspacing=2)

    def setup(ax, ymax):
        ax.set_xlim(-3, 104)
        ax.set_ylim(-.5, ymax)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_yticks([])
        ax.grid(axis="x", color="#e7edef", zorder=0)
        ax.set_axisbelow(True)
        ax.set_xlabel("Terminal success (%)", fontsize=12, labelpad=8)

    def point(ax, value, y, color, marker):
        mean = 100 * value["mean"]
        lo, hi = [100 * bound for bound in value["ci95"]]
        ax.errorbar(mean, y, xerr=[[mean-lo], [hi-mean]], fmt=marker,
                    color=color, markersize=6, capsize=3, lw=1.6, zorder=3)

    def number(ax, x, y, value, color):
        # Numbers occupy fixed columns, keeping endpoint labels off error bars.
        fy = fig.transFigure.inverted().transform(ax.transData.transform((0, y)))[1]
        fig.text(x, fy, f"{100 * value['mean']:.2f}", ha="center", va="center",
                 color=color, fontsize=12.5, weight="bold")

    fig.text(.04, .836, "A   Numerical interventions (E052)", fontsize=14, weight="bold")
    fig.text(.80, .833, "Matched", color=AMBER, ha="center", fontsize=11)
    fig.text(.925, .833, "Independent", color=TEAL, ha="center", fontsize=11)
    ax = fig.add_axes([.305, .486, .425, .330])
    setup(ax, 5.5)
    for index, (condition, label) in enumerate(numeric):
        y = 5-index
        ax.text(-8, y, label, ha="right", va="center", fontsize=12)
        for pairing, _, color, marker, offset in PAIRINGS:
            value = points_a[pairing, condition]
            point(ax, value, y+offset, color, marker)
            number(ax, .80 if pairing == "paired" else .925, y, value, color)

    fig.text(.04, .389, "B   Returning-edge writing (E051)", fontsize=13, weight="bold")
    bx = fig.add_axes([.13, .189, .215, .159])
    bx.set_xlim(-3, 118)
    bx.set_ylim(-.45, 1.45)
    bx.set_xticks([0, 50, 100])
    bx.set_yticks([1, 0], ["Matched", "Independent"])
    bx.tick_params(axis="y", length=0, labelsize=11)
    bx.grid(axis="x", color="#e7edef", zorder=0)
    bx.set_axisbelow(True)
    bx.set_xlabel("Ordinary fallback (%)", fontsize=12, labelpad=8)
    for index, (pairing, _, color, marker, _) in enumerate(PAIRINGS):
        value = points_b[pairing]
        y = 1-index
        bx.barh(y, 100 * value["mean"], height=.26, color=color, alpha=.16)
        point(bx, value, y, color, marker)
        bx.text(100 * value["mean"]+5, y, f"{100 * value['mean']:.0f}",
                va="center", fontsize=12, color=color, weight="bold")
    fig.text(.045, .068, "Original writer; available connections\nreturning after injury, boundaries 2–32.",
             fontsize=11.5, color=MUTED, linespacing=1.5)

    fig.text(.43, .389, "C   Writing policies (E051)", fontsize=13, weight="bold")
    fig.text(.85, .365, "Matched", color=AMBER, ha="center", fontsize=10.5)
    fig.text(.945, .365, "Independent", color=TEAL, ha="center", fontsize=10.5)
    cx = fig.add_axes([.595, .157, .205, .192])
    setup(cx, 3.5)
    cx.set_xticks([0, 50, 100])
    for index, (policy, label) in enumerate(policies):
        y = 3-index
        cx.text(-8, y, label, ha="right", va="center", fontsize=11.5)
        for pairing, _, color, marker, offset in PAIRINGS:
            value = points_c[pairing, policy]
            point(cx, value, y+offset, color, marker)
            number(cx, .85 if pairing == "paired" else .945, y, value, color)
    fig.text(.43, .055, "Preserving strong weights reverses its ranking relative to full rewriting;\nweaker weights are still rewritten. This is not protected copying.",
             fontsize=11, color=MUTED, linespacing=1.5)
    fig.text(.04, .022, "Each study: 32 independent blocks, 512 lineages per condition. Saved pointwise 95% block intervals.",
             fontsize=11, color=MUTED)

    outputs = []
    for ext in ("png", "svg"):
        path = FIGURES / f"data-rebuilding-regimes-v0.18.{ext}"
        fig.savefig(path, dpi=240, facecolor="white", metadata={"Creator": "Matplotlib"})
        outputs.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path)})
    plt.close(fig)

    selected = {"scope": "Editorial display of retained estimates; no new inference or trajectories.",
                "cohorts_pooled": False, "blocks_per_study": 32, "lineages_per_condition": 512,
                "sources": sources, "rows": rows,
                "selection": {
                    "A": "E052 reference, storage-only control and all four primary stress levels; matched and independent rebuilding noise.",
                    "B": "E051 original-writer ordinary fallback on available returning edges, boundaries 2–32; matched and independent rebuilding noise.",
                    "C": "E051 original, tolerance, contrast-only and strong-preserving writers; matched and independent rebuilding noise. Ordinary-only and intermediate correlations remain in Appendix D.8.3.",
                },
                "intervals": "Native pointwise 95% whole-block bootstrap intervals, unchanged; no multiplicity adjustment or cross-study inference.",
                "excluded": "E053 incomplete; no preliminary estimates enter this figure."}
    data_path = DATA / "rebuilding-regimes-v0.18.json"
    data_path.write_text(json.dumps(selected, indent=2)+"\n")
    csv_path = DATA / "rebuilding-regimes-v0.18.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["panel", "experiment", "pairing", "condition", "mean_percent",
                         "ci95_low_percent", "ci95_high_percent", "native_statistic_key"])
        for value in rows:
            writer.writerow([value["panel"], value["experiment"], value["pairing"], value["condition"],
                             100*value["mean"], *[100*b for b in value["ci95"]], value["native_statistic_key"]])
    provenance = {"figure_id": "fig-rebuilding-regimes", "kind": "reported-estimates",
                  "png": "data-rebuilding-regimes-v0.18.png",
                  "data": str(data_path.relative_to(ROOT)), "data_sha256": sha(data_path),
                  "csv": str(csv_path.relative_to(ROOT)), "csv_sha256": sha(csv_path),
                  "plot_script": str(SCRIPT.relative_to(ROOT)), "plot_script_sha256": sha(SCRIPT),
                  "sources": sources, "outputs": outputs,
                  "native_statistics_verified": len(rows), "statistics_recomputed": False,
                  "new_trajectories": False, "cohorts_pooled": False,
                  "intervals": selected["intervals"], "selection": selected["selection"]}
    (FIGURES / "rebuilding-regimes-assets-v0.18.json").write_text(json.dumps(provenance, indent=2)+"\n")
    print(f"Rendered 3 panels from {len(rows)} verified retained statistics; no new inference.")


if __name__ == "__main__":
    main()
