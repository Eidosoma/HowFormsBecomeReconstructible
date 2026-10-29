"""Generated report and figures for the contract-bridge capsule."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .artifacts import atomic_json, atomic_text, environment_manifest
from .config import BridgeConfig, results_root
from .pipeline import finalize_results


def _save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _contract_figure(atlas: pd.DataFrame, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(6, 5))
    floor = 1e-6
    x = np.maximum(atlas["p_equal_exact"].to_numpy(), floor)
    y = np.maximum(atlas["p_binomial"].to_numpy(), floor)
    axis.loglog(x, y, ".", markersize=2, alpha=0.25)
    limits = [floor, max(float(x.max()), float(y.max())) * 1.5]
    axis.loglog(limits, limits, "k--", linewidth=1)
    axis.set_xlabel("equal-fission strict probability (exact)")
    axis.set_ylabel("binomial-fission strict probability")
    axis.set_title("Strict event across fission contracts")
    _save_figure(figure, path)


def _recalibration_figure(atlas: pd.DataFrame, frozen: dict, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(6, 5))
    x = atlas["p_equal_exact"].to_numpy()
    y = atlas["p_binomial"].to_numpy()
    axis.plot(x, y, ".", markersize=2, alpha=0.2, label="cells")
    grid = np.linspace(0.0, max(float(x.max()), 1e-6), 200)
    for kind, payload in frozen["recalibration_maps"].items():
        fitted = np.interp(grid, payload["knots_x"], payload["knots_y"])
        axis.plot(grid, fitted, linewidth=2, label=f"{kind} map (dev-fitted)")
    axis.set_xlabel("equal-fission strict probability")
    axis.set_ylabel("binomial-fission strict probability")
    axis.legend()
    axis.set_title("Frozen monotone recalibration")
    _save_figure(figure, path)


def _ladder_figure(ladder: pd.DataFrame, path: Path) -> None:
    eval_rows = ladder[ladder["half"] == "eval"]
    medians = eval_rows.groupby(["rung", "map"])["composite"].median().reset_index()
    rungs = list(dict.fromkeys(medians["rung"]))
    maps = list(dict.fromkeys(medians["map"]))
    figure, axis = plt.subplots(figsize=(8, 5))
    width = 0.8 / max(len(maps), 1)
    for index, map_name in enumerate(maps):
        values = [
            float(
                medians[(medians["rung"] == rung) & (medians["map"] == map_name)][
                    "composite"
                ].median()
            )
            if not medians[(medians["rung"] == rung) & (medians["map"] == map_name)].empty
            else np.nan
            for rung in rungs
        ]
        axis.bar(
            np.arange(len(rungs)) + index * width,
            values,
            width=width,
            label=map_name,
        )
    axis.set_xticks(np.arange(len(rungs)) + 0.4 - width / 2)
    axis.set_xticklabels(rungs, rotation=20, ha="right")
    axis.set_ylabel("median scaled composite (eval half, lower is better)")
    axis.set_title("Translator ladder under the symmetric scorer")
    axis.legend()
    _save_figure(figure, path)


def _frontier_figure(frontier: pd.DataFrame, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(6, 5))
    raw = frontier[frontier["variant"] == "raw"]
    for family, marker in (("epsilon", "o"), ("rank", "s")):
        rows = raw[raw["family"] == family]
        axis.scatter(
            rows["compression"].to_numpy(),
            rows["cross_contract_ari"].to_numpy(),
            marker=marker,
            alpha=0.7,
            label=family,
        )
    axis.set_xlabel("compression")
    axis.set_ylabel("cross-contract adjusted Rand")
    axis.set_title("Quotient families: compression vs contract stability")
    axis.legend()
    _save_figure(figure, path)


def _reliability_figure(reliability: pd.DataFrame, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(6, 5))
    budgets = reliability["budget"].to_numpy()
    axis.plot(
        budgets,
        reliability["split_half_spearman_mean"].to_numpy(),
        "o-",
        label="split-half (cell level)",
    )
    axis.fill_between(
        budgets,
        reliability["split_half_spearman_lo"].to_numpy(),
        reliability["split_half_spearman_hi"].to_numpy(),
        alpha=0.2,
    )
    axis.plot(
        budgets,
        reliability["spearman_vs_truth_mean"].to_numpy(),
        "s-",
        label="vs exact truth",
    )
    axis.set_xscale("log", base=2)
    axis.set_xlabel("futures per cell")
    axis.set_ylabel("Spearman reliability")
    axis.set_title("Estimator rank reliability vs futures budget")
    axis.legend()
    _save_figure(figure, path)


def generate_report(config: BridgeConfig) -> dict:
    results = results_root(config)
    required = {
        "atlas": results / "binomial_strict_atlas.csv",
        "summary": results / "contract_shift_summary.json",
        "frozen": results / "frozen_components.json",
        "ladder": results / "translator_ladder.csv",
        "translator_summary": results / "translator_summary.json",
        "frontier": results / "ordinal_frontier.csv",
        "reliability": results / "estimator_rank_reliability.csv",
        "metrics": results / "METRICS.json",
        "feasibility": results / "strict_feasibility.json",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing analysis artifacts: {missing}")

    atlas = pd.read_csv(required["atlas"])
    summary = json.loads(required["summary"].read_text())
    frozen = json.loads(required["frozen"].read_text())
    ladder = pd.read_csv(required["ladder"])
    translator_summary = json.loads(required["translator_summary"].read_text())
    frontier = pd.read_csv(required["frontier"])
    reliability = pd.read_csv(required["reliability"])
    metrics = json.loads(required["metrics"].read_text())
    feasibility = json.loads(required["feasibility"].read_text())

    figures = {
        "contract_scatter": results / "figures" / "contract_scatter.png",
        "recalibration": results / "figures" / "recalibration_map.png",
        "ladder": results / "figures" / "translator_ladder.png",
        "frontier": results / "figures" / "ordinal_frontier.png",
        "reliability": results / "figures" / "estimator_reliability.png",
    }
    _contract_figure(atlas, figures["contract_scatter"])
    _recalibration_figure(atlas, frozen, figures["recalibration"])
    _ladder_figure(ladder, figures["ladder"])
    _frontier_figure(frontier, figures["frontier"])
    _reliability_figure(reliability, figures["reliability"])

    sealed = summary["sealed_e1b_check"]
    part_b_eval = [row for row in metrics["part_b_eval"]]
    part_b_lines = "\n".join(
        f"- `{row['kind']}` map, eval half: removable fraction (median) "
        f"**{row['removable_fraction_median']:.3f}**, (rms) "
        f"**{row['removable_fraction_rms']:.3f}**; Spearman before/after "
        f"{row['spearman_before']:.3f}/{row['spearman_after']:.3f}"
        for row in part_b_eval
    )
    checks = metrics["part_c_checks"]
    recommended = metrics["part_d_recommended_quotient_eval"]
    reliability_rows = "\n".join(
        f"| {int(row.budget)} | {row.split_half_spearman_mean:.3f} | "
        f"{row.spearman_vs_truth_mean:.3f} |"
        for row in reliability.itertuples(index=False)
    )

    report = f"""# Contract bridge (EIDOSOMA-1.5)

