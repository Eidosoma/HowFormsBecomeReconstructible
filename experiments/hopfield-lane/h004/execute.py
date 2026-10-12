"""Execute an already frozen H004 specification from its own source snapshot."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os
import sys
import time
import traceback
import numpy as np

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE))
from h003 import experiment as e
from h003.audit import audit
from h003.fixtures import run_tests
from h004.analysis import analyze


def save(path, value):
    """Atomic durable markers so status readers never see a partial JSON file."""
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def verify_frozen(out):
    for name, expected in json.loads((out / 'freeze.json').read_text()).items():
        if e.checksum(out / name) != expected:
            raise AssertionError('Frozen input changed: ' + name)


def extra_audit(out, config):
    retained = json.loads((out / 'audit.json').read_text())

    def check(label, value):
        retained['checks'].append(dict(label=label, passed=bool(value)))
        retained['checks_count'] = len(retained['checks'])
        retained['passed'] = all(item['passed'] for item in retained['checks'])
        save(out / 'audit.json', retained)
        if not value:
            raise AssertionError(label)

    seeds = config['seeds']
    check('all and only declared blocks retained',
          {p.name for p in out.glob('function_*.npz')} == {f'function_{s}.npz' for s in seeds})
    check('unique independent block identifiers', len(seeds) == len(set(seeds)))
    if config['mode'] == 'confirmation':
        check('confirmation matches precision plan', seeds == config['sample_size_plan']['seeds'])
        check('no previous public cohort seed reused',
              not set(seeds).intersection(config['previous_public_seeds']))
    for seed in seeds:
        with np.load(out / f'function_{seed}.npz') as raw:
            base, founder, initial, cues, stable = e.h001.acquire(seed, 'function')
            for name, expected in [('base', base), ('founder', founder), ('initial', initial),
                                   ('cues', cues), ('stable_founder', stable)]:
                check(f'{seed} fresh formation {name}', np.array_equal(raw[name], expected))
            expected_masks = np.stack([e.m.mask_edges(e.m.rng(seed, 'h003', 'damage', g),
                                      (e.F, e.R, e.N, e.N), .5) for g in range(1, 17)])
            check(f'{seed} declared damage tape', np.array_equal(raw['damage'], expected_masks))
    if config['mode'] == 'benchmark':
        reference = out / 'engineering_reference.npz'
        check('engineering reference sealed', e.checksum(reference) == config['reference_sha256'])
        with np.load(reference) as expected, np.load(out / 'function_12900.npz') as actual:
            check('exact development replay array inventory', set(expected.files) == set(actual.files))
            for key in expected.files:
                check('exact development replay ' + key, np.array_equal(actual[key], expected[key]))
    return retained


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    out = args.run.resolve()
    if SOURCE != out / 'source':
        parser.error('Execute the frozen source snapshot inside the prepared run')
    started = time.perf_counter()
    completed = 0
    claim = out / 'execution_claim.json'
    # Exclusive creation prevents a second runner from touching this campaign.
    with claim.open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat()), stream)
        stream.write('\n')
    try:
        verify_frozen(out)
        config = json.loads((out / 'config.json').read_text())
        if np.__version__ != config['numpy'] or sys.version != config['python']:
            raise AssertionError('Runtime differs from frozen configuration')
        for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
            if os.environ.get(key) != '1':
                raise AssertionError('Numerical thread limit missing: ' + key)
        save(out / 'STATUS.json', dict(state='RUNNING', stage='fixtures', pid=os.getpid(), completed_blocks=0))
        run_tests(out / 'fixtures.log')
        for seed in config['seeds']:
            # No new implementation or configuration-dependent model branch.
            data = e.lineage(seed)
            np.savez_compressed(out / f'function_{seed}.npz', **data)
            del data
            completed += 1
            save(out / 'STATUS.json', dict(state='RUNNING', stage='simulation', pid=os.getpid(),
                                          completed_blocks=completed, total_blocks=len(config['seeds'])))
            print(f'Completed {completed}/{len(config["seeds"])} blocks in {time.perf_counter()-started:.1f}s', flush=True)
        simulation_seconds = time.perf_counter() - started
        save(out / 'raw_sha256.json', {p.name: e.checksum(p) for p in sorted(out.glob('function_*.npz'))})
        save(out / 'STATUS.json', dict(state='RUNNING', stage='audit', pid=os.getpid(), completed_blocks=completed))
        audit(out)
        checked = extra_audit(out, config)
        audit_seconds = time.perf_counter() - started - simulation_seconds
        save(out / 'STATUS.json', dict(state='RUNNING', stage='analysis', pid=os.getpid(), completed_blocks=completed))
        analyze(out)
        verify_frozen(out)
        save(out / 'checksums.json', {p.name: e.checksum(p) for p in sorted(out.iterdir())
             if p.is_file() and p.name not in ['STATUS.json', 'checksums.json', 'COMPLETE.json', 'FAILED.json']})
        summary = json.loads((out / 'summary.json').read_text())
        result = dict(state='COMPLETE', pid=os.getpid(), completed_blocks=completed,
                      elapsed_seconds=time.perf_counter()-started, simulation_seconds=simulation_seconds,
                      audit_seconds=audit_seconds, audit_checks=checked['checks_count'],
                      primary_qualified=summary['primary_qualification']['qualified'],
                      secondary_timing_qualified=summary['early_intervention_contrast']['qualified'],
                      completed_utc=datetime.now(timezone.utc).isoformat())
        save(out / 'COMPLETE.json', result)
        save(out / 'STATUS.json', result)
        print(out / 'REPORT.md', flush=True)
    except BaseException:
        result = dict(state='FAILED', pid=os.getpid(), completed_blocks=completed,
                      elapsed_seconds=time.perf_counter()-started, traceback=traceback.format_exc())
        save(out / 'FAILED.json', result)
        save(out / 'STATUS.json', result)
        raise


if __name__ == '__main__':
    main()
