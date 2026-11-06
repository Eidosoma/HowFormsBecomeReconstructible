"""Fresh-source and excluded-reference registry; exact retained artifacts."""
import csv
import io
import json
import hashlib
import numpy as np
from common import dump,sha,utc
from E118_finite_formation.plan import HERE,ROOT,BLOCKS

def save(path,arrays):
    assert all(np.isfinite(v).all() for v in arrays.values())
    with path.open('xb') as f:np.savez_compressed(f,**arrays)

def equal(a,b):
    assert set(a)==set(b),(set(a)-set(b),set(b)-set(a))
    for k in a:
        assert a[k].shape==b[k].shape and a[k].dtype==b[k].dtype,(k,a[k].shape,b[k].shape)
        assert a[k].tobytes()==b[k].tobytes(),k

def export(path,rows,fields=None):
    fields=fields or list(rows[0])
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def fresh_audit():
    paths=sorted(set(ROOT.glob('E*/runs/*/manifest.json'))|set(ROOT.glob('E*/jobs/*/manifest.json')))
    checked=[]
    def integers(v):
        if isinstance(v,dict):
            for x in v.values():yield from integers(x)
        elif isinstance(v,list):
            for x in v:yield from integers(x)
        elif isinstance(v,int) and not isinstance(v,bool):yield v
    for p in paths:
        if p.is_relative_to(HERE):continue
        d=json.loads(p.read_text());collision=set(BLOCKS)&set(integers(d.get('contract',d)))
        assert not collision,(p,collision)
        checked.append(str(p.relative_to(ROOT)))
    return dict(utc=utc(),blocks=list(BLOCKS),manifests_checked=len(checked),paths=checked,no_collision=True)

def register():
    p=HERE/'SOURCE_DATA.json';assert not p.exists()
    source=ROOT/'E112_fresh_component_prediction/runs/benchmark_v1'
    c=json.loads((source/'COMPLETE.json').read_text());assert c['status']=='COMPLETE' and c['controls_pass']
    names=['acquisition_9000980.npz','body_9000980.npz','outgoing_9000980.npz',
           'source_mixture_9000980.npz','source_recovery_9000980.npz','source_pruning_9000980.npz',
           'writer_9000980.npz','assay_9000980_r0.npz','assay_9000980_r1.npz']
    names += [f'source_boundary_9000980_g{g}.npz' for g in range(1,33)]
    names += [f'source_continuation_9000980_g{g}.npz' for g in range(1,4)]
    files={}
    for n in names:
        h=sha(source/n);assert h==c['outputs_sha256'][n],n;files[n]=h
    dump(p,dict(utc=utc(),fresh=fresh_audit(),excluded_path=str(source.relative_to(ROOT)),
                excluded_files=files,receipts={str((source/'COMPLETE.json').relative_to(ROOT)):sha(source/'COMPLETE.json')},
                no_old_scientific_packets=True,scientific_sources_generated=False))

def registry(full=False):
    r=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for p,h in r['receipts'].items():assert sha(ROOT/p)==h,p
    if full:
        for p,h in r['excluded_files'].items():assert sha(ROOT/r['excluded_path']/p)==h,p
    return r

def golden(name):
    r=registry();raw=(ROOT/r['excluded_path']/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['excluded_files'][name],name
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k] for k in z.files}
