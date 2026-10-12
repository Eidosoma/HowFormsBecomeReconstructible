"""D173 disposable physics, synthetic models and launch-safety qualification."""
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace
import numpy as np
import pytest
from l20_extension1 import feedback_pulse as m, feedback_pulse_check as c
from l20_extension1 import feedback_pulse_models as models, feedback_pulse_models_check as mc
from l20_extension1 import feedback_pulse_run as run


def forbid(*args, **kwargs):
    raise AssertionError('forbidden production/development entry point')


@pytest.fixture(scope='module')
def source():
    pins = run.source_inputs()
    for p in run.source_paths():
        assert pins[str(p)] == run.io.sha256_file(p)
    return run.load_source()


@pytest.fixture(scope='module')
def one(source):
    tick = time.monotonic()
    raw, meta, proof = run.checked_life(*source, 0)
    return raw, meta, proof, time.monotonic() - tick


def test_complete_disposable_life(one, record_property):
    proof = one[2]
    assert proof['passes'] and proof['full_physics_replayed']
    assert (proof['writer_paths'], proof['reader_paths'], proof['original_U1_reproductions']) == (8, 16, 4)
    record_property('complete_life_seconds', one[3])


def test_original_reproduction(one, source):
    raw, original = one[0], run.life(source[0], 0)
    for key in ('input', 'routed', 'outgoing', 'terminal_packet', 'read_states', 'terminal_states', 'scores', 'shift', 'diagnostic_features'):
        np.testing.assert_array_equal(raw[key][:, 0], original[key][:, 1])
    np.testing.assert_array_equal(raw['write_states'][:, 0][:, [0, 1, 2, 6]], original['write_states'][:, 1])


def test_matched_prefix_and_streams(one):
    raw, meta = one[:2]
    np.testing.assert_array_equal(raw['read_states'][:, 0], raw['read_states'][:, 1])
    np.testing.assert_array_equal(raw['write_states'][:, 0, :3], raw['write_states'][:, 1, :3])
    np.testing.assert_array_equal(raw['write_states'][:, :, 0, 3], 0)
    for cells in meta['cycles']:
        for section, key in (('reader', 'birth_rng'), ('reader', 'read_rng'), ('writer', 'noise_rng'),
                             ('terminal_reader', 'birth_rng'), ('terminal_reader', 'read_rng')):
            assert cells[0][section][key] == cells[1][section][key]


@pytest.mark.parametrize('mode', ['translated', 'aligned'])
@pytest.mark.parametrize('step', [1, 300, 301, 400, 401, 1000])
def test_mapping_boundaries(mode, step):
    field = np.arange(256, dtype=float).reshape(1, 16, 16)
    y, x = np.indices((16, 16))
    for encoded in range(256):
        shift = np.array(divmod(encoded, 16), np.int64)
        base = shift if mode == 'translated' else np.zeros(2, np.int64)
        move = base + np.array([2, 1]) if 301 <= step <= 400 else base
        result = m.applied(field, mode, shift, step, True)
        np.testing.assert_array_equal(result, field[:, (y-move[0]) % 16, (x-move[1]) % 16])
        np.testing.assert_array_equal(np.sort(result.ravel()), field.ravel())


@pytest.mark.parametrize('mode', ['translated', 'aligned'])
def test_zero_offset_alias(source, one, mode):
    group = int(mode == 'aligned'); old = source[0]
    start = old['read_states'][0, group, 1, -1]
    shift = old['shift'][0, group, 1]
    ctx = m.old.context(514240)
    for pulse, offset in ((False, (2, 1)), (True, (0, 0))):
        got, _ = m.write_streams(start, ctx, m.draw('disposable', 514240, 0, 'write'), mode, shift, pulse, offset=offset)
        np.testing.assert_array_equal(got, one[0]['write_states'][group, 0])


def test_preupdate_theta():
    start = np.arange(768, dtype=float).reshape(3, 16, 16) / 700
    seen = []
    def step(v, ema, ref, applied, *args):
        seen.append(applied.copy())
        return v.copy(), ema.copy(), ref.copy()
    ctx = dict(api=dict(blueprint_step=step, original=SimpleNamespace(project_theta=lambda x, norm: x)), tissue=None, ladder=None, bp=None)
    shift = np.array([7, 4], np.int64)
    m.write_streams(start, ctx, np.random.default_rng(1), 'aligned', shift, True)
    theta = np.zeros((1, 16, 16))
    for t, value in enumerate(seen, 1):
        expected = np.roll(theta, (2, 1), (-2, -1)) if 300 < t <= 400 else theta
        np.testing.assert_array_equal(value, expected)
        theta = .999 * theta + .001 * np.tanh(start[2][None])
    assert len(seen) == 1000 and not np.array_equal(seen[300], .999 * seen[299] + .001 * np.tanh(start[2][None]))


