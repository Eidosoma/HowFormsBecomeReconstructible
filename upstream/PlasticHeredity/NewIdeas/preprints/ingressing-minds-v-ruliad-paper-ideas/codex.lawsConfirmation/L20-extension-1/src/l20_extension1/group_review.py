"""Post-result D152 saved-fit arithmetic only: no optimization or dynamics."""
import numpy as np

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
ARCH=('shared','group_sensitive')
ALPHAS=(.001,.01,.1,1.,10.,100.)
PAIRS=(('passive','starting'),('shuffle','starting'),('shuffle','passive'),
    ('attenuate','starting'),('attenuate','passive'),('attenuate','shuffle'),
    ('attenuate','sham_plus'),('attenuate','sham_minus'),('sham_plus','starting'),
    ('sham_plus','passive'),('sham_plus','shuffle'),('sham_minus','starting'),
    ('sham_minus','passive'),('sham_minus','shuffle'),('sham_minus','sham_plus'),
    ('attenuate','mean_sham_loss'),('mean_sham_loss','starting'),('mean_sham_loss','passive'))
Q=np.array([[-.5,-.5,.5],[-.5,.5,-.5],[.5,-.5,-.5],[.5,.5,.5]])
PARTS=('intercept','starting','U0','second','clipping')
GROUPS=('A_ordinary','A_aligned','B_ordinary','B_aligned')
COHORTS=(('d135',0,8),('d140',8,16),('former_test',16,32))


def specs():
    result=[dict(candidate_arch=a,candidate=c,reference_arch=a,reference=r) for a in ARCH for c,r in PAIRS]
    result.extend(dict(candidate_arch='group_sensitive',candidate=k,reference_arch='shared',reference=k) for k in MODELS)
    return result


def members(name):return (4,5) if name=='mean_sham_loss' else (MODELS.index(name),)


def matrices(data):
    a,e,t=data['start'],data['endpoint'],data['targeted']
    assert a.shape==(32,4,4,7) and e.shape==t.shape==(32,4,4,3,6)
    second=(e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])
    return [a]+[np.concatenate((a,e[...,0,:],value),axis=-1) for value in second]


def choose(mean):
    assert mean.shape==(6,) and np.isfinite(mean).all()
    return max(i for i in range(6) if mean[i]<=mean.min()+1e-12)


def forward(model,x,architecture):
    assert x.shape[:2]==(4,4);d=x.shape[-1]
    mu,offset,scale=(np.array(model[k]) for k in ('means','offsets','scale'))
    assert mu.shape==(4,d) and offset.shape==(4,) and scale.shape==(d,) and (scale>0).all()
    z=(x-mu[None,:,:])/scale
    if architecture=='shared':
        beta=np.array(model['beta']);assert beta.shape==(d,);slopes=np.broadcast_to(beta,(4,d))
    else:
        b=np.array(model['coefficients']);assert b.shape==(4,d);slopes=b[0]+Q@b[1:]
    terms=z*slopes[None,:,:];pieces=np.zeros((4,4,5));pieces[...,0]=offset
    pieces[...,1]=terms[...,:7].sum(axis=-1)
    if d==19:
        pieces[...,2]=terms[...,7:13].sum(axis=-1);pieces[...,3]=terms[...,13:19].sum(axis=-1)
    else:assert d==7
    raw=pieces.sum(axis=-1);prediction=np.clip(raw,-1,1);pieces[...,4]=prediction-raw
    assert np.isfinite(pieces).all();return prediction,pieces


def decompose(candidate,reference,y):
    # Arrays have model as first dimension. Composite comparators average
    # separate pairwise loss decompositions, never ensemble prediction loss.
    result=[]
    for c in candidate:
        for r in reference:
            d=np.broadcast_to(c-r,y.shape);cross=2*d*(r-y)
            result.append(np.stack(((r-y)**2-(c-y)**2,d*d,cross),axis=-1))
    return np.mean(result,axis=0)


