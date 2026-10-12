"""D160: zero raw reading-difference slopes under the original ridge objective."""
import numpy as np
from . import influence_models as prior, group_models as ridge

ALPHAS=prior.ALPHAS
EDITED=prior.old.EDITED
NEW=tuple('tied:'+k for k in EDITED)
OBSERVERS=prior.OBSERVERS+NEW
NEW_LOSS=NEW+('tied:mean_sham_loss',)
CLASS='raw_reading_difference_zero_original_ridge_penalty'
PAIRS=tuple(
    [(k,r) for k in NEW for r in ('separate:'+k.split(':')[1],'mean:'+k.split(':')[1],'starting','one_copy')]
    +[(k,'tied:passive') for k in NEW[1:]+('tied:mean_sham_loss',)]
    +[('tied:attenuate',r) for r in ('tied:shuffle','tied:sham_plus','tied:sham_minus','tied:mean_sham_loss')]
    +[('tied:mean_sham_loss',r) for r in ('starting','one_copy','separate:mean_sham_loss','mean:mean_sham_loss')])
SCOPES=prior.SCOPES


def embedding(scale):
    s=np.asarray(scale,dtype=float)
    if s.shape!=(19,) or not np.isfinite(s).all() or np.min(s)<=0:raise ValueError('nineteen positive scales')
    h=np.hypot(s[7:13],s[13:]);t=np.zeros((19,13))
    t[:7,:7]=np.eye(7)
    for j in range(6):t[7+j,7+j]=s[7+j]/h[j];t[13+j,7+j]=s[13+j]/h[j]
    return t


def fit(x,y,g,alpha):
    if x.shape[1]!=19 or alpha not in ALPHAS:raise ValueError('frozen features/alpha')
    mu,offset,scale,z,target=ridge.ridge.prepare(x,y,g)
    t=embedding(scale);a=ridge.design(z@t,g)
    eta=np.linalg.solve(a.T@a/len(y)+alpha*np.eye(52),a.T@target/len(y)).reshape(4,13)
    beta=eta@t.T
    return dict(alpha=alpha,means=mu.tolist(),offsets=offset.tolist(),scale=scale.tolist(),
        coefficients=beta.tolist(),reduced_coefficients=eta.tolist(),model_class=CLASS)


def coordinates(x,g,model):
    mu,s,beta=(np.asarray(model[k]) for k in ('means','scale','coefficients'))
    z=x-mu[g];w=beta/s
    md=np.concatenate([z[:,:7],(z[:,7:13]+z[:,13:])/2,(z[:,13:]-z[:,7:13])/2],axis=1)
    gamma=np.concatenate([w[:,:7],w[:,7:13]+w[:,13:],w[:,13:]-w[:,7:13]],axis=1)
    restored=np.concatenate([gamma[:,:7]*s[:7],.5*(gamma[:,7:13]-gamma[:,13:])*s[7:13],
        .5*(gamma[:,7:13]+gamma[:,13:])*s[13:]],axis=1)
    return md,gamma,restored


def geometry(source,constrained,x,y,g,test,h,source_raw):
    alpha=source['alpha'];assert alpha==constrained['alpha']
    mu,offset,s,z,target=ridge.ridge.prepare(x,y,g)
    for k,v in (('means',mu),('offsets',offset),('scale',s)):
        np.testing.assert_allclose(source[k],v,atol=2e-10,rtol=0)
        np.testing.assert_array_equal(constrained[k],v)
    a=ridge.design(z,g);beta=np.asarray(source['coefficients'])
    md,gamma,restored=coordinates(x,g,source);td,tg,_=coordinates(test,h,source)
    raw=offset[h]+ridge.design(td,h)@tg.ravel()
    np.testing.assert_allclose(raw,source_raw,atol=2e-10,rtol=0)
    np.testing.assert_allclose(ridge.design(md,g)@gamma.ravel(),a@beta.ravel(),atol=2e-10,rtol=0)
    np.testing.assert_allclose(restored,beta,atol=2e-10,rtol=0)
    penalty=float((restored*restored).sum());reference_penalty=float((beta*beta).sum())
    stationarity=a.T@(a@beta.ravel()-target)/len(y)+alpha*beta.ravel()
    np.testing.assert_allclose(stationarity,0,atol=2e-10,rtol=0)
    t=embedding(s);eta=np.asarray(constrained['reduced_coefficients']);limited=np.asarray(constrained['coefficients'])
    np.testing.assert_allclose(t.T@t,np.eye(13),atol=2e-14,rtol=0)
    np.testing.assert_allclose(limited,eta@t.T,atol=2e-14,rtol=0)
    _,lg,_=coordinates(x,g,constrained);restriction=float(np.max(abs(lg[:,13:])))
    np.testing.assert_allclose(lg[:,13:],0,atol=2e-10,rtol=0)
    reduced=ridge.design(z@t,g)
    residual=reduced.T@(reduced@eta.ravel()-target)/len(y)+alpha*eta.ravel()
    np.testing.assert_allclose(residual,0,atol=2e-10,rtol=0)
    obj=lambda b:float(np.mean((a@b.ravel()-target)**2)+alpha*np.sum(b*b))
    original=obj(beta);restricted=obj(limited);assert restricted>=original-2e-10
    return dict(full_objective=original,restricted_objective=restricted,objective_increase=restricted-original,
        full_stationarity=float(np.max(abs(stationarity))),restricted_stationarity=float(np.max(abs(residual))),
        max_abs_reexpression=float(np.max(abs(raw-source_raw))),penalty_identity_residual=abs(penalty-reference_penalty),
        max_abs_raw_difference_slope=restriction)


