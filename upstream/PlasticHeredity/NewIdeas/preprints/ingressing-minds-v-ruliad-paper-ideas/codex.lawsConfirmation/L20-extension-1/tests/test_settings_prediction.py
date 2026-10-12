"""D171 synthetic qualification. Run with external --basetemp and JUnit paths."""
import copy
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from l20_extension1 import settings_prediction as m
from l20_extension1 import settings_prediction_check as c
from l20_extension1 import settings_prediction_run as r


@pytest.fixture(scope='module')
def panel():
    data = m.fixture(4); old, old_raw, refs = m.fit_all(data, False)
    new, raw, fits = m.fit_all(data)
    return data, old, old_raw, refs, new, raw, fits


def test_small_audit(tmp_path):
    data = m.fixture(4); old, raw, refs = m.fit_all(data, False)
    proof, hashes = r.write_experiment(tmp_path / 'small', data, old, raw, refs)
    assert proof['passes'] and proof['fits']['new_svd_solutions_checked'] == 84
    r.verify_hashes(hashes)


def test_all_shifts():
    s = np.zeros((256, 4, 4, 2, 2), dtype=np.int64)
    for i, (dy, dx) in enumerate(np.ndindex(16, 16)):
        s[i, ...] = (dy, dx)
    np.testing.assert_array_equal(m.effective_q(s), c.rolled_q(s))
    assert len(np.unique(m.effective_q(s)[:, 0, 0, 0])) == 9
    assert len(np.unique(m.effective_q(s)[:, 0, 2, 0])) == 5


def test_aligned_unused_shift(panel):
    d = copy.deepcopy(panel[0]); original = m.effective_q(d['shifts'])
    d['shifts'][:, :, (1, 3)] = (d['shifts'][:, :, (1, 3)] + 3) % 16
    np.testing.assert_array_equal(m.effective_q(d['shifts']), original)


@pytest.mark.parametrize('key', ['labels', 'futures', 'block_ids', 'parent', 'third', 'U1_minus_C1', 'actual_lineage_shift'])
def test_feature_boundary(panel, key):
    d = panel[0]
    inputs = dict(start=d['start'], q=m.effective_q(d['shifts']), u0=d['endpoint'][..., 0, :], second=d['endpoint'][..., 1, :])
    inputs[key] = np.zeros(1)
    with pytest.raises(ValueError): m.observer_features('tied:passive', inputs)
    measurements = {k: d[k] for k in m.MEASUREMENTS}; measurements[key] = np.zeros(1)
    with pytest.raises(ValueError): m.panels(measurements)


@pytest.mark.parametrize('name', m.OBSERVERS)
def test_fixed_dimensions(panel, name):
    d = panel[0]; a = m.panels({k: d[k] for k in m.MEASUREMENTS}); b = c.features(d, False)
    expected = 9 if name == 'starting' else 15 if name == 'one_copy' else 21
    assert a[name].shape[-1] == expected
    np.testing.assert_array_equal(a[name][..., :-2], b[name])
    np.testing.assert_array_equal(a[name][..., -2:], m.effective_q(d['shifts']))


def test_unobserved_reading_isolation(panel):
    d = copy.deepcopy(panel[0]); before = m.panels({k: d[k] for k in m.MEASUREMENTS})
    d['endpoint'][..., 2, :] += 17; d['targeted'] += 31
    after = m.panels({k: d[k] for k in m.MEASUREMENTS})
    for k in ('starting', 'one_copy', 'tied:passive'):
        np.testing.assert_array_equal(before[k], after[k])
    assert not np.array_equal(before['tied:shuffle'], after['tied:shuffle'])


def test_no_hidden_raw_difference(panel):
    d, _, _, _, _, _, fits = panel
    x = m.panels({k: d[k] for k in m.MEASUREMENTS})['tied:passive'][0].reshape(16, 21)
    moved = x.copy(); moved[:, 7:13] += 3.7; moved[:, 13:19] -= 3.7
    groups = np.tile(np.arange(4, dtype=np.int64), 4)
    for model in fits['tied:passive']['folds'][0]['models']:
        np.testing.assert_allclose(m.raw_predict(model, x, groups), m.raw_predict(model, moved, groups), atol=2e-13)