def test_invariant_fields_and_template_geometry():
    y, x = np.indices((16, 16)); shift = np.array([14, 15], np.int64)
    for field in (np.zeros((1, 16, 16)), np.ones((1, 16, 16))):
        np.testing.assert_array_equal(m.applied(field, 'aligned', shift, 301, True), field)
    for template in (np.where(y < 8, 1., -1.), np.where(x % 8 < 4, 1., -1.)):
        changed = m.applied(template[None], 'aligned', shift, 301, True)[0]
        assert np.mean(template * changed) == .5 and np.mean((template - changed)**2) == 1
    field = np.arange(256, dtype=float).reshape(1, 16, 16)
    np.testing.assert_array_equal(m.applied(field, 'translated', shift, 301, True), field)


def test_order_invariance(one, source):
    old = run.life(source[0], 0)
    founders, guide = old['founder_packets'].copy(), old['guide'].copy()
    got, meta = m.simulate_life(founders, guide, 'disposable', 514240, 0, tuple(reversed(m.CELLS)))
    for key in got:
        np.testing.assert_array_equal(got[key], one[0][key])
    c.same(meta, one[1])
    np.testing.assert_array_equal(founders, old['founder_packets']); np.testing.assert_array_equal(guide, old['guide'])


def test_checker_independence(one, source, monkeypatch):
    for name in ('applied', 'write_streams', 'cycle', 'simulate_life', 'namespace', 'draw'):
        monkeypatch.setattr(m, name, forbid)
    for name in ('read_selected', 'write_streams', 'route', 'record', 'context', 'generator'):
        monkeypatch.setattr(m.old, name, forbid)
    for name in ('record_features', 'terminal_features'):
        monkeypatch.setattr(m.features, name, forbid)
    proof = c.check_life(one[0], one[1], run.life(source[0], 0), source[1]['lives'][0], True)
    c.same(proof, one[2])


@pytest.mark.parametrize('key', list(m.SHAPES))
def test_corruption(one, source, key):
    raw = deepcopy(one[0])
    if raw[key].dtype == np.uint8:
        raw[key].flat[-1] ^= 1
    else:
        raw[key].flat[-1] += 1 if raw[key].dtype == np.int64 else .03
    with pytest.raises((AssertionError, ValueError)):
        c.check_life(raw, one[1], run.life(source[0], 0), source[1]['lives'][0], key in ('read_states', 'write_states', 'terminal_states'))


@pytest.mark.parametrize('which', ['tag', 'pulse', 'window', 'times', 'host', 'noise', 'guide_access', 'extra', 'reordered'])
def test_metadata_corruption(one, source, which):
    meta = deepcopy(one[1])
    if which == 'tag': meta['tag'] = 'actual-lineage'
    elif which == 'pulse': meta['cycles'][0][1]['writer']['pulse_enabled'] = False
    elif which == 'window': meta['cycles'][0][1]['writer']['pulse_bounds'][0] = 300
    elif which == 'times': meta['write_times'][3] = 302
    elif which == 'host': meta['host']['tissue']['sigma'] = .4
    elif which == 'noise': meta['cycles'][0][1]['writer']['noise_rng'] = 'wrong'
    elif which == 'guide_access': meta['cycles'][0][1]['writer']['guide_access'] = True
    elif which == 'extra': meta['outcome'] = 0.
    else: meta['cycles'].reverse()
    with pytest.raises(AssertionError):
        c.check_life(one[0], meta, run.life(source[0], 0), source[1]['lives'][0], False)


@pytest.mark.parametrize('args', [('development', 89999, 0), ('development', 90016, 0), ('pilot', 100000, 0),
                                 ('disposable', 514241, 0), ('disposable', 514240, 4), ('disposable', True, 0)])
def test_illegal_identity(args):
    with pytest.raises(ValueError): m.namespace(*args)


def test_diagnostic_interface(source):
    a = run.life(source[0], 0)
    with pytest.raises(TypeError):
        m.simulate_life(a['founder_packets'], a['guide'], 'disposable', 514240, 0, outcomes=np.zeros(4))
    with pytest.raises(ValueError):
        m.simulate_life(a['founder_packets'], a['guide'], 'disposable', 514240, 0, order=m.CELLS[:-1])
    with pytest.raises(ValueError): m.draw('disposable', 514240, 0, 'g3:read')


@pytest.fixture(scope='module')
def four():
    data = models.fixture(4)
    p, raw, fits = models.synthetic_panel(data)
    summary, losses = models.summarize(data, p, raw)
    return data, p, raw, fits, summary, losses


