"""Paired record lineages; assessments are pure functions of saved records.

The independent implementation uses indexed updates and independent capture,
mask, packing and score routines inherited from audited finite-rule tests.
"""
import numpy as np
from common import rng
from E077_fresh_reconstruction_tradeoff import model as old
from E116_finite_resolution_pruning import model as finite, audit as independent
from E077_fresh_reconstruction_tradeoff.data import equal

base, reader, P = old.base, old.reader, old.P
PLUS = np.r_[np.arange(1,16),0]
MINUS = np.r_[15,np.arange(15)]

def simulate(packets, task, cfg, steps, seed, mask_seed, independent_noise=False,
             no_injury=False, audit=False, pulse=None):
    """Packets A,F,R,B; sharing draws never shares an outgoing treatment record."""
    A,F,R = packets.shape[:-1]
    assert F==4 and R==cfg['recipients'] and packets.dtype==np.uint8
    impl = independent if audit else finite
    legacy = independent.legacy if audit else old
    random = legacy.random if audit else rng
    pair = legacy.pair if audit else base.paired_founders
    mask = legacy.masks(task,R,mask_seed[0],mask_seed[1])
    if no_injury: mask = np.zeros_like(mask)
    w,d,eff,k = impl.structure(packets,mask,0.)
    stream=random(*seed); innovation=random('reviewer_independent_cue',*seed)
    shape=(2,R,16,16)
    birth=cfg['birth_sd']*pair(stream.standard_normal(shape))
    v=np.broadcast_to(birth[None,:,:,None],(A,F,R,2,16,16)).copy()
    live=(~mask)[None,:,:,None];cue=np.array([1.,-1.]).reshape(1,1,1,2,1)
    v*=live;v[...,P[0]]=cue
    initial=v.copy();traces=[];hashes=[];counts=np.zeros((A,F,R),np.int64)
    free=((~mask)&~P.any(axis=0))[None,:,:,None]
    conf=base.Config(recipients=R,dt=cfg['dt'],noise=cfg['noise'])
    right=w[...,None,0,:,:];left=np.take(right,MINUS,axis=-1)
    below=w[...,None,1,:,:];above=np.take(below,MINUS,axis=-2)
    flags=np.broadcast_to(np.asarray(independent_noise,dtype=bool),(A,))
    if pulse:
        # Field is exogenous and matched across all regimes; only pulse arms receive it.
        field=np.zeros((4,R,16,16));sites=np.zeros(field.shape,bool)
        for f,r in np.ndindex(2,R):
            st=random('E055',task,'pulse_field',f,r)
            eligible=np.flatnonzero(~mask[2*f,r].ravel() & ~P.any(axis=0).ravel())
            ids=st.choice(eligible,pulse['sites'],replace=False);values=st.choice(np.array([-1.,1.]),pulse['sites'])
            for member in (2*f,2*f+1):
                field[member,r].ravel()[ids]=values;sites[member,r].ravel()[ids]=True
        pulse_flags=np.asarray(pulse['arms'],bool)[:,None,None,None,None,None]
        before=None
    for t in range(steps['read_steps']):
        z=pair(stream.standard_normal(shape));z2=pair(innovation.standard_normal(shape))
        eta=np.broadcast_to(z[None,:,:,None],v.shape).copy();eta[flags,:,:,1]=z2
        if audit:
            total=right*np.take(v,PLUS,axis=-1)
            total=total+left*np.take(v,MINUS,axis=-1)
            total=total+below*np.take(v,PLUS,axis=-2)
            total=total+above*np.take(v,MINUS,axis=-2)
            u=np.zeros_like(total);np.divide(total,eff[...,None,:,:],out=u,where=eff[...,None,:,:]>0)
            local=v-v**3 if t>=steps['settling_steps'] else -v**3
            v=np.clip(v+cfg['dt']*(local+2.*(u-v))+cfg['noise']*eta,-2.,2.)
        else:
            v=reader.compensated_step(v,w[...,None,:,:,:],eff[...,None,:,:],eta,conf,t>=steps['settling_steps'])
        if pulse and t>=pulse['start']:
            v=np.clip(v+cfg['dt']*pulse['amplitude']*field[None,:,:,None]*pulse_flags,-2.,2.)
        v*=live;v[...,P[0]]=cue
        hashes.append(legacy.digest(v));counts+=((abs(v)==2)&free).sum(axis=(-3,-2,-1))
        if pulse and t+1==pulse['start']:before=v.copy()
        if t>=steps['read_steps']-cfg['observe_steps']:
            traces.append(np.stack((v[...,P[1]].mean(axis=-1),v[...,P[2]].mean(axis=-1)),axis=-1))
    trace=np.stack(traces)
    out=dict(incoming=packets.copy(),masks=mask,effective=w,denominator=d,coupling=k,
             birth=birth,initial=initial,end=v,late_ports=trace,mean_ports=trace.mean(axis=0),
             state_hashes=np.stack(hashes),boundary_counts=counts)
    if pulse:out.update(before=before,pulse_field=field,pulse_sites=sites)
    return out

