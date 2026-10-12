"""D165 no-fit transport of saved whole-founder-excluded prediction rules."""
import numpy as np
from . import asymmetry as a

CALIBRATION = ('passive', 'sham_plus', 'sham_minus')
CLASS = 'condition_blind_equal_three_view_ridge_v1'
CHEAP_CLASS = 'common_plus_zero_sum_group_deviations_penalty_ratio_1'
TARGETS = ['original', 'future0', 'future1', 'future2', 'future3', 'future_mean']


def registry(shared, cheap):
    """Select saved rules, checking identity; no training data/outcome argument."""
    ids = shared['training_blocks']; n = len(ids)
    assert n >= 3 and len(set(ids)) == n and all(type(i) is int for i in ids)
    assert shared['schema'] == 'd164_shared_models_v1'
    assert shared['calibration'] == list(CALIBRATION)
    assert shared['encodings'] == list(a.ENCODINGS) and shared['alphas'] == list(a.ALPHAS)
    assert shared['new_fits'] == 9*(n+1) and shared['target'] == 'four_future_mean'
    assert shared['pilot_outcomes_used'] is shared['condition_indicator'] is shared['inner_selection'] is False
    assert set(shared['models']) == set(a.ENCODINGS)
    result = []
    for b, held in enumerate(ids):
        train = ids[:b]+ids[b+1:]; models = {}
        for e in a.ENCODINGS:
            record = shared['models'][e]
            assert record['training_blocks'] == ids and len(record['folds']) == n
            fold = record['folds'][b]
            assert fold['validation_block'] == held and fold['training_blocks'] == train
            assert len(fold['models']) == 3
            for ai, model in enumerate(fold['models']):
                assert model['alpha'] == a.ALPHAS[ai] and model['encoding'] == e
                assert model['model_class'] == CLASS and model['calibration'] == list(CALIBRATION)
                assert model['training_rows'] == 48*(n-1) and model['unique_training_cases'] == 16*(n-1)
                _, w = a.affine(model, 13 if e == 'mean' else 19)
                if e == 'tied':np.testing.assert_allclose(w[:,7:13], w[:,13:], atol=2e-10, rtol=0)
            for k in a.EDITS:models[e+':'+k] = fold['models']
        for name in ('starting', 'one_copy'):
            record = cheap[name]
            assert record['blocks'] == ids and record['alphas'] == list(a.ALPHAS)
            assert record['observer'] == name and record['model_class'] == CHEAP_CLASS
            assert record['training_targets'] == TARGETS and record['inner_selection'] is False
            assert record['prospective_evidence'] is False
            assert record['preprocessing'] == 'training-only within each whole-founder fold'
            assert len(record['folds']) == n
            fold = record['folds'][b]
            assert fold['validation_block'] == held and fold['training_blocks'] == train
            assert len(fold['models']) == 6 and len(fold['models'][5]) == 3
            for ai, model in enumerate(fold['models'][5]):
                assert model['alpha'] == a.ALPHAS[ai] and model['model_class'] == CHEAP_CLASS
                a.affine(model, 7 if name == 'starting' else 13)
            models[name] = fold['models'][5]
        result.append(dict(validation_block=held, training_blocks=train, models=models))
    return result


def forecasts(rules, features, heldout_ids=None):
    """Pilot: rule x alpha x founder x life x group. Heldout: no rule axis."""
    x = a.feature_matrices(features); n = len(features['start']); raw = {}
    if heldout_ids is not None:
        assert heldout_ids.dtype == np.int64 and heldout_ids.shape == (len(rules),)
        assert heldout_ids.tolist() == [r['validation_block'] for r in rules] and n == len(rules)
    for name in a.OBSERVERS:
        rows = []
        for b, rule in enumerate(rules):
            assert rule['validation_block'] not in rule['training_blocks']
            values = x[name] if heldout_ids is None else x[name][b:b+1]
            batch = []
            for model in rule['models'][name]:
                intercept, slopes = a.affine(model, values.shape[-1])
                batch.append(intercept+(values*slopes).sum(-1))
            rows.append(np.stack(batch))
        value = np.stack(rows)
        raw[name] = value if heldout_ids is None else np.transpose(value[:,:,0], (1,0,2,3))
    return {k:np.clip(v,-1,1) for k,v in raw.items()}, raw


def validate(p, raw, y, ids):
    n = len(ids)
    assert n >= 1 and ids.shape == (n,) and ids.dtype == np.int64 and len(set(ids)) == n
    assert y.shape == (n,4,4,4) and y.dtype == np.float64 and np.isfinite(y).all() and np.max(abs(y)) <= 1
    assert set(p) == set(raw) == set(a.OBSERVERS)
    nr = p['starting'].shape[0]
    assert nr >= 1
    for name in p:
        for v in (p[name],raw[name]):
            assert v.shape == (nr,3,n,4,4) and v.dtype == np.float64 and np.isfinite(v).all()
        assert np.array_equal(p[name],np.clip(raw[name],-1,1))
    return nr


