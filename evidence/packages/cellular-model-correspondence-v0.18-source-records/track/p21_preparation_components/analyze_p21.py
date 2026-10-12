"""Independent P21 primary-component, binding-refresh, lineage and outcome audit."""
import argparse
from pathlib import Path
import numpy as np
import p21_design as d
import analyze_p20 as p20

p19=p20.p19
Checks,labels,arrays,INDEX=p19.Checks,p19.labels,p19.arrays,p19.INDEX
STAGES=('controls','components','onward')

def spec(stage='components',founder='written',kind='component',target='newcomer',mask=1,readout='',fine=False):
    if stage!='onward': stage='controls' if kind=='historical' or mask in (0,7) else 'components'
    if mask==0: target='none'
    parts=[stage,founder,kind,target,str(mask)]+([readout] if readout else [])
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,
        kind=kind,target=target,mask=mask,readout=readout,fine=fine)

def expected_stage(stage):
    if stage not in STAGES: raise ValueError('Unknown P21 stage')
    conditions=[('historical','none',0),('historical','newcomer',7),('historical','neighbour',7),('component','none',0)]
    conditions += [('component',t,m) for t in ('newcomer','neighbour') for m in (1,2,3,4,5,6,7)]
    return [c for f in (False,True) for h in ('written','ordinary') for k,t,m in conditions
        for q in (('open','rna','cut') if stage=='onward' else ('',))
        for c in [spec(stage,h,k,t,m,q,f)] if c['stage']==stage]
def expected_cases(last='onward'): return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s)]
def parent(c): return spec('components',c['founder'],c['kind'],c['target'],c['mask'],fine=c['fine'])
def stem(c): return 'p21:%s:%s:%s:%d'%(c['founder'],c['kind'],c['target'],c['mask'])
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c):
    loc=c['target'] if c['kind']=='historical' else 'none'
    return 'renewal__%s__%s__%s'%(c['founder'],'after' if loc=='newcomer' else 'before',
        'after' if loc=='neighbour' else 'before')+('__fine' if c['fine'] else '')
def replay(c):
    if c['kind']!='historical': return None
    s='onward' if c['stage']=='onward' else 'renewal'
    return 'p20/'+s+'__'+c['founder']+'__'+('after' if c['target']=='newcomer' else 'before')+'__'+(
        'after' if c['target']=='neighbour' else 'before')+('__'+c['readout'] if s=='onward' else '')+('__fine' if c['fine'] else '')
def stock(run,fine): return p20.stock(run/'inputs/p20',fine)

def canonical_binding(value):
    """Independent formula for the pinned non-iterative native binding rule."""
    result=value.copy(); ratio=value[5]/40.0
    result[8]=value[5]
    for n in range(7): result[9+n]=value[6]*(ratio**n)/((1+ratio)**6)
    return result

def observed_behavior(data):
    times=data['times'].tolist(); lab=labels(data['concentrations'],INDEX)[:,0].tolist()
    loss=next((i for i,x in enumerate(lab) if x!='E'),None)
    regained=next((i for i,x in enumerate(lab) if loss is not None and i>loss and x=='E'),None)
    interval=lambda i:None if i is None else [float(times[max(0,i-1)]),float(times[i])]
    mode='sampled_E_resistance' if loss is None else 'sampled_recovery_to_E' if lab[-1]=='E' else 'no_E_recovery_by_300'
    return dict(sample_times=times,newcomer_labels=lab,sampled_behavior=mode,M_observed='M' in lab,
        first_non_E_bracket=interval(loss),first_return_E_bracket=interval(regained))

