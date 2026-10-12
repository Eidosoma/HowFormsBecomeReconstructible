"""Independent P23 donor continuity, recipient retention and specificity audit."""
import argparse
from pathlib import Path
import numpy as np
import p23_design as d
import analyze_p22 as p22

p19=p22.p19
Checks,labels,arrays,INDEX=p19.Checks,p19.labels,p19.arrays,p19.INDEX
STAGES=('controls','onward')

def spec(founder='written',condition='early_pause',readout='open',fine=False):
    stage='controls' if condition=='reference' else 'onward'
    return dict(id=stage+'__'+founder+'__'+condition+'__'+readout+('__fine' if fine else ''),
        stage=stage,founder=founder,condition=condition,readout=readout,fine=fine)
def expected_stage(stage):
    if stage not in STAGES: raise ValueError('Unknown P23 stage')
    names=['reference'] if stage=='controls' else ['baseline','full_block','early_pause']
    return [spec(h,k,q,f) for f in (False,True) for h in ('written','ordinary') for k in names for q in ('open','rna','cut')]
def expected_cases(last='onward'): return [c for stage in STAGES[:STAGES.index(last)+1] for c in expected_stage(stage)]
def parent(c):
    k=c['condition']; panel='replay' if k=='reference' else 'timing_controls' if k=='baseline' else 'timing'
    route='newcomer_protein' if k=='reference' else 'none'
    window='rna_early' if k=='early_pause' else 'rna_full' if k=='full_block' else 'open'
    name='__'.join((panel,c['founder'],route,window,'legacy','5'))+('__fine' if c['fine'] else '')
    return dict(id=name,stage=panel,panel=panel,founder=c['founder'],route=route,window=window,
        draw='legacy',replacements=5,readout='',fine=c['fine'])
def source(c): return parent(c)['id']
def donor_ids(c):
    p=parent(c); stem='p22:%s:%s:%s:%s:legacy:5'%(p['panel'],p['founder'],p['route'],p['window'])
    return [stem+':replacement:1:'+str(i) for i in range(3)]
def pupils(c): return ['p23:'+c['founder']+':'+c['condition']+':pupil:0'+str(i) for i in range(3)]
def replay(c):
    if c['condition']!='reference': return None
    name='onward__replay__'+c['founder']+'__newcomer_protein__open__legacy__5__'+c['readout']+('__fine' if c['fine'] else '')
    return dict(source='p22/'+name,phases=['contact','isolated_1','isolated_2'])
def stock(run,fine): return p22.stock(run/'inputs/p22',fine)

