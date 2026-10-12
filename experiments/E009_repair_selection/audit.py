"""Independent packet, selector and utility audit; no production imports."""
from pathlib import Path
from datetime import datetime
import argparse
import csv
import hashlib
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from E008_rewired_transfer import audit as previous
import numpy as np

POLICIES=("map","source","heuristic","random")
MODEL_SHA="c4dfd0030b5a22c48e0b78b3ad1781cf566f1f2be13549297dd6f8f8f7bca59f"
sha=previous.sha
read_json=previous.read_json


def seed(*parts):
    key=json.dumps(parts,separators=(",",":")).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little")))


def array_sha(x):return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def check_source(source,block):
    native,rewired,_=previous.inspect_graph(source)
    np.testing.assert_array_equal(source["prototype"],source["formation_late"].mean(axis=0))
    np.testing.assert_array_equal(source["acquired"],previous.encode(source["capture_end"][:,:,3]))
    assert not source["acquired"][:,1].any()
    clean=np.frombuffer(source["acquired"][:,0].tobytes(),dtype="<f8").reshape(4,256)
    packets=source["repair_packets"];assert packets.shape==(4,12,2048)
    assert source["repair_injury"].dtype==bool and source["repair_restoration"].dtype==bool
    for f in range(4):
        injured=source["repair_injury"][f];restored=source["repair_restoration"][f]
        assert injured.shape==(256,) and injured.sum()==192 and restored.shape==(8,256)
        assert (restored.sum(axis=1)==64).all() and not (restored&~injured).any()
        assert len({r.tobytes() for r in restored})==8
        sites=seed("E009",block,f,"injury").choice(256,192,replace=False)
        np.testing.assert_array_equal(np.flatnonzero(injured),np.sort(sites))
        strongest=sorted(sites,key=lambda i:(-abs(clean[f,i]),i))[:64]
        expected=[tuple(sorted(strongest))];random=seed("E009",block,f,"repair_candidates")
        for _ in range(100000):
            if len(expected)==8:break
            candidate=tuple(sorted(random.choice(sites,64,replace=False).tolist()))
            if candidate not in expected:expected.append(candidate)
        assert len(expected)==8
        order=seed("E009",block,f,"menu_order").permutation(8)
        assert int(source["repair_heuristic"][f])==int(np.flatnonzero(order==0)[0])
        for i,j in enumerate(order):
            np.testing.assert_array_equal(np.flatnonzero(restored[i]),expected[int(j)])
        fields=[]
        for c in range(12):
            field=clean[f].copy()
            if c==1:field[injured]=0
            elif c==2:field=clean[(f+1)%4].copy()
            elif c==3:field[:]=0
            elif c>=4:field[injured]=0;field[restored[c-4]]=clean[f,restored[c-4]]
            fields.append(field.reshape(16,16))
        np.testing.assert_array_equal(packets[f],previous.encode(np.array(fields)))
    for key in source.files:assert np.isfinite(source[key]).all(),key
    return native,rewired


def inspect_body(run,source_root,block,body):
    with np.load(source_root/f"source_{block:06d}.npz",allow_pickle=False) as source:
        native,rewired=check_source(source,block)
        prototype=source["prototype"];packets=source["repair_packets"]
    with np.load(run/f"body_{body}_{block:06d}.npz",allow_pickle=False) as raw:
        assert raw["end"].shape==(4,8,12,3,16,16)
        np.testing.assert_array_equal(raw["packets"],np.repeat(packets[:,None],8,axis=1))
        np.testing.assert_array_equal(raw["applied_neighbors"],native if body=="A" else rewired)
        birth=seed("E009",block,body,"birth").standard_normal((4,8,1,16,16))
        birth=.2*(birth-birth.mean(axis=(-2,-1),keepdims=True))
        np.testing.assert_array_equal(raw["birth"],birth)
        v=raw["end"][:,:,:,0];values=np.empty((4,8,12,4))
        assert (abs(v)<=2).all()
        for f in range(4):
            sign=v[f]>0;resolved=abs(v[f])>.2
            values[f,:,:,0]=(resolved&(sign==(prototype[f]>0))).mean(axis=(-2,-1))
            values[f,:,:,1]=(resolved&(sign==(prototype[(f+1)%4]>0))).mean(axis=(-2,-1))
            values[f,:,:,2]=resolved.mean(axis=(-2,-1))
            values[f,:,:,3]=((sign==np.roll(sign,1,-1)).mean(axis=(-2,-1))+(sign==np.roll(sign,1,-2)).mean(axis=(-2,-1)))/2
        for key in raw.files:assert np.isfinite(raw[key]).all(),key
    return prototype,values.mean(axis=1),values,birth