def extract(data,predictions,fits):
    ids=data['block_ids'];assert ids.shape==(32,) and ids.dtype==np.int64 and len(set(ids.tolist()))==32
    assert set(predictions)==set(fits)==set(ARCH)
    x=matrices(data);p=np.stack([[predictions[a][k] for k in MODELS] for a in ARCH])
    assert p.shape==(2,6,32,4,4) and np.isfinite(p).all() and np.max(abs(p))<=1
    parts=np.empty(p.shape+(5,));inner=np.empty((2,6,32,31,6));means=np.empty((2,6,32,6))
    selected=np.empty((2,6,32),np.int64);drops=np.empty((2,6,32,31),np.int64)
    gaps=np.empty((2,6,32,2))
    for ai,a in enumerate(ARCH):
        assert set(predictions[a])==set(fits[a])==set(MODELS)
        for ki,k in enumerate(MODELS):
            record=fits[a][k];assert record['blocks']==ids.tolist() and record['alphas']==list(ALPHAS)
            assert len(record['folds'])==32
            for b,f in enumerate(record['folds']):
                train=np.delete(ids,b).tolist();assert f['validation_block']==int(ids[b])
                assert f['training_blocks']==f['inner_validation_blocks']==train
                v=np.array(f['inner_block_mse']);assert v.shape==(31,6) and np.isfinite(v).all() and (v>=0).all()
                mean=v.mean(axis=0);np.testing.assert_allclose(mean,f['inner_mean_mse'],atol=1e-14,rtol=0)
                index=choose(mean);assert f['selected_index']==index and f['model']['alpha']==ALPHAS[index]
                q,terms=forward(f['model'],x[ki][b],a);np.testing.assert_allclose(q,p[ai,ki,b],atol=2e-10,rtol=0)
                parts[ai,ki,b]=terms;inner[ai,ki,b]=v;means[ai,ki,b]=mean;selected[ai,ki,b]=index
                for j in range(31):drops[ai,ki,b,j]=choose(np.delete(v,j,axis=0).mean(axis=0))
                runner=min(mean[j] for j in range(6) if j!=index)
                gaps[ai,ki,b]=[mean[index]-mean.min(),runner-mean[index]]
    y=data['labels'];futures=data['futures'];assert y.shape==(32,4,4) and futures.shape==(16,4,4,4)
    assert all(np.isfinite(v).all() and np.max(abs(v))<=1 for v in (y,futures))
    original=[];future=[]
    for s in specs():
        c=p[ARCH.index(s['candidate_arch']),list(members(s['candidate']))]
        r=p[ARCH.index(s['reference_arch']),list(members(s['reference']))]
        original.append(decompose(c,r,y));future.append(decompose(c[:,16:,...,None],r[:,16:,...,None],futures))
    e=p-y
    return dict(block_ids=ids.copy(),labels=y.copy(),futures=futures.copy(),predictions=p,
        parts=parts,selected=selected,inner_losses=inner,inner_means=means,drop_selected=drops,selection_gaps=gaps,
        signed=e,absolute=abs(e),squared=e*e,contrast_terms=np.stack(original),future_terms=np.stack(future))


def error_stats(p,y):
    e=p-y;n=e.size;bias=float(e.mean());mse=float(np.mean(e*e))
    return dict(outcomes=n,mse=mse,mae_points=float(abs(e).mean()*100),rmse_points=float(np.sqrt(mse)*100),
        bias_points=bias*100,error_variance=float(np.var(e)))


def losses(panel,s,which,future=False):
    p=panel['predictions'][ARCH.index(s[which+'_arch']),list(members(s[which]))]
    y=panel['labels']
    if future:return ((p[:,16:,...,None]-panel['futures'])**2).mean(axis=(0,-1))
    return ((p-y)**2).mean(axis=0)


def stats(terms,candidate,reference,ids):
    n=len(terms)
    if not n:return dict(blocks=0,cases=0,block_ids=[],mse_reduction=None,candidate_mse=None,reference_mse=None,
        relative_reduction_percent=None,change_cost=None,error_correction=None,block_reductions=[],
        positive_blocks=0,negative_blocks=0,zero_blocks=0,group_reductions=[],group_contributions=[])
    gain=float(terms[...,0].mean());base=float(reference.mean());block=terms[...,0].mean(axis=(1,2));g=terms[...,0].mean(axis=(0,1))
    return dict(blocks=n,cases=candidate.size,block_ids=ids.tolist(),mse_reduction=gain,candidate_mse=float(candidate.mean()),
        reference_mse=base,relative_reduction_percent=100*gain/base if base else None,
        change_cost=float(terms[...,1].mean()),error_correction=float(-terms[...,2].mean()),
        block_reductions=block.tolist(),positive_blocks=int((block>0).sum()),negative_blocks=int((block<0).sum()),
        zero_blocks=int((block==0).sum()),group_reductions=g.tolist(),group_contributions=(g/4).tolist())


