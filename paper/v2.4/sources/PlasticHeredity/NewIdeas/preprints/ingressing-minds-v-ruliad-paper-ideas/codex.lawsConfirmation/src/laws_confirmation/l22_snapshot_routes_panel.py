"""D192 unchanged four-block panel: qualification, freeze, detached run and audit."""

import argparse
from dataclasses import asdict
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

from . import l22_snapshot_routes_panel_block as block
from . import l22_snapshot_routes_benchmark as benchmark
from . import l22_snapshot_routes_panel_analysis as analysis
from . import l22_fresh_founders as inherited
from .io import canonical_digest, sha256_file, utc_now

model, WS, BASE = block.model, block.WS, block.BASE
ROOT = block.ROOT
RUN = 'l22_snapshot_routes_v1_panel_attempt1'
CAP, HEADROOM, RESERVE = 2*1024**3, 64*1024**2, 4*1024**3
BLOCK_BOUND, EXTRA_BOUND, QUAL_BOUND = 256*1024**2, 32*1024**2, 512*1024**2
BOUND = 4*BLOCK_BOUND+EXTRA_BOUND
BLOCKS, FUTURES = model.BLOCKS, block.FUTURES
ENV, READY = 'D192_PANEL_STAGE', 'D192_PANEL_READY_FD'
BENCH_ROOT = benchmark.ROOT
BENCH_DATA = BENCH_ROOT/'outputs'/benchmark.RUN
BENCH_RECEIPTS = BENCH_ROOT/'runs'/benchmark.RUN
IDENTITIES = {
    BENCH_ROOT/'FREEZE.json': '9f5ddd7d1e42874512a42b637860e6e08ca5dfaaeb24f2e753cf0542af12715f',
    BENCH_RECEIPTS/'MANIFEST.json': '438d94ac746ab0eea5043f5d0fa7aca7971e5c3e08a1e7dd1c9777d0d193e740',
    BENCH_RECEIPTS/'COMPLETE.json': '8d3bf611dc0bd4e52fd1a46710077edea1a3ffcefb573556d492a9d94ec26489',
    BENCH_DATA/'SUMMARY.json': 'bd6104079d2830ccd9da56a803a442cce7c546b69193ae8d4c51b143ef469d1e',
}
SCIENCE = (*benchmark.SCIENCE, 'L22-active-form/SNAPSHOT_ROUTES_PANEL_V1.md',
    'src/laws_confirmation/l22_snapshot_routes_panel.py',
    'src/laws_confirmation/l22_snapshot_routes_panel_block.py',
    'src/laws_confirmation/l22_snapshot_routes_panel_analysis.py',
    'scripts/check_l22_snapshot_routes_panel.py', 'scripts/qualify_l22_snapshot_routes_panel.py',
    'tests/test_l22_snapshot_routes_panel.py', 'scripts/report_l22_snapshot_routes_benchmark.py',
    'L22-active-form/SNAPSHOT_ROUTES_BENCHMARK_RESULTS.md',
    'L22-active-form/SNAPSHOT_ROUTES_BENCHMARK_TABLES.md')
TESTS = (*benchmark.TESTS, 'tests/test_l22_snapshot_routes_panel.py')
REQUIRED = benchmark.REQUIRED | {'test_d192_panel_admission', 'test_d192_panel_source_binding',
    'test_d192_panel_exact_bridge', 'test_d192_panel_workflow_identity',
    'test_d192_panel_aggregate', 'test_d192_panel_summary_tamper', 'test_d192_panel_saved_tamper',
    'test_d192_panel_saved_no_dynamics', 'test_d192_panel_execute_order',
    'test_d192_panel_saved_panel', 'test_d192_panel_launch_startup_only', 'test_d192_panel_resources',
    'test_d192_panel_freeze_drift', 'test_d192_panel_failure_retained', 'test_d192_panel_write_once',
    'test_d192_panel_bound', 'test_d192_panel_prepare_binds_qualification', 'test_d192_panel_audit_chain',
    'test_d192_panel_report_matches', 'test_d192_panel_qualification_receipt'}
read, arrays, verify = block.read, block.arrays, block.verify


def target(path):
    if block.ROOT != ROOT: raise RuntimeError('block/executor roots diverged')
    return block.target(path)


def write(path, value):
    target(path); block.write(path, value)


