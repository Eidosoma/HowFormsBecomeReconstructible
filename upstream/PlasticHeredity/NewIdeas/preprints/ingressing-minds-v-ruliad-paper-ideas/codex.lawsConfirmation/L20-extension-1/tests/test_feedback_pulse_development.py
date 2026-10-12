"""D174 orchestration qualification: disposable/synthetic data only."""
import copy
import inspect
import io as memory
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
import numpy as np
import pytest
from l20_extension1 import feedback_pulse_development as d
from l20_extension1 import feedback_pulse_development_run as run


def forbidden(*args, **kwargs):
    raise AssertionError('forbidden production/outcome access')


@pytest.fixture(scope='module')
def wrapped(tmp_path_factory):
    run.cold.prepare()
    directory = tmp_path_factory.mktemp('complete_wrapper')
    inputs = d.qualified.frozen()['input_sha256']
    proof = run.wrapper_benchmark(directory, inputs, 'synthetic-qualification-freeze')
    return directory, inputs, proof


@pytest.fixture(scope='module')
def references():
    data, p, raw, fits = d.synthetic_sources()
    cheap, cp, cr = {}, {}, {}
    for name in d.REFERENCES[:2]:
        cheap[name] = dict(blocks=list(range(16)), alphas=list(d.model.ALPHAS),
            training_targets=['original', 'future0', 'future1', 'future2', 'future3', 'future_mean'],
            folds=[dict(validation_block=f['validation_block'], training_blocks=f['training_blocks'],
                        models=[['wrong target']] * 5 + [copy.deepcopy(f['models'])]) for f in fits[name]['folds']])
        cp[name] = np.stack([np.full_like(p[name], -.9)] * 5 + [p[name]])
        cr[name] = np.stack([np.full_like(raw[name], -.9)] * 5 + [raw[name]])
    return data, p, raw, fits, (cheap, cp, cr, {'tied:passive': fits['tied:passive']},
        {'tied:passive': p['tied:passive']}, {'tied:passive': raw['tied:passive']})


def test_complete_wrapper_benchmark(wrapped, record_property):
    directory, inputs, proof = wrapped
    assert proof['physical']['original_U1_reproductions'] == 16
    assert proof['saved_replay']['full_physics_replayed']
    assert proof['physical']['maximum_state_residual'] == proof['saved_replay']['maximum_state_residual'] == 0
    assert proof['synthetic']['fits']['models_checked'] == 192
    assert proof['new_real_fits'] == proof['actual_future_arrays_loaded'] == 0
    assert proof['new_synthetic_fits'] == 48
    assert d.verify_seal(directory, 'disposable', 'synthetic-qualification-freeze', inputs)['diagnostic_cycles'] == 32
    record_property('physical_seconds', proof['physical_seconds'])
    record_property('synthetic_seconds', proof['synthetic_seconds'])


def test_reference_normalization(references):
    data, p, raw, fits, args = references
    pp, rr, ff = d.normalize_references(*args, list(range(16)))
    for name in d.REFERENCES:
        np.testing.assert_array_equal(pp[name], p[name]); np.testing.assert_array_equal(rr[name], raw[name])
        assert ff[name] == fits[name]


@pytest.mark.parametrize('error', ['target', 'alpha', 'blocks', 'fold', 'training', 'models', 'shape', 'raw', 'nonfinite', 'tied_target'])
def test_wrong_reference(references, error):
    args = copy.deepcopy(references[-1]); cheap, cp, cr, tied, tp, tr = args
    if error == 'target': cheap['starting']['training_targets'][-1] = 'original'
    if error == 'alpha': cheap['starting']['alphas'][1] = .02
    if error == 'blocks': cheap['starting']['blocks'].reverse()
    if error == 'fold': cheap['starting']['folds'][0]['validation_block'] = 1
    if error == 'training': cheap['starting']['folds'][0]['training_blocks'].append(0)
    if error == 'models': cheap['starting']['folds'][0]['models'][5].pop()
    if error == 'shape': cp['starting'] = cp['starting'][0]
    if error == 'raw': cr['starting'][5, 0, 0, 0, 0] += .1
    if error == 'nonfinite': tr['tied:passive'][0, 0, 0, 0] = np.nan
    if error == 'tied_target': tied['tied:passive']['target'] = 'original'
    with pytest.raises((AssertionError, ValueError)):
        d.normalize_references(*args, list(range(16)))


