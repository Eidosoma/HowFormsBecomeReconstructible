"""D173 qualification/freeze/disposable benchmark ONLY; no development executor.

Stages are separately invoked, write-once and never start a successor.
"""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
from . import feedback_pulse as pulse, feedback_pulse_check as replay
from . import feedback_pulse_models as model, feedback_pulse_models_check as model_check
from . import settings_prediction_run as io

WS, ROOT = io.WS, io.ROOT
RUN = 'l20_extension1_feedback_pulse_qualification_v1_attempt1'
D172 = 'db3a2a783de73cd65ee46ad8a66205895081da858daea1bd8a20cdb0e7da1e24'
ALLOWANCE, RESERVE = 512 * 1024**2, 4 * 1024**3
ENV, READY = 'D173_DETACHED_STAGE', 'D173_READY_FD'
SCIENCE = ('feedback-placement-challenge/EXECUTION_PROTOCOL_V1.md',
    'src/l20_extension1/feedback_pulse.py', 'src/l20_extension1/feedback_pulse_check.py',
    'src/l20_extension1/feedback_pulse_models.py', 'src/l20_extension1/feedback_pulse_models_check.py',
    'src/l20_extension1/feedback_pulse_run.py', 'tests/test_feedback_pulse.py',
    'scripts/run_feedback_pulse.sh')
SOURCE_KEYS = ('founder_packets', 'guide', 'input', 'routed', 'outgoing', 'terminal_packet',
    'read_states', 'write_states', 'terminal_states', 'scores', 'shift', 'initial_features', 'diagnostic_features')
MODEL_FILES = ('synthetic_data.npz', 'synthetic_predictions.npz', 'synthetic_raw.npz',
    'synthetic_fits.json', 'synthetic_summary.json', 'synthetic_losses.npz', 'synthetic_verification.json')


def freeze_path(): return ROOT / 'tmp' / (RUN + '_freeze.json')
def timing_path(): return ROOT / 'tmp' / (RUN + '_benchmark.json')
def benchmark_dir(): return ROOT / 'tmp' / (RUN + '_benchmark')
def audit_path(): return ROOT / 'logs' / (RUN + '_saved_benchmark_audit_v1.json')
def log_path(stage): return ROOT / 'logs' / (RUN + '_' + stage + '.log')


def science():
    return [WS / 'L20-extension-1' / p for p in SCIENCE]


def resources():
    cpus = io.resources()
    if shutil.disk_usage(ROOT).free < RESERVE + ALLOWANCE:
        raise RuntimeError('4 GiB reserve plus 512 MiB new-artifact allowance required')
    return cpus


def contract():
    return dict(run=RUN, stages=['freeze', 'benchmark', 'audit-benchmark'],
        disposable=514240, lives=4, groups=4, branches=['U1', 'P1'],
        pulse_shift=[2, 1], pulse_bounds=[301, 400], write_times=list(pulse.WRITE_TIMES),
        readers_per_cycle=2, reader_steps=300, writer_steps=1000,
        benchmark_cycles=32, benchmark_independent_replay_cycles=32,
        synthetic_founders=16, synthetic_fits=192, new_real_fits=0,
        development_execution_available=False, actual_outcomes_accessed=False,
        allowance=ALLOWANCE, reserve=RESERVE, maximum_cpus=6, workers=1, numerical_threads=1,
        detach_above_seconds=600, automatic_polling=False, automatic_retry=False, automatic_successor=False)


def combine(result, incoming):
    for key, value in incoming.items():
        assert key not in result or result[key] == value, 'conflicting source hash: ' + key
        result[key] = value