## Status and evidential boundary

This is an **exploratory** capsule. It converts design lessons from the
completed Experiment 1 binomial-fission diagnostic into validated, frozen
components for a future sealed replication. Nothing here is a confirmatory
scientific claim, nothing touches the sealed Plato round, and every result
must be replicated under seal before publication.

- Capsule config digest: `{config.digest()}`
- Truth source for binomial strict values: `{summary['truth_source']}`
- Exact binomial automaton feasible: **{feasibility['exact_binomial_feasible']}**
  (census lower bound {feasibility['binomial']['post_states_lower_bound']:,} post states,
  complete={feasibility['binomial']['complete']})

## A. Two-contract strict atlas

{summary['n_cells']:,} cells ({summary['n_rule_orbits']:,} rule orbits x
{len(atlas['state_id'].unique())} launch states), equal contract exact,
binomial contract {summary['truth_source']} at {summary['mc_futures']:,} futures.

- Weighted mean strict probability: equal **{summary['weighted_mean_equal']:.5f}**,
  binomial **{summary['weighted_mean_binomial']:.5f}**
- Contract rank correlation: cell-level Spearman **{summary['cell_spearman']:.4f}**,
  rule-level Spearman **{summary['rule_spearman']:.4f}**
- Fraction of cells with binomial above equal: raw **{summary['sign_flip_fraction_raw']:.4f}**,
  beyond two MC standard errors **{summary['sign_flip_fraction_significant']:.4f}**
