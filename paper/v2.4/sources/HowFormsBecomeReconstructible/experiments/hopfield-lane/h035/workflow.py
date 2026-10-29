"""Freeze and execute the bounded H035 smoke, benchmark and pilot workflow."""
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
from h035 import design as d, experiment as e, analysis
from h035.audit import audit
from h035.fixtures import run_tests

FILES = ['model.py', 'h007/io.py', 'run_python.sh', 'requirements.txt'] + [
    'h035/'+name for name in ('design.py', 'experiment.py', 'audit.py', 'analysis.py',
                              'fixtures.py', 'workflow.py', 'PROTOCOL.md')]


def utc():
    return datetime.now(timezone.utc).isoformat()


def cpu_snapshot():
    """Count partly scheduled active processes separately, under 12 slots."""
    def snapshot():
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
    first = snapshot(); start = time.monotonic(); time.sleep(1.); second = snapshot()
    elapsed = time.monotonic()-start; hz = os.sysconf('SC_CLK_TCK')
    rows = []
    for pid, (ticks, threads, born) in second.items():
        previous = first.get(pid)
        # A new process contributes its lifetime ticks only if born during
        # this sample. PID reuse cannot borrow ticks from an older process.
        prior = previous[0] if previous and previous[2] == born else 0
        used = max(0, ticks-prior)/hz/elapsed
        if used >= .05:
            rows.append(dict(pid=pid, cpu_equivalents=used,
                             active_cpu_slots=min(threads, max(1, math.ceil(used-.05)))))
    return dict(observed_utc=utc(), sample_seconds=elapsed, logical_cpus=os.cpu_count(),
        active_cpu_slots=sum(row['active_cpu_slots'] for row in rows), active_processes=rows)


def capacity(out, workers, phase, progress):
    start = time.monotonic(); consecutive = 0; samples = []
    while True:
        sample = cpu_snapshot(); samples.append(sample)
        eligible = sample['active_cpu_slots']+workers <= 12
        consecutive = consecutive+1 if eligible else 0
        progress(state='RUNNING' if consecutive >= 2 else 'WAITING_CAPACITY',
                 phase='admission_'+phase, requested_workers=workers, active_slots=sample['active_cpu_slots'])
        if consecutive >= 2:
            result = dict(workers=workers, samples=samples, wait_seconds=time.monotonic()-start)
            save(out/(phase+'_admission.json'), result)
            return result
        time.sleep(3. if eligible else 30.)


def task(item):
    out, cohort, block = Path(item['out']), item['cohort'], item['block']
    path = out/f'{cohort}_{block:03d}.npz'
    started = time.perf_counter()
    try:
        if path.exists():
            raise FileExistsError(path)
        data = e.lineage(cohort, block)
        with path.open('xb') as stream:
            np.savez_compressed(stream, **data)
        del data
        generated = time.perf_counter()-started
        with np.load(path) as saved:
            data = {name: saved[name] for name in saved.files}
        result = audit(data, cohort, block)
        save(path.with_suffix('.audit.json'), result)
        return dict(block=block, cohort=cohort, path=str(path), checks=result['checks_count'],
            passed=result['passed'], generation_and_io_seconds=generated,
            audit_seconds=time.perf_counter()-started-generated, elapsed_seconds=time.perf_counter()-started)
    except BaseException:
        save(path.with_suffix('.FAILED.json'), dict(failed_utc=utc(), error=traceback.format_exc()))
        raise


def compare(out):
    count = 0
    for block in d.BENCHMARK_BLOCKS:
        paths = [out/'raw'/phase/f'engineering_{block:03d}.npz'
                 for phase in ('benchmark_serial', 'benchmark_parallel')]
        with np.load(paths[0]) as a, np.load(paths[1]) as b:
            assert set(a.files) == set(b.files)
            for name in a.files:
                np.testing.assert_array_equal(a[name], b[name]); count += 1
        assert json.loads(paths[0].with_suffix('.audit.json').read_text()) == json.loads(paths[1].with_suffix('.audit.json').read_text())
    return count


