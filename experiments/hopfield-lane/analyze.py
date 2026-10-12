"""Block-level descriptive analysis of H001; no input to simulated dynamics."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import model as m


def estimate(block_values):
    x = np.asarray(block_values, dtype=float)
    if len(x) == 1:
        return dict(mean=float(x.mean()), low=None, high=None,
                    positive_blocks=int((x > 0).sum()), blocks=1)
    random = m.rng(910011, "bootstrap", len(x))
    sampled = x[random.integers(0, len(x), (4000, len(x)))].mean(axis=1)
    return dict(mean=float(x.mean()), low=float(np.quantile(sampled, .025)),
                high=float(np.quantile(sampled, .975)), positive_blocks=int((x > 0).sum()),
                blocks=len(x))


def formatted(value):
    if value['low'] is None:
        return f"{100*value['mean']:.2f}% [one block; no interval]"
    return f"{100*value['mean']:.2f}% [{100*value['low']:.2f}, {100*value['high']:.2f}]"


def analyze(out):
    config = json.loads((out/"config.json").read_text())
    summary = {"status": "EXPLORATORY_DEVELOPMENT", "blocks": config["blocks"],
               "intervals": "Pointwise 95% whole-block bootstrap; no multiplicity correction"}
    curves = {}
    for task in ("capture", "function"):
        values, metrics, body, stability, diversity, rule_results = [], [], [], [], [], []
        for seed in config["seeds"]:
            with np.load(out/f"{task}_{seed}.npz") as raw:
                values.append(raw["success"].mean(axis=(-2, -1)))
                metrics.append(raw["metric"].mean(axis=(-2, -1)))
                body.append(raw["body_success"].mean(axis=(-2, -1)))
                checkpoints, arms = raw["checkpoints"], raw["arms"].tolist()
                founder = raw["founder"]
                stability.append(float(np.all(founder == raw["stable_founder"], axis=-1).mean()))
                diversity.append(len(np.unique(founder.reshape(4, -1), axis=0)))
                if task == "function":
                    per_rule = raw["success"].reshape(len(checkpoints), len(arms), 2, 2, 4).mean(axis=(-2, -1))
                    rule_results.append(per_rule)
        values, metrics, body = np.array(values), np.array(metrics), np.array(body)
        curves[task] = (checkpoints, values, arms)
        terminal = {arm: estimate(values[:, -1, i]) for i, arm in enumerate(arms)}
        differences = {f"renewal_minus_{arm}": estimate(values[:, -1, 0]-values[:, -1, i])
                       for i, arm in enumerate(arms) if i}
        metric_differences = {f"renewal_minus_{arm}": estimate(metrics[:, -1, 0]-metrics[:, -1, i])
                              for i, arm in enumerate(arms) if i}
        summary[task] = dict(terminal=terminal, contrasts=differences,
                             metric_contrasts=metric_differences,
                             initial_renewal=estimate(values[:, 0, 0]),
                             terminal_body=estimate(body[:, -1, 0]),
                             stable_founder_fraction=float(np.mean(stability)),
                             distinct_founders_per_block=diversity,
                             checkpoints=checkpoints.tolist(),
                             mean_success=values.mean(axis=0).tolist())
        if task == "function":
            summary[task]["terminal_by_rule"] = np.array(rule_results)[:, -1, 0].mean(axis=0).tolist()
    repair_success, repair_agreement = [], []
    for seed in config["seeds"]:
        with np.load(out/f"repair_{seed}.npz") as raw:
            repair_success.append(raw["success"].mean(axis=(-2, -1)))
            repair_agreement.append(raw["metric"].mean(axis=(-2, -1)))
            repair_arms = raw["arms"].tolist()
    repair_success, repair_agreement = np.array(repair_success), np.array(repair_agreement)
    repair_pairs = [("live_kept_minus_damaged", 1, 0), ("live_kept_minus_live_scrambled", 1, 2),
                    ("live_kept_minus_fixed_kept", 1, 3), ("fixed_kept_minus_damaged", 3, 0),
                    ("live_kept_minus_read_off", 1, 5)]
    summary["repair"] = dict(
        completion={a: estimate(repair_success[:, i]) for i, a in enumerate(repair_arms)},
        agreement={a: estimate(repair_agreement[:, i]) for i, a in enumerate(repair_arms)},
        contrasts={label: estimate(repair_success[:, i]-repair_success[:, j]) for label, i, j in repair_pairs})
    with np.load(out/"cellular.npz") as raw:
        ready, editing = raw["readiness"], raw["editing"]
        success = (np.tanh(2*ready) > .5).all(axis=-1)
        edit_success = (np.tanh(2*editing)*np.array([1., -1.])[None, None, None, :, None, None] > .5).all(axis=-1)
        modes = raw["modes"].tolist()
        panel = []
        for i, (a, g) in enumerate(raw["parameters"]):
            panel.append(dict(self_coupling=float(a), coupling=float(g),
                              immature={mode: bool(success[1, i, 0, j, -1]) for j, mode in enumerate(modes)},
                              prepared={mode: bool(success[1, i, 1, j, -1]) for j, mode in enumerate(modes)},
                              edited=bool(edit_success[1, i, 0, :, -1].all()),
                              sham_reverses=bool(edit_success[1, i, 1, 1, -1]),
                              blocked_edit_succeeds=bool(edit_success[1, i, 2, :, -1].all())))
        summary["cellular"] = dict(panels=panel,
            refinement_max_abs=float(max(np.max(abs(ready[0]-ready[1])), np.max(abs(editing[0]-editing[1])))),
            refinement_readiness_labels_agree=bool(np.array_equal(success[0], success[1])),
            refinement_editing_labels_agree=bool(np.array_equal(edit_success[0], edit_success[1])),
            statistical_unit="Deterministic related parameter panels; no population confidence intervals")
    (out/"summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")

    text = ["# H001 development results", "", f"{config['blocks']} independent random-base blocks; "
            f"four founders and four descendants per founder; {config['generations']} replacements.",
            "All intervals below are exploratory, pointwise 95% whole-block bootstrap intervals. "
            "This is a feasibility screen, not a fresh-cohort confirmation.", ""]
    for task in ("capture", "function"):
        text += [f"## {task.title()}", "", "| Arm | Terminal completion |", "|---|---:|"]
        text += [f"| {a} | {formatted(v)} |" for a, v in summary[task]["terminal"].items()]
        text += ["", "Contrasts are paired percentage-point differences:", "",
                 "| Contrast | Difference [interval] |", "|---|---:|"]
        text += [f"| {a} | {formatted(v)} |" for a, v in summary[task]["contrasts"].items()]
        text += ["", f"Initial completion: {formatted(summary[task]['initial_renewal'])}. "
                 f"Last rebuilding-body completion: {formatted(summary[task]['terminal_body'])}.",
                 f"Founder stability under another 24 teaching/formation sweeps: "
                 f"{summary[task]['stable_founder_fraction']:.3f}. "
                 f"Distinct observed founders by block: {summary[task]['distinct_founders_per_block']}.", ""]
    text += ["## Reciprocal repair", "", "| Arm | Completion | Agreement |", "|---|---:|---:|"]
    text += [f"| {a} | {formatted(summary['repair']['completion'][a])} | "
             f"{formatted(summary['repair']['agreement'][a])} |" for a in repair_arms]
    text += ["", "| Contrast | Completion difference [interval] |", "|---|---:|"]
    text += [f"| {a} | {formatted(v)} |" for a, v in summary["repair"]["contrasts"].items()]
    text += ["", "## Continuous transmission screen", "",
             "Each entry is one deterministic parameter setting at dt=0.0125. True/false is a "
             "bounded-model outcome; these settings are not independent experimental replicates.", "",
             "| Self | Contact | Immature/open | Prepared/open | Immature/immediate pause | Edited relay | Sham reverses | Blocked relay/edit |",
             "|---:|---:|---|---|---|---|---|---|"]
    for p in panel:
        text.append(f"| {p['self_coupling']} | {p['coupling']} | {p['immature']['open']} | "
                    f"{p['prepared']['open']} | {p['immature']['immediate_pause']} | {p['edited']} | "
                    f"{p['sham_reverses']} | {p['blocked_edit_succeeds']} |")
    text += ["", f"Maximum state discrepancy on halving dt: {summary['cellular']['refinement_max_abs']:.6g}. "
             f"Readiness labels agree: {summary['cellular']['refinement_readiness_labels_agree']}; "
             f"editing labels agree: {summary['cellular']['refinement_editing_labels_agree']}.", "",
             "## Interpretation boundary", "",
             "The binary writer is a supplied, redundant coactivity encoder. Dense connectivity, "
             "input sites, timing and coordinate conventions are also supplied. Successful "
             "renewal would establish a mechanism specimen under these conditions; it would not "
             "establish spontaneous useful competence or evolved reconstruction machinery. "
             "Capture and functional teaching are separate experiments. The continuous model "
             "does not reproduce molecular regulation or the original cellular time scales.", "",
             "Terminal fresh readers and the last rebuilding bodies use different independent "
             "births. Their aggregate difference alone is not evidence for recovery along the "
             "same body history. Copying comparisons have equal packet allocation, not equal "
             "computation cost. Correlation-preserving and address controls test the stated "
             "interfaces only. No pilot result has been added to the forms manuscript.", ""]
    (out/"REPORT.md").write_text("\n".join(text))
    plot(out, curves, repair_success, repair_arms, summary)


def plot(out, curves, repair_success, repair_arms, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    for axis, task in zip(axes[0], ("capture", "function")):
        horizons, values, arms = curves[task]
        for a in ("renewal", "foreign", "erased", "protected_copy", "damaged_copy"):
            i = arms.index(a)
            axis.plot(horizons, values.mean(axis=0)[:, i]*100, marker="o", label=a.replace("_", " "))
        axis.set(title=f"{task.title()}: independent fresh readers", xlabel="Completed replacements",
                 ylabel="Completion (%)", ylim=(-3, 103))
        axis.legend(fontsize=8)
    axis = axes[1, 0]
    for block in repair_success:
        axis.plot(np.arange(len(repair_arms)), block*100, color=".8", lw=.8)
    axis.plot(repair_success.mean(axis=0)*100, "o-", color="#154c79", lw=2)
    axis.set_xticks(np.arange(len(repair_arms)), [s.replace("_", "\n") for s in repair_arms], fontsize=8)
    axis.set(title="Reciprocal repair: paired block means", ylabel="Fresh-reader completion (%)", ylim=(-3, 103))
    axis = axes[1, 1]
    labels = [f"{p['self_coupling']}, {p['coupling']}" for p in summary["cellular"]["panels"]]
    matrix = np.array([[p["immature"]["open"], p["prepared"]["open"],
                       p["immature"]["immediate_pause"], p["edited"]] for p in summary["cellular"]["panels"]])
    axis.imshow(matrix, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    for (i, j), value in np.ndenumerate(matrix):
        axis.text(j, i, "yes" if value else "no", ha="center", va="center", color="white" if value else "black", fontsize=8)
    axis.set_yticks(np.arange(len(labels)), labels, fontsize=8)
    axis.set_xticks(np.arange(4), ["Immature\nopen", "Prepared\nopen", "Immature\npause", "Edited\nrelay"], fontsize=8)
    axis.set(title="Continuous analogue: deterministic screen", ylabel="Self coupling, contact coupling")
    fig.suptitle("H001 exploratory feasibility — separate tasks and information boundaries", fontsize=13)
    fig.savefig(out/"overview.png", dpi=170)
    fig.savefig(out/"overview.pdf")
    plt.close(fig)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    analyze(parser.parse_args().run)
