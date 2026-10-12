"""D162 prospective founder-block scoring; one primary and full secondary panel."""
import numpy as np
from . import pilot_models as models, target_models, difference_ablation, recovery_check

SEED=16120260920;DRAWS=20000
PAIRS=tuple(target_models.observer_pairs())+difference_ablation.PAIRS
PRIMARY=('tied:sham_minus','tied:passive')


def calibration(p,y):
    x=np.broadcast_to(p[...,None],y.shape).ravel();t=y.ravel()
    variance=float(np.mean((x-x.mean())**2))
    slope=float(np.mean((x-x.mean())*(t-t.mean()))/variance) if variance else None
    return dict(intercept=float(t.mean()-slope*x.mean()) if slope is not None else None,slope=slope)


def contrast(c,r,draws):
    d=r-c;v=d.mean(axis=(1,2,3));b=float(r.mean());gain=float(v.mean())
    return dict(candidate_mse=float(c.mean()),reference_mse=b,mse_reduction=gain,
        relative_reduction_percent=100*gain/b if b else None,block_differences=v.tolist(),
        group_differences=d.mean(axis=(0,1,3)).tolist(),future_differences=d.mean(axis=(0,1,2)).tolist(),
        block_bootstrap_95=np.quantile(v[draws].mean(1),[.025,.975]).tolist())


def summarize(predictions,raw,y,ids):
    n=len(ids)
    assert n>=1 and len(set(ids))==n and y.shape==(n,4,4,4) and np.isfinite(y).all() and np.max(abs(y))<=1
    assert set(predictions)==set(raw)==set(models.OBSERVERS)
    draws=np.random.default_rng(SEED).integers(0,n,(DRAWS,n));all_scores={};loss={}
    for k in models.OBSERVERS:
        p=predictions[k];assert p.shape==(3,n,4,4) and np.isfinite(p).all() and np.max(abs(p))<=1
        e=p[...,None]-y[None];loss[k]=e*e
        all_scores[k]=[]
        for a in range(3):
            score=target_models.error_stats(e[a]);score.update(alpha=models.ALPHAS[a],
                future_mse=loss[k][a].mean((0,1,2)).tolist(),mean_target_mse=float(np.mean((p[a]-y.mean(-1))**2)),
                calibration=calibration(p[a],y),clipped=int(np.count_nonzero(p[a]!=raw[k][a])))
            all_scores[k].append(score)
    for e in ('separate','mean','tied'):loss[e+':mean_sham_loss']=(loss[e+':sham_plus']+loss[e+':sham_minus'])/2
    comparisons=[dict(candidate=c,reference=r,alpha=alpha,**contrast(loss[c][a],loss[r][a],draws))
        for a,alpha in enumerate(models.ALPHAS) for c,r in PAIRS]
    primary=next(row for row in comparisons if (row['candidate'],row['reference'])==PRIMARY and row['alpha']==.01)
    lo,hi=primary['block_bootstrap_95'];label='FIXED_PROBE_PREDICTIVE_GAIN' if lo>0 else 'FIXED_PROBE_PREDICTIVE_HARM' if hi<0 else 'PREDICTIVE_DIFFERENCE_UNRESOLVED'
    cheap=[]
    for c in PRIMARY:
        for r in ('starting','one_copy'):
            ra=models.ALPHAS.index(models.SELECTED[r])
            cheap.append(dict(candidate=c,reference=r,candidate_alpha=.01,reference_alpha=models.SELECTED[r],
                **contrast(loss[c][1],loss[r][ra],draws)))
    return dict(schema='d162_pilot64_prediction_v1',blocks=n,founder_ids=list(map(int,ids)),primary_cases=16*n,
        independent_futures=4,terminal_outcomes=64*n,bootstrap_draws=DRAWS,bootstrap_seed=SEED,
        primary=primary,label=label,selected_cheap_baseline_comparisons=cheap,absolute_scores=all_scores,
        comparisons=comparisons,within_future_variance=float(np.mean(np.var(y,axis=-1))),
        no_refits_on_test=True,mean_sham_is_loss_not_ensemble=True,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False,automatic_extension=False)


