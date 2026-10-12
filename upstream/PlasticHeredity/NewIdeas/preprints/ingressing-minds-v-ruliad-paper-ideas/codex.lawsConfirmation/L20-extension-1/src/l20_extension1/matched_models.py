"""D153: predeclared matched penalties, no selection or new dynamics."""
import numpy as np
from . import group_models as group, group_review as review

ALPHAS=(.001,.01,.1)
MODELS=group.MODELS
PAIRS=review.PAIRS
SETTINGS=('0.001','0.01','0.1','nested')
COHORTS=(('d135',0,8),('d140',8,16),('former_test',16,32))


def outer(x,y,ids,b):
    X,Y,g,rows=group.panel(x,y,ids)
    if not 0<=b<len(x):raise ValueError('outer block')
    train=rows!=b;test=~train
    records=[group.fit(X[train],Y[train],g[train],a) for a in ALPHAS]
    guesses=np.stack([group.predict(m,X[test],g[test]).reshape(4,4) for m in records])
    return guesses,dict(validation_block=int(ids[b]),training_blocks=np.delete(ids,b).tolist(),models=records)


def fit_all(data,progress=None):
    x=group.matrices(data);p={};m={};ids=data['block_ids']
    for name in MODELS:
        rows=[outer(x[name],data['labels'],ids,b) for b in range(len(ids))]
        p[name]=np.stack([v[0] for v in rows],axis=1)
        m[name]=dict(blocks=ids.tolist(),alphas=list(ALPHAS),folds=[v[1] for v in rows],
            preprocessing='training-only in every outer fold',inner_selection=False,
            prospective_evidence=False,model_class=group.CLASS)
        if progress is not None:progress(name)
    return p,m


def fixture():
    data=group.fixture();p,m=fit_all(data);old={};fits={}
    for k,name in enumerate(MODELS):
        indices=[(b+k)%3 for b in range(32)]
        old[name]=np.stack([p[name][i,b] for b,i in enumerate(indices)])
        fits[name]=dict(folds=[dict(validation_block=int(data['block_ids'][b]),
            training_blocks=m[name]['folds'][b]['training_blocks'],selected_index=i,
            model=m[name]['folds'][b]['models'][i]) for b,i in enumerate(indices)])
    return data,p,m,old,fits


def by_setting(p,old):
    return {**{str(a):{k:p[k][i] for k in MODELS} for i,a in enumerate(ALPHAS)},'nested':old}


def loss_panel(p,y):
    out={k:(p[k]-y)**2 for k in MODELS}
    out['mean_sham_loss']=(out['sham_plus']+out['sham_minus'])/2
    return out


def effect(c,r):
    result=group.ridge.paired(c,r);n=len(c);d=np.asarray(result['block_differences'])
    result['leave_one_score_block_out']=((d.sum()-d)/(n-1)).tolist()
    result['groups']=[group.ridge.paired(c[:,:,g:g+1],r[:,:,g:g+1]) for g in range(4)]
    return result


def comparison(c,r,cf,rf,cm,rm):
    original=effect(c,r);future=effect(cf,rf);mean=effect(cm,rm)
    np.testing.assert_allclose(future['block_differences'],mean['block_differences'],atol=1e-14,rtol=0)
    return dict(original=original,cohorts={k:effect(c[l:h],r[l:h]) for k,l,h in COHORTS},
        individual_futures=future,mean_target=mean)


def score(p,data):
    y=data['labels'];f=data['futures'];loss=loss_panel(p,y)
    future=loss_panel({k:p[k][16:,...,None] for k in MODELS},f)
    future={k:v.mean(axis=-1) for k,v in future.items()}
    mean=loss_panel({k:p[k][16:] for k in MODELS},f.mean(axis=-1));scores={}
    for k in MODELS:
        e=p[k][16:,...,None]-f
        scores[k]=dict(original=group.ridge.errors(p[k],y),
            cohorts={c:group.ridge.errors(p[k][l:h],y[l:h]) for c,l,h in COHORTS},
            individual_futures=dict(mse=float(np.mean(e*e)),mae_points=float(abs(e).mean()*100),
                rmse_points=float(np.sqrt(np.mean(e*e))*100),block_mse=np.mean(e*e,axis=(1,2,3)).tolist(),
                group_mse=np.mean(e*e,axis=(0,1,3)).tolist()),
            mean_target=group.ridge.errors(p[k][16:],f.mean(axis=-1)))
        np.testing.assert_allclose(future[k],mean[k]+f.var(axis=-1),atol=1e-14,rtol=0)
    contrasts=[dict(candidate=c,reference=r,**comparison(loss[c],loss[r],future[c],future[r],mean[c],mean[r])) for c,r in PAIRS]
    return dict(models=scores,comparisons=contrasts), (loss,future,mean)


def metadata():
    return dict(schema='d153_matched_regularization_development_v1',stage='POST_RESULT_DEVELOPMENT',
        prospective_evidence=False,blocks=32,cases=512,all_cases_retained=True,alphas=list(ALPHAS),
        settings=list(SETTINGS),observers=list(MODELS),new_fits=576,new_predictions=9216,
        inner_selection=False,model_class=group.CLASS,common_deviation_penalty_ratio=1,
        feature_dimensions=[7,19,19,19,19,19],penalized_dimensions=[28,76,76,76,76,76],
        equal_alpha_is_not_equal_effective_complexity=True,former_test_is_now_development=True,
        old_nested_predictions_reused=True,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,model_selected_for_deployment=False,automatic_successor=False,
        mean_sham_is_loss_average_not_prediction_ensemble=True,
        focus=['sham_minus','passive'],no_best_alpha_selected=True)


def summarize(p,old,data):
    assert data['labels'].shape==(32,4,4) and data['futures'].shape==(16,4,4,4)
    bundles={};losses={}
    for setting,guesses in by_setting(p,old).items():bundles[setting],losses[setting]=score(guesses,data)
    changes=[]
    for setting in SETTINGS[:-1]:
        for name in MODELS:
            c,cf,cm=(v[name] for v in losses[setting]);r,rf,rm=(v[name] for v in losses['nested'])
            changes.append(dict(setting=setting,observer=name,reference='nested',**comparison(c,r,cf,rf,cm,rm)))
    return dict(**metadata(),scores=bundles,fixed_vs_nested=changes)


def case_errors(p,old,data):
    result={}
    for setting,guesses in by_setting(p,old).items():
        for name in MODELS:
            e=guesses[name]-data['labels'];key=setting+'__'+name
            result[key+'__signed']=e;result[key+'__absolute']=abs(e);result[key+'__squared']=e*e
    return result
