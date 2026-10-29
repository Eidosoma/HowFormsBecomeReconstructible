"""Independent exclusion of held coordinates with the existing energy audit."""
import numpy as np
from h093.reference import energy,factor_fields,fields,switched,neighborhood,RANGES
from h094 import dynamics

def segment(record,reference,initial,orders,indices,values,feedback,data,check,hold):
    state=initial.astype(np.int64).copy();free=np.ones(128,dtype=bool);free[indices]=False
    check.same(data['initial'],state,'independent prepared state');check.same(data['trace'][0],state,'initial trace')
    check.same(data['feedback'],feedback,'declared feedback schedule')
    check.same(data['hold_context'],hold,'declared context hold schedule')
    initial_energy=energy(reference,state);previous=initial_energy.copy();balance=np.zeros_like(previous);evaluations=0;coordinates=0;skipped=0
    check.same(data['initial_energy'],initial_energy,'initial polynomial energy',2e-11)
    for sweep,order in enumerate(orders):
        check.same(np.sort(order),np.arange(128),'coordinate permutation')
        ref=switched(reference,feedback[sweep]);actual=switched(record,feedback[sweep])
        after_switch=energy(ref,state);switch=after_switch-previous
        check.same(data['after_switch_energy'][sweep],after_switch,'switched polynomial energy',2e-11)
        check.same(data['switch_work'][sweep],switch,'external switch work',2e-11)
        state[...,indices]=values;start=energy(ref,state);clamp=start-after_switch
        check.same(data['pre_update'][sweep],state,'clamped state');check.same(data['start_energy'][sweep],start,'clamped energy',2e-11)
        check.same(data['clamp_work'][sweep],clamp,'external clamp work',2e-11)
        flips=np.zeros(state.shape[:-1],dtype=np.int16);coordinate_work=np.zeros_like(start)
        ref_terms=factor_fields(ref,state);actual_terms=dynamics.factor_fields(actual,state)
        for site in order:
            if not free[site]:continue
            if bool(hold[sweep]) and int(site) in range(32):
                skipped+=state.size//128;continue
            coordinates+=state.size//128
            h=np.sum(state*ref['J'][site],axis=-1)+ref_terms[...,site]
            h_actual=np.einsum('...i,i->...',state,actual['J'][site])+actual_terms[...,site]
            error=float(np.max(np.abs(h-h_actual)));check.max_field_error=max(check.max_field_error,error)
            assert error<=2e-11,'independent coordinate field'
            old=state[...,site].copy();new=check.decide(h,old);check.count+=1
            delta=-(new-old)*h;assert np.all(delta<=0);coordinate_work+=delta;flips+=(new!=old);state[...,site]=new
            affected=site>=80 or any(lo<=site<hi for lo,hi in RANGES)
            if affected:
                evaluations+=int(np.prod(state.shape[:-1]))
                if np.any(new!=old):ref_terms=factor_fields(ref,state);actual_terms=dynamics.factor_fields(actual,state)
        end=energy(ref,state);assert np.all(end<=start+2e-14)
        check.same(end-start,coordinate_work,'sum of independent coordinate energy differences',2e-11)
        check.same(data['trace'][sweep+1],state,'independent sweep endpoint');check.same(data['changes'][sweep],flips,'coordinate changes')
        check.same(data['end_energy'][sweep],end,'polynomial sweep energy',2e-11)
        balance+=switch+clamp+coordinate_work;previous=end
    check.same(data['final'],state,'independent final state');check.same(data['final_energy'],previous,'final energy',2e-11)
    check.same(previous-initial_energy,balance,'switch clamp and coordinate balance',2e-11)
    check.same(data['max_increase'],np.zeros_like(previous),'no positive coordinate energy change')
    check.same(data['interaction_site_evaluations'],np.asarray(evaluations,dtype=np.int64),'interaction update work')
    check.same(data['context_updates_skipped'],np.asarray(skipped,dtype=np.int64),'skipped context work')
    check.same(data['coordinate_evaluations'],np.asarray(coordinates,dtype=np.int64),'performed coordinate work')
    for rec,prefix in ((ref,''),(reference,'nominal_')):
        h=fields(rec,state);wanted=check.decide(h,state)
        check.same(data[prefix+'fields_final'],h,prefix+'endpoint fields',2e-11)
        check.same(data[prefix+'conditional_fixed'],(wanted[...,free]==state[...,free]).all(-1),prefix+'conditional fixed')
        check.same(data[prefix+'full_fixed'],(wanted==state).all(-1),prefix+'full fixed')
    check.same(data['nominal_final_energy'],energy(reference,state),'nominal final energy',2e-11)

def trajectory(raw,node,record,data,ref,projector,check):
    g,b=node['generation'],node['birth'];x=raw['inputs'];initial=np.broadcast_to(raw['birth'][g,b],(16,1,128))
    for phase,state,indices,values,feedback in (
        ('context',initial,np.arange(32),x[:,None,:32],np.ones(4)),
        ('gap',data['context_final'],np.asarray([],dtype=int),np.empty((16,1,0),dtype=np.int8),np.ones(4)),
        ('query',data['gap_final'],np.arange(32,80),x[:,None,32:],np.r_[0.,np.ones(7)])):
        segment(record,ref,state,raw['orders_'+phase][g],indices,values,feedback,
                {k[len(phase)+1:]:v for k,v in data.items() if k.startswith(phase+'_')},check,
                np.asarray([True]+[False]*7) if phase=='query' else np.zeros(len(feedback),dtype=bool))
    move={k[5:]:v for k,v in data.items() if k.startswith('kick_')}
    neighborhood(ref,projector,data['query_final'],move,check)
    for reader,state in (('ordinary',data['query_final']),('pair',move['after'])):
        saved={k[len(reader)+1:]:v for k,v in data.items() if k.startswith(reader+'_')}
        segment(record,ref,state,raw['orders_query'][g],np.arange(32,80),x[:,None,32:],np.ones(8),saved,check,np.zeros(8,dtype=bool))
        check.same(saved['clamp_work'],np.zeros((8,16,1)),'continuation inputs already clamped')
        delta=saved['final_energy']-energy(ref,data['query_final']);wanted=(saved['end_energy']-saved['start_energy']).sum(0)
        if reader=='pair':wanted=wanted+move['realized_delta']
        check.same(delta,wanted,'pair and continuation total work',2e-11)
