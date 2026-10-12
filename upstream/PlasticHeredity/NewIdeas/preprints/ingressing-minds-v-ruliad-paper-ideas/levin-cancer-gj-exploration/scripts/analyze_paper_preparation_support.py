"""P19 independent preparation, coupling-restoration and lineage reconstruction."""
import argparse
import json
import os
from pathlib import Path
import numpy as np
import paper_preparation_support_design as d
import analyze_paper_preparation_turnover as p18
from analyze_paper_memory import Checks,labels
from analyze_paper_sheet import arrays

INDEX=p18.INDEX
STAGES=('baseline','renewal','onward')
FOUNDERS=('written','ordinary','stock_E')
EXTRAS=(200,900)
MODES=('open','rna','isolated')
READOUTS=('open','rna','cut')
ANCHORS=(100,300,1000)

def spec(stage='renewal',founder='written',extra=200,mode='open',arm='',first=100,readout='',fine=False):
    later=300
    if stage=='baseline':
        if arm=='capacity': founder,extra,mode,first,later='stock_E',0,'none',0,0
        elif arm=='no_turn': extra,mode,first,later=0,'none',20000,20000
        elif arm in ('reference','wipe_reference'):
            extra,mode=0,'none'
            if arm=='wipe_reference': founder='stock_E'
        elif arm=='wipe': founder,first='stock_E',100
    else: arm,first='prepared',100
    name='__'.join([stage,founder,arm,str(first),str(later),str(extra),mode]+([readout] if readout else []))
    return dict(id=name+('__fine' if fine else ''),stage=stage,founder=founder,extra=extra,mode=mode,
                arm=arm,first=first,later=later,route='open',readout=readout,fine=fine)

def expected_stage(stage):
    if stage=='baseline':
        return ([spec(stage,arm='capacity',readout=k,fine=f) for f in (False,True) for k in READOUTS]+
            [spec(stage,h,arm='no_turn',fine=f) for f in (False,True) for h in FOUNDERS]+
            [spec(stage,h,arm='reference',first=t,fine=f) for f in (False,True) for h in FOUNDERS for t in ANCHORS]+
            [spec(stage,arm='wipe_reference',first=t,fine=f) for f in (False,True) for t in ANCHORS]+
            [spec(stage,extra=t,mode=m,arm='wipe',fine=f) for f in (False,True) for t in EXTRAS for m in MODES])
    if stage=='renewal':
        return [spec(stage,h,t,m,fine=f) for f in (False,True) for h in FOUNDERS for t in EXTRAS for m in MODES]
    if stage=='onward':
        return [spec(stage,h,t,m,readout=k,fine=f) for f in (False,True) for h in FOUNDERS for t in EXTRAS for m in MODES for k in READOUTS]
    raise ValueError('Unregistered stage')

def expected_cases(last='onward'): return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s)]
def parent(c): return spec('renewal',c['founder'],c['extra'],c['mode'],fine=c['fine'])
def prefix_source(c): return 'prefix__%s__100__open'%c['founder']+('__fine' if c['fine'] else '')
def stem(c): return 'p19:%s:%s:%s:%s'%(c['founder'],c['arm'],c['extra'],c['mode'])
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
expected_draws=p18.expected_draws
incoming=p18.incoming
descriptor=p18.descriptor
observation=p18.observation
masks=p18.masks
holds=p18.holds
def stock_folder(run,fine): return p18.stock_folder(run/'inputs/p18',fine)
def stock(run,fine):
    x=arrays(stock_folder(run,fine),'preparation')['final']; return x[:,168:169],x[:,1:2]

