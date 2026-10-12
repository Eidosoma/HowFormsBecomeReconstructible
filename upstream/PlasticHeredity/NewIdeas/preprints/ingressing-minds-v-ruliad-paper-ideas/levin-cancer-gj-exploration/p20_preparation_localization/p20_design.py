"""Fixed P20 whole-cell preparation crossover; inherited sources stay immutable."""
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'storage')]
import paper_preparation_support_design as prior
import run_p19_external_recovery as recovery

digest, write_json, source_check = prior.digest, prior.write_json, prior.source_check
REVISION, STORE = prior.REVISION, prior.STORE
BASE = STORE/'p20-preparation-localization'
JOBS, RUNS = BASE/'jobs', BASE/'runs'
P19_JOB = STORE/'p19-recovery/jobs/paper-preparation-support-recovery-20260923T163250Z-36tj3nb5'
P19_RUN = STORE/'p19-recovery/runs/paper-preparation-support-recovery-20260923T163954Z-jooh_ol5'
HERE = ROOT/'p20_preparation_localization'
FILES = [ROOT/'PAPER_PREPARATION_LOCALIZATION_PROTOCOL.md'] + [HERE/n for n in
    ('p20_design.py', 'run_p20.py', 'analyze_p20.py', 'supervise_p20.py', 'test_p20.py', 'config.json')]
STAGES = ('renewal', 'onward')
FOUNDERS = ('written', 'ordinary')
AGES = ('before', 'after')
READOUTS = ('open', 'rna', 'cut')
FIXED = dict(experiment='P20_preparation_localization', revision=REVISION,
    predecessor_run=str(P19_RUN), predecessor_job=str(P19_JOB), founders=list(FOUNDERS),
    ages=list(AGES), first_interval=100, extra_interval=200, preparation_mode='isolated',
    newcomer_column=0, neighbour_columns=[1,2], immediately_discarded_column=1,
    common_logical_start=1180300, before_state_reanchor_without_integration=200,
    replacements=[1,2,0,1,2], later_interval=300, isolation_horizons=[10000,10000],
    readout_horizon=20000, readouts=list(READOUTS), incoming_seed=501,
    incoming_draw_namespace='P16_turnover_limit_v1', workers=2, maximum_cases=64,
    maximum_integrations=256, numerical_pairs=32, worker_timeout_seconds=21600,
    total_budget_seconds=86400, verification_timeout_seconds=7200,
    audit_timeout_seconds=21600, overall_timeout_seconds=129600,
    power=60, mirna_kd=1.25e-14, clock=prior.FIXED['clock'], minimum_free_gib=5,
    external_store=str(BASE), archive_mode='reference_directory_v1',
    external_schedule=True, automatic_follow_on=False, outcome_dependent_selection=False)

def read(path): return json.loads(path.read_text())
def validate_config(value):
    if value != FIXED: raise ValueError('Unregistered P20 configuration')
    return value

def case(stage='renewal', founder='written', newcomer='before', neighbours='before', readout='', fine=False):
    name = '__'.join([stage, founder, newcomer, neighbours] + ([readout] if readout else []))
    return dict(id=name+('__fine' if fine else ''), stage=stage, founder=founder,
                newcomer=newcomer, neighbours=neighbours, readout=readout, fine=fine)

def stage_cases(stage):
    if stage not in STAGES: raise ValueError('Unregistered P20 stage')
    return [case(stage,h,n,b,k,f) for f in (False,True) for h in FOUNDERS for n in AGES for b in AGES
            for k in (('',) if stage=='renewal' else READOUTS)]
def fixed_cases(): return [c for s in STAGES for c in stage_cases(s)]
def parent(c): return case('renewal',c['founder'],c['newcomer'],c['neighbours'],fine=c['fine'])
def source(c): return prior.case('renewal',c['founder'],200,'isolated',fine=c['fine'])['id']
def stem(c): return 'p20:%s:%s:%s'%(c['founder'],c['newcomer'],c['neighbours'])
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
incoming = prior.incoming

