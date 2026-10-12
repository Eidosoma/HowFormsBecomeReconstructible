"""D159: algebraic accounting of saved forecasts; no fitting or dynamics."""
import numpy as np
from . import influence_models as prior

ALPHAS=prior.ALPHAS
OBSERVERS=prior.OBSERVERS
LOSS_OBSERVERS=prior.LOSS_OBSERVERS
PAIRS=prior.PAIRS
PARTS=('group_offset','starting','reading_level','reading_half_difference','clipping')
Q=np.array([[-1,-1,1],[-1,1,-1],[1,-1,-1],[1,1,1]],dtype=float)/2


def model_parts(model,x):
    """Saved training centering/scales; raw-coordinate mean/half-difference."""
    mu,scale,beta,offset=(np.asarray(model[k],dtype=float) for k in ('means','scale','coefficients','offsets'))
    if x.shape not in ((4,4,7),(4,4,13),(4,4,19)):raise ValueError('declared features')
    d=x.shape[-1]
    if mu.shape!=(4,d) or scale.shape!=(d,) or beta.shape!=(4,d) or offset.shape!=(4,):raise ValueError('model shapes')
    if not all(np.isfinite(v).all() for v in (x,mu,scale,beta,offset)) or np.any(scale<=0):raise ValueError('finite positive scaling')
    w=(beta[0]+Q@beta[1:])/scale
    centered=x-mu
    parts=np.zeros((4,4,5),dtype=float);parts[...,0]=offset
    parts[...,1]=(centered[...,:7]*w[:,:7]).sum(axis=-1)
    if d==19:
        m=(x[...,7:13]+x[...,13:19])/2
        diff=(x[...,13:19]-x[...,7:13])/2
        mm=(mu[:,7:13]+mu[:,13:19])/2
        md=(mu[:,13:19]-mu[:,7:13])/2
        parts[...,2]=((m-mm)*(w[:,7:13]+w[:,13:19])).sum(axis=-1)
        parts[...,3]=((diff-md)*(w[:,13:19]-w[:,7:13])).sum(axis=-1)
    elif d==13:parts[...,2]=(centered[...,7:]*w[:,7:]).sum(axis=-1)
    return parts


def extract(data,b,br,p,raw,bfits,rfits):
    prior.validate(data);features=prior.old.features(data);n=len(data['block_ids']);answer={}
    for name in OBSERVERS:
        base=np.empty((3,n,4,4,5));refit=np.empty((n,3,n-1,4,4,5))
        for v in range(n):
            for a in range(3):
                base[a,v]=model_parts(bfits[name]['folds'][v]['models'][5][a],features[name][v])
        for d in range(n):
            for j,v in enumerate(i for i in range(n) if i!=d):
                for a in range(3):
                    refit[d,a,j]=model_parts(rfits[name]['deletions'][d]['folds'][j]['models'][a],features[name][v])
        for prefix,z,clipped,unclipped in (('baseline',base,b[name],br[name]),('refit',refit,p[name],raw[name])):
            np.testing.assert_allclose(z.sum(axis=-1),unclipped,atol=2e-10,rtol=0)
            np.testing.assert_array_equal(clipped,np.clip(unclipped,-1,1))
            z[...,4]=clipped-unclipped
            np.testing.assert_allclose(z.sum(axis=-1),clipped,atol=2e-10,rtol=0)
            answer[prefix+'__'+name]=z
    return answer


def members(name):
    if name.endswith(':mean_sham_loss'):
        prefix=name.split(':')[0]+':'
        return ((prefix+'sham_plus',.5),(prefix+'sham_minus',.5))
    if name not in OBSERVERS:raise ValueError('unknown observer')
    return ((name,1.),)


def gap(candidate,reference,cp,rp,cq,rq,y,future=False):
    answer=None
    for c,cweight in members(candidate):
        for r,rweight in members(reference):
            delta=rp[r]-cp[c];factor=rq[r]+cq[c]
            if future:delta=delta[...,None,:];factor=factor[...,None]
            value=cweight*rweight*delta*(factor-2*y)[...,None]
            answer=value if answer is None else answer+value
    return answer


