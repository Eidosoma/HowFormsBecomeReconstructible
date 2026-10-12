"""Exact dyadic binomial tail checks and outward Clopper--Pearson brackets."""
from fractions import Fraction
from functools import lru_cache
import math

import numpy as np
from scipy.stats import beta


def cdf_numerator(n,k,a,b):
    """P(Bin(n,a/b)<=k) times b**n, with exact integer arithmetic."""
    if not 0<=a<=b or b<=0 or n<0:raise ValueError('Invalid binomial input')
    if k<0:return 0
    if k>=n:return b**n
    if a==0:return b**n
    if a==b:return 0
    if k>n//2:return b**n-cdf_numerator(n,n-k-1,b-a,b)
    term=(b-a)**n;total=term
    for j in range(k):
        numerator=term*(n-j)*a;denominator=(j+1)*(b-a)
        term,remainder=divmod(numerator,denominator)
        if remainder:raise ArithmeticError('Binomial term recursion lost integrality')
        total+=term
    return total


def tail_compare(n,k,p,denominator,upper_tail):
    """Compare an exact binomial tail at dyadic p with 1/denominator."""
    a,b=float(p).as_integer_ratio();total=b**n
    value=total-cdf_numerator(n,k-1,a,b) if upper_tail else cdf_numerator(n,k,a,b)
    difference=value*denominator-total
    return (difference>0)-(difference<0)


@lru_cache(None)
def cp(k,n,tail_denominator):
    if not isinstance(k,int) or not isinstance(n,int) or not 0<=k<=n or n<1 or tail_denominator<=2:
        raise ValueError('Invalid confidence interval input')
    alpha=1./tail_denominator
    if k==0:lower=0.;lower_neighbor=0.
    else:
        lower=float(beta.ppf(alpha,k,n-k+1))
        for _ in range(4096):
            nxt=float(np.nextafter(lower,1.))
            if tail_compare(n,k,lower,tail_denominator,True)>0:lower=float(np.nextafter(lower,0.));continue
            if tail_compare(n,k,nxt,tail_denominator,True)<0:lower=nxt;continue
            lower_neighbor=nxt;break
        else:raise ArithmeticError('Could not certify lower quantile bracket')
    if k==n:upper=1.;upper_neighbor=1.
    else:
        upper=float(beta.isf(alpha,k+1,n-k))
        for _ in range(4096):
            prev=float(np.nextafter(upper,0.))
            if tail_compare(n,k,upper,tail_denominator,False)>0:upper=float(np.nextafter(upper,1.));continue
            if tail_compare(n,k,prev,tail_denominator,False)<0:upper=prev;continue
            upper_neighbor=prev;break
        else:raise ArithmeticError('Could not certify upper quantile bracket')
    return dict(k=k,n=n,tail_denominator=tail_denominator,lower=lower,upper=upper,
        lower_inside_neighbor=lower_neighbor,upper_inside_neighbor=upper_neighbor)


def intervals(counts,family=1):
    c=np.asarray(counts)
    if c.shape!=(27,) or not np.issubdtype(c.dtype,np.integer) or (c<0).any() or c.sum()<=0:raise ValueError('27 integer counts required')
    denominator=20*2*27*int(family)
    records=[cp(int(k),int(c.sum()),denominator) for k in c]
    return np.array([[r['lower'],r['upper']] for r in records]),records