def describe(terms,candidate,reference,ids):
    result=stats(terms,candidate,reference,ids);n=len(ids);g=terms[...,0];block=g.mean(axis=(1,2))
    order=np.argsort(-block,kind='stable');case_order=np.argsort(-g.ravel(),kind='stable')
    deleted=np.array([np.delete(block,j).mean() for j in range(n)])
    result.update(block_contributions=(block/n).tolist(),block_order_best_first=ids[order].tolist(),
        case_order_best_first=case_order.tolist(),case_gains=int((g>0).sum()),case_losses=int((g<0).sum()),case_ties=int((g==0).sum()),
        leave_one_score_block_out=deleted.tolist(),leave_one_min=float(deleted.min()),leave_one_max=float(deleted.max()),
        leave_one_positive=int((deleted>0).sum()),leave_one_negative=int((deleted<0).sum()),leave_one_zero=int((deleted==0).sum()))
    return result


def alpha_relation(panel,s,terms,candidate,reference,ids,future=False):
    if s['candidate_arch']!=s['reference_arch'] or 'mean_sham_loss' in (s['candidate'],s['reference']):return None
    a=ARCH.index(s['candidate_arch']);ci,ri=MODELS.index(s['candidate']),MODELS.index(s['reference'])
    start=16 if future else 0;c=panel['selected'][a,ci,start:];r=panel['selected'][a,ri,start:]
    equal=c==r;out={}
    for name,mask in (('same',equal),('different',~equal)):
        value=stats(terms[mask],candidate[mask],reference[mask],ids[mask])
        value['contribution_to_full_mse_reduction']=float(terms[mask,...,0].sum()/terms[...,0].size)
        out[name]=value
    means=panel['inner_means'][a];c_cost=[means[ci,start+i,r[i]]-means[ci,start+i,c[i]] for i in range(len(ids))]
    r_cost=[means[ri,start+i,c[i]]-means[ri,start+i,r[i]] for i in range(len(ids))]
    return dict(partitions=out,candidate_indices=c.tolist(),reference_indices=r.tolist(),
        candidate_inner_cost_at_reference_index=c_cost,reference_inner_cost_at_candidate_index=r_cost,
        causal_isolation=False,new_outer_forecasts=False)


