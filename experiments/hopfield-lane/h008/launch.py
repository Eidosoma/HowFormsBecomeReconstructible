"""Freeze the H007 nomination and unchanged cohort before any H008 probe."""
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
from h008 import engine as e
from h007.io import checksum, save, verify, seal

MODEL_FILES = ['model.py', 'run.py', 'h003/experiment.py', 'h003/diagnose.py', 'h003/fixtures.py',
               'h005/engine.py', 'h007/io.py', 'h007/engine.py', 'h007/inference.py', 'h007/fixtures.py']
FILES = [*MODEL_FILES, 'run_python.sh', 'requirements.txt',
         'h008/PROTOCOL.md', 'h008/engine.py', 'h008/inference.py', 'h008/fixtures.py',
         'h008/audit.py', 'h008/analysis.py', 'h008/execute.py', 'h008/launch.py']


def prepare(mode, out, benchmark):
    nomination_parent = LANE/'runs/h007_development_v1'
    nomination_seals = json.loads((nomination_parent/'checksums.json').read_text())
    for name in ('summary.json', 'audit.json'):
        if checksum(nomination_parent/name) != nomination_seals[name]:
            raise AssertionError('Changed H007 nomination evidence')
    nominated = json.loads((nomination_parent/'summary.json').read_text())
    if (nominated['verdict'] != 'FEASIBILITY_CANDIDATE' or nominated['nominated_dose'] != e.DOSE or
        not json.loads((nomination_parent/'audit.json').read_text())['passed']):
        raise AssertionError('Selected dose lacks the required completed H007 feasibility result')
    parent = LANE/('runs/h007_benchmark_v1' if mode == 'benchmark' else 'runs/h007_development_v1')
    parent_seals = json.loads((parent/'checksums.json').read_text())
    for name in ('config.json', 'freeze.json', 'input_receipts.json', 'audit.json', 'ENROLLMENT.json', 'raw_sha256.json'):
        if checksum(parent/name) != parent_seals[name]:
            raise AssertionError('Changed H007 source '+name)
    if not json.loads((parent/'audit.json').read_text())['passed']:
        raise AssertionError('Source audit failed')
    parent_config = json.loads((parent/'config.json').read_text())
    parent_freeze = json.loads((parent/'freeze.json').read_text())
    parent_raw = json.loads((parent/'raw_sha256.json').read_text())
    original_receipts = json.loads((parent/'input_receipts.json').read_text())
    prior = next(d for d in json.loads((parent/'ENROLLMENT.json').read_text())['decisions'] if d['dose'] == e.DOSE)
    for name in MODEL_FILES:
        if checksum(LANE/name) != parent_freeze['source/'+name]:
            raise AssertionError('Original model/intervention changed: '+name)
    seeds = [12900] if mode == 'benchmark' else list(range(13000, 13024))
    if parent_config['seeds'] != seeds or sorted(map(int, original_receipts)) != seeds:
        raise AssertionError('Unexpected source cohort')
    config = dict(experiment='H008', mode=mode,
        classification='ENGINEERING_BENCHMARK' if mode == 'benchmark' else 'PROSPECTIVE_DURABILITY_ON_FIXED_H007_DEVELOPMENT_COHORT',
        seeds=seeds, dose=e.DOSE, source_generation=16, source_regime='cue_gain4', source_arm='renewal',
        variants=e.VARIANTS, arms=e.ARMS, forks=e.FORKS, generations=e.GENERATIONS, checkpoints=e.CHECKPOINTS,
        validation_probes=e.VALIDATION_PROBES, analysis_seed=980008, bootstrap_draws=20000,
        reader_gain=4., sweeps_per_cue=8, damage_probability=.5, equivalence_tolerance=.01,
        equivalence_quantiles=[.0125, .9875], primary_quantiles=[.05/18, 1-.05/18], control_quantile=.05/9,
        minimum_absolute_terminal_difference=.10, minimum_route_difference=.15, family_size=9,
        workers=1, numerical_threads=1, numpy=np.__version__, python=sys.version,
        prepared_utc=datetime.now(timezone.utc).isoformat(), source_parent=str(parent.relative_to(LANE)),
        source_freeze_sha256=checksum(parent/'freeze.json'), source_enrollment_sha256=checksum(parent/'ENROLLMENT.json'),
        fixed_matches=prior['matches'], fixed_nonempty_blocks=prior['nonempty_blocks'])
    if mode == 'development':
        for manifest in ('freeze.json', 'enrollment_sha256.json', 'raw_sha256.json', 'checksums.json'):
            verify(benchmark, manifest)
        done = json.loads((benchmark/'COMPLETE.json').read_text())
        if (done['state'] != 'COMPLETE' or done['completed_forks'] != e.FORKS or
            done['verdict'] != 'ENGINEERING_ONLY' or not json.loads((benchmark/'audit.json').read_text())['passed']):
            raise AssertionError('Complete engineering benchmark required')
        for name in FILES:
            if checksum(LANE/name) != checksum(benchmark/'source'/name):
                raise AssertionError('Source changed after benchmark: '+name)
        forecast = done['elapsed_seconds']*24*1.25+60
        config['runtime_forecast'] = dict(seconds=forecast, benchmark_seconds=done['elapsed_seconds'],
             method='Entire fixed-dose, eight-branch sixteen-replacement benchmark with full replay audit and reporting times 24, plus 25% and 60 seconds.',
             detached=forecast > 600)
    estimated_bytes = len(seeds)*(e.FORKS*24_000_000+3_000_000)
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
    receipts, count = {}, 0
    index = e.selected.DOSES.index(e.DOSE)
    prior_rows = {row['seed']: row for row in prior['blocks']}
    for seed in seeds:
        relative = f'inputs/source_{seed}.npz'
        original = parent/relative
        present_path = parent/f'present_{seed}.npz'
        if checksum(original) != parent_freeze[relative] or checksum(present_path) != parent_raw[present_path.name]:
            raise AssertionError('Changed source input or present-only candidate')
        shutil.copyfile(original, out/relative)
        if checksum(out/relative) != parent_freeze[relative]:
            raise AssertionError('Source copy mismatch')
        with np.load(original) as source, np.load(present_path) as present:
            packets = present['packet_codes'][index]
            changed_bodies = present['changed_bodies'][index]
            eligible = present['eligible'][index]
            if (int(source['seed']) != seed or not np.array_equal(e.decode(packets[0]), source['records']) or
                not np.array_equal(e.decode(packets[1]), e.model.m.write_body(changed_bodies)) or
                not np.array_equal(eligible, prior_rows[seed]['eligible'])):
                raise AssertionError('Selected source, writer or enrollment mismatch')
            np.savez_compressed(out/f'inputs/candidate_{seed}.npz', packet_codes=packets,
                                changed_bodies=changed_bodies, permutations=present['permutations'][index],
                                feasible=present['feasible'], eligible=eligible, seed=seed, dose=e.DOSE)
            count += int(eligible.sum())
        receipts[str(seed)] = dict(source_file=str(original.relative_to(LANE)), source_sha256=parent_freeze[relative],
                                  present_file=str(present_path.relative_to(LANE)), present_sha256=parent_raw[present_path.name],
                                  candidate_file=f'inputs/candidate_{seed}.npz', selected_dose_index=index,
                                  source_receipt=original_receipts[str(seed)])
    if count != prior['matches']:
        raise AssertionError('Fixed source membership changed')
    shutil.copyfile(parent/'input_receipts.json', out/'upstream_input_receipts.json')
    shutil.copyfile(parent/'ENROLLMENT.json', out/'upstream_enrollment.json')
    save(out/'nomination_receipt.json', dict(parent=str(nomination_parent.relative_to(LANE)),
         summary_sha256=nomination_seals['summary.json'], audit_sha256=nomination_seals['audit.json'],
         nominated_dose=e.DOSE, method='H007 prespecified largest passing dose; no new dose selection'))
    save(out/'input_receipts.json', receipts)
    save(out/'config.json', config)
    seal(out, 'freeze.json', [out/'config.json', out/'input_receipts.json', out/'upstream_input_receipts.json',
         out/'upstream_enrollment.json', out/'nomination_receipt.json', *sorted((out/'inputs').glob('*.npz')),
         *sorted(p for p in (out/'source').rglob('*') if p.is_file())])
    save(out/'STATUS.json', dict(state='PREPARED', blocks=len(seeds), dose=e.DOSE, fixed_matches=count))
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['benchmark', 'development'], required=True)
    parser.add_argument('--version', default='v1')
    parser.add_argument('--benchmark', type=Path, default=LANE/'runs/h008_benchmark_v1')
    args = parser.parse_args()
    if not args.version.replace('_', '').isalnum():
        parser.error('Simple alphanumeric version required')
    out = LANE/f'runs/h008_{args.mode}_{args.version}'
    log, pid_path = out.with_suffix('.log'), out.with_suffix('.pid')
    ledger_path = out.with_name(out.name+'_launch.json')
    if any(p.exists() for p in (out, log, pid_path, ledger_path)):
        raise FileExistsError('Refusing to reuse run destination')
    config = prepare(args.mode, out, args.benchmark.resolve())
    command = [sys.executable, '-B', str(out/'source/h008/execute.py'), '--run', str(out)]
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
