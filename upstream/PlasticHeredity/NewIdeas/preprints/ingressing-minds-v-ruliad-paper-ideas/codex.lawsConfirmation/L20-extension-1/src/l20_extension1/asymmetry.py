"""D163 descriptive algebra of already saved forecasts; no fitting/dynamics."""
import numpy as np
from .pilot_analysis import PAIRS

ALPHAS = (.001, .01, .1)
ENCODINGS = ('separate', 'mean', 'tied')
EDITS = ('passive', 'shuffle', 'attenuate', 'sham_plus', 'sham_minus')
OBSERVERS = ('starting', 'one_copy') + tuple(e+':'+k for e in ENCODINGS for k in EDITS)
Q = np.array([[-1,-1,1],[-1,1,-1],[1,-1,-1],[1,1,1]], dtype=float)/2
TERMS = ('alignment', 'bias_alignment', 'covariance_alignment', 'shift_cost', 'gain')


def specifications():
    rows = [dict(candidate=c, reference=r, candidate_alpha=a, reference_alpha=a,
                 kind='source_same_setting') for a in ALPHAS for c,r in PAIRS]
    rows += [dict(candidate=c, reference=r, candidate_alpha=.01,
                  reference_alpha=.001 if r=='starting' else .01, kind='source_selected_baseline')
             for c in ('tied:sham_minus','tied:passive') for r in ('starting','one_copy')]
    rows += [dict(candidate=e+':sham_plus', reference=e+':sham_minus',
                  candidate_alpha=a, reference_alpha=a, kind='direct_plus_minus')
             for e in ENCODINGS for a in ALPHAS]
    return rows


def members(name):
    if name in OBSERVERS:return ((name,1.),)
    if name in tuple(e+':mean_sham_loss' for e in ENCODINGS):
        e=name.split(':')[0]
        return ((e+':sham_plus',.5),(e+':sham_minus',.5))
    raise ValueError('unknown frozen observer')


def validate(predictions, raw, y, ids):
    n=len(ids)
    if n<2 or np.asarray(ids).shape!=(n,) or np.asarray(ids).dtype!=np.int64 or len(set(ids))!=n:
        raise ValueError('unique int64 whole-founder identities')
    if y.shape!=(n,4,4,4) or y.dtype!=np.float64 or not np.isfinite(y).all() or np.max(abs(y))>1:
        raise ValueError('complete bounded four-future outcomes')
    if set(predictions)!=set(OBSERVERS) or set(raw)!=set(OBSERVERS):
        raise ValueError('complete seventeen-observer panel')
    for k in OBSERVERS:
        for v in (predictions[k],raw[k]):
            if v.shape!=(3,n,4,4) or v.dtype!=np.float64 or not np.isfinite(v).all():
                raise ValueError('complete finite setting/founder/life/group panel')
        if not np.array_equal(predictions[k],np.clip(raw[k],-1,1)):
            raise ValueError('saved clipping identity')


def aggregate(values, ids):
    """Cell terms: founder, life, group, future, component; equal weights."""
    if values.ndim!=5 or values.shape[:4]!=(len(ids),4,4,4) or not np.isfinite(values).all():
        raise ValueError('complete finite cell-term panel')
    blocks=values.mean(axis=(1,2,3));futures=values.mean(axis=(0,1,2))
    return dict(overall=values.mean(axis=(0,1,2,3)).tolist(),
                blocks=blocks.tolist(), groups=values.mean(axis=(0,1,3)).tolist(),
                futures=futures.tolist(),
                omit_founder=((blocks.sum(0)-blocks)/(len(ids)-1)).tolist(),
                omit_future=((futures.sum(0)-futures)/3).tolist())


def pair_cells(c,r,y):
    d=(c-r)[...,None];residual=y-r[...,None]
    alignment=2*d*residual;cost=np.broadcast_to(d*d,y.shape)
    # Bias/covariance are defined within each requested aggregation, not per cell.
    return np.stack((alignment,cost,alignment-cost),-1)


