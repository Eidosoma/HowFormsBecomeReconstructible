"""D097 write-once calibration, freeze, benchmark, launch and saved audit."""
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
import traceback
import xml.etree.ElementTree as ET

import numpy as np

from . import l15_repair_speed as p
from .io import (atomic_json, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now)

WORKERS = 4
RESERVE, ALLOWANCE = 4*1024**3, 512*1024**2
SOURCE_UNITS = tuple((arm, i) for arm in ('D','T','T_lesion') for i in range(12))
OLD_HASHES = {
    'audit.json': '9ad8f8cc4b45863b68e26147f75737cf24b19700ac7ac73d0c934b1a053d51a8',
    'audit.md': '9c53695639fcb47dacb28caadfa77f7334e76df33d6668476f554f41f51d81d2',
    'e48_surface.csv': 'f54657902d37a1df3a43ca1a1218af8e116d46d07123d476416e15abfb764305',
    'e49_tissue_contrasts.csv': '0b35807900c5e9cb347fab441873228c53d588e8c7e39f7cb534e145ec41a36a',
    'input_hashes.sha256': 'a69523938b6a1fa34188225aa1b39238bfa3d6bebb8fdce28b580cac1acb21ae'}
LEGACY_CASE = dict(path=str(p.WS/'laws/L15_timescale.md'),
    historical_sha256='8db888526c892de2b46c375dd4060d67951b6c9103ebac9de86da60b3659cfb7',
    current_sha256='883781eb0c3478bc33a7684a3f072371735b49b59d37341dc7f87fe9f5337977',
    reason='historical manifest predates final post-audit case note; exact revision pinned, not restored')


def read_json(path):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('duplicate JSON key: '+key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('nonfinite JSON: '+value)
    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=invalid)


def write_json(path, value, root):
    target = require_beneath(path, root)
    if path.is_symlink():
        raise ValueError('no artifact symlinks')
    payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target.open('x') as handle:
        handle.write(payload)


def write_npz(path, raw, root):
    target = require_beneath(path, root)
    if path.is_symlink():
        raise ValueError('no artifact symlinks')
    with target.open('xb') as handle:
        np.savez_compressed(handle, **raw)


def load_npz(path):
    with np.load(path, allow_pickle=False) as saved:
        assert len(saved.files) == len(set(saved.files)), 'duplicate NPZ field'
        return dict(saved)


def hashes(paths):
    paths = list(paths)
    assert len(paths) == len(set(paths)), 'duplicate hash input'
    assert all(x.is_file() and not x.is_symlink() for x in paths), 'regular input files required'
    return {str(x.resolve()): sha256_file(x) for x in sorted(paths)}


def hash_text(mapping):
    return ''.join(f'{digest}  {path}\n' for path, digest in sorted(mapping.items()))


def preflight(root, starting=True):
    assert not sys.flags.optimize, 'audit assertions must remain enabled'
    assert external_root(root) == root.resolve()
    cpus = sorted(os.sched_getaffinity(0))
    if not cpus or len(cpus) > 4 or not set(cpus) <= set(range(4)):
        raise RuntimeError('at most CPUs 0-3 required')
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        if os.environ.get(key) != '1':
            raise RuntimeError(key+'=1 required')
    if os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
        raise RuntimeError('disable bytecode writes')
    for key in ('TMPDIR','XDG_CACHE_HOME'):
        path = Path(os.environ.get(key,'/')).resolve()
        if root not in path.parents or not path.is_dir():
            raise RuntimeError('external '+key+' required')
    if shutil.disk_usage(root).free < RESERVE+(ALLOWANCE if starting else 0):
        raise RuntimeError('external reserve/allowance gate failed')
    return cpus


def failure(directory, error, root):
    write_json(directory/'FAILED.json', dict(failed_utc=utc_now(), error=str(error),
               traceback=traceback.format_exc(), automatic_retry=False), root)


def source_cache_paths():
    return [p.ORIGIN/f'triangle_final/results/full/work/triangle_shard_{i:02d}_of_04.json' for i in range(4)]


def source_expected():
    rows = {}
    for path in source_cache_paths():
        data = read_json(path); assert data['config_digest'] == p.SOURCE_DIGEST
        for entry in data['entries']:
            if entry['kind'] == 'transport':
                key = (entry['arm'], entry['tissue']); assert key not in rows
                rows[key] = {k:v for k,v in entry.items() if k != 'kind'}
    assert set(rows) == set(SOURCE_UNITS)
    return rows


