"""Synthetic/in-memory qualification; no source-cohort extraction or dynamics."""
import ast
import copy
import json
from pathlib import Path

import numpy as np
import pytest

import review_divergence as main
import audit_divergence as audit


@pytest.mark.parametrize('role', [0, 1])
def test_template(role):
    assert main.best(main.TARGETS[role], role) == 1.
    assert main.best(main.TARGETS[1-role], role) == 0.


@pytest.mark.parametrize('role,shift', [(0, (1, 3)), (0, (8, 4)), (1, (3, 9)), (1, (15, 15))])
def test_translation(role, shift):
    value = np.roll(main.TARGETS[role], shift, (0, 1))
    assert main.best(value, role) == 1.
    assert audit.best(value, role) == pytest.approx(1., abs=1e-12, rel=0)


def test_scale_offset_batch_and_fft():
    rng = np.random.default_rng(145)
    a = rng.normal(size=(4, 3, 16, 16))
    for role in (0, 1):
        np.testing.assert_allclose(main.best(a, role), audit.best(a, role), atol=1e-12, rtol=0)
        np.testing.assert_allclose(main.best(3*a+7, role), main.best(a, role), atol=1e-12, rtol=0)


@pytest.mark.parametrize('value', [0., 1.])
def test_constant(value):
    a = np.full((2, 16, 16), value)
    np.testing.assert_array_equal(main.best(a, 0), [0., 0.])
    np.testing.assert_array_equal(audit.best(a, 0), [0., 0.])


@pytest.mark.parametrize('a', [np.zeros(256), np.full((16, 16), np.nan), np.full((16, 16), np.inf)])
def test_invalid_fields(a):
    with pytest.raises(ValueError): main.best(a, 0)
    with pytest.raises(ValueError): main.preference(a, 0)


def test_invalid_role():
    with pytest.raises(ValueError): main.best(main.TARGETS[0], 2)
    with pytest.raises(ValueError): main.preference(main.TARGETS[0], -1)


def test_strict_preference():
    assert main.preference(.2*main.TARGETS[0], 0) == 0
    assert main.preference(.200001*main.TARGETS[0], 0) == .5
    assert main.preference(main.TARGETS[1], 0) == -.5
    assert audit.pref(.2*main.TARGETS[1], 1) == 0


def test_all_cell_denominator():
    a = np.zeros((16, 16)); a[0, 4] = 1
    assert main.preference(a, 0) == audit.pref(a, 0) == 1/256


def test_zero_sign_rule():
    # Strict qualification excludes exactly zero; negative/zero are distinct.
    a = np.zeros((16, 4, 4))
    a[0, 0, 0] = -.1
    p = main.profile(a, True)
    assert p['negative_count'] == 1 and p['zero_count'] == 255
    audit.equal(p, audit.profile(a, True))


def test_packet_decode_batch():
    fields = np.stack([main.TARGETS[0], main.TARGETS[1]])
    packets = fields.astype('<f8').view(np.uint8).reshape(2, 2048)
    np.testing.assert_array_equal(main.decode(packets), fields)
    np.testing.assert_array_equal(audit.unpack(packets), fields)
    with pytest.raises(ValueError): main.decode(np.zeros(2047, np.uint8))
    with pytest.raises(ValueError): main.decode(np.zeros(2048, float))


def test_future_variance_divisor_three():
    y = np.broadcast_to(np.arange(4), (16, 4, 4)).copy()
    p = main.profile(y)
    assert p['mean'] == 1.5 and p['within_pair_variance'] == pytest.approx(5/3)
    audit.equal(p, audit.profile(y))


def test_sixteen_block_normalization():
    y = np.arange(1, 17)[:, None, None]*np.broadcast_to(np.arange(4), (16, 4, 4))
    p = main.profile(y)
    assert p['within_pair_variance'] == pytest.approx(np.mean(np.arange(1, 17)**2)*5/3)
    assert p['mean'] == 8.5*1.5
    audit.equal(p, audit.profile(y))


def test_no_between_case_variance_leak():
    y = np.broadcast_to(np.arange(64).reshape(16, 4, 1), (16, 4, 4)).copy()
    assert main.profile(y)['within_pair_variance'] == 0.
    assert audit.profile(y)['within_pair_variance'] == 0.


