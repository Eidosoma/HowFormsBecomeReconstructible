"""Outward IEEE float intervals for the full continuous candidate domain."""
import itertools
import numpy as np
import support as s

READY=(s.PATTERNS!=2).astype(int)
FIRST=[];SIGN=[];GAPS=[];AGREE=[];ACTIVE=[]
for pattern in s.PATTERNS:
    times=np.flatnonzero(pattern!=2)
    FIRST.append(int(times[0]) if len(times) else 0)
    SIGN.append(1 if not len(times) or pattern[times[0]]==0 else -1)
    gaps=[];agree=[];active=[]
    for j in range(2):
        present=j+1<len(times);active.append(present)
        gaps.append(int(times[j+1]-times[j]) if present else 0)
        agree.append(1 if not present or pattern[times[j]]==pattern[times[j+1]] else -1)
    GAPS.append(gaps);AGREE.append(agree);ACTIVE.append(active)
FIRST=np.array(FIRST);SIGN=np.array(SIGN);GAPS=np.array(GAPS);AGREE=np.array(AGREE);ACTIVE=np.array(ACTIVE)
HAS_ID=READY.any(axis=1)


def down(x):return np.nextafter(np.asarray(x,dtype=float),-np.inf)
def up(x):return np.nextafter(np.asarray(x,dtype=float),np.inf)
def add(a,b):return down(a[0]+b[0]),up(a[1]+b[1])
def neg(a):return -a[1],-a[0]
def sub(a,b):return add(a,neg(b))
def mul(a,b):
    products=np.array([a[0]*b[0],a[0]*b[1],a[1]*b[0],a[1]*b[1]])
    return down(products.min(axis=0)),up(products.max(axis=0))
def unit(a):return np.maximum(0.,a[0]),np.minimum(1.,a[1])
def positive_product(a,b):return np.maximum(0.,down(a[0]*b[0])),np.minimum(1.,up(a[1]*b[1]))
ONE=(np.array(1.),np.array(1.))
HALF=(np.array(.5),np.array(.5))


def power(a,n):
    if n<0:raise ValueError('Nonnegative power required')
    result=ONE
    while n:
        if n&1:result=positive_product(result,a)
        n//=2
        if n:a=positive_product(a,a)
    return result


def pattern_bounds(lower,upper):
    lo,hi=np.asarray(lower,float),np.asarray(upper,float)
    pi,mu,lam,r0,chi=[(lo[i],hi[i]) for i in range(5)]
    lost=unit(sub(ONE,mu));recovery=positive_product(pi,lost)
    loss=positive_product(unit(sub(ONE,pi)),lost)
    stay0=unit(sub(ONE,recovery));stay1=unit(sub(ONE,loss))
    tlo=np.array([[stay0[0],recovery[0]],[loss[0],stay1[0]]])
    thi=np.array([[stay0[1],recovery[1]],[loss[1],stay1[1]]])
    nr=unit(sub(ONE,r0))
    ready=(np.where(READY[:,0],r0[0],nr[0]),np.where(READY[:,0],r0[1],nr[1]))
    for j in (0,1):ready=positive_product(ready,(tlo[READY[:,j],READY[:,j+1]],thi[READY[:,j],READY[:,j+1]]))
    powers=[power(lam,j) for j in range(3)]
    pl=np.array([x[0] for x in powers]);pu=np.array([x[1] for x in powers])
    bias=mul(chi,(pl[FIRST],pu[FIRST]));signed=mul(bias,(SIGN,SIGN))
    identity=unit(mul(add(ONE,signed),HALF))
    identity=(np.where(HAS_ID,identity[0],1.),np.where(HAS_ID,identity[1],1.))
    for j in (0,1):
        term=unit(mul(add(ONE,mul((pl[GAPS[:,j]],pu[GAPS[:,j]]),(AGREE[:,j],AGREE[:,j]))),HALF))
        term=(np.where(ACTIVE[:,j],term[0],1.),np.where(ACTIVE[:,j],term[1],1.))
        identity=positive_product(identity,term)
    return np.stack(positive_product(ready,identity),axis=-1)


def forecast_bounds(lower,upper,horizons=None):
    lo,hi=np.asarray(lower,float),np.asarray(upper,float);rows=[]
    for horizon in s.PLAN['horizons'] if horizons is None else horizons:
        mode=power((lo[1],hi[1]),int(horizon))
        # Readability is monotone in pi and r0 for each fixed mu.
        low_r=add((lo[0],lo[0]),mul(sub((lo[3],lo[3]),(lo[0],lo[0])),mode))[0]
        high_r=add((hi[0],hi[0]),mul(sub((hi[3],hi[3]),(hi[0],hi[0])),mode))[1]
        readiness=(max(0.,float(low_r)),min(1.,float(high_r)))
        bias=mul((lo[4],hi[4]),power((lo[2],hi[2]),int(horizon)))
        ancestral=positive_product(readiness,unit(mul(add(ONE,bias),HALF)))
        opposite=positive_product(readiness,unit(mul(sub(ONE,bias),HALF)))
        neither=unit(sub(ONE,readiness))
        rows.append([ancestral,opposite,neither])
    return np.asarray(rows,float)