def science_paths(root):
    old = root/'outputs/l15_timescale_audit_v1'
    for name, digest in OLD_HASHES.items():
        assert sha256_file(old/name) == digest, 'old L15 output drift: '+name
    old_rows = [line.split('  ',1) for line in (old/'input_hashes.sha256').read_text().splitlines()]
    assert len(old_rows) == 111 and len({x[1] for x in old_rows}) == 111
    for digest, name in old_rows:
        if name == LEGACY_CASE['path']:
            assert digest == LEGACY_CASE['historical_sha256']
            assert sha256_file(Path(name)) == LEGACY_CASE['current_sha256'], 'unrecognized case-note revision'
        else:
            assert sha256_file(Path(name)) == digest, 'old L15 input drift: '+name
    assert sum(name == LEGACY_CASE['path'] for _,name in old_rows) == 1
    paths = [Path(x[1]) for x in old_rows]+[old/n for n in OLD_HASHES]
    paths += [p.WS/x for x in (*p.SCIENCE, 'src/laws_confirmation/io.py',
        'src/laws_confirmation/__init__.py', 'src/laws_confirmation/l15_audit.py',
        'tests/test_l15_audit.py', 'laws/L15_timescale.md',
        'reviews/L15_TIMESCALE_AUDIT_2026-09-02.md', 'reviews/L21_CLOSEOUT_2026-09-12.md')]
    paths += [p.ORIGIN/'LAWS.md', p.WS.parents[3]/'PRE_PRINT_PAPER_DRAFT_V2.3.md',
              p.ORIGIN/'triangle_final/EXPECTATIONS.md', *source_cache_paths()]
    assert sha256_file(p.ORIGIN/'LAWS.md') == 'd4205acf612f7eb7f4d63022ee9bc9a66d0c35c114b5a3930bab982788e011db'
    assert sha256_file(p.WS.parents[3]/'PRE_PRINT_PAPER_DRAFT_V2.3.md') == 'c0a80cdcda6373708639a25bfb535a8df979a8b7b820a09f3ff37b78aea686d0'
    for package in p.PACKAGES:
        files = sorted((p.ORIGIN/package/'src').rglob('*.py')); assert files
        paths.extend(files)
    return sorted(set(paths))


def test_proof(path, root):
    path = require_beneath(path, root/'logs')
    if path.is_symlink() or not path.name.startswith('d097_') or path.suffix != '.xml':
        raise ValueError('retained external D097 JUnit report required')
    report = ET.parse(path).getroot(); cases = report.findall('.//testcase')
    assert len(cases) >= 60 and not any(report.findall('.//'+x) for x in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases}) == len(cases)
    names = {c.get('name') for c in cases}
    assert {'test_fresh_process_import', 'test_dynamic_complete_block_replay',
            'test_dynamic_matched_body_and_reference_controls', 'test_dynamic_order_and_duplicate_aliases',
            'test_hand_built_block_pooling', 'test_saved_summary_corruptions',
            'test_l15_recalculates_bounded_results_without_inventing_timescale_effect'} <= names
    assert any(c.get('classname','').endswith('test_l15_repair_speed') for c in cases)
    return dict(path=str(path), tests=len(cases), failed=0, skipped=0)


def save_pair(directory, name, raw, meta, root):
    write_npz(directory/(name+'.npz'), raw, root)
    write_json(directory/(name+'.json'), meta, root)
    loaded = load_npz(directory/(name+'.npz')); assert set(loaded) == set(raw)
    for key in raw:
        np.testing.assert_array_equal(loaded[key], raw[key])
    assert canonical_digest(read_json(directory/(name+'.json'))) == canonical_digest(meta)
    return loaded


def source_worker(root, arm, index):
    preflight(root, starting=False)
    raw, meta = p.source_control(arm,index)
    expected = source_expected()[(arm,index)]
    assert meta['result'] == expected, 'retained source scalar drift'
    save_pair(root/'outputs'/p.CONTROL_ID, f'{arm}_{index}', raw, meta, root)
    return meta