def capture(body,tolerance,audit=False):
    impl=independent if audit else finite
    physical=independent.legacy.alive(body['masks']) if audit else reader.surviving_edges(body['masks'])
    tolerances=np.broadcast_to(np.asarray(tolerance),(len(body['end']),))
    values=[impl.capture(x,physical,float(t)) for x,t in zip(body['end'],tolerances)]
    result={k:np.stack([v[k] for v in values]) for k in values[0]}
    result['outgoing']=result['pre_channel'].copy()
    return result

def checked_body(packets,task,cfg,steps,seed,mask_seed,independent_noise=False,
                 no_injury=False,pulse=None,tolerance=None):
    a=simulate(packets,task,cfg,steps,seed,mask_seed,independent_noise,no_injury,False,pulse)
    b=simulate(packets,task,cfg,steps,seed,mask_seed,independent_noise,no_injury,True,pulse)
    equal(a,b)
    if tolerance is not None:
        ca=capture(a,tolerance);cb=capture(b,tolerance,True);equal(ca,cb);a.update(ca)
    return a

def scores(body):
    shape=body['mean_ports'].shape[:-2]
    founders=np.broadcast_to(np.arange(4)[None,:,None],shape).ravel()
    mean=body['mean_ports'].reshape(-1,2,2)
    a=finite.scores(mean,founders);equal(a,independent.scores(mean,founders))
    return {k:v.reshape(shape) for k,v in a.items()}

def selection(incoming,outgoing,fallback,route='fallback'):
    w0,w1=base.decode(incoming),base.decode(outgoing)
    selected=(w0==0)&(w1!=0)
    if route=='fallback':selected &= fallback
    else:assert route=='restored'
    # Independent Boolean form, including empty operations.
    a=independent.legacy.unpack(incoming);b=independent.legacy.unpack(outgoing)
    expected=np.logical_and(np.equal(a,0),np.not_equal(b,0))
    if route=='fallback':expected=np.logical_and(expected,fallback)
    assert selected.tobytes()==expected.tobytes()
    return selected

def prune(packets,selected):
    w=base.decode(packets);out=w.copy();out[selected]=0.
    other=independent.legacy.unpack(packets).copy();other=np.where(selected,0.,other)
    p=base.encode(out);assert p.tobytes()==independent.legacy.pack(other).tobytes()
    assert out[~selected].tobytes()==w[~selected].tobytes()
    return p

def structure_diagnostics(intact,pruned,selected):
    wi,wp=base.decode(intact),base.decode(pruned)
    di,ki=old.coupling(wi);dp,kp=old.coupling(wp)
    reiso=(di>0)&(dp==0)&~P.any(axis=0)
    return dict(reisolated=reiso,reisolated_cells=reiso.sum(axis=(-2,-1)),
        intact_denominator=di,pruned_denominator=dp,
        selected_edges=selected.sum(axis=(-3,-2,-1)),
        selected_mass=(abs(wi)*selected).sum(axis=(-3,-2,-1)),
        selected_coupling_share=old.fraction((abs(ki)*old.directed(selected)).sum(axis=(-3,-2,-1)),abs(ki).sum(axis=(-3,-2,-1))),
        coupling_l1_per_cell=abs(ki-kp).sum(axis=(-3,-2,-1))/256,
        intact_isolated=((di==0)&~P.any(axis=0)).sum(axis=(-2,-1)),
        pruned_isolated=((dp==0)&~P.any(axis=0)).sum(axis=(-2,-1)))
