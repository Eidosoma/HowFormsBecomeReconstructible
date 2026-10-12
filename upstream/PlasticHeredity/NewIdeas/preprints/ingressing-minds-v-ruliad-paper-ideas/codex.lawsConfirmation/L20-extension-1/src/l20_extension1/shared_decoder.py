"""D164 condition-blind ridge calibration; no filesystem or tissue dynamics."""
import numpy as np
from . import asymmetry as a, group_models as group, difference_ablation as tied

CALIBRATION=('passive','sham_plus','sham_minus')
CLASS='condition_blind_equal_three_view_ridge_v1'


def validate_training(features,futures,ids):
    x=a.feature_matrices(features);n=len(ids)
    if n<3 or ids.shape!=(n,) or ids.dtype!=np.int64 or len(set(ids))!=n or len(features['start'])!=n:
        raise ValueError('complete unique training founders')
    if futures.shape!=(n,4,4,4) or futures.dtype!=np.float64 or not np.isfinite(futures).all() or np.max(abs(futures))>1:
        raise ValueError('complete bounded training futures')
    return x


def pooled(x,y,encoding,keep):
    if encoding not in a.ENCODINGS:raise ValueError('frozen encoding')
    keep=np.asarray(keep)
    if keep.ndim!=1 or len(keep)<2 or keep.dtype!=np.int64 or len(set(keep))!=len(keep) or np.min(keep)<0 or np.max(keep)>=len(y):
        raise ValueError('distinct training indices')
    X=np.concatenate([x[encoding+':'+k][keep].reshape(16*len(keep),-1) for k in CALIBRATION])
    Y=np.tile(y[keep].ravel(),3);g=np.tile(np.arange(4,dtype=np.int64),12*len(keep))
    return X,Y,g