- Diagonal-architecture Spearman with rule-level mean strict:
  equal **{summary['architecture']['diag_spearman_equal']:.3f}**,
  binomial **{summary['architecture']['diag_spearman_binomial']:.3f}**
- Sealed E1B cross-check: status `{sealed['status']}`, cells {sealed.get('cells_compared', 'n/a')},
  Wilson coverage {sealed.get('coverage_fraction', 'n/a')}, Spearman vs sealed
  {sealed.get('spearman_vs_sealed', 'n/a')}
- Same-sampler equal-contract check: max |z| {summary['sampler_equal_check']['max_z']:.2f}
  over {summary['sampler_equal_check']['cells']} cells
- Truncated forward-DP check: {sum(1 for e in summary['truncated_forward_check']['entries'] if e['status'] == 'compared')}
  compared / {len(summary['truncated_forward_check']['entries'])} attempted

## B. Gauge-removable fraction

Monotone maps fitted on the development half only, frozen, evaluated on the
untouched half:

{part_b_lines}

Positive control: the catalytic clock gauge changed absorption probabilities
by at most `{json.loads((results / 'recalibration_controls.json').read_text())['gauge_max_absorption_error']:.3g}`
(exactly removable, as predicted).

## C. Symmetric translator ladder

All maps scored by one block registry ({', '.join(frozen['block_names'])}),
robust-scaled by dev-fitted constants. Corrections to the five audited
EIDOSOMA-2 deviations are structural: one frozen regularization
({config.sinkhorn_regularization}), scaling applied to every block for every
map, identical block sets, independent baselines, occupancy-matched null.

- Exact-relabel rung, exact map, worst composite: `{checks['exact_relabel_max_composite']:.3g}`
- Clock-gauge rung, identity map: event blocks at most
  `{checks['clock_gauge_identity_event_blocks_max']:.3g}`, physical-time block at least
  `{checks['clock_gauge_identity_time_block_min']:.3g}` (the observer split, as predicted)
- Full per-rung medians are in `translator_summary.json`; the
  non-isomorphic outlook rung is descriptive only.

## D. Ordinal observer frontier

Rank-quantile partitions vs epsilon quantizers over the same cells
(`ordinal_frontier.csv`). Dev-half recommended quotient, re-evaluated on the
untouched half: family `{recommended['family']}`, resolution
{recommended['resolution']}, offset {recommended['offset']} ->
compression **{recommended['compression']:.4f}**, cross-contract ARI
**{recommended['cross_contract_ari']:.4f}**.

## E. Estimator calibration

Observed MC split-half Spearman at {summary['mc_futures']:,} futures:
**{metrics['part_e_observed_split_half']:.4f}**.

| futures | split-half Spearman | vs exact truth |
| ---: | ---: | ---: |
{reliability_rows}

Gate operating characteristics are in `estimator_gate_oc.csv`.

## Figures

- `figures/contract_scatter.png`
- `figures/recalibration_map.png`
- `figures/translator_ladder.png`
- `figures/ordinal_frontier.png`
- `figures/estimator_reliability.png`

## Limitations

The full-universe exact binomial automaton is infeasible (measured by the
census above), so full-mode binomial values are Monte Carlo at
{summary['mc_futures']:,} futures with exact cross-checks; the mini fixture
runs the exact-DP path end to end. The rule family remains tiny and
artificial; none of this bears on the Ruliad, Platonic ingression, or the
unrun Plato round.
"""
    atomic_text(results / "REPORT.md", report)
    manifest = {
        "config_digest": config.digest(),
        "exploratory": True,
        "environment": environment_manifest(),
        "figures": sorted(str(path.relative_to(results)) for path in figures.values()),
    }
    atomic_json(results / "report_manifest.json", manifest)
    finalize_results(config)
    return manifest