def integrity(run,summary):
    try:
        h,f,i=summary['hashes_sha256'],summary['frozen_hashes_sha256'],summary['inputs']; required=d.input_paths()
        return dict(revision=summary['revision']==d.REVISION,
            complete_manifest=set(h)==set(d.execution_manifest()) and set(f)=={p.name for p in d.LOCAL_FILES} and set(i)==set(required),
            input_origins=all(Path(i[p]['source'])==path for p,path in required.items()),
            execution=all(d.digest(d.ROOT/p)==v for p,v in h.items()),
            frozen=all(d.digest(run/'frozen'/p)==v for p,v in f.items()),
            sources=all(d.digest(Path(v['source']))==v['sha256'] for v in i.values()),
            inputs=all(d.digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            linked_inputs=all(v.get('storage')=='hardlink_immutable_v1' and os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()))
    except (OSError,KeyError,RuntimeError): return dict(integrity_readable=False)

class Reader(p18.p16.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}; self.environment=arrays(stock_folder(folder.parent,c['fine']),'preparation')['environment']
    def take(self,layout,initial):
        final=super().take(layout,initial)
        # Native EMT_GJ_gate applies RNA flux through its recorded mirna_kd;
        # both RNA rows are reset to zero outside that gate's evaluation.
        self.ck(layout['name']+'/no_direct_nonionic_diffusion',
                not self.data[layout['name']]['junction_diffusion'][4:].any())
        return final

def replay_case(c):
    if c['stage']!='baseline' or c['arm']=='wipe': return None
    if c['arm']=='reference': return p18.spec('renewal',c['founder'],c['first'],300,'open',fine=c['fine'])
    return p18.spec('baseline',c['founder'],c['first'],c['later'],'open',
        arm='wipe' if c['arm']=='wipe_reference' else c['arm'],readout=c['readout'],fine=c['fine'])
def replay_source(c):
    x=replay_case(c); return x['id'] if x else None

def replace(rd,c,M,value,ids,cycle,positions,event):
    value=value.copy(); rows=[]
    for pos in positions:
        x=incoming(M,cycle,pos); lab=str(labels(x,INDEX)[0]); rd.ck('incoming_%d_%d_M'%(cycle,pos),lab=='M')
        old=ids[pos]; ids[pos]=new_id(c,cycle,pos); value[:,pos:pos+1]=x
        rows.append(dict(event=event,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
    return value,rows

def prepare(rd,c,ids,value,cursor,observations):
    layout=descriptor('preparation_extra',ids,cursor,c['extra'],'isolated' if c['mode']=='isolated' else 'chain',
                      'rna' if c['mode']=='rna' else 'open')
    value=rd.take(layout,value); observations['preparation_extra']=observation(rd.data['preparation_extra'],range(3))
    return value,cursor+c['extra']

def audit_baseline(rd,run,c):
    mapped=replay_case(c)
    if mapped is not None:
        fn=p18.audit_renewal if c['arm']=='reference' else p18.audit_baseline
        return fn(rd,run/'inputs/p18',mapped)
    E,M=stock(run,c['fine']); value=np.repeat(E,3,axis=1); ids=stock_ids(c); originals=ids.copy()
    observations={}; replacements=[]; cursor=0
    value,new=replace(rd,c,M,value,ids,0,range(3),1); replacements.extend(new)
    value=rd.take(descriptor('wipe_initial',ids,0,100,'chain'),value); cursor=100
    observations['wipe_initial']=observation(rd.data['wipe_initial'],range(3))
    value,cursor=prepare(rd,c,ids,value,cursor,observations)
    value=rd.take(descriptor('wipe_first_remainder',ids,cursor,600,'chain'),value); cursor+=600
    observations['wipe_first_remainder']=observation(rd.data['wipe_first_remainder'],range(3))
    value,new=replace(rd,c,M,value,ids,1,range(3),2); replacements.extend(new)
    value=rd.take(descriptor('wipe_second_cycle',ids,cursor,900,'chain'),value); cursor+=900
    observations['wipe_second_cycle']=observation(rd.data['wipe_second_cycle'],range(3))
    rd.ck('wipe_exposure_and_burden',cursor==1600+c['extra'] and len(replacements)==6)
    rd.ck('wipe_originals_removed',not set(ids)&set(originals))
    cursor=holds(rd,ids,value,cursor,observations)
    return dict(available=True,original_ids=originals,observations=observations,replacements=replacements,
                retained_E=all(masks(observations)),logical_end=cursor)

def audit_renewal(rd,run,c):
    mapped=p18.spec('renewal',c['founder'],100,300,'open',fine=c['fine'])
    prefix,ids,cursor,record=p18.prefix_state(rd,run/'inputs/p18',mapped)
    value=prefix['final']; initial_ids=ids.copy(); fork_labels=''.join(labels(value,INDEX))
    observations={}; replacements=[]; _,M=stock(run,c['fine'])
    value,cursor=prepare(rd,c,ids,value,cursor,observations); prepared=''.join(labels(value,INDEX))
    for at in range(1,6):
        cycle,pos=divmod(at,3); value,new=replace(rd,c,M,value,ids,cycle,[pos],at+1); replacements.extend(new)
        name='replacement_%02d'%(at+1); value=rd.take(descriptor(name,ids,cursor,300,'chain'),value); cursor+=300
        observations[name]=observation(rd.data[name],range(3))
    original=p18.original_ids(mapped)
    rd.ck('original_ids',record['outcome']['original_ids']==original)
    rd.ck('all_founders_and_first_newcomer_removed',not set(ids)&set(original+initial_ids))
    rd.ck('fixed_order_and_duration',len(replacements)==5 and cursor==(0 if c['founder']=='stock_E' else 1180000)+1600+c['extra'])
    cursor=holds(rd,ids,value,cursor,observations)
    later_good=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement'))
    return dict(available=True,fork_ids=initial_ids,fork_labels=fork_labels,
        preparation_end_labels=prepared,preparation_window_E=all(observations['preparation_extra']['stable_E']),
        first_cell_stable_E_after_preparation=observations['preparation_extra']['stable_E'][0],
        observations=observations,retained_E=all(masks(observations)),logical_end=cursor,
        original_ids=record['outcome']['original_ids'],replacements=replacements,
        first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=later_good,complete_carrier_replacement=True)

def audit_readout(rd,run,c):
    _,M=stock(run,c['fine']); par=parent(c); path=run/par['id']; donors=arrays(path,'isolated_2')['final']
    ids=[new_id(c,1,i) for i in range(3)]; base=(0 if c['founder']=='stock_E' else 1180000)+21600+c['extra']
    record=json.loads((path/'result.json').read_text()); rec=record['phases'][-1]
    rd.ck('actual_renewal_parent',record['case']==par and rec['setup']['cell_ids']==ids and
          rec['logical_interval']==[base-10000,base] and record['outcome']['logical_end']==base)
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1)
    initial_donors=''.join(labels(donors,INDEX)); initial_recipients=''.join(labels(recipients,INDEX)); rd.ck('fresh_recipients_M',initial_recipients=='MMM')
    value=rd.take(descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),np.concatenate((donors,recipients),axis=1))
    observations={'contact':observation(rd.data['contact'],range(3,6))}; donor_end=''.join(labels(value[:,:3],INDEX))
    rd.ck('all_donors_removed',not set(ids)&set(fresh)); holds(rd,fresh,value[:,3:],base+20000,observations)
    return dict(available=True,donor_initial_labels=initial_donors,recipient_initial_labels=initial_recipients,
        donor_end_labels=donor_end,observations=observations,transmitted_E=all(masks(observations)),logical_end=base+40000)

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','full_source_transfer','only_registered_columns_replaced','fixed_onward_schedules','later_coupling_restored')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('benchmark_prior_age_matched','autonomous_reproduction','parameter_retuning',
        'outcome_dependent_cell_selection','cross_branch_pooling','cell_division_simulated','independent_biological_replicates','automatic_follow_on','split_unsplit_exact_array_equality_required')))
    rd.ck('fork_scope',result.get('exact_archived_prefix_fork')==(c['stage']=='renewal'))
    rd.ck('preparation_scope',result.get('preparation_only_coupling_intervention')==(c['stage']=='renewal' or c['arm']=='wipe'))
    rd.ck('prefix_provenance',result.get('archived_prefix_source')==(prefix_source(c) if c['stage']=='renewal' else None))
    out={'baseline':audit_baseline,'renewal':audit_renewal,'onward':audit_readout}[c['stage']](rd,folder.parent,c)
    src=replay_source(c); rd.ck('replay_scope',result.get('exact_P18_replay')==(src is not None))
    if src is not None:
        for name,data in rd.data.items():
            archived=arrays(folder.parent/'inputs/p18'/src,name); rd.ck(name+'/replay_inventory',set(archived)==set(data))
            for key in archived: rd.eq(name+'/historical_replay/'+key,data[key],archived[key])
    return rd.finish(out)

