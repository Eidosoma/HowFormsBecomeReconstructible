"""P18 independent reconstruction of preparation/subsequent-turnover contrasts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import paper_preparation_turnover_design as d
import analyze_paper_renewal_maturation as p17
from analyze_paper_memory import Checks,labels
from analyze_paper_sheet import arrays

p16=p17.p16
p12=p17.p12
INDEX=p16.INDEX
STAGES=('baseline','renewal','onward')
FOUNDERS=('written','ordinary','stock_E')
TIMES=(100,300,1000)
ROUTES=('open','rna')
READOUTS=('open','rna','cut')
ONWARD=((100,100),(100,300),(300,300),(1000,100))

def spec(stage='renewal',founder='written',first=100,later=100,route='open',arm='',readout='',fine=False):
    if stage=='baseline':
        route='open'
        if arm=='capacity': founder,first,later='stock_E',0,0
        if arm=='no_turn': first=later=20000
        if arm=='wipe': founder='stock_E'
    else: arm='renew'
    name='__'.join([stage,founder,str(first),str(later),route]+[x for x in (arm,readout) if x])
    return dict(id=name+('__fine' if fine else ''),stage=stage,founder=founder,first=first,later=later,
                route=route,arm=arm,readout=readout,fine=fine)

def expected_stage(stage):
    if stage=='baseline':
        return ([spec(stage,arm='capacity',readout=k,fine=f) for f in (False,True) for k in READOUTS]+
            [spec(stage,h,arm='no_turn',fine=f) for f in (False,True) for h in FOUNDERS]+
            [spec(stage,first=u,later=v,arm='wipe',fine=f) for f in (False,True) for u in TIMES for v in TIMES])
    if stage=='renewal':
        return [spec(stage,h,u,v,r,fine=f) for f in (False,True) for h in FOUNDERS for u in TIMES for v in TIMES for r in ROUTES]
    if stage=='onward':
        return [spec(stage,h,u,v,r,readout=k,fine=f) for f in (False,True) for h in FOUNDERS for u,v in ONWARD for r in ROUTES for k in READOUTS]
    raise ValueError('Unregistered stage')

def expected_cases(last='onward'): return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s)]
def parent(c): return spec('renewal',c['founder'],c['first'],c['later'],c['route'],fine=c['fine'])
def prefix_source(c): return 'prefix__%s__%d__%s'%(c['founder'],c['first'],c['route'])+('__fine' if c['fine'] else '')
def stem(c): return 'p18:%s:%s:%s:%s'%(c['founder'],c['first'],c['later'],c['route'])
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def prefix_stem(c): return 'p17:%s:%d:%s'%(c['founder'],c['first'],c['route'])
def original_ids(c):
    return ([prefix_stem(c)+':stock_E:%02d'%i for i in range(3)] if c['founder']=='stock_E' else
            ['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)])
def random_word(i):
    return int.from_bytes(hashlib.sha256(('P16_turnover_limit_v1|501|turnover|%d'%i).encode('ascii')).digest()[:8],'big')
def expected_draws(): return {'501':{'turnover':['%016x'%random_word(i) for i in range(6)]}}
def incoming(M,cycle,pos):
    x=M.copy(); x[7,0]=M[7,0]*(1+(random_word(cycle*3+pos)*51//(1<<64)-25)/100); return x
def stock_folder(run,fine):
    return run/'inputs/p17/inputs/p16/inputs/p15/inputs/p14/inputs/p13/inputs/p12/inputs/p11'/('stock'+('__fine' if fine else ''))
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

descriptor=p16.descriptor
observation=p16.observation
masks=p17.masks
holds=p17.holds

class Reader(p16.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}; self.environment=arrays(stock_folder(folder.parent,c['fine']),'preparation')['environment']

def founder(rd,run,c):
    if c['founder']=='stock_E':
        E,_=stock(run,c['fine']); value=np.repeat(E,3,axis=1); ids=stock_ids(c); base=0
    else:
        src='onward__%s__actual__patch__open'%c['founder']+('__fine' if c['fine'] else '')
        path=run/'inputs/p17/inputs/p16/inputs/p15'/src; ids=original_ids(c); base=1180000
        rec=json.loads((path/'result.json').read_text())['phases'][-1]
        rd.ck('source_identity_and_clock',rec['phase']=='isolated_2' and rec['setup']['cell_ids']==ids and rec['logical_interval']==[1170000,1180000])
        value=arrays(path,'isolated_2')['final']
    rd.ck('founder_E',''.join(labels(value,INDEX))=='EEE')
    return value,ids,base

def replace(rd,c,M,value,ids,cycle,positions,event):
    value=value.copy(); rows=[]
    for pos in positions:
        x=incoming(M,cycle,pos); lab=str(labels(x,INDEX)[0]); rd.ck('incoming_%d_%d_M'%(cycle,pos),lab=='M')
        old=ids[pos]; ids[pos]=new_id(c,cycle,pos); value[:,pos:pos+1]=x
        rows.append(dict(event=event,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
    return value,rows

def audit_baseline(rd,run,c):
    if c['arm']=='capacity': return audit_readout(rd,run,c)
    _,M=stock(run,c['fine']); value,ids,base=founder(rd,run,c); original=ids.copy()
    observations={}; replacements=[]; cursor=base
    if c['arm']=='no_turn':
        value=rd.take(descriptor('no_turnover',ids,cursor,120000,'chain'),value); cursor+=120000
        observations['no_turnover']=observation(rd.data['no_turnover'],range(3))
    else:
        for cycle,span in enumerate((c['first']+2*c['later'],3*c['later'])):
            value,new=replace(rd,c,M,value,ids,cycle,range(3),cycle+1); replacements.extend(new)
            name='replacement_%02d'%(cycle+1); value=rd.take(descriptor(name,ids,cursor,span,'chain'),value); cursor+=span
            observations[name]=observation(rd.data[name],range(3))
        rd.ck('wipe_removed_all_originals',not set(ids)&set(original))
        rd.ck('wipe_matches_burden_and_exposure',len(replacements)==6 and cursor-base==c['first']+5*c['later'])
    cursor=holds(rd,ids,value,cursor,observations)
    return dict(available=True,original_ids=original,observations=observations,replacements=replacements,
                retained_E=all(masks(observations)),logical_end=cursor)

def prefix_state(rd,run,c):
    src=prefix_source(c); path=run/'inputs/p17'/src; record=json.loads((path/'result.json').read_text())
    rec=record['phases'][0]; ids=original_ids(c); ids[0]=prefix_stem(c)+':replacement:0:0'
    base=0 if c['founder']=='stock_E' else 1180000; cursor=base+c['first']
    expected=dict(id=src,stage='prefix',founder=c['founder'],tau=c['first'],route=c['route'],arm='',readout='',fine=c['fine'])
    rd.ck('archived_prefix_identity_and_clock',record['case']==expected and len(record['phases'])==1 and rec['phase']=='replacement_01' and
          rec['setup']['cell_ids']==ids and rec['logical_interval']==[base,cursor])
    rd.ck('prefix_transport_route',rec['setup']['mirna_kd']==(0 if c['route']=='rna' else 1.25e-14))
    data=arrays(path,'replacement_01'); rd.ck('prefix_raw_frozen',d.digest(path/'replacement_01.npz')==rec['sha256'])
    rd.ck('prefix_observation_reconstructed',observation(data,range(3))==record['outcome']['observations']['replacement_01'])
    return data,ids,cursor,record

def audit_renewal(rd,run,c):
    prefix,ids,cursor,record=prefix_state(rd,run,c); value=prefix['final']; initial_ids=ids.copy()
    fork_labels=''.join(labels(value,INDEX)); observations={}; replacements=[]; _,M=stock(run,c['fine'])
    for at in range(1,6):
        cycle,pos=divmod(at,3); value,new=replace(rd,c,M,value,ids,cycle,[pos],at+1); replacements.extend(new)
        name='replacement_%02d'%(at+1); value=rd.take(descriptor(name,ids,cursor,c['later'],'chain',c['route']),value); cursor+=c['later']
        observations[name]=observation(rd.data[name],range(3))
    originals=original_ids(c); rd.ck('original_ids',record['outcome']['original_ids']==originals)
    rd.ck('all_founders_and_first_newcomer_removed',not set(ids)&set(originals+initial_ids))
    rd.ck('fixed_order_and_duration',len(replacements)==5 and cursor==(0 if c['founder']=='stock_E' else 1180000)+c['first']+5*c['later'])
    cursor=holds(rd,ids,value,cursor,observations); kept=masks(observations)
    later_good=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement'))
    all_good=later_good and all(observation(prefix,range(3))['stable_E'])
    return dict(available=True,fork_ids=initial_ids,fork_labels=fork_labels,
        observations=observations,retained_E=all(kept),logical_end=cursor,
        original_ids=record['outcome']['original_ids'],replacements=replacements,
        first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=later_good,all_windows_E=all_good,continuous_renewal=all_good and all(kept),complete_carrier_replacement=True)

def audit_readout(rd,run,c):
    E,M=stock(run,c['fine'])
    if c['stage']=='baseline':
        donors=np.repeat(E,3,axis=1); ids=['p18:readout:stock_E:%02d'%i for i in range(3)]; base=0
    else:
        par=parent(c); path=run/par['id']; donors=arrays(path,'isolated_2')['final']
        ids=[new_id(c,1,i) for i in range(3)]; base=(0 if c['founder']=='stock_E' else 1180000)+c['first']+5*c['later']+20000
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

def replay_source(c):
    suffix='__fine' if c['fine'] else ''
    if c['stage']=='baseline':
        if c['arm']=='capacity': return 'baseline__stock_E__0__open__capacity__'+c['readout']+suffix
        if c['arm']=='no_turn': return 'baseline__%s__20000__open__no_turn'%c['founder']+suffix
        if c['first']==c['later']: return 'baseline__stock_E__%d__open__wipe'%c['first']+suffix
    elif c['first']==c['later']:
        if c['stage']=='renewal': return 'forks__%s__%d__%s__renew'%(c['founder'],c['first'],c['route'])+suffix
        if c['stage']=='onward': return 'onward__%s__%d__%s__renew__%s'%(c['founder'],c['first'],c['route'],c['readout'])+suffix
    return None

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve','full_source_transfer','only_registered_columns_replaced','fixed_onward_schedules')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('benchmark_prior_age_matched','autonomous_reproduction','parameter_retuning',
        'outcome_dependent_cell_selection','cross_branch_pooling','cell_division_simulated','independent_biological_replicates','automatic_follow_on')))
    rd.ck('fork_scope',result.get('exact_archived_prefix_fork')==(c['stage']=='renewal'))
    rd.ck('prefix_provenance',result.get('archived_prefix_source')==(prefix_source(c) if c['stage']=='renewal' else None))
    out={'baseline':audit_baseline,'renewal':audit_renewal,'onward':audit_readout}[c['stage']](rd,folder.parent,c)
    src=replay_source(c); rd.ck('replay_scope',result.get('exact_P17_replay')==(src is not None))
    if src is not None:
        for name,data in rd.data.items():
            archived=arrays(folder.parent/'inputs/p17'/src,name); rd.ck(name+'/replay_inventory',set(archived)==set(data))
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
    fine=p12.compare_fine(cases,by,endpoints,checks); history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==json.loads((run/'predecessor_audit.json').read_text()) and d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('draw_book',json.loads((run/'frozen/paper_preparation_turnover_draws_v1.json').read_text())==expected_draws())
    checks.add('call_count',calls=={'baseline':108,'renewal':864,'onward':1296}[stage])
    checks.add('unique_case_records',len(records)==len(summary['cases']))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality),checks=checks.rows,integrity=provenance,
        branches=branches,fine_comparisons=fine,integration_calls=calls,cumulative_cases=len(branches),eligibility_means_technical_permission_only=True)

def predecessor_audit(run):
    run=Path(run); original=p17.analyze(d.PREDECESSOR); saved=json.loads((run/'inputs/p17/independent_audit.json').read_text())
    summary=json.loads((run/'summary.json').read_text()); verified=integrity(run,summary)
    archive=all(verified.values())
    good=original==saved and original['quality_gate'] and original['independent_check_count']==75638 and archive
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_byte_identical=archive,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],prior_calls=original['integration_calls'],
        original_reaudit_count=1,archive_separate_mathematical_reaudit=False,hardlinked_inputs_not_independent_backup=True,
        actual_P17_prefix_sources=True)

def contrasts(by):
    def pair(stage,h='written',u=100,v=100,r='open',arm='',k=''):
        return [by.get(spec(stage,h,u,v,r,arm,k,f)['id'],{}) for f in (False,True)]
    def both(rows,key,value=True): return all(x.get('available') is True and x.get(key) is value for x in rows)
    def present(rows): return all(x.get('available') is True for x in rows)
    opened=both(pair('baseline',arm='capacity',k='open'),'transmitted_E')
    blocked=all(both(pair('baseline',arm='capacity',k=k),'transmitted_E',False) for k in ('rna','cut'))
    capacity=dict(open_transmission_both=opened,negative_controls_both=blocked,qualified=opened and blocked)
    no_turn=[dict(founder=h,source_trials=1,retained_E_both=both(pair('baseline',h,arm='no_turn'),'retained_E')) for h in FOUNDERS]
    wipes=[dict(first=u,later=v,negative_both=both(pair('baseline',u=u,v=v,arm='wipe'),'retained_E',False)) for u in TIMES for v in TIMES]
    grid=[]; rna=[]; timing=[]; chains=[]
    for h in FOUNDERS:
        for u in TIMES:
            for v in TIMES:
                for route in ROUTES:
                    rows=pair('renewal',h,u,v,route)
                    grid.append(dict(founder=h,first=u,later=v,route=route,source_trials=1,available=present(rows),
                        retained_E_both=both(rows,'retained_E'),first_cell_stable_E_after_second_both=both(rows,'first_cell_stable_E_after_second'),
                        later_windows_E_both=both(rows,'later_windows_E'),all_windows_E_both=both(rows,'all_windows_E'),continuous_renewal_both=both(rows,'continuous_renewal')))
                rna.append(dict(founder=h,first=u,later=v,source_trials=1,
                    renewal_RNA_dependence=both(pair('renewal',h,u,v),'retained_E') and both(pair('renewal',h,u,v,'rna'),'retained_E',False)))
        for dimension in ('first','later'):
            for longer in (300,1000):
                u,v=(longer,100) if dimension=='first' else (100,longer)
                base=pair('renewal',h,100,100); changed=pair('renewal',h,u,v)
                base_fail=both(base,'retained_E',False); success=both(changed,'retained_E')
                controls=both(pair('renewal',h,u,v,'rna'),'retained_E',False) and both(pair('baseline',u=u,v=v,arm='wipe'),'retained_E',False)
                timing.append(dict(founder=h,varied_interval=dimension,longer=longer,first=u,later=v,source_trials=1,
                    available=present(base+changed),baseline_failed_both=base_fail,changed_retained_E_both=success,
                    raw_rescue=base_fail and success,control_qualified_rescue=base_fail and success and controls))
        for u,v in ONWARD:
            for route in ROUTES:
                rows=pair('renewal',h,u,v,route); onward=both(pair('onward',h,u,v,route,k='open'),'transmitted_E')
                controls=all(both(pair('onward',h,u,v,route,k=k),'transmitted_E',False) for k in ('rna','cut'))
                wipe=both(pair('baseline',u=u,v=v,arm='wipe'),'retained_E',False); retained=both(rows,'retained_E'); raw=retained and onward
                chains.append(dict(founder=h,first=u,later=v,route=route,source_trials=1,retained_E_both=retained,
                    onward_transmission_both=onward,raw_retention_and_onward=raw,continuous_full_chain=both(rows,'continuous_renewal') and onward,
                    negative_wipe_both=wipe,control_qualified_transmission=onward and controls,control_qualified_chain=raw and controls and wipe,
                    benchmark_supported_chain=raw and controls and wipe and capacity['qualified']))
    return dict(readout_capacity=capacity,no_turnover=no_turn,wipe_controls=wipes,timing_grid=grid,RNA_contrasts=rna,
                timing_contrasts=timing,chain_outcomes=chains)

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_preparation_turnover_v1.json').read_text()))
    checks.add('registration',summary['registered_cases']==expected_cases())
    stages=summary.get('attempted_stages',[]); checks.add('all_stages',stages==list(STAGES))
    history=predecessor_audit(run); checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==282 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values()); by={b['case']['id']:b['outcome'] for b in final['branches']}
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,stages=reports,
        completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],completion_reason=summary.get('completion_reason'),
        fine_comparisons=final['fine_comparisons'],all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),**contrasts(by),
        external_schedule=True,autonomous_reproduction=False,independent_biological_replicates=False,benchmark_prior_age_matched=False,
        reused_P17_prefix_sources=True,first_prefixes_newly_integrated=False,outcome_dependent_selection=False,
        molecular_maturation_mechanism_established=False,exact_turnover_threshold_established=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree','readout_capacity','timing_contrasts','chain_outcomes','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2)); return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
