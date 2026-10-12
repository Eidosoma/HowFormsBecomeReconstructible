"""Fixed P27 pause-duration/start map and pinned completed evidence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p26_pause_window'))
import p26_design as prior
import p22_design as p22

digest,source_check,read=prior.digest,prior.source_check,prior.read
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
BASE=STORE/'p27-pause-boundary'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P26_JOB=Path('/mnt/workspaces/levin-cancer-gj-exploration/p26-pause-window/jobs/p26-20261001T193708Z-gbmaqodx')
P26_RUN=Path('/mnt/workspaces/levin-cancer-gj-exploration/p26-pause-window/runs/p26-20261001T195350Z-agohmy4u')
HERE=ROOT/'p27_pause_boundary'
FILES=[ROOT/'PAPER_PAUSE_BOUNDARY_PROTOCOL.md']+[HERE/n for n in
    ('p27_design.py','run_p27.py','analyze_p27.py','supervise_p27.py','test_p27.py','config.json','draws.json')]
STAGES=('controls','renewal','onward'); FOUNDERS=('written','ordinary'); READOUTS=('open','rna','cut')
DRAWS=('legacy','heldout_17021')
WINDOWS={'baseline':(None,0),'pause_0_5':(0,5),'pause_0_10':(0,10),'pause_0_15':(0,15),'pause_0_20':(0,20),
    'pause_0_25':(0,25),'pause_0_100':(0,100),'pause_5_100':(5,100),'pause_10_100':(10,100),
    'pause_15_100':(15,100),'pause_20_100':(20,100),'pause_25_100':(25,100),'full_block':(0,300)}
BOUNDARIES=(0,5,10,15,20,25,50,75,100,105,110,115,120,125,150,175,200,225,250,275,300)
ANCHORS=('baseline','pause_0_25','pause_0_100','pause_25_100','full_block')
CONDITIONS=tuple(WINDOWS); ROUTES={'none':(None,[])}
PINS={'summary.json':'873fe6ee5c6cbdf9f3be86bc729284fd908cd22d09525c2be1d3e2aa64e822c9','independent_audit.json':'01240f9a94ec61a71ca84a3da89246fda22b2c58fae8f65d9e2e39516013711a'}
STATUS_PIN='ff32837c10921d51b829a9abe9294adc0e8a1be65a166bdf5a6bf3ad02ab4d10'
LOG_PIN='39af065ed48d9bc96cb7b6d37991ecc3a8b8685df99876b34352716994476a24'
FIXED=dict(experiment='P27_pause_boundary',revision=REVISION,predecessor_run=str(P26_RUN),predecessor_job=str(P26_JOB),
    founders=list(FOUNDERS),conditions=list(CONDITIONS),pause_windows={k:dict(start=v[0],duration=v[1]) for k,v in WINDOWS.items()},
    draws=list(DRAWS),new_random_draws=False,draw_count=11,incoming_protein_percent_range=[-25,25],
    renewal_lengths=[5],common_logical_start=1180300,first_challenge_boundaries=list(BOUNDARIES),
    common_sample_times=list(range(0,301,15)),later_interval=300,segmented_first_challenge=True,
    native_binding_refresh='noniterative_all_columns_once',primary_rows=list(range(8))+[16],refresh_rows=list(range(8,16)),
    readouts=list(READOUTS),hold_horizons=[10000,10000],readout_horizon=20000,
    maximum_cases=428,maximum_integrations=3676,numerical_pairs=214,renewal_parents=104,readout_cases=324,
    shared_schedule_prefix_pairs=288,anchor_conditions=list(ANCHORS),anchor_policy='P26_retention_transmission_first_challenge_outcomes_v1',
    retention_anchor_keys=['retained_E','first_cell_sampled_behavior','first_cell_stable_E_after_second'],
    transmission_anchor_keys=['parent_retained_E','transmitted_E'],software_tests=47,
    split_unsplit_exact_array_equality_required=False,power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],
    workers=2,worker_timeout_seconds=21600,total_budget_seconds=144000,verification_timeout_seconds=7200,
    audit_timeout_seconds=21600,overall_timeout_seconds=172800,minimum_free_gib=5,external_store=str(BASE),
    archive_mode='reference_directory_v1',external_schedule=True,
    historical_audit_policy='pinned_completed_evidence_and_all_input_hashes_v1',historical_mathematical_audit_repeated=False,
    json_serialization='compact_atomic_v1',primary_state_edits_at_assembly=False,repeated_preparation=False,repeated_pause=False,
    outcome_dependent_selection=False,automatic_follow_on=False)

def write_json(path,value):
    path=Path(path); temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n'); temporary.replace(path)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P27 configuration')
    return value
def case(founder='written',condition='pause_0_100',draw='legacy',replacements=5,readout='',fine=False):
    stage='controls' if condition=='reference' else 'onward' if readout else 'renewal'
    parts=[stage,founder,condition,draw,str(replacements)]+([readout] if readout else [])
    start,duration=WINDOWS.get(condition,(None,0))
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,condition=condition,
        panel='reference' if condition=='reference' else 'timing_grid',
        route='newcomer_protein' if condition=='reference' else 'none',window='open' if start is None else condition,
        pause_start=start,pause_duration=duration,draw=draw,replacements=replacements,readout=readout,fine=fine)
def stage_cases(stage):
    if stage=='controls': return [case(h,'reference',readout=q,fine=f) for f in (False,True) for h in FOUNDERS for q in READOUTS]
    if stage=='renewal': return [case(h,k,draw,fine=f) for f in (False,True) for h in FOUNDERS for k in CONDITIONS for draw in DRAWS]
    if stage=='onward': return [case(c['founder'],c['condition'],c['draw'],c['replacements'],q,c['fine']) for c in stage_cases('renewal') for q in READOUTS]
    raise ValueError('Unknown P27 stage')
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case(c['founder'],c['condition'],c['draw'],c['replacements'],fine=c['fine'])
def stem(c): return 'p27:'+':'.join(str(c[k]) for k in ('founder','condition','draw','replacements'))
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return 'p26/inputs/'+prior.source(c)
def reference_parent(c): return 'p26/inputs/'+prior.reference_parent(c)
def window_routes(c):
    start,duration=WINDOWS[c['condition']]
    return ['rna' if start is not None and start<=t<start+duration else 'open' for t in BOUNDARIES[:-1]]
def challenge_segments(c): return [(start,end,route) for start,end,route in zip(BOUNDARIES,BOUNDARIES[1:],window_routes(c))]
def replay(c):
    if c['condition']=='reference':
        old=prior.case(c['founder'],'reference',readout=c['readout'],fine=c['fine'])
        return dict(source='p26/'+old['id'],phases=['contact','isolated_1','isolated_2'])
    return None
def anchor(c):
    if c['condition'] not in ANCHORS: return None
    return 'p26/'+prior.case(c['founder'],c['condition'],c['draw'],5,c['readout'],c['fine'])['id']
def random_word(draw,event):
    if draw not in DRAWS or event not in range(1,12): raise ValueError('Unregistered incoming word')
    return p22.random_word(draw,event)
def draw_book(): return {key:['%016x'%random_word(key,i) for i in range(1,12)] for key in DRAWS}
def incoming(M,draw,event):
    value=M.copy(); value[7,0]*=1+(random_word(draw,event)*51//2**64-25)/100; return value

def manifest():
    result=prior.manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe source path')
    return result
def inherited_verification():
    prior.verify_launch(P26_JOB); s=read(P26_JOB/'status.json'); a=read(P26_RUN/'independent_audit.json')
    if not (s['phase']=='complete' and s['exit_code']==s['runner_exit_code']==s['audit_exit_code']==s['verification_exit_code']==0
        and s['run']==str(P26_RUN) and s['quality_gate'] and a['quality_gate'] and a['completed_cases']==396
        and a['integration_calls']==2628 and a['independent_check_count']==206483 and len(a['fine_comparisons'])==198
        and a['all_fine_agree'] and digest(P26_JOB/'status.json')==STATUS_PIN
        and all(digest(P26_RUN/n)==h for n,h in PINS.items()) and digest(P26_JOB/'verification.log')==s['verification_log_sha256']==LOG_PIN
        and 'Ran 43 tests in 653.058s\n\nOK\n' in (P26_JOB/'verification.log').read_text()):
        raise RuntimeError('Completed P26 evidence changed')
    return dict(legacy=prior.inherited_verification(),p26=dict(job=str(P26_JOB),tests=43,seconds=653.058,
        log_sha256=LOG_PIN,inherited_unchanged=True),new_full_legacy_regression_run=False)
def input_paths():
    summary=read(P26_RUN/'summary.json'); names=['summary.json','independent_audit.json','predecessor_audit.json']
    names += [stage+'_audit.json' for stage in prior.STAGES]
    names += ['frozen/'+p for p in summary['hashes_sha256']]+['inputs/'+p for p in summary['inputs']]
    for row in summary['cases']:
        if not row['execution_pass']: raise ValueError('Invalid P26 predecessor')
        names += [row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if not row['result']['case']['readout']: names += [row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    if len(names)!=len(set(names)): raise ValueError('Duplicate archive paths')
    result={'p26/'+n:P26_RUN/n for n in names}
    result.update({'p26_job/'+n:P26_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    return result
def space_available(path): return shutil.disk_usage(path).free>=5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p27-'): raise ValueError('P27 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def archive_view(run):
    (run/'inputs').mkdir()
    (run/'inputs/p26').symlink_to(P26_RUN,target_is_directory=True)
    (run/'inputs/p26_job').symlink_to(P26_JOB,target_is_directory=True)
def input_manifest(): return {n:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for n,p in input_paths().items()}
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=inherited_verification(): raise RuntimeError('P27 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P27 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P27 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P27 draws changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(Path(v['source']))==v['sha256'] for v in i.values()),
            archive_bytes=all(digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            referenced_inputs=all(v.get('storage')=='reference_directory_v1' and os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()),
            directory_views=all((run/'inputs'/n).is_symlink() and (run/'inputs'/n).resolve()==p for n,p in (('p26',P26_RUN),('p26_job',P26_JOB))),
            inherited_verification=summary['inherited_verification']==inherited_verification(),
            incoming_draws=read(HERE/'draws.json')==read(run/'frozen/p27_pause_boundary/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
