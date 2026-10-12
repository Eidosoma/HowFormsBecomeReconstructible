"""D176 independent feature, group-SVD, objective and complete score checks."""
import numpy as np
from . import contextual_prediction as spec
from . import settings_prediction_check as legacy

H = np.array([[-.5, -.5, .5], [-.5, .5, -.5], [.5, -.5, -.5], [.5, .5, .5]])
same = legacy.same
ATOL = 2e-10


def features(data):
    start, a, q = data['start'], data['u0'], data['q']
    result = {}
    for version in ('old', 'settings', 'interaction'):
        for name in ('starting', 'one_copy', 'tied:passive', 'tied:pulse'):
            if version == 'interaction' and name == 'starting': continue
            rows = [start]
            if name != 'starting': rows.append(a)
            if name.startswith('tied:'): rows.append(data['pulse' if name == 'tied:pulse' else 'u1'])
            if version != 'old': rows.append(q)
            if version == 'interaction':
                first = np.empty_like(a)
                for j in range(6): first[..., j] = (q[..., 0]-1)*a[..., j]
                rows.append(first)
                if name.startswith('tied:'):
                    second = np.empty_like(a); value = data['pulse' if name == 'tied:pulse' else 'u1']
                    for j in range(6): second[..., j] = (q[..., 1]-1)*value[..., j]
                    rows.append(second)
            result[version+'/'+name] = np.concatenate(rows, axis=-1)
    return result


def frame(x, y, g, tied):
    width = x.shape[1]
    mu = np.array([np.sum(x[g == k], axis=0)/np.count_nonzero(g == k) for k in range(4)])
    offset = np.array([np.sum(y[g == k])/np.count_nonzero(g == k) for k in range(4)])
    centered = x-mu[g]; scale = np.sqrt(np.sum(centered**2, axis=0)/len(x)); scale[scale <= 1e-12] = 1
    t = np.eye(width)
    if tied:
        assert width in (19, 21, 33)
        t = np.zeros((width, width-(12 if width == 33 else 6)))
        t[:7, :7] = np.eye(7)
        for left, right, col in [(7+j, 13+j, 7+j) for j in range(6)] + (
            [(21+j, 27+j, 15+j) for j in range(6)] if width == 33 else []):
            denominator = np.sqrt(scale[left]**2+scale[right]**2)
            t[left, col], t[right, col] = scale[left]/denominator, scale[right]/denominator
        if width >= 21: t[19, 13] = t[20, 14] = 1
    return mu, offset, scale, t, centered/scale, y-offset[g]


def solution(x, y, g, test, h, alpha, tied):
    mu, offset, scale, t, z, target = frame(x, y, g, tied)
    white = np.eye(4)+.25*np.ones((4, 4))
    a = np.einsum('ig,ij->igj', white[g], z@t).reshape(len(y), -1)
    u, singular, vh = np.linalg.svd(a/np.sqrt(len(y)), full_matrices=False)
    w = (vh.T@((singular/(singular**2+alpha))*(u.T@(target/np.sqrt(len(y)))))).reshape(4, -1)
    group = white@w; eta = np.vstack((group.mean(0), H.T@group)); beta = eta@t.T
    prediction = offset[h]+np.sum((((test-mu[h])/scale)@t)*group[h], axis=1)
    return dict(means=mu, offsets=offset, scale=scale, coefficients=beta, reduced_coefficients=eta), prediction


def model(record, x, y, g, test, h, raw, alpha, key):
    version, name = key.split('/', 1); tied = name.startswith('tied:')
    mu, offset, scale, t, z, target = frame(x, y, g, tied)
    klass = spec.CLASS if version == 'interaction' else (spec.prior.OLD_CLASSES if version == 'old' else spec.prior.NEW_CLASSES)[int(tied)]
    assert record['alpha'] == alpha and record['model_class'] == klass
    for k, value in (('means', mu), ('offsets', offset), ('scale', scale)): same(record[k], value)
    beta = np.asarray(record['coefficients']); assert beta.shape == (4, x.shape[1]) and np.isfinite(beta).all()
    eta = beta@t; same(eta@t.T, beta); same(t.T@t, np.eye(t.shape[1]))
    if 'reduced_coefficients' in record: same(record['reduced_coefficients'], eta)
    slopes = beta[0]+H@beta[1:]
    expected = offset[h]+np.sum(((test-mu[h])/scale)*slopes[h], axis=1)
    same(raw, expected)
    reduced = z@t; design = np.hstack([reduced]+[reduced*H[g, j, None] for j in range(3)])
    gradient = design.T@(design@eta.ravel()-target)/len(y)+alpha*eta.ravel()
    same(gradient, np.zeros_like(gradient))
    tie_error = 0.
    if tied:
        for left, right in ((7, 13),) + (((21, 27),) if len(scale) == 33 else ()):
            difference = beta[:, left:left+6]/scale[left:left+6]-beta[:, right:right+6]/scale[right:right+6]
            same(difference, np.zeros_like(difference)); tie_error = max(tie_error, float(abs(difference).max()))
    proof, svd_raw = solution(x, y, g, test, h, alpha, tied)
    for k, value in proof.items():
        if k != 'reduced_coefficients' or k in record: same(record[k], value)
    same(raw, svd_raw)
    objective = float(np.mean((design@eta.ravel()-target)**2)+alpha*np.sum(beta*beta))
    return dict(objective=objective, stationarity=float(abs(gradient).max()), tie=tie_error,
                svd=float(abs(raw-svd_raw).max()))


