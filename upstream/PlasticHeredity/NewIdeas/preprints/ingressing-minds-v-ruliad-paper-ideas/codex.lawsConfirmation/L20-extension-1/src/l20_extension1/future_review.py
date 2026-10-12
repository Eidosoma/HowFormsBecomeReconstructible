"""D156: descriptive review of fixed forecasts, without fitting or dynamics."""
import numpy as np

ALPHAS=('0.001','0.01','0.1')
EDITED=('passive','shuffle','attenuate','sham_plus','sham_minus')
OLD=('starting',)+EDITED
OBSERVERS=('starting','one_copy')+tuple('separate:'+k for k in EDITED)+tuple('mean:'+k for k in EDITED)
GROUPS=('A_ordinary','A_aligned','B_ordinary','B_aligned')
IDS=np.array(list(range(75000,75008))+list(range(78000,78008))+list(range(90000,90016)),np.int64)
OLD_PAIRS=(('passive','starting'),('shuffle','starting'),('shuffle','passive'),
    ('attenuate','starting'),('attenuate','passive'),('attenuate','shuffle'),
    ('attenuate','sham_plus'),('attenuate','sham_minus'),('sham_plus','starting'),
    ('sham_plus','passive'),('sham_plus','shuffle'),('sham_minus','starting'),
    ('sham_minus','passive'),('sham_minus','shuffle'),('sham_minus','sham_plus'),
    ('attenuate','mean_sham_loss'),('mean_sham_loss','starting'),('mean_sham_loss','passive'))


def canonical(name):return name if name in ('starting','one_copy') else 'separate:'+name


def series():
    return [a+'/'+k for a in ALPHAS for k in OBSERVERS]+['nested/'+canonical(k) for k in OLD]


def specs():
    out=[]
    for a in (*ALPHAS,'nested'):
        out.extend(dict(origin='D153',candidate=a+'/'+canonical(c),reference=a+'/'+canonical(r)) for c,r in OLD_PAIRS)
    for a in ALPHAS:
        out.extend(dict(origin='D153_fixed_vs_nested',candidate=a+'/'+canonical(k),reference='nested/'+canonical(k)) for k in OLD)
    one_pairs=(('one_copy','starting'),)+tuple((k,'one_copy') for k in EDITED)+(('mean_sham_loss','one_copy'),)
    for a in ALPHAS:
        out.extend(dict(origin='D154',candidate=a+'/'+canonical(c),reference=a+'/'+canonical(r)) for c,r in one_pairs)
    mean_pairs=[('mean:'+k,'separate:'+k) for k in EDITED]
    mean_pairs.extend(('mean:'+k,r) for k in EDITED for r in ('one_copy','starting'))
    mean_pairs.extend(('mean:'+c,'mean:'+r) for c,r in OLD_PAIRS if c in EDITED and r in EDITED)
    mean_pairs.extend([('mean:mean_sham_loss','mean:passive'),('mean:mean_sham_loss','one_copy'),
        ('mean:mean_sham_loss','starting'),('mean:mean_sham_loss','separate:mean_sham_loss'),
        ('mean:attenuate','mean:mean_sham_loss')])
    for a in ALPHAS:out.extend(dict(origin='D155',candidate=a+'/'+c,reference=a+'/'+r) for c,r in mean_pairs)
    return out


def components(key):
    names=series()
    if key in names:return [names.index(key)]
    if key.endswith('mean_sham_loss'):
        return [names.index(key.replace('mean_sham_loss',k)) for k in ('sham_plus','sham_minus')]
    raise ValueError('declared forecast or mean separate control loss required')


def assemble(mean,refs,nested):
    assert set(mean)==set(EDITED) and set(refs)==set(OLD)|{'one_copy'} and set(nested)==set(OLD)
    for value in (*mean.values(),*refs.values()):assert value.shape==(3,32,4,4)
    for value in nested.values():assert value.shape==(32,4,4)
    result=[]
    for i in range(3):
        result.extend([refs['starting'][i],refs['one_copy'][i]])
        result.extend(refs[k][i] for k in EDITED);result.extend(mean[k][i] for k in EDITED)
    result.extend(nested[k] for k in OLD)
    return np.stack(result)


