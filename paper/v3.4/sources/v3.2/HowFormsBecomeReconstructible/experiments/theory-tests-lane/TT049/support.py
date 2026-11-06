"""Immutable local evidence helpers for prospective TT014."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
def utc():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def require(value,label):
    if not value:raise ValueError(label)
def dump(p,value):
    with Path(p).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def table(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))
def csv_write(p,rows):
    with Path(p).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def descriptor(a):return dict(shape=list(a.shape),dtype=a.dtype.str,sha256=hashlib.sha256(a.tobytes()).hexdigest())
def save(p,values):
    require(all(isinstance(x,np.ndarray) and (x.dtype.kind!='f' or np.isfinite(x).all()) for x in values.values()),'Finite arrays only')
    index={k:descriptor(v) for k,v in values.items()}
    with Path(p).open('xb') as f:np.savez_compressed(f,**values,__index__=np.frombuffer(json.dumps(index,sort_keys=True).encode(),np.uint8))
def arrays(p):
    with np.load(p,allow_pickle=False) as z:
        index=json.loads(z['__index__'].tobytes());require(set(z.files)==set(index)|{'__index__'},'Complete indexed arrays')
        values={k:z[k] for k in index}
    for k,v in values.items():
        require(descriptor(v)==index[k],'Array commitment '+str(p)+'/'+k)
        if v.dtype.kind=='f':require(np.isfinite(v).all(),'Finite data '+k)
    return values
def equal(a,b,label):require(a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes(),'Byte equality '+label)
def close(a,b,tol=1e-12,label='Numeric comparison'):
    a,b=np.asarray(a),np.asarray(b);require(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all(),label+' shape/finite')
    error=float(np.max(abs(a-b),initial=0));require(error<=tol,label+': '+str(error));return error
def config():return read(HERE/'plan.json')
def verify_sources():
    receipt=read(HERE/'SOURCE_RECEIPT.json')
    for rel,h in receipt['files_sha256'].items():require(sha(HERE/rel)==h,'Source identity '+rel)
    return receipt
