"""Fresh recipient assays only; this module has no writer or rule-label input."""
import json
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
import support as s

READER=s.reference('E022_reader_compensation.model')


def read_body(weights,masks,birth,noise,cfg):
    original=np.asarray(weights).tobytes()
    w=np.array(weights,dtype=np.float64,copy=True)
    if w.ndim!=4 or w.shape[1:]!=(2,16,16) or not np.isfinite(w).all(): raise ValueError('Invalid packets')
    p=s.ports()
    if masks.dtype!=bool or masks.ndim!=3 or masks.shape[1:]!=(16,16) or (masks&p.any(axis=0)).any():
        raise ValueError('Invalid damage masks')
    if birth.ndim!=5 or birth.shape[1:]!=(len(masks),2,16,16) or not np.isfinite(birth).all():
        raise ValueError('Invalid paired-cue initial states')
    if not 0<=cfg['settling_steps']<cfg['read_steps'] or not 0<cfg['observe_steps']<=cfg['read_steps']:
        raise ValueError('Invalid read schedule')
    available=READER.surviving_edges(masks)
    physical=w[:,None]*available[None]
    denominator=READER.incident_sum(abs(physical))
    v=np.broadcast_to(birth[None],(len(w),*birth.shape)).copy()
    active=(~masks)[None,None,:,None]
    cue=np.array([1.,-1.])[None,None,None,:,None]
    v*=active;v[...,p[0]]=cue
    late=[];state_hashes=[];noise_hashes=[];namespace=SimpleNamespace(**cfg)
    count=0
    for t,draw in enumerate(noise):
        if t>=cfg['read_steps'] or draw.shape!=birth.shape or not np.isfinite(draw).all():
            raise ValueError('Invalid noise frame')
        noise_hashes.append(s.digest(draw))
        v=READER.compensated_step(v,physical[:,None,:,None],denominator[:,None,:,None],draw[None],
            namespace,amplification=t>=cfg['settling_steps'])
        v*=active;v[...,p[0]]=cue
        state_hashes.append(s.digest(v))
        if t>=cfg['read_steps']-cfg['observe_steps']:
            late.append(np.stack((v[...,p[1]].mean(axis=-1),v[...,p[2]].mean(axis=-1)),axis=-1))
        count+=1
    if count!=cfg['read_steps'] or not np.isfinite(v).all(): raise ValueError('Incomplete or nonfinite assay')
    if original!=np.asarray(weights).tobytes(): raise ValueError('Packet mutated during assay')
    late=np.stack(late)
    return dict(incoming=w,masks=masks.copy(),birth=birth.copy(),available=available,physical=physical,
        denominator=denominator,read_end=v,late_ports=late,mean_ports=late.mean(axis=0),
        state_hashes=np.stack(state_hashes),noise_hashes=np.stack(noise_hashes))


def simulate(weights,context,cfg):
    masks,birth,noise=s.draws(context,cfg)
    return read_body(weights,np.repeat(masks,cfg['replicates_per_mask'],axis=0),birth,noise,cfg)


def run_events(output,mode):
    output=Path(output);folder=output/'events';folder.mkdir(exist_ok=False)
    contexts,weights=s.cases(mode);cfg=s.config(mode);entries=[];started=time.monotonic()
    for i,context in enumerate(contexts):
        began=time.monotonic();raw=simulate(weights[i],context,cfg)
        path=folder/(context['id']+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**raw)
        entry=dict(context_index=i,context_id=context['id'],key=s.key(context),path=str(path.relative_to(output)),
            sha256=s.sha(path),paired_cue_assays=len(s.NAMES)*len(s.PLAN['assay_pairings'])*cfg['masks_per_context']*cfg['replicates_per_mask'],
            seconds=time.monotonic()-began)
        entries.append(entry)
        with (output/'events.jsonl').open('a') as f:f.write(json.dumps(entry,sort_keys=True)+'\n')
        print(json.dumps(dict(phase='simulated',context=context['id'],utc=s.utc())),flush=True)
    s.dump(output/'EVENTS.json',dict(mode=mode,cfg=cfg,contexts=contexts,packet_names=s.NAMES,
        assay_pairings=s.PLAN['assay_pairings'],events=entries,paired_cue_assays=sum(e['paired_cue_assays'] for e in entries),
        native_rebuilds=0,simulation_seconds=time.monotonic()-started))
    return time.monotonic()-started
