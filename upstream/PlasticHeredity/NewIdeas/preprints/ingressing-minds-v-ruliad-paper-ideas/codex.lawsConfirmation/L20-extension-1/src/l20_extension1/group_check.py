"""Independent D152 SVD in whitened group-slope coordinates and score checks."""
import numpy as np
from . import recovery_check as old, probe_model_check as score_check

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
ALPHAS=(.001,.01,.1,1.,10.,100.)
CLASS='common_plus_zero_sum_group_deviations_penalty_ratio_1'


def error_stats(prediction,y):
    e=prediction-y;squared=np.square(e);n,lives,groups=y.shape;count=lives*groups
    mse=float(np.sum(squared)/(n*count))
    return dict(mse=mse,mae_points=float(100*np.sum(abs(e))/(n*count)),rmse_points=100*float(np.sqrt(mse)),
        block_mse=(np.sum(squared,axis=(1,2))/count).tolist(),
        block_mae_points=(100*np.sum(abs(e),axis=(1,2))/count).tolist(),
        group_mse=(np.sum(squared,axis=(0,1))/(n*lives)).tolist())


def reduction(candidate,reference):
    n,lives,groups=candidate.shape;count=lives*groups
    delta=np.sum(reference-candidate,axis=(1,2))/count;mean=float(np.sum(delta)/n)
    base=float(np.sum(reference)/(n*count))
    return dict(mse_reduction=mean,relative_reduction_percent=100*mean/base if base else None,
        block_differences=delta.tolist(),positive_blocks=int(np.count_nonzero(delta>0)),
        negative_blocks=int(np.count_nonzero(delta<0)),zero_blocks=int(np.count_nonzero(delta==0)))


def matrices(data):
    a,e,t=data['start'],data['endpoint'],data['targeted']
    assert a.shape[-1]==7 and e.shape==t.shape==a.shape[:-1]+(3,6)
    result={'starting':a.copy()}
    for name,second in zip(MODELS[1:],(e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])):
        result[name]=np.concatenate([a,e[...,0,:],second],axis=-1)
    return result


def svd_path(x,y,g,test,h):
    assert x.ndim==test.ndim==2 and len(x)==len(y)==len(g) and len(test)==len(h)
    assert np.isfinite(x).all() and np.isfinite(y).all() and np.isfinite(test).all()
    assert set(g.tolist())==set(range(4)) and set(h.tolist())<=set(range(4))
    mu=np.stack([np.sum(x[g==j],axis=0)/np.count_nonzero(g==j) for j in range(4)])
    offset=np.array([np.sum(y[g==j])/np.count_nonzero(g==j) for j in range(4)])
    centered=x-mu[g];sd=np.sqrt(np.sum(centered**2,axis=0)/len(y));sd[sd<=1e-12]=1
    z=centered/sd;target=y-offset[g];d=x.shape[1]
    # Slopes B have penalty B' P B, P=I-(3/16)11'. Its inverse square root
    # is I+(1/4)11'. This is NOT the production common/contrast design.
    whitening=np.eye(4)+np.ones((4,4))*.25
    train=np.einsum('ig,ij->igj',whitening[g],z).reshape(len(y),4*d)
    u,s,vh=np.linalg.svd(train/np.sqrt(len(y)),full_matrices=False)
    projected=u.T@(target/np.sqrt(len(y)));guesses=[];records=[]
    contrasts=np.array([[-1,-1,1],[-1,1,-1],[1,-1,-1],[1,1,1]])/2
    for alpha in ALPHAS:
        theta=(vh.T@((s/(s*s+alpha))*projected)).reshape(4,d)
        slopes=whitening@theta;common=np.sum(slopes,axis=0)/4
        coefficients=np.vstack([common,contrasts.T@slopes])
        prediction=offset[h]+np.sum(((test-mu[h])/sd)*slopes[h],axis=1)
        guesses.append(np.maximum(-1,np.minimum(1,prediction)))
        records.append(dict(alpha=alpha,means=mu.tolist(),offsets=offset.tolist(),scale=sd.tolist(),
            coefficients=coefficients.tolist(),model_class=CLASS))
    return np.stack(guesses,axis=-1),records


def check_fold(prediction,record,x,y,ids,outer):
    n=len(x);assert x.shape[:3]==y.shape==(n,4,4) and ids.shape==(n,) and n>=4
    assert ids.dtype==np.int64 and len(set(ids.tolist()))==n
    X=x.reshape(n*16,-1);Y=y.reshape(n*16);g=np.tile(np.arange(4,dtype=np.int64),n*4)
    assert np.isfinite(Y).all() and np.max(abs(Y))<=1
    blocks=[i for i in range(n) if i!=outer];losses=[]
    rows=lambda indexes:np.concatenate([np.arange(16*i,16*i+16) for i in indexes])
    for inner in blocks:
        train=rows([i for i in blocks if i!=inner]);test=rows([inner])
        p,_=svd_path(X[train],Y[train],g[train],X[test],g[test])
        losses.append(np.sum((p-Y[test,None])**2,axis=0)/16)
    losses=np.array(losses);mean=np.sum(losses,axis=0)/(n-1)
    ai=[i for i,v in enumerate(mean) if v<=min(mean)+1e-12][-1]
    train=rows(blocks);test=rows([outer]);p,models=svd_path(X[train],Y[train],g[train],X[test],g[test])
    expected=dict(validation_block=int(ids[outer]),training_blocks=[int(ids[i]) for i in blocks],
        inner_validation_blocks=[int(ids[i]) for i in blocks],inner_block_mse=losses.tolist(),
        inner_mean_mse=mean.tolist(),selected_index=ai,model=models[ai])
    assert np.asarray(prediction).shape==(4,4)
    np.testing.assert_allclose(prediction,p[:,ai].reshape(4,4),atol=2e-10,rtol=0)
    old.same(record,expected)
    return dict(passes=True,outer_folds=1,inner_folds=n-1,svd_group_coordinates=True)