def source_inputs():
    """Hash consumed sources; never load development measurements/outcomes."""
    receipt = ROOT / 'logs/d172_feedback_placement_design_v1.json'
    assert io.sha256_file(receipt) == D172
    design = io.read_json(receipt)
    assert design['passes'] and design['new_fits'] == design['new_dynamics'] == 0
    used = {str(receipt): D172}
    for key in ('source_sha256', 'documentation_sha256', 'newly_bound_inspected_source_sha256'):
        combine(used, design[key])
    io.verify_hashes(used)
    expected = used.copy()
    swap_manifest = ROOT / 'runs/l20_extension1_address_swap_v1_attempt1/MANIFEST.json'
    settings_freeze = ROOT / 'tmp/l20_extension1_settings_prediction_dev_v1_attempt1_freeze.json'
    for path in (swap_manifest, settings_freeze):
        assert io.sha256_file(path) == used[str(path)]
        combine(expected, io.read_json(path)['input_sha256'])
    pilot_manifest = ROOT / 'runs/l20_extension1_pilot64_v1_attempt1/MANIFEST.json'
    assert io.sha256_file(pilot_manifest) == expected[str(pilot_manifest)]
    used[str(pilot_manifest)] = expected[str(pilot_manifest)]
    combine(expected, io.read_json(pilot_manifest)['input_sha256'])
    # Materialize production physics imports, but do not generate a body or run it.
    pulse.old.context(514240)
    fresh = {p.resolve() for p in science()}
    repository = WS.parents[3]
    for module in list(sys.modules.values()):
        file = getattr(module, '__file__', None)
        if not file:
            continue
        path = Path(file).resolve()
        if path.suffix == '.py' and repository in path.parents and path not in fresh:
            assert str(path) in expected, 'unbound imported repository source: ' + str(path)
            used[str(path)] = expected[str(path)]
    io.verify_hashes(used)
    combine(used, io.hashes(science()))
    return used


def source_paths():
    stem = ROOT / 'tmp/l20_extension1_pilot64_v1_attempt1_benchmark/diagnostic_514240'
    return stem.with_suffix('.npz'), stem.with_suffix('.json')


def load_source():
    array_path, metadata_path = source_paths()
    raw = io.load_npz(array_path, SOURCE_KEYS)
    meta = io.read_json(metadata_path)
    assert meta['index'] == 514240 and len(meta['lives']) == 4
    assert raw['founder_packets'].shape == (4, 2, 2048)
    for life, row in enumerate(meta['lives']):
        assert row['index'] == row['host']['index'] == 514240 and row['life'] == life
        assert row['tag'] == pulse.namespace('disposable', 514240, life)
        assert row['cohort'] == 'disposable' and row['cases'] == [list(c) for c in pulse.CASES]
        assert row['replay']['full_dynamics_replayed']
    return raw, meta


def life(raw, index):
    return {k: v[index] for k, v in raw.items()}


def checked_life(original, metadata, index):
    source = life(original, index)
    raw, meta = pulse.simulate_life(source['founder_packets'], source['guide'], 'disposable', 514240, index)
    proof = replay.check_life(raw, meta, source, metadata['lives'][index], True)
    return raw, meta, proof


def saved_block(directory, original, metadata, full_replay):
    raw = io.load_npz(directory / 'disposable_514240.npz')
    record = io.read_json(directory / 'disposable_514240.json')
    pulse.validate(raw, 4)
    assert set(record) == {'index', 'lives', 'proofs'} and record['index'] == 514240
    assert len(record['lives']) == len(record['proofs']) == 4
    proofs = []
    for l in range(4):
        expected = replay.check_life(life(raw, l), record['lives'][l], life(original, l), metadata['lives'][l], full_replay)
        prior = record['proofs'][l]
        assert prior['full_physics_replayed'] and prior['passes']
        if not full_replay:
            expected['full_physics_replayed'] = True
            for key in ('initial_reader_max_abs', 'writer_max_abs', 'final_reader_max_abs'):
                assert 0 <= prior[key] <= 1e-10
                expected[key] = prior[key]
        replay.same(expected, prior)
        proofs.append(expected)
    return dict(passes=True, diagnostic_cycles=32, writer_paths=32, reader_paths=64,
        original_U1_reproductions=16, full_physics_replayed=full_replay,
        uncompressed_bytes=sum(x.nbytes for x in raw.values()),
        maximum_state_residual=max(p[k] for p in proofs for k in ('initial_reader_max_abs', 'writer_max_abs', 'final_reader_max_abs')))


