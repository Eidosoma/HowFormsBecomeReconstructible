"""Extract H003 gain-4 records and run a frozen, benchmarked H006 pipeline."""
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
from h006 import engine as e
from h006.execute import save

MODEL_FILES = ['model.py', 'run.py', 'h003/experiment.py', 'h003/diagnose.py', 'h003/fixtures.py']
FILES = [*MODEL_FILES, 'h005/engine.py', 'run_python.sh', 'requirements.txt',
         'h006/PROTOCOL.md', 'h006/engine.py', 'h006/inference.py', 'h006/fixtures.py',
         'h006/audit.py', 'h006/analysis.py', 'h006/execute.py', 'h006/launch.py']


def prepare(mode, out, benchmark):
    parent = LANE/('runs/h003_benchmark_v1' if mode == 'benchmark' else 'runs/h003_development_v1')
    parent_config = json.loads((parent/'config.json').read_text())
    parent_seals = json.loads((parent/'checksums.json').read_text())
    for name in ('config.json', 'freeze.json', 'raw_sha256.json', 'audit.json'):
        if e.e.checksum(parent/name) != parent_seals[name]:
            raise AssertionError('Changed parent '+name)
    if not json.loads((parent/'audit.json').read_text())['passed']:
        raise AssertionError('Parent audit failed')
    freeze = json.loads((parent/'freeze.json').read_text())
    for name in MODEL_FILES:
        if e.e.checksum(LANE/name) != freeze['source/'+name]:
            raise AssertionError('Original model changed: '+name)
    selection_seeds = [12900] if mode == 'benchmark' else list(range(13000, 13008))
    assay_seeds = [12900] if mode == 'benchmark' else list(range(13008, 13024))
    seeds = sorted(set(selection_seeds + assay_seeds))
    if parent_config['seeds'] != seeds:
        raise AssertionError('Unexpected source cohort')
    config = dict(experiment='H006', mode=mode,
        classification='ENGINEERING_BENCHMARK' if mode == 'benchmark' else 'PROSPECTIVE_INTERVENTION_ON_DEVELOPMENT_CHECKPOINTS',
        seeds=seeds, selection_seeds=selection_seeds, assay_seeds=assay_seeds,
        source_generation=16, source_regime='cue_gain4', source_arm='renewal',
        doses=e.DOSES, variants=e.VARIANTS, arms=e.ARMS, checkpoints=e.CHECKPOINTS,
        forks=e.FORKS, screen_probes=e.SCREEN_PROBES, validation_probes=e.VALIDATION_PROBES,
        analysis_seed=960006, bootstrap_draws=20000, reader_gain=4., sweeps_per_cue=8,
        damage_probability=.5, additional_generations=16, equivalence_tolerance=.01,
        workers=1, numerical_threads=1, numpy=np.__version__, python=sys.version,
        prepared_utc=datetime.now(timezone.utc).isoformat(), source_parent=str(parent.relative_to(LANE)),
        source_classification=parent_config['classification'], source_config_sha256=e.e.checksum(parent/'config.json'))
    if mode == 'development':
        done = json.loads((benchmark/'COMPLETE.json').read_text())
        seals = json.loads((benchmark/'checksums.json').read_text())
        if e.e.checksum(benchmark/'audit.json') != seals['audit.json'] or not json.loads((benchmark/'audit.json').read_text())['passed']:
            raise AssertionError('Benchmark integrity failed')
        for name in FILES:
            if e.e.checksum(LANE/name) != e.e.checksum(benchmark/'source'/name):
                raise AssertionError('Source changed after benchmark: '+name)
        if done['state'] != 'COMPLETE' or done['completed_forks'] != 8:
            raise AssertionError('Full benchmark incomplete')
        forecast = done['elapsed_seconds']*24*1.25+60
        config['runtime_forecast'] = dict(seconds=forecast, benchmark_seconds=done['elapsed_seconds'],
             method='Entire five-dose selection plus assay, eight futures, audit and reporting block times 24, plus 25% and 60 seconds.',
             detached=forecast > 600)
    estimated_bytes = len(assay_seeds)*e.FORKS*27_000_000+len(seeds)*15_000_000
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
    raw_seals = json.loads((parent/'raw_sha256.json').read_text())
    receipts = {}
    for seed in seeds:
        original = parent/f'function_{seed}.npz'
        if e.e.checksum(original) != raw_seals[original.name]:
            raise AssertionError('Changed source block')
        with np.load(original) as raw:
            records = raw['records'][-1, 2, 0]
            bodies = raw['bodies'][-1, 2, 0]
            if not np.array_equal(records, e.e.m.write_body(bodies)):
                raise AssertionError('Source packet not complete body writing')
            np.savez_compressed(out/f'inputs/source_{seed}.npz', records=records, source_bodies=bodies,
                                base=raw['base'], founder=raw['founder'], cues=raw['cues'], seed=seed)
        receipts[str(seed)] = dict(original_file=str(original.relative_to(LANE)), sha256=raw_seals[original.name],
                                  extracted_file=f'inputs/source_{seed}.npz', regime_index=2, arm_index=0, generation=16)
    save(out/'input_receipts.json', receipts)
    save(out/'config.json', config)
    frozen = [out/'config.json', out/'input_receipts.json', *sorted((out/'inputs').glob('*.npz')),
              *sorted(p for p in (out/'source').rglob('*') if p.is_file())]
    save(out/'freeze.json', {str(p.relative_to(out)): e.e.checksum(p) for p in frozen})
    save(out/'STATUS.json', dict(state='PREPARED', selection_blocks=len(selection_seeds), assay_blocks=len(assay_seeds)))
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['benchmark', 'development'], required=True)
    parser.add_argument('--version', default='v1')
    parser.add_argument('--benchmark', type=Path, default=LANE/'runs/h006_benchmark_v1')
    args = parser.parse_args()
    if not args.version.replace('_', '').isalnum():
        parser.error('Simple alphanumeric version required')
    out = LANE/f'runs/h006_{args.mode}_{args.version}'
    log, pid_path = out.with_suffix('.log'), out.with_suffix('.pid')
    ledger_path = out.with_name(out.name+'_launch.json')
    if any(p.exists() for p in (out, log, pid_path, ledger_path)):
        raise FileExistsError('Refusing to reuse run destination')
    config = prepare(args.mode, out, args.benchmark.resolve())
    command = [sys.executable, '-B', str(out/'source/h006/execute.py'), '--run', str(out)]
    detached = args.mode == 'development' and config['runtime_forecast']['detached']
    ledger = dict(state='PREPARED', command=command, output=str(out), log=str(log), prepared_utc=config['prepared_utc'],
                  freeze_sha256=e.e.checksum(out/'freeze.json'), detached=detached, workers=1, numerical_threads=1,
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
