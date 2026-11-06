"""Independent E111 update equations, with scalar E114 state construction."""
import numpy as np
from E105_cycle_input_control.audit import old,P,budget_checks
from E106_fresh_reader_sign_control.audit import score
from E114_matched_component_amplitude.normalization_audit import initial

def read_batch(inter,sources,norm,task,draw,cfg,condition):
    assert len(condition)==3 and set(condition)<=set('ON')
    R=cfg['recipients'];split=cfg['switch_step'];stop=cfg['reader']['read_steps']
    assert split==cfg['reader']['settling_steps'] and 0<split<stop
    idx=[]
    for v in range(2,4):
        for a in range(4):
            for f in range(4):
                for r in range(R):
                    if inter['eligible'][a,f,r]:idx.append((v,a,f,r))
    n=len(idx);indices=np.array(idx,np.int16).reshape(-1,4)
    mask=old.masks(task,R,f'E102_terminal_{draw}_injury',0)
    assert mask.tobytes()==inter['injury_masks'][draw].tobytes()
    w=old.unpack(inter['packets']);used=np.zeros((n,16,16),bool);effective=np.zeros((n,2,16,16))
    for j,(v,a,f,r) in enumerate(idx):
        used[j]=mask[f,r];effective[j]=w[4*v+a,f,r]*old.alive(mask[f,r])
    den,k=old.coupling(effective);state=initial(sources,norm,condition[:2]);injected=state.copy()
    assert np.isfinite(state).all() and (abs(state)<=2).all()
    assert not state[np.broadcast_to(used[:,None],state.shape)].any()
    cues=np.array([1.,-1.]).reshape(1,2,1)
    assert np.array_equal(state[...,P[0]],np.broadcast_to(cues,state[...,P[0]].shape))
    g=old.random('E077',task,f'E102_terminal_{draw}',0) if condition[2]=='O' else old.random('E106',task,'terminal',draw)
    birth=cfg['config']['birth_sd']*old.pair(g.standard_normal((2,R,16,16)))
    assert birth.tobytes()==sources['O']['source_births'][int(condition[2]=='N')].tobytes()
    bank=np.array([old.pair(g.standard_normal((2,R,16,16))) for _ in range(stop if n else 0)])
    live=(~used)[:,None];h=effective[:,None,0];vert=effective[:,None,1]
    trace=[];hashes=[];noise_hashes=[];boundary=np.zeros(n,np.int64);observed=((~used)&~P.any(0))[:,None]
    for t in range(split,stop) if n else ():
        noise=bank[t];eta=np.array([noise[f,r] for _,_,f,r in idx])[:,None]
        noise_hashes.append(old.digest(noise))
        incoming=h*np.roll(state,-1,-1)
        incoming=incoming+np.roll(h,1,-1)*np.roll(state,1,-1)
        incoming=incoming+vert*np.roll(state,-1,-2)
        incoming=incoming+np.roll(vert,1,-2)*np.roll(state,1,-2)
        u=np.zeros_like(incoming);np.divide(incoming,den[:,None],out=u,where=den[:,None]>0)
        drift=state-state**3+2.*(u-state)
        state=np.clip(state+cfg['config']['dt']*drift+cfg['config']['noise']*eta,-2.,2.)
        state*=live;state[...,P[0]]=cues;hashes.append(old.digest(state))
        boundary+=((abs(state)==2.)&observed).sum((-3,-2,-1))
        if t>=stop-cfg['config']['observe_steps']:
            trace.append(np.stack((state[...,P[1]].mean(-1),state[...,P[2]].mean(-1)),axis=-1))
    trace=np.array(trace) if n else np.empty((cfg['config']['observe_steps'],0,2,2))
    return dict(indices=indices,masks=mask,used_masks=used,effective=effective,denominator=den,coupling=k,
        source_states=np.stack([sources[o]['switch_state'] for o in ('O','N')]),initial_state=injected,
        end=state,late_ports=trace,mean_ports=trace.mean(0),boundary_counts=boundary,
        absolute_steps=np.arange(split,stop,dtype=np.int64) if n else np.empty(0,np.int64),
        state_hashes=np.array(hashes,np.uint8).reshape(-1,32),noise_hashes=np.array(noise_hashes,np.uint8).reshape(-1,32),
        source_noise_hashes=sources['O']['source_noise_hashes'][split:stop].copy() if n else np.empty((0,2,32),np.uint8))
