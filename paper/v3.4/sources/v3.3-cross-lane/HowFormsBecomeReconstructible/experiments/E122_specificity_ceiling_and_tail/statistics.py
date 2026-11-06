"""Paired ratios and bounded, deterministic profile-grid tail models."""
import numpy as np
from scipy.stats import t as student_t

def interval(v,draws):
    v=np.asarray(v,float);means=v[draws].mean(axis=1)
    return dict(mean=float(v.mean()),ci95=np.quantile(means,[.025,.975]).tolist(),block_values=v.tolist())

def fieller(n,d,confidence=.95):
    n,d=np.asarray(n,float),np.asarray(d,float);size=len(n)
    assert n.shape==d.shape and size>1 and np.isfinite(n).all() and np.isfinite(d).all()
    a,b=float(n.mean()),float(d.mean());cov=np.cov(np.stack((n,d)),ddof=1)/size
    q=float(student_t.ppf((1+confidence)/2,size-1))**2
    aa=b*b-q*cov[1,1];bb=-2*(a*b-q*cov[0,1]);cc=a*a-q*cov[0,0]
    disc=bb*bb-4*aa*cc
    # Correct only cancellation at the discriminant's floating-point roundoff scale;
    # never regularize the denominator or truncate a confidence-set endpoint.
    corrected=bool(disc<0 and -disc<=64*np.finfo(float).eps*(bb*bb+abs(4*aa*cc)))
    if corrected:disc=0.
    if aa==0:
        if bb==0:kind,sets=('all_real',[[None,None]]) if cc<=0 else ('empty',[])
        else:
            bound=-cc/bb;kind='half_line';sets=[[None,float(bound)]] if bb>0 else [[float(bound),None]]
    elif disc<0 or (disc==0 and aa<0):kind,sets=('all_real',[[None,None]]) if aa<0 else ('empty',[])
    else:
        lo,hi=sorted(((-bb-np.sqrt(disc))/(2*aa),(-bb+np.sqrt(disc))/(2*aa)))
        kind,sets=('bounded',[[float(lo),float(hi)]]) if aa>0 else ('two_rays',[[None,float(lo)],[float(hi),None]])
    return dict(point=a/b if b!=0 else None,numerator=a,denominator=b,
        confidence=confidence,method='Student-t Fieller set for paired block means; asymptotic joint-normal approximation',
        kind=kind,sets=sets,unbounded_endpoint_convention='null',quadratic=[float(aa),float(bb),float(cc)],
        discriminant_roundoff_corrected=corrected,
        denominator_t_interval=[float(b-np.sqrt(q*cov[1,1])),float(b+np.sqrt(q*cov[1,1]))])

def ratio_bootstrap(n,d,draws):
    nn=np.asarray(n)[draws].mean(axis=1);dd=np.asarray(d)[draws].mean(axis=1)
    with np.errstate(divide='ignore',invalid='ignore'):ratio=nn/dd
    valid=np.isfinite(ratio)
    info=dict(draws=len(dd),zero_denominators=int((dd==0).sum()),negative_denominators=int((dd<0).sum()),
        nonfinite_ratios=int((~valid).sum()),discarded_draws=0,
        percentile95=np.quantile(ratio,[.025,.975]).tolist() if valid.all() else None,
        percentile_available=bool(valid.all()))
    return info,np.stack((nn,dd,ratio),axis=1)

def grid(g,model,cfg):
    g=np.asarray(g,float)
    if model=='power_zero':
        tau=np.geomspace(*cfg['fit_tau_bounds'],cfg['power_tau_points'])
        p=np.geomspace(*cfg['power_p_bounds'],cfg['power_p_points'])
        tau,p=np.meshgrid(tau,p,indexing='ij');tau=tau.ravel();p=p.ravel()
        x=(1+g[None,:]/tau[:,None])**(-p[:,None])
    else:
        tau=np.geomspace(*cfg['fit_tau_bounds'],cfg['fit_tau_points']);p=np.zeros_like(tau)
        x=np.exp(-g[None,:]/tau[:,None])
    return tau,p,x

def fit_batch(y,g,model,cfg):
    y=np.atleast_2d(np.asarray(y,float));tau,p,x=grid(g,model,cfg)
    assert np.isfinite(y).all() and y.shape[1]==len(g)
    sx=x.sum(axis=1);sxx=(x*x).sum(axis=1);m=len(g);answers=[]
    amin,amax=cfg['fit_A_bounds'];cmin,cmax=cfg['fit_C_bounds']
    for first in range(0,len(y),128):
        yy=y[first:first+128];sy=yy.sum(axis=1)[:,None];syy=(yy*yy).sum(axis=1)[:,None]
        xy=yy@x.T
        if model=='exponential_plateau':
            denom=sxx-sx*sx/m
            a=(xy-sy*sx/m)/denom;c=(sy-a*sx)/m
            pairs=[(c,a,(c>=cmin)&(c<=cmax)&(a>=amin)&(a<=amax))]
            for bound in (amin,amax):
                aa=np.full_like(a,bound);pairs.append((np.clip((sy-aa*sx)/m,cmin,cmax),aa,True))
            for bound in (cmin,cmax):
                cc=np.full_like(c,bound);pairs.append((cc,np.clip((xy-cc*sx)/sxx,amin,amax),True))
        else:
            a=np.clip(xy/sxx,amin,amax);pairs=[(np.zeros_like(a),a,True)]
        best=np.full_like(xy,np.inf);best_c=np.zeros_like(xy);best_a=np.zeros_like(xy)
        for c,a,ok in pairs:
            loss=np.maximum(0.,syy+m*c*c+a*a*sxx+2*c*a*sx-2*c*sy-2*a*xy)
            loss=np.where(ok,loss,np.inf);take=loss<best
            best=np.where(take,loss,best);best_c=np.where(take,c,best_c);best_a=np.where(take,a,best_a)
        index=best.argmin(axis=1);row=np.arange(len(yy))
        c=best_c[row,index];a=best_a[row,index];tt=tau[index];pp=p[index]
        boundary=(tt==cfg['fit_tau_bounds'][0])|(tt==cfg['fit_tau_bounds'][1])|(a==amin)|(a==amax)
        if model=='exponential_plateau':boundary|=(c==cmin)|(c==cmax)
        if model=='power_zero':boundary|=(pp==cfg['power_p_bounds'][0])|(pp==cfg['power_p_bounds'][1])
        answers.append(np.stack((c,a,tt,pp,best[row,index],boundary.astype(float)),axis=1))
    result=np.concatenate(answers);assert np.isfinite(result).all();return result

def predict(fits,g,model):
    fits=np.atleast_2d(fits);g=np.asarray(g,float)[None,:]
    c,a,tau,p=[fits[:,i,None] for i in range(4)]
    x=(1+g/tau)**(-p) if model=='power_zero' else np.exp(-g/tau)
    return c+a*x

def fit_summary(fits,g,y,model):
    point=fits[0];boot=fits[1:]
    return dict(model=model,parameters=dict(zip(('C','A','tau','p','sse','at_boundary'),point.tolist())),
        bootstrap95={name:np.quantile(boot[:,i],[.025,.975]).tolist() for i,name in enumerate(('C','A','tau','p'))},
        boundary_draws=int(boot[:,5].sum()),bootstrap_draws=len(boot),failed_fits=0,discarded_draws=0,
        predictions=predict(point,g,model)[0].tolist(),residuals=(y-predict(point,g,model)[0]).tolist(),
        identification='Grid-boundary fits and broad time-constant intervals indicate weak identification; a finite-horizon fitted plateau is not indefinite retention.')
