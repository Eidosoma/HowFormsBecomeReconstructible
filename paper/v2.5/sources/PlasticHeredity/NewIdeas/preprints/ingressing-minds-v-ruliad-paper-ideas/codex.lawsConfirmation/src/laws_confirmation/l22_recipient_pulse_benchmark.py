"""D195 qualified recipient-pulse benchmark, detached execution and saved audit."""

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

from . import l22_recipient_pulse_run as block
from . import l22_fresh_founders as inherited
from .io import canonical_digest, sha256_file, utc_now

model, WS, BASE = block.model, block.WS, block.BASE
ROOT = block.ROOT
RUN = 'l22_recipient_pulse_v1_benchmark_attempt1'
CAP, BOUND, HEADROOM, RESERVE = 2*1024**3, 512*1024**2, 64*1024**2, 4*1024**3
QUAL_BOUND, ALLOWANCE = 512*1024**2, 1200
ENV, READY = 'D195_BENCHMARK_STAGE', 'D195_BENCHMARK_READY_FD'
KERNEL = BASE/'L22-yoked-reference-v1/qualification/kernel_attempt1'
KERNEL_IDENTITIES = {KERNEL/'MANIFEST.json': '6630040c1983ca0bf48852d826d591a87afa2b20cb47bc6dd263e1540d9c56f4',
    KERNEL/'COMPLETE.json': 'ff9c76b70c4d8852687010f1bc34f72b0d3a26b8e1451176e75f8e40cab9f9dc',
    KERNEL/'tests.xml': 'c81e768bdb1b1dd20ebf859844fff4e1b2c9c7c584b509373925ee2fdb2c23bd',
    KERNEL/'tests.log': 'b92dff94c5f223468031bdf29e5d1bac09ec2cdc527ccc328238decbdb44da79'}
SCIENCE = ('L22-active-form/YOKED_REFERENCE_V1.md', 'L22-active-form/YOKED_REFERENCE_BENCHMARK_V1.md',
    'src/laws_confirmation/l22_yoked_reference.py', 'src/laws_confirmation/l22_yoked_reference_run.py',
    'src/laws_confirmation/l22_yoked_reference_benchmark.py', 'scripts/check_l22_yoked_reference.py',
    'scripts/check_l22_yoked_reference_run.py', 'scripts/qualify_l22_yoked_reference_workflow.py',
    'tests/test_l22_yoked_reference.py', 'tests/test_l22_yoked_reference_run.py', 'pyproject.toml',
    'scripts/report_l22_snapshot_routes_panel.py', 'L22-active-form/SNAPSHOT_ROUTES_PANEL_TABLES.md')
SCIENCE += ('L22-active-form/RECIPIENT_PULSE_V1.md',
    'src/laws_confirmation/l22_recipient_pulse.py', 'src/laws_confirmation/l22_recipient_pulse_run.py',
    'src/laws_confirmation/l22_recipient_pulse_benchmark.py', 'scripts/check_l22_recipient_pulse_kernel.py',
    'scripts/check_l22_recipient_pulse_run.py', 'scripts/qualify_l22_recipient_pulse.py',
    'tests/test_l22_recipient_pulse.py', 'scripts/report_l22_yoked_reference_benchmark.py')
TESTS = ('tests/test_l22_yoked_reference.py','tests/test_l22_recipient_pulse.py')
REQUIRED = {'test_d193_full_schedule_native_and_self_replay', 'test_pulse_full_schedule',
    'test_complete_workflow','test_saved_no_dynamics','test_pulse_tamper','test_saved_tamper',
    'test_scope','test_donor_barrier','test_bad_seal','test_admission','test_launch_startup_only',
    'test_resources','test_write_once','test_failure_retained','test_freeze_drift','test_bound',
    'test_qualification_binding','test_saved_audit_chain','test_source_binding','test_native_bridge'}
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
    trace = 4*(model.CONFIG.sweeps+1)*field
    repair = (24*7+8*3)*times*field
    source, packets = 64*field, 37*field
    reads = 74*rt*4*draws*field+74*(4*model.READOUT.parents*draws)*10*8
    behavior = 74*4*model.READOUT.parents*draws*3*8
    event = 12*12*field
    return dict(event_arrays=event, trace_arrays=trace, repair_arrays=repair, source_arrays=source, packet_arrays=packets,
        read_arrays=reads, behavior_arrays=behavior, json_and_container_allowance=64*1024**2,
        total=sum((trace, repair, event, source, packets, reads, behavior, 64*1024**2)))


