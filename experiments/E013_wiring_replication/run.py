"""Frozen-model replication with an identical predictor given incorrect wiring."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from dataclasses import asdict
from pathlib import Path
import argparse
import csv
import json
import subprocess
import sys
import time
import traceback
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import bootstrap,cap_cpus,dump,finish,new_run,sha,utc
import design as d
import numpy as np


def verify_run(path,phase):
    path=Path(path).resolve()
    assert path.is_relative_to(ROOT)
    manifest=json.loads((path/"manifest.json").read_text())
    complete=json.loads((path/"COMPLETE.json").read_text())
    assert complete["status"]=="COMPLETE" and not (path/"FAILED.json").exists()
    assert manifest["contract"]["phase"]==phase
    for rel,digest in complete["outputs_sha256"].items():assert sha(path/rel)==digest,rel
    for rel,digest in manifest["inputs_sha256"].items():
        assert sha(ROOT/rel)==sha(path/"inputs"/rel)==digest,rel
    audit=json.loads((path/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"]=="PASS" and audit["complete_sha256"]==sha(path/"COMPLETE.json")
    assert audit["audit_code_sha256"]==sha(path.parent.parent/"audit.py")
    return dict(path=str(path.relative_to(ROOT)),phase=phase,complete_sha256=sha(path/"COMPLETE.json"),
        audit_sha256=sha(path/"INDEPENDENT_AUDIT.json"))


def load(path):
    with np.load(path,allow_pickle=False) as f:return dict(f)


def worker(phase,block,output,prediction=None):
    cap_cpus();started=time.monotonic()
    if phase=="evaluate":
        path=prediction/f"source_{block:06d}.npz";source=load(path);bodies=("B",)
    else:
        source=d.make_source(block);path=output/f"source_{block:06d}.npz"
        np.savez_compressed(path,**source);bodies=("A","B") if phase=="benchmark" else ("A",)
    source_hash=sha(path);frozen=utc();times={};starts={}
    for body in bodies:
        t=time.monotonic();starts[body]=utc()
        raw=d.read(source["repair_packets"],block,body,source["graph_neighbors"])
        np.savez_compressed(output/f"body_{body}_{block:06d}.npz",**raw)
        times[body]=time.monotonic()-t
    assert sha(path)==source_hash
    dump(output/f"worker_{block}.json",dict(block=block,phase=phase,seconds=time.monotonic()-started,
        source_file=str(path.relative_to(ROOT)),source_sha256=source_hash,source_frozen_utc=frozen,
        body_started_utc=starts,body_seconds=times))


def freeze_choices(output,ids,models_path,technical):
    x=[];wrong=[];a=[];h=[]
    for block in ids:
        source=load(output/f"source_{block:06d}.npz");raw=load(output/f"body_A_{block:06d}.npz")
        obs=d.observe(raw,source["prototype"])["observed"]
        actual,incorrect=d.features_pair(source,raw,obs)
        x.append(actual);wrong.append(incorrect);a.append(obs);h.append(source["repair_heuristic"])
    x=np.array(x);wrong=np.array(wrong);a=np.array(a)
    selected=d.select(x,wrong,a[:,:,4:,0]-a[:,:,4:,1],np.array(h),json.loads(models_path.read_text()))
    np.savez_compressed(output/"selections.npz",blocks=ids,features=x,wrong_features=wrong,observed_A=a,**selected)
    dump(output/"selection_freeze.json",dict(time=utc(),blocks=ids,policies=d.POLICIES,
        models_sha256=sha(models_path),model_file=str(models_path.relative_to(ROOT)),
        selections_sha256=sha(output/"selections.npz"),B_generated=technical,
        source_sha256={p.name:sha(p) for p in sorted(output.glob("source_*.npz"))},
        raw_A_sha256={p.name:sha(p) for p in sorted(output.glob("body_A_*.npz"))}))


def graph_descriptors(prediction,ids):
    rows=[]
    for block in ids:
        source=load(prediction/f"source_{block:06d}.npz")
        actual=set(map(tuple,source["graph_edges"].tolist()))
        wrong=set(map(tuple,source["wrong_graph_edges"].tolist()))
        native=set(map(tuple,source["graph_original_edges"].tolist()))
        rows.append(dict(block=block,wrong_seed=int(source["wrong_graph_seed"]),
            shared_edges=len(actual&wrong),shared_long_edges=len((actual-native)&(wrong-native)),
            identical_graphs=actual==wrong))
    return rows


def stats(x):return bootstrap(x,"E013:utility")


def csv_write(path,rows):
    with path.open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def evaluate(output,ids,prediction,technical):
    outcomes=[]
    for block in ids:
        source=load(prediction/f"source_{block:06d}.npz")
        outcomes.append(d.observe(load(output/f"body_B_{block:06d}.npz"),source["prototype"]))
    obs={key:np.array([item[key] for item in outcomes]) for key in outcomes[0]}
    np.savez_compressed(output/"evaluation_observations.npz",blocks=ids,**obs)
    b=obs["observed"];selected=load(prediction/"selections.npz");weights=selected["weights"]
    scores=np.einsum("bfpk,bfko->bfpo",weights,b[:,:,4:,:2])
    specificity=scores[:,:,:,0]-scores[:,:,:,1]
    utility=specificity-(b[:,:,1,0]-b[:,:,1,1])[:,:,None]
    target=b[:,:,4:,0]-b[:,:,4:,1]
    metrics=dict(utility=utility,specificity=specificity,own_agreement=scores[:,:,:,0],
        own_gain=scores[:,:,:,0]-b[:,:,1:2,0],hindsight_regret=target.max(axis=2)[:,:,None]-specificity)
    policies={name:{key:stats(v[:,:,j].mean(axis=1)) for key,v in metrics.items()}
              for j,name in enumerate(d.POLICIES)}
    comparisons={name:stats((utility[:,:,0]-utility[:,:,j]).mean(axis=1)) for j,name in enumerate(d.POLICIES) if j}
    gates={"graph_beats_"+name:st["ci95"][0]>0 for name,st in comparisons.items()}
    gates.update(graph_recovers_specificity=policies["graph"]["utility"]["ci95"][0]>0,
        graph_recovers_own_agreement=policies["graph"]["own_gain"]["ci95"][0]>0)
    choices=selected["choices"]
    agreement={a+"_"+b:float((choices[:,:,i]==choices[:,:,j]).mean())
        for i,a in enumerate(d.POLICIES[:-1]) for j,b in enumerate(d.POLICIES[:-1]) if j>i}
    rmse={name:float(np.sqrt(np.mean((selected["predicted"][:,:,j]-d.center_menu(target))**2)))
        for j,name in enumerate(d.PREDICTORS)}
    offsets={}
    for offset in (1,2,3):
        pair=np.stack([(obs["agreement"][:,f,:,:,f]-obs["agreement"][:,f,:,:,(f+offset)%4]).mean(axis=1)
                       for f in range(4)],axis=1)
        u=np.einsum("bfpk,bfk->bfp",weights,pair[:,:,4:])-pair[:,:,1:2]
        offsets[str(offset)]=dict(utility={name:stats(u[:,:,j].mean(axis=1)) for j,name in enumerate(d.POLICIES)},
            comparisons={name:stats((u[:,:,0]-u[:,:,j]).mean(axis=1)) for j,name in enumerate(d.POLICIES) if j})
    replication_gates={name:value for name,value in gates.items() if name!="graph_beats_wrong_graph"}
    replication_status="TECHNICAL_ONLY" if technical else "GRAPH_SELECTION_REPLICATED" if all(replication_gates.values()) else "GRAPH_SELECTION_NOT_REPLICATED"
    control_status="TECHNICAL_ONLY" if technical else "CORRECT_WIRING_ADVANTAGE" if gates["graph_beats_wrong_graph"] else "CORRECT_WIRING_ADVANTAGE_NOT_QUALIFIED"
    status="TECHNICAL_ONLY" if technical else "REPLICATION_AND_WIRING_QUALIFIED" if all(gates.values()) else "REPLICATION_AND_WIRING_NOT_QUALIFIED"
    summary=dict(experiment="E013",status=status,replication_status=replication_status,control_status=control_status,replication_gates=replication_gates,blocks=ids,founders=4*len(ids),recipients=8,
        policies=policies,comparisons=comparisons,gates=gates,choice_agreement=agreement,
        choice_frequency={name:np.bincount(choices[:,:,j].ravel(),minlength=8).tolist() for j,name in enumerate(d.POLICIES[:-1])},
        centered_prediction_rmse=rmse,native_minus_source=stats((utility[:,:,1]-utility[:,:,2]).mean(axis=1)),
        individual_foreign_offsets=offsets,B_mean_observations=b.mean(axis=(0,1)).tolist(),
        selections_sha256=sha(prediction/"selections.npz"),prediction_run=str(prediction.relative_to(ROOT)),
        primary_body="B",foreign_references_per_founder=3,external_backup=True,refit_on_fresh_data=False,
        cohort_filtered=False,restored_entries=64,injured_entries=192,menu_options=8,models_sha256=d.MODEL_SHA,wrong_graph_seed_offset=d.WRONG_OFFSET,
        target_body_uses_actual_graph=True,graph_descriptors=graph_descriptors(prediction,ids))
    dump(output/"summary.json",summary)
    rows=[];menu=[]
    for i,block in enumerate(ids):
        for f in range(4):
            for j,name in enumerate(d.POLICIES):
                rows.append(dict(block=block,founder=f,policy=name,choice=int(choices[i,f,j]) if j<len(d.POLICIES)-1 else "uniform",
                    **{key:float(v[i,f,j]) for key,v in metrics.items()}))
            for c,name in enumerate(d.CONDITIONS):
                row=dict(block=block,founder=f,condition=name)
                for body,values in (("A",selected["observed_A"]),("B",b)):
                    for k,key in enumerate(("own","foreign","resolved","neighbor")):row[body+"_"+key]=float(values[i,f,c,k])
                for j,policy in enumerate(d.PREDICTORS):row[policy+"_prediction"]=float(selected["predicted"][i,f,j,c-4]) if c>=4 else ""
                for j,policy in enumerate(d.POLICIES):row[policy+"_weight"]=float(weights[i,f,j,c-4]) if c>=4 else 0.
                menu.append(row)
    csv_write(output/"individual_policies.csv",rows);csv_write(output/"menu_outcomes.csv",menu)
    fmt=lambda st:f"{100*st['mean']:+.3f} [{100*st['ci95'][0]:+.3f}, {100*st['ci95'][1]:+.3f}]"
    lines=["# E013 — frozen replication and incorrect-wiring control","",f"**{status}**","",
        f"All {len(ids)} blocks / {4*len(ids)} founders retained; eight recipient futures and eight equal-budget options per founder.","",
        "Specificity = own agreement minus mean agreement with the other three founders. Recovery is relative to unrepaired. Values are percentage points with 95% whole-block bootstrap intervals.","",
        "| Policy | Specificity recovery | Own-agreement recovery | Gap to noisy hindsight best |",
        "| --- | --- | --- | --- |"]
    for name,st in policies.items():lines.append(f"| {name} | {fmt(st['utility'])} | {fmt(st['own_gain'])} | {fmt(st['hindsight_regret'])} |")
    lines += ["","| Graph minus comparator | Points [95%] |","| --- | --- |"]
    for name,st in comparisons.items():lines.append(f"| {name} | {fmt(st)} |")
    lines += ["",f"Original six-gate replication: **{replication_status}**. Incorrect-wiring control: **{control_status}**.","",
        f"Overall seven-gate conjunction: `{json.dumps(gates,sort_keys=True)}`.","",
        f"Native-model minus source choice: {fmt(summary['native_minus_source'])} points.","",
        "| Predictor | Centered target RMSE (points) |","| --- | --- |"]
    for name,value in rmse.items():lines.append(f"| {name} | {100*value:.3f} |")
    lines += ["",f"Choice agreement: `{json.dumps(agreement,sort_keys=True)}`.","",
        "Both E012 models, feature transforms and training scales were applied unchanged. There was no refit or pooling with E012. Choices were frozen and audited before any scientific B future. The incorrect-wiring policy uses the identical graph model, supplied one independent structurally matched graph; all outcomes are scored on the actual B graph. Native probes, prototypes and an external clean backup are supplied.","",
        "Secondary per-foreign-reference results, absolute scores, raw endpoints, full features and every candidate are retained in the JSON, NPZ and CSV files. Intervals are individual contrasts, not simultaneous bands. The noisy hindsight maximum is an optimistic diagnostic. A failed primary gate cannot be rescued by another observer or predictor metric.","",
        "This is one-read selection in related tissue models, with externally supplied sensing and repair. It does not establish autonomous repair, a complete graph predictor, optimality or independently active forms."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("benchmark","predict","evaluate"))
    p.add_argument("--output",type=Path,required=True);p.add_argument("--models",type=Path,default=d.MODEL_PATH)
    p.add_argument("--predictions",type=Path);p.add_argument("--workers",type=int,default=12)
    p.add_argument("--worker",type=int);args=p.parse_args();cap_cpus()
    args.output=args.output.resolve()
    assert args.output.is_relative_to(HERE) and 1<=args.workers<=12
    if args.models:args.models=args.models.resolve()
    if args.predictions:args.predictions=args.predictions.resolve()
    if args.worker is not None:worker(args.phase,args.worker,args.output,args.predictions);return
    assert args.models==d.MODEL_PATH and sha(args.models)==d.MODEL_SHA
    dependencies=dict(models=verify_run(args.models.parent,"develop"))
    if args.phase=="evaluate":
        assert args.predictions and args.predictions.is_relative_to(HERE)
        dependencies["predictions"]=verify_run(args.predictions,"predict")
        frozen=json.loads((args.predictions/"selection_freeze.json").read_text())
        assert not frozen["B_generated"] and not list(args.predictions.glob("body_B*"))
        assert frozen["models_sha256"]==sha(args.models) and frozen["blocks"]==list(d.IDS)
        assert frozen["selections_sha256"]==sha(args.predictions/"selections.npz")
    ids=list([d.BENCH_ID] if args.phase=="benchmark" else d.IDS)
    inputs=[ROOT/x for x in ("common.py","run_python.sh","SOURCE_SNAPSHOT.json","E001_unprescribed_capture/model.py",
        "E003_cross_embodiment/design.py","E008_rewired_transfer/design.py","E008_rewired_transfer/audit.py",
        "E009_repair_selection/design.py","E009_repair_selection/audit.py","E010_record_strength/design.py",
        "E012_graph_informed_repair/design.py","E012_graph_informed_repair/audit.py")]
    inputs += [HERE/x for x in ("design.py","run.py","audit.py","tests.py","PROTOCOL.md")]
    for dep in dependencies.values():
        inputs += [ROOT/dep["path"]/name for name in ("COMPLETE.json","INDEPENDENT_AUDIT.json")]
    if args.models:inputs.append(args.models)
    if args.predictions:inputs += [args.predictions/name for name in ("selections.npz","selection_freeze.json")]
    started=time.monotonic()
    output=new_run(args.output,inputs,dict(experiment="E013",phase=args.phase,blocks=ids,config=asdict(d.CFG),
        conditions=d.CONDITIONS,policies=d.POLICIES,workers=args.workers,dependencies=dependencies,
        feature_names=d.BASE_NAMES+d.GRAPH_NAMES,penalty=.01,primary_body="B",foreign_references_per_founder=3,
        injury_entries=192,restored_entries=64,menu_options=8,bootstrap_tag="E013:utility",models_sha256=d.MODEL_SHA,
        wrong_graph_seed_offset=d.WRONG_OFFSET,no_refit=True,target_body_uses_actual_graph=True))
    try:
        def launch(block):
            command=[sys.executable,"-B",str(HERE/"run.py"),args.phase,"--output",str(output),"--worker",str(block)]
            if args.predictions:command += ["--predictions",str(args.predictions)]
            with (output/f"worker_{block}.log").open("x") as log:
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for count,future in enumerate(as_completed([pool.submit(launch,b) for b in ids]),1):
                future.result()
                if count%16==0 or count==len(ids):print(f"Completed {args.phase}: {count}/{len(ids)} blocks",flush=True)
        if args.phase in ("benchmark","predict"):freeze_choices(output,ids,args.models,args.phase=="benchmark")
        if args.phase in ("benchmark","evaluate"):evaluate(output,ids,output if args.phase=="benchmark" else args.predictions,args.phase=="benchmark")
        for dep in dependencies.values():assert verify_run(ROOT/dep["path"],dep["phase"])==dep
        finish(output,started,dict(experiment="E013",phase=args.phase,blocks_completed=len(ids)))
        print("Complete:",output,flush=True)
    except BaseException:
        dump(output/"FAILED.json",dict(time=utc(),traceback=traceback.format_exc()));raise


if __name__=="__main__":main()
