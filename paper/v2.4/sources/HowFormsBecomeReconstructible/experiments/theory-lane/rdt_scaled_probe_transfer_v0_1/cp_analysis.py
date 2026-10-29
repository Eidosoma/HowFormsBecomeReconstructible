"""Paired founder losses for fixed conventional injury forecasts."""
import math
import statistics
import numpy as np
from scipy.stats import t
from it_common import C, REGIMES, require, ROOT, read
from cp_models import NAMES, READS

CANDIDATE = "scale_direct8"
PRIMARY_RIVALS = ("linear_direct8", "quadratic_direct8", "scale_boundary0")
RIVALS = (*PRIMARY_RIVALS, "quadratic_boundary0", "quadratic_condition0", "mean_direct8",
          "expression_direct8", "scale_direct64", "scale_successor64", "expression_successor64")


def contrast(blocks, rival):
    gains = [b["brier"][rival]-b["brier"][CANDIDATE] for b in blocks]
    mean = math.fsum(gains)/len(gains)
    radius = float(t.ppf(.975, len(gains)-1))*statistics.stdev(gains)/math.sqrt(len(gains))
    return dict(rival_minus_candidate=mean, lower=mean-radius, upper=mean+radius,
                block_gains=gains, interval="Nominal95% block-t, descriptive, no simultaneous coverage")


def summarize(blocks):
    count = len(blocks)
    means = {field: {m: math.fsum(b[field][m] for b in blocks)/count for m in NAMES}
             for field in ("brier", "mean_forecast")}
    observed = math.fsum(b["observed"] for b in blocks)/count
    return dict(**means, observed_success=observed,
                calibration_bias={m: means["mean_forecast"][m]-observed for m in NAMES},
                contrasts={r: contrast(blocks, r) for r in RIVALS}, blocks=blocks)