@pytest.mark.parametrize('key', m.MEASUREMENTS)
def test_missing_inputs(panel, key):
    d = {k: v for k, v in panel[0].items() if k != key}
    with pytest.raises(ValueError): m.validate(d)


@pytest.mark.parametrize('key', ['start', 'endpoint', 'targeted', 'futures'])
def test_nonfinite(panel, key):
    d = copy.deepcopy(panel[0]); d[key].flat[0] = np.nan
    with pytest.raises(ValueError): m.validate(d)


@pytest.mark.parametrize('value', [-1, 16])
def test_illegal_shift(panel, value):
    d = copy.deepcopy(panel[0]); d['shifts'].flat[0] = value
    with pytest.raises(ValueError): m.validate(d)


@pytest.mark.parametrize('kind', ['duplicate', 'pilot', 'reversed', 'float'])
def test_block_identity(kind):
    d = m.fixture(16); d['block_ids'] = np.arange(90000, 90016, dtype=np.int64)
    if kind == 'duplicate': d['block_ids'][1] = d['block_ids'][0]
    elif kind == 'pilot': d['block_ids'] += 10000
    elif kind == 'reversed': d['block_ids'] = d['block_ids'][::-1]
    else: d['block_ids'] = d['block_ids'].astype(float)
    with pytest.raises(ValueError): m.validate(d, development=True)


def test_original_label_forbidden(panel):
    d = dict(panel[0], labels=panel[0]['futures'][..., 0])
    with pytest.raises(ValueError): m.validate(d)


def test_founder_exclusion(panel):
    d = copy.deepcopy(panel[0]); d['futures'][0] = -.9
    new, raw, fits = m.fit_all(d)
    for k in m.OBSERVERS:
        np.testing.assert_array_equal(new[k][:, 0], panel[4][k][:, 0])
        assert fits[k]['folds'][0] == panel[6][k]['folds'][0]


def test_heldout_scaling(panel):
    d = copy.deepcopy(panel[0]); d['start'][0] += 1000
    _, _, fits = m.fit_all(d)
    for k in m.OBSERVERS: assert fits[k]['folds'][0] == panel[6][k]['folds'][0]


def test_future_permutation(panel):
    d = copy.deepcopy(panel[0]); d['futures'] = d['futures'][..., ::-1]
    p, _, _ = m.fit_all(d)
    for key in m.OBSERVERS: np.testing.assert_allclose(p[key], panel[4][key], atol=2e-13)


def test_raw_tying(panel):
    d, old, old_raw, refs, new, raw, fits = panel
    proof = c.verify_fits(*((d, new, raw, fits, old, old_raw, refs)))
    assert proof['max_raw_tie_error'] < 1e-12
    model = fits['tied:passive']['folds'][0]['models'][0]
    b = np.asarray(model['coefficients']); s = np.asarray(model['scale'])
    assert np.max(abs(b[:, 7:13] - b[:, 13:19])) > 1e-4
    np.testing.assert_allclose(b[:, 7:13] / s[7:13], b[:, 13:19] / s[13:19], atol=1e-14)


def test_zero_settings_nesting(panel):
    d = copy.deepcopy(panel[0]); d['shifts'].fill(0)
    old, old_raw, refs = m.fit_all(d, False); new, raw, fits = m.fit_all(d)
    for name in m.OBSERVERS: np.testing.assert_allclose(new[name], old[name], atol=2e-13)
    assert c.verify_fits(d, new, raw, fits, old, old_raw, refs)['zero_settings_nesting_checked']


def test_constants(panel):
    d = copy.deepcopy(panel[0])
    for k in ('start', 'endpoint', 'targeted'): d[k].fill(.25)
    old, old_raw, refs = m.fit_all(d, False); new, raw, fits = m.fit_all(d)
    assert c.verify_fits(d, new, raw, fits, old, old_raw, refs)['passes']


def test_rank_deficient(panel):
    d = copy.deepcopy(panel[0]); d['start'][..., 1:] = d['start'][..., :1]
    d['endpoint'][..., 1:, :] = d['endpoint'][..., :1, :]
    old, old_raw, refs = m.fit_all(d, False); new, raw, fits = m.fit_all(d)
    assert c.verify_fits(d, new, raw, fits, old, old_raw, refs)['passes']


