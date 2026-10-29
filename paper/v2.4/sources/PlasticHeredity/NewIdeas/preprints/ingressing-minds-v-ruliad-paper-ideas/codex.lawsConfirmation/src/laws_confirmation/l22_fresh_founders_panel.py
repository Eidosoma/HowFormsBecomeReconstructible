"""D191 fixed fresh-founder panel; unchanged science, one detached CPU."""

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import resource
import select
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

import numpy as np

from . import l22_fresh_founders as benchmark
from . import l22_fresh_founders_panel_block as block
from . import l22_direction_allocation_panel as numerical_panel
from .io import canonical_digest, sha256_file, utc_now

model, WS, BASE = benchmark.model, benchmark.WS, benchmark.BASE
CONFIG, READOUT, BLOCKS, FUTURES = benchmark.CONFIG, benchmark.READOUT, benchmark.BLOCKS, benchmark.FUTURES
BENCH_ROOT = benchmark.ROOT
BENCH_DATA, BENCH_RECEIPTS = BENCH_ROOT/'outputs'/benchmark.RUN, BENCH_ROOT/'runs'/benchmark.RUN
ROOT = BASE/'L22-fresh-founders-panel-v1'
RUN = 'l22_fresh_founders_v1_panel_attempt1'
ENV, READY = 'D191_PANEL_STAGE', 'D191_PANEL_READY_FD'
CAP, RESERVE, HEADROOM = 3*1024**3, 4*1024**3, 64*1024**2
BLOCK_BOUND, EXTRA_BOUND = 384*1024**2, 16*1024**2
BOUND = 4*BLOCK_BOUND+EXTRA_BOUND
IDENTITIES = {
    BENCH_ROOT/'FREEZE.json': 'd673ba9533f9ffa87f82cb395032afc93f8556d5305db45989fdcae0e2f89ba8',
    BENCH_RECEIPTS/'MANIFEST.json': '1e48ef74143cb9c38a3b4bb2d78947c216d09c7a5ca1d7506b304b3c2a2d8aa3',
    BENCH_RECEIPTS/'COMPLETE.json': '04b80bf276ddb38eb2f23abfedd249fd8b968f4bf48bb14a0c7b130171d485bb',
    BENCH_DATA/'SUMMARY.json': 'e76d4130ea1fb8607723055aea296c5318c668d1a9e12d0f049d1892e7d430a9',
}
SCIENCE = ('L22-active-form/FRESH_FOUNDERS_PANEL_V1.md',
    'src/laws_confirmation/l22_fresh_founders_panel.py',
    'src/laws_confirmation/l22_fresh_founders_panel_block.py',
    'src/laws_confirmation/l22_fresh_founders_panel_capture.py',
    'scripts/check_l22_fresh_founders_panel.py', 'tests/test_l22_fresh_founders_panel.py',
    'scripts/report_l22_fresh_founders_benchmark.py',
    'L22-active-form/FRESH_FOUNDERS_BENCHMARK_RESULTS.md', 'L22-active-form/FRESH_FOUNDERS_BENCHMARK_TABLES.md',
    'scripts/qualify_l22_fresh_founders_panel.py')
TESTS = (*benchmark.TESTS, SCIENCE[5])
read, arrays, verify, checker = benchmark.read, benchmark.arrays, benchmark.verify, block.checker
REQUIRED_TESTS = benchmark.REQUIRED_TESTS | {'test_d191_panel_complete_block', 'test_d191_panel_exact_bridge',
    'test_d191_panel_workflow_identity', 'test_d191_panel_scope', 'test_d191_panel_root_restored',
    'test_d191_panel_aggregate', 'test_d191_panel_summary_tamper', 'test_d191_panel_saved_tamper',
    'test_d191_panel_execute_order', 'test_d191_panel_saved_panel', 'test_d191_panel_launch_startup_only',
    'test_d191_panel_resources', 'test_d191_panel_freeze_changed', 'test_d191_panel_failure_retained',
    'test_d191_panel_write_once', 'test_d191_panel_budget_and_closure', 'test_d191_benchmark_report_matches',
    'test_d191_qualification_launch', 'test_d191_qualification_failure'}


