"""Fixed recovery contrasts, original-expression strata and paired noise interaction."""
import math
import statistics
import numpy as np
from scipy.stats import t
from it_common import C, REGIMES, require, ROOT, read
from cp_models import NAMES, READS

CANDIDATE = "quadratic_successor64"
PRIMARY_RIVALS = tuple(h+"_direct64" for h in ("linear", "quadratic", "mean", "scale", "expression"))
INTERACTION = "matched_minus_independent:quadratic_direct64"
RIVALS = tuple(m for m in NAMES if m != CANDIDATE)


def paired_summary(gains):
    require(len(gains) >= 2 and all(math.isfinite(g) for g in gains), "Finite founder gains required")
    mean = math.fsum(gains)/len(gains)
    radius = float(t.ppf(.975, len(gains)-1))*statistics.stdev(gains)/math.sqrt(len(gains))
    return dict(rival_minus_candidate=mean, lower=mean-radius, upper=mean+radius,
                block_gains=gains,
                leave_one_founder_out=[(math.fsum(gains)-g)/(len(gains)-1) for g in gains],
                interval="Nominal95% block-t, descriptive, no simultaneous coverage")


def contrast(blocks, rival):
    return paired_summary([b["brier"][rival]-b["brier"][CANDIDATE] for b in blocks])


def primary_contrasts(cells, spec):
    require(spec["injuries"] == [18], "Recovery prediction requires the complete injury18 panel")
    matched = cells["18"]["matched"]["expression_strata"]["0"]
    independent = cells["18"]["independent"]["expression_strata"]["0"]
    require([b["block"] for b in matched["blocks"]] == [b["block"] for b in independent["blocks"]] == spec["blocks"],
            "Primary noise contrast must pair the same founders")
    values = {"matched:"+r: dict(matched["contrasts"][r], kind="matched_recovery", rival=r,
                                 candidate=CANDIDATE) for r in PRIMARY_RIVALS}
    mg = matched["contrasts"]["quadratic_direct64"]["block_gains"]
    ig = independent["contrasts"]["quadratic_direct64"]["block_gains"]
    values[INTERACTION] = dict(paired_summary([a-b for a,b in zip(mg, ig, strict=True)]),
        kind="paired_noise_interaction", rival="quadratic_direct64", candidate=CANDIDATE,
        interpretation="Matched minus independent gain; the difference of paired founder gains, not separate interval endpoints",
        matched_block_gains=mg, independent_block_gains=ig)
    return {name: dict(value, injury=18, original_expression_class=0, blocks=spec["blocks"],
        fixed_panel_direction=("NOT_SCIENTIFIC_QUALIFICATION" if spec["scope"] == "qualification" else
                               "POSITIVE" if value["rival_minus_candidate"] > 0 else "DIRECTIONAL_PREDICTION_CONTRADICTED"),
        population_inference="Unresolved by this development screen") for name,value in values.items()}


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
    pooled = {}
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
    primary = primary_contrasts(cells, spec)
    result = dict(scope=spec["scope"], blocks=len(spec["blocks"]), packets=len(rows), outcomes=len(outcomes),
                  models=list(NAMES), injuries=cells, pooled_by_noise=pooled, primary=primary,
                  candidate=CANDIDATE, new_model_fits=0, primary_injury=18, primary_original_expression_class=0,
                  inferential_verdict=None, fixed_panel_all_directions_positive=(
                      all(x["rival_minus_candidate"] > 0 for x in primary.values())
                      if spec["scope"] == "development" else None))
    return result, dict(status="PASS", scalar_block_model_checks=scalar_checks,
                        exact_forecast_and_outcome_coverage=True, new_model_fits=0,
                        independent_expression_stratum_checks=2*scalar_checks,
                        calibration_models_sha256=C["calibration_models_sha256"],
                        candidate_models_sha256=C["candidate_models_sha256"])


