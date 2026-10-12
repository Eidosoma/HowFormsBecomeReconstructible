"""Independent rational arithmetic used to audit stored floating certificates."""
from fractions import Fraction as F
from functools import lru_cache
import itertools
import math


@lru_cache(16384)
def q(value):return F(float(value))
def plus(a,b):return a[0]+b[0],a[1]+b[1]
def minus(a,b):return a[0]-b[1],a[1]-b[0]
def times(a,b):
    corners=[x*y for x in a for y in b]
    return min(corners),max(corners)
ONE=(F(1),F(1))
HALF=(F(1,2),F(1,2))


def pattern_interval(lower,upper,pattern):
    """Rational interval extension; no calls to the float implementation."""
    pi,mu,lam,r,chi=[(q(a),q(b)) for a,b in zip(lower,upper,strict=True)]
    recovery=times(pi,minus(ONE,mu));loss=times(minus(ONE,pi),minus(ONE,mu))
    transition=[[minus(ONE,recovery),recovery],[loss,minus(ONE,loss)]]
    ready=[int(c!=2) for c in pattern]
    result=r if ready[0] else minus(ONE,r)
    for t in (0,1):result=times(result,transition[ready[t]][ready[t+1]])
    observed=[t for t,c in enumerate(pattern) if c!=2]
    if not observed:return result
    first=observed[0];sign=(F(1),F(1)) if pattern[first]==0 else (F(-1),F(-1))
    bias=times(chi,(lam[0]**first,lam[1]**first))
    result=times(result,times(plus(ONE,times(sign,bias)),HALF))
    for a,b in zip(observed,observed[1:]):
        gap=b-a;mode=(lam[0]**gap,lam[1]**gap)
        term=plus(ONE,mode) if pattern[a]==pattern[b] else minus(ONE,mode)
        result=times(result,times(term,HALF))
    return result


def probabilities(theta):
    """Enumerate hidden identity paths independently of the factorized formula."""
    pi,mu,lam,r,chi=map(q,theta)
    loss=(1-pi)*(1-mu);recovery=pi*(1-mu)
    rt=((1-recovery,recovery),(loss,1-loss))
    flip=(1-lam)/2;it=((1-flip,flip),(flip,1-flip))
    result=[F(0)]*27
    for states in itertools.product(range(4),repeat=3):
        identities=[s//2 for s in states];readiness=[s%2 for s in states]
        weight=((1+chi)/2 if identities[0]==0 else (1-chi)/2)*(r if readiness[0] else 1-r)
        for t in (0,1):weight*=it[identities[t]][identities[t+1]]*rt[readiness[t]][readiness[t+1]]
        emitted=[i if z else 2 for i,z in zip(identities,readiness,strict=True)]
        code=9*emitted[0]+3*emitted[1]+emitted[2]
        result[code]+=weight
    return result


def forecasts(theta,horizons):
    pi,mu,lam,r,chi=map(q,theta)
    result=[]
    for h in horizons:
        ready=pi+(r-pi)*mu**h;bias=chi*lam**h
        result.append([ready*(1+bias)/2,ready*(1-bias)/2,1-ready])
    return result


@lru_cache(8192)
def readiness_extrema(pi0,pi1,mu0,mu1,r0,r1,h):
    corners=itertools.product((q(pi0),q(pi1)),(q(mu0),q(mu1)),(q(r0),q(r1)))
    values=[pi+(r-pi)*mu**h for pi,mu,r in corners]
    return min(values),max(values)


@lru_cache(8192)
def bias_extrema(lam0,lam1,chi0,chi1,h):
    values=[chi*lam**h for chi,lam in itertools.product((q(chi0),q(chi1)),(q(lam0),q(lam1)))]
    return min(values),max(values)


def forecast_intervals(lower,upper,horizons):
    result=[]
    for h in horizons:
        rmin,rmax=readiness_extrema(lower[0],upper[0],lower[1],upper[1],lower[3],upper[3],h)
        bmin,bmax=bias_extrema(lower[2],upper[2],lower[4],upper[4],h)
        # All factors are nonnegative, and the two parameter groups are disjoint.
        result.append([(rmin*(1+bmin)/2,rmax*(1+bmax)/2),
            (rmin*(1-bmax)/2,rmax*(1-bmin)/2),(1-rmax,1-rmin)])
    return result


@lru_cache(None)
def cdf_direct(n,k,a,b):
    """Exact homogeneous-polynomial Horner evaluation, with integer coefficients.

    Does not share the production binomial-term recurrence or use SciPy.
    """
    if k<0:return 0
    if k>=n:return b**n
    if a==0:return b**n
    if a==b:return 0
    if k>n//2:return b**n-cdf_direct(n,n-k-1,b-a,b)
    complement=b-a;value=math.comb(n,k);power=1
    for j in range(k-1,-1,-1):
        power*=complement
        value=value*a+math.comb(n,j)*power
    return value*complement**(n-k)


def tail_sign(n,k,p,denominator,upper):
    a,b=float(p).as_integer_ratio();total=b**n
    tail=total-cdf_direct(n,k-1,a,b) if upper else cdf_direct(n,k,a,b)
    diff=tail*denominator-total
    return (diff>0)-(diff<0)


@lru_cache(None)
def check_cp_tuple(k,n,den,lower,upper,lower_neighbor,upper_neighbor):
    if not 0<=lower<=upper<=1:raise ValueError('Invalid CP interval')
    if k:
        if not lower<lower_neighbor or math.nextafter(lower,1.)!=lower_neighbor:raise ValueError('Lower neighbors invalid')
        if tail_sign(n,k,lower,den,True)>0 or tail_sign(n,k,lower_neighbor,den,True)<0:raise ValueError('Lower exact root not bracketed')
    elif lower!=0:raise ValueError('Zero-count lower endpoint changed')
    if k<n:
        if not upper_neighbor<upper or math.nextafter(upper,0.)!=upper_neighbor:raise ValueError('Upper neighbors invalid')
        if tail_sign(n,k,upper,den,False)>0 or tail_sign(n,k,upper_neighbor,den,False)<0:raise ValueError('Upper exact root not bracketed')
    elif upper!=1:raise ValueError('Full-count upper endpoint changed')
    return True


def check_cp(record):
    return check_cp_tuple(*(record[key] for key in ('k','n','tail_denominator','lower','upper','lower_inside_neighbor','upper_inside_neighbor')))


def enclosed(bounds,exact):
    return q(bounds[0])<=exact[0]<=exact[1]<=q(bounds[1])
