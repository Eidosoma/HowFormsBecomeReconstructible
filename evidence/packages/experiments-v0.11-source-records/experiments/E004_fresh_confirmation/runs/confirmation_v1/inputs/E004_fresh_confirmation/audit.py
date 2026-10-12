"""Post-run independent rescore; does not import the simulation or analysis code."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import time

for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[key]="1"
import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def random_for(tag,*parts):
    key=json.dumps([tag,*parts],separators=(",",":")).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little")))


def interval(x,background):
    x=np.asarray(x)
    draws=random_for("E001:"+background,"bootstrap").integers(0,len(x),(10000,len(x)))
    return np.quantile(x[draws].mean(axis=1),[.025,.975])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("run",type=Path)
    args=parser.parse_args()
    run=args.run.resolve()
    here=Path(__file__).resolve().parent
    if not run.is_relative_to(here):raise ValueError("Local run required")
    if hasattr(os,"sched_getaffinity"):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    started=time.monotonic()
    complete=json.loads((run/"COMPLETE.json").read_text())
    for rel,sha in complete["outputs_sha256"].items():
        assert digest(run/rel)==sha,rel
    source=json.loads((run/"inputs/SOURCE_SNAPSHOT.json").read_text())
    for row in source["files"]:
        assert digest(row["path"])==row["sha256"],row["path"]
    summary=json.loads((run/"summary.json").read_text())
    records={}
    files=0;value_checks=0
    for background,group in summary["groups"].items():
        arms=group["arms"]; stages=group["stages"]
        cells=[];preferences=[]; budgets=[];observed_form=[]
        for block in summary["blocks"]:
            with np.load(run/f"block_{block:06d}_{background}.npz",allow_pickle=False) as raw:
                files+=1
                np.testing.assert_array_equal(raw["prototype"],raw["formation_late"].mean(axis=0))
                v=np.concatenate((raw["generation_read"][:,:,:,:,0],raw["terminal"][None,:,:,:,0]))
                own=np.empty(v.shape[:4]); pref=np.empty(v.shape[:4])
                for s in range(4):
                    for f in range(4):
                        for r in range(2):
                            for a,arm in enumerate(arms):
                                body=v[s,f,r,a]
                                matches=[float(((np.signbit(body)==np.signbit(p)) & (np.abs(body)>.2)).sum()/256) for p in raw["prototype"]]
                                own[s,f,r,a]=matches[f]
                                pref[s,f,r,a]=matches[f]-sum(matches[j] for j in range(4) if j!=f)/3
                                records[(background,str(block),str(f),str(r),stages[s],arm)]=(own[s,f,r,a],pref[s,f,r,a])
                                value_checks+=1
                cells.append(own.mean(axis=(1,2)))
                preferences.append(pref.mean(axis=(1,2)))
                outgoing=raw["outgoing"];incoming=raw["incoming"]
                np.testing.assert_array_equal(outgoing[:-1],incoming[1:])
                cp=arms.index("copy")
                np.testing.assert_array_equal(incoming[:,:,:,cp],outgoing[:,:,:,cp])
                erased=[a for a,arm in enumerate(arms) if arm!="copy"]
                assert np.count_nonzero(raw["generation_write_birth"][:,:,:,erased,3])==0
                assert not raw["acquired"][:,1].any()
                assert not outgoing[:,:,:,arms.index("write_off")].any()
                np.testing.assert_array_equal(raw["terminal"][:,:,arms.index("held")],raw["terminal"][:,:,arms.index("erased")])
                np.testing.assert_array_equal(raw["generation_read"][0,:,:,arms.index("read_off")],raw["generation_read"][0,:,:,arms.index("erased")])
                for f in range(4):
                    for r in range(2):
                        np.testing.assert_array_equal(incoming[0,f,r,arms.index("foreign")],raw["acquired"][(f+1)%4,0])
                        original=np.frombuffer(raw["acquired"][f,0].tobytes(),dtype="<f8")
                        shuffled=np.frombuffer(incoming[0,f,r,arms.index("shuffled")].tobytes(),dtype="<f8")
                        np.testing.assert_array_equal(np.sort(original),np.sort(shuffled))
                for g in range(3):
                    b=random_for("forms-e001-unprescribed-v1",block,f"g{g+1}","birth").standard_normal((4,2,1,16,16))
                    b=.2*(b-b.mean(axis=(-2,-1),keepdims=True))
                    np.testing.assert_array_equal(b,raw["generation_birth"][g])
                qbud=[]
                for k,factor in enumerate((1,2,4)):
                    assert raw[f"budget_payload_{factor}"].shape[-1]==2048//factor**2
                    vb=raw["budget_terminal"][k,:,:,:,0]
                    qbud.append(np.stack([((np.signbit(vb[f])==np.signbit(raw["prototype"][f])) & (abs(vb[f])>.2)).mean(axis=(-2,-1)) for f in range(4)]).mean(axis=(0,1)))
                budgets.append(qbud)
                p=raw["prototype"]>0
                balance=p.mean(axis=(-2,-1));amp=(abs(raw["prototype"])>.2).mean(axis=(-2,-1))
                neighbor=((p==np.roll(p,1,-1)).mean(axis=(-2,-1))+(p==np.roll(p,1,-2)).mean(axis=(-2,-1)))/2
                stable=((raw["prototype_halves"][0]>0)==(raw["prototype_halves"][1]>0)).mean(axis=(-2,-1))
                observed_form.extend(((balance>=.1)&(balance<=.9)&(amp>=.8)&(neighbor>=.65)&(stable>=.8)).tolist())
        cells=np.asarray(cells);budgets=np.asarray(budgets)
        np.testing.assert_array_equal(cells,group["block_qualified_own"])
        np.testing.assert_allclose(preferences,group["block_preference"],atol=2e-16,rtol=0)
        assert sum(observed_form)==group["formation_qualified_count"]
        for s,stage in enumerate(stages):
            for name,stats in group["contrasts"][stage].items():
                left,right=name.split("_minus_")
                x=cells[:,s,arms.index(left)]-cells[:,s,arms.index(right)]
                assert float(x.mean())==stats["mean"]
                np.testing.assert_array_equal(x,stats["block_means"])
                np.testing.assert_array_equal(interval(x,background),stats["ci95"])
        for k,row in enumerate(group["budgets"]):
            x=budgets[:,k,0]-budgets[:,k,1]
            np.testing.assert_array_equal(interval(x,background),row["own_minus_foreign"]["ci95"])
            assert float(x.mean())==row["own_minus_foreign"]["mean"]
    csvcount=0
    with (run/"observations.csv").open() as f:
        for row in csv.DictReader(f):
            key=tuple(row[k] for k in ("background","block","founder","recipient","stage","arm"))
            q,p=records[key]
            assert q==float(row["qualified_own"])
            assert abs(p-float(row["preference"]))<3e-16
            csvcount+=1
    assert csvcount==len(records)
    result=dict(status="PASS",audited_complete_sha256=digest(run/"COMPLETE.json"),audit_code_sha256=digest(__file__),
                raw_files=files,individual_scores_checked=value_checks,csv_rows=csvcount,
                primary_and_control_intervals_exact=True,source_hashes_unchanged=len(source["files"]),
                packet_lineage_and_controls=True,seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