def execute(out):
    if SOURCE != out/'source':
        raise ValueError('Execute only the frozen source snapshot')
    started = time.perf_counter(); config = json.loads((out/'config.json').read_text())
    status = dict(state='RUNNING', pid=os.getpid(), mode=config['mode'], phase='verification')
    timings, admissions, groups = {}, {}, {}
    def progress(**values):
        status.update(values, elapsed_seconds=time.perf_counter()-started, updated_utc=utc())
        save(out/'STATUS.json', status); print(json.dumps(status), flush=True)
    def admit(workers, phase):
        admissions[phase] = capacity(out, workers, phase, progress)
    def batch(phase, cohort, blocks, workers):
        folder = out/'raw'/phase; folder.mkdir(parents=True, exist_ok=False)
        results = []; active_seconds = 0.
        # Recheck shared capacity between bounded waves. Admission time is
        # retained separately from full generation/I/O/audit benchmark cost.
        waves = [list(blocks)] if workers == 1 else [list(blocks[i:i+workers]) for i in range(0, len(blocks), workers)]
        for wave, ids in enumerate(waves):
            admit(workers, phase+f'_wave{wave}'); verify(out, 'freeze.json')
            progress(state='RUNNING', phase=phase, workers=workers, completed_blocks=len(results), total_blocks=len(blocks))
            tick = time.perf_counter()
            items = [dict(out=str(folder), cohort=cohort, block=b) for b in ids]
            def accept(row):
                assert row['passed']; results.append(row)
                progress(completed_blocks=len(results))
            if workers == 1:
                for item in items:
                    accept(task(item))
            else:
                with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
                    jobs = [pool.submit(task, item) for item in items]
                    for job in as_completed(jobs):
                        accept(job.result())
            active_seconds += time.perf_counter()-tick
        results.sort(key=lambda row: row['block'])
        record = dict(workers=workers, active_seconds=active_seconds, tasks=results)
        save(out/(phase+'.json'), record)
        seal(out, phase+'_sha256.json', [out/(phase+'.json'), *sorted(folder.iterdir())])
        timings[phase] = active_seconds; groups[phase] = record
        return record
    try:
        with (out/'EXECUTION.json').open('x') as stream:
            json.dump(dict(pid=os.getpid(), started_utc=utc()), stream)
        verify(out, 'freeze.json')
        assert config['settings'] == json.loads(json.dumps(d.settings()))
        assert config['numpy'] == np.__version__ and config['python'] == sys.version
        assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
        if config['smoke']:
            prior = Path(config['smoke']); verify(prior, 'checksums.json')
            assert checksum(prior/'checksums.json') == config['smoke_checksums_sha256']
        admit(1, 'fixtures'); progress(state='RUNNING', phase='fixtures', workers=1)
        tick = time.perf_counter(); fixtures = run_tests(out/'fixtures.log'); timings['fixtures'] = time.perf_counter()-tick
        if config['mode'] == 'smoke':
            group = batch('smoke', 'engineering', [0], 1)
            classification = 'ENGINEERING_ONLY'
        else:
            serial = batch('benchmark_serial', 'engineering', list(d.BENCHMARK_BLOCKS), 1)
            parallel = batch('benchmark_parallel', 'engineering', list(d.BENCHMARK_BLOCKS), 4)
            admit(1, 'benchmark_comparison'); progress(state='RUNNING', phase='benchmark_comparison', workers=1)
            equal_arrays = compare(out)
            workers = 4 if parallel['active_seconds'] < .9*serial['active_seconds'] else 1
            selected = parallel if workers == 4 else serial
            decision = dict(workers=workers, serial_seconds=serial['active_seconds'],
                parallel_seconds=parallel['active_seconds'], exactly_equal_arrays=equal_arrays,
                rule='Four iff full four-block parallel generation/I/O/audit cost is below 90% of serial.',
                frozen_before_pilot=True, frozen_utc=utc(),
                pilot_compute_forecast_seconds=selected['active_seconds']*2*1.25+60,
                capacity_wait_additional=True)
            save(out/'worker_decision.json', decision)
            seal(out, 'decision_sha256.json', [out/'worker_decision.json', out/'benchmark_serial_sha256.json', out/'benchmark_parallel_sha256.json'])
            group = batch('pilot', 'pilot', list(d.PILOT_BLOCKS), workers)
            classification = d.CLASSIFICATION
        admit(1, 'analysis'); progress(state='RUNNING', phase='analysis', workers=1)
        tick = time.perf_counter()
        summary = analysis.analyze(out, [Path(row['path']) for row in group['tasks']], classification)
        timings['analysis'] = time.perf_counter()-tick
        verify(out, 'freeze.json')
        for manifest in sorted(out.glob('*_sha256.json')):
            verify(out, manifest.name)
        save(out/'execution_summary.json', dict(timings=timings, fixtures=fixtures, groups=groups,
            capacity_wait_seconds=sum(v['wait_seconds'] for v in admissions.values()),
            independent_audit_checks=sum(row['checks'] for group in groups.values() for row in group['tasks']),
            prior_verdicts_changed=False, predictor_fits=0, private_material=False,
            manuscript_edit=False, next_campaign_launched=False))
        progress(state='COMPLETE', phase='complete', integrity_passed=True, workers=0,
            scientific_classification=classification, development_verdict=summary['development_screens']['verdict'],
            completed_utc=utc())
        save(out/'COMPLETE.json', status)
        seal(out, 'checksums.json', sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'checksums.json'))
        verify(out, 'checksums.json')
    except BaseException:
        progress(state='FAILED', phase=status.get('phase'), error=traceback.format_exc(), failed_utc=utc())
        save(out/'FAILED.json', status)
        raise


