"""Multiaffine interaction energy and energy-decreasing asynchronous dynamics."""
import numpy as np
from h077 import model as base
from h083 import model as pair

BLOCKS=(np.arange(0,8),np.arange(16,24),np.arange(32,44),np.arange(56,68))
SITE_BLOCK=np.full(128,-1,dtype=int)
for b,sites in enumerate(BLOCKS):SITE_BLOCK[sites]=b
BITS=np.asarray([[(mask>>b)&1 for b in range(4)] for mask in range(16)],dtype=bool)
LOWBIT=[(mask&-mask).bit_length()-1 for mask in range(1,16)]

def basis(means):
    result=np.ones((*means.shape[:-1],16),dtype=means.dtype)
    for mask,b in enumerate(LOWBIT,1):result[...,mask]=result[...,mask^(1<<b)]*means[...,b]
    return result

def means(state):return np.stack([state[...,sites].mean(-1) for sites in BLOCKS],axis=-1)

def factor_fields(record,state):
    masks=record['interaction_masks'];weights=record['interaction_weights'];mu=means(state);phi=basis(mu)
    result=np.zeros(state.shape,dtype=float);result[...,80:]=phi[...,masks]*weights
    contribution=state[...,80:]*weights
    for b,sites in enumerate(BLOCKS):
        h=np.sum(contribution*phi[...,masks&~(1<<b)]*BITS[masks,b],axis=-1)/len(sites)
        result[...,sites]=h[...,None]
    return result

def fields(record,state):return state@record['J'].T+factor_fields(record,state)

def factor_energy(record,state):
    return -np.sum(state[...,80:]*record['interaction_weights']*basis(means(state))[...,record['interaction_masks']],axis=-1)

def energy(record,state):return base.energy(record['J'],state)+factor_energy(record,state)

def effective(record,strength):
    current={k:v for k,v in record.items()};current['J']=record['J'].copy();current['J'][80:,80:]*=strength
    return current

def validate(record):
    assert set(record)=={'J','interaction_masks','interaction_weights'} and record['J'].shape==(128,128)
    assert np.array_equal(record['J'],record['J'].T) and not np.diag(record['J']).any() and np.isfinite(record['J']).all()
    assert record['interaction_masks'].shape==record['interaction_weights'].shape==(48,)
    assert record['interaction_masks'].dtype==np.dtype('int8') and np.isin(record['interaction_masks'],np.arange(16)).all()
    assert record['interaction_weights'].dtype==np.dtype('float64') and np.isin(record['interaction_weights'],[-1.,0.,1.]).all()
    masks=record['interaction_masks'];assert not record['interaction_weights'][((masks&3)==0)|((masks&12)==0)].any()

