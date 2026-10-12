"""Independent scalar recomputation of every saved transition and access score."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[key]="1"
import numpy as np


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scalar_step(state,weights,record,gain):
    x=np.array([1 if (state>>j)&1 else -1 for j in range(10)],dtype=np.int8)
    for j in range(10):
        field=float(np.dot(weights[j],x))+gain*record[j]
        if field>0:x[j]=1
        elif field<0:x[j]=-1
    return sum((1<<j) for j in range(10) if x[j]>0)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("run",type=Path);args=parser.parse_args()
    run=args.run.resolve()
    if not run.is_relative_to(Path(__file__).resolve().parent):raise ValueError("Local run required")
    if hasattr(os,"sched_getaffinity"):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    started=time.monotonic()
    complete=json.loads((run/"COMPLETE.json").read_text())
    for rel,sha in complete["outputs_sha256"].items():assert digest(run/rel)==sha,rel
    summary=json.loads((run/"summary.json").read_text())
    all_meta=[];count=0
    for b in range(16):
        meta=json.loads((run/f"rulebook_{b:03d}.json").read_text());all_meta.append(meta)
        with np.load(run/f"rulebook_{b:03d}.npz",allow_pickle=False) as raw:
            for mi,entry in enumerate(meta["entries"]):
                expected=np.array([scalar_step(s,raw["weights"],entry["record"],entry["gain"]) for s in range(1024)],dtype=np.uint16)
                np.testing.assert_array_equal(expected,raw["successors"][mi]);count+=1024
                labels=raw["attractor_assignment"][mi];dist=raw["distance_to_cycle"][mi]
                cycles=meta["cycles"][mi]
                np.testing.assert_array_equal(labels,labels[expected])
                np.testing.assert_array_equal(dist[dist>0],dist[expected[dist>0]]+1)
                for cid,cycle in enumerate(cycles):
                    assert cycle[0]==min(cycle)
                    assert all(int(expected[node])==cycle[(j+1)%len(cycle)] for j,node in enumerate(cycle))
                    assert all(labels[node]==cid and dist[node]==0 for node in cycle)
                np.testing.assert_array_equal(np.bincount(labels,minlength=len(cycles)),meta["basin_counts"][mi])
                assert sum(meta["basin_counts"][mi])==1024
                if mi:
                    target=entry["founder_native_orbit"]
                    if target in cycles:
                        mask=labels==cycles.index(target)
                        p16=float(np.count_nonzero(mask & (dist<=16))/1024)
                        eventual=float(np.count_nonzero(mask)/1024)
                    else:p16=eventual=0.
                    assert p16==entry["access16"] and eventual==entry["eventual_access"]
                    native={tuple(c):n/1024 for c,n in zip(meta["cycles"][0],meta["basin_counts"][0])}
                    altered={tuple(c):n/1024 for c,n in zip(cycles,meta["basin_counts"][mi])}
                    tv=sum(abs(native.get(c,0)-altered.get(c,0)) for c in set(native)|set(altered))/2
                    assert tv==entry["basin_total_variation"]
                    edge=float((expected!=raw["successors"][0]).mean())
                    assert edge==entry["changed_edge_fraction"]
                    category=("unchanged_transition_map" if edge==0 else "changed_destinations" if set(native)!=set(altered)
                              else "same_destinations_changed_basin_masses" if tv else "same_destinations_same_basin_masses")
                    assert category==entry["category"]
            x=raw["founder_birth"].copy()
            history=[]
            for t in range(64):
                x=np.array([scalar_step(int(s),raw["weights"],np.zeros(10),0.) for s in x],dtype=np.uint16)
                np.testing.assert_array_equal(x,raw["founder_history"][t]);history.append(x)
            activity=np.array([[[1 if (int(state)>>j)&1 else -1 for j in range(10)] for state in line] for line in history[-16:]]).mean(axis=0)
            np.testing.assert_array_equal(activity,raw["activity_records"])
            for k in (2,5):
                decoded=np.frombuffer(raw[f"payload_{k}"].tobytes(),dtype="<f8").reshape(4,k)
                np.testing.assert_array_equal(decoded,activity[:,raw["public_mask_order"][:k]])
        print(f"Audited all transitions for rulebook {b}",flush=True)
    key=json.dumps(["E002","bootstrap"],separators=(",",":")).encode()
    rng=np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little")))
    draws=rng.integers(0,16,(10000,16))
    for panel in summary["panels"]:
        blocks=[]
        for meta in all_meta:
            rows=[r for r in meta["entries"][1:] if r["k"]==panel["k"] and r["gain"]==panel["gain"]]
            own=np.mean([r["access16"] for r in rows if r["arm"]=="own"])
            foreign=np.mean([r["access16"] for r in rows if r["arm"]=="foreign"])
            blocks.append(own-foreign)
        x=np.asarray(blocks)
        np.testing.assert_array_equal(x,panel["own_minus_foreign"]["block_means"])
        np.testing.assert_array_equal(np.quantile(x[draws].mean(axis=1),[.025,.975]),panel["own_minus_foreign"]["ci95"])
    result=dict(status="PASS",transition_edges_recomputed_scalar=count,all_maps=784,rulebooks=16,
                graph_recursions_and_basin_counts=True,writer_history_and_packet_values=True,
                access_scores_categories_and_primary_intervals=True,
                complete_sha256=digest(run/"COMPLETE.json"),audit_code_sha256=digest(__file__),seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