def accounting(parts,b,p,data):
    n=len(data['block_ids'])
    bp={k:parts['baseline__'+k] for k in OBSERVERS}
    rp={k:parts['refit__'+k] for k in OBSERVERS}
    scorep={k:np.stack([np.delete(bp[k],d,axis=1) for d in range(n)]) for k in OBSERVERS}
    scoreq={k:np.stack([np.delete(b[k],d,axis=1) for d in range(n)]) for k in OBSERVERS}
    yy=np.stack([np.delete(data['labels'],d,axis=0) for d in range(n)])[:,None]
    ff=np.stack([np.delete(data['futures'],d,axis=0) for d in range(n)])[:,None]
    out={}
    for panel,cp,rparts,cq,rq,y,f,pairs in (
        ('baseline',bp,bp,b,b,data['labels'],data['futures'],PAIRS),
        ('refit',rp,rp,p,p,yy,ff,PAIRS),
        ('training',rp,scorep,p,scoreq,yy,ff,tuple((k,k) for k in LOSS_OBSERVERS))):
        for j,(c,r) in enumerate(pairs):
            out[f'{panel}__pair{j:02d}__original']=gap(c,r,cp,rparts,cq,rq,y)
            out[f'{panel}__pair{j:02d}__futures']=gap(c,r,cp,rparts,cq,rq,f,True)
    return out


def totals(x,detailed=True):
    # x is founder,life,group,component, after repeat averaging/selection.
    mean=x.mean(axis=(0,1,2))
    result=dict(mse_reduction=float(mean.sum()),components=mean.tolist())
    if detailed:
        result.update(block_components=x.mean(axis=(1,2)).tolist(),group_components=x.mean(axis=(0,1)).tolist())
    return result


def contrast(original,futures):
    return dict(original=totals(original),individual_futures=totals(futures.mean(axis=3)),
        mean_target=totals(futures.mean(axis=3)),
        by_repeat=[totals(futures[...,i,:],False) for i in range(4)],
        leave_one_repeat_out=[totals(np.delete(futures,i,axis=3).mean(axis=3),False) for i in range(4)])


def component_stats(x):
    return dict(mean=x.mean(axis=(0,1,2)).tolist(),rms=np.sqrt((x*x).mean(axis=(0,1,2))).tolist(),
        group_mean=x.mean(axis=(0,1)).tolist())


def panel(parts,q,raw,data,arrays,prefix,a,d=None,score=False):
    models={}
    for name in OBSERVERS:
        z=parts['baseline__'+name][a] if d is None or score else parts['refit__'+name][d,a]
        if score:z=np.delete(z,d,axis=0)
        pred=q[name][a];f=data['futures'];y=data['labels']
        models[name]=dict(original=prior.old.error_stats(pred-y),
            individual_futures=prior.old.error_stats(pred[...,None]-f),
            mean_target=prior.old.error_stats(pred-f.mean(axis=-1)),
            by_repeat=[prior.old.error_stats(pred-f[...,i]) for i in range(4)],
            clipped_cases=int(np.count_nonzero(abs(raw[name][a])>1)),component_stats=component_stats(z))
    comparisons=[]
    for j,(c,r) in enumerate(PAIRS):
        o=arrays[f'{prefix}__pair{j:02d}__original']
        f=arrays[f'{prefix}__pair{j:02d}__futures']
        o,f=(o[a],f[a]) if prefix=='baseline' else (o[d,a],f[d,a])
        if score:o,f=np.delete(o,d,axis=0),np.delete(f,d,axis=0)
        comparisons.append(dict(candidate=c,reference=r,**contrast(o,f)))
    return dict(blocks=data['block_ids'].tolist(),models=models,comparisons=comparisons)


def metadata(n):
    return dict(schema='d159_reading_components_development_v1',components=list(PARTS),
        blocks=n,cases=16*n,observers=list(OBSERVERS),alphas=list(ALPHAS),
        groups=list(prior.old.GROUPS),observer_comparison_records=165*(1+2*n),
        training_effect_records=42*n,saved_models_replayed=36*n*n,
        saved_forecasts_replayed=576*n*n,new_fits=0,new_predictions=0,new_dynamics=0,
        new_founders=0,new_diagnostic_cycles=0,posthoc=True,prospective_evidence=False,
        all_deletions_retained=True,all_repeats_retained=True,all_settings_retained=True,
        component_only_forecasts=False,causal_attribution=False,
        centering='saved training group means; original raw-coordinate mean and half-difference',
        gap_rule='(reference_part-candidate_part)*(reference_prediction+candidate_prediction-2*outcome)',
        mean_sham_is_loss_not_ensemble=True,confidence_intervals=False,automatic_successor=False)