class Reader(p19.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks; self.result=d.read(folder/'result.json')
        self.records=self.result['phases']; self.at=0; self.data={}
        self.environment=arrays(p19.stock_folder(folder.parent/'inputs/p20/inputs/p19',c['fine']),'preparation')['environment']

def audit_assembly(rd,run,c):
    src=run/'inputs/p20'/source(c); old=d.read(src/'result.json'); source_meta=d.read(src/'assembly/assembly.json')
    checkpoint=arrays(src/'assembly','checkpoint'); before,after=checkpoint['before'],checkpoint['after']
    target=c['target'] if c['kind']=='historical' else 'none'
    expected_case=p20.spec(founder=c['founder'],newcomer='after' if target=='newcomer' else 'before',
        neighbours='after' if target=='neighbour' else 'before',fine=c['fine'])
    rd.ck('source_case',old['case']==expected_case)
    original=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    ids=['p17:%s:100:open:replacement:0:0'%c['founder']]+original[1:]
    rd.ck('source_identity',source_meta['cell_ids']==ids and old['outcome']['original_ids']==original)
    rd.ck('source_epoch',source_meta['common_logical_start']==1180300)
    rd.ck('source_binding_archive',source_meta==old['provenance']['assembly'] and
        d.digest(src/'assembly/assembly.json')==old['provenance']['assembly_metadata_sha256'] and
        d.digest(src/'assembly/checkpoint.npz')==source_meta['checkpoint_sha256'])
    rd.ck('source_shape',before.shape==after.shape==(17,3))
    rd.ck('fixed_source_inputs',np.all(before[4]==72) and np.all(after[4]==72) and not before[16].any() and not after[16].any())
    hybrid=checkpoint['assembled'].copy() if c['kind']=='historical' else before.copy()
    selected=([7] if c['mask']&1 else [])+([5,6] if c['mask']&2 else [])+([0,1,2,3] if c['mask']&4 else [])
    pos={'newcomer':0,'neighbour':2}.get(c['target'])
    if c['kind']=='component' and c['mask']:
        for row in selected: hybrid[row,pos]=after[row,pos]
    expected=canonical_binding(hybrid) if c['kind']=='component' else hybrid.copy()
    folder=rd.folder/'assembly'; saved=arrays(folder,'checkpoint'); meta=d.read(folder/'assembly.json')
    rd.ck('assembly_inventory',{p.name for p in folder.iterdir()}=={'checkpoint.npz','assembly.json'} and
        set(saved)=={'before','after','hybrid_before_refresh','assembled'})
    for n,x in (('before',before),('after',after),('hybrid_before_refresh',hybrid),('assembled',expected)):
        rd.eq('assembly/'+n,saved[n],x)
    rd.eq('refresh_preserves_primary',saved['assembled'][list(range(8))+[16]],hybrid[list(range(8))+[16]])
    if c['kind']=='component':
        rd.eq('derived_not_independently_edited',saved['hybrid_before_refresh'][8:16],before[8:16])
        rd.eq('discarded_column_before_refresh',saved['hybrid_before_refresh'][:,1],before[:,1])
        for j in range(3):
            for row in list(range(8))+[16]:
                if j!=pos or row not in selected:
                    rd.ck('untouched_primary_%d_%d'%(row,j),saved['hybrid_before_refresh'][row,j]==before[row,j])
    expected_meta=dict(source='p20/'+source(c),source_result_sha256=d.digest(src/'result.json'),
        source_checkpoint_sha256=d.digest(src/'assembly/checkpoint.npz'),source_metadata_sha256=d.digest(src/'assembly/assembly.json'),
        kind=c['kind'],target=c['target'],mask=c['mask'],edited_primary_rows=sorted(selected) if c['kind']=='component' else [],
        edited_column=pos if c['kind']=='component' else None,cell_ids=ids.copy(),original_ids=original.copy(),common_logical_start=1180300,
        algebraic_refresh=c['kind']=='component',refresh_columns=[0,1,2] if c['kind']=='component' else [],
        checkpoint_sha256=d.digest(folder/'checkpoint.npz'))
    rd.ck('assembly_metadata',meta==expected_meta)
    rd.ck('assembly_provenance',rd.result['provenance']['assembly']==expected_meta and
        rd.result['provenance']['assembly_metadata_sha256']==d.digest(folder/'assembly.json'))
    rd.ck('initial_EEE',''.join(labels(expected,INDEX))=='EEE')
    return expected,ids,original

def audit_renewal(rd,run,c):
    value,ids,original=audit_assembly(rd,run,c); initial=ids.copy(); lab=''.join(labels(value,INDEX))
    _,M=stock(run,c['fine']); observations={}; replacements=[]; cursor=1180300
    for at in range(1,6):
        cycle,pos=divmod(at,3); x=p19.incoming(M,cycle,pos); incoming_label=str(labels(x,INDEX)[0]); rd.ck('incoming_%d_M'%at,incoming_label=='M')
        value=value.copy(); old=ids[pos]; ids[pos]=new_id(c,cycle,pos); value[:,pos:pos+1]=x
        replacements.append(dict(event=at+1,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=incoming_label))
        name='replacement_%02d'%(at+1); value=rd.take(p19.descriptor(name,ids,cursor,300,'chain'),value); cursor+=300
        observations[name]=p19.observation(rd.data[name],range(3))
    complete=not bool(set(ids)&set(original+initial)); rd.ck('complete_carrier_replacement',complete)
    rd.ck('schedule',cursor==1181800 and [r['position'] for r in replacements]==[1,2,0,1,2])
    cursor=p19.holds(rd,ids,value,cursor,observations); diagnostic=observed_behavior(rd.data['replacement_02'])
    rd.ck('trajectory_diagnostics',rd.result['provenance']['trajectory_diagnostics']==diagnostic)
    rd.ck('provenance_inventory',set(rd.result['provenance'])=={'assembly','assembly_metadata_sha256','trajectory_diagnostics'})
    return dict(available=True,fork_ids=initial,original_ids=original,assembly_labels=lab,observations=observations,
        replacements=replacements,retained_E=all(p19.masks(observations)),
        first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement')),
        complete_carrier_replacement=complete,logical_end=cursor,first_cell_sampled_behavior=diagnostic['sampled_behavior'],
        first_cell_M_observed=diagnostic['M_observed'])

def audit_readout(rd,run,c):
    _,M=stock(run,c['fine']); par=parent(c); path=run/par['id']; record=d.read(path/'result.json')
    donors=arrays(path,'isolated_2')['final']; ids=[new_id(c,1,i) for i in range(3)]; base=1201800
    rd.ck('actual_parent',record['case']==par and record['phases'][-1]['setup']['cell_ids']==ids and
        record['outcome']['logical_end']==base and record['phases'][-1]['logical_interval']==[base-10000,base])
    rd.ck('parent_provenance',rd.result['provenance']==dict(actual_parent=par['id'],parent_result_sha256=d.digest(path/'result.json'),
        parent_phase_sha256=d.digest(path/'isolated_2.npz')))
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1); donor_initial=''.join(labels(donors,INDEX)); recipient_initial=''.join(labels(recipients,INDEX))
    rd.ck('fresh_M',recipient_initial=='MMM'); rd.ck('donors_discarded',not bool(set(ids)&set(fresh)))
    value=rd.take(p19.descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),np.concatenate((donors,recipients),axis=1))
    observations={'contact':p19.observation(rd.data['contact'],range(3,6))}; donor_end=''.join(labels(value[:,:3],INDEX))
    p19.holds(rd,fresh,value[:,3:],base+20000,observations)
    return dict(available=True,donor_initial_labels=donor_initial,recipient_initial_labels=recipient_initial,
        donor_end_labels=donor_end,observations=observations,transmitted_E=all(p19.masks(observations)),logical_end=base+40000)

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result.get('clock_method')=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve',
        'only_registered_primary_edits','fixed_onward_schedules','counterfactual_reconstruction')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('autonomous_reproduction','cell_division_simulated',
        'parameter_retuning','independent_biological_replicates','outcome_dependent_selection','automatic_follow_on')))
    rd.ck('whole_cell_scope',result.get('full_cell_state_transfer')==(c['kind']=='historical' or c['stage']=='onward'))
    rd.ck('refresh_scope',result.get('algebraic_refresh_at_assembly')==(c['kind']=='component' and c['stage']!='onward'))
    rd.ck('reconstruction_scope',result.get('reconstructed_initial_state')==(c['stage']!='onward'))
    out=(audit_readout if c['stage']=='onward' else audit_renewal)(rd,folder.parent,c)
    ref=replay(c); rd.ck('replay_provenance',result.get('historical_numeric_replay')==ref)
    if ref is not None:
        for name,data in rd.data.items():
            historical=arrays(folder.parent/'inputs'/ref,name); rd.ck(name+'/replay_inventory',set(data)==set(historical))
            for key in historical: rd.eq(name+'/historical_replay/'+key,data[key],historical[key])
    return rd.finish(out)

