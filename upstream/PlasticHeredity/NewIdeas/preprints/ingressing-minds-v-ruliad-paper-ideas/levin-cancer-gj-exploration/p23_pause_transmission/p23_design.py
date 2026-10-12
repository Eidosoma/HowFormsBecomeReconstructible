"""Fixed P23 readouts from actual P22 renewed donor groups."""
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p22_rna_timing_robustness'))
import p22_design as prior

digest,write_json,source_check=prior.digest,prior.write_json,prior.source_check
read,REVISION,STORE,recovery=prior.read,prior.REVISION,prior.STORE,prior.recovery
BASE=STORE/'p23-pause-transmission'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P22_JOB=STORE/'p22-rna-timing-robustness/jobs/p22-20260927T175518Z-24c3dtmy'
P22_RUN=STORE/'p22-rna-timing-robustness/runs/p22-20260927T180252Z-fpod_fmq'
HERE=ROOT/'p23_pause_transmission'
FILES=[ROOT/'PAPER_PAUSE_TRANSMISSION_PROTOCOL.md']+[HERE/n for n in
    ('p23_design.py','run_p23.py','analyze_p23.py','supervise_p23.py','test_p23.py','config.json')]
STAGES=('controls','onward'); FOUNDERS=('written','ordinary'); READOUTS=('open','rna','cut')
PARENTS={'reference':('replay','newcomer_protein','open'),'baseline':('timing_controls','none','open'),
    'full_block':('timing','none','rna_full'),'early_pause':('timing','none','rna_early')}
FIXED=dict(experiment='P23_pause_transmission',revision=REVISION,predecessor_run=str(P22_RUN),predecessor_job=str(P22_JOB),
    founders=list(FOUNDERS),parent_routes={k:list(v) for k,v in PARENTS.items()},readouts=list(READOUTS),
    parent_logical_end=1201800,readout_horizon=20000,hold_horizons=[10000,10000],readout_logical_end=1241800,
    maximum_cases=48,maximum_integrations=144,numerical_pairs=24,archived_parents=16,fresh_recipient_placements=144,
    power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],workers=2,worker_timeout_seconds=21600,
    total_budget_seconds=57600,verification_timeout_seconds=7200,audit_timeout_seconds=28800,overall_timeout_seconds=100800,
    minimum_free_gib=5,external_store=str(BASE),archive_mode='reference_directory_v1',external_schedule=True,
    parent_states_edited=False,algebraic_refresh=False,new_renewal_trajectories=False,repeated_pause=False,
    selected_using_prior_results=True,outcome_dependent_selection=False,automatic_follow_on=False)

def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P23 configuration')
    return value
def case(founder='written',condition='early_pause',readout='open',fine=False):
    stage='controls' if condition=='reference' else 'onward'
    return dict(id='__'.join((stage,founder,condition,readout))+('__fine' if fine else ''),
        stage=stage,founder=founder,condition=condition,readout=readout,fine=fine)
def stage_cases(stage):
    if stage not in STAGES: raise ValueError('Unknown P23 stage')
    conditions=('reference',) if stage=='controls' else ('baseline','full_block','early_pause')
    return [case(h,k,q,f) for f in (False,True) for h in FOUNDERS for k in conditions for q in READOUTS]
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c):
    panel,route,window=PARENTS[c['condition']]
    return prior.case(panel,c['founder'],route,window,fine=c['fine'])
def source(c): return parent(c)['id']
def pupils(c): return ['p23:%s:%s:pupil:%02d'%(c['founder'],c['condition'],i) for i in range(3)]
def replay(c):
    if c['condition']!='reference': return None
    return dict(source='p22/'+prior.case('replay',c['founder'],'newcomer_protein',readout=c['readout'],fine=c['fine'])['id'],
        phases=['contact','isolated_1','isolated_2'])

def manifest():
    result=prior.manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe source path')
    return result
def inherited_verification():
    prior.verify_launch(P22_JOB); s=read(P22_JOB/'status.json'); a=read(P22_RUN/'independent_audit.json'); log=digest(P22_JOB/'verification.log')
    if not (s['phase']=='complete' and s['exit_code']==s['runner_exit_code']==s['audit_exit_code']==s['verification_exit_code']==0
        and s['run']==str(P22_RUN) and s['quality_gate'] and a['quality_gate'] and a['completed_cases']==544
        and a['integration_calls']==2944 and a['independent_check_count']==219181 and len(a['fine_comparisons'])==272
        and a['all_fine_agree'] and log==s['verification_log_sha256']=='69ccb0cfb8deff28df606aa180f17b203b78d07812d25b86913587444dc78a4a'
        and 'Ran 55 tests in 412.690s\n\nOK\n' in (P22_JOB/'verification.log').read_text()):
        raise RuntimeError('Completed P22 evidence changed')
    return dict(legacy=prior.inherited_verification(),p22=dict(job=str(P22_JOB),tests=55,seconds=412.690,
        log_sha256=log,inherited_unchanged=True),new_full_legacy_regression_run=False)
def input_paths():
    summary=read(P22_RUN/'summary.json'); names=['summary.json','independent_audit.json','predecessor_audit.json']
    names += [stage+'_audit.json' for stage in prior.STAGES]
    names += ['frozen/'+p for p in summary['hashes_sha256']]+['inputs/'+p for p in summary['inputs']]
    for row in summary['cases']:
        if not row['execution_pass']: raise ValueError('Invalid P22 predecessor')
        names += [row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if not row['result']['case']['readout']: names += [row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    if len(names)!=len(set(names)): raise ValueError('Duplicate archive paths')
    result={'p22/'+n:P22_RUN/n for n in names}
    result.update({'p22_job/'+n:P22_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    return result
def space_available(path): return shutil.disk_usage(path).free>=5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p23-'): raise ValueError('P23 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def archive_view(run):
    (run/'inputs').mkdir()
    (run/'inputs/p22').symlink_to(P22_RUN,target_is_directory=True)
    (run/'inputs/p22_job').symlink_to(P22_JOB,target_is_directory=True)
def input_manifest(): return {n:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for n,p in input_paths().items()}
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=inherited_verification(): raise RuntimeError('P23 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P23 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P23 input manifest changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(Path(v['source']))==v['sha256'] for v in i.values()),
            archive_bytes=all(digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            referenced_inputs=all(v.get('storage')=='reference_directory_v1' and os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()),
            directory_views=all((run/'inputs'/n).is_symlink() and (run/'inputs'/n).resolve()==p for n,p in (('p22',P22_RUN),('p22_job',P22_JOB))),
            inherited_verification=summary['inherited_verification']==inherited_verification())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