def physical_block(directory):
    original, metadata = load_source()
    rows, entries, proofs = [], [], []
    for l in range(4):
        raw, meta, proof = checked_life(original, metadata, l)
        rows.append(raw); entries.append(meta); proofs.append(proof)
    stacked = {k: np.stack([row[k] for row in rows]) for k in pulse.SHAPES}
    io.write_npz(directory / 'disposable_514240.npz', stacked)
    io.write_json(directory / 'disposable_514240.json', dict(index=514240, lives=entries, proofs=proofs))
    saved = io.load_npz(directory / 'disposable_514240.npz')
    for key in stacked:
        np.testing.assert_array_equal(saved[key], stacked[key])
    return saved_block(directory, original, metadata, False)


def saved_synthetic(directory):
    data = io.load_npz(directory / 'synthetic_data.npz')
    assert np.array_equal(data['block_ids'], np.arange(len(data['block_ids']), dtype=np.int64))
    p = io.load_npz(directory / 'synthetic_predictions.npz')
    raw = io.load_npz(directory / 'synthetic_raw.npz')
    fits = io.read_json(directory / 'synthetic_fits.json')
    summary = io.read_json(directory / 'synthetic_summary.json')
    losses = io.load_npz(directory / 'synthetic_losses.npz')
    proof = dict(fits=model_check.check_fits(data, p, raw, fits), scores=model_check.check_summary(data, p, raw, summary, losses))
    model_check.same(proof, io.read_json(directory / 'synthetic_verification.json'))
    return proof


def synthetic_workflow(directory, n=16):
    data = model.fixture(n)
    p, raw, fits = model.synthetic_panel(data)
    summary, losses = model.summarize(data, p, raw)
    proof = dict(fits=model_check.check_fits(data, p, raw, fits), scores=model_check.check_summary(data, p, raw, summary, losses))
    for name, payload in (('synthetic_data.npz', data), ('synthetic_predictions.npz', p),
                          ('synthetic_raw.npz', raw), ('synthetic_losses.npz', losses)):
        io.write_npz(directory / name, payload)
    for name, payload in (('synthetic_fits.json', fits), ('synthetic_summary.json', summary), ('synthetic_verification.json', proof)):
        io.write_json(directory / name, payload)
    return saved_synthetic(directory)


def artifact_files():
    found = set()
    for area in ('logs', 'tmp'):
        for pattern in (RUN + '*', 'd173_feedback_pulse_qualification_v*'):
            for path in (ROOT / area).glob(pattern):
                if path.is_file() and not path.is_symlink():
                    found.add(path)
                elif path.is_dir() and not path.is_symlink():
                    found.update(p for p in path.rglob('*') if p.is_file() and not p.is_symlink())
    return sorted(found)


def qualification(xml, fixtures):
    io.external(xml); io.external(fixtures)
    assert xml.parent == ROOT / 'logs' and xml.name.startswith('d173_feedback_pulse_qualification_v') and xml.suffix == '.xml'
    assert fixtures.parent == ROOT / 'tmp' and fixtures.name == xml.stem and fixtures.is_dir()
    tree = ET.parse(xml).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 60 and not any(tree.findall('.//' + key) for key in ('failure', 'error', 'skipped'))
    assert len({(case.get('classname'), case.get('name')) for case in cases}) == len(cases)
    names = {case.get('name').split('[', 1)[0] for case in cases}
    required = {'test_complete_disposable_life', 'test_complete_synthetic_workflow', 'test_checker_independence',
        'test_original_reproduction', 'test_zero_offset_alias', 'test_order_invariance', 'test_preupdate_theta',
        'test_corruption', 'test_observer_isolation', 'test_model_checker_independence', 'test_whole_founder_exclusion',
        'test_stage_guard', 'test_startup_ack', 'test_write_once', 'test_development_unavailable'}
    assert required <= names
    times = {}
    for name, prop in (('test_complete_disposable_life', 'complete_life_seconds'),
                       ('test_complete_synthetic_workflow', 'complete_synthetic_seconds')):
        case = next(c for c in cases if c.get('name') == name)
        props = {p.get('name'): p.get('value') for p in case.findall('./properties/property')}
        times[prop] = float(props[prop]); assert 0 < times[prop] < 600
    files = [p for p in fixtures.rglob('*') if p.is_file() and not p.is_symlink()]
    assert files
    return dict(xml=str(xml), xml_sha256=io.sha256_file(xml), tests=len(cases), fixtures=str(fixtures),
        fixture_sha256=io.hashes(files), fixture_bytes=sum(p.stat().st_size for p in files), **times)


