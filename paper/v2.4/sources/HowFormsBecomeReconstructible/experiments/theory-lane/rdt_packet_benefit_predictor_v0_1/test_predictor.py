"""Check block leakage, strong shrinkage, causal labels and resource accounting."""
import copy
import inspect
from pathlib import Path
import numpy as np
import pytest
import core
import scalar_audit as audit
import data


def fixture():
    records = []
    for block in range(4):
        for i in range(2):
            for regime in core.REGIMES:
                x = float(2 * i - 1)
                y = int(i == 1 and block % 2 == 0) - int(i == 0 and block % 2 == 1)
                records.append(dict(key=[block, 'synthetic', i, 0], block=block, regime=regime,
                    weight=.25, benefit=y, control=int(y < 0), repaired=int(y > 0),
                    features=dict(independent=float(regime == 'independent'), transfer=x,
                        transfer_change=.25 * x, ordinary_risk=(x + 1) / 2, direct_risk=.3, successor_risk=.7)))
    return records


def test_fixed_feature_contract_and_ridge_known_solution():
    records = fixture()
    # Perfect D = standardized transfer in a two-point, balanced fixture.
    for r in records:
        r['benefit'] = r['features']['transfer']
        r['features']['independent'] = 0.
    model = core.fit(records, 'packet_blind')
    assert model['intercept'] == 0.
    assert model['coefficients'] == pytest.approx([0., .5])
    audit.check_fit(records, 'packet_blind', model)
    assert list(inspect.signature(data.packet_features).parameters) == ['original', 'repaired', 'rule']
    assert len(core.FEATURES['candidate']) == 3
    assert core.P['fit']['ridge_penalty'] == 1.


def test_actual_packet_feature_and_dynamics_audit_are_distinct():
    assert Path(data.transfer_audit.__file__).resolve() == (core.ROOT / 'support/inherited/audit.py').resolve()
    assert data.transfer_audit is not audit
    empty = np.zeros((2, 16, 16))
    feature, cpu, check_cpu = data.packet_features(empty, empty.copy(), 1)
    assert feature == dict(transfer=0., transfer_change=0.)
    assert cpu >= 0 and check_cpu >= 0
    known = np.full((2, 16, 16), .7)
    feature, _, _ = data.packet_features(known, known.copy(), -1)
    assert feature['transfer_change'] == 0 and np.isfinite(feature['transfer'])


def test_held_out_labels_and_features_never_enter_fold_fit():
    records = fixture()
    before, _ = core.fold(records, 2)
    modified = copy.deepcopy(records)
    for r in modified:
        if r['block'] == 2:
            r['benefit'] = -r['benefit']
            r['features']['transfer'] = 1000.
    after, _ = core.fold(modified, 2)
    assert before == after
    assert all(2 not in model['train_blocks'] for model in before.values())


def test_complete_scalar_audit_and_dry_run_costs():
    records = fixture(); folds, predictions = {}, []
    for block in range(4):
        models, p = core.fold(records, block)
        folds[str(block)] = models; predictions.extend(p)
    result = core.evaluate(records, predictions)
    assert audit.evaluate(records, folds, predictions, result)['status'] == 'PASS'
    for regime in core.REGIMES:
        policy = result['regimes'][regime]['policies']['candidate']
        assert policy['dry_run_optimizer_calls'] == policy['total_deployment_optimizer_calls'] == 8
        assert result['regimes'][regime]['policies']['direct_risk']['extra_native_probe_reads'] == 64
        assert result['regimes'][regime]['policies']['repair_all']['applied_repairs'] == 8
        assert result['regimes'][regime]['policies']['zero']['applied_repairs'] == 0
    bad = copy.deepcopy(result)
    bad['regimes']['matched']['policies']['candidate']['dry_run_optimizer_calls'] = 0
    with pytest.raises(ValueError): audit.evaluate(records, folds, predictions, bad)
    broken = copy.deepcopy(folds); broken['0']['candidate']['coefficients'][0] += .1
    with pytest.raises(ValueError): audit.evaluate(records, broken, predictions, result)


def test_no_candidate_advantage_when_all_outcomes_identical():
    records = fixture()
    for r in records:
        r['benefit'] = 0; r['control'] = r['repaired'] = 1
    folds, predictions = {}, []
    for b in range(4):
        folds[str(b)], p = core.fold(records, b); predictions.extend(p)
    result = core.evaluate(records, predictions)
    audit.evaluate(records, folds, predictions, result)
    assert result['decision'] == 'DEVELOPMENT_SCREEN_FAILED'
    assert not result['advance_gate_pass']
    with pytest.raises(ValueError): core.evaluate(records, predictions[:-1])
    with pytest.raises(ValueError): core.evaluate(records, predictions + [predictions[0]])


def test_harm_is_negative_target_and_zero_threshold_is_fixed():
    records = fixture()
    for r in records:
        r['control'] = 1; r['repaired'] = 0; r['benefit'] = -1
    models, p = core.fold(records, 0)
    assert all(v['predictions']['regime_mean'] == -1 for v in p)
    assert all(v['predictions']['candidate'] == pytest.approx(-1) for v in p)
    audit.check_fit([r for r in records if r['block'] != 0], 'candidate', models['candidate'])