def segment(packet):
    assert set(packet)=={'record','state','orders','clamp_indices','clamp_values','active_sweeps','feedback'}
    record,state,orders,indices,values,active,tape=(packet[k] for k in ('record','state','orders','clamp_indices','clamp_values','active_sweeps','feedback'))
    validate(record)
    assert np.isin(state,[-1,1]).all() and np.isin(values,[-1,1]).all() and np.isin(tape,[0.,1.]).all()
    assert orders.shape==(len(tape),128) and 0<=active<=len(tape) and len(tape)>0
    assert np.array_equal(np.sort(orders,axis=1),np.broadcast_to(np.arange(128),orders.shape))
    assert len(set(indices.tolist()))==len(indices) and np.isin(indices,np.arange(80)).all()
    state=state.copy();trace=[state.copy()];pre=[];changes=[];starts=[];ends=[];works=[];switches=[];switched=[]
    initial=energy(record,state);previous=initial.copy();maximum=np.zeros(state.shape[:-1]);free=np.ones(128,dtype=bool);free[indices]=False
    masks=record['interaction_masks'];weights=record['interaction_weights'];evaluations=0
    for sweep,order in enumerate(orders):
        current=effective(record,tape[sweep]);after_switch=energy(current,state);switches.append(after_switch-previous);switched.append(after_switch)
        if len(indices):state[...,indices]=values
        start=energy(current,state);pre.append(state.copy());starts.append(start);works.append(start-after_switch)
        flips=np.zeros(state.shape[:-1],dtype=np.int16);mu=means(state);phi=basis(mu)
        for site in order if sweep<active else ():
            if not free[site]:continue
            field=np.einsum('...i,i->...',state,current['J'][site]);b=SITE_BLOCK[site]
            if site>=80:
                j=site-80;field=field+weights[j]*phi[...,masks[j]];evaluations+=int(np.prod(state.shape[:-1]))
            elif b>=0:
                field=field+np.sum(state[...,80:]*weights*phi[...,masks&~(1<<b)]*BITS[masks,b],axis=-1)/len(BLOCKS[b]);evaluations+=int(np.prod(state.shape[:-1]))
            old=state[...,site].copy();new=np.where(field>base.TOL,1,np.where(field < -base.TOL,-1,old)).astype(np.int8)
            maximum=np.maximum(maximum,-(new-old)*field);flips+=(old!=new);state[...,site]=new
            if b>=0 and np.any(old!=new):
                mu[...,b]=state[...,BLOCKS[b]].mean(-1);phi=basis(mu)
        end=energy(current,state);assert np.all(end<=start+2e-11)
        ends.append(end);changes.append(flips);trace.append(state.copy());previous=end
    def flags(rec):
        h=fields(rec,state);nxt=np.where(h>base.TOL,1,np.where(h < -base.TOL,-1,state))
        return h,(nxt[...,free]==state[...,free]).all(-1),(nxt==state).all(-1)
    h,conditional,full=flags(current);nominal,nc,nf=flags(record)
    return dict(initial=trace[0],final=state,trace=np.stack(trace),pre_update=np.stack(pre),changes=np.stack(changes),
        start_energy=np.stack(starts),end_energy=np.stack(ends),clamp_work=np.stack(works),switch_work=np.stack(switches),
        after_switch_energy=np.stack(switched),feedback=tape.copy(),initial_energy=initial,final_energy=previous,max_increase=maximum,
        fields_final=h,conditional_fixed=conditional,full_fixed=full,nominal_fields_final=nominal,
        nominal_conditional_fixed=nc,nominal_full_fixed=nf,nominal_final_energy=energy(record,state),
        interaction_site_evaluations=np.asarray(evaluations,dtype=np.int64))

def kick(record,state):
    h=fields(record,state);i,j=pair.PAIRS.T
    single=2*state[...,pair.FREE]*h[...,pair.FREE]
    delta=2*state[...,i]*h[...,i]+2*state[...,j]*h[...,j]-4*state[...,i]*state[...,j]*record['J'][i,j]
    chosen=pair.choose(delta);after=state.copy();flat=after.reshape(-1,128);indices=chosen.reshape(-1);selected=np.flatnonzero(indices>=0)
    for row in selected:flat[row,pair.PAIRS[indices[row]]]*=-1
    selected_delta=np.zeros(state.shape[:-1]);selected_delta.reshape(-1)[selected]=delta.reshape(-1,pair.PAIR_COUNT)[selected,indices[selected]]
    realized=energy(record,after)-energy(record,state);np.testing.assert_allclose(realized,selected_delta,rtol=0,atol=2e-11)
    assert np.all(realized<=2e-11)
    return dict(fields=h,single_delta=single,pair_delta=delta,choice=chosen,after=after,selected_delta=selected_delta,realized_delta=realized)

def read(packet):
    assert set(packet)=={'record','birth','observed_history','orders_context','orders_gap','orders_query'}
    record=packet['record'];x=packet['observed_history'];validate(record)
    assert x.ndim==2 and x.shape[1]==80 and packet['birth'].shape==(128,) and np.isin(x,[-1,1]).all()
    state=np.broadcast_to(packet['birth'],(len(x),1,128)).copy()
    result={}
    for phase,indices,values,count,feedback in [('context',np.arange(32),x[:,None,:32],4,np.ones(4)),
            ('gap',np.asarray([],dtype=int),np.empty((len(x),1,0),dtype=np.int8),4,np.ones(4)),
            ('query',np.arange(32,80),x[:,None,32:],8,np.r_[0.,np.ones(7)])]:
        saved=segment(dict(record=record,state=state,orders=packet['orders_'+phase],clamp_indices=indices,clamp_values=values,active_sweeps=count,feedback=feedback))
        result.update({phase+'_'+k:v for k,v in saved.items()});state=saved['final']
    move=kick(record,state);result.update({'kick_'+k:v for k,v in move.items()})
    for policy,initial in [('ordinary',state),('pair',move['after'])]:
        saved=segment(dict(record=record,state=initial,orders=packet['orders_query'],clamp_indices=np.arange(32,80),clamp_values=x[:,None,32:],active_sweeps=8,feedback=np.ones(8)))
        result.update({policy+'_'+k:v for k,v in saved.items()})
    return result
