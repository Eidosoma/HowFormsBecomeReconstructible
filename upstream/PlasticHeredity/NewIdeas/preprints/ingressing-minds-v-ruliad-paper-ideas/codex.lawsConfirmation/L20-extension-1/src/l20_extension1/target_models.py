"""D157 fixed training-target comparison; no tissue dynamics or model selection."""
import numpy as np
from . import mean_models as old,group_models as ridge

ALPHAS=(.001,.01,.1)
TARGETS=('original','future0','future1','future2','future3','future_mean')
EDITED=('passive','shuffle','attenuate','sham_plus','sham_minus')
OBSERVERS=('starting','one_copy')+tuple('separate:'+k for k in EDITED)+tuple('mean:'+k for k in EDITED)
LOSS_OBSERVERS=OBSERVERS+('separate:mean_sham_loss','mean:mean_sham_loss')
GROUPS=('A_ordinary','A_aligned','B_ordinary','B_aligned')


def validate(data):
    n=len(data['block_ids']);ids=data['block_ids']
    if n<4 or ids.shape!=(n,) or ids.dtype!=np.int64 or len(set(ids.tolist()))!=n:raise ValueError('whole-founder identities')
    shapes=dict(start=(n,4,4,7),endpoint=(n,4,4,3,6),targeted=(n,4,4,3,6),labels=(n,4,4),futures=(n,4,4,4))
    for k,shape in shapes.items():
        if data[k].shape!=shape or data[k].dtype!=np.float64 or not np.isfinite(data[k]).all():raise ValueError('complete finite '+k)
    if max(np.max(abs(data[k])) for k in ('labels','futures'))>1:raise ValueError('bounded outcomes')


def features(data):
    validate(data);separate=ridge.matrices(data);mean=old.features(data)
    return dict(starting=data['start'].copy(),one_copy=old.prior.features(data),
        **{'separate:'+k:separate[k] for k in EDITED},**{'mean:'+k:mean[k] for k in EDITED})


def targets(data):
    validate(data)
    return np.stack([data['labels']]+[data['futures'][...,j] for j in range(4)]+[data['futures'].mean(axis=-1)])


def raw_predict(m,x,g):
    mu,scale,offset,beta=(np.asarray(m[k]) for k in ('means','scale','offsets','coefficients'))
    return offset[g]+ridge.design((x-mu[g])/scale,g)@beta.ravel()


def outer(x,ys,ids,b):
    n=len(ids)
    if ys.shape!=(6,n,4,4) or not 0<=b<n:raise ValueError('six targets and one held-out founder')
    X,_,g,rows=ridge.panel(x,ys[0],ids);train=rows!=b;test=~train;guesses=[];raw=[];records=[]
    for y in ys:
        models=[ridge.fit(X[train],y.ravel()[train],g[train],a) for a in ALPHAS]
        r=np.stack([raw_predict(m,X[test],g[test]).reshape(4,4) for m in models])
        guesses.append(np.clip(r,-1,1));raw.append(r);records.append(models)
    return np.stack(guesses),np.stack(raw),dict(validation_block=int(ids[b]),
        training_blocks=np.delete(ids,b).tolist(),models=records)


def fit_all(data,progress=None):
    x=features(data);ys=targets(data);ids=data['block_ids'];p={};raw={};fits={}
    for name in OBSERVERS:
        rows=[outer(x[name],ys,ids,b) for b in range(len(ids))]
        p[name]=np.stack([r[0] for r in rows],axis=2);raw[name]=np.stack([r[1] for r in rows],axis=2)
        fits[name]=dict(blocks=ids.tolist(),alphas=list(ALPHAS),training_targets=list(TARGETS),
            folds=[r[2] for r in rows],model_class=ridge.CLASS,observer=name,
            preprocessing='training-only within each whole-founder fold',inner_selection=False,prospective_evidence=False)
        if progress is not None:progress(name)
    return p,raw,fits


def canonical(k):return k if k in ('starting','one_copy') else 'separate:'+k


def observer_pairs():
    return [(canonical(c),canonical(r)) for c,r in old.prior.prior.PAIRS]+[
        (canonical(c),canonical(r)) for c,r in old.prior.PAIRS]+old.specs()


def specs():
    result=[dict(kind='observer',candidate_target=t,candidate=c,reference_target=t,reference=r)
        for t in TARGETS for c,r in observer_pairs()]
    for name in LOSS_OBSERVERS:
        result.extend(dict(kind='target',candidate_target='future_mean',candidate=name,reference_target=t,reference=name)
            for t in (*TARGETS[:-1],'single_mean_loss'))
        result.append(dict(kind='target',candidate_target='single_mean_loss',candidate=name,reference_target='original',reference=name))
    return result


def error_stats(error):
    loss=error*error;bias=float(error.mean())
    return dict(mse=float(loss.mean()),mae_points=float(abs(error).mean()*100),rmse_points=float(np.sqrt(loss.mean())*100),
        bias_points=bias*100,group_mse=loss.mean(axis=(0,1)+tuple(range(3,error.ndim))).tolist(),
        block_mse=loss.mean(axis=tuple(range(1,error.ndim))).tolist())


