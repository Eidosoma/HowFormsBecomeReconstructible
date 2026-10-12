"""Independent P20 column reconstruction, native phase audit and qualified contrasts."""
import argparse
from pathlib import Path
import numpy as np
import p20_design as d
import analyze_paper_preparation_support as p19

Checks, labels, arrays, INDEX = p19.Checks, p19.labels, p19.arrays, p19.INDEX
STAGES=('renewal','onward')

def spec(stage='renewal',founder='written',newcomer='before',neighbours='before',readout='',fine=False):
    name='__'.join([stage,founder,newcomer,neighbours]+([readout] if readout else []))
    return dict(id=name+('__fine' if fine else ''),stage=stage,founder=founder,
        newcomer=newcomer,neighbours=neighbours,readout=readout,fine=fine)
def expected_stage(stage):
    if stage not in STAGES: raise ValueError('Unknown P20 stage')
    return [spec(stage,h,n,b,k,f) for f in (False,True) for h in ('written','ordinary')
        for n in ('before','after') for b in ('before','after')
        for k in (('',) if stage=='renewal' else ('open','rna','cut'))]
def expected_cases(last='onward'): return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s)]
def parent(c): return spec('renewal',c['founder'],c['newcomer'],c['neighbours'],fine=c['fine'])
def stem(c): return 'p20:%s:%s:%s'%(c['founder'],c['newcomer'],c['neighbours'])
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c):
    return 'renewal__%s__prepared__100__300__200__isolated'%c['founder']+('__fine' if c['fine'] else '')
def replay(c):
    if c['newcomer']!=c['neighbours']: return None
    suffix='__fine' if c['fine'] else ''
    if c['newcomer']=='after':
        return 'p19/'+c['stage']+'__'+c['founder']+'__prepared__100__300__200__isolated'+(
            '__'+c['readout'] if c['stage']=='onward' else '')+suffix
    if c['stage']=='renewal': return 'p19/baseline__'+c['founder']+'__reference__100__300__0__none'+suffix
    return 'p19/inputs/p18/onward__'+c['founder']+'__100__300__open__renew__'+c['readout']+suffix
def stock(run,fine): return p19.stock(run/'inputs/p19',fine)