@pytest.mark.parametrize('key', ['means', 'offsets', 'scale', 'coefficients', 'reduced_coefficients', 'alpha', 'training_blocks', 'prediction', 'reference'])
def test_corrupt_fit(panel, key):
    d, old, old_raw, refs, new, raw, fits = copy.deepcopy(panel)
    fold = fits['tied:passive']['folds'][0]; record = fold['models'][0]
    if key == 'training_blocks': fold[key][0] = -999
    elif key == 'prediction': raw['tied:passive'][0, 0, 0, 0] += .1; new['tied:passive'] = np.clip(raw['tied:passive'], -1, 1)
    elif key == 'reference': refs['starting']['folds'][0]['models'][0]['offsets'][0] += .1
    elif key == 'alpha': record[key] = .1
    else:
        a = np.asarray(record[key]); a.flat[0] += .1; record[key] = a.tolist()
    with pytest.raises((AssertionError, ValueError)): c.verify_fits(d, new, raw, fits, old, old_raw, refs)


def test_clipping(panel):
    d = copy.deepcopy(panel[0]); d['start'][0, :, :, 0] = 1e3
    old, old_raw, refs = m.fit_all(d, False); new, raw, fits = m.fit_all(d)
    assert any(np.any(abs(p) > 1) for p in raw.values())
    assert c.verify_fits(d, new, raw, fits, old, old_raw, refs)['passes']
    summary, losses = m.report(new, raw, old, old_raw, d)
    assert c.verify_report(summary, losses, d, new, raw, old, old_raw)['passes']


def test_future_mean_identity(panel):
    d, old, old_raw, refs, new, raw, fits = panel
    summary, losses = m.report(new, raw, old, old_raw, d)
    assert c.verify_report(summary, losses, d, new, raw, old, old_raw)['mean_future_gain_identity']


def test_extreme_scale_fails_closed(panel):
    # The first qualification attempt exposed ~1e-9 rounding at million-unit
    # extrapolations. Keep the fixed 2e-10 tolerance; do not accept that case.
    d = copy.deepcopy(panel[0]); d['start'][0, :, :, 0] = 1e7
    old, old_raw, refs = m.fit_all(d, False); new, raw, fits = m.fit_all(d)
    with pytest.raises(AssertionError): c.verify_fits(d, new, raw, fits, old, old_raw, refs)


@pytest.mark.parametrize('kind', ['absolute', 'group', 'founder', 'omission', 'gain', 'gap', 'cheap', 'context', 'losses', 'focal', 'count'])
def test_corrupt_summary(panel, kind):
    d, old, old_raw, refs, new, raw, fits = panel
    summary, losses = m.report(new, raw, old, old_raw, d)
    if kind == 'absolute': summary['absolute']['settings/starting'][0]['mse'] += .01
    elif kind == 'group': summary['absolute']['settings/starting'][0]['group_mse'][0] += .01
    elif kind == 'founder': summary['comparisons'][0]['block_gains'][0] += .01
    elif kind == 'omission': summary['comparisons'][0]['score_only_omit_gains'][0] += .01
    elif kind == 'gain': summary['comparisons'][0]['mse_reduction'] *= -1
    elif kind == 'gap': summary['gap_changes'][0]['mse_reduction'] += .01
    elif kind == 'cheap': summary['cheap_selection_context']['old/starting']['alpha'] = 2.
    elif kind == 'context': summary['selected_cheap_comparisons'][0]['mse_reduction'] += .01
    elif kind == 'losses': losses['settings/starting'][0, 0, 0, 0] += .01
    elif kind == 'focal': summary['focal']['candidate'] = 'tied:sham_plus'
    else: summary['new_fits'] += 1
    with pytest.raises(AssertionError): c.verify_report(summary, losses, d, new, raw, old, old_raw)


def test_score_omission_not_refit(panel):
    d, old, old_raw, refs, new, raw, fits = panel
    summary, _ = m.report(new, raw, old, old_raw, d)
    row = summary['comparisons'][0]; b = np.asarray(row['block_gains'])
    for i in range(4): assert row['score_only_omit_gains'][i] == pytest.approx(np.delete(b, i).mean())
    assert not summary['confidence_intervals']


