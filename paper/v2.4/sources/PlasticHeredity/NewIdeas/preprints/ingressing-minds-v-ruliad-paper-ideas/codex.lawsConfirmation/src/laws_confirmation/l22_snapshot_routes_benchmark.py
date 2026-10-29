"""D192 qualified disposable-only freeze, detached execution and saved audit."""

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

from . import l22_snapshot_routes_run as block
from . import l22_fresh_founders as inherited
from .io import canonical_digest, sha256_file, utc_now

model, WS, BASE = block.model, block.WS, block.BASE
ROOT = block.ROOT
RUN = 'l22_snapshot_routes_v1_benchmark_attempt1'
CAP, BOUND, HEADROOM, RESERVE = 1024**3, 256*1024**2, 64*1024**2, 4*1024**3
QUAL_BOUND, ALLOWANCE = 384*1024**2, 1200
ENV, READY = 'D192_BENCHMARK_STAGE', 'D192_BENCHMARK_READY_FD'
KERNEL = BASE/'L22-snapshot-routes-v1/qualification/kernel_attempt1'
KERNEL_IDENTITIES = {KERNEL/'MANIFEST.json': '1474b4359841ee8cbc1f9a363fa76a68058390bd783a128cb62b91cadd5f9b16',
    KERNEL/'COMPLETE.json': '9b74bfe3a3dca3453e2e7b854a42ff7f6ec277651154b0f75f6ed4361b583140',
    KERNEL/'tests.xml': '253d91e14198f75b5aff897340729de2acffdf5c96150d184f3cdf1599416df4',
    KERNEL/'tests.log': 'ecc462d12bac734e50039684df6c226cad1f40b9154146b407e2abec932ef5e9'}
SCIENCE = ('L22-active-form/SNAPSHOT_ROUTES_V1.md', 'L22-active-form/SNAPSHOT_ROUTES_BENCHMARK_V1.md',
    'src/laws_confirmation/l22_snapshot_routes.py', 'src/laws_confirmation/l22_snapshot_routes_run.py',
    'src/laws_confirmation/l22_snapshot_routes_benchmark.py', 'scripts/check_l22_snapshot_routes.py',
    'scripts/check_l22_snapshot_routes_run.py', 'scripts/qualify_l22_snapshot_routes_workflow.py',
    'tests/test_l22_snapshot_routes.py', 'tests/test_l22_snapshot_routes_run.py',
    'scripts/report_l22_fresh_founders_panel.py', 'L22-active-form/FRESH_FOUNDERS_PANEL_TABLES.md')
TESTS = ('tests/test_l22_snapshot_routes.py', 'tests/test_l22_snapshot_routes_run.py')
REQUIRED = {'test_d192_full_schedule_native_bridge', 'test_d192_every_path_replays',
    'test_d192_snapshot_writer_body_independence', 'test_d192_writer_gate_cannot_change_body',
    'test_d192_complete_workflow', 'test_d192_complete_saved_no_dynamics', 'test_d192_saved_tamper',
    'test_d192_summary_tamper', 'test_d192_source_binding', 'test_d192_complete_scope',
    'test_d192_admission', 'test_d192_launch_startup_only', 'test_d192_resources',
    'test_d192_write_once', 'test_d192_failure_retained', 'test_d192_freeze_drift',
    'test_d192_bound', 'test_d192_prepare_binds_qualification', 'test_d192_saved_audit_chain'}
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
    field = 4*model.CONFIG.replicates*16*16*8
    times, rt, draws = len(model.CONFIG.times), len(model.READOUT.times), model.READOUT.draws
    # Per-family full arrays: 4 gate*8 + averaging2 + held2*8 + free3 + off8
    # + scramble8 + ordinary fixed6/live4 + captured live4/held4 = 87.
    repair = 2*87*times*field+2*8*times*8+2*model.CONFIG.replicates*256*8
    bridges = 2*(6*4+2*2)*times*field
    source = 64*field
    packets = 35*field
    reads = 70*rt*4*draws*field+70*(4*model.READOUT.parents*draws)*10*8
    behavior = 70*4*model.READOUT.parents*draws*3*8
    return dict(repair_arrays=repair, copied_bridge_arrays=bridges, source_arrays=source,
        packet_arrays=packets, read_arrays=reads, behavior_arrays=behavior,
        json_and_container_allowance=32*1024**2,
        total=sum((repair, bridges, source, packets, reads, behavior, 32*1024**2)))