@pytest.mark.parametrize('a', [np.zeros((8, 4, 4)), np.zeros((16, 4, 3)), np.full((16, 4, 4), np.nan)])
def test_bad_panel(a):
    with pytest.raises(ValueError): main.profile(a)


def test_covariance_contraction_and_telescope():
    x = np.broadcast_to(np.arange(4)[None, None, :, None, None], (16, 4, 4, 3, 5))
    y = x*np.array([1., .5, .25, .5, .1])
    p = main.decomposition(y)
    assert p['within_change'][0][0] < 0
    assert p['within_increment'][0][0] > 0
    assert p['twice_covariance'][0][0] < 0
    assert p['pairs_spread_decreased'][0][0] == 64
    assert sum(p['within_change'][0]) == pytest.approx((.1**2-1)*5/3)
    audit.equal({k: v for k, v in p.items() if k != 'max_identity_error'}, audit.phase_stats(y))


def test_zero_variance_path():
    y = np.ones((16, 4, 4, 3, 5))
    p = main.decomposition(y)
    assert np.count_nonzero(p['within_change']) == 0
    assert np.count_nonzero(p['futures_fidelity_decreased']) == 0
    assert p['max_identity_error'] == 0


def panel():
    rng = np.random.default_rng(14142)
    tails = dict(read_preference=(3, 5), read_shape=(3, 5), write_preference=(3, 4),
                 write_shape=(3, 4), terminal_preference=(4,), terminal_shape=(4,), phase_shape=(3, 5))
    result = {k: rng.normal(size=(16, 4, 4, 4, *tail)) for k, tail in tails.items()}
    result['guide_family'] = rng.integers(-1, 2, (16, 4, 4, 4, 4))
    return result


def test_complete_summary_and_pair_moments():
    data = panel(); s, m = main.summarize(data)
    assert audit.check_summary(data, s, m)
    assert s['cases'] == 256 and s['futures'] == 1024
    assert s['no_causal_phase_allocation'] and s['no_new_intervals']
    assert len(m) == 80


def test_corrupt_summary_rejected():
    data = panel(); s, m = main.summarize(data)
    s['groups']['B_aligned']['metrics']['reader_endpoints']['within_pair_variance'][0] += .01
    with pytest.raises(AssertionError): audit.check_summary(data, s, m)


def test_corrupt_pair_moment_rejected():
    data = panel(); s, m = main.summarize(data)
    m['A_aligned__read_shape__variance'][0, 0, 0, 0] += .01
    with pytest.raises(AssertionError): audit.check_summary(data, s, m)


def test_dropped_case_rejected():
    data = panel(); data['phase_shape'] = data['phase_shape'][:-1]
    with pytest.raises(AssertionError): main.summarize(data)


