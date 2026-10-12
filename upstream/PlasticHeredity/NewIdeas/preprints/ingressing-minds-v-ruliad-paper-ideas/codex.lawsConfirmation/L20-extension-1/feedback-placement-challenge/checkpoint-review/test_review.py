"""Synthetic qualification only; no real checkpoint/outcome access."""
import inspect
from pathlib import Path
import numpy as np
import pytest
import measure as m
import verify as v
import workflow as w


@pytest.mark.parametrize('kind', ('equal', 'offset', 'scale', 'reverse', 'constant', 'one_constant'))
def test_pair_algebra(kind):
    u = np.arange(256, dtype=float).reshape(16, 16)/100
    p = {'equal': u, 'offset': u+3, 'scale': u*2, 'reverse': -u,
         'constant': np.zeros((16, 16)), 'one_constant': u}[kind].copy()
    if kind == 'constant': u = p.copy()
    if kind == 'one_constant': u = np.zeros((16, 16))
    got, valid = m.paired(u, p); want, flag = v.direct_pair(u, p)
    np.testing.assert_allclose(got, want, atol=1e-12, rtol=0); assert valid == flag
    if kind in ('equal', 'offset', 'scale'): assert got[3] < 1e-12
    if kind == 'reverse': assert got[3] == pytest.approx(2)
    if 'constant' in kind: assert not valid and got[3] == 0


@pytest.mark.parametrize('role', (0, 1))
def test_all_256_addresses(role):
    deltas = set()
    for y in range(16):
        for x in range(16):
            assert m.geometry(role, (y, x)) == v.q(role, (y, x))
            before = m.geometry(role, (y, x)); after = m.geometry(role, (y+2, x+1))
            assert after == v.q(role, (y+2, x+1)); deltas.add(after-before)
    assert deltas <= {-.5, 0, .5}
    assert m.geometry(role, (2, 1))-m.geometry(role, (0, 0)) == -.5


@pytest.fixture
def raw(): return w.synthetic(175)


def test_full_block(raw):
    got = m.extract(raw); assert v.block(raw, got)['passes']
    np.testing.assert_array_equal(got['distance'][:, :, :12, 0], 0)
    assert not got['shape_valid'][:, :, 3].any()
    assert got['shape_valid'][:, :, :3].all()


@pytest.mark.parametrize('key', ('input', 'routed', 'read_states', 'shift', 'prefix', 'birth', 'outgoing', 'terminal_packet', 'terminal_feature'))
def test_bridge_corruption(raw, key):
    if key in ('input', 'routed'): raw[key][0, 0, 1, 0] = 1
    elif key == 'read_states': raw[key][0, 0, 1, 0, 0, 0, 0] = 1
    elif key == 'shift': raw[key][0, 0, 1, 0] = (int(raw[key][0, 0, 1, 0])+1) % 16
    elif key == 'prefix': raw['write_states'][0, 0, 1, 2, 0, 0, 0] += .1
    elif key == 'birth': raw['terminal_states'][0, 0, 1, 0, 0, 0, 0] += .1
    elif key in ('outgoing', 'terminal_packet'): raw[key][0, 0, 1, 7] ^= 4
    else: raw['diagnostic_features'][0, 0, 1, 4] += .1
    with pytest.raises(AssertionError): m.extract(raw)


@pytest.mark.parametrize('key', ('distance', 'shape_valid', 'entry', 'q', 'endpoint', 'routing'))
def test_independent_metric_corruption(raw, key):
    got = m.extract(raw)
    if key == 'shape_valid': got[key][0, 0, 0] = False
    else: got[key].flat[0] += .5 if got[key].dtype == np.float64 else 1
    with pytest.raises(AssertionError): v.block(raw, got)


def panel(raw):
    return w.stack([m.extract(raw) for _ in range(16)])


def test_complete_summary(raw):
    arrays = panel(raw); report = m.summary(arrays)
    assert v.summary(arrays, report)['passes']
    assert len(report['groups']) == 4 and report['cases'] == 256
    assert all(sum(x['n'] for x in g['geometry']) == 64 for g in report['groups'])
    assert report['groups'][1]['geometry'][0]['n'] == 64
    assert report['groups'][1]['geometry'][1]['means'] is None