@pytest.mark.parametrize('error', ['cohort', 'blocks', 'missing', 'cases', 'cycles', 'future', 'fits',
    'freeze', 'source', 'hash', 'proof_count', 'proof_index', 'replay', 'residual', 'U1', 'extra'])
def test_seal_corruption(wrapped, monkeypatch, error):
    directory, inputs, _ = wrapped; path = directory / 'DIAGNOSTICS_SEALED.json'
    original = d.io.read_json; value = copy.deepcopy(original(path))
    if error == 'cohort': value['cohort'] = 'development'
    if error == 'blocks': value['blocks'] = [90000]
    if error == 'missing': value['artifact_sha256'].pop(next(iter(value['artifact_sha256'])))
    if error == 'cases': value['cases'] -= 1
    if error == 'cycles': value['diagnostic_cycles'] -= 1
    if error == 'future': value['actual_future_arrays_loaded'] = True
    if error == 'fits': value['new_fits'] = 1
    if error == 'freeze': value['freeze_sha256'] = 'wrong'
    if error == 'source': value['source_sha256'] = {}
    if error == 'hash': value['artifact_sha256'][next(iter(value['artifact_sha256']))] = '0' * 64
    if error == 'proof_count': value['proofs'] = []
    if error == 'proof_index': value['proofs'][0]['index'] = 90000
    if error == 'replay': value['proofs'][0]['in_memory_full_replay_passed'] = False
    if error == 'residual': value['proofs'][0]['maximum_state_residual'] = 1e-5
    if error == 'U1': value['proofs'][0]['original_U1_reproductions'] = 15
    if error == 'extra': value['extra'] = True
    monkeypatch.setattr(d.io, 'read_json', lambda p: value if Path(p) == path else original(p))
    with pytest.raises(AssertionError):
        d.verify_seal(directory, 'disposable', 'synthetic-qualification-freeze', inputs)


@pytest.mark.parametrize('state', ['missing', 'disposable', 'wrong_freeze'])
def test_outcome_gate(wrapped, tmp_path, monkeypatch, state):
    directory, inputs, _ = wrapped
    monkeypatch.setattr(d, 'load_npz', forbidden)
    with pytest.raises((AssertionError, FileNotFoundError)) as caught:
        d.development_data(tmp_path if state == 'missing' else directory,
            'wrong' if state == 'wrong_freeze' else 'synthetic-qualification-freeze', inputs)
    assert 'forbidden production/outcome access' not in str(caught.value)


def test_outcome_order_and_features(references, tmp_path, monkeypatch):
    fixture = copy.deepcopy(references[0]); fixture['block_ids'] = np.array(d.IDS, np.int64)
    endpoint = np.stack([fixture['u0'], fixture['u1'], np.zeros_like(fixture['u1'])], axis=3)
    events = []
    def seal(*args):
        events.append('complete_seal_verified')
    def loader(path, keys):
        assert events[0] == 'complete_seal_verified'
        if Path(path).name == 'dataset.npz':
            events.append('future_arrays_loaded')
            assert keys == ('start', 'endpoint', 'futures', 'block_ids')
            return dict(start=fixture['start'], endpoint=endpoint, futures=fixture['futures'], block_ids=fixture['block_ids'])
        b = d.IDS.index(int(Path(path).stem.split('_')[-1]))
        if keys == ('diagnostic_features',): return dict(diagnostic_features=endpoint[b])
        assert keys == ('starting_features', 'diagnostic_features')
        return dict(starting_features=fixture['start'][b],
            diagnostic_features=np.stack([fixture['u1'][b], fixture['pulse'][b]], axis=2))
    monkeypatch.setattr(d, 'verify_seal', seal); monkeypatch.setattr(d, 'load_npz', loader)
    monkeypatch.setattr(d.io, 'sha256_file', lambda path: 'frozen')
    data = d.development_data(tmp_path, 'freeze', {str(d.ROOT / 'outputs' / d.io.OLD157 / 'dataset.npz'): 'frozen'})
    assert events == ['complete_seal_verified', 'future_arrays_loaded']
    for key in fixture: np.testing.assert_array_equal(data[key], fixture[key])