def check_fold_all(p,m,data,outer=0):
    assert set(p)==set(m)==set(MODELS);x=matrices(data)
    for name in MODELS:check_fold(p[name],m[name],x[name],data['labels'],data['block_ids'],outer)
    return dict(passes=True,models=6,outer_folds=6,inner_folds=6*(len(data['labels'])-1),svd_group_coordinates=True)


def check_all(p,m,data):
    assert set(p)==set(m)==set(MODELS);x=matrices(data);n=len(data['labels']);ids=data['block_ids']
    for name in MODELS:
        assert p[name].shape==(n,4,4) and len(m[name]['folds'])==n
        for i in range(n):check_fold(p[name][i],m[name]['folds'][i],x[name],data['labels'],ids,i)
        header={k:v for k,v in m[name].items() if k!='folds'}
        assert header==dict(blocks=ids.tolist(),alphas=list(ALPHAS),
            preprocessing='training-only in every inner and outer fold',prospective_evidence=False,model_class=CLASS)
    return dict(passes=True,models=6,outer_folds=6*n,inner_folds=6*n*(n-1),svd_group_coordinates=True)


def check_summary(s,p,m,baseline,baseline_fits,data):
    architectures={};y,f=data['labels'],data['futures']
    for label,predictions,records in (('shared',baseline,baseline_fits),('group_sensitive',p,m)):
        bundle=s['architectures'][label]
        # Reuse the independently written, frozen D151 arithmetic checker.
        prior=dict(schema='d151_targeted_prediction_development_v1',stage='POST_RESULT_DEVELOPMENT',
            prospective_evidence=False,blocks=32,cases=512,all_cases_retained=True,new_diagnostic_cycles=1536,
            new_actual_lineages=0,new_founders=0,
            **{k:bundle[k] for k in ('models','comparisons','central_comparison','repeated_future_models','repeated_future_comparisons')},
            repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
            confidence_intervals=False,model_selected_for_deployment=False,automatic_successor=False,
            baseline_predictions_reused=True,observer_cycles=2,mean_sham_is_loss_average_not_prediction_ensemble=True,
            interpretation='Existing-founder development of a fixed repair-like diagnostic; not prospective validation.')
        score_check.check_summary(prior,predictions,records,data)
        details={k:[error_stats(predictions[k][:,:,g:g+1],y[:,:,g:g+1]) for g in range(4)] for k in MODELS}
        old.same(bundle['group_details'],details)
        assert set(bundle)=={'models','comparisons','central_comparison','repeated_future_models','repeated_future_comparisons','group_details'}
        architectures[label]=bundle
    changes=[]
    for name in MODELS:
        a=np.square(p[name]-y);b=np.square(baseline[name]-y)
        af=np.sum(np.square(p[name][16:,...,None]-f),axis=-1)/4
        bf=np.sum(np.square(baseline[name][16:,...,None]-f),axis=-1)/4
        am=np.square(p[name][16:]-np.sum(f,axis=-1)/4);bm=np.square(baseline[name][16:]-np.sum(f,axis=-1)/4)
        individual=reduction(af,bf);mean=reduction(am,bm)
        np.testing.assert_allclose(individual['block_differences'],mean['block_differences'],atol=1e-14,rtol=0)
        changes.append(dict(model=name,candidate='group_sensitive',reference='shared',original=reduction(a,b),
            groups=[reduction(a[:,:,g:g+1],b[:,:,g:g+1]) for g in range(4)],
            cohorts={key:reduction(a[l:r],b[l:r]) for key,l,r in (('d135',0,8),('d140',8,16),('former_test',16,32))},
            individual_futures=individual,mean_target=mean))
    expected=dict(schema='d152_group_sensitive_prediction_development_v1',stage='POST_RESULT_DEVELOPMENT',
        prospective_evidence=False,blocks=32,cases=512,all_cases_retained=True,new_diagnostic_cycles=0,
        new_actual_lineages=0,new_founders=0,architectures=architectures,architecture_comparisons=changes,
        primary_development_comparison=architectures['group_sensitive']['central_comparison'],
        feature_dimensions=[7,19,19,19,19,19],penalized_dimensions=[28,76,76,76,76,76],
        common_deviation_penalty_ratio=1,model_class=CLASS,observer_cycles=2,baseline_predictions_reused=True,
        former_test_is_now_development=True,repeated_future_blocks=16,repeated_future_outcomes=1024,
        repeated_outcomes_used_for_training=False,confidence_intervals=False,model_selected_for_deployment=False,
        automatic_successor=False,mean_sham_is_loss_average_not_prediction_ensemble=True,
        interpretation='One pre-specified model-class comparison on observed founders; not prospective validation.')
    old.same(s,expected)
    return dict(passes=True,architectures=2,observers=6,observer_contrasts=20,architecture_contrasts=6,
        blocks=32,cases=512,repeated_outcomes=1024,prospective_evidence=False)


def check_errors(stored,p,baseline,data):
    assert len(stored)==36
    for label,values in (('shared',baseline),('group_sensitive',p)):
        for name in MODELS:
            prefix=label+'_'+name;error=values[name]-data['labels']
            np.testing.assert_array_equal(stored[prefix+'_signed'],error)
            np.testing.assert_array_equal(stored[prefix+'_absolute'],np.maximum(error,-error))
            np.testing.assert_array_equal(stored[prefix+'_squared'],error*error)
    return dict(passes=True,case_arrays=36,cases=512)
