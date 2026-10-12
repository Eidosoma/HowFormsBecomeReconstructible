"""P30 full refined boundary panel; source precision and resolution stay separate."""
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p29_upstream_fork_convergence'))
import p29_design as prior
import p27_design as grid
digest,read,write_json,source_check=prior.digest,prior.read,prior.write_json,prior.source_check
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
HERE=ROOT/'p30_refined_pause_boundary'
BASE=STORE/'p30-refined-pause-boundary'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P29_JOB=STORE/'p29-upstream-fork-convergence/jobs/p29-20261004T174704Z-ndbszb7i'
P29_RUN=STORE/'p29-upstream-fork-convergence/runs/p29-20261004T175717Z-1ihs979y'
FILES=[ROOT/'PAPER_REFINED_PAUSE_BOUNDARY_PROTOCOL.md']+[HERE/n for n in
    ('p30_design.py','run_p30.py','analyze_p30.py','supervise_p30.py','test_p30.py','config.json','draws.json','predecessor_pins.json')]
STAGES=('controls','renewal','onward'); LEVELS=(8,16)
FOUNDERS,DRAWS,CONDITIONS,READOUTS=grid.FOUNDERS,grid.DRAWS,grid.CONDITIONS,grid.READOUTS
WINDOWS,BOUNDARIES,ANCHORS=grid.WINDOWS,grid.BOUNDARIES,grid.ANCHORS
incoming,random_word,draw_book=grid.incoming,grid.random_word,grid.draw_book
new_id,pupils,window_routes,challenge_segments=grid.new_id,grid.pupils,grid.window_routes,grid.challenge_segments
integrator,phase_settings=prior.integrator,prior.phase_settings

def case(founder='written',condition='pause_0_100',draw='legacy',replacements=5,readout='',fine=False,resolution=16):
    c=grid.case(founder,condition,draw,replacements,readout,fine)
    c.update(id=c['id'].removesuffix('__fine')+'__source_'+('fine' if fine else 'coarse')+'__q'+str(resolution),
        source_fine=fine,resolution=resolution,prefix_resolution=None if condition=='reference' else resolution,
        kind='readout' if readout else 'renewal')
    return c
def stage_cases(stage):
    if stage=='controls': return [case(h,'reference',readout=q,fine=f,resolution=r) for r in LEVELS for f in (False,True) for h in FOUNDERS for q in READOUTS]
    if stage=='renewal': return [case(h,k,draw,fine=f,resolution=r) for r in LEVELS for f in (False,True) for h in FOUNDERS for k in CONDITIONS for draw in DRAWS]
    if stage=='onward': return [case(c['founder'],c['condition'],c['draw'],5,q,c['fine'],c['resolution']) for c in stage_cases('renewal') for q in READOUTS]
    raise ValueError('Unregistered P30 stage')
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case(c['founder'],c['condition'],c['draw'],5,fine=c['fine'],resolution=c['resolution'])
def prefix_source(c): return 'p29/'+prior.prefix(c['founder'],c['source_fine'],c['prefix_resolution'])['id']
reference_parent=grid.reference_parent
def replay(c):
    if c['stage']=='renewal' and c['draw']=='heldout_17021' and c['condition'] in prior.CONDITIONS and c['resolution']==16:
        return 'p29/'+prior.case(c['founder'],c['condition'],c['source_fine'],16,16)['id']
    return None
def anchor(c): return grid.anchor(c)
FIXED=dict(experiment='P30_refined_pause_boundary',revision=REVISION,
    predecessor_run=str(P29_RUN),predecessor_job=str(P29_JOB),predecessor_repair_qualified=True,
    founders=list(FOUNDERS),conditions=list(CONDITIONS),draws=list(DRAWS),readouts=list(READOUTS),
    pause_windows={k:dict(start=v[0],duration=v[1]) for k,v in WINDOWS.items()},
    source_precision=['coarse','fine'],resolutions=[8,16],preparation_resolution_matches_downstream=True,
    preparation_source='qualified_archived_P29_prefix',full_historical_lineage_refined=False,
    first_challenge_boundaries=list(BOUNDARIES),common_sample_times=list(range(0,301,15)),
    common_logical_start=1180300,reanchor_without_integration=200,renewal_replacements=5,
    hold_horizons=[10000,10000],readout_horizon=20000,native_binding_refresh='all_columns_once_noniterative',
    primary_rows=list(range(8))+[16],scaled_error_limit=.01,
    numerical_comparison='8_vs_16_at_each_fixed_source_with_preparation_and_downstream_refined_together',
    source_comparison='coarse_vs_fine_source_at_resolution_16',full_grid_contraction_claimed=False,
    maximum_cases=856,maximum_integrations=7352,stage_cases=[24,208,624],
    cumulative_cases=[24,232,856],cumulative_integrations=[72,5480,7352],
    numerical_pairs=428,source_pairs=214,shared_schedule_prefix_pairs=576,
    exact_P29_replays=16,reference_readouts=24,retention_anchors=80,transmission_anchors=240,
    new_onward_assays=624,software_tests=54,workers=2,minimum_free_gib=5,
    worker_timeout_seconds=43200,total_budget_seconds=1209600,verification_timeout_seconds=7200,
    audit_timeout_seconds=43200,overall_timeout_seconds=1296000,
    external_store=str(BASE),archive_mode='reference_directory_v1',
    historical_policy='pinned_qualified_P29_and_P26_evidence_with_all_input_hashes_v1',
    historical_mathematical_audit_repeated=False,new_random_draws=False,original_P27_gate_changed=False,
    full_grid_requires_numerical_agreement=True,favorable_novel_outcomes_required=False,
    outcome_dependent_selection=False,automatic_follow_on=False)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P30 configuration')
    return value