def audit_choices(run,ids,contract,technical):
    freeze=read_json(run/"selection_freeze.json")
    model=ROOT/freeze["model_development_run"]/"models.json"
    assert sha(model)==freeze["models_sha256"]==MODEL_SHA
    assert freeze["selections_sha256"]==sha(run/"selections.npz")
    assert freeze["blocks"]==ids and freeze["policies"]==list(POLICIES)
    assert freeze["conditions"]==contract["conditions"]
    assert freeze["B_generated"]==technical
    if not technical:assert not list(run.glob("body_B*"))
    for collection in ("source_sha256","raw_A_sha256"):
        assert len(freeze[collection])==len(ids)
        for rel,digest in freeze[collection].items():assert sha(run/rel)==digest
    m=read_json(model)["causal"]
    with np.load(run/"selections.npz",allow_pickle=False) as stored:
        assert stored["blocks"].tolist()==ids
        for i,block in enumerate(ids):
            p,a,_,_=inspect_body(run,run,block,"A")
            np.testing.assert_array_equal(a,stored["observed_A"][i])
            x=previous.features(p,a,contract["conditions"])["causal"]
            predicted=np.clip(x/np.array(m["scale"])@np.array(m["coefficients"]),-1,1)
            np.testing.assert_allclose(predicted,stored["predicted"][i],rtol=1e-12,atol=1e-13)
            np.testing.assert_array_equal(predicted[:,0],np.zeros((4,2)))
            with np.load(run/f"source_{block:06d}.npz",allow_pickle=False) as source:
                heuristic=source["repair_heuristic"]
                assert freeze["graph_sha256"][str(block)]==array_sha(source["graph_neighbors"].astype("<i8"))
                assert freeze["menu_sha256"][str(block)]==array_sha(source["repair_packets"])
            for f in range(4):
                margins=(predicted[f,4:,0]-predicted[f,4:,1]).tolist()
                a_margins=(a[f,4:,0]-a[f,4:,1]).tolist()
                choices=[margins.index(max(margins)),a_margins.index(max(a_margins)),int(heuristic[f])]
                np.testing.assert_array_equal(choices,stored["choices"][i,f])
                expected=np.zeros((4,8));expected[3,:]=.125
                for j,c in enumerate(choices):expected[j,c]=1.
                np.testing.assert_array_equal(expected,stored["weights"][i,f])
    start=datetime.fromisoformat(read_json(run/"manifest.json")["started_utc"])
    assert start<=datetime.fromisoformat(freeze["time"])<=datetime.fromisoformat(read_json(run/"COMPLETE.json")["finished_utc"])


def check_stats(values,stored,draws):
    values=np.asarray(values)
    np.testing.assert_allclose(values,stored["block_means"],rtol=0,atol=1e-15)
    assert abs(float(values.mean())-stored["mean"])<1e-15
    ci=np.quantile(values[draws].mean(axis=1),[.025,.975])
    np.testing.assert_allclose(ci,stored["ci95"],rtol=0,atol=1e-15)
    assert int((values>0).sum())==stored["positive_blocks"]
    return ci