def moments(p, raw, y, ids):
    nr = validate(p,raw,y,ids); values = {}
    for name in a.OBSERVERS:
        error = p[name][...,None]-y
        values[name] = dict(loss=(error*error).mean(0), absolute=abs(error).mean(0),
                            signed=error.mean(0), clipped=np.count_nonzero(p[name]!=raw[name],axis=(0,2,3,4)))
    return values, nr


def reductions(value):
    assert value.ndim == 4 and value.shape[1:] == (4,4,4) and np.isfinite(value).all()
    blocks = value.mean((1,2,3)); futures = value.mean((0,1,2)); n = len(value)
    return dict(overall=float(value.mean()), blocks=blocks.tolist(), groups=value.mean((0,1,3)).tolist(),
                futures=futures.tolist(), omit_founder=((blocks.sum()-blocks)/(n-1)).tolist() if n>1 else None,
                omit_future=((futures.sum()-futures)/3).tolist())


def loss(values, name, ai):
    return sum(w*values[k]['loss'][ai] for k,w in a.members(name))


def contrast(candidate, reference):
    ref = float(reference.mean()); cand = float(candidate.mean())
    return dict(candidate_mse=cand, reference_mse=ref,
                relative_gain_percent=100*(ref-cand)/ref if ref else None, **reductions(reference-candidate))


def panel(values, nr, ids, y):
    absolute = {}
    for name in a.OBSERVERS:
        v = values[name]; rows = []
        for ai, alpha in enumerate(a.ALPHAS):
            mse = float(v['loss'][ai].mean()); r = reductions(v['loss'][ai])
            rows.append(dict(alpha=alpha, mse=mse, rmse_points=100*np.sqrt(mse),
                mae_points=100*float(v['absolute'][ai].mean()), bias_points=100*float(v['signed'][ai].mean()),
                clipped=int(v['clipped'][ai]), blocks=r['blocks'], groups=r['groups'], futures=r['futures']))
        absolute[name] = rows
    rows = []
    for spec in a.specifications():
        c = loss(values,spec['candidate'],a.ALPHAS.index(spec['candidate_alpha']))
        r = loss(values,spec['reference'],a.ALPHAS.index(spec['reference_alpha']))
        rows.append(dict(**spec,**contrast(c,r)))
    return dict(ids=ids.tolist(), founders=len(ids), cases=16*len(ids), futures=4, calibrations=nr,
        forecast_instances_per_observer_alpha=nr*16*len(ids), absolute=absolute, comparisons=rows,
        within_future_variance=float(np.var(y,axis=-1).mean()), calibration_averaging='loss_not_prediction')


def single(p):return {k:v[None] for k,v in p.items()}


def summarize(p, raw, dev, full, calibration_ids):
    dp, dr, dy, di = dev; fp, fr, py, pi = full
    assert di.tolist() == list(calibration_ids) and not set(di)&set(pi)
    dm, dn = moments(single(dp),single(dr),dy,di)
    pm, pn = moments(p,raw,py,pi)
    fm, fn = moments(single(fp),single(fr),py,pi)
    assert pn == len(di)
    cohorts = dict(development=panel(dm,dn,di,dy), pilot=panel(pm,pn,pi,py), full16_pilot=panel(fm,fn,pi,py))
    folds = []
    for b, held in enumerate(di):
        d = {k:{field:v[:,b:b+1] if field!='clipped' else
                     np.count_nonzero(dp[k][:,b:b+1]!=dr[k][:,b:b+1],axis=(1,2,3))
                 for field,v in row.items()} for k,row in dm.items()}
        pc = {k:v[b:b+1] for k,v in p.items()}; rc = {k:v[b:b+1] for k,v in raw.items()}
        v, n = moments(pc,rc,py,pi)
        folds.append(dict(validation_block=int(held), training_blocks=di[di!=held].tolist(),
            development=panel(d,1,di[b:b+1],dy[b:b+1]), pilot=panel(v,n,pi,py)))
    changes = []
    for name in a.OBSERVERS+tuple(e+':mean_sham_loss' for e in a.ENCODINGS):
        for ai,alpha in enumerate(a.ALPHAS):
            changes.append(dict(observer=name,alpha=alpha,**contrast(loss(pm,name,ai),loss(fm,name,ai))))
    cohort_changes = []
    for j,spec in enumerate(a.specifications()):
        values = [f['pilot']['comparisons'][j]['overall']-f['development']['comparisons'][j]['overall'] for f in folds]
        cohort_changes.append(dict(**spec,pilot_minus_development_gain=float(np.mean(values)),calibrations=values))
    return dict(schema='d165_decoder_transport_v1',cohorts=cohorts,calibrations=folds,
        transport_vs_full16=changes,cohort_gain_changes=cohort_changes,
        new_fits=0,new_forecasts=51*len(di)*16*len(pi),saved_rules=15*len(di),
        reconstructed_development_forecasts=51*16*len(di),post_test_explanation=True,
        prospective_evidence=False,confidence_intervals=False,source_primary_unchanged=True,
        new_dynamics=0,new_diagnostic_cycles=0,new_founders=0,automatic_successor=False)
