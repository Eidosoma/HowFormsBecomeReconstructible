"""Unchanged polynomial energy; hold current context during one query sweep."""
import numpy as np
from h077 import model as base
from h093 import dynamics as old
from h093.dynamics import BLOCKS,SITE_BLOCK,BITS,basis,means,fields,energy,effective,validate,factor_fields,factor_energy,kick

HOLD=np.asarray([True,False,False,False,False,False,False,False])

def segment(packet):
    assert set(packet)=={'record','state','orders','clamp_indices','clamp_values','active_sweeps','feedback','hold_context'}
    record,state,orders,indices,values,active,tape=(packet[k] for k in ('record','state','orders','clamp_indices','clamp_values','active_sweeps','feedback'))
    validate(record);hold=packet['hold_context']
    assert hold.dtype==np.dtype('bool') and hold.shape==tape.shape
    assert np.isin(state,[-1,1]).all() and np.isin(values,[-1,1]).all() and np.isin(tape,[0.,1.]).all()
    assert orders.shape==(len(tape),128) and 0<=active<=len(tape) and len(tape)>0
    assert np.array_equal(np.sort(orders,axis=1),np.broadcast_to(np.arange(128),orders.shape))
    assert len(set(indices.tolist()))==len(indices) and np.isin(indices,np.arange(80)).all()
    state=state.copy();trace=[state.copy()];pre=[];changes=[];starts=[];ends=[];works=[];switches=[];switched=[]
    initial=energy(record,state);previous=initial.copy();maximum=np.zeros(state.shape[:-1]);free=np.ones(128,dtype=bool);free[indices]=False
    masks=record['interaction_masks'];weights=record['interaction_weights'];evaluations=0;coordinates=0;skipped=0
    for sweep,order in enumerate(orders):
        current=effective(record,tape[sweep]);after_switch=energy(current,state);switches.append(after_switch-previous);switched.append(after_switch)
        if len(indices):state[...,indices]=values
        start=energy(current,state);pre.append(state.copy());starts.append(start);works.append(start-after_switch)
        flips=np.zeros(state.shape[:-1],dtype=np.int16);mu=means(state);phi=basis(mu)
        for site in order if sweep<active else ():
            if not free[site]:continue
            if hold[sweep] and site<32:
                skipped+=int(np.prod(state.shape[:-1]));continue
            coordinates+=int(np.prod(state.shape[:-1]))
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
        interaction_site_evaluations=np.asarray(evaluations,dtype=np.int64),hold_context=hold.copy(),
        context_updates_skipped=np.asarray(skipped,dtype=np.int64),coordinate_evaluations=np.asarray(coordinates,dtype=np.int64))

def read(packet,protect=True):
    assert isinstance(protect,bool)
    assert set(packet)=={'record','birth','observed_history','orders_context','orders_gap','orders_query'}
    record=packet['record'];x=packet['observed_history'];validate(record)
    assert x.ndim==2 and x.shape[1]==80 and packet['birth'].shape==(128,) and np.isin(x,[-1,1]).all()
    state=np.broadcast_to(packet['birth'],(len(x),1,128)).copy()
    result={}
    for phase,indices,values,count,feedback in [('context',np.arange(32),x[:,None,:32],4,np.ones(4)),
            ('gap',np.asarray([],dtype=int),np.empty((len(x),1,0),dtype=np.int8),4,np.ones(4)),
            ('query',np.arange(32,80),x[:,None,32:],8,np.r_[0.,np.ones(7)])]:
        saved=segment(dict(record=record,state=state,orders=packet['orders_'+phase],clamp_indices=indices,clamp_values=values,active_sweeps=count,feedback=feedback,hold_context=HOLD.copy() if phase=='query' and protect else np.zeros(count,dtype=bool)))
        result.update({phase+'_'+k:v for k,v in saved.items()});state=saved['final']
    move=kick(record,state);result.update({'kick_'+k:v for k,v in move.items()})
    for policy,initial in [('ordinary',state),('pair',move['after'])]:
        saved=segment(dict(record=record,state=initial,orders=packet['orders_query'],clamp_indices=np.arange(32,80),clamp_values=x[:,None,32:],active_sweeps=8,feedback=np.ones(8),hold_context=np.zeros(8,dtype=bool)))
        result.update({policy+'_'+k:v for k,v in saved.items()})
    return result
