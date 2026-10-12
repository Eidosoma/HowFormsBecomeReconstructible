"""Seal present-only decisions before permitting any H006 study futures."""
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
from h006 import engine as e
from h006.inference import present_summary, select_dose
from h006.fixtures import run_tests
from h003.fixtures import run_tests as original_fixtures
from h006.audit import audit
from h006.analysis import analyze


def save(path, value):
    tmp = path.with_name(path.name+'.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def verify(out, name):
    for relative, expected in json.loads((out/name).read_text()).items():
        if e.e.checksum(out/relative) != expected:
            raise AssertionError('Changed sealed file: '+relative)


def load_source(out, seed):
    with np.load(out/f'inputs/source_{seed}.npz') as raw:
        return {key: raw[key] for key in raw.files}


def seal(out, name, paths):
    save(out/name, {str(p.relative_to(out)): e.e.checksum(p) for p in paths})


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
        for i, seed in enumerate(config['selection_seeds']):
            status('present_only_selection', completed_blocks=i, total_blocks=len(config['selection_seeds']))
            np.savez_compressed(out/f'selection_{seed}.npz', **e.measure(seed, load_source(out, seed), e.DOSES, 'selection'))
        decisions = present_summary(out, config['selection_seeds'], e.DOSES, 'selection', config)
        selected = 32 if config['mode'] == 'benchmark' else select_dose(decisions)
        if list(out.glob('assay_*.npz')) or list(out.glob('future_*.npz')):
            raise AssertionError('Assay/future existed before dose selection freeze')
        save(out/'SELECTION.json', dict(decisions=decisions, selected_dose=selected,
             method='largest dose passing every current gate' if config['mode'] == 'development' else 'engineering-only forced largest dose',
             assay_files_at_freeze=0, future_files_at_freeze=0, frozen_utc=datetime.now(timezone.utc).isoformat()))
        seal(out, 'selection_sha256.json', [out/'SELECTION.json', *sorted(out.glob('selection_*.npz'))])
        selection_seconds = time.perf_counter()-started
        print(f'Selection sealed; dose={selected}; no assay outcomes or futures opened.', flush=True)
        run_futures = False
        if selected is not None:
            verify(out, 'selection_sha256.json')
            for i, seed in enumerate(config['assay_seeds']):
                status('assay_present_validation', completed_blocks=i, total_blocks=len(config['assay_seeds']))
                np.savez_compressed(out/f'assay_{seed}.npz', **e.measure(seed, load_source(out, seed), (selected,), 'assay'))
            current = present_summary(out, config['assay_seeds'], (selected,), 'assay', config)[0]
            if list(out.glob('future_*.npz')):
                raise AssertionError('Future outcome existed before assay enrollment freeze')
            run_futures = config['mode'] == 'benchmark' or current['passed']
            save(out/'ENROLLMENT.json', dict(dose=selected, decision=current,
                 candidate_packets=16*len(config['assay_seeds']), future_files_at_freeze=0,
                 engineering_override=config['mode'] == 'benchmark', allow_futures=run_futures,
                 frozen_utc=datetime.now(timezone.utc).isoformat()))
            save(out/'FORECAST.json', dict(frozen_utc=datetime.now(timezone.utc).isoformat(), future_files_at_freeze=0,
                 direction='unchanged and hidden-flip renewal each exceed output-flip renewal by at least 0.10',
                 qualification='All independent present and integrity gates, both location contrasts, and four route controls.',
                 dose=selected, matches=current['matches'], nonempty_blocks=current['nonempty_blocks']))
            seal(out, 'enrollment_sha256.json', [out/'ENROLLMENT.json', out/'FORECAST.json', *sorted(out.glob('assay_*.npz'))])
            print(f'Assay enrollment sealed: {current["matches"]} matches; current_passed={current["passed"]}; allow_futures={run_futures}.', flush=True)
        present_seconds = time.perf_counter()-started
        if run_futures:
            verify(out, 'enrollment_sha256.json')
            for seed in config['assay_seeds']:
                source = load_source(out, seed)
                with np.load(out/f'assay_{seed}.npz') as present:
                    packets = e.decode(present['packet_codes'][0])
                for fork in range(e.FORKS):
                    status('future_simulation', completed_forks=completed, total_forks=len(config['assay_seeds'])*e.FORKS)
                    np.savez_compressed(out/f'future_{seed}_{fork:02d}.npz', **e.rollout(seed, source, packets, fork))
                    completed += 1
                print(f'Completed {completed}/{len(config["assay_seeds"])*e.FORKS} block/forks in {time.perf_counter()-started:.1f}s', flush=True)
        simulation_seconds = time.perf_counter()-started
        seal(out, 'raw_sha256.json', sorted(out.glob('*.npz')))
        status('audit', completed_forks=completed)
        checked = audit(out)
        audit_seconds = time.perf_counter()-started-simulation_seconds
        status('analysis', completed_forks=completed)
        summary = analyze(out)
        for manifest in ('freeze.json', 'selection_sha256.json', 'enrollment_sha256.json'):
            if (out/manifest).exists():
                verify(out, manifest)
        seal(out, 'checksums.json', sorted(p for p in out.iterdir() if p.is_file()
             and p.name not in ('STATUS.json', 'checksums.json', 'COMPLETE.json', 'FAILED.json')))
        complete = dict(state='COMPLETE', pid=os.getpid(), completed_forks=completed,
                        elapsed_seconds=time.perf_counter()-started, selection_seconds=selection_seconds,
                        present_seconds=present_seconds, simulation_seconds=simulation_seconds, audit_seconds=audit_seconds,
                        audit_checks=checked['checks_count'], selected_dose=selected, verdict=summary['verdict'],
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
