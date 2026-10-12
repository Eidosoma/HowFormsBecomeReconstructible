"""D152: one fixed partially pooled group-slope class; no source/dynamics access."""
import numpy as np
from . import recovery_models as ridge, probe_models as observers

ALPHAS=ridge.ALPHAS
MODELS=observers.MODELS
CONTRASTS=observers.CONTRASTS
Q=np.array([[-.5,-.5,.5],[-.5,.5,-.5],[.5,-.5,-.5],[.5,.5,.5]])
CLASS='common_plus_zero_sum_group_deviations_penalty_ratio_1'
SCORE_KEYS=('models','comparisons','central_comparison','repeated_future_models','repeated_future_comparisons')


def design(z,g):
    if z.ndim!=2 or g.shape!=(len(z),) or g.dtype!=np.int64 or not set(g.tolist())<=set(range(4)):
        raise ValueError('public group schema')
    return np.concatenate([z]+[z*Q[g,j,None] for j in range(3)],axis=1)


def fit(x,y,g,alpha):
    if alpha not in ALPHAS:raise ValueError('frozen alpha grid')
    mu,offset,scale,z,t=ridge.prepare(x,y,g);a=design(z,g)
    b=np.linalg.solve(a.T@a/len(y)+alpha*np.eye(a.shape[1]),a.T@t/len(y))
    return dict(alpha=alpha,means=mu.tolist(),offsets=offset.tolist(),scale=scale.tolist(),
        coefficients=b.reshape(4,x.shape[1]).tolist(),model_class=CLASS)


def predict(model,x,g):
    if model['model_class']!=CLASS:raise ValueError('frozen model class')
    mu,offset,scale,b=(np.asarray(model[k]) for k in ('means','offsets','scale','coefficients'))
    if b.shape!=(4,x.shape[-1]) or mu.shape!=b.shape or scale.shape!=(x.shape[-1],) or offset.shape!=(4,):
        raise ValueError('model schema')
    if not all(np.isfinite(v).all() for v in (x,mu,offset,scale,b)) or np.any(scale<=0):raise ValueError('finite model')
    return np.clip(offset[g]+design((x-mu[g])/scale,g)@b.ravel(),-1.,1.)


def path(x,y,g,test,h):
    mu,offset,scale,z,t=ridge.prepare(x,y,g);a=design(z,g);b=design((test-mu[h])/scale,h)
    gram=a.T@a/len(y);cross=a.T@t/len(y)
    return np.stack([np.clip(offset[h]+b@np.linalg.solve(gram+alpha*np.eye(a.shape[1]),cross),-1,1)
        for alpha in ALPHAS],axis=-1)


def panel(x,y,ids):
    x=np.asarray(x);y=np.asarray(y);ids=np.asarray(ids);n=len(x)
    if x.ndim!=4 or x.shape[1:3]!=(4,4) or y.shape!=x.shape[:3] or n<4:raise ValueError('all blocks/lives/groups')
    if ids.shape!=(n,) or ids.dtype!=np.int64 or len(set(ids.tolist()))!=n:raise ValueError('unique whole-founder IDs')
    X=x.reshape(n*16,-1);Y=y.ravel();g=np.tile(np.arange(4,dtype=np.int64),n*4)
    ridge.validate(X,Y,g);return X,Y,g,np.repeat(np.arange(n),16)


def outer_fold(x,y,ids,outer):
    X,Y,g,rows=panel(x,y,ids);n=len(x)
    if not 0<=outer<n:raise ValueError('outer index')
    blocks=[i for i in range(n) if i!=outer];losses=[]
    for inner in blocks:
        keep=(rows!=outer)&(rows!=inner);test=rows==inner
        p=path(X[keep],Y[keep],g[keep],X[test],g[test]);losses.append(np.mean((p-Y[test,None])**2,axis=0))
    losses=np.stack(losses);mean=losses.mean(axis=0)
    ai=max(i for i in range(len(ALPHAS)) if mean[i]<=mean.min()+1e-12)
    keep=rows!=outer;test=~keep;m=fit(X[keep],Y[keep],g[keep],ALPHAS[ai])
    fold=dict(validation_block=int(ids[outer]),training_blocks=ids[blocks].tolist(),
        inner_validation_blocks=ids[blocks].tolist(),inner_block_mse=losses.tolist(),
        inner_mean_mse=mean.tolist(),selected_index=ai,model=m)
    return predict(m,X[test],g[test]).reshape(4,4),fold


