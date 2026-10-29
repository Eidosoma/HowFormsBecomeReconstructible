"""One target-free hysteresis rule, two controls, and untouched legacy readers."""
import hashlib
import json
import numpy as np
from h079.model import (N,NC,NQ,NY,R,CONTEXT,QUERY,RESPONSE,CODES,QUERY_CODES,X,SHIFT,
    SCENARIOS,GAPS,HORIZONS,NEURAL,BASELINES,METHODS,TOL,BUDGET,acquire,energy,
    baseline,history,source_index,packet_for_baseline,load,save,constant_segment,
    SCHEDULES,FEEDBACK,effective,segment,run_tapes,view)

SEED,NETWORKS,ENGINEERING=81081,64,4
INTERVENTIONS=('cue_hysteresis','half_feedback','all_hysteresis')
POLICIES=SCHEDULES+INTERVENTIONS
PRIMARY='cue_hysteresis'
BARRIER=1.


def rng(cohort,block,stream):
    assert cohort in ('fixture','engineering','development') and int(block)==block and block>=0
    if cohort=='engineering':assert block<ENGINEERING
    if cohort=='development':assert block<NETWORKS
    text=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(text).digest()[:16],'little'))


def tapes(cohort,block):
    gen=rng(cohort,block,'responses');y=np.full((8,NY),-1,dtype=np.int8)
    for row in y:row[gen.permutation(NY)[:NY//2]]=1
    out=dict(responses=y,birth=rng(cohort,block,'birth').choice([-1,1],size=(R,N)).astype(np.int8))
    for phase,count in (('context',4),('gap',4),('query',8)):
        gen=rng(cohort,block,'orders_'+phase)
        out['orders_'+phase]=np.stack([gen.permutation(N) for _ in range(count)])
    return out


def decide(field,old):return np.where(field>TOL,1,np.where(field < -TOL,-1,old)).astype(np.int8)


def gate(old,field,input_field,policy,enabled=True):
    assert policy in POLICIES
    proposed=decide(field,old);slack=-old*field-BARRIER*np.abs(input_field)
    veto=np.zeros(old.shape,dtype=bool)
    if enabled and policy in ('cue_hysteresis','all_hysteresis'):
        veto=(proposed!=old)&(slack<=TOL)
        if policy=='cue_hysteresis':veto&=old*input_field>TOL
    return np.where(veto,old,proposed).astype(np.int8),proposed,veto,slack


def coefficient(policy):
    return .5 if policy=='half_feedback' else 0. if policy=='off' else 1.


def endpoint(record,state,policy):
    current=record.copy();current[80:,80:]*=coefficient(policy)
    fields=state@current.T;ordinary=decide(fields,state);updated=ordinary.copy()
    inputs=state[...,:80]@record[80:,:80].T
    updated[...,80:]=gate(state[...,80:],fields[...,80:],inputs,policy)[0]
    free=np.r_[0:32,80:128]
    nominal=state@record.T;unmodified=decide(nominal,state)
    return dict(fields_final=fields,conditional_fixed=(updated[...,free]==state[...,free]).all(-1),
        full_fixed=(updated==state).all(-1),ordinary_conditional_fixed=(ordinary[...,free]==state[...,free]).all(-1),
        ordinary_full_fixed=(ordinary==state).all(-1),nominal_fields_final=nominal,
        nominal_conditional_fixed=(unmodified[...,free]==state[...,free]).all(-1),
        nominal_full_fixed=(unmodified==state).all(-1),nominal_final_energy=energy(record,state))


def intervene(packet):
    assert set(packet)=={'record','state','orders','clamp_indices','clamp_values','policy'}
    j,state,orders,indices,values,policy=(packet[k] for k in
        ('record','state','orders','clamp_indices','clamp_values','policy'))
    assert policy in INTERVENTIONS and j.shape==(N,N) and np.array_equal(j,j.T) and not np.diag(j).any()
    assert np.array_equal(indices,QUERY) and orders.shape==(8,N)
    assert np.isin(state,[-1,1]).all() and np.isin(values,[-1,1]).all()
    state=state.copy();shape=(8,*state.shape[:-1],NY)
    extra={k:np.empty(shape,dtype=dtype) for k,dtype in
        (('response_before',np.int8),('response_after',np.int8),('ordinary_proposal',np.int8),
         ('veto',bool),('input_field',float),('response_field',float),('gate_slack',float))}
    trace=[state.copy()];pre=[];changes=[];starts=[];ends=[];works=[];switches=[];switched=[]
    tape=np.r_[0.,np.full(7,coefficient(policy))]
    initial=energy(j,state);previous=initial.copy();max_increase=np.zeros(state.shape[:-1])
    for sweep,order in enumerate(orders):
        current=j.copy();current[80:,80:]*=tape[sweep]
        after_switch=energy(current,state);switches.append(after_switch-previous);switched.append(after_switch)
        state[...,indices]=values;start=energy(current,state);works.append(start-after_switch)
        pre.append(state.copy());starts.append(start);flips=np.zeros(state.shape[:-1],dtype=np.int16)
        for site in order:
            if 32<=site<80:continue
            old=state[...,site].copy();field=np.einsum('...i,i->...',state,current[site]);new=decide(field,old)
            if site>=80:
                u=np.einsum('...i,i->...',state[...,:80],j[site,:80])
                response=np.einsum('...i,i->...',state[...,80:],current[site,80:])
                new,proposal,veto,slack=gate(old,field,u,policy,enabled=sweep>0)
                ix=(sweep,Ellipsis,site-80)
                for key,value in (('response_before',old),('response_after',new),('ordinary_proposal',proposal),
                        ('veto',veto),('input_field',u),('response_field',response),('gate_slack',slack)):
                    extra[key][ix]=value
                np.testing.assert_allclose(field,u+response,rtol=0,atol=2e-11)
            delta=-(new-old)*field;assert np.all(delta<=0)
            max_increase=np.maximum(max_increase,delta);flips+=new!=old;state[...,site]=new
        end=energy(current,state);assert np.all(end<=start+1e-12)
        changes.append(flips);ends.append(end);previous=end;trace.append(state.copy())
    return dict(initial=trace[0],final=state,trace=np.stack(trace),pre_update=np.stack(pre),changes=np.stack(changes),
        start_energy=np.stack(starts),end_energy=np.stack(ends),clamp_work=np.stack(works),
        switch_work=np.stack(switches),after_switch_energy=np.stack(switched),feedback=tape,
        initial_energy=initial,final_energy=previous,max_increase=max_increase,
        **endpoint(j,state,policy),**extra)


def prefix(policy,gap,scenario):return f'intervention_{policy}_d{gap}_{scenario}_read8_'


def run(cohort,block):
    raw=run_tapes(tapes(cohort,block))
    for policy in INTERVENTIONS:
        for gap in GAPS:
            for scenario in SCENARIOS:
                result=intervene(dict(record=raw['source_J_projection'][source_index(scenario)],
                    state=raw[f'd{gap}_{scenario}_gap_final'],orders=raw['orders_query'],
                    clamp_indices=QUERY,clamp_values=history(scenario)[:,None,NC:],policy=policy))
                raw.update({prefix(policy,gap,scenario)+k:v for k,v in result.items()})
    for policy in POLICIES:
        for source,yy in enumerate((raw['responses'],raw['responses'][SHIFT])):
            patterns=np.concatenate((X,yy),axis=1)
            result=endpoint(raw['source_J_projection'][source],patterns,policy)
            raw.update({f'stability_{policy}_{source}_'+k:v for k,v in result.items()})
    return raw


def policy_view(raw,policy):
    if policy in SCHEDULES:return view(raw,policy)
    assert policy in INTERVENTIONS
    result=view(raw,'delayed')
    for gap in GAPS:
        for scenario in SCENARIOS:
            p=prefix(policy,gap,scenario);dest=f'd{gap}_{scenario}_read8_'
            result.update({dest+k[len(p):]:v for k,v in raw.items() if k.startswith(p)})
    return result