class Reader(p19.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=d.read(folder/'result.json'); self.records=self.result['phases']
        self.at=0; self.data={}
        self.environment=arrays(p19.stock_folder(folder.parent/'inputs/p19',c['fine']),'preparation')['environment']

def audit_assembly(rd,run,c):
    src=run/'inputs/p19'/source(c); record=d.read(src/'result.json'); data=arrays(src,'preparation_extra')
    rec=record['phases'][0]; before,after=data['initial'],data['final']
    original=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    ids=['p17:%s:100:open:replacement:0:0'%c['founder']]+original[1:]
    rd.ck('source_case',record['case']==p19.spec('renewal',c['founder'],200,'isolated',fine=c['fine']))
    rd.ck('source_interval',rec['phase']=='preparation_extra' and rec['logical_interval']==[1180100,1180300])
    rd.ck('source_identity',rec['setup']['cell_ids']==ids and record['outcome']['original_ids']==original)
    rd.ck('source_raw_hash',rec['sha256']==d.digest(src/'preparation_extra.npz'))
    rd.ck('source_shapes',before.shape==after.shape==(17,3))
    rd.ck('same_source_labels',''.join(labels(before,INDEX))==''.join(labels(after,INDEX))=='EEE')
    value=before.copy()
    if c['newcomer']=='after': value[:,0]=after[:,0]
    if c['neighbours']=='after': value[:,1:]=after[:,1:]
    folder=rd.folder/'assembly'; checkpoint=arrays(folder,'checkpoint'); meta=d.read(folder/'assembly.json')
    rd.ck('assembly_inventory',{p.name for p in folder.iterdir()}=={'checkpoint.npz','assembly.json'} and
        set(checkpoint)=={'before','after','assembled'})
    for name,expected in (('before',before),('after',after),('assembled',value)):
        rd.eq('assembly/'+name,checkpoint[name],expected)
    expected=dict(source='p19/'+source(c),source_phase='preparation_extra',
        source_result_sha256=d.digest(src/'result.json'),source_phase_sha256=d.digest(src/'preparation_extra.npz'),
        column_ages=[c['newcomer'],c['neighbours'],c['neighbours']],cell_ids=ids,original_ids=original,
        source_interval=[1180100,1180300],common_logical_start=1180300,before_reanchor_without_integration=200,
        full_17_species=True,checkpoint_sha256=d.digest(folder/'checkpoint.npz'))
    rd.ck('assembly_metadata',meta==expected)
    rd.ck('assembly_provenance',rd.result['provenance']==dict(assembly=expected,
        assembly_metadata_sha256=d.digest(folder/'assembly.json')))
    rd.ck('assembly_native_snail',np.all(value[INDEX['snail']]==72))
    return value,ids,original

def audit_renewal(rd,run,c):
    value,ids,originals=audit_assembly(rd,run,c); initial=ids.copy()
    initial_labels=''.join(labels(value,INDEX)); observations={}; replacements=[]; cursor=1180300
    _,M=stock(run,c['fine'])
    for at in range(1,6):
        cycle,pos=divmod(at,3); incoming=p19.incoming(M,cycle,pos); lab=str(labels(incoming,INDEX)[0])
        rd.ck('incoming_%d_M'%at,lab=='M'); value=value.copy(); old=ids[pos]; ids[pos]=new_id(c,cycle,pos)
        value[:,pos:pos+1]=incoming
        replacements.append(dict(event=at+1,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
        name='replacement_%02d'%(at+1)
        value=rd.take(p19.descriptor(name,ids,cursor,300,'chain'),value); cursor+=300
        observations[name]=p19.observation(rd.data[name],range(3))
    complete=not bool(set(ids)&set(originals+initial)); rd.ck('complete_carrier_replacement',complete)
    rd.ck('schedule',cursor==1181800 and [r['position'] for r in replacements]==[1,2,0,1,2])
    cursor=p19.holds(rd,ids,value,cursor,observations)
    return dict(available=True,fork_ids=initial,original_ids=originals,assembly_labels=initial_labels,
        observations=observations,replacements=replacements,retained_E=all(p19.masks(observations)),
        first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement')),
        complete_carrier_replacement=complete,logical_end=cursor)

def audit_readout(rd,run,c):
    _,M=stock(run,c['fine']); par=parent(c); path=run/par['id']; record=d.read(path/'result.json')
    donors=arrays(path,'isolated_2')['final']; ids=[new_id(c,1,i) for i in range(3)]; base=1201800
    rd.ck('actual_parent',record['case']==par and record['phases'][-1]['setup']['cell_ids']==ids and
        record['outcome']['logical_end']==base and record['phases'][-1]['logical_interval']==[base-10000,base])
    rd.ck('parent_provenance',rd.result['provenance']==dict(actual_parent=par['id'],
        parent_result_sha256=d.digest(path/'result.json'),parent_phase_sha256=d.digest(path/'isolated_2.npz')))
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1)
    donor_initial=''.join(labels(donors,INDEX)); recipient_initial=''.join(labels(recipients,INDEX))
    rd.ck('fresh_M',recipient_initial=='MMM'); rd.ck('donors_discarded',not bool(set(ids)&set(fresh)))
    value=rd.take(p19.descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),np.concatenate((donors,recipients),axis=1))
    observations={'contact':p19.observation(rd.data['contact'],range(3,6))}
    donor_end=''.join(labels(value[:,:3],INDEX)); p19.holds(rd,fresh,value[:,3:],base+20000,observations)
    return dict(available=True,donor_initial_labels=donor_initial,recipient_initial_labels=recipient_initial,
        donor_end_labels=donor_end,observations=observations,transmitted_E=all(p19.masks(observations)),logical_end=base+40000)

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result.get('clock_method')=='native_explicit_euler_bounded_clock_v1' and
        result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve',
        'full_cell_state_transfer','fixed_onward_schedules','counterfactual_reconstruction')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('autonomous_reproduction','cell_division_simulated',
        'parameter_retuning','independent_biological_replicates','outcome_dependent_selection','automatic_follow_on')))
    rd.ck('reconstruction_scope',result.get('reconstructed_initial_state')==(c['stage']=='renewal'))
    out=(audit_renewal if c['stage']=='renewal' else audit_readout)(rd,folder.parent,c)
    ref=replay(c); rd.ck('replay_provenance',result.get('historical_numeric_replay')==ref)
    if ref is not None:
        for name,data in rd.data.items():
            historical=arrays(folder.parent/'inputs'/ref,name)
            rd.ck(name+'/replay_inventory',set(data)==set(historical))
            for key in historical: rd.eq(name+'/historical_replay/'+key,data[key],historical[key])
    return rd.finish(out)

def stage_audit(run,stage):
    summary=d.read(run/'summary.json'); checks=Checks(); cases=expected_cases(stage)
    records={r['id']:r for r in summary['cases']}; branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; result=d.read(path)
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and result==row['result'])
        report,data=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']
        endpoints[c['id']]=data; calls+=len(data)
    fine=p19.p18.p12.compare_fine(cases,by,endpoints,checks); history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==d.read(run/'predecessor_audit.json') and
        d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('call_count',calls=={'renewal':112,'onward':256}[stage])
    checks.add('unique_records',len(records)==len(summary['cases']))
    checks.add('registered_records',set(records).issubset({c['id'] for c in expected_cases()}))
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    return dict(stage=stage,quality_gate=bool(quality),checks=checks.rows,integrity=integrity,branches=branches,
        fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches),eligibility_means_technical_permission_only=True)