def path(X,Y,g,encoding):
    mu,offset,scale,z,target=group.ridge.prepare(X,Y,g)
    expected=13 if encoding=='mean' else 19
    if encoding not in a.ENCODINGS or X.shape[1]!=expected:raise ValueError('encoding columns')
    transform=tied.embedding(scale) if encoding=='tied' else np.eye(expected)
    design=group.design(z@transform,g);gram=design.T@design/len(Y);cross=design.T@target/len(Y)
    records=[]
    for alpha in a.ALPHAS:
        eta=np.linalg.solve(gram+alpha*np.eye(gram.shape[0]),cross).reshape(4,-1)
        beta=eta@transform.T
        records.append(dict(alpha=alpha,encoding=encoding,model_class=CLASS,calibration=list(CALIBRATION),
            means=mu.tolist(),offsets=offset.tolist(),scale=scale.tolist(),coefficients=beta.tolist(),
            reduced_coefficients=eta.tolist(),training_rows=len(Y),unique_training_cases=len(Y)//3))
    return records


def train(features,futures,ids):
    x=validate_training(features,futures,ids);n=len(ids);y=futures.mean(-1);records={}
    for encoding in a.ENCODINGS:
        folds=[]
        for b in range(n):
            keep=np.array([j for j in range(n) if j!=b],dtype=np.int64)
            models=path(*pooled(x,y,encoding,keep),encoding)
            folds.append(dict(validation_block=int(ids[b]),training_blocks=ids[keep].tolist(),models=models))
        models=path(*pooled(x,y,encoding,np.arange(n,dtype=np.int64)),encoding)
        records[encoding]=dict(training_blocks=ids.tolist(),folds=folds,models=models)
    return dict(schema='d164_shared_models_v1',training_blocks=ids.tolist(),calibration=list(CALIBRATION),
                encodings=list(a.ENCODINGS),alphas=list(a.ALPHAS),new_fits=9*(n+1),models=records,
                target='four_future_mean',pilot_outcomes_used=False,condition_indicator=False,inner_selection=False)


def forward(model,x):
    if model['model_class']!=CLASS or model['calibration']!=list(CALIBRATION):raise ValueError('shared model contract')
    if x.ndim!=4 or x.shape[1:3]!=(4,4) or x.dtype!=np.float64 or not np.isfinite(x).all():
        raise ValueError('one complete view, no outcome or condition input')
    b,w=a.affine(model,x.shape[-1])
    return b+(x*w).sum(-1)


def forecast(records,features,ids=None):
    x=a.feature_matrices(features);n=len(features['start']);raw={}
    if records['schema']!='d164_shared_models_v1' or records['calibration']!=list(CALIBRATION):raise ValueError('model contract')
    if ids is not None and (ids.dtype!=np.int64 or ids.tolist()!=records['training_blocks'] or len(ids)!=n):
        raise ValueError('out-of-founder forecasts require exact fold identities')
    for e in a.ENCODINGS:
        m=records['models'][e]
        for kind in a.EDITS:
            name=e+':'+kind
            if ids is None:values=np.stack([forward(model,x[name]) for model in m['models']])
            else:
                rows=[]
                for j,fold in enumerate(m['folds']):
                    assert fold['validation_block']==int(ids[j]) and int(ids[j]) not in fold['training_blocks']
                    rows.append(np.stack([forward(model,x[name][j:j+1])[0] for model in fold['models']]))
                values=np.stack(rows,axis=1)
            if values.shape!=(3,n,4,4):raise ValueError('complete forecast panel')
            raw[name]=values
    return {k:np.clip(v,-1,1) for k,v in raw.items()},raw


def with_baselines(new,raw,source,source_raw):
    required=set(a.OBSERVERS)-{'starting','one_copy'}
    if set(new)!=set(raw) or set(new)!=required:raise ValueError('all fifteen diagnostic observers')
    p=dict(new);r=dict(raw)
    for k in ('starting','one_copy'):p[k]=source[k].copy();r[k]=source_raw[k].copy()
    return p,r


def decoder_changes(p,old,y,ids):
    result=[]
    for name in a.OBSERVERS+tuple(e+':mean_sham_loss' for e in a.ENCODINGS):
        for ai,alpha in enumerate(a.ALPHAS):
            c_loss=sum(w*(p[k][ai,...,None]-y)**2 for k,w in a.members(name))
            r_loss=sum(w*(old[k][ai,...,None]-y)**2 for k,w in a.members(name))
            ref=float(r_loss.mean());cand=float(c_loss.mean())
            values=a.aggregate((r_loss-c_loss)[...,None],ids)
            result.append(dict(observer=name,alpha=alpha,candidate='shared_decoder',reference='original_decoder',
                candidate_mse=cand,reference_mse=ref,relative_gain_percent=100*(ref-cand)/ref if ref else None,
                **{k:np.asarray(v)[...,0].tolist() for k,v in values.items()}))
    return result


def summarize(panels,sources):
    out={}
    for cohort in ('development','pilot'):
        p,raw=panels[cohort];old,old_raw,y,ids=sources[cohort]
        a.validate(old,old_raw,y,ids)
        for name in ('starting','one_copy'):
            np.testing.assert_array_equal(p[name],old[name]);np.testing.assert_array_equal(raw[name],old_raw[name])
        out[cohort]=dict(scores=a.cohort(p,raw,y,ids),decoder_changes=decoder_changes(p,old,y,ids))
    nd=len(sources['development'][3]);npilot=len(sources['pilot'][3])
    return dict(schema='d164_shared_decoder_v1',cohorts=out,new_fits=9*(nd+1),
        new_forecasts=45*16*(nd+npilot),reused_forecasts=6*16*(nd+npilot),
        calibration=list(CALIBRATION),post_test_development=True,prospective_evidence=False,
        condition_indicator=False,training_exposure_changed=True,causal_sharing_only_ablation=False,
        new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,source_primary_unchanged=True,
        confidence_intervals=False,automatic_successor=False)