def audit_evaluation(run,prediction,ids,contract,technical):
    if not technical:
        previous.verify(prediction)
        audit=read_json(prediction/"INDEPENDENT_AUDIT.json")
        assert audit["status"]=="PASS" and audit["complete_sha256"]==sha(prediction/"COMPLETE.json")
        assert datetime.fromisoformat(audit["finished_utc"])<datetime.fromisoformat(read_json(run/"manifest.json")["started_utc"])
        audit_choices(prediction,ids,read_json(prediction/"manifest.json")["contract"],False)
    observed=[]
    with np.load(run/"evaluation_observations.npz",allow_pickle=False) as saved:
        for i,block in enumerate(ids):
            _,b,individual,birth=inspect_body(run,prediction,block,"B")
            with np.load(prediction/f"body_A_{block:06d}.npz",allow_pickle=False) as a:
                assert not np.array_equal(birth,a["birth"])
            np.testing.assert_array_equal(saved["B"][i],b)
            np.testing.assert_array_equal(saved["individual_B"][i],individual)
            observed.append(b)
    b=np.array(observed);summary=read_json(run/"summary.json")
    with np.load(prediction/"selections.npz",allow_pickle=False) as f:selected=dict(f)
    scores=np.empty((len(ids),4,4,2))
    for i in range(len(ids)):
        for f in range(4):
            for j in range(3):scores[i,f,j]=b[i,f,4+int(selected["choices"][i,f,j]),:2]
            scores[i,f,3]=b[i,f,4:,:2].mean(axis=0)
    specificity=scores[:,:,:,0]-scores[:,:,:,1]
    unrepaired=b[:,:,1,0]-b[:,:,1,1]
    utility=specificity-unrepaired[:,:,None]
    metrics=dict(utility=utility,specificity=specificity,own_agreement=scores[:,:,:,0],
        own_gain=scores[:,:,:,0]-b[:,:,1:2,0],
        hindsight_regret=(b[:,:,4:,0]-b[:,:,4:,1]).max(axis=2)[:,:,None]-specificity)
    draws=seed("E009:utility","bootstrap").integers(0,len(ids),(10000,len(ids)))
    for j,name in enumerate(POLICIES):
        for key,values in metrics.items():check_stats(values[:,:,j].mean(axis=1),summary["policies"][name][key],draws)
    gates={}
    for j,name in enumerate(POLICIES[1:],1):
        ci=check_stats((utility[:,:,0]-utility[:,:,j]).mean(axis=1),summary["comparisons"][name],draws)
        gates["map_beats_"+name]=bool(ci[0]>0)
    gates["map_recovers_specificity"]=summary["policies"]["map"]["utility"]["ci95"][0]>0
    gates["map_recovers_own_agreement"]=summary["policies"]["map"]["own_gain"]["ci95"][0]>0
    assert gates==summary["gates"]
    status="TECHNICAL_ONLY" if technical else "REPAIR_SELECTION_QUALIFIED" if all(gates.values()) else "REPAIR_SELECTION_NOT_QUALIFIED"
    assert summary["status"]==status
    assert summary["blocks"]==ids and summary["founders"]==len(ids)*4 and summary["recipients"]==8
    assert summary["model_sha256"]==MODEL_SHA and summary["selections_sha256"]==sha(prediction/"selections.npz")
    np.testing.assert_array_equal(summary["B_mean_observations"],b.mean(axis=(0,1)))
    choices=selected["choices"]
    for j,name in enumerate(POLICIES[:3]):
        np.testing.assert_array_equal(np.bincount(choices[:,:,j].ravel(),minlength=8),summary["choice_frequency"][name])
    for i,a in enumerate(POLICIES[:3]):
        for j,c in enumerate(POLICIES[:3]):
            if j>i:assert summary["choice_agreement"][a+"_"+c]==float((choices[:,:,i]==choices[:,:,j]).mean())
    for body,obs in (("A",selected["observed_A"]),("B",b)):
        x=obs.mean(axis=1)
        deltas=dict(intact_minus_foreign_record=x[:,0,0]-x[:,2,0],
            intact_minus_erased_record=x[:,0,0]-x[:,3,0],intact_minus_unrepaired_own=x[:,0,0]-x[:,1,0])
        for i,c in enumerate(contract["conditions"][:4]):deltas[c["name"]+"_specificity"]=x[:,i,0]-x[:,i,1]
        for name,v in deltas.items():check_stats(v,summary["reference_contrasts"][body][name],draws)
    with (run/"individual_policies.csv").open() as f:
        seen=set()
        for row in csv.DictReader(f):
            i=ids.index(int(row["block"]));f=int(row["founder"]);j=POLICIES.index(row["policy"])
            assert (i,f,j) not in seen;seen.add((i,f,j))
            assert row["choice"]==(str(choices[i,f,j]) if j<3 else "uniform")
            assert float(row["unrepaired_specificity"])==unrepaired[i,f]
            for key,v in metrics.items():assert abs(float(row[key])-v[i,f,j])<1e-15
        assert len(seen)==len(ids)*4*4
    with (run/"menu_outcomes.csv").open() as f:
        seen=set()
        for row in csv.DictReader(f):
            i=ids.index(int(row["block"]));f=int(row["founder"])
            c=[x["name"] for x in contract["conditions"]].index(row["condition"])
            assert (i,f,c) not in seen;seen.add((i,f,c))
            for j,key in enumerate(("own","foreign")):assert float(row["predicted_"+key+"_change"])==selected["predicted"][i,f,c,j]
            for body,obs in (("A",selected["observed_A"]),("B",b)):
                for j,key in enumerate(("own","foreign","resolved","neighbor")):assert float(row[body+"_"+key])==obs[i,f,c,j]
            for j,name in enumerate(POLICIES):assert float(row[name+"_weight"])==(selected["weights"][i,f,j,c-4] if c>=4 else 0.)
        assert len(seen)==len(ids)*4*12


