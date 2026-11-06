"""Narrow, hash-bound reuse of the stopped run; no new native dynamics."""
from pathlib import Path
import shutil
from sr_common import ROOT,P,read,write,sha,binding,stamp

REUSE=read(ROOT/'context/REUSE.json')
CORE=('sr_common.py','sr_forcing.py','sr_quota.py','sr_policy.py','sr_unit_audit.py',
      'sr_worker.py','sr_analysis.py','sr_source.py','sr_verification.py','sr_entry.py')


def verify_protocol(current,prior):
    allowed={'resource','amendment','status','source_pricing_sha256','software_test_count'}
    if {k:v for k,v in current.items() if k not in allowed}!={k:v for k,v in prior.items() if k not in allowed}:
        raise ValueError('Resource amendment changed a scientific field')
    resource_changes={'workers','target_seconds','combined_seconds','continuation_waves',
                      'remaining_acquisition_worker_batches','capacity_wait_seconds','capacity_check_interval_seconds'}
    if {k:v for k,v in current['resource'].items() if k not in resource_changes}!={k:v for k,v in prior['resource'].items() if k not in resource_changes}:
        raise ValueError('Undeclared resource change')
    r=current['resource'];a=current['amendment']
    if (r['workers'],r['parent_reserve'],r['shared_limit'],r['target_seconds'],r['combined_seconds'])!=(4,1,12,6500,7200):
        raise ValueError('Unexpected amended resource contract')
    if a['prior_charged_wall_seconds']!=REUSE['prior_charged_wall_seconds'] or a['prior_charged_wall_seconds']+r['target_seconds']>r['combined_seconds']:
        raise ValueError('Prior time omitted or total budget exceeded')
    return True


def check_manifest(base,manifest):
    base=Path(base)
    for rel,digest in manifest['sha256'].items():
        path=base/rel
        if Path(rel).is_absolute() or '..' in Path(rel).parts or path.is_symlink() or not path.resolve().is_relative_to(base.resolve()):
            raise ValueError('Unsafe committed source path')
        if sha(path)!=digest:raise ValueError('Committed source file changed: '+rel)
    return len(manifest['sha256'])


def acquisition_binding(folder,stage,block,legacy=False):
    """Only the fixed fourteen imported scientific commitments use the old binding."""
    if stage=='scientific' and block in REUSE['imported_acquisition_blocks']:
        folder=Path(folder)
        if legacy or folder.name!=f'b{block}' or folder.parent.name!='acquisition':
            raise ValueError('Imported acquisition identity differs')
        if sha(folder/'COMMIT.json')!=REUSE['imported_acquisition_commits'][str(block)]:
            raise ValueError('Imported acquisition commit changed')
        return REUSE['source_binding']
    return binding()


def validate_prior():
    old=Path(REUSE['source_inputs']);run=Path(REUSE['source_run'])
    if sha(old/'INPUTS.json')!=REUSE['source_input_manifest_sha256'] or sha(old/'protocol.json')!=REUSE['source_protocol_sha256']:
        raise ValueError('Original frozen inputs changed')
    prior=read(old/'protocol.json');verify_protocol(P,prior)
    input_count=check_manifest(old,read(old/'INPUTS.json'))
    for name in CORE:
        if sha(ROOT/name)!=sha(old/name):raise ValueError('Qualified scientific implementation changed: '+name)
    receipt=read(ROOT/'COPY_RECEIPT.json')
    for name,digest in receipt['native_files_required_byte_identical'].items():
        if sha(ROOT/name)!=digest or sha(old/name)!=digest:raise ValueError('Native implementation changed')
    if (ROOT/'sr_acquire.py').read_text().split('def verify(')[0]!=(old/'sr_acquire.py').read_text().split('def verify(')[0]:
        raise ValueError('Native acquisition implementation changed')
    manifest_path=ROOT/'context/prior_STOPPED_RUN_MANIFEST.json'
    if sha(manifest_path)!=REUSE['source_stopped_manifest_sha256']:raise ValueError('Stop snapshot changed')
    manifest=read(manifest_path);output_count=check_manifest(run,manifest)
    actual={str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()}
    if actual!=set(manifest['sha256']):raise ValueError('Stopped run acquired extra or missing evidence')
    for name in ['COHORT.json','FUTURE_RELEASE.json','scientific_SEAL.json','OUTCOMES.json','ANALYSIS.json','COMPLETE.json','scientific']:
        if (run/name).exists():raise ValueError('Scientific futures or complete cohort already existed')
    if sha(run/'FAILED.json')!=REUSE['source_failure_sha256'] or read(run/'FAILED.json')['scientific_futures_started']:
        raise ValueError('Wrong prior stopping condition')
    if sha(run/'QUALIFICATION.json')!=REUSE['source_qualification_sha256']:
        raise ValueError('Qualified native receipt changed')
    q=read(run/'QUALIFICATION.json')
    if q['status']!='PASS' or q['binding']!=REUSE['source_binding'] or q['continuation']['units']!=4 or q['acquisition']['units']!=3:
        raise ValueError('Incomplete prior native qualification')
    if not all(v>0 for v in q['continuation']['policy_branch_coverage'].values()):
        raise ValueError('Prior coupled-policy branch qualification absent')
    import sr_acquire,sr_source
    attempts={}
    for block in REUSE['imported_acquisition_blocks']:
        folder=run/'acquisition'/f'b{block}'
        rows,_=sr_acquire.verify(folder,'scientific',block)
        attempts[block]=rows
    panel=sr_source.select_panel(attempts);sr_source.verify_selection(attempts,panel)
    if panel['complete'] or panel['eligible_blocks']!=REUSE['eligible_imported_blocks'] or panel['ineligible_blocks']!=[6]:
        raise ValueError('Imported boundary selection differs')
    return dict(status='PASS',utc=stamp(),source_inputs_sha256=REUSE['source_input_manifest_sha256'],
        source_stopped_manifest_sha256=REUSE['source_stopped_manifest_sha256'],prior_input_files_verified=input_count,
        prior_output_files_verified=output_count,imported_acquisitions=14,eligible_imported_blocks=panel['eligible_blocks'],
        ineligible_imported_blocks=panel['ineligible_blocks'],scientific_fields_unchanged=True,
        native_and_scientific_modules_byte_identical=True,prior_qualification_passed=True,
        prior_charged_wall_seconds=REUSE['prior_charged_wall_seconds'],prior_full_native_reads=17868,new_native_reads=0)


def install(run):
    run=Path(run);receipt=validate_prior();source=Path(REUSE['source_run'])
    (run/'acquisition').mkdir(exist_ok=False)
    import sr_acquire
    for block in REUSE['imported_acquisition_blocks']:
        target=run/'acquisition'/f'b{block}'
        shutil.copytree(source/'acquisition'/f'b{block}',target)
        sr_acquire.verify(target,'scientific',block)
    shutil.copyfile(source/'QUALIFICATION.json',run/'QUALIFICATION.json')
    if sha(run/'QUALIFICATION.json')!=REUSE['source_qualification_sha256']:raise ValueError('Qualification copy changed')
    receipt.update(binding=binding(),qualification_reused=True,source_qualification_sha256=REUSE['source_qualification_sha256'],
                   imported_commit_hashes=REUSE['imported_acquisition_commits'])
    write(run/'QUALIFICATION_REUSE.json',receipt)
    return receipt
