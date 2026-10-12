"""D154 one-copy information baseline; references reused, no model selection."""
import numpy as np
from . import matched_models as prior

ALPHAS=prior.ALPHAS
MODELS=('starting','one_copy','passive','shuffle','attenuate','sham_plus','sham_minus')
PAIRS=(('one_copy','starting'),)+tuple((k,'one_copy') for k in prior.MODELS[1:])+ (('mean_sham_loss','one_copy'),)


def features(data):
    a=data['start'];e=data['endpoint']
    if a.ndim!=4 or a.shape[1:]!=(4,4,7) or e.shape!=a.shape[:-1]+(3,6):raise ValueError('complete one-copy feature schema')
    x=np.concatenate((a,e[...,0,:]),axis=-1)
    if not np.isfinite(x).all():raise ValueError('finite permitted features')
    return x


def fit_all(data,progress=None):
    x=features(data);ids=data['block_ids']
    rows=[]
    for b in range(len(ids)):
        rows.append(prior.outer(x,data['labels'],ids,b))
        if progress is not None:progress(int(ids[b]))
    p=np.stack([r[0] for r in rows],axis=1)
    m=dict(blocks=ids.tolist(),alphas=list(ALPHAS),folds=[r[1] for r in rows],
        preprocessing='training-only in every outer fold',inner_selection=False,
        prospective_evidence=False,model_class=prior.group.CLASS,feature_definition='starting_7_then_U0_endpoint_6')
    return {'one_copy':p},m


def fixture():
    data=prior.group.fixture();rng=np.random.default_rng(15420260920)
    references={k:np.clip(.35*data['start'][...,0][None]+rng.normal(scale=.1,size=(3,32,4,4)),-1,1) for k in prior.MODELS}
    nested={k:references[k][i%3].copy() for i,k in enumerate(prior.MODELS)}
    source=prior.summarize(references,nested,data)
    return data,references,nested,source


def stats(p,data):
    y=data['labels'];f=data['futures'];e=p[16:,...,None]-f
    if p.shape!=y.shape or not np.isfinite(p).all() or np.max(abs(p))>1:raise ValueError('bounded complete predictions')
    loss=(p-y)**2;future=(e*e).mean(axis=-1);mean=(p[16:]-f.mean(axis=-1))**2
    np.testing.assert_allclose(future,mean+f.var(axis=-1),atol=1e-14,rtol=0)
    return dict(original=prior.group.ridge.errors(p,y),
        cohorts={c:prior.group.ridge.errors(p[l:h],y[l:h]) for c,l,h in prior.COHORTS},
        individual_futures=dict(mse=float((e*e).mean()),mae_points=float(abs(e).mean()*100),
            rmse_points=float(np.sqrt((e*e).mean())*100),block_mse=(e*e).mean(axis=(1,2,3)).tolist(),
            group_mse=(e*e).mean(axis=(0,1,3)).tolist()),
        mean_target=prior.group.ridge.errors(p[16:],f.mean(axis=-1))), (loss,future,mean)


def metadata():
    return dict(schema='d154_one_copy_development_v1',stage='POST_RESULT_DEVELOPMENT',prospective_evidence=False,
        blocks=32,cases=512,all_cases_retained=True,alphas=list(ALPHAS),observers=list(MODELS),
        feature_definition='starting_7_then_U0_endpoint_6',new_feature_dimension=13,new_penalized_dimension=52,
        model_class=prior.group.CLASS,common_deviation_penalty_ratio=1,new_fits=96,new_predictions=1536,
        inner_selection=False,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,reference_fits_recomputed=False,
        original_reference_summary_exact=True,retained_reference_contrasts=90,new_contrasts=21,
        one_copy_budget=1,two_copy_budget=2,equal_observation_budget=False,
        equal_alpha_is_not_equal_effective_complexity=True,former_test_is_now_development=True,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,model_selected_for_deployment=False,no_best_alpha_selected=True,
        mean_sham_is_loss_average_not_prediction_ensemble=True,automatic_successor=False,
        focal_pairs=[['one_copy','starting'],['passive','one_copy'],['sham_minus','one_copy']])


def summarize(p,references,source_summary,data):
    assert set(p)=={'one_copy'} and p['one_copy'].shape==(3,32,4,4)
    assert data['labels'].shape==(32,4,4) and data['futures'].shape==(16,4,4,4)
    scores={}
    for i,a in enumerate(ALPHAS):
        guesses={k:references[k][i] for k in prior.MODELS}
        _,losses=prior.score(guesses,data);score,one=stats(p['one_copy'][i],data)
        for bundle,value in zip(losses,one):bundle['one_copy']=value
        comparisons=[]
        for c,r in PAIRS:
            loss,future,mean=losses
            comparisons.append(dict(candidate=c,reference=r,**prior.comparison(loss[c],loss[r],future[c],future[r],mean[c],mean[r])))
        scores[str(a)]=dict(one_copy=score,comparisons=comparisons)
    return dict(**metadata(),scores=scores,retained_d153=source_summary)


def case_errors(p,references,nested,data):
    result=prior.case_errors(references,nested,data);e=p['one_copy']-data['labels'][None]
    result.update(one_copy__signed=e,one_copy__absolute=abs(e),one_copy__squared=e*e)
    return result
