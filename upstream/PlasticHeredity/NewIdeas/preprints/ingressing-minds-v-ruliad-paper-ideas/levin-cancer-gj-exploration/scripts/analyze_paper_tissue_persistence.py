"""Independent P14 reconstruction of live tissue, withdrawal and each cell replacement."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import paper_tissue_persistence_design as d
import analyze_paper_lineage_robustness as p12
import analyze_paper_lineage_return as p13
from analyze_paper_memory import Checks,labels
from analyze_paper_sheet import arrays,edges

INDEX=p12.INDEX
STAGES=('panel',)
HISTORIES=('written','ordinary','fresh_M')
ARMS=('sham','internal','boundary','both','rna','cut')
PATCH=(83,84,85)
COMPETITORS=tuple(13*y+x for y in range(2,5) for x in range(2,5))
BACKGROUND=tuple(i for i in range(169) if i not in PATCH+COMPETITORS)

def spec(history='written',arm='both',fine=False):
    return dict(id='panel__%s__%s'%(history,arm)+('__fine' if fine else ''),
                stage='panel',history=history,arm=arm,fine=fine)
def expected_cases(last=None):
    if last not in (None,'panel'): raise ValueError('Unknown stage')
    return [spec(h,a,f) for f in (False,True) for h in HISTORIES for a in ARMS]
def random_word(i):
    return int.from_bytes(hashlib.sha256(('P14_tissue_persistence_v1|401|turnover|%d'%i).encode('ascii')).digest()[:8],'big')
def expected_draws(): return {'401':{'turnover':['%016x'%random_word(i) for i in range(3)]}}
def incoming(M,i):
    x=M.copy(); delta=random_word(i)*51//(1<<64)-25
    # Same prescribed multiplication order as the recorded input generation.
    x[7,0]=M[7,0]*(1+delta/100)
    return x
def base_time(c): return 0 if c['history']=='fresh_M' else 1020000
def source(c):
    h=c['history']
    if h=='fresh_M': return None,None,['p14:fresh_M:ordinary_M:%02d'%i for i in range(3)]
    name='returns__%s__301__open'%h+('__fine' if c['fine'] else '')
    return name,'r09_isolated_2',['p13:%s:301:pupil:09:%02d'%(h,i) for i in range(3)]
def tissue_ids(c,ids):
    result=['p14:%s:background:%03d'%(c['history'],i) for i in range(169)]
    for pos,name in zip(PATCH,ids): result[pos]=name
    return result
def new_id(c,i): return 'p14:%s:replacement:%02d'%(c['history'],i)
def stock(run,fine):
    x=arrays(run/'inputs/p13/inputs/p12/inputs/p11'/('stock'+('__fine' if fine else '')),'preparation')['final']
    return x[:,168:169],x[:,1:2]

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

def descriptor(name,ids,base,span,arm='sham',isolated=False):
    shape=[1,3] if isolated else [13,13]; fr,to=edges(shape)
    if isolated:
        internal,boundary,power,kd,cut=1,1,1,0,False
        regions=np.zeros(len(fr),dtype=np.int8)
    else:
        settings={'sham':(60,1,1.25e-14,False),'internal':(1,1,1.25e-14,False),
                  'boundary':(60,60,1.25e-14,False),'both':(1,60,1.25e-14,False),
                  'rna':(1,60,0,False),'cut':(1,60,1.25e-14,True)}
        internal,boundary,kd,cut=settings[arm]; power=60
        membership=np.isin(np.arange(169),PATCH)
        regions=np.where(membership[fr]&membership[to],1,np.where(membership[fr]^membership[to],2,0)).astype(np.int8)
    powers=np.choose(regions,[power,internal,boundary]).astype(float)
    available=np.where((regions==2)&cut,0.,1.)
    return dict(name=name,ids=ids.copy(),shape=shape,base=base,horizon=span,graph=False,
        power=power,kd=kd,isolated=isolated,fr=fr,to=to,regions=regions,powers=powers,available=available,
        compartments=dict(internal=internal,boundary=boundary,helper=power,boundary_cut=cut))

class Reader(p12.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}
        self.environment=arrays(folder.parent/'inputs/p13/inputs/p12/inputs/p11'/
            ('stock'+('__fine' if c['fine'] else '')),'preparation')['environment']
    def finish(self,out):
        self.ck('exact_raw_inventory',{p.stem for p in self.folder.glob('*.npz')}=={p['phase'] for p in self.records})
        return super().finish(out)

def observation(data,tissue=True):
    end=labels(data['final'],INDEX); values=labels(data['concentrations'],INDEX)
    positions=list(PATCH) if tissue else [0,1,2]
    late=values[data['times']>=.75*data['times'][-1]]
    result=dict(patch_labels=''.join(end[positions]))
    for lab in ('E','M'):
        result['stable_'+lab]=((end[positions]==lab)&(np.mean(late[:,positions]==lab,axis=0)>=.95)).tolist()
    if tissue:
        result.update(background_E_now_M=int(np.count_nonzero(end[list(BACKGROUND)]=='M')),
            maximum_background_E_now_M=int(np.max(np.count_nonzero(values[:,list(BACKGROUND)]=='M',axis=1))),
            competitor_labels=''.join(end[list(COMPETITORS)]))
    return result

def branch(folder,c,checks):
    run=folder.parent; rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve',
        'only_new_cells_perturbed','shared_audited_stock')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('benchmark_prior_age_matched',
        'autonomous_reproduction','parameter_retuning','outcome_dependent_cell_selection','carrier_reset',
        'cross_branch_pooling','intervention_retained','cell_division_simulated','new_isolated_PH_handover',
        'exact_paper_replication','independent_biological_replicates','automatic_follow_on')))
    rd.ck('ancestry',result.get('actual_P13_descendants')==(c['history']!='fresh_M') and
        result.get('historical_rounds')==(0 if c['history']=='fresh_M' else 9))
    E,M=stock(run,c['fine']); src,phase,carrier_ids=source(c); base=base_time(c)
    carry=np.repeat(M,3,axis=1) if src is None else arrays(run/'inputs/p13'/src,phase)['final']
    if src is not None:
        row=json.loads((run/'inputs/p13'/src/'result.json').read_text())
        record=next(p for p in row['phases'] if p['phase']==phase)
        rd.ck('actual_source',record['setup']['cell_ids']==carrier_ids and record['logical_interval']==[1010000,1020000])
    rd.ck('source_M',''.join(labels(carry,INDEX))=='MMM')
    ids=tissue_ids(c,carrier_ids); state=np.repeat(E,169,axis=1)
    state[:,list(COMPETITORS)]=np.repeat(M,9,axis=1); state[:,list(PATCH)]=carry
    observed={}; replacements=[]
    def take(name,span,start,value,arm='sham',isolated=False):
        x=rd.take(descriptor(name,ids,base+start,span,arm,isolated),value)
        observed[name]=observation(rd.data[name],not isolated)
        return x
    state=take('intervention',20000,0,state,c['arm'])
    state=take('withdrawal_1',10000,20000,state)
    state=take('withdrawal_2',10000,30000,state)
    for i,pos in enumerate(PATCH):
        initial=incoming(M,i); lab=str(labels(initial,INDEX)[0])
        rd.ck('replacement_%d_initial_M'%(i+1),lab=='M')
        removed=ids[pos]; ids[pos]=new_id(c,i); state=state.copy(); state[:,pos:pos+1]=initial
        state=take('replacement_'+str(i+1),20000,40000+20000*i,state)
        replacements.append(dict(position=pos,removed=removed,inserted=ids[pos],initial_label=lab,
            stable_E=observed['replacement_'+str(i+1)]['stable_E']))
    rd.ck('all_originals_removed',not set(carrier_ids)&set(ids))
    state=state[:,list(PATCH)]; ids=[ids[i] for i in PATCH]
    state=take('isolated_1',10000,100000,state,isolated=True)
    state=take('isolated_2',10000,110000,state,isolated=True)
    corrected=observed['intervention']['patch_labels']=='EEE'
    persistent=all(all(observed[n]['stable_E']) for n in ('withdrawal_1','withdrawal_2'))
    replaced=all(all(x['stable_E']) for x in replacements)
    isolated=all(all(observed[n]['stable_E']) for n in ('isolated_1','isolated_2'))
    out=dict(available=True,observations=observed,replacements=replacements,
        corrected_at_intervention_end=corrected,persistent_after_withdrawal=persistent,
        lost_stable_correction=corrected and not persistent,
        M_return_after_withdrawal=corrected and 'M' in observed['withdrawal_2']['patch_labels'],
        all_replacements_corrected=replaced,isolated_E_memory=isolated,
        tissue_correction=persistent and replaced and isolated,logical_end=base+120000)
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
    checks.add('draw_book',json.loads((run/'frozen/paper_tissue_persistence_draws_v1.json').read_text())==expected_draws())
    checks.add('call_ceiling',calls==288)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality),checks=checks.rows,
        integrity=provenance,branches=branches,fine_comparisons=fine,integration_calls=calls,
        cumulative_cases=len(branches),eligibility_means_technical_permission_only=True)

def predecessor_audit(run):
    original=p13.analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p13/independent_audit.json').read_text())
    archived=p13.analyze(run/'inputs/p13'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==63744
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],actual_round_nine_sources=True)

def contrasts(by):
    comparisons=[]; mechanism=[]
    for h in HISTORIES:
        for arm in ARMS:
            pair=[by.get(spec(h,arm,f)['id'],{}) for f in (False,True)]
            sham=[by.get(spec(h,'sham',f)['id'],{}) for f in (False,True)]
            comparisons.append(dict(history=h,arm=arm,source_trials=1,
                tissue_correction_both=all(o.get('tissue_correction',False) for o in pair),
                withdrawal_persistence_both=all(o.get('persistent_after_withdrawal',False) for o in pair),
                better_than_sham_both=all(o.get('tissue_correction',False) and not s.get('tissue_correction',False)
                                          for o,s in zip(pair,sham))))
        active=[by.get(spec(h,'both',f)['id'],{}) for f in (False,True)]
        controls=[by.get(spec(h,arm,f)['id'],{}) for f in (False,True) for arm in ('sham','rna','cut')]
        available=all(x.get('available',False) for x in active+controls)
        negative=available and all(not x['persistent_after_withdrawal'] for x in controls)
        positive=all(x.get('tissue_correction',False) for x in active)
        mechanism.append(dict(history=h,available=available,controls_without_persistence=negative,
                              provisional_both_mechanism_support=available and negative and positive))
    return comparisons,mechanism

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_tissue_persistence_v1.json').read_text()))
    checks.add('registration',summary['registered_cases']==expected_cases())
    stages=summary.get('attempted_stages',[])
    checks.add('all_stages',stages==list(STAGES))
    history=predecessor_audit(run)
    checks.add('predecessor_fresh',history['quality_gate'] and history==summary['predecessor_audit'])
    reports={}
    for stage in stages:
        report=stage_audit(run,stage); reports[stage]=report
        checks.add(stage+'/quality',report['quality_gate'])
        checks.add(stage+'/saved',report==summary['gates'][stage]==json.loads((run/(stage+'_audit.json')).read_text()) and
            d.digest(run/(stage+'_audit.json'))==summary['gate_hashes'][stage])
    if not stages: return dict(quality_gate=False,checks=checks.rows)
    final=reports[stages[-1]]; cases=expected_cases()
    checks.add('case_count',len(summary['cases'])==len(cases) and {r['id'] for r in summary['cases']}=={c['id'] for c in cases})
    checks.add('gates',set(summary['gates'])==set(summary['gate_hashes'])==set(stages))
    checks.add('runner_pass',summary.get('all_execution_valid') is True)
    checks.add('valid_stop',summary.get('completion_reason')=='all_registered_stages_completed')
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    by={b['case']['id']:b['outcome'] for b in final['branches']}
    comparisons,mechanism=contrasts(by)
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,
        stages=reports,completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],
        completion_reason=summary.get('completion_reason'),fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),comparisons=comparisons,mechanism_contrasts=mechanism,external_schedule=True,autonomous_reproduction=False,
        reused_P13_ancestry=True,independent_biological_replicates=False,unique_PH_demonstrated=False,
        benchmark_prior_age_matched=False,new_isolated_PH_handover=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count',
          'all_fine_agree','comparisons','mechanism_contrasts','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2))
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())
