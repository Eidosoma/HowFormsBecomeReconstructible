"""D158: fixed mean-target founder-deletion refits and score/training accounting."""
import numpy as np
from . import target_models as old, group_models as ridge

ALPHAS=old.ALPHAS
OBSERVERS=old.OBSERVERS
LOSS_OBSERVERS=old.LOSS_OBSERVERS
PAIRS=tuple(old.observer_pairs())
SCOPES=('original','individual_futures','mean_target')+tuple('repeat'+str(i) for i in range(4))+tuple('omit_repeat'+str(i) for i in range(4))


def validate(data):
    old.validate(data)
    if len(data['block_ids'])<5:raise ValueError('at least five whole founders')


def subset(data,d):
    validate(data)
    if not 0<=d<len(data['block_ids']):raise ValueError('deletion index')
    return {k:np.delete(v,d,axis=0) for k,v in data.items() if k in ('start','endpoint','targeted','labels','futures','block_ids')}


def fold(x,y,ids,b,d=None):
    X,Y,g,rows=ridge.panel(x,y,ids)
    if not 0<=b<len(ids) or (d is not None and (not 0<=d<len(ids) or d==b)):raise ValueError('distinct exclusions')
    keep=rows!=b
    if d is not None:keep &= rows!=d
    test=rows==b
    records=[ridge.fit(X[keep],Y[keep],g[keep],a) for a in ALPHAS]
    raw=np.stack([old.raw_predict(m,X[test],g[test]).reshape(4,4) for m in records])
    training=[int(ids[j]) for j in range(len(ids)) if j!=b and j!=d]
    return np.clip(raw,-1,1),raw,dict(validation_block=int(ids[b]),training_blocks=training,models=records)


def fit_all(data,progress=None):
    validate(data);ids=data['block_ids'];n=len(ids);x=old.features(data);y=data['futures'].mean(axis=-1)
    p={};raw={};fits={}
    for name in OBSERVERS:
        panels=[];raws=[];deletions=[]
        for d in range(n):
            keep=[b for b in range(n) if b!=d];rows=[fold(x[name],y,ids,b,d) for b in keep]
            panels.append(np.stack([r[0] for r in rows],axis=1))
            raws.append(np.stack([r[1] for r in rows],axis=1))
            deletions.append(dict(deleted_block=int(ids[d]),remaining_blocks=ids[keep].tolist(),folds=[r[2] for r in rows]))
        p[name]=np.stack(panels);raw[name]=np.stack(raws)
        fits[name]=dict(blocks=ids.tolist(),alphas=list(ALPHAS),target='future_mean',observer=name,
            model_class=ridge.CLASS,training_blocks_per_fold=n-2,inner_selection=False,
            preprocessing='training-only; deletion and validation founder excluded',deletions=deletions)
        if progress is not None:progress(name)
    return p,raw,fits


def fixture(n=16):return old.fixture(n)


def fixture_baseline(data):
    # Only synthetic qualification/benchmark uses this helper. Actual baselines are loaded exactly.
    validate(data);x=old.features(data);ids=data['block_ids'];y=data['futures'].mean(axis=-1);p={};raw={}
    for name in OBSERVERS:
        rows=[fold(x[name],y,ids,b) for b in range(len(ids))]
        p[name]=np.stack([r[0] for r in rows],axis=1);raw[name]=np.stack([r[1] for r in rows],axis=1)
    return p,raw


def losses(p,data,i):
    y=data['labels'];f=data['futures'];mu=f.mean(axis=-1)
    out={k:((p[k][i]-y)**2,(p[k][i,...,None]-f)**2,(p[k][i]-mu)**2) for k in OBSERVERS}
    for prefix in ('separate:','mean:'):
        a,b=(out[prefix+k] for k in ('sham_plus','sham_minus'))
        out[prefix+'mean_sham_loss']=tuple((v+w)/2 for v,w in zip(a,b))
    return out


def panel(p,raw,data,i):
    y=data['labels'];f=data['futures'];mu=f.mean(axis=-1);errors={}
    for k in OBSERVERS:
        q=p[k][i];e=q[...,None]-f
        errors[k]=dict(original=old.error_stats(q-y),individual_futures=old.error_stats(e),
            mean_target=old.error_stats(q-mu),by_repeat=[old.error_stats(e[...,r]) for r in range(4)],
            clipped_cases=int(np.count_nonzero(abs(raw[k][i])>1)))
    loss=losses(p,data,i)
    return dict(blocks=data['block_ids'].tolist(),models=errors,
        comparisons=[dict(candidate=c,reference=r,**old.comparison(loss[c],loss[r])) for c,r in PAIRS])


def scopes(comparison):
    return {**{k:comparison[k] for k in SCOPES[:3]},
        **{'repeat'+str(j):v for j,v in enumerate(comparison['by_repeat'])},
        **{'omit_repeat'+str(j):v for j,v in enumerate(comparison['leave_one_repeat_out'])}}


