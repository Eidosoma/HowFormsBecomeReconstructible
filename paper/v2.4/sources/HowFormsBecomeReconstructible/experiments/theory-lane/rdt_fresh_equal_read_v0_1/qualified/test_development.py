"""Leakage, pairing, complete-cohort scoring and bounded-failure checks."""
from copy import deepcopy
import hashlib
import math

import numpy as np
import pytest

import ec_common as common
import ec_development as runner
from ec_source import D
from ec_analysis import analyze, scalar_check
from test_equal_reads import measured_contract


@pytest.fixture
def extended_case(measured_contract):
    records, _ = measured_contract
    direct, receipt = records['direct64']
    receipt.update(stage=D['stage'], namespace=D['namespace'])
    row = dict(key=receipt['key'], rule=receipt['rule'], boundary=receipt['boundary'], block=-99,
        current_pass=0, packet_sha256=hashlib.sha256(direct['packet'].tobytes()).hexdigest())
    cached = {k: v.copy() for k, v in records['successor32'][0].items()}
    cached.update({k: v.copy() for k, v in records['direct8'][0].items() if k.startswith('direct_')})
    forcing = [dict(probe=i, purposes=dict(
        writer=next(f['sha256'] for f in records['successor32'][1]['forcing'] if f['branch'] == 'writer' and f['probe'] == i),
        evaluation=receipt['forcing'][i]['sha256'].copy())) for i in range(32)]
    forecast = dict(**row, regime='matched', probabilities={
        'candidate': records['successor32'][1]['probability'],
        'direct_rival': records['direct8'][1]['probability'],
        'tt008': common.probability_scalar(row['boundary'], common.MODELS['tt008'])})
    return dict(index=0, row=row, regime='matched'), direct, receipt, (cached, dict(forcing=forcing), forecast)


def test_cached_models_are_preserved_exactly_and_pooled_uses_original_writer(extended_case):
    item, raw, receipt, original = extended_case
    prediction = runner.verify_new(item, raw, receipt, original)
    assert prediction['q_direct64'] == prediction['q_pooled32'] == 0
    for name, old in D['cached_names'].items():
        assert prediction['probabilities'][name] == original[2]['probabilities'][old]
    # Writer32 supplies half the pooled denominator, not a rewritten evaluation.
    original[0]['writer_passed'][:] = 1
    assert runner.verify_new(item, raw, receipt, original)['q_pooled32'] == .5


@pytest.mark.parametrize('change', ['state_prefix', 'forcing_prefix', 'reused_noise', 'namespace', 'stage', 'budget', 'packet', 'endpoint', 'probability', 'coverage'])
def test_adapter_rejects_changed_scientific_identity_or_evidence(extended_case, change):
    item, raw, receipt, original = extended_case
    if change == 'state_prefix':
        raw['direct_end'][0, 0, 0, 0, 0] += 1
    elif change == 'forcing_prefix':
        receipt['forcing'][9]['sha256']['noise'] = 'changed'
    elif change == 'reused_noise':
        receipt['forcing'][63]['sha256']['noise'] = receipt['forcing'][62]['sha256']['noise']
    elif change in ('namespace', 'stage'):
        receipt[change] = 'qualification_stream'
    elif change == 'budget':
        receipt['native_reads'] = 56
    elif change == 'packet':
        raw['packet'][0, 0, 0] += 1
    elif change == 'endpoint':
        raw['direct_passed'][-1, 0] = 1
    elif change == 'probability':
        receipt['probability'] += .01
    else:
        raw['probes'][-1] = 62
    with pytest.raises(ValueError):
        runner.verify_new(item, raw, receipt, original)


def test_development_adapter_changes_only_the_original_probe_namespace():
    common.configure('development')
    expected = deepcopy(common.ORIGINAL)
    expected['forcing']['namespace'] = D['namespace']
    assert common.P == expected
    with pytest.raises(ValueError):
        common.configure('future')


