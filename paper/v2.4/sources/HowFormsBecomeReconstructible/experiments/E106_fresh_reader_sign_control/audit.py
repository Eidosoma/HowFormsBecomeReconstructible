"""Separate compact equations and original SHA/PCG construction for new streams."""
import numpy as np
from E105_cycle_input_control.audit import old,P,budget_checks,diagnostics


def read_batch(inter,task,draw,cfg):
    R=cfg['recipients'];phase=f'E102_terminal_{draw}'
    mask=old.masks(task,R,phase+'_injury',0);assert np.array_equal(mask,inter['injury_masks'][draw])
    weights=old.unpack(inter['packets']);idx=[]
    for variant,a,f,r in np.ndindex(4,4,4,R):
        if variant==0 or inter['eligible'][a,f,r]:idx.append((variant,a,f,r))
    indices=np.array(idx,np.int16).reshape(-1,4);N=len(idx)
    assert cfg['reader_stream'] in ('E106_fresh','E105_replay')
    random=old.random('E106',task,'terminal',draw) if cfg['reader_stream']=='E106_fresh' else old.random('E077',task,phase,0)
    birth=cfg['config']['birth_sd']*old.pair(random.standard_normal((2,R,16,16)))
    b=np.zeros((N,16,16));used=np.zeros((N,16,16),bool);effective=np.zeros((N,2,16,16))
    for j,(v,a,f,r) in enumerate(idx):
        b[j]=birth[f,r];used[j]=mask[f,r];effective[j]=weights[4*v+a,f,r]*old.alive(mask[f,r])
    den,coupling=old.coupling(effective);state=np.empty((N,2,16,16))
    for j in range(N):
        for cue in range(2):state[j,cue]=b[j]
    live=(~used)[:,None];state*=live;cues=np.array([1.,-1.]).reshape(1,2,1);state[...,P[0]]=cues
    h=effective[:,None,0];vert=effective[:,None,1]
    trace=[];hashes=[];noise_hashes=[];boundary=np.zeros(N,np.int64);observed=((~used)&~P.any(axis=0))[:,None]
    for t in range(cfg['reader']['read_steps'] if N else 0):
        full_noise=old.pair(random.standard_normal((2,R,16,16)));noise_hashes.append(old.digest(full_noise))
        eta=np.array([full_noise[f,r] for _,_,f,r in idx])[:,None]
        incoming=h*np.roll(state,-1,-1)
        incoming=incoming+np.roll(h,1,-1)*np.roll(state,1,-1)
        incoming=incoming+vert*np.roll(state,-1,-2)
        incoming=incoming+np.roll(vert,1,-2)*np.roll(state,1,-2)
        u=np.zeros_like(incoming);np.divide(incoming,den[:,None],out=u,where=den[:,None]>0)
        drift=(state-state**3 if t>=cfg['reader']['settling_steps'] else -state**3)+2.*(u-state)
        state=np.clip(state+cfg['config']['dt']*drift+cfg['config']['noise']*eta,-2.,2.)
        state*=live;state[...,P[0]]=cues;hashes.append(old.digest(state))
        boundary+=((abs(state)==2.)&observed).sum((-3,-2,-1))
        if t>=cfg['reader']['read_steps']-cfg['config']['observe_steps']:
            trace.append(np.stack((state[...,P[1]].mean(-1),state[...,P[2]].mean(-1)),axis=-1))
    trace=np.array(trace) if N else np.empty((cfg['config']['observe_steps'],0,2,2))
    return dict(indices=indices,masks=mask,birth=birth,used_masks=used,used_birth=b,
        effective=effective,denominator=den,coupling=coupling,end=state,late_ports=trace,
        mean_ports=trace.mean(0),noise_hashes=np.array(noise_hashes),state_hashes=np.array(hashes) if N else np.empty((0,32),np.uint8),boundary_counts=boundary)


def score(ports,indices,threshold):
    n=len(indices);m=np.empty((n,2));opposite=np.empty_like(m);transfer=np.empty(n);aligned=np.empty(n)
    for j,(_,_,f,_) in enumerate(indices):
        rule=(1.,-1.,1.,-1.)[f]
        for c,cue in enumerate((1.,-1.)):
            a=rule*cue*ports[j,c,0];b=-rule*cue*ports[j,c,1]
            m[j,c]=a if a<b else b;opposite[j,c]=-a if -a<-b else -b
        transfer[j]=((ports[j,0,0]-ports[j,1,0])-(ports[j,0,1]-ports[j,1,1]))/4
        aligned[j]=transfer[j]*rule
    both=(m>threshold).all(-1);wrong=(m<0).any(-1)
    return dict(margin=m,minimum_margin=m.min(-1),both=both,transfer=transfer,aligned_transfer=aligned,
        correct_signs_below_threshold=(m>0).all(-1)&~both,
        zero_without_wrong_sign=(m==0).any(-1)&~wrong,any_wrong_sign=wrong,
        opposite_rule_success=(opposite>threshold).all(-1))
