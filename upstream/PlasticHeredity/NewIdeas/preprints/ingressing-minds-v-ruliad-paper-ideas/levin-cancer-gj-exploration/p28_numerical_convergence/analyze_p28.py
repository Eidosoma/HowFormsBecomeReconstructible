"""Independent P28 state/clock audit and fixed-source numerical convergence."""
import argparse
from itertools import combinations
from pathlib import Path
import numpy as np
import p28_design as d
import analyze_p27 as p27
Checks,labels,arrays,INDEX=p27.Checks,p27.labels,p27.arrays,p27.INDEX
GRAPH=p27.p19.p18.p16.GRAPH

def spec(founder='written',condition='pause_0_5',source_fine=False,resolution=1):
    # Independent of runner/design case construction.
    windows={'baseline':(None,0),'pause_0_5':(0,5),'pause_0_25':(0,25),'pause_10_100':(10,100)}
    start,duration=windows[condition]
    stage='replay' if (source_fine and resolution==2) or (not source_fine and resolution==1) else 'convergence'
    return dict(id='__'.join([stage,founder,condition,'source_fine' if source_fine else 'source_coarse','r'+str(resolution)]),
        stage=stage,founder=founder,condition=condition,panel='timing_grid',route='none',window='open' if start is None else condition,
        pause_start=start,pause_duration=duration,draw='heldout_17021',replacements=5,readout='',fine=source_fine,
        source_fine=source_fine,resolution=resolution)
def expected_stage(stage):
    if stage not in ('replay','convergence'): raise ValueError('Unknown P28 stage')
    return [c for q in (1,2,4,8,16) for h in ('written','ordinary') for k in ('baseline','pause_0_5','pause_0_25','pause_10_100')
            for f in (False,True) if (c:=spec(h,k,f,q))['stage']==stage]
def expected_cases(last='convergence'):
    return expected_stage('replay')+(expected_stage('convergence') if last=='convergence' else [])
def old_id(c): return 'renewal__'+c['founder']+'__'+c['condition']+'__heldout_17021__5'+('__fine' if c['source_fine'] else '')
def replay(c): return 'p27/'+old_id(c) if c['stage']=='replay' else None
def anchor(c): return 'p27/'+old_id(c) if c['condition'] in ('baseline','pause_0_25') else None

