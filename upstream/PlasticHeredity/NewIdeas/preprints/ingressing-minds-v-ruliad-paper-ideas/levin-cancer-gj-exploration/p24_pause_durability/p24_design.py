"""Fixed P24 early-pause durability panel and verified historical evidence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p23_pause_transmission'))
import p23_design as prior

digest,source_check,read=prior.digest,prior.source_check,prior.read
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
BASE=STORE/'p24-pause-durability'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P23_JOB=STORE/'p23-pause-transmission/jobs/p23-20260928T192419Z-h5hjj1az'
P23_RUN=STORE/'p23-pause-transmission/runs/p23-20260928T192742Z-pjtd6x7t'
HERE=ROOT/'p24_pause_durability'
FILES=[ROOT/'PAPER_PAUSE_DURABILITY_PROTOCOL.md']+[HERE/n for n in
    ('p24_design.py','run_p24.py','analyze_p24.py','supervise_p24.py','test_p24.py','config.json','draws.json')]
STAGES=('controls','renewal','onward'); FOUNDERS=('written','ordinary'); READOUTS=('open','rna','cut')
DRAWS=('legacy','heldout_17021','heldout_17022','new_24001'); CONDITIONS=('baseline','early_pause')
ROUTES={'none':(None,[])}
P21_PREFIX='p23/inputs/p22/inputs/p21/'
PINS={'summary.json':'bd567c30076485f2657b106802a9ead1c42c0a72f5bca1c448ae42cba7f08fd2',
    'independent_audit.json':'588ac18b8ba8fa041c15369f537ac1535b6c493aa12bc1483998fb620a5c3195'}
STATUS_PIN='1025340506f1e1ad6156a11b42772834a68680dda31c66bc99df5b6e947c7c1d'
LOG_PIN='61d4ca7c02dbcdef183f3abba9bb7dfdc2a350643a5f8d746bdaec32869d4aad'
FIXED=dict(experiment='P24_pause_durability',revision=REVISION,predecessor_run=str(P23_RUN),predecessor_job=str(P23_JOB),
    founders=list(FOUNDERS),conditions=list(CONDITIONS),draws=list(DRAWS),new_seed=24001,new_namespace='P24_incoming_v1',
    draw_count=11,incoming_protein_percent_range=[-25,25],renewal_lengths=[5,11],common_logical_start=1180300,
    first_challenge_boundaries=[0,100,200,300],common_sample_times=list(range(0,301,15)),later_interval=300,
    native_binding_refresh='noniterative_all_columns_once',primary_rows=list(range(8))+[16],refresh_rows=list(range(8,16)),
    readouts=list(READOUTS),hold_horizons=[10000,10000],readout_horizon=20000,
    maximum_cases=268,maximum_integrations=1380,numerical_pairs=134,renewal_parents=64,readout_cases=204,
    power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],workers=2,worker_timeout_seconds=21600,
    total_budget_seconds=108000,verification_timeout_seconds=7200,audit_timeout_seconds=14400,overall_timeout_seconds=129600,
    minimum_free_gib=5,external_store=str(BASE),archive_mode='reference_directory_v1',external_schedule=True,
    historical_audit_policy='pinned_completed_evidence_and_all_input_hashes_v1',historical_mathematical_audit_repeated=False,
    json_serialization='compact_atomic_v1',primary_state_edits_at_assembly=False,repeated_pause=False,
    outcome_dependent_selection=False,automatic_follow_on=False)

def write_json(path,value):
    path=Path(path); temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n'); temporary.replace(path)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P24 configuration')
    return value
def case(founder='written',condition='early_pause',draw='legacy',replacements=5,readout='',fine=False):
    stage='controls' if condition=='reference' else 'onward' if readout else 'renewal'
    parts=[stage,founder,condition,draw,str(replacements)]+([readout] if readout else [])
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,condition=condition,
        panel='reference' if condition=='reference' else 'timing' if condition=='early_pause' else 'timing_controls',
        route='newcomer_protein' if condition=='reference' else 'none',window='rna_early' if condition=='early_pause' else 'open',
        draw=draw,replacements=replacements,readout=readout,fine=fine)
def stage_cases(stage):
    if stage=='controls': return [case(h,'reference',readout=q,fine=f) for f in (False,True) for h in FOUNDERS for q in READOUTS]
    if stage=='renewal': return [case(h,k,draw,n,fine=f) for f in (False,True) for h in FOUNDERS for k in CONDITIONS for draw in DRAWS for n in (5,11)]
    if stage=='onward': return [case(c['founder'],c['condition'],c['draw'],c['replacements'],q,c['fine']) for c in stage_cases('renewal') for q in READOUTS]
    raise ValueError('Unknown P24 stage')
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case(c['founder'],c['condition'],c['draw'],c['replacements'],fine=c['fine'])
def stem(c): return 'p24:'+':'.join(str(c[k]) for k in ('founder','condition','draw','replacements'))
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return P21_PREFIX+prior.prior.source(c)
def reference_parent(c):
    old=prior.case(c['founder'],'reference',c['readout'],c['fine'])
    return 'p23/inputs/p22/'+prior.source(old)
def window_routes(c): return ['rna' if c['condition']=='early_pause' else 'open','open','open']
def replay(c):
    if c['condition']=='reference':
        return dict(source='p23/'+prior.case(c['founder'],'reference',c['readout'],c['fine'])['id'],phases=['contact','isolated_1','isolated_2'])
    if c['draw']!='legacy': return None
    if c['readout']:
        return dict(source='p23/'+prior.case(c['founder'],c['condition'],c['readout'],c['fine'])['id'],phases=['contact','isolated_1','isolated_2']) if c['replacements']==5 else None
    old=prior.prior.case(c['panel'],c['founder'],'none',c['window'],fine=c['fine'])
    names=['challenge_%02d'%i for i in (1,2,3)]+['replacement_%02d'%i for i in range(3,7)]
    if c['replacements']==5: names+=['isolated_1','isolated_2']
    return dict(source='p23/inputs/p22/'+old['id'],phases=names)
def random_word(draw,event):
    if draw not in DRAWS or event not in range(1,12): raise ValueError('Unregistered incoming word')
    if draw!='new_24001': return prior.prior.random_word(draw,event)
    return int.from_bytes(hashlib.sha256(('P24_incoming_v1|24001|turnover|%d'%event).encode('ascii')).digest()[:8],'big')
def draw_book(): return {key:['%016x'%random_word(key,i) for i in range(1,12)] for key in DRAWS}
def incoming(M,draw,event):
    value=M.copy(); value[7,0]*=1+(random_word(draw,event)*51//2**64-25)/100; return value

def manifest():
    result=prior.manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe source path')
    return result
def inherited_verification():
    prior.verify_launch(P23_JOB); s=read(P23_JOB/'status.json'); a=read(P23_RUN/'independent_audit.json')
    if not (s['phase']=='complete' and s['exit_code']==s['runner_exit_code']==s['audit_exit_code']==s['verification_exit_code']==0
        and s['run']==str(P23_RUN) and s['quality_gate'] and a['quality_gate'] and a['completed_cases']==48
        and a['integration_calls']==144 and a['independent_check_count']==11827 and len(a['fine_comparisons'])==24
        and a['all_fine_agree'] and digest(P23_JOB/'status.json')==STATUS_PIN
        and all(digest(P23_RUN/n)==h for n,h in PINS.items()) and digest(P23_JOB/'verification.log')==s['verification_log_sha256']==LOG_PIN
        and 'Ran 44 tests in 137.488s\n\nOK\n' in (P23_JOB/'verification.log').read_text()):
        raise RuntimeError('Completed P23 evidence changed')
    return dict(legacy=prior.inherited_verification(),p23=dict(job=str(P23_JOB),tests=44,seconds=137.488,
        log_sha256=LOG_PIN,inherited_unchanged=True),new_full_legacy_regression_run=False)
def input_paths():
    summary=read(P23_RUN/'summary.json'); names=['summary.json','independent_audit.json','predecessor_audit.json']
    names += [stage+'_audit.json' for stage in prior.STAGES]
    names += ['frozen/'+p for p in summary['hashes_sha256']]+['inputs/'+p for p in summary['inputs']]
    for row in summary['cases']:
        if not row['execution_pass']: raise ValueError('Invalid P23 predecessor')
        names += [row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)): raise ValueError('Duplicate archive paths')
    result={'p23/'+n:P23_RUN/n for n in names}
    result.update({'p23_job/'+n:P23_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    return result
def space_available(path): return shutil.disk_usage(path).free>=5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p24-'): raise ValueError('P24 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def archive_view(run):
    (run/'inputs').mkdir()
    (run/'inputs/p23').symlink_to(P23_RUN,target_is_directory=True)
    (run/'inputs/p23_job').symlink_to(P23_JOB,target_is_directory=True)
def input_manifest(): return {n:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for n,p in input_paths().items()}
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=inherited_verification(): raise RuntimeError('P24 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P24 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P24 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P24 draws changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(Path(v['source']))==v['sha256'] for v in i.values()),
            archive_bytes=all(digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            referenced_inputs=all(v.get('storage')=='reference_directory_v1' and os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()),
            directory_views=all((run/'inputs'/n).is_symlink() and (run/'inputs'/n).resolve()==p for n,p in (('p23',P23_RUN),('p23_job',P23_JOB))),
            inherited_verification=summary['inherited_verification']==inherited_verification(),
            incoming_draws=read(HERE/'draws.json')==read(run/'frozen/p24_pause_durability/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