def target(path):
    path = Path(path)
    if ROOT.is_symlink() or ROOT.resolve() not in path.resolve().parents or path.is_symlink():
        raise ValueError('panel evidence must stay in its dedicated external root')
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    data = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target(path).open('x') as stream: stream.write(data)


def resources(allowance=0):
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve().is_relative_to(Path('/mnt/bioIce1').resolve())
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(n) == '1', n
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    for n in ('outputs', 'runs', 'logs'):
        branch = ROOT/n
        assert not branch.is_symlink() and not any(p.is_symlink() for p in branch.rglob('*'))
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE+allowance+HEADROOM
    return dict(bytes=size, cap_bytes=CAP, reserved_output_bytes=allowance, headroom_bytes=HEADROOM,
        free_reserve_bytes=RESERVE, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS, 0), workers=1, numerical_threads=1)


@contextmanager
def output_root():
    original = block.ROOT
    if original != BASE/'L22-fresh-founders-panel-v1': raise RuntimeError('nested or changed block root')
    block.ROOT = ROOT
    try: yield
    finally: block.ROOT = original


def run_block(directory, index, cfg=CONFIG, rcfg=READOUT):
    if type(index) is not int or index not in BLOCKS: raise ValueError('all four registered main founders only')
    block.admit(index, cfg, rcfg)
    with output_root(): return block.run_block(directory, index, cfg, rcfg)


def saved_block(directory, index, cfg=CONFIG, rcfg=READOUT):
    if type(index) is not int or index not in BLOCKS: raise ValueError('all four registered main founders only')
    with output_root(): return block.saved_check(directory, index, cfg, rcfg)


def omissions(value):
    for group in ('arms', 'contrasts'):
        for row in value[group].values():
            row['leave_one_block_out'] = [{k: float(np.mean([row['by_block'][j][k] for j in range(4) if j != i]))
                for k in row['mean']} for i in range(4)]
    return value


def factorial(blocks, parents, draws):
    if set(blocks) != set(BLOCKS): raise ValueError('four new blocks required')
    # Only numerical argument slots are relabelled. No old packets/outcomes are read.
    value = numerical_panel.aggregate({slot: blocks[index] for slot, index in zip(numerical_panel.BLOCKS, BLOCKS)}, parents, draws)
    value.update(schema='d191_four_fresh_founder_factorial_v1', blocks=list(BLOCKS), new_founders=4)
    omissions(value); checker().factorial(blocks, value, parents, draws)
    return value


def upstream(blocks, parents):
    if set(blocks) != set(BLOCKS): raise ValueError('four upstream blocks required')
    fields = model.METRICS

    def means(rows, keys):
        a = np.array([[[r[k] for k in keys] for r in rows[i]] for i in BLOCKS])
        grouped, by_block = a.reshape(4, 4, parents, len(keys)).mean(axis=2), a.mean(axis=1)
        dictionary = lambda v: dict(zip(keys, v.tolist()))
        return dict(mean=dictionary(by_block.mean(axis=0)), by_block=[dictionary(v) for v in by_block],
            by_message=[dictionary(v) for v in grouped.mean(axis=0)],
            by_block_message=[[dictionary(v) for v in b] for b in grouped])

    def count(xs):
        a = np.array(xs)
        return dict(n=int(a.size), improved=int(np.sum(a > model.TOL)), worsened=int(np.sum(a < -model.TOL)),
            tied=int(np.sum(np.abs(a) <= model.TOL)), net=float(a.mean()),
            positive=float(np.maximum(a, 0).mean()), negative=float(np.minimum(a, 0).mean()))

    arms = {n: means({i: blocks[i]['records'][n] for i in BLOCKS}, fields) for n in sorted(blocks[BLOCKS[0]]['records'])}
    contrasts = {}
    for name, terms in blocks[BLOCKS[0]]['contrasts'].items():
        left, right, keys = terms['left'], terms['right'], tuple(terms['mean'])
        rows = {i: [{k: a[k]-b[k] for k in keys} for a, b in zip(blocks[i]['records'][left], blocks[i]['records'][right])]
                for i in BLOCKS}
        delta = np.array([[r['accuracy'] for r in rows[i]] for i in BLOCKS]).reshape(4, 4, parents)
        contrasts[name] = dict(left=left, right=right, **means(rows, keys),
            transitions=dict(pooled=count(delta), by_block=[count(b) for b in delta],
                by_message=[count(delta[:, m]) for m in range(4)],
                by_block_message=[[count(v) for v in b] for b in delta]))
    value = omissions(dict(arms=arms, contrasts=contrasts, records=16*parents, named_reads=372,
        repair_paths=272, comparisons=44, pooling_unit='equal_block', stream='native_upstream_not_factorial_futures'))
    checker().upstream(blocks, value, parents)
    return value


