"""P17 independent audit of exact forks, focal retention and continued renewal."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import paper_renewal_maturation_design as d
import analyze_paper_turnover_limit as p16
import analyze_paper_lineage_robustness as p12
from analyze_paper_memory import Checks,labels
from analyze_paper_sheet import arrays

INDEX=p16.INDEX
STAGES=('baseline','prefix','forks','onward')
FOUNDERS=('written','ordinary','stock_E')
TAUS=(100,300,1000,3000,10000,20000)
ROUTES=('open','rna')
READOUTS=('open','rna','cut')

def spec(stage='prefix',founder='written',tau=100,route='open',arm='',readout='',fine=False):
    if stage=='baseline':
        route='open'
        if arm=='capacity': founder,tau='stock_E',0
        if arm=='no_turn': tau=20000
        if arm=='wipe': founder='stock_E'
    if stage=='prefix': arm=''
    if stage=='onward': arm='renew'
    name='__'.join([stage,founder,str(tau),route]+[x for x in (arm,readout) if x])
    return dict(id=name+('__fine' if fine else ''),stage=stage,founder=founder,tau=tau,route=route,arm=arm,readout=readout,fine=fine)

def expected_stage(stage,selection=None):
    if stage=='baseline':
        return ([spec(stage,arm='capacity',readout=k,fine=f) for f in (False,True) for k in READOUTS]+
                [spec(stage,h,arm='no_turn',fine=f) for f in (False,True) for h in FOUNDERS]+
                [spec(stage,tau=t,arm='wipe',fine=f) for f in (False,True) for t in TAUS])
    if stage in ('prefix','forks'):
        return [spec(stage,h,t,r,k,fine=f) for f in (False,True) for h in FOUNDERS for t in TAUS for r in ROUTES
                for k in (('',) if stage=='prefix' else ('isolate','renew'))]
    if stage!='onward' or selection is None: raise ValueError('Missing P17 stage/selection')
    return [spec(stage,h,t,r,'renew',k,f) for f in (False,True) for h in FOUNDERS for t in selection['taus'] for r in ROUTES for k in READOUTS]

def expected_cases(last='onward',selection=None):
    return [c for s in STAGES[:STAGES.index(last)+1] for c in expected_stage(s,selection)]

def selection_from(by):
    passing=[]
    for tau in TAUS:
        rows=[by.get(spec('forks',h,tau,'open','renew',fine=f)['id'],{}) for h in ('written','ordinary') for f in (False,True)]
        if all(x.get('available') is True and x.get('retained_E') is True for x in rows): passing.append(tau)
    if not passing: return dict(taus=[100,20000],reason='no_shared_renewal')
    first=min(passing); below=[t for t in TAUS if t<first]
    return dict(taus=[max(below),first] if below else [100,300],reason='shared_boundary' if below else 'left_censored')

def prefix(c): return spec('prefix',c['founder'],c['tau'],c['route'],fine=c['fine'])
def parent(c): return spec('forks',c['founder'],c['tau'],c['route'],'renew',fine=c['fine'])
def stem(c): return 'p17:%s:%s:%s'%(c['founder'],c['tau'],c['route'])
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return 'onward__%s__actual__patch__open'%c['founder']+('__fine' if c['fine'] else '')
def source_ids(c): return ['p15:%s:actual:patch:pupil:%02d'%(c['founder'],i) for i in range(3)]
def random_word(i):
    return int.from_bytes(hashlib.sha256(('P16_turnover_limit_v1|501|turnover|%d'%i).encode('ascii')).digest()[:8],'big')
def expected_draws(): return {'501':{'turnover':['%016x'%random_word(i) for i in range(6)]}}
def incoming(M,cycle,pos):
    x=M.copy(); x[7,0]=M[7,0]*(1+(random_word(cycle*3+pos)*51//(1<<64)-25)/100); return x

def stock_folder(run,fine):
    return run/'inputs/p16/inputs/p15/inputs/p14/inputs/p13/inputs/p12/inputs/p11'/('stock'+('__fine' if fine else ''))
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
            inputs=all(d.digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()))
    except (OSError,KeyError,RuntimeError): return dict(integrity_readable=False)

descriptor=p16.descriptor
observation=p16.observation

class Reader(p16.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}; self.environment=arrays(stock_folder(folder.parent,c['fine']),'preparation')['environment']

def founder(rd,run,c):
    if c['founder']=='stock_E':
        E,_=stock(run,c['fine']); value=np.repeat(E,3,axis=1); ids=stock_ids(c); base=0
    else:
        src=source(c); ids=source_ids(c); base=1180000
        rec=json.loads((run/'inputs/p16/inputs/p15'/src/'result.json').read_text())['phases'][-1]
        rd.ck('source_identity_and_clock',rec['phase']=='isolated_2' and rec['setup']['cell_ids']==ids and
              rec['logical_interval']==[1170000,1180000])
        value=arrays(run/'inputs/p16/inputs/p15'/src,'isolated_2')['final']
    rd.ck('founder_E',''.join(labels(value,INDEX))=='EEE')
    return value,ids,base

def replace(rd,c,M,value,ids,cycle,positions,event):
    value=value.copy(); rows=[]
    for pos in positions:
        x=incoming(M,cycle,pos); lab=str(labels(x,INDEX)[0]); rd.ck('incoming_%d_%d_M'%(cycle,pos),lab=='M')
        old=ids[pos]; ids[pos]=new_id(c,cycle,pos); value[:,pos:pos+1]=x
        rows.append(dict(event=event,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
    return value,rows

def holds(rd,ids,value,cursor,observations):
    for i in (1,2):
        name='isolated_'+str(i); value=rd.take(descriptor(name,ids,cursor,10000,'isolated'),value); cursor+=10000
        observations[name]=observation(rd.data[name],range(3))
    return cursor

def masks(observations):
    one,two=(observations['isolated_'+str(i)]['stable_E'] for i in (1,2))
    return [bool(x and y) for x,y in zip(one,two)]

def audit_baseline(rd,run,c):
    if c['arm']=='capacity': return audit_readout(rd,run,c)
    _,M=stock(run,c['fine']); value,ids,base=founder(rd,run,c); original_ids=ids.copy()
    observations={}; replacements=[]; cursor=base
    if c['arm']=='no_turn':
        value=rd.take(descriptor('no_turnover',ids,cursor,120000,'chain'),value); cursor+=120000
        observations['no_turnover']=observation(rd.data['no_turnover'],range(3))
    else:
        for cycle in (0,1):
            value,new=replace(rd,c,M,value,ids,cycle,range(3),cycle+1); replacements.extend(new)
            name='replacement_%02d'%(cycle+1)
            value=rd.take(descriptor(name,ids,cursor,3*c['tau'],'chain'),value); cursor+=3*c['tau']
            observations[name]=observation(rd.data[name],range(3))
        rd.ck('wipe_removed_every_original',not set(ids)&set(original_ids))
        rd.ck('wipe_equal_burden',len(replacements)==6 and cursor-base==6*c['tau'])
    cursor=holds(rd,ids,value,cursor,observations)
    return dict(available=True,original_ids=original_ids,observations=observations,replacements=replacements,
                retained_E=all(masks(observations)),logical_end=cursor)

def audit_prefix(rd,run,c):
    _,M=stock(run,c['fine']); value,ids,base=founder(rd,run,c); original_ids=ids.copy()
    source_labels=''.join(labels(value,INDEX)); value,replacements=replace(rd,c,M,value,ids,0,[0],1)
    value=rd.take(descriptor('replacement_01',ids,base,c['tau'],'chain',c['route']),value)
    obs=observation(rd.data['replacement_01'],range(3))
    return dict(available=True,source_labels=source_labels,original_ids=original_ids,replacements=replacements,
        observations={'replacement_01':obs},fork_labels=obs['patch_labels'],focal_E_at_fork=obs['patch_labels'][0]=='E',
        logical_end=base+c['tau'])

def prefix_state(rd,run,c):
    par=prefix(c); path=run/par['id']; record=json.loads((path/'result.json').read_text()); rec=record['phases'][-1]
    ids=stock_ids(c) if c['founder']=='stock_E' else source_ids(c); ids[0]=new_id(c,0,0)
    base=(0 if c['founder']=='stock_E' else 1180000); cursor=base+c['tau']
    rd.ck('shared_prefix_source',record['case']==par and len(record['phases'])==1 and rec['phase']=='replacement_01' and
          rec['setup']['cell_ids']==ids and rec['logical_interval']==[base,cursor])
    return arrays(path,'replacement_01')['final'],ids,cursor,record

def audit_forks(rd,run,c):
    value,ids,cursor,record=prefix_state(rd,run,c); initial_ids=ids.copy(); fork_labels=''.join(labels(value,INDEX))
    observations={}; replacements=[]
    if c['arm']=='renew':
        _,M=stock(run,c['fine'])
        for at in range(1,6):
            cycle,pos=divmod(at,3); value,new=replace(rd,c,M,value,ids,cycle,[pos],at+1); replacements.extend(new)
            name='replacement_%02d'%(at+1)
            value=rd.take(descriptor(name,ids,cursor,c['tau'],'chain',c['route']),value); cursor+=c['tau']
            observations[name]=observation(rd.data[name],range(3))
        original=stock_ids(c) if c['founder']=='stock_E' else source_ids(c)
        rd.ck('actual_original_ids',record['outcome']['original_ids']==original)
        rd.ck('all_founders_and_first_newcomer_removed',not set(ids)&set(original+initial_ids))
        rd.ck('fixed_five_further_replacements',len(replacements)==5 and cursor==(0 if c['founder']=='stock_E' else 1180000)+6*c['tau'])
    cursor=holds(rd,ids,value,cursor,observations); kept=masks(observations)
    common=dict(available=True,fork_ids=initial_ids,fork_labels=fork_labels,observations=observations,
                retained_E=all(kept),logical_end=cursor)
    if c['arm']=='isolate':
        rd.ck('focal_identity_preserved',ids==initial_ids and ids[0]==new_id(c,0,0))
        return dict(common,focal_id=initial_ids[0],focal_retained_E=kept[0],retained_E_by_cell=kept)
    first=observation(arrays(run/prefix(c)['id'],'replacement_01'),range(3))
    windows=[first]+[v for k,v in observations.items() if k.startswith('replacement')]
    continuous=all(all(x['stable_E']) for x in windows)
    return dict(common,original_ids=record['outcome']['original_ids'],replacements=replacements,
        first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        all_windows_E=continuous,continuous_renewal=continuous and all(kept),complete_carrier_replacement=True)

def audit_readout(rd,run,c):
    E,M=stock(run,c['fine'])
    if c['stage']=='baseline':
        donors=np.repeat(E,3,axis=1); ids=['p17:readout:stock_E:%02d'%i for i in range(3)]; base=0
    else:
        par=parent(c); path=run/par['id']; donors=arrays(path,'isolated_2')['final']
        ids=[new_id(c,1,i) for i in range(3)]; base=(0 if c['founder']=='stock_E' else 1180000)+6*c['tau']+20000
        record=json.loads((path/'result.json').read_text()); rec=record['phases'][-1]
        rd.ck('actual_renewal_parent',record['case']==par and rec['setup']['cell_ids']==ids and
              rec['logical_interval']==[base-10000,base] and record['outcome']['logical_end']==base)
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1)
    initial_donors=''.join(labels(donors,INDEX)); initial_recipients=''.join(labels(recipients,INDEX))
    rd.ck('fresh_recipients_M',initial_recipients=='MMM')
    value=rd.take(descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),np.concatenate((donors,recipients),axis=1))
    observations={'contact':observation(rd.data['contact'],range(3,6))}; donor_end=''.join(labels(value[:,:3],INDEX))
    rd.ck('all_donors_removed',not set(ids)&set(fresh)); holds(rd,fresh,value[:,3:],base+20000,observations)
    return dict(available=True,donor_initial_labels=initial_donors,recipient_initial_labels=initial_recipients,
        donor_end_labels=donor_end,observations=observations,transmitted_E=all(masks(observations)),logical_end=base+40000)

def replay_source(c):
    suffix='__fine' if c['fine'] else ''
    if c['stage']=='baseline':
        if c['arm']=='capacity': return 'baseline__stock_E__capacity__0__open__'+c['readout']+suffix
        if c['arm']=='no_turn': return 'baseline__%s__no_turn__20000__open'%c['founder']+suffix
        if c['arm']=='wipe' and c['tau'] in (100,20000): return 'screen__stock_E__wipe__%d__open'%c['tau']+suffix
    if c['stage']=='prefix' or (c['stage']=='forks' and c['arm']=='renew'):
        if c['route']=='open' and c['tau'] in (100,20000): stage='screen'
        elif c['route']=='rna' and c['tau']==20000: stage='rna_controls'
        else: return None
        return '%s__%s__single__%d__%s'%(stage,c['founder'],c['tau'],c['route'])+suffix
    return None

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1' and result.get('clock_policy')=='phase_scaled_sampling_and_step_cap_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve',
        'full_source_transfer','only_registered_columns_replaced','registered_interval_selection')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('benchmark_prior_age_matched','autonomous_reproduction',
        'parameter_retuning','outcome_dependent_cell_selection','cross_branch_pooling','cell_division_simulated',
        'independent_biological_replicates','automatic_follow_on')))
    rd.ck('fork_scope',result.get('exact_shared_prefix_fork')==(c['stage']=='forks'))
    functions={'baseline':audit_baseline,'prefix':audit_prefix,'forks':audit_forks,'onward':audit_readout}
    out=functions[c['stage']](rd,folder.parent,c); src=replay_source(c)
    rd.ck('replay_scope',result.get('exact_P16_replay')==(src is not None))
    if src is not None:
        for name,data in rd.data.items():
            archived=arrays(folder.parent/'inputs/p16'/src,name); rd.ck(name+'/replay_inventory',set(archived)==set(data))
            for key in archived: rd.eq(name+'/historical_replay/'+key,data[key],archived[key])
    return rd.finish(out)

def stage_audit(run,stage):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    cases=expected_cases(stage,summary.get('selection')); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; result=json.loads(path.read_text())
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and result==row['result'])
        report,data=branch(run/c['id'],c,checks); branches.append(report); by[c['id']]=report['outcome']
        endpoints[c['id']]=data; calls+=len(data)
    fine=p12.compare_fine(cases,by,endpoints,checks)
    chosen=selection_from(by) if stage in ('forks','onward') else None
    if stage=='onward': checks.add('independent_selection',chosen==summary['selection'])
    history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==json.loads((run/'predecessor_audit.json').read_text()) and
        d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('draw_book',json.loads((run/'frozen/paper_renewal_maturation_draws_v1.json').read_text())==expected_draws())
    checks.add('call_count',calls=={'baseline':84,'prefix':156,'forks':804,'onward':1020}[stage])
    checks.add('unique_case_records',len(records)==len(summary['cases']))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality),checks=checks.rows,
        integrity=provenance,branches=branches,fine_comparisons=fine,integration_calls=calls,
        cumulative_cases=len(branches),selection=chosen,eligibility_means_technical_permission_only=True)

def predecessor_audit(run):
    original=p16.analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p16/independent_audit.json').read_text())
    archived=p16.analyze(run/'inputs/p16'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==70715
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],actual_prechallenge_sources=True)

def contrasts(by,selection):
    def pair(stage,h='written',t=100,r='open',arm='',k=''):
        return [by.get(spec(stage,h,t,r,arm,k,f)['id'],{}) for f in (False,True)]
    def both(rows,key,value=True):
        return all(x.get('available') is True and x.get(key) is value for x in rows)
    opened=both(pair('baseline',arm='capacity',k='open'),'transmitted_E')
    blocked=all(both(pair('baseline',arm='capacity',k=k),'transmitted_E',False) for k in ('rna','cut'))
    capacity=dict(open_transmission_both=opened,negative_controls_both=blocked,qualified=opened and blocked)
    baseline=[dict(founder=h,source_trials=1,retained_E_both=both(pair('baseline',h,arm='no_turn'),'retained_E')) for h in FOUNDERS]
    wipes=[dict(tau=t,retained_E_both=both(pair('baseline',t=t,arm='wipe'),'retained_E'),
                negative_both=both(pair('baseline',t=t,arm='wipe'),'retained_E',False)) for t in TAUS]
    forks=[]; mechanisms=[]; chains=[]; timing=[]
    for h in FOUNDERS:
        for t in TAUS:
            for r in ROUTES:
                p=pair('prefix',h,t,r); isolated=pair('forks',h,t,r,'isolate'); renewed=pair('forks',h,t,r,'renew')
                focal=both(isolated,'focal_retained_E'); renewal=both(renewed,'retained_E')
                available=all(x.get('available') is True for x in p+isolated+renewed)
                classification=('both' if focal and renewal else 'retention_only' if focal else 'renewal_only' if renewal else 'neither') if available else 'unavailable'
                forks.append(dict(founder=h,tau=t,route=r,source_trials=1,available=available,
                    focal_E_at_fork_both=both(p,'focal_E_at_fork'),focal_isolated_retention_both=focal,
                    renewal_retention_both=renewal,classification=classification,
                    first_cell_stable_E_after_second_both=both(renewed,'first_cell_stable_E_after_second'),
                    all_windows_E_both=both(renewed,'all_windows_E'),continuous_renewal_both=both(renewed,'continuous_renewal')))
            mechanisms.append(dict(founder=h,tau=t,source_trials=1,
                focal_RNA_dependence=both(pair('forks',h,t,'open','isolate'),'focal_retained_E') and
                    both(pair('forks',h,t,'rna','isolate'),'focal_retained_E',False),
                renewal_RNA_dependence=both(pair('forks',h,t,'open','renew'),'retained_E') and
                    both(pair('forks',h,t,'rna','renew'),'retained_E',False)))
        timing.append(dict(founder=h,
            E_label_intervals=[t for t in TAUS if both(pair('prefix',h,t),'focal_E_at_fork')],
            focal_retention_intervals=[t for t in TAUS if both(pair('forks',h,t,arm='isolate'),'focal_retained_E')],
            renewal_intervals=[t for t in TAUS if both(pair('forks',h,t,arm='renew'),'retained_E')]))
        for t in selection['taus']:
            erased=both(pair('baseline',t=t,arm='wipe'),'retained_E',False)
            for r in ROUTES:
                renewed=pair('forks',h,t,r,'renew'); onward=both(pair('onward',h,t,r,k='open'),'transmitted_E')
                controls=all(both(pair('onward',h,t,r,k=k),'transmitted_E',False) for k in ('rna','cut'))
                raw=both(renewed,'retained_E') and onward
                chains.append(dict(founder=h,tau=t,route=r,source_trials=1,
                    retained_E_both=both(renewed,'retained_E'),onward_transmission_both=onward,
                    raw_retention_and_onward=raw,continuous_full_chain=both(renewed,'continuous_renewal') and onward,
                    negative_wipe_both=erased,control_qualified_transmission=onward and controls,
                    control_qualified_chain=raw and controls and erased,
                    benchmark_supported_chain=raw and controls and erased and capacity['qualified']))
    return dict(readout_capacity=capacity,no_turnover=baseline,wipe_controls=wipes,
                fork_contrasts=forks,RNA_contrasts=mechanisms,timing_summary=timing,chain_outcomes=chains)

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_renewal_maturation_v1.json').read_text()))
    selection=summary.get('selection'); checks.add('registration',summary['registered_cases']==expected_cases(selection=selection))
    stages=summary.get('attempted_stages',[]); checks.add('all_stages',stages==list(STAGES))
    history=predecessor_audit(run); checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report; checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==312 and
        {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases(selection=selection)})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    checks.add('selection',selection==reports['forks']['selection']==final['selection'])
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,
        stages=reports,completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],
        completion_reason=summary.get('completion_reason'),fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),selection=selection,
        **contrasts(by,selection),external_schedule=True,autonomous_reproduction=False,
        reused_P16_prechallenge_sources=True,independent_biological_replicates=False,benchmark_prior_age_matched=False,
        selected_followups_independently_confirmed=False,exact_turnover_threshold_established=False,
        molecular_maturation_mechanism_established=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree',
          'selection','readout_capacity','timing_summary','chain_outcomes','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2))
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
