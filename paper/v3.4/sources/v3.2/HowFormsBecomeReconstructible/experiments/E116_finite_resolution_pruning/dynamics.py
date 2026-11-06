"""Exact-input reuse; every new continuation gets an independent full replay."""
import time
import numpy as np
from E116_finite_resolution_pruning import model,audit,data
from E116_finite_resolution_pruning.plan import BODY_FIELDS


def record_key(packet, floor, f, r):
    return int(f),int(r),float(floor),packet.tobytes()


def archived_cache(packets, archived):
    """One phase only; the caller checks masks, birth and all reference scores."""
    cache={}; n,F,R=packets.shape[:3]
    for s,f,r in np.ndindex(n,F,R):
        value={k:(archived[k][:,s,f,r].copy() if k=='late_ports' else archived[k][s,f,r].copy())
               for k in BODY_FIELDS}
        key=record_key(packets[s,f,r],0.,f,r)
        if key in cache:
            for k in value:data.equal(value[k],cache[key][k],k)
        else:cache[key]=value
    return cache


def resolve(panels, floors, task, cfg, phase, generation, cache, run, name):
    """Panels (panel, slot, founder, recipient, bytes); no outcome-based sharing."""
    shape=panels.shape[:-1]; assert shape[2:]==(4,cfg['recipients'])
    flat=panels.reshape(-1,4096)
    contexts=np.array([(f,r) for p,s,f,r in np.ndindex(shape)],np.int64)
    eps=np.broadcast_to(np.array(floors)[:,None,None,None],shape).reshape(-1)
    lookup={}; unique=[];keys=[];mapping=[];reused=0
    for i,(packet,e,(f,r)) in enumerate(zip(flat,eps,contexts)):
        k=record_key(packet,e,f,r)
        if k not in lookup:
            lookup[k]=len(unique);unique.append(i);keys.append(k)
        mapping.append(lookup[k]);reused+=int(k in cache)
    new=[i for i,k in enumerate(keys) if k not in cache]
    outputs=[cache.get(k) for k in keys];seconds=0.;chunks=0
    for offset in range(0,len(new),cfg['chunk_records']):
        ids=new[offset:offset+cfg['chunk_records']];ix=np.array([unique[i] for i in ids])
        tick=time.monotonic()
        a=model.simulate(flat[ix],eps[ix],contexts[ix],task,cfg,phase,generation)
        b=audit.simulate(flat[ix],eps[ix],contexts[ix],task,cfg,phase,generation)
        for k in a:data.equal(a[k],b[k],name+'/'+k)
        seconds+=time.monotonic()-tick;chunks+=1
        if run is not None:
            data.save(run/f'{name}_replay_{offset//cfg["chunk_records"]:03d}_{task}.npz',
                dict(indices=ix,contexts=contexts[ix],floors=eps[ix],state_hashes=a['state_hashes']))
        for j,u in enumerate(ids):
            outputs[u]={k:a[k][j].copy() for k in BODY_FIELDS}
    mapping=np.array(mapping,np.int64)
    result={k:np.stack([x[k] for x in outputs])[mapping].reshape(*shape,*outputs[0][k].shape)
            for k in BODY_FIELDS}
    result.update(packets=panels.copy(),floors=eps.reshape(shape),contexts=contexts.reshape(*shape,2),
                  reuse_map=mapping.reshape(shape),unique_flat_indices=np.array(unique,np.int64),
                  unique_from_archive=np.array([k in cache for k in keys]))
    # Static fields are independently checked even for archived trajectories.
    R=cfg['recipients'];mask=model.old.masks(task,R,phase+'_injury',generation)
    imask=audit.legacy.masks(task,R,phase+'_injury',generation);data.equal(mask,imask,'mask')
    m=mask[contexts[:,0],contexts[:,1]]
    a=model.structure(flat,m,eps);b=audit.structure(flat,m,eps)
    for k,x,y in zip(('effective','denominator','effective_denominator','coupling'),a,b):
        data.equal(x,y,k);result[k]=x.reshape(*shape,*x.shape[1:])
    d,eff=result['denominator'],result['effective_denominator']
    result['attenuation']=np.divide(d,eff,out=np.zeros_like(d),where=d>0)
    result['weak_denominator_counts']=((d>0)&(eff>d)).sum(axis=(-2,-1))
    result['isolated_cell_counts']=(d==0).sum(axis=(-2,-1))
    result['masks']=mask
    return result,dict(record_outcomes=len(flat),unique_records=len(keys),archive_outcomes=reused,
        new_records=len(new),deduplicated_new_outcomes=len(flat)-reused-len(new),
        new_record_steps=len(new)*cfg['steps']['read_steps'],chunks=chunks,seconds=seconds,
        all_new_steps_independently_replayed=True)
