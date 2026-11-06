"""Five independent record histories with matched exogenous random streams."""
import numpy as np
from common import rng
from E116_finite_resolution_pruning import model as finite
from E055_stress_capture_recovery.model import pulse_field
from E118_finite_formation.plan import REGIMES,parameters
base,reader,P=finite.base,finite.reader,finite.P

def channel(packets):
    return np.stack([finite.quantize(p,parameters(r)['grid']) for p,r in zip(packets,REGIMES)])

def capture(incoming,end,masks,beta):
    physical=reader.surviving_edges(masks)
    parts=[finite.capture(state,physical,parameters(r)['tolerance'],beta) for state,r in zip(end,REGIMES)]
    out={k:np.stack([p[k] for p in parts]) for k in parts[0]}
    out['outgoing']=channel(out['pre_channel'])
    return out

def develop(incoming,task,cfg,steps,namespace,generation=0,pulse=None):
    K,N,F,R=incoming.shape[:-1]
    conf=base.Config(**cfg)
    if namespace in ('E022','E058'):
        mask=base.damage_masks(task,f'{namespace}_renewal_g{generation}',conf)[:,:,1]
        seed=(namespace,task,'develop',generation)
    else:
        assert namespace=='E055' and N==2 and pulse is not None
        mask=base.damage_masks(task,'E055_current_body',conf)[:,:,1]
        seed=('E055',task,'current_body')
    floors=np.array([parameters(r)['floor'] for r in REGIMES])[:,None,None,None]
    effective,d,eff,k=finite.structure(incoming,mask,floors)
    stream=rng(*seed);shape=(2,R,16,16)
    birth=cfg['birth_sd']*base.paired_founders(stream.standard_normal(shape))
    v=np.broadcast_to(birth[None,None,:,:,None],(K,N,F,R,2,16,16)).copy()
    live=(~mask)[None,None,:,:,None];cue=base.CUES.reshape(1,1,1,1,2,1)
    v*=live;v[...,P[0]]=cue
    initial=v.copy();trace=[];hashes=[];reference_hashes=[];before=None
    count=np.zeros((K,N,F,R),np.int64);free=((~mask)&~P.any(axis=0))[None,None,:,:,None]
    if pulse:
        field,sites=pulse_field(mask,task,pulse['pulse_sites'])
        requested=np.zeros((K,F,R,2));delivered=np.zeros_like(requested);clipped=np.zeros(requested.shape,np.int64)
        before_trace=[]
    for t in range(steps['read_steps']):
        shape_noise=(2,R,2,16,16) if pulse else shape
        eta=base.paired_founders(stream.standard_normal(shape_noise))
        noise=eta[None,None] if pulse else eta[None,None,:,:,None]
        v=reader.compensated_step(v,effective[...,None,:,:,:],eff[...,None,:,:],noise,conf,t>=steps['settling_steps'])
        if pulse and pulse['body_pre_steps']<=t:
            increment=cfg['dt']*pulse['pulse_amplitude']*field[None,:,:,None]
            proposal=v[:,1]+increment;actual=np.clip(proposal,-2.,2.)
            requested+=np.broadcast_to(increment*increment,v[:,1].shape).sum(axis=(-2,-1))
            delivered+=((actual-v[:,1])**2).sum(axis=(-2,-1));clipped+=(abs(proposal)>2).sum(axis=(-2,-1))
            v[:,1]=actual
        v*=live;v[...,P[0]]=cue
        hashes.append(finite.old.digest(v));reference_hashes.append(finite.old.digest(v[0]))
        count+=((abs(v)==2)&free).sum(axis=(-3,-2,-1))
        if t>=steps['read_steps']-cfg['observe_steps']:
            trace.append(np.stack([v[...,P[p]].mean(axis=-1) for p in (1,2)],axis=-1))
        if pulse:
            if pulse['body_pre_steps']-cfg['observe_steps']<=t<pulse['body_pre_steps']:
                before_trace.append(np.stack([v[...,P[p]].mean(axis=-1) for p in (1,2)],axis=-1))
            if t+1==pulse['body_pre_steps']:before=v.copy()
    trace=np.stack(trace)
    out=dict(incoming=incoming.copy(),masks=mask,effective=effective,denominator=d,effective_denominator=eff,
        coupling=k,birth=birth,initial=initial,end=v,late_ports=trace,mean_ports=trace.mean(axis=0),
        state_hashes=np.stack(hashes),reference_hashes=np.stack(reference_hashes),boundary_counts=count)
    if pulse:
        out.update(before=before,before_ports=np.stack(before_trace),pulse_field=field,pulse_sites=sites,
                   requested_squared=requested,delivered_squared=delivered,clipping_count=clipped)
    return out

def mixture(initial,final):
    old,w=base.decode(initial),base.decode(final)
    common=(old!=0)&(w!=0);mixed=w.copy()
    mixed[common]=np.copysign(abs(old[common]),w[common])
    pre=base.encode(np.concatenate((w,mixed,np.zeros_like(w[:,:1])),axis=1))
    return dict(initial=initial,final=final,common=common,pre_channel=pre,packets=channel(pre))

def prune(recovery):
    incoming=base.decode(recovery['incoming'])[:,:4]
    pre=base.decode(recovery['pre_channel'])[:,:4]
    w=base.decode(recovery['outgoing'])
    selected=(incoming==0)&(pre!=0)&recovery['fallback'][:,:4]
    pruned=w[:,:4].copy();pruned[selected]=0.
    return dict(packets=base.encode(np.concatenate((w[:,:4],pruned,w[:,4:5]),axis=1)),
                selected=selected,delivered_selected=selected&(w[:,:4]!=0))
