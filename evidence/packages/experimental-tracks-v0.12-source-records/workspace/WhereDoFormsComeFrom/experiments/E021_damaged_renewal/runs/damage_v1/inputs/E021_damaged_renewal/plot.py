"""Audited functional renewal figure, with separate legend and provenance."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    cap_cpus()
    run = args.run.resolve()
    if not run.is_relative_to(HERE/"runs"): raise ValueError("Local E021 run required")
    audit = json.loads((run/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(run/"COMPLETE.json")
    complete = json.loads((run/"COMPLETE.json").read_text())
    assert complete["outputs_sha256"]["summary.json"] == sha(run/"summary.json")
    summary = json.loads((run/"summary.json").read_text())
    output = HERE/"figures"/run.name
    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size": 10})
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 5.8), sharey=True)
    fig.subplots_adjust(left=.07, right=.99, bottom=.24, top=.73, wspace=.12)
    labels = ("Damaged renewal", "Intact renewal", "Protected copy", "Copy with erased edges", "Reading blocked", "Writing blocked")
    colors = ("#008c87", "#3465a4", "#536878", "#9a731b", "#d5662c", "#a84e86")
    for ax, damage, title in zip(axes, summary["damage"], ("Intact assay", "Assay: 24 cells removed", "Assay: 3×3 lesion")):
        initial = summary["groups"]["0"]["initial"]["both_cues"][damage]["own"]
        for k, (condition, label, color) in enumerate(zip(summary["conditions"], labels, colors)):
            stats = [initial]+[summary["groups"][str(h)][condition]["both_cues"][damage]["own"] for h in (1, 3)]
            means = 100*np.array([st["mean"] for st in stats])
            bounds = 100*np.array([st["ci95"] for st in stats]).T
            ax.errorbar(np.array([0, 1, 3])+(k-2.5)*.035, means,
                yerr=np.maximum(0, np.array([means-bounds[0], bounds[1]-means])), fmt="o-", capsize=3,
                markersize=5, linewidth=1.5, label=label, color=color)
        ax.set(title=title, xticks=[0, 1, 3], xlabel="Record replacements", ylim=(-3, 103), yticks=range(0, 101, 20))
        ax.grid(axis="y", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Both opposing input tests correct (%)")
    axes[0].axhline(75, color="black", linestyle=":", linewidth=.8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(.5, .915), ncol=3, fontsize=9)
    cohort = "excluded technical benchmark" if summary["evidence_status"] == "technical" else f"{len(summary['blocks'])} fresh blocks / {summary['lineages']} lineages"
    fig.suptitle(f"E021: function through damaged renewal · {cohort}", y=.985)
    primary = summary["primary"]["statistics"]
    fig.supxlabel(f"Primary, intact assay after three damaged-body replacements: {100*primary['mean']:.1f}% "
        f"[95% {100*primary['ci95'][0]:.1f}, {100*primary['ci95'][1]:.1f}].\n"
        "Renewal: 24 non-port cells absent from birth, new mask each generation. Immediate capture unchanged.\n"
        "Whole-block intervals; secondary comparisons pointwise. Assays never feed back into renewal.", fontsize=9, y=.025)
    for ext in ("png", "svg"): fig.savefig(output/f"damaged_renewal.{ext}", dpi=170)
    plt.close(fig)
    dump(output/"provenance.json", dict(summary_sha256=sha(run/"summary.json"), complete_sha256=sha(run/"COMPLETE.json"),
        audit_sha256=sha(run/"INDEPENDENT_AUDIT.json"), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))
    print("Figures:", output, flush=True)


if __name__ == "__main__": main()
