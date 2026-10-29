"""Contract checks; separate native qualification tests the physical arithmetic."""
from copy import deepcopy
from pathlib import Path
import time

import numpy as np
import pytest

import ec_common as common
import ec_probe as probe


def test_features_use_the_declared_number_and_kind_of_reads():
    data = dict(boundary=np.zeros((2, 11)), writer=np.zeros((2, 128)), retained=np.zeros((2, 128)), rewrite=np.zeros((2, 128)))
    data['writer'][:, :32] = 1
    data['retained'][:, 32:64] = 1
    data['rewrite'][:, :16] = 1
    for name, q in [('successor32', .5), ('direct64', .5), ('pooled32', .5), ('direct8', 0.)]:
        result = common.feature_matrix(data, [0, 1], common.MODELS[name]['spec'])
        assert result.shape == (2, 12) and np.all(result[:, -1] == q)
    assert common.feature_matrix(data, [0, 1], common.MODELS['tt008']['spec']).shape == (2, 11)


@pytest.mark.parametrize('bad', ['short', 'nonbinary', 'nonfinite'])
def test_invalid_measurements_cannot_be_silently_averaged(bad):
    values = np.zeros((1, 64))
    if bad == 'short':
        values = values[:, :8]
    else:
        values[0, 0] = 2 if bad == 'nonbinary' else np.nan
    with pytest.raises(ValueError, match='Complete binary'):
        common.feature_matrix(dict(boundary=np.zeros((1, 11)), retained=values), [0], common.MODELS['direct64']['spec'])


@pytest.mark.parametrize('rule', [-1, 1])
def test_endpoint_requires_every_aligned_port_strictly_over_threshold(rule):
    target = np.array([[1., -1.], [-1., 1.]]) * rule
    windows = np.broadcast_to(.25 * target, (2, 32, 1, 2, 2)).copy()
    windows[1] *= 1.04
    _, passed = probe.independent_scores(windows, rule)
    assert passed.tolist() == [[0], [1]]
    windows[1, :, 0, 1, 1] = -.26 * rule
    assert probe.independent_scores(windows, rule)[1][1, 0] == 0


@pytest.mark.parametrize('name', list(common.MODELS))
def test_scalar_and_matrix_prediction_agree_for_extreme_features(name):
    width = 11 if name == 'tt008' else 12
    values = np.array([np.full(width, -100.), np.zeros(width), np.full(width, 100.)])
    a = common.probability_matrix(values, common.MODELS[name])
    b = [common.probability_scalar(v, common.MODELS[name]) for v in values]
    assert np.max(abs(a - b)) < 1e-12


@pytest.fixture
def measured_contract(tmp_path, monkeypatch):
    common.configure()
    calls = []

    def environment(stage, key, index, purpose, regime):
        code = 100 * index + (1 if purpose == 'writer' else 2)
        return np.zeros((16, 16), bool), np.zeros((2, 16, 16)), np.full((1, 2, 16, 16), code, dtype=float)

    def calculate(weights):
        count, branches = weights.shape[:2]
        amplitude = np.where(weights.mean(axis=(-3, -2, -1)) > .5, .4, .2)
        windows = np.broadcast_to(amplitude[:, None, :, None, None] * np.array([[1., -1.], [-1., 1.]]),
                                  (count, 32, branches, 2, 2)).copy()
        return dict(end=weights.copy(), windows=windows, outgoing=weights + 1)

    def primary(weights, envs):
        calls.append(weights.copy())
        return calculate(weights)

    def flat(weights, mask, birth, noise, cfg, beta):
        return {k: v[0] for k, v in calculate(weights[None]).items()}

    monkeypatch.setattr(probe.probes, 'environment', environment)
    monkeypatch.setattr(probe.fast_reader, 'read_batch', primary)
    monkeypatch.setattr(probe.audit, 'read_write', flat)
    packet = np.zeros((2, 16, 16), dtype=float)
    before = packet.tobytes()
    guard = common.Guard(tmp_path, time.time() + 30)
    records = {name: probe.measure(packet, 1, [-99, 'fixture', 0, 0], 'matched', name, [0.] * 11, tmp_path / name, guard)
               for name in ('direct8', 'direct64', 'pooled32', 'successor32')}
    assert packet.tobytes() == before
    return records, calls


