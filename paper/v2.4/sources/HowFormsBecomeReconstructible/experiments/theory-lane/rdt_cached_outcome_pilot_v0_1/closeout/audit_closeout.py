"""Audit completed frozen evidence; never run dynamics, fit, or change the study.

The existing separate scalar audit checks the primary contrasts. This adds full
file coverage, receipt/forcing checks, and separately implemented weighted
calibration and class diagnostics. All new output is exclusive to closeout/v1.
"""
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import signal
import statistics
import sys
import time

PACKAGE = Path(__file__).resolve().parents[1]
INPUT = PACKAGE / "jobs/pilot_v1/inputs"
RUN = PACKAGE / "runs/pilot_v1"
DEST = PACKAGE / "closeout/v1"
sys.path.insert(0, str(INPUT))

import numpy as np
from bridge import P, e, read, verify_inputs
import audit_pilot
import independent_arithmetic as arithmetic
import ledger
import runner
import verify_science

MODELS = ("tt008", "direct_rival", "candidate")
REGIMES = ("matched", "independent")
NAMES = {"tt008": "TT008 ordinary", "direct_rival": "Direct probe", "candidate": "Successor fixed32"}
MAX_ERROR = 0.0


def require(condition, message):
    if not condition:
        raise ArithmeticError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


def close(actual, expected, name):
    global MAX_ERROR
    require(math.isfinite(actual) and math.isfinite(expected), name + ": nonfinite")
    error = abs(actual - expected)
    MAX_ERROR = max(MAX_ERROR, error)
    require(error <= 1e-12, name + ": numerical discrepancy")


def write(name, value):
    with (DEST / name).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def coverage(root, hashes, omitted=()):
    require(not any(p.is_symlink() for p in root.rglob("*")), "Evidence symlink")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    require(actual == set(hashes) | set(omitted), "Manifest coverage mismatch: " + str(root))
    for name, expected in hashes.items():
        require(sha(ledger.child(root, name)) == expected, "Changed evidence: " + name)
    return len(hashes)


def diagnostics(rows, forecasts, outcomes, result):
    """Use scalar lists, fsum and statistics, independently of scoring_pilot."""
    blocks = sorted({r["block"] for r in rows})
    counts = Counter((r["block"], r["current_pass"]) for r in rows)
    predictions = {(tuple(r["key"]), r["regime"]): r["probabilities"] for r in forecasts}
    labels = {(tuple(r["key"]), r["regime"]): r["passed"] for r in outcomes}
    weights = {tuple(r["key"]): 1 / (2 * counts[r["block"], r["current_pass"]]) for r in rows}
    close(math.fsum(weights.values()), len(blocks), "Total panel weight")
    bins_out, strata_out, totals = [], [], []
    for regime in REGIMES:
        saved = result["regimes"][regime]
        for model in MODELS:
            for block in blocks:
                selected = [r for r in rows if r["block"] == block]
                loss = math.fsum(weights[tuple(r["key"])] * (
                    predictions[tuple(r["key"]), regime][model] - labels[tuple(r["key"]), regime]
                ) ** 2 for r in selected)
                close(loss, saved["score_blocks"][model][blocks.index(block)], "Block Brier")
            for b in range(10):
                group = [r for r in rows if min(math.floor(10 * predictions[tuple(r["key"]), regime][model]), 9) == b]
                weight = math.fsum(weights[tuple(r["key"])] for r in group)
                mean = math.fsum(weights[tuple(r["key"])] * predictions[tuple(r["key"]), regime][model] for r in group) / weight if group else None
                observed = math.fsum(weights[tuple(r["key"])] * labels[tuple(r["key"]), regime] for r in group) / weight if group else None
                item = dict(bin=b, records=len(group), panel_mass=weight / len(blocks), mean_prediction=mean, observed_fraction=observed)
                original = saved["calibration"][model][b]
                require(item.keys() == original.keys(), "Calibration fields differ")
                for field, value in item.items():
                    if value is None or field in ("bin", "records"):
                        require(value == original[field], "Calibration count/empty-bin mismatch")
                    else:
                        close(value, original[field], "Calibration " + field)
                bins_out.append(dict(regime=regime, model=model, **item))
            for current in (0, 1):
                selected = [r for r in rows if r["current_pass"] == current]
                original = saved["current_expression"][str(current)]
                require(original["records"] == len(selected) and original["blocks"] == len(blocks), "Class metadata mismatch")
                score = statistics.mean([
                    statistics.mean((predictions[tuple(r["key"]), regime][model] - labels[tuple(r["key"]), regime]) ** 2
                                    for r in selected if r["block"] == block)
                    for block in blocks])
                close(score, original["scores"][model], "Current-expression Brier")
                strata_out.append(dict(regime=regime, model=model, current_pass=current, records=len(selected), brier=score))
            totals.append(dict(regime=regime, model=model,
                mean_prediction=math.fsum(weights[tuple(r["key"])] * predictions[tuple(r["key"]), regime][model] for r in rows) / len(blocks),
                observed_fraction=math.fsum(weights[tuple(r["key"])] * labels[tuple(r["key"]), regime] for r in rows) / len(blocks)))
        for rival in ("tt008", "direct_rival"):
            contrast = saved["primary"][rival]
            require(contrast["margin"] == P["analysis"]["margins"][rival], "Changed inferential margin")
            for i in range(len(blocks)):
                close(contrast["block_values"][i], saved["score_blocks"][rival][i] - saved["score_blocks"]["candidate"][i], "Saved block contrast")
    return dict(calibration=bins_out, current_expression=strata_out, calibration_totals=totals)


