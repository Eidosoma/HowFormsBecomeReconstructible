"""Freeze, check, benchmark and detach the authorized conditional-future diagnosis."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
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
from h019.audit import load
from h021.launch import cpu_snapshot
from h021.recovery import wait_for_capacity
from h034 import design as d, measure, analysis

NEW_FILES = ['h034/'+name for name in ('design.py', 'measure.py', 'analysis.py',
                                     'workflow.py', 'fixtures.py', 'PROTOCOL.md', 'README.md')]


def utc():
    return datetime.now(timezone.utc).isoformat()


def prepare(lane, out):
    """Freeze code and the fixed launch plan; defer data work until admission."""
    prior = lane/'runs/h033_prediction_v1'
    complete = json.loads((prior/'COMPLETE.json').read_text())
    evaluation = json.loads((prior/'evaluation.json').read_text())
    assert complete['qualified'] and complete['state'] == 'COMPLETE'
    assert evaluation['verdict'] == 'NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE'
    assert evaluation['observation_verdict'] == 'NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN'
    out.mkdir(exist_ok=False)
    try:
        for path in sorted((prior/'source').rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(prior/'source')
            if path.suffix == '.py' or path.name in ('PROTOCOL.md', 'run_python.sh', 'requirements.txt'):
                assert checksum(lane/relative) == checksum(path), str(relative)
            target = out/'source'/relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        for name in NEW_FILES:
            target = out/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(lane/name, target)
        shutil.copyfile(lane.parent/'RUN_POLICY.md', out/'RUN_POLICY.md')
        bindings = {str(prior/name): checksum(prior/name) for name in
                    ('checksums.json', 'COMPLETE.json', 'evaluation.json', 'prediction_sha256.json')}
        for name in ('.cache/h033_closeout_v1.json', '.cache/h033_diagnosis_v1.json',
                     'runs/h031_prediction_v1/evaluation.json', 'runs/h031_prediction_v1/COMPLETE.json'):
            bindings[str(lane/name)] = checksum(lane/name)
        save(out/'external_bindings.json', bindings)
        old = json.loads((prior/'benchmark_serial.json').read_text())['tasks']
        unit = max(row['elapsed_seconds']/d.prior_design.old.CELLS[int(row['name'].split('_')[1][1:])][1] for row in old)
        # Worst cell recovery interval; matched benchmarks replace this upper forecast.
        forecast = (809/d.CHUNK*3+2*10.5)*unit*1.5+900
        config = dict(experiment='H034', label=d.LABEL, root=d.SEED, prior=str(prior),
            selected_prefixes=809, early_disagreement_prefixes=dict(train=227, test=198),
            agreement_controls_per_panel=d.CONTROLS,
            futures_per_prefix=d.TAILS, paths=809*2*d.TAILS,
            observed_replacements=6, final_replacement=24, scoring_endpoints=list(range(13, 25)),
            dt=d.DTS, models=d.MODELS, model_fits=0, candidate_workers=[1, 4], numerical_threads=1,
            initial_compute_forecast_seconds=forecast,
            forecast_note='Conservative serial upper forecast using the maximum H033 full-pipeline benchmark time per recovery-time unit and worst-cell recovery interval, scaled by prefix count, plus 50% overhead and 900s. Matched continuation benchmarks replace it; capacity waiting is additional.',
            prepared_utc=utc(), python=sys.version, numpy=np.__version__, private_material=False,
            selection_uses_observation_only=True, cohorts_previously_exposed=True,
            prior_verdicts_changed=False, manuscript_edit=False)
        save(out/'launch_config.json', config)
        seal(out, 'source_sha256.json', sorted(p for p in out.rglob('*') if p.is_file()))
        save(out/'STATUS.json', dict(state='PREPARED', phase='source_frozen', label=d.LABEL))
    except Exception:
        failure = dict(state='FAILED', phase='preparation', error=traceback.format_exc(), failed_utc=utc())
        save(out/'FAILED.json', failure); save(out/'STATUS.json', failure)
        raise


def prepare_data(out, launch_config):
    verify(out, 'source_sha256.json')
    prior = Path(launch_config['prior']); verify(prior, 'checksums.json')
    tasks, benchmark, selection = d.prepare_inputs(prior, out)
    save(out/'selection.json', selection)
    early = {split: sum(p['early_disagreement'] for p in selection['panels'][split])
             for split in ('train', 'test')}
    assert early == launch_config['early_disagreement_prefixes']
    assert sum(t['pairs'] for t in tasks) == launch_config['selected_prefixes']
    main_clock = sum(t['interval']*t['pairs']/d.CHUNK for t in tasks)
    bench_clock = sum(t['interval'] for t in benchmark)
    config = dict(launch_config, tasks=tasks, benchmark=benchmark,
                  benchmark_main_scale=main_clock/bench_clock, inputs_frozen_utc=utc())
    save(out/'config.json', config)
    paths = [out/name for name in json.loads((out/'source_sha256.json').read_text())]
    paths += [out/name for name in ('source_sha256.json', 'config.json', 'selection.json')]
    paths += sorted((out/'inputs').glob('*.npz'))
    seal(out, 'freeze.json', paths)
    verify(out, 'freeze.json')
    return config


def external_check(out, full=False):
    bindings = json.loads((out/'external_bindings.json').read_text())
    for path, digest in bindings.items():
        assert checksum(path) == digest, path
    if full:
        prior = Path(json.loads((out/'launch_config.json').read_text())['prior'])
        verify(prior, 'checksums.json')


def reproduce(out, config):
    prior = Path(config['prior']); count = 0
    selected = json.loads((out/'selection.json').read_text())
    for split in ('train', 'test'):
        rows, early = d.scan(prior, split)
        expected, panels = d.choose(rows, early, split)
        assert expected == selected['rows'][split] and panels == selected['panels'][split]
    for spec in config['tasks']+config['benchmark']:
        benchmark = spec in config['benchmark']
        actual = load(out/'inputs'/f'{spec["name"]}.npz')
        expected = d.pack(prior, spec['rows'], benchmark=benchmark)
        assert actual.keys() == expected.keys()
        for key in actual:
            np.testing.assert_array_equal(actual[key], expected[key]); count += 1
    return dict(arrays_exactly_reproduced=count, selection_exactly_reproduced=True)


def compare_benchmarks(out, specs):
    count = 0
    for spec in specs:
        a, b = [out/'raw'/(spec['name']+'_'+mode) for mode in ('serial', 'parallel')]
        for name in ('raw_0.npz', 'raw_1.npz', 'raw_2.npz', 'outcomes.npz'):
            x, y = load(a/name), load(b/name)
            assert x.keys() == y.keys()
            for key in x:
                np.testing.assert_array_equal(x[key], y[key]); count += 1
        assert json.loads((a/'audit.json').read_text()) == json.loads((b/'audit.json').read_text())
    return count


def execute(out):
    started = time.perf_counter()
    launch_config = json.loads((out/'launch_config.json').read_text())
    config = None
    status = dict(state='RUNNING', phase='verification', label=d.LABEL)
    timings, admissions, groups = {}, {}, {}
    def progress(**values):
        status.update(values, elapsed_seconds=time.perf_counter()-started, updated_utc=utc())
        save(out/'STATUS.json', status); print(json.dumps(status), flush=True)
    def capacity(workers, phase):
        def update(record):
            progress(state='RUNNING' if record['capacity_available'] else 'WAITING_CAPACITY',
                     phase='capacity_'+phase, capacity=record)
        admissions[phase] = wait_for_capacity(workers, cpu_snapshot, update)
        save(out/(phase+'_admission.json'), admissions[phase])
    def tasks(phase, specs, workers, suffix=''):
        capacity(workers, phase); verify(out, 'freeze.json')
        items = [dict(out=str(out), input_name=s['name'], name=s['name']+suffix) for s in specs]
        progress(state='RUNNING', phase=phase, workers=workers, completed_tasks=0,
                 total_tasks=len(items), failed_qualifications=0)
        before, results = time.perf_counter(), []
        def accept(row):
            results.append(row)
            progress(completed_tasks=len(results), failed_qualifications=sum(not r['qualified'] for r in results))
        if workers == 1:
            for item in items:
                accept(measure.task(item))
        else:
            with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
                submitted = [pool.submit(measure.task, item) for item in items]
                for job in as_completed(submitted):
                    accept(job.result())
        timings[phase] = time.perf_counter()-before
        seal(out, phase+'_sha256.json', sorted(p for item in items
            for p in (out/'raw'/item['name']).rglob('*') if p.is_file()))
        return sorted(results, key=lambda r: r['name'])
    def finish(qualified, finding, diagnosis=None):
        progress(state='RUNNING', phase='reporting')
        for name in ('freeze.json', 'benchmark_serial_sha256.json', 'benchmark_parallel_sha256.json',
                     'decision_sha256.json', 'continuations_sha256.json'):
            if (out/name).exists():
                verify(out, name)
        external_check(out, full=True)
        summary = dict(label=d.LABEL, qualified=qualified, finding=finding, diagnosis=diagnosis,
            timings=timings, groups=groups,
            capacity_wait_seconds=sum(r['wait_seconds'] for r in admissions.values()),
            elapsed_seconds=time.perf_counter()-started, prior_verdicts_changed=False, fits=0)
        save(out/'summary.json', summary)
        if not qualified:
            (out/'REPORT.md').write_text('# H034 — Numerical qualification failed\n\n'+finding+
                '\n\nAll submitted results and numerical audits are retained; no scientific interpretation or further stage follows.\n')
        progress(state='COMPLETE', phase='complete', qualified=qualified, finding=finding,
                 completed_utc=utc(), remaining_compute_forecast_seconds=0.)
        save(out/'COMPLETE.json', status)
        seal(out, 'checksums.json', sorted(p for p in out.rglob('*') if p.is_file()))
        verify(out, 'checksums.json')
    try:
        with (out/'EXECUTION.json').open('x') as stream:
            json.dump(dict(pid=os.getpid(), started_utc=utc()), stream)
        verify(out, 'source_sha256.json'); external_check(out)
        capacity(1, 'preparation'); progress(state='RUNNING', phase='preparation', workers=1)
        before = time.perf_counter()
        config = prepare_data(out, launch_config)
        timings['preparation'] = time.perf_counter()-before
        progress(input_freeze_sha256=checksum(out/'freeze.json'), selected_prefixes=config['selected_prefixes'])
        capacity(1, 'fixtures'); progress(state='RUNNING', phase='fixtures', workers=1)
        before = time.perf_counter()
        with (out/'fixtures.log').open('x') as stream:
            subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v', 'h022.fixtures', 'h034.fixtures'],
                cwd=SOURCE, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, check=True)
        timings['fixtures'] = time.perf_counter()-before
        count = int(re.search(r'Ran (\d+) tests', (out/'fixtures.log').read_text()).group(1))
        progress(fixture_tests_passed=count, phase='input_reproduction')
        save(out/'input_reproduction.json', reproduce(out, config))
        benchmarks = {}
        for mode, workers in (('serial', 1), ('parallel', 4)):
            phase = 'benchmark_'+mode
            rows = tasks(phase, config['benchmark'], workers, '_'+mode)
            groups[phase] = rows
            benchmarks[mode] = dict(tasks=rows, elapsed_seconds=timings[phase],
                                    qualified=all(r['qualified'] for r in rows))
            save(out/(phase+'.json'), benchmarks[mode])
            if not benchmarks[mode]['qualified']:
                finish(False, phase.upper()+'_NUMERICALLY_UNQUALIFIED'); return
        count = compare_benchmarks(out, config['benchmark'])
        serial, parallel = [benchmarks[mode]['elapsed_seconds'] for mode in ('serial', 'parallel')]
        workers = 4 if parallel < .9*serial else 1
        decision = dict(workers=workers, serial_seconds=serial, parallel_seconds=parallel,
            arrays_exactly_equal=count, benchmark_qualified=True,
            remaining_compute_forecast_seconds=(parallel if workers == 4 else serial)*config['benchmark_main_scale']*1.5+300,
            capacity_wait_additional=True)
        save(out/'benchmark_decision.json', decision)
        seal(out, 'decision_sha256.json', [out/name for name in ('benchmark_decision.json',
            'benchmark_serial.json', 'benchmark_parallel.json', 'benchmark_serial_sha256.json', 'benchmark_parallel_sha256.json')])
        progress(phase='benchmark_complete', selected_workers=workers,
                 remaining_compute_forecast_seconds=decision['remaining_compute_forecast_seconds'])
        groups['continuations'] = tasks('continuations', config['tasks'], workers)
        assert sum(r['paths'] for r in groups['continuations']) == config['paths']
        if not all(r['qualified'] for r in groups['continuations']):
            finish(False, 'CONTINUATIONS_NUMERICALLY_UNQUALIFIED'); return
        capacity(1, 'analysis'); progress(state='RUNNING', phase='analysis', workers=1)
        before = time.perf_counter()
        result = analysis.assemble(out, config)
        timings['analysis'] = time.perf_counter()-before
        finish(True, result['finding'], result)
    except Exception:
        failure = dict(state='FAILED', phase=status.get('phase'), label=d.LABEL,
            error=traceback.format_exc(), failed_utc=utc(), elapsed_seconds=time.perf_counter()-started)
        save(out/'FAILED.json', failure); save(out/'STATUS.json', failure)
        raise


def launch(version):
    if not version.replace('_', '').isalnum():
        raise ValueError('Simple version required')
    out = SOURCE/f'runs/h034_branching_{version}'
    log, pidfile, ledger = out.with_suffix('.log'), out.with_suffix('.pid'), out.with_name(out.name+'_launch.json')
    if any(path.exists() for path in (out, log, pidfile, ledger)):
        raise FileExistsError('Occupied H034 destination')
    prepare(SOURCE, out)
    config = json.loads((out/'launch_config.json').read_text())
    command = [sys.executable, '-B', str(out/'source/h034/workflow.py'), '--execute', str(out)]
    env = os.environ.copy(); (SOURCE/'.cache/tmp').mkdir(parents=True, exist_ok=True)
    env.update(TMPDIR=str(SOURCE/'.cache/tmp'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1',
        MPLCONFIGDIR=str(SOURCE/'.cache/matplotlib'), XDG_CACHE_HOME=str(SOURCE/'.cache'))
    record = dict(state='PREPARED', label=d.LABEL, output=str(out), log=str(log), command=command,
        detached=True, candidate_workers=[1, 4], numerical_threads=1,
        initial_compute_forecast_seconds=config['initial_compute_forecast_seconds'],
        capacity_wait_additional=True, source_freeze_sha256=checksum(out/'source_sha256.json'),
        input_preparation_requires_capacity=True)
    save(ledger, record)
    with log.open('xb') as stream:
        process = subprocess.Popen(command, cwd=out/'source', env=env, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    pidfile.write_text(str(process.pid)+'\n')
    record.update(state='LAUNCHED', pid=process.pid); save(ledger, record)
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--launch', metavar='VERSION')
    group.add_argument('--execute', type=Path)
    args = parser.parse_args()
    launch(args.launch) if args.launch else execute(args.execute.resolve())
