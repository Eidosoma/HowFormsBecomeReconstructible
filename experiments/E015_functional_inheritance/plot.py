"""Fixed feasibility display: all settings, controls and damage cases."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("run", type=Path); args = parser.parse_args()
    cap_cpus(); run = args.run.resolve()
    if not run.is_relative_to(HERE / "runs"): raise ValueError("Local E015 run required")
    receipt = json.loads((run / "INDEPENDENT_AUDIT.json").read_text())
    assert receipt["status"] == "PASS" and receipt["complete_sha256"] == sha(run / "COMPLETE.json")
    complete = json.loads((run / "COMPLETE.json").read_text())
    assert complete["outputs_sha256"]["summary.json"] == sha(run / "summary.json")
    summary = json.loads((run / "summary.json").read_text())
    output = HERE / "figures" / run.name; output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(11.3, 5.4), layout="constrained", sharey=True)
    labels = ["Own record", "Opposite-rule record", "Shuffled edges", "Erased record", "Untrained scaffold",
              "Communication off", "Input isolated"]
    for ax, gain in zip(axes, summary["gains"]):
        group = summary["groups"][str(gain)]
        values = np.array([[group["accuracy"][d][arm]["mean"] for d in summary["damage"]] for arm in summary["arms"]])
        heat = ax.imshow(values, vmin=0, vmax=1, cmap="Blues", aspect="auto")
        for row in range(7):
            for col in range(3):
                ax.text(col, row, f"{100*values[row,col]:.1f}%", ha="center", va="center", color="white" if values[row,col] > .55 else "#222222")
        ax.set(xticks=range(3), xticklabels=["Intact", "24 cells removed", "3×3 lesion"],
               yticks=range(7), yticklabels=labels,
               title=f"Reader gain {gain:g} · {'all gates passed' if group['all_gates_pass'] else 'criterion not met'}")
        ax.tick_params(axis="both", length=0)
    fig.colorbar(heat, ax=axes, label="Fraction of successful trials", shrink=.8)
    stage = "disposable technical block" if summary["evidence_status"] == "technical" else f"{len(summary['blocks'])} development blocks"
    fig.suptitle(f"E015: taught routing in fresh bodies · {stage}")
    fig.supxlabel("Correct opposing outputs must exceed ±0.25; all cases retained. Gates also require rule-specific 95% block intervals.", fontsize=9)
    for ext in ("png", "svg"): fig.savefig(output / f"functional_feasibility.{ext}", dpi=170)
    plt.close(fig)
    dump(output / "provenance.json", dict(summary_sha256=sha(run / "summary.json"),
        complete_sha256=sha(run / "COMPLETE.json"), audit_sha256=sha(run / "INDEPENDENT_AUDIT.json"),
        plot_code_sha256=sha(__file__), outputs_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))
    print("Figures:", output, flush=True)


if __name__ == "__main__": main()