def test_complete_synthetic_workflow(tmp_path, record_property):
    tick = time.monotonic()
    proof = run.synthetic_workflow(tmp_path, 4)
    assert proof['fits']['models_checked'] == 48 and proof['scores']['paired_rows'] == 18
    record_property('complete_synthetic_seconds', time.monotonic() - tick)


@pytest.mark.parametrize('key', ['u1', 'pulse', 'start', 'u0'])
def test_observer_isolation(key):
    data = {k: v for k, v in models.fixture(4).items() if k in models.MEASUREMENTS}
    before = models.matrices(data); changed = deepcopy(data); changed[key] += 2.
    after = models.matrices(changed)
    invariant = {'u1': ('starting', 'one_copy', 'tied:pulse'), 'pulse': ('starting', 'one_copy', 'tied:passive'),
                 'u0': ('starting',), 'start': ()}[key]
    for name in invariant: np.testing.assert_array_equal(after[name], before[name])
    for name in set(models.OBSERVERS) - set(invariant): assert not np.array_equal(after[name], before[name])


@pytest.mark.parametrize('key', ['outcomes', 'block_ids', 'q', 'shift', 'checkpoint', 'response_difference'])
def test_extra_inference_inputs(key):
    data = {k: v for k, v in models.fixture(4).items() if k in models.MEASUREMENTS}
    with pytest.raises(ValueError): models.matrices(dict(data, **{key: np.zeros(4)}))


def test_whole_founder_exclusion():
    data = models.fixture(4); _, raw, fits = models.fit_observer(data, 'tied:pulse')
    altered = deepcopy(data); altered['futures'][0] *= -1
    _, new_raw, new_fits = models.fit_observer(altered, 'tied:pulse')
    np.testing.assert_array_equal(raw[:, 0], new_raw[:, 0]); assert fits['folds'][0] == new_fits['folds'][0]
    altered = deepcopy(data); altered['pulse'][0] *= 1e3
    _, _, new_fits = models.fit_observer(altered, 'tied:pulse')
    assert fits['folds'][0] == new_fits['folds'][0]


def test_model_checker_independence(four, monkeypatch):
    data, p, raw, fits, summary, losses = four
    for name in ('fit_observer', 'matrices', 'summarize', 'paired', 'absolute'):
        monkeypatch.setattr(models, name, forbid)
    monkeypatch.setattr(models.ridge, 'fit', forbid); monkeypatch.setattr(models.tied, 'fit', forbid)
    assert mc.check_fits(data, p, raw, fits)['passes']
    assert mc.check_summary(data, p, raw, summary, losses)['passes']


@pytest.mark.parametrize('kind', ['constant', 'collinear', 'unequal_scale'])
def test_synthetic_edge_cases(kind):
    data = models.fixture(4)
    if kind == 'constant':
        for key in models.MEASUREMENTS: data[key].fill(1)
    elif kind == 'collinear':
        data['pulse'] = data['u0'].copy(); data['start'][..., 2] = data['start'][..., 1]
    else:
        data['u0'] *= 100; data['pulse'] /= 100
    p, raw, fits = models.synthetic_panel(data)
    assert mc.check_fits(data, p, raw, fits)['passes']
    summary, loss = models.summarize(data, p, raw)
    assert mc.check_summary(data, p, raw, summary, loss)['passes']


def test_clipping_and_raw_tie():
    data = models.fixture(4); data['start'][0, ..., 0] *= 1000
    p, raw, fits = models.synthetic_panel(data)
    assert any(np.any(p[k] != raw[k]) for k in p)
    assert mc.check_fits(data, p, raw, fits)['passes']
    summary, loss = models.summarize(data, p, raw)
    assert mc.check_summary(data, p, raw, summary, loss)['passes']


@pytest.mark.parametrize('which', ['coefficient', 'scale', 'offset', 'training_ids', 'validation_id', 'raw', 'clipped', 'loss', 'summary'])
def test_prediction_corruption(four, which):
    data, p, raw, fits, summary, losses = deepcopy(four)
    name = 'tied:pulse'; fold = fits[name]['folds'][0]; model = fold['models'][1]
    if which == 'coefficient': model['coefficients'][0][7] += .1
    elif which == 'scale': model['scale'][7] += .1
    elif which == 'offset': model['offsets'][0] += .1
    elif which == 'training_ids': fold['training_blocks'][0] = fold['validation_block']
    elif which == 'validation_id': fold['validation_block'] += 1
    elif which == 'raw': raw[name][1, 0, 0, 0] += .1
    elif which == 'clipped': p[name][1, 0, 0, 0] += .1
    elif which == 'loss': losses[name][1, 0, 0, 0] += .1
    else: summary['comparisons'][0]['gain'] += .1
    with pytest.raises(AssertionError):
        if which in ('loss', 'summary'): mc.check_summary(data, p, raw, summary, losses)
        else: mc.check_fits(data, p, raw, fits)


