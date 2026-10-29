"""Independent long-double gated trajectories; no production decision helper."""
import numpy as np
from h077.audit import exact_projector
from h081 import model as m,legacy_audit


class Check:
    def __init__(self):self.count=0;self.max_field_error=0.;self.boundary_minimum=float('inf')
    def same(self,x,y,label,tol=0):
        assert np.shape(x)==np.shape(y),label
        if tol:np.testing.assert_allclose(x,y,rtol=0,atol=tol,err_msg=label)
        else:np.testing.assert_array_equal(x,y,err_msg=label)
        self.count+=1
    def boundary(self,values,threshold):
        distance=float(np.min(np.abs(values-np.longdouble(str(threshold)))))
        assert distance>5e-14,'reference decision too close to threshold'
        self.boundary_minimum=min(self.boundary_minimum,distance)
    def decide(self,field,old):
        self.boundary(np.abs(field),m.TOL)
        new=old.copy();new[field>m.TOL]=1;new[field < -m.TOL]=-1
        return new
    def response(self,field,input_field,old,policy,enabled=True):
        proposal=self.decide(field,old);new=proposal.copy();veto=np.zeros(old.shape,dtype=bool)
        slack=-old*field-np.abs(input_field)
        if enabled and policy in ('cue_hysteresis','all_hysteresis'):
            self.boundary(slack,m.TOL)
            protected=np.ones(old.shape,dtype=bool)
            if policy=='cue_hysteresis':
                support=old*input_field;self.boundary(support,m.TOL);protected=support>m.TOL
            veto=(proposal!=old)&protected&~(slack>m.TOL);new[veto]=old[veto]
        return new,proposal,veto,slack


def energy(record,state):return -.5*np.sum(state*(state.astype(np.longdouble)@record.T),axis=-1)


def endpoint(reference,state,policy,check):
    factor={'off':0.,'half_feedback':.5}.get(policy,1.)
    current=reference.copy();current[80:,80:]*=factor
    fields=state.astype(np.longdouble)@current.T
    ordinary=check.decide(fields,state);actual=ordinary.copy()
    inputs=state[...,:80].astype(np.longdouble)@reference[80:,:80].T
    actual[...,80:]=check.response(fields[...,80:],inputs,state[...,80:],policy)[0]
    nominal=state.astype(np.longdouble)@reference.T;unmodified=check.decide(nominal,state)
    free=np.r_[0:32,80:128]
    return dict(fields_final=fields,conditional_fixed=(actual[...,free]==state[...,free]).all(-1),
        full_fixed=(actual==state).all(-1),ordinary_conditional_fixed=(ordinary[...,free]==state[...,free]).all(-1),
        ordinary_full_fixed=(ordinary==state).all(-1),nominal_fields_final=nominal,
        nominal_conditional_fixed=(unmodified[...,free]==state[...,free]).all(-1),
        nominal_full_fixed=(unmodified==state).all(-1),nominal_final_energy=energy(reference,state))


