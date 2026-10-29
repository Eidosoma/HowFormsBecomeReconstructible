"""D094 write-once source controls, freeze, timing, launch and saved audit.

No implicit simulation, retry, cleanup or parameter selection. Only STATUS
is mutable; scientific artifacts and launch/execution locks are exclusive.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

import numpy as np

from . import l21_paired_fitness as p
from .io import (canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now)

WS = Path(__file__).resolve().parents[2]
CONTROL_ID = 'l21_paired_fitness_v1_source_controls_attempt2'
WORKERS = 4
EXTRA_SCIENCE = ('src/laws_confirmation/l21_paired_fitness_run.py',
                 'tests/test_l21_paired_fitness_run.py', 'scripts/run_l21_paired_fitness.sh')
UNITS = tuple((t, r) for t in p.TISSUES for r in range(p.CONFIG.replicates))
SOURCE_UNITS = tuple((u, r) for u in (.001, 1.) for r in range(3))


def read_json(path):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError(f'duplicate JSON key: {key}')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f'nonfinite JSON constant: {value}')

    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=invalid)


def write_json(path, value, root):
    payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    target = require_beneath(path, root)
    if path.is_symlink():
        raise ValueError('no artifact symlinks')
    with target.open('x') as handle:
        handle.write(payload)


def write_npz(path, raw, root):
    target = require_beneath(path, root)
    if path.is_symlink():
        raise ValueError('no artifact symlinks')
    # Opening exclusively also protects against an accidental second worker.
    with target.open('xb') as handle:
        np.savez_compressed(handle, **raw)


def load_npz(path):
    with np.load(path, allow_pickle=False) as saved:
        if len(saved.files) != len(set(saved.files)):
            raise ValueError('duplicate NPZ fields')
        return dict(saved)


def hashes(paths):
    paths = list(paths)
    if any(x.is_symlink() or not x.is_file() for x in paths):
        raise ValueError('expected regular, non-symlink input files')
    if len(set(paths)) != len(paths):
        raise ValueError('duplicate input paths')
    return {str(x.resolve()): sha256_file(x) for x in sorted(paths)}


def source_cache():
    return p.source.base.sources_root()/'ancestry_world/results/full/work/preround.json'


def science_paths():
    local = (*p.SCIENCE, *EXTRA_SCIENCE, 'src/laws_confirmation/l24_descendant_pilot.py',
             'scripts/audit_l24_descendant_pilot_outputs.py', 'src/laws_confirmation/l17_r_channel.py',
             'src/laws_confirmation/io.py', 'src/laws_confirmation/__init__.py')
    paths = [WS/x for x in local]
    origin = p.source.base.sources_root()
    paths += [origin/'LAWS.md', WS.parents[3]/'PRE_PRINT_PAPER_DRAFT_V2.3.md', source_cache(),
              origin/'ancestry_world/EXPECTATIONS.md', WS/'laws/L21_ancestry_selects_pen.md',
              WS/'reviews/L21_ANCESTRY_SELECTS_PEN_AUDIT_2026-09-03.md']
    for package in (*p.source.PACKAGES, 'ancestry_world'):
        files = sorted((origin/package/'src').rglob('*.py'))
        if not files:
            raise FileNotFoundError(f'missing source package: {package}')
        paths.extend(files)
    return sorted(set(paths))


def pair_name(tissue, replicate):
    if type(tissue) is not int or type(replicate) is not int or (tissue, replicate) not in UNITS:
        raise ValueError('undeclared main identity')
    return f'pair_{tissue}_{replicate}'


def output_names():
    return tuple(f'{pair_name(t,r)}.{ext}' for t, r in UNITS for ext in ('npz', 'json')) + (
        'summary.json', 'verification.json', 'input_hashes.sha256')


def contract():
    return p.contract() | dict(harness_schema='l21_paired_fitness_run_v1', workers=WORKERS,
        output_files=list(output_names()), output_hash_count=35,
        full_saved_pair_replay=True, intact_alias_orders=[[0, 1, 2], [2, 0, 1]],
        known_source_control_id=CONTROL_ID, automatic_retry=False,
        forecast='16*checked_pair_seconds+2*hash_seconds+180',
        storage_forecast='16*(pair_uncompressed_bytes+metadata_bytes+4096)+32MiB')


def check_source_saved(directory):
    expected = read_json(source_cache())
    entries = []
    for i, (u, r) in enumerate(SOURCE_UNITS):
        raw = load_npz(directory/f'source_{i}.npz')
        meta = read_json(directory/f'source_{i}.json')
        assert meta['u'] == u and type(meta['replicate']) is int and meta['replicate'] == r
        assert p.checker().check_source(raw, meta)
        entries.append(meta)
    values = [float(np.mean([row['traced_fitness'] for row in entries if row['u'] == u]))
              for u in (.001, 1.)]
    cached = {row['u']: row['fitness'] for row in expected['data']['rows']}
    assert expected['config_digest'] == p.SOURCE_DIGEST
    assert values == [cached[.001], cached[1.]]
    assert values[1]-values[0] == expected['data']['positive_control_advantage']
    return dict(rates=[.001, 1.], means=values, advantage=values[1]-values[0],
                exact_cached_means=True, source_bridges=6, known_outcomes=True,
                main_pool=False, full_source_state_equivalence=False)


def failure(directory, error, root):
    write_json(directory/'FAILED.json', dict(failed_utc=utc_now(), error=str(error),
               traceback=traceback.format_exc(), automatic_retry=False), root)


def source_controls(root):
    p.source.preflight(root)
    directory = require_beneath(root/'outputs'/CONTROL_ID, root)
    inputs = hashes(science_paths())
    directory.mkdir()
    start = time.monotonic()
    try:
        write_json(directory/'INPUTS.json', dict(input_sha256=inputs, started_utc=utc_now(),
                   source_digest=p.SOURCE_DIGEST, environment=environment_manifest()), root)
        for i, (u, replicate) in enumerate(SOURCE_UNITS):
            raw, meta = p.source_control(u, replicate, root=root)
            write_npz(directory/f'source_{i}.npz', raw, root)
            write_json(directory/f'source_{i}.json', meta, root)
            print(f'E69 known-source control {i+1}/6: scalar and RNG bridge exact', flush=True)
        summary = check_source_saved(directory)
        write_json(directory/'summary.json', summary, root)
        assert hashes(science_paths()) == inputs, 'source-control input drift'
        paths = list(directory.iterdir())
        assert len(paths) == 14
        record = dict(status='COMPLETE', completed_utc=utc_now(),
                      elapsed_seconds=time.monotonic()-start, output_sha256=hashes(paths))
        write_json(directory/'COMPLETE.json', record, root)
        print(json.dumps(summary | dict(seconds=record['elapsed_seconds'])), flush=True)
        return record
    except Exception as error:
        failure(directory, error, root)
        raise


def source_artifacts(root):
    directory = root/'outputs'/CONTROL_ID
    names = {f'source_{i}.{ext}' for i in range(6) for ext in ('json', 'npz')} | {
        'INPUTS.json', 'summary.json', 'COMPLETE.json'}
    assert {x.name for x in directory.iterdir()} == names
    complete = read_json(directory/'COMPLETE.json')
    assert complete['status'] == 'COMPLETE'
    assert read_json(directory/'INPUTS.json')['input_sha256'] == hashes(science_paths())
    assert read_json(directory/'INPUTS.json')['environment'] == environment_manifest()
    assert complete['output_sha256'] == hashes([directory/n for n in names if n != 'COMPLETE.json'])
    assert read_json(directory/'summary.json') == check_source_saved(directory)
    return [directory/n for n in sorted(names)]


def test_proof(path, root):
    path = require_beneath(path, root/'logs')
    if path.is_symlink() or not path.name.startswith('d094_') or path.suffix != '.xml':
        raise ValueError('retained D094 external JUnit report required')
    report = ET.parse(path).getroot()
    cases = report.findall('.//testcase')
    assert len(cases) > 206 and not report.findall('.//failure') and not report.findall('.//error')
    assert not report.findall('.//skipped'), 'dynamic skips are not passes'
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    assert sum(c.get('name', '').startswith('test_dynamic_') for c in cases) == 16
    assert any(c.get('classname', '').endswith('test_l21_paired_fitness_run') for c in cases)
    return dict(path=str(path), tests=len(cases), failed=0, skipped=0, short_dynamic_tests=16)


def freeze_path(root):
    return root/'tmp'/f'{p.RUN_ID}_freeze.json'


def timing_path(root):
    return root/'tmp'/f'{p.RUN_ID}_benchmark.json'


def freeze(root, report):
    p.source.preflight(root)
    for path in (freeze_path(root), timing_path(root), root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID):
        if path.exists():
            raise FileExistsError('main inputs/run already reserved')
    proof = test_proof(report, root)
    inputs = hashes([*science_paths(), *source_artifacts(root), Path(proof['path'])])
    record = dict(contract=contract(), input_sha256=inputs, test_proof=proof,
                  frozen_utc=utc_now(), main_outcomes_seen=False, environment=environment_manifest())
    write_json(freeze_path(root), record, root)
    print(json.dumps(dict(status='FROZEN', input_files=len(inputs))), flush=True)
    return record


def frozen_inputs(root):
    record = read_json(freeze_path(root))
    assert canonical_digest(record['contract']) == canonical_digest(contract())
    assert record['main_outcomes_seen'] is False
    assert record['environment'] == environment_manifest(), 'frozen runtime environment changed'
    proof = test_proof(Path(record['test_proof']['path']), root)
    assert record['test_proof'] == proof
    current = hashes([*science_paths(), *source_artifacts(root), Path(proof['path'])])
    assert record['input_sha256'] == current, 'frozen scientific input changed'
    return current


def aliases(raw, meta, ctx, cfg):
    for order in ((0, 1, 2), (2, 0, 1)):
        random = p.SharedNoise(ctx['index'], meta['replicate'], f'cycle_{cfg.cycles}')
        state, fresh = p.cut(ctx, np.take(raw['prefix_ends'][-1], order, axis=1), random)
        for _ in range(cfg.inter_fission):
            state = p.advance(ctx, state, random, np.take(p.RATES, order), cfg)
        np.testing.assert_array_equal(state, np.take(raw['descendants'][-1, :, :, 0], order, axis=1))
        np.testing.assert_array_equal(fresh, np.broadcast_to(raw['fresh'][-1], fresh.shape))
        assert random.digest() == meta['rng_final'][-1]
    return 2


def checked_pair(root, directory, stem, tissue, replicate):
    start = time.monotonic()
    raw, meta = p.execute_pair(tissue, replicate, root=root)
    write_npz(directory/f'{stem}.npz', raw, root)
    write_json(directory/f'{stem}.json', meta, root)
    saved = load_npz(directory/f'{stem}.npz')
    saved_meta = read_json(directory/f'{stem}.json')
    for name in raw:
        np.testing.assert_array_equal(saved[name], raw[name])
    assert canonical_digest(saved_meta) == canonical_digest(meta)
    check = p.checker(); ctx = p.context(tissue)
    assert check.check_pair_schema(saved, saved_meta, tissue, replicate)
    error = check.replay_pair(saved, saved_meta, ctx, p.CONFIG, root=root)
    count = aliases(saved, saved_meta, ctx, p.CONFIG)
    return dict(tissue=tissue, replicate=replicate, replay_max_abs=error,
                intact_alias_orders=count, saved_metrics_checked=True, full_replay=True,
                seconds=time.monotonic()-start, raw_bytes=sum(a.nbytes for a in raw.values()),
                metadata_bytes=(directory/f'{stem}.json').stat().st_size)


def forecast(seconds, hash_seconds, raw_bytes, metadata_bytes):
    if not all(np.isfinite(x) and x > 0 for x in (seconds, hash_seconds, raw_bytes, metadata_bytes)):
        raise ValueError('positive finite timing and sizes required')
    duration = len(UNITS)*seconds+2*hash_seconds+180
    size = len(UNITS)*(raw_bytes+metadata_bytes+4096)+32*1024**2
    if size > p.source.ALLOWANCE:
        raise RuntimeError('fixed output allowance exceeded')
    return dict(projected_seconds=duration, must_detach=duration > 600, projected_bytes=size,
                forecast_does_not_credit_parallel_speedup=True)


def benchmark(root):
    p.source.preflight(root)
    if timing_path(root).exists():
        raise FileExistsError('immutable benchmark already exists')
    start = time.monotonic(); inputs = frozen_inputs(root); hash_seconds = time.monotonic()-start
    directory = require_beneath(root/'tmp'/f'{p.RUN_ID}_benchmark', root)
    directory.mkdir()
    try:
        row = checked_pair(root, directory, 'pair', p.DISPOSABLE, 0)
        write_json(directory/'checks.json', row, root)
        timing = dict(run_id=p.RUN_ID, completed_utc=utc_now(), disposable=p.DISPOSABLE,
            effects_not_reported=True, checked_pair=row, hash_seconds=hash_seconds,
            input_sha256=inputs, freeze_sha256=sha256_file(freeze_path(root)),
            files=hashes(list(directory.iterdir())), **forecast(row['seconds'], hash_seconds,
                         row['raw_bytes'], row['metadata_bytes']))
        assert inputs == frozen_inputs(root)
        write_json(timing_path(root), timing, root)
        print(json.dumps({k: timing[k] for k in ('projected_seconds', 'must_detach', 'projected_bytes')}), flush=True)
        return timing
    except Exception as error:
        failure(directory, error, root)
        raise


def validate_timing(root, timing, inputs):
    assert timing['run_id'] == p.RUN_ID and timing['disposable'] == p.DISPOSABLE
    assert timing['effects_not_reported'] is True
    assert timing['freeze_sha256'] == sha256_file(freeze_path(root))
    assert timing['input_sha256'] == inputs
    directory = root/'tmp'/f'{p.RUN_ID}_benchmark'
    assert {f.name for f in directory.iterdir()} == {'pair.npz', 'pair.json', 'checks.json'}
    assert timing['files'] == hashes(list(directory.iterdir()))
    row = read_json(directory/'checks.json')
    assert timing['checked_pair'] == row
    assert row['tissue'] == p.DISPOSABLE and row['replicate'] == 0
    assert row['full_replay'] is True and row['saved_metrics_checked'] is True
    assert 0 <= row['replay_max_abs'] <= 1e-10 and row['intact_alias_orders'] == 2
    for key, value in forecast(row['seconds'], timing['hash_seconds'], row['raw_bytes'], row['metadata_bytes']).items():
        assert timing[key] == value
    raw, meta = load_npz(directory/'pair.npz'), read_json(directory/'pair.json')
    assert p.checker().check_pair_schema(raw, meta, p.DISPOSABLE, 0)
    assert p.checker().check_boundary(raw) and p.checker().check_metrics(raw)
    assert row['raw_bytes'] == sum(a.nbytes for a in raw.values())
    assert row['metadata_bytes'] == (directory/'pair.json').stat().st_size
    return True


def hash_text(inputs):
    return ''.join(f'{inputs[path]}  {path}\n' for path in sorted(inputs))


def prepare(root):
    p.source.preflight(root)
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    if run.exists() or out.exists():
        raise FileExistsError('immutable main run already exists')
    inputs = frozen_inputs(root); timing = read_json(timing_path(root))
    assert validate_timing(root, timing, inputs)
    inputs = inputs | timing['files'] | hashes([freeze_path(root), timing_path(root)])
    manifest = dict(contract=contract(), input_sha256=inputs, hash_contract=canonical_digest(inputs),
                    timing=timing, environment=environment_manifest(), prepared_utc=utc_now())
    require_beneath(run, root).mkdir(); require_beneath(out, root).mkdir()
    write_json(run/'MANIFEST.json', manifest, root)
    with (out/'input_hashes.sha256').open('x') as handle:
        handle.write(hash_text(inputs))
    write_json(run/'STATUS.json', dict(status='PREPARED', run_id=p.RUN_ID), root)
    print(json.dumps(dict(status='PREPARED', input_files=len(inputs), **{k: timing[k]
                         for k in ('projected_seconds', 'must_detach', 'projected_bytes')})), flush=True)
    return manifest


def verify_manifest(root):
    manifest = read_json(root/'runs'/p.RUN_ID/'MANIFEST.json')
    assert canonical_digest(manifest['contract']) == canonical_digest(contract())
    inputs = frozen_inputs(root); timing = read_json(timing_path(root))
    assert timing == manifest['timing'] and validate_timing(root, timing, inputs)
    inputs = inputs | timing['files'] | hashes([freeze_path(root), timing_path(root)])
    assert manifest['input_sha256'] == inputs and manifest['hash_contract'] == canonical_digest(inputs)
    assert (root/'outputs'/p.RUN_ID/'input_hashes.sha256').read_text() == hash_text(inputs)
    return manifest


def prepared(root):
    manifest = verify_manifest(root); run = root/'runs'/p.RUN_ID
    assert read_json(run/'STATUS.json') == dict(status='PREPARED', run_id=p.RUN_ID)
    assert not any((run/x).exists() for x in ('COMPLETE.json', 'FAILED.json', 'EXECUTION.lock'))
    assert {x.name for x in (root/'outputs'/p.RUN_ID).iterdir()} == {'input_hashes.sha256'}
    return manifest


def detach(root):
    p.source.preflight(root); manifest = prepared(root)
    run = root/'runs'/p.RUN_ID
    (run/'LAUNCH.lock').mkdir()
    logs = [root/'logs'/f'{p.RUN_ID}.{kind}.log' for kind in ('stdout', 'stderr')]
    with logs[0].open('xb') as out, logs[1].open('xb') as err:
        child = subprocess.Popen([sys.executable, '-m', 'laws_confirmation.l21_paired_fitness_run',
            '--external-root', str(root), '--run'], cwd=WS, stdin=subprocess.DEVNULL,
            stdout=out, stderr=err, start_new_session=True)
    record = dict(pid=child.pid, launched_utc=utc_now(), polling_owner='user',
                  estimated_seconds=manifest['timing']['projected_seconds'],
                  status=str(run/'STATUS.json'), stdout_log=str(logs[0]), stderr_log=str(logs[1]))
    write_json(run/'LAUNCH.json', record, root)
    print(json.dumps(record, indent=2), flush=True)
    return record


def detached_guard(root, required):
    if required:
        run = root/'runs'/p.RUN_ID
        if not (run/'LAUNCH.lock').is_dir() or os.getsid(0) != os.getpid():
            raise RuntimeError('new-session detached launch required; a lock alone is insufficient')
        if Path('/proc/self/fd/0').resolve() != Path('/dev/null'):
            raise RuntimeError('detached stdin must be /dev/null')
        for fd, kind in ((1, 'stdout'), (2, 'stderr')):
            if Path(f'/proc/self/fd/{fd}').resolve() != root/'logs'/f'{p.RUN_ID}.{kind}.log':
                raise RuntimeError('detached output must use declared external logs')


def worker(root, tissue, replicate):
    return checked_pair(root, root/'outputs'/p.RUN_ID, pair_name(tissue, replicate), tissue, replicate)


def run_experiment(root):
    p.source.preflight(root); manifest = prepared(root)
    detached_guard(root, manifest['timing']['must_detach'])
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    (run/'EXECUTION.lock').mkdir(); start = time.monotonic()
    try:
        checks = {}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            pending = {pool.submit(worker, root, t, r): (t, r) for t, r in UNITS}
            try:
                for future in as_completed(pending):
                    address = pending[future]; checks[address] = future.result()
                    p.source.preflight(root, starting=False)
                    p.source.strict_json(run/'STATUS.json', dict(status='RUNNING', run_id=p.RUN_ID,
                        checked_pairs=len(checks), updated_utc=utc_now()), root)
                    print(f'D094 pair {address}: saved independent replay and two aliases pass', flush=True)
            except Exception:
                for future in pending:
                    future.cancel()
                raise
        assert set(checks) == set(UNITS)
        records = [p.final_score_record(load_npz(out/f'{pair_name(t,r)}.npz'),
                   read_json(out/f'{pair_name(t,r)}.json')) for t, r in UNITS]
        write_json(out/'summary.json', p.summarize(records), root)
        write_json(out/'verification.json', dict(schema='l21_paired_fitness_checks_v1',
                   rows=[checks[x] for x in UNITS], checked_pairs=16, independent_replays=16,
                   intact_alias_orders=32, checked_utc=utc_now()), root)
        audit = p.checker().check_saved(root, complete=False)
        paths = [out/name for name in output_names()]
        output_hashes = hashes(paths)
        with (out/'output_hashes.sha256').open('x') as handle:
            handle.write(hash_text(output_hashes))
        size = sum(x.stat().st_size for x in paths)+(out/'output_hashes.sha256').stat().st_size
        assert size <= manifest['timing']['projected_bytes'] <= p.source.ALLOWANCE
        p.source.preflight(root, starting=False)
        status = dict(status='COMPLETE', run_id=p.RUN_ID, completed_utc=utc_now(),
                      elapsed_seconds=time.monotonic()-start, output_bytes=size,
                      output_sha256=output_hashes, manifest_sha256=sha256_file(run/'MANIFEST.json'),
                      hash_file_sha256=sha256_file(out/'output_hashes.sha256'), saved_audit=audit)
        write_json(run/'COMPLETE.json', status, root)
        p.source.strict_json(run/'STATUS.json', status, root)
        print(json.dumps({k: status[k] for k in ('status', 'elapsed_seconds', 'output_bytes', 'saved_audit')}, indent=2), flush=True)
        return 0
    except Exception as error:
        failure(run, error, root)
        p.source.strict_json(run/'STATUS.json', dict(status='FAILED', run_id=p.RUN_ID,
                             error=str(error), automatic_retry=False), root)
        raise


def main():
    if sys.flags.optimize:
        raise RuntimeError('optimized Python disables audit assertions and is not permitted')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', type=Path, required=True)
    parser.add_argument('--test-report', type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ('source-controls', 'freeze', 'benchmark', 'prepare', 'run', 'detach', 'audit'):
        group.add_argument('--'+name, action='store_true')
    args = parser.parse_args(); root = external_root(args.external_root)
    if args.freeze != (args.test_report is not None):
        parser.error('--test-report is required only with --freeze')
    if args.audit:
        print(json.dumps(p.checker().check_saved(root), indent=2)); return 0
    if args.freeze:
        freeze(root, args.test_report); return 0
    for name in ('source_controls', 'benchmark', 'prepare', 'run', 'detach'):
        if getattr(args, name):
            value = (run_experiment if name == 'run' else globals()[name])(root)
            return value if type(value) is int else 0


if __name__ == '__main__':
    raise SystemExit(main())