def source_summary(directory):
    expected = source_expected(); records = []
    for arm,index in SOURCE_UNITS:
        meta = read_json(directory/f'{arm}_{index}.json')
        assert meta['arm'] == arm and type(meta['index']) is int and meta['index'] == index
        assert meta['result'] == expected[(arm,index)]
        assert meta['replay']['full_source_replay'] is True and meta['replay']['max_abs'] <= 1e-10
        assert meta['config'] == json.loads(json.dumps(p.api()['TriangleConfig']().as_dict()))
        records.append(meta)
    means = {}
    for arm in ('D','T','T_lesion'):
        means[arm] = {metric: float(np.mean([row['result']['by_distance'][str(d)][metric]
            for row in records if row['arm']==arm for d in (4,6,8)]))
            for metric in ('profile_recovery','sign_recovery')}
    return dict(source_jobs=36, distance_cells=108, futures_per_job=16, exact_cached_scalars=True,
        full_independent_source_replays=36, max_abs=max(r['replay']['max_abs'] for r in records),
        known_outcomes=True, main_pool=False, means=means,
        T_minus_lesion={m:means['T'][m]-means['T_lesion'][m] for m in means['T']})


def source_controls(root, report):
    preflight(root); proof = test_proof(report,root)
    # Archived four-shard run included all 150 E49 jobs, not just these 36.
    # Three times its slowest shard plus 30 s conservatively allows replay/I/O.
    source_forecast = 3*max(read_json(x)['elapsed_seconds'] for x in source_cache_paths())+30
    assert source_forecast <= 600, 'source-calibration forecast requires a detached design before reservation'
    inputs = hashes(science_paths(root)+[report])
    directory = root/'outputs'/p.CONTROL_ID; directory.mkdir()
    start = time.monotonic()
    try:
        write_json(directory/'INPUTS.json', dict(input_sha256=inputs, test_proof=proof,
            environment=environment_manifest(), started_utc=utc_now(), contract=contract(),
            projected_seconds=source_forecast), root)
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            futures = [pool.submit(source_worker,root,a,i) for a,i in SOURCE_UNITS]
            for number, future in enumerate(as_completed(futures),1):
                future.result()
                if number % 12 == 0:
                    print(f'E49 source control {number}/36: cached scalars and full replay pass', flush=True)
        summary = source_summary(directory); write_json(directory/'summary.json',summary,root)
        assert inputs == hashes(science_paths(root)+[report]), 'source-control input drift'
        preflight(root,starting=False)
        record = dict(status='COMPLETE', elapsed_seconds=time.monotonic()-start,
            completed_utc=utc_now(), output_sha256=hashes(list(directory.iterdir())))
        write_json(directory/'COMPLETE.json',record,root)
        print(json.dumps(summary | dict(seconds=record['elapsed_seconds']),indent=2),flush=True)
    except Exception as error:
        failure(directory,error,root); raise


def source_artifacts(root, report):
    directory = root/'outputs'/p.CONTROL_ID
    names = {f'{a}_{i}.{ext}' for a,i in SOURCE_UNITS for ext in ('json','npz')} | {'INPUTS.json','summary.json','COMPLETE.json'}
    assert {x.name for x in directory.iterdir()} == names
    inputs, complete = read_json(directory/'INPUTS.json'), read_json(directory/'COMPLETE.json')
    assert inputs['input_sha256'] == hashes(science_paths(root)+[report])
    assert inputs['test_proof'] == test_proof(report,root)
    assert inputs['contract'] == json.loads(json.dumps(contract()))
    assert inputs['environment'] == environment_manifest()
    assert complete['status'] == 'COMPLETE'
    assert complete['output_sha256'] == hashes([directory/n for n in names if n != 'COMPLETE.json'])
    assert read_json(directory/'summary.json') == source_summary(directory)
    return [directory/n for n in sorted(names)]


def output_names():
    return tuple(f'block_{t}.{ext}' for t in p.TISSUES for ext in ('npz','json'))+(
        'summary.json','verification.json','input_hashes.sha256')


def contract():
    return p.contract() | dict(workers=4, reserve_bytes=RESERVE, allowance_bytes=ALLOWANCE,
        historical_inputs_hash_match=110, documented_post_audit_case_revision=LEGACY_CASE,
        detach_above_seconds=600, output_files=list(output_names()), output_hash_count=19,
        forecast='8*checked_block_seconds+2*hash_seconds+180',
        storage_forecast='8*uncompressed_block_bytes+calibration_bytes+benchmark_bytes+32MiB')


def freeze_path(root):
    return root/'tmp'/f'{p.RUN_ID}_freeze.json'