def extract(data,mean,refs,nested):
    p=assemble(mean,refs,nested);y=data['labels'];f=data['futures'];ids=data['block_ids']
    assert y.shape==(32,4,4) and f.shape==(16,4,4,4)
    np.testing.assert_array_equal(ids,IDS)
    for value in (p,y,f):
        assert value.dtype==np.float64 and np.isfinite(value).all() and np.max(abs(value))<=1
    mu=f.mean(axis=-1);variance=((f-mu[...,None])**2).mean(axis=-1);shift=mu-y[16:]
    error=p-y;future_error=p[:,16:,...,None]-f;mean_error=p[:,16:]-mu
    panel=dict(block_ids=ids.copy(),labels=y.copy(),futures=f.copy(),predictions=p,
        signed=error,absolute=abs(error),squared=error**2,future_signed=future_error,
        future_absolute=abs(future_error),future_squared=future_error**2,
        mean_signed=mean_error,mean_squared=mean_error**2,
        future_mean=mu,future_variance=variance,target_shift=shift)
    original=[];repeats=[];average=[];delta=[];change=[]
    for s in specs():
        ci,ri=components(s['candidate']),components(s['reference'])
        original.append(panel['squared'][ri].mean(axis=0)-panel['squared'][ci].mean(axis=0))
        repeats.append(panel['future_squared'][ri].mean(axis=0)-panel['future_squared'][ci].mean(axis=0))
        average.append(panel['mean_squared'][ri].mean(axis=0)-panel['mean_squared'][ci].mean(axis=0))
        dp=p[ci,16:].mean(axis=0)-p[ri,16:].mean(axis=0)
        delta.append(dp);change.append(2*dp*shift)
    panel.update(contrast_original=np.stack(original),contrast_futures=np.stack(repeats),
        contrast_mean=np.stack(average),contrast_prediction_delta=np.stack(delta),contrast_shift=np.stack(change))
    return panel


def error_stats(error):
    bias=float(error.mean());mse=float(np.mean(error**2))
    return dict(mse=mse,mae_points=float(abs(error).mean()*100),rmse_points=float(np.sqrt(mse)*100),
        bias_points=bias*100,error_variance=float(np.mean((error-bias)**2)))


def describe_error(error):
    return dict(**error_stats(error),groups=[error_stats(error[:,:,g,...]) for g in range(4)],
        blocks=[error_stats(block) for block in error])


def contributions(values,ids):
    assert values.shape==(len(ids),4,4)
    block=values.mean(axis=(1,2));group=values.mean(axis=(0,1));n=len(ids)
    return dict(mean=float(values.mean()),block_means=block.tolist(),block_contributions=(block/n).tolist(),
        group_means=group.tolist(),group_contributions=(group/4).tolist(),
        block_order_descending=ids[np.argsort(-block,kind='stable')].tolist(),
        positive_blocks=int((block>0).sum()),negative_blocks=int((block<0).sum()),zero_blocks=int((block==0).sum()),
        positive_cases=int((values>0).sum()),negative_cases=int((values<0).sum()),zero_cases=int((values==0).sum()),
        leave_one_score_block_out=((block.sum()-block)/(n-1)).tolist())


def contrast_stats(gain,c,r,ids):
    result=contributions(gain,ids);ref=float(r.mean())
    result.update(candidate_mse=float(c.mean()),reference_mse=ref,
        relative_reduction_percent=100*result['mean']/ref if ref else None)
    return result


