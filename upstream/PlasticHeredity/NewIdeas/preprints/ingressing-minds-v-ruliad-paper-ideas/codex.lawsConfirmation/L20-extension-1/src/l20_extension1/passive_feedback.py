"""D168 saved-copy feedback geometry and descriptive mixture accounting."""
import numpy as np
from . import passive_stages as old

GROUPS=old.GROUPS;TIMES=(0,1,300,1000)
LEVELS=(tuple(np.arange(-4,5)/4),tuple(np.arange(-2,3)/2))
RESPONSES=tuple(f'write_R_change:{t}' for t in TIMES)+('outgoing_own','outgoing_guide','final_preference')
DESCRIPTORS=('assigned_q','effective_q','start_reference_assigned','feedback_applied_R_at1')
PROFILE=('reference_assigned','reference_effective','theta_native_R','theta_applied_R',
    'theta_native_V','theta_applied_V','theta_R_alignment_change','theta_V_alignment_change')
EPS=1e-24;SIGN_TOL=1e-12
SHAPES=dict(shift=(4,4,2,2),q=(4,4,2,2),reference=(4,4,2,4,2),reference_valid=(4,4,2,4,2),
    feedback=(4,4,2,4,4),feedback_valid=(4,4,2,4,4),response=(4,4,2,7))


def corr(a,b):
    a,b=np.broadcast_arrays(a,b)
    assert a.shape[-2:]==(16,16) and np.isfinite(a).all() and np.isfinite(b).all()
    x=a-a.mean(axis=(-2,-1),keepdims=True);y=b-b.mean(axis=(-2,-1),keepdims=True)
    valid=(np.ptp(a,axis=(-2,-1))>0)&(np.ptp(b,axis=(-2,-1))>0)
    den=np.sqrt(np.sum(x*x,axis=(-2,-1))*np.sum(y*y,axis=(-2,-1)))
    return np.divide(np.sum(x*y,axis=(-2,-1)),den,out=np.zeros_like(den),where=valid),valid


def shifted(field,shift):
    assert field.shape[-2:]==(16,16) and shift.shape==field.shape[:-2]+(2,)
    assert shift.dtype==np.int64 and np.all((shift>=0)&(shift<16))
    return np.stack([np.roll(x,tuple(int(v) for v in s),(0,1)) for x,s in zip(
        field.reshape(-1,16,16),shift.reshape(-1,2))]).reshape(field.shape)


def ideal(shift,role):
    assert role in (0,1)
    target=np.broadcast_to(old.targets()[role],shift.shape[:-1]+(16,16))
    return np.mean(target*shifted(target,shift),axis=(-2,-1))


