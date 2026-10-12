"""Independent raw scoring, spatial features, ridge, decisions and interval audit."""
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
import numpy as np

sha=old.sha
read_json=old.read_json
POLICIES=("graph","native","source","strongest","uniform")
CONDITIONS=("intact","unrepaired","foreign","erased",*(f"repair_{i}" for i in range(8)))


def close(a,b):np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)


def observe(raw,prototype):
    v=raw["end"][:,:,:,0];agreement=np.empty((4,8,12,4));individual=np.empty((4,8,12,4))
    for f in range(4):
        signs=v[f]>0;resolved=abs(v[f])>.2
        for t in range(4):agreement[f,:,:,t]=(resolved&(signs==(prototype[t]>0))).mean(axis=(-2,-1))
        individual[f,:,:,0]=agreement[f,:,:,f]
        individual[f,:,:,1]=sum(agreement[f,:,:,t] for t in range(4) if t!=f)/3
        individual[f,:,:,2]=resolved.mean(axis=(-2,-1))
        individual[f,:,:,3]=((signs==np.roll(signs,1,-1)).mean(axis=(-2,-1))+(signs==np.roll(signs,1,-2)).mean(axis=(-2,-1)))/2
    return dict(agreement=agreement,individual=individual,observed=individual.mean(axis=1))


def features(source,raw,a):
    original=set(map(tuple,source["graph_original_edges"].tolist()))
    native=[[] for _ in range(256)]
    for i,j in original:native[i].append(j);native[j].append(i)
    native=np.array([sorted(x) for x in native]);graph=source["graph_neighbors"]
    packet=np.frombuffer(source["repair_packets"].tobytes(),dtype="<f8").reshape(4,12,256)
    v=raw["end"][:,:,:,0].reshape(4,8,12,256)
    signs=np.where(source["prototype"].reshape(4,256)>0,1.,-1.)
    result=np.empty((4,8,23))
    for f in range(4):
        own=signs[f];foreign=sum(signs[t] for t in range(4) if t!=f)/3
        def soft(values):
            all_scores=[(1/(1+np.exp(-((values*signs[t]-.2)/.2)))).mean() for t in range(4)]
            return np.array([all_scores[f],sum(all_scores[t] for t in range(4) if t!=f)/3])
        for k in range(8):
            c=k+4;field=packet[f,c];state=v[f,:,c]
            nfield=field[native].mean(axis=1);bfield=field[graph].mean(axis=1)
            nv=state[:,native].mean(axis=2);bv=state[:,graph].mean(axis=2)
            delta=bv-nv;native_delta=nv-state
            native_delta-=native_delta.mean(axis=1,keepdims=True)
            centered_delta=delta-delta.mean(axis=1,keepdims=True)
            soft0=soft(state);soft_native=soft(state+.2*native_delta)-soft0
            soft_graph=soft(state+.2*centered_delta)-soft0
            result[f,k]=[*a[f,c],field.mean(),abs(field).mean(),np.sqrt((field**2).mean()),
                (field*own).mean(),(field*foreign).mean(),(field*nfield).mean(),*soft0,
                (state*nv).mean(),(nv*own).mean(),(nv*foreign).mean(),*soft_native,
                (field*(bfield-nfield)).mean(),(state*delta).mean(),(delta*own).mean(),
                (delta*foreign).mean(),*soft_graph]
    return result


def inspect_body(source,raw,block,body,native,graph):
    assert raw["end"].shape==(4,8,12,3,16,16)
    np.testing.assert_array_equal(raw["packets"],np.repeat(source["repair_packets"][:,None],8,axis=1))
    np.testing.assert_array_equal(raw["applied_neighbors"],native if body=="A" else graph)
    birth=old.seed("E009",block,body,"birth").standard_normal((4,8,1,16,16))
    birth=.2*(birth-birth.mean(axis=(-2,-1),keepdims=True))
    np.testing.assert_array_equal(raw["birth"],birth)
    for name in raw.files:assert np.isfinite(raw[name]).all(),name
    assert (abs(raw["end"][:,:,:,0])<=2).all()
    return observe(raw,source["prototype"])


