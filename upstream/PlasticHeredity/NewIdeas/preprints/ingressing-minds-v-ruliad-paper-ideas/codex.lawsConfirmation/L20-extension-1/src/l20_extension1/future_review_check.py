"""Independent D156 fixed-score arithmetic and exact source bridge; no refits."""
import numpy as np
from .group_review_check import PAIRS as OLD_PAIRS

SETTINGS=('0.001','0.01','0.1')
EDITED=('passive','shuffle','attenuate','sham_plus','sham_minus')
OLD=('starting',)+EDITED
GROUPS=['A_ordinary','A_aligned','B_ordinary','B_aligned']


def same(actual,expected):
    if isinstance(expected,dict):
        assert isinstance(actual,dict) and actual.keys()==expected.keys()
        for k in expected:same(actual[k],expected[k])
    elif isinstance(expected,(list,tuple)):
        assert isinstance(actual,(list,tuple)) and len(actual)==len(expected)
        for a,b in zip(actual,expected):same(a,b)
    elif isinstance(expected,(float,np.floating)):
        assert not isinstance(actual,bool) and np.isfinite(actual)
        np.testing.assert_allclose(actual,expected,atol=2e-12,rtol=0)
    else:assert actual==expected,(actual,expected)


def canonical(k):return k if k in ('starting','one_copy') else 'separate:'+k


def names():
    observers=['starting','one_copy']+['separate:'+k for k in EDITED]+['mean:'+k for k in EDITED]
    return [s+'/'+k for s in SETTINGS for k in observers]+['nested/'+canonical(k) for k in OLD]


def specifications():
    result=[]
    for s in (*SETTINGS,'nested'):
        for c,r in OLD_PAIRS:result.append(dict(origin='D153',candidate=s+'/'+canonical(c),reference=s+'/'+canonical(r)))
    for s in SETTINGS:
        for k in OLD:result.append(dict(origin='D153_fixed_vs_nested',candidate=s+'/'+canonical(k),reference='nested/'+canonical(k)))
    for s in SETTINGS:
        for c,r in [('one_copy','starting')]+[(k,'one_copy') for k in EDITED]+[('mean_sham_loss','one_copy')]:
            result.append(dict(origin='D154',candidate=s+'/'+canonical(c),reference=s+'/'+canonical(r)))
    inter=(('shuffle','passive'),('attenuate','passive'),('attenuate','shuffle'),('attenuate','sham_plus'),
        ('attenuate','sham_minus'),('sham_plus','passive'),('sham_plus','shuffle'),('sham_minus','passive'),
        ('sham_minus','shuffle'),('sham_minus','sham_plus'))
    for s in SETTINGS:
        pairs=[('mean:'+k,'separate:'+k) for k in EDITED]
        pairs += [(('mean:'+k),r) for k in EDITED for r in ('one_copy','starting')]
        pairs += [('mean:'+c,'mean:'+r) for c,r in inter]
        pairs += [('mean:mean_sham_loss','mean:passive'),('mean:mean_sham_loss','one_copy'),
            ('mean:mean_sham_loss','starting'),('mean:mean_sham_loss','separate:mean_sham_loss'),
            ('mean:attenuate','mean:mean_sham_loss')]
        for c,r in pairs:result.append(dict(origin='D155',candidate=s+'/'+c,reference=s+'/'+r))
    return result


def guesses(panel,key):
    if key.endswith('mean_sham_loss'):
        return np.stack([panel['predictions'][names().index(key.replace('mean_sham_loss',v))] for v in ('sham_plus','sham_minus')])
    return panel['predictions'][names().index(key)][None]


def mean_loss(prediction,y):
    return sum(np.square(p-y) for p in prediction)/len(prediction)


