"""Freeze current enrollment before any one-replacement observation."""
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
from h007 import engine as e
from h007.io import save, verify, seal, load_source
from h007.inference import present_summary
from h007.fixtures import run_tests
from h003.fixtures import run_tests as original_fixtures
from h007.audit import audit
from h007.analysis import analyze


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    out = args.run.resolve()
    if SOURCE != out/'source':
        parser.error('Execute the frozen snapshot inside its prepared destination')
    with (out/'execution_claim.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat()), stream)
    started = time.perf_counter()
    completed = 0
    try:
        verify(out, 'freeze.json')
        config = json.loads((out/'config.json').read_text())
        if config['numpy'] != np.__version__ or config['python'] != sys.version:
            raise AssertionError('Runtime differs from frozen environment')
        for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            if os.environ.get(key) != '1':
                raise AssertionError('Numerical thread limit missing')

        def status(stage, **kwargs):
            save(out/'STATUS.json', dict(state='RUNNING', stage=stage, pid=os.getpid(),
                                        elapsed_seconds=time.perf_counter()-started, **kwargs))

        status('fixtures')
        original_fixtures(out/'original_fixtures.log')
        run_tests(out/'fixtures.log')
        for i, seed in enumerate(config['seeds']):
            status('present_only', completed_blocks=i, total_blocks=len(config['seeds']))
            np.savez_compressed(out/f'present_{seed}.npz', **e.measure(seed, load_source(out, seed)))
        decisions = present_summary(out, config)
        if list(out.glob('replacement_*.npz')):
            raise AssertionError('Replacement existed before current enrollment freeze')
        engineering = config['mode'] == 'benchmark'
        allowed = engineering or any(d['passed'] for d in decisions)
        save(out/'ENROLLMENT.json', dict(decisions=decisions, candidate_packets=16*len(config['seeds']),
             replacement_files_at_freeze=0, engineering_override=engineering, allow_replacements=allowed,
             frozen_utc=datetime.now(timezone.utc).isoformat()))
        save(out/'FORECAST.json', dict(frozen_utc=datetime.now(timezone.utc).isoformat(), replacement_files_at_freeze=0,
             prediction='Coherent hidden swaps can preserve current function and both distinct intended packets through one replacement.',
             primary_event='Both exact intended records retained; both rebuilt bodies and fresh readers functional.',
             decision='Largest dose passing current match, mean joint event >=.80, lower >=.70, and both route contrasts >=.50 with positive adjusted lower bounds.',
             scope='One-replacement feasibility; no sixteen-replacement durability test.',
             current_passing_doses=[d['dose'] for d in decisions if d['passed']],
             runtime_forecast=config.get('runtime_forecast')))
        seal(out, 'enrollment_sha256.json', [out/'ENROLLMENT.json', out/'FORECAST.json', *sorted(out.glob('present_*.npz'))])
        print(f"Current enrollment sealed: passing doses={[d['dose'] for d in decisions if d['passed']]}; allow_replacements={allowed}.", flush=True)
        present_seconds = time.perf_counter()-started
        if allowed:
            verify(out, 'enrollment_sha256.json')
            for seed in config['seeds']:
                source = load_source(out, seed)
                with np.load(out/f'present_{seed}.npz') as present:
                    packets = e.decode(present['packet_codes'])
                for trial in range(e.TRIALS):
                    status('replacement_simulation', completed_trials=completed, total_trials=len(config['seeds'])*e.TRIALS)
                    np.savez_compressed(out/f'replacement_{seed}_{trial:02d}.npz', **e.one_step(seed, source, packets, trial))
                    completed += 1
                print(f'Completed {completed}/{len(config["seeds"])*e.TRIALS} network/trials in {time.perf_counter()-started:.1f}s', flush=True)
        simulation_seconds = time.perf_counter()-started
        seal(out, 'raw_sha256.json', sorted(out.glob('*.npz')))
        status('audit', completed_trials=completed)
        checked = audit(out)
        audit_seconds = time.perf_counter()-started-simulation_seconds
        status('analysis', completed_trials=completed)
        summary = analyze(out)
        for manifest in ('freeze.json', 'enrollment_sha256.json', 'raw_sha256.json'):
            verify(out, manifest)
        seal(out, 'checksums.json', sorted(p for p in out.iterdir() if p.is_file()
             and p.name not in ('STATUS.json', 'checksums.json', 'COMPLETE.json', 'FAILED.json')))
        complete = dict(state='COMPLETE', pid=os.getpid(), completed_trials=completed,
                        elapsed_seconds=time.perf_counter()-started, present_seconds=present_seconds,
                        simulation_seconds=simulation_seconds, audit_seconds=audit_seconds,
                        audit_checks=checked['checks_count'], verdict=summary['verdict'],
                        nominated_dose=summary['nominated_dose'], completed_utc=datetime.now(timezone.utc).isoformat())
        save(out/'COMPLETE.json', complete)
        save(out/'STATUS.json', complete)
        print(out/'REPORT.md', flush=True)
    except BaseException:
        failed = dict(state='FAILED', pid=os.getpid(), completed_trials=completed,
                      elapsed_seconds=time.perf_counter()-started, traceback=traceback.format_exc())
        save(out/'FAILED.json', failed)
        save(out/'STATUS.json', failed)
        raise


if __name__ == '__main__':
    main()