def metadata():
    return dict(schema='d156_fixed_prediction_future_review_v1',posthoc=True,prospective_evidence=False,
        all_cases_retained=True,blocks=32,cases=512,repeat_blocks=16,repeat_cases=256,repeat_outcomes=1024,
        groups=list(GROUPS),alphas=list(ALPHAS),series=series(),comparisons_count=201,
        new_fits=0,new_predictions=0,new_dynamics=0,new_founders=0,source_primary_unchanged=True,
        mean_sham_is_loss_not_ensemble=True,future_variance_divisor=4,population_bias_identified=False,
        irreducible_noise_floor_identified=False,confidence_intervals=False,equivalence_claim=False,
        omissions_are_scores_not_refits=True,repeat_omission_averages_individual_losses=True,
        causal_overfitting_claim=False,former_test_is_development=True,automatic_successor=False)


def summarize(panel):
    ids=panel['block_ids'];p=panel['predictions'];v=panel['future_variance'];models={}
    for i,key in enumerate(series()):
        f=panel['future_signed'][i];e=panel['mean_signed'][i];mu_mse=float((e*e).mean());future_mse=float((f*f).mean())
        models[key]=dict(full_original=describe_error(panel['signed'][i]),
            original_same_founders=describe_error(panel['signed'][i,16:]),
            individual_futures=describe_error(f),mean_future=describe_error(e),
            by_repeat=[describe_error(f[...,j]) for j in range(4)],
            leave_one_repeat_out=[describe_error(f[...,[k for k in range(4) if k!=j]]) for j in range(4)],
            mean_future_error_mse=mu_mse,within_future_variance=float(v.mean()),
            within_variance_share_of_mse=float(v.mean()/future_mse) if future_mse else None,
            squared_mean_error=float(e.mean()**2),variance_of_mean_errors=float(e.var()))
    comparisons=[]
    for j,s in enumerate(specs()):
        ci,ri=components(s['candidate']),components(s['reference'])
        c=panel['squared'][ci].mean(axis=0);r=panel['squared'][ri].mean(axis=0)
        cf=panel['future_squared'][ci].mean(axis=0);rf=panel['future_squared'][ri].mean(axis=0)
        cm=panel['mean_squared'][ci].mean(axis=0);rm=panel['mean_squared'][ri].mean(axis=0)
        original=panel['contrast_original'][j];future=panel['contrast_futures'][j]
        by_repeat=[contrast_stats(future[...,k],cf[...,k],rf[...,k],ids[16:]) for k in range(4)]
        omitted=[]
        for k in range(4):
            keep=[r for r in range(4) if r!=k]
            omitted.append(contrast_stats(future[...,keep].mean(axis=-1),cf[...,keep].mean(axis=-1),rf[...,keep].mean(axis=-1),ids[16:]))
        comparisons.append(dict(**s,full_original=contrast_stats(original,c,r,ids),
            original_same_founders=contrast_stats(original[16:],c[16:],r[16:],ids[16:]),
            individual_futures=contrast_stats(future.mean(axis=-1),cf.mean(axis=-1),rf.mean(axis=-1),ids[16:]),
            mean_future=contrast_stats(panel['contrast_mean'][j],cm,rm,ids[16:]),
            by_repeat=by_repeat,leave_one_repeat_out=omitted,
            shift=contributions(panel['contrast_shift'][j],ids[16:]),
            prediction_delta=contributions(panel['contrast_prediction_delta'][j],ids[16:])))
    return dict(**metadata(),models=models,comparisons=comparisons,
        targets=dict(original=describe_error(panel['labels'][16:]),future_mean=describe_error(panel['future_mean']),
            mean_minus_original=describe_error(panel['target_shift']),
            within_future_variance=contributions(v,ids[16:])))


def fixture():
    from . import mean_models
    data,refs,nested,old=mean_models.fixture();data['block_ids']=IDS.copy()
    rng=np.random.default_rng(15620260920)
    mean={k:np.clip(refs[k]+rng.normal(0,.025,refs[k].shape),-1,1) for k in EDITED}
    # Existing summary implementations only; no model fitting, even in fixtures.
    source=mean_models.summarize(mean,refs,old,data)
    return data,mean,refs,nested,source
