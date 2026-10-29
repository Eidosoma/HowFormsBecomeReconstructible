"""Independent projection replay with external switching and clamping work."""
import numpy as np
from h077.audit import Audit as PreviousAudit,exact_projector,SEGMENT_KEYS
from h081 import model as m


class Audit(PreviousAudit):
    def __init__(self,schedule='on'):
        super().__init__('projection');assert schedule in m.SCHEDULES;self.schedule=schedule

    def segment(self,raw,prefix,packet):
        if 'feedback' not in packet:return super().segment(raw,prefix,packet)
        ref=np.asarray(self.reference if self.reference is not None else packet['record'],dtype=np.longdouble)
        state=packet['state'].astype(np.int64).copy();indices=packet['clamp_indices'];free=np.ones(m.N,dtype=bool);free[indices]=False
        data={k:raw[prefix+k] for k in (*SEGMENT_KEYS,'switch_work','after_switch_energy','feedback',
            'nominal_fields_final','nominal_conditional_fixed','nominal_full_fixed','nominal_final_energy')}
        self.same(data['feedback'],packet['feedback'],'declared query feedback schedule')
        self.same(data['initial'],state,'common prepared state');self.same(data['trace'][0],state,'common initial trace')
        def energy(record,x):return -np.sum(x*(x.astype(np.longdouble)@record.T),axis=-1)/2
        def decide(field,old):
            boundary=float(np.min(np.abs(np.abs(field)-np.longdouble(str(m.TOL)))))
            self.boundary_minimum=min(self.boundary_minimum,boundary)
            assert boundary>5e-14,'reference field too close to decision threshold'
            return np.where(field>m.TOL,1,np.where(field < -m.TOL,-1,old))
        initial=energy(ref,state);previous=initial.copy();switch_sum=np.zeros_like(initial);work_sum=np.zeros_like(initial);neural_sum=np.zeros_like(initial)
        self.same(data['initial_energy'],initial,'nominal initial energy',2e-11)
        for sweep,order in enumerate(packet['orders']):
            assert np.array_equal(np.sort(order),np.arange(m.N))
            strength=packet['feedback'][sweep];assert strength in (0.,1.)
            current=ref.copy();current[80:,80:]*=strength
            actual=packet['record'].copy();actual[80:,80:]*=strength
            switched=energy(current,state);switch=switched-previous
            self.same(data['after_switch_energy'][sweep],switched,'after external coupling change',2e-11)
            self.same(data['switch_work'][sweep],switch,'external switch work',2e-11)
            if len(indices):state[...,indices]=packet['clamp_values']
            start=energy(current,state);work=start-switched
            self.same(data['pre_update'][sweep],state,'clamped state')
            self.same(data['start_energy'][sweep],start,'energy after clamp',2e-11)
            self.same(data['clamp_work'][sweep],work,'external clamp work',2e-11)
            flips=np.zeros(state.shape[:-1],dtype=np.int16)
            if sweep<packet['active_sweeps']:
                for site in order:
                    if not free[site]:continue
                    field=np.sum(state.astype(np.longdouble)*current[site],axis=-1)
                    error=float(np.max(np.abs(np.einsum('...i,i->...',state,actual[site])-field)))
                    self.max_field_error=max(self.max_field_error,error);assert error<=2e-11
                    old=state[...,site].copy();new=decide(field,old)
                    assert np.all(-(new-old)*field<=0);self.checks+=1;flips+=(new!=old);state[...,site]=new
            end=energy(current,state);assert np.all(end<=start+2e-14)
            self.same(data['trace'][sweep+1],state,'independent scheduled sweep')
            self.same(data['changes'][sweep],flips,'scheduled flips')
            self.same(data['end_energy'][sweep],end,'scheduled energy',2e-11)
            switch_sum+=switch;work_sum+=work;neural_sum+=end-start;previous=end
        self.same(data['final'],state,'scheduled endpoint');self.same(data['final_energy'],previous,'final scheduled energy',2e-11)
        self.same(previous-initial,switch_sum+work_sum+neural_sum,'switch/clamp/neural balance',2e-11)
        self.same(data['max_increase'],np.zeros_like(initial),'no positive coordinate energy change')
        for record,p in ((current,''),(ref,'nominal_')):
            fields=state.astype(np.longdouble)@record.T;next_state=decide(fields,state)
            self.same(data[p+'fields_final'],fields,p+'endpoint fields',2e-11)
            self.same(data[p+'conditional_fixed'],(next_state[...,free]==state[...,free]).all(-1),p+'conditional fixed')
            self.same(data[p+'full_fixed'],(next_state==state).all(-1),p+'fully fixed')
        self.same(data['nominal_final_energy'],energy(ref,state),'nominal final energy',2e-11)

    def network_one(self,raw,cohort,block):
        expected=m.tapes(cohort,block)
        for name,value in expected.items():self.same(raw[name],value,'committed random tape '+name)
        self.same(raw['training_inputs'],m.X,'public input alphabet');self.same(raw['shift'],m.SHIFT,'declared context shift')
        y=raw['responses'];assert y.shape==(8,m.NY) and np.isin(y,[-1,1]).all() and (y.sum(-1)==0).all()
        distances=np.empty((8,8),dtype=int)
        for a in range(8):
            for b in range(8):distances[a,b]=sum(x!=z for x,z in zip(y[a].tolist(),y[b].tolist()))
        self.same(raw['output_distances'],distances,'response separation')
        references=[]
        for source,yy in enumerate((y,y[m.SHIFT])):
            patterns=np.concatenate((m.X,yy),axis=1).astype(np.int64);k=np.zeros((m.N,m.N),dtype=np.int64)
            for observation in patterns:k+=observation[:,None]*observation[None,:]
            np.fill_diagonal(k,0)
            if self.rule=='hebbian':reference=k.astype(np.longdouble)/m.N
            else:
                projector,rank=exact_projector(patterns)
                self.same(raw['source_projector'][source],projector,'independent projection',4e-14)
                assert rank==int(raw['source_projector_rank'][source])
                self.same(patterns@projector,patterns.astype(np.longdouble),'projection contains training span',2e-13)
                self.same(projector@projector,projector,'projection idempotence',2e-13)
                reference=projector.copy();np.fill_diagonal(reference,0)
                self.max_record_error=max(self.max_record_error,float(np.max(np.abs(raw['source_J'][source]-reference))))
            references.append(reference)
            self.same(raw['source_J'][source],reference,'independent learned weights',4e-14 if self.rule=='projection' else 0)
            fields=patterns.astype(np.longdouble)@reference.T
            self.same(raw[f'target_{source}_fields'],fields,'target fields',2e-11)
            self.same(raw[f'target_{source}_signed'],patterns*fields,'target signed fields',2e-11)
            if self.rule=='projection':
                identity=np.broadcast_to(1-np.diag(projector),patterns.shape)
                self.same(raw[f'target_{source}_signed'],identity,'projection target margin identity',2e-11)
            mean=np.asarray([sum(m.X[:,i])/8 for i in range(m.NC+m.NQ)])
            self.same(raw['source_mean'][source],mean,'input-only feature center')
            basis=raw['source_basis'][source];self.same(basis.T@basis,np.eye(4),'orthonormal learned basis',2e-12)
            self.same((m.X-mean)@basis@basis.T,m.X-mean,'input-span completeness',2e-12)
            z=(m.X-mean)@basis
            for name,degree in (('linear',1),('quadratic',2)):
                columns=[np.ones(8)]+[z[:,i] for i in range(4)]
                if degree==2:columns += [z[:,i]*z[:,j] for i in range(4) for j in range(i,4)]
                design=np.column_stack(columns);fit=np.linalg.pinv(design,rcond=1e-12)@yy
                self.same(raw['source_'+name][source],fit,'independent minimum-norm '+name,2e-12)
            self.same(raw['source_prototype_inputs'][source],m.X,'stored observed input pairs')
            self.same(raw['source_prototype_outputs'][source],yy,'stored observed responses')
        for name in ('J','J_hebbian','J_projection','projector','projector_rank','pattern_singular_values','mean','basis','linear','quadratic','prototype_inputs','prototype_outputs'):
            self.same(raw['source_'+name][2],np.zeros_like(raw['source_'+name][2]),'complete learned-record erasure')
        initial=np.broadcast_to(raw['birth'][None],(8,m.R,m.N));empty=np.asarray([],dtype=int)
        for scenario in m.SCENARIOS:
            obs=m.history(scenario);self.same(raw['history_'+scenario],obs,'actual observed history')
            j=raw['source_J'][m.source_index(scenario)]
            self.reference=references[m.source_index(scenario)] if scenario!='erased' else np.zeros((m.N,m.N),dtype=np.longdouble)
            for gap in m.GAPS:
                prefix=f'd{gap}_{scenario}_';ci=empty if scenario=='context_absent' else m.CONTEXT
                cv=np.empty((8,1,0),dtype=np.int8) if scenario=='context_absent' else obs[:,None,:m.NC]
                self.segment(raw,prefix+'context_',dict(record=j,state=initial,orders=raw['orders_context'],
                    clamp_indices=ci,clamp_values=cv,active_sweeps=4))
                self.segment(raw,prefix+'gap_',dict(record=j,state=raw[prefix+'context_final'],orders=raw['orders_gap'][:gap],
                    clamp_indices=empty,clamp_values=np.empty((8,1,0),dtype=np.int8),active_sweeps=gap))
                for horizon in m.HORIZONS:
                    self.segment(raw,prefix+f'read{horizon}_',dict(record=j,state=raw[prefix+'gap_final'],orders=raw['orders_query'],
                        clamp_indices=m.QUERY,clamp_values=obs[:,None,m.NC:],active_sweeps=horizon,feedback=m.FEEDBACK[self.schedule]))
                self.same(raw[prefix+'read1_trace'][1],raw[prefix+'read8_trace'][1],'shared first query sweep')
                self.same(raw[prefix+'read1_final'],raw[prefix+'read1_trace'][1],'one-sweep arm remains held')
                if scenario=='context_absent':
                    out=raw[prefix+'read8_final'].reshape(4,2,m.R,m.N)
                    self.same(out,np.broadcast_to(out[:1],out.shape),'identical absent-context histories')
            for name in SEGMENT_KEYS:self.same(raw['d0_'+scenario+'_context_'+name],raw['d4_'+scenario+'_context_'+name],'shared context preparation')
            for method in m.BASELINES:self.conventional(raw,scenario,method)
        sizes=dict(recurrent=m.BUDGET,linear_ls=80+80*4+5*m.NY,
            quadratic_ls=80+80*4+15*m.NY,nearest_history=8*m.N)
        assert all(n<=m.BUDGET for n in sizes.values())
        return dict(passed=True,numerical_checks=self.checks,integer_coordinate_replay=self.rule=='hebbian',
            projection_extended_replay=self.rule=='projection',max_record_error=self.max_record_error,
            max_field_error=self.max_field_error,minimum_decision_boundary_distance=None if self.rule=='hebbian' else self.boundary_minimum,
            clamp_work_and_energy_balance=True,strict_reader_inputs=True,history_controls_audited=True,
            learned_record_values=sizes,history_buffer_values=80,
            minimum_response_distance=int(distances[np.triu_indices(8,1)].min()))


def network(raw,cohort,block):
    results={s:Audit(s).network_one(m.view(raw,s),cohort,block) for s in m.SCHEDULES}
    identities=0
    for s in m.SCHEDULES:
        np.testing.assert_array_equal(raw['feedback_'+s],m.FEEDBACK[s]);identities+=1
        for gap in m.GAPS:
            for scenario in m.SCENARIOS:
                p=f'd{gap}_{scenario}_'
                for h in m.HORIZONS:
                    np.testing.assert_array_equal(raw[s+'_'+p+f'read{h}_initial'],raw[p+'gap_final']);identities+=1
                np.testing.assert_array_equal(raw[s+'_'+p+'read0_final'],raw['on_'+p+'read0_final']);identities+=1
    return dict(passed=True,numerical_checks=sum(r['numerical_checks'] for r in results.values())+identities,
        schedule_audits=results,common_prequery_states_verified=True,projection_extended_replay=True,
        max_projection_record_error=max(r['max_record_error'] for r in results.values()),
        max_projection_field_error=max(r['max_field_error'] for r in results.values()),
        projection_boundary_distance=min(r['minimum_decision_boundary_distance'] for r in results.values()),
        switch_clamp_and_neural_energy_balance=True,conventional_controls_audited=True)