def test_only_pulse_fit(references, tmp_path, monkeypatch):
    data, p, raw, fits, _ = references; calls = []; old = d.model.fit_observer
    snapshot = copy.deepcopy(fits)
    def counted(data, name):
        calls.append(name); assert name == 'tied:pulse'; return old(data, name)
    monkeypatch.setattr(d.model, 'fit_observer', counted)
    proof = d.write_panel(tmp_path / 'panel', data, p, raw, fits)
    assert calls == ['tied:pulse'] and proof['new_models'] == 48 and proof['reused_models'] == 144
    assert fits == snapshot


def test_panel_checker_independence(wrapped, references, monkeypatch):
    directory, _, _ = wrapped; data, p, raw, fits, _ = references
    monkeypatch.setattr(d.model, 'fit_observer', forbidden)
    monkeypatch.setattr(d.model.ridge, 'fit', forbidden); monkeypatch.setattr(d.model.tied, 'fit', forbidden)
    monkeypatch.setattr(d.pulse, 'simulate_life', forbidden); monkeypatch.setattr(d.pulse.old, 'context', forbidden)
    assert d.check_panel(directory / 'panel', data, p, raw, fits)['passes']


def test_cold_saved_replay(wrapped, tmp_path):
    directory, _, _ = wrapped
    program = '''
import json, sys
from pathlib import Path
from l20_extension1 import feedback_pulse_development as d, feedback_pulse_cold_audit as cold
def forbidden(*a, **k): raise AssertionError('production function called')
d.pulse.simulate_life = d.pulse.write_streams = d.pulse.old.context = forbidden
d.model.fit_observer = d.model.ridge.fit = d.model.tied.fit = forbidden
cold.checked_support(); cold.prepare()
directory = Path(sys.argv[1])
proof = d.saved_block(directory, 514240, 'disposable', True)
data, p, raw, fits = d.synthetic_sources()
panel = d.check_panel(directory / 'panel', data, p, raw, fits)
print(json.dumps(dict(physical=proof, panel=panel)))
'''
    env = dict(os.environ, PYTHONPATH='L20-extension-1/src:src')
    result = subprocess.run([sys.executable, '-c', program, str(directory)], cwd=run.WS,
        env=env, capture_output=True, text=True, timeout=90)
    d.io.write_bytes(tmp_path / 'cold_stdout.log', result.stdout.encode())
    d.io.write_bytes(tmp_path / 'cold_stderr.log', result.stderr.encode())
    assert result.returncode == 0, result.stderr
    proof = json.loads(result.stdout)
    assert proof['physical']['full_physics_replayed'] and proof['physical']['maximum_state_residual'] == 0
    assert proof['panel']['fits']['models_checked'] == 192


@pytest.mark.parametrize('required,env', [(True, None), (True, 'audit'), (True, 'benchmark')])
def test_stage_guard(monkeypatch, required, env):
    monkeypatch.delenv(run.ENV, raising=False)
    if env: monkeypatch.setenv(run.ENV, env)
    with pytest.raises(RuntimeError): run.stage_guard(required, 'execute')


def test_stage_guard_attached_short(monkeypatch):
    monkeypatch.delenv(run.ENV, raising=False); run.stage_guard(False, 'benchmark')


@pytest.mark.parametrize('error', ['session', 'stdin', 'stdout', 'stderr'])
def test_detached_descriptor_guard(monkeypatch, error):
    monkeypatch.setenv(run.ENV, 'execute')
    monkeypatch.setattr(run.os, 'getpid', lambda: 123)
    monkeypatch.setattr(run.os, 'getsid', lambda pid: 124 if error == 'session' else 123)
    values = {'/proc/self/fd/0': '/dev/null', '/proc/self/fd/1': str(run.log_path('execute')),
              '/proc/self/fd/2': str(run.log_path('execute'))}
    if error != 'session': values['/proc/self/fd/' + {'stdin': '0', 'stdout': '1', 'stderr': '2'}[error]] = '/wrong'
    monkeypatch.setattr(run.os, 'readlink', lambda path: values[path])
    with pytest.raises(AssertionError): run.stage_guard(True, 'execute')


def test_startup_ack(monkeypatch):
    reader, writer = os.pipe(); monkeypatch.setenv(run.READY, str(writer))
    try:
        run.ready('execute')
        assert json.loads(os.read(reader, 4096)) == dict(stage='execute', pid=os.getpid(), status='STARTED')
        assert run.READY not in os.environ
    finally:
        os.close(reader)