def analyze(rows, forecasts, outcomes, spec):
    require(len({tuple(r["key"]) for r in rows}) == len(rows) and
            sorted({r["block"] for r in rows}) == spec["blocks"], "Complete unique candidate cohort required")
    expected_f = {(tuple(r["key"]), n, g) for r in rows for n in spec["injuries"] for g in REGIMES}
    fmap = {(tuple(f["key"]), f["injury"], f["regime"]): f for f in forecasts}
    require(len(forecasts) == len(fmap) and set(fmap) == expected_f, "Incomplete candidate panel")
    expected_y = {(*k, rep) for k in expected_f for rep in spec["repeats"]}
    ymap = {(tuple(y["key"]), y["injury"], y["regime"], y["replicate"]): y["passed"] for y in outcomes}
    require(len(outcomes) == len(ymap) and set(ymap) == expected_y, "Incomplete candidate outcome panel")
    require(all(y in (0, 1) for y in ymap.values()), "Nonbinary outcome")
    require(all(set(f["probabilities"]) == set(NAMES) and
                all(math.isfinite(p) and 0 <= p <= 1 for p in f["probabilities"].values())
                for f in forecasts), "Invalid candidate probability coverage")
    cell_blocks, scalar_checks = {}, 0
    for injury in spec["injuries"]:
        for regime in REGIMES:
            blocks = []
            for block in spec["blocks"]:
                selected = [r for r in rows if r["block"] == block]
                require({r["current_pass"] for r in selected} == {0, 1}, "Missing expression stratum")
                matrix, labels, weights, classes = [], [], [], []
                for row in selected:
                    class_n = sum(r["current_pass"] == row["current_pass"] for r in selected)
                    f = fmap[(tuple(row["key"]), injury, regime)]
                    require(f["block"] == block and f["current_pass"] == row["current_pass"], "Candidate identity changed")
                    for rep in spec["repeats"]:
                        matrix.append([f["probabilities"][m] for m in NAMES])
                        labels.append(ymap[(tuple(row["key"]), injury, regime, rep)])
                        weights.append(1/(2*class_n*len(spec["repeats"])))
                        classes.append(row["current_pass"])
                p, y, w = np.array(matrix), np.array(labels), np.array(weights)
                require(abs(float(w.sum())-1) < 1e-12, "Weight normalization differs")
                loss, means, observed = w @ (p-y[:, None])**2, w @ p, float(w @ y)
                strata = {}
                for state in (0, 1):
                    keep = np.array(classes) == state
                    sw = 2*w[keep]
                    strata[str(state)] = dict(block=block,
                        brier=dict(zip(NAMES, map(float, sw @ (p[keep]-y[keep, None])**2), strict=True)),
                        mean_forecast=dict(zip(NAMES, map(float, sw @ p[keep]), strict=True)),
                        observed=float(sw @ y[keep]))
                # Independent scalar hierarchy: class -> packet -> individual repeat loss.
                for j, model in enumerate(NAMES):
                    class_loss, class_prob, class_y = [], [], []
                    for state in (0, 1):
                        rs = [r for r in selected if r["current_pass"] == state]
                        ls, ps, ys = [], [], []
                        for r in rs:
                            key = tuple(r["key"])
                            forecast = fmap[(key, injury, regime)]["probabilities"][model]
                            targets = [ymap[(key, injury, regime, rep)] for rep in spec["repeats"]]
                            ls.append(math.fsum((forecast-target)**2 for target in targets)/len(targets))
                            ps.append(forecast)
                            ys.append(math.fsum(targets)/len(targets))
                        class_loss.append(math.fsum(ls)/len(ls))
                        class_prob.append(math.fsum(ps)/len(ps))
                        class_y.append(math.fsum(ys)/len(ys))
                        independent = strata[str(state)]
                        require(max(abs(independent["brier"][model]-class_loss[-1]),
                                    abs(independent["mean_forecast"][model]-class_prob[-1]),
                                    abs(independent["observed"]-class_y[-1])) < 1e-12,
                                "Independent expression-stratum scores differ")
                    require(max(abs(loss[j]-math.fsum(class_loss)/2),
                                abs(means[j]-math.fsum(class_prob)/2),
                                abs(observed-math.fsum(class_y)/2)) < 1e-12, "Independent candidate scores differ")
                    scalar_checks += 1
                blocks.append(dict(block=block, brier=dict(zip(NAMES, map(float, loss), strict=True)),
                                   mean_forecast=dict(zip(NAMES, map(float, means), strict=True)),
                                   observed=observed, expression_strata=strata))
            cell_blocks[(injury, regime)] = blocks
    cells = {str(n): {g: summarize(cell_blocks[(n, g)]) for g in REGIMES} for n in spec["injuries"]}
    for n in spec["injuries"]:
        for g in REGIMES:
            cells[str(n)][g]["expression_strata"] = {
                str(s): summarize([b["expression_strata"][str(s)] for b in cell_blocks[(n, g)]])
                for s in (0, 1)}
    pooled, primary = {}, {}
    for regime in REGIMES:
        blocks = []
        for i, block in enumerate(spec["blocks"]):
            same = [cell_blocks[(n, regime)][i] for n in spec["injuries"]]
            require(all(b["block"] == block for b in same), "Pooled founder pairing differs")
            blocks.append(dict(block=block,
                **{field: {m: math.fsum(b[field][m] for b in same)/len(same) for m in NAMES}
                   for field in ("brier", "mean_forecast")},
                observed=math.fsum(b["observed"] for b in same)/len(same)))
        pooled[regime] = summarize(blocks)
        for rival in PRIMARY_RIVALS:
            value = pooled[regime]["contrasts"][rival]
            primary[f"{regime}:{rival}"] = dict(**value,
                fixed_panel_direction=("NOT_SCIENTIFIC_QUALIFICATION" if spec["scope"] == "qualification" else
                    "POSITIVE" if value["rival_minus_candidate"] > 0 else "DIRECTIONAL_PREDICTION_CONTRADICTED"),
                population_inference="Unresolved by this development screen")
    result = dict(scope=spec["scope"], blocks=len(spec["blocks"]), packets=len(rows), outcomes=len(outcomes),
                  models=list(NAMES), injuries=cells, pooled_by_noise=pooled, primary=primary,
                  candidate=CANDIDATE, new_model_fits=0,
                  inferential_verdict=None, fixed_panel_all_directions_positive=(
                      all(x["rival_minus_candidate"] > 0 for x in primary.values())
                      if spec["scope"] == "development" else None))
    return result, dict(status="PASS", scalar_block_model_checks=scalar_checks,
                        exact_forecast_and_outcome_coverage=True, new_model_fits=0,
                        independent_expression_stratum_checks=2*scalar_checks,
                        calibration_models_sha256=C["calibration_models_sha256"],
                        candidate_models_sha256=C["candidate_models_sha256"])