def extract(raw,saved):
    old.validate(raw);assert set(saved)=={'fields','preference'}
    assert saved['fields'].shape==(4,4,2,48,5) and saved['preference'].shape==(4,4,2,4)
    shift=raw['shift'];assert np.all((shift>=0)&(shift<16)) and not np.any(np.all(shift==0,axis=-1))
    for g in range(1,4):np.testing.assert_array_equal(shift[:,g],shift[:,0])
    q=np.empty((4,4,2,2));ref=np.empty((4,4,2,4,2));rv=np.empty_like(ref,dtype=bool)
    feedback=np.empty((4,4,2,4,4));fv=np.empty_like(feedback,dtype=bool)
    for g in range(4):
        effective=shift[:,g] if g%2==0 else np.zeros_like(shift[:,g])
        q[:,g,:,0]=ideal(shift[:,g],g//2);q[:,g,:,1]=ideal(effective,g//2)
        for j in range(4):
            state=raw['write_states'][:,g,:,j];v,r,theta=state[:,:,0],state[:,:,2],state[:,:,3]
            ref[:,g,:,j,0],rv[:,g,:,j,0]=corr(r,shifted(r,shift[:,g]))
            ref[:,g,:,j,1],rv[:,g,:,j,1]=corr(r,shifted(r,effective))
            applied=shifted(theta,effective)
            for k,(a,b) in enumerate(((theta,r),(applied,r),(theta,v),(applied,v))):
                feedback[:,g,:,j,k],fv[:,g,:,j,k]=corr(a,b)
    values=saved['fields'];initial=values[:,:,:,old.STAGES.index('write:0:R'),0]
    responses=[values[:,:,:,old.STAGES.index(f'write:{t}:R'),0]-initial for t in TIMES]
    responses += [values[:,:,:,old.STAGES.index('outgoing'),k] for k in (0,2)]
    responses += [saved['preference'][...,-1]]
    result=dict(shift=shift.copy(),q=q,reference=ref,reference_valid=rv,feedback=feedback,
        feedback_valid=fv,response=np.stack(responses,axis=-1))
    validate(result);return result


def validate(a,founders=None):
    assert set(a)==set(SHAPES)
    for k,shape in SHAPES.items():
        want=shape if founders is None else (founders,)+shape
        assert a[k].shape==want and a[k].dtype==(np.int64 if k=='shift' else bool if k.endswith('_valid') else np.float64)
        assert np.isfinite(a[k]).all()
    for k in ('reference','feedback'):assert np.all(a[k][~a[k+'_valid']]==0)
    assert np.all((a['shift']>=0)&(a['shift']<16)) and not np.any(np.all(a['shift']==0,axis=-1))
    for g in range(4):assert np.isin(a['q'][...,g,:,:] if founders is None else a['q'][:,:,g],LEVELS[g//2]).all()


def profiles(a):
    result=[('assigned_q',None,a['q'][...,0],np.ones_like(a['q'][...,0],dtype=bool)),
        ('effective_q',None,a['q'][...,1],np.ones_like(a['q'][...,1],dtype=bool))]
    for j,t in enumerate(TIMES):
        values=np.concatenate((a['reference'][...,j,:],a['feedback'][...,j,:],
            (a['feedback'][...,j,1]-a['feedback'][...,j,0])[...,None],
            (a['feedback'][...,j,3]-a['feedback'][...,j,2])[...,None]),axis=-1)
        valid=np.concatenate((a['reference_valid'][...,j,:],a['feedback_valid'][...,j,:],
            (a['feedback_valid'][...,j,0]&a['feedback_valid'][...,j,1])[...,None],
            (a['feedback_valid'][...,j,2]&a['feedback_valid'][...,j,3])[...,None]),axis=-1)
        result += [(name,t,values[...,k],valid[...,k]) for k,name in enumerate(PROFILE)]
    return result


def nullable(sums,counts):
    return [float(s/n) if n else None for s,n in zip(np.ravel(sums),np.ravel(counts))]


def describe(x,valid):
    assert x.ndim==valid.ndim==3 and x.shape==valid.shape and x.shape[1:]==(4,2)
    counts=valid.sum(axis=1);sums=np.where(valid,x,0).sum(axis=1);total=counts.sum(0)
    paired=valid[...,0]&valid[...,1];gap=x[...,1]-x[...,0]
    gn=paired.sum(1);gs=np.where(paired,gap,0).sum(1);means=nullable(gs,gn)
    return dict(copy_mean=nullable(sums.sum(0),total),valid=total.tolist(),invalid=(x.shape[0]*4-total).tolist(),
        founder_sum=sums.tolist(),founder_count=counts.tolist(),founder_mean=[nullable(s,n) for s,n in zip(sums,counts)],
        paired_gap=float(gs.sum()/gn.sum()) if gn.sum() else None,paired_count=int(gn.sum()),
        founder_gap=means,founder_gap_sum=gs.tolist(),founder_pair_count=gn.tolist(),
        positive=sum(v is not None and v>SIGN_TOL for v in means),negative=sum(v is not None and v<-SIGN_TOL for v in means),
        numerical_zero=sum(v is not None and abs(v)<=SIGN_TOL for v in means),undefined=sum(v is None for v in means))


def association(x,valid,y):
    assert x.shape==valid.shape==y.shape and x.shape[1:]==(4,)
    n=valid.sum(1);x=np.where(valid,x,0);y=np.where(valid,y,0)
    sufficient=np.stack((n,x.sum(1),y.sum(1),(x*x).sum(1),(x*y).sum(1),(y*y).sum(1)),axis=-1)
    count,sx,sy,sxx,sxy,syy=sufficient.sum(0)
    mx,my=(sx/count,sy/count) if count else (0.,0.)
    xx=np.where(valid,(x-mx)**2,0).sum();xy=np.where(valid,(x-mx)*(y-my),0).sum();yy=np.where(valid,(y-my)**2,0).sum()
    return dict(valid_pairs=int(count),invalid_pairs=int(valid.size-count),mean_x=float(mx) if count else None,
        mean_y=float(my) if count else None,sxx=float(xx),sxy=float(xy),syy=float(yy),
        slope=float(xy/xx) if xx>EPS else None,correlation=float(xy/np.sqrt(xx*yy)) if xx>EPS and yy>EPS else None,
        founder_sufficient=sufficient.tolist())


def level_rows(q,y,role):
    assert q.shape==y.shape[:-1] and q.shape[1:]==(4,2) and y.shape[-1]==7
    rows=[]
    for level in LEVELS[role]:
        mask=q==level;counts=mask.sum(1);sums=np.where(mask[...,None],y,0).sum(1);total=counts.sum(0)
        pooled=int(total.sum());means=[(sums[:,c].sum(0)/total[c]).tolist() if total[c] else [None]*7 for c in range(2)]
        rows.append(dict(q=float(level),counts=total.tolist(),proportions=(total/(len(q)*4)).tolist(),
            founders=(counts>0).sum(0).tolist(),founder_count=counts.tolist(),founder_sum=sums.tolist(),
            founder_mean=[[(s[c]/n[c]).tolist() if n[c] else [None]*7 for c in range(2)] for s,n in zip(sums,counts)],
            copy_means=means,pooled_mean=(sums.sum(axis=(0,1))/pooled).tolist() if pooled else [None]*7))
    return rows


def mixture(q,y,rows,k):
    ref=np.zeros_like(q)
    terms=[]
    for r in rows:
        mu=r['pooled_mean'][k];dp=r['proportions'][1]-r['proportions'][0]
        terms.append(dp*mu if mu is not None else 0.)
        if mu is not None:ref[q==r['q']]=mu
    g=(y[...,1]-y[...,0]).mean(1);mix=(ref[...,1]-ref[...,0]).mean(1)
    residual=((y-ref)[...,1]-(y-ref)[...,0]).mean(1)
    def omitted(v):
        z=(v.sum()-v)/(len(v)-1)
        return dict(values=z.tolist(),minimum=float(z.min()),maximum=float(z.max()))
    return dict(gap=float(g.mean()),mixture=float(mix.mean()),residual=float(residual.mean()),level_terms=terms,
        founder_gap=g.tolist(),founder_mixture=mix.tolist(),founder_residual=residual.tolist(),
        gap_omissions=omitted(g),mixture_omissions=omitted(mix),residual_omissions=omitted(residual),
        pooled_reference_refit_on_omission=False)


def summarize(development,pilot,di,pi):
    assert di.dtype==pi.dtype==np.int64 and len(di)>1 and len(pi)>1
    assert len(set(di))==len(di) and len(set(pi))==len(pi) and not set(di)&set(pi)
    profile_rows=[];levels=[];associations=[];mixtures=[]
    for co,a,ids in (('development',development,di),('pilot',pilot,pi)):
        validate(a,len(ids));available=profiles(a)
        descriptor=[(a['q'][...,0],np.ones_like(a['q'][...,0],bool)),(a['q'][...,1],np.ones_like(a['q'][...,1],bool)),
            (a['reference'][...,0,0],a['reference_valid'][...,0,0]),(a['feedback'][...,1,1],a['feedback_valid'][...,1,1])]
        for g,group in enumerate(GROUPS):
            for name,t,x,flag in available:
                profile_rows.append(dict(cohort=co,group=group,metric=name,time=t,**describe(x[:,:,g],flag[:,:,g])))
            q=a['q'][:,:,g,:,0];y=a['response'][:,:,g];lr=level_rows(q,y,g//2)
            levels += [dict(cohort=co,group=group,**r) for r in lr]
            for k,response in enumerate(RESPONSES):
                mixtures.append(dict(cohort=co,group=group,response=response,**mixture(q,y[...,k],lr,k)))
            for name,(x,flag) in zip(DESCRIPTORS,descriptor):
                v=x[:,:,g];ok=flag[:,:,g];delta=v[...,1]-v[...,0];valid=ok[...,0]&ok[...,1]
                for k,response in enumerate(RESPONSES):
                    dy=y[...,1,k]-y[...,0,k]
                    associations.append(dict(cohort=co,group=group,descriptor=name,response=response,
                        **association(delta,valid,dy)))
    return dict(schema='d168_passive_feedback_v1',development_ids=di.tolist(),pilot_ids=pi.tolist(),groups=list(GROUPS),
        times=list(TIMES),responses=list(RESPONSES),descriptors=list(DESCRIPTORS),profile_metrics=list(PROFILE),
        profile_rows=profile_rows,level_rows=levels,association_rows=associations,mixture_rows=mixtures,
        diagnostic_copies=32*(len(di)+len(pi)),independent_founders=len(di)+len(pi),
        post_test_description=True,all_cases_retained=True,new_dynamics=0,new_fits=0,new_forecasts=0,new_founders=0,
        outcomes_used=False,source_primary_unchanged=True,confidence_intervals=False,causal_attribution=False,
        prospective_evidence=False,automatic_successor=False)
