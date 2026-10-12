"""Sealed-model inference and the single registered prospective comparison."""
import hashlib
import numpy as np
from . import diagnostics as dev, predictor, audit as independent
from . import heldout_system as system

MODEL_NAMES = ('starting_only', 'passive', 'challenge')


def feature_hash(x):
    return hashlib.sha256(np.asarray(x, dtype='<f8').tobytes()).hexdigest()


def features(raw):
    start, cycles = raw['initial_features'], raw['diagnostic_features']
    assert start.shape == (4, 4, 4) and cycles.shape == (4, 4, 3, 6)
    return dict(starting_only=start,
                passive=dev.observer_features(start, cycles[:, :, 0], cycles[:, :, 1]),
                challenge=dev.observer_features(start, cycles[:, :, 0], cycles[:, :, 2]))


def forecasts(index, raw, models):
    """No outcomes, parent history or identifiers enter the predictor."""
    x = features(raw)
    groups = np.tile(np.arange(4, dtype=np.int64), 4)
    predicted = {k: predictor.predict(models['fits'][k]['model'], v.reshape(16, -1), groups)
                 for k, v in x.items()}
    return [dict(block=index, life=life, family=role, writer=mode,
                 features={k: v[life, ci].tolist() for k, v in x.items()},
                 feature_sha256={k: feature_hash(v[life, ci]) for k, v in x.items()},
                 predictions={k: float(v[4*life+ci]) for k, v in predicted.items()})
            for life in range(4) for ci, (role, mode) in enumerate(dev.CASES)]


def check_forecasts(rows, indexes, blocks, models):
    """Reconstruct inference directly, without production feature/inference calls."""
    assert len(rows) == len(indexes)*16 and len(blocks) == len(indexes)
    for bi, (index, raw) in enumerate(zip(indexes, blocks)):
        for life in range(4):
            for ci, (role, mode) in enumerate(independent.CASES):
                row = rows[16*bi+4*life+ci]
                assert set(row) == {'block', 'life', 'family', 'writer', 'features',
                                    'feature_sha256', 'predictions'}
                assert (row['block'], row['life'], row['family'], row['writer']) == (index, life, role, mode)
                start = raw['initial_features'][life, ci]
                probes = raw['diagnostic_features'][life, ci]
                x = {'starting_only': start, 'passive': np.r_[start, probes[0], probes[1]],
                     'challenge': np.r_[start, probes[0], probes[2]]}
                for key in ('features', 'feature_sha256', 'predictions'):
                    assert set(row[key]) == set(MODEL_NAMES)
                for key, values in x.items():
                    np.testing.assert_array_equal(row['features'][key], values)
                    assert row['feature_sha256'][key] == hashlib.sha256(values.astype('<f8').tobytes()).hexdigest()
                    model = models['fits'][key]['model']
                    centered = values - np.array(model['group_feature_means'][ci])
                    value = model['group_outcome_means'][ci]
                    value += sum(centered[j] / model['scales'][j] * model['coefficients'][j]
                                 for j in range(len(values)))
                    np.testing.assert_allclose(row['predictions'][key], max(-1., min(1., value)), atol=1e-12, rtol=0)
    return True


def observations(blocks):
    assert len(blocks) == 16
    y = np.empty((16, 4, 4))
    for bi, block in enumerate(blocks):
        for ci, (role, mode) in enumerate(dev.CASES):
            pi = system.PROBES.index((role, mode))
            values = block['terminal_values'][:, pi, -1]
            y[bi, :, ci] = values[:, 0] - values[:, 1]
    return y


def summarize(rows, blocks):
    y = observations(blocks)
    predictions = {k: np.array([r['predictions'][k] for r in rows]).reshape(16, 4, 4)
                   for k in MODEL_NAMES}
    secondary = {}
    for key, prediction in predictions.items():
        error = prediction-y
        centered = prediction.ravel()-prediction.mean()
        denominator = float(centered @ centered)
        varying = bool(np.any(prediction != prediction.flat[0]))
        slope = float(centered @ (y.ravel()-y.mean())/denominator) if varying else None
        secondary[key] = dict(mse=float(np.mean(error**2)), mae=float(np.mean(abs(error))),
            calibration_slope=slope,
            calibration_intercept=float(y.mean()-slope*prediction.mean()) if slope is not None else None,
            calibration_definition='observed outcome regressed on saved forecast; null if forecast variance is zero',
            group_mse=[float(np.mean(error[:, :, ci]**2)) for ci in range(4)])
    return dict(stage='PROSPECTIVE_HELDOUT', primary=predictor.score(y, predictions['passive'], predictions['challenge']),
        secondary=secondary, controls=system.summarize(blocks),
        both_diagnostics_worse_than_starting=bool(all(secondary[k]['mse'] > secondary['starting_only']['mse']
                                                   for k in ('passive', 'challenge'))),
        outcomes=y.tolist(), cases=[list(c) for c in dev.CASES], blocks=list(system.TISSUES),
        excluded_cases=0, refitted_models=0, automatic_successor=False,
        interpretation_scope='Fixed challenge, sealed ridge models, fixed tissue and guide, two supplied families.')