def aggregate(blocks, parents=4, draws=4):
    if set(blocks) != set(BLOCKS): raise ValueError('retain every registered founder, no disposable or replacement')
    if type(parents) is not int or type(draws) is not int or min(parents, draws) < 1:
        raise ValueError('positive integer parent/draw counts required')
    for i, data in blocks.items():
        if set(data) != {'futures', 'upstream'}: raise ValueError('factorial and complete upstream data required')
        block.statistics(data['futures'], i)
    value = dict(schema='d191_fresh_founder_panel_v1', blocks=list(BLOCKS), futures=list(FUTURES),
        records=16*parents, records_per_block=4*parents, reader_draws_per_future=draws,
        new_draws_per_record=2*draws, factorial_named_reads=216, upstream_named_reads=372,
        total_named_reads=588, repair_paths=272, contrasts=66, upstream_comparisons=44,
        new_founders=4, old_outcomes_pooled=False, benchmark_excluded=True,
        pooling_unit='equal_block_equal_future', fitted_models=0, confirmatory=False, serial_renewal=False,
        uncertainty_interval=None,
        by_future={f: factorial({i: blocks[i]['futures'][f] for i in BLOCKS}, parents, draws) for f in FUTURES},
        new_only=factorial({i: block.pool(blocks[i]['futures']) for i in BLOCKS}, parents, 2*draws),
        upstream=upstream({i: blocks[i]['upstream'] for i in BLOCKS}, parents))
    checker().check(blocks, value, parents, draws)
    return value


def load_blocks(directory):
    return {i: dict(futures=block.load_futures(directory/f'tissue_{i}'),
        upstream={n: read(directory/f'tissue_{i}'/'capture'/(n+'.json')) for n in ('records', 'contrasts')}) for i in BLOCKS}


