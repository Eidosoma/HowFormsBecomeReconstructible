"""Independent E013 audit, including replay of the decoy graph random stream."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import csv
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from E009_repair_selection import audit as old
from E012_graph_informed_repair import audit as e012
import numpy as np

sha=old.sha
read_json=old.read_json
POLICIES=("graph","native","source","strongest","wrong_graph","uniform")
PREDICTORS=("graph","native","source","wrong_graph")
MODEL_SHA="259d4b401ca4bddc2f4c98dcfe64692018f3928c12d6f578114a7ffdced5d922"
CONDITIONS=("intact","unrepaired","foreign","erased",*(f"repair_{i}" for i in range(8)))


def close(a,b):np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)


observe=e012.observe
features=e012.features
inspect_body=e012.inspect_body
dependencies=e012.dependencies
centered=e012.centered


def replay_wrong_graph(block):
    edges=set()
    for i in range(256):
        y,x=divmod(i,16)
        for j in (16*((y+1)%16)+x,16*y+(x+1)%16):edges.add(tuple(sorted((i,j))))
    available=sorted(edges);random=old.seed("E008",1000000+block,"rewiring")
    swaps=[];attempts=0
    def distance(a,b):
        ay,ax=divmod(a,16);by,bx=divmod(b,16)
        return min(abs(ay-by),16-abs(ay-by))+min(abs(ax-bx),16-abs(ax-bx))
    while len(swaps)<64:
        attempts+=1
        if attempts>100000:raise AssertionError("Decoy replay proposal limit exceeded")
        first,second=[available[int(k)] for k in random.choice(len(available),2,replace=False)]
        a,b=first;c,d=second;flip=bool(random.integers(0,2))
        if len({a,b,c,d})!=4:continue
        added=tuple(tuple(sorted(e)) for e in (((a,d),(b,c)) if flip else ((a,c),(b,d))))
        if any(e in edges or distance(*e)<4 for e in added):continue
        trial=edges-{first,second}|set(added)
        adjacency=[[] for _ in range(256)]
        for i,j in trial:adjacency[i].append(j);adjacency[j].append(i)
        seen={0};pending=[0]
        while pending:
            for j in adjacency[pending.pop()]:
                if j not in seen:seen.add(j);pending.append(j)
        if len(seen)!=256:continue
        edges=trial;swaps.append((first,second,*added))
        available=[e for e in available if e not in (first,second)]
    return np.array(sorted(edges)),np.array(swaps),attempts


def check_source(source,block):
    native,graph=old.check_source(source,block)
    wrong={key[6:]:source[key] for key in source.files if key.startswith("wrong_graph_")}
    _,wrong_neighbors,_=old.previous.inspect_graph(wrong)
    assert int(source["wrong_graph_seed"])==1000000+block
    edges,swaps,attempts=replay_wrong_graph(block)
    np.testing.assert_array_equal(source["wrong_graph_edges"],edges)
    np.testing.assert_array_equal(source["wrong_graph_swaps"],swaps)
    assert int(source["wrong_graph_attempts"])==attempts
    np.testing.assert_array_equal(source["wrong_graph_neighbors"],wrong_neighbors)
    return native,graph


def audit_choices(run,ids,technical):
    freeze=read_json(run/"selection_freeze.json");models_path=ROOT/freeze["model_file"]
    assert sha(models_path)==freeze["models_sha256"]==MODEL_SHA and sha(run/"selections.npz")==freeze["selections_sha256"]
    assert freeze["blocks"]==ids and freeze["policies"]==list(POLICIES) and freeze["B_generated"]==technical
    if not technical:assert not list(run.glob("body_B*"))
    for collection in ("source_sha256","raw_A_sha256"):
        assert len(freeze[collection])==len(ids)
        for name,digest in freeze[collection].items():assert sha(run/name)==digest
    models=read_json(models_path)
    with np.load(run/"selections.npz",allow_pickle=False) as saved:
        assert saved["blocks"].tolist()==ids
        for i,block in enumerate(ids):
            with np.load(run/f"source_{block:06d}.npz",allow_pickle=False) as source:
                native,graph=check_source(source,block);heuristic=source["repair_heuristic"].copy()
                with np.load(run/f"body_A_{block:06d}.npz",allow_pickle=False) as raw:
                    a=inspect_body(source,raw,block,"A",native,graph)["observed"]
                    x=features(source,raw,a)
                    substitute=dict(source);substitute["graph_neighbors"]=source["wrong_graph_neighbors"]
                    wrong=features(substitute,raw,a)
            close(x,saved["features"][i]);close(wrong,saved["wrong_features"][i]);close(a,saved["observed_A"][i])
            np.testing.assert_array_equal(saved["features"][i,...,:17],saved["wrong_features"][i,...,:17])
            wrong=wrong-wrong.mean(axis=1,keepdims=True)
            x=x-x.mean(axis=1,keepdims=True);spec=a[:,4:,0]-a[:,4:,1];spec-=spec.mean(axis=1,keepdims=True)
            expected=[]
            for name,columns in (("graph",23),("native",17)):
                m=models[name];expected.append(spec+(x[...,:columns]/np.array(m["scale"]))@np.array(m["coefficients"]))
            m=models["graph"];incorrect=spec+(wrong/np.array(m["scale"]))@np.array(m["coefficients"])
            expected=np.stack((*expected,spec,incorrect),axis=1)
            close(expected,saved["predicted"][i])
            choices=np.column_stack((expected[:,:3].argmax(axis=2),heuristic,expected[:,3].argmax(axis=1)))
            np.testing.assert_array_equal(choices,saved["choices"][i])
            weights=np.zeros((4,6,8));weights[:,5]=.125
            for f in range(4):
                for j in range(5):weights[f,j,choices[f,j]]=1.
            np.testing.assert_array_equal(weights,saved["weights"][i])
    start=read_json(run/"manifest.json")["started_utc"];end=read_json(run/"COMPLETE.json")["finished_utc"]
    assert datetime.fromisoformat(start)<=datetime.fromisoformat(freeze["time"])<=datetime.fromisoformat(end)


def check_stats(values,saved,draws):
    close(values,saved["block_means"]);close(np.mean(values),saved["mean"])
    ci=np.quantile(values[draws].mean(axis=1),[.025,.975]);close(ci,saved["ci95"])
    assert int((np.array(saved["block_means"])>0).sum())==saved["positive_blocks"]
    assert np.all((np.sign(values)==np.sign(saved["block_means"]))|((abs(values)<1e-12)&(abs(np.array(saved["block_means"]))<1e-12)))
    return ci


def audit_evaluation(run,prediction,ids,technical):
    audit_choices(prediction,ids,technical)
    if not technical:
        before=read_json(prediction/"INDEPENDENT_AUDIT.json")["finished_utc"]
        assert datetime.fromisoformat(before)<datetime.fromisoformat(read_json(run/"manifest.json")["started_utc"])
    obs=[];all_agreement=[]
    with np.load(run/"evaluation_observations.npz",allow_pickle=False) as saved:
        assert saved["blocks"].tolist()==ids
        for i,block in enumerate(ids):
            with np.load(prediction/f"source_{block:06d}.npz",allow_pickle=False) as source:
                native,graph=check_source(source,block)
                with np.load(run/f"body_B_{block:06d}.npz",allow_pickle=False) as raw:
                    values=inspect_body(source,raw,block,"B",native,graph);birth=raw["birth"]
            with np.load(prediction/f"body_A_{block:06d}.npz",allow_pickle=False) as raw:assert not np.array_equal(birth,raw["birth"])
            for key,value in values.items():close(value,saved[key][i])
            obs.append(values["observed"]);all_agreement.append(values["agreement"])
    b=np.array(obs);all_agreement=np.array(all_agreement)
    with np.load(prediction/"selections.npz",allow_pickle=False) as f:selection=dict(f)
    chosen=np.empty((len(ids),4,6,2));choices=selection["choices"]
    for i in range(len(ids)):
        for f in range(4):
            for j in range(5):chosen[i,f,j]=b[i,f,4+choices[i,f,j],:2]
            chosen[i,f,5]=b[i,f,4:,:2].mean(axis=0)
    spec=chosen[:,:,:,0]-chosen[:,:,:,1]
    utility=spec-(b[:,:,1,0]-b[:,:,1,1])[:,:,None]
    target=b[:,:,4:,0]-b[:,:,4:,1]
    metrics=dict(utility=utility,specificity=spec,own_agreement=chosen[:,:,:,0],
        own_gain=chosen[:,:,:,0]-b[:,:,1:2,0],hindsight_regret=target.max(axis=2)[:,:,None]-spec)
    draws=old.seed("E013:utility","bootstrap").integers(0,len(ids),(10000,len(ids)))
    summary=read_json(run/"summary.json");gates={}
    for j,name in enumerate(POLICIES):
        for key,value in metrics.items():check_stats(value[:,:,j].mean(axis=1),summary["policies"][name][key],draws)
        if j:
            ci=check_stats((utility[:,:,0]-utility[:,:,j]).mean(axis=1),summary["comparisons"][name],draws)
            gates["graph_beats_"+name]=bool(ci[0]>0)
        if j<5:
            assert np.bincount(choices[:,:,j].ravel(),minlength=8).tolist()==summary["choice_frequency"][name]
        if name in PREDICTORS:close(np.sqrt(np.mean((selection["predicted"][:,:,PREDICTORS.index(name)]-centered(target))**2)),summary["centered_prediction_rmse"][name])
    check_stats((utility[:,:,1]-utility[:,:,2]).mean(axis=1),summary["native_minus_source"],draws)
    gates.update(graph_recovers_specificity=summary["policies"]["graph"]["utility"]["ci95"][0]>0,
                 graph_recovers_own_agreement=summary["policies"]["graph"]["own_gain"]["ci95"][0]>0)
    assert gates==summary["gates"]
    replication={name:value for name,value in gates.items() if name!="graph_beats_wrong_graph"}
    assert replication==summary["replication_gates"]
    assert summary["replication_status"]==("TECHNICAL_ONLY" if technical else "GRAPH_SELECTION_REPLICATED" if all(replication.values()) else "GRAPH_SELECTION_NOT_REPLICATED")
    assert summary["control_status"]==("TECHNICAL_ONLY" if technical else "CORRECT_WIRING_ADVANTAGE" if gates["graph_beats_wrong_graph"] else "CORRECT_WIRING_ADVANTAGE_NOT_QUALIFIED")
    assert summary["models_sha256"]==MODEL_SHA and summary["wrong_graph_seed_offset"]==1000000
    assert summary["target_body_uses_actual_graph"]
    expected="TECHNICAL_ONLY" if technical else "REPLICATION_AND_WIRING_QUALIFIED" if all(gates.values()) else "REPLICATION_AND_WIRING_NOT_QUALIFIED"
    assert summary["status"]==expected and summary["blocks"]==ids and summary["founders"]==4*len(ids)
    assert summary["recipients"]==8 and summary["foreign_references_per_founder"]==3 and summary["primary_body"]=="B"
    assert summary["external_backup"] and not summary["refit_on_fresh_data"] and not summary["cohort_filtered"]
    assert summary["restored_entries"]==64 and summary["injured_entries"]==192 and summary["menu_options"]==8
    assert summary["selections_sha256"]==sha(prediction/"selections.npz")
    close(b.mean(axis=(0,1)),summary["B_mean_observations"])
    descriptors=[]
    for block in ids:
        with np.load(prediction/f"source_{block:06d}.npz",allow_pickle=False) as source:
            actual=set(map(tuple,source["graph_edges"].tolist()))
            wrong=set(map(tuple,source["wrong_graph_edges"].tolist()))
            native=set(map(tuple,source["graph_original_edges"].tolist()))
            descriptors.append(dict(block=block,wrong_seed=1000000+block,shared_edges=len(actual&wrong),
                shared_long_edges=len((actual-native)&(wrong-native)),identical_graphs=actual==wrong))
    assert descriptors==summary["graph_descriptors"]
    agreements={a+"_"+b:float((choices[:,:,i]==choices[:,:,j]).mean()) for i,a in enumerate(POLICIES[:-1]) for j,b in enumerate(POLICIES[:-1]) if j>i}
    assert agreements==summary["choice_agreement"]
    for offset in (1,2,3):
        pair=np.empty((len(ids),4,12))
        for f in range(4):pair[:,f]=(all_agreement[:,f,:,:,f]-all_agreement[:,f,:,:,(f+offset)%4]).mean(axis=1)
        u=np.empty((len(ids),4,6))
        for i in range(len(ids)):
            for f in range(4):
                for j in range(5):u[i,f,j]=pair[i,f,4+choices[i,f,j]]-pair[i,f,1]
                u[i,f,5]=pair[i,f,4:].mean()-pair[i,f,1]
        st=summary["individual_foreign_offsets"][str(offset)]
        for j,name in enumerate(POLICIES):
            check_stats(u[:,:,j].mean(axis=1),st["utility"][name],draws)
            if j:check_stats((u[:,:,0]-u[:,:,j]).mean(axis=1),st["comparisons"][name],draws)
    with (run/"individual_policies.csv").open() as file:
        seen=set()
        for row in csv.DictReader(file):
            i=ids.index(int(row["block"]));f=int(row["founder"]);j=POLICIES.index(row["policy"])
            assert (i,f,j) not in seen;seen.add((i,f,j))
            assert row["choice"]==("uniform" if j==5 else str(choices[i,f,j]))
            for key,v in metrics.items():close(float(row[key]),v[i,f,j])
        assert len(seen)==len(ids)*4*6
    with (run/"menu_outcomes.csv").open() as file:
        seen=set()
        for row in csv.DictReader(file):
            i=ids.index(int(row["block"]));f=int(row["founder"]);c=CONDITIONS.index(row["condition"])
            assert (i,f,c) not in seen;seen.add((i,f,c))
            for body,values in (("A",selection["observed_A"]),("B",b)):
                for j,key in enumerate(("own","foreign","resolved","neighbor")):close(float(row[body+"_"+key]),values[i,f,c,j])
            for j,name in enumerate(PREDICTORS):
                if c>=4:close(float(row[name+"_prediction"]),selection["predicted"][i,f,j,c-4])
                else:assert row[name+"_prediction"]==""
            for j,name in enumerate(POLICIES):close(float(row[name+"_weight"]),selection["weights"][i,f,j,c-4] if c>=4 else 0.)
        assert len(seen)==len(ids)*4*12


def audit(run):
    manifest=old.previous.verify(run);assert not (run/"FAILED.json").exists()
    contract=manifest["contract"];phase=contract["phase"];ids=contract["blocks"]
    assert ids==([900513] if phase=="benchmark" else list(range(11000,11128)))
    assert contract["policies"]==list(POLICIES) and contract["conditions"]==list(CONDITIONS)
    assert contract["penalty"]==.01 and len(contract["feature_names"])==23
    assert contract["primary_body"]=="B" and contract["foreign_references_per_founder"]==3
    assert contract["injury_entries"]==192 and contract["restored_entries"]==64 and contract["menu_options"]==8
    assert contract["bootstrap_tag"]=="E013:utility"
    assert contract["models_sha256"]==MODEL_SHA and contract["wrong_graph_seed_offset"]==1000000
    assert contract["no_refit"] and contract["target_body_uses_actual_graph"]
    dependencies(contract,manifest["started_utc"])
    source_root=ROOT/contract["dependencies"]["predictions"]["path"] if phase=="evaluate" else run
    for block in ids:
        worker=read_json(run/f"worker_{block}.json")
        assert worker["source_sha256"]==sha(source_root/f"source_{block:06d}.npz")
        assert worker["phase"]==phase and worker["block"]==block
        for when in worker["body_started_utc"].values():
            assert datetime.fromisoformat(manifest["started_utc"])<=datetime.fromisoformat(worker["source_frozen_utc"])<=datetime.fromisoformat(when)
    if phase=="predict":audit_choices(run,ids,False)
    else:audit_evaluation(run,source_root,ids,phase=="benchmark")
    return contract


def main():
    p=argparse.ArgumentParser();p.add_argument("run",type=Path);args=p.parse_args();run=args.run.resolve()
    assert run.is_relative_to(Path(__file__).resolve().parent)
    if hasattr(os,"sched_getaffinity"):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    started=time.monotonic();contract=audit(run)
    result=dict(status="PASS",phase=contract["phase"],blocks=len(contract["blocks"]),
        finished_utc=datetime.now(timezone.utc).isoformat(),complete_sha256=sha(run/"COMPLETE.json"),
        audit_code_sha256=sha(__file__),previous_audit_sha256=sha(old.__file__),
        raw_scoring_features_frozen_models_choices_and_applicable_intervals_checked=True,
        incorrect_graph_seed_replayed=True,e012_audit_sha256=sha(e012.__file__),seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