def audit_clock(data,rec,case,checks):
    ck=lambda name,value:checks.add(case['id']+'/'+rec['phase']+'/clock/'+name,value)
    base=.0001/case['resolution']; horizon=rec['requested_horizon']
    sample=min(100,horizon/20); maximum=min(100,horizon/100)/case['resolution']
    total=round(horizon/base); stride=round(sample/base); cap=round(maximum/base)
    meta=rec.get('clock',{})
    ck('method',meta.get('method')=='native_explicit_euler_bounded_clock_v1')
    ck('configuration',meta.get('base_step')==base and meta.get('sample_interval')==sample and
        meta.get('maximum_step')==maximum and meta.get('adaptive') is True and
        meta.get('integer_tick_clock') is True and meta.get('initial_and_final_samples') is True)
    ck('at_least_21_samples',len(data['times'])>=21)
    expected=np.array(list(range(0,total,stride))+[total],dtype=np.int64)
    ck('required_arrays',all(k in data for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')))
    if not all(k in data for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks')): return
    step,proposed,shots=(data[k] for k in ('clock_step_ticks','clock_proposed_ticks','clock_sample_ticks'))
    ck('integer_traces',step.dtype==proposed.dtype==shots.dtype==np.dtype('int64') and
        step.ndim==proposed.ndim==shots.ndim==1 and len(step)==len(proposed)>0)
    ck('observations',np.array_equal(shots,expected) and np.array_equal(data['times'],expected*base))
    ck('observation_shape',len(data['times'])==len(data['concentrations'])==len(expected))
    ck('first_live_sample',np.array_equal(data['concentrations'][0],data['initial']))
    ck('last_live_sample',np.array_equal(data['concentrations'][-1],data['final']))
    ck('bounded_steps',np.all(step>0) and np.all(step<=cap) and np.all(proposed>=1))
    if step.ndim!=1 or proposed.shape!=step.shape or not len(step): return
    end=np.cumsum(step); before=np.concatenate(([0],end[:-1]))
    next_sample=np.minimum(((before//stride)+1)*stride,total)
    allowed=np.minimum(np.minimum(proposed,next_sample-before),np.minimum(total-before,cap))
    ck('exact_step_clipping',np.array_equal(step,allowed))
    ck('every_boundary_respected',np.all(before>=0) and np.all(end<=next_sample) and np.all(end<=total))
    ck('exact_final_tick',int(end[-1])==total==meta.get('total_ticks'))
    ck('exact_final_time',meta.get('actual_final_time')==horizon==data['times'][-1]
        and meta.get('requested_horizon')==horizon)
    ck('trace_counts',meta.get('iterations')==len(step) and meta.get('sample_count')==len(expected)
        and meta.get('capped_steps')==int(np.count_nonzero(step<proposed)))
    if 'isolated' in rec['phase']:
        ck('late_sample_count',int(np.count_nonzero(data['times']>=7500))==26)


def audit_phase(folder,case,rec,layout,checks):
    idx=INDEX
    name=rec['phase']; ck=lambda n,v:checks.add(case['id']+'/'+name+'/'+n,v)
    ck('hash',d.digest(folder/(name+'.npz'))==rec['sha256']); a=arrays(folder,name)
    shape,ids=layout['shape'],layout['ids']; algo='depol'
    power,kd,iso,horizon=(layout[k] for k in ('power','kd','isolated','horizon'))
    count=len(ids); setup=rec['setup']; fr,to=layout['fr'],layout['to']
    regions,powers,available,compartments=(layout[k] for k in ('regions','powers','available','compartments'))
    ck('compartments',setup['compartment_expression']==compartments)
    for side in ('initial','final'):
        for k,v in (('region',regions),('power',powers),('available',available)):
            ck('edge_'+k+'_'+side,np.array_equal(a['edge_'+k+'_'+side],v))
    ck('shape',a['initial'].shape==a['final'].shape==(17,count) and a['concentrations'].shape[1:]==(17,count))
    ck('ids',setup['cell_ids']==ids and len(set(ids))==count and setup['cells']==count)
    if layout['graph']:
        ck('geometry',setup['grid_shape'] is None and setup['storage_shape']==[1,6] and
            setup['orthogonal_only'] is False and setup['periodic'] is False and
            setup['network_mode']=='explicit_common_graph' and setup['explicit_edges']==[list(e) for e in GRAPH])
        ck('schedule_mask',setup['scheduled_pupils']==layout['active'] and setup['route']==layout['route'])
    else:
        ck('geometry',setup['grid_shape']==shape and setup['orthogonal_only'] is True and setup['periodic'] is False)
    ck('topology',np.array_equal(a['edge_from'],fr) and np.array_equal(a['edge_to'],to))
    times=a['times']
    ck('time_axis',times.ndim==1 and len(times)>=2 and len(times)==len(a['concentrations']) and
        times[0]>=0 and np.all(np.diff(times)>0) and np.any(times>=.75*horizon))
    ck('logical_interval',rec.get('logical_interval')==[layout['base'],layout['base']+horizon])
    ck('duration',rec['requested_horizon']==horizon and rec['last_sample_time']==times[-1] and rec['samples']==len(times))
    for key in ('initial','concentrations','final'):
        ck(key+'_finite',np.isfinite(a[key]).all() and np.min(a[key])>=0)
        ck(key+'_snail',np.all(a[key][...,idx['snail'],:]==72))
    ck('labels',''.join(labels(a['final'],idx))==rec['final_labels'])
    ck('snapshot_difference',float(np.max(np.abs(a['concentrations'][-1]-a['final'])))==rec['last_snapshot_live_difference'])
    ck('strategy',setup['algorithm']==algo and setup['power']==power and setup['mirna_kd']==kd and setup['isolated']==iso)
    ck('neighbor',not setup['neighbor_voltage_reading'] and setup['cell_voltage_gate_present']==(algo!='hypol'))
    ck('transport',not a['junction_diffusion'].any() if iso else a['junction_diffusion'][:4].any())
    ck('gate_inventory',setup['gate_classes']==dict(ic=[] if algo=='hypol' else ['set_Vmem_from_conc'],
        gj=['GJ_gate','tumor_overX_GJ_gate'],gd=['EMT_GRN_gate'],gj_add=['EMT_GJ_gate']))
    ck('integrator',setup['integrator']==dict(time_step=.0001/case['resolution'],
        sim_integ_max_delt_cc=.001/case['resolution'],
        sim_integ_max_delt_Vm=.0001/case['resolution'],use_implicit=False))
    ck('expression_constants',setup['tumor_rule']==dict(x0=40.,M_ZEB_miR200=200000/18000,tness=1,GJ_OiET=.5))
    q=setup['voltage_constants']
    ck('voltage_constants',q['F']==96485 and q['cm']==.05 and
        np.isclose(q['cell_vol'],4*np.pi*(5e-6)**3/3,rtol=1e-14,atol=0) and
        np.isclose(q['cell_sa'],4*np.pi*(5e-6)**2,rtol=1e-14,atol=0))
    for key,value in (('A1',-110.),('A2',-110.),('VO1',-.0102),('VO2',-.0102)):
        ck('Cx45_'+key,np.all(a['gate_'+key]==value))
    ck('miRNA_size',np.all(a['gate_Gmin'][idx['miR200_total']]==0) and
        np.all(a['gate_Gdelta'][idx['miR200_total']]==1.56) and setup['mirna_transport']==dict(valence=-1,medium_size=True))
    ck('membrane_valences',np.array_equal(a['valences'],[1,1,-1,-1]+[0]*13))
    for side in ('initial','final'):
        value=a[side]; vm=(value*a['valences'][:,None]).sum(0)*96485*q['cell_vol']/(q['cell_sa']*.05)
        ck('vm_'+side,np.allclose(vm,a['vm_'+side],rtol=1e-12,atol=1e-14))
        dv=vm[fr]-vm[to]
        voltage=1.56/(1+np.exp(-110*(-dv+.0102))+np.exp(-110*(dv+.0102)))
        ck('voltage_'+side,np.allclose(voltage,a['voltage_gate_'+side],rtol=1e-10,atol=1e-12))
        mi,zeb,protein=(value[idx[k]] for k in ('miR200_total','Zeb_mRNA_total','ZEB_prot'))
        tp=(protein/(200000/18000+5))**10; tumor=1/(1+(mi/30)**10)*tp/(1+tp)
        lo=np.minimum(tumor[fr],tumor[to]); hi=np.maximum(tumor[fr],tumor[to])
        expression=(1+(lo+.5*(hi-lo))*(powers-1))*available
        ck('expression_'+side,np.allclose(expression,a['expression_gate_'+side],rtol=1e-12,atol=1e-12))
        potassium=np.ones(count)
        if algo!='hypol':
            ratio=(mi/(.001+zeb))**10; potassium=1+30*ratio/(1+ratio)
        ck('potassium_'+side,np.allclose(potassium,a['potassium_gate_'+side],rtol=1e-12,atol=1e-12))
    audit_clock(a,rec,case,checks)
    return a



class Reader(p27.Reader):
    def take(self,layout,initial):
        name=layout['name']
        if self.at>=len(self.records): raise ValueError('Missing registered phase '+name)
        rec=self.records[self.at]; self.at+=1
        self.ck(name+'/ordered_phase',rec['phase']==name)
        if rec['phase']!=name: raise ValueError('Unexpected phase order')
        value=audit_phase(self.folder,self.c,rec,layout,self.checks)
        self.eq(name+'/actual_initial',value['initial'],initial)
        self.eq(name+'/native_bath',value['environment'],self.environment)
        self.ck(name+'/no_direct_nonionic_diffusion',not value['junction_diffusion'][4:].any())
        self.data[name]=value
        return value['final']

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('source_factor',c['fine'] is c['source_fine'] and result['source_precision']==('fine' if c['source_fine'] else 'coarse'))
    rd.ck('solver_factor',result['numerical_resolution']==c['resolution'] and result['independent_source_and_solver_factors'] is True)
    rd.ck('clock',result.get('clock_method')=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='fixed_source_geometric_resolution_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','counterfactual_reconstruction','numerical_parameters_refined','algebraic_refresh_at_assembly','segmented_first_challenge')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('primary_state_edits_at_assembly','repeated_pause','donors_clamped','readout_states_edited',
        'autonomous_reproduction','cell_division_simulated','parameter_retuning','independent_biological_replicates','outcome_dependent_selection',
        'automatic_follow_on','new_onward_assays','original_P27_gate_changed','fixed_onward_schedules','new_incoming_protein_draws')))
    rd.ck('timing_scope',result['global_network_timing_intervention'] is (c['condition']!='baseline'))
    rd.ck('replay_provenance',result['historical_numeric_replay']==replay(c))
    rd.ck('anchor_provenance',result['historical_outcome_anchor']==anchor(c))
    out=p27.audit_renewal(rd,folder.parent,c)
    reference=replay(c)
    if reference:
        archived=d.read(folder.parent/'inputs'/reference/'result.json')
        rd.ck('replay_outcome',out==archived['outcome'])
        for name,value in rd.data.items():
            old=arrays(folder.parent/'inputs'/reference,name)
            rd.ck(name+'/replay_inventory',set(value)==set(old))
            for key in old: rd.eq(name+'/historical_replay/'+key,value[key],old[key])
    return rd.finish(out)

def predecessor_audit(run):
    evidence=d.stopped_evidence(); summary=d.read(run/'summary.json'); integrity=d.integrity(run,summary)
    return dict(quality_gate=bool(evidence['diagnostic_archive_valid'] and all(integrity.values())),
        inherited=evidence,integrity=integrity,predecessor_quality_gate=False,
        permits_diagnostic_study_only=True,historical_mathematical_audit_repeated=False)

def control_anchors(by,run,cases):
    rows=[]
    for c in cases:
        source=anchor(c)
        if source is None: continue
        old=d.read(run/'inputs'/source/'result.json')['outcome']; current=by.get(c['id'],{})
        keys=('retained_E','first_cell_sampled_behavior','first_cell_stable_E_after_second','complete_carrier_replacement')
        rows.append(dict(case=c,source=source,keys=list(keys),qualified=all(current.get(k)==old[k] for k in keys)))
    return rows

def prefix_comparisons(run,cases,checks):
    rows=[]
    for x,y in combinations(cases,2):
        if not all(x[k]==y[k] for k in ('founder','source_fine','resolution')): continue
        names=[]
        for i,(left,right) in enumerate(zip(p27.window_routes(x),p27.window_routes(y)),1):
            if left!=right: break
            names.append('challenge_%02d'%i)
        if not names: continue
        same=True
        for name in names:
            left,right=arrays(run/x['id'],name),arrays(run/y['id'],name)
            equal=set(left)==set(right) and all(np.array_equal(left[k],right[k]) for k in left)
            checks.add(x['id']+'/shared_prefix/'+y['id']+'/'+name,equal); same &= equal
        rows.append(dict(left=x['id'],right=y['id'],phases=names,exact_numeric_agreement=bool(same)))
    return rows

def pair(left,right,by,data):
    x,y=data[left['id']],data[right['id']]; phases={}; scaled=0.
    primary=list(range(8))+[16]
    for name in x:
        a,b=x[name],y[name]
        if name not in y: raise ValueError('Missing comparison phase')
        if not np.array_equal(a['times'],b['times']): raise ValueError('Comparison sampling changed')
        first,last=a['concentrations'][:,primary,:],b['concentrations'][:,primary,:]
        denom=np.maximum(1.,np.maximum(np.abs(first),np.abs(last)))
        error=float(np.max(np.abs(first-last)/denom)); scaled=max(scaled,error)
        phases[name]=dict(labels_agree=bool(np.array_equal(labels(a['final'],INDEX),labels(b['final'],INDEX))),
            max_primary_scaled_error=error,max_absolute_difference=float(np.max(np.abs(a['final']-b['final']))))
    common_left=p27.p21.observed_behavior(p27.first_challenge(x,left))
    common_right=p27.p21.observed_behavior(p27.first_challenge(y,right))
    return dict(left=left['id'],right=right['id'],phase_inventory_agrees=set(x)==set(y),
        outcomes_agree=by[left['id']]==by[right['id']],
        all_phase_labels_agree=all(p['labels_agree'] for p in phases.values()),
        common_grid_diagnostics_agree=common_left==common_right,
        max_primary_scaled_error=scaled,phases=phases)

def convergence_report(by,data):
    adjacent=[]; finest=[]
    for h in ('written','ordinary'):
        for k in ('baseline','pause_0_5','pause_0_25','pause_10_100'):
            for f in (False,True):
                comparisons=[]
                for lo,hi in ((1,2),(2,4),(4,8),(8,16)):
                    row=pair(spec(h,k,f,lo),spec(h,k,f,hi),by,data)
                    row.update(founder=h,condition=k,source_fine=f,levels=[lo,hi])
                    adjacent.append(row); comparisons.append(row)
                previous,last=comparisons[-2:]
                acceptable=(last['phase_inventory_agrees'] and last['outcomes_agree'] and last['all_phase_labels_agree']
                    and last['common_grid_diagnostics_agree'] and last['max_primary_scaled_error']<=.01
                    and last['max_primary_scaled_error']<=previous['max_primary_scaled_error']+1e-12)
                finest.append(dict(founder=h,condition=k,source_fine=f,levels=[8,16],
                    maximum_scaled_error=last['max_primary_scaled_error'],
                    preceding_scaled_error=previous['max_primary_scaled_error'],
                    converged=bool(acceptable)))
    sources=[]
    for h in ('written','ordinary'):
        for k in ('baseline','pause_0_5','pause_0_25','pause_10_100'):
            row=pair(spec(h,k,False,16),spec(h,k,True,16),by,data)
            row.update(founder=h,condition=k,resolution=16,
                source_robust=bool(row['phase_inventory_agrees'] and row['outcomes_agree'] and row['all_phase_labels_agree']
                    and row['common_grid_diagnostics_agree'] and row['max_primary_scaled_error']<=.01))
            sources.append(row)
    return dict(adjacent_resolution_comparisons=adjacent,finest_resolution_comparisons=finest,
        source_precision_comparisons=sources,all_finest_converged=all(x['converged'] for x in finest),
        all_source_comparisons_agree=all(x['source_robust'] for x in sources),
        refined_full_panel_supported=bool(all(x['converged'] for x in finest) and all(x['source_robust'] for x in sources)),
        original_P27_quality_gate=False,qualified_onward_transmission_established=False)

def stage_audit(run,stage):
    summary=d.read(run/'summary.json'); checks=Checks(); cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and d.read(path)==row['result'])
        branch_report,data=branch(run/c['id'],c,checks)
        branches.append(branch_report); by[c['id']]=branch_report['outcome']; calls+=len(data)
        # Clock/geometry arrays are audited above; retain only convergence samples.
        endpoints[c['id']]={name:{k:a[k] for k in ('times','concentrations','initial','final')} for name,a in data.items()}
    n,calls_wanted=(16,416) if stage=='replay' else (80,2080)
    checks.add('counts',len(branches)==n and calls==calls_wanted)
    checks.add('unique_records',len(records)==len(summary['cases']))
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    checks.add('diagnostic_history',summary['predecessor_gate'] and history.get('quality_gate') is True and history.get('predecessor_quality_gate') is False
        and history==d.read(hp) and d.digest(hp)==summary['predecessor_audit_sha256'])
    anchors=control_anchors(by,run,cases); checks.add('anchor_count',len(anchors)==(8 if stage=='replay' else 40))
    checks.add('anchors_qualified',all(x['qualified'] for x in anchors))
    prefixes=prefix_comparisons(run,cases,checks) if len(branches)==n else []
    checks.add('prefix_count',len(prefixes)==(8 if stage=='replay' else 40))
    result=convergence_report(by,endpoints) if stage=='convergence' and len(branches)==n else {}
    if result:
        checks.add('comparison_inventory',len(result['adjacent_resolution_comparisons'])==64 and len(result['finest_resolution_comparisons'])==16 and len(result['source_precision_comparisons'])==8)
    integrity=d.integrity(run,summary)
    return dict(stage=stage,quality_gate=bool(all(checks.rows.values()) and all(integrity.values())),checks=checks.rows,integrity=integrity,
        branches=branches,integration_calls=calls,cumulative_cases=len(branches),anchor_controls=anchors,
        shared_schedule_prefix_comparisons=prefixes,convergence=result,favorable_convergence_required_for_valid_diagnosis=False)

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p28_numerical_convergence/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases()); stages=summary.get('attempted_stages',[])
    checks.add('all_stages',stages==['replay','convergence'])
    history=predecessor_audit(run); checks.add('history',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json')) and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    checks.add('all_cases',len(summary['cases'])==80 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary['all_execution_valid'] is True and summary.get('completion_reason')=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); valid=bool(all(checks.rows.values()) and all(integrity.values()))
    final=reports.get('convergence',{}); convergence=final.get('convergence',{})
    return dict(run=str(run),quality_gate=valid,ready_for_interpretation=valid,checks=checks.rows,integrity=integrity,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final.get('integration_calls',0),
        independent_check_count=len(checks.rows)+len(final.get('checks',{})),**convergence,
        ready_for_refined_full_panel=bool(valid and convergence.get('refined_full_panel_supported')),
        historical_mathematical_audit_repeated=False,scientific_scope='targeted_numerical_diagnosis',automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path); args=p.parse_args()
    run=args.run.absolute(); d.check_run_path(run); report=analyze(run); d.write_json(run/'independent_audit.json',report)
    print({k:report.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_finest_converged','all_source_comparisons_agree','ready_for_refined_full_panel')},flush=True)
    return 0 if report['quality_gate'] else 1
if __name__=='__main__': raise SystemExit(main())
