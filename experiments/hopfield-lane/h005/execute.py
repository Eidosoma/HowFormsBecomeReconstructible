"""Freeze matching before running new futures; execute a sealed snapshot only."""
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
from h005 import engine as e
from h005.fixtures import run_tests
from h003.fixtures import run_tests as original_fixtures
from h005.audit import audit
from h005.analysis import analyze


def save(path, value):
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    tmp.replace(path)


def verify(out, name):
    for relative, expected in json.loads((out / name).read_text()).items():
        if e.e.checksum(out / relative) != expected:
            raise AssertionError('Changed sealed file: ' + relative)


def load_source(out, seed):
    with np.load(out / f'inputs/source_{seed}.npz') as data:
        return {key:data[key] for key in data.files}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args(); out = args.run.resolve()
    if SOURCE != out / 'source':parser.error('Run the frozen snapshot inside its prepared destination')
    with (out / 'execution_claim.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat()), stream)
    started = time.perf_counter(); completed = 0
    try:
        verify(out, 'freeze.json')
        config = json.loads((out / 'config.json').read_text())
        if config['numpy'] != np.__version__ or config['python'] != sys.version:
            raise AssertionError('Runtime differs from frozen environment')
        for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
            if os.environ.get(key) != '1':raise AssertionError('Numerical thread limit missing')
        save(out / 'STATUS.json', dict(state='RUNNING', stage='fixtures', pid=os.getpid()))
        original_fixtures(out / 'original_fixtures.log'); run_tests(out / 'fixtures.log')
        enrollment = dict(candidate_pairs=16*len(config['seeds']), blocks={}, rule='four exact passing probes')
        for i, seed in enumerate(config['seeds']):
            measured = e.measure(seed, load_source(out, seed))
            np.savez_compressed(out / f'present_{seed}.npz', **measured)
            enrollment['blocks'][str(seed)] = dict(eligible=measured['eligible'].tolist(),
                                                  count=int(measured['eligible'].sum()))
            save(out / 'STATUS.json', dict(state='RUNNING', stage='present_probes', pid=os.getpid(),
                                          completed_blocks=i+1, total_blocks=len(config['seeds'])))
        enrollment['eligible_pairs'] = sum(row['count'] for row in enrollment['blocks'].values())
        enrollment['matched_blocks'] = sum(row['count']>0 for row in enrollment['blocks'].values())
        enrollment['frozen_utc'] = datetime.now(timezone.utc).isoformat()
        save(out / 'ENROLLMENT.json', enrollment)
        if list(out.glob('future_*.npz')):raise AssertionError('Future outcome exists before matching freeze')
        save(out / 'FORECAST.json', dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
            future_files_at_freeze=0, direction='gain4_history renewal minus gain1_history renewal >= 0.10',
            qualification='Requires matching coverage, independent current-expression validation, '
                          'all five primary contrasts and integrity gates.',
            eligible_pairs=enrollment['eligible_pairs'], matched_blocks=enrollment['matched_blocks']))
        sealed = [out / 'ENROLLMENT.json', out / 'FORECAST.json', *sorted(out.glob('present_*.npz'))]
        save(out / 'enrollment_sha256.json', {p.name:e.e.checksum(p) for p in sealed})
        present_seconds = time.perf_counter()-started
        print(f'Enrollment frozen: {enrollment["eligible_pairs"]} pairs in {enrollment["matched_blocks"]} blocks. No futures opened.', flush=True)
        for seed in config['seeds']:
            source = load_source(out, seed)
            for fork in range(e.FORKS):
                result = e.rollout(seed, source, fork)
                np.savez_compressed(out / f'future_{seed}_{fork:02d}.npz', **result)
                del result
                completed += 1
                save(out / 'STATUS.json', dict(state='RUNNING', stage='future_simulation', pid=os.getpid(),
                    completed_forks=completed, total_forks=len(config['seeds'])*e.FORKS, current_seed=seed))
            print(f'Completed {completed}/{len(config["seeds"])*e.FORKS} block/forks in {time.perf_counter()-started:.1f}s', flush=True)
        simulation_seconds = time.perf_counter()-started
        save(out / 'raw_sha256.json', {p.name:e.e.checksum(p) for p in sorted(out.glob('*.npz'))})
        save(out / 'STATUS.json', dict(state='RUNNING', stage='audit', pid=os.getpid(), completed_forks=completed))
        checked = audit(out); audit_seconds = time.perf_counter()-started-simulation_seconds
        save(out / 'STATUS.json', dict(state='RUNNING', stage='analysis', pid=os.getpid(), completed_forks=completed))
        analyze(out)
        verify(out, 'freeze.json'); verify(out, 'enrollment_sha256.json')
        save(out / 'checksums.json', {p.name:e.e.checksum(p) for p in sorted(out.iterdir()) if p.is_file()
             and p.name not in ['STATUS.json','checksums.json','COMPLETE.json','FAILED.json']})
        summary = json.loads((out / 'summary.json').read_text())
        complete = dict(state='COMPLETE', pid=os.getpid(), completed_blocks=len(config['seeds']),
                        completed_forks=completed, elapsed_seconds=time.perf_counter()-started,
                        present_seconds=present_seconds, simulation_seconds=simulation_seconds,
                        audit_seconds=audit_seconds, audit_checks=checked['checks_count'],
                        qualified=summary['decision']['qualified'],
                        completed_utc=datetime.now(timezone.utc).isoformat())
        save(out / 'COMPLETE.json', complete); save(out / 'STATUS.json', complete)
        print(out / 'REPORT.md', flush=True)
    except BaseException:
        failed = dict(state='FAILED', pid=os.getpid(), completed_forks=completed,
                      elapsed_seconds=time.perf_counter()-started, traceback=traceback.format_exc())
        save(out / 'FAILED.json', failed); save(out / 'STATUS.json', failed)
        raise


if __name__ == '__main__':main()
