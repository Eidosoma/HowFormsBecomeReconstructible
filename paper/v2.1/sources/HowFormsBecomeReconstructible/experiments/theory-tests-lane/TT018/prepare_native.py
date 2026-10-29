"""Copy qualified numerical helpers and exposed fixtures without opening TT017 outcomes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from source_review import HERE, LANE, read, dump, sha, require, retain


def main():
    require(not (HERE/'SOURCE_RECEIPT.json').exists(), 'Preserve native preparation')
    prior = LANE/'TT017'
    job = read(prior/'jobs/validation_v1/job.json')
    for name, digest in job['inputs_sha256'].items():
        require(sha(prior/name)==digest, 'Unchanged TT017 input '+name)
    archive = HERE/'implementation_inputs'
    archive.mkdir()
    names = ['README.md','DRAFT_PROTOCOL.md','design.json','PREPARATION_STATUS.json',
             'PREPARATION_MANIFEST.json','future_statistics.py','forecast_adapter.py']
    for name in names:
        shutil.copyfile(HERE/name, archive/name)
    dump(archive/'MANIFEST.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        files_sha256={name:sha(archive/name) for name in names}))
    unchanged = ['support.py','capacity.py','lineage.py','native.py','core.py','roll_dynamics.py',
        'optimizer.py','optimizer_audit.py','repair.py','source/spacing_dynamics.py',
        'source/native/common.py','source/native/E015_functional_inheritance/model.py',
        'source/native/E016_teaching_consistency/model.py','source/known/teaching.npz',
        'source/known/g12.npz','source/known/g13.npz','source/known/g14.npz',
        'source/known/tt016_g15.npz','source/known/tt016_enrollment.npz']
    bindings=[]
    for name in unchanged:
        bindings.append(retain(prior/name,HERE/name,job['inputs_sha256'][name]))
    name='source/design_reference/tt016_plan.json'
    bindings.append(retain(prior/name,HERE/name,job['inputs_sha256'][name]))
    files={b['local']:b['sha256'] for b in bindings}
    # These were already bound and copied during source review; use no live parent import.
    previous=read(HERE/'PREPARATION_INPUTS.json')
    for b in previous['files']:
        if b['local'].startswith('sources/tt008/'):
            require(sha(HERE/b['local'])==b['sha256'],'Forecast source binding')
            files[b['local']]=b['sha256']
    cfg=read(HERE/'sources/tt017/plan.json')
    native={k:cfg[k] for k in ('native_config','native_cycle','development_config','cycle',
        'optimizer','tolerance','tolerance_generations','histories')}
    native.update(study='TT018',schema_version=1,classification='UNREGISTERED_IMPLEMENTATION',
        blocks=list(range(18000000,18000064)),lineage_namespace='TT018_serial_futures_v1_acquisition',
        continuation_namespace='TT018_serial_futures_v1_record',
        excluded_namespace='TT018_EXCLUDED_NATIVE_QUALIFICATION_v1',
        cases_per_acquisition_block=16,selected_records=64,futures=64,batch_size=16,
        policies=['untreated','one_time','repeated'],generations=list(range(15,33)),
        primary_margin=.02,bootstrap_seed=2026101208,bootstrap_replicates=20000,
        maximum_forecast_seconds=172800,maximum_qualification_seconds=600,
        storage_reserve_bytes=1073741824,automatic_polling=False,automatic_successor=False,
        cohort_identity_status='PROPOSED_UNRESERVED_NO_GENERATION',
        terminal_repair=False,terminal_write=False)
    dump(HERE/'plan.json',native)
    dump(HERE/'SOURCE_RECEIPT.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        files_sha256=files,bindings=bindings,tt017_inputs_verified_unchanged=len(job['inputs_sha256']),
        tt017_outcomes_read=False,scoped_forecast_sources=previous['files'],
        source='Qualified unchanged numerical helpers and exposed archived fixtures only',
        bytes=sum((HERE/name).stat().st_size for name in files)))
    print(json.dumps(dict(status='PASS',copied_unchanged_helpers_and_fixtures=len(bindings),
        bound_source_files=len(files),tt017_inputs_unchanged=len(job['inputs_sha256']),
        registered=False,new_cohort_generated=False)))


if __name__=='__main__':
    main()
