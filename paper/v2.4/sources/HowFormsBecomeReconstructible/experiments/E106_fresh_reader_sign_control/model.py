"""New baseline for every case; extra variants only for nonidentical packets."""
import numpy as np
from common import rng
from E105_cycle_input_control.model import old,base,reader,P,structural,diagnostics


def seed_parts(task,draw,cfg):
    assert cfg['reader_stream'] in ('E106_fresh','E105_replay')
    return ('E106',task,'terminal',draw) if cfg['reader_stream']=='E106_fresh' else ('E077',task,f'E102_terminal_{draw}',0)


def read_indices(inter):
    R=inter['eligible'].shape[2]
    return np.array([(v,a,f,r) for v,a,f,r in np.ndindex(4,4,4,R) if v==0 or inter['eligible'][a,f,r]],np.int16).reshape(-1,4)


def read_batch(inter,task,draw,cfg):
    indices=read_indices(inter);R=cfg['recipients'];phase=f'E102_terminal_{draw}'
    masks=old.masks(task,R,phase+'_injury',0);assert np.array_equal(masks,inter['injury_masks'][draw])
    stream=rng(*seed_parts(task,draw,cfg));birth=cfg['config']['birth_sd']*base.paired_founders(stream.standard_normal((2,R,16,16)))
    weights=base.decode(inter['packets']);n=len(indices)
    selected=np.array([weights[4*v+a,f,r] for v,a,f,r in indices]).reshape(n,2,16,16)
    used_masks=np.array([masks[f,r] for _,_,f,r in indices],dtype=bool).reshape(n,16,16)
    used_birth=np.array([birth[f,r] for _,_,f,r in indices]).reshape(n,16,16)
    effective=selected*reader.surviving_edges(used_masks);den,coupling=old.coupling(effective)
    state=np.repeat(used_birth[:,None],2,axis=1);live=(~used_masks)[:,None];state*=live
    cue=base.CUES.reshape(1,2,1);state[...,P[0]]=cue
    config=base.Config(recipients=R,dt=cfg['config']['dt'],noise=cfg['config']['noise'])
    trace=[];hashes=[];noise_hashes=[];boundary=np.zeros(n,np.int64);observed=((~used_masks)&~P.any(axis=0))[:,None]
    for t in range(cfg['reader']['read_steps'] if n else 0):
        noise=base.paired_founders(stream.standard_normal((2,R,16,16)));noise_hashes.append(old.digest(noise))
        eta=np.array([noise[f,r] for _,_,f,r in indices])[:,None]
        state=reader.compensated_step(state,effective[:,None],den[:,None],eta,config,t>=cfg['reader']['settling_steps'])
        state*=live;state[...,P[0]]=cue;hashes.append(old.digest(state))
        boundary+=((abs(state)==2.)&observed).sum(axis=(-3,-2,-1))
        if t>=cfg['reader']['read_steps']-cfg['config']['observe_steps']:
            trace.append(np.stack([state[...,P[p]].mean(axis=-1) for p in (1,2)],axis=-1))
    trace=np.stack(trace) if n else np.empty((cfg['config']['observe_steps'],0,2,2))
    return dict(indices=indices,masks=masks,birth=birth,used_masks=used_masks,used_birth=used_birth,
        effective=effective,denominator=den,coupling=coupling,end=state,late_ports=trace,
        mean_ports=trace.mean(axis=0),noise_hashes=np.stack(noise_hashes),state_hashes=np.stack(hashes) if n else np.empty((0,32),np.uint8),boundary_counts=boundary)


def score(ports,indices,threshold):
    rules=base.RULES[indices[:,2]];desired=rules[:,None]*base.CUES[None]
    a=desired*ports[...,0];b=-desired*ports[...,1];m=np.minimum(a,b)
    transfer=((ports[:,0,0]-ports[:,1,0])-(ports[:,0,1]-ports[:,1,1]))/4
    both=(m>threshold).all(axis=-1);wrong=(m<0).any(axis=-1)
    return dict(margin=m,minimum_margin=m.min(axis=-1),both=both,transfer=transfer,
        aligned_transfer=transfer*rules,correct_signs_below_threshold=(m>0).all(axis=-1)&~both,
        zero_without_wrong_sign=(m==0).any(axis=-1)&~wrong,any_wrong_sign=wrong,
        opposite_rule_success=(np.minimum(-a,-b)>threshold).all(axis=-1))
