"""Pinned saved arrays and unchanged outcome evidence."""
import csv
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from common import dump,sha,utc
from E117_saved_finite_sensitivity.plan import HERE,ROOT,PARENT,COPY_NAMES,settings,key

def register():
    target=HERE/'SOURCE_DATA.json';assert not target.exists()
    close=PARENT/'analysis/closeout_v1.json';c=json.loads(close.read_text());assert c['status']=='PASS'
    receipts={str(p.relative_to(ROOT)):sha(p) for p in (close,PARENT/'PROTOCOL.md',PARENT/'SAMPLE_FREEZE.json')}
    sources={}
    for mode in ('benchmark','scientific'):
        cfg=settings(mode);run=PARENT/'runs'/cfg['source_run'];done=json.loads((run/'COMPLETE.json').read_text())
        assert done['status']=='COMPLETE' and done['controls_pass']
        if mode=='scientific':assert c['complete_sha256']==sha(run/'COMPLETE.json')
        names=list(COPY_NAMES)+[n for b in cfg['blocks'] for n in
            (f'writer_{b}.npz',f'capture_{b}.npz',f'assay_{b}_r0.npz',f'assay_{b}_r1.npz')]
        files={}
        for name in names:
            p=run/name;h=sha(p);assert done['outputs_sha256'][name]==h,name
            files[name]=dict(sha256=h,bytes=p.stat().st_size)
        for name in ('COMPLETE.json','CHECKS.json','manifest.json'):
            p=run/name;receipts[str(p.relative_to(ROOT))]=sha(p)
        sources[mode]=dict(path=str(run.relative_to(ROOT)),files=files)
    dump(target,dict(utc=utc(),receipts=receipts,sources=sources,no_new_dynamics=True,
        all_sources_retained=True,old_outcomes_known=True,new_scientific_features_extracted=False))

def registry(mode=None,full=False):
    r=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for p,h in r['receipts'].items():assert sha(ROOT/p)==h,p
    if full:
        for label,s in r['sources'].items():
            if mode is not None and mode!=label:continue
            for name,info in s['files'].items():
                p=ROOT/s['path']/name;assert p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],name
    return r

def raw(mode,name):
    s=json.loads((HERE/'SOURCE_DATA.json').read_text())['sources'][mode]
    raw=(ROOT/s['path']/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==s['files'][name]['sha256'],name
    return raw

def arrays(mode,name,fields=None):
    with np.load(io.BytesIO(raw(mode,name)),allow_pickle=False) as z:
        out={k:z[k] for k in (z.files if fields is None else fields)}
    assert all(np.isfinite(v).all() for v in out.values());return out

def cases(mode):return {key(r):r for r in csv.DictReader(io.StringIO(raw(mode,'cases.csv').decode()))}

def copy_tables(mode,run):
    for name in COPY_NAMES:
        with (run/('source_'+name)).open('xb') as f:f.write(raw(mode,name))

def save(path,arrays):
    assert all(np.isfinite(v).all() for v in arrays.values())
    with Path(path).open('xb') as f:np.savez_compressed(f,**arrays)

def export(path,rows,fields=None):
    fields=fields or list(rows[0])
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def close(a,b,label,exact=False):
    assert a.shape==b.shape,(label,a.shape,b.shape)
    if exact:assert a.dtype==b.dtype and a.tobytes()==b.tobytes(),label
    else:np.testing.assert_allclose(a,b,rtol=2e-13,atol=2e-12,err_msg=label)
    return a.size