def test_cheapest_alpha_tie(panel):
    d = panel[0]; p = {k: np.zeros((3, 4, 4, 4)) for k in m.OBSERVERS}
    summary, losses = m.report(p, p, p, p, d)
    assert all(v['alpha'] == .1 and v['selection_affected'] for v in summary['cheap_selection_context'].values())
    assert c.verify_report(summary, losses, d, p, p, p, p)['passes']


def metadata_fixture():
    s = np.ones((4, 4, 3, 2), dtype=np.int64)
    a = dict(index=90000, lives=[dict(life=j, index=90000, cases=copy.deepcopy(r.CASES),
        branches=['U0', 'U1', 'C1'], diagnostic_to_lineage=False) for j in range(4)])
    b = dict(spec=['former_test', 90000], lives=[dict(life=j, spec=['former_test', 90000],
        cases=copy.deepcopy(r.CASES), edits=list(m.EDITED[2:]), diagnostic_to_lineage=False) for j in range(4)])
    return {'shift': s.copy()}, a, {'shift': s.copy()}, b


@pytest.mark.parametrize('kind', ['case', 'life', 'id', 'branch', 'edit', 'shift', 'target_shift', 'leak'])
def test_case_order(kind):
    a, am, b, bm = metadata_fixture()
    assert r.metadata_shifts(a, am, b, bm, 90000).shape == (4, 4, 2, 2)
    if kind == 'case': am['lives'][0]['cases'].reverse()
    elif kind == 'life': am['lives'].reverse()
    elif kind == 'id': am['index'] += 1
    elif kind == 'branch': am['lives'][0]['branches'].reverse()
    elif kind == 'edit': bm['lives'][0]['edits'].reverse()
    elif kind == 'shift': a['shift'][0, 0, 2, 0] += 1
    elif kind == 'target_shift': b['shift'][0, 0, 0, 0] += 1
    else: am['lives'][0]['diagnostic_to_lineage'] = True
    with pytest.raises(ValueError): r.metadata_shifts(a, am, b, bm, 90000)


def test_roundtrip(tmp_path, panel):
    data, old, raw, refs = panel[:4]; out = tmp_path / 'roundtrip'
    proof, h = r.write_experiment(out, data, old, raw, refs)
    c.same(r.verify_saved(out, data, old, raw, refs), proof)
    r.verify_hashes(h)
    p = out / 'summary.json'; original = p.read_bytes()
    # Intentional corruption stays within a disposable external test fixture.
    with p.open('ab') as handle: handle.write(b'\n')
    with pytest.raises(AssertionError): r.verify_hashes(h)
    assert p.read_bytes() == original + b'\n'


def test_write_once(tmp_path):
    p = tmp_path / 'one.json'; r.write_json(p, {'value': 1})
    with pytest.raises(FileExistsError): r.write_json(p, {'value': 2})
    assert r.read_json(p) == {'value': 1}


def test_symlink_rejected(tmp_path):
    p = tmp_path / 'first.json'; r.write_json(p, {'x': 1}); link = tmp_path / 'alias.json'; link.symlink_to(p)
    with pytest.raises(ValueError): r.write_json(link, {'x': 2})


def test_root_output_rejected():
    with pytest.raises(ValueError): r.external(r.WS / 'data.json')


def test_resource_guard(monkeypatch):
    monkeypatch.setattr(r.os, 'sched_getaffinity', lambda _: set(range(7)))
    with pytest.raises(RuntimeError): r.resources()
    monkeypatch.setattr(r.os, 'sched_getaffinity', lambda _: {0})
    monkeypatch.setenv('OPENBLAS_NUM_THREADS', '2')
    with pytest.raises(RuntimeError): r.resources()


def test_reserve_guard(monkeypatch):
    monkeypatch.setattr(r.shutil, 'disk_usage', lambda _: SimpleNamespace(free=1))
    with pytest.raises(RuntimeError): r.resources()


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(r.ENV, raising=False)
    r.detach_guard(600)
    with pytest.raises(RuntimeError): r.detach_guard(601)
    monkeypatch.setenv(r.ENV, '1'); monkeypatch.setattr(r.os, 'getsid', lambda _: r.os.getpid() + 1)
    with pytest.raises(RuntimeError): r.detach_guard(601)
    monkeypatch.setattr(r.os, 'getsid', lambda _: r.os.getpid()); r.detach_guard(601)


