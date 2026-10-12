"""Independent restoration, all-foreign scoring and inference audit."""
from pathlib import Path
from datetime import datetime,timezone
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

POLICIES=("weak","strong","random")
CONDITIONS=("intact","unrepaired","erased","foreign_1","foreign_2","foreign_3",*POLICIES)
sha=previous.sha
read_json=previous.read_json


def seed(*parts):
    key=json.dumps(parts,separators=(",",":")).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little")))


def array_sha(x):return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def close(a,b):np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)


def inspect_source(source,block):
    native,rewired,_=previous.inspect_graph(source)
    np.testing.assert_array_equal(source["prototype"],source["formation_late"].mean(axis=0))
    np.testing.assert_array_equal(source["acquired"],previous.encode(source["capture_end"][:,:,3]))
    assert not source["acquired"][:,1].any()
    clean=np.frombuffer(source["acquired"][:,0].tobytes(),dtype="<f8").reshape(4,256)
    prototype=source["prototype"].reshape(4,256)>0
    injury=source["repair_injury"];restore=source["repair_restoration"]
    assert injury.dtype==bool and restore.dtype==bool
    assert injury.shape==(4,256) and restore.shape==(4,3,256)
    assert (injury.sum(axis=1)==192).all() and (restore.sum(axis=2)==64).all()
    assert not (restore&~injury[:,None]).any()
    magnitude=np.empty((4,3));distinction=np.empty((4,3,3))
    fields=np.empty((4,9,16,16))
    for f in range(4):
        sites=seed("E010",block,f,"injury").choice(256,192,replace=False)
        np.testing.assert_array_equal(np.flatnonzero(injury[f]),np.sort(sites))
        ordered_low=sorted(sites,key=lambda k:(abs(clean[f,k]),k))[:64]
        ordered_high=sorted(sites,key=lambda k:(-abs(clean[f,k]),k))[:64]
        random=seed("E010",block,f,"random_repair").choice(sites,64,replace=False)
        for j,subset in enumerate((ordered_low,ordered_high,random)):
            np.testing.assert_array_equal(np.flatnonzero(restore[f,j]),sorted(subset))
            selected=np.flatnonzero(restore[f,j])
            magnitude[f,j]=sum(abs(clean[f,k]) for k in selected)
            for offset in (1,2,3):
                distinction[f,j,offset-1]=sum(bool(prototype[f,k]!=prototype[(f+offset)%4,k]) for k in selected)/64
        for c in range(9):
            value=clean[f].copy()
            if c==1:value[injury[f]]=0.
            elif c==2:value[:]=0.
            elif c in (3,4,5):value=clean[(f+c-2)%4].copy()
            elif c>=6:value[injury[f]]=0.;value[restore[f,c-6]]=clean[f,restore[f,c-6]]
            fields[f,c]=value.reshape(16,16)
    np.testing.assert_array_equal(source["repair_packets"],previous.encode(fields))
    for name in source.keys():assert np.isfinite(source[name]).all(),name
    return native,rewired,dict(mean_absolute_value=magnitude/64,total_absolute_value=magnitude,
        distinguishing_by_foreign=distinction,distinguishing_fraction=distinction.mean(axis=2))


def inspect_body(raw,prototype,packets,graph,block,body):
    np.testing.assert_array_equal(raw["packets"],np.repeat(packets[:,None],8,axis=1))
    np.testing.assert_array_equal(raw["applied_neighbors"],graph)
    birth=seed("E010",block,body,"birth").standard_normal((4,8,1,16,16))
    birth=.2*(birth-birth.mean(axis=(-2,-1),keepdims=True))
    np.testing.assert_array_equal(raw["birth"],birth)
    assert raw["end"].shape==(4,8,9,3,16,16)
    v=raw["end"][:,:,:,0];assert (abs(v)<=2).all()
    agreement=np.empty((4,8,9,4));individual=np.empty((4,8,9,4))
    for f in range(4):
        signs=v[f]>0;resolved=abs(v[f])>.2
        for target in range(4):agreement[f,:,:,target]=(resolved&(signs==(prototype[target]>0))).mean(axis=(-2,-1))
        individual[f,:,:,0]=agreement[f,:,:,f]
        individual[f,:,:,1]=sum(agreement[f,:,:,target] for target in range(4) if target!=f)/3
        individual[f,:,:,2]=resolved.mean(axis=(-2,-1))
        individual[f,:,:,3]=((signs==np.roll(signs,1,-1)).mean(axis=(-2,-1))+(signs==np.roll(signs,1,-2)).mean(axis=(-2,-1)))/2
    for name in raw.keys():assert np.isfinite(raw[name]).all(),name
    return dict(agreement=agreement,individual=individual,observed=individual.mean(axis=1))