def scoring_fixture():
    rows, forecasts, outcomes = [], [], []
    probabilities = dict(successor32=.25, direct64=.5, pooled32=.1, direct8=.9, tt008=.75)
    for b in range(2):
        for j, c in enumerate([0, 1, 1]):
            row = dict(key=[b, 'fixture', j, 0], block=b, current_pass=c)
            rows.append(row)
            for g in D['regimes']:
                forecasts.append(dict(**row, regime=g, probabilities=probabilities.copy()))
                for r in range(4):
                    y = int(r == 3) if j == 0 else int(j == 1)
                    outcomes.append(dict(key=row['key'], regime=g, replicate=r, passed=y))
    return rows, forecasts, outcomes


def test_individual_future_losses_and_equal_class_weights_with_unequal_class_sizes():
    rows, forecasts, outcomes = scoring_fixture()
    result = analyze(rows, forecasts, outcomes, expected_blocks=2, expected_packets=6)
    for g in D['regimes']:
        assert result['regimes'][g]['observed_success'] == .375
        for m, p in forecasts[0]['probabilities'].items():
            assert result['regimes'][g]['brier'][m] == pytest.approx(p * p + (1 - 2 * p) * .375)
    assert scalar_check(rows, forecasts, outcomes, result)['status'] == 'PASS'
    assert result['decision'] == 'NO_NEW_CONFIRMATORY_VERDICT'
    assert len(result['planning_covariance']['order']) == 8
    result['regimes']['matched']['contrasts']['direct64']['mean_gain'] += .01
    with pytest.raises(ValueError, match='contrast'):
        scalar_check(rows, forecasts, outcomes, result)


@pytest.mark.parametrize('change', ['missing_packet', 'missing_forecast', 'extra_forecast', 'missing_repeat', 'duplicate_repeat', 'invalid_probability', 'metadata', 'nonbinary'])
def test_partial_or_corrupted_data_cannot_supply_a_score(change):
    rows, forecasts, outcomes = scoring_fixture()
    if change == 'missing_packet':
        rows.pop()
    elif change == 'missing_forecast':
        forecasts.pop()
    elif change == 'extra_forecast':
        forecasts.append(deepcopy(forecasts[0]))
    elif change == 'missing_repeat':
        outcomes.pop()
    elif change == 'duplicate_repeat':
        outcomes[-1] = deepcopy(outcomes[0])
    elif change == 'invalid_probability':
        forecasts[0]['probabilities']['direct64'] = math.nan
    elif change == 'metadata':
        forecasts[0]['current_pass'] = 1
    else:
        outcomes[0]['passed'] = 2
    with pytest.raises(ValueError):
        analyze(rows, forecasts, outcomes, expected_blocks=2, expected_packets=6)


def test_cost_gate_retains_slower_benchmark_and_measures_process_startup(monkeypatch):
    monkeypatch.setattr(runner, 'read', lambda _: dict(models=dict(direct64=dict(maximum_total_wall_seconds=18.))))
    payloads = [dict(unit_wall_seconds=10.) for _ in range(8)]
    assert runner.qualification_price([15., 16.], payloads)['conservative_wall_seconds'] == 5952
    assert runner.qualification_price([20., 16.], payloads)['conservative_wall_seconds'] == 6600
    with pytest.raises(ValueError, match='runtime cap'):
        runner.qualification_price([(D['hard_wall_seconds'] - 120) / 324 + 1, 16.], payloads)
    with pytest.raises(ValueError, match='complete qualification'):
        runner.qualification_price([15.], payloads)


def test_failure_is_durable_and_cannot_overwrite_attempt(tmp_path, monkeypatch):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    (inputs / 'INPUTS.json').write_text('{}')
    monkeypatch.setattr(runner, 'ROOT', inputs)
    monkeypatch.setattr(runner, 'verify_snapshot', lambda: (_ for _ in ()).throw(ValueError('deliberate changed input')))
    output = tmp_path / 'attempt'
    with pytest.raises(ValueError, match='changed input'):
        runner.execute(output, 'qualification')
    assert common.read(output / 'STATUS.json')['status'] == 'FAILED'
    assert not (output / 'COMPLETE.json').exists()
    with pytest.raises(FileExistsError):
        runner.execute(output, 'qualification')
