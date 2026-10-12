"""D174 write-once development workflow. No polling, retries or successor jobs."""
import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from . import feedback_pulse_development as dev
from . import feedback_pulse_cold_audit as cold

q, io = dev.qualified, dev.io
ROOT, WS = io.ROOT, io.WS
RUN = 'l20_extension1_feedback_pulse_dev_v1_attempt1'
ENV, READY = 'D174_DETACHED_STAGE', 'D174_READY_FD'
SETTINGS_SHA = 'dea3c08f0de000ff827bd1d2dcc46dffab74952420a12beccb98c6bb712fed4a'
ANCHORS = {
    q.freeze_path(): cold.FREEZE_SHA,
    q.timing_path(): cold.BENCHMARK_SHA,
    cold.support_path(): '1b96a51479725e5cd9b1ed98f8b6879b9c0d0126d8a5389c2b25b186be81af56',
    q.audit_path(): '86f26d7abf18a370f50f4d8214b859d025b1bd20d1f322d6533428df20fc8e8a',
    ROOT / 'logs' / (q.RUN + '_documentation_v1.json'): '82399d6843768063da92ac9f30ffed92adbe234989349644d54445d728d023c6',
    io.freeze_path(): SETTINGS_SHA,
}
SCIENCE = ('feedback-placement-challenge/DEVELOPMENT_PROTOCOL_V1.md',
    'src/l20_extension1/feedback_pulse_development.py',
    'src/l20_extension1/feedback_pulse_development_run.py',
    'tests/test_feedback_pulse_development.py', 'scripts/run_feedback_pulse_development.sh')


def freeze_path(): return ROOT / 'tmp' / (RUN + '_freeze.json')
def timing_path(): return ROOT / 'tmp' / (RUN + '_benchmark.json')
def benchmark_dir(): return ROOT / 'tmp' / (RUN + '_benchmark')
def run_dir(): return ROOT / 'runs' / RUN
def output_dir(): return ROOT / 'outputs' / RUN
def audit_path(): return ROOT / 'logs' / (RUN + '_saved_audit_v1.json')
def log_path(stage): return ROOT / 'logs' / (RUN + '_' + stage + '.log')


def science(): return [WS / 'L20-extension-1' / name for name in SCIENCE]


def contract():
    return dict(run=RUN, blocks=list(dev.IDS), lives=4, groups=4, cases=256,
        branches=['U1', 'P1'], diagnostic_cycles=512, readers_per_cycle=2,
        independent_replay_cycles=512, source_U1_reproductions=256,
        future_arrays_only_after_diagnostic_seal=True, future_source='D142_saved_four_via_D157',
        new_models=48, reused_models=144, new_forecasts=768, reference_refits=0,
        alphas=list(dev.model.ALPHAS), focal=['tied:pulse', 'tied:passive', .01],
        pulse_shift=[2, 1], pulse_bounds=[301, 400], prospective_evidence=False,
        new_actual_lineages=0, new_founders=0, pilot_application=False,
        workers=1, maximum_cpus=6, numerical_threads=1,
        allowance=q.ALLOWANCE, reserve=q.RESERVE, allowance_includes_D173=True,
        detach_above_seconds=600, automatic_polling=False, automatic_retry=False, automatic_successor=False)


def pytest_alias(root, item):
    """Accept only pytest's redundant sibling-directory `...current` aliases."""
    assert root.parent == ROOT / 'tmp' and root.name.startswith('d174_feedback_pulse_development_v')
    assert item.name.endswith('current') and item.is_symlink()
    target = item.resolve(strict=True)
    prefix = item.name[:-len('current')]
    assert target.parent == item.parent.resolve() and target.is_dir()
    assert target.name.startswith(prefix) and target.name[len(prefix):].isdigit()


def artifact_files():
    found = set(q.artifact_files())
    for area in ('tmp', 'logs', 'runs', 'outputs'):
        for pattern in (RUN + '*', 'd174_feedback_pulse_development_v*'):
            for path in (ROOT / area).glob(pattern):
                assert not path.is_symlink()
                if path.is_file():
                    found.add(path)
                elif path.is_dir():
                    for item in path.rglob('*'):
                        if item.is_symlink():
                            pytest_alias(path, item)
                            continue
                        if item.is_file():
                            found.add(item)
    return sorted(found)


