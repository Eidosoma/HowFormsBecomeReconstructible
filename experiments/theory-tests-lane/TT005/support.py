"""Frozen input identities, sampling keys and scoring; no native dynamics."""
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE/'plan.json').read_text())
NAMES = [p+'/'+w for p in PLAN['rebuilding_pairings'] for w in PLAN['writers']]+PLAN['controls']


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value): return np.frombuffer(hashlib.sha256(np.ascontiguousarray(value).tobytes()).digest(), np.uint8)


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')


def random(*parts):
    key=json.dumps(list(parts),separators=(',',':')).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],'little')))


def ports():
    result=np.zeros((3,16,16),bool)
    for i,(y,x) in enumerate(((7,1),(3,10),(11,10))): result[i,y:y+2,x:x+2]=True
    return result


def reference(name):
    cache={k:os.environ.get(k) for k in ('MPLCONFIGDIR','XDG_CACHE_HOME')}
    sys.path.insert(0,str(HERE/'reference/e051'))
    try: return importlib.import_module(name)
    finally:
        for k,v in cache.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v


def verify_inputs():
    refs=json.loads((HERE/'reference_manifest.json').read_text())
    for rel,expected in refs['files_sha256'].items():
        if sha(HERE/rel)!=expected: raise ValueError('Reference identity changed: '+rel)
    source=json.loads((HERE/'source_manifest.json').read_text())
    for rel,expected in source['prepared_files_sha256'].items():
        if sha(HERE/rel)!=expected: raise ValueError('Prepared evidence changed: '+rel)
    if source['source_complete_sha256']!=PLAN['source_complete_sha256']: raise ValueError('Source run changed')
    return source


def config(mode):
    cfg=dict(PLAN['native'],masks_per_context=PLAN['masks_per_context'],replicates_per_mask=PLAN['replicates_per_mask'])
    if mode=='fixture': cfg.update(PLAN['fixture'])
    elif mode not in ('benchmark','pilot'): raise ValueError('Unknown mode')
    return cfg


def key(context):
    # Rule labels and packet/policy identities never select physical randomness.
    return [*PLAN['random_namespace'],context['block'],context['founder'],context['recipient']]


def cases(mode):
    if mode=='pilot':
        source=verify_inputs()
        with np.load(HERE/'source_packets.npz',allow_pickle=False) as z: packets=z['packets']
        for i,context in enumerate(source['contexts']):
            for j,row in enumerate(context['packets']):
                if hashlib.sha256(packets[i,j].tobytes()).hexdigest()!=row['packet_sha256']:
                    raise ValueError('Packet identity changed')
        weights=np.frombuffer(packets.tobytes(),dtype='<f8').reshape(len(source['contexts']),len(NAMES),2,16,16).copy()
        return source['contexts'],weights
    context=dict(PLAN['technical_context'])
    p=ports(); sign=np.ones((16,16)); sign[p[2]]=-1
    original=np.stack((sign*np.roll(sign,-1,-1),sign*np.roll(sign,-1,-2)))
    values=[]
    for i in range(9):
        if i%3==0: values.append(original*(2.**(-i)))
        elif i%3==1: values.append(random('TT005','excluded_packets',i).uniform(-1,1,(2,16,16)))
        else: values.append(np.zeros_like(original))
    sign[p[1]]=-1; sign[p[2]]=1
    foreign=np.stack((sign*np.roll(sign,-1,-1),sign*np.roll(sign,-1,-2)))
    values.extend([np.zeros_like(original),foreign])
    return [context],np.stack(values)[None]


def draws(context,cfg):
    k=key(context); allowed=np.flatnonzero(~ports().any(axis=0).ravel())
    masks=np.zeros((cfg['masks_per_context'],16,16),bool)
    birth_base=[]; birth_other=[]; noise_base=[]; noise_other=[]
    for m in range(cfg['masks_per_context']):
        masks[m].ravel()[random(*k,'mask',m,'damage').choice(allowed,cfg['damage_cells'],replace=False)]=True
        for r in range(cfg['replicates_per_mask']):
            for destination,name in [(birth_base,'birth_base'),(birth_other,'birth_other')]:
                destination.append(cfg['birth_sd']*random(*k,'mask',m,'repeat',r,name).standard_normal((16,16)))
            noise_base.append(random(*k,'mask',m,'repeat',r,'noise_base'))
            noise_other.append(random(*k,'mask',m,'repeat',r,'noise_other'))
    base,other=np.stack(birth_base),np.stack(birth_other)
    birth=np.stack([np.stack((base,base if reset else other),axis=1) for _,reset,_ in PLAN['assay_pairings']])
    def noise():
        for _ in range(cfg['read_steps']):
            a=np.stack([r.standard_normal((16,16)) for r in noise_base])
            b=np.stack([r.standard_normal((16,16)) for r in noise_other])
            yield np.stack([np.stack((a,a if paired else b),axis=1) for _,_,paired in PLAN['assay_pairings']])
    return masks,birth,noise()


def score(mean_ports,rule,margin):
    values=np.asarray(mean_ports)
    if values.shape[-2:]!=(2,2) or not np.isfinite(values).all(): raise ValueError('Invalid paired-cue readout')
    target=float(rule)*np.array([1.,-1.])
    ancestral=np.minimum(target*values[...,0],-target*values[...,1])
    opposite=np.minimum(-target*values[...,0],target*values[...,1])
    a=(ancestral>margin).all(axis=-1); b=(opposite>margin).all(axis=-1)
    if (a&b).any(): raise ValueError('Rule categories overlap')
    return dict(category=np.where(a,0,np.where(b,1,2)).astype(np.int8),cue_success=ancestral>margin,
                ancestral_margin=ancestral,opposite_margin=opposite)
