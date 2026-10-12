"""P15 independent reconstruction of support contrasts, turnover and donor-free readouts."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import paper_tissue_dependence_design as d
import analyze_paper_lineage_robustness as p12
import analyze_paper_tissue_persistence as p14
from analyze_paper_memory import Checks,labels
from analyze_paper_sheet import arrays,edges

INDEX=p12.INDEX
STAGES=('readout','turnover','onward')
HISTORIES=('written','ordinary')
CARRIERS=('actual','stock_E')
ROUTES=('tissue','patch','patch_rna')
READOUTS=('open','rna','cut')
PATCH=(83,84,85)

def spec(stage='turnover',history='written',carrier='actual',route='patch',readout='',fine=False):
    if stage=='readout': history,carrier,route='stock','stock_E',''
    name='__'.join([stage]+[x for x in (history,carrier,route,readout) if x])
    return dict(id=name+('__fine' if fine else ''),stage=stage,history=history,carrier=carrier,
                route=route,readout=readout,fine=fine)
def expected_stage(stage):
    if stage=='readout': return [spec(stage,readout=k,fine=f) for f in (False,True) for k in READOUTS]
    if stage not in ('turnover','onward'): raise ValueError('Unknown stage')
    return [spec(stage,h,s,r,k,f) for f in (False,True) for h in HISTORIES for s in CARRIERS
            for r in ROUTES for k in (READOUTS if stage=='onward' else ('',))]
def expected_cases(last='onward'):
    return [c for stage in STAGES[:STAGES.index(last)+1] for c in expected_stage(stage)]
def parent(c): return spec('turnover',c['history'],c['carrier'],c['route'],fine=c['fine'])
def prefix(c): return 'p15:%s:%s:%s'%(c['history'],c['carrier'],c['route'])
def stock_ids(c): return [prefix(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,i): return prefix(c)+':replacement:%02d'%i
def pupils(c): return [prefix(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return 'panel__%s__sham'%c['history']+('__fine' if c['fine'] else '')
def source_ids(c):
    ids=['p14:%s:background:%03d'%(c['history'],i) for i in range(169)]
    for i,pos in enumerate(PATCH): ids[pos]='p13:%s:301:pupil:09:%02d'%(c['history'],i)
    return ids
def random_word(i):
    return int.from_bytes(hashlib.sha256(('P14_tissue_persistence_v1|401|turnover|%d'%i).encode('ascii')).digest()[:8],'big')
def expected_draws(): return {'401':{'turnover':['%016x'%random_word(i) for i in range(3)]}}
def incoming(M,i):
    value=M.copy(); value[7,0]=M[7,0]*(1+(random_word(i)*51//(1<<64)-25)/100)
    return value
def stock(run,fine):
    value=arrays(run/'inputs/p14/inputs/p13/inputs/p12/inputs/p11'/
                 ('stock'+('__fine' if fine else '')),'preparation')['final']
    return value[:,168:169],value[:,1:2]

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

def descriptor(name,ids,base,span,kind,route='open'):
    isolated=kind=='isolated'; shape=[1,3] if isolated else [13,13] if kind=='tissue' else [2,3]
    fr,to=edges(shape); power=1 if isolated else 60
    internal=power; boundary=1 if kind=='tissue' else power
    kd=0 if isolated or route in ('patch_rna','rna') else 1.25e-14
    cut=(kind=='tissue' and route!='tissue') or (kind=='readout' and route=='cut')
    members=set(PATCH) if kind=='tissue' else {0,1,2} if kind=='readout' else set()
    regions=np.array([1 if f in members and t in members else 2 if (f in members)!=(t in members) else 0
                      for f,t in zip(fr,to)],dtype=np.int8)
    return dict(name=name,ids=ids.copy(),shape=shape,base=base,horizon=span,graph=False,
        power=power,kd=kd,isolated=isolated,fr=fr,to=to,regions=regions,
        powers=np.choose(regions,[power,internal,boundary]).astype(float),
        available=np.where((regions==2)&cut,0.,1.),
        compartments=dict(internal=internal,boundary=boundary,helper=power,boundary_cut=cut))

class Reader(p12.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}
        self.environment=arrays(folder.parent/'inputs/p14/inputs/p13/inputs/p12/inputs/p11'/
            ('stock'+('__fine' if c['fine'] else '')),'preparation')['environment']
    def finish(self,out):
        self.ck('exact_raw_inventory',{p.stem for p in self.folder.glob('*.npz')}=={p['phase'] for p in self.records})
        return super().finish(out)

def observation(data,positions,tissue=False):
    end=labels(data['final'],INDEX); samples=labels(data['concentrations'],INDEX)
    late=samples[data['times']>=.75*data['times'][-1]]
    pos=list(positions); result=dict(patch_labels=''.join(end[pos]))
    for lab in ('E','M'):
        result['stable_'+lab]=((end[pos]==lab)&(np.mean(late[:,pos]==lab,axis=0)>=.95)).tolist()
    if tissue:
        competitor=[13*y+x for y in range(2,5) for x in range(2,5)]
        background=[i for i in range(169) if i not in set(PATCH)|set(competitor)]
        result.update(background_E_now_M=int(np.count_nonzero(end[background]=='M')),
            maximum_background_E_now_M=int(np.max(np.count_nonzero(samples[:,background]=='M',axis=1))),
            competitor_labels=''.join(end[competitor]))
    return result

def audit_turnover(rd,run,c):
    E,M=stock(run,c['fine']); src=source(c); ids=source_ids(c)
    info=json.loads((run/'inputs/p14'/src/'result.json').read_text())
    rec=next(p for p in info['phases'] if p['phase']=='withdrawal_2')
    rd.ck('source_identity_and_clock',rec['setup']['cell_ids']==ids and rec['logical_interval']==[1050000,1060000])
    value=arrays(run/'inputs/p14'/src,'withdrawal_2')['final']
    rd.ck('actual_source_E',''.join(labels(value[:,list(PATCH)],INDEX))=='EEE')
    if c['carrier']=='stock_E':
        value=value.copy(); value[:,list(PATCH)]=np.repeat(E,3,axis=1)
        for pos,name in zip(PATCH,stock_ids(c)): ids[pos]=name
    original_ids=[ids[p] for p in PATCH]; source_labels=''.join(labels(value[:,list(PATCH)],INDEX))
    observed={}; replacements=[]
    for i,pos in enumerate(PATCH):
        initial=incoming(M,i); lab=str(labels(initial,INDEX)[0]); rd.ck('incoming_%d_M'%i,lab=='M')
        old=ids[pos]; ids[pos]=new_id(c,i); value=value.copy(); value[:,pos:pos+1]=initial
        name='replacement_'+str(i+1)
        value=rd.take(descriptor(name,ids,1060000+20000*i,20000,'tissue',c['route']),value)
        observed[name]=observation(rd.data[name],PATCH,True)
        replacements.append(dict(position=pos,removed=old,inserted=ids[pos],initial_label=lab,
                                 stable_E=observed[name]['stable_E']))
    rd.ck('all_original_carriers_removed',not set(original_ids)&set(ids))
    value=value[:,list(PATCH)]; ids=[ids[p] for p in PATCH]
    for i in (1,2):
        name='isolated_'+str(i)
        value=rd.take(descriptor(name,ids,1120000+(i-1)*10000,10000,'isolated'),value)
        observed[name]=observation(rd.data[name],range(3))
    if c['carrier']=='actual' and c['route']=='tissue':
        for name,data in rd.data.items():
            archived=arrays(run/'inputs/p14'/src,name)
            rd.ck(name+'/historical_replay_inventory',set(archived)==set(data))
            for key in archived: rd.eq(name+'/historical_replay/'+key,data[key],archived[key])
    replaced=all(all(x['stable_E']) for x in replacements)
    isolated=all(all(observed['isolated_'+str(i)]['stable_E']) for i in (1,2))
    return dict(available=True,source_labels=source_labels,original_ids=original_ids,
        observations=observed,replacements=replacements,all_replacements_corrected=replaced,
        isolated_E_memory=isolated,renewal_success=replaced and isolated,logical_end=1140000)

def audit_readout(rd,run,c):
    E,M=stock(run,c['fine'])
    if c['stage']=='readout':
        donors=np.repeat(E,3,axis=1); ids=['p15:readout:stock_E:%02d'%i for i in range(3)]; base=0
    else:
        parent_case=parent(c); path=run/parent_case['id']
        donors=arrays(path,'isolated_2')['final']; ids=[new_id(c,i) for i in range(3)]; base=1140000
        row=json.loads((path/'result.json').read_text())
        rd.ck('actual_turnover_parent',row['case']==parent_case and row['phases'][-1]['setup']['cell_ids']==ids and
              row['phases'][-1]['logical_interval']==[1130000,1140000])
    fresh=pupils(c); recipients=np.repeat(M,3,axis=1)
    initial_donors=''.join(labels(donors,INDEX)); initial_recipients=''.join(labels(recipients,INDEX))
    rd.ck('fresh_recipients_M',initial_recipients=='MMM')
    value=rd.take(descriptor('contact',ids+fresh,base,20000,'readout',c['readout']),
                  np.concatenate((donors,recipients),axis=1))
    observed={'contact':observation(rd.data['contact'],range(3,6))}
    donor_end=''.join(labels(value[:,:3],INDEX)); value=value[:,3:]
    rd.ck('all_donors_removed',not set(ids)&set(fresh))
    for i in (1,2):
        name='isolated_'+str(i)
        value=rd.take(descriptor(name,fresh,base+20000+(i-1)*10000,10000,'isolated'),value)
        observed[name]=observation(rd.data[name],range(3))
    success=all(all(observed['isolated_'+str(i)]['stable_E']) for i in (1,2))
    return dict(available=True,donor_initial_labels=initial_donors,recipient_initial_labels=initial_recipients,
        donor_end_labels=donor_end,observations=observed,transmitted_E=success,logical_end=base+40000)

def branch(folder,c,checks):
    rd=Reader(folder,c,checks); result=rd.result; run=folder.parent
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve',
        'full_source_transfer','only_registered_columns_replaced')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('benchmark_prior_age_matched',
        'autonomous_reproduction','parameter_retuning','outcome_dependent_cell_selection','cross_branch_pooling',
        'cell_division_simulated','independent_biological_replicates','automatic_follow_on')))
    rd.ck('replay_scope',result.get('exact_P14_suffix_replay')==
          (c['stage']=='turnover' and c['carrier']=='actual' and c['route']=='tissue'))
    out=audit_turnover(rd,run,c) if c['stage']=='turnover' else audit_readout(rd,run,c)
    return rd.finish(out)

def stage_audit(run,stage):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    cases=expected_cases(stage); records={r['id']:r for r in summary['cases']}
    branches=[]; by={}; endpoints={}; calls=0
    for c in cases:
        row=records.get(c['id']); checks.add(c['id']+'/record',row is not None and row['execution_pass'])
        if row is None or not row['execution_pass']: continue
        path=run/c['id']/'result.json'; result=json.loads(path.read_text())
        checks.add(c['id']+'/result_frozen',d.digest(path)==row['result_sha256'] and result==row['result'])
        report,data=branch(run/c['id'],c,checks)
        branches.append(report); by[c['id']]=report['outcome']; endpoints[c['id']]=data; calls+=len(data)
    fine=p12.compare_fine(cases,by,endpoints,checks)
    history=summary.get('predecessor_audit',{})
    checks.add('history_checked',summary.get('predecessor_gate') is True and history.get('quality_gate') is True)
    checks.add('history_saved',history==json.loads((run/'predecessor_audit.json').read_text()) and
               d.digest(run/'predecessor_audit.json')==summary.get('predecessor_audit_sha256'))
    checks.add('draw_book',json.loads((run/'frozen/paper_tissue_dependence_draws_v1.json').read_text())==expected_draws())
    checks.add('call_count',calls=={'readout':18,'turnover':138,'onward':354}[stage])
    checks.add('unique_case_records',len(records)==len(summary['cases']))
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality),checks=checks.rows,
        integrity=provenance,branches=branches,fine_comparisons=fine,integration_calls=calls,
        cumulative_cases=len(branches),eligibility_means_technical_permission_only=True)

def predecessor_audit(run):
    original=p14.analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p14/independent_audit.json').read_text())
    archived=p14.analyze(run/'inputs/p14'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==18273
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],actual_pre_replacement_sources=True)

def contrasts(by):
    def outcome(c): return by.get(c['id'],{})
    def pair(stage,h='written',s='actual',r='patch',k=''):
        return [outcome(spec(stage,h,s,r,k,f)) for f in (False,True)]
    def all_true(rows,key): return all(x.get('available',False) and x.get(key,False) for x in rows)
    def all_false(rows,key): return all(x.get('available',False) and x.get(key) is False for x in rows)
    positive=all_true(pair('readout',k='open'),'transmitted_E')
    negative=all(all_false(pair('readout',k=k),'transmitted_E') for k in ('rna','cut'))
    capacity=dict(open_transmission_both=positive,negative_controls_both=negative,qualified=positive and negative)
    support=[]; chains=[]
    for h in HISTORIES:
        for s in CARRIERS:
            statuses={r:all_true(pair('turnover',h,s,r),'renewal_success') for r in ROUTES}
            t,p=statuses['tissue'],statuses['patch']
            classification='both_renew' if t and p else 'tissue_only' if t else 'patch_only' if p else 'neither'
            available=all(x.get('available',False) for r in ROUTES for x in pair('turnover',h,s,r))
            support.append(dict(history=h,carrier=s,source_trials=1,available=available,
                renewal_both=statuses,comparison=classification if available else 'unavailable',
                patch_RNA_dependence=available and p and all_false(pair('turnover',h,s,'patch_rna'),'renewal_success')))
            for r in ROUTES:
                opened=all_true(pair('onward',h,s,r,'open'),'transmitted_E')
                controls=all(all_false(pair('onward',h,s,r,k),'transmitted_E') for k in ('rna','cut'))
                raw=statuses[r] and opened
                chains.append(dict(history=h,carrier=s,route=r,source_trials=1,renewal_both=statuses[r],
                    onward_transmission_both=opened,raw_full_chain=raw,
                    control_qualified_transmission=opened and controls,
                    control_qualified_full_chain=raw and controls,
                    benchmark_supported_full_chain=raw and controls and capacity['qualified']))
    return capacity,support,chains

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_tissue_dependence_v1.json').read_text()))
    checks.add('registration',summary['registered_cases']==expected_cases())
    stages=summary.get('attempted_stages',[]); checks.add('all_stages',stages==list(STAGES))
    history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]
    checks.add('case_count',len(summary['cases'])==102 and {r['id'] for r in summary['cases']}=={c['id'] for c in expected_cases()})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}
    capacity,support,chains=contrasts(by)
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,
        stages=reports,completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],
        completion_reason=summary.get('completion_reason'),fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),readout_capacity=capacity,
        support_contrasts=support,chain_outcomes=chains,external_schedule=True,autonomous_reproduction=False,
        reused_P14_ancestry=True,independent_biological_replicates=False,benchmark_prior_age_matched=False,
        automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count','all_fine_agree',
          'readout_capacity','support_contrasts','chain_outcomes','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2))
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