def test_successor_propagates_written_state_and_direct_preserves_original(measured_contract):
    records, calls = measured_contract
    assert probe.verify_case(records)['status'] == 'PASS'
    assert records['successor32'][1]['q'] == 1
    assert records['direct64'][1]['q'] == records['pooled32'][1]['q'] == 0
    assert sum(v.shape[0] * v.shape[1] for v in calls) == 200
    assert sum(r['flat_native_reads'] for _, r in records.values()) == 7


@pytest.mark.parametrize('change', ['state', 'budget', 'forcing', 'identity', 'probability'])
def test_changed_case_cannot_pass_validation(measured_contract, change):
    records, _ = measured_contract
    if change == 'state':
        records['direct64'][0]['direct_end'][0, 0, 0, 0, 0] += 1
    elif change == 'budget':
        records['direct64'][1]['native_reads'] = 8
    elif change == 'forcing':
        records['direct64'][1]['forcing'][-1]['sha256']['noise'] = records['direct64'][1]['forcing'][0]['sha256']['noise']
    elif change == 'identity':
        records['pooled32'][1]['key'] = [-98, 'fixture', 0, 0]
    else:
        records['direct64'][1]['probability'] += .01
    with pytest.raises(ValueError):
        probe.verify_case(records)


def test_namespace_adapter_preserves_every_numerical_parameter():
    common.configure()
    expected = deepcopy(common.ORIGINAL)
    expected['forcing']['namespace'] = common.C['benchmark']['namespace']
    assert common.P == expected


def test_completed_evidence_rejects_mutation(tmp_path):
    (tmp_path / 'raw.txt').write_text('record')
    common.complete(tmp_path, dict(decision='TEST_ONLY'))
    assert common.verify_complete(tmp_path)['status'] == 'COMPLETE'
    (tmp_path / 'raw.txt').write_text('changed')
    with pytest.raises(ValueError, match='Changed saved evidence'):
        common.verify_complete(tmp_path)


def test_guard_enforces_declared_deadline(tmp_path):
    with pytest.raises(ValueError, match='deadline'):
        common.Guard(tmp_path, time.time() - 1).check()


def timing_fixture(seconds=10.):
    value = dict(without_audit_wall_seconds=seconds - 1, total_wall_seconds=seconds,
                 without_audit_cpu_seconds=seconds - 2, primary_cpu_seconds=seconds - 3, audit_cpu_seconds=1.)
    return [{name: dict(value) for name in common.C['benchmark']['models']} for _ in range(8)]


@pytest.mark.parametrize('seconds,expected,admitted', [(10., 3360., True), (11., 3684., False)])
def test_development_pricing_keeps_full_panel_audits_and_safety_factor(seconds, expected, admitted):
    from ec_benchmark import summarize
    result = summarize(timing_fixture(seconds), 4)['exposed_108_block_development']
    assert result['conservative_wall_seconds'] == expected
    assert result['within_preferred_hour'] is admitted
    assert result['primary_native_reads'] == 55296 and result['flat_native_reads'] == 1728
    assert result['new_future_outcomes'] == 0


@pytest.mark.parametrize('change', ['incomplete', 'untested_concurrency', 'invalid_time'])
def test_pricing_rejects_missing_or_inapplicable_evidence(change):
    from ec_benchmark import summarize
    timings = timing_fixture()
    workers = 4
    if change == 'incomplete':
        timings.pop()
    elif change == 'untested_concurrency':
        workers = 8
    else:
        timings[0]['direct64']['total_wall_seconds'] = float('nan')
    with pytest.raises(ValueError):
        summarize(timings, workers)