def check_panel(panel,data,mean,refs,nested):
    shapes=dict(block_ids=(32,),labels=(32,4,4),futures=(16,4,4,4),predictions=(42,32,4,4),
        signed=(42,32,4,4),absolute=(42,32,4,4),squared=(42,32,4,4),
        future_signed=(42,16,4,4,4),future_absolute=(42,16,4,4,4),future_squared=(42,16,4,4,4),
        mean_signed=(42,16,4,4),mean_squared=(42,16,4,4),future_mean=(16,4,4),
        future_variance=(16,4,4),target_shift=(16,4,4),contrast_original=(201,32,4,4),
        contrast_futures=(201,16,4,4,4),contrast_mean=(201,16,4,4),
        contrast_prediction_delta=(201,16,4,4),contrast_shift=(201,16,4,4))
    assert panel.keys()==shapes.keys()
    for k,shape in shapes.items():
        assert panel[k].shape==shape and np.isfinite(panel[k]).all()
        assert panel[k].dtype==(np.int64 if k=='block_ids' else np.float64)
    for k in ('block_ids','labels','futures'):np.testing.assert_array_equal(panel[k],data[k])
    assert panel['block_ids'].tolist()==list(range(75000,75008))+list(range(78000,78008))+list(range(90000,90016))
    assert set(mean)==set(EDITED) and set(refs)==set(OLD)|{'one_copy'} and set(nested)==set(OLD)
    for i,key in enumerate(names()):
        setting,observer=key.split('/')
        if setting=='nested':expected=nested[observer.split(':')[-1]]
        elif observer.startswith('mean:'):expected=mean[observer[5:]][SETTINGS.index(setting)]
        else:expected=refs[observer.split(':')[-1]][SETTINGS.index(setting)]
        np.testing.assert_array_equal(panel['predictions'][i],expected)
    y=panel['labels'];f=panel['futures'];p=panel['predictions']
    assert all(np.max(abs(x))<=1 for x in (y,f,p))
    mu=np.sum(f,axis=3)/4;variance=np.sum(np.square(f-mu[...,None]),axis=3)/4;shift=mu-y[16:]
    expected=dict(signed=p-y,absolute=np.abs(p-y),squared=np.square(p-y),
        future_signed=p[:,16:,...,None]-f,future_absolute=np.abs(p[:,16:,...,None]-f),
        future_squared=np.square(p[:,16:,...,None]-f),mean_signed=p[:,16:]-mu,mean_squared=np.square(p[:,16:]-mu),
        future_mean=mu,future_variance=variance,target_shift=shift)
    for k,value in expected.items():np.testing.assert_allclose(panel[k],value,atol=1e-14,rtol=0)
    np.testing.assert_allclose(np.sum(panel['future_squared'],axis=-1)/4,panel['mean_squared']+variance,atol=1e-14,rtol=0)
    for i,s in enumerate(specifications()):
        c,r=(guesses(panel,s[k]) for k in ('candidate','reference'))
        d=mean_loss(r,y)-mean_loss(c,y)
        fd=mean_loss(r[:,16:,...,None],f)-mean_loss(c[:,16:,...,None],f)
        md=mean_loss(r[:,16:],mu)-mean_loss(c[:,16:],mu)
        dp=sum(c[:,16:])/len(c)-sum(r[:,16:])/len(r)
        for k,wanted in (('contrast_original',d),('contrast_futures',fd),('contrast_mean',md),
                         ('contrast_prediction_delta',dp),('contrast_shift',np.sum(fd,axis=-1)/4-d[16:])):
            np.testing.assert_allclose(panel[k][i],wanted,atol=1e-14,rtol=0)
        np.testing.assert_allclose(np.sum(fd,axis=-1)/4,md,atol=1e-14,rtol=0)
        np.testing.assert_allclose(md-d[16:],2*dp*shift,atol=1e-14,rtol=0)
    return dict(passes=True,series=42,contrasts=201,arrays=len(shapes),cases=512,repeat_cases=256,
        new_fits=0,new_predictions=0,new_dynamics=0)