def benchmark_evidence():
    verify({str(p): h for p, h in IDENTITIES.items()})
    f, done, manifest = read(BENCH_ROOT/'FREEZE.json'), read(BENCH_RECEIPTS/'COMPLETE.json'), read(BENCH_RECEIPTS/'MANIFEST.json')
    assert done['status'] == 'COMPLETE' and not (BENCH_RECEIPTS/'FAILED.json').exists()
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == sha256_file(BENCH_ROOT/'FREEZE.json')
    assert done['manifest_sha256'] == sha256_file(BENCH_RECEIPTS/'MANIFEST.json')
    assert done['summary_sha256'] == sha256_file(BENCH_DATA/'SUMMARY.json')
    assert len(f['inputs']) == 3765 and len(done['output_sha256']) == 411
    assert set(done['output_sha256']) == {str(p) for p in BENCH_DATA.rglob('*') if p.is_file()}
    assert {p.name for p in BENCH_RECEIPTS.iterdir()} == {'COMPLETE.json', 'MANIFEST.json'}
    assert done['full_replay'] == read(BENCH_DATA/'CHECK.json')
    assert f['planned_blocks'] == list(BLOCKS) and f['futures'] == list(FUTURES)
    assert canonical_digest(f['config']) == canonical_digest(asdict(CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(READOUT))
    inputs = dict(f['inputs']) | done['output_sha256'] | {str(p): h for p, h in IDENTITIES.items()}
    verify(inputs)
    assert benchmark.saved_check(BENCH_DATA, benchmark.DISPOSABLE) == done['verification']
    assert done['main_cohort_started'] is False and done['automatic_successor'] is False
    elapsed = done['seconds']; assert abs(elapsed-506.5322414881084) < 1e-9
    paths = [BENCH_ROOT/'logs'/(benchmark.RUN+s) for s in ('.log', '_launch.json')]
    inputs.update({str(p): sha256_file(p) for p in paths})
    launch = read(paths[1]); assert launch['status'] == 'DETACHED_STARTED' and launch['main_cohort_started'] is False
    final_log = json.loads(paths[0].read_text().splitlines()[-1])
    assert all(done[k] == v for k, v in final_log.items())
    return inputs, dict(measured_complete_block_seconds=elapsed, serial_reference_seconds=4*elapsed,
        allowance_seconds=8*elapsed+180, measured_panel_runtime=False)


def imported_paths():
    checker(); numerical_panel.checker().block_checker()
    return benchmark.imported_paths() | {WS/'scripts/check_l22_fresh_founders_panel.py',
        WS/'scripts/check_l22_direction_allocation_panel.py'}


def freeze_path(): return ROOT/'FREEZE.json'


def test_receipt(path):
    assert ROOT.resolve() in path.resolve().parents
    suites = list(ET.parse(path).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    assert cases and len(cases) == sum(int(s.get('tests', 0)) for s in suites)
    assert not any(list(c.iter(k)) for c in cases for k in ('failure', 'error', 'skipped'))
    assert REQUIRED_TESTS <= {c.get('name').split('[')[0] for c in cases}
    return dict(path=str(path), sha256=sha256_file(path), cases=len(cases), seconds=sum(float(s.get('time', 0)) for s in suites))


def prepare(xml):
    resources(BOUND)
    assert not freeze_path().exists() and not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    assert xml.stat().st_mtime_ns >= max((WS/n).stat().st_mtime_ns for n in (*SCIENCE, *TESTS))
    tests = test_receipt(xml); inputs, budget = benchmark_evidence(); modules = imported_paths()
    assert set(read(BENCH_ROOT/'FREEZE.json')['imported_repository_modules']) <= {str(p) for p in modules}
    inputs.update({str(p): sha256_file(p) for p in modules | {WS/n for n in (*SCIENCE, *TESTS)} | {xml}})
    value = dict(schema='d191_fresh_founder_panel_freeze_v1', frozen_utc=utc_now(), inputs=inputs, tests=tests,
        imported_repository_modules=sorted(str(p) for p in modules), config=asdict(CONFIG), readout_config=asdict(READOUT),
        blocks=list(BLOCKS), futures=list(FUTURES), plan=list(model.plan()), contrasts=model.contrasts(),
        repair_plan={k: asdict(v) for k, v in block.capture.model.plan().items()}, qualification=block.QUALIFICATION,
        budget=budget, storage_upper_bound_bytes=BOUND, resources=resources(BOUND), benchmark_excluded=True,
        new_confirmation_founders=0, new_founders=4, source_regenerated=True, automatic_polling=False, automatic_retry=False,
        automatic_successor=False, python=sys.version, numpy=np.__version__)
    write(freeze_path(), value)
    return dict(freeze_sha256=sha256_file(freeze_path()), inputs=len(inputs), tests=tests,
        imported_repository_modules=len(modules), budget=budget, resources=value['resources'])


def frozen():
    f = read(freeze_path()); verify(f['inputs'])
    assert f['schema'] == 'd191_fresh_founder_panel_freeze_v1'
    assert canonical_digest(f['config']) == canonical_digest(asdict(CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(READOUT))
    assert f['blocks'] == list(BLOCKS) and f['futures'] == list(FUTURES) and f['plan'] == list(model.plan())
    assert f['contrasts'] == model.contrasts()
    assert f['repair_plan'] == {k: asdict(v) for k, v in block.capture.model.plan().items()}
    assert f['qualification'] == block.QUALIFICATION
    assert f['storage_upper_bound_bytes'] == BOUND and f['resources']['cap_bytes'] == CAP
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert f['new_confirmation_founders'] == 0 and f['source_regenerated'] is True and f['new_founders'] == 4 and f['benchmark_excluded'] is True
    assert all(f[k] is False for k in ('automatic_polling', 'automatic_retry', 'automatic_successor'))
    seconds = read(BENCH_RECEIPTS/'COMPLETE.json')['seconds']
    assert f['budget'] == dict(measured_complete_block_seconds=seconds, serial_reference_seconds=4*seconds,
        allowance_seconds=8*seconds+180, measured_panel_runtime=False)
    assert {str(p) for p in imported_paths()} == set(f['imported_repository_modules'])
    assert set(f['imported_repository_modules']) <= set(f['inputs']) and benchmark.ROOT == BENCH_ROOT
    return f


def saved_panel(directory, receipts, cfg=CONFIG, rcfg=READOUT):
    assert {p.name for p in directory.iterdir()} == {'SUMMARY.json'} | {f'tissue_{i}' for i in BLOCKS}
    unique, hashes = 0, {}
    for i in BLOCKS:
        block = directory/f'tissue_{i}'; record = read(receipts/f'BLOCK_{i}.json')
        assert record['status'] == 'COMPLETE' and record['tissue'] == i
        assert record['freeze_sha256'] == sha256_file(freeze_path())
        assert record['full_replay'] == read(block/'CHECK.json')
        verify(record['output_sha256'])
        assert set(record['output_sha256']) == {str(p) for p in block.rglob('*') if p.is_file()}
        checked = saved_block(block, i, cfg, rcfg); assert checked == record['verification']
        unique += checked['factorial_unique_reads']; hashes.update(record['output_sha256'])
    result = aggregate(load_blocks(directory), cfg.replicates, rcfg.draws)
    assert result == read(directory/'SUMMARY.json')
    return dict(passes=True, blocks=4, records=16*cfg.replicates, new_future_sets=2, new_founders=4,
        factorial_named_reads=216, upstream_named_reads=372, total_named_reads=588, repair_paths=272,
        factorial_unique_reads=unique, contrasts=66, upstream_comparisons=44, new_dynamics=0,
        saved_packets_and_scalar_scores_recomputed=True, output_files=len(hashes)+1)


def execute_blocks(directory, receipts, cfg=CONFIG, rcfg=READOUT):
    assert not directory.exists(); directory.mkdir(parents=True)
    for position, i in enumerate(BLOCKS):
        resources((4-position)*BLOCK_BOUND+EXTRA_BOUND)
        block = directory/f'tissue_{i}'; proof = run_block(block, i, cfg, rcfg)
        saved = saved_block(block, i, cfg, rcfg)
        write(receipts/f'BLOCK_{i}.json', dict(status='COMPLETE', tissue=i, completed_utc=utc_now(),
            freeze_sha256=sha256_file(freeze_path()), full_replay=proof, verification=saved,
            output_sha256={str(p): sha256_file(p) for p in sorted(block.rglob('*')) if p.is_file()}))
        print(json.dumps(dict(stage='block_complete', tissue=i, checked_blocks=position+1, total_blocks=4)), flush=True)
    summary = aggregate(load_blocks(directory), cfg.replicates, rcfg.draws)
    write(directory/'SUMMARY.json', summary)
    return saved_panel(directory, receipts, cfg, rcfg)


def execute():
    resources(BOUND); f = frozen()
    assert os.environ.get(ENV) == 'panel' and os.getsid(0) == os.getpid()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists(); rd.mkdir(parents=True); tick = time.monotonic()
    try:
        write(rd/'MANIFEST.json', dict(started_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            budget=f['budget'], resources=resources(BOUND), blocks=list(BLOCKS), automatic_successor=False))
        fd = os.environ.pop(READY, None)
        if fd is not None: os.write(int(fd), b'READY\n'); os.close(int(fd))
        checked = execute_blocks(od, rd); frozen(); resources()
        hashes = {str(p): sha256_file(p) for p in sorted(od.rglob('*')) if p.is_file()}
        raw_bytes = sum(sum(v.nbytes for v in arrays(p).values()) for p in od.rglob('*.npz'))
        assert raw_bytes < BOUND
        value = dict(status='COMPLETE', completed_utc=utc_now(), seconds=time.monotonic()-tick,
            freeze_sha256=sha256_file(freeze_path()), manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            output_sha256=hashes, block_receipts_sha256={str(rd/f'BLOCK_{i}.json'): sha256_file(rd/f'BLOCK_{i}.json') for i in BLOCKS},
            summary_sha256=sha256_file(od/'SUMMARY.json'), verification=checked, resources=resources(),
            uncompressed_array_bytes=raw_bytes, process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            benchmark_excluded=True, new_confirmation_founders=0, new_founders=4,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write(rd/'COMPLETE.json', value)
        return {k: v for k, v in value.items() if k not in ('output_sha256', 'block_receipts_sha256')}
    except Exception as exc:
        write(rd/'FAILED.json', dict(failed_utc=utc_now(), error=str(exc), traceback=traceback.format_exc(),
            automatic_retry=False, automatic_successor=False))
        raise


def launch():
    resources(BOUND); f = frozen()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log, receipt = ROOT/'logs'/(RUN+'.log'), ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    rd, wr = os.pipe(); env = dict(os.environ, **{ENV: 'panel', READY: str(wr)})
    try:
        with target(log).open('xb') as stream:
            process = subprocess.Popen([sys.executable, '-u', '-m', 'laws_confirmation.l22_fresh_founders_panel', '--run'],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, cwd=WS, env=env,
                start_new_session=True, pass_fds=(wr,))
    finally: os.close(wr)
    ready = select.select([rd], [], [], 30)[0]
    message = os.read(rd, 64) if ready else b''; os.close(rd)
    value = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=process.pid, acknowledged_utc=utc_now(), log=str(log), affinity=[6], nice=10, workers=1, numerical_threads=1,
        budget=f['budget'], automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write(receipt, value); return value


def audit():
    resources(); frozen()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN; done = read(rd/'COMPLETE.json')
    assert done['status'] == 'COMPLETE' and not (rd/'FAILED.json').exists()
    assert done['freeze_sha256'] == read(rd/'MANIFEST.json')['freeze_sha256'] == sha256_file(freeze_path())
    assert done['manifest_sha256'] == sha256_file(rd/'MANIFEST.json')
    assert done['summary_sha256'] == sha256_file(od/'SUMMARY.json')
    verify(done['output_sha256']); verify(done['block_receipts_sha256'])
    assert set(done['output_sha256']) == {str(p) for p in od.rglob('*') if p.is_file()}
    assert set(done['block_receipts_sha256']) == {str(rd/f'BLOCK_{i}.json') for i in BLOCKS}
    assert {p.name for p in rd.iterdir()} == {'COMPLETE.json', 'MANIFEST.json'} | {f'BLOCK_{i}.json' for i in BLOCKS}
    assert done['benchmark_excluded'] is True and done['new_confirmation_founders'] == 0 and done['new_founders'] == 4
    assert all(done[k] is False for k in ('automatic_polling', 'automatic_retry', 'automatic_successor'))
    checked = saved_panel(od, rd); assert checked == done['verification']
    frozen(); return checked


def main():
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare', type=Path); g.add_argument('--launch', action='store_true')
    g.add_argument('--run', action='store_true'); g.add_argument('--audit', action='store_true')
    a = p.parse_args()
    value = prepare(a.prepare.resolve()) if a.prepare else launch() if a.launch else execute() if a.run else audit()
    print(json.dumps(value, sort_keys=True), flush=True)


if __name__ == '__main__': main()
