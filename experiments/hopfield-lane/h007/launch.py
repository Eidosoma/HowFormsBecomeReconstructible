"""Reuse verified H003 input snapshots and launch a frozen H007 pipeline."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import shutil
import subprocess
import sys
import numpy as np

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE))
from h007 import engine as e
from h007.io import checksum, save, verify, seal

MODEL_FILES = ['model.py', 'run.py', 'h003/experiment.py', 'h003/diagnose.py', 'h003/fixtures.py', 'h005/engine.py']
FILES = [*MODEL_FILES, 'run_python.sh', 'requirements.txt',
         'h007/PROTOCOL.md', 'h007/io.py', 'h007/engine.py', 'h007/inference.py',
         'h007/fixtures.py', 'h007/audit.py', 'h007/analysis.py', 'h007/execute.py', 'h007/launch.py']


def prepare(mode, out, benchmark):
    parent = LANE/('runs/h006_benchmark_v1' if mode == 'benchmark' else 'runs/h006_development_v1')
    parent_seals = json.loads((parent/'checksums.json').read_text())
    for name in ('config.json', 'freeze.json', 'input_receipts.json', 'audit.json'):
        if checksum(parent/name) != parent_seals[name]:
            raise AssertionError('Changed cached source parent '+name)
    if not json.loads((parent/'audit.json').read_text())['passed']:
        raise AssertionError('Source parent audit failed')
    parent_config = json.loads((parent/'config.json').read_text())
    parent_freeze = json.loads((parent/'freeze.json').read_text())
    original_receipts = json.loads((parent/'input_receipts.json').read_text())
    for name in MODEL_FILES:
        if checksum(LANE/name) != parent_freeze['source/'+name]:
            raise AssertionError('Original model changed: '+name)
    seeds = [12900] if mode == 'benchmark' else list(range(13000, 13024))
    if parent_config['seeds'] != seeds or sorted(map(int, original_receipts)) != seeds:
        raise AssertionError('Unexpected source cohort')
    config = dict(experiment='H007', mode=mode,
        classification='ENGINEERING_BENCHMARK' if mode == 'benchmark' else 'PROSPECTIVE_FEASIBILITY_SCREEN_ON_DEVELOPMENT_CHECKPOINTS',
        seeds=seeds, source_generation=16, source_regime='cue_gain4', source_arm='renewal',
        doses=e.DOSES, variants=e.VARIANTS, arms=e.ARMS, trials=e.TRIALS,
        screen_probes=e.SCREEN_PROBES, validation_probes=e.VALIDATION_PROBES,
        analysis_seed=970007, bootstrap_draws=20000, reader_gain=4., sweeps_per_cue=8,
        damage_probability=.5, additional_replacements=1, equivalence_tolerance=.01,
        equivalence_quantiles=[.0125, .9875], directional_quantile=.05/12,
        workers=1, numerical_threads=1, numpy=np.__version__, python=sys.version,
        prepared_utc=datetime.now(timezone.utc).isoformat(), cached_source_parent=str(parent.relative_to(LANE)),
        original_source_parent=parent_config['source_parent'],
        source_receipts_sha256=checksum(parent/'input_receipts.json'), source_freeze_sha256=checksum(parent/'freeze.json'))
    if mode == 'development':
        for manifest in ('freeze.json', 'enrollment_sha256.json', 'raw_sha256.json', 'checksums.json'):
            verify(benchmark, manifest)
        done = json.loads((benchmark/'COMPLETE.json').read_text())
        if (done['state'] != 'COMPLETE' or done['completed_trials'] != e.TRIALS or
            done['verdict'] != 'ENGINEERING_ONLY' or not json.loads((benchmark/'audit.json').read_text())['passed']):
            raise AssertionError('Complete engineering benchmark required')
        for name in FILES:
            if checksum(LANE/name) != checksum(benchmark/'source'/name):
                raise AssertionError('Source changed after benchmark: '+name)
        forecast = done['elapsed_seconds']*24*1.25+60
        config['runtime_forecast'] = dict(seconds=forecast, benchmark_seconds=done['elapsed_seconds'],
             method='Entire four-dose, eight-trial engineering block including audit and reporting times 24, plus 25% and 60 seconds.',
             detached=forecast > 600)
    estimated_bytes = len(seeds)*(e.TRIALS*8_000_000+3_000_000)
    free = shutil.disk_usage(LANE).free
    if free < estimated_bytes*1.25+100_000_000:
        raise RuntimeError('Insufficient local disk reserve')
    config['storage_preflight'] = dict(free_bytes=free, conservative_uncompressed_bytes=estimated_bytes)
    out.mkdir(parents=True, exist_ok=False)
    (out/'inputs').mkdir()
    for name in FILES:
        target = out/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LANE/name, target)
    receipts = {}
    for seed in seeds:
        relative = f'inputs/source_{seed}.npz'
        original = parent/relative
        if checksum(original) != parent_freeze[relative]:
            raise AssertionError('Changed extracted source block')
        with np.load(original) as raw:
            if int(raw['seed']) != seed or not np.array_equal(raw['records'], e.e.m.write_body(raw['source_bodies'])):
                raise AssertionError('Source identity or body-only writing mismatch')
        shutil.copyfile(original, out/relative)
        if checksum(out/relative) != parent_freeze[relative]:
            raise AssertionError('Source copy mismatch')
        receipts[str(seed)] = dict(cached_file=str(original.relative_to(LANE)), sha256=parent_freeze[relative],
                                  extracted_file=relative, original=original_receipts[str(seed)])
    shutil.copyfile(parent/'input_receipts.json', out/'upstream_input_receipts.json')
    save(out/'input_receipts.json', receipts)
    save(out/'config.json', config)
    seal(out, 'freeze.json', [out/'config.json', out/'input_receipts.json', out/'upstream_input_receipts.json',
         *sorted((out/'inputs').glob('*.npz')), *sorted(p for p in (out/'source').rglob('*') if p.is_file())])
    save(out/'STATUS.json', dict(state='PREPARED', blocks=len(seeds), doses=e.DOSES, trials=e.TRIALS))
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['benchmark', 'development'], required=True)
    parser.add_argument('--version', default='v1')
    parser.add_argument('--benchmark', type=Path, default=LANE/'runs/h007_benchmark_v1')
    args = parser.parse_args()
    if not args.version.replace('_', '').isalnum():
        parser.error('Simple alphanumeric version required')
    out = LANE/f'runs/h007_{args.mode}_{args.version}'
    log, pid_path = out.with_suffix('.log'), out.with_suffix('.pid')
    ledger_path = out.with_name(out.name+'_launch.json')
    if any(p.exists() for p in (out, log, pid_path, ledger_path)):
        raise FileExistsError('Refusing to reuse run destination')
    config = prepare(args.mode, out, args.benchmark.resolve())
    command = [sys.executable, '-B', str(out/'source/h007/execute.py'), '--run', str(out)]
    detached = args.mode == 'development' and config['runtime_forecast']['detached']
    ledger = dict(state='PREPARED', command=command, output=str(out), log=str(log), prepared_utc=config['prepared_utc'],
                  freeze_sha256=checksum(out/'freeze.json'), detached=detached, workers=1, numerical_threads=1,
                  runtime_forecast=config.get('runtime_forecast'))
    save(ledger_path, ledger)
    with log.open('xb') as stream:
        process = subprocess.Popen(command, cwd=LANE, stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=detached, close_fds=True)
    pid_path.write_text(str(process.pid)+'\n')
    ledger.update(state='LAUNCHED', pid=process.pid)
    save(ledger_path, ledger)
    print(json.dumps(dict(state='LAUNCHED', pid=process.pid, detached=detached, output=str(out),
                         forecast_minutes=config.get('runtime_forecast', {}).get('seconds', 0)/60)), flush=True)
    if not detached:
        code = process.wait()
        print(json.dumps(dict(state='PROCESS_EXIT', returncode=code)), flush=True)
        if code:
            raise SystemExit(code)


if __name__ == '__main__':
    main()
