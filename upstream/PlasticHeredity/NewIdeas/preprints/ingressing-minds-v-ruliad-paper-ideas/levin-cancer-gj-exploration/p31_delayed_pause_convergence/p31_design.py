"""Fixed P31 precision diagnosis of the preserved P30 start-15 label stop."""
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p30_refined_pause_boundary'))
import p30_design as prior
import p29_design as prefix_design
import p27_design as grid
digest,read,write_json,source_check=prior.digest,prior.read,prior.write_json,prior.source_check
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
p17=prefix_design.p17
HERE=ROOT/'p31_delayed_pause_convergence'
BASE=STORE/'p31-delayed-pause-convergence'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P30_JOB=STORE/'p30-refined-pause-boundary/jobs/p30-20261005T132855Z-oic4e3y0'
P30_RUN=STORE/'p30-refined-pause-boundary/runs/p30-20261005T140222Z-shal5ynt'
REVIEW=ROOT/'storage/p30-stop-review-20261006.json'
FILES=[ROOT/'PAPER_DELAYED_PAUSE_CONVERGENCE_PROTOCOL.md']+[HERE/n for n in
    ('p31_design.py','run_p31.py','analyze_p31.py','supervise_p31.py','test_p31.py','config.json','draws.json','predecessor_pins.json')]
STAGES=('prefix_replay','prefix_refine','replay','refinement')
FOUNDERS=('written','ordinary'); CONDITIONS=('baseline','pause_10_100','pause_15_100','pause_20_100')
CONTROLS=('baseline','pause_10_100','pause_20_100'); LEVELS=(8,16,32,64)
EXTRA_AXES=((16,64),(32,64),(64,16),(64,32))
AXES=((32,32),(64,64))+EXTRA_AXES
def prefix(founder='written',source_fine=False,resolution=64):
    stage='prefix_replay' if resolution in (8,16) else 'prefix_refine'
    return dict(id='__'.join((stage,founder,'source_fine' if source_fine else 'source_coarse','r'+str(resolution))),
        stage=stage,kind='prefix',founder=founder,fine=source_fine,source_fine=source_fine,resolution=resolution)
def case(founder='written',condition='pause_15_100',source_fine=False,prefix_resolution=64,resolution=64):
    c=grid.case(founder,condition,'heldout_17021',fine=source_fine)
    stage='replay' if prefix_resolution==resolution and resolution in (8,16) else 'refinement'
    c.update(id='__'.join((stage,founder,condition,'source_fine' if source_fine else 'source_coarse',
        'p'+str(prefix_resolution),'r'+str(resolution))),stage=stage,kind='renewal',source_fine=source_fine,
        prefix_resolution=prefix_resolution,resolution=resolution)
    return c
def stage_cases(stage):
    if stage in ('prefix_replay','prefix_refine'):
        return [c for q in LEVELS for h in FOUNDERS for f in (False,True) if (c:=prefix(h,f,q))['stage']==stage]
    if stage=='replay':
        return [case(h,k,f,q,q) for q in (8,16) for h in FOUNDERS for k in CONDITIONS for f in (False,True)]
    if stage=='refinement':
        return ([case(h,k,f,q,q) for q in (32,64) for h in FOUNDERS for k in CONDITIONS for f in (False,True)]
            +[case(h,'pause_15_100',f,p,q) for p,q in EXTRA_AXES for h in FOUNDERS for f in (False,True)])
    raise ValueError('Unregistered P31 stage')
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def prefix_source(c): return prefix(c['founder'],c['source_fine'],c['prefix_resolution'])['id']
founder_source,stock_source=prefix_design.founder_source,prefix_design.stock_source
def replay(c):
    if c['stage']=='prefix_replay': return 'p29/'+prefix_design.prefix(c['founder'],c['source_fine'],c['resolution'])['id']
    if c['stage']=='replay': return 'p30/'+prior.case(c['founder'],c['condition'],'heldout_17021',fine=c['fine'],resolution=c['resolution'])['id']
    return None
def anchor(c):
    if c['kind']=='renewal' and c['condition'] in CONTROLS:
        return 'p30/'+prior.case(c['founder'],c['condition'],'heldout_17021',fine=c['fine'],resolution=16)['id']
    return None
