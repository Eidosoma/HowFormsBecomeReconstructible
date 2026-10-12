"""P32 full refined boundary panel; source precision and resolution stay separate."""
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'p31_delayed_pause_convergence'))
import p31_design as prior
import p27_design as grid
digest,read,write_json,source_check=prior.digest,prior.read,prior.write_json,prior.source_check
REVISION,STORE,recovery=prior.REVISION,prior.STORE,prior.recovery
HERE=ROOT/'p32_converged_pause_boundary'
BASE=STORE/'p32-converged-pause-boundary'; JOBS,RUNS=BASE/'jobs',BASE/'runs'
P31_JOB=STORE/'p31-delayed-pause-convergence/jobs/p31-20261007T164236Z-6sdqdblw'
P31_RUN=STORE/'p31-delayed-pause-convergence/runs/p31-20261007T164849Z-xa2dojrk'
FILES=[ROOT/'PAPER_CONVERGED_PAUSE_BOUNDARY_PROTOCOL.md']+[HERE/n for n in
    ('p32_design.py','run_p32.py','analyze_p32.py','supervise_p32.py','test_p32.py','config.json','draws.json','predecessor_pins.json')]
STAGES=('controls','renewal','onward'); LEVELS=(32,64)
FOUNDERS,DRAWS,CONDITIONS,READOUTS=grid.FOUNDERS,grid.DRAWS,grid.CONDITIONS,grid.READOUTS
WINDOWS,BOUNDARIES,ANCHORS=grid.WINDOWS,grid.BOUNDARIES,grid.ANCHORS
incoming,random_word,draw_book=grid.incoming,grid.random_word,grid.draw_book
new_id,pupils,window_routes,challenge_segments=grid.new_id,grid.pupils,grid.window_routes,grid.challenge_segments
integrator,phase_settings=prior.integrator,prior.phase_settings

def case(founder='written',condition='pause_0_100',draw='legacy',replacements=5,readout='',fine=False,resolution=64):
    c=grid.case(founder,condition,draw,replacements,readout,fine)
    c.update(id=c['id'].removesuffix('__fine')+'__source_'+('fine' if fine else 'coarse')+'__q'+str(resolution),
        source_fine=fine,resolution=resolution,prefix_resolution=None if condition=='reference' else resolution,
        kind='readout' if readout else 'renewal')
    return c
def stage_cases(stage):
    if stage=='controls': return [case(h,'reference',readout=q,fine=f,resolution=r) for r in LEVELS for f in (False,True) for h in FOUNDERS for q in READOUTS]
    if stage=='renewal': return [case(h,k,draw,fine=f,resolution=r) for r in LEVELS for f in (False,True) for h in FOUNDERS for k in CONDITIONS for draw in DRAWS]
    if stage=='onward': return [case(c['founder'],c['condition'],c['draw'],5,q,c['fine'],c['resolution']) for c in stage_cases('renewal') for q in READOUTS]
    raise ValueError('Unregistered P32 stage')
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case(c['founder'],c['condition'],c['draw'],5,fine=c['fine'],resolution=c['resolution'])
def prefix_source(c): return 'p31/'+prior.prefix(c['founder'],c['source_fine'],c['prefix_resolution'])['id']
reference_parent=grid.reference_parent
def replay(c):
    if c['stage']=='renewal' and c['draw']=='heldout_17021' and c['condition'] in prior.CONDITIONS:
        return 'p31/'+prior.case(c['founder'],c['condition'],c['source_fine'],c['resolution'],c['resolution'])['id']
    return None
