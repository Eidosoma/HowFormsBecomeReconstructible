"""Verified archived starting pairs and newly reserved prospective sources."""
import io,json,hashlib
import numpy as np
from common import dump,sha,utc
from E077_fresh_reconstruction_tradeoff.data import save,equal
from E118_finite_formation.data import export
from E119_reversal_duration.plan import ROOT,here,settings

def fresh_audit():
    reserved=set(settings('histories','scientific')['blocks']);checked=[]
    def numbers(x):
        if isinstance(x,dict):
            for v in x.values():yield from numbers(v)
        elif isinstance(x,list):
            for v in x:yield from numbers(v)
        elif isinstance(x,int) and not isinstance(x,bool):yield x
    for p in sorted(set(ROOT.glob('E*/runs/*/manifest.json'))|set(ROOT.glob('E*/jobs/*/manifest.json'))):
        if p.is_relative_to(here('histories')):continue
        v=json.loads(p.read_text());assert not reserved.intersection(numbers(v.get('contract',{}))),p
        checked.append(str(p.relative_to(ROOT)))
    return dict(blocks=sorted(reserved),manifests_checked=len(checked),no_collision=True,utc=utc())

def register(study):
    target=here(study)/'SOURCE_DATA.json';assert not target.exists()
    sources={};receipts={}
    for mode,run,blocks in [('benchmark','benchmark_v1',[900041]),('scientific','confirmation_v1',list(range(41000,41032)))]:
        if study=='histories' and mode=='scientific':continue
        path=ROOT/'E077_fresh_reconstruction_tradeoff/runs'/run
        receipt=path/'COMPLETE.json';c=json.loads(receipt.read_text());assert c['status']=='COMPLETE'
        receipts[str(receipt.relative_to(ROOT))]=sha(receipt)
        files={}
        for b in blocks:
            for prefix in ('source','interventions','rewrite'):
                name=f'{prefix}_{b:06d}.npz';h=sha(path/name)
                assert h==c['outputs_sha256'][name],name;files[name]=h
        sources[mode]=dict(path=str(path.relative_to(ROOT)),files=files)
    dump(target,dict(utc=utc(),sources=sources,receipts=receipts,
        sources_known=study!='histories',new_assessments_not_seen=True,
        fresh=fresh_audit() if study=='histories' else None))

def verify(study,full=False):
    x=json.loads((here(study)/'SOURCE_DATA.json').read_text())
    for p,h in x['receipts'].items():assert sha(ROOT/p)==h,p
    if full:
        for source in x['sources'].values():
            for n,h in source['files'].items():assert sha(ROOT/source['path']/n)==h,n
    return x

def load_source(study,mode,task,prefix):
    source=verify(study)['sources'][mode];name=f'{prefix}_{task:06d}.npz'
    raw=(ROOT/source['path']/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==source['files'][name],name
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k] for k in z.files}

def starting(study,mode,task,R):
    from E119_reversal_duration import model
    s=load_source(study,mode,task,'source');inter=load_source(study,mode,task,'interventions')
    expected=model.old.intervene(s);equal(inter,expected)
    selected=model.selection(s['incoming'][:4],s['outgoing'][:4],s['fallback'][:4])
    assert selected.tobytes()==inter['eligible'].tobytes()
    p=model.prune(s['outgoing'][:4],selected)
    assert p.tobytes()==inter['packets'][4:8].tobytes()
    if inter['packets'].shape[2]!=R:
        assert mode=='benchmark' and inter['packets'].shape[2]==1
        inter={k:np.repeat(v,R,axis=2) for k,v in inter.items()}
    return inter