def timing_path(root):
    return root/'tmp'/f'{p.RUN_ID}_benchmark.json'


def benchmark_dir(root):
    return root/'tmp'/f'{p.RUN_ID}_benchmark'


def freeze(root, report):
    preflight(root); proof = test_proof(report,root)
    for target in (freeze_path(root), timing_path(root), benchmark_dir(root),
                   root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID):
        if target.exists():
            raise FileExistsError(target)
    inputs = hashes(science_paths(root)+[report]+source_artifacts(root,report))
    record = dict(frozen_utc=utc_now(), contract=contract(), input_sha256=inputs,
                  test_proof=proof, environment=environment_manifest(), main_futures_seen=0)
    write_json(freeze_path(root),record,root)
    print(f'D097 inputs frozen: {len(inputs)} files; no main future yet',flush=True)


def frozen(root):
    record = read_json(freeze_path(root)); report = Path(record['test_proof']['path'])
    assert record['contract'] == json.loads(json.dumps(contract())) and record['main_futures_seen'] == 0
    assert record['test_proof'] == test_proof(report,root)
    assert record['environment'] == environment_manifest()
    assert record['input_sha256'] == hashes(science_paths(root)+[report]+source_artifacts(root,report))
    return record


def checked_block(root, directory, index):
    preflight(root,starting=False)
    raw, meta = p.execute_block(index)
    loaded = save_pair(directory,f'block_{index}',raw,meta,root)
    assert p.checker().check_block(loaded,read_json(directory/f'block_{index}.json'),p.CONFIG,replay=False)
    return dict(index=index, lives=2, full_independent_replays=2, exact_alias_futures=6,
        max_abs=max(r['replay']['max_abs'] for r in meta['lives']),
        uncompressed_bytes=sum(x.nbytes for x in raw.values()))


def benchmark(root):
    preflight(root); frozen(root)
    directory = benchmark_dir(root); directory.mkdir()
    start = time.monotonic()
    try:
        record = checked_block(root,directory,p.DISPOSABLE)
        raw = load_npz(directory/f'block_{p.DISPOSABLE}.npz')
        assert p.checker().check_summary(p.summarize([raw]*8),[raw]*8,p.CONFIG)
        seconds = time.monotonic()-start
        hstart = time.monotonic(); frozen(root); hash_seconds = time.monotonic()-hstart
        calibration_bytes = sum(x.stat().st_size for x in (root/'outputs'/p.CONTROL_ID).iterdir())
        saved = list(directory.iterdir()); benchmark_bytes = sum(x.stat().st_size for x in saved)
        forecast = 8*seconds+2*hash_seconds+180
        size = 8*record['uncompressed_bytes']+calibration_bytes+benchmark_bytes+32*1024**2
        assert size <= ALLOWANCE, 'budget exceeded; no automatic downsizing'
        preflight(root)
        timing = dict(benchmark_utc=utc_now(), disposable=p.DISPOSABLE, main_pool=False,
            block=record, checked_block_seconds=seconds, hash_seconds=hash_seconds,
            projected_seconds=forecast, must_detach=forecast > 600,
            projected_total_bytes=size, calibration_bytes=calibration_bytes, benchmark_bytes=benchmark_bytes,
            artifact_sha256=hashes(saved), freeze_sha256=sha256_file(freeze_path(root)))
        write_json(timing_path(root),timing,root)
        print(json.dumps(timing,indent=2),flush=True)
    except Exception as error:
        failure(directory,error,root); raise


def timing_checked(root):
    timing = read_json(timing_path(root))
    assert timing['freeze_sha256'] == sha256_file(freeze_path(root))
    assert timing['disposable'] == p.DISPOSABLE and timing['main_pool'] is False
    assert timing['artifact_sha256'] == hashes(list(benchmark_dir(root).iterdir()))
    expected = 8*timing['checked_block_seconds']+2*timing['hash_seconds']+180
    assert np.isfinite(expected) and timing['projected_seconds'] == expected
    assert timing['must_detach'] == (expected > 600)
    assert 0 < timing['projected_total_bytes'] <= ALLOWANCE
    assert timing['projected_total_bytes'] == (8*timing['block']['uncompressed_bytes']+
        timing['calibration_bytes']+timing['benchmark_bytes']+32*1024**2)
    return timing


