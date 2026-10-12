"""Fixed-packet nonlinear reads; native arithmetic with explicit sample axes."""
from collections import deque
import hashlib
import json

import numpy as np

PORTS=np.zeros((3,16,16),bool)
for i,(y,x) in enumerate(((7,1),(3,10),(11,10))):
    PORTS[i,y:y+2,x:x+2]=True
CUES=np.array([1.,-1.])


def stream(tag,*parts):
    key=json.dumps([tag,*parts],separators=(',',':')).encode()
    seed=int.from_bytes(hashlib.sha256(key).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed))


def generators(cfg,block,replicates,original=False):
    if original:
        return [stream('E022',block,'develop',14) for _ in replicates]
    return [stream(cfg['random_namespace'],block,'read',int(rep)) for rep in replicates]


def decode(packets):
    assert packets.dtype==np.uint8 and packets.shape[-1]==4096
    return np.frombuffer(packets.tobytes(),dtype='<f8').reshape(*packets.shape[:-1],2,16,16).copy()


def available(mask):
    live=~mask
    return np.stack((live & np.roll(live,-1,-1),live & np.roll(live,-1,-2)),axis=-3)


def incident(w):
    h,v=w[...,0,:,:],w[...,1,:,:]
    return h+np.roll(h,1,-1)+v+np.roll(v,1,-2)


def step(value,weights,denominator,noise,cfg,amplification):
    h,v=weights[...,0,:,:],weights[...,1,:,:]
    incoming=(h*np.roll(value,-1,-1)+np.roll(h,1,-1)*np.roll(value,1,-1)
              +v*np.roll(value,-1,-2)+np.roll(v,1,-2)*np.roll(value,1,-2))
    local=np.divide(incoming,denominator,out=np.zeros_like(incoming),where=denominator>0)
    drift=(value-value**3 if amplification else -value**3)+2.*(local-value)
    return np.clip(value+cfg['dt']*drift+cfg['noise']*noise,-2.,2.)


def draw(random, founders, recipients):
    # Every replicate draws the complete native founder/recipient panel. Selection,
    # packet order and count cannot alter the sequence for any retained context.
    base=np.stack([r.standard_normal((2,4,16,16)) for r in random])
    selected=base[:,founders//2,recipients].transpose(1,0,2,3)
    return np.repeat(selected[:,:,None],2,axis=2)


def read_fixed(packets,masks,founders,recipients,random,cfg,budgets,settling_steps):
    """Return arrays with budget, case, variant, replicate, cue, spatial axes."""
    assert packets.ndim==3 and packets.shape[-1]==4096
    n,variants=packets.shape[:2]
    reps=len(random)
    assert masks.shape==(n,16,16) and founders.shape==recipients.shape==(n,)
    assert np.all((0<=founders)&(founders<4)) and np.all((0<=recipients)&(recipients<4))
    assert not (masks & PORTS.any(axis=0)).any()
    assert budgets==sorted(set(budgets)) and min(budgets)>=cfg['observe_steps']
    effective=decode(packets)*available(masks)[:,None]
    denominator=incident(abs(effective))
    weights=effective[:,:,None,None]
    den=denominator[:,:,None,None]
    birth=cfg['birth_sd']*draw(random,founders,recipients)
    value=np.repeat(birth[:,None],variants,axis=1)
    alive=(~masks)[:,None,None,None]
    cue=CUES.reshape(1,1,1,2,1)
    value*=alive
    value[...,PORTS[0]]=cue
    recent=deque(maxlen=cfg['observe_steps'])
    windows,means,end=[],[],[]
    for t in range(max(budgets)):
        noise=draw(random,founders,recipients)[:,None]
        value=step(value,weights,den,noise,cfg,t>=settling_steps)
        value*=alive
        value[...,PORTS[0]]=cue
        # Port means only need to be collected in declared endpoint windows.
        if any(b-cfg['observe_steps']<=t<b for b in budgets):
            recent.append(np.stack((value[...,PORTS[1]].mean(axis=-1),value[...,PORTS[2]].mean(axis=-1)),axis=-1))
        if t+1 in budgets:
            assert len(recent)==cfg['observe_steps']
            window=np.stack(recent)
            windows.append(window)
            means.append(window.mean(axis=0))
            end.append(value.copy())
            recent.clear()
    return dict(budgets=np.array(budgets),birth=birth,end=np.stack(end),
                port_windows=np.stack(windows),mean_ports=np.stack(means))


def scores(mean_ports,founders,margin):
    # mean_ports: budget, case, variant, replicate, cue, output port.
    rules=np.where(founders%2==0,1.,-1.)
    aligned=mean_ports*rules[None,:,None,None,None,None]*CUES[None,None,None,None,:,None]*np.array([1.,-1.])[None,None,None,None,None,:]
    minimum=aligned.min(axis=(-2,-1))
    return dict(min_margin=minimum,both_pass=minimum>margin)