def resources():
    cpus = q.resources()
    assert sum(p.stat().st_size for p in artifact_files()) < q.ALLOWANCE, 'preserve evidence; stop at storage ceiling'
    return cpus


def source_inputs():
    io.verify_hashes({str(p): h for p, h in ANCHORS.items()})
    core, support = q.frozen(), cold.checked_support()
    cold.prepare()
    audit = io.read_json(q.audit_path())
    assert audit['passes'] and audit['physical']['full_physics_replayed']
    expected = dict(core['input_sha256'])
    q.combine(expected, support['input_sha256'])
    settings = io.read_json(io.freeze_path())['input_sha256']
    required = [p for i in dev.IDS for p in dev.source_paths(i)]
    required += [ROOT / 'outputs' / io.OLD157 / p for p in
                 ('dataset.npz', 'fits.json', 'predictions.npz', 'raw_predictions.npz')]
    required += [ROOT / 'outputs' / io.OLD160 / p for p in ('tied_fits.json', 'tied_full.npz', 'tied_full_raw.npz')]
    q.combine(expected, {str(p): settings[str(p)] for p in required})
    q.combine(expected, {str(p): h for p, h in ANCHORS.items()})
    io.verify_hashes(expected)
    # Every repository module used in the cold freeze must have prior provenance,
    # or be one of this explicitly new wrapper's files.
    fresh = {p.resolve() for p in science()}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            p = Path(filename).resolve()
            if p.suffix == '.py' and WS.parents[3] in p.parents and p not in fresh:
                assert str(p) in expected, 'unbound imported source: ' + str(p)
    q.combine(expected, io.hashes(science()))
    return expected


def qualification(xml, fixtures):
    io.external(xml); io.external(fixtures)
    assert xml.parent == ROOT / 'logs' and xml.name.startswith('d174_feedback_pulse_development_v')
    assert xml.suffix == '.xml' and fixtures.parent == ROOT / 'tmp' and fixtures.name == xml.stem
    tree = ET.parse(xml).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 35 and not any(tree.findall('.//' + k) for k in ('failure', 'error', 'skipped'))
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    names = {c.get('name').split('[', 1)[0] for c in cases}
    assert {'test_reference_normalization', 'test_wrong_reference', 'test_seal_corruption',
        'test_outcome_gate', 'test_complete_wrapper_benchmark', 'test_only_pulse_fit',
        'test_cold_saved_replay', 'test_stage_guard', 'test_startup_ack', 'test_write_once',
        'test_duplicate_npz', 'test_source_binding', 'test_no_successor', 'test_pytest_alias_inventory'} <= names
    files = [p for p in fixtures.rglob('*') if p.is_file() and not p.is_symlink()]
    assert files
    return dict(xml=str(xml), tests=len(cases), xml_sha256=io.sha256_file(xml),
        fixtures=str(fixtures), fixture_sha256=io.hashes(files))


def freeze(xml, fixtures):
    resources()
    assert not any(p.exists() for p in (freeze_path(), timing_path(), benchmark_dir(), run_dir(), output_dir(), audit_path()))
    proof = qualification(xml, fixtures)
    tick = time.monotonic(); inputs = source_inputs(); hash_seconds = time.monotonic() - tick
    inputs[str(xml)] = proof['xml_sha256']
    budget = 2 * (q.timing()['seconds'] + io.read_json(q.audit_path())['seconds']) + 4 * hash_seconds + 120
    record = dict(status='FROZEN_DEVELOPMENT', frozen_utc=io.utc_now(), contract=contract(),
        input_sha256=inputs, qualification=proof, environment=io.environment_manifest(),
        hash_seconds=hash_seconds, benchmark_budget_seconds=budget, benchmark_must_detach=budget > 600)
    io.write_json(freeze_path(), record)
    return dict(status=record['status'], inputs=len(inputs), tests=proof['tests'],
        benchmark_budget_seconds=budget, benchmark_must_detach=budget > 600)