def main_inputs(root):
    record = frozen(root); timing_checked(root)
    return hashes([Path(x) for x in record['input_sha256']]+
        [freeze_path(root),timing_path(root),*list(benchmark_dir(root).iterdir())])


def prepare(root):
    preflight(root); inputs = main_inputs(root); timing = timing_checked(root)
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    if run.exists() or out.exists():
        raise FileExistsError('single-use run/output identity already reserved')
    run.mkdir(); out.mkdir()
    try:
        write_json(run/'MANIFEST.json',dict(contract=contract(),input_sha256=inputs,
            environment=environment_manifest(),timing=timing,prepared_utc=utc_now()),root)
        with (out/'input_hashes.sha256').open('x') as handle:
            handle.write(hash_text(inputs))
        atomic_json(run/'STATUS.json',dict(status='PREPARED',run_id=p.RUN_ID,
            projected_seconds=timing['projected_seconds'],must_detach=timing['must_detach']),root)
        print(f'D097 prepared: {len(inputs)} inputs, forecast {timing["projected_seconds"]:.1f}s',flush=True)
    except Exception as error:
        failure(run,error,root); raise


def prepared(root):
    manifest = read_json(root/'runs'/p.RUN_ID/'MANIFEST.json')
    assert manifest['contract'] == json.loads(json.dumps(contract()))
    assert manifest['input_sha256'] == main_inputs(root)
    assert manifest['environment'] == environment_manifest()
    assert manifest['timing'] == timing_checked(root)
    assert (root/'outputs'/p.RUN_ID/'input_hashes.sha256').read_text() == hash_text(manifest['input_sha256'])
    return manifest


def detached_guard(root, required):
    if required or (root/'runs'/p.RUN_ID/'LAUNCH.json').exists():
        launch = read_json(root/'runs'/p.RUN_ID/'LAUNCH.json')
        assert launch['pid'] == os.getpid() and os.getsid(0) == os.getpid()
        assert os.readlink('/proc/self/fd/0') == '/dev/null'
        assert all(os.readlink('/proc/self/fd/'+str(fd)) == launch['log'] for fd in (1,2))
        assert launch['manifest_sha256'] == sha256_file(root/'runs'/p.RUN_ID/'MANIFEST.json')


def detach(root):
    preflight(root); prepared(root)
    run = root/'runs'/p.RUN_ID
    if (run/'EXECUTION.lock').exists() or (run/'COMPLETE.json').exists() or (run/'FAILED.json').exists():
        raise FileExistsError('execution already attempted')
    (run/'LAUNCH.lock').mkdir()
    log = root/'logs'/f'{p.RUN_ID}.log'
    command = [sys.executable,'-m','laws_confirmation.l15_repair_speed_run',
               '--external-root',str(root),'--run']
    # The child writes its own launch identity before checking it; no polling/race.
    env = os.environ.copy(); env['L15_DETACHED_LAUNCH'] = str(log)
    with log.open('xb') as handle:
        child = subprocess.Popen(command,cwd=p.WS,env=env,stdin=subprocess.DEVNULL,
            stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(status='DETACHED',pid=child.pid,log=str(log),
        user_polls=True,automatic_polling=False)),flush=True)


