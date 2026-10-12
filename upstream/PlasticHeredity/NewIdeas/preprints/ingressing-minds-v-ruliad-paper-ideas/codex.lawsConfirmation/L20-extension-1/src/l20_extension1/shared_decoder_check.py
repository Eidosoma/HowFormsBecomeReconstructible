"""D164 independent group-coordinate SVD, forecast and paired-score audit."""
import numpy as np
from . import asymmetry as a, asymmetry_check as oldcheck

CALIBRATION=('passive','sham_plus','sham_minus')
CLASS='condition_blind_equal_three_view_ridge_v1'


def close(x,y):np.testing.assert_allclose(x,y,atol=2e-10,rtol=0)


def reference_path(features,futures,encoding,keep):
    # Independent column construction and case/intervention row ordering.
    views=[oldcheck.matrix(features,encoding+':'+k)[keep] for k in CALIBRATION]
    X=np.stack(views,axis=3).reshape(-1,views[0].shape[-1])
    g=np.broadcast_to(np.arange(4,dtype=np.int64)[None,None,:,None],(len(keep),4,4,3)).ravel()
    y=np.repeat((np.sum(futures[keep],axis=-1)/4).ravel(),3)
    mu=np.array([X[g==v].sum(0)/np.count_nonzero(g==v) for v in range(4)])
    offset=np.array([y[g==v].sum()/np.count_nonzero(g==v) for v in range(4)])
    centered=X-mu[g];scale=np.sqrt(np.sum(centered**2,axis=0)/len(X));scale[scale<=1e-12]=1
    if encoding=='tied':
        z=np.concatenate((centered[:,:7]/scale[:7],
                          (centered[:,7:13]+centered[:,13:])/np.sqrt(scale[7:13]**2+scale[13:]**2)),axis=1)
    else:z=centered/scale
    white=np.eye(4)+.25*np.ones((4,4))
    design=np.einsum('ig,ij->igj',white[g],z).reshape(len(X),-1)
    u,s,vh=np.linalg.svd(design/np.sqrt(len(y)),full_matrices=False)
    projected=u.T@((y-offset[g])/np.sqrt(len(y)))
    q=np.array([[-1,-1,1],[-1,1,-1],[1,-1,-1],[1,1,1]],dtype=float)/2
    result=[]
    for alpha in (.001,.01,.1):
        eta_white=(vh.T@((s/(s*s+alpha))*projected)).reshape(4,-1)
        slopes=white@eta_white;eta=np.vstack((slopes.sum(0)/4,q.T@slopes))
        beta=eta.copy()
        if encoding=='tied':
            beta=np.zeros((4,19));beta[:,:7]=eta[:,:7];norm=np.sqrt(scale[7:13]**2+scale[13:]**2)
            beta[:,7:13]=eta[:,7:]*scale[7:13]/norm;beta[:,13:]=eta[:,7:]*scale[13:]/norm
            close(beta[:,7:13]/scale[7:13],beta[:,13:]/scale[13:])
        # Independent stationarity and preservation of the ridge norm.
        residual=design.T@(design@eta_white.ravel()-(y-offset[g]))/len(y)+alpha*eta_white.ravel()
        close(residual,0);close(np.sum(eta_white**2),np.sum(beta**2))
        result.append(dict(alpha=alpha,encoding=encoding,model_class=CLASS,calibration=list(CALIBRATION),
            means=mu.tolist(),offsets=offset.tolist(),scale=scale.tolist(),coefficients=beta.tolist(),
            reduced_coefficients=eta.tolist(),training_rows=len(y),unique_training_cases=len(y)//3))
    return result


def check_models(records,features,futures,ids):
    n=len(ids)
    expected=dict(schema='d164_shared_models_v1',training_blocks=ids.tolist(),calibration=list(CALIBRATION),
        encodings=['separate','mean','tied'],alphas=[.001,.01,.1],new_fits=9*(n+1),target='four_future_mean',
        pilot_outcomes_used=False,condition_indicator=False,inner_selection=False)
    assert {k:v for k,v in records.items() if k!='models'}==expected
    assert set(records['models'])=={'separate','mean','tied'}
    count=0;max_error=0.
    for encoding in ('separate','mean','tied'):
        r=records['models'][encoding];assert set(r)=={'training_blocks','folds','models'}
        assert r['training_blocks']==ids.tolist() and len(r['folds'])==n
        for excluded in [None]+list(range(n)):
            keep=[i for i in range(n) if i!=excluded]
            if excluded is None:models=r['models']
            else:
                fold=r['folds'][excluded];assert set(fold)=={'validation_block','training_blocks','models'}
                assert fold['validation_block']==int(ids[excluded]) and fold['training_blocks']==ids[keep].tolist()
                models=fold['models']
            expected=reference_path(features,futures,encoding,keep);assert len(models)==len(expected)==3
            for got,want in zip(models,expected):
                assert got.keys()==want.keys()
                for k in ('alpha','encoding','model_class','calibration','training_rows','unique_training_cases'):assert got[k]==want[k]
                for k in ('means','offsets','scale','coefficients','reduced_coefficients'):
                    close(got[k],want[k]);max_error=max(max_error,float(np.max(abs(np.asarray(got[k])-np.asarray(want[k])))))
                count+=1
    return dict(passes=True,fitted_models=count,max_coefficient_error=max_error,independent_group_svd=True,
                both_founder_views_and_outcomes_excluded=True,training_rows_normalized=True)


def check_forecasts(records,features,p,raw,ids=None):
    n=len(features['start']);keys={e+':'+k for e in ('separate','mean','tied') for k in a.EDITS}
    assert set(p)==set(raw)==keys and (ids is None or ids.tolist()==records['training_blocks'])
    max_error=0.
    for name in sorted(keys):
        encoding=name.split(':')[0];x=oldcheck.matrix(features,name);r=records['models'][encoding]
        if ids is None:expected=np.stack([oldcheck.forward(model,x) for model in r['models']])
        else:
            expected=np.stack([np.stack([oldcheck.forward(model,x[i:i+1])[0] for model in r['folds'][i]['models']])
                               for i in range(n)],axis=1)
        assert raw[name].shape==p[name].shape==(3,n,4,4)
        assert raw[name].dtype==p[name].dtype==np.float64 and np.isfinite(raw[name]).all()
        close(raw[name],expected);np.testing.assert_array_equal(p[name],np.maximum(-1,np.minimum(1,raw[name])))
        max_error=max(max_error,float(np.max(abs(expected-raw[name]))))
    return dict(passes=True,forecasts=45*16*n,max_prediction_error=max_error,
                same_parameters_all_five_conditions=True,two_copy_inference=True)


def check_summary(s,panels,sources,prior_summary):
    nd=len(sources['development'][3]);nt=len(sources['pilot'][3])
    header=dict(schema='d164_shared_decoder_v1',new_fits=9*(nd+1),new_forecasts=45*16*(nd+nt),
        reused_forecasts=6*16*(nd+nt),calibration=list(CALIBRATION),post_test_development=True,
        prospective_evidence=False,condition_indicator=False,training_exposure_changed=True,
        causal_sharing_only_ablation=False,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,
        source_primary_unchanged=True,confidence_intervals=False,automatic_successor=False)
    assert {k:v for k,v in s.items() if k!='cohorts'}==header and set(s['cohorts'])=={'development','pilot'}
    proofs={}
    for cohort in ('development','pilot'):
        p,raw=panels[cohort];old,old_raw,y,ids=sources[cohort];score=s['cohorts'][cohort]
        for k in ('starting','one_copy'):
            np.testing.assert_array_equal(p[k],old[k]);np.testing.assert_array_equal(raw[k],old_raw[k])
        new_proof=oldcheck.check_cohort(score['scores'],p,raw,y,ids)
        old_proof=oldcheck.check_cohort(prior_summary[cohort],old,old_raw,y,ids)
        names=list(a.OBSERVERS)+[e+':mean_sham_loss' for e in a.ENCODINGS]
        assert len(score['decoder_changes'])==60
        for row,(name,ai) in zip(score['decoder_changes'],[(k,j) for k in names for j in range(3)]):
            assert (row['observer'],row['alpha'],row['candidate'],row['reference'])==(name,a.ALPHAS[ai],'shared_decoder','original_decoder')
            def loss(panel):return sum(w*np.square(panel[k][ai,...,None]-y) for k,w in oldcheck.weighted(name))
            c,r=loss(p),loss(old);delta=r-c
            saved={k:np.asarray(row[k])[...,None].tolist() for k in ('overall','blocks','groups','futures','omit_founder','omit_future')}
            oldcheck.check_aggregate(saved,delta[...,None])
            close(row['candidate_mse'],c.sum()/c.size);close(row['reference_mse'],r.sum()/r.size)
            if r.mean():close(row['relative_gain_percent'],100*delta.mean()/r.mean())
            else:assert row['relative_gain_percent'] is None
            close(delta.mean(),(sum(w*(old[k][ai]-y.mean(-1))**2 for k,w in oldcheck.weighted(name))
                               -sum(w*(p[k][ai]-y.mean(-1))**2 for k,w in oldcheck.weighted(name))).mean())
            if name in ('starting','one_copy'):np.testing.assert_array_equal(delta,0)
        proofs[cohort]=dict(new=new_proof,original=old_proof,decoder_changes=60)
    return dict(passes=True,cohorts=proofs,source_primary_unchanged=True,cheap_baselines_exact=True)