def refresh_controls(by,onward=False):
    rows=[]; keys=('available','assembly_labels','observations','retained_E','first_cell_label_after_second',
        'first_cell_stable_E_after_second','later_windows_E','complete_carrier_replacement','logical_end',
        'first_cell_sampled_behavior','first_cell_M_observed')
    for f in (False,True):
        for h in ('written','ordinary'):
            for t,m in (('none',0),('newcomer',7),('neighbour',7)):
                old=by.get(spec('controls',h,'historical',t,m,fine=f)['id'],{})
                refreshed=by.get(spec('controls',h,'component',t,m,fine=f)['id'],{})
                present=old.get('available') is True and refreshed.get('available') is True
                match=present and all(old.get(k)==refreshed.get(k) for k in keys)
                contrast=present and old.get('retained_E') is (m==7) and refreshed.get('retained_E') is (m==7)
                readouts=True
                if onward:
                    for k in ('open','rna','cut'):
                        raw=by.get(spec('onward',h,'historical',t,m,k,f)['id'],{})
                        new=by.get(spec('onward',h,'component',t,m,k,f)['id'],{})
                        readouts &= raw.get('available') is True and new.get('available') is True and raw==new
                rows.append(dict(founder=h,target=t,fine=f,renewal_metrics_match=match,expected_contrast=contrast,
                    onward_checked=onward,onward_metrics_match=bool(readouts),qualified=bool(match and contrast and readouts)))
    return rows