def replay(c):
    if c['newcomer'] != c['neighbours']: return None
    if c['newcomer']=='after':
        return 'p19/'+prior.case(c['stage'],c['founder'],200,'isolated',readout=c['readout'],fine=c['fine'])['id']
    if c['stage']=='renewal':
        return 'p19/'+prior.case('baseline',c['founder'],arm='reference',first=100,fine=c['fine'])['id']
    return 'p19/inputs/p18/'+prior.prior.case('onward',c['founder'],100,300,'open',readout=c['readout'],fine=c['fine'])['id']

def manifest():
    result=prior.execution_manifest(); result.update(recovery.manifest())
    result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe manifest path')
    return result

def inherited_verification():
    native=recovery.inherited_verification(); recovery.verify_launch(P19_JOB)
    s=read(P19_JOB/'status.json'); a=read(P19_RUN/'independent_audit.json')
    log=digest(P19_JOB/'verification.log')
    if not (s['phase']=='complete' and s['exit_code']==s['runner_exit_code']==s['audit_exit_code']==
            s['recovery_verification_exit_code']==0 and s['run']==str(P19_RUN) and
            s['quality_gate'] and a['quality_gate'] and a['completed_cases']==192 and
            a['integration_calls']==870 and a['independent_check_count']==65479 and
            log==s['verification_log_sha256']=='5159bfd22554d97c5b0e7a5bf561728e2a6c0afa592c91d86f5c9439c5c8cb1c' and
            'Ran 58 tests in 418.898s\n\nOK\n' in (P19_JOB/'verification.log').read_text()):
        raise RuntimeError('Completed P19 evidence changed')
    return dict(native=native,recovery=dict(job=str(P19_JOB),tests=58,seconds=418.898,
        log_sha256=log,inherited_unchanged=True),new_full_legacy_regression_run=False)

def input_paths():
    s=read(P19_RUN/'summary.json')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[x+'_audit.json' for x in prior.STAGES]
    names += ['frozen/'+p for p in s['frozen_hashes_sha256']]
    names += ['inputs/'+p for p in s['inputs']]
    names += ['recovery_frozen/'+Path(p).name for p in recovery.manifest()]
    for row in s['cases']:
        if not row['execution_pass']: raise ValueError('Invalid P19 source')
        names += [row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)): raise ValueError('Duplicate P19 archive entries')
    result={'p19/'+p:P19_RUN/p for p in names}
    result.update({'p19_job/'+p:P19_JOB/p for p in ('launch.json','status.json','verification.log')})
    return result

def space_available(path): return shutil.disk_usage(path).free >= 5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p20-'):
        raise ValueError('P20 output outside registered external runs')

def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes

def archive_view(run):
    (run/'inputs').mkdir()
    (run/'inputs/p19').symlink_to(P19_RUN,target_is_directory=True)
    (run/'inputs/p19_job').symlink_to(P19_JOB,target_is_directory=True)

def input_manifest():
    return {p:dict(source=str(source),sha256=digest(source),storage='reference_directory_v1')
            for p,source in input_paths().items()}

def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=inherited_verification():
        raise RuntimeError('Frozen P20 source or verification evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()):
        raise RuntimeError('P20 frozen execution copy changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']:
        raise RuntimeError('P20 input manifest changed')

def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,
            manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),
            origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(Path(v['source']))==v['sha256'] for v in i.values()),
            archive_bytes=all(digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            referenced_inputs=all(v.get('storage')=='reference_directory_v1' and
                os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()),
            directory_views=all((run/'inputs'/name).is_symlink() and (run/'inputs'/name).resolve()==target
                for name,target in (('p19',P19_RUN),('p19_job',P19_JOB))),
            inherited_verification=summary['inherited_verification']==inherited_verification())
    except (OSError,KeyError,ValueError,RuntimeError): return dict(integrity_readable=False)