def resources(allowance=0):
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve().is_relative_to(Path('/mnt/bioIce1').resolve())
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(n) == '1', n
    for n in ('TMPDIR', 'XDG_CACHE_HOME'):
        assert Path(os.environ[n]).resolve().is_relative_to(ROOT.resolve()), n
    for p in ROOT.rglob('*'):
        if p.is_symlink():
            parts = p.relative_to(ROOT).parts
            # Pytest keeps "current" aliases and our negative tests deliberately
            # construct links. They are retained evidence, never execution paths.
            assert len(parts) >= 4 and parts[0] == 'qualification'
            assert parts[1].startswith('workflow_attempt') and parts[2] == 'fixtures'
            fixture_root = ROOT/'qualification'/parts[1]/'fixtures'
            assert p.resolve().is_relative_to(fixture_root.resolve())
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE+allowance+HEADROOM
    return dict(bytes=size, cap_bytes=CAP, reserved_output_bytes=allowance, headroom_bytes=HEADROOM,
        free_volume_reserve_bytes=RESERVE, workers=1, numerical_threads=1, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS, 0))


def storage_bound():
    per_block = benchmark.storage_bound()
    return dict(per_block=per_block, blocks=4, aggregate_allowance=EXTRA_BOUND,
                total=4*per_block['total']+EXTRA_BOUND)


def imported_paths():
    block.checker(); model.source.api()
    return benchmark.imported_paths() | {WS/n for n in SCIENCE if n.endswith('.py')}


def benchmark_evidence():
    verify({str(p): h for p, h in IDENTITIES.items()})
    f, done = read(BENCH_ROOT/'FREEZE.json'), read(BENCH_RECEIPTS/'COMPLETE.json')
    manifest = read(BENCH_RECEIPTS/'MANIFEST.json')
    assert done['status'] == 'COMPLETE' and done['verification']['passes']
    assert {p.name for p in BENCH_RECEIPTS.iterdir()} == {'COMPLETE.json', 'MANIFEST.json'}
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == sha256_file(BENCH_ROOT/'FREEZE.json')
    assert done['manifest_sha256'] == sha256_file(BENCH_RECEIPTS/'MANIFEST.json')
    assert done['summary_sha256'] == sha256_file(BENCH_DATA/'SUMMARY.json')
    assert done['main_cohort_started'] is False
    assert set(done['output_sha256']) == {str(p) for p in BENCH_DATA.rglob('*') if p.is_file()}
    assert done['full_replay'] == read(BENCH_DATA/'CHECK.json')
    inputs = f['inputs'] | done['output_sha256'] | {str(p): h for p, h in IDENTITIES.items()}
    verify(inputs)
    assert benchmark.block.saved_check(BENCH_DATA, model.DISPOSABLE) == done['verification']
    assert abs(done['seconds']-222.78985717194155) < 1e-9
    return inputs


def budget():
    seconds = read(BENCH_RECEIPTS/'COMPLETE.json')['seconds']
    return dict(measured_complete_block_seconds=seconds, serial_reference_seconds=4*seconds,
                allowance_seconds=8*seconds+180, measured_panel_runtime=False)


