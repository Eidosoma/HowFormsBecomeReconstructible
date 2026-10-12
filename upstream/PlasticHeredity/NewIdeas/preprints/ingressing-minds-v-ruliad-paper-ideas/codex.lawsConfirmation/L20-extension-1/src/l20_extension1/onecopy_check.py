"""Independent D154 feature assembly/SVD and saved-score verification."""
import numpy as np
from . import matched_check as prior

ALPHAS=(.001,.01,.1)
PAIRS=(('one_copy','starting'),('passive','one_copy'),('shuffle','one_copy'),('attenuate','one_copy'),
    ('sham_plus','one_copy'),('sham_minus','one_copy'),('mean_sham_loss','one_copy'))
same=prior.same


def features(data):
    n=len(data['block_ids']);a=data['start'];e=data['endpoint']
    assert a.shape==(n,4,4,7) and e.shape==(n,4,4,3,6)
    out=np.empty((n,4,4,13),np.float64);out[...,:7]=a;out[...,7:]=e[...,0,:]
    assert np.isfinite(out).all();return out


def check_all(p,m,data):
    n=len(data['block_ids']);ids=data['block_ids'];assert set(p)=={'one_copy'}
    assert ids.dtype==np.int64 and len(set(ids.tolist()))==n and n>=4
    assert data['labels'].shape==(n,4,4) and p['one_copy'].shape==(3,n,4,4)
    assert np.isfinite(p['one_copy']).all() and np.max(abs(p['one_copy']))<=1
    X=features(data).reshape(n*16,13);Y=data['labels'].ravel();g=np.tile(np.arange(4,dtype=np.int64),n*4)
    assert np.isfinite(Y).all() and np.max(abs(Y))<=1 and len(m['folds'])==n
    for b in range(n):
        blocks=[i for i in range(n) if i!=b];train=np.concatenate([np.arange(i*16,(i+1)*16) for i in blocks])
        test=np.arange(b*16,(b+1)*16)
        guesses,records=prior.group.svd_path(X[train],Y[train],g[train],X[test],g[test])
        np.testing.assert_allclose(p['one_copy'][:,b],guesses[:,:3].T.reshape(3,4,4),atol=2e-10,rtol=0)
        same(m['folds'][b],dict(validation_block=int(ids[b]),training_blocks=ids[blocks].tolist(),models=records[:3]))
    same({k:v for k,v in m.items() if k!='folds'},dict(blocks=ids.tolist(),alphas=list(ALPHAS),
        preprocessing='training-only in every outer fold',inner_selection=False,prospective_evidence=False,
        model_class=prior.group.CLASS,feature_definition='starting_7_then_U0_endpoint_6'))
    return dict(passes=True,models=1,settings=3,outer_fits=n*3,inner_fits=0,svd_group_coordinates=True,features=13)


def stats(p,data):
    y=data['labels'];f=data['futures'];average=np.sum(f,axis=-1)/4
    assert p.shape==y.shape and np.isfinite(p).all() and np.max(abs(p))<=1
    e=p[16:,...,None]-f;count=e.size;future=np.sum(e*e,axis=-1)/4;mean=np.square(p[16:]-average)
    np.testing.assert_allclose(future,mean+np.sum((f-average[...,None])**2,axis=-1)/4,atol=1e-14,rtol=0)
    return dict(original=prior.group.error_stats(p,y),
        cohorts={k:prior.group.error_stats(p[l:h],y[l:h]) for k,l,h in prior.COHORTS},
        individual_futures=dict(mse=float(np.sum(e*e)/count),mae_points=float(100*np.sum(abs(e))/count),
            rmse_points=float(100*np.sqrt(np.sum(e*e)/count)),block_mse=(np.sum(e*e,axis=(1,2,3))/64).tolist(),
            group_mse=(np.sum(e*e,axis=(0,1,3))/256).tolist()),mean_target=prior.group.error_stats(p[16:],average)), (np.square(p-y),future,mean)


def check_summary(s,p,references,nested,source_summary,data):
    assert data['labels'].shape==(32,4,4) and data['futures'].shape==(16,4,4,4)
    assert set(p)=={'one_copy'} and p['one_copy'].shape==(3,32,4,4)
    assert s['retained_d153']==source_summary
    prior.check_summary(source_summary,references,nested,data)
    scores={}
    for i,label in enumerate(('0.001','0.01','0.1')):
        score,one=stats(p['one_copy'][i],data)
        _,losses=prior.score({k:references[k][i] for k in prior.MODELS},data)
        for bundle,value in zip(losses,one):bundle['one_copy']=value
        loss,future,mean=losses
        comparisons=[dict(candidate=c,reference=r,**prior.contrast(loss[c],loss[r],future[c],future[r],mean[c],mean[r])) for c,r in PAIRS]
        scores[label]=dict(one_copy=score,comparisons=comparisons)
    expected=dict(schema='d154_one_copy_development_v1',stage='POST_RESULT_DEVELOPMENT',prospective_evidence=False,
        blocks=32,cases=512,all_cases_retained=True,alphas=[.001,.01,.1],
        observers=['starting','one_copy','passive','shuffle','attenuate','sham_plus','sham_minus'],
        feature_definition='starting_7_then_U0_endpoint_6',new_feature_dimension=13,new_penalized_dimension=52,
        model_class=prior.group.CLASS,common_deviation_penalty_ratio=1,new_fits=96,new_predictions=1536,
        inner_selection=False,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,reference_fits_recomputed=False,
        original_reference_summary_exact=True,retained_reference_contrasts=90,new_contrasts=21,
        one_copy_budget=1,two_copy_budget=2,equal_observation_budget=False,
        equal_alpha_is_not_equal_effective_complexity=True,former_test_is_now_development=True,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,model_selected_for_deployment=False,no_best_alpha_selected=True,
        mean_sham_is_loss_average_not_prediction_ensemble=True,automatic_successor=False,
        focal_pairs=[['one_copy','starting'],['passive','one_copy'],['sham_minus','one_copy']],
        scores=scores,retained_d153=source_summary)
    same(s,expected)
    return dict(passes=True,settings=3,new_contrasts=21,retained_contrasts=90,blocks=32,cases=512,secondary_outcomes=1024)


def check_errors(stored,p,references,nested,data):
    keys={'one_copy__signed','one_copy__absolute','one_copy__squared'};assert len(stored)==75
    prior.check_errors({k:v for k,v in stored.items() if k not in keys},references,nested,data)
    e=p['one_copy']-data['labels'][None]
    for k,v in zip(('one_copy__signed','one_copy__absolute','one_copy__squared'),(e,np.maximum(e,-e),e*e)):
        np.testing.assert_array_equal(stored[k],v)
    return dict(passes=True,new_case_arrays=3,retained_case_arrays=72,all_cases_retained=True)
