"""Excluded mathematical checks; no development-panel results are computed."""
import copy
from fractions import Fraction as F
import itertools
import json
import math
import time

import numpy as np
from scipy.stats import binomtest
import auditor
import engine
import exact
import intervals as iv
import oracle as o
import support as s
import two_mode


def fails(call):
    try:call()
    except (ValueError,AssertionError):return
    raise AssertionError('Corrupted certificate was accepted')


def run():
    began=time.monotonic();passed=[]
    for n in (1,2,7,16):
        for k in range(-1,n+1):
            for p in (0.,.125,.5,.875,1.):
                a,b=p.as_integer_ratio()
                direct=sum(F(math.comb(n,j)*a**j*(b-a)**(n-j),b**n) for j in range(max(0,k+1)))
                assert F(exact.cdf_numerator(n,k,a,b),b**n)==direct
                assert F(o.cdf_direct(n,k,a,b),b**n)==direct
    passed.append('Binomial recurrence and independent Horner polynomial equal direct rational sums')
    for family in (1,16):
        for n in (1,16,64,1024):
            for k in sorted(set([0,1,n//2,n-1,n])):
                record=exact.cp(k,n,20*2*27*family);o.check_cp(record)
                reference=binomtest(k,n).proportion_ci(confidence_level=1-1/(20*27*family),method='exact')
                assert max(abs(record['lower']-reference.low),abs(record['upper']-reference.high))<2e-11
    passed.append('Exact outward CP brackets, endpoints and primary SciPy comparison')
    n=8;den=40;records=[exact.cp(k,n,den) for k in range(n+1)]
    for j in range(33):
        p=F(j,32);coverage=sum(F(math.comb(n,k))*p**k*(1-p)**(n-k) for k,r in enumerate(records) if o.q(r['lower'])<=p<=o.q(r['upper']))
        assert coverage>=1-F(2,den)
    passed.append('Enumerated small-binomial coverage obeys exact allocated tail bound')
    generator=s.random('TT006','excluded_arithmetic_checks')
    points=[list(p) for p in itertools.product(*[(0.,1.)]*4,[(-1.,1.)][0])]
    points += [list(x[:4])+[2*x[4]-1] for x in generator.random((12,5))]
    for theta in points:
        rational=o.probabilities(theta);bounds=iv.pattern_bounds(theta,theta)
        assert sum(rational)==1
        assert all(o.enclosed(b,(p,p)) for b,p in zip(bounds,rational,strict=True))
        assert np.allclose(two_mode.pattern_probabilities(theta),np.array(rational,float),atol=2e-15,rtol=2e-14)
        forecasts=iv.forecast_bounds(theta,theta);truth=o.forecasts(theta,s.PLAN['horizons'])
        assert all(o.enclosed(forecasts[h,c],(truth[h][c],truth[h][c])) for h,c in itertools.product(range(2),range(3)))
        inverse=theta.copy();inverse[4]*=-1;p=two_mode.pattern_probabilities(inverse)
        indices=[sum((1-int(c) if c!=2 else 2)*3**(2-t) for t,c in enumerate(pattern)) for pattern in s.PATTERNS]
        assert np.allclose(p,np.array(rational,float)[indices],atol=2e-15,rtol=2e-14)
    passed.append('Full HMM, independent 64 hidden paths, factorization and identity inversion agree')
    for _ in range(16):
        ends=np.sort(generator.integers(0,17,size=(2,5))/16,axis=0);ends[:,4]=2*ends[:,4]-1
        lower,upper=ends;bounds=iv.pattern_bounds(lower,upper)
        assert all(o.enclosed(bounds[i],o.pattern_interval(lower,upper,pattern)) for i,pattern in enumerate(s.PATTERNS))
        forecast=iv.forecast_bounds(lower,upper);truth=o.forecast_intervals(lower,upper,s.PLAN['horizons'])
        assert all(o.enclosed(forecast[h,c],truth[h][c]) for h,c in itertools.product(range(2),range(3)))
        enumerated=[o.forecasts(theta,s.PLAN['horizons']) for theta in itertools.product(*zip(lower,upper,strict=True))]
        for h,c in itertools.product(range(2),range(3)):
            values=[point[h][c] for point in enumerated]
            assert truth[h][c]==(min(values),max(values))
    passed.append('Continuous-box probability enclosures and forecast corner extrema pass rational checks')
    a=np.zeros(27,int);a[0]=16
    root,arrays=engine.solve(a,maximum_splits=0);auditor.region(root,arrays)
    assert root['retained_leaves']==1 and root['feasibility']=='WITNESS_PROVEN'
    assert np.array_equal(root['outer_bounds'],np.tile([0.,1.],(2,3,1)))
    refined,tree=engine.solve(a,maximum_splits=31);auditor.region(refined,tree)
    assert refined['splits']<=31 and refined['retained_leaves']>0
    assert np.all(np.asarray(refined['outer_bounds'])[:,:,0]>=np.asarray(root['outer_bounds'])[:,:,0])
    assert np.all(np.asarray(refined['outer_bounds'])[:,:,1]<=np.asarray(root['outer_bounds'])[:,:,1])
    passed.append('Zero-budget and interrupted searches retain a complete conservative domain cover')
    b=np.zeros(27,int);b[3]=128;b[10]=128
    rejected,empty=engine.solve(b,maximum_splits=31);auditor.region(rejected,empty)
    assert rejected['feasibility']=='CERTIFIED_EMPTY' and rejected['outer_bounds'] is None
    passed.append('Constructed alternating histories are certifiably incompatible, not forced to fit')
    broken={key:value.copy() for key,value in tree.items()};broken['lower'][1,0]=.123
    fails(lambda:auditor.region(refined,broken))
    broken={key:value.copy() for key,value in arrays.items()};broken['forecast'][0,1,0,1]=0
    fails(lambda:auditor.region(root,broken))
    broken=copy.deepcopy(root);broken['cp_records'][0]['lower']=.5
    fails(lambda:auditor.region(broken,arrays))
    broken=copy.deepcopy(root);broken['witnesses']['points'].append([0,0,0,0,0])
    fails(lambda:auditor.region(broken,arrays))
    broken={key:value.copy() for key,value in empty.items()};broken['rejection_interval'][0]=[0,1]
    fails(lambda:auditor.region(rejected,broken))
    passed.append('Audit rejects missing domain, false forecast bound, CP, witness and rejection certificates')
    return dict(status='PASS',checks=len(passed),passed=passed,seconds=time.monotonic()-began,classification='TECHNICAL_EXCLUSION')


if __name__=='__main__':print(json.dumps(run(),indent=2))
