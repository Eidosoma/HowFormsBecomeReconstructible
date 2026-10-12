"""Freeze source-only repair choices, then evaluate untouched target futures."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import bootstrap, cap_cpus, dump, finish, new_run, sha, utc
import design as d
import numpy as np


def verify_run(path, phase):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT): raise ValueError("Local dependency required")
    complete = json.loads((path/"COMPLETE.json").read_text())
    assert complete["status"] == "COMPLETE" and not (path/"FAILED.json").exists()
    for rel, digest in complete["outputs_sha256"].items():
        if sha(path/rel) != digest: raise ValueError(f"Changed dependency: {rel}")
    manifest = json.loads((path/"manifest.json").read_text())
    assert manifest["contract"]["phase"] == phase
    for rel, digest in manifest["inputs_sha256"].items():
        assert sha(ROOT/rel) == sha(path/"inputs"/rel) == digest, rel
    audit = json.loads((path/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(path/"COMPLETE.json")
    assert audit["audit_code_sha256"] == sha(path.parent.parent/"audit.py")
    return dict(path=str(path.relative_to(ROOT)), phase=phase,
                complete_sha256=sha(path/"COMPLETE.json"), audit_sha256=sha(path/"INDEPENDENT_AUDIT.json"))


def array_sha(x): return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def worker(phase, block, output, prediction_path=None):
    cap_cpus(); started = time.monotonic()
    if phase == "evaluate":
        source_path = prediction_path/f"source_{block:06d}.npz"
        with np.load(source_path, allow_pickle=False) as f: source = dict(f)
        bodies = ("B",)
    else:
        source = d.make_source(block)
        source_path = output/f"source_{block:06d}.npz"
        np.savez_compressed(source_path, **source)
        bodies = ("A", "B") if phase == "benchmark" else ("A",)
    source_sha = sha(source_path); times = {}
    for body in bodies:
        step_started = time.monotonic()
        raw = d.read(source["repair_packets"], block, body, source["graph_neighbors"])
        np.savez_compressed(output/f"body_{body}_{block:06d}.npz", **raw)
        times[body] = time.monotonic()-step_started
    assert sha(source_path) == source_sha
    dump(output/f"worker_{block}.json", dict(block=block, phase=phase, seconds=time.monotonic()-started,
         body_seconds=times, source_file=str(source_path.relative_to(ROOT)), source_sha256=source_sha,
         graph_sha256=array_sha(source["graph_neighbors"].astype("<i8")),
         menu_sha256=array_sha(source["repair_packets"])))


def observe(output, source_root, block, body):
    with np.load(source_root/f"source_{block:06d}.npz", allow_pickle=False) as f:
        prototype = f["prototype"]; heuristic = f["repair_heuristic"]
    with np.load(output/f"body_{body}_{block:06d}.npz", allow_pickle=False) as f:
        individual, mean = d.old.observations(f, prototype)
    return prototype, heuristic, individual, mean


def freeze_choices(output, ids, technical=False):
    models = json.loads(d.MODEL_PATH.read_text()); records = []
    for block in ids:
        p, heuristic, _, a = observe(output, output, block, "A")
        records.append(d.select(p, a, heuristic, models))
    np.savez_compressed(output/"selections.npz", blocks=np.array(ids),
                        **{key:np.array([v[key] for v in records]) for key in records[0]})
    dump(output/"selection_freeze.json", dict(time=utc(), blocks=ids, policies=d.POLICIES,
         conditions=d.CONDITIONS, models_sha256=sha(d.MODEL_PATH),
         model_development_run=str(d.MODEL_PATH.parent.relative_to(ROOT)),
         selections_sha256=sha(output/"selections.npz"), B_generated=technical,
         source_sha256={f.name:sha(f) for f in sorted(output.glob("source_*.npz"))},
         raw_A_sha256={f.name:sha(f) for f in sorted(output.glob("body_A_*.npz"))},
         graph_sha256={str(b):json.loads((output/f"worker_{b}.json").read_text())["graph_sha256"] for b in ids},
         menu_sha256={str(b):json.loads((output/f"worker_{b}.json").read_text())["menu_sha256"] for b in ids}))


def csv_write(path, rows):
    with path.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def evaluate(output, ids, prediction_path, technical=False):
    observations = []; individuals = []
    for block in ids:
        _, _, individual, b = observe(output, prediction_path, block, "B")
        observations.append(b); individuals.append(individual)
    b = np.array(observations)
    np.savez_compressed(output/"evaluation_observations.npz", B=b, individual_B=np.array(individuals))
    with np.load(prediction_path/"selections.npz", allow_pickle=False) as f:
        assert f["blocks"].tolist() == list(ids)
        selected = dict(f)
    weights = selected["weights"]
    scores = np.einsum("bfpk,bfko->bfpo", weights, b[:,:,4:,:2])
    specificity = scores[:,:,:,0]-scores[:,:,:,1]
    unrepaired_specificity = b[:,:,1,0]-b[:,:,1,1]
    utility = specificity-unrepaired_specificity[:,:,None]
    own_gain = scores[:,:,:,0]-b[:,:,1:2,0]
    best = (b[:,:,4:,0]-b[:,:,4:,1]).max(axis=-1)
    regret = best[:,:,None]-specificity
    metrics = dict(utility=utility, specificity=specificity, own_agreement=scores[:,:,:,0],
                   own_gain=own_gain, hindsight_regret=regret)
    policies = {name:{key:bootstrap(values[:,:,j].mean(axis=1), "E009:utility")
                     for key,values in metrics.items()} for j,name in enumerate(d.POLICIES)}
    comparisons = {name:bootstrap((utility[:,:,0]-utility[:,:,j]).mean(axis=1), "E009:utility")
                   for j,name in enumerate(d.POLICIES) if j}
    gates = {"map_beats_"+name:st["ci95"][0]>0 for name,st in comparisons.items()}
    gates.update(map_recovers_specificity=policies["map"]["utility"]["ci95"][0]>0,
                 map_recovers_own_agreement=policies["map"]["own_gain"]["ci95"][0]>0)
    references = {}
    for body, obs in (("A",selected["observed_A"]),("B",b)):
        means = obs.mean(axis=1)
        deltas = dict(intact_minus_foreign_record=means[:,0,0]-means[:,2,0],
                      intact_minus_erased_record=means[:,0,0]-means[:,3,0],
                      intact_minus_unrepaired_own=means[:,0,0]-means[:,1,0])
        deltas.update({c["name"]+"_specificity":means[:,j,0]-means[:,j,1] for j,c in enumerate(d.CONDITIONS[:4])})
        references[body] = {name:bootstrap(v,"E009:utility") for name,v in deltas.items()}
    choices = selected["choices"]
    frequency = {name:np.bincount(choices[:,:,j].ravel(),minlength=8).tolist() for j,name in enumerate(d.POLICIES[:3])}
    agreement = {a+"_"+c:float((choices[:,:,i]==choices[:,:,j]).mean())
                 for i,a in enumerate(d.POLICIES[:3]) for j,c in enumerate(d.POLICIES[:3]) if j>i}
    status = "TECHNICAL_ONLY" if technical else "REPAIR_SELECTION_QUALIFIED" if all(gates.values()) else "REPAIR_SELECTION_NOT_QUALIFIED"
    summary = dict(experiment="E009", status=status, blocks=ids, founders=4*len(ids), recipients=8,
        policies=policies, comparisons=comparisons, gates=gates, reference_contrasts=references,
        choice_frequency=frequency, choice_agreement=agreement, conditions=d.CONDITIONS,
        model_sha256=sha(d.MODEL_PATH), selections_sha256=sha(prediction_path/"selections.npz"),
        prediction_run=str(prediction_path.relative_to(ROOT)), B_mean_observations=b.mean(axis=(0,1)).tolist(),
        external_backup=True, restored_entries=64, initial_erased_entries=192, candidates=8,
        no_refit=True, random_policy="exact uniform menu expectation", hindsight_optimistic=True)
    dump(output/"summary.json", summary)
    policy_rows = []; menu_rows = []
    for i, block in enumerate(ids):
        for f in range(4):
            for j,name in enumerate(d.POLICIES):
                policy_rows.append(dict(block=block, founder=f, policy=name,
                    choice=int(choices[i,f,j]) if j<3 else "uniform",
                    unrepaired_specificity=float(unrepaired_specificity[i,f]),
                    **{key:float(v[i,f,j]) for key,v in metrics.items()}))
            for c,condition in enumerate(d.CONDITIONS):
                row = dict(block=block, founder=f, condition=condition["name"],
                    predicted_own_change=float(selected["predicted"][i,f,c,0]),
                    predicted_foreign_change=float(selected["predicted"][i,f,c,1]))
                for body,obs in (("A",selected["observed_A"]),("B",b)):
                    for j,key in enumerate(("own","foreign","resolved","neighbor")):
                        row[body+"_"+key] = float(obs[i,f,c,j])
                row.update({name+"_weight":float(weights[i,f,j,c-4]) if c>=4 else 0.
                            for j,name in enumerate(d.POLICIES)})
                menu_rows.append(row)
    csv_write(output/"individual_policies.csv", policy_rows)
    csv_write(output/"menu_outcomes.csv", menu_rows)
    fmt = lambda st:f"{100*st['mean']:+.3f} [{100*st['ci95'][0]:+.3f}, {100*st['ci95'][1]:+.3f}]"
    lines = ["# E009 — prospective repair selection", "", f"**{status}**", "",
        f"All {len(ids)} fresh blocks / {4*len(ids)} founders retained; eight recipient futures per body and eight equal-cost repair options per founder.", "",
        "Primary utility is recovery of own-minus-foreign founder agreement from the unrepaired record. Values are percentage points, with 95% whole-block bootstrap intervals.", "",
        "| Frozen policy | Specificity recovery | Own-agreement recovery | Gap to hindsight best specificity |",
        "| --- | --- | --- | --- |"]
    for name,st in policies.items():
        lines.append(f"| {name} | {fmt(st['utility'])} | {fmt(st['own_gain'])} | {fmt(st['hindsight_regret'])} |")
    lines += ["", "| Map minus baseline utility | Points [95%] |", "| --- | --- |"]
    for name,st in comparisons.items(): lines.append(f"| {name} | {fmt(st)} |")
    lines += ["", f"Qualification gates: `{json.dumps(gates, sort_keys=True)}`.", "",
        "| Policy | Absolute target specificity | Absolute own agreement |", "| --- | --- | --- |"]
    for name,st in policies.items(): lines.append(f"| {name} | {fmt(st['specificity'])} | {fmt(st['own_agreement'])} |")
    lines += ["", f"Choice agreement: `{json.dumps(agreement, sort_keys=True)}`.", "",
        "| Reference contrast | A, points [95%] | B, points [95%] |", "| --- | --- | --- |"]
    for name in references["A"]: lines.append(f"| {name} | {fmt(references['A'][name])} | {fmt(references['B'][name])} |")
    lines += ["", "The E008 model was applied unchanged. Source observations and saved founder prototypes enter the selector; target states do not. Every candidate shares the same intervention descriptors, so only source-response features distinguish candidates within a founder's menu. The random comparator is the exact expected utility of uniform choice among the same eight options, including the heuristic candidate.", "",
        "Repair restores 64 of 192 erased float64 entries from an external clean backup, before development in a fresh body. The backup and source probes are supplied; equal restoration budgets do not equalize sensing or computation. The hindsight best option uses noisy target outcomes and is an optimistic diagnostic. This is one-read decision utility in a related tissue family, not autonomous bodily repair or serial renewal. Full qualification requires every gate, and all failed comparisons are retained."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    p = argparse.ArgumentParser(); p.add_argument("phase", choices=("benchmark","predict","evaluate"))
    p.add_argument("--output",type=Path,required=True); p.add_argument("--workers",type=int,default=12)
    p.add_argument("--predictions",type=Path); p.add_argument("--worker",type=int)
    args = p.parse_args(); cap_cpus()
    if not args.output.resolve().is_relative_to(HERE): raise ValueError("Local E009 output required")
    if not 1<=args.workers<=12: p.error("workers must be 1–12")
    if args.phase=="evaluate" and args.predictions is None: p.error("evaluate requires --predictions")
    if args.predictions: args.predictions=args.predictions.resolve()
    if args.worker is not None:
        worker(args.phase,args.worker,args.output.resolve(),args.predictions); return
    assert sha(d.MODEL_PATH)==d.MODEL_SHA
    dependencies = dict(model_development=verify_run(d.MODEL_PATH.parent,"development"))
    if args.predictions:
        if not args.predictions.is_relative_to(HERE): raise ValueError("Local prediction run required")
        dependencies["predictions"]=verify_run(args.predictions,"predict")
        frozen=json.loads((args.predictions/"selection_freeze.json").read_text())
        assert not frozen["B_generated"] and not list(args.predictions.glob("body_B*"))
        assert frozen["selections_sha256"]==sha(args.predictions/"selections.npz")
        assert frozen["models_sha256"]==d.MODEL_SHA and frozen["blocks"]==list(d.IDS)
    ids = [d.BENCH_ID] if args.phase=="benchmark" else list(d.IDS)
    inputs = [ROOT/x for x in ("common.py","run_python.sh","SOURCE_SNAPSHOT.json",
        "E001_unprescribed_capture/model.py","E003_cross_embodiment/design.py",
        "E008_rewired_transfer/design.py","E008_rewired_transfer/audit.py")]
    inputs += [d.MODEL_PATH,d.MODEL_PATH.parent/"COMPLETE.json",d.MODEL_PATH.parent/"INDEPENDENT_AUDIT.json"]
    inputs += [HERE/x for x in ("design.py","run.py","audit.py","tests.py","PROTOCOL.md")]
    started=time.monotonic()
    output=new_run(args.output,inputs,dict(experiment="E009",phase=args.phase,blocks=ids,
        config=asdict(d.CFG),conditions=d.CONDITIONS,policies=d.POLICIES,workers=args.workers,
        dependencies=dependencies,model_sha256=d.MODEL_SHA,injury_entries=192,restored_entries=64,
        menu_options=8,bootstrap_tag="E009:utility",model_refitting=False))
    def launch(block):
        command=[sys.executable,"-B",str(HERE/"run.py"),args.phase,"--output",str(output),"--worker",str(block)]
        if args.predictions:command += ["--predictions",str(args.predictions)]
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for count,future in enumerate(as_completed([pool.submit(launch,b) for b in ids]),1):
                future.result()
                if count%16==0 or count==len(ids):print(f"Completed {args.phase}: {count}/{len(ids)} blocks",flush=True)
        if args.phase in ("predict","benchmark"):freeze_choices(output,ids,args.phase=="benchmark")
        if args.phase in ("evaluate","benchmark"):evaluate(output,ids,output if args.phase=="benchmark" else args.predictions,args.phase=="benchmark")
        for item in dependencies.values():assert verify_run(ROOT/item["path"],item["phase"])==item
        finish(output,started,dict(experiment="E009",phase=args.phase,blocks_completed=len(ids)))
        print("Complete:",output,flush=True)
    except BaseException:
        dump(output/"FAILED.json",dict(time=utc(),traceback=traceback.format_exc()));raise


if __name__=="__main__":main()