def reconstructed_p19():
    """Read-only equivalent of the recovery audit; never overwrite P19 evidence."""
    result=p19.analyze(d.P19_RUN); flags=d.recovery.recovery_integrity(d.P19_RUN)
    summary=d.read(d.P19_RUN/'summary.json'); rec=summary['recovery']
    rows=[r for r in summary['cases'] if r['id'] in rec['new_cases']]
    calls=sum(len(r['result']['phases']) for r in rows if r['execution_pass'])
    flags['new_execution_count']=len(rows)==114 and calls==372
    flags['complete_partition']={r['id'] for r in summary['cases']}==set(rec['new_cases'])|set(rec['reused_cases'])
    good=result['quality_gate'] and all(flags.values())
    result.update(quality_gate=bool(good),ready_for_interpretation=bool(good),recovery_checks=flags,
        independent_check_count=result['independent_check_count']+len(flags),reused_cases=78,
        newly_executed_cases=len(rows),reused_integrations=498,newly_executed_integrations=calls,
        earlier_partial_phases_excluded=3,total_saved_phases_across_attempts=498+3+calls,
        inherited_native_verification=rec['inherited_verification'],external_output_recovery=True)
    return result

def predecessor_audit(run):
    fresh=reconstructed_p19(); saved=d.read(run/'inputs/p19/independent_audit.json')
    integrity=d.integrity(run,d.read(run/'summary.json')); archive=all(integrity.values())
    quality=fresh==saved and fresh['quality_gate'] and fresh['independent_check_count']==65479 and archive
    return dict(quality_gate=bool(quality),original_matches_saved=fresh==saved,archive_byte_identical=archive,
        prior_checks=fresh['independent_check_count'],prior_cases=fresh['completed_cases'],prior_calls=fresh['integration_calls'],
        original_reaudit_count=1,archive_separate_mathematical_reaudit=False,reference_is_independent_backup=False,
        original_audit_file_rewritten=False)

def contrasts(by,inherited):
    def pair(stage,h,n,b,k=''): return [by.get(spec(stage,h,n,b,k,f)['id'],{}) for f in (False,True)]
    def both(rows,key,value=True): return all(r.get('available') is True and r.get(key) is value for r in rows)
    capacity=inherited.get('readout_capacity',{}).get('qualified') is True
    wipe=any(x.get('extra')==200 and x.get('mode')=='isolated' and x.get('negative_both') is True
        for x in inherited.get('wipe_controls',[]))
    grid=[]; findings=[]
    for h in ('written','ordinary'):
        sham=both(pair('renewal',h,'before','before'),'retained_E',False) and both(pair('renewal',h,'after','after'),'retained_E')
        for n in ('before','after'):
            for b in ('before','after'):
                renewal=pair('renewal',h,n,b); opened=pair('onward',h,n,b,'open')
                controls=all(both(pair('onward',h,n,b,k),'transmitted_E',False) for k in ('rna','cut'))
                retained=both(renewal,'retained_E'); transmitted=both(opened,'transmitted_E')
                available=all(x.get('available') is True for x in renewal+opened+
                    pair('onward',h,n,b,'rna')+pair('onward',h,n,b,'cut'))
                grid.append(dict(founder=h,newcomer=n,neighbours=b,available=available,source_trials=1,
                    retained_E_both=retained,first_cell_stable_E_after_second_both=both(renewal,'first_cell_stable_E_after_second'),
                    later_windows_E_both=both(renewal,'later_windows_E'),onward_transmission_both=transmitted,
                    negative_readout_controls_both=controls,sham_contrast_qualified=sham,
                    control_qualified_transmission=transmitted and controls and capacity,
                    control_qualified_chain=retained and transmitted and controls and capacity and wipe and sham))
        ab=both(pair('renewal',h,'after','before'),'retained_E'); ba=both(pair('renewal',h,'before','after'),'retained_E')
        ab_no=both(pair('renewal',h,'after','before'),'retained_E',False)
        ba_no=both(pair('renewal',h,'before','after'),'retained_E',False)
        category='unqualified'
        if sham:
            if ab and ba_no: category='newcomer_preparation_alone_sufficient'
            elif ba and ab_no: category='surviving_neighbour_preparation_alone_sufficient'
            elif ab and ba: category='alternative_sufficient_routes'
            elif ab_no and ba_no: category='joint_prepared_states_required_in_tested_contrast'
        findings.append(dict(founder=h,sham_contrast_qualified=sham,renewal_localization=category,
            newcomer_only_retained_E_both=ab,neighbour_only_retained_E_both=ba))
    return dict(inherited_readout_capacity_qualified=capacity,inherited_isolated_200_wipe_negative=wipe,
        cell_state_grid=grid,localization=findings)

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p20_preparation_localization/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases())
    stages=summary.get('attempted_stages',[]); checks.add('all_stages',stages==list(STAGES))
    history=predecessor_audit(run); checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json')) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==64 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}; inherited=d.read(run/'inputs/p19/independent_audit.json')
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=integrity,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(x['agree'] for x in final['fine_comparisons']),**contrasts(by,inherited),
        inherited_controls_newly_integrated=False,counterfactual_whole_cell_reconstruction=True,
        absolute_clock_reanchor_is_state_preparation=False,molecular_mechanism_established=False,
        autonomous_reproduction=False,independent_biological_replicates=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path); args=p.parse_args()
    run=args.run.absolute(); d.check_run_path(run); result=analyze(run)
    d.write_json(run/'independent_audit.json',result)
    print({k:result.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree','localization')},flush=True)
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