def fits(data, predictions, raw, records, refs_p, refs_raw, refs):
    n = spec.validate(data); x = features(data); ids = data['block_ids']
    same(x, spec.panels({k: data[k] for k in spec.MEASUREMENTS}))
    for box in (predictions, raw, records): assert set(box) == set(spec.KEYS)
    for box in (refs_p, refs_raw, refs): assert set(box) == set(spec.REFERENCES)
    for key in spec.REFERENCES:
        np.testing.assert_array_equal(predictions[key], refs_p[key]); np.testing.assert_array_equal(raw[key], refs_raw[key])
        assert records[key] == refs[key], 'reference coefficients/records must be unchanged'
    y = (data['futures'].sum(-1)/4).ravel(); g = np.tile(np.arange(4, dtype=np.int64), n*4)
    owner = np.repeat(np.arange(n), 16); checks = {}; maxima = np.zeros(3)
    for key in spec.KEYS:
        xx = x[key].reshape(n*16, -1); record = records[key]
        assert record['observer'] == key.split('/', 1)[1] and record['blocks'] == ids.tolist()
        assert record['alphas'] == [.001, .01, .1] and record['target'] == 'future_mean'
        assert len(record['folds']) == n and predictions[key].shape == raw[key].shape == (3, n, 4, 4)
        np.testing.assert_array_equal(predictions[key], np.clip(raw[key], -1, 1))
        checks[key] = []
        for block, fold in enumerate(record['folds']):
            assert fold['validation_block'] == int(ids[block])
            assert fold['training_blocks'] == ids[np.arange(n) != block].tolist() and len(fold['models']) == 3
            train, test = owner != block, owner == block; proof = []
            for i, alpha in enumerate((.001, .01, .1)):
                r = model(fold['models'][i], xx[train], y[train], g[train], xx[test], g[test], raw[key][i, block].ravel(), alpha, key)
                maxima = np.maximum(maxima, [r['stationarity'], r['tie'], r['svd']]); proof.append(r)
            checks[key].append(proof)
    nesting_max = -float('inf'); nested = 0
    for new, old in [('settings/'+k, 'old/'+k) for k in spec.OBSERVERS] + [('interaction/'+k, 'settings/'+k) for k in spec.OBSERVERS[1:]]:
        width = x[old].shape[-1]
        np.testing.assert_array_equal(x[new][..., :width], x[old])
        for block in range(n):
            train = owner != block; xn = x[new].reshape(n*16, -1)[train]
            for i, alpha in enumerate((.001, .01, .1)):
                nm, om = records[new]['folds'][block]['models'][i], records[old]['folds'][block]['models'][i]
                same(np.asarray(nm['means'])[:, :width], om['means']); same(nm['scale'][:width], om['scale'])
                same(nm['offsets'], om['offsets'])
                beta = np.pad(np.asarray(om['coefficients']), ((0, 0), (0, xn.shape[-1]-width)))
                mu, offset, scale, t, z, target = frame(xn, y[train], g[train], new.split('/', 1)[1].startswith('tied:'))
                same(beta@t@t.T, beta)
                slopes = beta[0]+H@beta[1:]
                obj = float(np.mean((np.sum(z*slopes[g[train]], axis=1)-target)**2)+alpha*np.sum(beta*beta))
                same(obj, checks[old][block][i]['objective'])
                change = checks[new][block][i]['objective']-obj
                assert change <= ATOL, 'nested un-clipped training optimum'
                nesting_max = max(nesting_max, change); nested += 1
    return dict(passes=True, models_checked=n*33, new_models=n*12, reused_models=n*21,
        reference_refits=0, nested_objectives=nested, maximum_objective_change=nesting_max,
        max_stationarity=float(maxima[0]), max_raw_tie=float(maxima[1]), max_svd_prediction=float(maxima[2]),
        whole_founder_exclusions_checked=True)


