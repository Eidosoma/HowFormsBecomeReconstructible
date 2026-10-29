"""Assemble unchanged packets and old labels from independently audited archives."""
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from common import dump,sha,utc
from E083_reader_repeatability.plan import HERE,ROOT,settings,cohort,source_block

FIELDS=('both','margin','minimum_margin','transfer','aligned_transfer')
FOLDERS={'E077':('E077_fresh_reconstruction_tradeoff','confirmation_v1'),
         'E080':('E080_strength_allocation','allocation_v1'),
         'E081':('E081_fresh_strength_pattern','confirmation_v1')}


def save(path,arrays):
    assert all(np.isfinite(v).all() for v in arrays.values())
    with Path(path).open('xb') as f:np.savez_compressed(f,**arrays)


def load(path):
    with np.load(path,allow_pickle=False) as z:out={k:z[k] for k in z.files}
    assert all(np.isfinite(v).all() for v in out.values())
    return out


def equal(a,b):
    assert set(a)==set(b)
    for key in a:
        assert a[key].shape==b[key].shape and a[key].dtype==b[key].dtype,key
        assert a[key].tobytes()==b[key].tobytes(),key


def register():
    path=HERE/'SOURCE_DATA.json';assert not path.exists()
    modes={};predecessors={}
    for mode in ('fixture','benchmark','scientific'):
        modes[mode]={}
        for tag,(folder,scientific_name) in FOLDERS.items():
            run=ROOT/folder/'runs'/(scientific_name if mode=='scientific' else mode+'_v1')
            complete=json.loads((run/'COMPLETE.json').read_text());audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
            assert complete['status']=='COMPLETE' and complete['controls_pass'] and audit['status']=='PASS'
            assert audit['complete_sha256']==sha(run/'COMPLETE.json')
            if mode=='scientific':
                p=ROOT/folder/'analysis/closeout_v1.json';c=json.loads(p.read_text());assert c['status']=='PASS'
                assert c['complete_sha256']==sha(run/'COMPLETE.json') and c['audit_sha256']==sha(run/'INDEPENDENT_AUDIT.json')
                predecessors[str(p.relative_to(ROOT))]=sha(p)
            blocks=list(range(42000,42032)) if tag=='E081' else list(range(41000,41032))
            if mode!='scientific':blocks=[900041]
            names=[f'{kind}_{b:06d}.npz' for b in blocks for kind in ('records','interventions','cases')]
            for name in names:assert sha(run/name)==complete['outputs_sha256'][name],name
            modes[mode][tag]=dict(path=str(run.relative_to(ROOT)),blocks=blocks,
                files={n:complete['outputs_sha256'][n] for n in names},
                receipts={str((run/n).relative_to(ROOT)):sha(run/n) for n in ('COMPLETE.json','INDEPENDENT_AUDIT.json','manifest.json')})
    d=ROOT/'E082_saved_pattern_diagnosis/analysis/closeout_v1.json'
    c=json.loads(d.read_text());assert c['status']=='PASS'
    assert c['complete_sha256']==sha(ROOT/'E082_saved_pattern_diagnosis/runs/diagnosis_v1/COMPLETE.json')
    predecessors[str(d.relative_to(ROOT))]=sha(d)
    dump(path,dict(utc=utc(),sources=modes,predecessors=predecessors,
                   new_reader_outcomes_seen=False,prior_outcomes_known=True,case_selection=False,
                   old_observations_pooled=False,fresh_draws=[0,1]))


def verify_receipts(mode):
    r=json.loads((HERE/'SOURCE_DATA.json').read_text())
    checks=dict(r['predecessors'])
    for s in r['sources'][mode].values():checks.update(s['receipts'])
    for rel,digest in checks.items():assert sha(ROOT/rel)==digest,rel
    return r['sources'][mode]


def archive(mode,tag,block,kind):
    r=json.loads((HERE/'SOURCE_DATA.json').read_text())['sources'][mode][tag]
    assert block in r['blocks']
    name=f'{kind}_{block:06d}.npz';raw=(ROOT/r['path']/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['files'][name],name
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k] for k in z.files}


def source(mode,task,independent=False):
    c,b=cohort(task),source_block(task)
    current=archive(mode,c,b,'records');cases=archive(mode,c,b,'cases');inter=archive(mode,c,b,'interventions')
    if c=='E080':
        old=archive(mode,'E077',b,'records');old_cases=archive(mode,'E077',b,'cases')
        old_inter=archive(mode,'E077',b,'interventions')
        np.testing.assert_array_equal(inter['eligible'][8:12],old_inter['eligible'])
        packets=np.concatenate((old['packets'][:18],current['packets'][8:16]))
        scores={k:np.concatenate((old_cases[k][:18],cases[k][8:16])) for k in FIELDS}
        eligible=old_inter['eligible']
    else:
        packets=current['packets'].copy();scores={k:cases[k].copy() for k in FIELDS};eligible=inter['eligible'].copy()
    if independent:
        # Independent slot-by-slot assembly, before any new response exists.
        out=np.empty_like(packets);other={k:np.empty_like(v) for k,v in scores.items()}
        for slot in range(26):
            if c=='E081':src,sc,loc=current,cases,slot
            elif slot<18:src,sc,loc=old,old_cases,slot
            else:src,sc,loc=current,cases,slot-10
            out[slot]=src['packets'][loc]
            for k in FIELDS:other[k][slot]=sc[k][loc]
        packets,scores=out,other
    r=settings(mode)['recipients'];assert packets.shape==(26,4,r,4096)
    assert eligible.shape==(4,4,r,2,16,16) and eligible.dtype==bool
    out=dict(packets=packets,eligible=eligible,**{'old_'+k:v for k,v in scores.items()})
    preflight(out)
    return out


def preflight(source):
    from E015_functional_inheritance.audit import unpack
    w=unpack(source['packets']);e=source['eligible'];of,ff=w[18:22],w[22:26]
    assert np.array_equal(of!=0,ff!=0) and np.array_equal(np.signbit(of),np.signbit(ff))
    for group in (of,ff):assert group[~e].tobytes()==w[13:17][~e].tobytes()
    np.testing.assert_allclose(np.where(e,abs(of),0.).sum(axis=(-3,-2,-1)),
                               np.where(e,abs(ff),0.).sum(axis=(-3,-2,-1)),rtol=2e-14,atol=0)
    assert w[:4][~e].tobytes()==w[4:8][~e].tobytes()
    assert not w[4:8][e].any() and not np.signbit(w[4:8][e]).any()
    assert (w[:4][e]!=0).all()
    np.testing.assert_array_equal(source['old_both'],(source['old_margin']>.25).all(axis=-1))
    np.testing.assert_array_equal(source['old_minimum_margin'],source['old_margin'].min(axis=-1))
    for slot in (8,17):
        for f in (0,2):assert source['packets'][slot,f].tobytes()==source['packets'][slot,f+1].tobytes()
    return True
