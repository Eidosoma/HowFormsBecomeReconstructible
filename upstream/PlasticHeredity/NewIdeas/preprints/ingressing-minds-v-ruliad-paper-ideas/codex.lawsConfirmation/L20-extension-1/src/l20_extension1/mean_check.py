"""Independent D155 average assembly, group-slope SVD and complete scoring."""
import numpy as np
from . import onecopy_check as prior

MODELS=('passive','shuffle','attenuate','sham_plus','sham_minus')
ALPHAS=(.001,.01,.1)
FEATURES='starting_7_then_raw_arithmetic_endpoint_mean_6'
same=prior.same


def features(data):
    n=len(data['block_ids']);a=data['start'];e=data['endpoint'];t=data['targeted']
    assert a.shape==(n,4,4,7) and e.shape==t.shape==(n,4,4,3,6)
    result={}
    for name,source,index in (('passive',e,1),('shuffle',e,2),('attenuate',t,0),('sham_plus',t,1),('sham_minus',t,2)):
        x=np.empty((n,4,4,13),np.float64);x[...,:7]=a;x[...,7:]=.5*e[...,0,:]+.5*source[...,index,:]
        assert np.isfinite(x).all();result[name]=x
    return result


def check_all(p,m,data):
    n=len(data['block_ids']);ids=data['block_ids'];assert set(p)==set(m)==set(MODELS)
    assert ids.dtype==np.int64 and len(set(ids.tolist()))==n and n>=4 and data['labels'].shape==(n,4,4)
    y=data['labels'].ravel();g=np.tile(np.arange(4,dtype=np.int64),n*4);x=features(data)
    assert np.isfinite(y).all() and np.max(abs(y))<=1
    for name in MODELS:
        assert p[name].shape==(3,n,4,4) and np.isfinite(p[name]).all() and np.max(abs(p[name]))<=1
        assert len(m[name]['folds'])==n;X=x[name].reshape(n*16,13)
        for b in range(n):
            blocks=[j for j in range(n) if j!=b];train=np.concatenate([np.arange(j*16,(j+1)*16) for j in blocks]);test=np.arange(b*16,(b+1)*16)
            guesses,records=prior.prior.group.svd_path(X[train],y[train],g[train],X[test],g[test])
            np.testing.assert_allclose(p[name][:,b],guesses[:,:3].T.reshape(3,4,4),atol=2e-10,rtol=0)
            same(m[name]['folds'][b],dict(validation_block=int(ids[b]),training_blocks=ids[blocks].tolist(),models=records[:3]))
        same({k:v for k,v in m[name].items() if k!='folds'},dict(blocks=ids.tolist(),alphas=list(ALPHAS),
            preprocessing='training-only in every outer fold',inner_selection=False,prospective_evidence=False,
            model_class=prior.prior.group.CLASS,feature_definition=FEATURES,observer=name))
    return dict(passes=True,models=5,settings=3,outer_fits=n*15,inner_fits=0,svd_group_coordinates=True,features=13)


def specs():
    result=[('mean:'+k,'separate:'+k) for k in MODELS]
    result += [('mean:'+k,r) for k in MODELS for r in ('one_copy','starting')]
    pairs=(('shuffle','passive'),('attenuate','passive'),('attenuate','shuffle'),('attenuate','sham_plus'),
        ('attenuate','sham_minus'),('sham_plus','passive'),('sham_plus','shuffle'),('sham_minus','passive'),
        ('sham_minus','shuffle'),('sham_minus','sham_plus'))
    result += [('mean:'+c,'mean:'+r) for c,r in pairs]
    result += [('mean:mean_sham_loss','mean:passive'),('mean:mean_sham_loss','one_copy'),
        ('mean:mean_sham_loss','starting'),('mean:mean_sham_loss','separate:mean_sham_loss'),('mean:attenuate','mean:mean_sham_loss')]
    return result


def check_summary(s,p,refs,nested,source,data):
    assert set(p)==set(MODELS) and all(v.shape==(3,32,4,4) for v in p.values())
    assert set(refs)==set(prior.prior.MODELS)|{'one_copy'} and s['retained_d154']==source
    prior.check_summary(source,{'one_copy':refs['one_copy']},{k:refs[k] for k in prior.prior.MODELS},nested,source['retained_d153'],data)
    scores={}
    for i,label in enumerate(('0.001','0.01','0.1')):
        models={};loss={}
        for name in MODELS:models[name],loss['mean:'+name]=prior.stats(p[name][i],data)
        for name in ('starting','one_copy',*MODELS):
            _,loss['separate:'+name if name in MODELS else name]=prior.stats(refs[name][i],data)
        for prefix in ('mean:','separate:'):
            loss[prefix+'mean_sham_loss']=tuple(.5*loss[prefix+'sham_plus'][j]+.5*loss[prefix+'sham_minus'][j] for j in range(3))
        comparisons=[]
        for c,r in specs():
            a,af,am=loss[c];b,bf,bm=loss[r]
            comparisons.append(dict(candidate=c,reference=r,**prior.prior.contrast(a,b,af,bf,am,bm)))
        scores[label]=dict(models=models,comparisons=comparisons)
    expected=dict(schema='d155_mean_compression_development_v1',stage='POST_RESULT_DEVELOPMENT',prospective_evidence=False,
        blocks=32,cases=512,all_cases_retained=True,alphas=[.001,.01,.1],new_observers=list(MODELS),
        feature_definition=FEATURES,feature_dimension=13,penalized_dimension=52,raw_mean_before_standardization=True,
        model_class=prior.prior.group.CLASS,common_deviation_penalty_ratio=1,new_fits=480,new_predictions=7680,
        inner_selection=False,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,reference_fits_recomputed=False,
        original_reference_summary_exact=True,retained_reference_contrasts=111,new_contrasts=90,
        two_copy_budget=2,one_copy_budget=1,equal_dimension_is_not_equal_effective_complexity=True,
        discarded_between_copy_differences=True,former_test_is_now_development=True,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,model_selected_for_deployment=False,no_best_alpha_selected=True,
        mean_sham_is_loss_average_not_prediction_ensemble=True,automatic_successor=False,
        focal_pairs=[['mean:passive','separate:passive'],['mean:passive','one_copy'],['mean:sham_minus','mean:passive']],
        scores=scores,retained_d154=source)
    same(s,expected)
    return dict(passes=True,settings=3,new_contrasts=90,retained_contrasts=111,blocks=32,cases=512,secondary_outcomes=1024)


def check_errors(stored,p,refs,nested,data):
    names={f'mean_{name}__{kind}' for name in MODELS for kind in ('signed','absolute','squared')}
    assert len(stored)==90
    prior.check_errors({k:v for k,v in stored.items() if k not in names},{'one_copy':refs['one_copy']},
        {k:refs[k] for k in prior.prior.MODELS},nested,data)
    for name in MODELS:
        e=p[name]-data['labels'][None]
        for suffix,v in (('signed',e),('absolute',np.maximum(e,-e)),('squared',np.square(e))):
            np.testing.assert_array_equal(stored[f'mean_{name}__{suffix}'],v)
    return dict(passes=True,new_case_arrays=15,retained_case_arrays=75,all_cases_retained=True)
