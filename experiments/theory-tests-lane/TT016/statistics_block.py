"""Frozen stratified block inference and independently checkable decisions."""
import math
import numpy as np
from scipy.stats import t
import support as s

def bounds(values,margin):
    x=np.asarray(values,dtype=float).reshape(4,16);s.require(np.isfinite(x).all() and np.max(abs(x))<=1,'Bounded complete block contrasts')
    mean=float(x.mean());v=x.var(axis=1,ddof=1)/16;variance=float(v.sum()/16)
    if variance==0:
        df=None;method='Hoeffding zero-variance fallback';radius=math.sqrt(2*math.log(20)/64);radius2=math.sqrt(2*math.log(40)/64)
    else:
        df=float(v.sum()**2/np.sum(v*v/15));method='stratified Welch-Satterthwaite'
        radius=float(t.ppf(.95,df))*math.sqrt(variance);radius2=float(t.ppf(.975,df))*math.sqrt(variance)
    low,high=max(-1.,mean-radius),min(1.,mean+radius)
    return dict(mean=mean,se=math.sqrt(variance),df=df,method=method,practical_margin=margin,
        lower_one_sided95=low,upper_one_sided95=high,two_sided95=[max(-1.,mean-radius2),min(1.,mean+radius2)],
        practical_superiority=bool(low>margin),practical_superiority_unsupported=bool(high<margin),
        classification='PASS' if low>margin else 'UNSUPPORTED' if high<margin else 'INCONCLUSIVE',
        positive_blocks=int((x>0).sum()),tied_blocks=int((x==0).sum()),negative_blocks=int((x<0).sum()))


def bootstrap(values,cfg):
    x=np.asarray(values,dtype=float).reshape(4,16);rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    total=np.zeros(20000)
    for h in range(4):total+=x[h,rng.integers(0,16,(20000,16))].mean(axis=1)/4
    return np.quantile(total,[.025,.975]).tolist()


def audit_bounds(counts,margin,observed):
    """Integer per-block success differences over 16 records; separate quantile calculation."""
    from fractions import Fraction
    from scipy.special import stdtrit
    rows=np.asarray(counts).reshape(4,16);s.require(rows.dtype.kind in 'iu','Integer success differences')
    mean=float(Fraction(sum(map(int,rows.ravel())),64*16));variances=[]
    for row in rows:
        values=list(map(int,row));ss=Fraction(sum(y*y for y in values),1)-Fraction(sum(values)**2,16)
        variances.append(ss/Fraction(15*16*16**2,1))
    total=sum(variances);variance=total/16
    if not variance:
        df=None;radius=math.sqrt(math.log(20)/32);radius2=math.sqrt(math.log(40)/32)
    else:
        df=float(total*total/sum(v*v/15 for v in variances))
        radius=float(stdtrit(df,.95))*math.sqrt(float(variance));radius2=float(stdtrit(df,.975))*math.sqrt(float(variance))
    low,high=max(-1.,mean-radius),min(1.,mean+radius)
    for key,truth in dict(mean=mean,se=math.sqrt(float(variance)),lower_one_sided95=low,upper_one_sided95=high,
        two_sided95=[max(-1.,mean-radius2),min(1.,mean+radius2)]).items():s.close(observed[key],truth,1e-12,'Independent interval '+key)
    if df is None:s.require(observed['df'] is None,'Degenerate interval convention')
    else:s.close(df,observed['df'],1e-12,'Independent degrees of freedom')
    s.require(observed['practical_superiority']==(low>margin) and observed['practical_superiority_unsupported']==(high<margin),'Independent practical decision')
    s.require(observed['classification']==('PASS' if low>margin else 'UNSUPPORTED' if high<margin else 'INCONCLUSIVE'),'Complete gate classification')
    return True


def audit_bootstrap(counts,cfg,interval,denominator=16):
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']));values=np.zeros(20000)
    for h,row in enumerate(np.asarray(counts).reshape(4,16)):
        draws=rng.integers(0,16,(20000,16))
        multiplicities=np.stack([(draws==i).sum(axis=1) for i in range(16)],axis=1)
        values+=(multiplicities@row)/(4*16*denominator)
    ordered=sorted(map(float,values))
    def q(p):
        location=p*19999;i=math.floor(location);fraction=location-i
        return ordered[i]*(1-fraction)+ordered[i+1]*fraction
    s.close(interval,[q(.025),q(.975)],1e-12,'Independent bootstrap multiplicities')