def pair_record(predictions,y,ids,spec):
    ca=ALPHAS.index(spec['candidate_alpha']);ra=ALPHAS.index(spec['reference_alpha'])
    cells=np.zeros(y.shape+(3,));bias_inputs=[];reference_loss=0.;candidate_loss=0.
    for c,cw in members(spec['candidate']):
        candidate_loss+=cw*float(np.mean((predictions[c][ca,...,None]-y)**2))
        for r,rw in members(spec['reference']):
            pc,pr=predictions[c][ca],predictions[r][ra];weight=cw*rw
            cells+=weight*pair_cells(pc,pr,y)
            bias_inputs.append((weight,np.broadcast_to((pc-pr)[...,None],y.shape),y-pr[...,None]))
    for r,rw in members(spec['reference']):
        reference_loss+=rw*float(np.mean((predictions[r][ra,...,None]-y)**2))
    parts=aggregate(cells,ids)
    axes={'overall':(0,1,2,3),'blocks':(1,2,3),'groups':(0,1,3),'futures':(0,1,2)}
    for name,ax in axes.items():
        bias=sum(2*w*d.mean(axis=ax)*err.mean(axis=ax) for w,d,err in bias_inputs)
        old=np.asarray(parts[name]);align,cost,gain=np.moveaxis(old,-1,0)
        parts[name]=np.stack((align,bias,align-bias,cost,gain),-1).tolist()
    # Sensitivities use their own centering for the bias/covariance split.
    for name,ax,size in (('omit_founder',(1,2,3),len(ids)),('omit_future',(0,1,2),4)):
        b=sum(2*w*((d.mean()*size-d.mean(axis=ax))/(size-1))
              *((err.mean()*size-err.mean(axis=ax))/(size-1)) for w,d,err in bias_inputs)
        align,cost,gain=np.moveaxis(np.asarray(parts[name]),-1,0)
        parts[name]=np.stack((align,b,align-b,cost,gain),-1).tolist()
    return dict(**spec,reference_mse=reference_loss,candidate_mse=candidate_loss,
                relative_gain_percent=100*(reference_loss-candidate_loss)/reference_loss if reference_loss else None,
                **parts)


def sign_cells(plus,minus,passive,y):
    a=((plus+minus)/2-passive)[...,None];b=((plus-minus)/2)[...,None]
    r=y-passive[...,None]
    common=2*a*r-a*a-b*b;direction=2*b*r-2*a*b
    return np.stack((common,direction,common+direction,common-direction,2*direction),-1)


def cohort(predictions,raw,y,ids):
    validate(predictions,raw,y,ids)
    records=[pair_record(predictions,y,ids,s) for s in specifications()]
    signs=[]
    for e in ENCODINGS:
        for ai,a in enumerate(ALPHAS):
            z=sign_cells(predictions[e+':sham_plus'][ai],predictions[e+':sham_minus'][ai],
                         predictions[e+':passive'][ai],y)
            signs.append(dict(encoding=e,alpha=a,**aggregate(z,ids)))
    absolute={}
    for name in OBSERVERS:
        rows=[]
        for ai,a in enumerate(ALPHAS):
            error=predictions[name][ai,...,None]-y;loss=error*error
            rows.append(dict(alpha=a,mse=float(loss.mean()),mae_points=float(abs(error).mean()*100),
                rmse_points=float(np.sqrt(loss.mean())*100),bias_points=float(error.mean()*100),
                clipped=int(np.count_nonzero(predictions[name][ai]!=raw[name][ai])),
                blocks=loss.mean((1,2,3)).tolist(),groups=loss.mean((0,1,3)).tolist(),
                futures=loss.mean((0,1,2)).tolist()))
        absolute[name]=rows
    return dict(ids=ids.tolist(),founders=len(ids),cases=16*len(ids),futures=4,
                terms=list(TERMS),sign_terms=['common','directional','plus_gain','minus_gain','plus_over_minus'],
                absolute=absolute,comparisons=records,signs=signs,
                within_future_variance=float(np.var(y,axis=-1).mean()))


def feature_matrices(data):
    if set(data)!={'start','endpoint','targeted'}:raise ValueError('permitted features only')
    a,e,t=(data[k] for k in ('start','endpoint','targeted'));n=len(a)
    if a.shape!=(n,4,4,7) or e.shape!=(n,4,4,3,6) or t.shape!=e.shape:
        raise ValueError('frozen feature schema')
    if any(v.dtype!=np.float64 or not np.isfinite(v).all() for v in (a,e,t)):
        raise ValueError('finite float64 features')
    result={'starting':a.copy(),'one_copy':np.concatenate((a,e[...,0,:]),-1)}
    for name,second in zip(EDITS,(e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])):
        result['separate:'+name]=np.concatenate((a,e[...,0,:],second),-1)
        result['tied:'+name]=result['separate:'+name].copy()
        result['mean:'+name]=np.concatenate((a,(e[...,0,:]+second)/2),-1)
    return result


