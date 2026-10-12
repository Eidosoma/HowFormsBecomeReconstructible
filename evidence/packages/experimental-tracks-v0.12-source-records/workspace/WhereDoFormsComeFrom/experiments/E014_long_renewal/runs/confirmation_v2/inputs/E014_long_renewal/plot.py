"""Fixed displays of absolute fidelity, history specificity and copying loss."""
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
    parser = argparse.ArgumentParser(); parser.add_argument("run", type=Path)
    args = parser.parse_args(); cap_cpus()
    run = args.run.resolve()
    if not run.is_relative_to(HERE / "runs"): raise ValueError("Local E014 run required")
    audit = json.loads((run / "INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(run / "COMPLETE.json")
    summary = json.loads((run / "summary.json").read_text())
    complete = json.loads((run / "COMPLETE.json").read_text())
    assert sha(run / "summary.json") == complete["outputs_sha256"]["summary.json"]
    output = HERE / "figures" / run.name; output.mkdir(parents=True, exist_ok=False)
    checkpoints = summary["checkpoint_numbers"]
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.4), layout="constrained")
    for factor, color, offset in ((1, "#176b91", -.10), (4, "#b65c21", .10)):
        group = summary["groups"][str(factor)]; label = f"{group['packet_bytes']} bytes"
        for ax, measure in zip(axes, ("own", "specificity", "copy_gap")):
            if measure == "own":
                stats = [group["own_statistics"][f"after_{g}"]["rewrite"] for g in checkpoints]
            else:
                name = "rewrite_minus_foreign" if measure == "specificity" else "rewrite_minus_copy"
                stats = [group["contrasts"][f"after_{g}"][name] for g in checkpoints]
            mean = np.array([100 * st["mean"] for st in stats])
            bounds = np.array([st["ci95"] for st in stats]).T * 100
            ax.errorbar(np.array(checkpoints) + offset, mean, yerr=np.stack((mean - bounds[0], bounds[1] - mean)),
                        color=color, marker="o", lw=1.5, capsize=3, label=label)
        copy = [100 * group["own_statistics"][f"after_{g}"]["copy"]["mean"] for g in checkpoints]
        axes[0].plot(checkpoints, copy, color=color, ls="--", alpha=.55)
    titles = ("Absolute founder agreement", "Historical specificity", "Loss relative to protected copying")
    labels = ("Resolved sign agreement (%)", "Own − foreign record (percentage points)", "Rewrite − copy (percentage points)")
    for i, (ax, title, label) in enumerate(zip(axes, titles, labels)):
        ax.set(title=title, ylabel=label, xlabel="Completed rewrites", xticks=checkpoints)
        ax.grid(axis="y", alpha=.2)
        if i: ax.axhline(0, color="#666666", lw=.8, ls=":")
    axes[0].legend(frameon=False, loc="best")
    fig.suptitle(f"E014: fresh readers after 1, 3, 8 and 16 replacements · {len(summary['source_blocks'])} independent blocks")
    fig.supxlabel("95% whole-block intervals (pointwise); dashed lines show protected-copy agreement.", fontsize=9)
    for extension in ("png", "svg"):
        fig.savefig(output / f"long_renewal.{extension}", dpi=170)
    plt.close(fig)
    dump(output / "provenance.json", dict(summary_file=str((run / "summary.json").relative_to(ROOT)),
        summary_sha256=sha(run / "summary.json"), complete_sha256=sha(run / "COMPLETE.json"),
        audit_sha256=sha(run / "INDEPENDENT_AUDIT.json"), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))
    print("Figures:", output, flush=True)


if __name__ == "__main__": main()