def report(data, predictions, raw, summary, losses):
    f = data['futures']; n = len(f)
    meta = dict(schema='d176_contextual_prediction_v1', blocks=data['block_ids'].tolist(), cases=n*16,
        new_fits=n*12, reused_models=n*21, new_predictions=n*192, actual_reference_refits=0,
        focal=['interaction/tied:pulse', 'interaction/tied:passive', .01], prospective_evidence=False,
        confidence_intervals=False, equivalence=False, deployment_selected=False, new_dynamics=0, automatic_successor=False)
    panels = {'absolute', 'comparisons', 'gap_changes', 'selected_cheap', 'selected_contexts'}
    same({k: value for k, value in summary.items() if k not in panels}, meta)
    assert set(losses) == set(summary['absolute']) == set(spec.KEYS)
    errors = {}
    for key in spec.KEYS:
        errors[key] = np.sum(np.square(predictions[key][..., None]-f), axis=-1)/4
        same(losses[key], errors[key])
        assert len(summary['absolute'][key]) == 3
        for i in range(3):
            row = dict(summary['absolute'][key][i]); row['irreducible_future_variance'] = row.pop('future_dispersion')
            legacy.metric_check(row, predictions[key][i], raw[key][i], f)
    pairs = [('settings/'+k, 'old/'+k) for k in ('starting', 'one_copy', 'tied:passive', 'tied:pulse')]
    pairs += [('interaction/'+k, v+'/'+k) for v in ('settings', 'old') for k in ('one_copy', 'tied:passive', 'tied:pulse')]
    pairs += [(v+'/tied:pulse', v+'/tied:passive') for v in ('old', 'settings', 'interaction')]
    cheap = ('old/starting', 'old/one_copy', 'settings/starting', 'settings/one_copy', 'interaction/one_copy')
    two = tuple(v+'/'+k for v in ('old', 'settings', 'interaction') for k in ('tied:passive', 'tied:pulse'))
    pairs += [(k, c) for k in two for c in cheap]
    pairs += [(v+'/one_copy', ('settings' if v == 'interaction' else v)+'/starting') for v in ('old', 'settings', 'interaction')]
    assert len(pairs) == 46 and len(summary['comparisons']) == 138
    for row, (c, r, i) in zip(summary['comparisons'], ((c, r, i) for c, r in pairs for i in range(3))):
        gain = errors[r][i]-errors[c][i]
        mean = f.sum(-1)/4
        np.testing.assert_allclose(gain, (predictions[r][i]-mean)**2-(predictions[c][i]-mean)**2, atol=1e-14, rtol=0)
        legacy.gain_check(row, gain, dict(candidate=c, reference=r, alpha=(.001, .01, .1)[i]))
    assert len(summary['gap_changes']) == 9
    for row, (before, after, i) in zip(summary['gap_changes'],
            ((b, a, i) for b, a in (('old', 'settings'), ('settings', 'interaction'), ('old', 'interaction')) for i in range(3))):
        gain = errors[after+'/tied:passive'][i]-errors[after+'/tied:pulse'][i]-errors[before+'/tied:passive'][i]+errors[before+'/tied:pulse'][i]
        legacy.gain_check(row, gain, dict(before=before, after=after, alpha=(.001, .01, .1)[i]))
    assert set(summary['selected_cheap']) == set(cheap) and len(summary['selected_contexts']) == 30
    for key in cheap:
        scores = errors[key].mean((1, 2, 3)); best = max(i for i in range(3) if scores[i] <= min(scores)+1e-12)
        same(summary['selected_cheap'][key], dict(index=best, alpha=(.001, .01, .1)[best],
            metrics=summary['absolute'][key][best], selection_affected=True))
    for row, (c, r) in zip(summary['selected_contexts'], ((c, r) for c in two for r in cheap)):
        choice = summary['selected_cheap'][r]
        legacy.gain_check(row, errors[r][choice['index']]-errors[c][1], dict(candidate=c, candidate_alpha=.01,
            reference=r, reference_alpha=choice['alpha'], selection_affected=True))
    return dict(passes=True, absolute_rows=33, comparisons=138, gap_changes=9, selected_contexts=30,
        mean_future_gain_identity=True, all_cases_founders_groups_retained=True)