def segment(record,reference,initial,orders,values,policy,data,check):
    state=initial.astype(np.int64).copy();reference=reference.astype(np.longdouble)
    tape=np.asarray([0.]+[.5 if policy=='half_feedback' else 1.]*7)
    check.same(data['feedback'],tape,'fixed intervention coefficient tape')
    check.same(data['initial'],state,'prepared state');check.same(data['trace'][0],state,'initial trace')
    previous=energy(reference,state);initial_energy=previous.copy()
    check.same(data['initial_energy'],previous,'initial nominal energy',2e-11)
    switches=np.zeros_like(previous);work=np.zeros_like(previous);neural=np.zeros_like(previous)
    for sweep,order in enumerate(orders):
        check.same(np.sort(order),np.arange(m.N),'coordinate permutation')
        ref=reference.copy();ref[80:,80:]*=tape[sweep]
        actual=record.copy();actual[80:,80:]*=tape[sweep]
        switched=energy(ref,state);switch=switched-previous
        check.same(data['after_switch_energy'][sweep],switched,'after coefficient switch',2e-11)
        check.same(data['switch_work'][sweep],switch,'switch work',2e-11)
        state[...,32:80]=values;start=energy(ref,state);clamp=start-switched
        check.same(data['pre_update'][sweep],state,'pre-update state')
        check.same(data['start_energy'][sweep],start,'clamped energy',2e-11)
        check.same(data['clamp_work'][sweep],clamp,'clamp work',2e-11)
        changes=np.zeros(state.shape[:-1],dtype=np.int16);coordinate_energy=np.zeros_like(previous)
        for site in order:
            if 32<=site<80:continue
            old=state[...,site].copy();field=np.sum(state.astype(np.longdouble)*ref[site],axis=-1)
            error=float(np.max(np.abs(field-np.einsum('...i,i->...',state,actual[site]))))
            check.max_field_error=max(check.max_field_error,error);assert error<=2e-11
            if site>=80:
                inputs=np.sum(state[...,:80].astype(np.longdouble)*reference[site,:80],axis=-1)
                response=np.sum(state[...,80:].astype(np.longdouble)*ref[site,80:],axis=-1)
                new,proposal,veto,slack=check.response(field,inputs,old,policy,enabled=sweep>0)
                ix=(sweep,Ellipsis,site-80)
                for key,value in (('response_before',old),('response_after',new),('ordinary_proposal',proposal),('veto',veto)):
                    check.same(data[key][ix],value,'independent '+key)
                for key,value in (('input_field',inputs),('response_field',response),('gate_slack',slack)):
                    check.same(data[key][ix],value,'independent '+key,2e-11)
                check.same(inputs+response,field,'field conservation',2e-11)
            else:new=check.decide(field,old)
            delta=-(new-old)*field;assert np.all(delta<=0);coordinate_energy+=delta
            changes+=new!=old;state[...,site]=new;check.count+=1
        end=energy(ref,state)
        check.same(coordinate_energy,end-start,'coordinate energy sum',2e-11)
        check.same(data['changes'][sweep],changes,'accepted changes')
        check.same(data['trace'][sweep+1],state,'propagated state')
        check.same(data['end_energy'][sweep],end,'sweep energy',2e-11)
        switches+=switch;work+=clamp;neural+=end-start;previous=end
    check.same(data['final'],state,'final state')
    check.same(data['final_energy'],previous,'final energy',2e-11)
    check.same(previous-initial_energy,switches+work+neural,'total energy balance',2e-11)
    check.same(data['max_increase'],np.zeros_like(previous),'no positive accepted coordinate energy change')
    for key,value in endpoint(reference,state,policy,check).items():
        check.same(data[key],value,'independent endpoint '+key,2e-11 if 'fields' in key or 'energy' in key else 0)


def network(raw,cohort,block):
    old=legacy_audit.network(raw,cohort,block);check=Check();references=[]
    for source,yy in enumerate((raw['responses'],raw['responses'][m.SHIFT])):
        projector,rank=exact_projector(np.concatenate((m.X,yy),axis=1).astype(np.int64))
        reference=projector.copy();np.fill_diagonal(reference,0);references.append(reference)
        check.same(raw['source_J_projection'][source],reference,'independent projection record',4e-14)
    references.append(np.zeros((m.N,m.N),dtype=np.longdouble))
    for policy in m.INTERVENTIONS:
        for gap in m.GAPS:
            for scenario in m.SCENARIOS:
                p=m.prefix(policy,gap,scenario);data={k[len(p):]:v for k,v in raw.items() if k.startswith(p)}
                source=m.source_index(scenario);initial=raw[f'd{gap}_{scenario}_gap_final']
                segment(raw['source_J_projection'][source],references[source],initial,raw['orders_query'],
                    m.history(scenario)[:,None,32:],policy,data,check)
                check.same(data['trace'][1],raw[f'delayed_d{gap}_{scenario}_read1_final'],'shared delayed first sweep')
                assert not data['veto'][0].any()
    for policy in m.POLICIES:
        for source,yy in enumerate((raw['responses'],raw['responses'][m.SHIFT])):
            patterns=np.concatenate((m.X,yy),axis=1).astype(np.int64)
            for key,value in endpoint(references[source],patterns,policy,check).items():
                check.same(raw[f'stability_{policy}_{source}_'+key],value,'taught pattern '+key,
                    2e-11 if 'fields' in key or 'energy' in key else 0)
    return dict(passed=True,numerical_checks=old['numerical_checks']+check.count,
        legacy_control_checks=old['numerical_checks'],intervention_checks=check.count,
        legacy_controls_audited=True,target_free_packets=True,gate_and_propagated_paths_audited=True,
        max_projection_record_error=old['max_projection_record_error'],
        max_projection_field_error=max(old['max_projection_field_error'],check.max_field_error),
        projection_boundary_distance=min(old['projection_boundary_distance'],check.boundary_minimum),
        shared_preparation_and_first_sweep=True,switch_clamp_and_neural_energy_balance=True,
        inherited_transitions=0,predictors_fitted=0)