def imported_paths():
    block.checker(); model.source.api()
    values = inherited.imported_paths()
    values |= {WS/n for n in SCIENCE if n.endswith('.py')}
    values |= {WS/'scripts'/n for n in ('check_l22_yoked_reference.py', 'check_l22_yoked_reference_run.py',
        'check_l22_snapshot_routes.py', 'check_l22_snapshot_routes_run.py', 'check_l22_fresh_founders.py',
        'check_l22_active_form_boundary.py', 'check_l22_active_form_pilot.py', 'check_l22_early_capture.py',
        'check_l22_packet_components.py', 'check_l22_direction_allocation.py')}
    return values


def kernel_evidence():
    verify({str(p): h for p, h in KERNEL_IDENTITIES.items()})
    m, d = read(KERNEL/'MANIFEST.json'), read(KERNEL/'COMPLETE.json')
    assert d['passes'] and d['status'] == 'COMPLETE' and d['counts'] == dict(errors=0, failures=0, skipped=0, tests=102)
    assert d['manifest_sha256'] == sha256_file(KERNEL/'MANIFEST.json')
    verify(m['inputs']); verify(d['artifacts'])
    return m['inputs'] | d['artifacts'] | {str(p): h for p, h in KERNEL_IDENTITIES.items()}


def test_receipt(xml):
    assert xml.resolve().is_relative_to(ROOT.resolve())
    suites = list(ET.parse(xml).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    assert len(cases) == sum(int(s.get('tests', 0)) for s in suites) and len(cases) >= 140
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
    inputs = kernel_evidence() | qualification | block.baseline_evidence()
    source = block.source_bundle(model.DISPOSABLE)
    old = read(block.OLD_ROOT/'FREEZE.json')
    verify(old['inputs'])
    inputs.update(old['inputs']); inputs.update(source['provenance']['source_sha256'])
    modules = imported_paths(); inputs.update({str(p): sha256_file(p) for p in modules | {WS/n for n in SCIENCE}})
    # No earlier-qualified path may silently take a new identity.
    assert all(inputs[p] == h for p, h in qualification.items())
    verify(inputs)
    value = dict(schema='d195_disposable_freeze_v1', frozen_utc=utc_now(), inputs=inputs,
        tests=tests, imported_repository_modules=sorted(str(p) for p in modules),
        config=asdict(model.CONFIG), readout_config=asdict(model.READOUT), disposable=model.DISPOSABLE,
        qualification=model.QUALIFICATION, planned_main_blocks=list(model.BLOCKS), futures=list(block.FUTURES),
        repairs={n: dict(stream=s, **asdict(spec)) for n, (s, spec) in block.paths().items()}, packets=list(block.packet_names()),
        comparisons=model.comparisons(), repair_streams=list(block.ROLES), analytical_storage_bound=analytical,
        output_reservation_bytes=BOUND, benchmark_allowance_seconds=ALLOWANCE, resources=resources(BOUND),
        pulse=model.pulse_contract(model.CONFIG,True), main_cohort_executor_enabled=False, automatic_polling=False, automatic_retry=False, automatic_successor=False,
        python=sys.version, numpy=np.__version__)
    write(freeze_path(), value)
    return dict(freeze_sha256=sha256_file(freeze_path()), inputs=len(inputs), imported_repository_modules=len(modules),
        tests=tests, analytical_storage_bound=analytical, resources=value['resources'], benchmark_allowance_seconds=ALLOWANCE)


def frozen():
    f = read(freeze_path()); verify(f['inputs'])
    assert f['schema'] == 'd195_disposable_freeze_v1'
    assert canonical_digest(f['config']) == canonical_digest(asdict(model.CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(model.READOUT))
    assert f['disposable'] == model.DISPOSABLE and f['qualification'] == model.QUALIFICATION
    assert f['planned_main_blocks'] == list(model.BLOCKS) and f['futures'] == list(block.FUTURES)
    assert f['repairs'] == {n: dict(stream=s, **asdict(spec)) for n, (s, spec) in block.paths().items()}
    assert f['packets'] == list(block.packet_names()) and f['comparisons'] == model.comparisons()
    assert f['pulse'] == model.pulse_contract(model.CONFIG,True)
    assert f['repair_streams'] == list(block.ROLES) and f['analytical_storage_bound'] == storage_bound()
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
            process = subprocess.Popen([sys.executable, '-u', '-m', 'laws_confirmation.l22_recipient_pulse_benchmark', '--benchmark'],
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
