"""Small, staged analytical development calculations. No native experiments.

Calibration writes its forecasts before evaluation. The generative toy model is
known to its designer, so this ordering is provenance, not a blinded test.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import time

import numpy as np

import joint_kernel as jk

ROOT = Path(__file__).resolve().parent
STATUS = "DEVELOPMENT_TOY_NOT_CONFIRMATORY"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def forecasts(p, a, factor, output, q, horizons):
    rows = []
    for h in horizons:
        estimated = jk.terminal(p, q, h)
        simple = jk.terminal(factor, q, h)
        pooled = jk.terminal(output, [0, 1], h)
        rows.append(dict(horizon=h,
            joint_model=dict(own=float(estimated[1]), foreign=float(estimated[3]),
                             specificity=float(estimated[1]-estimated[3])),
            generic_four_state=dict(own=float(estimated[1]), foreign=float(estimated[3]),
                                    specificity=float(estimated[1]-estimated[3])),
            independent_two_factor=dict(own=float(simple[1]), foreign=float(simple[3]),
                                        specificity=float(simple[1]-simple[3])),
            output_only=dict(own=float(pooled[1]), foreign=float(pooled[0]),
                             specificity=float(pooled[1]-pooled[0])),
            all_cycle_probability=float(jk.all_cycle(a, h)[1])))
    return rows


def calibrate(config_path, output_path):
    config = json.loads(Path(config_path).read_text())
    random = np.random.default_rng(config["seed"])
    n = config["one_step_samples_per_state"]
    q = np.array([0., 1., 0., 0.])
    result = dict(status=STATUS, created_at_utc=stamp(), config=config,
                  config_sha256=sha(config_path),
                  code_sha256={name: sha(ROOT/name) for name in ("joint_kernel.py", "develop.py")},
                  environment=dict(python=platform.python_version(), numpy=np.__version__),
                  interpretation="Known toy source states and fixed generative law. No native-system claim.", cases=[])
    for case in config["cases"]:
        p = jk.two_factor_kernel(case["identity_flip"], case["readiness_loss"], case["readiness_recovery"])
        counts = np.zeros((4, 2, 4), dtype=np.int64)
        for i in range(4):
            draws = random.multinomial(n, p[i])
            for j in range(4):
                counts[i, int(q[j]), j] = draws[j]
        joint, estimated, passed = jk.fit_joint(counts)
        factor = jk.factor_fit(counts)
        output = jk.output_only_fit(counts, q.astype(int))
        result["cases"].append(dict(name=case["name"], counts=counts.tolist(),
            one_step_observations=int(counts.sum()), known_readout=q.tolist(),
            joint=joint.tolist(), p=estimated.tolist(), pass_matrix=passed.tolist(),
            factor_matrix=factor.tolist(), output_matrix=output.tolist(),
            forecasts=forecasts(estimated, passed, factor, output, q, config["horizons"])))
    write_once(output_path, result)
    print(json.dumps(dict(written=str(output_path), status=STATUS,
                          observations=sum(c["one_step_observations"] for c in result["cases"]))))


def counterexamples():
    q = np.array([0., 1., 0., 0.])
    p = jk.two_factor_kernel(.005, .15, .6)
    reduction = jk.aggregate(p, q, q.astype(int))
    alias_actual = jk.terminal(p, q, 32)
    alias_approx = reduction["membership"] @ jk.terminal(reduction["p"], reduction["q"], 32)
    examples = [dict(id="CE01", name="One attracting prototype erases identity", status="EXACT_CONSTRUCTED",
                     kernel=[[1., 0.], [1., 0.]], terminal_q=[1., 0.],
                     own_and_foreign_terminal=[1., 1.], specificity_after_one=0.),
                dict(id="CE02", name="Perfect record with unusable reader", status="EXACT_CONSTRUCTED",
                     retained_identity_bits=1, terminal_q=[0., 0.], terminal_success=0.),
                dict(id="CE03", name="Current success leaves a failing successor", status="EXACT_CONSTRUCTED",
                     kernel=[[0., 1.], [0., 1.]], q=[1., 0.], current=1., next=0.),
                dict(id="CE04", name="Failed expression precedes recovery", status="EXACT_CONSTRUCTED",
                     kernel=[[0., 1.], [0., 1.]], q=[0., 1.], current=0., next=1.),
                dict(id="CE05", name="Nonnormal transient escapes a safe region", status="EXACT_CONSTRUCTED",
                     matrix=[[.5, 8.], [0., .5]], spectral_radius=.5,
                     initial=[0., .1], after_one=[.8, .05], safe_infinity_radius=.2),
                dict(id="CE06", name="External guide supplies erased founder identity", status="EXACT_CONSTRUCTED",
                     information_F_record_bits=0, information_F_record_and_guide_bits=1,
                     decoder_accuracy_using_guide=1., independent_guide_accuracy=.5),
                dict(id="CE07", name="Mutual copying preserves a defect", status="EXACT_CONSTRUCTED",
                     trajectory=[[1, 0], [0, 1], [1, 0]], declared_goal=[1, 1], goal_reached=False),
                dict(id="CE08", name="Large nuisance memory misses task value", status="EXACT_CONSTRUCTED",
                     nuisance_storage=dict(total_temporal_information_bits=20, task_accuracy=.5),
                     useful_storage=dict(total_temporal_information_bits=1, task_accuracy=1.)),
                dict(id="CE09", name="Current-output aggregation aliases different successors", status="EXACT_CONSTRUCTED",
                     transition_defect=reduction["transition_defect"],
                     readout_defect=reduction["readout_defect"], horizon=32,
                     maximum_terminal_error=float(np.max(np.abs(alias_actual-alias_approx))),
                     conditional_bound=jk.terminal_error_bound(reduction["p"], reduction["q"], 32,
                                                              reduction["transition_defect"], reduction["readout_defect"]))]
    # A passing cycle leaves the state in which the next cycle necessarily fails.
    joint = np.zeros((2, 2, 2))
    joint[0, 0, 0] = .5
    joint[0, 1, 1] = .5
    joint[1, 0, 0] = 1.
    ordinary, passed = jk.joint_operators(joint)
    invalid = passed.sum(axis=1)[:, None] * ordinary
    examples.append(dict(id="CE10", name="Success and successor noise cannot be factorized", status="EXACT_CONSTRUCTED",
                         joint=joint.tolist(), horizon=2,
                         true_all_cycle=float(jk.all_cycle(passed, 2)[0]),
                         marginal_factorization=float(jk.all_cycle(invalid, 2)[0])))
    limit = 4
    good = np.eye(limit+3)
    bad = good.copy()
    for i in range(limit):
        good[i] = 0; good[i, i+1] = 1
        bad[i] = good[i]
    good[limit] = 0; good[limit, limit+1] = 1
    bad[limit] = 0; bad[limit, limit+2] = 1
    endpoint = np.ones(limit+3); endpoint[-1] = 0
    examples.append(dict(id="CE11", name="Identical bounded probe transcripts hide an unvisited failure", status="EXACT_CONSTRUCTED",
                         maximum_probe_depth=limit,
                         short_endpoint_good=[float(jk.terminal(good, endpoint, h)[0]) for h in range(limit+1)],
                         short_endpoint_bad=[float(jk.terminal(bad, endpoint, h)[0]) for h in range(limit+1)],
                         first_divergent_horizon=limit+1,
                         later_good=float(jk.terminal(good, endpoint, limit+1)[0]),
                         later_bad=float(jk.terminal(bad, endpoint, limit+1)[0]),
                         minimax_absolute_error_at_least=.5))
    return examples


def evaluate(calibration_path, output_path):
    started = time.perf_counter()
    frozen = json.loads(Path(calibration_path).read_text())
    for name, expected in frozen["code_sha256"].items():
        if sha(ROOT/name) != expected:
            raise ValueError(f"Code changed after toy calibration: {name}")
    config = frozen["config"]
    result = dict(status=STATUS, created_at_utc=stamp(), calibration_sha256=sha(calibration_path),
                  interpretation="Exact matrix expectations evaluate known constructed toys. Neither native confirmation nor a blinded theory test.",
                  cases=[], counterexamples=counterexamples(), sample_complexity=[])
    for case, fitted in zip(config["cases"], frozen["cases"], strict=True):
        truth = jk.two_factor_kernel(case["identity_flip"], case["readiness_loss"], case["readiness_recovery"])
        q = np.asarray(fitted["known_readout"])
        fitted_p = np.asarray(fitted["p"])
        actual_tv = float(.5 * np.abs(truth-fitted_p).sum(axis=1).max())
        sampling_radius = jk.tv_row_radius(config["one_step_samples_per_state"], 4, 8, config["statistical_radius_delta"])
        rows = []
        formula_error = 0.
        for forecast in fitted["forecasts"]:
            h = forecast["horizon"]
            exact = jk.terminal(truth, q, h)
            for own, state in ((True, 1), (False, 3)):
                formula = jk.two_factor_exact(case["identity_flip"], case["readiness_loss"], case["readiness_recovery"], h, own=own)
                formula_error = max(formula_error, abs(formula-exact[state]))
            oracle_bound = jk.terminal_error_bound(fitted_p, q, h, actual_tv)
            rows.append(dict(**forecast, truth=dict(own=float(exact[1]), foreign=float(exact[3]), specificity=float(exact[1]-exact[3])),
                             oracle_error_bound=oracle_bound,
                             sampling_only_conditional_bound=jk.terminal_error_bound(fitted_p, q, h, sampling_radius)))
        errors = {}
        for name in ("joint_model", "generic_four_state", "independent_two_factor", "output_only"):
            relevant = [r for r in rows if r["horizon"] > 0]
            errors[name] = {key: math.sqrt(sum((r[name][key]-r["truth"][key])**2 for r in relevant)/len(relevant))
                            for key in ("own", "foreign", "specificity")}
        result["cases"].append(dict(name=case["name"], rows=rows, rmse_over_declared_positive_horizons=errors,
                                   analytic_formula_max_error=float(formula_error),
                                   actual_transition_tv_for_toy_audit=actual_tv,
                                   simultaneous_sampling_radius=sampling_radius,
                                   representation_defect=0,
                                   representation_defect_basis="Identity/readiness is the supplied complete toy state, not an empirically validated native reduction."))
    illustration = config["sample_complexity_illustration"]
    logterm = math.log(illustration["rows"] * (2**illustration["joint_categories"]-2) / illustration["delta"])
    for h in [1, 8, 16, 32, 64]:
        eps = (illustration["absolute_error"]-illustration["readout_error"])/h
        n = math.ceil(logterm/(2*eps**2))
        result["sample_complexity"].append(dict(horizon=h, sufficient_one_step_samples_per_row=n,
                                                 sufficient_total_one_step_samples=n*illustration["rows"],
                                                 assumptions="Zero representation defect, known readout, independent fixed-row samples; illustrative worst-case union bound, not a lower bound or native sample-size recommendation."))
    result["elapsed_seconds"] = time.perf_counter()-started
    write_once(output_path, result)
    print(json.dumps(dict(written=str(output_path), cases=len(result["cases"]), counterexamples=len(result["counterexamples"]), status=STATUS)))


def export(calibration_path, result_path, output_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    frozen = json.loads(Path(calibration_path).read_text())
    results = json.loads(Path(result_path).read_text())
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path, png_path, svg_path = (out/name for name in ("forecast_curves.csv", "forecast_curves.png", "forecast_curves.svg"))
    if any(p.exists() for p in (csv_path, png_path, svg_path)):
        raise FileExistsError("Refusing to overwrite figure or table artifacts")
    with csv_path.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case", "horizon", "method", "own", "foreign", "specificity"])
        writer.writeheader()
        for case in results["cases"]:
            for row in case["rows"]:
                for method in ("truth", "joint_model", "generic_four_state", "independent_two_factor", "output_only"):
                    writer.writerow(dict(case=case["name"], horizon=row["horizon"], method=method, **row[method]))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
    colors = ["#116466", "#ad4620"]
    for color, case in zip(colors, results["cases"], strict=True):
        h = [r["horizon"] for r in case["rows"]]
        label = case["name"].replace("_", " ")
        for ax, key in zip(axes, ("own", "specificity"), strict=True):
            ax.plot(h, [r["truth"][key] for r in case["rows"]], color=color, lw=2, label=label+" exact")
            ax.plot(h, [r["joint_model"][key] for r in case["rows"]], color=color, ls="--", marker="o", ms=3, label=label+" estimated")
    axes[0].set_ylabel("Terminal success probability")
    axes[1].set_ylabel("Own minus foreign success probability")
    for ax in axes:
        ax.set_xlabel("Renewal horizon")
        ax.set_ylim(-.03, 1.03)
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("Constructed development examples with known state\n512 one-step probes per state; generic four-state Markov model is identical", fontsize=11)
    fig.savefig(png_path, dpi=160)
    fig.savefig(svg_path)
    plt.close(fig)
    print(json.dumps(dict(csv=str(csv_path), png=str(png_path), svg=str(svg_path), seed=frozen["config"]["seed"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("calibrate"); c.add_argument("--config", type=Path, required=True); c.add_argument("--output", type=Path, required=True)
    e = sub.add_parser("evaluate"); e.add_argument("--calibration", type=Path, required=True); e.add_argument("--output", type=Path, required=True)
    x = sub.add_parser("export"); x.add_argument("--calibration", type=Path, required=True); x.add_argument("--results", type=Path, required=True); x.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "calibrate": calibrate(args.config, args.output)
    elif args.command == "evaluate": evaluate(args.calibration, args.output)
    else: export(args.calibration, args.results, args.output_dir)


if __name__ == "__main__":
    main()
