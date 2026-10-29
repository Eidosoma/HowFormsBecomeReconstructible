"""D111 six-CPU, external-only, write-once qualification and saved audit."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

from . import l16_body_content as p
from . import l15_repair_speed_run as u
from .io import (DEFAULT_EXTERNAL_ROOT, atomic_json, environment_manifest, external_root,
                 git_head, sha256_file, utc_now)

WORKERS = 6
RESERVE, ALLOWANCE = 4*1024**3, 512*1024**2
SOURCE_DIGEST = '46a00eebd4ed079dbd5aa3ee15df5bd4c94ac535cbde4d1c3b9c87ea173f4ebc'


def preflight(root, starting=True):
    assert not sys.flags.optimize, 'assertions must be enabled'
    assert external_root(root) == DEFAULT_EXTERNAL_ROOT.resolve() == root.resolve()
    affinity = set(os.sched_getaffinity(0))
    if not affinity or len(affinity) > WORKERS or not affinity <= set(range(WORKERS)):
        raise RuntimeError('at most CPUs0-5 required')
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        if os.environ.get(key) != '1':
            raise RuntimeError(key+'=1 required')
    if os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
        raise RuntimeError('bytecode writes must be disabled')
    for key in ('TMPDIR', 'XDG_CACHE_HOME'):
        path = Path(os.environ.get(key, '/')).resolve()
        if root not in path.parents or not path.is_dir():
            raise RuntimeError('external '+key+' required')
    if shutil.disk_usage(root).free < RESERVE + (ALLOWANCE if starting else 0):
        raise RuntimeError('external reserve/allowance gate failed')
    return sorted(affinity)


def source_paths():
    return [p.ORIGIN/f'hidden_genome/results/full/work/knife_shard_{i:02d}_of_03.json' for i in range(3)]


def source_expected():
    result = {}
    for path in source_paths():
        data = u.read_json(path)
        assert data['config_digest'] == SOURCE_DIGEST
        for row in data['entries']:
            assert row['tissue'] not in result
            result[row['tissue']] = row
    assert set(result) == set(range(6))
    return result


def science_paths(root):
    files = [p.WS/n for n in (*p.SCIENCE, 'REVIEW_PROTOCOL.md', 'laws/L16_landlord_tenant.md',
        'reviews/L16_LANDLORD_TENANT_AUDIT_2026-09-02.md', 'reviews/L16_NEXT_STEP_2026-09-13.md',
        'reviews/L19_CLOSEOUT_2026-09-13.md', 'src/laws_confirmation/l15_repair_speed.py',
        'src/laws_confirmation/l15_repair_speed_run.py', 'src/laws_confirmation/io.py',
        'scripts/audit_l15_repair_speed_outputs.py', 'tests/test_l16_audit.py')]
    files += [p.ORIGIN/'LAWS.md', p.ORIGIN/'hidden_genome/EXPECTATIONS.md', *source_paths()]
    for package in p.PACKAGES:
        files.extend((p.ORIGIN/package/'src').rglob('*.py'))
    return sorted(set(files))


def test_proof(report, root):
    report = u.require_beneath(report, root/'logs')
    assert not report.is_symlink() and report.name.startswith('d111_') and report.suffix == '.xml'
    tree = ET.parse(report).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 40 and not any(tree.findall('.//'+k) for k in ('failure', 'error', 'skipped'))
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    names = {c.get('name', '').split('[', 1)[0] for c in cases}
    assert {'test_e53_exact_source_bridge', 'test_full_disposable_replay', 'test_birth_histograms',
        'test_no_donor_reference_or_ema', 'test_arm_order_and_noise', 'test_independent_observer',
        'test_gate_failure_not_no_memory', 'test_saved_roundtrip', 'test_external_and_cpu_guards',
        'test_rank_stable_ties', 'test_raw_corruption', 'test_summary_corruption',
        'test_source_metadata_corruption', 'test_fresh_process_import', 'test_reservation_guards'} <= names
    source_seconds = max(float(c.get('time', '0')) for c in cases if c.get('name') == 'test_e53_exact_source_bridge')
    block_seconds = max(float(c.get('time', '0')) for c in cases if c.get('name') == 'test_full_disposable_replay')
    return dict(path=str(report), tests=len(cases), failed=0, skipped=0,
                source_test_seconds=source_seconds, block_test_seconds=block_seconds)


def source_worker(root, directory, index):
    preflight(root, False)
    raw, meta = p.source_control(index)
    assert meta['result'] == source_expected()[index]
    u.save_pair(directory, f'tissue_{index}', raw, meta, root)
    return dict(index=index, **meta['replay'])


def source_controls(root, report):
    preflight(root); proof = test_proof(report, root)
    forecast = 12*proof['source_test_seconds']+60
    assert forecast <= 600, 'source bridge requires a separate detached design'
    directory = root/'outputs'/p.CONTROL_ID
    inputs = u.hashes(science_paths(root)+[report])
    directory.mkdir(); start = time.monotonic()
    try:
        u.write_json(directory/'INPUTS.json', dict(input_sha256=inputs, test_proof=proof,
            contract=contract(), environment=environment_manifest(), projected_seconds=forecast), root)
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs = [pool.submit(source_worker, root, directory, i) for i in range(6)]
            rows = [job.result() for job in jobs]
        summary = dict(known_outcomes=True, qualification_pool=False, rows=rows,
            source_jobs=6, exact_cached_scalars=True, full_independent_replays=6,
            branches=120, futures_per_branch=8, max_abs=max(r['max_abs'] for r in rows))
        u.write_json(directory/'summary.json', summary, root)
        assert inputs == u.hashes(science_paths(root)+[report])
        preflight(root, False)
        complete = dict(status='COMPLETE', elapsed_seconds=time.monotonic()-start,
            completed_utc=utc_now(), output_sha256=u.hashes(list(directory.iterdir())))
        u.write_json(directory/'COMPLETE.json', complete, root)
        print(json.dumps(dict(status='SOURCE_COMPLETE', seconds=complete['elapsed_seconds'], **summary), indent=2), flush=True)
    except Exception as error:
        u.failure(directory, error, root); raise


def source_artifacts(root, report):
    directory = root/'outputs'/p.CONTROL_ID
    names = {f'tissue_{i}.{ext}' for i in range(6) for ext in ('json', 'npz')} | {'INPUTS.json', 'summary.json', 'COMPLETE.json'}
    assert {x.name for x in directory.iterdir()} == names
    inputs, complete = u.read_json(directory/'INPUTS.json'), u.read_json(directory/'COMPLETE.json')
    assert complete['status'] == 'COMPLETE'
    assert inputs['input_sha256'] == u.hashes(science_paths(root)+[report])
    assert inputs['test_proof'] == test_proof(report, root) and inputs['environment'] == environment_manifest()
    p.checker().nested(inputs['contract'], contract())
    assert complete['output_sha256'] == u.hashes([directory/n for n in names if n != 'COMPLETE.json'])
    expected = source_expected(); rows = []
    for i in range(6):
        meta = u.read_json(directory/f'tissue_{i}.json')
        assert meta['index'] == i and meta['result'] == expected[i]
        proof = meta['replay']
        assert proof['full_source_replay'] is True and 0 <= proof['max_abs'] <= 1e-10
        assert proof['branches'] == 20 and proof['futures_per_branch'] == 8
        rows.append(dict(index=i, **proof))
    assert u.read_json(directory/'summary.json') == dict(known_outcomes=True, qualification_pool=False,
        rows=rows, source_jobs=6, exact_cached_scalars=True, full_independent_replays=6,
        branches=120, futures_per_branch=8, max_abs=max(r['max_abs'] for r in rows))
    return [directory/n for n in sorted(names)]


def output_names():
    return tuple(f'block_{t}.{ext}' for t in p.TISSUES for ext in ('npz', 'json')) + (
        'summary.json', 'verification.json', 'input_hashes.sha256')


def contract():
    return p.contract() | dict(workers=WORKERS, cpu_affinity_max=list(range(WORKERS)),
        reserve_bytes=RESERVE, allowance_bytes=ALLOWANCE, detach_above_seconds=600,
        output_files=list(output_names()), output_hash_count=19,
        forecast='8*checked_block_seconds+2*hash_seconds+180',
        storage_forecast='8*raw_block_bytes+source_bytes+benchmark_bytes+32MiB',
        successor='none; qualification readout failure stops inference, any confirmation needs a new freeze')


def freeze_path(root): return root/'tmp'/f'{p.RUN_ID}_freeze.json'
def timing_path(root): return root/'tmp'/f'{p.RUN_ID}_benchmark.json'
def benchmark_dir(root): return root/'tmp'/f'{p.RUN_ID}_benchmark'


def freeze(root, report):
    preflight(root); proof = test_proof(report, root)
    for target in (freeze_path(root), timing_path(root), benchmark_dir(root), root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID):
        if target.exists(): raise FileExistsError(target)
    inputs = u.hashes(science_paths(root)+[report]+source_artifacts(root, report))
    u.write_json(freeze_path(root), dict(frozen_utc=utc_now(), contract=contract(), input_sha256=inputs,
        environment=environment_manifest(), git_head=git_head(p.WS), test_proof=proof, qualification_futures_seen=0), root)
    print(f'D111 frozen: {len(inputs)} inputs, zero qualification futures', flush=True)


def frozen(root):
    saved = u.read_json(freeze_path(root)); report = Path(saved['test_proof']['path'])
    p.checker().nested(saved['contract'], contract())
    assert saved['qualification_futures_seen'] == 0 and saved['environment'] == environment_manifest()
    assert saved['test_proof'] == test_proof(report, root)
    assert saved['input_sha256'] == u.hashes(science_paths(root)+[report]+source_artifacts(root, report))
    return saved


def checked_block(root, directory, index):
    preflight(root, False)
    assert index in p.TISSUES or index == p.DISPOSABLE
    raw, meta = p.execute_block(index)
    saved = u.save_pair(directory, f'block_{index}', raw, meta, root)
    assert p.checker().check_block(saved, u.read_json(directory/f'block_{index}.json'), p.CONFIG, replay=False)
    return dict(index=index, full_life_replays=2, exact_sham_aliases=8,
        max_abs=max(m['replay']['max_abs'] for m in meta['lives']),
        uncompressed_bytes=sum(a.nbytes for a in raw.values()))


def benchmark(root):
    preflight(root); saved = frozen(root)
    # Full-config disposable replay was timed by the technical suite, not a fresh-seed pilot.
    assert 4*saved['test_proof']['block_test_seconds']+60 <= 600, 'benchmark needs detachment design'
    directory = benchmark_dir(root); directory.mkdir(); start = time.monotonic()
    try:
        block = checked_block(root, directory, p.DISPOSABLE)
        raw = u.load_npz(directory/f'block_{p.DISPOSABLE}.npz')
        assert p.checker().check_summary(p.summarize([raw]*8), [raw]*8, p.CONFIG)
        seconds = time.monotonic()-start
        hstart = time.monotonic(); frozen(root); hseconds = time.monotonic()-hstart
        paths = list(directory.iterdir()); size = sum(x.stat().st_size for x in paths)
        source_bytes = sum(x.stat().st_size for x in (root/'outputs'/p.CONTROL_ID).iterdir())
        forecast = 8*seconds+2*hseconds+180
        budget = 8*block['uncompressed_bytes']+size+source_bytes+32*1024**2
        assert budget <= ALLOWANCE, 'budget exceeded; no automatic reduction'
        preflight(root)
        timing = dict(benchmark_utc=utc_now(), disposable=p.DISPOSABLE, qualification_pool=False,
            block=block, checked_block_seconds=seconds, hash_seconds=hseconds,
            projected_seconds=forecast, must_detach=forecast > 600, projected_total_bytes=budget,
            source_bytes=source_bytes, benchmark_bytes=size, artifact_sha256=u.hashes(paths),
            freeze_sha256=sha256_file(freeze_path(root)))
        u.write_json(timing_path(root), timing, root)
        print(json.dumps({k: timing[k] for k in ('checked_block_seconds', 'projected_seconds', 'must_detach', 'projected_total_bytes')}, indent=2), flush=True)
    except Exception as error:
        u.failure(directory, error, root); raise


def timing_checked(root):
    t = u.read_json(timing_path(root))
    assert t['freeze_sha256'] == sha256_file(freeze_path(root))
    assert t['disposable'] == p.DISPOSABLE and t['qualification_pool'] is False
    assert t['artifact_sha256'] == u.hashes(list(benchmark_dir(root).iterdir()))
    forecast = 8*t['checked_block_seconds']+2*t['hash_seconds']+180
    assert np.isfinite(forecast) and forecast > 0 and t['projected_seconds'] == forecast
    assert t['must_detach'] == (forecast > 600)
    assert t['projected_total_bytes'] == 8*t['block']['uncompressed_bytes']+t['source_bytes']+t['benchmark_bytes']+32*1024**2
    assert 0 < t['projected_total_bytes'] <= ALLOWANCE
    return t


def main_inputs(root):
    saved = frozen(root); timing_checked(root)
    return u.hashes([Path(x) for x in saved['input_sha256']] + [freeze_path(root), timing_path(root), *benchmark_dir(root).iterdir()])


def prepare(root):
    preflight(root); inputs = main_inputs(root); timing = timing_checked(root)
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    if run.exists() or out.exists(): raise FileExistsError('single-use identity already reserved')
    run.mkdir(); out.mkdir()
    try:
        u.write_json(run/'MANIFEST.json', dict(contract=contract(), input_sha256=inputs,
            environment=environment_manifest(), timing=timing, prepared_utc=utc_now(), git_head=git_head(p.WS)), root)
        with (out/'input_hashes.sha256').open('x') as handle: handle.write(u.hash_text(inputs))
        atomic_json(run/'STATUS.json', dict(status='PREPARED', run_id=p.RUN_ID, timing=timing), root)
        print(f'D111 prepared: {len(inputs)} inputs, forecast {timing["projected_seconds"]:.1f}s', flush=True)
    except Exception as error:
        u.failure(run, error, root); raise


def prepared(root):
    manifest = u.read_json(root/'runs'/p.RUN_ID/'MANIFEST.json')
    p.checker().nested(manifest['contract'], contract())
    assert manifest['input_sha256'] == main_inputs(root)
    assert manifest['environment'] == environment_manifest() and manifest['timing'] == timing_checked(root)
    assert (root/'outputs'/p.RUN_ID/'input_hashes.sha256').read_text() == u.hash_text(manifest['input_sha256'])
    return manifest


def detached_guard(root, required):
    run = root/'runs'/p.RUN_ID
    if required or (run/'LAUNCH.json').exists():
        launch = u.read_json(run/'LAUNCH.json')
        assert launch['pid'] == os.getpid() == os.getsid(0)
        assert launch['log'] == str(root/'logs'/f'{p.RUN_ID}.log')
        assert os.readlink('/proc/self/fd/0') == '/dev/null'
        assert all(os.readlink('/proc/self/fd/'+str(fd)) == launch['log'] for fd in (1, 2))
        assert launch['manifest_sha256'] == sha256_file(run/'MANIFEST.json')


def detach(root):
    preflight(root); prepared(root); run = root/'runs'/p.RUN_ID
    for name in ('EXECUTION.lock', 'COMPLETE.json', 'FAILED.json'):
        if (run/name).exists(): raise FileExistsError('execution already attempted')
    (run/'LAUNCH.lock').mkdir(); log = root/'logs'/f'{p.RUN_ID}.log'
    env = os.environ.copy(); env['L16_BODY_CONTENT_DETACHED_LOG'] = str(log)
    command = [sys.executable, '-m', 'laws_confirmation.l16_body_content_run', '--external-root', str(root), '--run']
    with log.open('xb') as handle:
        child = subprocess.Popen(command, cwd=p.WS, env=env, stdin=subprocess.DEVNULL,
            stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    print(json.dumps(dict(status='DETACHED', pid=child.pid, log=str(log), user_polls=True, automatic_polling=False)), flush=True)


def audit(root, complete=True, replay=False):
    preflight(root, False); manifest = prepared(root)
    out, run = root/'outputs'/p.RUN_ID, root/'runs'/p.RUN_ID
    assert {x.name for x in out.iterdir()} == set(output_names()) | ({'output_hashes.sha256'} if complete else set())
    assert (run/'EXECUTION.lock').is_dir() and not (run/'FAILED.json').exists()
    if replay: assert manifest['timing']['projected_seconds'] <= 600, 'long replay needs separate detached design'
    p.api(); blocks = []
    for index in p.TISSUES:
        raw, meta = u.load_npz(out/f'block_{index}.npz'), u.read_json(out/f'block_{index}.json')
        assert type(meta['index']) is int and meta['index'] == index
        assert p.checker().check_block(raw, meta, p.CONFIG, replay)
        blocks.append(raw)
    summary = u.read_json(out/'summary.json')
    assert p.checker().check_summary(summary, blocks, p.CONFIG)
    v = u.read_json(out/'verification.json')
    assert v['independent_life_replays'] == 16 and v['exact_sham_aliases'] == 64
    assert [r['index'] for r in v['rows']] == list(p.TISSUES)
    assert all(r['full_life_replays'] == 2 and r['exact_sham_aliases'] == 8 and 0 <= r['max_abs'] <= 1e-10 for r in v['rows'])
    if complete:
        status = u.read_json(run/'COMPLETE.json')
        assert status['status'] == 'COMPLETE' and u.read_json(run/'STATUS.json') == status
        actual = u.hashes([out/n for n in output_names()])
        assert status['output_sha256'] == actual
        assert (out/'output_hashes.sha256').read_text() == u.hash_text(actual)
        assert status['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
        assert status['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
        assert status['output_bytes'] == sum(x.stat().st_size for x in out.iterdir()) <= manifest['timing']['projected_total_bytes']
    return dict(passes=True, checked_blocks=8, checked_lives=16, branches=384,
        exact_sham_aliases=64, full_dynamics_replayed_now=replay,
        input_hashes=len(manifest['input_sha256']), output_hashes=19 if complete else 0,
        label=summary['label'], primary=summary['primary'], readout_qualified=summary['readout_qualified'])


def run_experiment(root):
    preflight(root); manifest = prepared(root)
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    if 'L16_BODY_CONTENT_DETACHED_LOG' in os.environ:
        u.write_json(run/'LAUNCH.json', dict(pid=os.getpid(), launched_utc=utc_now(),
            log=os.environ['L16_BODY_CONTENT_DETACHED_LOG'], manifest_sha256=sha256_file(run/'MANIFEST.json')), root)
    detached_guard(root, manifest['timing']['must_detach'])
    (run/'EXECUTION.lock').mkdir(); start = time.monotonic()
    try:
        checked = {}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs = {pool.submit(checked_block, root, out, index): index for index in p.TISSUES}
            for job in as_completed(jobs):
                index = jobs[job]; checked[index] = job.result(); preflight(root, False)
                atomic_json(run/'STATUS.json', dict(status='RUNNING', run_id=p.RUN_ID,
                    checked_blocks=len(checked), updated_utc=utc_now()), root)
                print(f'D111 tissue{index}: full native replay and eight sham aliases pass', flush=True)
        blocks = [u.load_npz(out/f'block_{i}.npz') for i in p.TISSUES]
        u.write_json(out/'summary.json', p.summarize(blocks), root)
        u.write_json(out/'verification.json', dict(independent_life_replays=16, exact_sham_aliases=64,
            rows=[checked[i] for i in p.TISSUES], checked_utc=utc_now()), root)
        saved_audit = audit(root, complete=False)
        actual = u.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as handle: handle.write(u.hash_text(actual))
        size = sum(x.stat().st_size for x in out.iterdir())
        assert size <= manifest['timing']['projected_total_bytes'] <= ALLOWANCE
        preflight(root, False)
        status = dict(status='COMPLETE', run_id=p.RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start, output_bytes=size, output_sha256=actual,
            manifest_sha256=sha256_file(run/'MANIFEST.json'), hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            saved_audit=saved_audit)
        u.write_json(run/'COMPLETE.json', status, root); atomic_json(run/'STATUS.json', status, root)
        print(json.dumps({k: status[k] for k in ('status', 'elapsed_seconds', 'output_bytes', 'saved_audit')}, indent=2), flush=True)
    except Exception as error:
        u.failure(run, error, root)
        atomic_json(run/'STATUS.json', dict(status='FAILED', error=str(error), automatic_retry=False), root)
        raise


def main(default_command=None):
    if sys.flags.optimize: raise RuntimeError('assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', type=Path, required=True)
    parser.add_argument('--test-report', type=Path); parser.add_argument('--replay', action='store_true')
    group = parser.add_mutually_exclusive_group(required=default_command is None)
    commands = ('source_controls', 'freeze', 'benchmark', 'prepare', 'run', 'detach', 'audit')
    for name in commands: group.add_argument('--'+name.replace('_', '-'), action='store_true')
    args = parser.parse_args(); root = external_root(args.external_root)
    chosen = [name for name in commands if getattr(args, name)]
    command = chosen[0] if chosen else default_command
    if (command in ('source_controls', 'freeze')) != (args.test_report is not None):
        parser.error('--test-report required only for source-controls/freeze')
    if args.replay and command != 'audit': parser.error('--replay is audit-only')
    if command == 'audit': print(json.dumps(audit(root, replay=args.replay), indent=2)); return
    if command in ('source_controls', 'freeze'): globals()[command](root, args.test_report)
    else: (run_experiment if command == 'run' else globals()[command])(root)


if __name__ == '__main__': main()
