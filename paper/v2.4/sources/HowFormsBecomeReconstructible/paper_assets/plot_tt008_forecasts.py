#!/usr/bin/env python3
"""Present frozen TT008 forecasts; no dynamics, fitting or recalibration.

Reliability bins and AUC are post hoc descriptions. Primary comparisons and
pass/fail contributions are checked against the retained scoring record.
"""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "paper_assets/data/tt008-forecast-v0.18-source-records.zip"
INSPECTION = ROOT / "reviews/V0.18_TT008_FORECAST_SOURCES.json"
BASE = "experiments/theory-tests-lane/TT008/"
RUN = BASE + "runs/prospective_v2/"
MODELS = ("expression_history", "expression_unsigned", "candidate")
GROUPS = ("all", "failing", "passing")
LABELS = ("Expression + history", "+ unsigned access", "+ signed transfer (candidate)")
COLORS = ("#667482", "#C17D15", "#007F91")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def identity(row):
    return tuple(row[k] for k in ("block", "history", "founder", "recipient"))


def auc(y, p):
    n1, n0 = int(y.sum()), int((1-y).sum())
    ranks = rankdata(p, method="average")
    result = float((ranks[y == 1].sum() - n1*(n1+1)/2)/(n1*n0))
    # Independent pair-count check includes half credit for ties.
    positive, negative = p[y == 1, None], p[None, y == 0]
    pairwise = float(((positive > negative) + .5*(positive == negative)).mean())
    assert abs(result-pairwise) < 1e-14
    return result