def main():
    parser=argparse.ArgumentParser();parser.add_argument("run",type=Path);args=parser.parse_args()
    run=args.run.resolve()
    if not run.is_relative_to(Path(__file__).resolve().parent):raise ValueError("Local E009 run required")
    if hasattr(os,"sched_getaffinity"):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    started=time.monotonic();manifest=previous.verify(run);contract=manifest["contract"]
    phase=contract["phase"];ids=contract["blocks"];technical=phase=="benchmark"
    assert ids==([900109] if technical else list(range(7000,7064)))
    assert contract["model_sha256"]==MODEL_SHA and not contract["model_refitting"]
    assert contract["injury_entries"]==192 and contract["restored_entries"]==64 and contract["menu_options"]==8
    for item in contract["dependencies"].values():
        dependency=ROOT/item["path"];previous.verify(dependency)
        assert sha(dependency/"COMPLETE.json")==item["complete_sha256"]
        assert sha(dependency/"INDEPENDENT_AUDIT.json")==item["audit_sha256"]
        receipt=read_json(dependency/"INDEPENDENT_AUDIT.json")
        assert receipt["status"]=="PASS" and receipt["complete_sha256"]==item["complete_sha256"]
        assert receipt["audit_code_sha256"]==sha(dependency.parent.parent/"audit.py")
        assert datetime.fromisoformat(read_json(dependency/"COMPLETE.json")["finished_utc"])<=datetime.fromisoformat(manifest["started_utc"])
    for block in ids:
        meta=read_json(run/f"worker_{block}.json")
        assert sha(ROOT/meta["source_file"])==meta["source_sha256"]
        with np.load(ROOT/meta["source_file"],allow_pickle=False) as source:
            assert meta["graph_sha256"]==array_sha(source["graph_neighbors"].astype("<i8"))
            assert meta["menu_sha256"]==array_sha(source["repair_packets"])
    if phase in ("predict","benchmark"):audit_choices(run,ids,contract,technical)
    if phase in ("evaluate","benchmark"):
        prediction=run if technical else ROOT/contract["dependencies"]["predictions"]["path"]
        audit_evaluation(run,prediction,ids,contract,technical)
    result=dict(status="PASS",phase=phase,blocks=len(ids),finished_utc=datetime.now().astimezone().isoformat(),
        equal_cost_menus_exact_backup_bytes_and_graphs_checked=True,
        observations_frozen_selectors_and_applicable_utilities_reproduced=True,
        all_applicable_csv_rows_checked=True,chronology_checked=not technical,
        complete_sha256=sha(run/"COMPLETE.json"),audit_code_sha256=sha(__file__),
        previous_audit_sha256=sha(previous.__file__),seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
