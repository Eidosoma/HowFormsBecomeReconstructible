"""Bind known forecasting evidence and completed technical benchmarks for planning."""
from datetime import datetime, timezone
from pathlib import Path
import json
from source_review import HERE, LANE, sha, read, dump, require, retain


def main():
    bindings = []
    old = LANE/'TT008'
    job = read(old/'jobs/prospective_v2/job.json')
    done = read(old/'runs/prospective_v2/COMPLETE.json')
    require(done['status'] == 'COMPLETE' and done['audit_status'] == 'PASS', 'Completed TT008 source')
    for name in ('FROZEN_MODELS.json', 'selection.json', 'measure.py', 'forecast.py'):
        bindings.append(retain(old/name, HERE/'sources/tt008'/name, job['inputs_sha256'][name]))
    for name in ('features.csv', 'predictions.csv'):
        bindings.append(retain(old/'runs/prospective_v2'/name, HERE/'sources/tt008'/name, done['outputs_sha256'][name]))
    bindings.append(retain(old/'runs/prospective_v2/COMPLETE.json', HERE/'sources/tt008/COMPLETE.json'))
    bindings.append(retain(old/'jobs/prospective_v2/job.json', HERE/'sources/tt008/job.json'))
    current = LANE/'TT017'
    job = read(current/'jobs/validation_v1/job.json')
    for name, digest in job['inputs_sha256'].items():
        require(sha(current/name) == digest, 'TT017 frozen scientific input unchanged: '+name)
    for name in ('PROTOCOL.md', 'plan.json', 'REGISTRATION.json'):
        bindings.append(retain(current/name, HERE/'sources/tt017'/name, job['inputs_sha256'][name]))
    benchmark = read(current/'runs/benchmark_v2/COMPLETE.json')
    require(benchmark['status'] == 'COMPLETE' and benchmark['audit_status'] == 'PASS', 'Completed technical benchmark')
    bindings.append(retain(current/'runs/benchmark_v2/benchmark.json', HERE/'sources/tt017/benchmark.json',
                           benchmark['outputs_sha256']['benchmark.json']))
    bindings.append(retain(current/'runs/benchmark_v2/COMPLETE.json', HERE/'sources/tt017/BENCHMARK_COMPLETE.json'))
    for study in ('TT014', 'TT015', 'TT016'):
        bindings.append(retain(LANE/study/'INTERPRETATION.md', HERE/'sources'/study.lower()/'INTERPRETATION.md'))
    result = dict(status='PASS', recorded_utc=datetime.now(timezone.utc).isoformat(),
        code_sha256=sha(Path(__file__)), source_review_sha256=sha(HERE/'SOURCE_REVIEW.json'),
        files=bindings, tt017_frozen_scientific_inputs_verified=len(job['inputs_sha256']),
        tt017_scientific_results_read=False, tt017_inputs_changed=False,
        tt008_models_refit=False, fresh_native_outcomes_generated=False,
        status_observation=dict(observed_utc='2026-10-12T14:24:51+00:00', run_status='RUNNING',
            block=17000006, generation=24, status_only=True),
        scope='Completed source and technical benchmark bindings only; no live TT017 scientific outcome inspection or successor launch.')
    dump(HERE/'PREPARATION_INPUTS.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    main()
