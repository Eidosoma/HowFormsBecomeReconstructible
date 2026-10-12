"""Separate random-draw and equation replay. No production dynamics imports."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import support as s

BASE=s.reference('E015_functional_inheritance.audit')
NATIVE=s.reference('E022_reader_compensation.audit')
FIELDS={'incoming','masks','birth','available','physical','denominator','read_end','late_ports','mean_ports','state_hashes','noise_hashes'}


def equal(a,b,name):
    a,b=np.asarray(a),np.asarray(b)
    if a.shape!=b.shape or a.dtype!=b.dtype or a.tobytes()!=b.tobytes(): raise ValueError('Replay differs: '+name)


def commitment(value):
    return np.frombuffer(hashlib.sha256(value.tobytes(order='C')).digest(),dtype=np.uint8)


def replay(path,weights,context,cfg):
    with np.load(path,allow_pickle=False) as z:raw={k:z[k] for k in z.files}
    if set(raw)!=FIELDS or not all(np.isfinite(v).all() for v in raw.values()): raise ValueError('Evidence schema or finiteness')
    equal(raw['incoming'],weights,'immutable incoming packet')
    p=BASE.ports();allowed=np.flatnonzero(~p.any(axis=0).ravel())
    k=[*s.PLAN['random_namespace'],context['block'],context['founder'],context['recipient']]
    masks=[];starts=[];streams=[]
    for m in range(cfg['masks_per_context']):
        mask=np.zeros((16,16),bool)
        mask.ravel()[BASE.random(*k,'mask',m,'damage').choice(allowed,cfg['damage_cells'],replace=False)]=True
        for r in range(cfg['replicates_per_mask']):
            masks.append(mask.copy())
            starts.append([cfg['birth_sd']*BASE.random(*k,'mask',m,'repeat',r,name).standard_normal((16,16))
                           for name in ('birth_base','birth_other')])
            streams.append([BASE.random(*k,'mask',m,'repeat',r,name) for name in ('noise_base','noise_other')])
    masks=np.array(masks);starts=np.array(starts);q=len(masks)
    birth=np.empty((4,q,2,16,16))
    for c,(_,rho,_) in enumerate(s.PLAN['assay_pairings']):
        birth[c,:,0]=starts[:,0];birth[c,:,1]=starts[:,0 if rho else 1]
    edges=np.empty((q,2,16,16),bool)
    for y,x in np.ndindex(16,16):
        edges[:,0,y,x]=~masks[:,y,x]&~masks[:,y,(x+1)%16]
        edges[:,1,y,x]=~masks[:,y,x]&~masks[:,(y+1)%16,x]
    physical=weights[:,None]*edges[None]
    denominator=np.empty((len(weights),q,16,16));w=abs(physical)
    for y,x in np.ndindex(16,16):
        denominator[:,:,y,x]=w[:,:,0,y,x]+w[:,:,0,y,(x-1)%16]+w[:,:,1,y,x]+w[:,:,1,(y-1)%16,x]
    for name,value in [('masks',masks),('birth',birth),('available',edges),('physical',physical),('denominator',denominator)]:
        equal(raw[name],value,name)
    if raw['state_hashes'].shape!=(cfg['read_steps'],32) or raw['noise_hashes'].shape!=(cfg['read_steps'],32):
        raise ValueError('Missing trajectory commitments')
    v=np.broadcast_to(birth[None],(len(weights),*birth.shape)).copy()
    active=(~masks)[None,None,:,None];cue=np.array([1.,-1.])[None,None,None,:,None]
    v*=active;v[...,p[0]]=cue;late=[]
    for t in range(cfg['read_steps']):
        sample=np.array([[rng.standard_normal((16,16)) for rng in row] for row in streams])
        noise=np.empty_like(birth)
        for c,(_,_,rho) in enumerate(s.PLAN['assay_pairings']):
            noise[c,:,0]=sample[:,0];noise[c,:,1]=sample[:,0 if rho else 1]
        equal(raw['noise_hashes'][t],commitment(noise),'noise commitment '+str(t))
        v=NATIVE.advance_compensated(v,physical[:,None,:,None],denominator[:,None,:,None],noise[None],cfg,
                                    t>=cfg['settling_steps'])
        v*=active;v[...,p[0]]=cue
        equal(raw['state_hashes'][t],commitment(v),'trajectory commitment '+str(t))
        if t>=cfg['read_steps']-cfg['observe_steps']:
            late.append(np.stack((v[...,p[1]].mean(axis=-1),v[...,p[2]].mean(axis=-1)),axis=-1))
    equal(raw['read_end'],v,'read end');equal(raw['late_ports'],np.array(late),'late trace')
    equal(raw['mean_ports'],np.array(late).mean(axis=0),'mean ports')
    for c in range(1,4):equal(v[:,c,:,0],v[:,0,:,0],'first-cue invariance')
    return raw['mean_ports']


def audit(output):
    output=Path(output);started=time.monotonic();index=json.loads((output/'EVENTS.json').read_text())
    contexts,weights=s.cases(index['mode']);cfg=s.config(index['mode'])
    if index['contexts']!=contexts or index['cfg']!=cfg or index['packet_names']!=s.NAMES or index['assay_pairings']!=s.PLAN['assay_pairings']:
        raise ValueError('Assay contract changed')
    if len(index['events'])!=len(contexts):raise ValueError('Incomplete event list')
    count=0
    for i,(context,entry) in enumerate(zip(contexts,index['events'])):
        expected_path='events/'+context['id']+'.npz'
        expected_key=[*s.PLAN['random_namespace'],context['block'],context['founder'],context['recipient']]
        n=11*4*cfg['masks_per_context']*cfg['replicates_per_mask']
        if (entry['context_index'],entry['context_id'],entry['path'],entry['key'],entry['paired_cue_assays'])!=(i,context['id'],expected_path,expected_key,n):
            raise ValueError('Event identity mismatch')
        path=output/expected_path
        if s.sha(path)!=entry['sha256']:raise ValueError('Event evidence changed')
        replay(path,weights[i],context,cfg);count+=n
    if count!=index['paired_cue_assays'] or index['native_rebuilds']!=0:raise ValueError('Assay count mismatch')
    if index['mode']=='pilot' and count!=s.PLAN['pilot_paired_cue_assays']:raise ValueError('Pilot panel mismatch')
    report=dict(status='PASS',utc=s.utc(),seconds=time.monotonic()-started,contexts_replayed=len(contexts),
        paired_cue_assays=count,update_batches_replayed=len(contexts)*cfg['read_steps'],
        all_state_and_noise_commitments_match=True,first_cue_invariant=True,native_rebuilds=0,
        scope='Separate seed construction, physical geometry and native auditor equations; shared NumPy runtime and declared sampling contract.')
    s.dump(output/'DYNAMICS_AUDIT.json',report)
    return report
