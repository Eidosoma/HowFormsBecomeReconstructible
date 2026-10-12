"""Development -> frozen A-only predictions -> previously unobserved B outcomes."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import bootstrap, cap_cpus, dump, finish, new_run, rng, sha, utc
import design as d
import numpy as np


def verify_run(path, phase=None):
    path = Path(path).resolve()
    if not path.is_relative_to(HERE): raise ValueError("Local E008 inputs required")
    complete = json.loads((path/"COMPLETE.json").read_text())
    for rel, digest in complete["outputs_sha256"].items():
        if sha(path/rel) != digest: raise ValueError(f"Changed input {rel}")
    if phase is not None:
        assert json.loads((path/"manifest.json").read_text())["contract"]["phase"] == phase
    return complete


def worker(phase, block, output, prediction_path=None):
    cap_cpus(); started = time.monotonic()
    if phase == "evaluate":
        source_path = prediction_path/f"source_{block:06d}.npz"
        with np.load(source_path, allow_pickle=False) as file: source = dict(file)
        jobs = (("B", "test", d.TEST),)
    else:
        source = d.make_source(block)
        source_path = output/f"source_{block:06d}.npz"
        np.savez_compressed(source_path, **source)
        if phase == "development": jobs = (("A", "development", d.DEVELOPMENT), ("B", "development", d.DEVELOPMENT))
        elif phase == "predict": jobs = (("A", "test", d.TEST),)
        elif phase == "benchmark": jobs = (("A", "development", d.DEVELOPMENT), ("B", "development", d.DEVELOPMENT), ("A", "test", d.TEST), ("B", "test", d.TEST))
        else: raise ValueError(phase)
    source_sha = sha(source_path)
    times = {}
    for body, domain, conditions in jobs:
        step_started = time.monotonic()
        raw = d.read(source["acquired"], block, body, conditions, neighbors=source["graph_neighbors"])
        np.savez_compressed(output/f"body_{body}_{domain}_{block:06d}.npz", **raw)
        times[body+"_"+domain] = time.monotonic()-step_started
    assert sha(source_path) == source_sha
    dump(output/f"worker_{block}.json", dict(block=block, phase=phase, seconds=time.monotonic()-started,
         body_seconds=times, graph_sha256=hashlib.sha256(source["graph_neighbors"].astype("<i8").tobytes()).hexdigest(), source_file=str(source_path.relative_to(ROOT)), source_sha256=source_sha))


def load_observations(output, block, body, domain, source_root=None):
    with np.load((source_root or output)/f"source_{block:06d}.npz", allow_pickle=False) as source:
        prototype = source["prototype"]
    with np.load(output/f"body_{body}_{domain}_{block:06d}.npz", allow_pickle=False) as raw:
        individual, observed = d.observations(raw, prototype)
    return prototype, individual, observed


def train(output, ids):
    feature_rows = {name: [] for name in ("intervention", "appearance", "causal")}
    targets = []; all_a = []; all_b = []
    for block in ids:
        p, _, a = load_observations(output, block, "A", "development")
        _, _, b = load_observations(output, block, "B", "development")
        x = d.features(p, a, d.DEVELOPMENT)
        for name in feature_rows: feature_rows[name].append(x[name][:, 1:].reshape(-1, x[name].shape[-1]))
        targets.append((b[:, 1:, :2]-b[:, :1, :2]).reshape(-1, 2)); all_a.append(a); all_b.append(b)
    target = np.concatenate(targets)
    models = {name: d.fit_ridge(np.concatenate(rows), target) for name, rows in feature_rows.items()}
    dump(output/"models.json", models)
    np.savez_compressed(output/"development_observations.npz", A=np.array(all_a), B=np.array(all_b))
    dump(output/"development_summary.json", dict(blocks=ids, founders=4*len(ids), training_rows=len(target),
         conditions=d.DEVELOPMENT, fixed_penalty=.01, tuning_performed=False,
         target_response_rms=float(np.sqrt((target*target).mean())), model_file_sha256=sha(output/"models.json")))


def forecasts(output, ids, development_path, technical=False):
    models = json.loads((development_path/"models.json").read_text())
    data = {name: [] for name in d.MODELS}; observations = []
    for block in ids:
        p, _, a = load_observations(output, block, "A", "test")
        predictions = d.predict(d.features(p, a, d.TEST), a-a[:, :1], models)
        for name in d.MODELS: data[name].append(predictions[name])
        observations.append(a)
    np.savez_compressed(output/"predictions.npz", **{name:np.array(x) for name,x in data.items()},
                        observed_A=np.array(observations), blocks=np.array(ids))
    dump(output/"prediction_freeze.json", dict(time=utc(), blocks=ids, conditions=d.TEST,
         primary_condition_indices=list(range(3,len(d.TEST))), development_run=str(development_path.relative_to(ROOT)),
         development_complete_sha256=None if technical else sha(development_path/"COMPLETE.json"), models_sha256=sha(development_path/"models.json"),
         predictions_sha256=sha(output/"predictions.npz"), B_test_generated=technical,
         graph_sha256={str(b):json.loads((output/f"worker_{b}.json").read_text())["graph_sha256"] for b in ids},
         raw_A_sha256={f.name:sha(f) for f in sorted(output.glob("body_A_test_*.npz"))}))


def evaluate(output, ids, prediction_path, technical=False):
    observed = []; individual = []
    for block in ids:
        _, individual_b, b = load_observations(output, block, "B", "test", source_root=prediction_path)
        observed.append(b); individual.append(individual_b)
    observed = np.array(observed); actual = observed[:, :, 3:, :2]-observed[:, :, :1, :2]
    np.savez_compressed(output/"evaluation_observations.npz", B=observed, individual_B=np.array(individual))
    losses = {}; rows = []
    with np.load(prediction_path/"predictions.npz", allow_pickle=False) as predictions:
        assert predictions["blocks"].tolist() == list(ids)
        observed_a = predictions["observed_A"]
        for name in d.MODELS:
            p = predictions[name][:, :, 3:]
            losses[name] = ((p-actual)**2).mean(axis=(1,2,3))
            for i, block in enumerate(ids):
                for f in range(4):
                    for c, condition in enumerate(d.JOINT):
                        rows.append(dict(block=block, founder=f, condition=condition["name"], model=name,
                            predicted_own=float(p[i,f,c,0]), actual_own=float(actual[i,f,c,0]),
                            predicted_foreign=float(p[i,f,c,1]), actual_foreign=float(actual[i,f,c,1])))
    comparisons = {name:bootstrap(loss-losses["causal"], "E008:evaluation") for name,loss in losses.items() if name != "causal"}
    gates = {name:stats["ci95"][0]>0 for name,stats in comparisons.items()}
    direct_comparisons = {name:bootstrap(losses[name]-losses["identity"], "E008:evaluation") for name in ("zero","intervention","appearance")}
    draws = rng("E008:evaluation","bootstrap").integers(0,len(ids),(10000,len(ids)))
    direct_ci = np.quantile(100*np.sqrt(losses["identity"][draws].mean(axis=1)),[.025,.975]).tolist()
    direct_status = "TECHNICAL_ONLY" if technical else "WITHIN_TOLERANCE" if direct_ci[1]<2. else "OUTSIDE_TOLERANCE" if direct_ci[0]>2. else "TOLERANCE_UNRESOLVED"
    references = {}
    for body,x in (("A",observed_a),("B",observed)):
        block = x.mean(axis=1)
        differences = dict(intact_minus_foreign_record=block[:,0,0]-block[:,1,0],
                           intact_minus_erased_record=block[:,0,0]-block[:,2,0])
        differences.update({name+"_own_minus_foreign_target":block[:,i,0]-block[:,i,1]
                            for i,name in enumerate(("intact","foreign","erased"))})
        references[body] = {name:bootstrap(x,"E008:evaluation") for name,x in differences.items()}
    graph_rows = []
    for block in ids:
        with np.load(prediction_path/f"source_{block:06d}.npz",allow_pickle=False) as source:
            original = set(map(tuple,source["graph_original_edges"].tolist()))
            edges = set(map(tuple,source["graph_edges"].tolist()))
            added = sorted(edges-original)
            graph_rows.append(dict(block=block,replaced_edges=len(original-edges),new_edges=len(added),
                mean_new_edge_distance=float(np.mean([d.distance(*edge) for edge in added])),
                proposals=int(source["graph_attempts"])))
    status = "TECHNICAL_ONLY" if technical else "RESPONSE_TRANSFER_QUALIFIED" if all(gates.values()) else "RESPONSE_TRANSFER_NOT_QUALIFIED"
    summary = dict(experiment="E008", status=status, blocks=ids, founders=4*len(ids), recipients=8,
        test_conditions=d.JOINT, losses={name:dict(block_mse=x.tolist(), mean_mse=float(x.mean()), rmse_points=float(100*np.sqrt(x.mean()))) for name,x in losses.items()},
        comparisons=comparisons, gates=gates,
        direct_transfer=dict(status=direct_status,rmse_ci95_points=direct_ci,tolerance_points=2.,comparisons=direct_comparisons),
        reference_contrasts=references,
        graph_summary=graph_rows, prediction_run=str(prediction_path.relative_to(ROOT)),
        predictions_sha256=sha(prediction_path/"predictions.npz"), B_mean_observations=observed.mean(axis=(0,1)).tolist(),
        B_mean_response=actual.mean(axis=(0,1)).tolist(), related_tissue_family_only=True,
        independent_recipient_noise_between_bodies=True, refit_on_test=False)
    dump(output/"summary.json", summary)
    with (output/"individual_predictions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    lines = ["# E008 prospective transfer between tissue connectivities", "", f"**{status}**", "",
             f"{len(ids)} test blocks, {4*len(ids)} founders, eight fresh recipients per body and eight joint interventions. A and B recipient noise is independent.", "",
             "| Forecaster | RMSE, percentage points | MSE improvement from causal response, squared points [95%] |",
             "| --- | --- | --- |"]
    for name in d.MODELS:
        stats = comparisons.get(name)
        gain = "—" if stats is None else f"{10000*stats['mean']:+.3f} [{10000*stats['ci95'][0]:+.3f}, {10000*stats['ci95'][1]:+.3f}]"
        lines.append(f"| {name} | {summary['losses'][name]['rmse_points']:.3f} | {gain} |")
    lines += ["", f"Direct transfer tolerance assessment: **{direct_status}**. RMSE 95% interval [{direct_ci[0]:.3f}, {direct_ci[1]:.3f}] points; prospective tolerance 2 points. This secondary assessment does not change the learned-map verdict.", "",
              "| Baseline versus direct transfer | MSE improvement, squared points [95%] |", "| --- | --- |"]
    for name,st in direct_comparisons.items():
        lines.append(f"| {name} | {10000*st['mean']:+.3f} [{10000*st['ci95'][0]:+.3f}, {10000*st['ci95'][1]:+.3f}] |")
    lines += ["", f"Qualification gates: `{json.dumps(gates, sort_keys=True)}`.", "",
              "The forecast concerns changes in own/foreign founder agreement relative to B's intact response. B's intact response was unavailable to the forecasters. It becomes an evaluation reference after prediction freezing. A's actual response to each test intervention is an input to transfer. All models and comparisons were fixed before development outcomes.", "",
              "| Joint intervention | Mean B own-agreement change, points | Mean B foreign-agreement change, points |", "| --- | --- | --- |"]
    for c, condition in enumerate(d.JOINT):
        lines.append(f"| {condition['name']} | {100*actual[:,:,c,0].mean():+.3f} | {100*actual[:,:,c,1].mean():+.3f} |")
    lines += ["", "| Reference contrast, points [95%] | A | B |", "| --- | --- | --- |"]
    fmt = lambda st:f"{100*st['mean']:+.2f} [{100*st['ci95'][0]:+.2f}, {100*st['ci95'][1]:+.2f}]"
    for name in references["A"]:
        lines.append(f"| {name} | {fmt(references['A'][name])} | {fmt(references['B'][name])} |")
    lines += ["", "This is a one-read response test between related tissues with shared coordinates and a supplied reader. Each node retains degree four and total coupling strength one; exactly 128 of 512 undirected edges are replaced by links of toroidal Manhattan length at least four. One new graph is sampled per block. The learned model receives no graph-specific feature. Founder formation and capture use A. It does not establish transfer between unrelated substrates, transfer of a competence, serial renewal, or independently active forms. Every declared founder and intervention is retained. The comparisons are a conjunction; a partial win does not pass the full transfer criterion."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    p = argparse.ArgumentParser(); p.add_argument("phase", choices=("benchmark", "development", "predict", "evaluate"))
    p.add_argument("--output", type=Path, required=True); p.add_argument("--workers", type=int, default=12)
    p.add_argument("--development", type=Path); p.add_argument("--predictions", type=Path); p.add_argument("--worker", type=int)
    args = p.parse_args(); cap_cpus()
    if not args.output.resolve().is_relative_to(HERE): raise ValueError("Local E008 output required")
    if not 1 <= args.workers <= 12: p.error("workers must be 1–12")
    if args.phase == "predict" and args.development is None: p.error("predict requires --development")
    if args.phase == "evaluate" and args.predictions is None: p.error("evaluate requires --predictions")
    if args.worker is not None:
        worker(args.phase, args.worker, args.output.resolve(), args.predictions.resolve() if args.predictions else None); return
    dependencies = {}
    if args.development:
        args.development = args.development.resolve(); verify_run(args.development, "development")
        dependencies["development"] = dict(path=str(args.development.relative_to(ROOT)), complete_sha256=sha(args.development/"COMPLETE.json"))
    if args.predictions:
        args.predictions = args.predictions.resolve(); verify_run(args.predictions, "predict")
        dependencies["predictions"] = dict(path=str(args.predictions.relative_to(ROOT)), complete_sha256=sha(args.predictions/"COMPLETE.json"))
        freeze = json.loads((args.predictions/"prediction_freeze.json").read_text())
        assert not freeze["B_test_generated"] and freeze["predictions_sha256"] == sha(args.predictions/"predictions.npz")
        assert not list(args.predictions.glob("body_B*"))
    ids = [d.BENCH_ID] if args.phase == "benchmark" else list(d.DEV_IDS if args.phase == "development" else d.TEST_IDS)
    inputs = [ROOT/x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json", "E001_unprescribed_capture/model.py", "E003_cross_embodiment/design.py")]
    inputs += [HERE/x for x in ("design.py", "run.py", "audit.py", "tests.py", "PROTOCOL.md")]
    started = time.monotonic()
    output = new_run(args.output, inputs, dict(experiment="E008", phase=args.phase, blocks=ids, config=asdict(d.CFG),
             development_conditions=d.DEVELOPMENT, test_conditions=d.TEST, dependencies=dependencies, workers=args.workers,
             rewiring_fraction=.25, edges_replaced=128, minimum_new_edge_distance=4, direct_rmse_tolerance_points=2.))
    def launch(block):
        command = [sys.executable, "-B", str(HERE/"run.py"), args.phase, "--output", str(output), "--worker", str(block)]
        if args.development: command += ["--development", str(args.development)]
        if args.predictions: command += ["--predictions", str(args.predictions)]
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(launch,b) for b in ids]): print("Completed", args.phase, future.result(), flush=True)
        if args.phase == "development": train(output, ids)
        elif args.phase == "predict": forecasts(output, ids, args.development)
        elif args.phase == "evaluate": evaluate(output, ids, args.predictions)
        else:
            train(output, ids)
            # This technical case deliberately has all outcomes; no blind claim.
            forecasts(output, ids, output, technical=True)
            evaluate(output, ids, output, technical=True)
        for item in dependencies.values():
            path = ROOT/item["path"]; verify_run(path)
            assert sha(path/"COMPLETE.json") == item["complete_sha256"]
        finish(output, started, dict(experiment="E008", phase=args.phase, blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output/"FAILED.json", dict(time=utc(), traceback=traceback.format_exc())); raise


if __name__ == "__main__": main()