def imported_paths():
    block.checker(); model.source.api()
    values = inherited.imported_paths()
    values |= {WS/n for n in SCIENCE if n.endswith('.py')}
    values |= {WS/'scripts'/n for n in ('check_l22_snapshot_routes.py', 'check_l22_snapshot_routes_run.py',
        'check_l22_fresh_founders.py', 'check_l22_active_form_boundary.py', 'check_l22_active_form_pilot.py',
        'check_l22_early_capture.py', 'check_l22_packet_components.py', 'check_l22_direction_allocation.py')}
    # This explicitly includes dynamically loaded checkers and qualification/test code.
    return values


def kernel_evidence():
    verify({str(p): h for p, h in KERNEL_IDENTITIES.items()})
    m, d = read(KERNEL/'MANIFEST.json'), read(KERNEL/'COMPLETE.json')
    assert d['passes'] and d['status'] == 'COMPLETE' and d['counts'] == dict(errors=0, failures=0, skipped=0, tests=67)
    assert d['manifest_sha256'] == sha256_file(KERNEL/'MANIFEST.json')
    verify(m['inputs']); verify(d['artifacts'])
    return m['inputs'] | d['artifacts'] | {str(p): h for p, h in KERNEL_IDENTITIES.items()}


def test_receipt(xml):
    assert xml.resolve().is_relative_to(ROOT.resolve())
    suites = list(ET.parse(xml).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    assert len(cases) == sum(int(s.get('tests', 0)) for s in suites) and len(cases) >= 90
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
    inputs = kernel_evidence() | qualification
    source = block.source_bundle(model.DISPOSABLE)
    old = read(block.OLD_ROOT/'FREEZE.json')
    verify(old['inputs'])
    inputs.update(old['inputs']); inputs.update(source['provenance']['source_sha256'])
    modules = imported_paths(); inputs.update({str(p): sha256_file(p) for p in modules | {WS/n for n in SCIENCE}})
    # No earlier-qualified path may silently take a new identity.
    assert all(inputs[p] == h for p, h in qualification.items())
    verify(inputs)
    value = dict(schema='d192_disposable_freeze_v1', frozen_utc=utc_now(), inputs=inputs,
        tests=tests, imported_repository_modules=sorted(str(p) for p in modules),
        config=asdict(model.CONFIG), readout_config=asdict(model.READOUT), disposable=model.DISPOSABLE,
        qualification=model.QUALIFICATION, planned_main_blocks=list(model.BLOCKS), futures=list(block.FUTURES),
        repairs={n: asdict(s) for n, s in model.plan().items()}, packets=list(block.packet_names()),
        comparisons=model.comparisons(), bridge_names=block.bridge_names(), analytical_storage_bound=analytical,
        output_reservation_bytes=BOUND, benchmark_allowance_seconds=ALLOWANCE, resources=resources(BOUND),
        main_cohort_executor_enabled=False, automatic_polling=False, automatic_retry=False, automatic_successor=False,
        python=sys.version, numpy=np.__version__)
    write(freeze_path(), value)
    return dict(freeze_sha256=sha256_file(freeze_path()), inputs=len(inputs), imported_repository_modules=len(modules),
        tests=tests, analytical_storage_bound=analytical, resources=value['resources'], benchmark_allowance_seconds=ALLOWANCE)


def frozen():
    f = read(freeze_path()); verify(f['inputs'])
    assert f['schema'] == 'd192_disposable_freeze_v1'
    assert canonical_digest(f['config']) == canonical_digest(asdict(model.CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(model.READOUT))
    assert f['disposable'] == model.DISPOSABLE and f['qualification'] == model.QUALIFICATION
    assert f['planned_main_blocks'] == list(model.BLOCKS) and f['futures'] == list(block.FUTURES)
    assert f['repairs'] == {n: asdict(s) for n, s in model.plan().items()}
    assert f['packets'] == list(block.packet_names()) and f['comparisons'] == model.comparisons()
    assert f['bridge_names'] == block.bridge_names() and f['analytical_storage_bound'] == storage_bound()
    assert f['output_reservation_bytes'] == BOUND and f['resources']['cap_bytes'] == CAP
    assert f['benchmark_allowance_seconds'] == ALLOWANCE
    assert all(f[k] is False for k in ('main_cohort_executor_enabled', 'automatic_polling', 'automatic_retry', 'automatic_successor'))
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert set(f['imported_repository_modules']) == {str(p) for p in imported_paths()}
    assert set(f['imported_repository_modules']) <= set(f['inputs'])
    return f


def benchmark():
    resources(BOUND); frozen()
    assert os.environ.get(ENV) == 'benchmark' and os.getsid(0) == os.getpid()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists()
    rd.mkdir(parents=True); started = time.monotonic()
    try:
        write(rd/'MANIFEST.json', dict(started_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            benchmark_allowance_seconds=ALLOWANCE, main_cohort_started=False, automatic_successor=False))
        fd = os.environ.pop(READY, None)
        if fd is not None: os.write(int(fd), b'READY\n'); os.close(int(fd))
        proof = block.run_block(od, model.DISPOSABLE)
        tick = time.monotonic(); checked = block.saved_check(od, model.DISPOSABLE)
        verification_seconds = time.monotonic()-tick
        frozen(); resources()
        output_hashes = {str(p): sha256_file(p) for p in sorted(od.rglob('*')) if p.is_file()}
        size = sum(sum(v.nbytes for v in arrays(p).values()) for p in od.rglob('*.npz'))
        assert size < storage_bound()['total'] < BOUND
        result = dict(status='COMPLETE', completed_utc=utc_now(), seconds=time.monotonic()-started,
            saved_verification_seconds=verification_seconds, freeze_sha256=sha256_file(freeze_path()),
            manifest_sha256=sha256_file(rd/'MANIFEST.json'), summary_sha256=sha256_file(od/'SUMMARY.json'),
            verification=checked, full_replay=proof, output_sha256=output_hashes, resources=resources(),
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            uncompressed_array_bytes=size, main_cohort_started=False, automatic_polling=False,
            automatic_retry=False, automatic_successor=False)
        write(rd/'COMPLETE.json', result)
        return {k: v for k, v in result.items() if k not in ('output_sha256', 'full_replay')}
    except Exception as exc:
        write(rd/'FAILED.json', dict(status='FAILED', failed_utc=utc_now(), error=str(exc), traceback=traceback.format_exc(),
            retained=True, automatic_retry=False, main_cohort_started=False, automatic_successor=False))
        raise


def audit():
    resources(); frozen()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    done, manifest = read(rd/'COMPLETE.json'), read(rd/'MANIFEST.json')
    assert done['status'] == 'COMPLETE' and {p.name for p in rd.iterdir()} == {'COMPLETE.json', 'MANIFEST.json'}
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == sha256_file(freeze_path())
    assert done['manifest_sha256'] == sha256_file(rd/'MANIFEST.json')
    assert done['summary_sha256'] == sha256_file(od/'SUMMARY.json')
    verify(done['output_sha256'])
    assert set(done['output_sha256']) == {str(p) for p in od.rglob('*') if p.is_file()}
    assert done['full_replay'] == read(od/'CHECK.json')
    assert all(done[k] is False for k in ('main_cohort_started', 'automatic_polling', 'automatic_retry', 'automatic_successor'))
    checked = block.saved_check(od, model.DISPOSABLE); assert checked == done['verification']; frozen()
    return checked | dict(output_files=len(done['output_sha256']))


def launch():
    resources(BOUND); frozen()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log, receipt = ROOT/'logs'/(RUN+'.log'), ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    rd, wr = os.pipe(); env = dict(os.environ, **{ENV: 'benchmark', READY: str(wr)})
    try:
        with target(log).open('xb') as out:
            process = subprocess.Popen([sys.executable, '-u', '-m', 'laws_confirmation.l22_snapshot_routes_benchmark', '--benchmark'],
                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, cwd=WS, env=env,
                start_new_session=True, pass_fds=(wr,))
    finally: os.close(wr)
    available = select.select([rd], [], [], 30)[0]
    message = os.read(rd, 64) if available else b''; os.close(rd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        acknowledged_utc=utc_now(), pid=process.pid, log=str(log), workers=1, numerical_threads=1,
        affinity=[6], nice=10, benchmark_allowance_seconds=ALLOWANCE, main_cohort_started=False,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write(receipt, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare', type=Path); g.add_argument('--launch-benchmark', action='store_true')
    g.add_argument('--benchmark', action='store_true'); g.add_argument('--audit', action='store_true')
    args = p.parse_args()
    result = prepare(args.prepare.resolve()) if args.prepare else launch() if args.launch_benchmark else audit() if args.audit else benchmark()
    print(__import__('json').dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__': main()
