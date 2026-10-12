"""Independent byte-boundary and saved-field audit; no production imports."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[name]="1"
import numpy as np


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(packet,factor):
    shape=packet.shape[:-1]+(16//factor,16//factor)
    small=np.frombuffer(packet.tobytes(),dtype="<f8").reshape(shape)
    return np.repeat(np.repeat(small,factor,axis=-2),factor,axis=-1)


def encode(field,factor):
    shape=field.shape[:-2]+(16//factor,factor,16//factor,factor)
    small=field.reshape(shape).mean(axis=(-3,-1)) if factor>1 else field
    return np.ascontiguousarray(small,dtype="<f8").view(np.uint8).reshape(*field.shape[:-2],-1)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("run",type=Path);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];run=args.run.resolve()
    if not run.is_relative_to(root/"E006_compact_renewal"):raise ValueError("Local run required")
    if hasattr(os,"sched_getaffinity"):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    started=time.monotonic()
    complete=json.loads((run/"COMPLETE.json").read_text())
    for rel,digest in complete["outputs_sha256"].items():assert sha(run/rel)==digest,rel
    summary=json.loads((run/"summary.json").read_text())
    ids=summary["source_blocks"];arms=summary["arms"];stages=summary["stages"]
    key=json.dumps(["E006","bootstrap"],separators=(",",":")).encode()
    random=np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little")))
    draws=random.integers(0,len(ids),(10000,len(ids)))
    scores_by_factor={};files=0
    for factor in (1,2,4):
        group=summary["groups"][str(factor)];scores=[]
        for block in ids:
            meta=json.loads((run/f"block_{block:06d}_factor_{factor}.json").read_text())
            assert sha(root/meta["source_file"])==meta["source_sha256"]
            with np.load(run/f"block_{block:06d}_factor_{factor}.npz",allow_pickle=False) as raw:
                files+=1;incoming=raw["incoming"];outgoing=raw["outgoing"]
                assert incoming.shape==(3,4,2,10,2048//factor**2)
                np.testing.assert_array_equal(incoming[1:],outgoing[:-1])
                cp=arms.index("copy")
                np.testing.assert_array_equal(incoming[:,:,:,cp],outgoing[:,:,:,cp])
                for g in range(3):
                    written=encode(raw["generation_written"][g,:,:,:,3],factor).copy()
                    written[:,:,cp]=incoming[g,:,:,cp]
                    np.testing.assert_array_equal(written,outgoing[g])
                erase=[a for a,arm in enumerate(arms) if arm!="copy"]
                assert not raw["generation_write_birth"][:,:,:,erase,3].any()
                assert not outgoing[:,:,:,arms.index("write_off")].any()
                np.testing.assert_array_equal(raw["terminal"][:,:,arms.index("held")],raw["terminal"][:,:,arms.index("erased")])
                np.testing.assert_array_equal(raw["generation_read"][0,:,:,arms.index("read_off")],raw["generation_read"][0,:,:,arms.index("erased")])
                source_full=np.frombuffer(raw["acquired"][:,0].tobytes(),dtype="<f8").reshape(4,16,16)
                expected=encode(source_full,factor)
                for f in range(4):
                    for r in range(2):
                        np.testing.assert_array_equal(incoming[0,f,r,0],expected[f])
                        np.testing.assert_array_equal(incoming[0,f,r,arms.index("foreign")],expected[(f+1)%4])
                        a=np.frombuffer(expected[f].tobytes(),dtype="<f8")
                        b=np.frombuffer(incoming[0,f,r,arms.index("shuffled")].tobytes(),dtype="<f8")
                        np.testing.assert_array_equal(np.sort(a),np.sort(b))
                vs=np.concatenate((raw["generation_read"][:,:,:,:,0],raw["terminal"][None,:,:,:,0]))
                own=np.empty((4,4,2,10))
                for s in range(4):
                    for f in range(4):
                        own[s,f]=(((vs[s,f]>0)==(raw["prototype"][f]>0)) & (np.abs(vs[s,f])>.2)).mean(axis=(-2,-1))
                scores.append(own.mean(axis=(1,2)))
                fields=np.concatenate((decode(incoming,factor),decode(outgoing[-1:],factor)))
                assert np.isfinite(fields).all()
        x=np.array(scores);scores_by_factor[factor]=x
        np.testing.assert_array_equal(x,group["block_own"])
        for s,stage in enumerate(stages):
            for name,st in group["contrasts"][stage].items():
                left,right=name.split("_minus_")
                difference=x[:,s,arms.index(left)]-x[:,s,arms.index(right)]
                np.testing.assert_array_equal(difference,st["block_means"])
                assert float(difference.mean())==st["mean"]
                sampled=difference[draws].mean(axis=1)
                np.testing.assert_array_equal(np.quantile(sampled,[.025,.975]),st["ci95"])
                np.testing.assert_array_equal(np.quantile(sampled,[.0125,.9875]),st["ci975"])
        positive=lambda stage,name:group["contrasts"][stage][name]["ci95"][0]>0
        expected_gates=dict(acquisition_readable=positive("G1","copy_minus_erased"),
            early_specificity=all(positive(s,"rewrite_minus_foreign") for s in stages[:3]),
            terminal_specificity=group["contrasts"]["terminal"]["rewrite_minus_foreign"]["ci95" if factor==1 else "ci975"][0]>0,
            terminal_read_required=positive("terminal","rewrite_minus_read_off"),terminal_write_required=positive("terminal","rewrite_minus_write_off"))
        assert group["gates"]==expected_gates
    for factor in (1,2,4):
        x=scores_by_factor[factor][:,3,0]-scores_by_factor[1][:,3,0]
        st=summary["groups"][str(factor)]["terminal_minus_full_field"]
        np.testing.assert_array_equal(st["block_means"],x)
        np.testing.assert_array_equal(st["ci95"],np.quantile(x[draws].mean(axis=1),[.025,.975]))
    result=dict(status="PASS",raw_files=files,individual_primary_observations=files*4*4*2*10,
                all_boundaries_at_declared_byte_budget=True,copy_and_erasure_exact=True,
                encoded_shuffle_multiset_preserved=True,all_scores_intervals_and_gates_reproduced=True,
                complete_sha256=sha(run/"COMPLETE.json"),audit_code_sha256=sha(__file__),seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
