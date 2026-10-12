"""P21 three-block factorial in the two individually sufficient P20 cell routes."""
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p20_preparation_localization_v2'))
import p20_design as prior

digest,write_json,source_check=prior.digest,prior.write_json,prior.source_check
read,REVISION,STORE,recovery=prior.read,prior.REVISION,prior.STORE,prior.recovery
BASE=STORE/'p21-preparation-components'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P20_JOB=STORE/'p20-preparation-localization-v2/jobs/p20-20260924T131555Z-cw30_ccr'
P20_RUN=STORE/'p20-preparation-localization-v2/runs/p20-20260924T131753Z-zojusn62'
HERE=ROOT/'p21_preparation_components'
FILES=[ROOT/'PAPER_PREPARATION_COMPONENTS_PROTOCOL.md']+[HERE/n for n in
    ('p21_design.py','run_p21.py','analyze_p21.py','supervise_p21.py','test_p21.py','config.json')]
STAGES=('controls','components','onward'); FOUNDERS=('written','ordinary'); TARGETS=('newcomer','neighbour')
READOUTS=('open','rna','cut'); BLOCKS=(('protein',1,[7]),('rna',2,[5,6]),('ions',4,[0,1,2,3]))
FIXED=dict(experiment='P21_preparation_components',revision=REVISION,predecessor_run=str(P20_RUN),predecessor_job=str(P20_JOB),
    founders=list(FOUNDERS),targets=dict(newcomer=0,neighbour=2),blocks={n:dict(bit=b,rows=r) for n,b,r in BLOCKS},
    masks=list(range(8)),shared_mask_zero=True,historical_controls=['none','newcomer','neighbour'],
    source_extra_interval=200,source_preparation='isolated',common_logical_start=1180300,
    refresh='native_noniterative_all_columns_once_before_turnover',refresh_rows=list(range(8,16)),
    primary_rows=list(range(8))+[16],discarded_column=1,replacements=[1,2,0,1,2],later_interval=300,
    isolation_horizons=[10000,10000],readout_horizon=20000,readouts=list(READOUTS),incoming_seed=501,
    incoming_draw_namespace='P16_turnover_limit_v1',workers=2,maximum_cases=288,maximum_integrations=1152,
    numerical_pairs=144,renewal_parents=72,worker_timeout_seconds=21600,total_budget_seconds=86400,
    verification_timeout_seconds=7200,audit_timeout_seconds=21600,overall_timeout_seconds=129600,
    power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],minimum_free_gib=5,external_store=str(BASE),
    archive_mode='reference_directory_v1',external_schedule=True,automatic_follow_on=False,outcome_dependent_selection=False)

def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P21 configuration')
    return value

def case(stage='components',founder='written',kind='component',target='newcomer',mask=1,readout='',fine=False):
    if stage!='onward': stage='controls' if kind=='historical' or mask in (0,7) else 'components'
    if mask==0: target='none'
    name='__'.join([stage,founder,kind,target,str(mask)]+([readout] if readout else []))
    return dict(id=name+('__fine' if fine else ''),stage=stage,founder=founder,kind=kind,target=target,mask=mask,readout=readout,fine=fine)

def conditions():
    return [('historical','none',0),('historical','newcomer',7),('historical','neighbour',7),
        ('component','none',0)]+[('component',t,m) for t in TARGETS for m in range(1,8)]
def stage_cases(stage):
    if stage not in STAGES: raise ValueError('Unknown P21 stage')
    rows=[case('onward' if stage=='onward' else 'components',h,k,t,m,q,f)
        for f in (False,True) for h in FOUNDERS for k,t,m in conditions()
        for q in (READOUTS if stage=='onward' else ('',))]
    return [c for c in rows if c['stage']==stage]
def fixed_cases(): return [c for s in STAGES for c in stage_cases(s)]
def parent(c): return case('components',c['founder'],c['kind'],c['target'],c['mask'],fine=c['fine'])
def source(c):
    target=c['target'] if c['kind']=='historical' else 'none'
    return prior.case(founder=c['founder'],newcomer='after' if target=='newcomer' else 'before',
        neighbours='after' if target=='neighbour' else 'before',fine=c['fine'])['id']
def control_source(c):
    return prior.case('onward' if c['stage']=='onward' else 'renewal',c['founder'],
        'after' if c['target']=='newcomer' else 'before','after' if c['target']=='neighbour' else 'before',
        c['readout'],c['fine'])['id']
def replay(c): return 'p20/'+control_source(c) if c['kind']=='historical' else None
def stem(c): return 'p21:%s:%s:%s:%d'%(c['founder'],c['kind'],c['target'],c['mask'])
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
incoming=prior.incoming

def manifest():
    result=prior.manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe source path')
    return result

def inherited_verification():
    prior.verify_launch(P20_JOB); s=read(P20_JOB/'status.json'); a=read(P20_RUN/'independent_audit.json')
    log=digest(P20_JOB/'verification.log')
    if not (s['phase']=='complete' and s['exit_code']==s['runner_exit_code']==s['audit_exit_code']==s['verification_exit_code']==0
        and s['run']==str(P20_RUN) and s['quality_gate'] and a['quality_gate'] and a['completed_cases']==64
        and a['integration_calls']==256 and a['independent_check_count']==21938 and len(a['fine_comparisons'])==32
        and a['all_fine_agree'] and log==s['verification_log_sha256']=='8c12000b372dc5b960b56974005a0407311fb9f11e10af2ead6a31c279a1fe2e'
        and 'Ran 42 tests in 91.068s\n\nOK\n' in (P20_JOB/'verification.log').read_text()):
        raise RuntimeError('Completed P20 evidence changed')
    return dict(legacy=prior.inherited_verification(),p20=dict(job=str(P20_JOB),tests=42,seconds=91.068,
        log_sha256=log,inherited_unchanged=True),new_full_legacy_regression_run=False)

def input_paths():
    s=read(P20_RUN/'summary.json')
    names=['summary.json','independent_audit.json','predecessor_audit.json','renewal_audit.json','onward_audit.json']
    names+=['frozen/'+p for p in s['hashes_sha256']]+['inputs/'+p for p in s['inputs']]
    for row in s['cases']:
        if not row['execution_pass']: raise ValueError('Invalid P20 predecessor')
        names+=[row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if row['result']['case']['stage']=='renewal': names+=[row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    if len(names)!=len(set(names)): raise ValueError('Duplicate archive paths')
    result={'p20/'+n:P20_RUN/n for n in names}
    result.update({'p20_job/'+n:P20_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    return result

def space_available(path): return shutil.disk_usage(path).free>=5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p21-'): raise ValueError('P21 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def archive_view(run):
    (run/'inputs').mkdir()
    (run/'inputs/p20').symlink_to(P20_RUN,target_is_directory=True)
    (run/'inputs/p20_job').symlink_to(P20_JOB,target_is_directory=True)
def input_manifest():
    return {n:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for n,p in input_paths().items()}
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=inherited_verification(): raise RuntimeError('P21 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P21 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P21 input manifest changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(Path(v['source']))==v['sha256'] for v in i.values()),
            archive_bytes=all(digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            referenced_inputs=all(v.get('storage')=='reference_directory_v1' and os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()),
            directory_views=all((run/'inputs'/n).is_symlink() and (run/'inputs'/n).resolve()==p for n,p in (('p20',P20_RUN),('p20_job',P20_JOB))),
            inherited_verification=summary['inherited_verification']==inherited_verification())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