def check_summary(summary, rows, blocks):
    """Count matches from retained V, then independently reproduce all scores."""
    from . import heldout_lineage_audit as lineage_audit
    assert len(rows) == 256 and len(blocks) == 16
    y = []
    for block in blocks:
        lives = []
        for life in range(4):
            lives.append([independent.terminal_features(
                block['terminal_states'][life, lineage_audit.PROBES.index((role, mode)), -1, 0], role)[0]
                for role, mode in independent.CASES])
        y.append(lives)
    y = np.array(y)
    np.testing.assert_array_equal(summary['outcomes'], y)
    predictions = {k: np.array([r['predictions'][k] for r in rows]).reshape(16, 4, 4) for k in MODEL_NAMES}
    errors = {k: v-y for k, v in predictions.items()}
    block_deltas = np.array([sum((errors['passive'][b]**2-errors['challenge'][b]**2).ravel())/16
                             for b in range(16)])
    draws = np.random.default_rng(14120260917).integers(0, 16, (10000, 16))
    bounds = np.percentile(np.sum(block_deltas[draws], axis=1)/16, [2.5, 97.5])
    pmse = float(np.sum(errors['passive']**2)/256)
    cmse = float(np.sum(errors['challenge']**2)/256)
    label = ('CHALLENGE_PREDICTIVE_GAIN' if bounds[0] > 0 else 'CHALLENGE_PREDICTIVE_HARM'
             if bounds[1] < 0 else 'PREDICTIVE_DIFFERENCE_UNRESOLVED')
    expected = dict(label=label, passive_mse=pmse, challenge_mse=cmse,
        mse_improvement=float(np.sum(block_deltas)/16), ci95=bounds.tolist(),
        block_differences=block_deltas.tolist(), relative_reduction=float(block_deltas.mean()/pmse) if pmse else None,
        passive_mae=float(np.sum(abs(errors['passive']))/256), challenge_mae=float(np.sum(abs(errors['challenge']))/256),
        independent_blocks=16, bootstrap_draws=10000, bootstrap_seed=14120260917)
    independent.nested(summary['primary'], expected)
    expected_secondary = {}
    for key, prediction in predictions.items():
        flat = prediction.ravel()
        if np.any(flat != flat[0]):
            # Independent least-squares calibration; no production covariance formula.
            intercept, slope = np.linalg.lstsq(np.column_stack((np.ones(256), flat)), y.ravel(), rcond=None)[0]
            intercept, slope = float(intercept), float(slope)
        else:
            intercept = slope = None
        expected_secondary[key] = dict(mse=float(np.sum(errors[key]**2)/256),
            mae=float(np.sum(abs(errors[key]))/256), calibration_slope=slope, calibration_intercept=intercept,
            calibration_definition='observed outcome regressed on saved forecast; null if forecast variance is zero',
            group_mse=[float(np.sum(errors[key][:, :, ci]**2)/64) for ci in range(4)])
    independent.nested(summary['secondary'], expected_secondary)
    assert lineage_audit.check_summary(summary['controls'], blocks, system.CONFIG)
    assert summary['both_diagnostics_worse_than_starting'] == all(
        expected_secondary[k]['mse'] > expected_secondary['starting_only']['mse'] for k in ('passive', 'challenge'))
    assert set(summary) == {'stage', 'primary', 'secondary', 'controls', 'both_diagnostics_worse_than_starting',
                            'outcomes', 'cases', 'blocks', 'excluded_cases', 'refitted_models',
                            'automatic_successor', 'interpretation_scope'}
    assert summary['stage'] == 'PROSPECTIVE_HELDOUT'
    assert summary['cases'] == [list(c) for c in independent.CASES] and summary['blocks'] == list(range(90000, 90016))
    assert summary['excluded_cases'] == summary['refitted_models'] == 0 and summary['automatic_successor'] is False
    assert summary['interpretation_scope'] == 'Fixed challenge, sealed ridge models, fixed tissue and guide, two supplied families.'
    return True
