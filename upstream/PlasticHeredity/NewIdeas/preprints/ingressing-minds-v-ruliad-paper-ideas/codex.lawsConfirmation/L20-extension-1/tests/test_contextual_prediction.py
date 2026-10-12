"""D176 synthetic-only qualification; never loads real data or reference models."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from l20_extension1 import contextual_prediction as m, contextual_prediction_check as c, contextual_prediction_run as r


@pytest.fixture
def data(): return m.fixture(4)


@pytest.fixture(scope='module')
def panel():
    d = m.fixture(4); refs = m.synthetic_references(d); p, raw, fits = m.fit_new(d, *refs)
    report, losses = m.report(d, p, raw)
    return d, refs, p, raw, fits, report, losses


def test_full_small_audit(panel):
    d, refs, p, raw, fits, report, losses = panel
    proof = c.fits(d, p, raw, fits, *refs)
    assert proof['models_checked'] == 132 and proof['new_models'] == 48 and proof['reused_models'] == 84
    assert proof['maximum_objective_change'] <= 2e-10
    assert c.report(d, p, raw, report, losses)['passes']


@pytest.mark.parametrize('key', m.KEYS)
def test_feature_dimensions_and_independent_assembly(data, key):
    x = m.panels({k: data[k] for k in m.MEASUREMENTS})
    np.testing.assert_array_equal(x[key], c.features(data)[key])
    version, name = key.split('/', 1)
    want = dict(old=dict(starting=7, one_copy=13, **{'tied:passive': 19, 'tied:pulse': 19}),
        settings=dict(starting=9, one_copy=15, **{'tied:passive': 21, 'tied:pulse': 21}),
        interaction=dict(one_copy=21, **{'tied:passive': 33, 'tied:pulse': 33}))[version][name]
    assert x[key].shape == (4, 4, 4, want)


@pytest.mark.parametrize('extra', ('futures', 'block_ids', 'u1', 'theta', 'routing', 'second_copy_difference'))
def test_feature_boundary(data, extra):
    inputs = dict(start=data['start'], u0=data['u0'], second=data['pulse'], q=data['q'])
    inputs[extra] = np.zeros(1)
    with pytest.raises(ValueError): m.observer_features('interaction/tied:pulse', inputs)


def test_unused_reading_cannot_change_forecast_inputs(data):
    before = m.panels({k: data[k] for k in m.MEASUREMENTS})
    data['u1'][:] += 99
    after = m.panels({k: data[k] for k in m.MEASUREMENTS})
    for v in m.VERSIONS:
        np.testing.assert_array_equal(before[v+'/tied:pulse'], after[v+'/tied:pulse'])
    for key in m.CHEAP: np.testing.assert_array_equal(before[key], after[key])


def test_aligned_zero_interactions(data):
    x = m.panels({k: data[k] for k in m.MEASUREMENTS})
    for key in m.NEW[1:]:
        first = 15 if key.endswith('one_copy') else 21
        np.testing.assert_array_equal(x[key][:, :, (1, 3), first:], 0)
    shifts = np.zeros((4, 4, 4, 2, 2), dtype=np.int64)
    a = m.prior.effective_q(shifts); shifts[:, :, (1, 3)] = 13
    np.testing.assert_array_equal(a, m.prior.effective_q(shifts))


def test_all_addresses():
    shifts = np.zeros((16, 4, 4, 2, 2), dtype=np.int64)
    for role in (0, 1):
        for start in range(0, 256, 128):
            values = np.array([divmod(i, 16) for i in range(start, start+128)]).reshape(16, 4, 2, 2)
            shifts[:, :, 2*role] = values
            np.testing.assert_array_equal(m.prior.effective_q(shifts), c.legacy.rolled_q(shifts))


def test_own_setting_pairing(data):
    inp = dict(start=data['start'], u0=data['u0'], second=data['pulse'], q=data['q'])
    a = m.observer_features('interaction/tied:pulse', inp)
    b = m.observer_features('interaction/tied:pulse', dict(inp, u0=inp['second'], second=inp['u0'], q=inp['q'][..., ::-1].copy()))
    np.testing.assert_array_equal(a[..., 21:27], b[..., 27:33]); np.testing.assert_array_equal(a[..., 27:33], b[..., 21:27])
    np.testing.assert_array_equal(a[..., 21:27], (data['q'][..., :1]-1)*data['u0'])


@pytest.mark.parametrize('key', ('interaction/one_copy', 'interaction/tied:passive', 'interaction/tied:pulse'))
def test_founder_exclusion(data, key):
    _, _, before = m.fit_key(data, key)
    changed = copy.deepcopy(data); changed['futures'][0] = .99; changed['start'][0] += 50
    _, _, after = m.fit_key(changed, key)
    assert before['folds'][0] == after['folds'][0]
    assert before['folds'][1] != after['folds'][1]


def test_double_tying(panel):
    d, refs, p, raw, fits, report, losses = panel
    for key in ('interaction/tied:passive', 'interaction/tied:pulse'):
        rec = fits[key]['folds'][0]['models'][1]
        scale, beta = np.array(rec['scale']), np.array(rec['coefficients'])
        assert not np.allclose(scale[7:13], scale[13:19])
        for lo, hi in ((7, 13), (21, 27)):
            np.testing.assert_allclose(beta[:, lo:lo+6]/scale[lo:lo+6], beta[:, hi:hi+6]/scale[hi:hi+6], atol=2e-12, rtol=0)
        for q in (-1, 0, 1):
            left = beta[:, 7:13]/scale[7:13]+(q-1)*beta[:, 21:27]/scale[21:27]
            right = beta[:, 13:19]/scale[13:19]+(q-1)*beta[:, 27:33]/scale[27:33]
            np.testing.assert_allclose(left, right, atol=2e-12, rtol=0)


@pytest.mark.parametrize('constant', (False, True))
def test_collinear_and_constant_features(data, constant):
    x = m.panels({k: data[k] for k in m.MEASUREMENTS})['interaction/tied:pulse'].reshape(64, 33)
    if constant: x[:] = 0
    else: x[:, 2] = x[:, 1]
    g = np.tile(np.arange(4, dtype=np.int64), 16); y = data['futures'].mean(-1).ravel()
    rec = m.fit(x, y, g, .01, 'interaction/tied:pulse'); raw = m.prior.raw_predict(rec, x, g)
    assert c.model(rec, x, y, g, x, g, raw, .01, 'interaction/tied:pulse')['svd'] < 2e-10


@pytest.mark.parametrize('field', ('means', 'scale', 'coefficients', 'validation_block', 'training_blocks'))
def test_model_corruption(panel, field):
    d, refs, p, raw, fits, report, losses = panel; fits = copy.deepcopy(fits)
    fold = fits['interaction/tied:pulse']['folds'][0]
    if field == 'validation_block': fold[field] = 99
    elif field == 'training_blocks': fold[field][0] = 0
    elif field == 'scale': fold['models'][0][field][0] += .1
    else: fold['models'][0][field][0][0] += .1
    with pytest.raises(AssertionError): c.fits(d, p, raw, fits, *refs)


def test_reference_identity(panel):
    d, refs, p, raw, fits, report, losses = panel; fits = copy.deepcopy(fits)
    fits['old/starting']['folds'][0]['models'][0]['alpha'] = .1
    with pytest.raises(AssertionError): c.fits(d, p, raw, fits, *refs)


def test_complete_report(panel):
    d, refs, p, raw, fits, report, losses = panel
    assert len(report['absolute']) == 11 and len(report['comparisons']) == 138
    assert len(report['gap_changes']) == 9 and len(report['selected_contexts']) == 30
    assert report['focal'] == ['interaction/tied:pulse', 'interaction/tied:passive', .01]
    assert c.report(d, p, raw, report, losses)['mean_future_gain_identity']


@pytest.mark.parametrize('field', ('absolute', 'comparisons', 'gap_changes', 'selected_cheap', 'selected_contexts'))
def test_report_corruption(panel, field):
    d, refs, p, raw, fits, report, losses = panel; report = copy.deepcopy(report)
    if field == 'absolute': report[field]['old/starting'][0]['mse'] += 1
    elif field == 'selected_cheap': report[field]['old/starting']['alpha'] = 2
    else: report[field][0]['mse_reduction'] += 1
    with pytest.raises(AssertionError): c.report(d, p, raw, report, losses)


def test_clipping_and_mean_future_identity(panel):
    d, refs, p, raw, fits, _, _ = panel; raw = copy.deepcopy(raw)
    raw['interaction/tied:pulse'][:] = 2
    p = {k: np.clip(v, -1, 1) for k, v in raw.items()}
    report, losses = m.report(d, p, raw); assert c.report(d, p, raw, report, losses)['passes']
    assert report['absolute']['interaction/tied:pulse'][0]['clipped'] == 64


@pytest.mark.parametrize('bad', ('pilot', 'missing_future', 'original', 'nonfinite', 'bad_q', 'aligned_q'))
def test_data_boundary(data, bad):
    if bad == 'pilot':
        data['block_ids'] += 100000
        with pytest.raises(ValueError): m.validate(data, development=True)
        return
    if bad == 'missing_future': data['futures'] = data['futures'][..., :3]
    elif bad == 'original': data['labels'] = np.zeros((4, 4, 4))
    elif bad == 'nonfinite': data['pulse'].flat[0] = np.nan
    elif bad == 'bad_q': data['q'].flat[0] = 2
    else: data['q'][:, :, 1] = 0
    with pytest.raises(ValueError): m.validate(data)


def test_reference_fit_forbidden_on_real_ids(data):
    data['block_ids'] += 90000
    with pytest.raises(ValueError): m.synthetic_references(data)


def test_time_gate(monkeypatch):
    monkeypatch.setattr(r.io, 'read_json', lambda p: dict(passes=True, freeze_sha256='x', attached_bound_seconds=601, benchmark_bytes=1))
    monkeypatch.setattr(r, 'resources', lambda: dict(retained_bytes=0))
    with pytest.raises(AssertionError, match='detached'): r.time_gate('x')


def test_saved_roundtrip_and_no_audit_fitting(tmp_path, panel, monkeypatch):
    d, refs, *_ = panel; directory = tmp_path/'saved'
    proof = r.save_panel(directory, d, refs)
    def forbidden(*args, **kwargs): raise AssertionError('production fit called during saved audit')
    monkeypatch.setattr(m, 'fit', forbidden); monkeypatch.setattr(m, 'fit_key', forbidden)
    c.same(r.check_panel(directory, d, refs), proof)
    with pytest.raises(FileExistsError): r.save_panel(directory, d, refs)


def test_external_and_hash_guards(tmp_path):
    with pytest.raises(ValueError): r.io.external(Path('/tmp/outside_d176_scope.json'))
    file = tmp_path/'record.json'; r.io.write_json(file, {'value': 1}); pins = r.io.hashes([file]); r.io.verify_hashes(pins)
    with pytest.raises(FileExistsError): r.io.write_json(file, {'value': 2})
    with pytest.raises(AssertionError): r.io.verify_hashes({str(file): '0'*64})
    link = tmp_path/'alias.json'; link.symlink_to(file)
    with pytest.raises(ValueError): r.io.external(link)


def test_no_physics_imports():
    assert not any(k.startswith('laws_confirmation.l20_') for k in sys.modules)
    assert not any(k.startswith('l20_extension1.feedback_pulse') for k in sys.modules)


def test_inventory_preserves_guard_alias(tmp_path):
    root = tmp_path.parent
    folder = tmp_path/'test_external_and_hash_guards0'
    folder.mkdir(); target = folder/'record.json'; r.io.write_json(target, {'fixture': True})
    link = folder/'alias.json'; link.symlink_to(target)
    r.fixture_alias(root, link)
    with pytest.raises(AssertionError): r.fixture_alias(r.output_dir(), link)


@pytest.mark.parametrize('name', ('unknown/observer', '../outside', '/absolute'))
def test_undeclared_archive_path_rejected(tmp_path, name):
    path = tmp_path/'bad.npz'; r.io.write_npz(path, {name: np.zeros(1)})
    with pytest.raises(AssertionError): r.npz(path, (name,))