def test_target_and_reference_guards():
    data = models.fixture(4)
    with pytest.raises(ValueError): models.validate(dict(data, labels=np.zeros((4, 4, 4))))
    data['block_ids'] += 90000
    with pytest.raises(ValueError): models.synthetic_panel(data)


def test_roundtrip(one, source, tmp_path):
    run.io.write_npz(tmp_path / 'one.npz', one[0]); run.io.write_json(tmp_path / 'one.json', one[1])
    raw = run.io.load_npz(tmp_path / 'one.npz'); meta = run.io.read_json(tmp_path / 'one.json')
    assert c.check_life(raw, meta, run.life(source[0], 0), source[1]['lives'][0], False)['passes']


def test_write_once(tmp_path):
    path = tmp_path / 'receipt.json'; run.io.write_json(path, {'preserve': True})
    with pytest.raises(FileExistsError): run.io.write_json(path, {'preserve': False})
    assert run.io.read_json(path) == {'preserve': True}


def test_external_only():
    with pytest.raises(ValueError): run.io.external(run.WS / 'unwanted_output.json')


def test_stage_guard(monkeypatch):
    monkeypatch.delenv(run.ENV, raising=False)
    run.stage_guard(False, 'benchmark')
    with pytest.raises(RuntimeError): run.stage_guard(True, 'benchmark')
    monkeypatch.setenv(run.ENV, 'audit-benchmark')
    with pytest.raises(RuntimeError): run.stage_guard(True, 'benchmark')


def test_startup_ack(monkeypatch):
    reader, writer = os.pipe(); monkeypatch.setenv(run.READY, str(writer))
    try:
        run.ready('benchmark')
        assert json.loads(os.read(reader, 4096)) == dict(stage='benchmark', pid=os.getpid(), status='STARTED')
        assert run.READY not in os.environ
    finally:
        os.close(reader)


@pytest.mark.parametrize('acknowledged', [True, False])
def test_detached_launcher(tmp_path, monkeypatch, acknowledged):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    (tmp_path / 'logs').mkdir(); (tmp_path / 'tmp').mkdir()
    monkeypatch.setattr(run, 'resources', lambda: None)
    monkeypatch.setattr(run, 'frozen', lambda: dict(benchmark_budget_seconds=720))
    calls = []
    def launch(argv, **kwargs):
        calls.append((argv, kwargs))
        assert kwargs['start_new_session'] and kwargs['stdin'] == subprocess.DEVNULL
        assert kwargs['stderr'] == subprocess.STDOUT and kwargs['cwd'] == run.WS
        assert argv[-1] == 'benchmark' and kwargs['env'][run.ENV] == 'benchmark'
        if acknowledged:
            os.write(kwargs['pass_fds'][0], json.dumps(dict(stage='benchmark', pid=42424, status='STARTED')).encode())
        return SimpleNamespace(pid=42424)
    monkeypatch.setattr(run.subprocess, 'Popen', launch)
    if acknowledged:
        result = run.detach('benchmark'); assert result['startup_ack']['pid'] == 42424
    else:
        with pytest.raises(AssertionError): run.detach('benchmark')
    receipt = tmp_path / 'logs' / (run.RUN + '_benchmark_launch.json')
    assert receipt.is_file() and len(calls) == 1
    with pytest.raises(AssertionError): run.detach('benchmark')
    assert len(calls) == 1


@pytest.mark.parametrize('stage', ['execute', 'development', 'fit', 'all'])
def test_development_unavailable(monkeypatch, stage):
    monkeypatch.setattr(run.sys, 'argv', ['feedback_pulse_run', stage])
    monkeypatch.setattr(run, 'resources', forbid)
    with pytest.raises(SystemExit) as exc: run.main()
    assert exc.value.code == 2


def test_no_actual_loader():
    code = inspect.getsource(run)
    assert 'def development_data' not in code
    assert 'io.development_data(' not in code
    assert 'lineage_' not in inspect.getsource(run.load_source)
    assert not run.contract()['development_execution_available']


@pytest.mark.parametrize('key', ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'PYTHONDONTWRITEBYTECODE'])
def test_resource_limits(monkeypatch, key):
    monkeypatch.setenv(key, '2')
    with pytest.raises(RuntimeError): run.resources()
