"""D150 nested whole-block development fits; no source/dynamics access."""
import numpy as np

ALPHAS=(.001,.01,.1,1.,10.,100.)
MODELS=('starting','passive_endpoint','challenge_endpoint','passive_recovery','challenge_recovery')
CONTRASTS=(('challenge_recovery','passive_recovery'),('challenge_endpoint','passive_endpoint'),
    ('passive_recovery','passive_endpoint'),('challenge_recovery','challenge_endpoint'),
    ('passive_endpoint','starting'),('challenge_endpoint','starting'),
    ('passive_recovery','starting'),('challenge_recovery','starting'))


def validate(x,y,groups):
    if x.ndim!=2 or len(x)!=len(y) or y.ndim!=1 or groups.shape!=y.shape:raise ValueError('paired rows')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.max(abs(y))>1:raise ValueError('finite bounded training data')
    if groups.dtype!=np.int64 or set(groups.tolist())!=set(range(4)):raise ValueError('all four groups required')


def prepare(x,y,groups):
    validate(x,y,groups)
    means=np.stack([x[groups==g].mean(axis=0) for g in range(4)])
    offsets=np.array([y[groups==g].mean() for g in range(4)])
    centered=x-means[groups];scale=np.sqrt(np.mean(centered*centered,axis=0));scale[scale<=1e-12]=1.
    return means,offsets,scale,centered/scale,y-offsets[groups]


def fit(x,y,groups,alpha):
    if alpha not in ALPHAS:raise ValueError('frozen alpha grid')
    means,offsets,scale,z,t=prepare(x,y,groups)
    beta=np.linalg.solve(z.T@z/len(y)+alpha*np.eye(x.shape[1]),z.T@t/len(y))
    return dict(alpha=alpha,means=means.tolist(),offsets=offsets.tolist(),scale=scale.tolist(),beta=beta.tolist())


def predict(model,x,groups):
    means,offsets,scale,beta=(np.asarray(model[k]) for k in ('means','offsets','scale','beta'))
    if x.ndim!=2 or x.shape[1]!=len(beta) or groups.shape!=(len(x),):raise ValueError('model/row schema')
    return np.clip(offsets[groups]+((x-means[groups])/scale)@beta,-1.,1.)


def path(x,y,g,z,h):
    means,offsets,scale,train,target=prepare(x,y,g)
    gram=train.T@train/len(y);cross=train.T@target/len(y);test=(z-means[h])/scale
    return np.stack([np.clip(offsets[h]+test@np.linalg.solve(gram+a*np.eye(x.shape[1]),cross),-1.,1.) for a in ALPHAS],-1)


def nested(x,y,block_ids):
    x=np.asarray(x);y=np.asarray(y);block_ids=np.asarray(block_ids)
    if x.ndim!=4 or x.shape[1:3]!=(4,4) or y.shape!=x.shape[:3]:raise ValueError('complete blocks/lives/groups required')
    nb=len(x)
    if nb<4 or block_ids.shape!=(nb,) or block_ids.dtype!=np.int64 or len(set(block_ids.tolist()))!=nb:raise ValueError('unique whole-block IDs')
    groups=np.tile(np.arange(4,dtype=np.int64),nb*4);rows=np.repeat(np.arange(nb),16)
    X=x.reshape(nb*16,-1);Y=y.ravel();validate(X,Y,groups)
    forecasts=np.empty_like(y);folds=[]
    for outer in range(nb):
        train_blocks=[i for i in range(nb) if i!=outer];losses=[]
        for inner in train_blocks:
            keep=(rows!=outer)&(rows!=inner);test=rows==inner
            guesses=path(X[keep],Y[keep],groups[keep],X[test],groups[test])
            losses.append(np.mean((guesses-Y[test,None])**2,axis=0))
        losses=np.stack(losses);errors=losses.mean(axis=0)
        ai=max(i for i in range(len(ALPHAS)) if errors[i]<=errors.min()+1e-12)
        keep=rows!=outer;test=~keep
        model=fit(X[keep],Y[keep],groups[keep],ALPHAS[ai])
        forecasts[outer]=predict(model,X[test],groups[test]).reshape(4,4)
        folds.append(dict(validation_block=int(block_ids[outer]),training_blocks=block_ids[train_blocks].tolist(),
            inner_validation_blocks=block_ids[train_blocks].tolist(),inner_block_mse=losses.tolist(),
            inner_mean_mse=errors.tolist(),selected_index=ai,model=model))
    return forecasts,dict(blocks=block_ids.tolist(),alphas=list(ALPHAS),folds=folds,
        preprocessing='training-only in every inner and outer fold',prospective_evidence=False)