def manifest():
    hashes=prior.manifest(); hashes.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(k).is_absolute() or '..' in Path(k).parts for k in hashes): raise ValueError('Unsafe source path')
    return hashes
def completed_evidence():
    pins=read(HERE/'predecessor_pins.json')
    for key,wanted in pins.items():
        side,tail=key.split('/',1); path={'job':P29_JOB,'run':P29_RUN,'root':ROOT}[side]/tail
        if digest(path)!=wanted: raise RuntimeError('P29 completed evidence changed: '+key)
    prior.verify_launch(P29_JOB)
    s=read(P29_RUN/'summary.json'); a=read(P29_RUN/'independent_audit.json'); status=read(P29_JOB/'status.json')
    if not (status['phase']=='complete' and all(status[k]==0 for k in ('exit_code','verification_exit_code','runner_exit_code','audit_exit_code'))
        and status['verification_tests']==34 and a['quality_gate'] and a['completed_cases']==116 and a['integration_calls']==2516
        and a['independent_check_count']==177161 and a['all_finest_converged'] and a['all_source_comparisons_agree']
        and a['ready_for_refined_full_panel'] and a['original_P27_quality_gate'] is False
        and a['qualified_onward_transmission_established'] is False and s['hashes_sha256']==prior.manifest()
        and all(read(P29_RUN/(k+'_audit.json'))==v==a['stages'][k] and digest(P29_RUN/(k+'_audit.json'))==s['gate_hashes'][k]
            and v['quality_gate'] and all(v['checks'].values()) for k,v in s['gates'].items())):
        raise RuntimeError('P29 no longer matches the qualified targeted repair')
    close=read(ROOT/'storage/p29-completion-integrity-20261005.json')
    if not (close['all_results_valid'] and all(close['checks'].values()) and all(close['fresh_integrity'].values())):
        raise RuntimeError('P29 completion preservation not qualified')
    return dict(p29_quality_gate=True,p29_repair_qualified=True,original_P27_quality_gate=False,pins=pins,
        completed_P26=grid.inherited_verification(),historical_mathematical_audit_repeated=False)
def input_paths():
    paths=prior.input_paths(); s=read(P29_RUN/'summary.json')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[k+'_audit.json' for k in prior.STAGES]
    names+=['frozen/'+p for p in s['hashes_sha256']]
    for row in s['cases']:
        names+=[row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if row['result']['case']['kind']=='renewal': names+=[row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    paths.update({'p29/'+n:P29_RUN/n for n in names})
    paths.update({'p29_job/'+n:P29_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    paths['p29_completion.json']=ROOT/'storage/p29-completion-integrity-20261005.json'
    return paths
def archive_view(run):
    prior.archive_view(run)
    for name,path in (('p29',P29_RUN),('p29_job',P29_JOB)):(run/'inputs'/name).symlink_to(path,target_is_directory=True)
    (run/'inputs/p29_completion.json').symlink_to(ROOT/'storage/p29-completion-integrity-20261005.json')
def input_manifest(): return {k:dict(source=str(p),sha256=digest(p),storage='reference_directory_v1') for k,p in input_paths().items()}
space_available=prior.space_available
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p30-'): raise ValueError('P30 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=completed_evidence(): raise RuntimeError('P30 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P30 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P30 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P30 draws changed')
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
            draws=read(HERE/'draws.json')==read(run/'frozen/p30_refined_pause_boundary/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
