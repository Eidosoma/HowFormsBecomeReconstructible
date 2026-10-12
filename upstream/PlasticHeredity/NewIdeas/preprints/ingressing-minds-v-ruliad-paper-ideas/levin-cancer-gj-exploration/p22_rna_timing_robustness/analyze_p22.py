"""Independent P22 assembly, draw, schedule, lineage and result reconstruction."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
import p22_design as d
import analyze_p21 as p21

p19=p21.p19
Checks,labels,arrays,INDEX=p19.Checks,p19.labels,p19.arrays,p19.INDEX
STAGES=('replay','rna','timing_controls','timing','robust','onward')
KNOWN=('none','newcomer_protein','newcomer_rna','neighbour_rna')
SINGLES=('newcomer_mir200','newcomer_zebmrna','neighbour_mir200','neighbour_zebmrna')
WINDOWS=('rna_early','rna_middle','rna_late','rna_full','isolated_full')

def spec(panel='rna',founder='written',route='newcomer_mir200',window='open',draw='legacy',replacements=5,readout='',fine=False):
    stage='onward' if readout else panel
    parts=([stage,panel] if readout else [panel])+[founder,route,window,draw,str(replacements)]+([readout] if readout else [])
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,panel=panel,founder=founder,
        route=route,window=window,draw=draw,replacements=replacements,readout=readout,fine=fine)
def expected_stage(stage):
    if stage=='onward':
        return [spec(c['panel'],c['founder'],c['route'],c['window'],c['draw'],c['replacements'],q,c['fine'])
            for panel in ('replay','rna','robust') for c in expected_stage(panel) for q in ('open','rna','cut')]
    if stage not in STAGES: raise ValueError('Unknown P22 stage')
    conditions=[]
    for route in (SINGLES if stage=='rna' else KNOWN):
        if stage=='robust':
            for draw in ('legacy','heldout_17021','heldout_17022'):
                for n in (5,11):
                    if draw!='legacy' or n==11: conditions.append((route,'open',draw,n))
        else:
            for window in (WINDOWS if stage=='timing' else ('open',)): conditions.append((route,window,'legacy',5))
    return [spec(stage,h,r,w,draw,n,fine=f) for f in (False,True) for h in ('written','ordinary') for r,w,draw,n in conditions]
def expected_cases(last='onward'): return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s)]
def parent(c): return spec(c['panel'],c['founder'],c['route'],c['window'],c['draw'],c['replacements'],fine=c['fine'])
def twin(c,fine,readout=''): return spec(c['panel'],c['founder'],c['route'],c['window'],c['draw'],c['replacements'],readout,fine)
def stem(c): return 'p22:%s:%s:%s:%s:%s:%d'%(c['panel'],c['founder'],c['route'],c['window'],c['draw'],c['replacements'])
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return 'controls__'+c['founder']+'__component__none__0'+('__fine' if c['fine'] else '')
def reference(c):
    target,mask={'none':('none',0),'newcomer_protein':('newcomer',1),'newcomer_rna':('newcomer',2),'neighbour_rna':('neighbour',2)}[c['route']]
    stage='onward' if c['readout'] else 'controls' if mask==0 else 'components'
    return '__'.join([stage,c['founder'],'component',target,str(mask)]+([c['readout']] if c['readout'] else []))+('__fine' if c['fine'] else '')
def replay(c):
    if c['panel']=='replay':
        names=['contact','isolated_1','isolated_2'] if c['readout'] else ['replacement_%02d'%i for i in range(2,7)]+['isolated_1','isolated_2']
    elif c['panel']=='robust' and c['draw']=='legacy' and not c['readout']: names=['replacement_%02d'%i for i in range(2,7)]
    else: return None
    return dict(source='p21/'+reference(c),phases=names)
def expected_word(draw,event):
    namespace,seed={'legacy':('P16_turnover_limit_v1',501),'heldout_17021':('P22_incoming_v1',17021),
        'heldout_17022':('P22_incoming_v1',17022)}[draw]
    return int.from_bytes(hashlib.sha256(f'{namespace}|{seed}|turnover|{event}'.encode('ascii')).digest()[:8],byteorder='big')
def expected_draws(): return {k:['%016x'%expected_word(k,i) for i in range(1,12)] for k in ('legacy','heldout_17021','heldout_17022')}
def incoming(M,c,event):
    result=M.copy(); pct=(expected_word(c['draw'],event)*51)//(1<<64)-25
    # Preserve the registered floating-point multiplication order as well.
    result[7,0]=M[7,0]*(1+pct/100)
    return result
def window_routes(c):
    if c['window']=='isolated_full': return ['isolated','isolated','isolated']
    blocked={'open':(), 'rna_early':(0,), 'rna_middle':(1,), 'rna_late':(2,), 'rna_full':(0,1,2)}[c['window']]
    return ['rna' if i in blocked else 'open' for i in range(3)]
def stock(run,fine): return p21.stock(run/'inputs/p21',fine)
canonical_binding=p21.canonical_binding

class Reader(p19.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks; self.result=d.read(folder/'result.json')
        self.records=self.result['phases']; self.at=0; self.data={}
        self.environment=arrays(p19.stock_folder(folder.parent/'inputs/p21/inputs/p20/inputs/p19',c['fine']),'preparation')['environment']

def audit_assembly(rd,run,c):
    src=run/'inputs/p21'/source(c); old=d.read(src/'result.json'); source_meta=d.read(src/'assembly/assembly.json')
    checkpoint=arrays(src/'assembly','checkpoint'); before,after=checkpoint['before'],checkpoint['after']
    rd.ck('source_case',old['case']==p21.spec(founder=c['founder'],target='none',mask=0,fine=c['fine']))
    originals=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    ids=['p17:%s:100:open:replacement:0:0'%c['founder']]+originals[1:]
    rd.ck('source_identity',source_meta['cell_ids']==ids and old['outcome']['original_ids']==originals)
    rd.ck('source_epoch',source_meta['common_logical_start']==1180300)
    rd.ck('source_archive',source_meta==old['provenance']['assembly'] and
        d.digest(src/'assembly/assembly.json')==old['provenance']['assembly_metadata_sha256'] and
        d.digest(src/'assembly/checkpoint.npz')==source_meta['checkpoint_sha256'])
    rd.ck('source_shape',before.shape==after.shape==(17,3))
    rd.ck('fixed_inputs',np.all(before[4]==72) and np.all(after[4]==72) and not before[16].any() and not after[16].any())
    pos=0 if c['route'].startswith('newcomer_') else 2 if c['route'].startswith('neighbour_') else None
    suffix=c['route'].split('_')[-1]; rows={'none':[],'protein':[7],'rna':[5,6],'mir200':[5],'zebmrna':[6]}[suffix]
    hybrid=before.copy()
    for row in rows: hybrid[row,pos]=after[row,pos]
    expected=canonical_binding(hybrid); folder=rd.folder/'assembly'; saved=arrays(folder,'checkpoint'); meta=d.read(folder/'assembly.json')
    rd.ck('assembly_inventory',{p.name for p in folder.iterdir()}=={'checkpoint.npz','assembly.json'} and set(saved)=={'before','after','hybrid_before_refresh','assembled'})
    for name,value in (('before',before),('after',after),('hybrid_before_refresh',hybrid),('assembled',expected)): rd.eq('assembly/'+name,saved[name],value)
    rd.eq('refresh_preserves_primary',saved['assembled'][list(range(8))+[16]],hybrid[list(range(8))+[16]])
    rd.eq('derived_not_independently_edited',saved['hybrid_before_refresh'][8:16],before[8:16])
    rd.eq('discarded_column_before',saved['hybrid_before_refresh'][:,1],before[:,1])
    for j in range(3):
        for row in list(range(8))+[16]:
            if j!=pos or row not in rows: rd.ck('untouched_%d_%d'%(row,j),saved['hybrid_before_refresh'][row,j]==before[row,j])
    expected_meta=dict(source='p21/'+source(c),source_result_sha256=d.digest(src/'result.json'),
        source_checkpoint_sha256=d.digest(src/'assembly/checkpoint.npz'),source_metadata_sha256=d.digest(src/'assembly/assembly.json'),
        route=c['route'],edited_primary_rows=rows,edited_column=pos,cell_ids=ids.copy(),original_ids=originals.copy(),
        common_logical_start=1180300,algebraic_refresh=True,refresh_columns=[0,1,2],checkpoint_sha256=d.digest(folder/'checkpoint.npz'))
    rd.ck('assembly_metadata',meta==expected_meta)
    rd.ck('assembly_provenance',rd.result['provenance']['assembly']==expected_meta and
        rd.result['provenance']['assembly_metadata_sha256']==d.digest(folder/'assembly.json'))
    rd.ck('initial_EEE',''.join(labels(expected,INDEX))=='EEE')
    return expected,ids,originals

def first_challenge(data,c):
    if c['panel'] not in ('timing_controls','timing'): return data['replacement_02']
    values=[]; times=[]
    for part in range(3):
        x=data['challenge_%02d'%(part+1)]
        for i,t in enumerate(x['times']):
            if part and i==0: continue
            absolute=100*part+float(t)
            if absolute in range(0,301,15): times.append(absolute); values.append(x['concentrations'][i])
    if times!=list(range(0,301,15)): raise ValueError('Missing common challenge sample')
    return dict(times=np.array(times),concentrations=np.array(values),initial=data['challenge_01']['initial'],final=data['challenge_03']['final'])

def audit_renewal(rd,run,c):
    value,ids,originals=audit_assembly(rd,run,c); initial=ids.copy(); lab=''.join(labels(value,INDEX))
    _,M=stock(run,c['fine']); observations={}; replacements=[]; cursor=1180300
    for event in range(1,c['replacements']+1):
        cycle,pos=divmod(event,3); x=incoming(M,c,event); incoming_label=str(labels(x,INDEX)[0]); rd.ck('incoming_%d_M'%event,incoming_label=='M')
        value=value.copy(); removed=ids[pos]; ids[pos]=new_id(c,cycle,pos); value[:,pos:pos+1]=x
        replacements.append(dict(event=event+1,cycle=cycle,position=pos,removed=removed,inserted=ids[pos],initial_label=incoming_label))
        name='replacement_%02d'%(event+1)
        if event==1 and c['panel'] in ('timing_controls','timing'):
            for number,route in enumerate(window_routes(c),1):
                value=rd.take(p19.descriptor('challenge_%02d'%number,ids,cursor,100,'isolated' if route=='isolated' else 'chain',route),value); cursor+=100
            first=first_challenge(rd.data,c); observations[name]=p19.observation(first,range(3))
        else:
            value=rd.take(p19.descriptor(name,ids,cursor,300,'chain'),value); cursor+=300
            observations[name]=p19.observation(rd.data[name],range(3))
    complete=not bool(set(ids)&set(originals+initial)); rd.ck('complete_carrier_replacement',complete)
    rd.ck('schedule',cursor==1180300+300*c['replacements'] and [x['position'] for x in replacements]==[i%3 for i in range(1,c['replacements']+1)])
    cursor=p19.holds(rd,ids,value,cursor,observations); diagnostic=p21.observed_behavior(first_challenge(rd.data,c))
    rd.ck('trajectory_diagnostics',rd.result['provenance']['trajectory_diagnostics']==diagnostic)
    rd.ck('provenance_inventory',set(rd.result['provenance'])=={'assembly','assembly_metadata_sha256','trajectory_diagnostics'})
    return dict(available=True,fork_ids=initial,original_ids=originals,assembly_labels=lab,observations=observations,
        replacements=replacements,retained_E=all(p19.masks(observations)),first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement')),
        complete_carrier_replacement=complete,logical_end=cursor,first_cell_sampled_behavior=diagnostic['sampled_behavior'],first_cell_M_observed=diagnostic['M_observed'])

def audit_readout(rd,run,c):
    rd.ck('onward_panel',c['panel'] in ('replay','rna','robust'))
    _,M=stock(run,c['fine']); par=parent(c); path=run/par['id']; record=d.read(path/'result.json'); donors=arrays(path,'isolated_2')['final']
    cycle=(c['replacements']-2)//3; ids=[new_id(c,cycle,i) for i in range(3)]; base=1200300+300*c['replacements']
    rd.ck('actual_parent',record['case']==par and record['phases'][-1]['setup']['cell_ids']==ids and
        record['outcome']['logical_end']==base and record['phases'][-1]['logical_interval']==[base-10000,base])
    rd.ck('parent_provenance',rd.result['provenance']==dict(actual_parent=par['id'],parent_result_sha256=d.digest(path/'result.json'),parent_phase_sha256=d.digest(path/'isolated_2.npz')))
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1); donor_initial=''.join(labels(donors,INDEX)); recipient_initial=''.join(labels(recipients,INDEX))
    rd.ck('fresh_M',recipient_initial=='MMM'); rd.ck('donors_discarded',not bool(set(ids)&set(fresh)))
    value=rd.take(p19.descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),np.concatenate((donors,recipients),axis=1))
    observations={'contact':p19.observation(rd.data['contact'],range(3,6))}; donor_end=''.join(labels(value[:,:3],INDEX))
    p19.holds(rd,fresh,value[:,3:],base+20000,observations)
    return dict(available=True,donor_initial_labels=donor_initial,recipient_initial_labels=recipient_initial,donor_end_labels=donor_end,
        observations=observations,transmitted_E=all(p19.masks(observations)),logical_end=base+40000)

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result.get('clock_method')=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','only_registered_primary_edits','fixed_onward_schedules','counterfactual_reconstruction')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('autonomous_reproduction','cell_division_simulated','parameter_retuning','independent_biological_replicates','outcome_dependent_selection','automatic_follow_on')))
    rd.ck('refresh_scope',result.get('algebraic_refresh_at_assembly')==(not bool(c['readout'])))
    rd.ck('segmented_scope',result.get('segmented_first_challenge')==(c['panel'] in ('timing_controls','timing')))
    rd.ck('network_scope',result.get('global_network_timing_intervention')==(c['panel']=='timing'))
    rd.ck('draw_scope',result.get('new_incoming_protein_draws')==(c['draw']!='legacy'))
    out=(audit_readout if c['readout'] else audit_renewal)(rd,folder.parent,c)
    ref=replay(c); rd.ck('replay_provenance',result.get('historical_numeric_replay')==ref)
    if ref:
        for name in ref['phases']:
            data=rd.data[name]; historical=arrays(folder.parent/'inputs'/ref['source'],name)
            rd.ck(name+'/replay_inventory',set(data)==set(historical))
            for key in historical: rd.eq(name+'/historical_replay/'+key,data[key],historical[key])
    return rd.finish(out)

def replay_controls(by,onward=False):
    result=[]
    for f in (False,True):
        for h in ('written','ordinary'):
            for route in KNOWN:
                out=by.get(spec('replay',h,route,fine=f)['id'],{}); expected=route!='none'
                renewal=out.get('available') is True and out.get('retained_E') is expected
                transmitted=True
                if onward:
                    for q in ('open','rna','cut'):
                        x=by.get(spec('replay',h,route,readout=q,fine=f)['id'],{})
                        transmitted &= x.get('available') is True and x.get('transmitted_E') is (expected and q=='open')
                result.append(dict(founder=h,route=route,fine=f,renewal_qualified=renewal,onward_checked=onward,
                    onward_qualified=bool(transmitted),qualified=bool(renewal and transmitted)))
    return result

def timing_controls(by):
    keys=('assembly_labels','observations','retained_E','first_cell_label_after_second','first_cell_stable_E_after_second',
        'later_windows_E','complete_carrier_replacement','logical_end','first_cell_sampled_behavior','first_cell_M_observed')
    result=[]
    for f in (False,True):
        for h in ('written','ordinary'):
            for route in KNOWN:
                raw=by.get(spec('replay',h,route,fine=f)['id'],{}); split=by.get(spec('timing_controls',h,route,fine=f)['id'],{})
                good=raw.get('available') is True and split.get('available') is True and all(raw.get(k)==split.get(k) for k in keys)
                result.append(dict(founder=h,route=route,fine=f,qualified=bool(good)))
    return result

def stage_audit(run,stage):
    summary=d.read(run/'summary.json'); checks=Checks(); cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; value=d.read(path)
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and value==row['result'])
        report,data=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']; endpoints[c['id']]=data; calls+=len(data)
    fine=p19.p18.p12.compare_fine(cases,by,endpoints,checks); history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==d.read(run/'predecessor_audit.json') and d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    counts={'replay':(16,112),'rna':(32,224),'timing_controls':(48,368),'timing':(128,1088),'robust':(208,1936),'onward':(544,2944)}
    checks.add('count',len(branches)==counts[stage][0] and calls==counts[stage][1])
    checks.add('unique_records',len(records)==len(summary['cases']))
    checks.add('registered_records',set(records).issubset({c['id'] for c in expected_cases()}))
    checks.add('draw_book',d.read(run/'frozen/p22_rna_timing_robustness/draws.json')==expected_draws())
    controls=replay_controls(by,stage=='onward'); checks.add('replay_controls_qualified',all(x['qualified'] for x in controls))
    timing=timing_controls(by) if STAGES.index(stage)>=2 else []
    checks.add('segmentation_qualified',all(x['qualified'] for x in timing))
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    return dict(stage=stage,quality_gate=bool(quality),checks=checks.rows,integrity=integrity,branches=branches,
        fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches),replay_controls=controls,timing_controls=timing,
        favorable_novel_outcomes_required=False)

def predecessor_audit(run):
    fresh=p21.analyze(d.P21_RUN); saved=d.read(run/'inputs/p21/independent_audit.json')
    archive=all(d.integrity(run,d.read(run/'summary.json')).values())
    good=fresh==saved and fresh['quality_gate'] and fresh['independent_check_count']==87985 and archive
    return dict(quality_gate=bool(good),original_matches_saved=fresh==saved,archive_byte_identical=archive,
        prior_checks=fresh['independent_check_count'],prior_cases=fresh['completed_cases'],prior_calls=fresh['integration_calls'],
        original_reaudit_count=1,archive_separate_mathematical_reaudit=False,reference_is_independent_backup=False,original_audit_file_rewritten=False)

def contrasts(by,inherited,controls_qualified):
    capacity=inherited.get('inherited_readout_capacity_qualified') is True; wipe=inherited.get('inherited_wipe_qualified') is True
    def both(c,key,value=True,readout=''):
        rows=[by.get(twin(c,f,readout)['id'],{}) for f in (False,True)]
        return all(x.get('available') is True and x.get(key) is value for x in rows)
    def profile(c,onward=True):
        rows=[by.get(twin(c,f)['id'],{}) for f in (False,True)]
        behavior=rows[0].get('first_cell_sampled_behavior') if all(x.get('available') is True for x in rows) and rows[0].get('first_cell_sampled_behavior')==rows[1].get('first_cell_sampled_behavior') else 'missing_or_disagree'
        retained=both(c,'retained_E'); blocked=onward and all(both(c,'transmitted_E',False,q) for q in ('rna','cut'))
        transmitted=onward and both(c,'transmitted_E',readout='open')
        return dict(retained_E_both=retained,retained_E_false_both=both(c,'retained_E',False),
            first_cell_sampled_behavior_both=behavior,first_cell_stable_E_after_second_both=both(c,'first_cell_stable_E_after_second'),
            later_windows_E_both=both(c,'later_windows_E'),onward_assayed=onward,
            onward_transmission_both=bool(transmitted),negative_readout_controls_both=bool(blocked),
            qualified_chain=bool(controls_qualified and retained and transmitted and blocked and capacity and wipe))
    rna_grid=[]; rna_interpretations=[]; timing_grid=[]; robustness_grid=[]
    for h in ('written','ordinary'):
        baseline=spec('replay',h,'none')
        for loc in ('newcomer','neighbour'):
            conditions=[baseline,spec('rna',h,loc+'_mir200'),spec('rna',h,loc+'_zebmrna'),spec('replay',h,loc+'_rna')]
            qualified=controls_qualified and both(baseline,'retained_E',False) and both(conditions[3],'retained_E')
            rows=[dict(founder=h,target=loc,mask=i,route=c['route'],**profile(c),control_qualified_rescue=bool(qualified and i and both(c,'retained_E'))) for i,c in enumerate(conditions)]
            rna_grid.extend(rows); success=[i for i in (1,2) if rows[i]['control_qualified_rescue']]
            interpretation='controls_unqualified' if not qualified else 'both_single_changes_sufficient' if len(success)==2 else 'miR200_alone_sufficient' if success==[1] else 'Zeb_mRNA_alone_sufficient' if success==[2] else 'both_changes_required_at_tested_values'
            rna_interpretations.append(dict(founder=h,target=loc,controls_qualified=bool(qualified),interpretation=interpretation,
                miR200_removal_loses_rescue=bool(qualified and rows[2]['retained_E_false_both']),
                Zeb_mRNA_removal_loses_rescue=bool(qualified and rows[1]['retained_E_false_both']),
                minimal_tested_rescue_masks=success or ([3] if qualified else []),
                necessity_scope='prepared_RNA_pair_with_unprepared_protein_and_ions'))
        for route in KNOWN:
            control=profile(spec('timing_controls',h,route),False)
            for window in ('open',)+WINDOWS:
                c=spec('timing_controls' if window=='open' else 'timing',h,route,window); row=profile(c,False)
                timing_grid.append(dict(founder=h,route=route,window=window,**row,
                    sampled_behavior_differs_from_open=row['first_cell_sampled_behavior_both']!=control['first_cell_sampled_behavior_both'],
                    loss_of_retention_vs_open=control['retained_E_both'] and row['retained_E_false_both'],
                    intervention_scope='whole_network'))
            for draw in ('legacy','heldout_17021','heldout_17022'):
                for n in (5,11):
                    panel='replay' if draw=='legacy' and n==5 else 'robust'
                    c=spec(panel,h,route,draw=draw,replacements=n); row=profile(c)
                    matched=spec(panel,h,'none',draw=draw,replacements=n); baseline_failed=both(matched,'retained_E',False)
                    robustness_grid.append(dict(founder=h,route=route,draw=draw,replacements=n,**row,
                        matched_baseline_fails_both=baseline_failed,
                        preparation_specific_rescue=bool(controls_qualified and route!='none' and baseline_failed and row['retained_E_both']),
                        source_trials=1,independent_biological_replicates=False))
    return dict(inherited_readout_capacity_qualified=capacity,inherited_wipe_qualified=wipe,rna_grid=rna_grid,
        rna_interpretations=rna_interpretations,timing_grid=timing_grid,robustness_grid=robustness_grid)

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p22_rna_timing_robustness/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases()); stages=summary.get('attempted_stages',[])
    checks.add('all_stages',stages==list(STAGES)); history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit']); reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json')) and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==544 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}; inherited=d.read(run/'inputs/p21/independent_audit.json')
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=integrity,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(x['agree'] for x in final['fine_comparisons']),
        **contrasts(by,inherited,all(x['qualified'] for x in final['replay_controls']+final['timing_controls'])),
        inherited_controls_newly_integrated=False,external_schedule=True,counterfactual_component_intervention=True,
        unique_molecular_carrier_established=False,autonomous_reproduction=False,independent_biological_replicates=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path); args=p.parse_args()
    run=args.run.absolute(); d.check_run_path(run); report=analyze(run); d.write_json(run/'independent_audit.json',report)
    print({k:report.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree','rna_interpretations')},flush=True)
    return 0 if report['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