def fit_all(features,y,ids):
    if set(features)!=set(MODELS):raise ValueError('five frozen models')
    forecasts={};fits={}
    for name in MODELS:forecasts[name],fits[name]=nested(features[name],y,ids)
    return forecasts,fits


def errors(prediction,y):
    e=prediction-y;sq=e*e
    return dict(mse=float(sq.mean()),mae_points=float(abs(e).mean()*100),rmse_points=float(np.sqrt(sq.mean())*100),
        block_mse=sq.mean(axis=(1,2)).tolist(),block_mae_points=(100*abs(e).mean(axis=(1,2))).tolist(),
        group_mse=sq.mean(axis=(0,1)).tolist())


def paired(a,b):
    # Errors of the reference minus candidate: positive favors candidate.
    d=(b-a).mean(axis=(1,2));base=float(b.mean());mean=float(d.mean())
    return dict(mse_reduction=mean,relative_reduction_percent=100*mean/base if base else None,
        block_differences=d.tolist(),positive_blocks=int((d>0).sum()),negative_blocks=int((d<0).sum()),zero_blocks=int((d==0).sum()))


def summarize(predictions,fits,y,futures,specs):
    assert set(predictions)==set(fits)==set(MODELS) and y.shape==(32,4,4) and futures.shape==(16,4,4,4)
    assert np.isfinite(y).all() and np.isfinite(futures).all() and np.max(abs(y))<=1 and np.max(abs(futures))<=1
    assert len(specs)==32 and [s[0] for s in specs]==['d135']*8+['d140']*8+['former_test']*16
    scores={};future_scores={};loss={};future_loss={};mean_loss={}
    for name in MODELS:
        p=predictions[name]
        assert p.shape==y.shape and np.isfinite(p).all() and np.max(abs(p))<=1
        loss[name]=(p-y)**2
        score=errors(p,y)
        score['cohorts']={key:errors(p[start:stop],y[start:stop]) for key,start,stop in (('d135',0,8),('d140',8,16),('former_test',16,32))}
        selected=[f['model']['alpha'] for f in fits[name]['folds']]
        score['selected_alphas']=selected;score['alpha_counts']={str(a):selected.count(a) for a in ALPHAS}
        scores[name]=score
        e=p[16:,...,None]-futures;future_loss[name]=(e*e).mean(axis=-1)
        mean_loss[name]=(p[16:]-futures.mean(axis=-1))**2
        future_scores[name]=dict(individual_future_mse=float((e*e).mean()),individual_future_mae_points=float(abs(e).mean()*100),
            individual_future_block_mse=(e*e).mean(axis=(1,2,3)).tolist(),individual_future_group_mse=(e*e).mean(axis=(0,1,3)).tolist(),
            mean_target_mse=float(mean_loss[name].mean()),mean_target_block_mse=mean_loss[name].mean(axis=(1,2)).tolist(),
            mean_target_group_mse=mean_loss[name].mean(axis=(0,1)).tolist())
    comparisons=[];repeated=[]
    for candidate,reference in CONTRASTS:
        comparisons.append(dict(candidate=candidate,reference=reference,**paired(loss[candidate],loss[reference])))
        a=paired(future_loss[candidate],future_loss[reference]);b=paired(mean_loss[candidate],mean_loss[reference])
        np.testing.assert_allclose(a['block_differences'],b['block_differences'],atol=1e-14,rtol=0)
        repeated.append(dict(candidate=candidate,reference=reference,individual_futures=a,mean_target=b))
    return dict(schema='d150_recovery_prediction_development_v1',stage='POST_RESULT_DEVELOPMENT',prospective_evidence=False,
        all_cases_retained=True,blocks=32,cases=512,diagnostic_cycles=1536,new_dynamics=0,new_founders=0,
        former_test_is_now_development=True,models=scores,comparisons=comparisons,
        central_comparison=comparisons[0],repeated_future_models=future_scores,repeated_future_comparisons=repeated,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,success_threshold=False,model_selected_for_deployment=False,
        new_challenge_selected=False,automatic_successor=False,
        interpretation='Exploratory nested whole-founder validation on observed cohorts; not new prospective evidence.')


def fixture(blocks=32,seed=15020260919):
    rng=np.random.default_rng(seed)
    start=rng.normal(size=(blocks,4,4,7));end=rng.normal(size=(blocks,4,4,3,6));recovery=rng.normal(size=end.shape)
    y=np.clip(.2*start[...,0]+.07*end[...,0,0]+.03*recovery[...,1,1]+rng.normal(scale=.07,size=(blocks,4,4)),-1,1)
    return dict(start=start,endpoint=end,recovery=recovery),y
