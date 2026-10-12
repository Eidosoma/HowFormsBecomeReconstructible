"""D155 fixed mean encoding; old predictions reused, no selection or dynamics."""
import numpy as np
from . import onecopy_models as prior

ALPHAS=prior.ALPHAS
MODELS=('passive','shuffle','attenuate','sham_plus','sham_minus')
FEATURES='starting_7_then_raw_arithmetic_endpoint_mean_6'


def features(data):
    a=data['start'];e=data['endpoint'];t=data['targeted']
    if a.ndim!=4 or a.shape[1:]!=(4,4,7) or e.shape!=a.shape[:-1]+(3,6) or t.shape!=e.shape:
        raise ValueError('complete paired endpoint schema')
    second=(e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])
    result={name:np.concatenate((a,(e[...,0,:]+b)/2),axis=-1) for name,b in zip(MODELS,second)}
    if not all(np.isfinite(v).all() for v in result.values()):raise ValueError('finite permitted features')
    return result


def fit_all(data,progress=None):
    x=features(data);ids=data['block_ids'];p={};m={}
    for name in MODELS:
        rows=[prior.prior.outer(x[name],data['labels'],ids,b) for b in range(len(ids))]
        p[name]=np.stack([r[0] for r in rows],axis=1)
        m[name]=dict(blocks=ids.tolist(),alphas=list(ALPHAS),folds=[r[1] for r in rows],
            preprocessing='training-only in every outer fold',inner_selection=False,prospective_evidence=False,
            model_class=prior.prior.group.CLASS,feature_definition=FEATURES,observer=name)
        if progress is not None:progress(name)
    return p,m


def fixture():
    data,refs,nested,source=prior.fixture();one={'one_copy':(refs['starting']+refs['passive'])/2}
    summary=prior.summarize(one,refs,source,data)
    return data,{**refs,**one},nested,summary


def specs():
    pairs=[('mean:'+k,'separate:'+k) for k in MODELS]
    pairs.extend(('mean:'+k,r) for k in MODELS for r in ('one_copy','starting'))
    pairs.extend(('mean:'+c,'mean:'+r) for c,r in prior.prior.PAIRS if c in MODELS and r in MODELS)
    pairs.extend([('mean:mean_sham_loss','mean:passive'),('mean:mean_sham_loss','one_copy'),
        ('mean:mean_sham_loss','starting'),('mean:mean_sham_loss','separate:mean_sham_loss'),
        ('mean:attenuate','mean:mean_sham_loss')])
    return pairs


def panel(p,refs,data,i):
    scores={};losses={}
    for name in MODELS:scores[name],losses['mean:'+name]=prior.stats(p[name][i],data)
    for name in prior.MODELS:
        key='separate:'+name if name in MODELS else name
        _,losses[key]=prior.stats(refs[name][i],data)
    for prefix in ('mean:','separate:'):
        losses[prefix+'mean_sham_loss']=tuple((a+b)/2 for a,b in zip(losses[prefix+'sham_plus'],losses[prefix+'sham_minus']))
    return scores,losses


def metadata():
    return dict(schema='d155_mean_compression_development_v1',stage='POST_RESULT_DEVELOPMENT',prospective_evidence=False,
        blocks=32,cases=512,all_cases_retained=True,alphas=list(ALPHAS),new_observers=list(MODELS),
        feature_definition=FEATURES,feature_dimension=13,penalized_dimension=52,raw_mean_before_standardization=True,
        model_class=prior.prior.group.CLASS,common_deviation_penalty_ratio=1,new_fits=480,new_predictions=7680,
        inner_selection=False,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,reference_fits_recomputed=False,
        original_reference_summary_exact=True,retained_reference_contrasts=111,new_contrasts=90,
        two_copy_budget=2,one_copy_budget=1,equal_dimension_is_not_equal_effective_complexity=True,
        discarded_between_copy_differences=True,former_test_is_now_development=True,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,model_selected_for_deployment=False,no_best_alpha_selected=True,
        mean_sham_is_loss_average_not_prediction_ensemble=True,automatic_successor=False,
        focal_pairs=[['mean:passive','separate:passive'],['mean:passive','one_copy'],['mean:sham_minus','mean:passive']])


def summarize(p,refs,source_summary,data):
    assert set(p)==set(MODELS) and all(v.shape==(3,32,4,4) for v in p.values())
    assert set(refs)==set(prior.MODELS) and data['labels'].shape==(32,4,4) and data['futures'].shape==(16,4,4,4)
    scores={}
    for i,alpha in enumerate(ALPHAS):
        models,loss=panel(p,refs,data,i);comparisons=[]
        for c,r in specs():
            a,af,am=loss[c];b,bf,bm=loss[r]
            comparisons.append(dict(candidate=c,reference=r,**prior.prior.comparison(a,b,af,bf,am,bm)))
        scores[str(alpha)]=dict(models=models,comparisons=comparisons)
    return dict(**metadata(),scores=scores,retained_d154=source_summary)


def case_errors(p,refs,nested,data):
    result=prior.case_errors({'one_copy':refs['one_copy']},{k:refs[k] for k in prior.prior.MODELS},nested,data)
    for name in MODELS:
        e=p[name]-data['labels'][None]
        result['mean_'+name+'__signed']=e;result['mean_'+name+'__absolute']=abs(e);result['mean_'+name+'__squared']=e*e
    return result
