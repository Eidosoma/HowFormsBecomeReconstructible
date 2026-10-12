"""TT008 immutable artifacts and scoped development source bindings."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
CFG=json.loads((HERE/'selection.json').read_text())
FIELDS=CFG['expression_fields'];HISTORIES=CFG['histories'];KEYS=('block','history','founder','recipient')
INTS={'block','founder','recipient','generation','task_rule','current_pass','terminal_success'}
def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def require(condition,label):
    if not condition:raise ValueError(label)
def dump(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def table(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))
def csv_write(path,rows):
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def key(row):return tuple(row[k] for k in KEYS)
def records():return [{k:v if k=='history' else int(v) if k in INTS else float(v) for k,v in row.items()} for row in table(HERE/'source/records.csv')]
def close(a,b,tol=1e-12,label='Numerical mismatch'):
    a,b=np.asarray(a),np.asarray(b);require(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all(),label+' shape/finite')
    error=float(np.max(abs(a-b),initial=0));require(error<=tol,f'{label}: {error} > {tol}');return error
def verify_sources():
    files=read(HERE/'SOURCE_RECEIPT.json')['files_sha256']
    for rel,digest in files.items():require(sha(HERE/rel)==digest,'Changed source '+rel)
    return files


def packets(rows):
    cache={};result=[]
    for row in rows:
        block=row['block'];history=row['history'];label,slot=('pulse',2) if history==HISTORIES[1] else ('spacing',{HISTORIES[0]:0,HISTORIES[2]:1,HISTORIES[3]:2}[history])
        if (label,block) not in cache:
            with np.load(HERE/f'source/{label}/boundary_{block:06d}_g14.npz',allow_pickle=False) as z:
                data=z['outgoing'];idx=json.loads(z['__index__'].tobytes())['outgoing']
                require(hashlib.sha256(data.tobytes()).hexdigest()==idx['sha256'],'Native packet commitment');cache[label,block]=data
        data=cache[label,block][slot,row['founder'],row['recipient']]
        result.append(np.frombuffer(data.tobytes(),dtype='<f8').copy())
    return np.array(result)
