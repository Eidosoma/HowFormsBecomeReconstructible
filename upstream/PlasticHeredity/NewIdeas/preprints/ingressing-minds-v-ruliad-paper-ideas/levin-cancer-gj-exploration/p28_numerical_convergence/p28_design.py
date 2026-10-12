"""P28 fixed-source resolution study; the stopped P27 remains frozen."""
import hashlib,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p27_pause_boundary'))
import p27_design as prior
digest,read,write_json,source_check=prior.digest,prior.read,prior.write_json,prior.source_check
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
BASE=STORE/'p28-numerical-convergence'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
HERE=ROOT/'p28_numerical_convergence'
P27_JOB=Path('/mnt/workspaces/levin-cancer-gj-exploration/p27-pause-boundary/jobs/p27-20261002T212758Z-5l5k7e25')
P27_RUN=Path('/mnt/workspaces/levin-cancer-gj-exploration/p27-pause-boundary/runs/p27-20261002T215638Z-66w7ms2k')
REVIEW=ROOT/'storage/p27-stop-review-20261003.json'
FILES=[ROOT/'PAPER_NUMERICAL_CONVERGENCE_PROTOCOL.md']+[HERE/n for n in
    ('p28_design.py','run_p28.py','analyze_p28.py','supervise_p28.py','test_p28.py','config.json','draws.json')]
STAGES=('replay','convergence')
FOUNDERS=('written','ordinary')
CONDITIONS=('baseline','pause_0_5','pause_0_25','pause_10_100')
LEVELS=(1,2,4,8,16)
DRAW='heldout_17021'
# Source precision and solver resolution are independent registered factors.
def case(founder='written',condition='pause_0_5',source_fine=False,resolution=1):
    c=prior.case(founder,condition,DRAW,fine=source_fine)
    stage='replay' if resolution==(2 if source_fine else 1) else 'convergence'
    c.update(id='__'.join((stage,founder,condition,'source_fine' if source_fine else 'source_coarse','r'+str(resolution))),
        stage=stage,source_fine=source_fine,resolution=resolution)
    return c
def stage_cases(stage):
    if stage not in STAGES: raise ValueError('Unregistered P28 stage')
    return [c for level in LEVELS for h in FOUNDERS for condition in CONDITIONS for f in (False,True)
            if (c:=case(h,condition,f,level))['stage']==stage]
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def original_case(c): return prior.case(c['founder'],c['condition'],DRAW,fine=c['source_fine'])
def replay(c): return 'p27/'+original_case(c)['id'] if c['stage']=='replay' else None
def integrator(c):
    q=c['resolution']
    return dict(time_step=.0001/q,sim_integ_max_delt_cc=.001/q,sim_integ_max_delt_Vm=.0001/q,use_implicit=False)
def phase_settings(c,horizon): return min(100,horizon/20),min(100,horizon/100)/c['resolution']
def draw_book(): return {DRAW:prior.draw_book()[DRAW]}
FIXED=dict(experiment='P28_numerical_convergence',revision=REVISION,
    predecessor_run=str(P27_RUN),predecessor_job=str(P27_JOB),predecessor_quality_gate=False,
    founders=list(FOUNDERS),conditions=list(CONDITIONS),draw=DRAW,source_precision=['coarse','fine'],
    resolutions=list(LEVELS),integrator_scaling='all_three_native_numerical_controls_and_phase_cap_divided_by_level',
    fixed_source_across_resolutions=True,sampling_unchanged=True,primary_rows=list(range(8))+[16],
    maximum_cases=80,maximum_integrations=2080,replay_cases=16,convergence_cases=64,phases_per_case=26,
    finest_pairs=16,adjacent_pairs=64,source_pairs_at_finest=8,shared_schedule_prefix_pairs=40,
    outcome_anchor_cases=40,scaled_error_limit=.01,contraction_allowance=1e-12,
    finest_comparison=[8,16],contraction_reference=[4,8],full_phase_label_agreement_required=True,
    common_grid_diagnostic_agreement_required=True,new_onward_assays=0,original_P27_gate_changed=False,
    workers=2,worker_timeout_seconds=21600,total_budget_seconds=144000,verification_timeout_seconds=7200,
    audit_timeout_seconds=21600,overall_timeout_seconds=172800,minimum_free_gib=5,
    external_store=str(BASE),software_tests=36,historical_mathematical_audit_repeated=False,
    historical_policy='pinned_stopped_P27_reports_and_all_input_hashes_v1',automatic_follow_on=False)
