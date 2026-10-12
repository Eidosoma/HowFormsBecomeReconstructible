"""Revalidate fixed membership, seal it, then run complete H008 futures."""
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
from h008 import engine as e
from h008.inference import present_summary
from h008.fixtures import run_tests
from h008.audit import audit
from h008.analysis import analyze
from h003.fixtures import run_tests as original_fixtures
from h007.fixtures import run_tests as intervention_fixtures
from h007.io import save, verify, seal, load_source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    out = parser.parse_args().run.resolve()
    if SOURCE != out/'source':
        parser.error('Execute the frozen snapshot inside its prepared destination')
    with (out/'execution_claim.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat()), stream)
    started, completed = time.perf_counter(), 0
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
        intervention_fixtures(out/'intervention_fixtures.log')
        run_tests(out/'fixtures.log')
        for i, seed in enumerate(config['seeds']):
            status('fresh_current_validation', completed_blocks=i, total_blocks=len(config['seeds']))
            np.savez_compressed(out/f'present_{seed}.npz', **e.measure(seed, load_source(out, seed), e.load_candidate(out, seed)))
        decision = present_summary(out, config)
        if list(out.glob('future_*.npz')):
            raise AssertionError('Future existed before current validation seal')
        engineering = config['mode'] == 'benchmark'
        allowed = engineering or decision['passed']
        save(out/'ENROLLMENT.json', dict(decision=decision, candidate_packets=16*len(config['seeds']),
             membership='Unchanged H007 dose-eight present-only membership; no H008 rematching.',
             future_files_at_freeze=0, engineering_override=engineering, allow_futures=allowed,
             frozen_utc=datetime.now(timezone.utc).isoformat()))
        save(out/'FORECAST.json', dict(frozen_utc=datetime.now(timezone.utc).isoformat(), future_files_at_freeze=0,
             question='Does the fixed coherent hidden swap change terminal functional durability over sixteen replacements?',
             primary='hidden_swap minus unchanged renewal, either direction; absolute mean >=.10 and adjusted interval excludes zero.',
             controls='Each variant renewal minus foreign/read_off/write_off/damaged_copy >=.15 with positive adjusted lower bounds.',
             inference='Nine tests: primary two-sided tails .05/18, eight control lower bounds .05/9.',
             no_substitution='Record distinctness, self-retention, uninterrupted success and intermediate horizons are diagnostics.',
             matches=decision['matches'], current_passed=decision['passed'], runtime_forecast=config.get('runtime_forecast')))
        seal(out, 'enrollment_sha256.json', [out/'ENROLLMENT.json', out/'FORECAST.json', *sorted(out.glob('present_*.npz'))])
        print(f"Current validation sealed: matches={decision['matches']}; current_passed={decision['passed']}; allow_futures={allowed}.", flush=True)
        present_seconds = time.perf_counter()-started
        if allowed:
            verify(out, 'enrollment_sha256.json')
            for seed in config['seeds']:
                source, candidate = load_source(out, seed), e.load_candidate(out, seed)
                for fork in range(e.FORKS):
                    status('future_simulation', completed_forks=completed, total_forks=len(config['seeds'])*e.FORKS)
                    np.savez_compressed(out/f'future_{seed}_{fork:02d}.npz', **e.rollout(seed, source, candidate, fork))
                    completed += 1
                print(f'Completed {completed}/{len(config["seeds"])*e.FORKS} network/forks in {time.perf_counter()-started:.1f}s', flush=True)
        simulation_seconds = time.perf_counter()-started
        seal(out, 'raw_sha256.json', sorted(out.glob('*.npz')))
        status('audit', completed_forks=completed)
        checked = audit(out)
        audit_seconds = time.perf_counter()-started-simulation_seconds
        status('analysis', completed_forks=completed)
        summary = analyze(out)
        for manifest in ('freeze.json', 'enrollment_sha256.json', 'raw_sha256.json'):
            verify(out, manifest)
        seal(out, 'checksums.json', sorted(p for p in out.iterdir() if p.is_file()
             and p.name not in ('STATUS.json', 'checksums.json', 'COMPLETE.json', 'FAILED.json')))
        complete = dict(state='COMPLETE', pid=os.getpid(), completed_forks=completed,
                        elapsed_seconds=time.perf_counter()-started, present_seconds=present_seconds,
                        simulation_seconds=simulation_seconds, audit_seconds=audit_seconds,
                        audit_checks=checked['checks_count'], verdict=summary['verdict'],
                        qualified=summary['decision']['qualified'], completed_utc=datetime.now(timezone.utc).isoformat())
        save(out/'COMPLETE.json', complete)
        save(out/'STATUS.json', complete)
        print(out/'REPORT.md', flush=True)
    except BaseException:
        failed = dict(state='FAILED', pid=os.getpid(), completed_forks=completed,
                      elapsed_seconds=time.perf_counter()-started, traceback=traceback.format_exc())
        save(out/'FAILED.json', failed)
        save(out/'STATUS.json', failed)
        raise


if __name__ == '__main__':
    main()