def main():
    start = time.monotonic()
    require(DEST.is_dir(), "Create output directory with CPU admission first")
    admission = read(DEST / "CPU_ADMISSION.json")
    require(admission["within_limit"], "Shared CPU budget unavailable")
    launch = read(PACKAGE / "DECISION.json")
    for name, expected in launch["artifact_sha256"].items():
        require(sha(ledger.child(PACKAGE, name)) == expected, "Launch artifact changed: " + name)
    manifest = read(INPUT / "INPUTS.json")
    input_count = coverage(INPUT, manifest["sha256"], ["INPUTS.json"])
    require(verify_inputs() == input_count, "Input count mismatch")
    qualification = read(INPUT / "QUALIFICATION.json")
    require(qualification["status"] == "PASS", "Qualification missing")
    for name, expected in qualification["source_sha256"].items():
        require(manifest["sha256"][name] == expected, "Qualified source differs")
    complete = read(RUN / "COMPLETE.json")
    require(complete["status"] == "COMPLETE" and read(RUN / "STATUS.json")["status"] == "COMPLETE", "Run incomplete")
    require(sha(RUN / "OUTPUTS.json") == complete["output_manifest_sha256"], "Output manifest binding")
    output_count = coverage(RUN, read(RUN / "OUTPUTS.json")["sha256"], ["OUTPUTS.json", "COMPLETE.json", "STATUS.json"])
    require(input_count == complete["input_files_verified"], "Completion input count")
    source = read(INPUT / "SOURCE_DATA.json")
    for item in source["source_files"].values():
        require(sha(item["path"]) == item["sha256"], "Historical source changed")
    source_run = PACKAGE.parent / P["cohort"]["source"]
    require(sha(source_run / "COMPLETE.json") == source["source_complete_sha256"], "Source completion changed")
    require(sha(source_run / "OUTPUTS.json") == source["source_manifest_sha256"], "Source manifest changed")
    rows, forecasts, _ = runner.check_cache()
    blocks = sorted({r["block"] for r in rows})
    seal = read(RUN / "FORECAST_SEAL.json")
    seal_sha = sha(RUN / "FORECAST_SEAL.json")
    binding = sha(INPUT / "INPUTS.json")
    require(seal["rows"] == rows and seal["forecasts"] == forecasts, "Forecast seal content changed")
    require(seal["input_binding"] == binding and complete["forecast_seal_sha256"] == seal_sha, "Forecast/input binding")
    run_start = read(RUN / "START.json")
    require(run_start["input_manifest_sha256"] == binding and run_start["wall_ceiling_seconds"] == 3600, "Start contract changed")
    seal_time = datetime.fromisoformat(seal["utc"])
    require(datetime.fromisoformat(run_start["utc"]) <= seal_time, "Seal precedes run start")
    references = read(RUN / "FUTURE_REFERENCES.json")
    expected_paths = {f"futures/block_{b:06d}_{regime}" for b in blocks for regime in REGIMES}
    require(len(references) == len(expected_paths) and {r["path"] for r in references} == expected_paths, "Future batch coverage")
    outcomes, paired_raw, chronology = [], {}, []
    native = flat = forcing_count = 0
    for reference in references:
        folder, committed = ledger.referenced(RUN, reference)
        identity = committed["identity"]
        block, regime = identity["block"], identity["regime"]
        selected = [r for r in rows if r["block"] == block]
        expected_identity = dict(binding=binding, block=block, regime=regime, keys=[r["key"] for r in selected], seal_sha256=seal_sha)
        require(identity == expected_identity and reference["path"] == f"futures/block_{block:06d}_{regime}", "Batch identity")
        labels = read(folder / "OUTCOMES.json")
        receipt = read(folder / "future.json")
        require(labels == committed["payload"]["outcomes"], "Committed labels differ")
        audit_key = min(selected, key=lambda r: r["selection_hash"])["key"]
        verification = verify_science.continuation(folder, selected, labels, P["reader"], seal_sha, audit_key)
        require(verification == read(folder / "VERIFICATION.json"), "Batch verification differs")
        require(receipt["stage"] == P["forcing"]["future_stage"], "Future stage changed")
        end_time = datetime.fromisoformat(receipt["utc"])
        inferred_start = end_time - timedelta(seconds=receipt["wall_seconds"])
        # UTC receipts and monotonic durations provide procedural chronology,
        # not trusted external timestamping. Actual code gates on seal existence.
        require(inferred_start >= seal_time and end_time <= datetime.fromisoformat(committed["utc"]), "Future/seal chronology")
        chronology.append((inferred_start - seal_time).total_seconds())
        raw = arithmetic.load(folder / "future.npz")
        require(raw["rules"].tolist() == [r["rule"] for r in selected], "Future rule identity")
        require(np.all(raw["mask"].sum(axis=(-2, -1)) == 24), "Wrong injury count")
        require(not np.any(raw["mask"][..., e.PORTS.any(axis=0)]), "Injury touches protected port")
        require(len(receipt["forcing"]) == 19 * len(selected), "Forcing receipt coverage")
        for g_index, generation in enumerate(range(15, 34)):
            for index, row in enumerate(selected):
                entry = receipt["forcing"][g_index * len(selected) + index]
                require(entry["key"] == row["key"] and entry["generation"] == generation and entry["purpose"] == ("writer" if generation < 33 else "evaluation"), "Forcing identity")
                for field in ("mask", "birth"):
                    require(digest(raw[field][g_index, index]) == entry["sha256"][field], "Retained forcing hash")
                require(len(bytes.fromhex(entry["sha256"]["noise"])) == 32, "Noise hash format")
                forcing_count += 1
        for index, label in enumerate(labels):
            close(label["margin"], float(raw["terminal_aligned"][index].min()), "Terminal margin")
            close(label["margin"], float(raw["terminal_margin"][index]), "Raw terminal margin")
        paired_raw[block, regime] = {n: raw[n] for n in ("mask", "birth", "initial_packets")}
        for field in ("native_reads", "flat_native_reads"):
            require(receipt[field] == committed["payload"][field], "Batch cost mismatch")
        native += receipt["native_reads"]
        flat += receipt["flat_native_reads"]
        outcomes.extend(labels)
    for block in blocks:
        matched, independent = (paired_raw[block, r] for r in REGIMES)
        for field in ("mask", "initial_packets"):
            require(matched[field].tobytes() == independent[field].tobytes(), "Paired regime initial state/injury differs")
        require(matched["birth"][:, :, 0].tobytes() == independent["birth"][:, :, 0].tobytes(), "Shared birth cue differs")
        require(matched["birth"][:, :, 0].tobytes() == matched["birth"][:, :, 1].tobytes(), "Matched birth not copied")
    result = read(RUN / "ANALYSIS.json")
    primary = audit_pilot.evaluate(rows, forecasts, outcomes, result)
    require(primary == read(RUN / "VERIFICATION.json"), "Primary audit receipt differs")
    require(complete["decision"] == result["decision"], "Completion decision differs")
    for field, value in (("records", len(rows)), ("acquisition_blocks", len(blocks)), ("case_regimes", len(outcomes)), ("primary_native_reads", native), ("flat_native_reads", flat)):
        require(complete[field] == value, "Completion count: " + field)
    require(complete["wall_seconds"] <= 3600, "Runtime ceiling exceeded")
    diag = diagnostics(rows, forecasts, outcomes, result)
    costs = read(PACKAGE / "COMPARATOR_COSTS.json")
    cohort = read(PACKAGE / "COHORT_COMPOSITION.json")
    review = read(PACKAGE / "REVIEW_CLOSEOUT_REQUIREMENTS.json")
    for name, expected in review["source_hashes"].items():
        require(sha(PACKAGE / name) == expected, "Review source changed")
    require(cohort["source_rows_sha256"] == sha(INPUT / "cohort/ROWS.json"), "Composition source binding")
    for field, key in (("history_counts", "history"), ("current_expression_counts", "current_pass"), ("rule_counts", "rule")):
        require(cohort[field] == dict(Counter(str(r[key]) for r in rows)), "Composition mismatch: " + field)
    require(cohort["records"] == len(rows) and cohort["acquisition_blocks"] == len(blocks), "Composition totals")
    expected_cost = {"tt008": 0, "direct_rival": 8, "candidate": 64}
    for model in costs["models"]:
        require(model["extra_native_probe_reads"] == expected_cost[model["model"]], "Model probe accounting")
        require(model["retained_panel_reads"] == expected_cost[model["model"]] * len(outcomes), "Panel probe accounting")
    require(costs["new_future_native_reads"] == native and costs["new_future_flat_audit_reads"] == flat, "Future cost accounting")
    require(costs["combined_retained_first_repeat_native_reads"] == 72 * len(outcomes), "Retained measurement cost")
    require(costs["separate_retained_first_repeat_flat_audit_reads"] == 3 * len(outcomes), "Retained audit cost")
    for field in ("new_measurement_reads", "new_acquisition_reads", "new_model_fits"):
        require(complete[field] == 0, "Unexpected new acquisition/measurement/fitting")
    write("DIAGNOSTICS.json", diag)
    with (DEST / "CALIBRATION.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(diag["calibration"][0]))
        writer.writeheader()
        writer.writerows(diag["calibration"])
    summary = dict(utc=datetime.now(timezone.utc).isoformat(), status="PASS",
        implementation_qualification="PASS", selected_panel_predictive_verdict=result["decision"], rdt_specific_support=False,
        frozen_input_files=input_count, output_files=output_count, historical_source_files=len(source["source_files"]),
        cached_forecasts_checked=len(forecasts), continuation_batches=len(references), terminal_outcomes=len(outcomes),
        native_future_reads=native, existing_flat_audit_checks=flat, retained_forcing_receipts_checked=forcing_count,
        scalar_primary_audit=primary, scalar_calibration_bins=60, scalar_class_scores=12,
        maximum_additional_arithmetic_discrepancy=MAX_ERROR,
        minimum_inferred_future_start_after_seal_seconds=min(chronology),
        current_run_wall_seconds=complete["wall_seconds"], closeout_wall_seconds=time.monotonic()-start,
        new_native_reads=0, new_model_fits=0, new_scientific_runs=0,
        input_manifest_sha256=binding, output_manifest_sha256=sha(RUN / "OUTPUTS.json"),
        source_complete_sha256=sha(RUN / "COMPLETE.json"), audit_script_sha256=sha(__file__),
        limitations=["Flat dynamics were checked during the original run; this closeout checks their bound receipts and retained evidence without replaying dynamics.",
            "Ongoing noise is represented by hashes and frozen generator code; the complete noise streams were not regenerated in closeout.",
            "An independently coded arithmetic check in the same research programme is not an independent laboratory replication.",
            "The sample is an inspected selected precision panel. No inference to all acquisition records, no completed 304-block study, no external preregistration."])
    write("VERIFICATION.json", summary)
    # A separately maintained reader report is finalized only after these checks.
    write("AUDITED_RESULTS.json", dict(complete=complete, analysis=result, costs=costs, cohort=cohort))
    print(json.dumps({k: summary[k] for k in ("status", "selected_panel_predictive_verdict", "frozen_input_files", "output_files", "terminal_outcomes", "scalar_calibration_bins", "maximum_additional_arithmetic_discrepancy", "closeout_wall_seconds")}))


if __name__ == "__main__":
    def timed_out(*_):
        raise TimeoutError("Closeout audit exceeded its three-minute ceiling")
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(180)
    try:
        main()
    except BaseException as error:
        if DEST.is_dir() and not (DEST / "FAILED.json").exists():
            write("FAILED.json", dict(utc=datetime.now(timezone.utc).isoformat(), type=type(error).__name__, message=str(error)))
        raise
    finally:
        signal.alarm(0)