PINS={'run/summary.json': 'bfd413fcc282fb7bd5934070c40e3defa0056747492d3300f19f330520727394', 'run/predecessor_audit.json': 'd52b6d81db00404e307e6173ce0716a28dd5515413134b05105ff6d284aa1510', 'run/controls_audit.json': 'c84470cdcd5c5a048385407939b0eb3e0c02e062270e90adf452d26f35923638', 'run/renewal_audit.json': '677a71e26c77c1ca33239cfd4e02e162dbf4ad20485225f74e9072cac61de5ce', 'job/launch.json': 'c64792b2eee3b55afd6c1e979251169190a34adb4c4832a76f49ca3a4f971e0c', 'job/status.json': '4ab6dab22d9a0d4e10ffc1cf49d2b0f1d61f304894e7c412142b254127159d5e', 'job/verification.log': 'dfea6bafee8ba8664ec31403677e09660edd9734fc785dc109f5aa9ab23674c2', 'job/input_manifest.json': '4e9075a28eaec66233c316e047e38cb582746ee5481bca4cb050883fef4121eb', 'root/storage/p27-stop-review-20261003.json': '51033dfcf975f899565202bf75251b0e9f40a5b581c59e28a5cbfe17f77968fe'}
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P28 configuration')
    return value
def manifest():
    result=prior.manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in result): raise ValueError('Unsafe source path')
    return result
def stopped_evidence():
    for key,wanted in PINS.items():
        where,tail=key.split('/',1); path={'run':P27_RUN,'job':P27_JOB,'root':ROOT}[where]/tail
        if digest(path)!=wanted: raise RuntimeError('Stopped P27 evidence changed: '+key)
    s=read(P27_RUN/'summary.json'); status=read(P27_JOB/'status.json'); gate=read(P27_RUN/'renewal_audit.json')
    failed=sorted(k for k,v in gate['checks'].items() if not v)
    expected=sorted(prior.case(h,k,DRAW,fine=True)['id']+'/fine' for h in FOUNDERS for k in ('pause_0_5','pause_10_100'))
    if not (status['phase']=='failed' and status['exit_code']==status['runner_exit_code']==1
        and status['verification_exit_code']==0 and status['verification_tests']==47
        and status['verification_log_sha256']==digest(P27_JOB/'verification.log')
        and s['completion_reason']=='technical_gate_failure' and s['all_execution_valid'] is False
        and len(s['cases'])==116 and all(x['execution_pass'] for x in s['cases'])
        and s['attempted_stages']==['controls','renewal'] and failed==expected
        and s['gates']['controls']['quality_gate'] and gate['quality_gate'] is False
        and all(s['integrity'].values()) and all(x['qualified'] for x in gate['anchor_controls'])
        and all(read(P27_RUN/(k+'_audit.json'))==v and digest(P27_RUN/(k+'_audit.json'))==s['gate_hashes'][k] for k,v in s['gates'].items())
        and prior.manifest()==s['hashes_sha256']):
        raise RuntimeError('P27 is not the registered preserved numerical stop')
    return dict(diagnostic_archive_valid=True,predecessor_quality_gate=False,known_failed_checks=failed,
        software_tests=47,verification_log_sha256=status['verification_log_sha256'],
        historical_mathematical_audit_repeated=False,pins=PINS)
def input_paths():
    result=prior.input_paths(); s=read(P27_RUN/'summary.json')
    names=['summary.json','predecessor_audit.json','controls_audit.json','renewal_audit.json']
    names+=['frozen/'+p for p in s['hashes_sha256']]
    for row in s['cases']:
        names+=[row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if not row['result']['case']['readout']: names+=[row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    if len(names)!=len(set(names)): raise ValueError('Duplicate archive path')
    result.update({'p27/'+n:P27_RUN/n for n in names})
    result.update({'p27_job/'+n:P27_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    result['p27_stop_review.json']=REVIEW
    return result
def archive_view(run):
    (run/'inputs').mkdir()
    for name,path in (('p26',prior.P26_RUN),('p26_job',prior.P26_JOB),('p27',P27_RUN),('p27_job',P27_JOB)):
        (run/'inputs'/name).symlink_to(path,target_is_directory=True)
    (run/'inputs/p27_stop_review.json').symlink_to(REVIEW)
def input_manifest(): return {name:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for name,p in input_paths().items()}
def space_available(path): return shutil.disk_usage(path).free>=5*1024**3
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p28-'): raise ValueError('P28 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=stopped_evidence(): raise RuntimeError('P28 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P28 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P28 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P28 draws changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),
            origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(v)==i[k]['sha256'] for k,v in required.items()),
            archive_bytes=all(digest(run/'inputs'/k)==v['sha256'] for k,v in i.items()),
            referenced_inputs=all(v['storage']=='reference_directory_v1' and os.path.samefile(run/'inputs'/k,v['source']) for k,v in i.items()),
            inherited_verification=summary['inherited_verification']==stopped_evidence(),
            draws=read(HERE/'draws.json')==read(run/'frozen/p28_numerical_convergence/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
