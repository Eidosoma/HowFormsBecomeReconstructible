"""Scalar reductions under a distinct name from the inherited dynamics audit."""
import math
from core import FEATURES, MODELS, REGIMES, P, require


def near(a, b):
    require(math.isfinite(a) and math.isfinite(b) and abs(a - b) <= 1e-11, 'Independent scalar audit disagreement')


def solve(matrix, target):
    n = len(target)
    a = [list(row) + [value] for row, value in zip(matrix, target, strict=True)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        require(abs(a[pivot][col]) > 1e-14, 'Singular audit system')
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        a[col] = [v / divisor for v in a[col]]
        for row in range(n):
            if row == col:
                continue
            multiplier = a[row][col]
            a[row] = [v - multiplier * q for v, q in zip(a[row], a[col], strict=True)]
    return [row[-1] for row in a]


def check_fit(rows, model, state):
    require(state['train_blocks'] == sorted({r['block'] for r in rows}), 'Independent training-block check')
    require(state['training_records'] == len(rows) and state['model'] == model, 'Fit metadata changed')
    total = math.fsum(r['weight'] for r in rows)
    w = [r['weight'] / total for r in rows]
    y = [r['benefit'] for r in rows]
    if model == 'zero':
        return
    if model == 'regime_mean':
        for regime in REGIMES:
            selected = [r for r in rows if r['regime'] == regime]
            near(state['means'][regime], math.fsum(r['weight'] * r['benefit'] for r in selected) / math.fsum(r['weight'] for r in selected))
        return
    names = FEATURES[model]
    means = [math.fsum(weight * r['features'][name] for weight, r in zip(w, rows, strict=True)) for name in names]
    scales = []
    for name, mean in zip(names, means, strict=True):
        variance = math.fsum(weight * (r['features'][name] - mean) ** 2 for weight, r in zip(w, rows, strict=True))
        sd = math.sqrt(variance)
        scales.append(sd if sd > P['fit']['scale_floor'] else 1.)
    z = [[(r['features'][name] - mean) / scale for name, mean, scale in zip(names, means, scales, strict=True)] for r in rows]
    intercept = math.fsum(a * b for a, b in zip(w, y, strict=True))
    matrix = [[math.fsum(weight * values[j] * values[k] for weight, values in zip(w, z, strict=True)) + (P['fit']['ridge_penalty'] if j == k else 0) for k in range(len(names))] for j in range(len(names))]
    target = [math.fsum(weight * values[j] * (value - intercept) for weight, values, value in zip(w, z, y, strict=True)) for j in range(len(names))]
    coefficients = solve(matrix, target)
    require(state['features'] == names and state['ridge_penalty'] == P['fit']['ridge_penalty'], 'Ridge specification mismatch')
    near(state['intercept'], intercept)
    for field, values in (('center', means), ('scale', scales), ('coefficients', coefficients)):
        for a, b in zip(state[field], values, strict=True): near(a, b)


def predict(row, model):
    if model['model'] == 'zero':
        return 0.
    if model['model'] == 'regime_mean':
        return model['means'][row['regime']]
    value = model['intercept'] + math.fsum(c * (row['features'][n] - m) / s for n, m, s, c in zip(model['features'], model['center'], model['scale'], model['coefficients'], strict=True))
    return max(-1., min(1., value))


def evaluate(records, folds, predictions, result):
    blocks = sorted({r['block'] for r in records})
    rows = {(tuple(r['key']), r['regime']): r for r in records}
    forecast = {(tuple(p['key']), p['regime']): p for p in predictions}
    require(len(rows) == len(records) == len(forecast) == len(predictions) and set(rows) == set(forecast), 'Independent full prediction coverage')
    require(set(folds) == {str(b) for b in blocks}, 'Independent fold coverage')
    for block in blocks:
        models = folds[str(block)]
        require(set(models) == set(MODELS), 'Independent model coverage')
        training = [r for r in records if r['block'] != block]
        for model, state in models.items():
            check_fit(training, model, state)
        for row in [r for r in records if r['block'] == block]:
            p = forecast[tuple(row['key']), row['regime']]
            require(p['block'] == block, 'Held-out prediction attached to wrong block')
            for name, state in models.items(): near(p['predictions'][name], predict(row, state))
    gates = []
    for regime in REGIMES:
        saved = result['regimes'][regime]
        selected = [r for r in records if r['regime'] == regime]
        for model in MODELS:
            errors = []
            for b in blocks:
                group = [r for r in selected if r['block'] == b]
                denom = math.fsum(r['weight'] for r in group)
                error = math.fsum(r['weight'] * (r['benefit'] - forecast[tuple(r['key']), regime]['predictions'][model]) ** 2 for r in group) / denom
                errors.append(error)
            near(saved['scores'][model], math.fsum(errors) / len(blocks))
            for a, b in zip(errors, saved['block_scores'][model], strict=True): near(a, b)
            if model != 'candidate':
                gain = saved['scores'][model] - saved['scores']['candidate']
                near(gain, saved['comparator_gains'][model]['mean_gain'])
                require(saved['comparator_gains'][model]['candidate_better'] == (gain > 0), 'Wrong comparator gate')
                for i, value in enumerate(saved['comparator_gains'][model]['block_values']):
                    near(value, errors[i] - saved['block_scores']['candidate'][i])
                gates.append(gain > 0)
        for model in (*MODELS, 'repair_all', 'no_repair'):
            values, apply = [], []
            for r in selected:
                chosen = model == 'repair_all' or (model not in ('repair_all', 'no_repair') and forecast[tuple(r['key']), regime]['predictions'][model] > 0)
                apply.append(chosen)
                values.append(r['weight'] * (r['repaired'] if chosen else r['control']))
            policy = saved['policies'][model]
            near(policy['weighted_terminal_success'], math.fsum(values) / math.fsum(r['weight'] for r in selected))
            require(policy['applied_repairs'] == sum(apply), 'Policy repair count')
            require(policy['extra_native_probe_reads'] == len(selected) * P['costs']['extra_native_probes'].get(model, 0), 'Probe cost mismatch')
            require(policy['dry_run_optimizer_calls'] == (len(selected) if model == 'candidate' else 0), 'Dry-run costs missing')
            require(policy['total_deployment_optimizer_calls'] == (len(selected) if model == 'candidate' else sum(apply)), 'Deployment solver cost mismatch')
    require(result['advance_gate_pass'] == all(gates), 'Wrong advancement decision')
    require(result['decision'] == ('DEVELOPMENT_SCREEN_PASS' if all(gates) else 'DEVELOPMENT_SCREEN_FAILED'), 'Wrong screen label')
    return dict(status='PASS', acquisition_blocks=len(blocks), held_out_records=len(records),
        audited_fold_models=len(blocks) * len(MODELS), comparator_checks=len(gates), independent_scalar_solver=True,
        independent_scores_and_policy_costs=True, no_training_test_block_overlap=True)