def stage_audit(run,stage):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}; branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; result=json.loads(path.read_text())
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and result==row['result'])
        report,data=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']; endpoints[c['id']]=data; calls+=len(data)
    fine=p18.p12.compare_fine(cases,by,endpoints,checks); history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==json.loads((run/'predecessor_audit.json').read_text()) and d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('draw_book',json.loads((run/'frozen/paper_preparation_support_draws_v1.json').read_text())==expected_draws())
    checks.add('call_count',calls=={'baseline':258,'renewal':546,'onward':870}[stage])
    checks.add('unique_case_records',len(records)==len(summary['cases']))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality),checks=checks.rows,integrity=provenance,
        branches=branches,fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches),eligibility_means_technical_permission_only=True)

def predecessor_audit(run):
    run=Path(run); original=p18.analyze(d.PREDECESSOR); saved=json.loads((run/'inputs/p18/independent_audit.json').read_text())
    summary=json.loads((run/'summary.json').read_text()); verified=integrity(run,summary)
    archive=all(verified.values())
    good=original==saved and original['quality_gate'] and original['independent_check_count']==104607 and archive
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_byte_identical=archive,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],prior_calls=original['integration_calls'],
        original_reaudit_count=1,archive_separate_mathematical_reaudit=False,hardlinked_inputs_not_independent_backup=True,
        actual_P17_prefix_sources=True)