def nested(x,y,ids):
    panel(x,y,ids);predictions=[];folds=[]
    for i in range(len(x)):
        p,m=outer_fold(x,y,ids,i);predictions.append(p);folds.append(m)
    return np.stack(predictions),dict(blocks=ids.tolist(),alphas=list(ALPHAS),folds=folds,
        preprocessing='training-only in every inner and outer fold',prospective_evidence=False,model_class=CLASS)


def matrices(data):
    return observers.matrices(data['start'],data['endpoint'],data['targeted'])


def fit_all(data,progress=None):
    x=matrices(data);p={};m={}
    for name in MODELS:
        p[name],m[name]=nested(x[name],data['labels'],data['block_ids'])
        if progress is not None:progress(name)
    return p,m


def fold_all(data,outer=0):
    x=matrices(data);p={};m={}
    for name in MODELS:p[name],m[name]=outer_fold(x[name],data['labels'],data['block_ids'],outer)
    return p,m


def fixture(blocks=32):
    rng=np.random.default_rng(15220260920)
    start=rng.normal(size=(blocks,4,4,7));e=rng.normal(size=(blocks,4,4,3,6));t=rng.normal(size=e.shape)
    slopes=np.array([.23,-.17,.32,-.12]);y=np.clip(start[...,0]*slopes+.09*e[...,0,0]+
        rng.normal(scale=.075,size=(blocks,4,4)),-1,1)
    return dict(start=start,endpoint=e,targeted=t,labels=y,block_ids=np.arange(blocks,dtype=np.int64),
        futures=np.clip(y[-16:,...,None]+rng.normal(scale=.08,size=(min(blocks,16),4,4,4)),-1,1))


def detail(p,y):
    return [ridge.errors(p[:,:,g:g+1],y[:,:,g:g+1]) for g in range(4)]


def architecture_comparisons(new,old,data):
    y,f=data['labels'],data['futures'];rows=[]
    for name in MODELS:
        a=(new[name]-y)**2;b=(old[name]-y)**2
        af=(new[name][16:,...,None]-f)**2;bf=(old[name][16:,...,None]-f)**2
        am=(new[name][16:]-f.mean(axis=-1))**2;bm=(old[name][16:]-f.mean(axis=-1))**2
        future=ridge.paired(af.mean(axis=-1),bf.mean(axis=-1));mean=ridge.paired(am,bm)
        np.testing.assert_allclose(future['block_differences'],mean['block_differences'],atol=1e-14,rtol=0)
        rows.append(dict(model=name,candidate='group_sensitive',reference='shared',original=ridge.paired(a,b),
            groups=[ridge.paired(a[:,:,g:g+1],b[:,:,g:g+1]) for g in range(4)],
            cohorts={key:ridge.paired(a[l:r],b[l:r]) for key,l,r in (('d135',0,8),('d140',8,16),('former_test',16,32))},
            individual_futures=future,mean_target=mean))
    return rows


def summarize(p,fits,old,old_fits,data):
    architectures={}
    for label,guesses,records in (('shared',old,old_fits),('group_sensitive',p,fits)):
        source=observers.summarize(guesses,records,data)
        architectures[label]={k:source[k] for k in SCORE_KEYS}
        architectures[label]['group_details']={k:detail(guesses[k],data['labels']) for k in MODELS}
    return dict(schema='d152_group_sensitive_prediction_development_v1',stage='POST_RESULT_DEVELOPMENT',
        prospective_evidence=False,blocks=32,cases=512,all_cases_retained=True,new_diagnostic_cycles=0,
        new_actual_lineages=0,new_founders=0,architectures=architectures,
        architecture_comparisons=architecture_comparisons(p,old,data),
        primary_development_comparison=architectures['group_sensitive']['central_comparison'],
        feature_dimensions=[7,19,19,19,19,19],penalized_dimensions=[28,76,76,76,76,76],
        common_deviation_penalty_ratio=1,model_class=CLASS,observer_cycles=2,
        baseline_predictions_reused=True,former_test_is_now_development=True,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,model_selected_for_deployment=False,automatic_successor=False,
        mean_sham_is_loss_average_not_prediction_ensemble=True,
        interpretation='One pre-specified model-class comparison on observed founders; not prospective validation.')


def case_errors(p,baseline,data):
    result={}
    for label,values in (('shared',baseline),('group_sensitive',p)):
        for name in MODELS:
            e=values[name]-data['labels'];prefix=label+'_'+name
            result[prefix+'_signed']=e;result[prefix+'_absolute']=abs(e);result[prefix+'_squared']=e*e
    return result