def affine(model,d):
    mu,scale,beta,offset=(np.asarray(model[k],dtype=float) for k in ('means','scale','coefficients','offsets'))
    if mu.shape!=(4,d) or beta.shape!=mu.shape or scale.shape!=(d,) or offset.shape!=(4,):
        raise ValueError('frozen affine model shapes')
    if not all(np.isfinite(v).all() for v in (mu,scale,beta,offset)) or np.min(scale)<=0:
        raise ValueError('finite positive scaling')
    w=(beta[0]+Q@beta[1:])/scale
    return offset-(w*mu).sum(-1),w


def model_accounting(data,fitted,predictions,raw,y,ids):
    validate(predictions,raw,y,ids);x=feature_matrices(data)
    if set(fitted)!=set(OBSERVERS):raise ValueError('all frozen models required')
    coordinates={};max_error=0.
    for k in OBSERVERS:
        if len(fitted[k])!=3:raise ValueError('all settings required')
        for ai,a in enumerate(ALPHAS):
            m=fitted[k][ai]
            if m['alpha']!=a:raise ValueError('fixed model setting')
            b,w=affine(m,x[k].shape[-1]);restored=b+(x[k]*w).sum(-1)
            np.testing.assert_allclose(restored,raw[k][ai],atol=2e-10,rtol=0)
            max_error=max(max_error,float(np.max(abs(restored-raw[k][ai]))))
            coordinates[k,ai]=(b,w)
    rows=[];arrays={}
    for e in ENCODINGS:
        kp,km=e+':sham_plus',e+':sham_minus';xp,xm=x[kp],x[km]
        for ai,a in enumerate(ALPHAS):
            bp,wp=coordinates[kp,ai];bm,wm=coordinates[km,ai]
            feature=((wp+wm)/2*(xp-xm)).sum(-1)
            model=bp-bm+((wp-wm)*(xp+xm)/2).sum(-1)
            clipping=(predictions[kp][ai]-raw[kp][ai])-(predictions[km][ai]-raw[km][ai])
            delta=np.stack((feature,model,clipping),-1)
            np.testing.assert_allclose(delta.sum(-1),predictions[kp][ai]-predictions[km][ai],atol=2e-10,rtol=0)
            factor=2*y-predictions[kp][ai,...,None]-predictions[km][ai,...,None]
            terms=delta[...,None,:]*factor[...,None]
            key=e+'__'+str(ai);arrays[key+'__forecast_parts']=delta;arrays[key+'__gain_parts']=terms
            rows.append(dict(encoding=e,alpha=a,forecast_mean=delta.mean((0,1,2)).tolist(),
                             forecast_rms=np.sqrt((delta*delta).mean((0,1,2))).tolist(),
                             gain=aggregate(terms,ids)))
    return dict(parts=['feature','model','clipping'],comparisons=rows,
                saved_models_reconstructed=51,saved_forecasts_reconstructed=51*16*len(ids),
                max_raw_error=max_error,causal_attribution=False,crossed_forecasts_deployed=False),arrays


def fixture(n=4,seed=16320260922):
    rng=np.random.default_rng(seed)
    data=dict(start=rng.normal(0,.4,(n,4,4,7)),endpoint=rng.normal(0,.4,(n,4,4,3,6)),
              targeted=rng.normal(0,.4,(n,4,4,3,6)))
    x=feature_matrices(data);fitted={};raw={}
    for k in OBSERVERS:
        d=x[k].shape[-1];records=[];r=[]
        for a in ALPHAS:
            scale=rng.uniform(.5,1.5,d);beta=rng.normal(0,.045,(4,d))
            if k.startswith('tied:'):beta[:,13:]=beta[:,7:13]*scale[13:]/scale[7:13]
            m=dict(alpha=a,means=rng.normal(0,.05,(4,d)).tolist(),scale=scale.tolist(),
                   coefficients=beta.tolist(),offsets=rng.normal(0,.1,4).tolist())
            b,w=affine(m,d);r.append(b+(x[k]*w).sum(-1));records.append(m)
        fitted[k]=records;raw[k]=np.stack(r)
    p={k:np.clip(v,-1,1) for k,v in raw.items()}
    y=np.tanh(data['start'][...,0,None]+rng.normal(0,.15,(n,4,4,4)))
    return data,fitted,p,raw,y,np.arange(n,dtype=np.int64)