def paired(c,r):
    delta=(r-c).mean(axis=(1,2));groups=(r-c).mean(axis=(0,1));gain=float(delta.mean());base=float(r.mean())
    return dict(mse_reduction=gain,candidate_mse=float(c.mean()),reference_mse=base,
        relative_reduction_percent=100*gain/base if base else None,block_differences=delta.tolist(),
        group_differences=groups.tolist(),positive_blocks=int((delta>0).sum()),negative_blocks=int((delta<0).sum()),
        zero_blocks=int((delta==0).sum()),leave_one_score_block_out=((delta.sum()-delta)/(len(delta)-1)).tolist())


def comparison(c,r):
    co,cf,cm=c;ro,rf,rm=r
    return dict(original=paired(co,ro),individual_futures=paired(cf.mean(axis=-1),rf.mean(axis=-1)),
        mean_target=paired(cm,rm),by_repeat=[paired(cf[...,k],rf[...,k]) for k in range(4)],
        leave_one_repeat_out=[paired(np.delete(cf,k,axis=-1).mean(axis=-1),np.delete(rf,k,axis=-1).mean(axis=-1)) for k in range(4)])


def losses(p,data,i):
    y=data['labels'];f=data['futures'];mu=f.mean(axis=-1);out={}
    for j,t in enumerate(TARGETS):
        for k in OBSERVERS:
            q=p[k][j,i];out[t+'/'+k]=((q-y)**2,(q[...,None]-f)**2,(q-mu)**2)
        for prefix in ('separate:','mean:'):
            plus,minus=(out[t+'/'+prefix+k] for k in ('sham_plus','sham_minus'))
            out[t+'/'+prefix+'mean_sham_loss']=tuple((a+b)/2 for a,b in zip(plus,minus))
    for name in LOSS_OBSERVERS:
        out['single_mean_loss/'+name]=tuple(np.stack([out[t+'/'+name][j] for t in TARGETS[1:5]]).mean(axis=0) for j in range(3))
    return out


def metadata(n):
    return dict(schema='d157_target_averaging_development_v1',posthoc=True,prospective_evidence=False,
        blocks=n,cases=16*n,training_blocks_per_fold=n-1,all_cases_retained=True,training_targets=list(TARGETS),
        observers=list(OBSERVERS),alphas=list(ALPHAS),groups=list(GROUPS),new_fits=216*n,new_predictions=3456*n,
        feature_dimensions=[7,13]+[19]*5+[13]*5,model_class=ridge.CLASS,common_deviation_penalty_ratio=1,
        inner_selection=False,observer_contrasts=990,target_contrasts=294,total_contrasts=1284,
        repeated_outcomes_used_for_training=True,held_out_outcomes_used_for_training=False,
        mean_training_label_budget=4,single_training_label_budget=1,diagnostic_budgets_unchanged=True,
        equal_dimension_is_not_equal_complexity=True,mean_sham_is_loss_not_ensemble=True,
        single_mean_is_loss_not_ensemble=True,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,
        confidence_intervals=False,model_selected_for_deployment=False,former_test_is_development=True,
        no_best_alpha_or_repeat_selected=True,old_reference_fits_recomputed=False,automatic_successor=False)


def summarize(p,raw,data):
    validate(data);n=len(data['block_ids']);scores={};y=data['labels'];f=data['futures'];mu=f.mean(axis=-1)
    for i,a in enumerate(ALPHAS):
        models={};loss=losses(p,data,i)
        for j,t in enumerate(TARGETS):
            for k in OBSERVERS:
                q=p[k][j,i];e=q[...,None]-f
                models[t+'/'+k]=dict(original=error_stats(q-y),individual_futures=error_stats(e),
                    mean_target=error_stats(q-mu),by_repeat=[error_stats(e[...,r]) for r in range(4)],
                    clipped_cases=int(np.count_nonzero(abs(raw[k][j,i])>1)))
        comparisons=[dict(**s,**comparison(loss[s['candidate_target']+'/'+s['candidate']],
                                          loss[s['reference_target']+'/'+s['reference']])) for s in specs()]
        linearity={k:dict(max_abs_unclipped_mean_residual=float(np.max(abs(raw[k][5,i]-raw[k][1:5,i].mean(axis=0)))),
            mean_fit_clipped_cases=int(np.count_nonzero(abs(raw[k][5,i])>1)),
            single_fit_clipped_cases=int(np.count_nonzero(abs(raw[k][1:5,i])>1)),
            max_abs_clipped_average_difference=float(np.max(abs(p[k][5,i]-p[k][1:5,i].mean(axis=0))))) for k in OBSERVERS}
        scores[str(a)]=dict(models=models,comparisons=comparisons,averaging_identity=linearity)
    return dict(**metadata(n),scores=scores,within_future_variance=float(f.var(axis=-1).mean()))


def case_errors(p,data):
    arrays={}
    for k in OBSERVERS:
        for scope,error in (('original',p[k]-data['labels']),('futures',p[k][...,None]-data['futures']),
                            ('mean',p[k]-data['futures'].mean(axis=-1))):
            for suffix,v in (('signed',error),('absolute',abs(error)),('squared',error**2)):
                arrays[k+'__'+scope+'__'+suffix]=v
    return arrays


def fixture(n=16):
    data=ridge.fixture(n);data['block_ids']=np.arange(90000,90000+n,dtype=np.int64)
    if data['futures'].shape!=(n,4,4,4):raise ValueError('synthetic block count at most16')
    return data
