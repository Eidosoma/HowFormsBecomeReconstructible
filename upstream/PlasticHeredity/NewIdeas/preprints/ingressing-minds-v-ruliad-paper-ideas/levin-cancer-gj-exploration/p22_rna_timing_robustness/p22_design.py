"""Fixed P22 RNA dissection, communication windows and protein-draw/length panel."""
import hashlib
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p21_preparation_components'))
import p21_design as prior

digest,write_json,source_check=prior.digest,prior.write_json,prior.source_check
read,REVISION,STORE,recovery=prior.read,prior.REVISION,prior.STORE,prior.recovery
BASE=STORE/'p22-rna-timing-robustness'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P21_JOB=STORE/'p21-preparation-components/jobs/p21-20260925T124102Z-pcf11d5k'
P21_RUN=STORE/'p21-preparation-components/runs/p21-20260925T124448Z-pk8j6_e6'
HERE=ROOT/'p22_rna_timing_robustness'
FILES=[ROOT/'PAPER_RNA_TIMING_ROBUSTNESS_PROTOCOL.md']+[HERE/n for n in
    ('p22_design.py','run_p22.py','analyze_p22.py','supervise_p22.py','test_p22.py','config.json','draws.json')]
STAGES=('replay','rna','timing_controls','timing','robust','onward')
KNOWN=('none','newcomer_protein','newcomer_rna','neighbour_rna')
SINGLES=('newcomer_mir200','newcomer_zebmrna','neighbour_mir200','neighbour_zebmrna')
ROUTES={'none':(None,[]),'newcomer_protein':(0,[7]),'newcomer_rna':(0,[5,6]),
    'neighbour_rna':(2,[5,6]),'newcomer_mir200':(0,[5]),'newcomer_zebmrna':(0,[6]),
    'neighbour_mir200':(2,[5]),'neighbour_zebmrna':(2,[6])}
WINDOWS=('rna_early','rna_middle','rna_late','rna_full','isolated_full')
FOUNDERS=('written','ordinary'); READOUTS=('open','rna','cut'); DRAWS=('legacy','heldout_17021','heldout_17022')
COUNTS={'replay':(16,112),'rna':(32,224),'timing_controls':(48,368),
    'timing':(128,1088),'robust':(208,1936),'onward':(544,2944)}
FIXED=dict(experiment='P22_RNA_timing_robustness',revision=REVISION,predecessor_run=str(P21_RUN),predecessor_job=str(P21_JOB),
    founders=list(FOUNDERS),routes={k:dict(column=v[0],rows=v[1]) for k,v in ROUTES.items()},known_routes=list(KNOWN),
    single_RNA_routes=list(SINGLES),timing_windows=list(WINDOWS),timing_boundaries=[0,100,200,300],
    common_sample_times=list(range(0,301,15)),common_logical_start=1180300,source_extra_interval=200,
    native_binding_refresh='noniterative_all_columns_once',primary_rows=list(range(8))+[16],refresh_rows=list(range(8,16)),
    renewal_lengths=[5,11],later_interval=300,hold_horizons=[10000,10000],readout_horizon=20000,
    readouts=list(READOUTS),timing_onward_assays=False,draws=list(DRAWS),heldout_seeds=[17021,17022],
    draw_namespace='P22_incoming_v1',historical_namespace='P16_turnover_limit_v1',historical_seed=501,
    draw_count=11,incoming_protein_percent_range=[-25,25],maximum_cases=544,maximum_integrations=2944,numerical_pairs=272,
    renewal_parents=208,readout_parents=112,workers=2,worker_timeout_seconds=21600,total_budget_seconds=172800,
    verification_timeout_seconds=7200,audit_timeout_seconds=28800,overall_timeout_seconds=216000,
    power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],minimum_free_gib=5,external_store=str(BASE),
    archive_mode='reference_directory_v1',external_schedule=True,outcome_dependent_selection=False,
    automatic_follow_on=False,authorized_fixed_panels=['RNA identity','communication timing','robustness'])

def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P22 configuration')
    return value

def case(panel='rna',founder='written',route='newcomer_mir200',window='open',draw='legacy',replacements=5,readout='',fine=False):
    stage='onward' if readout else panel
    parts=[stage]+([panel] if readout else [])+[founder,route,window,draw,str(replacements)]+([readout] if readout else [])
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,panel=panel,founder=founder,
        route=route,window=window,draw=draw,replacements=replacements,readout=readout,fine=fine)

def stage_cases(stage):
    if stage not in STAGES: raise ValueError('Unknown P22 stage')
    if stage=='onward':
        return [case(c['panel'],c['founder'],c['route'],c['window'],c['draw'],c['replacements'],q,c['fine'])
            for panel in ('replay','rna','robust') for c in stage_cases(panel) for q in READOUTS]
    if stage=='robust':
        conditions=[(r,'open',draw,n) for r in KNOWN for draw in DRAWS for n in (5,11) if draw!='legacy' or n==11]
    else:
        conditions=[(r,w,'legacy',5) for r in (SINGLES if stage=='rna' else KNOWN)
            for w in (WINDOWS if stage=='timing' else ('open',))]
    return [case(stage,h,r,w,draw,n,fine=f) for f in (False,True) for h in FOUNDERS for r,w,draw,n in conditions]