def contrasts(by):
    def pair(stage,h='written',t=200,m='open',arm='',first=100,k=''):
        return [by.get(spec(stage,h,t,m,arm,first,k,f)['id'],{}) for f in (False,True)]
    def both(rows,key,value=True): return all(x.get('available') is True and x.get(key) is value for x in rows)
    def present(rows): return all(x.get('available') is True for x in rows)
    opened=both(pair('baseline',arm='capacity',k='open'),'transmitted_E')
    blocked=all(both(pair('baseline',arm='capacity',k=k),'transmitted_E',False) for k in ('rna','cut'))
    capacity=dict(open_transmission_both=opened,negative_controls_both=blocked,qualified=opened and blocked)
    no_turn=[dict(founder=h,source_trials=1,retained_E_both=both(pair('baseline',h,arm='no_turn'),'retained_E')) for h in FOUNDERS]
    references=[dict(founder=h,first=u,retained_E_both=both(pair('baseline',h,arm='reference',first=u),'retained_E')) for h in FOUNDERS for u in ANCHORS]
    wipes=[dict(extra=t,mode=m,negative_both=both(pair('baseline',t=t,m=m,arm='wipe'),'retained_E',False)) for t in EXTRAS for m in MODES]
    reference_wipes=[dict(first=u,negative_both=both(pair('baseline',arm='wipe_reference',first=u),'retained_E',False)) for u in ANCHORS]
    grid=[]; consistency=[]; mode_contrasts=[]; chains=[]
    for h in FOUNDERS:
        no_extra=pair('baseline',h,arm='reference',first=100); no_extra_failed=both(no_extra,'retained_E',False)
        for t in EXTRAS:
            normal=pair('renewal',h,t,'open'); unsplit=pair('baseline',h,arm='reference',first=100+t)
            keys=('retained_E','first_cell_stable_E_after_second','later_windows_E')
            agree=present(normal+unsplit) and all(all(x.get(k)==y.get(k) for k in keys) for x,y in zip(normal,unsplit))
            benchmark=agree and both(normal,'retained_E') and both(unsplit,'retained_E')
            consistency.append(dict(founder=h,extra=t,reference_first=100+t,source_trials=1,
                available=present(normal+unsplit),compared_metrics=list(keys),registered_metrics_agree_both=agree,
                split_retained_E_both=both(normal,'retained_E'),unsplit_retained_E_both=both(unsplit,'retained_E'),
                benchmark_recovery_qualified=benchmark,exact_array_equality_required=False))
            for m in MODES:
                rows=pair('renewal',h,t,m); wipe=both(pair('baseline',t=t,m=m,arm='wipe'),'retained_E',False)
                retained=both(rows,'retained_E'); raw=no_extra_failed and retained
                grid.append(dict(founder=h,extra=t,mode=m,source_trials=1,available=present(rows),
                    retained_E_both=retained,preparation_window_E_both=both(rows,'preparation_window_E'),
                    first_cell_stable_E_after_preparation_both=both(rows,'first_cell_stable_E_after_preparation'),
                    first_cell_stable_E_after_second_both=both(rows,'first_cell_stable_E_after_second'),
                    later_windows_E_both=both(rows,'later_windows_E'),no_extra_failed_both=no_extra_failed,
                    negative_wipe_both=wipe,raw_rescue=raw,control_qualified_rescue=raw and wipe,
                    P18_benchmark_supported_rescue=raw and wipe and benchmark,
                    isolated_extra_time_sufficient=m=='isolated' and raw and wipe))
                onward=both(pair('onward',h,t,m,k='open'),'transmitted_E')
                controls=all(both(pair('onward',h,t,m,k=k),'transmitted_E',False) for k in ('rna','cut'))
                chains.append(dict(founder=h,extra=t,mode=m,source_trials=1,retained_E_both=retained,
                    onward_transmission_both=onward,raw_retention_and_onward=retained and onward,
                    negative_wipe_both=wipe,control_qualified_transmission=onward and controls,
                    control_qualified_chain=retained and onward and controls and wipe,
                    benchmark_supported_chain=retained and onward and controls and wipe and capacity['qualified']))
            for changed in ('rna','isolated'):
                other=pair('renewal',h,t,changed)
                raw=both(normal,'retained_E') and both(other,'retained_E',False)
                controls=all(both(pair('baseline',t=t,m=m,arm='wipe'),'retained_E',False) for m in ('open',changed))
                mode_contrasts.append(dict(founder=h,extra=t,changed_mode=changed,source_trials=1,
                    available=present(normal+other),normal_retained_E_both=both(normal,'retained_E'),
                    changed_retained_E_both=both(other,'retained_E'),normal_positive_changed_negative=raw,
                    matched_wipes_negative_both=controls,control_qualified_preparation_dependence=raw and controls,
                    P18_benchmark_supported_dependence=raw and controls and benchmark,
                    first_cell_survival_depends_on_mode=both(normal,'first_cell_stable_E_after_second') and both(other,'first_cell_stable_E_after_second',False)))
    return dict(readout_capacity=capacity,no_turnover=no_turn,references=references,wipe_controls=wipes,
        reference_wipes=reference_wipes,preparation_grid=grid,benchmark_consistency=consistency,
        mode_contrasts=mode_contrasts,chain_outcomes=chains)

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_preparation_support_v1.json').read_text()))
    checks.add('registration',summary['registered_cases']==expected_cases())
    stages=summary.get('attempted_stages',[]); checks.add('all_stages',stages==list(STAGES))
    history=predecessor_audit(run); checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==192 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values()); by={b['case']['id']:b['outcome'] for b in final['branches']}
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],completion_reason=summary.get('completion_reason'),
        fine_comparisons=final['fine_comparisons'],all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),**contrasts(by),
        external_schedule=True,autonomous_reproduction=False,independent_biological_replicates=False,benchmark_prior_age_matched=False,
        reused_P17_prefix_sources=True,extra_preparation_modes_fixed=True,later_coupling_common=True,first_prefixes_newly_integrated=False,outcome_dependent_selection=False,
        molecular_maturation_mechanism_established=False,exact_turnover_threshold_established=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree','readout_capacity','mode_contrasts','chain_outcomes','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2)); return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