def audit(root, complete=True, replay=False):
    preflight(root,starting=False); manifest = prepared(root)
    out, run = root/'outputs'/p.RUN_ID, root/'runs'/p.RUN_ID
    expected = set(output_names()) | ({'output_hashes.sha256'} if complete else set())
    assert {x.name for x in out.iterdir()} == expected
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    p.api(); blocks = []
    for index in p.TISSUES:
        raw, meta = load_npz(out/f'block_{index}.npz'), read_json(out/f'block_{index}.json')
        assert type(meta['index']) is int and meta['index'] == index
        assert p.checker().check_block(raw,meta,p.CONFIG,replay=replay)
        blocks.append(raw)
    summary = read_json(out/'summary.json')
    assert p.checker().check_summary(summary,blocks,p.CONFIG)
    verification = read_json(out/'verification.json')
    assert verification['checked_blocks'] == 8 and verification['independent_life_replays'] == 16
    assert verification['alias_futures'] == 48 and verification['source_jobs'] == 36
    assert [row['index'] for row in verification['rows']] == list(p.TISSUES)
    assert all(row['full_independent_replays']==2 and row['exact_alias_futures']==6
               and 0 <= row['max_abs'] <= 1e-10 for row in verification['rows'])
    if complete:
        status = read_json(run/'COMPLETE.json'); assert status['status'] == 'COMPLETE'
        assert read_json(run/'STATUS.json') == status
        actual = hashes([out/n for n in output_names()])
        assert status['output_sha256'] == actual
        assert (out/'output_hashes.sha256').read_text() == hash_text(actual)
        assert status['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
        assert status['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
        assert status['output_bytes'] == sum(x.stat().st_size for x in out.iterdir())
        assert status['output_bytes'] <= manifest['timing']['projected_total_bytes'] <= ALLOWANCE
    return dict(passes=True, checked_blocks=8, checked_lives=16, main_futures=192,
        aliases=48, full_dynamics_replayed_now=replay, input_hashes=len(manifest['input_sha256']),
        output_hashes=19 if complete else 0, primary=summary['primary'])


def run_experiment(root):
    preflight(root); manifest = prepared(root)
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    if 'L15_DETACHED_LAUNCH' in os.environ:
        write_json(run/'LAUNCH.json',dict(pid=os.getpid(),launched_utc=utc_now(),
            log=os.environ['L15_DETACHED_LAUNCH'], manifest_sha256=sha256_file(run/'MANIFEST.json')),root)
    detached_guard(root,manifest['timing']['must_detach'])
    (run/'EXECUTION.lock').mkdir(); start = time.monotonic()
    try:
        checks = {}
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending = {pool.submit(checked_block,root,out,t):t for t in p.TISSUES}
            for future in as_completed(pending):
                index = pending[future]; checks[index] = future.result()
                preflight(root,starting=False)
                atomic_json(run/'STATUS.json',dict(status='RUNNING',run_id=p.RUN_ID,
                    checked_blocks=len(checks),updated_utc=utc_now()),root)
                print(f'D097 tissue {index}: 2 full independent replays and 6 exact aliases pass',flush=True)
        blocks = [load_npz(out/f'block_{t}.npz') for t in p.TISSUES]
        write_json(out/'summary.json',p.summarize(blocks),root)
        write_json(out/'verification.json',dict(checked_blocks=8,independent_life_replays=16,
            alias_futures=48,source_jobs=36,rows=[checks[t] for t in p.TISSUES],checked_utc=utc_now()),root)
        result = audit(root,complete=False)
        current = hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as handle:
            handle.write(hash_text(current))
        size = sum(x.stat().st_size for x in out.iterdir())
        assert size <= manifest['timing']['projected_total_bytes'] <= ALLOWANCE
        preflight(root,starting=False)
        status = dict(status='COMPLETE',run_id=p.RUN_ID,completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start,output_bytes=size,output_sha256=current,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            saved_audit=result)
        write_json(run/'COMPLETE.json',status,root); atomic_json(run/'STATUS.json',status,root)
        print(json.dumps({k:status[k] for k in ('status','elapsed_seconds','output_bytes','saved_audit')},indent=2),flush=True)
    except Exception as error:
        failure(run,error,root)
        atomic_json(run/'STATUS.json',dict(status='FAILED',run_id=p.RUN_ID,error=str(error),automatic_retry=False),root)
        raise


def main(default_command=None):
    if sys.flags.optimize:
        raise RuntimeError('optimized Python disables audit assertions')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root',type=Path,required=True)
    parser.add_argument('--test-report',type=Path)
    parser.add_argument('--replay',action='store_true')
    group = parser.add_mutually_exclusive_group(required=default_command is None)
    for name in ('source-controls','freeze','benchmark','prepare','run','detach','audit'):
        group.add_argument('--'+name,action='store_true')
    args = parser.parse_args(); root = external_root(args.external_root)
    selected = [n for n in ('source_controls','freeze','benchmark','prepare','run','detach','audit') if getattr(args,n)]
    command = selected[0] if selected else default_command
    if (command in ('source_controls','freeze')) != (args.test_report is not None):
        parser.error('--test-report required only for source-controls or freeze')
    if args.replay and command != 'audit':
        parser.error('--replay is audit-only')
    if command == 'audit':
        print(json.dumps(audit(root,replay=args.replay),indent=2)); return
    if command in ('source_controls','freeze'):
        globals()[command](root,args.test_report)
    else:
        (run_experiment if command=='run' else globals()[command])(root)


if __name__ == '__main__':
    main()
