"""Write the complete, reviewed closeout from checked artifacts only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "v1"
PACKAGE = HERE.parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


verification = read(OUT / "VERIFICATION.json")
assert verification["status"] == "PASS"
assert sha(HERE / "audit_closeout.py") == verification["audit_script_sha256"]
assert sha(PACKAGE / "runs/pilot_v1/OUTPUTS.json") == verification["output_manifest_sha256"]
data = read(OUT / "AUDITED_RESULTS.json")
result, complete, costs, cohort = (data[k] for k in ("analysis", "complete", "costs", "cohort"))
diagnostics = read(OUT / "DIAGNOSTICS.json")
assert result["decision"] == verification["selected_panel_predictive_verdict"] == "PILOT_UNRESOLVED"
models = ("tt008", "direct_rival", "candidate")
names = {"tt008": "TT008 ordinary", "direct_rival": "Direct probe", "candidate": "Successor fixed32"}
extra = {r["model"]: r["extra_native_probe_reads"] for r in costs["models"]}

lines = [
    "**Successor-prediction pilot: verified closeout, 17 October 2026.**",
    "",
    "The bounded cached-panel pilot is complete and its evidence audit passes. Its scientific verdict is **PILOT_UNRESOLVED**: all four predeclared successor-prediction advantages remain unresolved. The successor model has the lowest point Brier score in both noise regimes, but every contrast interval includes zero and its required margin. This result does not qualify its additional measurement cost, and does not establish an RDT-specific predictive mechanism.",
    "",
    f"The run completed on 16 October in {complete['wall_seconds']:.2f} seconds (18 minutes 23 seconds), using {complete['cpu_seconds']:.2f} CPU seconds and a peak resident footprint of {complete['peak_resident_bytes'] / 1e6:.1f} MB. It stayed within its one-hour cap. This closeout added {verification['closeout_wall_seconds']:.2f} seconds of audit work and no native dynamics, fitted models or scientific runs.",
    "",
    "Brier score is mean squared probability error; lower is better. All models receive the same eleven boundary features, including current expression, history and signed/unsigned transfer. Additional native probe-read counts below are per record and noise regime, beyond those shared measurements.",
    "",
    "| Predictor | Matched-noise Brier | Independent-noise Brier | Extra native probe reads |",
    "|---|---:|---:|---:|",
]
for model in models:
    lines.append(f"| {names[model]} | {result['regimes']['matched']['scores'][model]:.8f} | {result['regimes']['independent']['scores'][model]:.8f} | {extra[model]} |")
lines += [
    "",
    "The direct model measures eight fresh reads of the protected original packet. The successor model measures 32 writer reads and 32 fresh successor reads. All three are fixed logistic predictors: TT008 has eleven standardized features plus an intercept; the others each add one probe-success feature. No coefficients, probability calibration, probe budget or first-repeat choice were changed using these continuation outcomes.",
    "",
    "All predeclared paired comparisons follow. Gain is comparator Brier minus successor Brier, averaged across the sixteen acquisition blocks with the frozen weighting. Each component interval is mean ± t(.975, 15) × block SD / √16. Lower limit above the required margin supports that advantage; upper limit at or below it rejects it; otherwise it remains unresolved. All four must support the joint claim. The component intervals are not simultaneous intervals.",
    "",
    "| Noise | Comparator | Mean gain | Lower limit | Upper limit | Required margin | Decision |",
    "|---|---|---:|---:|---:|---:|---|",
]
for regime in ("matched", "independent"):
    for rival in ("tt008", "direct_rival"):
        item = result["regimes"][regime]["primary"][rival]
        lines.append(f"| {regime} | {names[rival]} | {item['mean_gain']:.8f} | {item['lower']:.8f} | {item['upper']:.8f} | {item['margin']:.3f} | {item['decision']} |")
lines += [
    "",
    "The estimand is the previously selected precision panel: 63 boundary records in sixteen acquisition blocks, each evaluated under both noise regimes. Every block receives equal weight, and its current-fail and current-pass classes each receive half its weight. There are 31 currently failing and 32 currently passing records; block 1 contributes one failing record, while all other block/class cells contribute two. This is not an estimate for the full 64-record acquisition population.",
    "",
    "Each future starts at the saved generation-14 packet, undergoes eighteen full original-writer rewrites, and is evaluated in one fresh terminal recipient reading the generation-32 packet. Every read has 24 non-port injuries, the full 2,048 integration steps and the last 32-frame task means. All four task-aligned means must strictly exceed 0.25. Earlier failure does not stop a lineage. The endpoint is terminal reconstruction, not uninterrupted success or endogenous apparatus maintenance.",
    "",
    "Matched and independent regimes share base injury and random draws; matched forcing copies the first cue's birth/noise draws to the second cue, while independent forcing retains both. Each regime propagates its own outgoing packets. All 126 forecasts were sealed before the first future. The snapshot and procedural timing establish provenance within this programme, not external preregistration.",
    "",
    "Current-expression diagnostics use equal block weighting within each class. They are descriptive checks and do not replace the four primary comparisons.",
    "",
    "| Noise | Current expression | Records | TT008 ordinary | Direct probe | Successor fixed32 |",
    "|---|---|---:|---:|---:|---:|",
]
for regime in ("matched", "independent"):
    for current in (0, 1):
        item = result["regimes"][regime]["current_expression"][str(current)]
        values = " | ".join(f"{item['scores'][m]:.8f}" for m in models)
        lines.append(f"| {regime} | {'pass' if current else 'fail'} | {item['records']} | {values} |")
lines += [
    "",
    "The selected history composition is given below. Rule signs are −1 for 32 records and +1 for 31. History counts describe enrollment; no history-specific success claim or favorable-subgroup rescue is made.",
    "",
    "| Acquisition history | Selected records |",
    "|---|---:|",
]
for history, count in cohort["history_counts"].items():
    lines.append(f"| {history} | {count} |")
lines += [
    "",
    "Calibration uses the same block/class weights. Mean predicted probability and observed success below summarize the entire selected panel; all sixty prespecified bin cells appear later and in [CALIBRATION.csv](CALIBRATION.csv). Many bins contain only one to six records, so these tables do not establish precise calibration. No recalibration or calibration-based selection was performed.",
    "",
    "| Noise | Predictor | Weighted mean prediction | Weighted observed success |",
    "|---|---|---:|---:|",
]
for item in diagnostics["calibration_totals"]:
    lines.append(f"| {item['regime']} | {names[item['model']]} | {item['mean_prediction']:.8f} | {item['observed_fraction']:.8f} |")
lines += [
    "",
    "The retained first-repeat measurements cost 9,072 native reads in total: 8,064 successor-model reads and 1,008 direct-model reads, plus 378 separate flat-audit reads. TT008 uses zero additional native probes. Cached reuse incurred zero new probe reads here, but does not erase their original cost. The source acquisition used 14,336 native reads; both original measurement repeats used 18,144 native reads; acquisition and both repeats added 948 flat-audit reads. These historical totals include the retained subset and must not be added to it again.",
    "",
    "The present continuation evaluation added 2,394 primary native reads and 608 flat-audit reads, shared as an evaluation cost across predictors. Shared boundary acquisition, transfer computation, fitting/scaling and prediction arithmetic also cost resources. Model-specific elapsed times were not measured separately. The 64-to-8 comparison is an eightfold probe-read count ratio, not a measured wall-time or total-cost ratio. No cost-effectiveness advantage has been established.",
    "",
    f"The closeout verified {verification['frozen_input_files']} frozen input files, {verification['output_files']} output-manifest files, 272 historical source files, all 126 first-repeat forecasts and packet identities, all 32 continuation commits and all 126 terminal labels. It checked every saved rewrite chain, terminal generation, protected injury mask, retained birth-force binding and paired-regime starting packet. All six Brier scores, four block contrasts, sixty calibration bins and twelve current-expression scores agree with separate scalar reductions; the maximum additional arithmetic discrepancy was {verification['maximum_additional_arithmetic_discrepancy']:.3g}.",
    "",
    "The worker had checked one key-selected record per block, both regimes and all nineteen reads against a separate flat implementation, totaling 608 byte-exact checks with each implementation propagating its own packet. Closeout verified those bound receipts and retained arrays; it did not rerun dynamics or regenerate full ongoing noise streams. Those streams are bound by hashes and frozen generator code. The prior eleven wrapper tests and native-reader qualifications remain intact. An independently coded check within this programme is not an independent laboratory replication. Details are in [VERIFICATION.json](VERIFICATION.json), [DIAGNOSTICS.json](DIAGNOSTICS.json) and the original [run report](../../runs/pilot_v1/REPORT.md).",
    "",
    "This completes execution and evidence qualification for the bounded pilot. Predictive superiority remains unresolved on the selected panel. The 304-block comparison remains stopped by user instruction; it has no global forecast seal or future outcomes and is not completed by this smaller experiment. Earlier nested-selection and paired-reduction failures remain part of the evidence. Family/budget selection used previously exposed development outcomes, and the present panel was already inspected for precision before these new futures.",
    "",
    "The next decision is to develop a bounded paired repair-benefit test, not to qualify a scheduler from failure risk alone. For a declared action a and pre-action boundary z, the target is Δ(z,a) = E[Y_H(repair a) − Y_H(no repair) | z]. Binary benefit equals the probability of rescue minus the probability of harm. A high predicted failure rate does not identify either term. Both branches must start at the same boundary, receive a predeclared coupling with correct disturbance marginals, and propagate their own states. Their endpoint, horizon and retained distinction must match.",
    "",
    "Before new outcomes, specify the actual repair operation and its information/resource inputs, freeze the acquisition and evaluation split by founder block, and benchmark the complete paired assay on disposable inputs. Keep direct-probe and ordinary predictors, failure-risk allocation, random/fixed allocation and no repair as appropriate comparators under the same total sensing-and-repair budget. For varying action costs, specify the constrained policy; benefit divided by cost alone does not prove optimal sequential scheduling. An initial development assay should aim below one hour with a fixed cap, following the user's six-hour general ceiling. The present natural-future labels identify no repair counterfactual; a later benefit assay remains a separate study. No new scientific study or automatic sample extension has been launched by this closeout.",
    "",
    "All weighted calibration bins follow. A bin b covers [b/10, (b+1)/10), except the last includes probability one. Panel mass sums to one within each predictor/noise pair; record counts are unweighted. Empty cells, if any, are shown as a dash.",
    "",
    "| Noise | Predictor | Bin | Records | Panel mass | Mean prediction | Observed fraction |",
    "|---|---|---:|---:|---:|---:|---:|",
]
for item in diagnostics["calibration"]:
    fmt = lambda v: "—" if v is None else f"{v:.8f}"
    lines.append(f"| {item['regime']} | {names[item['model']]} | {item['bin']} | {item['records']} | {item['panel_mass']:.8f} | {fmt(item['mean_prediction'])} | {fmt(item['observed_fraction'])} |")
with (OUT / "REPORT.md").open("x") as stream:
    stream.write("\n".join(lines) + "\n")

write("DECISION.json", dict(utc=datetime.now(timezone.utc).isoformat(),
    status="BOUNDED_PILOT_CLOSED", evidence_audit="PASS", predictive_verdict=result["decision"],
    cost_effective_advantage_established=False, rdt_specific_prediction_established=False,
    completed_study="rdt_cached_outcome_pilot_v0_1/pilot_v1",
    stopped_304_block_study_completed=False, automatic_extension=False,
    next_target="Paired repair benefit including rescues and harms, with shared total resource budgets.",
    next_study_launched=False, preferred_future_wall_seconds=3600, general_wall_ceiling_seconds=21600,
    source_sha256={"run_complete":sha(PACKAGE / "runs/pilot_v1/COMPLETE.json"),
        "verification":sha(OUT / "VERIFICATION.json"), "report":sha(OUT / "REPORT.md")}))
write("EXPOSURE.json", dict(utc=datetime.now(timezone.utc).isoformat(),
    programme="RDT theory lane", status="ALL_PILOT_OUTCOMES_EXPOSED_DEVELOPMENT_DATA_FOR_FUTURE_WORK",
    study="rdt_cached_outcome_pilot_v0_1", blocks=list(range(16)), records=63, case_regimes=126,
    already_exposed="Earlier eight-block development outcomes informed model family/budget; all precision measurements and selected records had been inspected before these futures.",
    newly_inspected="Complete future outcomes, raw terminal windows, scores, contrasts, calibration, class diagnostics and metadata in the named pilot.",
    namespace="RDT_cached_outcome_pilot_v0_1_future", stage="pilot",
    future_labels_used_to_refit_current_models=False, external_preregistration=False,
    later_hypotheses_status="Development informed by these outcomes; fresh seeds alone do not make a fresh hypothesis.",
    scope="Local exposure delta for handoff; does not edit another lane's register or inspect its results.",
    result_manifest_sha256=sha(PACKAGE / "runs/pilot_v1/OUTPUTS.json"),
    forecasts_sha256=sha(PACKAGE / "runs/pilot_v1/FORECAST_SEAL.json")))
files = {str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
write("MANIFEST.json", dict(utc=datetime.now(timezone.utc).isoformat(), sha256=files,
    code_sha256={p.name:sha(p) for p in (HERE / "audit_closeout.py", Path(__file__))}))
print(json.dumps(dict(status="CLOSEOUT_SAVED", decision=result["decision"], report=str(OUT / "REPORT.md"), files=len(files))))
