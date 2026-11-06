"""E111 continuation equations with the frozen E114 initial-state intervention."""
import numpy as np
from common import rng
from E105_cycle_input_control.model import old,base,reader,P,structural
from E106_fresh_reader_sign_control.model import score
from E108_reader_factorial.model import seed,read_indices
from E111_halfway_component_cross.model import validate_state
from E114_matched_component_amplitude.normalization import initial
from E114_matched_component_amplitude.plan import CONDITIONS

def read_batch(inter,sources,norm,task,draw,cfg,condition):
    assert condition in CONDITIONS
    assert cfg['switch_step']==cfg['reader']['settling_steps']
    start=cfg['switch_step'];stop=cfg['reader']['read_steps'];assert 0<start<stop
    idx=read_indices(inter);n=len(idx);R=cfg['recipients'];ref=sources['O']
    assert idx.tobytes()==ref['indices'].tobytes()==sources['N']['indices'].tobytes()
    masks=old.masks(task,R,f'E102_terminal_{draw}_injury',0)
    assert masks.tobytes()==inter['injury_masks'][draw].tobytes()==ref['masks'].tobytes()
    w=base.decode(inter['packets']);selected=np.array([w[4*v+a,f,r] for v,a,f,r in idx]).reshape(n,2,16,16)
    used=np.array([masks[f,r] for _,_,f,r in idx],bool).reshape(n,16,16)
    effective=selected*reader.surviving_edges(used);den,k=old.coupling(effective)
    for name,value in (('effective',effective),('denominator',den),('coupling',k),('used_masks',used)):
        assert value.tobytes()==ref[name].tobytes()==sources['N'][name].tobytes(),name
    state=initial(sources,norm,condition[:2]);injected=state.copy();stream=rng(*seed(condition[2],task,draw))
    source_birth=cfg['config']['birth_sd']*base.paired_founders(stream.standard_normal((2,R,16,16)))
    assert source_birth.tobytes()==ref['source_births'][int(condition[2]=='N')].tobytes()
    live=(~used)[:,None];config=base.Config(recipients=R,dt=cfg['config']['dt'],noise=cfg['config']['noise'])
    hashes=[];noise_hashes=[];trace=[];boundary=np.zeros(n,np.int64);observed=((~used)&~P.any(0))[:,None]
    owner=int(condition[2]=='N')
    for t in range(stop if n else 0):
        noise=base.paired_founders(stream.standard_normal((2,R,16,16)))
        h=old.digest(noise);assert h.tobytes()==ref['source_noise_hashes'][t,owner].tobytes()
        if t<start:continue
        eta=np.array([noise[f,r] for _,_,f,r in idx])[:,None]
        state=reader.compensated_step(state,effective[:,None],den[:,None],eta,config,True)
        state*=live;state[...,P[0]]=base.CUES.reshape(1,2,1)
        hashes.append(old.digest(state));noise_hashes.append(h)
        boundary+=((abs(state)==2.)&observed).sum((-3,-2,-1))
        if t>=stop-cfg['config']['observe_steps']:
            trace.append(np.stack([state[...,P[p]].mean(-1) for p in (1,2)],axis=-1))
    trace=np.stack(trace) if n else np.empty((cfg['config']['observe_steps'],0,2,2))
    validate_state(state,used)
    return dict(indices=idx,masks=masks,used_masks=used,effective=effective,denominator=den,coupling=k,
        source_states=np.stack([sources[o]['switch_state'] for o in ('O','N')]),initial_state=injected,
        end=state,late_ports=trace,mean_ports=trace.mean(0),boundary_counts=boundary,
        absolute_steps=np.arange(start,stop,dtype=np.int64) if n else np.empty(0,np.int64),
        state_hashes=np.array(hashes,np.uint8).reshape(-1,32),noise_hashes=np.array(noise_hashes,np.uint8).reshape(-1,32),
        source_noise_hashes=ref['source_noise_hashes'][start:stop].copy() if n else np.empty((0,2,32),np.uint8))
