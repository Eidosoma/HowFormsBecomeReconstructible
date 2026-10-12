"""Local immutable evidence and explicit numerical checks for TT009."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
def utc():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text())
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def require(value,label):
    if not value:raise ValueError(label)
def dump(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def table(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))
def csv_write(path,rows):
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def descriptor(a):return dict(shape=list(a.shape),dtype=a.dtype.str,sha256=hashlib.sha256(a.tobytes()).hexdigest())
def arrays(path):
    with np.load(path,allow_pickle=False) as z:
        index=json.loads(z['__index__'].tobytes());require(set(z.files)==set(index)|{'__index__'},'Array field index')
        values={k:z[k] for k in index}
    for k,v in values.items():
        require(descriptor(v)==index[k],'Array commitment '+str(path)+'/'+k)
        if v.dtype.kind=='f':require(np.isfinite(v).all(),'Finite source arrays')
    return values
def equal(a,b,label):
    require(a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes(),'Byte equality '+label)
def close(a,b,tolerance=2e-14,label='Numeric comparison'):
    a,b=np.asarray(a),np.asarray(b);require(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all(),label+' shape/finite')
    error=float(np.max(abs(a-b),initial=0));require(error<=tolerance,f'{label}: {error} > {tolerance}');return error
def config(kind):return read(HERE/f'source/{kind}/inputs/config.json')
def prepared(kind,block):return arrays(HERE/f'source/{kind}/inputs/prepared/cases_{block:06d}.npz')
def observed(kind,block):return arrays(HERE/f'source/{kind}/run/reads_{block:06d}.npz')
def verify_sources():
    receipt=read(HERE/'SOURCE_RECEIPT.json')
    for rel,h in receipt['files_sha256'].items():require(sha(HERE/rel)==h,'Source identity '+rel)
    return receipt
def origin(path):return HERE/read(HERE/'SOURCE_RECEIPT.json')['origins'][str(path)]