class Reader(p19.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks; self.result=d.read(folder/'result.json')
        self.records=self.result['phases']; self.at=0; self.data={}
        self.environment=arrays(p19.stock_folder(folder.parent/'inputs/p22/inputs/p21/inputs/p20/inputs/p19',c['fine']),'preparation')['environment']

def audit_parent(rd,run,c):
    path=run/'inputs/p22'/source(c); old=d.read(path/'result.json'); ids=donor_ids(c)
    originals=['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
    fork=['p17:%s:100:open:replacement:0:0'%c['founder']]+originals[1:]
    expected_names=(['replacement_%02d'%i for i in range(2,7)] if c['condition']=='reference' else
        ['challenge_%02d'%i for i in (1,2,3)]+['replacement_%02d'%i for i in range(3,7)])+['isolated_1','isolated_2']
    rd.ck('parent_case',old['case']==parent(c) and old['execution_pass'] is True)
    rd.ck('parent_phase_inventory',[p['phase'] for p in old['phases']]==expected_names)
    rd.ck('parent_lineage',old['outcome']['original_ids']==originals and old['outcome']['fork_ids']==fork and
        old['outcome']['complete_carrier_replacement'] is True and not set(ids)&set(originals+fork))
    obs={}; value=None
    for i,rec in enumerate(old['phases'][-2:],1):
        name='isolated_'+str(i); data=arrays(path,name)
        rd.ck('parent_'+name+'_identity_clock',rec['phase']==name and rec['setup']['cell_ids']==ids and
            rec['logical_interval']==[1181800+(i-1)*10000,1181800+i*10000] and rec['requested_horizon']==10000)
        rd.ck('parent_'+name+'_hash',d.digest(path/(name+'.npz'))==rec['sha256'])
        rd.ck('parent_'+name+'_shape',data['initial'].shape==data['final'].shape==(17,3))
        if value is not None: rd.eq('parent_holds_continuous',data['initial'],value)
        value=data['final']; obs[name]=p19.observation(data,range(3))
        rd.ck('parent_'+name+'_observation',obs[name]==old['outcome']['observations'][name])
    retained=all(p19.masks(obs)); rd.ck('parent_retention',old['outcome']['retained_E'] is retained and retained==(c['condition'] in ('reference','early_pause')))
    rd.ck('parent_logical_end',old['outcome']['logical_end']==1201800)
    rd.ck('parent_provenance',rd.result['provenance']==dict(actual_parent='p22/'+source(c),
        parent_result_sha256=d.digest(path/'result.json'),parent_phase_sha256=d.digest(path/'isolated_2.npz')))
    rd.ck('no_new_assembly',not (rd.folder/'assembly').exists())
    return value,ids,originals+fork,retained

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result.get('clock_method')=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','archived_parent_readout','fixed_onward_schedules','selected_using_prior_results')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('parent_states_edited','algebraic_refresh','donors_clamped','repeated_pause',
        'new_renewal_trajectories','autonomous_reproduction','cell_division_simulated','parameter_retuning',
        'independent_biological_replicates','outcome_dependent_selection','automatic_follow_on')))
    donors,ids,old_ids,retained=audit_parent(rd,folder.parent,c); _,M=stock(folder.parent,c['fine'])
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1); initial=np.concatenate((donors,recipients),axis=1)
    donor_initial=''.join(labels(donors,INDEX)); recipient_initial=''.join(labels(recipients,INDEX))
    rd.ck('fresh_M',recipient_initial=='MMM'); rd.ck('fresh_identities',len(set(ids+fresh))==6 and not set(fresh)&set(old_ids))
    value=rd.take(p19.descriptor('contact',ids+fresh,1201800,20000,'readout',c['readout']),initial)
    obs={'contact':p19.observation(rd.data['contact'],range(3,6))}; donor_end=''.join(labels(value[:,:3],INDEX))
    cursor=p19.holds(rd,fresh,value[:,3:],1221800,obs)
    out=dict(available=True,parent_retained_E=retained,donor_initial_labels=donor_initial,recipient_initial_labels=recipient_initial,
        donor_end_labels=donor_end,observations=obs,contact_stable_E=all(obs['contact']['stable_E']),
        transmitted_E=all(p19.masks(obs)),logical_end=cursor)
    ref=replay(c); rd.ck('replay_provenance',result.get('historical_numeric_replay')==ref)
    if ref:
        for name in ref['phases']:
            data=rd.data[name]; historical=arrays(folder.parent/'inputs'/ref['source'],name)
            rd.ck(name+'/replay_inventory',set(data)==set(historical))
            for key in historical: rd.eq(name+'/historical_replay/'+key,data[key],historical[key])
    return rd.finish(out)

def reference_controls(by):
    result=[]
    for f in (False,True):
        for h in ('written','ordinary'):
            for q in ('open','rna','cut'):
                out=by.get(spec(h,'reference',q,f)['id'],{})
                good=out.get('available') is True and out.get('parent_retained_E') is True and out.get('transmitted_E') is (q=='open')
                result.append(dict(founder=h,readout=q,fine=f,qualified=bool(good)))
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
    count=12 if stage=='controls' else 48
    checks.add('count',len(branches)==count and calls==count*3); checks.add('unique_records',len(records)==len(summary['cases']))
    checks.add('registered_records',set(records).issubset({c['id'] for c in expected_cases()}))
    controls=reference_controls(by); checks.add('reference_controls_qualified',all(x['qualified'] for x in controls))
    integrity=d.integrity(run,summary)
    return dict(stage=stage,quality_gate=bool(all(checks.rows.values()) and all(integrity.values())),checks=checks.rows,
        integrity=integrity,branches=branches,fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches),
        reference_controls=controls,favorable_novel_outcomes_required=False)

