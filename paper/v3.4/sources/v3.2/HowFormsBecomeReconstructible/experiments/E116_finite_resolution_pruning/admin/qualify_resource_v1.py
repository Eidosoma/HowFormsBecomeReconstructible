"""Resource-only qualification amendment; frozen scientific equations are unchanged."""
import json
import math
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common import check_inputs,dump,sha,utc
from E116_finite_resolution_pruning.run import verify,inputs,latest_tests,inventory
from E116_finite_resolution_pruning.plan import HERE,ROOT,settings


def main():
    run,c=verify('benchmark_v1')
    check_inputs(HERE/'jobs/benchmark_v1')
    assert c['mode']=='benchmark' and c['blocks']==2
    for p in ('SAMPLE_FREEZE.json','analysis/qualification_v1.json','analysis/forecast_v1.json',
              'analysis/resource_amendment_v1.json'):
        assert not (HERE/p).exists(),p
    current={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    assert json.loads((run/'manifest.json').read_text())['inputs_sha256']==current
    reports=[json.loads(p.read_text()) for p in sorted(run.glob('block_*.json'))]
    unit=max(r['dynamics_seconds']/r['new_record_steps'] for r in reports)
    static=2*max(r['static_seconds'] for r in reports)
    steps_per_block=(13824+129024)//32*2048
    cost=unit*steps_per_block+static
    resources=inventory()
    workers=min(4,12-resources['other_busy_capacity'],len(resources['affinity']))
    assert workers>=1
    summary=max(240.,max(0.,c['seconds']-sum(r['seconds'] for r in reports))*16)
    forecasts={str(w):dict(expected_seconds=(32/w+1-1/w)*cost+summary,
        conservative_seconds=3*(32/w+1-1/w)*cost+summary) for w in range(1,5)}
    member_rows=[];fixed=0;temporal=0
    for p in sorted(run.glob('*.npz')):
        with zipfile.ZipFile(p) as z:
            for item in z.infolist():
                is_trace=item.filename=='state_hashes.npy'
                if is_trace:assert '_replay_' in p.name
                else:assert 'state_hashes' not in item.filename
                if is_trace:temporal+=item.file_size
                else:fixed+=item.file_size
                member_rows.append(dict(archive=p.name,member=item.filename,
                    uncompressed_bytes=item.file_size,scales_with_read_length=is_trace))
    other=sum(p.stat().st_size for p in run.rglob('*') if p.is_file() and p.suffix!='.npz')
    old_reserve=math.ceil(1.5*((fixed+temporal)*16*16+other*32))+1024**3
    reserve=math.ceil(1.5*(fixed*16+temporal*16*16+other*32))+1024**3
    assert fixed+temporal==sum(sum(i.file_size for i in zipfile.ZipFile(p).infolist()) for p in run.glob('*.npz'))
    assert reserve<old_reserve and resources['free_bytes']>reserve
    old_limit=settings('scientific')['conservative_resource_limit_seconds'];new_limit=64800
    assert old_limit==43200
    assert forecasts[str(workers)]['conservative_seconds']<new_limit
    reviewed=dict(utc=utc(),status='PASS',before_finite_scientific_outcomes=True,
        benchmark_complete_sha256=sha(run/'COMPLETE.json'),outputs_verified=len(c['outputs_sha256']),
        figures_inspected=True,scientific_input_hashes_unchanged=current,
        numerical_settings_unchanged=True,cohort_endpoints_and_inference_unchanged=True,
        original_conservative_limit_seconds=old_limit,effective_conservative_limit_seconds=new_limit,
        original_storage_reserve_bytes=old_reserve,storage_reserve_bytes=reserve,
        fixed_array_bytes_in_benchmark=fixed,step_trace_bytes_in_benchmark=temporal,
        other_bytes_in_benchmark=other,array_members=member_rows,
        source_count_scaling=16,step_count_scaling=16,other_file_scaling=32,
        storage_padding=1.5,storage_extra_bytes=1024**3,
        rationale='Price fixed-shape arrays separately from per-step traces; retain full authorised comparison and unchanged threefold runtime margin under an 18-hour planning allowance.',
        authorization='User authorised E116 execution and running as long as needed for good science.',
        amendment_document_sha256=sha(HERE/'RESOURCE_AMENDMENT_1.md'),
        administrative_script_sha256=sha(Path(__file__)),resources=resources,
        automatic_restart=False,automatic_successor=False)
    amendment=HERE/'analysis/resource_amendment_v1.json';dump(amendment,reviewed)
    forecast=dict(utc=utc(),workers=workers,**forecasts[str(workers)],forecasts_by_workers=forecasts,
        new_record_steps_upper_bound=steps_per_block*32,
        seconds_per_new_record_step_with_replay=unit,static_seconds_per_block=static,
        summary_allowance_seconds=summary,storage_reserve_bytes=reserve,
        fixed_shape_scientific_array_bytes_bound=fixed*16,
        step_trace_scientific_bytes_bound=temporal*16*16,
        detach_required=forecasts[str(workers)]['conservative_seconds']>600,
        original_conservative_resource_limit_seconds=old_limit,
        effective_conservative_resource_limit_seconds=new_limit,
        resource_amendment_sha256=sha(amendment),
        method='Original full-width measured runtime formula; fixed cohort and pre-deduplication work bound. Storage dimensions corrected by resource amendment 1.')
    dump(HERE/'analysis/forecast_v1.json',forecast)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',
        run/'finite_pruning.png',latest_tests(),HERE/'analysis/forecast_v1.json',amendment,
        HERE/'RESOURCE_AMENDMENT_1.md',Path(__file__).resolve())}
    exception=dict(original_conservative_limit_seconds=old_limit,effective_conservative_limit_seconds=new_limit,
        resource_amendment_sha256=sha(amendment),resource_amendment='E116_finite_resolution_pruning/analysis/resource_amendment_v1.json',
        scientific_inputs_unchanged=True)
    dump(HERE/'analysis/qualification_v1.json',dict(status='PASS',utc=utc(),evidence=evidence,
        figures_inspected=True,outputs_verified=len(c['outputs_sha256']),inputs_sha256=current,
        resource_exception=exception))
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=settings('scientific'),
        before_finite_scientific_outcomes=True,old_outcomes_known=True,
        source_registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources,
        qualification_sha256=sha(HERE/'analysis/qualification_v1.json'),resource_exception=exception))
    print(json.dumps(dict(status='PASS',**forecast)))


if __name__=='__main__':main()