def frozen():
    f = io.read_json(freeze_path())
    assert f['status'] == 'FROZEN_DEVELOPMENT' and f['contract'] == contract()
    io.verify_hashes(f['input_sha256']); io.verify_hashes(f['qualification']['fixture_sha256'])
    assert qualification(Path(f['qualification']['xml']), Path(f['qualification']['fixtures'])) == f['qualification']
    for path in science():
        assert f['input_sha256'][str(path)] == io.sha256_file(path)
    env = io.environment_manifest()
    for key in ('python', 'numpy', 'thread_limits'):
        assert env[key] == f['environment'][key]
    cold.checked_support(); cold.prepare()
    return f


def stage_guard(required, stage):
    if required and os.environ.get(ENV) != stage:
        raise RuntimeError('forecast above 600 seconds requires detached execution')
    if os.environ.get(ENV) == stage:
        assert os.getsid(0) == os.getpid() and os.readlink('/proc/self/fd/0') == '/dev/null'
        assert Path(os.readlink('/proc/self/fd/1')) == log_path(stage)
        assert os.readlink('/proc/self/fd/2') == os.readlink('/proc/self/fd/1')


def ready(stage):
    value = os.environ.pop(READY, None)
    if value is not None:
        fd = int(value)
        try:
            os.write(fd, json.dumps(dict(stage=stage, pid=os.getpid(), status='STARTED')).encode())
        except BrokenPipeError:
            pass
        finally:
            os.close(fd)


def failed(path, exc):
    io.write_json(path, dict(failed_utc=io.utc_now(), error=str(exc), traceback=traceback.format_exc(),
        automatic_retry=False, automatic_successor=False))


def wrapper_benchmark(directory, inputs, freeze_sha256):
    """Exact block/seal/panel workflow, disposable physics and saved synthetic targets."""
    tick = time.monotonic()
    physical = dev.write_block(directory, 514240, 'disposable')
    dev.seal_diagnostics(directory, 'disposable', freeze_sha256, inputs)
    physical_seconds = time.monotonic() - tick
    tick = time.monotonic()
    data, p, raw, fits = dev.synthetic_sources()
    synthetic = dev.write_panel(directory / 'panel', data, p, raw, fits)
    synthetic_seconds = time.monotonic() - tick
    tick = time.monotonic()
    replay = dev.saved_block(directory, 514240, 'disposable', True)
    dev.model_check.same(dev.check_panel(directory / 'panel', data, p, raw, fits), synthetic)
    saved_audit_seconds = time.monotonic() - tick
    return dict(physical=physical, synthetic=synthetic, saved_replay=replay,
        physical_seconds=physical_seconds, synthetic_seconds=synthetic_seconds,
        saved_audit_seconds=saved_audit_seconds, actual_future_arrays_loaded=0,
        actual_development_cases_simulated=0, new_real_fits=0, new_synthetic_fits=48)


def benchmark():
    resources(); f = frozen()
    stage_guard(f['benchmark_must_detach'], 'benchmark')
    directory = benchmark_dir(); directory.mkdir(); ready('benchmark'); start = time.monotonic()
    try:
        io.write_json(directory / 'MANIFEST.json', dict(started_utc=io.utc_now(), freeze_sha256=io.sha256_file(freeze_path()), contract=contract()))
        proof = wrapper_benchmark(directory, f['input_sha256'], io.sha256_file(freeze_path()))
        tick = time.monotonic(); frozen(); hash_seconds = time.monotonic() - tick
        current = sum(p.stat().st_size for p in artifact_files())
        projected = current + 2 * 16 * proof['physical']['uncompressed_bytes'] + 2 * io.size(directory / 'panel') + 32 * 1024**2
        assert projected < q.ALLOWANCE
        budget = 2 * 16 * proof['physical_seconds'] + 2 * proof['synthetic_seconds'] + 4 * hash_seconds + 120
        result = dict(status='COMPLETE', completed_utc=io.utc_now(), seconds=time.monotonic() - start,
            freeze_sha256=io.sha256_file(freeze_path()), artifact_sha256=io.hashes(p for p in directory.rglob('*') if p.is_file()),
            source_hash_seconds=hash_seconds, retained_bytes_before_timing_receipt=current,
            projected_aggregate_bytes=projected, conservative_development_and_audit_budget_seconds=budget,
            development_must_detach=budget > 600, parallel_credit_in_budget=False, automatic_successor=False, **proof)
        io.write_json(timing_path(), result)
        return {k: v for k, v in result.items() if k != 'artifact_sha256'}
    except Exception as exc:
        failed(directory / 'FAILED.json', exc); raise


