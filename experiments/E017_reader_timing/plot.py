"""Frozen display of both-cue routing under the three reader schedules."""
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
    if not run.is_relative_to(HERE/"runs"): raise ValueError("Local E017 run required")
    audit = json.loads((run/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(run/"COMPLETE.json")
    complete = json.loads((run/"COMPLETE.json").read_text())
    assert complete["outputs_sha256"]["summary.json"] == sha(run/"summary.json")
    summary = json.loads((run/"summary.json").read_text())
    output = HERE/"figures"/run.name
    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.6), layout="constrained", sharey=True)
    labels = ("Baseline: 512 steps", "Extended: 2048 steps", "Staged: 2048 steps, delay 256")
    colors = ("#536878", "#b56a18", "#008c87")
    for ax, regime, title in zip(axes, summary["regimes"], ("Consistent learned record", "Engineered capacity control")):
        for k, (condition, label, color) in enumerate(zip(summary["conditions"], labels, colors)):
            stats = [summary["groups"][regime][condition]["both_cues"][damage]["own"] for damage in summary["damage"]]
            means = 100*np.array([st["mean"] for st in stats])
            bounds = 100*np.array([st["ci95"] for st in stats]).T
            ax.errorbar(np.arange(3)+(k-1)*.13, means, yerr=np.maximum(0, np.array([means-bounds[0], bounds[1]-means])),
                fmt="o", capsize=4, markersize=7, label=label, color=color)
        ax.set(title=title, xticks=range(3), xticklabels=["Intact", "24 cells removed", "3×3 lesion"], ylim=(-3, 103), yticks=range(0, 101, 20))
        ax.grid(axis="y", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Both opposing input tests correct (%)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside upper center", ncol=3, fontsize=9)
    primary = summary["primary"]["statistics"]
    fig.suptitle(f"E017: reader timing · {len(summary['blocks'])} fresh blocks / {summary['founders']} founders")
    fig.supxlabel(f"Primary staged-minus-extended effect: {100*primary['mean']:+.1f} points "
        f"[95% {100*primary['ci95'][0]:+.1f}, {100*primary['ci95'][1]:+.1f}].\n"
        "Final 32-step mean; strict margin ±0.25; all cases retained. Whole-block intervals; secondary comparisons pointwise.", fontsize=9)
    for ext in ("png", "svg"): fig.savefig(output/f"reader_timing.{ext}", dpi=170)
    plt.close(fig)
    dump(output/"provenance.json", dict(summary_sha256=sha(run/"summary.json"), complete_sha256=sha(run/"COMPLETE.json"),
        audit_sha256=sha(run/"INDEPENDENT_AUDIT.json"), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))
    print("Figures:", output, flush=True)


if __name__ == "__main__": main()