def freeze(xml, fixtures):
    resources()
    assert not any(p.exists() for p in (freeze_path(), timing_path(), benchmark_dir(), audit_path()))
    q = qualification(xml, fixtures)
    tick = time.monotonic(); sources = source_inputs(); hash_seconds = time.monotonic() - tick
    combine(sources, {str(xml): q['xml_sha256']})
    budget = 8 * q['complete_life_seconds'] + 8 * q['complete_synthetic_seconds'] + 2 * hash_seconds + 120
    assert sum(p.stat().st_size for p in artifact_files()) < ALLOWANCE
    frozen = dict(status='FROZEN_QUALIFICATION_ONLY', frozen_utc=io.utc_now(), contract=contract(),
        input_sha256=sources, qualification=q, environment=io.environment_manifest(),
        source_hash_seconds=hash_seconds, benchmark_budget_seconds=budget,
        benchmark_must_detach=budget > 600, automatic_successor=False)
    io.write_json(freeze_path(), frozen)
    return dict(status=frozen['status'], inputs=len(sources), tests=q['tests'],
        benchmark_budget_seconds=budget, benchmark_must_detach=budget > 600)


def frozen():
    value = io.read_json(freeze_path())
    assert value['status'] == 'FROZEN_QUALIFICATION_ONLY' and value['contract'] == contract()
    io.verify_hashes(value['input_sha256']); io.verify_hashes(value['qualification']['fixture_sha256'])
    assert qualification(Path(value['qualification']['xml']), Path(value['qualification']['fixtures'])) == value['qualification']
    for path in science():
        assert value['input_sha256'][str(path)] == io.sha256_file(path)
    env = io.environment_manifest()
    for key in ('python', 'numpy', 'thread_limits'):
        assert env[key] == value['environment'][key]
    return value


def stage_guard(required, stage):
    if required and os.environ.get(ENV) != stage:
        raise RuntimeError('forecast over 600 seconds requires detached launch')
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


def failed(directory, error):
    io.write_json(directory / 'FAILED.json', dict(failed_utc=io.utc_now(), error=str(error),
        traceback=traceback.format_exc(), automatic_retry=False, automatic_successor=False))


def benchmark():
    resources(); frozen_state = frozen()
    stage_guard(frozen_state['benchmark_must_detach'], 'benchmark')
    directory = benchmark_dir(); directory.mkdir(); ready('benchmark')
    started = time.monotonic()
    try:
        io.write_json(directory / 'MANIFEST.json', dict(started_utc=io.utc_now(),
            freeze_sha256=io.sha256_file(freeze_path()), contract=contract(), scientific_evidence=False))
        tick = time.monotonic(); physics = physical_block(directory); physical_seconds = time.monotonic() - tick
        tick = time.monotonic(); synthetic = synthetic_workflow(directory); synthetic_seconds = time.monotonic() - tick
        tick = time.monotonic(); frozen(); hash_seconds = time.monotonic() - tick
        files = sorted(directory.iterdir())
        fixture_bytes = sum((directory / p).stat().st_size for p in MODEL_FILES)
        current_bytes = sum(p.stat().st_size for p in artifact_files())
        projected = current_bytes + 2 * 16 * physics['uncompressed_bytes'] + 2 * fixture_bytes + 32 * 1024**2
        assert projected <= ALLOWANCE, 'measured conservative storage exceeds the fixed ceiling'
        budget = 2 * 16 * physical_seconds + 2 * synthetic_seconds + 4 * hash_seconds + 120
        result = dict(status='COMPLETE', completed_utc=io.utc_now(), seconds=time.monotonic() - started,
            physical_seconds=physical_seconds, synthetic_seconds=synthetic_seconds, source_hash_seconds=hash_seconds,
            freeze_sha256=io.sha256_file(freeze_path()), artifact_sha256=io.hashes(files),
            benchmark_bytes=sum(p.stat().st_size for p in files), retained_bytes_before_timing_receipt=current_bytes,
            conservative_development_and_audit_budget_seconds=budget, development_would_require_detachment=budget > 600,
            projected_aggregate_bytes=projected, parallel_credit_in_budget=False,
            physical=physics, synthetic=synthetic, synthetic_fits=192, actual_development_cases_simulated=0,
            new_real_fits=0, actual_outcome_arrays_loaded=0, scientific_evidence=False, automatic_successor=False)
        io.write_json(timing_path(), result)
        return {k: v for k, v in result.items() if k != 'artifact_sha256'}
    except Exception as exc:
        failed(directory, exc)
        raise


