"""Independent indexed state update, channel, branch and lineage construction."""
import numpy as np
from E116_finite_resolution_pruning import audit as finite
from E055_stress_capture_recovery.audit_model import masks as damage_masks
from E118_finite_formation.plan import REGIMES,parameters
old=finite.legacy
P=old.P
PLUS=np.r_[np.arange(1,16),0];MINUS=np.r_[15,np.arange(15)]

def channel(packets):
    return np.array([finite.quantize(p,parameters(r)['grid']) for p,r in zip(packets,REGIMES)])

def capture(incoming,end,masks,beta):
    parts=[]
    for i,r in enumerate(REGIMES):parts.append(finite.capture(end[i],old.alive(masks),parameters(r)['tolerance'],beta))
    out={k:np.array([a[k] for a in parts]) for k in parts[0]}
    out['outgoing']=channel(out['pre_channel']);return out

def develop(incoming,task,cfg,steps,namespace,generation=0,pulse=None):
    K,N,F,R=incoming.shape[:-1]
    if namespace in ('E022','E058'):
        mask=damage_masks(task,R,f'{namespace}_renewal_g{generation}')[:,:,1]
        seed=(namespace,task,'develop',generation)
    else:
        assert namespace=='E055' and N==2 and pulse is not None
        mask=damage_masks(task,R,'E055_current_body')[:,:,1];seed=('E055',task,'current_body')
    floors=np.array([parameters(r)['floor'] for r in REGIMES])[:,None,None,None]
    effective,d,eff,k=finite.structure(incoming,mask,floors)
    stream=old.random(*seed);shape=(2,R,16,16)
    birth=cfg['birth_sd']*old.pair(stream.standard_normal(shape))
    v=np.empty((K,N,F,R,2,16,16))
    for regime,slot,cue in np.ndindex(K,N,2):v[regime,slot,:,:,cue]=birth
    live=(~mask)[None,None,:,:,None];cues=np.array([1.,-1.]).reshape(1,1,1,1,2,1)
    v*=live;v[...,P[0]]=cues
    initial=v.copy();trace=[];hashes=[];reference_hashes=[];before=None
    counts=np.zeros((K,N,F,R),np.int64);free=((~mask)&~P.any(axis=0))[None,None,:,:,None]
    right=effective[...,None,0,:,:];left=np.take(right,MINUS,axis=-1)
    below=effective[...,None,1,:,:];above=np.take(below,MINUS,axis=-2)
    if pulse:
        field=np.zeros((F,R,16,16));sites=np.zeros(field.shape,bool)
        for f,r in np.ndindex(2,R):
            g=old.random('E055',task,'pulse_field',f,r)
            eligible=np.array([i for i in range(256) if not mask[2*f,r].ravel()[i] and not P.any(axis=0).ravel()[i]])
            ids=g.choice(eligible,pulse['pulse_sites'],replace=False);values=g.choice(np.array([-1.,1.]),pulse['pulse_sites'])
            for member in (2*f,2*f+1):field[member,r].ravel()[ids]=values;sites[member,r].ravel()[ids]=True
        requested=np.zeros((K,F,R,2));delivered=np.zeros_like(requested);clipped=np.zeros(requested.shape,np.int64);before_trace=[]
    for t in range(steps['read_steps']):
        eta=old.pair(stream.standard_normal((2,R,2,16,16) if pulse else shape))
        noise=eta[None,None] if pulse else eta[None,None,:,:,None]
        total=right*np.take(v,PLUS,axis=-1)
        total=total+left*np.take(v,MINUS,axis=-1)
        total=total+below*np.take(v,PLUS,axis=-2)
        total=total+above*np.take(v,MINUS,axis=-2)
        u=np.zeros_like(v);np.divide(total,eff[...,None,:,:],out=u,where=eff[...,None,:,:]>0)
        local=v-v**3 if t>=steps['settling_steps'] else -v**3
        v=np.clip(v+cfg['dt']*(local+2.*(u-v))+cfg['noise']*noise,-2.,2.)
        if pulse and t>=pulse['body_pre_steps']:
            force=cfg['dt']*pulse['pulse_amplitude']*field[None,:,:,None]
            proposal=v[:,1]+force;actual=np.minimum(2.,np.maximum(-2.,proposal))
            requested+=np.broadcast_to(force**2,v[:,1].shape).sum(axis=(-2,-1))
            delivered+=((actual-v[:,1])**2).sum(axis=(-2,-1));clipped+=((proposal < -2.)|(proposal > 2.)).sum(axis=(-2,-1))
            v[:,1]=actual
        v*=live;v[...,P[0]]=cues
        hashes.append(old.digest(v));reference_hashes.append(old.digest(v[0]))
        counts+=np.count_nonzero((abs(v)==2)&free,axis=(-3,-2,-1))
        if t>=steps['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,P[1]].mean(axis=-1),v[...,P[2]].mean(axis=-1)),axis=-1))
        if pulse:
            if pulse['body_pre_steps']-cfg['observe_steps']<=t<pulse['body_pre_steps']:
                before_trace.append(np.stack((v[...,P[1]].mean(axis=-1),v[...,P[2]].mean(axis=-1)),axis=-1))
            if t==pulse['body_pre_steps']-1:before=v.copy()
    trace=np.array(trace)
    out=dict(incoming=incoming.copy(),masks=mask,effective=effective,denominator=d,effective_denominator=eff,
        coupling=k,birth=birth,initial=initial,end=v,late_ports=trace,mean_ports=trace.mean(axis=0),
        state_hashes=np.array(hashes),reference_hashes=np.array(reference_hashes),boundary_counts=counts)
    if pulse:out.update(before=before,before_ports=np.array(before_trace),pulse_field=field,pulse_sites=sites,
                        requested_squared=requested,delivered_squared=delivered,clipping_count=clipped)
    return out

def mixture(initial,final):
    oldw,last=old.unpack(initial),old.unpack(final);common=(oldw!=0)&(last!=0)
    mixed=np.where(common,np.copysign(abs(oldw),last),last)
    pre=old.pack(np.concatenate((last,mixed,np.zeros_like(last[:,:1])),axis=1))
    return dict(initial=initial,final=final,common=common,pre_channel=pre,packets=channel(pre))

def prune(recovery):
    before=old.unpack(recovery['incoming'])[:,:4];pre=old.unpack(recovery['pre_channel'])[:,:4]
    after=old.unpack(recovery['outgoing']);selected=np.zeros(before.shape,bool)
    result=np.concatenate((after[:,:4],after[:,:4],after[:,4:5]),axis=1)
    for k,a,f,r,e,y,x in np.ndindex(before.shape):
        pos=k,a,f,r,e,y,x
        if before[pos]==0 and pre[pos]!=0 and recovery['fallback'][pos]:
            selected[pos]=True;result[k,a+4,f,r,e,y,x]=0.
    return dict(packets=old.pack(result),selected=selected,delivered_selected=selected&(after[:,:4]!=0))