integrator,phase_settings,draw_book=prefix_design.integrator,prefix_design.phase_settings,prefix_design.draw_book
FIXED=dict(experiment='P31_delayed_pause_convergence',revision=REVISION,
    predecessor_run=str(P30_RUN),predecessor_job=str(P30_JOB),predecessor_repair_qualified=False,
    founders=list(FOUNDERS),conditions=list(CONDITIONS),control_conditions=list(CONTROLS),source_precision=['coarse','fine'],
    prefix_resolutions=list(LEVELS),joint_resolutions=list(LEVELS),target_extra_axes=[list(x) for x in EXTRA_AXES],
    target='pause_15_100',draw='heldout_17021',new_random_draws=False,
    source_bundle='matched_archived_P15_founder_and_P11_incoming_stock',prefix_horizon=100,
    prefix_logical_interval=[1180000,1180100],counterfactual_reanchor_to=1180300,reanchor_integration=0,
    native_binding_refresh='all_columns_once_noniterative',numerical_scaling='all_three_native_controls_and_phase_cap_divided_by_resolution',
    sampling_unchanged=True,primary_rows=list(range(8))+[16],first_challenge_boundaries=list(grid.BOUNDARIES),
    maximum_cases=96,maximum_integrations=2096,prefix_cases=16,renewal_cases=80,
    stage_cases=[8,8,32,48],stage_cumulative_integrations=[8,16,848,2096],
    prefix_finest_pairs=4,upstream_finest_pairs=4,downstream_finest_pairs=4,joint_finest_pairs=16,
    prefix_source_pairs=2,downstream_source_pairs=8,control_anchors=48,shared_schedule_prefix_pairs=96,
    exact_P29_prefix_replays=8,exact_P30_renewal_replays=32,baseline_comparisons=16,known_baseline_failures=3,
    finest_comparison=[32,64],contraction_reference=[16,32],scaled_error_limit=.01,contraction_allowance=1e-12,
    threshold_diagnostic=dict(cell_column=2,relative_interval=[150,200],sample_interval=1.25,
        classifier='E if miR200_total-Zeb_mRNA_total > 2; M if < -2; X otherwise',
        samples_per_case=41,report_all_renewal_cases=True,require_finest_target_sample_labels=True),
    favorable_convergence_required_for_valid_diagnosis=False,new_onward_assays=0,
    original_P27_gate_changed=False,original_P30_gate_changed=False,full_historical_lineage_refined=False,
    workers=2,worker_timeout_seconds=21600,total_budget_seconds=144000,verification_timeout_seconds=7200,
    audit_timeout_seconds=21600,overall_timeout_seconds=172800,minimum_free_gib=5,
    external_store=str(BASE),software_tests=42,historical_mathematical_audit_repeated=False,
    historical_policy='pinned_P30_stop_P29_qualification_and_all_input_hashes_v1',automatic_follow_on=False)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P31 configuration')
    return value
def manifest():
    hashes=prior.manifest(); hashes.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(k).is_absolute() or '..' in Path(k).parts for k in hashes): raise ValueError('Unsafe source path')
    return hashes
def completed_evidence():
    # Pin the preserved terminal review, rather than recursively rerunning prior
    # mathematical audits. Every input byte is freshly verified by integrity().
    pins=read(HERE/'predecessor_pins.json')
    for key,wanted in pins.items():
        side,tail=key.split('/',1); path={'job':P30_JOB,'run':P30_RUN,'root':ROOT}[side]/tail
        if digest(path)!=wanted: raise RuntimeError('P30 stopped evidence changed: '+key)
    status=read(P30_JOB/'status.json'); stop=read(REVIEW); launch=read(P30_JOB/'launch.json')
    expected=sorted(prior.case(h,'pause_15_100','heldout_17021',fine=f,resolution=8)['id']+'/numerical_agreement'
        for h,f in (('written',False),('written',True),('ordinary',True)))
    if not (status['phase']=='failed' and status['exit_code']==status['runner_exit_code']==1
        and status['verification_exit_code']==0 and status['verification_tests']==54
        and status['verification_log_sha256']==digest(P30_JOB/'verification.log')
        and status['completed_cases']==232 and status['completed_integrations']==5480
        and status['stage_gates']==dict(controls=True,renewal=False)
        and launch['hashes_sha256']==prior.manifest() and launch['inherited_verification']['p29_repair_qualified']
        and stop['all_stop_review_checks_pass'] and all(stop['checks'].values())
        and stop['experiment_quality_gate'] is False and sorted(stop['failed_checks'])==expected
        and stop['numerical_pairs_passed']==113 and stop['finest_source_pairs_passed']==58
        and stop['onward_cases_started']==0 and stop['final_audit_run'] is False
        and not (P30_RUN/'independent_audit.json').exists()):
        raise RuntimeError('P30 no longer matches the preserved three-label stop')
    return dict(diagnostic_archive_valid=True,p30_quality_gate=False,p29_targeted_repair_qualified=True,
        original_P27_quality_gate=False,known_failed_checks=expected,pins=pins,
        historical_mathematical_audit_repeated=False)
def input_paths():
    paths=prior.input_paths(); s=read(P30_RUN/'summary.json')
    names=['summary.json','predecessor_audit.json','controls_audit.json','renewal_audit.json']
    names+=['frozen/'+p for p in s['hashes_sha256']]
    for row in s['cases']:
        names+=[row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if row['result']['case']['kind']=='renewal': names+=[row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    if len(names)!=len(set(names)): raise ValueError('Duplicate P30 archive path')
    paths.update({'p30/'+n:P30_RUN/n for n in names})
    paths.update({'p30_job/'+n:P30_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    paths['p30_stop_review.json']=REVIEW
    paths['p30_stop_report.md']=ROOT/'P30_NUMERICAL_STOP_REVIEW_2026-10-06.md'
    return paths
def archive_view(run):
    prior.archive_view(run)
    for name,path in (('p30',P30_RUN),('p30_job',P30_JOB)):(run/'inputs'/name).symlink_to(path,target_is_directory=True)
    (run/'inputs/p30_stop_review.json').symlink_to(REVIEW)
    (run/'inputs/p30_stop_report.md').symlink_to(ROOT/'P30_NUMERICAL_STOP_REVIEW_2026-10-06.md')
def input_manifest(): return {k:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for k,p in input_paths().items()}
space_available=prior.space_available
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p31-'): raise ValueError('P31 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=completed_evidence(): raise RuntimeError('P31 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P31 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P31 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P31 draws changed')
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
            draws=read(HERE/'draws.json')==read(run/'frozen/p31_delayed_pause_convergence/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