def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case(c['panel'],c['founder'],c['route'],c['window'],c['draw'],c['replacements'],fine=c['fine'])
def stem(c): return 'p22:'+':'.join(str(c[k]) for k in ('panel','founder','route','window','draw','replacements'))
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def source(c): return prior.case(founder=c['founder'],mask=0,fine=c['fine'])['id']
def reference(c):
    target,mask={'none':('none',0),'newcomer_protein':('newcomer',1),
        'newcomer_rna':('newcomer',2),'neighbour_rna':('neighbour',2)}[c['route']]
    return prior.case('onward' if c['readout'] else 'components',c['founder'],'component',target,mask,c['readout'],c['fine'])['id']
def replay(c):
    if c['panel']=='replay':
        return dict(source='p21/'+reference(c),phases=['contact','isolated_1','isolated_2'] if c['readout'] else
            ['replacement_%02d'%i for i in range(2,7)]+['isolated_1','isolated_2'])
    if c['panel']=='robust' and c['draw']=='legacy' and not c['readout']:
        return dict(source='p21/'+reference(c),phases=['replacement_%02d'%i for i in range(2,7)])
    return None
def window_routes(c):
    return {'open':['open']*3,'rna_early':['rna','open','open'],'rna_middle':['open','rna','open'],
        'rna_late':['open','open','rna'],'rna_full':['rna']*3,'isolated_full':['isolated']*3}[c['window']]
def random_word(draw,event):
    if draw not in DRAWS or event not in range(1,12): raise ValueError('Unregistered incoming word')
    namespace,seed=('P16_turnover_limit_v1',501) if draw=='legacy' else ('P22_incoming_v1',int(draw.split('_')[1]))
    return int.from_bytes(hashlib.sha256(('%s|%d|turnover|%d'%(namespace,seed,event)).encode('ascii')).digest()[:8],'big')
def draw_book(): return {key:['%016x'%random_word(key,i) for i in range(1,12)] for key in DRAWS}
def incoming(M,draw,event):
    value=M.copy(); value[7,0]*=1+(random_word(draw,event)*51//2**64-25)/100
    return value

def manifest():
    result=prior.manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe source path')
    return result
def inherited_verification():
    prior.verify_launch(P21_JOB); s=read(P21_JOB/'status.json'); a=read(P21_RUN/'independent_audit.json'); log=digest(P21_JOB/'verification.log')
    if not (s['phase']=='complete' and s['exit_code']==s['runner_exit_code']==s['audit_exit_code']==s['verification_exit_code']==0
        and s['run']==str(P21_RUN) and s['quality_gate'] and a['quality_gate'] and a['completed_cases']==288
        and a['integration_calls']==1152 and a['independent_check_count']==87985 and len(a['fine_comparisons'])==144
        and a['all_fine_agree'] and log==s['verification_log_sha256']=='639c107978f3adc0747ec69dc267365e67abdc17a773075cda367eb1c0567c2f'
        and 'Ran 51 tests in 194.815s\n\nOK\n' in (P21_JOB/'verification.log').read_text()):
        raise RuntimeError('Completed P21 evidence changed')
    return dict(legacy=prior.inherited_verification(),p21=dict(job=str(P21_JOB),tests=51,seconds=194.815,
        log_sha256=log,inherited_unchanged=True),new_full_legacy_regression_run=False)
def input_paths():
    summary=read(P21_RUN/'summary.json'); names=['summary.json','independent_audit.json','predecessor_audit.json']
    names += [stage+'_audit.json' for stage in prior.STAGES]
    names += ['frozen/'+p for p in summary['hashes_sha256']]+['inputs/'+p for p in summary['inputs']]
    for row in summary['cases']:
        if not row['execution_pass']: raise ValueError('Invalid P21 predecessor')
        names += [row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if row['result']['case']['stage']!='onward': names += [row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    if len(names)!=len(set(names)): raise ValueError('Duplicate archive paths')
    result={'p21/'+n:P21_RUN/n for n in names}
    result.update({'p21_job/'+n:P21_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    return result
def space_available(path): return shutil.disk_usage(path).free>=5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p22-'): raise ValueError('P22 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def archive_view(run):
    (run/'inputs').mkdir()
    (run/'inputs/p21').symlink_to(P21_RUN,target_is_directory=True)
    (run/'inputs/p21_job').symlink_to(P21_JOB,target_is_directory=True)
def input_manifest(): return {n:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for n,p in input_paths().items()}
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=inherited_verification(): raise RuntimeError('P22 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P22 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P22 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P22 draws changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(Path(v['source']))==v['sha256'] for v in i.values()),
            archive_bytes=all(digest(run/'inputs'/p)==v['sha256'] for p,v in i.items()),
            referenced_inputs=all(v.get('storage')=='reference_directory_v1' and os.path.samefile(run/'inputs'/p,v['source']) for p,v in i.items()),
            directory_views=all((run/'inputs'/n).is_symlink() and (run/'inputs'/n).resolve()==p for n,p in (('p21',P21_RUN),('p21_job',P21_JOB))),
            inherited_verification=summary['inherited_verification']==inherited_verification(),
            incoming_draws=read(HERE/'draws.json')==read(run/'frozen/p22_rna_timing_robustness/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
