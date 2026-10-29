"""Frozen fresh-input generation, matched benchmarks and confirmation execution."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
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
from h035 import experiment as baseline
from h038 import experiment as e
from h038.audit import audit
from h038.workflow import capacity
from h039 import design as d, analysis
from h039.fixtures import run_tests

UNCHANGED = ['model.py', 'h007/io.py', 'run_python.sh', 'requirements.txt',
    'h035/design.py', 'h035/experiment.py', 'h035/audit.py',
    'h038/experiment.py', 'h038/audit.py', 'h038/analysis.py',
    'h038/fixtures.py', 'h038/workflow.py']
FILES = [*UNCHANGED, 'h039/design.py', 'h039/plan.py', 'h039/SAMPLE_SIZE.json',
    'h039/inference.py', 'h039/analysis.py', 'h039/fixtures.py', 'h039/workflow.py', 'h039/PROTOCOL.md']
H038_MANIFEST = 'd14f6193e8952688aecc30bd31abe533545a819ced97c25a72d1885d8143b48e'


def utc():
    return datetime.now(timezone.utc).isoformat()


def arrays_equal(actual, expected):
    assert set(actual) == set(expected)
    for key in actual:
        np.testing.assert_array_equal(actual[key], expected[key])
    return len(actual)


def task(item):
    out = Path(item['out']); phase = item['phase']; cohort, block = item['cohort'], item['block']
    name = f'{cohort}_{block:03d}.npz'
    path = out/'raw'/phase/name; input_path = out/'inputs'/phase/name
    tick = time.perf_counter()
    try:
        assert not path.exists() and not input_path.exists()
        started = utc()
        source = baseline.lineage(cohort, block)
        fingerprint = hashlib.sha256(source['base'].tobytes()).hexdigest()
        if cohort == 'pilot':
            assert block in item['confirmation_blocks'] and fingerprint not in item['development_bases']
        else:
            assert cohort == 'engineering' and block in range(4)
        with input_path.open('xb') as stream:
            np.savez_compressed(stream, **source)
        save(input_path.with_suffix('.generation.json'), dict(started_utc=started, completed_utc=utc(),
            cohort=cohort, block=block, base_sha256=fingerprint, input_sha256=checksum(input_path),
            fresh_confirmation=cohort == 'pilot', generated_after_source_freeze=True))
        raw = e.generate(source, cohort, block)
        with path.open('xb') as stream:
            np.savez_compressed(stream, **raw)
        del raw
        generation_seconds = time.perf_counter()-tick
        raw = e.load_archive(path)
        checked = audit(source, raw, cohort, block)
        matched = 0
        if cohort == 'engineering':
            matched += arrays_equal(source, e.load_archive(out/'reference/inputs'/name))
            matched += arrays_equal(raw, e.load_archive(out/'reference/raw'/name))
        checked.update(exposed_reference_arrays_equal=matched, fresh_base_separation_passed=True)
        save(path.with_suffix('.audit.json'), checked)
        replay_seconds = time.perf_counter()-tick-generation_seconds
        summary = analysis.summarize(raw, source, block)
        save(path.with_suffix('.summary.json'), summary)
        return dict(block=block, cohort=cohort, path=str(path), input_path=str(input_path),
            passed=checked['passed'], checks=checked['checks_count'], base_sha256=fingerprint,
            exposed_reference_arrays_equal=matched, generate_io_seconds=generation_seconds,
            replay_seconds=replay_seconds, elapsed_seconds=time.perf_counter()-tick)
    except BaseException:
        save(path.with_suffix('.FAILED.json'), dict(failed_utc=utc(), error=traceback.format_exc()))
        raise


def compare(out):
    arrays = 0
    for block in range(4):
        name = f'engineering_{block:03d}.npz'
        for folder in ('inputs', 'raw'):
            paths = [out/folder/phase/name for phase in ('benchmark_serial', 'benchmark_parallel')]
            arrays += arrays_equal(e.load_archive(paths[0]), e.load_archive(paths[1]))
        for suffix in ('.audit.json', '.summary.json'):
            paths = [out/'raw'/phase/Path(name).with_suffix(suffix) for phase in ('benchmark_serial', 'benchmark_parallel')]
            assert json.loads(paths[0].read_text()) == json.loads(paths[1].read_text())
    return arrays


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
        for folder in ('raw', 'inputs'):
            (out/folder/phase).mkdir(parents=True, exist_ok=False)
        results = []; elapsed = 0.
        for wave, start in enumerate(range(0, len(blocks), workers)):
            ids = blocks[start:start+workers]
            admit(workers, phase+f'_wave{wave}'); verify(out, 'freeze.json')
            if cohort == 'pilot':
                verify(out, 'decision_sha256.json')
            progress(state='RUNNING', phase=phase, workers=workers, completed_blocks=len(results), total_blocks=len(blocks))
            tick = time.perf_counter()
            items = [dict(out=str(out), phase=phase, cohort=cohort, block=b,
                confirmation_blocks=config['settings']['confirmation_blocks'], development_bases=config['development_bases']) for b in ids]
            def accept(row):
                assert row['passed']; results.append(row); progress(completed_blocks=len(results))
            if workers == 1:
                for item in items:
                    accept(task(item))
            else:
                with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
                    for future in as_completed([pool.submit(task, item) for item in items]):
                        accept(future.result())
            elapsed += time.perf_counter()-tick
        assert len({r['base_sha256'] for r in results}) == len(results)
        record = dict(workers=workers, active_seconds=elapsed, tasks=sorted(results, key=lambda r: r['block']))
        save(out/(phase+'.json'), record)
        seal(out, phase+'_sha256.json', [out/(phase+'.json'),
            *sorted((out/'raw'/phase).iterdir()), *sorted((out/'inputs'/phase).iterdir())])
        groups[phase] = record; timings[phase] = elapsed
        return record
    try:
        with (out/'EXECUTION.json').open('x') as stream:
            json.dump(dict(pid=os.getpid(), started_utc=utc()), stream)
        verify(out, 'freeze.json')
        assert config['settings'] == json.loads(json.dumps(d.settings(config['sample_size']['blocks'])))
        assert config['python'] == sys.version and config['numpy'] == np.__version__
        assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
        assert checksum(Path(config['original'])/'checksums.json') == H038_MANIFEST
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
            decision = dict(workers=workers, serial_seconds=serial['active_seconds'], parallel_seconds=parallel['active_seconds'],
                exactly_equal_arrays=count, per_block_summaries_and_audits_equal=True, frozen_before_confirmation=True,
                frozen_utc=utc(), rule='Four iff full matched parallel cost is below 90% of serial cost.')
            save(out/'worker_decision.json', decision)
            seal(out, 'decision_sha256.json', [out/'worker_decision.json', out/'benchmark_serial_sha256.json', out/'benchmark_parallel_sha256.json'])
            group = batch('confirmation', 'pilot', config['settings']['confirmation_blocks'], workers)
            classification = d.CLASSIFICATION
        admit(1, 'analysis'); progress(state='RUNNING', phase='analysis', workers=1)
        verify(out, 'freeze.json')
        for manifest in sorted(out.glob('*_sha256.json')):
            verify(out, manifest.name)
        tick = time.perf_counter()
        summaries = [json.loads(Path(r['path']).with_suffix('.summary.json').read_text()) for r in group['tasks']]
        summary = analysis.analyze(out, summaries, classification); timings['analysis'] = time.perf_counter()-tick
        verify(out, 'freeze.json'); verify(Path(config['original']), 'checksums.json')
        save(out/'execution_summary.json', dict(timings=timings, fixtures=fixtures, groups=groups,
            capacity_wait_seconds=sum(v['wait_seconds'] for v in admissions.values()),
            independent_audit_checks=sum(r['checks'] for group in groups.values() for r in group['tasks']),
            original_h038_unchanged=True, writer_changes=False, prior_verdicts_changed=False, predictor_fits=0,
            private_material=False, manuscript_edit=False, next_campaign_launched=False))
        progress(state='COMPLETE', phase='complete', workers=0, integrity_passed=True,
            classification=summary['classification'], completed_utc=utc(),
            verdicts=summary['inference']['decisions'])
        save(out/'COMPLETE.json', status)
        seal(out, 'checksums.json', sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'checksums.json'))
        verify(out, 'checksums.json')
    except BaseException:
        progress(state='FAILED', failed_utc=utc(), error=traceback.format_exc())
        save(out/'FAILED.json', status)
        raise


def prepare(mode, version):
    out = SOURCE/'runs'/f'h039_{mode}_{version}'
    occupied = [out, out.with_suffix('.log'), out.with_suffix('.pid'), out.with_name(out.name+'_launch.json')]
    if any(p.exists() for p in occupied):
        raise FileExistsError('Refusing occupied H039 destination')
    original = SOURCE/'runs/h038_diagnostic_v1'
    assert checksum(original/'checksums.json') == H038_MANIFEST
    verify(original, 'checksums.json')
    for name in UNCHANGED:
        assert checksum(SOURCE/name) == checksum(original/'source'/name), 'Scientific source changed: '+name
    plan = json.loads((SOURCE/'h039/SAMPLE_SIZE.json').read_text())
    assert plan['blocks'] == 88 and plan['block_ids'] == list(range(d.FIRST_BLOCK, d.FIRST_BLOCK+88))
    assert plan['development_manifest_sha256'] == H038_MANIFEST
    if mode == 'confirmation':
        matches = list((SOURCE/'runs').rglob('pilot_39039*.npz'))
        if matches:
            raise AssertionError('Confirmation namespace already exposed: '+str(matches[:3]))
    smoke = None; forecast = 300.
    if mode == 'confirmation':
        smoke = SOURCE/'runs'/f'h039_smoke_{version}'
        verify(smoke, 'checksums.json')
        complete = json.loads((smoke/'COMPLETE.json').read_text())
        execution = json.loads((smoke/'execution_summary.json').read_text())
        assert complete['state'] == 'COMPLETE' and complete['integrity_passed']
        for name in FILES:
            assert checksum(SOURCE/name) == checksum(smoke/'source'/name), 'Source changed since smoke: '+name
        compute = complete['elapsed_seconds']-execution['capacity_wait_seconds']
        forecast = compute*(plan['blocks']+8)*1.25+60
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        target = out/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE/name, target)
    shutil.copyfile(SOURCE.parent/'RUN_POLICY.md', out/'RUN_POLICY.md')
    (out/'reference/inputs').mkdir(parents=True)
    (out/'reference/raw').mkdir(parents=True)
    bindings = {}; bases = []
    for path in sorted((original/'inputs').glob('*.npz')):
        with np.load(path) as source:
            bases.append(hashlib.sha256(source['base'].tobytes()).hexdigest())
    assert len(bases) == len(set(bases)) == 12
    for b in ([0] if mode == 'smoke' else range(4)):
        name = f'engineering_{b:03d}.npz'
        for kind, parent in (('inputs', original/'inputs'), ('raw', original/'raw/benchmark_serial')):
            source = parent/name; target = out/'reference'/kind/name
            shutil.copyfile(source, target)
            bindings[str(target.relative_to(out))] = dict(source=str(source), sha256=checksum(source))
    save(out/'reference_bindings.json', bindings)
    config = dict(experiment='H039', mode=mode, settings=d.settings(plan['blocks']), sample_size=plan,
        prepared_utc=utc(), python=sys.version, numpy=np.__version__, forecast_seconds=forecast,
        forecast_basis='Smoke: 300s allowance. Full: (88+8) full smoke work costs excluding waits, plus 25% and 60s; no assumed parallel speedup.',
        original=str(original), original_manifest_sha256=H038_MANIFEST, development_bases=bases,
        smoke=str(smoke) if smoke else None, smoke_sha256=checksum(smoke/'checksums.json') if smoke else None,
        candidate_workers=[1, 4], shared_cpu_limit=12, numerical_threads=1, private_material=False,
        confirmation=mode == 'confirmation', predictor_fits=0, manuscript_edit=False,
        confirmation_inputs_generated_at_prepare=False)
    save(out/'config.json', config)
    seal(out, 'freeze.json', sorted(p for p in out.rglob('*') if p.is_file()))
    save(out/'STATUS.json', dict(state='PREPARED', mode=mode, phase='source_frozen'))
    return out, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['smoke', 'confirmation'])
    parser.add_argument('--version', default='v1')
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    if args.run:
        execute(args.run.resolve()); return
    if not args.mode or not re.fullmatch(r'[a-zA-Z0-9_]+', args.version):
        parser.error('Mode and simple version required')
    out, config = prepare(args.mode, args.version)
    detached = config['forecast_seconds'] > 600
    command = [sys.executable, '-B', str(out/'source/h039/workflow.py'), '--run', str(out)]
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
