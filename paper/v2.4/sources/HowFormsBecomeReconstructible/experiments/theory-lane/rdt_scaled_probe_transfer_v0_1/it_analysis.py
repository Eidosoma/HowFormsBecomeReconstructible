"""Descriptive pilot scores using the already qualified balanced-loss reduction."""
import copy
import math
from it_common import C, MODELS, REGIMES, ROOT, read, require
import ff_analysis
import ff_audit


def analyze(rows, forecasts, outcomes, spec):
    expected = {(tuple(r["key"]), n, g, rep) for r in rows
                for n in spec["injuries"] for g in REGIMES for rep in spec["repeats"]}
    actual = {(tuple(y["key"]), y["injury"], y["regime"], y["replicate"]) for y in outcomes}
    require(len(actual) == len(outcomes) and actual == expected, "Incomplete or duplicated outcome panel")
    answer = dict(scope=spec["scope"], interpretation="DESCRIPTIVE_DEVELOPMENT_ONLY",
                  inferential_verdict=None, blocks=len(spec["blocks"]), packets=len(rows),
                  outcomes=len(outcomes), injuries={}, new_model_fits=0)
    audits = {}
    for injury in spec["injuries"]:
        fs = [{k: v for k, v in f.items() if k != "injury"} for f in forecasts if f["injury"] == injury]
        ys = [{k: v for k, v in y.items() if k != "injury"} for y in outcomes if y["injury"] == injury]
        calculated = ff_analysis.analyze(rows, fs, ys, spec)
        audits[str(injury)] = ff_audit.evaluate(rows, fs, ys, calculated, spec["repeats"])
        reduced = copy.deepcopy(calculated)
        reduced.pop("decision")
        reduced["inferential_verdict"] = None
        for regime in REGIMES:
            part = reduced["regimes"][regime]
            part.pop("primary")
            part.pop("secondary")
            for contrast in part["contrasts"].values():
                contrast.pop("decision")
                contrast.pop("margin")
                contrast["interval_status"] = "Descriptive nominal 95% block-t; no decision gate or simultaneous coverage"
            # Explicit degeneracy and mean-probability diagnostics under the same weights.
            group = [f for f in fs if f["regime"] == regime]
            weights = [1 / (len(spec["blocks"]) * 2 * sum(
                r["block"] == f["block"] and r["current_pass"] == f["current_pass"] for r in rows)) for f in group]
            part["prediction_diagnostics"] = {
                model: dict(
                    minimum=min(f["probabilities"][model] for f in group),
                    maximum=max(f["probabilities"][model] for f in group),
                    weighted_mean=math.fsum(w * f["probabilities"][model] for w, f in zip(weights, group, strict=True)),
                    packets_below_005=sum(f["probabilities"][model] < .05 for f in group),
                    packets_above_095=sum(f["probabilities"][model] > .95 for f in group),
                ) for model in MODELS
            }
        answer["injuries"][str(injury)] = reduced
    return answer, dict(status="PASS", independent_scalar_contrasts=16, by_injury=audits,
                        no_confirmatory_gate=True)


def report(result, costs, model_costs):
    lines = [
        f"Injury-transfer {result['scope']}: {result['blocks']} reused/disposable blocks, "
        f"{result['packets']} packets, {result['outcomes']} continuation outcomes.",
        "", "Status: descriptive development evidence; no confirmatory verdict or fitted model.",
        "", "Every model was fixed before the full-panel forecast seal; every future followed that seal.",
        "", "| Injury | Noise | Model | Native reads per forecast | Brier loss | Mean forecast | Observed success |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    reads = dict(successor32=64, direct64=64, pooled32=64, direct8=8, tt008=0)
    for injury, value in result["injuries"].items():
        for regime, part in value["regimes"].items():
            for model in MODELS:
                lines.append(
                    f"| {injury} | {regime} | {model} | {reads[model]} | {part['brier'][model]:.6f} | "
                    f"{part['prediction_diagnostics'][model]['weighted_mean']:.6f} | {part['observed_success']:.6f} |")
    lines += ["", "| Injury | Noise | Rival minus successor32 | Mean Brier gain | Descriptive lower | Descriptive upper |",
              "|---:|---|---|---:|---:|---:|"]
    for injury, value in result["injuries"].items():
        for regime, part in value["regimes"].items():
            for model, contrast in part["contrasts"].items():
                lines.append(f"| {injury} | {regime} | {model} | {contrast['mean_gain']:.6f} | "
                             f"{contrast['lower']:.6f} | {contrast['upper']:.6f} |")
    lines += [
        "", "Losses average individual future losses with equal founder-block and original expression-class weights. "
        "Intervals are descriptive nominal block-t intervals on only eight reused founders in development; "
        "they are not simultaneous intervals or a significance gate.",
        "", "The archived five-model fits are unchanged. The shared assay uses 128 primary plus four flat audit reads "
        "per packet/injury/noise condition. Primary models each require 64 native reads, direct8 requires eight, "
        "and TT008 needs zero additional probe reads. Acquisition and model training are separate costs.",
        "", "| Predictor | Standalone probe CPU seconds, audits excluded | Provenance |",
        "|---|---:|---|",
    ]
    for model in MODELS:
        item = model_costs[model]
        cpu = item.get("cpu_seconds")
        shown = "Not separately timed" if cpu is None else f"{cpu:.3f}"
        lines.append(f"| {model} | {shown} | {item['source']} |")
    lines += [
        "", f"Primary reads: {costs['primary_native_reads']}; flat audit reads: {costs['flat_native_reads']}; "
        f"worker CPU seconds: {costs['worker_cpu_seconds']:.3f}.",
        "", "All acquisition-boundary features remain those of the original 24-cell acquisition. "
        "Only the measured probe fractions and future injury distribution change. The injury levels use "
        "independent streams; the noise regimes are paired within each injury level.",
        "", "A useful transfer result would concern this fixed forecasting reduction. It does not establish "
        "a universal RDT law, endogenous apparatus maintenance, or a repair-benefit scheduler. "
        "Qualification uses disposable synthetic packets and has no scientific inferential interpretation.", "",
    ]
    return "\n".join(lines)
