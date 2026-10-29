"""Bind only closed source artifacts consumed by the saved-data diagnosis."""
from common import *


def selected(job, indices, corruptions, families, damages):
    paths = []
    for index in indices:
        folder = job/f'tissue_{index}'
        paths += [folder/name for name in ('CONFIG.json','ROWS.json','BODIES.json','SUMMARY.json','SAVED_CHECK.json')]
        for corruption in range(corruptions):
            for family in families:
                for damage in damages:
                    base = folder/f'corruption_{corruption:02d}'/family/damage/'own'
                    paths += [base/(arm+suffix) for arm in SELECTED[1:] for suffix in ('.json','_repair.npz')]
    return paths


def main():
    close = read_json(UPSTREAM/'CLOSEOUT.json')
    complete = read_json(UPSTREAM/'COMPLETION_HANDOFF.json')
    assert close['status'] == 'PASS' and complete['status'] == 'PASS_COMPLETION_HANDOFF'
    verify(complete['files'])
    original_manifest = UPSTREAM/'checks/closeout_v1/ORIGINAL_FILES.json'
    assert sha(original_manifest) == close['outputs'][str(original_manifest)]
    original = read_json(original_manifest)
    job = UPSTREAM/'runs/confirmation_v1'
    assert sha(job/'SUMMARY.json') == close['summary_sha256']
    assert sha(job/'FAILED.json') == close['original_failure_sha256']
    paths = selected(job, BLOCKS, 2, FAMILIES, DAMAGES)
    bench_job = UPSTREAM/'runs/benchmark_v1'; bench = read_json(bench_job/'COMPLETE.json')
    assert bench['status'] == 'COMPLETE' and bench['role'] == 'benchmark'
    benchmark_paths = selected(bench_job, EXCLUDED, 1, ('residual',), ('mix050',))
    production = {str(p):original[str(p)] for p in paths}
    benchmark = {str(p):bench['outputs'][str(p)] for p in benchmark_paths}
    evidence_paths = [UPSTREAM/name for name in ('CLOSEOUT.json','COMPLETION_HANDOFF.json','FREEZE.json',
        'RESULT_INSPECTION.json','FINDINGS.json','PROTOCOL.md','analysis.py','design.py')]
    evidence_paths += [original_manifest, job/'SUMMARY.json', job/'REPORT.md', job/'FAILED.json', bench_job/'COMPLETE.json', bench_job/'SUMMARY.json']
    receipt = dict(status='BOUND_CLOSED_EXPOSED_SOURCE', recorded_utc=now(), production_files=production,
        benchmark_files=benchmark, evidence={str(p):sha(p) for p in evidence_paths},
        source_blocks=list(BLOCKS), excluded_blocks=list(EXCLUDED), source_population_already_exposed=True,
        new_population_cases=0, new_dynamics=0, scientific_retry=False,
        production_source_bytes=sum(p.stat().st_size for p in paths),
        benchmark_source_bytes=sum(p.stat().st_size for p in benchmark_paths))
    write_json(ROOT/'SOURCE_MANIFEST.json', receipt)
    print(dict(status=receipt['status'], production_files=len(production), benchmark_files=len(benchmark),
        production_source_bytes=receipt['production_source_bytes'], new_dynamics=0), flush=True)


if __name__ == '__main__': main()