def anchor(c): return grid.anchor(c)
FIXED=dict(experiment='P32_converged_pause_boundary',revision=REVISION,
    predecessor_run=str(P31_RUN),predecessor_job=str(P31_JOB),predecessor_repair_qualified=True,
    founders=list(FOUNDERS),conditions=list(CONDITIONS),draws=list(DRAWS),readouts=list(READOUTS),
    pause_windows={k:dict(start=v[0],duration=v[1]) for k,v in WINDOWS.items()},
    source_precision=['coarse','fine'],resolutions=[32,64],preparation_resolution_matches_downstream=True,
    preparation_source='qualified_archived_P31_prefix',full_historical_lineage_refined=False,
    first_challenge_boundaries=list(BOUNDARIES),common_sample_times=list(range(0,301,15)),
    common_logical_start=1180300,reanchor_without_integration=200,renewal_replacements=5,
    hold_horizons=[10000,10000],readout_horizon=20000,native_binding_refresh='all_columns_once_noniterative',
    primary_rows=list(range(8))+[16],scaled_error_limit=.01,
    numerical_comparison='32_vs_64_at_each_fixed_source_with_preparation_and_downstream_refined_together',
    source_comparison='coarse_vs_fine_source_at_resolution_64',full_grid_contraction_claimed=False,
    maximum_cases=856,maximum_integrations=7352,stage_cases=[24,208,624],
    cumulative_cases=[24,232,856],cumulative_integrations=[72,5480,7352],
    numerical_pairs=428,source_pairs=214,shared_schedule_prefix_pairs=576,
    exact_P31_replays=32,reference_readouts=24,retention_anchors=80,transmission_anchors=240,
    new_onward_assays=624,software_tests=60,workers=2,minimum_free_gib=5,
    worker_timeout_seconds=43200,total_budget_seconds=1209600,verification_timeout_seconds=7200,
    audit_timeout_seconds=43200,overall_timeout_seconds=1296000,
    external_store=str(BASE),archive_mode='reference_directory_v1',
    historical_policy='pinned_qualified_P31_and_P26_with_original_inherited_input_digests_v1',
    historical_mathematical_audit_repeated=False,new_random_draws=False,original_P27_gate_changed=False,original_P30_gate_changed=False,
    target_neighborhood=dict(condition='pause_15_100',draws=list(DRAWS),cell_column=2,relative_interval=[150,200],sample_interval=1.25,samples_per_case=41,require_label_and_bracket_agreement=True),
    full_grid_requires_numerical_agreement=True,favorable_novel_outcomes_required=False,
    outcome_dependent_selection=False,automatic_follow_on=False)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P32 configuration')
    return value
def manifest():
    hashes=prior.manifest(); hashes.update({str(p.relative_to(ROOT)):digest(p) for p in FILES})
    if any(Path(k).is_absolute() or '..' in Path(k).parts for k in hashes): raise ValueError('Unsafe source path')
    return hashes
def completed_evidence():
    pins=read(HERE/'predecessor_pins.json')
    for key,wanted in pins.items():
        side,tail=key.split('/',1); path={'job':P31_JOB,'run':P31_RUN,'root':ROOT}[side]/tail
        if digest(path)!=wanted: raise RuntimeError('P31 completed evidence changed: '+key)
    status=read(P31_JOB/'status.json'); launch=read(P31_JOB/'launch.json')
    close=read(ROOT/'storage/p31-completion-integrity-20261008.json')
    if not (status['phase']=='complete' and all(status[k]==0 for k in ('exit_code','verification_exit_code','runner_exit_code','audit_exit_code'))
        and status['verification_tests']==42 and status['completed_cases']==96 and status['completed_integrations']==2096
        and status['independent_checks']==164462 and status['quality_gate'] and status['focused_repair_qualified']
        and status['all_finest_converged'] and status['source_precision_agrees']
        and status['verification_log_sha256']==digest(P31_JOB/'verification.log')
        and launch['hashes_sha256']==prior.manifest() and close['all_results_valid']
        and len(close['checks'])==26 and all(close['checks'].values()) and all(close['fresh_integrity'].values())
        and close['focused_repair_qualified'] and close['original_P30_quality_gate'] is False
        and close['original_P27_quality_gate'] is False and close['full_pause_panel_qualified'] is False
        and close['qualified_onward_transmission_established'] is False):
        raise RuntimeError('P31 no longer matches the qualified focused repair')
    # P31 pinned this P30 launch record, which carries the qualified P26
    # reference/capacity/wipe evidence. Do not recurse through old math audits.
    p30_launch=prior.P30_JOB/'launch.json'
    if digest(p30_launch)!=launch['inherited_verification']['pins']['job/launch.json']:
        raise RuntimeError('Inherited P26 evidence record changed')
    p26=read(p30_launch)['inherited_verification']['completed_P26']
    return dict(p31_quality_gate=True,p31_repair_qualified=True,original_P30_quality_gate=False,
        original_P27_quality_gate=False,pins=pins,completed_P26=p26,historical_mathematical_audit_repeated=False)
