"""Audited one-boundary functional capture figure and source provenance."""
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
    if not run.is_relative_to(HERE/"runs"): raise ValueError("Local E019 run required")
    audit = json.loads((run/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(run/"COMPLETE.json")
    complete = json.loads((run/"COMPLETE.json").read_text())
    assert complete["outputs_sha256"]["summary.json"] == sha(run/"summary.json")
    summary = json.loads((run/"summary.json").read_text())
    output = HERE/"figures"/run.name
    output.mkdir(parents=True, exist_ok=False)
    labels = ("Original (before replacement)", "Immediate snapshot", "Delayed snapshot", "128-step average", "Protected copy",
              "Immediate / reading blocked", "Delayed / reading blocked", "Average / reading blocked", "Writing blocked")
    colors = ("#596b78", "#007f86", "#bc7223", "#ae5367", "#596b78", "#9aabad", "#9aabad", "#9aabad", "#9aabad")
    plt.rcParams.update({"font.size": 10})
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 6.4), sharey=True)
    fig.subplots_adjust(left=.225, right=.985, bottom=.20, top=.79, wspace=.13)
    for ax, damage, title in zip(axes, summary["damage"], ("Intact", "24 cells removed", "3×3 lesion")):
        for y, ((h, name), color) in enumerate(zip(summary["panels"], colors)):
            st = summary["groups"][str(h)][name]["both_cues"][damage]["own"]
            mean = 100*st["mean"]
            bounds = 100*np.array(st["ci95"])
            ax.errorbar(mean, y, xerr=np.maximum(0, [[mean-bounds[0]], [bounds[1]-mean]]), fmt="o", color=color, capsize=3, markersize=6)
        ax.set(title=title, xlim=(-3, 103), xticks=range(0, 101, 25), xlabel="Both input tests correct (%)", yticks=range(9))
        ax.grid(axis="x", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_yticklabels(labels)
    axes[0].invert_yaxis()
    axes[0].axvline(75, color="black", linestyle=":", linewidth=.8)
    cohort = "excluded technical benchmark" if summary["evidence_status"] == "technical" else f"{len(summary['blocks'])} fresh blocks / {summary['lineages']} lineages"
    fig.suptitle(f"E019: capture timing after one replacement\n{cohort}", y=.97)
    primary = summary["primary"]["statistics"]
    fig.supxlabel(f"Primary, immediate minus delayed (intact): {100*primary['mean']:.1f} points "
        f"[95% {100*primary['ci95'][0]:.1f}, {100*primary['ci95'][1]:.1f}].\n"
        "Whole-block intervals; other comparisons pointwise. Renewal bodies intact; damage applied only in fresh assays.", fontsize=9, y=.025)
    for ext in ("png", "svg"): fig.savefig(output/f"capture_timing.{ext}", dpi=170)
    plt.close(fig)
    dump(output/"provenance.json", dict(summary_sha256=sha(run/"summary.json"), complete_sha256=sha(run/"COMPLETE.json"),
        audit_sha256=sha(run/"INDEPENDENT_AUDIT.json"), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))
    print("Figures:", output, flush=True)


if __name__ == "__main__": main()