def test_receipt(xml):
    assert xml.resolve().is_relative_to(ROOT.resolve())
    suites = list(ET.parse(xml).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    assert len(cases) == sum(int(s.get('tests', 0)) for s in suites) and len(cases) >= 125
    assert REQUIRED <= {c.get('name').split('[')[0] for c in cases}
    assert not any(list(c.iter(k)) for c in cases for k in ('failure', 'error', 'skipped'))
    return dict(path=str(xml), sha256=sha256_file(xml), cases=len(cases), seconds=sum(float(s.get('time', 0)) for s in suites))


def qualification_evidence(directory):
    assert directory.resolve().is_relative_to((ROOT/'qualification').resolve())
    assert (directory/'COMPLETE.json').exists() and not (directory/'FAILED.json').exists()
    m, d = read(directory/'MANIFEST.json'), read(directory/'COMPLETE.json')
    assert d['status'] == 'COMPLETE' and d['inputs_unchanged'] and d['main_cohort_started'] is False
    assert d['manifest_sha256'] == sha256_file(directory/'MANIFEST.json')
    verify(m['inputs']); verify(d['artifacts'])
    tests = test_receipt(directory/'tests.xml'); assert tests == d['tests']
    paths = imported_paths() | {WS/n for n in SCIENCE}
    assert {str(p) for p in paths} <= set(m['inputs'])
    assert (directory/'tests.xml').stat().st_mtime_ns >= max(p.stat().st_mtime_ns for p in paths)
    inputs = m['inputs'] | d['artifacts'] | {str(directory/n): sha256_file(directory/n) for n in ('MANIFEST.json', 'COMPLETE.json')}
    return inputs, tests


def freeze_path(): return ROOT/'FREEZE.json'


def prepare(directory):
    resources(BOUND); analytical = storage_bound(); assert analytical['total'] < BOUND
    assert not freeze_path().exists() and not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    qualification, tests = qualification_evidence(directory)
    inputs = benchmark_evidence() | qualification
    old = read(block.OLD_ROOT/'FREEZE.json')
    verify(old['inputs']); inputs.update(old['inputs'])
    for index in BLOCKS:
        inputs.update(block.source_bundle(index)['provenance']['source_sha256'])
    modules = imported_paths(); inputs.update({str(p): sha256_file(p) for p in modules | {WS/n for n in SCIENCE}})
    assert all(inputs[p] == h for p, h in qualification.items())
    verify(inputs)
    value = dict(schema='d192_panel_freeze_v1', frozen_utc=utc_now(), inputs=inputs,
        tests=tests, imported_repository_modules=sorted(str(p) for p in modules),
        config=asdict(model.CONFIG), readout_config=asdict(model.READOUT), blocks=list(BLOCKS),
        qualification=model.QUALIFICATION, futures=list(FUTURES),
        repairs={n: asdict(s) for n, s in model.plan().items()}, packets=list(block.packet_names()),
        comparisons=model.comparisons(), bridge_names=block.bridge_names(), analytical_storage_bound=analytical,
        output_reservation_bytes=BOUND, budget=budget(), resources=resources(BOUND),
        benchmark_excluded=True, new_founders=0, source_regenerated=False, confirmatory=False,
        automatic_polling=False, automatic_retry=False, automatic_successor=False,
        python=sys.version, numpy=np.__version__)
    write(freeze_path(), value)
    return dict(freeze_sha256=sha256_file(freeze_path()), inputs=len(inputs), imported_repository_modules=len(modules),
        tests=tests, analytical_storage_bound=analytical, resources=value['resources'], budget=value['budget'])


def frozen():
    f = read(freeze_path()); verify(f['inputs'])
    assert f['schema'] == 'd192_panel_freeze_v1'
    assert canonical_digest(f['config']) == canonical_digest(asdict(model.CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(model.READOUT))
    assert f['qualification'] == model.QUALIFICATION and f['blocks'] == list(BLOCKS) and f['futures'] == list(FUTURES)
    assert f['repairs'] == {n: asdict(s) for n, s in model.plan().items()}
    assert f['packets'] == list(block.packet_names()) and f['comparisons'] == model.comparisons()
    assert f['bridge_names'] == block.bridge_names() and f['analytical_storage_bound'] == storage_bound()
    assert f['output_reservation_bytes'] == BOUND and f['resources']['cap_bytes'] == CAP
    assert f['budget'] == budget() and f['benchmark_excluded'] is True and f['new_founders'] == 0
    assert all(f[k] is False for k in ('source_regenerated', 'confirmatory', 'automatic_polling', 'automatic_retry', 'automatic_successor'))
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert set(f['imported_repository_modules']) == {str(p) for p in imported_paths()}
    assert set(f['imported_repository_modules']) <= set(f['inputs'])
    return f


def saved_panel(directory, receipts, cfg=block.CONFIG, rcfg=block.READOUT):
    assert {p.name for p in directory.iterdir()} == {'SUMMARY.json'} | {f'tissue_{i}' for i in BLOCKS}
    unique, count = 0, 1
    for i in BLOCKS:
        d = directory/f'tissue_{i}'; record = read(receipts/f'BLOCK_{i}.json')
        assert record['status'] == 'COMPLETE' and record['index'] == i
        assert record['freeze_sha256'] == sha256_file(freeze_path())
        assert record['full_replay'] == read(d/'CHECK.json')
        verify(record['output_sha256'])
        assert set(record['output_sha256']) == {str(p) for p in d.rglob('*') if p.is_file()}
        checked = block.saved_check(d, i, cfg, rcfg); assert checked == record['verification']
        assert record['saved_verification_seconds'] >= 0
        unique += checked['unique_reads']; count += len(record['output_sha256'])
    value = analysis.aggregate(analysis.load_blocks(directory), cfg.replicates, rcfg.draws)
    assert value == read(directory/'SUMMARY.json')
    return dict(passes=True, blocks=4, records=16*cfg.replicates, repair_paths=104, body_free_paths=8,
        named_reads=280, unique_reads=unique, comparisons=54, native_saved_bridges=48, held_fixed_bridges=8,
        new_dynamics=0, new_founders=0, benchmark_excluded=True, output_files=count,
        independent_scalar_scores=True, equal_block_equal_future=True, omission_divisor=3)


def execute_blocks(directory, receipts, cfg=block.CONFIG, rcfg=block.READOUT):
    assert not directory.exists(); target(directory/'SUMMARY.json')
    for position, i in enumerate(BLOCKS):
        resources((4-position)*BLOCK_BOUND+EXTRA_BOUND)
        d = directory/f'tissue_{i}'; proof = block.run_block(d, i, cfg, rcfg)
        tick = time.monotonic(); checked = block.saved_check(d, i, cfg, rcfg)
        write(receipts/f'BLOCK_{i}.json', dict(status='COMPLETE', index=i, completed_utc=utc_now(),
            freeze_sha256=sha256_file(freeze_path()), full_replay=proof, verification=checked,
            saved_verification_seconds=time.monotonic()-tick,
            output_sha256={str(p): sha256_file(p) for p in sorted(d.rglob('*')) if p.is_file()}))
        print(__import__('json').dumps(dict(stage='block_complete', index=i, checked_blocks=position+1, total_blocks=4)), flush=True)
    write(directory/'SUMMARY.json', analysis.aggregate(analysis.load_blocks(directory), cfg.replicates, rcfg.draws))
    return saved_panel(directory, receipts, cfg, rcfg)


def execute():
    resources(BOUND); f = frozen()
    assert os.environ.get(ENV) == 'panel' and os.getsid(0) == os.getpid()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists()
    rd.mkdir(parents=True); started = time.monotonic()
    try:
        write(rd/'MANIFEST.json', dict(started_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            budget=f['budget'], resources=resources(BOUND), blocks=list(BLOCKS), automatic_successor=False))
        fd = os.environ.pop(READY, None)
        if fd is not None: os.write(int(fd), b'READY\n'); os.close(int(fd))
        checked = execute_blocks(od, rd)
        frozen(); resources()
        output_hashes = {str(p): sha256_file(p) for p in sorted(od.rglob('*')) if p.is_file()}
        size = sum(sum(v.nbytes for v in arrays(p).values()) for p in od.rglob('*.npz'))
        assert size < storage_bound()['total'] < BOUND
        result = dict(status='COMPLETE', completed_utc=utc_now(), seconds=time.monotonic()-started,
            freeze_sha256=sha256_file(freeze_path()), manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            summary_sha256=sha256_file(od/'SUMMARY.json'), verification=checked, output_sha256=output_hashes,
            block_receipts_sha256={str(rd/f'BLOCK_{i}.json'): sha256_file(rd/f'BLOCK_{i}.json') for i in BLOCKS},
            resources=resources(), process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            uncompressed_array_bytes=size, new_founders=0, source_regenerated=False, benchmark_excluded=True,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write(rd/'COMPLETE.json', result)
        return {k: v for k, v in result.items() if k not in ('output_sha256', 'block_receipts_sha256')}
    except Exception as exc:
        write(rd/'FAILED.json', dict(status='FAILED', failed_utc=utc_now(), error=str(exc), traceback=traceback.format_exc(),
            retained=True, automatic_retry=False, automatic_successor=False))
        raise


def audit():
    resources(); frozen()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    done, manifest = read(rd/'COMPLETE.json'), read(rd/'MANIFEST.json')
    assert done['status'] == 'COMPLETE'
    assert {p.name for p in rd.iterdir()} == {'COMPLETE.json', 'MANIFEST.json'} | {f'BLOCK_{i}.json' for i in BLOCKS}
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == sha256_file(freeze_path())
    assert done['manifest_sha256'] == sha256_file(rd/'MANIFEST.json')
    assert done['summary_sha256'] == sha256_file(od/'SUMMARY.json')
    verify(done['output_sha256']); verify(done['block_receipts_sha256'])
    assert set(done['output_sha256']) == {str(p) for p in od.rglob('*') if p.is_file()}
    assert set(done['block_receipts_sha256']) == {str(rd/f'BLOCK_{i}.json') for i in BLOCKS}
    assert done['new_founders'] == 0 and done['source_regenerated'] is False and done['benchmark_excluded'] is True
    assert all(done[k] is False for k in ('automatic_polling', 'automatic_retry', 'automatic_successor'))
    checked = saved_panel(od, rd); assert checked == done['verification']; frozen()
    return checked


def launch():
    resources(BOUND); f = frozen()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log, receipt = ROOT/'logs'/(RUN+'.log'), ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    rd, wr = os.pipe(); env = dict(os.environ, **{ENV: 'panel', READY: str(wr)})
    try:
        with target(log).open('xb') as out:
            process = subprocess.Popen([sys.executable, '-u', '-m', 'laws_confirmation.l22_snapshot_routes_panel', '--run'],
                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, cwd=WS, env=env,
                start_new_session=True, pass_fds=(wr,))
    finally: os.close(wr)
    available = select.select([rd], [], [], 30)[0]
    message = os.read(rd, 64) if available else b''; os.close(rd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        acknowledged_utc=utc_now(), pid=process.pid, log=str(log), workers=1, numerical_threads=1,
        affinity=[6], nice=10, budget=f['budget'], automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write(receipt, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare', type=Path); g.add_argument('--launch', action='store_true')
    g.add_argument('--run', action='store_true'); g.add_argument('--audit', action='store_true')
    args = p.parse_args()
    result = prepare(args.prepare.resolve()) if args.prepare else launch() if args.launch else audit() if args.audit else execute()
    print(__import__('json').dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__': main()
