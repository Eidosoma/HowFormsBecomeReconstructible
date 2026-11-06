"""Offline scoring. Founder prototypes are confined to this module."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import bootstrap, dump
from model import ARMS, unpack
import numpy as np

STAGES = ("G1", "G2", "G3", "terminal")
CONTRASTS = (("rewrite", "foreign"), ("copy", "erased"), ("rewrite", "read_off"),
             ("rewrite", "write_off"), ("rewrite", "copy"), ("rewrite", "shuffled"),
             ("rewrite", "background"), ("rewrite", "challenged"))


def score(v, prototypes, qualified=True):
    """v: stage, founder, replicate, arm, y, x. Return every observer target."""
    return np.stack([(((v > 0) == (p > 0)) & ((abs(v) > .2) if qualified else True)).mean(axis=(-2,-1))
                     for p in prototypes], axis=-1)


def own_scores(all_scores):
    f = all_scores.shape[1]
    indices = np.arange(f)[None, :, None, None, None]
    return np.take_along_axis(all_scores, indices, axis=-1)[..., 0]


def formation_metrics(raw):
    p = raw["prototype"]
    signs = p > 0
    positive = signs.mean(axis=(-2,-1))
    resolved = (abs(p) > .2).mean(axis=(-2,-1))
    neighbor = ((signs == np.roll(signs, 1, -1)).mean(axis=(-2,-1))
                + (signs == np.roll(signs, 1, -2)).mean(axis=(-2,-1))) / 2
    stability = ((raw["prototype_halves"][0] > 0) == (raw["prototype_halves"][1] > 0)).mean(axis=(-2,-1))
    qualified = (positive >= .1) & (positive <= .9) & (resolved >= .8) & (neighbor >= .65) & (stability >= .8)
    disagreement = [float((signs[i] != signs[j]).mean()) for i in range(len(p)) for j in range(i)]
    # Sign balance, amplitude, roughness, and temporal consistency stay separate.
    return dict(positive_fraction=positive.tolist(), resolved_fraction=resolved.tolist(),
                neighbor_agreement=neighbor.tolist(), half_window_agreement=stability.tolist(),
                qualified=qualified.tolist(), pairwise_disagreement=disagreement,
                capture_endpoint_sign_agreement=((raw["capture_end"][:,0,0] > 0) == signs).mean(axis=(-2,-1)).tolist())


def analyze(output, ids, backgrounds, technical=False):
    output = Path(output)
    groups = {}
    individual = []
    for background in backgrounds:
        obs, prefs, donor, signonly, formation, budgets, budget_stds = [], [], [], [], [], [], []
        for b in ids:
            with np.load(output / f"block_{b:06d}_{background}.npz", allow_pickle=False) as raw:
                v = np.concatenate((raw["generation_read"][:,:,:,:,0], raw["terminal"][None,:,:,:,0]), axis=0)
                q = score(v, raw["prototype"])
                own = own_scores(q)
                pref = own - (q.sum(axis=-1)-own)/(len(raw["prototype"])-1)
                obs.append(own.mean(axis=(1,2)))
                prefs.append(pref.mean(axis=(1,2)))
                signonly.append(own_scores(score(v, raw["prototype"], False)).mean(axis=(1,2)))
                donor_idx = np.roll(np.arange(len(raw["prototype"])), -1)[None,:,None,None,None]
                donor.append(np.take_along_axis(q, donor_idx, axis=-1)[...,0].mean(axis=(1,2)))
                formation.append(dict(block=b, **formation_metrics(raw)))
                budget = own_scores(score(raw["budget_terminal"][:,:,:,:,0], raw["prototype"]))
                budgets.append(budget.mean(axis=(1,2)))
                budget_stds.append([float(unpack(raw[f"budget_payload_{f}"], f)[:,:,0].std(axis=(-2,-1)).mean()) for f in (1,2,4)])
                for s, stage in enumerate(STAGES):
                    for founder in range(len(raw["prototype"])):
                        for replica in range(own.shape[2]):
                            for a, arm in enumerate(ARMS):
                                individual.append(dict(background=background, block=b, founder=founder, recipient=replica,
                                    stage=stage, arm=arm, qualified_own=float(own[s,founder,replica,a]),
                                    preference=float(pref[s,founder,replica,a])))
        obs, prefs, donor, signonly, budgets = map(np.asarray, (obs, prefs, donor, signonly, budgets))
        contrasts = {}
        for s, stage in enumerate(STAGES):
            contrasts[stage] = {}
            for left, right in CONTRASTS:
                x = obs[:,s,ARMS.index(left)] - obs[:,s,ARMS.index(right)]
                contrasts[stage][left+"_minus_"+right] = bootstrap(x, "E001:"+background)
        qualified = sum(sum(f["qualified"]) for f in formation)
        nfounders = sum(len(f["qualified"]) for f in formation)
        diversity = float(np.mean([v for f in formation for v in f["pairwise_disagreement"]]))
        lower = lambda stage, contrast: contrasts[stage][contrast]["ci95"][0] > 0
        gates = dict(formation=qualified/nfounders >= .75 and diversity > .10,
                     acquired_readable=lower("G1", "copy_minus_erased"),
                     all_four_specific=all(lower(s,"rewrite_minus_foreign") for s in STAGES),
                     terminal_read_required=lower("terminal", "rewrite_minus_read_off"),
                     terminal_write_required=lower("terminal", "rewrite_minus_write_off"))
        if technical:
            verdict = "TECHNICAL_ONLY"
        elif all(gates.values()):
            verdict = "PILOT_ORIGIN_TO_RENEWAL_QUALIFIED"
        elif not gates["formation"]:
            verdict = "FORMATION_NOT_QUALIFIED"
        elif not gates["acquired_readable"]:
            verdict = "ACQUISITION_OR_READOUT_UNRESOLVED"
        else:
            verdict = "RENEWAL_UNRESOLVED"
        budget_rows = []
        for k, factor in enumerate((1,2,4)):
            budget_rows.append(dict(factor=factor, bytes=2048//factor**2,
                decoded_field_sd=float(np.asarray(budget_stds)[:,k].mean()),
                own_mean=float(budgets[:,k,0].mean()), foreign_mean=float(budgets[:,k,1].mean()),
                own_minus_foreign=bootstrap(budgets[:,k,0]-budgets[:,k,1], "E001:"+background),
                own_minus_zero=bootstrap(budgets[:,k,0]-budgets[:,k,2], "E001:"+background)))
        groups[background] = dict(verdict=verdict, gates=gates, founder_count=nfounders,
            formation_qualified_count=int(qualified), mean_pairwise_disagreement=diversity,
            formation=formation, contrasts=contrasts, stages=STAGES, arms=ARMS,
            qualified_own_means=obs.mean(axis=0).tolist(), preference_means=prefs.mean(axis=0).tolist(),
            donor_agreement_means=donor.mean(axis=0).tolist(), sign_only_means=signonly.mean(axis=0).tolist(),
            block_qualified_own=obs.tolist(), block_preference=prefs.tolist(), budgets=budget_rows)
    dump(output / "summary.json", dict(experiment="E001", evidence_status="technical" if technical else "development_pilot",
        blocks=ids, groups=groups, uncertainty="pointwise percentile bootstrap of complete blocks; 10000 draws",
        payload_bytes=2048, renewal_generations=3, terminal_additional_transfer=True,
        supplied_target=False, evolved_writer=False, arbitrary_pattern_capacity_established=False))
    with (output / "observations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(individual[0]))
        writer.writeheader()
        writer.writerows(individual)
    report = ["# E001 development pilot", "", "All declared founders retained. Intervals below are exploratory, pointwise 95% block bootstraps.",
              "The original founder is observed before capture; no supplied target enters the dynamics.", ""]
    fmt = lambda s: f"{100*s['mean']:+.2f} [{100*s['ci95'][0]:+.2f}, {100*s['ci95'][1]:+.2f}]"
    for name, g in groups.items():
        report += [f"## {name.capitalize()}", "", f"Status: **{g['verdict']}**.",
                   f"Formation qualified {g['formation_qualified_count']}/{g['founder_count']} founders; mean within-block sign disagreement {100*g['mean_pairwise_disagreement']:.1f}%.", "",
                   "| Incoming record | Own versus foreign effect, percentage points | Own agreement: rewrite / copy |",
                   "| --- | --- | --- |"]
        for s, stage in enumerate(STAGES):
            means = g["qualified_own_means"][s]
            report.append(f"| {stage} | {fmt(g['contrasts'][stage]['rewrite_minus_foreign'])} | {100*means[0]:.1f}% / {100*means[ARMS.index('copy')]:.1f}% |")
        report += ["", "Terminal controls (qualified own agreement differences, percentage points):", ""]
        for key, stats in g["contrasts"]["terminal"].items():
            if key != "rewrite_minus_foreign":
                report.append(f"- {key}: {fmt(stats)}.")
        report += ["", "One-transfer capacity panel (different readers from serial lineages):", "",
                   "| Packet bytes | Own versus foreign, points | Decoded field SD |", "| --- | --- | --- |"]
        for row in g["budgets"]:
            report.append(f"| {row['bytes']} | {fmt(row['own_minus_foreign'])} | {row['decoded_field_sd']:.4f} |")
        report += ["", "Gate outcomes: `"+json.dumps(g["gates"], sort_keys=True)+"`.", ""]
    report += ["## Scope", "", "This is a finite development pilot under an engineered writer, normalized full-field carrier, shared coordinates, and supplied replacement schedule. It does not establish an evolved writer, biological heredity, arbitrary-pattern competence, or indefinite renewal. Smaller-packet results cover one transfer and change spatial resolution and amplitude together. Formation failures stay in every denominator. The held/erased alias is a construction, not an independent confirmation.", "",
               "Raw fields, packet bytes, every observation, code snapshots, source hashes, and run checks are retained alongside this report."]
    (output / "REPORT.md").write_text("\n".join(report)+"\n")
    if not technical:
        plot(output, groups, ids)


def plot(output, groups, ids):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(groups), figsize=(11,4.2), squeeze=False)
    for ax, (name, group) in zip(axes[0], groups.items()):
        means = np.array(group["qualified_own_means"])
        for arm in ("rewrite", "foreign", "copy", "read_off", "challenged"):
            ax.plot(range(4), 100*means[:, ARMS.index(arm)], marker="o", label=arm)
        ax.set(title=name, xticks=range(4), xticklabels=STAGES, ylabel="Agreement with founder (%)", ylim=(0,100))
        ax.spines[["top","right"]].set_visible(False)
        ax.legend(fontsize=8)
    fig.suptitle("E001: all founders retained; 3 rewrites plus a fresh terminal reader")
    fig.tight_layout()
    fig.savefig(output / "renewal.png", dpi=180)
    fig.savefig(output / "renewal.svg")
    plt.close(fig)
    # Fixed cohort slice, chosen by ID rather than outcome.
    fig, axes = plt.subplots(4*len(groups), 4, figsize=(8,3.1*len(groups)*2), squeeze=False)
    for k, background in enumerate(groups):
        with np.load(output / f"block_{ids[0]:06d}_{background}.npz") as raw:
            for f in range(4):
                panels = [raw["prototype"][f], unpack(raw["acquired"])[f,0],
                          raw["generation_read"][0,f,0,0,0], raw["terminal"][f,0,0,0]]
                for j, panel in enumerate(panels):
                    ax = axes[k*4+f,j]
                    ax.imshow(panel, cmap="coolwarm", vmin=-1 if j!=1 else -.6, vmax=1 if j!=1 else .6)
                    ax.set_xticks([]); ax.set_yticks([])
                    if k*4+f == 0:
                        ax.set_title(("Founder late mean", "Captured record", "G1 body", "Terminal body")[j], fontsize=9)
                    if j == 0:
                        ax.set_ylabel(f"{background}\nfounder {f}", fontsize=8)
    fig.suptitle("Fixed examples: first block, all four founders, recipient 0", fontsize=11)
    fig.tight_layout()
    fig.savefig(output / "fixed_examples.png", dpi=150)
    plt.close(fig)