def input_paths():
    paths=prior.input_paths(); s=read(P31_RUN/'summary.json')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[k+'_audit.json' for k in prior.STAGES]
    names+=['frozen/'+p for p in s['hashes_sha256']]
    for row in s['cases']:
        names+=[row['id']+'/result.json']+[row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
        if row['result']['case']['kind']=='renewal': names+=[row['id']+'/assembly/'+p for p in ('assembly.json','checkpoint.npz')]
    paths.update({'p31/'+n:P31_RUN/n for n in names})
    paths.update({'p31_job/'+n:P31_JOB/n for n in ('launch.json','status.json','verification.log','input_manifest.json')})
    paths['p31_completion.json']=ROOT/'storage/p31-completion-integrity-20261008.json'
    paths['p31_results.md']=ROOT/'PAPER_DELAYED_PAUSE_CONVERGENCE_RESULTS.md'
    return paths
def archive_view(run):
    prior.archive_view(run)
    for name,path in (('p31',P31_RUN),('p31_job',P31_JOB)):(run/'inputs'/name).symlink_to(path,target_is_directory=True)
    (run/'inputs/p31_completion.json').symlink_to(ROOT/'storage/p31-completion-integrity-20261008.json')
    (run/'inputs/p31_results.md').symlink_to(ROOT/'PAPER_DELAYED_PAUSE_CONVERGENCE_RESULTS.md')
def expected_input_hashes():
    s=read(P31_RUN/'summary.json'); expected={k:v['sha256'] for k,v in s['inputs'].items()}
    for name,value in s['hashes_sha256'].items(): expected['p31/frozen/'+name]=value
    for row in s['cases']:
        key='p31/'+row['id']+'/'; expected[key+'result.json']=row['result_sha256']
        for rec in row['result']['phases']: expected[key+rec['phase']+'.npz']=rec['sha256']
        if row['result']['case']['kind']=='renewal':
            provenance=row['result']['provenance']
            expected[key+'assembly/assembly.json']=provenance['assembly_metadata_sha256']
            expected[key+'assembly/checkpoint.npz']=provenance['assembly']['checkpoint_sha256']
    for key,value in read(HERE/'predecessor_pins.json').items():
        side,tail=key.split('/',1)
        if side=='root':
            name={'storage/p31-completion-integrity-20261008.json':'p31_completion.json',
                'PAPER_DELAYED_PAUSE_CONVERGENCE_RESULTS.md':'p31_results.md'}[tail]
        else: name=('p31/' if side=='run' else 'p31_job/')+tail
        expected[name]=value
    return expected

def verified_input_entry(path,wanted):
    actual=digest(path)
    if actual!=wanted: raise RuntimeError('Original archived input digest changed: '+str(path))
    return dict(source=str(path),sha256=actual,storage='reference_directory_v1')
def input_manifest():
    paths=input_paths(); expected=expected_input_hashes()
    if set(paths)!=set(expected): raise RuntimeError('Incomplete original input hash inventory')
    return {k:verified_input_entry(p,expected[k]) for k,p in paths.items()}
space_available=prior.space_available
def check_run_path(run):
    if run!=run.resolve() or run.parent!=RUNS or not run.name.startswith('p32-'): raise ValueError('P32 output outside external runs')
def freeze(job):
    hashes=manifest(); (job/'frozen').mkdir()
    for name,h in hashes.items():
        target=job/'frozen'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target)
        if digest(target)!=h: raise RuntimeError('Source changed during freeze')
    return hashes
def verify_launch(job):
    launch=read(job/'launch.json')
    if launch['hashes_sha256']!=manifest() or launch['inherited_verification']!=completed_evidence(): raise RuntimeError('P32 source/evidence changed')
    if not all(digest(job/'frozen'/p)==h for p,h in launch['hashes_sha256'].items()): raise RuntimeError('P32 frozen source changed')
    if digest(job/'input_manifest.json')!=launch['input_manifest_sha256']: raise RuntimeError('P32 input manifest changed')
    if read(HERE/'draws.json')!=draw_book(): raise RuntimeError('P32 draws changed')
def integrity(run,summary):
    try:
        h,i=summary['hashes_sha256'],summary['inputs']; required=input_paths(); expected=expected_input_hashes()
        return dict(revision=summary['revision']==REVISION,manifest=h==manifest() and set(i)==set(required),
            original_input_digests=set(i)==set(expected) and all(i[k]['sha256']==v for k,v in expected.items()),
            frozen=all(digest(run/'frozen'/p)==v for p,v in h.items()),
            origins=all(Path(i[p]['source'])==v for p,v in required.items()),
            source_bytes=all(digest(v)==i[k]['sha256'] for k,v in required.items()),
            archive_bytes=all(digest(run/'inputs'/k)==v['sha256'] for k,v in i.items()),
            referenced_inputs=all(v['storage']=='reference_directory_v1' and os.path.samefile(run/'inputs'/k,v['source']) for k,v in i.items()),
            inherited_verification=summary['inherited_verification']==completed_evidence(),
            draws=read(HERE/'draws.json')==read(run/'frozen/p32_converged_pause_boundary/draws.json')==draw_book())
    except (OSError,KeyError,RuntimeError,ValueError): return dict(integrity_readable=False)