def stage_audit(run,stage):
    summary=d.read(run/'summary.json'); checks=Checks(); cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; result=d.read(path)
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and result==row['result'])
        report,data=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']; endpoints[c['id']]=data; calls+=len(data)
    fine=p19.p18.p12.compare_fine(cases,by,endpoints,checks); history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==d.read(run/'predecessor_audit.json') and d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('call_count',calls=={'controls':168,'components':504,'onward':1152}[stage])
    checks.add('unique_records',len(records)==len(summary['cases']))
    checks.add('registered_records',set(records).issubset({c['id'] for c in expected_cases()}))
    controls=refresh_controls(by,stage=='onward'); checks.add('refresh_controls_qualified',all(x['qualified'] for x in controls))
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    return dict(stage=stage,quality_gate=bool(quality),checks=checks.rows,integrity=integrity,branches=branches,
        fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches),refresh_controls=controls,
        eligibility_requires_registered_refresh_controls=True,favorable_component_outcomes_required=False)

def predecessor_audit(run):
    fresh=p20.analyze(d.P20_RUN); saved=d.read(run/'inputs/p20/independent_audit.json')
    archive=all(d.integrity(run,d.read(run/'summary.json')).values())
    good=fresh==saved and fresh['quality_gate'] and fresh['independent_check_count']==21938 and archive
    return dict(quality_gate=bool(good),original_matches_saved=fresh==saved,archive_byte_identical=archive,
        prior_checks=fresh['independent_check_count'],prior_cases=fresh['completed_cases'],prior_calls=fresh['integration_calls'],
        original_reaudit_count=1,archive_separate_mathematical_reaudit=False,reference_is_independent_backup=False,original_audit_file_rewritten=False)