def check_summary(s,p,raw,y,ids):
    """Independent direct block sums/individual losses and bootstrap arithmetic."""
    n=len(ids);assert s['blocks']==n and s['founder_ids']==list(map(int,ids)) and s['primary_cases']==16*n
    assert s['terminal_outcomes']==64*n and s['bootstrap_draws']==20000 and s['bootstrap_seed']==16120260920
    draws=np.random.default_rng(16120260920).integers(0,n,(20000,n));loss={}
    for k in models.OBSERVERS:
        loss[k]=np.square(p[k][...,None]-y[None])
        for a in range(3):
            row=s['absolute_scores'][k][a];error=p[k][a][...,None]-y
            expected=float(np.sum(error*error)/(64*n))
            np.testing.assert_allclose(row['mse'],expected,atol=2e-14,rtol=0)
            np.testing.assert_allclose(row['mae_points'],np.sum(abs(error))*100/(64*n),atol=2e-12,rtol=0)
            np.testing.assert_allclose(row['bias_points'],np.sum(error)*100/(64*n),atol=2e-12,rtol=0)
            np.testing.assert_allclose(row['rmse_points'],100*np.sqrt(expected),atol=2e-12,rtol=0)
            np.testing.assert_allclose(row['group_mse'],np.sum(error*error,axis=(0,1,3))/(16*n),atol=2e-14,rtol=0)
            np.testing.assert_allclose(row['block_mse'],np.sum(error*error,axis=(1,2,3))/64,atol=2e-14,rtol=0)
            np.testing.assert_allclose(row['future_mse'],np.sum(error*error,axis=(0,1,2))/(16*n),atol=2e-14,rtol=0)
            assert row['clipped']==np.count_nonzero(p[k][a]!=raw[k][a])
            np.testing.assert_allclose(row['mse']-row['mean_target_mse'],np.var(y,axis=-1).mean(),atol=2e-14,rtol=0)
    for e in ('separate','mean','tied'):loss[e+':mean_sham_loss']=(loss[e+':sham_plus']+loss[e+':sham_minus'])*.5
    assert len(s['comparisons'])==3*len(PAIRS)
    all_rows=s['comparisons']+s['selected_cheap_baseline_comparisons']
    for row in all_rows:
        c,r=row['candidate'],row['reference'];ca=models.ALPHAS.index(row.get('candidate_alpha',row.get('alpha')))
        ra=models.ALPHAS.index(row.get('reference_alpha',row.get('alpha')))
        delta=loss[r][ra]-loss[c][ca];blocks=np.sum(delta,axis=(1,2,3))/64
        ref=float(np.sum(loss[r][ra])/(64*n));cand=float(np.sum(loss[c][ca])/(64*n))
        np.testing.assert_allclose([row['reference_mse'],row['candidate_mse']],[ref,cand],atol=2e-14,rtol=0)
        if ref:np.testing.assert_allclose(row['relative_reduction_percent'],100*np.sum(blocks)/(n*ref),atol=2e-10,rtol=0)
        else:assert row['relative_reduction_percent'] is None
        np.testing.assert_allclose(row['group_differences'],np.sum(delta,axis=(0,1,3))/(16*n),atol=2e-14,rtol=0)
        np.testing.assert_allclose(row['future_differences'],np.sum(delta,axis=(0,1,2))/(16*n),atol=2e-14,rtol=0)
        np.testing.assert_allclose(row['block_differences'],blocks,atol=2e-14,rtol=0)
        np.testing.assert_allclose(row['mse_reduction'],np.sum(blocks)/n,atol=2e-14,rtol=0)
        boot=np.add.reduce(blocks[draws],axis=1)/n
        np.testing.assert_allclose(row['block_bootstrap_95'],np.percentile(boot,[2.5,97.5]),atol=2e-14,rtol=0)
    fixed=next(r for r in s['comparisons'] if (r['candidate'],r['reference'],r['alpha'])==('tied:sham_minus','tied:passive',.01))
    assert s['primary']==fixed
    lo,hi=fixed['block_bootstrap_95'];label='FIXED_PROBE_PREDICTIVE_GAIN' if lo>0 else 'FIXED_PROBE_PREDICTIVE_HARM' if hi<0 else 'PREDICTIVE_DIFFERENCE_UNRESOLVED'
    assert s['label']==label
    return dict(passes=True,models=51,comparisons=len(all_rows),founders=n,normalization='whole_founder')
