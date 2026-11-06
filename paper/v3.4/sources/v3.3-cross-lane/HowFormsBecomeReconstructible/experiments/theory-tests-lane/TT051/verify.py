"""Read-only reproduction of frozen hashes, predictions and development scores."""
from io_utils import *
import csv
import math
from scipy.special import expit


def main():
    out = ROOT / 'development_v2'
    freeze = read(ROOT / 'INPUT_FREEZE_v2.json')
    for path, expected in freeze['sha256'].items():
        assert sha(path) == expected, path
    complete = read(out / 'COMPLETE.json')
    for name, expected in complete['outputs'].items():
        assert sha(out / name) == expected, name
    model_freeze = read(out / 'MODEL_FREEZE.json')
    artifact = read(out / 'MODELS.json')
    assert sha(out / 'MODELS.json') == model_freeze['model_sha256']
    assert sha(ROOT / 'FEATURE_SCHEMA.json') == model_freeze['feature_schema_sha256']
    assert read(ROOT / 'REVIEW.json')['status'] == 'PASS'
    data = arrays(ROOT / 'DATA.npz')
    schema = read(ROOT / 'FEATURE_SCHEMA.json')
    probabilities = arrays(out / 'PROBABILITIES.npz')
    with (out / 'PREDICTIONS.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    results = read(out / 'RESULTS.json')
    max_error = 0.0
    groups = 0
    for name, metrics in results['metrics'].items():
        for i, row in enumerate(rows):
            assert float(row[name]) == probabilities[name][i]
            assert int(row['outcome']) == data['y'][i]
            assert float(row['weight']) == data['weights'][i]
        selections = [(np.ones(len(rows), bool), metrics['overall'])]
        selections += [(data['blocks'] == b, metrics['blocks'][str(b)]) for b in BLOCKS]
        selections += [((data['injury'] == injury) & (data['noise'] == noise),
                        metrics['conditions'][f'{injury}_{noise}'])
                       for injury in (12, 24, 36) for noise in (False, True)]
        selections += [(data['current_pass'] == k, metrics['original_expression'][str(k)])
                       for k in (0, 1)]
        for mask, saved in selections:
            subset = [row for row, keep in zip(rows, mask, strict=True) if keep]
            total = math.fsum(float(row['weight']) for row in subset)
            values = dict(brier=0.0, bias=0.0, log_loss=0.0)
            terms = {key: [] for key in values}
            for row in subset:
                p, y, w = float(row[name]), int(row['outcome']), float(row['weight'])
                q = min(1 - 1e-12, max(1e-12, p))
                terms['brier'].append(w * (p-y)**2)
                terms['bias'].append(w * (p-y))
                terms['log_loss'].append(-w * (y*math.log(q) + (1-y)*math.log1p(-q)))
            for key in values:
                error = abs(math.fsum(terms[key])/total - saved[key])
                max_error = max(max_error, error)
                assert error < 2e-13, (name, key, error)
            groups += 1
    # Final deployment fits are distinct from outer-fold development predictions.
    # Check their scalar inference without refitting or confusing these two sets.
    import predict
    feature_rows = [dict(key=i, features=dict(zip(schema['all_columns'], row.tolist())))
                    for i, row in enumerate(data['X'])]
    emitted = predict.predict(feature_rows, artifact, tuple(artifact['models']))
    for name, model in artifact['models'].items():
        indices = [schema['all_columns'].index(c) for c in model['columns']]
        base = model['base']
        for i, row in enumerate(data['X']):
            z = [(float(row[j])-float(mu))/float(sd)
                 for j, mu, sd in zip(indices, base['mean'], base['scale'], strict=True)]
            eta = float(base['coefficients'][0]) + math.fsum(
                value*float(coef) for value, coef in zip(z, base['coefficients'][1:], strict=True))
            cal = model['calibration']
            probability = float(expit(cal['intercept'] + cal['slope']*eta))
            assert abs(probability-emitted[i]['probabilities'][name]) < 2e-12
    print(json.dumps(dict(status='PASS', frozen_inputs=len(freeze['sha256']),
                          scored_groups=groups, maximum_score_error=max_error,
                          rows=len(rows), final_models=len(artifact['models']),
                          new_fits=0, new_native_reads=0, writes=0)))


if __name__ == '__main__':
    main()