def report(result, incurred, model_costs):
    lines = [f"Fixed matched-recovery {result['scope']}: {result['blocks']} blocks, "
             f"{result['packets']} packets, {result['outcomes']} outcomes.", "",
             "All27 forecasts are fixed: ten ordinary base models, twelve saved corrections, and five archived models. "
             "Base and correction fits use founders0..7 at injuries12/24/36. Target founders24..31 at injury18 "
             "are excluded from fitting, but their24-cell outcomes were exposed. The hypothesis was selected after "
             "the recovery signal in exposed founders8..23; this is an outcome-informed development test. "
             "Qualification uses disposable synthetic packets with no scientific interpretation.", "",
             "The six comparisons are five matched-noise direct64-versus-quadratic_successor64 gains, plus "
             "the matched-minus-independent difference in its advantage over quadratic_direct64. "
             "All six concern original-fail injury18 and must be strictly positive. A nonpositive direction "
             "contradicts the fixed-panel joint prediction. Eight-founder population benefit remains unresolved.", "",
             "| Primary contrast, original-fail injury18 | Gain | Nominal lower | Nominal upper | Direction |",
             "|---|---:|---:|---:|---|"]
    for name, value in result["primary"].items():
        lines.append(f"| {name} | {value['rival_minus_candidate']:.6f} | {value['lower']:.6f} | "
                     f"{value['upper']:.6f} | {value['fixed_panel_direction']} |")
    lines += ["", "Positive gains favor the fixed successor predictor; the interaction is positive when its "
              "advantage is larger under matched noise. Noise interaction pairs the same founder blocks. "
              "Intervals are nominal95% block-t, descriptive, with no simultaneous guarantee. Every founder gain "
              "and leave-one-founder-out estimate is saved. All original pass/fail strata and balanced totals are retained.", "",
              "| Noise | Original class | Model | Extra native probe reads | Brier | Mean forecast | Observed |",
              "|---|---|---|---:|---:|---:|---:|"]
    for regime, cell in result["injuries"]["18"].items():
        for state, group in [("balanced", cell), *cell["expression_strata"].items()]:
            for model in NAMES:
                reads = READS[model.split("_", 1)[1]]
                lines.append(f"| {regime} | {state} | {model} | {reads} | {group['brier'][model]:.6f} | "
                             f"{group['mean_forecast'][model]:.6f} | {group['observed_success']:.6f} |")
    lines += ["", "All non-condition models receive the same B11 including signed/unsigned transfer. "
              "direct8 costs8 native reads; direct64 and successor64 each cost64, with32 writer/successor pairs "
              "in the latter. Boundary-only requires zero additional probes; shared boundary and training costs "
              "remain separate. This comparison incurs128 primary plus4 flat audit reads per packet/noise case.", "",
              "| Probe family | Standalone CPU seconds, audits excluded | Provenance |", "|---|---:|---|"]
    for family, archived in (("direct8", "direct8"), ("direct64", "direct64"), ("successor64", "successor32")):
        value = model_costs[archived]
        shown = "Unmeasured" if value["cpu_seconds"] is None else f"{value['cpu_seconds']:.3f}"
        lines.append(f"| {family} | {shown} | {value['source']} |")
    training = read(ROOT / "context/TRAINING_AUDIT.json")
    correction = read(ROOT / "context/CALIBRATION_ACCOUNTING.json")
    lines += ["", f"Ten earlier base-model fits consumed {training['cpu_seconds']:.3f} CPU seconds including "
              "source checks and numerical audits. The earlier calibration study performed44 scientific fits, "
              f"using {correction['fitting_cpu_seconds']:.3f} fitting CPU seconds. Both reused previously charged "
              "training simulations. This run performs zero fitting and zero acquisition. First full-panel inference "
              f"for22 ordinary/corrected models took {incurred['candidate_first_seal_cpu_seconds']:.3f} CPU seconds. "
              f"New primary reads {incurred['primary_native_reads']}; flat audit reads {incurred['flat_native_reads']}; "
              f"worker CPU seconds {incurred['worker_cpu_seconds']:.3f}.", "",
              "This is a restricted conventional forecasting prediction, with no RDT-specific or causal repair-benefit claim. "
              "Scheduling work requires paired repair-versus-no-repair benefit and action costs. Earlier failed studies remain failed.", ""]
    return "\n".join(lines)
