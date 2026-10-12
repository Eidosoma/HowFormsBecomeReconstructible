"""Fixed P25 reciprocal first-draw panel and pinned completed evidence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p24_pause_durability'))
import p24_design as prior
import p22_design as p22

digest,source_check,read=prior.digest,prior.source_check,prior.read
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
BASE=STORE/'p25-neighbour-first-draw'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P24_JOB=STORE/'p24-pause-durability/jobs/p24-20260930T045405Z-k47hj81s'
P24_RUN=STORE/'p24-pause-durability/runs/p24-20260930T045747Z-eg5cxwa7'
HERE=ROOT/'p25_neighbour_first_draw'
FILES=[ROOT/'PAPER_NEIGHBOUR_FIRST_DRAW_PROTOCOL.md']+[HERE/n for n in
    ('p25_design.py','run_p25.py','analyze_p25.py','supervise_p25.py','test_p25.py','config.json','draws.json')]
STAGES=('controls','renewal','onward'); FOUNDERS=('written','ordinary'); READOUTS=('open','rna','cut')
ORIGINALS=('legacy','heldout_17021','heldout_17022')
SEQUENCES={
    'legacy':('legacy','legacy'),
    'heldout_17021':('heldout_17021','heldout_17021'),
    'heldout_17022':('heldout_17022','heldout_17022'),
    'legacy_first_17021':('heldout_17021','legacy'),
    'legacy_first_17022':('heldout_17022','legacy'),
    'heldout_17021_first_legacy':('legacy','heldout_17021'),
    'heldout_17022_first_legacy':('legacy','heldout_17022')}
DRAWS=tuple(SEQUENCES); CONDITIONS=('neighbour_rna','newcomer_protein')
ROUTES={'neighbour_rna':(2,[5,6]),'newcomer_protein':(0,[7])}
P22_PREFIX='p24/inputs/p23/inputs/p22/'
PINS={'summary.json':'0fe2d56304228d0a0a8c0b407d6885bd801a96493c0a8a87e88f1df3651f9d87',
    'independent_audit.json':'370816e8d7d885b10a9060ab42a4c76cbacfa9959835634af965b8b519732fbd'}
STATUS_PIN='4119f710bea9fb248048cf450955a0705339125527fe1c770fef8533d45f72de'
LOG_PIN='375aa3f57eae68f9404f7be4559d9ee65561d7c5761d7b572268e55a8df2e68e'
FIXED=dict(experiment='P25_neighbour_first_draw',revision=REVISION,predecessor_run=str(P24_RUN),predecessor_job=str(P24_JOB),
    founders=list(FOUNDERS),conditions=list(CONDITIONS),routes={k:dict(column=v[0],rows=v[1]) for k,v in ROUTES.items()},
    draws=list(DRAWS),sequence_sources={k:dict(first=v[0],tail=v[1]) for k,v in SEQUENCES.items()},
    original_sequences=list(ORIGINALS),new_random_draws=False,draw_count=11,incoming_protein_percent_range=[-25,25],
    renewal_lengths=[5,11],common_logical_start=1180300,first_challenge_horizon=300,
    common_sample_times=list(range(0,301,15)),later_interval=300,segmented_first_challenge=False,
    native_binding_refresh='noniterative_all_columns_once',primary_rows=list(range(8))+[16],refresh_rows=list(range(8,16)),
    readouts=list(READOUTS),hold_horizons=[10000,10000],readout_horizon=20000,
    maximum_cases=460,maximum_integrations=2164,numerical_pairs=230,renewal_parents=112,readout_cases=348,
    length_prefix_pairs=56,first_challenge_pairs=64,power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],
    workers=2,worker_timeout_seconds=21600,total_budget_seconds=144000,verification_timeout_seconds=7200,
    audit_timeout_seconds=21600,overall_timeout_seconds=172800,minimum_free_gib=5,external_store=str(BASE),
    archive_mode='reference_directory_v1',external_schedule=True,
    historical_audit_policy='pinned_completed_evidence_and_all_input_hashes_v1',historical_mathematical_audit_repeated=False,
    json_serialization='compact_atomic_v1',primary_state_edits_at_assembly=True,repeated_preparation=False,
    global_network_timing_intervention=False,outcome_dependent_selection=False,automatic_follow_on=False)

def write_json(path,value):
    path=Path(path); temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n'); temporary.replace(path)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P25 configuration')
    return value
def case(founder='written',condition='neighbour_rna',draw='legacy',replacements=5,readout='',fine=False):
    stage='controls' if condition=='reference' else 'onward' if readout else 'renewal'
    parts=[stage,founder,condition,draw,str(replacements)]+([readout] if readout else [])
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,condition=condition,
        panel='reference' if condition=='reference' else 'swaps',
        route='newcomer_protein' if condition=='reference' else condition,window='open',
        draw=draw,replacements=replacements,readout=readout,fine=fine)
def stage_cases(stage):
    if stage=='controls': return [case(h,'reference',readout=q,fine=f) for f in (False,True) for h in FOUNDERS for q in READOUTS]
    if stage=='renewal': return [case(h,k,draw,n,fine=f) for f in (False,True) for h in FOUNDERS for k in CONDITIONS for draw in DRAWS for n in (5,11)]
    if stage=='onward': return [case(c['founder'],c['condition'],c['draw'],c['replacements'],q,c['fine']) for c in stage_cases('renewal') for q in READOUTS]
    raise ValueError('Unknown P25 stage')
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case(c['founder'],c['condition'],c['draw'],c['replacements'],fine=c['fine'])
def stem(c): return 'p25:'+':'.join(str(c[k]) for k in ('founder','condition','draw','replacements'))
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return 'p24/inputs/'+prior.source(c)
def reference_parent(c): return 'p24/inputs/'+prior.reference_parent(c)
def replay(c):
    if c['condition']=='reference':
        return dict(source='p24/'+prior.case(c['founder'],'reference',readout=c['readout'],fine=c['fine'])['id'],phases=['contact','isolated_1','isolated_2'])
    if c['draw'] not in ORIGINALS: return None
    panel='replay' if c['draw']=='legacy' and c['replacements']==5 else 'robust'
    old=p22.case(panel,c['founder'],c['route'],'open',c['draw'],c['replacements'],c['readout'],c['fine'])
    names=['contact','isolated_1','isolated_2'] if c['readout'] else ['replacement_%02d'%i for i in range(2,c['replacements']+2)]+['isolated_1','isolated_2']
    return dict(source=P22_PREFIX+old['id'],phases=names)
def random_word(draw,event):
    if draw not in SEQUENCES or event not in range(1,12): raise ValueError('Unregistered incoming word')
    source=SEQUENCES[draw][0 if event==1 else 1]
    return p22.random_word(source,event)
def draw_book(): return {key:['%016x'%random_word(key,i) for i in range(1,12)] for key in DRAWS}
def incoming(M,draw,event):
    value=M.copy(); value[7,0]*=1+(random_word(draw,event)*51//2**64-25)/100; return value

def manifest():
    result=prior.manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe source path')
    return result
def inherited_verification():
    prior.verify_launch(P24_JOB); s=read(P24_JOB/'status.json'); a=read(P24_RUN/'independent_audit.json')
    if not (s['phase']=='complete' and s['exit_code']==s['runner_exit_code']==s['audit_exit_code']==s['verification_exit_code']==0
        and s['run']==str(P24_RUN) and s['quality_gate'] and a['quality_gate'] and a['completed_cases']==268
        and a['integration_calls']==1380 and a['independent_check_count']==114346 and len(a['fine_comparisons'])==134
        and a['all_fine_agree'] and digest(P24_JOB/'status.json')==STATUS_PIN
        and all(digest(P24_RUN/n)==h for n,h in PINS.items()) and digest(P24_JOB/'verification.log')==s['verification_log_sha256']==LOG_PIN
        and 'Ran 40 tests in 163.653s\n\nOK\n' in (P24_JOB/'verification.log').read_text()):
        raise RuntimeError('Completed P24 evidence changed')
    return dict(legacy=prior.inherited_verification(),p24=dict(job=str(P24_JOB),tests=40,seconds=163.653,
        log_sha256=LOG_PIN,inherited_unchanged=True),new_full_legacy_regression_run=False)
def input_paths():
    summary=read(P24_RUN/'summary.json'); names=['summary.json','independent_audit.json','predecessor_audit.json']
    names += [stage+'_audit.json' for stage in prior.STAGES]
    names += ['frozen/'+p for p in summary['hashes_sha256']]+['inputs/'+p for p in summary['inputs']]
    for row in summary['cases']:
        if not row['execution_pass']: raise ValueError('Invalid P24 predecessor')
        names += [row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if not row['result']['case']['readout']: names += [row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    if len(names)!=len(set(names)): raise ValueError('Duplicate archive paths')
    result={'p24/'+n:P24_RUN/n for n in names}
    result.update({'p24_job/'+n:P24_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    return result
def space_available(path): return shutil.disk_usage(path).free>=5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p25-'): raise ValueError('P25 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def archive_view(run):
    (run/'inputs').mkdir()
    (run/'inputs/p24').symlink_to(P24_RUN,target_is_directory=True)
    (run/'inputs/p24_job').symlink_to(P24_JOB,target_is_directory=True)
def input_manifest(): return {n:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for n,p in input_paths().items()}
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=inherited_verification(): raise RuntimeError('P25 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P25 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P25 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P25 draws changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(Path(v['source']))==v['sha256'] for v in i.values()),
            archive_bytes=all(digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            referenced_inputs=all(v.get('storage')=='reference_directory_v1' and os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()),
            directory_views=all((run/'inputs'/n).is_symlink() and (run/'inputs'/n).resolve()==p for n,p in (('p24',P24_RUN),('p24_job',P24_JOB))),
            inherited_verification=summary['inherited_verification']==inherited_verification(),
            incoming_draws=read(HERE/'draws.json')==read(run/'frozen/p25_neighbour_first_draw/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
