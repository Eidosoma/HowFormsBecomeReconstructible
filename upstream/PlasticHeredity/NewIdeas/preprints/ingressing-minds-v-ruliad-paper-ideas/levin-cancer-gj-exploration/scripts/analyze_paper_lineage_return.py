"""Independent P13 audit: actual ancestry, second rewrite and three new handovers."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import paper_lineage_return_design as d
import analyze_paper_lineage_robustness as p12
from analyze_paper_memory import Checks,labels
from analyze_paper_restoration import stable
from analyze_paper_sheet import arrays

INDEX=p12.INDEX
STAGES=('benchmarks','returns','writing_controls','relay_controls')
HISTORIES=('written','ordinary')
SEEDS=(301,302,303)
WRITING_CONTROLS=('rna','cut','sham','none')

def spec(stage,history='written',seed=301,route='open',fine=False):
    fields=(stage,history,str(seed),route)
    return dict(id='__'.join(fields)+('__fine' if fine else ''),stage=stage,history=history,seed=seed,route=route,fine=fine)

def expected_stage(stage):
    result=[]
    for fine in (False,True):
        histories=('benchmark',) if stage=='benchmarks' else ('benchmark',)+HISTORIES if stage=='relay_controls' else HISTORIES
        routes=WRITING_CONTROLS if stage=='writing_controls' else ('rna','cut') if stage=='relay_controls' else ('open',)
        result += [spec(stage,h,s,r,fine) for h in histories for s in SEEDS for r in routes]
    return result

def expected_cases(last=None):
    stages=STAGES if last is None else STAGES[:STAGES.index(last)+1]
    return [c for stage in stages for c in expected_stage(stage)]

def random_word(seed,role,index):
    message='P13_lineage_return_v1|%d|%s|%d'%(seed,role,index)
    return int.from_bytes(hashlib.sha256(message.encode('ascii')).digest()[:8],'big')

def expected_draws():
    domains=['timing:r%02d'%n for n in (7,8,9)]+['protein:benchmark']+['protein:r%02d'%n for n in (7,8,9)]
    return {str(s):{key:['%016x'%random_word(s,key,i) for i in range(3)] for key in domains} for s in SEEDS}

def schedule(seed,number):
    gaps=[(random_word(seed,'timing:r%02d'%number,i)*51//(1<<64))*100 for i in range(3)]
    contacts=[(sum(gaps[:i+1])+20000*i,sum(gaps[:i+1])+20000*(i+1),[i]) for i in range(3)]
    boundaries=sorted({0,80000}|{t for start,end,_ in contacts for t in (start,end)})
    return [(start,end,next((active for lo,hi,active in contacts if lo<=start and end<=hi),[]))
            for start,end in zip(boundaries,boundaries[1:])]

def incoming(reference,seed,role):
    value=np.repeat(reference,3,axis=1)
    for i in range(3):
        percent=random_word(seed,'protein:'+role,i)*51//(1<<64)-25
        value[7,i]=value[7,i]*(1+percent/100)
    return value

def root_id(c): return 'p13:%s:%d'%(c['history'],c['seed'])
def founders(c): return [root_id(c)+':founder:%02d'%i for i in range(3)]
def pupils(c,n): return [root_id(c)+':pupil:%02d:%02d'%(n,i) for i in range(3)]
def source(c):
    name='combined__%d__%s__open'%(c['seed']-100,c['history'])+('__fine' if c['fine'] else '')
    ids=['p12:combined:%s:%d:pupil:06:%02d'%(c['history'],c['seed']-100,i) for i in range(3)]
    return name,'r06_isolated_2',ids
def parent(c): return spec('benchmarks' if c['history']=='benchmark' else 'returns',c['history'],c['seed'],fine=c['fine'])
def base_time(c): return 0 if c['history']=='benchmark' else 680000

def stock(run,fine):
    x=arrays(run/'inputs/p12/inputs/p11'/('stock'+('__fine' if fine else '')),'preparation')['final']
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

def descriptor(name,ids,base,span,*,mode=None,graph=False,active=(),route='open'):
    cue=mode is not None and mode not in ('age','none')
    value=p12.descriptor(name,ids,base,span,graph=graph,active=active,route=route,
        cue=cue,nocue=mode=='none',age=mode=='age')
    if cue and mode=='rna': value['kd']=0
    if cue and mode=='cut':
        value['available']=np.where(value['regions']==2,0.,1.)
        value['compartments']['boundary_cut']=True
    return value

class Reader(p12.Reader):
    def __init__(self,folder,c,checks):
        self.folder,self.c,self.checks=folder,c,checks
        self.result=json.loads((folder/'result.json').read_text()); self.records=self.result['phases']
        self.at=0; self.data={}
        witness=arrays(folder.parent/'inputs/p12/inputs/p11'/('stock'+('__fine' if c['fine'] else '')),'preparation')
        self.environment=witness['environment']
    def finish(self,out):
        self.ck('exact_raw_inventory',{p.stem for p in self.folder.glob('*.npz')}=={p['phase'] for p in self.records})
        return super().finish(out)

def writer(rd,targets,ids,E,M,mode,base):
    nocue=mode in ('age','none')
    cues=[root_id(rd.c)+':writing:cue:%02d'%i for i in range(6)]
    value=targets if nocue else np.concatenate((np.repeat(E if mode=='sham' else M,6,axis=1),targets),axis=1)
    contact=rd.take(descriptor('writing_contact',ids if nocue else cues+ids,base,20000,mode=mode),value)
    value=rd.take(descriptor('writing_isolated_1',ids,base+20000,10000),contact if nocue else contact[:,6:])
    value=rd.take(descriptor('writing_isolated_2',ids,base+30000,10000),value)
    masks=rd.masks('writing_')
    return value,dict(retained_E=masks['E'],retained_M=masks['M'],qualified=all(masks['M']))

def handover(rd,carry,ids,E,number,route,base):
    c=rd.c; prefix='r%02d_'%number; fresh=pupils(c,number)
    initial=incoming(E,c['seed'],'r%02d'%number); initial_labels=''.join(labels(initial,INDEX))
    value=np.concatenate((carry,initial),axis=1); presignal=[None]*3
    for slot,(start,end,active) in enumerate(schedule(c['seed'],number),1):
        for i in active:
            if presignal[i] is None: presignal[i]=str(labels(value[:,3+i:4+i],INDEX)[0])
        value=rd.take(descriptor(prefix+'segment_%02d'%slot,ids+fresh,base+start,end-start,
            graph=True,active=active,route=route),value)
    value=rd.take(descriptor(prefix+'isolated_1',fresh,base+80000,10000),value[:,3:])
    value=rd.take(descriptor(prefix+'isolated_2',fresh,base+90000,10000),value)
    masks=rd.masks(prefix)
    return value,fresh,dict(round=number,desired='M',retained_E=masks['E'],retained_M=masks['M'],
        initial_labels=initial_labels,presignal_labels=''.join(presignal),
        complete=all(masks['M']) and initial_labels=='EEE' and presignal==['E']*3,
        negative=all(masks['E']),logical_end=base+100000)

def parent_qualified(folder):
    one,two=(folder/(name+'.npz') for name in ('writing_isolated_1','writing_isolated_2'))
    if not (one.exists() and two.exists()): return False
    return bool(stable(arrays(folder,'writing_isolated_1'),arrays(folder,'writing_isolated_2'),INDEX,'M').all())

def branch(folder,c,checks):
    run=folder.parent; rd=Reader(folder,c,checks); result=rd.result
    rd.ck('case',result['case']==c and result['execution_pass'] is True)
    rd.ck('clock',result['clock_method']=='native_explicit_euler_bounded_clock_v1')
    rd.ck('positive_scope',all(result.get(k) is True for k in ('external_schedule','all_cells_evolve',
        'only_new_cells_perturbed','shared_audited_stock')))
    rd.ck('negative_scope',all(result.get(k) is False for k in ('benchmark_prior_age_matched',
        'autonomous_reproduction','parameter_retuning','outcome_dependent_cell_selection','carrier_reset',
        'cross_branch_pooling','cues_retained','independent_biological_replicates','automatic_follow_on')))
    rd.ck('ancestry',result.get('inherited_P12_ancestry')==(c['history']!='benchmark') and
        result.get('historical_rounds')==(0 if c['history']=='benchmark' else 6))
    E,M=stock(run,c['fine']); base=base_time(c)
    if c['stage']=='relay_controls':
        par=parent(c); parfolder=run/par['id']
        if not parent_qualified(parfolder):
            return rd.finish(dict(available=False,rounds=[],negative=False,skip_reason='parent_writing_unqualified'))
        carry=arrays(parfolder,'writing_isolated_2')['final']
        ids=founders(c) if c['history']=='benchmark' else source(c)[2]
        _,_,row=handover(rd,carry,ids,E,7,c['route'],base+40000)
        return rd.finish(dict(available=True,rounds=[row],negative=row['negative']))
    if c['stage']=='benchmarks':
        carry=incoming(M,c['seed'],'benchmark'); ids=founders(c); mode='age'
    else:
        src,name,ids=source(c); srcfolder=run/'inputs/p12'/src
        carry=arrays(srcfolder,name)['final']; mode=c['route']
        rec=next(p for p in json.loads((srcfolder/'result.json').read_text())['phases'] if p['phase']==name)
        rd.ck('actual_P12_source',rec['setup']['cell_ids']==ids and rec['logical_interval']==[670000,680000])
        rd.ck('source_E',''.join(labels(carry,INDEX))=='EEE')
    carry,w=writer(rd,carry,ids,E,M,mode,base)
    if c['stage']=='writing_controls':
        return rd.finish(dict(available=True,writing=w,rounds=[],negative=all(w['retained_E'])))
    rounds=[]; out=dict(available=True,writing=w,rounds=rounds,complete=False,stop_reason='writer_not_M')
    if not w['qualified']: return rd.finish(out)
    for number in (7,8,9):
        carry,ids,row=handover(rd,carry,ids,E,number,'open',base+40000+(number-7)*100000)
        rounds.append(row); out['stop_reason']='round_%d_incomplete'%number
        if not row['complete']: return rd.finish(out)
    out.update(complete=True,stop_reason='three_return_handovers_complete')
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
    checks.add('draw_book',json.loads((run/'frozen/paper_lineage_return_draws_v1.json').read_text())==expected_draws())
    checks.add('call_ceiling',calls<=1008)
    provenance=integrity(run,summary); quality=all(checks.rows.values()) and all(provenance.values())
    return dict(stage=stage,quality_gate=bool(quality),eligible=bool(quality),checks=checks.rows,
        integrity=provenance,branches=branches,fine_comparisons=fine,integration_calls=calls,
        cumulative_cases=len(branches),eligibility_means_technical_permission_only=True)

def predecessor_audit(run):
    original=p12.analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p12/independent_audit.json').read_text())
    archived=p12.analyze(run/'inputs/p12'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==110444
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],actual_round_six_sources=True)

def trial_counts(by):
    trials=[]; counts=[]; benchmarks=[]
    for seed in SEEDS:
        main=[spec('benchmarks','benchmark',seed,fine=f) for f in (False,True)]
        ctrls=[spec('relay_controls','benchmark',seed,r,f) for f in (False,True) for r in ('rna','cut')]
        raw=all(by.get(c['id'],{}).get('complete',False) for c in main)
        good=all(by.get(c['id'],{}).get('available',False) and by[c['id']].get('negative',False) for c in ctrls)
        benchmarks.append(dict(seed=seed,raw_success_both=raw,controls_qualified=good,qualified=raw and good))
    for history in HISTORIES:
        for seed in SEEDS:
            main=[spec('returns',history,seed,fine=f) for f in (False,True)]
            ctrls=[spec('writing_controls',history,seed,r,f) for f in (False,True) for r in WRITING_CONTROLS]
            ctrls += [spec('relay_controls',history,seed,r,f) for f in (False,True) for r in ('rna','cut')]
            raw=all(by.get(c['id'],{}).get('complete',False) for c in main)
            available=all(by.get(c['id'],{}).get('available',False) for c in ctrls)
            negative=all(by.get(c['id'],{}).get('negative',False) for c in ctrls)
            qualified=raw and available and negative
            benchmark=next(b['qualified'] for b in benchmarks if b['seed']==seed)
            trials.append(dict(history=history,source_seed=seed-100,challenge_seed=seed,raw_success_both=raw,
                controls_available_both=available,controls_negative_both=negative,control_qualified=qualified,
                benchmark_qualified=benchmark,benchmark_supported=qualified and benchmark,
                stop_reasons=[by.get(c['id'],{}).get('stop_reason','not_run') for c in main]))
        rows=[r for r in trials if r['history']==history]
        counts.append(dict(history=history,prior_lineages=3,raw_successes=sum(r['raw_success_both'] for r in rows),
            control_qualified_successes=sum(r['control_qualified'] for r in rows),
            benchmark_supported_successes=sum(r['benchmark_supported'] for r in rows)))
    return trials,counts,benchmarks

def analyze(run):
    run=Path(run); summary=json.loads((run/'summary.json').read_text()); checks=Checks()
    checks.add('config',summary['config']==d.FIXED==json.loads((run/'frozen/paper_lineage_return_v1.json').read_text()))
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
    trials,counts,benchmarks=trial_counts(by)
    return dict(run=str(run),quality_gate=bool(quality),ready_for_interpretation=bool(quality),checks=checks.rows,
        independent_check_count=len(checks.rows)+len(final['checks']),integrity=provenance,predecessor=history,
        stages=reports,completed_cases=len(summary['cases']),integration_calls=final['integration_calls'],
        completion_reason=summary.get('completion_reason'),fine_comparisons=final['fine_comparisons'],
        all_fine_agree=all(p['agree'] for p in final['fine_comparisons']),trials=trials,trial_counts=counts,
        benchmarks=benchmarks,external_schedule=True,autonomous_reproduction=False,
        reused_P12_ancestry=True,independent_biological_replicates=False,unique_PH_demonstrated=False,
        benchmark_prior_age_matched=False,hidden_ancestral_memory_demonstrated=False,automatic_follow_on=False)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run',type=Path)
    p.add_argument('--save',action='store_true'); p.add_argument('--compact',action='store_true'); args=p.parse_args()
    result=analyze(args.run.resolve())
    if args.save: d.write_json(args.run/'independent_audit.json',result)
    keys=('quality_gate','completed_cases','integration_calls','independent_check_count',
          'all_fine_agree','trial_counts','benchmarks','completion_reason')
    print(json.dumps({k:result.get(k) for k in keys} if args.compact else result,indent=2))
    return 0 if result['quality_gate'] else 1

if __name__=='__main__': raise SystemExit(main())


