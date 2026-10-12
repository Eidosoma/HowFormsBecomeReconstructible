"""Registered refinement of the upstream P17 first-replacement fork."""
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p28_numerical_convergence'))
import p28_design as prior
import paper_renewal_maturation_design as p17
digest,read,write_json,source_check=prior.digest,prior.read,prior.write_json,prior.source_check
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
HERE=ROOT/'p29_upstream_fork_convergence'
BASE=STORE/'p29-upstream-fork-convergence'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P28_JOB=STORE/'p28-numerical-convergence/jobs/p28-20261003T221626Z-31knd6_6'
P28_RUN=STORE/'p28-numerical-convergence/runs/p28-20261003T222151Z-r5cxy32h'
P17_RUN=prior.prior.P26_RUN/'inputs/p25/inputs/p24/inputs/p23/inputs/p22/inputs/p21/inputs/p20/inputs/p19/inputs/p18/inputs/p17'
P15_RUN=P17_RUN/'inputs/p16/inputs/p15'
P11_RUN=P15_RUN/'inputs/p14/inputs/p13/inputs/p12/inputs/p11'
FILES=[ROOT/'PAPER_UPSTREAM_FORK_CONVERGENCE_PROTOCOL.md']+[HERE/n for n in
    ('p29_design.py','run_p29.py','analyze_p29.py','supervise_p29.py','test_p29.py','config.json','draws.json','predecessor_pins.json')]
STAGES=('prefix_replay','prefix_refine','replay','refinement')
FOUNDERS=('written','ordinary'); CONDITIONS=prior.CONDITIONS; LEVELS=(1,2,4,8,16)
AXES=((4,16),(8,16),(16,4),(16,8),(16,16))
def prefix(founder='written',source_fine=False,resolution=16):
    stage='prefix_replay' if resolution==(2 if source_fine else 1) else 'prefix_refine'
    return dict(id='__'.join((stage,founder,'source_fine' if source_fine else 'source_coarse','r'+str(resolution))),
        stage=stage,kind='prefix',founder=founder,fine=source_fine,source_fine=source_fine,resolution=resolution)
def case(founder='written',condition='pause_0_5',source_fine=False,prefix_resolution=16,resolution=16):
    c=prior.case(founder,condition,source_fine,resolution)
    stage='replay' if prefix_resolution==(2 if source_fine else 1) and resolution==16 else 'refinement'
    c.update(id='__'.join((stage,founder,condition,'source_fine' if source_fine else 'source_coarse',
        'p'+str(prefix_resolution),'r'+str(resolution))),stage=stage,kind='renewal',prefix_resolution=prefix_resolution)
    return c
def stage_cases(stage):
    if stage in ('prefix_replay','prefix_refine'):
        return [c for q in LEVELS for h in FOUNDERS for f in (False,True) if (c:=prefix(h,f,q))['stage']==stage]
    if stage=='replay': return [case(h,k,f,2 if f else 1,16) for h in FOUNDERS for k in CONDITIONS for f in (False,True)]
    if stage=='refinement': return [case(h,k,f,p,q) for p,q in AXES for h in FOUNDERS for k in CONDITIONS for f in (False,True)]
    raise ValueError('Unregistered P29 stage')
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def prefix_source(c): return prefix(c['founder'],c['source_fine'],c['prefix_resolution'])['id']
def founder_source(c): return 'p15/'+p17.source(c)
def old_prefix(c): return 'p17/'+p17.case(founder=c['founder'],fine=c['fine'])['id']
def stock_source(c): return 'p11/stock'+('__fine' if c['fine'] else '')
def replay(c):
    if c['stage']=='prefix_replay': return old_prefix(c)
    if c['stage']=='replay': return 'p28/'+prior.case(c['founder'],c['condition'],c['source_fine'],16)['id']
    return None
def anchor(c):
    if c['kind']=='renewal' and c['condition'] in ('baseline','pause_0_25'):
        return 'p28/'+prior.case(c['founder'],c['condition'],c['source_fine'],16)['id']
    return None
integrator,phase_settings=prior.integrator,prior.phase_settings
def draw_book():
    return dict(prefix_legacy_event_zero='%016x'%p17.prior.random_word(0),downstream=prior.draw_book())
