"""Check saved shifts with an FFT oracle and independently rescore evaluation."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import cap_cpus,dump,sha
cap_cpus()
import numpy as np

run=HERE/"runs/diagnostic_v1"
complete=json.loads((run/"COMPLETE.json").read_text())
for rel,digest in complete["outputs_sha256"].items():assert sha(run/rel)==digest
summary=json.loads((run/"summary.json").read_text())
with np.load(run/"quarter_fields.npz",allow_pickle=False) as raw:
    for row in summary["rows"]:
        i=(0 if row["background"]=="homogeneous" else 8)+row["block"]
        q=raw["quarter_fields"][i,:,row["founder"]]
        donor=raw["quarter_fields"][i,:,(row["founder"]+1)%4]
        for kind,moving in (("own",q),("foreign",donor)):
            a=q[0]-q[0].mean();b=moving[2]-moving[2].mean()
            correlation=np.fft.ifft2(np.fft.fft2(a)*np.conj(np.fft.fft2(b))).real
            dy,dx=(row["dy"],row["dx"]) if kind=="own" else (row["foreign_dy"],row["foreign_dx"])
            assert abs(correlation[dy%16,dx%16]-correlation.max())<1e-10
            aligned=((q[1]>0)==(np.roll(moving[3],(dy,dx),axis=(0,1))>0)).mean()
            unshifted=((q[1]>0)==(moving[3]>0)).mean()
            assert aligned==row[kind+"_aligned"] and unshifted==row[kind+"_raw"]
            assert aligned-unshifted==row[kind+"_gain"]
for background,g in summary["groups"].items():
    key=json.dumps(["E005:"+background,"bootstrap"],separators=(",",":")).encode()
    random=np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little")))
    draws=random.integers(0,8,(10000,8))
    rows=[r for r in summary["rows"] if r["background"]==background]
    for metric,st in g["statistics"].items():
        means=np.array([np.mean([r[metric] for r in rows if r["block"]==b]) for b in range(8)])
        np.testing.assert_array_equal(means,st["block_means"])
        np.testing.assert_array_equal(np.quantile(means[draws].mean(axis=1),[.025,.975]),st["ci95"])
result=dict(status="PASS",founders=64,own_and_foreign_shifts_checked_by_fft=128,
            disjoint_quarter_scores_and_intervals_reproduced=True,complete_sha256=sha(run/"COMPLETE.json"),
            audit_code_sha256=sha(__file__))
destination=run/"INDEPENDENT_AUDIT.json"
if destination.exists():raise FileExistsError(destination)
dump(destination,result)
print(json.dumps(result,indent=2))
