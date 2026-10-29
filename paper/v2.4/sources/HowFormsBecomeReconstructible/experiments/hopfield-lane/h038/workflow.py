"""Frozen, capacity-limited H038 serial guidance factorial."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import math
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import numpy as np

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE))
from h007.io import checksum, save, seal, verify
from h038 import experiment as d, analysis
from h038.audit import audit
from h038.fixtures import run_tests

FILES = ['model.py', 'h007/io.py', 'run_python.sh', 'requirements.txt',
    'h035/design.py', 'h035/experiment.py', 'h035/audit.py',
    'h038/experiment.py', 'h038/audit.py', 'h038/analysis.py',
    'h038/fixtures.py', 'h038/workflow.py', 'h038/PROTOCOL.md']
H035_MANIFEST = 'd0db9e277954d065b1bf1f7ffeeca65d2f200eedb758978c7cb24271ccb73b4f'


def utc():
    return datetime.now(timezone.utc).isoformat()


def cpu_snapshot():
    def sample():
        result = {}
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                pid = int(path.parent.name)
                f = path.read_text().rsplit(')', 1)[1].split()
                if pid != os.getpid():
                    result[pid] = (int(f[11])+int(f[12]), int(f[17]), int(f[19]))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
        return result
    first = sample(); tick = time.monotonic(); time.sleep(1); second = sample()
    seconds = time.monotonic()-tick; hz = os.sysconf('SC_CLK_TCK'); rows = []
    for pid, (ticks, threads, born) in second.items():
        prior = first.get(pid)
        used = max(0, ticks-(prior[0] if prior and prior[2] == born else 0))/hz/seconds
        if used >= .05:
            rows.append(dict(pid=pid, cpu_equivalents=used,
                active_cpu_slots=min(threads, max(1, math.ceil(used-.05)))))
    return dict(observed_utc=utc(), seconds=seconds, logical_cpus=os.cpu_count(),
        active_cpu_slots=sum(r['active_cpu_slots'] for r in rows), active_processes=rows)


def capacity(out, workers, phase, progress):
    tick = time.perf_counter(); consecutive = 0; samples = []
    while True:
        sample = cpu_snapshot(); samples.append(sample)
        eligible = sample['active_cpu_slots']+workers <= 12
        consecutive = consecutive+1 if eligible else 0
        progress(state='RUNNING' if consecutive >= 2 else 'WAITING_CAPACITY',
            phase='admission_'+phase, requested_workers=workers, active_slots=sample['active_cpu_slots'])
        if consecutive >= 2:
            row = dict(workers=workers, samples=samples, wait_seconds=time.perf_counter()-tick)
            save(out/(phase+'_admission.json'), row)
            return row
        time.sleep(3 if eligible else 30)


def task(item):
    folder, source_path = Path(item['folder']), Path(item['source'])
    cohort, block = item['cohort'], item['block']
    path = folder/f'{cohort}_{block:03d}.npz'; tick = time.perf_counter()
    try:
        if path.exists():
            raise FileExistsError(path)
        source = d.load_archive(source_path)
        raw = d.generate(source, cohort, block)
        with path.open('xb') as stream:
            np.savez_compressed(stream, **raw)
        del raw
        generated = time.perf_counter()-tick
        with np.load(path) as saved:
            raw = {key: saved[key] for key in saved.files}
        checked = audit(source, raw, cohort, block)
        save(path.with_suffix('.audit.json'), checked)
        replayed = time.perf_counter()-tick-generated
        summary = analysis.summarize(raw, source, block)
        save(path.with_suffix('.summary.json'), summary)
        return dict(block=block, cohort=cohort, path=str(path), passed=checked['passed'],
            checks=checked['checks_count'], generate_io_seconds=generated, replay_seconds=replayed,
            elapsed_seconds=time.perf_counter()-tick)
    except BaseException:
        save(path.with_suffix('.FAILED.json'), dict(failed_utc=utc(), error=traceback.format_exc()))
        raise


def compare(out):
    count = 0
    for b in range(4):
        paths = [out/'raw'/phase/f'engineering_{b:03d}.npz'
                 for phase in ('benchmark_serial', 'benchmark_parallel')]
        with np.load(paths[0]) as a, np.load(paths[1]) as b:
            assert set(a.files) == set(b.files)
            for key in a.files:
                np.testing.assert_array_equal(a[key], b[key]); count += 1
        for suffix in ('.audit.json', '.summary.json'):
            assert json.loads(paths[0].with_suffix(suffix).read_text()) == json.loads(paths[1].with_suffix(suffix).read_text())
    return count


def execute(out):
    assert SOURCE == out/'source', 'Execute frozen sources only'
    started = time.perf_counter(); config = json.loads((out/'config.json').read_text())
    status = dict(state='RUNNING', pid=os.getpid(), mode=config['mode'], phase='verification')
    admissions, groups, timings = {}, {}, {}
    def progress(**values):
        status.update(values, elapsed_seconds=time.perf_counter()-started, updated_utc=utc())
        save(out/'STATUS.json', status); print(json.dumps(status), flush=True)
    def admit(workers, phase):
        admissions[phase] = capacity(out, workers, phase, progress)
    def batch(phase, cohort, blocks, workers):
        folder = out/'raw'/phase; folder.mkdir(parents=True, exist_ok=False)
        results = []; elapsed = 0.
        waves = [blocks] if workers == 1 else [blocks[i:i+workers] for i in range(0, len(blocks), workers)]
        for wave, ids in enumerate(waves):
            admit(workers, phase+f'_wave{wave}'); verify(out, 'freeze.json')
            progress(state='RUNNING', phase=phase, workers=workers, completed_blocks=len(results), total_blocks=len(blocks))
            tick = time.perf_counter()
            items = [dict(folder=str(folder), source=str(out/'inputs'/f'{cohort}_{b:03d}.npz'),
                          cohort=cohort, block=b) for b in ids]
            def accept(row):
                assert row['passed']; results.append(row); progress(completed_blocks=len(results))
            if workers == 1:
                for item in items:
                    accept(task(item))
            else:
                with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
                    futures = [pool.submit(task, item) for item in items]
                    for future in as_completed(futures):
                        accept(future.result())
            elapsed += time.perf_counter()-tick
        record = dict(workers=workers, active_seconds=elapsed, tasks=sorted(results, key=lambda row: row['block']))
        save(out/(phase+'.json'), record)
        seal(out, phase+'_sha256.json', [out/(phase+'.json'), *sorted(folder.iterdir())])
        groups[phase] = record; timings[phase] = elapsed
        return record
    try:
        with (out/'EXECUTION.json').open('x') as stream:
            json.dump(dict(pid=os.getpid(), started_utc=utc()), stream)
        verify(out, 'freeze.json')
        assert config['settings'] == json.loads(json.dumps(d.settings()))
        assert config['python'] == sys.version and config['numpy'] == np.__version__
        assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
        assert checksum(Path(config['original'])/'checksums.json') == H035_MANIFEST
        verify(Path(config['original']), 'checksums.json')
        if config['smoke']:
            prior = Path(config['smoke']); verify(prior, 'checksums.json')
            assert checksum(prior/'checksums.json') == config['smoke_sha256']
        admit(1, 'fixtures'); progress(state='RUNNING', phase='fixtures', workers=1)
        tick = time.perf_counter(); fixtures = run_tests(out/'fixtures.log'); timings['fixtures'] = time.perf_counter()-tick
        if config['mode'] == 'smoke':
            group = batch('smoke', 'engineering', [0], 1)
            classification = 'ENGINEERING_ONLY'
        else:
            serial = batch('benchmark_serial', 'engineering', list(range(4)), 1)
            parallel = batch('benchmark_parallel', 'engineering', list(range(4)), 4)
            admit(1, 'benchmark_comparison'); progress(state='RUNNING', phase='benchmark_comparison', workers=1)
            count = compare(out)
            workers = 4 if parallel['active_seconds'] < .9*serial['active_seconds'] else 1
            decision = dict(workers=workers, serial_seconds=serial['active_seconds'],
                parallel_seconds=parallel['active_seconds'], exactly_equal_arrays=count,
                per_block_summaries_and_audits_equal=True, frozen_before_diagnostic=True,
                frozen_utc=utc(), rule='Four iff full matched parallel cost is below 90% of serial cost.')
            save(out/'worker_decision.json', decision)
            seal(out, 'decision_sha256.json', [out/'worker_decision.json', out/'benchmark_serial_sha256.json', out/'benchmark_parallel_sha256.json'])
            group = batch('diagnostic', 'pilot', list(range(8)), workers)
            classification = 'EXPOSED_COHORT_SERIAL_GUIDANCE_DIAGNOSIS'
        admit(1, 'analysis'); progress(state='RUNNING', phase='analysis', workers=1)
        tick = time.perf_counter()
        summaries = [json.loads(Path(r['path']).with_suffix('.summary.json').read_text()) for r in group['tasks']]
        summary = analysis.analyze(out, summaries, classification); timings['analysis'] = time.perf_counter()-tick
        verify(out, 'freeze.json'); verify(Path(config['original']), 'checksums.json')
        for manifest in sorted(out.glob('*_sha256.json')):
            verify(out, manifest.name)
        save(out/'execution_summary.json', dict(timings=timings, fixtures=fixtures, groups=groups,
            capacity_wait_seconds=sum(v['wait_seconds'] for v in admissions.values()),
            independent_audit_checks=sum(r['checks'] for group in groups.values() for r in group['tasks']),
            original_h035_unchanged=True, writer_changes=False, prior_verdicts_changed=False, predictor_fits=0,
            private_material=False, manuscript_edit=False, next_campaign_launched=False))
        progress(state='COMPLETE', phase='complete', workers=0, integrity_passed=True,
            classification=summary['classification'], completed_utc=utc())
        save(out/'COMPLETE.json', status)
        seal(out, 'checksums.json', sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'checksums.json'))
        verify(out, 'checksums.json')
    except BaseException:
        progress(state='FAILED', failed_utc=utc(), error=traceback.format_exc())
        save(out/'FAILED.json', status)
        raise


def prepare(mode, version):
    out = SOURCE/'runs'/f'h038_{mode}_{version}'
    occupied = [out, out.with_suffix('.log'), out.with_suffix('.pid'), out.with_name(out.name+'_launch.json')]
    if any(p.exists() for p in occupied):
        raise FileExistsError('Refusing occupied H038 destination')
    original = SOURCE/'runs/h035_pilot_v1'
    assert checksum(original/'checksums.json') == H035_MANIFEST
    verify(original, 'checksums.json')
    for name in ('model.py', 'h035/design.py', 'h035/experiment.py', 'h035/audit.py'):
        assert checksum(SOURCE/name) == checksum(original/'source'/name), 'H035 scientific source changed: '+name
    smoke = None; forecast = 300.
    if mode == 'diagnostic':
        smoke = SOURCE/'runs'/f'h038_smoke_{version}'
        verify(smoke, 'checksums.json')
        complete = json.loads((smoke/'COMPLETE.json').read_text())
        execution = json.loads((smoke/'execution_summary.json').read_text())
        assert complete['state'] == 'COMPLETE' and complete['integrity_passed']
        for name in FILES:
            assert checksum(SOURCE/name) == checksum(smoke/'source'/name), 'Source changed since smoke: '+name
        compute = complete['elapsed_seconds']-execution['capacity_wait_seconds']
        forecast = compute*16*1.25+60
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        target = out/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE/name, target)
    shutil.copyfile(SOURCE.parent/'RUN_POLICY.md', out/'RUN_POLICY.md')
    (out/'inputs').mkdir()
    bindings = {}
    cohorts = [('engineering', 'benchmark_serial', range(4)), ('pilot', 'pilot', range(8))]
    if mode == 'smoke':
        cohorts = [('engineering', 'benchmark_serial', [0])]
    for cohort, phase, blocks in cohorts:
        for b in blocks:
            name = f'{cohort}_{b:03d}.npz'; source = original/'raw'/phase/name
            shutil.copyfile(source, out/'inputs'/name)
            bindings[name] = dict(h035_source=str(source), h035_sha256=checksum(source),
                frozen_input_sha256=checksum(out/'inputs'/name))
    save(out/'input_bindings.json', bindings)
    config = dict(experiment='H038', mode=mode, settings=d.settings(), prepared_utc=utc(),
        python=sys.version, numpy=np.__version__, forecast_seconds=forecast,
        forecast_basis='Smoke: 300s engineering allowance. Full: 16 full smoke work costs excluding capacity waits, plus 25% and 60s, without assumed parallel speedup.',
        original=str(original), original_manifest_sha256=H035_MANIFEST,
        smoke=str(smoke) if smoke else None, smoke_sha256=checksum(smoke/'checksums.json') if smoke else None,
        candidate_workers=[1, 4], shared_cpu_limit=12, numerical_threads=1, private_material=False,
        confirmation=False, predictor_fits=0, manuscript_edit=False)
    save(out/'config.json', config)
    seal(out, 'freeze.json', sorted(p for p in out.rglob('*') if p.is_file()))
    save(out/'STATUS.json', dict(state='PREPARED', mode=mode, phase='source_frozen'))
    return out, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['smoke', 'diagnostic'])
    parser.add_argument('--version', default='v1')
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    if args.run:
        execute(args.run.resolve()); return
    if not args.mode or not re.fullmatch(r'[a-zA-Z0-9_]+', args.version):
        parser.error('Mode and simple version required')
    out, config = prepare(args.mode, args.version)
    detached = config['forecast_seconds'] > 600
    command = [sys.executable, '-B', str(out/'source/h038/workflow.py'), '--run', str(out)]
    with out.with_suffix('.log').open('xb') as stream:
        process = subprocess.Popen(command, cwd=SOURCE, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    out.with_suffix('.pid').write_text(str(process.pid)+'\n')
    ledger = dict(state='LAUNCHED', pid=process.pid, command=command, output=str(out),
        launched_utc=utc(), detached=detached, new_session=True, forecast_seconds=config['forecast_seconds'],
        capacity_wait_additional=True, freeze_sha256=checksum(out/'freeze.json'))
    save(out.with_name(out.name+'_launch.json'), ledger); print(json.dumps(ledger), flush=True)
    if not detached:
        code = process.wait(); print(json.dumps(dict(output=str(out), returncode=code)), flush=True)
        if code:
            raise SystemExit(code)


if __name__ == '__main__':
    main()