def contrasts(by,inherited,controls_qualified):
    def pair(h,t,m,stage='components',readout=''):
        return [by.get(spec(stage,h,'component',t,m,readout,f)['id'],{}) for f in (False,True)]
    def both(rows,key,value=True): return all(x.get('available') is True and x.get(key) is value for x in rows)
    capacity=inherited.get('inherited_readout_capacity_qualified') is True
    wipe=inherited.get('inherited_isolated_200_wipe_negative') is True
    grid=[]; interpretations=[]
    for h in ('written','ordinary'):
        for target in ('newcomer','neighbour'):
            baseline=both(pair(h,target,0),'retained_E',False); positive=both(pair(h,target,7),'retained_E')
            qualified=bool(controls_qualified and baseline and positive); local=[]
            for mask in range(8):
                renewal=pair(h,target,mask); opened=pair(h,target,mask,'onward','open')
                blocked=all(both(pair(h,target,mask,'onward',k),'transmitted_E',False) for k in ('rna','cut'))
                retention=both(renewal,'retained_E'); onward=both(opened,'transmitted_E')
                behavior=(renewal[0].get('first_cell_sampled_behavior') if all(x.get('available') is True for x in renewal) and
                    renewal[0].get('first_cell_sampled_behavior')==renewal[1].get('first_cell_sampled_behavior') else 'missing_or_disagree')
                row=dict(founder=h,target=target,mask=mask,prepared_blocks=[n for n,b in (('protein',1),('rna',2),('ions',4)) if mask&b],
                    source_trials=1,shared_zero_control=mask==0,retained_E_both=retention,retained_E_false_both=both(renewal,'retained_E',False),
                    first_cell_sampled_behavior_both=behavior,first_cell_stable_E_after_second_both=both(renewal,'first_cell_stable_E_after_second'),
                    later_windows_E_both=both(renewal,'later_windows_E'),onward_transmission_both=onward,
                    negative_readout_controls_both=blocked,control_qualified_rescue=qualified and mask!=0 and retention,
                    control_qualified_chain=qualified and retention and onward and blocked and capacity and wipe)
                local.append(row); grid.append(row)
            def minimal(key):
                success=[x['mask'] for x in local if x[key]]
                return [m for m in success if not any(other!=m and (other&m)==other for other in success)]
            interventions=[]
            for name,bit in (('protein',1),('rna',2),('ions',4)):
                interventions.append(dict(block=name,forward_mask=bit,erasure_mask=7^bit,
                    single_block_rescue=qualified and local[bit]['retained_E_both'],
                    loss_of_renewal_after_erasure=qualified and local[7^bit]['retained_E_false_both']))
            interpretations.append(dict(founder=h,target=target,controls_qualified=qualified,
                minimal_tested_rescue_masks=minimal('control_qualified_rescue'),
                minimal_tested_chain_masks=minimal('control_qualified_chain'),reciprocal_interventions=interventions,
                necessity_scope='this_full_prepared_cell_background_only'))
    return dict(inherited_readout_capacity_qualified=capacity,inherited_wipe_qualified=wipe,
        component_grid=grid,component_interpretations=interpretations)

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p21_preparation_components/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases()); stages=summary.get('attempted_stages',[])
    checks.add('all_stages',stages==list(STAGES)); history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit']); reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json')) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==288 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}; inherited=d.read(run/'inputs/p20/independent_audit.json')
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=integrity,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(x['agree'] for x in final['fine_comparisons']),
        **contrasts(by,inherited,all(x['qualified'] for x in final['refresh_controls'])),
        inherited_controls_newly_integrated=False,external_schedule=True,counterfactual_component_intervention=True,
        unique_molecular_carrier_established=False,autonomous_reproduction=False,independent_biological_replicates=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path); args=p.parse_args()
    run=args.run.absolute(); d.check_run_path(run); result=analyze(run); d.write_json(run/'independent_audit.json',result)
    print({k:result.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree','component_interpretations')},flush=True)
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