def raw_fixture():
    rng = np.random.default_rng(1709)
    raw = {k: rng.normal(size=s) for k, s in dict(read_states=(4,4,4,3,5,3,16,16),
        write_states=(4,4,4,3,4,4,16,16), terminal_states=(4,4,4,4,3,16,16)).items()}
    packet = lambda a: np.ascontiguousarray(a, dtype='<f8').view(np.uint8).reshape(*a.shape[:-2], 2048)
    founders = packet(rng.normal(size=(4,2,16,16)))
    raw['founder_packets'] = np.repeat(founders[:, None], 4, axis=1)
    raw['outgoing'] = packet(rng.normal(size=(4,4,4,3,16,16)))
    raw['incoming'] = np.zeros_like(raw['outgoing'])
    for ci in range(4): raw['incoming'][:, :, ci, 0] = raw['founder_packets'][:, :, ci//2]
    raw['incoming'][..., 1:, :] = raw['outgoing'][..., :-1, :]
    raw['routed'] = raw['incoming'].copy()
    raw['terminal_input'] = raw['outgoing'][..., -1, :].copy()
    raw['targets'] = np.broadcast_to(main.TARGETS, (4,4,2,16,16)).copy()
    for role in range(2):
        raw['read_states'][:, :, 2*role+1, 0] = raw['read_states'][:, :, 2*role, 0]
        raw['write_states'][:, :, 2*role+1, 0, 1] = raw['write_states'][:, :, 2*role, 0, 1]
    raw['write_states'][..., 0, :3, :, :] = raw['read_states'][..., -1, :, :, :]
    raw['write_states'][..., 0, 3, :, :] = 0
    for k, prefix in (('values', 'read'), ('terminal_values', 'terminal')):
        states = raw[prefix+'_states']; raw[k] = np.zeros((*states.shape[:-3], 12))
        for ci in range(4):
            p = audit.pref(states[:, :, ci, ..., 0, :, :], ci//2)
            raw[k][:, :, ci, ..., 0] = np.maximum(p, 0)
            raw[k][:, :, ci, ..., 1] = np.maximum(-p, 0)
    paths = [dict(generations=[dict(selector=dict(inferred_family=ci//2)) for _ in range(3)],
                  terminal=dict(selector=dict(inferred_family=ci//2))) for ci in range(4)]
    meta = dict(index=90000, config=dict(steps=300, source_steps=1000, rescue_after=100, amp_threshold=.2),
        lives=[[dict(index=90000, life=l, future=f, namespace=f'l20-extension1-repeated-futures-v1:future{f}',
                     cases=[[0,'translated'],[0,'aligned'],[1,'translated'],[1,'aligned']], paths=copy.deepcopy(paths),
                     replay=dict(full_dynamics_replayed=True)) for f in range(4)] for l in range(4)])
    return raw, meta


@pytest.fixture(scope='module')
def measured_fixture():
    raw, meta = raw_fixture()
    return raw, meta, main.measure_block(raw, meta)


def test_full_synthetic_extraction_independence(measured_fixture):
    raw, meta, m = measured_fixture
    proof = audit.check_block(raw, meta, m)
    assert proof['body_preference_checks'] == 1984 and proof['independent_fft_shape_checks'] == 2560
    assert proof['new_dynamics'] == 0


def test_corrupt_extracted_metric_rejected(measured_fixture):
    raw, meta, m = measured_fixture
    changed = {k: v.copy() for k, v in m.items()}
    changed['phase_shape'][0, 0, 0, 0, 3] += .01
    with pytest.raises(AssertionError): audit.check_block(raw, meta, changed)


def test_corrupt_record_chain_rejected(measured_fixture):
    raw, meta, _ = measured_fixture
    bad = dict(raw); bad['terminal_input'] = raw['terminal_input'].copy(); bad['terminal_input'][0,0,0,0] ^= 1
    with pytest.raises(AssertionError): main.measure_block(bad, meta)


def test_future_order_rejected(measured_fixture):
    raw, meta, _ = measured_fixture
    bad = copy.deepcopy(meta); bad['lives'][0][0]['future'] = 1
    with pytest.raises(AssertionError): main.measure_block(raw, bad)


def artifact_fixture(tmp_path):
    names = ('FREEZE.json', 'benchmark.json', 'STARTED.json', 'measurements.npz', 'pair_moments.npz', 'summary.json', 'verification.json')
    for name in names: (tmp_path/name).write_bytes(b'qualification fixture')
    receipt = dict(status='COMPLETE', source_complete_sha256=audit.SOURCE_SHA,
        output_sha256={n: audit.sha(tmp_path/n) for n in names}, output_bytes=sum((tmp_path/n).stat().st_size for n in names))
    (tmp_path/'COMPLETE.json').write_text(json.dumps(receipt))
    return receipt


def test_artifact_seal(tmp_path):
    expected = artifact_fixture(tmp_path)
    assert audit.verify_artifacts(tmp_path) == expected
    (tmp_path/'summary.json').write_text('changed')
    with pytest.raises(AssertionError): audit.verify_artifacts(tmp_path)


def test_extra_artifact_rejected(tmp_path):
    artifact_fixture(tmp_path); (tmp_path/'unexpected.json').write_text('{}')
    with pytest.raises(AssertionError): audit.verify_artifacts(tmp_path)


def test_no_simulator_or_predictor_imports():
    allowed = {'__future__','argparse','datetime','hashlib','json','os','pathlib','platform','shutil','time','xml','numpy','audit_divergence'}
    for module in (main, audit):
        tree = ast.parse(Path(module.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name.split('.')[0] in allowed for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.module.split('.')[0] in allowed


def test_write_once(tmp_path):
    p = tmp_path/'once.json'
    main.write_json(p, {'test': 1})
    with pytest.raises(FileExistsError): main.write_json(p, {'test': 2})
    assert json.loads(p.read_text()) == {'test': 1}