def summarize(panel):
    ids=panel['block_ids'];models={};selection={}
    for ai,a in enumerate(ARCH):
        models[a]={};selection[a]={}
        for ki,k in enumerate(MODELS):
            p=panel['predictions'][ai,ki];y=panel['labels'];f=panel['futures'];parts=panel['parts'][ai,ki]
            models[a][k]=dict(original=error_stats(p,y),groups=[error_stats(p[:,:,g],y[:,:,g]) for g in range(4)],
                blocks=[error_stats(p[b],y[b]) for b in range(32)],
                cohorts={name:error_stats(p[l:r],y[l:r]) for name,l,r in COHORTS},
                individual_futures=error_stats(p[16:,...,None],f),future_mean=error_stats(p[16:],f.mean(axis=-1)),
                future_groups=[error_stats(p[16:,:,g,None],f[:,:,g,:]) for g in range(4)],
                future_blocks=[error_stats(p[b+16,...,None],f[b]) for b in range(16)],
                future_variance=float(np.var(f,axis=-1).mean()),parts_means=parts.mean(axis=(0,1,2)).tolist(),
                parts_group_means=parts.mean(axis=(0,1)).tolist(),parts_block_means=parts.mean(axis=(1,2)).tolist())
            selected=panel['selected'][ai,ki];drop=panel['drop_selected'][ai,ki]
            selection[a][k]=dict(selected_indices=selected.tolist(),alpha_counts={str(v):int((selected==j).sum()) for j,v in enumerate(ALPHAS)},
                cohorts={name:{str(v):int((selected[l:r]==j).sum()) for j,v in enumerate(ALPHAS)} for name,l,r in COHORTS},
                score_row_deletion_changed_counts=(drop!=selected[:,None]).sum(axis=1).tolist(),
                score_row_deletion_alpha_counts=[int((drop==j).sum()) for j in range(6)],
                selected_minus_minimum=panel['selection_gaps'][ai,ki,:,0].tolist(),
                runner_up_minus_selected=panel['selection_gaps'][ai,ki,:,1].tolist(),
                complete_founder_retraining=False,new_outer_predictions=False)
    comparisons=[]
    for i,s in enumerate(specs()):
        terms=panel['contrast_terms'][i];c=losses(panel,s,'candidate');r=losses(panel,s,'reference')
        ft=panel['future_terms'][i].mean(axis=-2);fc=losses(panel,s,'candidate',True);fr=losses(panel,s,'reference',True)
        comparisons.append(dict(**s,original=describe(terms,c,r,ids),secondary=describe(ft,fc,fr,ids[16:]),
            cohorts={name:stats(terms[l:h],c[l:h],r[l:h],ids[l:h]) for name,l,h in COHORTS},
            alpha_relation=alpha_relation(panel,s,terms,c,r,ids),
            future_alpha_relation=alpha_relation(panel,s,ft,fc,fr,ids[16:],True)))
    return dict(schema='d152_saved_fit_review_v1',posthoc=True,prospective_evidence=False,all_cases_retained=True,
        blocks=32,cases=512,architectures=list(ARCH),observers=list(MODELS),groups=list(GROUPS),parts=list(PARTS),
        models=models,selection=selection,comparisons=comparisons,new_fits=0,new_predictions=0,new_dynamics=0,
        repeated_future_blocks=16,repeated_outcomes=1024,source_primary_unchanged=True,
        confidence_intervals=False,causal_regularization_claim=False,automatic_successor=False,
        deleted_score_rows_are_not_retrained_folds=True,mean_sham_is_loss_not_ensemble=True)


def fixture():
    # Manual saved-fit fixtures; no optimizer is called even in qualification.
    rng=np.random.default_rng(1525202026)
    data=dict(start=rng.normal(size=(32,4,4,7)),endpoint=rng.normal(size=(32,4,4,3,6)),
        targeted=rng.normal(size=(32,4,4,3,6)),labels=rng.uniform(-.6,.6,(32,4,4)),
        futures=rng.uniform(-.6,.6,(16,4,4,4)),block_ids=np.arange(32,dtype=np.int64))
    x=matrices(data);predictions={};fits={}
    for ai,a in enumerate(ARCH):
        predictions[a]={};fits[a]={}
        for ki,k in enumerate(MODELS):
            forecasts=[];folds=[];d=x[ki].shape[-1]
            for b in range(32):
                center=(b+ki+ai)%6;v=rng.uniform(.001,.003,(31,6))+((np.arange(6)-center)**2)*.00002
                mean=v.mean(axis=0);index=choose(mean)
                m=dict(alpha=ALPHAS[index],means=rng.normal(scale=.05,size=(4,d)).tolist(),
                    offsets=rng.normal(scale=.03,size=4).tolist(),scale=rng.uniform(.8,1.2,d).tolist())
                if ai:m['coefficients']=rng.normal(scale=.06,size=(4,d)).tolist()
                else:m['beta']=rng.normal(scale=.1,size=d).tolist()
                forecast,_=forward(m,x[ki][b],a);forecasts.append(forecast);train=np.delete(data['block_ids'],b).tolist()
                folds.append(dict(validation_block=b,training_blocks=train,inner_validation_blocks=train,
                    inner_block_mse=v.tolist(),inner_mean_mse=mean.tolist(),selected_index=index,model=m))
            predictions[a][k]=np.stack(forecasts)
            fits[a][k]=dict(blocks=data['block_ids'].tolist(),alphas=list(ALPHAS),folds=folds)
    return data,predictions,fits