@pytest.mark.parametrize('mode,expected', (('zero', None), ('decay', .25), ('grow', 2.), ('persist', 1.)))
def test_recovery_ratios(raw, mode, expected):
    arrays = panel(raw)
    arrays['distance'][..., 18, 0] = 0 if mode == 'zero' else 2
    arrays['distance'][..., 26, 0] = 0 if mode == 'zero' else 2*expected
    report = m.summary(arrays); v.summary(arrays, report)
    for group in report['groups']:
        assert group['recovery'][2]['rms_ratio'] == expected
        assert group['recovery'][2]['zero_denominators'] == (64 if mode == 'zero' else 0)


@pytest.mark.parametrize('where', ('stage', 'founder', 'recovery', 'endpoint', 'geometry', 'route'))
def test_summary_corruption(raw, where):
    arrays = panel(raw); report = m.summary(arrays); g = report['groups'][0]
    if where == 'stage': g['stages'][0]['mean_delta'] += 1
    elif where == 'founder': g['stages'][0]['founders'][0]['rms_delta'] += 1
    elif where == 'recovery': g['recovery'][0]['rms_ratio'] += 1
    elif where == 'endpoint': g['endpoint'][0]['negative'] += 1
    elif where == 'geometry': next(x for x in g['geometry'] if x['n'])['means'][0] += 1
    else: g['route']['shift_switch'] += 1
    with pytest.raises(AssertionError): v.summary(arrays, report)


def test_case_axis_and_count(raw):
    arrays = panel(raw)
    arrays['distance'] = arrays['distance'][:8]
    with pytest.raises(AssertionError): m.summary(arrays)
    with pytest.raises(AssertionError): w.stack([m.extract(raw)]*15)


@pytest.mark.parametrize('index', (75000, 90016, 100000, '90000', None))
def test_forbidden_cohorts(index):
    with pytest.raises(AssertionError): w.load_block(index, {})


def test_forbidden_arrays_and_nonfinite(raw):
    bad = dict(raw, futures=np.zeros(1))
    with pytest.raises(AssertionError): m.extract(bad)
    raw['write_states'].flat[0] = np.nan
    with pytest.raises(AssertionError): m.extract(raw)


def test_write_once_and_corruption(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'ROOT', tmp_path)
    p = tmp_path / 'outputs' / w.RUN / 'sample.json'
    w.save_json(p, {'a': 1}); pins = w.hashes([p]); w.verify_hashes(pins)
    with pytest.raises(FileExistsError): w.save_json(p, {'a': 2})
    wrong = {str(p): '0'*64}
    with pytest.raises(AssertionError): w.verify_hashes(wrong)
    with pytest.raises(AssertionError): w.write(Path('/tmp/outside_d175_scope.json'), b'no')


def test_roundtrip(tmp_path, monkeypatch, raw):
    monkeypatch.setattr(w, 'ROOT', tmp_path)
    p = tmp_path / 'tmp' / w.RUN / 'metrics.npz'
    got = m.extract(raw); w.save_npz(p, got); back = w.npz(p, got)
    for key in got: np.testing.assert_array_equal(got[key], back[key])
    assert v.block(raw, back)['passes']
    with pytest.raises(AssertionError): w.npz(p, (*got, 'outcomes'))


def test_no_scientific_imports_or_evaluators():
    source = inspect.getsource(w) + inspect.getsource(m) + inspect.getsource(v)
    for forbidden in ('import torch', 'from laws_confirmation', 'from l20_extension1', 'scipy.optimize', '.fit(', 'blueprint_step('):
        assert forbidden not in source
    assert set(w.PINS) == {w.ROOT/'tmp'/(w.OLD+'_freeze.json'), w.ROOT/'runs'/w.OLD/'COMPLETE.json',
        w.ROOT/'logs'/(w.OLD+'_saved_audit_v1.json'), w.SOURCE/'DIAGNOSTICS_SEALED.json'}