def timing():
    t = io.read_json(timing_path())
    assert t['status'] == 'COMPLETE' and t['freeze_sha256'] == io.sha256_file(freeze_path())
    assert not (benchmark_dir() / 'FAILED.json').exists()
    io.verify_hashes(t['artifact_sha256'])
    return t


def execute():
    resources(); f = frozen(); t = timing()
    stage_guard(t['development_must_detach'], 'execute')
    # Count artifacts accrued since measurement; never grow the allowance.
    current = sum(p.stat().st_size for p in artifact_files())
    assert t['projected_aggregate_bytes'] + current - t['retained_bytes_before_timing_receipt'] < q.ALLOWANCE
    assert not run_dir().exists() and not output_dir().exists()
    run_dir().mkdir(); output_dir().mkdir(); start = time.monotonic()
    try:
        io.write_json(run_dir() / 'MANIFEST.json', dict(started_utc=io.utc_now(), contract=contract(),
            freeze_sha256=io.sha256_file(freeze_path()), benchmark_sha256=io.sha256_file(timing_path()),
            input_sha256=f['input_sha256']))
        ready('execute')
        tick = time.monotonic()
        for index in dev.IDS:
            dev.write_block(output_dir(), index, 'development'); resources()
            print(json.dumps(dict(event='block_checked', index=index, utc=io.utc_now())), flush=True)
        seal = dev.seal_diagnostics(output_dir(), 'development', io.sha256_file(freeze_path()), f['input_sha256'])
        diagnostics_seconds = time.monotonic() - tick
        print(json.dumps(dict(event='ALL_DIAGNOSTICS_SEALED', blocks=seal['blocks'], utc=io.utc_now())), flush=True)
        tick = time.monotonic()
        # No actual future, fit, or forecast archive is decoded before this point.
        data = dev.development_data(output_dir(), io.sha256_file(freeze_path()), f['input_sha256'])
        old, old_raw, refs = dev.load_references()
        loaded_seconds = time.monotonic() - tick
        tick = time.monotonic(); proof = dev.write_panel(output_dir() / 'panel', data, old, old_raw, refs)
        panel_seconds = time.monotonic() - tick
        frozen(); timing(); dev.verify_seal(output_dir(), 'development', io.sha256_file(freeze_path()), f['input_sha256'])
        resources()
        result = dict(status='COMPLETE', completed_utc=io.utc_now(), seconds=time.monotonic() - start,
            diagnostics_seconds=diagnostics_seconds, source_decode_seconds=loaded_seconds, panel_seconds=panel_seconds,
            manifest_sha256=io.sha256_file(run_dir() / 'MANIFEST.json'),
            diagnostics_seal_sha256=io.sha256_file(output_dir() / 'DIAGNOSTICS_SEALED.json'),
            output_sha256=io.hashes(p for p in output_dir().rglob('*') if p.is_file()),
            output_bytes=io.size(output_dir()), aggregate_bytes_before_complete=sum(p.stat().st_size for p in artifact_files()),
            verification=proof, cases=256, diagnostic_cycles=512, independent_writer_paths=512,
            independent_reader_paths=1024, original_U1_reproductions=256,
            new_real_fits=48, reused_real_fits=144, reference_refits=0,
            new_actual_lineages=0, prospective_evidence=False, independent_saved_audit_pending=True,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        io.write_json(run_dir() / 'COMPLETE.json', result)
        return {k: v for k, v in result.items() if k != 'output_sha256'}
    except Exception as exc:
        failed(run_dir() / 'FAILED.json', exc); raise


def completed():
    assert not (run_dir() / 'FAILED.json').exists()
    done = io.read_json(run_dir() / 'COMPLETE.json')
    assert done['status'] == 'COMPLETE' and done['manifest_sha256'] == io.sha256_file(run_dir() / 'MANIFEST.json')
    manifest = io.read_json(run_dir() / 'MANIFEST.json')
    assert manifest['freeze_sha256'] == io.sha256_file(freeze_path()) and manifest['benchmark_sha256'] == io.sha256_file(timing_path())
    assert manifest['contract'] == contract()
    assert done['diagnostics_seal_sha256'] == io.sha256_file(output_dir() / 'DIAGNOSTICS_SEALED.json')
    assert set(done['output_sha256']) == {str(p) for p in output_dir().rglob('*') if p.is_file()}
    io.verify_hashes(done['output_sha256'])
    return done


def audit():
    resources(); f = frozen(); t = timing(); done = completed()
    stage_guard(2 * 16 * t['physical_seconds'] + 120 > 600, 'audit')
    assert not audit_path().exists() and not audit_path().with_suffix('.failed.json').exists()
    ready('audit'); start = time.monotonic()
    try:
        # Cold configuration imports are explicit in frozen(); no production context warm-up.
        physical = [dev.saved_block(output_dir(), i, 'development', True) for i in dev.IDS]
        data = dev.development_data(output_dir(), io.sha256_file(freeze_path()), f['input_sha256'])
        old, raw, refs = dev.load_references()
        proof = dev.check_panel(output_dir() / 'panel', data, old, raw, refs)
        dev.model_check.same(proof, done['verification'])
        dev.model_check.same(proof, io.read_json(output_dir() / 'panel/verification.json'))
        frozen(); timing(); completed(); resources()
        result = dict(passes=True, checked_utc=io.utc_now(), seconds=time.monotonic() - start,
            complete_sha256=io.sha256_file(run_dir() / 'COMPLETE.json'),
            freeze_sha256=io.sha256_file(freeze_path()), physical=physical, models=proof,
            independent_writer_paths=512, independent_reader_paths=1024,
            production_simulator_called=False, production_fitter_called=False,
            new_real_fits=0, new_actual_lineages=0, prospective_evidence=False, automatic_successor=False)
        io.write_json(audit_path(), result)
        return result
    except Exception as exc:
        failed(audit_path().with_suffix('.failed.json'), exc); raise


def detach(stage):
    resources(); f = frozen()
    if stage == 'benchmark':
        assert not benchmark_dir().exists() and not timing_path().exists()
        budget, completion = f['benchmark_budget_seconds'], timing_path()
    elif stage == 'execute':
        t = timing(); assert not run_dir().exists() and not output_dir().exists()
        budget, completion = t['conservative_development_and_audit_budget_seconds'], run_dir() / 'COMPLETE.json'
    elif stage == 'audit':
        t = timing(); completed()
        assert not audit_path().exists() and not audit_path().with_suffix('.failed.json').exists()
        budget, completion = 2 * 16 * t['physical_seconds'] + 120, audit_path()
    else:
        raise ValueError('one explicit stage only')
    log, receipt = log_path(stage), ROOT / 'logs' / (RUN + '_' + stage + '_launch.json')
    assert not log.exists() and not receipt.exists()
    read_fd, write_fd = os.pipe(); env = dict(os.environ, **{ENV: stage, READY: str(write_fd)})
    try:
        with log.open('x') as handle:
            child = subprocess.Popen([sys.executable, '-u', '-m', 'l20_extension1.feedback_pulse_development_run', stage],
                cwd=WS, env=env, stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
                start_new_session=True, pass_fds=(write_fd,))
        os.close(write_fd); write_fd = None
        readable, _, _ = select.select([read_fd], [], [], 30)
        payload = os.read(read_fd, 4096) if readable else b''
        ack = json.loads(payload) if payload else None
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
    record = dict(launched_utc=io.utc_now(), stage=stage, pid=child.pid, startup_ack=ack,
        log=str(log), completion=str(completion), budget_seconds=budget,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    io.write_json(receipt, record)
    assert ack == dict(stage=stage, pid=child.pid, status='STARTED'), 'ambiguous startup; preserve log and inspect before retry'
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('freeze', 'benchmark', 'execute', 'audit', 'detach-benchmark', 'detach-execute', 'detach-audit'))
    parser.add_argument('--xml', type=Path); parser.add_argument('--fixtures', type=Path)
    args = parser.parse_args()
    if args.stage == 'freeze':
        if args.xml is None or args.fixtures is None:
            parser.error('freeze requires --xml and --fixtures')
        result = freeze(args.xml, args.fixtures)
    else:
        if args.xml is not None or args.fixtures is not None:
            parser.error('qualification paths only belong to freeze')
        result = detach(args.stage[7:]) if args.stage.startswith('detach-') else {'benchmark': benchmark, 'execute': execute, 'audit': audit}[args.stage]()
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
