"""Frozen low-dimensional ridge recipe; complete block holdout only."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'protocol.json').read_text())
FEATURES = {
    'candidate': ['independent', 'transfer', 'transfer_change'],
    'packet_blind': ['independent', 'transfer'],
    'ordinary_risk': ['independent', 'ordinary_risk'],
    'direct_risk': ['independent', 'direct_risk'],
    'successor_risk': ['independent', 'successor_risk'],
}
MODELS = ('zero', 'regime_mean', *FEATURES)
REGIMES = ('matched', 'independent')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fit(records, model):
    require(bool(records), 'Empty training fold')
    blocks = sorted({r['block'] for r in records})
    weights = np.array([r['weight'] for r in records], float)
    require(np.all(weights > 0) and np.isfinite(weights).all(), 'Invalid weights')
    y = np.array([r['benefit'] for r in records], float)
    require(np.isfinite(y).all() and np.all(abs(y) <= 1), 'Invalid paired targets')
    weights /= weights.sum()
    state = dict(model=model, train_blocks=blocks, training_records=len(records))
    if model == 'zero':
        return state
    if model == 'regime_mean':
        state['means'] = {}
        for regime in REGIMES:
            mask = np.array([r['regime'] == regime for r in records])
            require(mask.any(), 'Both regimes required in every training fold')
            state['means'][regime] = float(np.dot(weights[mask], y[mask]) / weights[mask].sum())
        return state
    names = FEATURES[model]
    x = np.array([[r['features'][n] for n in names] for r in records], float)
    require(np.isfinite(x).all(), 'Nonfinite feature')
    mean = weights @ x
    sd = np.sqrt(weights @ (x - mean) ** 2)
    scale = np.where(sd > P['fit']['scale_floor'], sd, 1.)
    z = (x - mean) / scale
    intercept = float(weights @ y)
    covariance = z.T @ (weights[:, None] * z)
    matrix = covariance + P['fit']['ridge_penalty'] * np.eye(len(names))
    target = z.T @ (weights * (y - intercept))
    coefficients = np.linalg.solve(matrix, target)
    state.update(features=names, center=mean.tolist(), scale=scale.tolist(), intercept=intercept,
        coefficients=coefficients.tolist(), ridge_penalty=P['fit']['ridge_penalty'])
    return state


def predict(row, state):
    if state['model'] == 'zero':
        return 0.
    if state['model'] == 'regime_mean':
        return state['means'][row['regime']]
    z = (np.array([row['features'][n] for n in state['features']]) - state['center']) / state['scale']
    return float(np.clip(state['intercept'] + z @ state['coefficients'], -1, 1))


def fold(records, block):
    training = [r for r in records if r['block'] != block]
    testing = [r for r in records if r['block'] == block]
    require(training and testing, 'Nonempty train and held-out blocks required')
    models = {name: fit(training, name) for name in MODELS}
    require(all(block not in s['train_blocks'] for s in models.values()), 'Held-out block leaked into fitting')
    predictions = [dict(key=r['key'], regime=r['regime'], block=block,
        predictions={name: predict(r, state) for name, state in models.items()}) for r in testing]
    return models, predictions


def evaluate(records, predictions):
    blocks = sorted({r['block'] for r in records})
    expected = {(tuple(r['key']), r['regime']) for r in records}
    p = {(tuple(r['key']), r['regime']): r for r in predictions}
    require(len(expected) == len(records) == len(predictions) == len(p) and set(p) == expected, 'Prediction coverage')
    require(all(set(r['predictions']) == set(MODELS) for r in predictions), 'Model coverage')
    require(all(np.isfinite(v) and -1 <= v <= 1 for r in predictions for v in r['predictions'].values()), 'Invalid benefit predictions')
    result = dict(records=len(records), acquisition_blocks=len(blocks), regimes={}, development_only=True)
    gates = []
    for regime in REGIMES:
        selected = [r for r in records if r['regime'] == regime]
        value = dict(scores={}, block_scores={}, comparator_gains={}, policies={})
        for model in MODELS:
            block_scores = []
            for b in blocks:
                group = [r for r in selected if r['block'] == b]
                require(group, 'Missing block/regime')
                block_scores.append(float(sum(r['weight'] * (r['benefit'] - p[tuple(r['key']), regime]['predictions'][model]) ** 2 for r in group) / sum(r['weight'] for r in group)))
            value['block_scores'][model] = block_scores
            value['scores'][model] = float(np.mean(block_scores))
        for model in MODELS:
            if model == 'candidate':
                continue
            gain = value['scores'][model] - value['scores']['candidate']
            value['comparator_gains'][model] = dict(mean_gain=gain,
                block_values=(np.array(value['block_scores'][model]) - value['block_scores']['candidate']).tolist(),
                candidate_better=gain > 0)
            gates.append(gain > 0)
        for model in (*MODELS, 'repair_all', 'no_repair'):
            policy_values, interventions = [], []
            for r in selected:
                apply = model == 'repair_all' or (model not in ('repair_all', 'no_repair') and p[tuple(r['key']), regime]['predictions'][model] > 0)
                policy_values.append((r, r['control'] + int(apply) * r['benefit']))
                interventions.append(int(apply))
            weighted_outcome = sum(r['weight'] * y for r, y in policy_values) / sum(r['weight'] for r in selected)
            value['policies'][model] = dict(weighted_terminal_success=float(weighted_outcome),
                applied_repairs=sum(interventions), records=len(selected),
                extra_native_probe_reads=len(selected) * P['costs']['extra_native_probes'].get(model, 0),
                dry_run_optimizer_calls=len(selected) if model == 'candidate' else 0,
                total_deployment_optimizer_calls=len(selected) if model == 'candidate' else sum(interventions),
                cost_scope='Applied repairs and sensing/solver work reported separately; not a matched-full-budget policy test.')
        result['regimes'][regime] = value
    result['advance_gate_pass'] = all(gates)
    result['decision'] = 'DEVELOPMENT_SCREEN_PASS' if all(gates) else 'DEVELOPMENT_SCREEN_FAILED'
    result['interpretation'] = 'Exposed-data whole-block development diagnostic, with no inferential claim from overlapping fitted folds and no new-founder validation.'
    return result
