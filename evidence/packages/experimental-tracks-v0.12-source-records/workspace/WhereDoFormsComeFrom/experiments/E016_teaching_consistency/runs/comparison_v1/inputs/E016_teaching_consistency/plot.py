"""Fixed complete-cohort comparison with block uncertainty."""
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
    if not run.is_relative_to(HERE / "runs"): raise ValueError("Local E016 run required")
    receipt = json.loads((run / "INDEPENDENT_AUDIT.json").read_text())
    assert receipt["status"] == "PASS" and receipt["complete_sha256"] == sha(run / "COMPLETE.json")
    complete = json.loads((run / "COMPLETE.json").read_text())
    assert sha(run / "summary.json") == complete["outputs_sha256"]["summary.json"]
    summary = json.loads((run / "summary.json").read_text())
    output = HERE / "figures" / run.name
    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.2), layout="constrained", sharey=True)
    colors = ("#536878", "#008c87", "#b56a18")
    labels = ("Ordinary teaching", "Consistent teaching", "Engineered capacity control")
    for ax, metric, title in zip(axes, ("accuracy", "both_cues"),
                                ("Individual input trials", "Both opposing inputs correct")):
        for m, (regime, color, label) in enumerate(zip(summary["regimes"], colors, labels)):
            stats = [summary["groups"][regime][metric][d]["own"] for d in summary["damage"]]
            means = 100*np.array([st["mean"] for st in stats])
            bounds = 100*np.array([st["ci95"] for st in stats]).T
            ax.errorbar(np.arange(3)+(m-1)*.13, means, yerr=np.maximum(0, np.array([means-bounds[0], bounds[1]-means])),
                        fmt="o", capsize=4, color=color, label=label, markersize=7)
        ax.set(xticks=range(3), xticklabels=["Intact", "24 cells removed", "3×3 lesion"],
               ylim=(-3, 103), yticks=range(0, 101, 20), title=title)
        ax.grid(axis="y", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Strict success (%)")
    axes[0].legend(loc="upper left", fontsize=9)
    primary = summary["primary"]["statistics"]
    fig.suptitle(f"E016: teaching consistency · {len(summary['blocks'])} fresh blocks / {summary['founders']} founders")
    fig.supxlabel(f"Primary intact both-input improvement: {100*primary['mean']:+.1f} percentage points "
                  f"[95% interval {100*primary['ci95'][0]:+.1f}, {100*primary['ci95'][1]:+.1f}].\n"
                  "Correct outputs must exceed ±0.25; all cases retained. Whole-block intervals; secondary comparisons are pointwise.", fontsize=9)
    for ext in ("png", "svg"): fig.savefig(output / f"teaching_consistency.{ext}", dpi=170)
    plt.close(fig)
    dump(output / "provenance.json", dict(summary_sha256=sha(run / "summary.json"),
        complete_sha256=sha(run / "COMPLETE.json"), audit_sha256=sha(run / "INDEPENDENT_AUDIT.json"),
        plot_code_sha256=sha(__file__), outputs_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))
    print("Figures:", output, flush=True)


if __name__ == "__main__":
    main()