def report(result, incurred, model_costs):
    lines = [f"Fixed scaling transfer {result['scope']}: {result['blocks']} blocks, "
             f"{result['packets']} packets, {result['outcomes']} outcomes.", "",
             "All27 forecasts are fixed: ten ordinary base models, twelve saved corrections, and five archived models. "
             "Base and correction fits use founders0..7 at injuries12/24/36. Target founders16..23 at injuries18/30 "
             "are excluded from fitting, but their24-cell outcomes were exposed. scale_direct8 was selected after "
             "the previous exposed calibration screen; this is an outcome-informed development test. "
             "Qualification uses disposable synthetic packets with no scientific interpretation.", "",
             "Primary prediction: scale_direct8 improves Brier loss over linear_direct8, quadratic_direct8 and scale_boundary0 "
             "in both noise regimes, pooling the two injuries equally: six comparisons. A nonpositive observed gain contradicts this "
             "fixed-panel prediction. No confirmatory population verdict, equivalence test, RDT-specific claim or repair policy.", "",
             "| Injury | Noise | Model | Probe reads | Brier | Mean forecast | Observed success |",
             "|---:|---|---|---:|---:|---:|---:|"]
    for injury, regimes in result["injuries"].items():
        for regime, cell in regimes.items():
            for model in NAMES:
                lines.append(f"| {injury} | {regime} | {model} | {READS[model.split('_', 1)[1]]} | "
                    f"{cell['brier'][model]:.6f} | {cell['mean_forecast'][model]:.6f} | {cell['observed_success']:.6f} |")
    lines += ["", "| Noise, pooled injuries | Rival minus scale_direct8 | Brier gain | Nominal lower | Nominal upper |",
              "|---|---|---:|---:|---:|"]
    for regime, cell in result["pooled_by_noise"].items():
        for rival, value in cell["contrasts"].items():
            lines.append(f"| {regime} | {rival} | {value['rival_minus_candidate']:.6f} | "
                         f"{value['lower']:.6f} | {value['upper']:.6f} |")
    lines += ["", "Positive gain favors the fixed eight-read scaling candidate. Intervals use founder blocks as the unit, "
              "are nominal95% block-t and descriptive; they have no simultaneous guarantee. Individual future losses "
              "are averaged with equal founder, injury and original-expression-class weights. All original pass/fail "
              "stratum scores and paired block losses are saved, including for the archived five models.", "",
              "All non-condition models receive identical B11 information, including signed/unsigned transfer. "
              "Native probe costs exclude shared boundary acquisition and feature computation. direct8 uses8 reads; "
              "direct64 and successor64 each use64 (successor is32 writer/successor pairs). "
              "The experiment itself uses128 primary plus4 independent flat audit reads per packet/injury/noise case.", "",
              "| Probe family | CPU seconds, standalone audits excluded | Provenance |", "|---|---:|---|"]
    for family, archived in (("direct8", "direct8"), ("direct64", "direct64"), ("successor64", "successor32")):
        value = model_costs[archived]
        shown = "Unmeasured" if value["cpu_seconds"] is None else f"{value['cpu_seconds']:.3f}"
        lines.append(f"| {family} | {shown} | {value['source']} |")
    training = read(ROOT / "context/TRAINING_AUDIT.json")
    correction = read(ROOT / "context/CALIBRATION_ACCOUNTING.json")
    lines += ["", f"Ten pre-run coefficient fits: {training['cpu_seconds']:.3f} CPU seconds including "
              "source verification and numeric audits. These reuse previously charged training simulations. "
              f"The earlier calibration screen added44 scientific fits using {correction['fitting_cpu_seconds']:.3f} fitting CPU seconds; "
              "no optimization is performed in this run. First complete-panel inference for22 base/correction models uses "
              f"{incurred['candidate_first_seal_cpu_seconds']:.3f} CPU seconds, separate from probes and repeat verification. "
              "The new run performs zero fitting or acquisition; primary reads "
              f"{incurred['primary_native_reads']}, flat audit reads {incurred['flat_native_reads']}, "
              f"worker CPU seconds {incurred['worker_cpu_seconds']:.3f}.", ""]
    return "\n".join(lines)