def timing():
    value = io.read_json(timing_path())
    assert value['status'] == 'COMPLETE' and value['freeze_sha256'] == io.sha256_file(freeze_path())
    assert not (benchmark_dir() / 'FAILED.json').exists()
    io.verify_hashes(value['artifact_sha256'])
    return value


def audit_benchmark():
    resources(); frozen(); t = timing()
    assert not audit_path().exists()
    stage_guard(2 * t['seconds'] + 120 > 600, 'audit-benchmark')
    ready('audit-benchmark'); started = time.monotonic()
    original, metadata = load_source()
    physics = saved_block(benchmark_dir(), original, metadata, True)
    synthetic = saved_synthetic(benchmark_dir())
    expected = dict(t['physical'], full_physics_replayed=True)
    replay.same(physics, expected); model_check.same(synthetic, t['synthetic'])
    frozen(); timing()
    result = dict(passes=True, checked_utc=io.utc_now(), seconds=time.monotonic() - started,
        benchmark_sha256=io.sha256_file(timing_path()), freeze_sha256=io.sha256_file(freeze_path()),
        physical=physics, synthetic=synthetic, production_simulator_called=False,
        production_fitter_called=False, actual_development_cases_simulated=0,
        actual_outcome_arrays_loaded=0, scientific_evidence=False, automatic_successor=False)
    io.write_json(audit_path(), result)
    return result


def detach(stage):
    resources(); f = frozen()
    if stage == 'benchmark':
        assert not benchmark_dir().exists() and not timing_path().exists()
        budget = f['benchmark_budget_seconds']; completion = timing_path()
    elif stage == 'audit-benchmark':
        t = timing(); assert not audit_path().exists()
        budget = 2 * t['seconds'] + 120; completion = audit_path()
    else:
        raise ValueError('qualification stages only')
    log = log_path(stage); receipt = ROOT / 'logs' / (RUN + '_' + stage + '_launch.json')
    assert not log.exists() and not receipt.exists()
    read_fd, write_fd = os.pipe(); env = dict(os.environ, **{ENV: stage, READY: str(write_fd)})
    try:
        with log.open('x') as handle:
            child = subprocess.Popen([sys.executable, '-u', '-m', 'l20_extension1.feedback_pulse_run', stage],
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
    result = dict(launched_utc=io.utc_now(), pid=child.pid, stage=stage, startup_ack=ack,
        log=str(log), completion=str(completion), budget_seconds=budget,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    io.write_json(receipt, result)
    assert ack == dict(stage=stage, pid=child.pid, status='STARTED'), 'ambiguous startup: keep evidence, inspect before retry'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('freeze', 'benchmark', 'audit-benchmark', 'detach-benchmark', 'detach-audit-benchmark'))
    parser.add_argument('--xml', type=Path); parser.add_argument('--fixtures', type=Path)
    args = parser.parse_args()
    if args.stage == 'freeze':
        if args.xml is None or args.fixtures is None:
            parser.error('freeze needs --xml and --fixtures')
        result = freeze(args.xml, args.fixtures)
    else:
        if args.xml is not None or args.fixtures is not None:
            parser.error('qualification arguments only belong to freeze')
        result = detach(args.stage[7:]) if args.stage.startswith('detach-') else benchmark() if args.stage == 'benchmark' else audit_benchmark()
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