def fold(x,y,ids,b,source_models,source_raw,d=None):
    X,Y,g,rows=ridge.panel(x,y,ids)
    if not 0<=b<len(ids) or d is not None and (not 0<=d<len(ids) or d==b):raise ValueError('distinct whole-founder exclusions')
    train=(rows!=b)&(rows!=d);test=rows==b
    records=[fit(X[train],Y[train],g[train],a) for a in ALPHAS]
    raw=np.stack([prior.old.raw_predict(m,X[test],g[test]).reshape(4,4) for m in records])
    geo=[geometry(s,m,X[train],Y[train],g[train],X[test],g[test],source_raw[i].ravel())
        for i,(s,m) in enumerate(zip(source_models,records))]
    return np.clip(raw,-1,1),raw,dict(validation_block=int(ids[b]),
        training_blocks=[int(ids[v]) for v in range(len(ids)) if v!=b and v!=d],models=records,geometry=geo)


def fit_all(data,b,br,p,raw,bfits,rfits,progress=None):
    prior.validate(data);ids=data['block_ids'];n=len(ids);x=prior.old.features(data);y=data['futures'].mean(-1)
    base={};base_raw={};deleted={};deleted_raw={};fits={}
    for name in NEW:
        source='separate:'+name.split(':')[1]
        rows=[fold(x[source],y,ids,v,bfits[source]['folds'][v]['models'][5],br[source][:,v]) for v in range(n)]
        base[name]=np.stack([r[0] for r in rows],axis=1);base_raw[name]=np.stack([r[1] for r in rows],axis=1)
        deletions=[];ps=[];rs=[]
        for d in range(n):
            keep=[v for v in range(n) if v!=d]
            cases=[fold(x[source],y,ids,v,rfits[source]['deletions'][d]['folds'][j]['models'],raw[source][d,:,j],d)
                for j,v in enumerate(keep)]
            ps.append(np.stack([r[0] for r in cases],axis=1));rs.append(np.stack([r[1] for r in cases],axis=1))
            deletions.append(dict(deleted_block=int(ids[d]),remaining_blocks=ids[keep].tolist(),folds=[r[2] for r in cases]))
        deleted[name]=np.stack(ps);deleted_raw[name]=np.stack(rs)
        fits[name]=dict(observer=name,blocks=ids.tolist(),alphas=list(ALPHAS),target='future_mean',
            model_class=CLASS,full_training_blocks=n-1,deletion_training_blocks=n-2,
            restriction='zero raw half-difference slope in every public group',
            preprocessing='original nineteen-feature training-only group means and residual scales',
            reference_fits_recomputed=False,inner_selection=False,folds=[r[2] for r in rows],deletions=deletions)
        if progress is not None:progress(name)
    return base,base_raw,deleted,deleted_raw,fits


def fixture(n=16):
    data=prior.fixture(n);ids=data['block_ids'];x=prior.old.features(data);y=data['futures'].mean(-1)
    b={};br={};bf={}
    for k in prior.OBSERVERS:
        rows=[prior.fold(x[k],y,ids,v) for v in range(n)]
        b[k]=np.stack([r[0] for r in rows],axis=1);br[k]=np.stack([r[1] for r in rows],axis=1)
        bf[k]=dict(blocks=ids.tolist(),alphas=list(ALPHAS),training_targets=list(prior.old.TARGETS),
            model_class=ridge.CLASS,observer=k,preprocessing='training-only within each whole-founder fold',
            inner_selection=False,prospective_evidence=False,
            folds=[dict(validation_block=r[2]['validation_block'],training_blocks=r[2]['training_blocks'],
                models=[r[2]['models']]*6) for r in rows])
    p,raw,rf=prior.fit_all(data)
    return data,b,br,p,raw,bf,rf


