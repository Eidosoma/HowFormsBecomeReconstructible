"""Evaluate unchanged TT008 logistic coefficients; no calibration or fitting API."""
import math


MODELS = ('candidate', 'expression_history', 'expression_unsigned')


def predict(row, model):
    if model['type'] != 'logistic':
        raise ValueError('Only the three frozen principal logistic models')
    columns = model['columns']
    weights = model['coefficients']
    means, scales = model['scaling']['mean'], model['scaling']['scale']
    if len(weights) != len(columns)+1 or len(means) != len(columns) or len(scales) != len(columns):
        raise ValueError('Frozen feature/scaling dimensions')
    terms = [float(weights[0])]
    for name, weight, mean, scale in zip(columns, weights[1:], means, scales, strict=True):
        value = float(row['history'] == name.split('=', 1)[1]) if name.startswith('history=') else float(row[name])
        if not all(map(math.isfinite, (value, weight, mean, scale))) or scale <= 0:
            raise ValueError('Finite feature and positive frozen scale')
        terms.append(weight*(value-mean)/scale)
    z = math.fsum(terms)
    if z >= 0:
        return 1/(1+math.exp(-z))
    ez = math.exp(z)
    return ez/(1+ez)