def predecessor_audit(run):
    fresh=p22.analyze(d.P22_RUN); saved=d.read(run/'inputs/p22/independent_audit.json')
    archive=all(d.integrity(run,d.read(run/'summary.json')).values())
    good=fresh==saved and fresh['quality_gate'] and fresh['independent_check_count']==219181 and archive
    return dict(quality_gate=bool(good),original_matches_saved=fresh==saved,archive_byte_identical=archive,
        prior_checks=fresh['independent_check_count'],prior_cases=fresh['completed_cases'],prior_calls=fresh['integration_calls'],
        original_reaudit_count=1,archive_separate_mathematical_reaudit=False,reference_is_independent_backup=False,original_audit_file_rewritten=False)

def contrasts(by,inherited,reference_qualified):
    capacity=inherited.get('inherited_readout_capacity_qualified') is True; wipe=inherited.get('inherited_wipe_qualified') is True
    def both(h,k,q,key,value=True):
        rows=[by.get(spec(h,k,q,f)['id'],{}) for f in (False,True)]
        return all(x.get('available') is True and x.get(key) is value for x in rows)
    rows=[]; conclusions=[]
    for h in ('written','ordinary'):
        profiles={}
        for k in ('reference','baseline','full_block','early_pause'):
            outcomes={q:True if both(h,k,q,'transmitted_E') else False if both(h,k,q,'transmitted_E',False) else None for q in ('open','rna','cut')}
            retained=all(both(h,k,q,'parent_retained_E') for q in ('open','rna','cut'))
            route_specific=outcomes['open'] is True and outcomes['rna'] is False and outcomes['cut'] is False
            row=dict(founder=h,condition=k,parent_retained_E_both=retained,readout_transmission_both=outcomes,
                contact_stable_E_both={q:both(h,k,q,'contact_stable_E') for q in ('open','rna','cut')},
                qualified_chain=bool(retained and route_specific and reference_qualified and capacity and wipe))
            rows.append(row); profiles[k]=row
        early=profiles['early_pause']; negatives=all(profiles[k]['readout_transmission_both'][q] is False for k in ('baseline','full_block') for q in ('open','rna','cut'))
        specific=early['qualified_chain'] and negatives
        outcome='early_pause_specific_qualified_chain' if specific else 'qualified_chain_without_matched_negative_specificity' if early['qualified_chain'] else 'no_onward_transmission' if early['readout_transmission_both']['open'] is False else 'onward_chain_not_qualified'
        conclusions.append(dict(founder=h,qualified_chain=early['qualified_chain'],matched_negative_parents_qualified=negatives,
            early_pause_specific_chain=bool(specific),interpretation=outcome))
    return dict(inherited_readout_capacity_qualified=capacity,inherited_wipe_qualified=wipe,readout_grid=rows,
        early_pause_comparisons=conclusions,early_pause_specific_both_histories=all(x['early_pause_specific_chain'] for x in conclusions))

def analyze(run):
    summary=d.read(run/'summary.json'); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==d.read(run/'frozen/p23_pause_transmission/config.json'))
    checks.add('registration',summary['registered_cases']==expected_cases()); stages=summary.get('attempted_stages',[])
    checks.add('all_stages',stages==list(STAGES)); history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit']); reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==d.read(run/(stage+'_audit.json')) and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==48 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    integrity=d.integrity(run,summary); quality=all(checks.rows.values()) and all(integrity.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}; inherited=d.read(run/'inputs/p22/independent_audit.json')
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=integrity,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(x['agree'] for x in final['fine_comparisons']),
        **contrasts(by,inherited,all(x['qualified'] for x in final['reference_controls'])),
        inherited_controls_newly_integrated=False,archived_parent_readout=True,parent_states_edited=False,repeated_pause=False,
        new_renewal_trajectories=False,selected_using_prior_results=True,outcome_dependent_selection=False,
        autonomous_reproduction=False,independent_biological_replicates=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path); args=p.parse_args()
    run=args.run.absolute(); d.check_run_path(run); report=analyze(run); d.write_json(run/'independent_audit.json',report)
    print({k:report.get(k) for k in ('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree','early_pause_comparisons')},flush=True)
    return 0 if report['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
