import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
FORMS=LANE.parent
THEORY=FORMS/'theory-lane'
HISTORIES=('exact_rewrite','single_tolerance_rewrite','spaced_tolerance_rewrite','clustered_tolerance_rewrite')
BLOCKS=list(range(8))
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def save(p,x):
    assert all(np.isfinite(v).all() for v in x.values())
    with Path(p).open('xb') as f:np.savez_compressed(f,**x)
def arrays(p):
    with np.load(p,allow_pickle=False) as z:
        result={k:z[k] for k in z.files if k!='__index__'}
        if '__index__' in z:
            index=json.loads(z['__index__'].tobytes())
            assert set(result)==set(index)
            for k,a in result.items():
                assert index[k]['sha256']==hashlib.sha256(a.tobytes()).hexdigest(),k
                assert index[k]['shape']==list(a.shape) and np.dtype(index[k]['dtype'])==a.dtype,k
    assert all(np.isfinite(v).all() for v in result.values());return result

