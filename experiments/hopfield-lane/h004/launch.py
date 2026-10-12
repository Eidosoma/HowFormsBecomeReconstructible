"""Freeze H004 before any new inputs, then execute only the frozen snapshot."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os
import shutil
import subprocess
import sys
import numpy as np

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE))
from h003.experiment import checksum
from h004.execute import save

MODEL_FILES = ['model.py', 'run.py', 'h003/experiment.py', 'h003/diagnose.py',
               'h003/audit.py', 'h003/fixtures.py']
FILES = [*MODEL_FILES, 'run_python.sh', 'h003/PROTOCOL.md', 'h004/PROTOCOL.md',
         'h004/plan.py', 'h004/SAMPLE_SIZE.json', 'h004/analysis.py',
         'h004/inference.py', 'h004/check_inference.py', 'h004/INFERENCE_CHECK.json',
         'h004/execute.py', 'h004/launch.py']


def checked_json(path):
    seals = json.loads((path.parent / 'checksums.json').read_text())
    if checksum(path) != seals[path.name]:
        raise AssertionError('Changed sealed input: ' + str(path))
    return json.loads(path.read_text())


def prepare(mode, out):
    plan = json.loads((LANE / 'h004/SAMPLE_SIZE.json').read_text())
    if plan['blocks'] != 72 or plan['seeds'] != list(range(14000, 14072)):
        raise AssertionError('Sample-size plan differs from frozen protocol')
    regression = json.loads((LANE / 'h004/INFERENCE_CHECK.json').read_text())
    if not regression['passed']:
        raise AssertionError('Inference regression did not pass')
    for name, expected in regression['source_sha256'].items():
        if checksum(LANE / name) != expected:
            raise AssertionError('Inference changed after regression: ' + name)
    development = LANE / 'runs/h003_development_v1'
    old_freeze = json.loads((development / 'freeze.json').read_text())
    for name in MODEL_FILES:
        if checksum(LANE / name) != old_freeze['source/' + name]:
            raise AssertionError('Scientific implementation changed since H003: ' + name)
    previous_seeds = set()
    for folder in (LANE / 'runs').iterdir():
        if not folder.is_dir():
            continue
        for raw in folder.glob('function_*.npz'):
            try:
                previous_seeds.add(int(raw.stem.split('_')[-1]))
            except ValueError:
                continue
    if mode == 'confirmation' and previous_seeds.intersection(plan['seeds']):
        raise AssertionError('A proposed confirmation block has already been generated')
    config = dict(experiment='H004', mode=mode,
                  classification='ENGINEERING_BENCHMARK' if mode == 'benchmark' else 'FRESH_COHORT_CONFIRMATION',
                  seeds=[12900] if mode == 'benchmark' else plan['seeds'], generations=16,
                  regimes=['cue_gain1', 'cue_gain2', 'cue_gain4', 'decoy_gain4'],
                  gains=[1., 2., 4., 4.], gain_sites=[[0, 1, 2, 3]] * 3 + [[24, 25, 26, 27]],
                  arms=['renewal', 'foreign', 'scrambled', 'erased', 'read_off', 'write_off',
                        'protected_copy', 'damaged_copy', 'writer_scrambled'],
                  neurons=64, founders=4, replicates=4, clamps=[0, 1, 2, 3], damage_probability=.5,
                  bootstrap_draws=20000, analysis_seed=940004, bootstrap_namespace='H004 whole-block bootstrap',
                  primary_family_size=17, primary_one_sided_quantile=.05/17,
                  secondary='Timing claim is eligible only after primary qualification',
                  workers=1, numerical_threads=1, numpy=np.__version__, python=sys.version,
                  prepared_utc=datetime.now(timezone.utc).isoformat(),
                  sample_size_plan=plan, previous_public_seeds=sorted(previous_seeds),
                  model_sha256={name: checksum(LANE / name) for name in MODEL_FILES})
    reference = LANE / 'runs/h003_benchmark_v1/function_12900.npz'
    if mode == 'benchmark':
        expected = checked_json(reference.parent / 'raw_sha256.json')[reference.name]
        if checksum(reference) != expected:
            raise AssertionError('Changed engineering reference')
        config['reference_sha256'] = expected
    else:
        benchmark = LANE / 'runs/h004_benchmark_v1'
        status = json.loads((benchmark / 'COMPLETE.json').read_text())
        checked = checked_json(benchmark / 'audit.json')
        if status['state'] != 'COMPLETE' or not checked['passed']:
            raise AssertionError('H004 engineering replay did not pass')
        # Both observed runtimes include generation, retained-data audit and figures.
        old_status = json.loads((development / 'STATUS.json').read_text())
        seconds_per_block = max(status['elapsed_seconds'], old_status['elapsed_seconds']/24)
        forecast = seconds_per_block * plan['blocks'] * 1.20 + 60
        config['runtime_forecast'] = dict(seconds=forecast, benchmark_elapsed_seconds=status['elapsed_seconds'],
            method='Larger observed full-wrapper seconds/block from H004 benchmark or H003 cohort, '
                   'times 72, plus 20% headroom and 60 seconds.',
            execution='DETACHED', numerical_threads=1, workers=1)
        for name in FILES:
            if checksum(LANE / name) != checksum(benchmark / 'source' / name):
                raise AssertionError('Source changed since H004 benchmark: ' + name)
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        target = out / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LANE / name, target)
    if mode == 'benchmark':
        shutil.copyfile(reference, out / 'engineering_reference.npz')
    save(out / 'config.json', config)
    frozen = [out / 'config.json', *sorted(p for p in (out / 'source').rglob('*') if p.is_file())]
    if mode == 'benchmark':
        frozen.append(out / 'engineering_reference.npz')
    save(out / 'freeze.json', {str(p.relative_to(out)): checksum(p) for p in frozen})
    save(out / 'STATUS.json', dict(state='PREPARED', completed_blocks=0, total_blocks=len(config['seeds'])))
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['benchmark', 'confirmation'], required=True)
    args = parser.parse_args()
    out = LANE / f'runs/h004_{args.mode}_v1'
    log = out.with_suffix('.log')
    pid_file = out.with_suffix('.pid')
    launch_file = out.with_name(out.name + '_launch.json')
    if any(path.exists() for path in [out, log, pid_file, launch_file]):
        raise FileExistsError('Refusing to reuse a campaign destination')
    config = prepare(args.mode, out)
    command = [sys.executable, '-B', str(out / 'source/h004/execute.py'), '--run', str(out)]
    ledger = dict(state='PREPARED', prepared_utc=config['prepared_utc'], command=command,
                  output=str(out), log=str(log), workers=1, numerical_threads=1,
                  freeze_sha256=checksum(out / 'freeze.json'),
                  policy='../RUN_POLICY.md: detached above 600 seconds; no automatic polling.')
    save(launch_file, ledger)
    if args.mode == 'benchmark':
        with log.open('xb') as stream:
            process = subprocess.Popen(command, cwd=LANE, stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT)
        pid_file.write_text(str(process.pid) + '\n')
        ledger.update(state='LAUNCHED', pid=process.pid, detached=False)
        save(launch_file, ledger)
        result = process.wait()
        print(json.dumps(dict(output=str(out), returncode=result)))
        if result:
            raise SystemExit(result)
    else:
        with log.open('xb') as stream:
            process = subprocess.Popen(command, cwd=LANE, stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True, close_fds=True)
        pid_file.write_text(str(process.pid) + '\n')
        ledger.update(state='LAUNCHED', pid=process.pid, detached=True,
                      runtime_forecast=config['runtime_forecast'])
        save(launch_file, ledger)
        print(json.dumps(dict(state='LAUNCHED', pid=process.pid, blocks=len(config['seeds']),
                              forecast_minutes=config['runtime_forecast']['seconds']/60,
                              log=str(log), status=str(out / 'STATUS.json'))))


if __name__ == '__main__':
    main()