def losses(p,data,a):
    y=data['labels'];f=data['futures'];mu=f.mean(-1)
    out={k:((p[k][a]-y)**2,(p[k][a,...,None]-f)**2,(p[k][a]-mu)**2) for k in OBSERVERS}
    for prefix in ('separate:','mean:','tied:'):
        plus,minus=(out[prefix+s] for s in ('sham_plus','sham_minus'))
        out[prefix+'mean_sham_loss']=tuple((u+v)/2 for u,v in zip(plus,minus))
    return out


def panel(p,raw,data,a):
    y=data['labels'];f=data['futures'];models={}
    for k in OBSERVERS:
        q=p[k][a]
        models[k]=dict(original=prior.old.error_stats(q-y),individual_futures=prior.old.error_stats(q[...,None]-f),
            mean_target=prior.old.error_stats(q-f.mean(-1)),by_repeat=[prior.old.error_stats(q-f[...,j]) for j in range(4)],
            clipped_cases=int(np.count_nonzero(abs(raw[k][a])>1)))
    loss=losses(p,data,a)
    return dict(blocks=data['block_ids'].tolist(),models=models,
        comparisons=[dict(candidate=c,reference=r,**prior.old.comparison(loss[c],loss[r])) for c,r in PAIRS])


def metadata(n):
    return dict(schema='d160_difference_ablation_development_v1',blocks=n,cases=16*n,observers=list(OBSERVERS),
        new_observers=list(NEW),alphas=list(ALPHAS),groups=list(prior.old.GROUPS),target='future_mean',
        new_fits=15*n*n,new_predictions=240*n*n,reference_forecasts_reused=576*n*n,
        untouched_model_geometry_checks=15*n*n,full_panels=1,deletion_panels=n,
        observer_orientations=99,observer_comparison_records=99*(1+2*n),training_effect_records=18*n,
        reference_observer_comparison_records=165*(1+2*n),reference_training_effect_records=42*n,
        free_coefficients=52,reference_coefficients=76,all_cases_retained=True,all_settings_retained=True,
        all_deletions_retained=True,all_repeats_retained=True,reference_fits_recomputed=False,
        penalty_geometry_matched=True,new_dynamics=0,new_diagnostic_cycles=0,new_founders=0,
        inner_selection=False,model_selected_for_deployment=False,confidence_intervals=False,
        mean_sham_is_loss_not_ensemble=True,posthoc=True,prospective_evidence=False,automatic_successor=False)


def summarize(b,br,p,raw,nb,nbr,npred,nraw,data):
    full={**b,**nb};fullraw={**br,**nbr};deleted={**p,**npred};deletedraw={**raw,**nraw}
    n=len(data['block_ids']);scores={}
    for a,alpha in enumerate(ALPHAS):
        allpanel=panel(full,fullraw,data,a);deletions=[]
        for d in range(n):
            reduced=prior.subset(data,d)
            q={k:deleted[k][d] for k in OBSERVERS};qr={k:deletedraw[k][d] for k in OBSERVERS}
            s={k:np.delete(full[k],d,axis=1) for k in OBSERVERS};sr={k:np.delete(fullraw[k],d,axis=1) for k in OBSERVERS}
            newloss=losses(q,reduced,a);refloss=losses(s,reduced,a)
            deletions.append(dict(deleted_block=int(data['block_ids'][d]),refitted=panel(q,qr,reduced,a),
                score_only=panel(s,sr,reduced,a),training_effect=[dict(observer=k,**prior.old.comparison(newloss[k],refloss[k])) for k in NEW_LOSS]))
        scores[str(alpha)]=dict(full=allpanel,deletions=deletions)
    return dict(**metadata(n),scores=scores,within_future_variance=float(data['futures'].var(axis=-1).mean()))


def case_errors(nb,npred,b,p,data):
    out={};n=len(data['block_ids'])
    yy=np.stack([np.delete(data['labels'],d,axis=0) for d in range(n)])[:,None]
    ff=np.stack([np.delete(data['futures'],d,axis=0) for d in range(n)])[:,None]
    for scope,pred,ref,y,f in (('full',nb,b,data['labels'],data['futures']),('deletion',npred,p,yy,ff)):
        for name in NEW:
            for outcome,e in (('original',pred[name]-y),('futures',pred[name][...,None]-f),
                ('mean',pred[name]-f.mean(-1)),('change_from_separate',pred[name]-ref['separate:'+name.split(':')[1]])):
                for suffix,v in (('signed',e),('absolute',abs(e)),('squared',e*e)):
                    out[scope+'__'+name+'__'+outcome+'__'+suffix]=v
    return out
