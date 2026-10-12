"""D142 single-use qualified/benchmarked repeated-futures executor; no auto successors."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import atomic_json, environment_manifest, sha256_file, utc_now, git_head
from . import repeated_system as system, repeated_audit as audit
from . import repeated_analysis as analysis, repeated_analysis_check as independent
from . import heldout_run as predecessor

ROOT = system.ROOT
RUN_ID = 'l20_extension1_repeated_futures_v1_attempt1'
WORKERS, ALLOWANCE, RESERVE = 6, 2*1024**3, 4*1024**3
DETACHED_ENV = 'L20_REPEATED_FUTURES_DETACHED'
SCIENCE = ('repeated-futures/PROTOCOL_V1.md', 'src/l20_extension1/repeated_system.py',
    'src/l20_extension1/repeated_audit.py', 'src/l20_extension1/repeated_analysis.py',
    'src/l20_extension1/repeated_analysis_check.py', 'src/l20_extension1/repeated_run.py',
    'tests/test_repeated.py', 'scripts/run_repeated.sh')


def paths(): return ROOT/'runs'/RUN_ID, ROOT/'outputs'/RUN_ID
def freeze_path(): return ROOT/'tmp'/f'{RUN_ID}_freeze.json'
def timing_path(): return ROOT/'tmp'/f'{RUN_ID}_benchmark.json'
def benchmark_dir(): return ROOT/'tmp'/f'{RUN_ID}_benchmark'
def log_path(stage='execute'): return ROOT/'logs'/f'{RUN_ID}_{stage}.log'


def preflight(starting=True):
    cpus = predecessor.preflight(False)
    if shutil.disk_usage(ROOT).free < RESERVE + (ALLOWANCE if starting else 0):
        raise RuntimeError('2 GiB allowance plus 4 GiB external reserve required')
    return cpus


def source_closure():
    run, out = ROOT/'runs'/system.SOURCE_RUN, ROOT/'outputs'/system.SOURCE_RUN
    assert sha256_file(run/'COMPLETE.json') == system.SOURCE_COMPLETE_SHA
    complete, manifest = io.read_json(run/'COMPLETE.json'), io.read_json(run/'MANIFEST.json')
    assert complete['status'] == 'COMPLETE' and io.read_json(run/'STATUS.json') == complete
    assert not (run/'FAILED.json').exists() and manifest['environment'] == environment_manifest()
    assert sha256_file(run/'MANIFEST.json') == complete['manifest_sha256']
    assert manifest['input_sha256'] == io.hashes([Path(x) for x in manifest['input_sha256']])
    assert complete['output_sha256'] == io.hashes([Path(x) for x in complete['output_sha256']])
    assert sha256_file(out/'output_hashes.sha256') == complete['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text() == io.hash_text(complete['output_sha256'])
    files = {Path(x) for x in (*manifest['input_sha256'], *complete['output_sha256'])}
    files.update((run/'COMPLETE.json', run/'MANIFEST.json', run/'STATUS.json', out/'output_hashes.sha256'))
    assert all(p in files for p in system.source_paths(system.DISPOSABLE))
    files.update(system.dev.WS/p for p in SCIENCE)
    files.add(system.dev.WS/'reviews/HELDOUT_LATE_LOSS_2026-09-17.md')
    return sorted(files)


def output_names():
    return [f'block_{i}.{ext}' for i in system.BLOCKS for ext in ('npz', 'json')] + [
        'NEW_FUTURES_STARTED.json', 'input_hashes.sha256', 'summary.json', 'verification.json']


def contract():
    return dict(run_id=RUN_ID, source_complete_sha256=system.SOURCE_COMPLETE_SHA,
        blocks=list(system.BLOCKS), cases=[list(c) for c in system.CASES], lives=4, futures=4,
        new_terminal_outcomes=1024, namespaces=[system.namespace(r) for r in range(4)],
        config=asdict(system.CONFIG), guide_sha256=system.old.GUIDE_SHA256,
        bootstrap_seed=14220260917, bootstrap_draws=10000, workers=6,
        allowance_bytes=ALLOWANCE, reserve_bytes=RESERVE, detach_above_seconds=600,
        benchmark_forecast='16*full_disposable_future_test_seconds+90',
        main_forecast='16*checked_block_seconds+2*hash_seconds+180',
        byte_budget='16*uncompressed_block_bytes+benchmark_bytes+64MiB',
        new_founders=0, refits=0, variance_clipping=False, output_files=output_names(),
        independent_worker_replay=True, automatic_polling=False, automatic_retry=False, automatic_successor=False)


def qualification(report):
    io.require_beneath(report, ROOT/'logs')
    tree = ET.parse(report).getroot(); cases = tree.findall('.//testcase')
    assert cases and not any(tree.findall('.//'+k) for k in ('failure', 'error', 'skipped'))
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    required = {'test_full_disposable_future', 'test_original_namespace_parity', 'test_noise_separation',
        'test_independent_replay', 'test_saved_no_dynamics', 'test_corruption', 'test_metadata_corruption',
        'test_condition_order', 'test_variance_formula', 'test_negative_between', 'test_zero_noise',
        'test_constant_outcomes', 'test_block_bootstrap', 'test_forecast_decomposition',
        'test_complete_summary', 'test_original_not_primary', 'test_new_forecasts_not_fitted',
        'test_namespace_guard', 'test_external_roundtrip', 'test_source_closure', 'test_resource_guards',
        'test_detached_guard', 'test_startup_handshake', 'test_no_automatic_successor',
        'test_main_barrier', 'test_failure_receipt', 'test_source_host_json_roundtrip'}
    ours = [c for c in cases if c.get('classname', '').endswith('test_repeated')]
    assert required <= {c.get('name', '').split('[', 1)[0] for c in ours}
    seconds = max(float(c.get('time')) for c in ours if c.get('name') == 'test_full_disposable_future')
    assert seconds > 0
    return dict(path=str(report), tests=len(cases), failures=0, skipped=0,
        full_future_seconds=seconds, benchmark_forecast=16*seconds+90)


def freeze(report):
    preflight()
    for path in (freeze_path(), timing_path(), benchmark_dir(), *paths(), log_path(), log_path('benchmark')):
        if path.exists(): raise FileExistsError(path)
    proof = qualification(report)
    value = dict(frozen_utc=utc_now(), contract=contract(), test_proof=proof,
        input_sha256=io.hashes(source_closure()+[report]), environment=environment_manifest(),
        new_main_futures_generated=0, git_head=git_head(system.old.WS))
    io.write_json(freeze_path(), value, ROOT)
    print(json.dumps(dict(status='FROZEN', inputs=len(value['input_sha256']), test_proof=proof)), flush=True)


def frozen():
    value = io.read_json(freeze_path())
    assert value['contract'] == contract() and value['environment'] == environment_manifest()
    report = Path(value['test_proof']['path'])
    assert value['test_proof'] == qualification(report)
    assert value['input_sha256'] == io.hashes(source_closure()+[report])
    assert value['new_main_futures_generated'] == 0
    return value


def load_block(directory, index):
    raw, meta = io.load_npz(directory/f'block_{index}.npz'), io.read_json(directory/f'block_{index}.json')
    assert set(meta) == {'index', 'config', 'lives'} and meta['index'] == index
    assert meta['config'] == asdict(system.CONFIG) and len(meta['lives']) == 4
    assert all(x.shape[:2] == (4, 4) for x in raw.values())
    return raw, meta


def check_block(directory, index):
    raw, meta = load_block(directory, index)
    founders, guides = system.load_source(index)
    for life in range(4):
        assert len(meta['lives'][life]) == 4
        for future in range(4):
            entry = meta['lives'][life][future]
            assert (entry['index'], entry['life'], entry['future']) == (index, life, future)
            current = audit.check({k: v[life, future] for k, v in raw.items()}, entry, founders[life], guides[life], False)
            saved = entry['replay']
            assert saved['full_dynamics_replayed'] is True and set(saved) == set(current)
            for key in current:
                if key != 'full_dynamics_replayed' and not key.endswith('_max_abs'):
                    assert current[key] == saved[key]
        # Full replay enforces each fresh namespace; also reject duplicate birth states.
        for a in range(4):
            for b in range(a+1, 4):
                assert not np.array_equal(raw['read_states'][life, a, 0, 0, 0], raw['read_states'][life, b, 0, 0, 0])
    return True


def barrier(run, out, expected):
    assert sha256_file(run/'MANIFEST.json') == expected
    receipt = io.read_json(out/'NEW_FUTURES_STARTED.json')
    assert receipt['manifest_sha256'] == expected and receipt['source_complete_sha256'] == system.SOURCE_COMPLETE_SHA
    assert receipt['namespaces'] == [system.namespace(r) for r in range(4)]
    return receipt


def worker(directory, index, run=None, manifest_sha=None):
    if index != system.DISPOSABLE:
        if run is None or manifest_sha is None:
            raise ValueError('frozen/prepared main-outcome barrier required')
        barrier(run, directory, manifest_sha)
    founders, guides = system.load_source(index)
    lives, entries = [], []
    for life in range(4):
        futures, records = [], []
        for future in range(4):
            raw, meta = system.simulate(index, life, future, founders[life], guides[life])
            meta['replay'] = audit.check(raw, meta, founders[life], guides[life], True)
            futures.append(raw); records.append(meta)
        lives.append({k: np.stack([r[k] for r in futures]) for k in futures[0]}); entries.append(records)
    block = {k: np.stack([r[k] for r in lives]) for k in lives[0]}
    io.write_npz(directory/f'block_{index}.npz', block, ROOT)
    io.write_json(directory/f'block_{index}.json', dict(index=index, config=asdict(system.CONFIG), lives=entries), ROOT)
    check_block(directory, index)
    return dict(index=index, uncompressed_bytes=sum(v.nbytes for v in block.values()),
        future_lives=16, generation_paths=192, terminal_paths=64, selector_decisions=256,
        full_dynamics_replayed=True, new_founders=0)


def existing_labels(disposable=False):
    directory = ROOT/('tmp' if disposable else 'outputs')/(system.SOURCE_RUN+'_benchmark' if disposable else system.SOURCE_RUN)
    rows = io.read_json(directory/('disposable_forecasts.json' if disposable else 'forecasts.json'))
    indexes = [system.DISPOSABLE] if disposable else list(system.BLOCKS)
    assert [(r['block'], r['life'], r['family'], r['writer']) for r in rows] == [
        (i, life, role, writer) for i in indexes for life in range(4) for role, writer in system.CASES]
    predictions = np.array([[r['predictions'][k] for k in ('starting_only', 'passive', 'challenge')] for r in rows]).reshape(len(indexes), 4, 4, 3)
    if not disposable:
        original = np.array(io.read_json(directory/'summary.json')['outcomes'])
        assert original.shape == (16, 4, 4)
    else:
        with np.load(directory/f'lineage_{system.DISPOSABLE}.npz', allow_pickle=False) as raw:
            values = raw['terminal_values'][:, [0, 1, 12, 13], -1]
        original = (values[..., 0]-values[..., 1])[None]
        predictions = np.repeat(predictions, 16, axis=0); original = np.repeat(original, 16, axis=0)
    return predictions, original


def detached_guard(required, stage='execute'):
    if required and os.environ.get(DETACHED_ENV) != '1':
        raise RuntimeError('forecast above ten minutes requires detached execution')
    if os.environ.get(DETACHED_ENV) == '1':
        assert os.getpid() == os.getsid(0)
        assert os.readlink('/proc/self/fd/0') == '/dev/null'
        assert Path(os.readlink('/proc/self/fd/1')) == log_path(stage)
        assert os.readlink('/proc/self/fd/2') == os.readlink('/proc/self/fd/1')


def signal_ready(stage):
    descriptor = os.environ.pop('D142_READY_FD', None)
    if descriptor is not None:
        fd = int(descriptor)
        try:
            os.write(fd, json.dumps(dict(stage=stage, pid=os.getpid(), status='STARTED')).encode())
        except BrokenPipeError:
            pass
        finally:
            os.close(fd)


def benchmark():
    preflight(); f = frozen()
    detached_guard(f['test_proof']['benchmark_forecast'] > 600, 'benchmark')
    directory = benchmark_dir(); directory.mkdir(); started = time.monotonic()
    try:
        signal_ready('benchmark')
        proof = worker(directory, system.DISPOSABLE)
        raw, meta = load_block(directory, system.DISPOSABLE)
        predictions, original = existing_labels(True)
        summary = analysis.summarize([raw]*16, [meta]*16, predictions, original)
        score_proof = independent.check(summary, [raw]*16, [meta]*16, predictions, original)
        io.write_json(directory/'score_fixture.json', dict(scientific_evidence=False, summary=summary, check=score_proof), ROOT)
        elapsed = time.monotonic()-started
        tick = time.monotonic(); frozen(); hashes_seconds = time.monotonic()-tick
        size = sum(p.stat().st_size for p in directory.iterdir())
        projected = 16*elapsed+2*hashes_seconds+180
        budget = 16*proof['uncompressed_bytes']+size+64*1024**2
        assert 0 < budget <= ALLOWANCE
        value = dict(status='COMPLETE', completed_utc=utc_now(), disposable=system.DISPOSABLE,
            proof=proof, score_check=score_proof, checked_block_seconds=elapsed, hash_seconds=hashes_seconds,
            projected_seconds=projected, must_detach=projected > 600,
            uncompressed_block_bytes=proof['uncompressed_bytes'], benchmark_bytes=size,
            projected_total_bytes=budget, artifact_sha256=io.hashes(list(directory.iterdir())),
            freeze_sha256=sha256_file(freeze_path()), scientific_evidence=False, new_main_futures_generated=0)
        io.write_json(timing_path(), value, ROOT)
        print(json.dumps(value, indent=2), flush=True)
    except Exception as error:
        io.failure(directory, error, ROOT); raise


def timing_checked():
    value = io.read_json(timing_path())
    assert value['status'] == 'COMPLETE' and value['new_main_futures_generated'] == 0
    assert value['disposable'] == system.DISPOSABLE and value['scientific_evidence'] is False
    assert value['freeze_sha256'] == sha256_file(freeze_path())
    assert {p.name for p in benchmark_dir().iterdir()} == {f'block_{system.DISPOSABLE}.npz', f'block_{system.DISPOSABLE}.json', 'score_fixture.json'}
    assert value['artifact_sha256'] == io.hashes(list(benchmark_dir().iterdir()))
    assert value['benchmark_bytes'] == sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert value['projected_seconds'] == 16*value['checked_block_seconds']+2*value['hash_seconds']+180
    assert value['must_detach'] == (value['projected_seconds'] > 600)
    assert value['projected_total_bytes'] == 16*value['uncompressed_block_bytes']+value['benchmark_bytes']+64*1024**2 <= ALLOWANCE
    return value


def benchmark_audit():
    frozen(); value = timing_checked(); check_block(benchmark_dir(), system.DISPOSABLE)
    raw, meta = load_block(benchmark_dir(), system.DISPOSABLE)
    fixture = io.read_json(benchmark_dir()/'score_fixture.json')
    assert fixture['scientific_evidence'] is False
    predictions, original = existing_labels(True)
    checked = independent.check(fixture['summary'], [raw]*16, [meta]*16, predictions, original)
    assert checked == fixture['check'] == value['score_check']
    return dict(passes=True, disposable_future_lives=16, generation_paths=192, terminal_paths=64,
        new_dynamics=0, indexed_artifacts=3)


def main_inputs():
    f = frozen(); timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']] + [freeze_path(), timing_path(), *benchmark_dir().iterdir()])


def prepare():
    preflight(); inputs = main_inputs(); timing = timing_checked(); benchmark_audit()
    run, out = paths()
    if run.exists() or out.exists(): raise FileExistsError('single-use run already reserved')
    run.mkdir(); out.mkdir()
    manifest = dict(prepared_utc=utc_now(), contract=contract(), input_sha256=inputs, timing=timing,
        environment=environment_manifest(), affinity=sorted(os.sched_getaffinity(0)),
        free_bytes=shutil.disk_usage(ROOT).free, git_head=git_head(system.old.WS))
    io.write_json(run/'MANIFEST.json', manifest, ROOT)
    with (out/'input_hashes.sha256').open('x') as stream: stream.write(io.hash_text(inputs))
    atomic_json(run/'STATUS.json', dict(status='PREPARED', run_id=RUN_ID), ROOT)
    print(json.dumps(dict(status='PREPARED', inputs=len(inputs), forecast_seconds=timing['projected_seconds'],
        must_detach=timing['must_detach'], projected_bytes=timing['projected_total_bytes'])), flush=True)


def prepared():
    run, out = paths(); value = io.read_json(run/'MANIFEST.json')
    assert value['contract'] == contract() and value['environment'] == environment_manifest()
    assert value['input_sha256'] == main_inputs() and value['timing'] == timing_checked()
    assert (out/'input_hashes.sha256').read_text() == io.hash_text(value['input_sha256'])
    return value


def saved_audit(complete=True):
    preflight(False); manifest = prepared(); run, out = paths()
    assert {p.name for p in out.iterdir()} == set(output_names()) | ({'output_hashes.sha256'} if complete else set())
    start = barrier(run, out, sha256_file(run/'MANIFEST.json'))
    assert start['started_utc'] >= manifest['prepared_utc'] >= frozen()['frozen_utc']
    blocks, records = [], []
    for index in system.BLOCKS:
        check_block(out, index)
        raw, meta = load_block(out, index); blocks.append(raw); records.append(meta)
    predictions, original = existing_labels()
    check = independent.check(io.read_json(out/'summary.json'), blocks, records, predictions, original)
    verification = io.read_json(out/'verification.json')
    assert verification['statistics'] == check and len(verification['blocks']) == 16
    for index, block, proof in zip(system.BLOCKS, blocks, verification['blocks']):
        assert proof == dict(index=index, uncompressed_bytes=sum(v.nbytes for v in block.values()),
            future_lives=16, generation_paths=192, terminal_paths=64, selector_decisions=256,
            full_dynamics_replayed=True, new_founders=0)
    if complete:
        receipt = io.read_json(run/'COMPLETE.json')
        assert receipt['status'] == 'COMPLETE' and io.read_json(run/'STATUS.json') == receipt
        assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
        assert receipt['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
        assert receipt['output_sha256'] == io.hashes([out/n for n in output_names()])
        assert (out/'output_hashes.sha256').read_text() == io.hash_text(receipt['output_sha256'])
        assert receipt['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
        assert receipt['summary_sha256'] == sha256_file(out/'summary.json')
        assert receipt['source_complete_sha256'] == system.SOURCE_COMPLETE_SHA
    return dict(passes=True, input_hashes=len(manifest['input_sha256']), indexed_outputs=len(output_names()),
        cases=256, independent_blocks=16, futures=1024, generation_paths=3072, terminal_paths=1024, new_dynamics=0)


def execute():
    run, out = paths()
    if any((run/name).exists() for name in ('COMPLETE.json', 'FAILED.json', 'EXECUTION.lock')):
        raise FileExistsError('single-use execution already started or closed')
    try:
        preflight(); m = prepared(); detached_guard(m['timing']['must_detach'])
        assert io.read_json(run/'STATUS.json')['status'] == 'PREPARED'
        assert {p.name for p in out.iterdir()} == {'input_hashes.sha256'}
        (run/'EXECUTION.lock').mkdir(); began = time.monotonic()
        with (run/'RUN.pid').open('x') as stream: stream.write(str(os.getpid())+'\n')
        manifest_sha = sha256_file(run/'MANIFEST.json')
        io.write_json(out/'NEW_FUTURES_STARTED.json', dict(started_utc=utc_now(), manifest_sha256=manifest_sha,
            source_complete_sha256=system.SOURCE_COMPLETE_SHA, namespaces=[system.namespace(r) for r in range(4)]), ROOT)
        atomic_json(run/'STATUS.json', dict(status='FRESH_FUTURES', run_id=RUN_ID, started_utc=utc_now()), ROOT)
        signal_ready('execute')
        proofs = {}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs = [pool.submit(worker, out, i, run, manifest_sha) for i in system.BLOCKS]
            try:
                for job in as_completed(jobs):
                    proof = job.result(); proofs[proof['index']] = proof
                    status = dict(status='FRESH_FUTURES', run_id=RUN_ID, completed_blocks=sorted(proofs),
                        total_blocks=16, updated_utc=utc_now())
                    atomic_json(run/'STATUS.json', status, ROOT); print(json.dumps(status), flush=True)
            except Exception:
                for job in jobs: job.cancel()
                raise
        blocks, records = zip(*(load_block(out, i) for i in system.BLOCKS))
        predictions, original = existing_labels()
        summary = analysis.summarize(blocks, records, predictions, original)
        checked = independent.check(summary, blocks, records, predictions, original)
        io.write_json(out/'summary.json', summary, ROOT)
        io.write_json(out/'verification.json', dict(blocks=[proofs[i] for i in system.BLOCKS], statistics=checked), ROOT)
        del blocks, records
        saved_audit(False); assert main_inputs() == m['input_sha256']; preflight(False)
        outputs = io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream: stream.write(io.hash_text(outputs))
        size = sum(p.stat().st_size for p in out.iterdir()); assert size <= ALLOWANCE
        receipt = dict(status='COMPLETE', run_id=RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-began, output_bytes=size, manifest_sha256=manifest_sha,
            output_sha256=outputs, hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            summary_sha256=sha256_file(out/'summary.json'), source_complete_sha256=system.SOURCE_COMPLETE_SHA,
            automatic_retry=False, automatic_successor=False)
        io.write_json(run/'COMPLETE.json', receipt, ROOT); atomic_json(run/'STATUS.json', receipt, ROOT)
        print(json.dumps({k: v for k, v in receipt.items() if k != 'output_sha256'}), flush=True)
    except Exception as error:
        if run.is_dir() and not (run/'FAILED.json').exists():
            io.failure(run, error, ROOT)
            atomic_json(run/'STATUS.json', dict(status='FAILED', run_id=RUN_ID, failed_utc=utc_now(), error=str(error)), ROOT)
        raise


def detach(stage='execute'):
    preflight()
    if stage == 'execute':
        prepared(); run, out = paths()
        assert io.read_json(run/'STATUS.json')['status'] == 'PREPARED'
        assert not any((run/n).exists() for n in ('EXECUTION.lock', 'FAILED.json', 'COMPLETE.json'))
    elif stage == 'benchmark':
        frozen(); assert not benchmark_dir().exists() and not timing_path().exists()
        run = ROOT/'tmp'
    else:
        raise ValueError('only declared benchmark or execution stage may detach')
    lock = ROOT/'tmp'/f'{RUN_ID}_{stage}_launch.lock'; lock.mkdir()
    env = os.environ.copy(); env[DETACHED_ENV] = '1'
    ready_read, ready_write = os.pipe(); env['D142_READY_FD'] = str(ready_write)
    command = [sys.executable, '-m', 'l20_extension1.repeated_run', '--'+stage]
    try:
        with log_path(stage).open('xb') as stream:
            child = subprocess.Popen(command, cwd=system.old.WS, env=env, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(ready_write,))
    finally:
        os.close(ready_write)
    readable, _, _ = select.select([ready_read], [], [], 55)
    acknowledgement = os.read(ready_read, 4096) if readable else b''; os.close(ready_read)
    ack = json.loads(acknowledgement) if acknowledgement else None
    if ack is not None: assert ack == dict(stage=stage, pid=child.pid, status='STARTED')
    receipt = dict(status='DETACHED', stage=stage, pid=child.pid, launched_utc=utc_now(), command=command,
        startup_acknowledged=ack is not None, log=str(log_path(stage)),
        progress=str(run/'STATUS.json') if stage == 'execute' else str(timing_path()),
        complete=str(run/'COMPLETE.json') if stage == 'execute' else str(timing_path()),
        failure=str(run/'FAILED.json') if stage == 'execute' else str(benchmark_dir()/'FAILED.json'),
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    io.write_json(lock/'LAUNCH.json', receipt, ROOT)
    if stage == 'execute': io.write_json(run/'LAUNCH.json', receipt, ROOT)
    print(json.dumps(receipt, indent=2), flush=True)


def main():
    if sys.flags.optimize: raise RuntimeError('audit assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-report', type=Path)
    choice = parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze', 'benchmark', 'benchmark-audit', 'prepare', 'execute', 'audit', 'detach', 'detach-benchmark'):
        choice.add_argument('--'+name, action='store_true')
    args = parser.parse_args()
    if args.freeze != (args.test_report is not None): parser.error('--test-report required only with --freeze')
    if args.freeze: freeze(args.test_report)
    elif args.benchmark: benchmark()
    elif args.benchmark_audit: print(json.dumps(benchmark_audit(), indent=2))
    elif args.prepare: prepare()
    elif args.execute: execute()
    elif args.audit: print(json.dumps(saved_audit(), indent=2))
    else: detach('benchmark' if args.detach_benchmark else 'execute')


if __name__ == '__main__': main()