def dependencies(contract,started):
    for dep in contract["dependencies"].values():
        path=ROOT/dep["path"]
        old.previous.verify(path)
        assert not (path/"FAILED.json").exists()
        assert sha(path/"COMPLETE.json")==dep["complete_sha256"]
        assert sha(path/"INDEPENDENT_AUDIT.json")==dep["audit_sha256"]
        receipt=read_json(path/"INDEPENDENT_AUDIT.json")
        assert receipt["status"]=="PASS" and receipt["complete_sha256"]==sha(path/"COMPLETE.json")
        assert receipt["audit_code_sha256"]==sha(path.parent.parent/"audit.py")
        assert datetime.fromisoformat(receipt["finished_utc"])<datetime.fromisoformat(started)


def centered(x):return x-x.mean(axis=2,keepdims=True)


def audit_development(run,ids):
    frozen=read_json(run/"model_freeze.json");models=read_json(run/"models.json")
    assert frozen["models_sha256"]==sha(run/"models.json") and frozen["rows_sha256"]==sha(run/"fit_rows.npz")
    assert not frozen["fresh_B_generated"] and frozen["development_blocks"]==ids and frozen["penalty"]==.01
    x=[];a=[];b=[];receipts={}
    source_root=ROOT/"E009_repair_selection/runs/prediction_v1"
    target_root=ROOT/"E009_repair_selection/runs/evaluation_v1"
    with np.load(run/"fit_rows.npz",allow_pickle=False) as saved:
        assert saved["blocks"].tolist()==ids
        for i,block in enumerate(ids):
            paths=[source_root/f"source_{block:06d}.npz",source_root/f"body_A_{block:06d}.npz",target_root/f"body_B_{block:06d}.npz"]
            with np.load(paths[0],allow_pickle=False) as source:
                native,graph=old.check_source(source,block)
                with np.load(paths[1],allow_pickle=False) as raw:
                    oa=inspect_body(source,raw,block,"A",native,graph)["observed"]
                    feat=features(source,raw,oa)
                with np.load(paths[2],allow_pickle=False) as raw:ob=inspect_body(source,raw,block,"B",native,graph)["observed"]
            close(feat,saved["features"][i]);close(oa,saved["observed_A"][i]);close(ob,saved["observed_B"][i])
            x.append(feat);a.append(oa);b.append(ob)
            receipts.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
        assert receipts==frozen["development_inputs_sha256"]
        x=np.array(x);a=np.array(a);b=np.array(b)
        a_spec=a[:,:,4:,0]-a[:,:,4:,1];b_spec=b[:,:,4:,0]-b[:,:,4:,1]
        y=centered(b_spec-a_spec);close(y,saved["residual"])
        predictions=[]
        for name,count in (("graph",23),("native",17)):
            rows=centered(x)[...,:count].reshape(-1,count);m=models[name]
            scale=np.sqrt(np.mean(rows**2,axis=0));scale[scale<1e-12]=1.
            z=rows/scale;beta=np.linalg.solve(z.T@z+.01*len(z)*np.eye(count),z.T@y.ravel())
            close(m["scale"],scale);close(m["coefficients"],beta)
            assert m["penalty"]==.01 and m["rows"]==2048
            predictions.append(centered(a_spec)+(centered(x)[...,:count]/scale)@beta)
        predictions=np.stack((*predictions,centered(a_spec)),axis=2)
        close(predictions,saved["predicted"])
    summary=read_json(run/"summary.json")
    assert summary["status"]=="DEVELOPMENT_ONLY" and not summary["search_performed"] and summary["fit_rows"]==2048
    for j,name in enumerate(POLICIES[:3]):close(summary["in_sample_centered_rmse"][name],np.sqrt(np.mean((predictions[:,:,j]-centered(b_spec))**2)))