def test_startup_handshake(monkeypatch):
    read_fd, write_fd = os.pipe()
    monkeypatch.setenv(r.READY, str(write_fd))
    try:
        r.acknowledge(); assert os.read(read_fd, 32) == b'READY\n'
    finally: os.close(read_fd)


def test_detached_launch_contract(monkeypatch, tmp_path):
    # No subprocess is started by this test; verify the launch contract and pipe.
    original_root = r.ROOT
    monkeypatch.setattr(r, 'ROOT', tmp_path)
    (tmp_path / 'logs').mkdir()
    monkeypatch.setattr(r, 'resources', lambda: [0])
    monkeypatch.setattr(r, 'checked_freeze', lambda: {})
    seen = []
    def fake_popen(command, **kwargs):
        assert command[-1] == 'benchmark'
        assert kwargs['start_new_session'] and kwargs['stdin'] == r.subprocess.DEVNULL
        assert kwargs['stderr'] == r.subprocess.STDOUT and kwargs['env'][r.ENV] == '1'
        fd = kwargs['pass_fds'][0]; assert kwargs['env'][r.READY] == str(fd)
        os.write(fd, b'READY\n'); seen.append(command)
        return SimpleNamespace(pid=12345)
    monkeypatch.setattr(r.subprocess, 'Popen', fake_popen)
    result = r.detach('benchmark')
    assert len(seen) == 1 and result['startup_acknowledged'] and not result['automatic_polling']


def test_no_launcher_retry_on_failed_ack(monkeypatch, tmp_path):
    monkeypatch.setattr(r, 'ROOT', tmp_path); (tmp_path / 'logs').mkdir()
    monkeypatch.setattr(r, 'resources', lambda: [0]); monkeypatch.setattr(r, 'checked_freeze', lambda: {})
    calls = []
    monkeypatch.setattr(r.subprocess, 'Popen', lambda *a, **k: (calls.append(k) or SimpleNamespace(pid=12346)))
    monkeypatch.setattr(r.select, 'select', lambda *a: ([], [], []))
    with pytest.raises(RuntimeError, match='unacknowledged'): r.detach('benchmark')
    assert len(calls) == 1


def test_no_automatic_successor():
    assert not r.contract()['automatic_polling'] and not r.contract()['automatic_retry'] and not r.contract()['automatic_successor']
    for function in (r.benchmark, r.execute, r.audit):
        text = inspect.getsource(function)
        assert 'subprocess.' not in text and 'detach(' not in text and 'sleep(' not in text
    text = inspect.getsource(r.benchmark)
    assert 'development_data(' not in text and 'execute(' not in text
    assert 'time.sleep' not in inspect.getsource(r)


def test_real_fit_approval_required():
    with pytest.raises(RuntimeError): r.execute()
    with pytest.raises(ValueError): r.detach('execute')


def test_no_dynamics_imports():
    for module in (m, c, r):
        text = inspect.getsource(module)
        assert 'import torch' not in text and 'from . import pilot_run' not in text
        assert 'tissue.step' not in text and 'from . import asymmetry' not in text


def test_source_binding():
    sources = r.source_files()
    assert len(sources) > 340
    assert str(r.ROOT / 'outputs' / r.OLD157 / 'dataset.npz') in sources
    assert str(r.ROOT / 'outputs' / r.OLD160 / 'tied_fits.json') in sources
    for relative in r.SCIENCE: assert str(r.WS / 'L20-extension-1' / relative) in sources


def test_saved_schema_rejects_extra(panel):
    d, old, old_raw, refs, new, raw, fits = copy.deepcopy(panel); new['pooled_extra'] = new['starting']
    with pytest.raises(AssertionError): c.verify_fits(d, new, raw, fits, old, old_raw, refs)


def test_full_counts():
    assert r.contract()['fits'] == 7 * 3 * 16
    assert r.contract()['forecasts'] == 7 * 3 * 16 * 16
    assert len(m.pairs()) == 31
    assert r.contract()['actual_reference_refits'] == r.contract()['new_dynamics'] == 0