def check_stats(values,stored,draws):
    values=np.asarray(values);close(values,stored["block_means"]);close(values.mean(),stored["mean"])
    ci=np.quantile(values[draws].mean(axis=1),[.025,.975]);close(ci,stored["ci95"])
    assert int((values>0).sum())==stored["positive_blocks"]
    return ci


def audit(run):
    manifest=previous.verify(run);contract=manifest["contract"];ids=contract["blocks"]
    technical=contract["phase"]=="benchmark"
    assert ids==([900210] if technical else list(range(8000,8064)))
    assert contract["conditions"]==list(CONDITIONS) and contract["policies"]==list(POLICIES)
    assert contract["primary_body"]=="B" and contract["foreign_references_per_founder"]==3
    assert contract["injury_entries"]==192 and contract["restored_entries"]==64
    assert contract["bootstrap_tag"]=="E010:confirmation"
    arrays={body:{key:[] for key in ("agreement","individual","observed")} for body in ("A","B")}
    descs={name:[] for name in ("mean_absolute_value","total_absolute_value","distinguishing_by_foreign","distinguishing_fraction")}
    with np.load(run/"observations.npz",allow_pickle=False) as saved,np.load(run/"repair_descriptors.npz",allow_pickle=False) as descriptors:
        assert saved["blocks"].tolist()==descriptors["blocks"].tolist()==ids
        for i,block in enumerate(ids):
            path=run/f"source_{block:06d}.npz"
            freeze=read_json(run/f"repair_freeze_{block}.json");worker=read_json(run/f"worker_{block}.json")
            assert sha(path)==freeze["source_sha256"]==worker["source_sha256"]
            assert not freeze["body_outcomes_exist"] and freeze["conditions"]==list(CONDITIONS)
            with np.load(path,allow_pickle=False) as source:
                native,rewired,described=inspect_source(source,block)
                prototype=source["prototype"];packets=source["repair_packets"]
                assert freeze["packets_sha256"]==array_sha(packets)
                assert freeze["graph_sha256"]==array_sha(rewired.astype("<i8"))
            for name,values in described.items():descs[name].append(values);close(values,descriptors[name][i])
            for body in ("A","B"):
                assert datetime.fromisoformat(manifest["started_utc"])<=datetime.fromisoformat(freeze["time"])<datetime.fromisoformat(worker["body_started_utc"][body])
                with np.load(run/f"body_{body}_{block:06d}.npz",allow_pickle=False) as raw:
                    observed=inspect_body(raw,prototype,packets,native if body=="A" else rewired,block,body)
                    if body=="A":birth_a=raw["birth"]
                    else:assert not np.array_equal(birth_a,raw["birth"])
                for name,values in observed.items():arrays[body][name].append(values);close(values,saved[body+"_"+name][i])
    arrays={body:{key:np.array(v) for key,v in values.items()} for body,values in arrays.items()}
    descs={key:np.array(v) for key,v in descs.items()}
    summary=read_json(run/"summary.json");draws=seed("E010:confirmation","bootstrap").integers(0,len(ids),(10000,len(ids)))
    utilities={}
    for body,obs in arrays.items():
        st=summary["bodies"][body];x=obs["observed"];spec=x[:,:,:,0]-x[:,:,:,1]
        utility=spec[:,:,6:]-spec[:,:,1:2];utilities[body]=utility
        values=dict(utility=utility,specificity=spec[:,:,6:],own_agreement=x[:,:,6:,0],
            foreign_agreement=x[:,:,6:,1],own_gain=x[:,:,6:,0]-x[:,:,1:2,0],resolution=x[:,:,6:,2])
        for j,name in enumerate(POLICIES):
            for key,v in values.items():check_stats(v[:,:,j].mean(axis=1),st["policies"][name][key],draws)
            if j:check_stats((utility[:,:,0]-utility[:,:,j]).mean(axis=1),st["comparisons"][name],draws)
        close(x.mean(axis=(0,1)),st["mean_observations"])
        reference=dict(intact_minus_foreign_records=(x[:,:,0,0]-x[:,:,3:6,0].mean(axis=2)).mean(axis=1),
            intact_minus_erased=(x[:,:,0,0]-x[:,:,2,0]).mean(axis=1),
            intact_minus_unrepaired=(x[:,:,0,0]-x[:,:,1,0]).mean(axis=1))
        reference.update({name+"_specificity":spec[:,:,j].mean(axis=1) for j,name in enumerate(CONDITIONS[:6])})
        for name,v in reference.items():check_stats(v,st["references"][name],draws)
        for offset in (1,2,3):
            pair=np.empty((len(ids),4,9))
            for f in range(4):pair[:,f]=(obs["agreement"][:,f,:,:,f]-obs["agreement"][:,f,:,:,(f+offset)%4]).mean(axis=1)
            gain=pair[:,:,6:]-pair[:,:,1:2];record=st["individual_foreign_offsets"][str(offset)]
            for j,name in enumerate(POLICIES):
                check_stats(gain[:,:,j].mean(axis=1),record["utility"][name],draws)
                if j:check_stats((gain[:,:,0]-gain[:,:,j]).mean(axis=1),record["comparisons"][name],draws)
    for j,name in enumerate(POLICIES):
        for key,v in descs.items():
            if v.ndim==3:check_stats(v[:,:,j].mean(axis=1),summary["repair_descriptors"][name][key],draws)
        check_stats((utilities["B"][:,:,j]-utilities["A"][:,:,j]).mean(axis=1),summary["secondary_B_minus_A_utility"][name],draws)
    target=summary["bodies"]["B"]
    gates={"weak_beats_"+name:st["ci95"][0]>0 for name,st in target["comparisons"].items()}
    gates.update(weak_recovers_specificity=target["policies"]["weak"]["utility"]["ci95"][0]>0,
        weak_recovers_own_agreement=target["policies"]["weak"]["own_gain"]["ci95"][0]>0)
    assert gates==summary["gates"]
    expected="TECHNICAL_ONLY" if technical else "WEAK_RESTORATION_QUALIFIED" if all(gates.values()) else "WEAK_RESTORATION_NOT_QUALIFIED"
    assert summary["status"]==expected and summary["blocks"]==ids and summary["founders"]==len(ids)*4
    assert summary["primary_body"]=="B" and summary["foreign_references_per_founder"]==3
    assert summary["restored_entries"]==64 and summary["injury_entries"]==192 and summary["recipients"]==8
    assert summary["external_backup"] and not summary["amplitude_normalization"] and not summary["models_fitted"] and not summary["cohort_filtered"]
    with (run/"individual_observations.csv").open() as file:
        seen=set()
        for row in csv.DictReader(file):
            i=ids.index(int(row["block"]));f=int(row["founder"]);c=CONDITIONS.index(row["condition"]);body=row["body"]
            assert (i,f,c,body) not in seen;seen.add((i,f,c,body))
            x=arrays[body]["observed"][i,f,c]
            for j,name in enumerate(("own","foreign_mean","resolved","neighbor")):close(float(row[name]),x[j])
            close(float(row["specificity"]),x[0]-x[1])
            for target in range(4):close(float(row[f"target_{target}"]),arrays[body]["agreement"][i,f,:,c,target].mean())
        assert len(seen)==len(ids)*4*9*2
    with (run/"individual_repairs.csv").open() as file:
        seen=set()
        for row in csv.DictReader(file):
            i=ids.index(int(row["block"]));f=int(row["founder"]);j=POLICIES.index(row["policy"])
            assert (i,f,j) not in seen;seen.add((i,f,j))
            for key in ("mean_absolute_value","total_absolute_value","distinguishing_fraction"):close(float(row[key]),descs[key][i,f,j])
            for offset in range(3):close(float(row[f"foreign_offset_{offset+1}"]),descs["distinguishing_by_foreign"][i,f,j,offset])
        assert len(seen)==len(ids)*4*3
    return contract


def main():
    p=argparse.ArgumentParser();p.add_argument("run",type=Path);args=p.parse_args();run=args.run.resolve()
    if not run.is_relative_to(Path(__file__).resolve().parent):raise ValueError("Local E010 run required")
    if hasattr(os,"sched_getaffinity"):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    started=time.monotonic();contract=audit(run)
    result=dict(status="PASS",phase=contract["phase"],blocks=len(contract["blocks"]),
        finished_utc=datetime.now(timezone.utc).isoformat(),complete_sha256=sha(run/"COMPLETE.json"),
        audit_code_sha256=sha(__file__),previous_audit_sha256=sha(previous.__file__),
        graph_repairs_backup_bytes_and_chronology_checked=True,all_four_target_scores_reproduced=True,
        all_intervals_csv_rows_and_gates_reproduced=True,seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
