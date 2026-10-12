"""TT007 local evidence, strict identities and non-overwriting artifacts."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
SUB=HERE/'source/submissions/p02_common_future_v0_1'
RESIDUAL=HERE/'source/submissions/p02_residual_leads_v0_1'
CFG=json.loads((SUB/'config.json').read_text())
PLAN=json.loads((HERE/'plan.json').read_text()) if (HERE/'plan.json').exists() else {}
KEYS=('block','history','founder','recipient')
INTS={'block','founder','recipient','generation','task_rule','current_pass','terminal_success'}
PACKAGES={'spacing':'p01_writer_spacing_v0_1','pulse':'p01_writer_factorial_pulse_v0_1'}


def read(path):return json.loads(Path(path).read_text())
def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def csv_write(path,rows):
    with Path(path).open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def table(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))
def records():return [{k:v if k=='history' else int(v) if k in INTS else float(v) for k,v in row.items()} for row in table(SUB/'results/records.csv')]
def key(row):return tuple(row[k] for k in KEYS)
def require(condition,message):
    if not condition:raise ValueError(message)
def close(a,b,tolerance=2e-12,label='Numerical mismatch'):
    aa,bb=np.asarray(a,float),np.asarray(b,float)
    require(aa.shape==bb.shape and np.isfinite(aa).all() and np.isfinite(bb).all(),label+' shape/finite')
    error=float(np.max(np.abs(aa-bb),initial=0.));require(error<=tolerance,f'{label}: {error} > {tolerance}')
    return error
def byte_equal(a,b,label):require(a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes(),label)
def native(label,name):return HERE/'source/native'/PACKAGES[label]/'runs/pilot_v1'/name


def arrays(path):
    with np.load(path,allow_pickle=False) as z:
        index=json.loads(z['__index__'].tobytes());require(set(z.files)==set(index)|{'__index__'},'Array index mismatch')
        result={k:z[k] for k in index}
    for k,value in result.items():
        require(index[k]==dict(shape=list(value.shape),dtype=value.dtype.str,sha256=hashlib.sha256(value.tobytes()).hexdigest()),'Raw array commitment '+k)
        if value.dtype.kind=='f':require(np.isfinite(value).all(),'Nonfinite raw boundary '+k)
    return result


def verify_sources():
    expected={}
    for name in ('SOURCE_RECEIPT.json','NATIVE_RECEIPT.json'):
        expected.update(read(HERE/name)['files_sha256'])
    for name,digest in expected.items():require(sha(HERE/name)==digest,'Changed evidence '+name)
    return expected
