#!/usr/bin/env python3
"""Present E014's saved native agreement and specificity estimates.

Reads the existing portable archive only. No model import, field replay,
bootstrap, sign-only analysis or new scientific estimate is performed.
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
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "paper_assets/data"
FIGURES = ROOT / "paper_assets/figures"
ARCHIVE = DATA / "experimental-tracks-v0.12-source-records.zip"
PREFIX = "workspace/WhereDoFormsComeFrom/experiments/E014_long_renewal/runs/confirmation_v2/"
SUMMARY_HASH = "3482f4acc8e58184127db6c33b41229d57b8911ccb5d28ad770b8ff8623d64b9"
INK, TEAL, AMBER, PURPLE, MUTED = "#123b49", "#087f8c", "#bf740e", "#76618e", "#54636b"
ARMS = [("rewrite", "Own-record renewal", TEAL, "o", "-"),
        ("foreign", "Matched foreign-record renewal", AMBER, "s", "--"),
        ("copy", "Protected own-record copying", PURPLE, "D", ":")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = []
    payloads = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in ["summary.json", "REPORT.md", "COMPLETE.json", "INDEPENDENT_AUDIT.json",
                     "manifest.json", "inputs/E014_long_renewal/PROTOCOL.md"]:
            payload = archive.read(PREFIX + name)
            payloads[name] = payload
            sources.append({"member": PREFIX + name,
                            "sha256": hashlib.sha256(payload).hexdigest()})
    assert sources[0]["sha256"] == SUMMARY_HASH
    summary = json.loads(payloads["summary.json"])
    complete = json.loads(payloads["COMPLETE.json"])
    audit = json.loads(payloads["INDEPENDENT_AUDIT.json"])
    assert complete["outputs_sha256"]["summary.json"] == SUMMARY_HASH
    assert complete["outputs_sha256"]["REPORT.md"] == sources[1]["sha256"]
    assert audit["complete_sha256"] == sources[2]["sha256"]
    assert audit["status"] == "PASS"  # Retained audit attribution, not a new replay.
    assert summary["source_blocks"] == list(range(12000, 12064))
    assert summary["founders"] == 256 and summary["complete_sequence_confirmed"]
    horizons = summary["checkpoint_numbers"]
    assert horizons == [1, 3, 8, 16]
    rows = []
    for factor in (4, 1):
        group = summary["groups"][str(factor)]
        block_scores = np.array(group["block_own"])
        assert block_scores.shape == (64, 20, 10)
        for h in horizons:
            stage = f"after_{h}"
            stage_id = summary["stages"].index(stage)
            for arm, *_ in ARMS:
                stat = group["own_statistics"][stage][arm]
                arm_id = summary["arms"].index(arm)
                np.testing.assert_array_equal(stat["block_means"], block_scores[:, stage_id, arm_id])
                assert stat["mean"] == float(np.mean(stat["block_means"]))
                rows.append(dict(factor=factor, packet_bytes=group["packet_bytes"], horizon=h,
                                 series=arm, endpoint="qualified_agreement", unit="fraction",
                                 native_key=f"groups/{factor}/own_statistics/{stage}/{arm}",
                                 **{k: stat[k] for k in ("mean", "ci95", "block_means")}))
            stat = group["contrasts"][stage]["rewrite_minus_foreign"]
            expected = block_scores[:, stage_id, 0] - block_scores[:, stage_id, 1]
            np.testing.assert_array_equal(stat["block_means"], expected)
            assert stat["mean"] == float(np.mean(expected))
            rows.append(dict(factor=factor, packet_bytes=group["packet_bytes"], horizon=h,
                             series="rewrite_minus_foreign", endpoint="historical_specificity",
                             unit="fraction_difference",
                             native_key=f"groups/{factor}/contrasts/{stage}/rewrite_minus_foreign",
                             **{k: stat[k] for k in ("mean", "ci95", "block_means")}))
        copy = group["own_statistics"]["after_1"]["copy"]
        assert all(group["own_statistics"][f"after_{h}"]["copy"] == copy for h in horizons)
    assert len(rows) == 32
    lookup = {(r["factor"], r["horizon"], r["series"]): r for r in rows}
    data = dict(experiment="E014", run="confirmation_v2", blocks=64, founders=256,
                recipient_replicates_per_founder=2, all_founders_retained=True,
                horizons=horizons, archive=str(ARCHIVE.relative_to(ROOT)), archive_sha256=sha(ARCHIVE),
                sources=sources, rows=rows,
                observer="Q: fraction of all 256 sites matching the own-founder sign with |V| > 0.2",
                comparator="Foreign record from next founder in the same background block at acquisition; both chains then renew and are scored against the same own prototype.",
                protected_copy="Exact original bytes at the same budget; checkpoint births/noise shared across horizons, so the copied-record probe is exactly constant.",
                intervals="Saved pointwise 95% whole-block bootstrap intervals; 128-byte after-16 specificity is the primary.",
                new_inference=False, sign_amplitude_decomposition="Pending separate analysis; not supplied by this figure.")
    json_path = DATA / "historical-specificity-v0.18.json"
    json_path.write_text(json.dumps(data, indent=2) + "\n")
    csv_path = DATA / "historical-specificity-v0.18.csv"
    with csv_path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=["packet_bytes", "horizon", "series", "endpoint",
                                                "mean_percent_or_points", "ci95_lower", "ci95_upper"])
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row[k] for k in ("packet_bytes", "horizon", "series", "endpoint")},
                             "mean_percent_or_points": 100 * row["mean"],
                             "ci95_lower": 100 * row["ci95"][0], "ci95_upper": 100 * row["ci95"][1]})

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "svg.fonttype": "none", "svg.hashsalt": "forms-specificity-v018",
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#b9c6cb", "text.color": INK,
                         "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})
    fig = plt.figure(figsize=(13.2, 8.6), facecolor="white")
    fig.text(.065, .95, "Total agreement and historical specificity", fontsize=23, weight="bold")
    fig.text(.065, .909, "E014  |  64 independent blocks  |  all 256 founders retained", fontsize=12, color=MUTED)
    legend = [Line2D([], [], color=c, marker=m, linestyle=ls, lw=2, markersize=6, label=name)
              for _, name, c, m, ls in ARMS]
    fig.legend(handles=legend, loc="center", bbox_to_anchor=(.5, .858), frameon=False,
               ncol=3, fontsize=11, columnspacing=1.7)
    for col, factor in enumerate((4, 1)):
        left = .08 + col * .48
        group = summary["groups"][str(factor)]
        ax = fig.add_axes([left, .46, .405, .31])
        ax.set_title(f"{'A' if col == 0 else 'B'}   {group['packet_bytes']}-byte record", loc="left", fontsize=15, weight="bold", pad=13)
        ax.set(xlim=(.3, 20.4), ylim=(60, 80), xticks=horizons, yticks=[60, 65, 70, 75, 80])
        ax.grid(axis="y", color="#e7edef")
        if col == 0:
            ax.set_ylabel("Qualified agreement (%)")
        for arm, _, color, marker, ls in ARMS:
            values = [lookup[factor, h, arm] for h in horizons]
            means = np.array([x["mean"] for x in values]) * 100
            intervals = np.array([x["ci95"] for x in values]) * 100
            ax.errorbar(horizons, means, yerr=np.array([means - intervals[:, 0], intervals[:, 1] - means]),
                        color=color, marker=marker, linestyle=ls, lw=2, ms=5.5, capsize=3, elinewidth=1.1,
                        zorder=3 if arm == "rewrite" else 2)
            ax.text(17.1, means[-1], f"{means[-1]:.2f}%", va="center", fontsize=11, color=color,
                    weight="bold" if arm == "rewrite" else "normal")
        ax.set_xlabel("Completed rewrites")
        gap = fig.add_axes([left, .135, .405, .205])
        gap.set_title(f"{'C' if col == 0 else 'D'}   Own − foreign advantage", loc="left", fontsize=14, weight="bold", pad=12)
        gap.set(xlim=(.3, 20.4), ylim=(0, 3.1), xticks=horizons, yticks=[0, 1, 2, 3], xlabel="Completed rewrites")
        if col == 0:
            gap.set_ylabel("Agreement points")
        gap.grid(axis="y", color="#e7edef")
        gap.axhline(0, color=MUTED, lw=1)
        values = [lookup[factor, h, "rewrite_minus_foreign"] for h in horizons]
        means = np.array([x["mean"] for x in values]) * 100
        intervals = np.array([x["ci95"] for x in values]) * 100
        gap.errorbar(horizons, means, yerr=np.array([means - intervals[:, 0], intervals[:, 1] - means]),
                     color=TEAL, marker="o", lw=2, ms=5.5, capsize=4, elinewidth=1.3)
        gap.text(17.1, means[-1], f"+{means[-1]:.3f}", va="center", fontsize=11, color=TEAL, weight="bold")
    fig.text(.065, .063, "All arms scored against the same own-founder prototype. Top axes show 60–80% of the 0–100% score range.", fontsize=10.5, color=MUTED)
    fig.text(.065, .034, "Saved 95% whole-block intervals; paired differences below. Checkpoint readers never enter the continuing lineage.", fontsize=10.5, color=MUTED)
    stem = "data-historical-specificity-v0.18"
    outputs = []
    for extension in ("png", "svg"):
        path = FIGURES / f"{stem}.{extension}"
        fig.savefig(path, dpi=190, metadata={"Date": None} if extension == "svg" else None)
        outputs.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path)})
    plt.close(fig)
    manifest = dict(figure_id="fig-historical-specificity", kind="reported-estimates",
                    png=stem + ".png", data=str(json_path.relative_to(ROOT)), data_sha256=sha(json_path),
                    csv=str(csv_path.relative_to(ROOT)), csv_sha256=sha(csv_path),
                    plot_script=str(Path(__file__).relative_to(ROOT)), plot_script_sha256=sha(Path(__file__)),
                    archive=str(ARCHIVE.relative_to(ROOT)), archive_sha256=sha(ARCHIVE),
                    sources=sources, outputs=outputs, native_estimates_verified=len(rows),
                    new_inference=False, selection="Both prespecified record budgets; all four fresh-reader checkpoints; own/foreign/protected-copy means and own-minus-foreign contrasts.")
    (FIGURES / "historical-specificity-assets-v0.18.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified {len(rows)} native means and intervals; wrote {stem}.png/.svg")


if __name__ == "__main__":
    main()