def prepare(lane, mode, version):
    out = lane/'runs'/f'h035_{mode}_{version}'
    paths = [out, out.with_suffix('.log'), out.with_suffix('.pid'), out.with_name(out.name+'_launch.json')]
    if any(p.exists() for p in paths):
        raise FileExistsError('Refusing occupied H035 destination')
    smoke = None; forecast = 180.; administrative_changes = {}; smoke_compute = None
    if mode == 'pilot':
        smoke = lane/'runs'/f'h035_smoke_{version}'
        verify(smoke, 'checksums.json')
        complete = json.loads((smoke/'COMPLETE.json').read_text())
        assert complete['state'] == 'COMPLETE' and complete['integrity_passed']
        for name in FILES:
            before, after = checksum(smoke/'source'/name), checksum(lane/name)
            if before != after:
                # Recorded pre-pilot administrative amendment: correct the
                # runtime forecast's treatment of capacity waits. Model,
                # analysis, audit, fixtures and all settings stay byte-exact.
                assert name in ('h035/workflow.py', 'h035/PROTOCOL.md'), 'Scientific source changed since smoke: '+name
                administrative_changes[name] = dict(smoke_sha256=before, pilot_sha256=after)
        # Sixteen complete block executions (4 serial + 4 parallel + 8 pilot)
        # at observed full-wrapper serial cost, without assuming any speedup.
        execution = json.loads((smoke/'execution_summary.json').read_text())
        smoke_compute = complete['elapsed_seconds']-execution['capacity_wait_seconds']
        assert smoke_compute >= execution['timings']['smoke'] > 0
        forecast = smoke_compute*16*1.25+60
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        target = out/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(lane/name, target)
    shutil.copyfile(lane.parent/'RUN_POLICY.md', out/'RUN_POLICY.md')
    config = dict(experiment='H035', mode=mode, settings=d.settings(), prepared_utc=utc(),
        python=sys.version, numpy=np.__version__, forecast_seconds=forecast,
        forecast_basis='Smoke: conservative 180s engineering allowance using prior binary model costs. Pilot: 16 block executions at full smoke work cost excluding measured capacity waits, plus 25% and 60s; no assumed parallel speedup. New capacity waits are additional.',
        smoke_compute_seconds=smoke_compute, administrative_changes_since_smoke=administrative_changes,
        smoke=str(smoke) if smoke else None, smoke_checksums_sha256=checksum(smoke/'checksums.json') if smoke else None,
        candidate_workers=[1, 4], numerical_threads=1, shared_cpu_limit=12,
        pilot_networks=8, private_material=False, confirmation=False,
        prior_verdicts_changed=False, predictor_fits=0, manuscript_edit=False)
    save(out/'config.json', config)
    seal(out, 'freeze.json', sorted(p for p in out.rglob('*') if p.is_file()))
    save(out/'STATUS.json', dict(state='PREPARED', mode=mode, phase='source_frozen'))
    return out, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['smoke', 'pilot'])
    parser.add_argument('--version', default='v1')
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    if args.run:
        execute(args.run.resolve()); return
    if not args.mode or not re.fullmatch(r'[a-zA-Z0-9_]+', args.version):
        parser.error('A mode and simple version are required')
    out, config = prepare(SOURCE, args.mode, args.version)
    detached = config['forecast_seconds'] > 600
    command = [sys.executable, '-B', str(out/'source/h035/workflow.py'), '--run', str(out)]
    with out.with_suffix('.log').open('xb') as stream:
        process = subprocess.Popen(command, cwd=SOURCE, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    out.with_suffix('.pid').write_text(str(process.pid)+'\n')
    ledger = dict(state='LAUNCHED', pid=process.pid, command=command, launched_utc=utc(),
        output=str(out), detached=detached, new_session=True, forecast_seconds=config['forecast_seconds'],
        capacity_wait_additional=True, freeze_sha256=checksum(out/'freeze.json'))
    save(out.with_name(out.name+'_launch.json'), ledger)
    print(json.dumps(ledger), flush=True)
    if not detached:
        code = process.wait()
        print(json.dumps(dict(output=str(out), returncode=code)), flush=True)
        if code:
            raise SystemExit(code)


if __name__ == '__main__':
    main()
