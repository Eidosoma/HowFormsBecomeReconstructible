"""Independent direct-product, extended-precision polynomial energy audit.

No production basis, block indexing, field, energy or decision helper is used
by the reference calculations. Production fields are compared against these.
"""
import numpy as np
from h083 import model as pairs, audit as pair_audit
from h093 import dynamics

RANGES=((0,8),(16,24),(32,44),(56,68))

def products(state,masks,omit=-1):
    mu=np.stack([np.sum(state[...,lo:hi],axis=-1,dtype=np.longdouble)/(hi-lo) for lo,hi in RANGES],axis=-1)
    selected=np.asarray([[bool(int(mask)&(1<<b)) and b!=omit for b in range(4)] for mask in masks])
    return np.prod(np.where(selected,mu[...,None,:],np.longdouble(1)),axis=-1)

def factor_energy(record,state):
    return -np.sum(state[...,80:]*record['interaction_weights']*products(state,record['interaction_masks']),axis=-1,dtype=np.longdouble)

def energy(record,state):
    s=state.astype(np.longdouble)
    return -np.sum(s*(s@record['J'].T),axis=-1)/2+factor_energy(record,s)

def factor_fields(record,state):
    result=np.zeros(state.shape,dtype=np.longdouble);masks=record['interaction_masks'];weights=record['interaction_weights']
    result[...,80:]=weights*products(state,masks)
    for b,(lo,hi) in enumerate(RANGES):
        selected=np.asarray([bool(int(mask)&(1<<b)) for mask in masks])
        terms=state[...,80:]*weights*selected*products(state,masks,omit=b)
        result[...,lo:hi]=(np.sum(terms,axis=-1)/(hi-lo))[...,None]
    return result

def fields(record,state):return state.astype(np.longdouble)@record['J'].T+factor_fields(record,state)

def switched(record,strength):
    result={k:v.copy() for k,v in record.items()};result['J'][80:,80:]*=strength
    return result

def segment(record,reference,initial,orders,indices,values,feedback,data,check):
    state=initial.astype(np.int64).copy();free=np.ones(128,dtype=bool);free[indices]=False
    check.same(data['initial'],state,'independent prepared state');check.same(data['trace'][0],state,'initial trace')
    check.same(data['feedback'],feedback,'declared feedback schedule')
    initial_energy=energy(reference,state);previous=initial_energy.copy();balance=np.zeros_like(previous);evaluations=0
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
    for rec,prefix in ((ref,''),(reference,'nominal_')):
        h=fields(rec,state);wanted=check.decide(h,state)
        check.same(data[prefix+'fields_final'],h,prefix+'endpoint fields',2e-11)
        check.same(data[prefix+'conditional_fixed'],(wanted[...,free]==state[...,free]).all(-1),prefix+'conditional fixed')
        check.same(data[prefix+'full_fixed'],(wanted==state).all(-1),prefix+'full fixed')
    check.same(data['nominal_final_energy'],energy(reference,state),'nominal final energy',2e-11)

def neighborhood(reference,projector,state,data,check):
    check.same(data['fields'],fields(reference,state),'independent pair-start fields',2e-11)
    quadratic=pair_audit.reference_deltas(reference['J'],state,projector)
    flat,inverse=np.unique(state.reshape(-1,128),axis=0,return_inverse=True);base=factor_energy(reference,flat)
    results=[]
    for sites,part in zip((pairs.FREE[:,None],pairs.PAIRS),quadratic):
        extra=np.empty((len(flat),len(sites)),dtype=np.longdouble)
        for begin in range(0,len(sites),32):
            coordinates=sites[begin:begin+32];changed=np.broadcast_to(flat[:,None],(len(flat),len(coordinates),128)).copy()
            for column in range(coordinates.shape[1]):changed[:,np.arange(len(coordinates)),coordinates[:,column]]*=-1
            extra[:,begin:begin+len(coordinates)]=factor_energy(reference,changed)-base[:,None]
        results.append(part+extra[inverse].reshape(part.shape))
    single,delta=results
    check.same(data['single_delta'],single,'direct full-energy single differences',2e-11)
    check.same(data['pair_delta'],delta,'direct full-energy pair differences',2e-11)
    check.max_pair_error=max(check.max_pair_error,float(np.max(np.abs(data['pair_delta']-delta))))
    check.single_comparisons+=single.size;check.pair_comparisons+=delta.size
    check.threshold(single,-1e-10);check.threshold(delta,-1e-10)
    choices=[];eps=np.longdouble('1e-10')
    for row in delta.reshape(-1,pairs.PAIR_COUNT):
        lowest=min(row);eligible=[]
        for i,value in enumerate(row):
            if value < -eps:
                check.threshold(np.asarray([value-lowest]),1e-10)
                if value<=lowest+eps:eligible.append(i)
        choices.append(eligible[0] if eligible else -1)
    wanted=np.asarray(choices,dtype=np.int16).reshape(state.shape[:-1]);check.same(data['choice'],wanted,'independent lexicographic selection')
    after=state.copy().reshape(-1,128);selected=np.zeros(len(choices),dtype=np.longdouble)
    for row,index in enumerate(choices):
        if index>=0:after[row,pairs.PAIRS[index]]*=-1;selected[row]=delta.reshape(-1,pairs.PAIR_COUNT)[row,index]
    after=after.reshape(state.shape);selected=selected.reshape(state.shape[:-1]);realized=energy(reference,after)-energy(reference,state)
    check.same(data['after'],after,'simultaneous response pair change');check.same(data['selected_delta'],selected,'selected energy difference',2e-11)
    check.same(data['realized_delta'],realized,'realized polynomial energy difference',2e-11)
    check.same(realized,selected,'selector energy identity',2e-11);assert np.all(selected<=0)
    check.same((after!=state).sum(-1),2*(wanted>=0),'exactly zero or two changed bits');check.same(after[...,:80],state[...,:80],'pair keeps inputs')

def trajectory(raw,node,record,data,ref,projector,check):
    g,b=node['generation'],node['birth'];x=raw['inputs'];initial=np.broadcast_to(raw['birth'][g,b],(16,1,128))
    for phase,state,indices,values,feedback in (
        ('context',initial,np.arange(32),x[:,None,:32],np.ones(4)),
        ('gap',data['context_final'],np.asarray([],dtype=int),np.empty((16,1,0),dtype=np.int8),np.ones(4)),
        ('query',data['gap_final'],np.arange(32,80),x[:,None,32:],np.r_[0.,np.ones(7)])):
        segment(record,ref,state,raw['orders_'+phase][g],indices,values,feedback,
                {k[len(phase)+1:]:v for k,v in data.items() if k.startswith(phase+'_')},check)
    move={k[5:]:v for k,v in data.items() if k.startswith('kick_')}
    neighborhood(ref,projector,data['query_final'],move,check)
    for reader,state in (('ordinary',data['query_final']),('pair',move['after'])):
        saved={k[len(reader)+1:]:v for k,v in data.items() if k.startswith(reader+'_')}
        segment(record,ref,state,raw['orders_query'][g],np.arange(32,80),x[:,None,32:],np.ones(8),saved,check)
        check.same(saved['clamp_work'],np.zeros((8,16,1)),'continuation inputs already clamped')
        delta=saved['final_energy']-energy(ref,data['query_final']);wanted=(saved['end_energy']-saved['start_energy']).sum(0)
        if reader=='pair':wanted=wanted+move['realized_delta']
        check.same(delta,wanted,'pair and continuation total work',2e-11)
