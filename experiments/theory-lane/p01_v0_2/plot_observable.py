"""Export frozen toy forecasts; no fitting, new observations or native outcomes."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from two_mode import distributions

ROOT = Path(__file__).resolve().parent


def main():
    frozen = json.loads((ROOT / "results/observable_forecasts_v1.json").read_text())
    results = ROOT / "results"
    paths = [results / ("observable_forecasts." + ext) for ext in ("png", "svg", "csv")]
    if any(p.exists() for p in paths):
        raise FileExistsError("Preserve existing figure/data exports")
    h = np.array(frozen["horizons"])
    titles = ["Slow identity loss", "Faster identity loss", "Poor initial expression"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.5), sharey=True)
    rows = []
    for ax, title, case in zip(axes, titles, frozen["cases"], strict=True):
        truth = distributions(case["params"], h)
        forecast = np.asarray(case["forecasts"])
        ax.axvspan(0, 2, color="#B7C5D3", alpha=.5)
        ax.plot(h, truth[:, 0], color="#181818", lw=2, label="Exact toy probability")
        ax.plot(h, forecast[:, 0], "o--", color="#23789C", lw=1.7, ms=4,
                label="Two-mode / same HMM")
        baseline = case["ordinary_output_markov_forecasts"]
        if baseline is not None:
            baseline = np.asarray(baseline)
            ax.plot(h, baseline[:, 0], "s:", color="#B35E21", lw=1.7, ms=3.5,
                    label="Output Markov")
        else:
            ax.text(.04, .09, "Output Markov: missing source row", transform=ax.transAxes, fontsize=8)
        for i, depth in enumerate(h):
            rows.append(dict(case=case["name"], horizon=int(depth), exact_A=float(truth[i, 0]),
                             two_mode_A=float(forecast[i, 0]),
                             output_markov_A="" if baseline is None else float(baseline[i, 0])))
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Renewal horizon")
        ax.set_xlim(0, 64)
        ax.set_ylim(0, 1.03)
        ax.grid(alpha=.18)
    axes[0].set_ylabel("Probability of expressing rule A")
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9, bbox_to_anchor=(.5, .01))
    fig.suptitle("Constructed development: forecast from depths 0, 1 and 2", fontsize=13, y=.98)
    fig.text(.5, .905, "512 paths per case; one sampling realization; point estimates without confidence intervals",
             ha="center", fontsize=9)
    fig.subplots_adjust(top=.79, bottom=.22, left=.065, right=.985, wspace=.13)
    fig.savefig(paths[0], dpi=170)
    fig.savefig(paths[1])
    plt.close(fig)
    with paths[2].open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"exports": [str(p) for p in paths]}))


if __name__ == "__main__":
    main()