def stats(error):
    count=error.size;bias=float(np.sum(error)/count);mse=float(np.sum(np.square(error))/count)
    return dict(mse=mse,mae_points=float(np.sum(np.abs(error))*100/count),rmse_points=float(np.sqrt(mse)*100),
        bias_points=100*bias,error_variance=float(np.sum(np.square(error-bias))/count))


def detail(error):
    return dict(**stats(error),groups=[stats(np.take(error,g,axis=2)) for g in range(4)],
        blocks=[stats(np.take(error,b,axis=0)) for b in range(len(error))])


def contributions(value,ids):
    n=len(ids);block=np.sum(value,axis=(1,2))/16;group=np.sum(value,axis=(0,1))/(4*n)
    return dict(mean=float(np.sum(value)/(16*n)),block_means=block.tolist(),
        block_contributions=[float(x/n) for x in block],group_means=group.tolist(),
        group_contributions=[float(x/4) for x in group],
        block_order_descending=[int(ids[j]) for j in sorted(range(n),key=lambda j:-block[j])],
        positive_blocks=sum(bool(x>0) for x in block),negative_blocks=sum(bool(x<0) for x in block),
        zero_blocks=sum(bool(x==0) for x in block),positive_cases=int(np.count_nonzero(value>0)),
        negative_cases=int(np.count_nonzero(value<0)),zero_cases=int(np.count_nonzero(value==0)),
        leave_one_score_block_out=[float(sum(block[k] for k in range(n) if k!=j)/(n-1)) for j in range(n)])


def paired(gain,c,r,ids):
    s=contributions(gain,ids);ref=float(np.sum(r)/r.size)
    return dict(**s,candidate_mse=float(np.sum(c)/c.size),reference_mse=ref,
        relative_reduction_percent=100*s['mean']/ref if ref!=0 else None)


def check_summary(s,panel):
    ids=panel['block_ids'];p=panel['predictions'];y=panel['labels'];f=panel['futures']
    mu=np.sum(f,axis=-1)/4;v=np.sum((f-mu[...,None])**2,axis=-1)/4
    models={}
    for i,key in enumerate(names()):
        e=p[i]-y;ef=p[i,16:,...,None]-f;em=p[i,16:]-mu;mf=float(np.sum(ef*ef)/ef.size)
        models[key]=dict(full_original=detail(e),original_same_founders=detail(e[16:]),
            individual_futures=detail(ef),mean_future=detail(em),by_repeat=[detail(ef[...,j]) for j in range(4)],
            leave_one_repeat_out=[detail(np.delete(ef,j,axis=3)) for j in range(4)],
            mean_future_error_mse=float(np.sum(em*em)/em.size),within_future_variance=float(np.sum(v)/v.size),
            within_variance_share_of_mse=float(np.sum(v)/v.size/mf) if mf else None,
            squared_mean_error=float((np.sum(em)/em.size)**2),
            variance_of_mean_errors=float(np.sum((em-np.sum(em)/em.size)**2)/em.size))
        np.testing.assert_allclose(models[key]['individual_futures']['mse'],
            models[key]['mean_future_error_mse']+models[key]['within_future_variance'],atol=1e-14,rtol=0)
    comparisons=[]
    for i,spec in enumerate(specifications()):
        c,r=(guesses(panel,spec[k]) for k in ('candidate','reference'))
        co,ro=mean_loss(c,y),mean_loss(r,y)
        cf,rf=mean_loss(c[:,16:,...,None],f),mean_loss(r[:,16:,...,None],f)
        cm,rm=mean_loss(c[:,16:],mu),mean_loss(r[:,16:],mu)
        original=ro-co;future=rf-cf;average=np.sum(future,axis=-1)/4
        dp=sum(c[:,16:])/len(c)-sum(r[:,16:])/len(r)
        omitted=[]
        for j in range(4):
            fc=np.sum(np.delete(cf,j,axis=3),axis=3)/3;fr=np.sum(np.delete(rf,j,axis=3),axis=3)/3
            omitted.append(paired(fr-fc,fc,fr,ids[16:]))
        comparisons.append(dict(**spec,full_original=paired(original,co,ro,ids),
            original_same_founders=paired(original[16:],co[16:],ro[16:],ids[16:]),
            individual_futures=paired(average,np.sum(cf,axis=3)/4,np.sum(rf,axis=3)/4,ids[16:]),
            mean_future=paired(rm-cm,cm,rm,ids[16:]),
            by_repeat=[paired(future[...,j],cf[...,j],rf[...,j],ids[16:]) for j in range(4)],
            leave_one_repeat_out=omitted,shift=contributions(2*dp*(mu-y[16:]),ids[16:]),
            prediction_delta=contributions(dp,ids[16:])))
    expected=dict(schema='d156_fixed_prediction_future_review_v1',posthoc=True,prospective_evidence=False,
        all_cases_retained=True,blocks=32,cases=512,repeat_blocks=16,repeat_cases=256,repeat_outcomes=1024,
        groups=GROUPS,alphas=list(SETTINGS),series=names(),comparisons_count=201,
        new_fits=0,new_predictions=0,new_dynamics=0,new_founders=0,source_primary_unchanged=True,
        mean_sham_is_loss_not_ensemble=True,future_variance_divisor=4,population_bias_identified=False,
        irreducible_noise_floor_identified=False,confidence_intervals=False,equivalence_claim=False,
        omissions_are_scores_not_refits=True,repeat_omission_averages_individual_losses=True,
        causal_overfitting_claim=False,former_test_is_development=True,automatic_successor=False,
        models=models,comparisons=comparisons,
        targets=dict(original=detail(y[16:]),future_mean=detail(mu),mean_minus_original=detail(mu-y[16:]),
            within_future_variance=contributions(v,ids[16:])))
    same(s,expected)
    return dict(passes=True,series=42,contrasts=201,repeat_streams=4,repeat_outcomes=1024,new_fits=0,new_dynamics=0)