def influence(full,score,refit,ids):
    s=np.array(score);r=np.array(refit);d=ids.tolist()
    return dict(full_gain=full,score_only_gains=score,refitted_gains=refit,
        score_composition_change=(s-full).tolist(),training_change=(r-s).tolist(),total_change=(r-full).tolist(),
        positive_score_only=int((s>0).sum()),positive_refitted=int((r>0).sum()),
        negative_refitted=int((r<0).sum()),zero_refitted=int((r==0).sum()),
        min_refitted=float(r.min()),max_refitted=float(r.max()),
        score_sign_reversals=[d[j] for j in range(len(d)) if s[j]*full<0],
        refit_sign_reversals=[d[j] for j in range(len(d)) if r[j]*full<0])


def forecast_change(a,b):
    e=a-b
    return dict(bias_points=float(100*e.mean()),mae_points=float(100*abs(e).mean()),
        rms_points=float(100*np.sqrt((e*e).mean())),max_abs_points=float(100*abs(e).max()),
        group_rms_points=(100*np.sqrt((e*e).mean(axis=(0,1)))).tolist())


def metadata(n):
    return dict(schema='d158_training_influence_development_v1',posthoc=True,prospective_evidence=False,
        blocks=n,cases=16*n,deletion_panels=n,training_blocks_per_fold=n-2,target='future_mean',
        observers=list(OBSERVERS),alphas=list(ALPHAS),groups=list(old.GROUPS),
        new_fits=36*n*(n-1),new_predictions=576*n*(n-1),reference_predictions_reused=576*n,
        observer_orientations=165,observer_comparison_records=165*(1+2*n),training_effect_records=42*n,
        decomposition_records=165,feature_dimensions=[7,13]+[19]*5+[13]*5,
        all_deletions_retained=True,all_repeats_retained=True,full_cohort_reference_retained=True,
        excluded_founder_in_training=False,validation_founder_in_training=False,mean_sham_is_loss_not_ensemble=True,
        no_best_setting_or_deletion_selected=True,old_reference_fits_recomputed=False,
        new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,confidence_intervals=False,
        independent_deletion_replications=False,inner_selection=False,automatic_successor=False)


def summarize(p,raw,baseline,base_raw,data):
    validate(data);n=len(data['block_ids']);scores={}
    for i,a in enumerate(ALPHAS):
        full=panel(baseline,base_raw,data,i);deletions=[]
        for d in range(n):
            reduced=subset(data,d);q={k:p[k][d] for k in OBSERVERS};qr={k:raw[k][d] for k in OBSERVERS}
            b={k:np.delete(baseline[k],d,axis=1) for k in OBSERVERS}
            br={k:np.delete(base_raw[k],d,axis=1) for k in OBSERVERS}
            new=losses(q,reduced,i);ref=losses(b,reduced,i)
            deletions.append(dict(deleted_block=int(data['block_ids'][d]),
                refitted=panel(q,qr,reduced,i),score_only=panel(b,br,reduced,i),
                training_effect=[dict(observer=k,**old.comparison(new[k],ref[k])) for k in LOSS_OBSERVERS],
                forecast_change={k:forecast_change(q[k][i],b[k][i]) for k in OBSERVERS}))
        decomposition=[]
        for j,(c,r) in enumerate(PAIRS):
            allscopes={}
            for scope,metric in scopes(full['comparisons'][j]).items():
                s=[scopes(v['score_only']['comparisons'][j])[scope]['mse_reduction'] for v in deletions]
                f=[scopes(v['refitted']['comparisons'][j])[scope]['mse_reduction'] for v in deletions]
                allscopes[scope]=influence(metric['mse_reduction'],s,f,data['block_ids'])
            decomposition.append(dict(candidate=c,reference=r,scopes=allscopes))
        scores[str(a)]=dict(full=full,deletions=deletions,decomposition=decomposition)
    return dict(**metadata(n),scores=scores,within_future_variance=float(data['futures'].var(axis=-1).mean()))


def case_errors(p,baseline,data):
    out={};n=len(data['block_ids'])
    deleted_y=np.stack([np.delete(data['labels'],d,axis=0) for d in range(n)])[:,None]
    deleted_f=np.stack([np.delete(data['futures'],d,axis=0) for d in range(n)])[:,None]
    for prefix,values,y,f in (('baseline',baseline,data['labels'],data['futures']),('refit',p,deleted_y,deleted_f)):
        for k in OBSERVERS:
            for scope,e in (('original',values[k]-y),('futures',values[k][...,None]-f),('mean',values[k]-f.mean(axis=-1))):
                for suffix,v in (('signed',e),('absolute',abs(e)),('squared',e*e)):
                    out[prefix+'__'+k+'__'+scope+'__'+suffix]=v
    for k in OBSERVERS:
        e=p[k]-np.stack([np.delete(baseline[k],d,axis=1) for d in range(n)])
        for suffix,v in (('signed',e),('absolute',abs(e)),('squared',e*e)):
            out['forecast_change__'+k+'__'+suffix]=v
    return out