def summarize(parts,arrays,b,br,p,raw,data):
    scores={};n=len(data['block_ids'])
    for a,alpha in enumerate(ALPHAS):
        full=panel(parts,b,br,data,arrays,'baseline',a);deletions=[]
        for d in range(n):
            reduced=prior.subset(data,d)
            refit=panel(parts,{k:p[k][d] for k in OBSERVERS},{k:raw[k][d] for k in OBSERVERS},
                reduced,arrays,'refit',a,d)
            score=panel(parts,{k:np.delete(b[k],d,axis=1) for k in OBSERVERS},
                {k:np.delete(br[k],d,axis=1) for k in OBSERVERS},reduced,arrays,'baseline',a,d,True)
            training=[dict(observer=k,**contrast(arrays[f'training__pair{j:02d}__original'][d,a],
                arrays[f'training__pair{j:02d}__futures'][d,a])) for j,k in enumerate(LOSS_OBSERVERS)]
            deletions.append(dict(deleted_block=int(data['block_ids'][d]),refitted=refit,score_only=score,training_effect=training))
        scores[str(alpha)]=dict(full=full,deletions=deletions)
    return dict(**metadata(n),scores=scores)


def fixture(n=16):
    """Fabricated saved models, not fitted models. No optimizer or linear solver."""
    data=prior.fixture(n);ids=data['block_ids'];features=prior.old.features(data)
    b={};br={};p={};raw={};bfits={};rfits={};rng=np.random.default_rng(159091)
    y=data['futures'].mean(axis=-1)
    for name,x in features.items():
        dim=x.shape[-1];base=np.empty((3,n,4,4));deleted=np.empty((n,3,n-1,4,4))
        def records(v,d=None):
            keep=[k for k in range(n) if k!=v and k!=d]
            mu=x[keep].mean(axis=(0,1));scale=np.maximum(x[keep].std(axis=(0,1,2)),.2)
            offset=y[keep].mean(axis=(0,1));models=[]
            for a,alpha in enumerate(ALPHAS):
                coef=rng.normal(0,.15/(a+1),(4,dim))
                m=dict(alpha=alpha,means=mu.tolist(),scale=scale.tolist(),offsets=offset.tolist(),
                    coefficients=coef.tolist(),model_class=prior.ridge.CLASS)
                models.append(m)
            return dict(validation_block=int(ids[v]),training_blocks=ids[keep].tolist(),models=models)
        folds=[]
        for v in range(n):
            record=records(v)
            for a,m in enumerate(record['models']):
                g=np.tile(np.arange(4),4)
                base[a,v]=prior.old.raw_predict(m,x[v].reshape(16,dim),g).reshape(4,4)
            folds.append(dict(**{k:record[k] for k in ('validation_block','training_blocks')},
                models=[record['models'] for _ in range(6)]))
        bfits[name]=dict(blocks=ids.tolist(),alphas=list(ALPHAS),training_targets=list(prior.old.TARGETS),
            folds=folds,model_class=prior.ridge.CLASS,observer=name,
            preprocessing='training-only within each whole-founder fold',inner_selection=False,prospective_evidence=False)
        deletions=[]
        for d in range(n):
            keep=[k for k in range(n) if k!=d];rows=[]
            for j,v in enumerate(keep):
                rec=records(v,d);rows.append(rec)
                for a,m in enumerate(rec['models']):
                    deleted[d,a,j]=prior.old.raw_predict(m,x[v].reshape(16,dim),g).reshape(4,4)
            deletions.append(dict(deleted_block=int(ids[d]),remaining_blocks=ids[keep].tolist(),folds=rows))
        rfits[name]=dict(blocks=ids.tolist(),alphas=list(ALPHAS),target='future_mean',observer=name,
            model_class=prior.ridge.CLASS,training_blocks_per_fold=n-2,inner_selection=False,
            preprocessing='training-only; deletion and validation founder excluded',deletions=deletions)
        br[name]=base;b[name]=np.clip(base,-1,1);raw[name]=deleted;p[name]=np.clip(deleted,-1,1)
    return data,b,br,p,raw,bfits,rfits