def source_bridge(s,source):
    old=source['retained_d154'];earlier=old['retained_d153']
    for key in names():
        setting,k=key.split('/')
        if k.startswith('mean:'):prior=source['scores'][setting]['models'][k[5:]]
        elif k=='one_copy':prior=old['scores'][setting]['one_copy']
        else:prior=earlier['scores'][setting]['models'][k.split(':')[-1]]
        actual=s['models'][key]
        for scope,target in [('full_original',prior['original']),('original_same_founders',prior['cohorts']['former_test']),
                             ('individual_futures',prior['individual_futures']),('mean_future',prior['mean_target'])]:
            for field in ('mse','mae_points','rmse_points'):same(actual[scope][field],target[field])
            same([x['mse'] for x in actual[scope]['groups']],target['group_mse'])
            same([x['mse'] for x in actual[scope]['blocks']],target['block_mse'])
    expected=[]
    for setting in (*SETTINGS,'nested'):expected.extend(earlier['scores'][setting]['comparisons'])
    expected.extend(earlier['fixed_vs_nested'])
    for setting in SETTINGS:expected.extend(old['scores'][setting]['comparisons'])
    for setting in SETTINGS:expected.extend(source['scores'][setting]['comparisons'])
    assert len(expected)==len(s['comparisons'])==201
    for actual,prior in zip(s['comparisons'],expected):
        for scope,target in [('full_original',prior['original']),('original_same_founders',prior['cohorts']['former_test']),
                             ('individual_futures',prior['individual_futures']),('mean_future',prior['mean_target'])]:
            row=actual[scope]
            same(row['mean'],target['mse_reduction']);same(row['relative_reduction_percent'],target['relative_reduction_percent'])
            same(row['block_means'],target['block_differences']);same(row['leave_one_score_block_out'],target['leave_one_score_block_out'])
            same(row['group_means'],[g['mse_reduction'] for g in target['groups']])
            for field in ('positive_blocks','negative_blocks','zero_blocks'):same(row[field],target[field])
    return dict(passes=True,exact_source_series=42,source_contrasts=201,source_primary_unchanged=True)