FIXED=dict(experiment='P29_upstream_fork_convergence',revision=REVISION,
    predecessor_run=str(P28_RUN),predecessor_job=str(P28_JOB),predecessor_repair_qualified=False,
    founders=list(FOUNDERS),conditions=list(CONDITIONS),source_precision=['coarse','fine'],
    prefix_resolutions=list(LEVELS),downstream_axes=[list(x) for x in AXES],downstream_replay_resolution=16,
    source_bundle='matched_archived_P15_founder_and_P11_incoming_stock',prefix_horizon=100,
    prefix_logical_interval=[1180000,1180100],counterfactual_reanchor_to=1180300,
    reanchor_integration=0,native_binding_refresh='all_columns_once_noniterative',
    numerical_scaling='all_three_native_controls_and_phase_cap_divided_by_resolution',sampling_unchanged=True,
    primary_rows=list(range(8))+[16],draw='heldout_17021',new_random_draws=False,
    maximum_cases=116,maximum_integrations=2516,prefix_cases=20,renewal_cases=96,
    stage_cases=[4,16,16,80],stage_cumulative_integrations=[4,20,436,2516],
    prefix_finest_pairs=4,upstream_finest_pairs=16,downstream_finest_pairs=16,
    prefix_source_pairs=2,downstream_source_pairs=8,control_anchors=48,shared_schedule_prefix_pairs=48,
    finest_comparison=[8,16],contraction_reference=[4,8],scaled_error_limit=.01,contraction_allowance=1e-12,
    favorable_convergence_required_for_valid_diagnosis=False,new_onward_assays=0,
    original_P27_gate_changed=False,full_historical_lineage_refined=False,
    workers=2,worker_timeout_seconds=21600,total_budget_seconds=144000,verification_timeout_seconds=7200,
    audit_timeout_seconds=21600,overall_timeout_seconds=172800,minimum_free_gib=5,
    external_store=str(BASE),software_tests=34,historical_mathematical_audit_repeated=False,
    historical_policy='pinned_P28_diagnosis_and_all_input_hashes_v1',automatic_follow_on=False)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P29 configuration')
    return value
def manifest():
    hashes=prior.manifest(); hashes.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(k).is_absolute() or '..' in Path(k).parts for k in hashes): raise ValueError('Unsafe source path')
    return hashes
def completed_evidence():
    pins=read(HERE/'predecessor_pins.json')
    for key,wanted in pins.items():
        side,tail=key.split('/',1); path={'job':P28_JOB,'run':P28_RUN,'root':ROOT}[side]/tail
        if digest(path)!=wanted: raise RuntimeError('P28 completed evidence changed: '+key)
    s=read(P28_RUN/'summary.json'); a=read(P28_RUN/'independent_audit.json'); status=read(P28_JOB/'status.json')
    if not (status['phase']=='complete' and all(status[k]==0 for k in ('exit_code','verification_exit_code','runner_exit_code','audit_exit_code'))
        and status['verification_tests']==36 and a['quality_gate'] and a['completed_cases']==80 and a['integration_calls']==2080
        and a['independent_check_count']==150878 and a['all_finest_converged']
        and a['all_source_comparisons_agree'] is False and a['ready_for_refined_full_panel'] is False
        and a['original_P27_quality_gate'] is False and s['hashes_sha256']==prior.manifest()
        and all(read(P28_RUN/(k+'_audit.json'))==v and digest(P28_RUN/(k+'_audit.json'))==s['gate_hashes'][k] for k,v in s['gates'].items())):
        raise RuntimeError('P28 no longer matches the registered unresolved diagnosis')
    return dict(diagnostic_archive_valid=True,p28_quality_gate=True,p28_repair_qualified=False,
        original_P27=prior.stopped_evidence(),pins=pins,historical_mathematical_audit_repeated=False)
def input_paths():
    paths=prior.input_paths(); s=read(P28_RUN/'summary.json')
    names=['summary.json','independent_audit.json','predecessor_audit.json','replay_audit.json','convergence_audit.json']
    names+=['frozen/'+p for p in s['hashes_sha256']]
    for row in s['cases']:
        names+=[row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        names+=[row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    paths.update({'p28/'+n:P28_RUN/n for n in names})
    paths.update({'p28_job/'+n:P28_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    paths['p28_completion.json']=ROOT/'storage/p28-completion-integrity-20261004.json'
    for h in FOUNDERS:
        for f in (False,True):
            c=prefix(h,f)
            for n in ('result.json','replacement_01.npz'): paths[old_prefix(c)+'/'+n]=P17_RUN/p17.case(founder=h,fine=f)['id']/n
            for n in ('result.json','isolated_2.npz'): paths[founder_source(c)+'/'+n]=P15_RUN/p17.source(c)/n
    for f in (False,True):
        c=prefix(source_fine=f)
        for n in ('result.json','preparation.npz'): paths[stock_source(c)+'/'+n]=P11_RUN/('stock'+('__fine' if f else ''))/n
    return paths
def archive_view(run):
    prior.archive_view(run)
    for name,path in (('p28',P28_RUN),('p28_job',P28_JOB),('p17',P17_RUN),('p15',P15_RUN),('p11',P11_RUN)):
        (run/'inputs'/name).symlink_to(path,target_is_directory=True)
    (run/'inputs/p28_completion.json').symlink_to(ROOT/'storage/p28-completion-integrity-20261004.json')
def input_manifest(): return {k:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for k,p in input_paths().items()}
space_available=prior.space_available
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p29-'): raise ValueError('P29 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=completed_evidence(): raise RuntimeError('P29 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P29 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P29 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P29 draws changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),
            origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(v)==i[k]['sha256'] for k,v in required.items()),
            archive_bytes=all(digest(run/'inputs'/k)==v['sha256'] for k,v in i.items()),
            referenced_inputs=all(v['storage']=='reference_directory_v1' and os.path.samefile(run/'inputs'/k,v['source']) for k,v in i.items()),
            inherited_verification=summary['inherited_verification']==completed_evidence(),
            draws=read(HERE/'draws.json')==read(run/'frozen/p29_upstream_fork_convergence/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