def test_detach_ack_without_polling(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path); (tmp_path / 'logs').mkdir()
    monkeypatch.setattr(run, 'resources', lambda: [0])
    monkeypatch.setattr(run, 'frozen', lambda: {})
    monkeypatch.setattr(run, 'timing', lambda: dict(conservative_development_and_audit_budget_seconds=1000))
    calls = []
    class Child:
        pid = 12345
        poll = wait = forbidden
    def launch(command, **kw):
        calls.append(command)
        assert kw['stdin'] == subprocess.DEVNULL and kw['start_new_session']
        assert kw['stderr'] == subprocess.STDOUT
        assert kw['env'][run.ENV] == 'execute'
        os.write(kw['pass_fds'][0], json.dumps(dict(stage='execute', pid=Child.pid, status='STARTED')).encode())
        return Child()
    monkeypatch.setattr(run.subprocess, 'Popen', launch)
    proof = run.detach('execute')
    assert len(calls) == 1 and proof['startup_ack']['status'] == 'STARTED'
    assert not proof['automatic_polling'] and not proof['automatic_successor']
    with pytest.raises(AssertionError): run.detach('execute')
    assert len(calls) == 1


@pytest.mark.parametrize('name', ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
    'PYTHONDONTWRITEBYTECODE', 'TMPDIR', 'XDG_CACHE_HOME'])
def test_resources(monkeypatch, name):
    monkeypatch.setenv(name, '2' if name.endswith('THREADS') else '/tmp' if name.endswith('DIR') or name.endswith('HOME') else '0')
    with pytest.raises(RuntimeError): run.resources()


def test_resource_cpu_limit(monkeypatch):
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: set(range(7)))
    with pytest.raises(RuntimeError): run.resources()


def test_pytest_alias_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    monkeypatch.setattr(run.q, 'artifact_files', lambda: [])
    root = tmp_path / 'tmp/d174_feedback_pulse_development_v99'
    target = root / 'sample0'; target.mkdir(parents=True)
    d.io.write_json(target / 'retained.json', {'one': 1})
    alias = root / 'samplecurrent'; alias.symlink_to(target, target_is_directory=True)
    run.pytest_alias(root, alias)
    assert run.artifact_files() == [target / 'retained.json']
    with pytest.raises(AssertionError): run.pytest_alias(tmp_path / 'outputs', alias)
    with pytest.raises(AssertionError): run.pytest_alias(root, target)


def test_resource_inventory_after_qualification(wrapped):
    assert run.resources() == sorted(os.sched_getaffinity(0))
    assert all(not p.is_symlink() for p in run.artifact_files())


def test_write_once(tmp_path):
    path = tmp_path / 'once.json'; d.io.write_json(path, {'once': True})
    with pytest.raises(FileExistsError): d.io.write_json(path, {'once': False})
    assert d.io.read_json(path) == {'once': True}


def test_external_only():
    with pytest.raises(ValueError): d.io.write_json(run.WS / 'not-an-output.json', {})


def test_duplicate_npz(tmp_path):
    array = memory.BytesIO(); np.save(array, np.array([1]))
    archive = memory.BytesIO()
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('a.npy', array.getvalue())
        with pytest.warns(UserWarning): z.writestr('a.npy', array.getvalue())
    path = tmp_path / 'duplicate.npz'; d.io.write_bytes(path, archive.getvalue())
    with pytest.raises(AssertionError): d.load_npz(path)


def test_source_binding(monkeypatch):
    monkeypatch.setattr(np, 'load', forbidden)
    inputs = run.source_inputs()
    for index in d.IDS:
        for path in d.source_paths(index): assert str(path) in inputs
    assert all(str(path) in inputs for path in run.science())
    assert inputs[str(run.q.freeze_path())] == run.cold.FREEZE_SHA


def test_no_successor():
    assert not run.contract()['automatic_successor'] and not run.contract()['automatic_polling']
    for function in (run.execute, run.benchmark, run.audit):
        text = inspect.getsource(function)
        assert 'detach(' not in text and 'sleep(' not in text and 'Popen(' not in text
    assert 'poll(' not in inspect.getsource(run.detach) and 'wait(' not in inspect.getsource(run.detach)
    assert run.contract()['new_actual_lineages'] == run.contract()['reference_refits'] == 0
