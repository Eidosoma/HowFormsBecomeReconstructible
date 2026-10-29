"""Frozen block-level claims and explicit pointwise conditional uncertainty."""
from functools import lru_cache
import math
from scipy.stats import t,beta
import design

def interval(values,alpha=design.ALPHA):
    values=list(values);n=len(values)
    assert n>=2 and all(math.isfinite(v) and -1<=v<=1 for v in values)
    mean=math.fsum(values)/n;variance=math.fsum((x-mean)**2 for x in values)/(n-1);se=math.sqrt(variance/n)
    bounded=math.sqrt(2*math.log(1/alpha)/n)
    radius=float(t.ppf(1-alpha,n-1))*se if se else bounded
    r95=float(t.ppf(.975,n-1))*se if se else math.sqrt(2*math.log(40)/n)
    clip=lambda x:max(-1.,min(1.,x))
    return dict(n=n,mean=mean,standard_error=se,lower_one_sided=clip(mean-radius),alpha=alpha,
        pointwise_two_sided_95=[clip(mean-r95),clip(mean+r95)],hoeffding_lower_sensitivity=clip(mean-bounded),
        method='approximate paired block Student-t' if se else 'bounded Hoeffding zero-variance fallback')
def results(summary):
    assert summary['role']=='confirmation' and len(summary['blocks'])==64
    claims={}
    for name,spec in design.claims().items():
        data=summary['panel'][spec['family']][spec['damage']][spec['body']][spec['arm']][spec['endpoint']]['overall']
        assert set(data['blocks'])=={str(i) for i in summary['blocks']}
        ci=interval(data['blocks'].values())
        assert abs(ci['mean']-data['effect'])<2e-15
        claims[name]=dict(**spec,interval=ci,classification='PRACTICAL_SUPERIORITY_PASS' if ci['lower_one_sided']>spec['margin'] else 'NOT_CONFIRMED')
    joint=all(claims[n]['classification']=='PRACTICAL_SUPERIORITY_PASS' for n in ('partial_correction','partial_body_specificity'))
    return dict(claims=claims,primary_classification=claims[design.PRIMARY]['classification'],
        joint_classification='CONFIRMED_CONDITIONAL_MESSAGE_SPECIFIC_CORRECTION' if joint else 'NOT_CONFIRMED',
        family_alpha=.05,per_claim_alpha=design.ALPHA,approximate_coverage=True,
        secondary_results_cannot_rescue_primary=True,population_units=64,automatic_extension=False)
@lru_cache(None)
def binomial_interval(k,n):
    assert type(k) is int and type(n) is int and 0<=k<=n and n>0
    return [0. if k==0 else float(beta.ppf(.025,k,n-k+1)),1. if k==n else float(beta.ppf(.975,k+1,n-k))]
def conditional(rows):
    n=len(rows);radius=math.sqrt(math.log(40)/(2*n));delta_radius=2*radius
    mean=lambda name:math.fsum(r[name] for r in rows)/n
    bounded=lambda m,r,lo,hi:[max(lo,m-r),min(hi,m+r)]
    return dict(level=.95,simultaneous=False,independent_receiving_draws=n,
        incoming_credit=bounded(mean('incoming'),radius,0.,1.),outgoing_credit=bounded(mean('outgoing'),radius,0.,1.),
        paired_credit_change=bounded(mean('effect'),delta_radius,-1.,1.),
        gain_probability=binomial_interval(sum(r['effect']>0 for r in rows),n),
        harm_probability=binomial_interval(sum(r['effect']<0 for r in rows),n),
        credit_method='bounded Hoeffding; paired changes use range [-1,1]',
        event_method='equal-tailed Clopper-Pearson for binary gain/harm indicators',
        scope='conditional on this fixed output packet, body/repair and corruption; excludes source-population uncertainty')