def audit_choices(run,ids,technical):
    freeze=read_json(run/"selection_freeze.json");models_path=ROOT/freeze["model_file"]
    assert sha(models_path)==freeze["models_sha256"] and sha(run/"selections.npz")==freeze["selections_sha256"]
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
                native,graph=old.check_source(source,block);heuristic=source["repair_heuristic"].copy()
                with np.load(run/f"body_A_{block:06d}.npz",allow_pickle=False) as raw:
                    a=inspect_body(source,raw,block,"A",native,graph)["observed"]
                    x=features(source,raw,a)
            close(x,saved["features"][i]);close(a,saved["observed_A"][i])
            x=x-x.mean(axis=1,keepdims=True);spec=a[:,4:,0]-a[:,4:,1];spec-=spec.mean(axis=1,keepdims=True)
            expected=[]
            for name,columns in (("graph",23),("native",17)):
                m=models[name];expected.append(spec+(x[...,:columns]/np.array(m["scale"]))@np.array(m["coefficients"]))
            expected=np.stack((*expected,spec),axis=1)
            close(expected,saved["predicted"][i])
            choices=np.column_stack((expected.argmax(axis=2),heuristic))
            np.testing.assert_array_equal(choices,saved["choices"][i])
            weights=np.zeros((4,5,8));weights[:,4]=.125
            for f in range(4):
                for j in range(4):weights[f,j,choices[f,j]]=1.
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
                native,graph=old.check_source(source,block)
                with np.load(run/f"body_B_{block:06d}.npz",allow_pickle=False) as raw:
                    values=inspect_body(source,raw,block,"B",native,graph);birth=raw["birth"]
            with np.load(prediction/f"body_A_{block:06d}.npz",allow_pickle=False) as raw:assert not np.array_equal(birth,raw["birth"])
            for key,value in values.items():close(value,saved[key][i])
            obs.append(values["observed"]);all_agreement.append(values["agreement"])
    b=np.array(obs);all_agreement=np.array(all_agreement)
    with np.load(prediction/"selections.npz",allow_pickle=False) as f:selection=dict(f)
    chosen=np.empty((len(ids),4,5,2));choices=selection["choices"]
    for i in range(len(ids)):
        for f in range(4):
            for j in range(4):chosen[i,f,j]=b[i,f,4+choices[i,f,j],:2]
            chosen[i,f,4]=b[i,f,4:,:2].mean(axis=0)
    spec=chosen[:,:,:,0]-chosen[:,:,:,1]
    utility=spec-(b[:,:,1,0]-b[:,:,1,1])[:,:,None]
    target=b[:,:,4:,0]-b[:,:,4:,1]
    metrics=dict(utility=utility,specificity=spec,own_agreement=chosen[:,:,:,0],
        own_gain=chosen[:,:,:,0]-b[:,:,1:2,0],hindsight_regret=target.max(axis=2)[:,:,None]-spec)
    draws=old.seed("E012:utility","bootstrap").integers(0,len(ids),(10000,len(ids)))
    summary=read_json(run/"summary.json");gates={}
    for j,name in enumerate(POLICIES):
        for key,value in metrics.items():check_stats(value[:,:,j].mean(axis=1),summary["policies"][name][key],draws)
        if j:
            ci=check_stats((utility[:,:,0]-utility[:,:,j]).mean(axis=1),summary["comparisons"][name],draws)
            gates["graph_beats_"+name]=bool(ci[0]>0)
        if j<4:
            assert np.bincount(choices[:,:,j].ravel(),minlength=8).tolist()==summary["choice_frequency"][name]
        if j<3:close(np.sqrt(np.mean((selection["predicted"][:,:,j]-centered(target))**2)),summary["centered_prediction_rmse"][name])
    check_stats((utility[:,:,1]-utility[:,:,2]).mean(axis=1),summary["native_minus_source"],draws)
    gates.update(graph_recovers_specificity=summary["policies"]["graph"]["utility"]["ci95"][0]>0,
                 graph_recovers_own_agreement=summary["policies"]["graph"]["own_gain"]["ci95"][0]>0)
    assert gates==summary["gates"]
    expected="TECHNICAL_ONLY" if technical else "GRAPH_SELECTION_QUALIFIED" if all(gates.values()) else "GRAPH_SELECTION_NOT_QUALIFIED"
    assert summary["status"]==expected and summary["blocks"]==ids and summary["founders"]==4*len(ids)
    assert summary["recipients"]==8 and summary["foreign_references_per_founder"]==3 and summary["primary_body"]=="B"
    assert summary["external_backup"] and not summary["refit_on_fresh_data"] and not summary["cohort_filtered"]
    assert summary["restored_entries"]==64 and summary["injured_entries"]==192 and summary["menu_options"]==8
    assert summary["selections_sha256"]==sha(prediction/"selections.npz")
    close(b.mean(axis=(0,1)),summary["B_mean_observations"])
    agreements={a+"_"+b:float((choices[:,:,i]==choices[:,:,j]).mean()) for i,a in enumerate(POLICIES[:4]) for j,b in enumerate(POLICIES[:4]) if j>i}
    assert agreements==summary["choice_agreement"]
    for offset in (1,2,3):
        pair=np.empty((len(ids),4,12))
        for f in range(4):pair[:,f]=(all_agreement[:,f,:,:,f]-all_agreement[:,f,:,:,(f+offset)%4]).mean(axis=1)
        u=np.empty((len(ids),4,5))
        for i in range(len(ids)):
            for f in range(4):
                for j in range(4):u[i,f,j]=pair[i,f,4+choices[i,f,j]]-pair[i,f,1]
                u[i,f,4]=pair[i,f,4:].mean()-pair[i,f,1]
        st=summary["individual_foreign_offsets"][str(offset)]
        for j,name in enumerate(POLICIES):
            check_stats(u[:,:,j].mean(axis=1),st["utility"][name],draws)
            if j:check_stats((u[:,:,0]-u[:,:,j]).mean(axis=1),st["comparisons"][name],draws)
    with (run/"individual_policies.csv").open() as file:
        seen=set()
        for row in csv.DictReader(file):
            i=ids.index(int(row["block"]));f=int(row["founder"]);j=POLICIES.index(row["policy"])
            assert (i,f,j) not in seen;seen.add((i,f,j))
            assert row["choice"]==("uniform" if j==4 else str(choices[i,f,j]))
            for key,v in metrics.items():close(float(row[key]),v[i,f,j])
        assert len(seen)==len(ids)*4*5
    with (run/"menu_outcomes.csv").open() as file:
        seen=set()
        for row in csv.DictReader(file):
            i=ids.index(int(row["block"]));f=int(row["founder"]);c=CONDITIONS.index(row["condition"])
            assert (i,f,c) not in seen;seen.add((i,f,c))
            for body,values in (("A",selection["observed_A"]),("B",b)):
                for j,key in enumerate(("own","foreign","resolved","neighbor")):close(float(row[body+"_"+key]),values[i,f,c,j])
            for j,name in enumerate(POLICIES[:3]):
                if c>=4:close(float(row[name+"_prediction"]),selection["predicted"][i,f,j,c-4])
                else:assert row[name+"_prediction"]==""
            for j,name in enumerate(POLICIES):close(float(row[name+"_weight"]),selection["weights"][i,f,j,c-4] if c>=4 else 0.)
        assert len(seen)==len(ids)*4*12


def audit(run):
    manifest=old.previous.verify(run);assert not (run/"FAILED.json").exists()
    contract=manifest["contract"];phase=contract["phase"];ids=contract["blocks"]
    assert ids==(list(range(7000,7064)) if phase=="develop" else [900412] if phase=="benchmark" else list(range(10000,10064)))
    assert contract["policies"]==list(POLICIES) and contract["conditions"]==list(CONDITIONS)
    assert contract["penalty"]==.01 and len(contract["feature_names"])==23
    assert contract["primary_body"]=="B" and contract["foreign_references_per_founder"]==3
    assert contract["injury_entries"]==192 and contract["restored_entries"]==64 and contract["menu_options"]==8
    assert contract["bootstrap_tag"]=="E012:utility"
    dependencies(contract,manifest["started_utc"])
    if phase=="develop":audit_development(run,ids)
    else:
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
        raw_scoring_features_fits_choices_and_applicable_intervals_checked=True,seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