def main():
    inspection = json.loads(INSPECTION.read_text())
    assert sha(ARCHIVE) == inspection["archive_sha256"]
    with zipfile.ZipFile(ARCHIVE) as z:
        for source in inspection["sources"]:
            assert hashlib.sha256(z.read(source["member"])).hexdigest() == source["sha256"]
        read = lambda path: json.loads(z.read(path))
        table = lambda path: list(csv.DictReader(io.StringIO(z.read(path).decode())))
        native = read(RUN + "analysis.json")
        manifest = read(RUN + "manifest.json")
        for source in inspection["sources"]:
            relative = source["member"].removeprefix(BASE)
            if relative in manifest["inputs_sha256"]:
                assert source["sha256"] == manifest["inputs_sha256"][relative]
        features = {identity(r): r for r in table(RUN + "features.csv")}
        predictions = {(r["model"], identity(r)): float(r["probability"])
                       for r in table(RUN + "predictions.csv")}
        scored = table(RUN + "scored_predictions.csv")
        terminal = {}
        for b in range(8800000, 8800064):
            for row in table(RUN + f"blocks/{b}/terminal.csv"):
                if row["injury"] == "scattered" and row["history"] != "erased":
                    terminal[identity(row)] = int(row["terminal_success"])

    assert len(features) == len(terminal) == 4096
    assert len(scored) == len(predictions) == 24576
    keys = sorted(features)
    assert set(keys) == set(terminal)
    y = np.array([terminal[k] for k in keys])
    current = np.array([int(features[k]["current_pass"]) for k in keys])
    blocks = np.array([int(k[0]) for k in keys])
    assert np.unique(blocks, return_counts=True)[1].tolist() == [64]*64
    for row in scored:
        k = identity(row)
        p = predictions[row["model"], k]
        assert p == float(row["probability"]) and int(row["target"]) == terminal[k]
        assert abs((p-terminal[k])**2-float(row["brier"])) < 1e-14
    for model in native["models"]:
        loss = np.array([(predictions[model, k]-terminal[k])**2 for k in keys])
        assert abs(float(loss.mean())-native["metrics"][model]["all"]["brier"]) < 1e-14

    masks = {"all": np.ones(4096, bool), "failing": current == 0, "passing": current == 1}
    probabilities = {m: np.array([predictions[m, k] for k in keys]) for m in MODELS}
    metrics, reliability, contributions = [], [], []
    for m in MODELS:
        for group, mask in masks.items():
            p, yy = probabilities[m][mask], y[mask]
            bins = np.minimum((p*10).astype(int), 9)
            calibration = 0.
            for b in range(10):
                take = bins == b
                if not take.any():
                    continue
                n, mp, freq = int(take.sum()), float(p[take].mean()), float(yy[take].mean())
                calibration += n/len(yy)*(mp-freq)**2
                reliability.append(dict(model=m, group=group, bin=b, lower=b/10,
                                        upper=(b+1)/10, records=n,
                                        mean_probability=mp, observed_frequency=freq))
            metrics.append(dict(model=m, group=group, records=len(yy), successes=int(yy.sum()),
                                brier=float(np.mean((p-yy)**2)), auc=auc(yy, p),
                                mean_probability=float(p.mean()), observed_frequency=float(yy.mean()),
                                binned_calibration_error=calibration))
    for m in MODELS[:2]:
        gain = (probabilities[m]-y)**2 - (probabilities["candidate"]-y)**2
        block_gain = [float(gain[blocks == b].mean()) for b in np.unique(blocks)]
        np.testing.assert_allclose(block_gain, native["contrasts"][m]["block_values"], rtol=0, atol=1e-14)
        for group in ("failing", "passing"):
            values = gain[masks[group]]
            contribution = math.fsum(values)/4096
            saved = native["strata"][str(int(group == "passing"))]["contrasts"][m]
            assert abs(contribution-saved["contribution_to_overall"]) < 1e-14
            assert abs(float(values.mean())-saved["conditional_record_mean"]) < 1e-14
            contributions.append(dict(comparator=m, group=group, records=len(values),
                                      conditional_gain=float(values.mean()),
                                      contribution_to_overall=contribution))

    data = dict(study="TT008", run="prospective_v2", blocks=64, records=4096,
                source_archive=str(ARCHIVE.relative_to(ROOT)), archive_sha256=sha(ARCHIVE),
                source_inspection=str(INSPECTION.relative_to(ROOT)), source_inspection_sha256=sha(INSPECTION),
                selection="All records, candidate and both primary rivals; no outcome filtering.",
                bins="Ten equal-width bins [0,.1),...,[.9,1]; empty bins omitted.",
                new_analysis="Post hoc descriptive reliability and AUC; no new intervals, fitting or recalibration.",
                weighting="All-record means equal block-weighted means (64 records/block); subgroup metrics pool records and are descriptive.",
                limits="Binned calibration error depends on the bins and does not exactly decompose the unbinned Brier score. Records within blocks are related.",
                metrics=metrics, reliability=reliability, contributions=contributions,
                original_primary_contrasts={m:native["contrasts"][m] for m in MODELS[:2]},
                matched_decisions=native["matched_decisions"],
                verification=dict(sealed_predictions_and_scored_rows=24576,
                                  terminal_csv_targets=4096, original_model_brier_means=6,
                                  original_primary_block_differences=128,
                                  original_subgroup_contributions=4,
                                  auc_rank_and_pairwise_agree=True,
                                  native_arrays_audited=False, simulations_run=False))
    data_path = ROOT / "paper_assets/data/tt008-forecast-v0.18.json"
    csv_path = ROOT / "paper_assets/data/tt008-reliability-v0.18.csv"
    dump(data_path, data)
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(reliability[0]))
        w.writeheader(); w.writerows(reliability)

    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10.5,
                         "axes.spines.top":False, "axes.spines.right":False,
                         "svg.hashsalt":"tt008-forecast-v018"})
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 9.1))
    fig.subplots_adjust(left=.09, right=.975, bottom=.16, top=.845, hspace=.48, wspace=.27)
    fig.suptitle("Record diagnostics improve forecasts chiefly among current failures", fontsize=17, y=.98, weight="bold", color="#123C50")
    handles = []
    for ax, group, letter, title in [(axes[0,0], "all", "A", "All records: reliability"),
                                      (axes[0,1], "failing", "B", "Current failures: reliability")]:
        ax.plot([0,1], [0,1], color="#A1A7AC", ls="--", lw=1, zorder=0)
        for i, m in enumerate(MODELS):
            rows = [r for r in reliability if r["model"] == m and r["group"] == group]
            line, = ax.plot([r["mean_probability"] for r in rows], [r["observed_frequency"] for r in rows],
                            marker=("o", "s", "D")[i], ms=4.5, lw=1.7, color=COLORS[i], label=LABELS[i])
            if group == "all": handles.append(line)
        ax.set(xlim=(0,1), ylim=(0,1), xlabel="Mean forecast probability", ylabel="Observed success fraction")
        ax.set_title(f"{letter}  {title}", loc="left", fontsize=12, pad=10, weight="bold")
        ax.grid(alpha=.15)
        ax.text(.04,.95, f"n = {int(masks[group].sum()):,} records\n10 fixed probability bins", transform=ax.transAxes, va="top", fontsize=9)

    ax = axes[1,0]
    for i, m in enumerate(MODELS[:2]):
        rows = [next(r for r in contributions if r["comparator"] == m and r["group"] == g)
                for g in ("failing", "passing")]
        pos = np.arange(2)+(i-.5)*.28
        values = [1000*r["contribution_to_overall"] for r in rows]
        ax.barh(pos, values, height=.23, color=COLORS[i], alpha=.88)
        for x, yy in zip(values, pos):
            ax.text(x+(.15 if x>=0 else -.12), yy, f"{x:+.3f}", ha="left" if x>=0 else "right", va="center", fontsize=9)
    ax.axvline(0, color="#6A7680", lw=.8)
    ax.set(yticks=[0,1], yticklabels=["Failing\n(n = 672)", "Passing\n(n = 3,424)"], xlim=(-1.6,11.3),
           xlabel="Contribution to overall Brier gain (×10⁻³)")
    ax.invert_yaxis();ax.grid(axis="x", alpha=.15)
    ax.set_title("C  Where the candidate gains", loc="left", fontsize=12, pad=10, weight="bold")
    ax.text(.02,-.27,"Grey: versus expression/history; amber: versus + unsigned.\nPositive values favor the candidate; no subgroup intervals.",transform=ax.transAxes,fontsize=8.5,va="top")

    ax = axes[1,1]
    for i, m in enumerate(MODELS):
        values = [next(r["auc"] for r in metrics if r["model"]==m and r["group"]==g) for g in GROUPS]
        pos = np.arange(3)+(i-1)*.2
        ax.scatter(values,pos,s=34,c=COLORS[i],marker=("o","s","D")[i],zorder=3)
        for x, yy in zip(values, pos):ax.text(x+.012,yy,f"{x:.3f}",va="center",fontsize=8.5,color=COLORS[i])
    ax.axvline(.5, color="#A1A7AC", ls="--", lw=1)
    ax.set(yticks=[0,1,2],yticklabels=["All", "Failing", "Passing"],xlim=(.45,.97),
           xlabel="ROC AUC (higher means better ranking)")
    ax.invert_yaxis();ax.grid(axis="x",alpha=.15)
    ax.set_title("D  Discrimination, separately measured",loc="left",fontsize=12,pad=10,weight="bold")
    fig.legend(handles,LABELS,ncol=3,loc="upper center",bbox_to_anchor=(.52,.937),frameon=False,fontsize=10)
    fig.text(.5,.018,"Same frozen forecasts and outcomes · 64 independent blocks · Reliability and AUC are descriptive post hoc checks",ha="center",fontsize=9,color="#56616A")
    outputs=[]
    for suffix in ("png","svg"):
        path=ROOT/f"paper_assets/figures/data-tt008-forecast-v0.18.{suffix}"
        fig.savefig(path,dpi=200,facecolor="white",metadata={"Date":None} if suffix=="svg" else {"Software":"Matplotlib"})
        outputs.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path)))
    plt.close(fig)
    dump(ROOT/"paper_assets/figures/tt008-forecast-assets-v0.18.json",
         dict(figure_id="fig-tt008-forecast",kind="post-hoc-measured",png="data-tt008-forecast-v0.18.png",
              data=str(data_path.relative_to(ROOT)),data_sha256=sha(data_path),
              csv=str(csv_path.relative_to(ROOT)),csv_sha256=sha(csv_path),
              archive=str(ARCHIVE.relative_to(ROOT)),archive_sha256=sha(ARCHIVE),
              source_inspection=str(INSPECTION.relative_to(ROOT)),source_inspection_sha256=sha(INSPECTION),
              plot_script=str(Path(__file__).relative_to(ROOT)),plot_script_sha256=sha(Path(__file__)),
              outputs=outputs,new_simulations=False,primary_qualification_unchanged=True))
    print("Verified 24,576 scored predictions, 4,096 CSV targets, six Brier means, 128 primary block differences and four subgroup contributions.")
    print("Rendered descriptive reliability, subgroup contributions and AUC; no refit, recalibration or new uncertainty estimates.")


if __name__ == "__main__":
    main()
