"""Four frozen directional population claims; repeated futures stay within blocks."""
import math
from scipy.stats import t
from common import *


def interval(values, bound):
    x=list(map(float,values));n=len(x)
    assert n>=2 and bound in (1,2) and all(math.isfinite(v) and -bound<=v<=bound for v in x)
    mean=math.fsum(x)/n;variance=math.fsum((v-mean)**2 for v in x)/(n-1);se=math.sqrt(variance/n)
    conservative=bound*math.sqrt(2*math.log(1/ALPHA)/n)
    radius=float(t.ppf(1-ALPHA,n-1))*se if se else conservative
    r95=float(t.ppf(.975,n-1))*se if se else bound*math.sqrt(2*math.log(40)/n)
    clip=lambda v:max(-bound,min(bound,v))
    return dict(n=n,mean=mean,standard_error=se,lower_one_sided=clip(mean-radius),alpha=ALPHA,
        pointwise_two_sided_95=[clip(mean-r95),clip(mean+r95)],hoeffding_lower_sensitivity=clip(mean-conservative),
        range=[-bound,bound],method='approximate paired block Student-t' if se else 'bounded Hoeffding zero-variance fallback')


def decide(values):
    assert set(values)=={'full_900','full_1000','full_minus_intact_900','full_minus_intact_1000'}
    result={}
    for k,v in values.items():
        assert len(v)==32
        ci=interval(v,2 if 'minus_intact' in k else 1)
        result[k]=dict(interval=ci,block_values=list(map(float,v)),margin=0.,
            classification='DIRECTIONAL_SUPERIORITY_PASS' if ci['lower_one_sided']>0 else 'NOT_CONFIRMED')
    passed=all(x['classification']=='DIRECTIONAL_SUPERIORITY_PASS' for x in result.values())
    return dict(status='CONFIRMED_JOINT_DAMAGE_DEPENDENT_PACKET_BENEFIT' if passed else 'NOT_CONFIRMED',
        endpoints=result,population_units=32,family_alpha=.05,per_endpoint_alpha=ALPHA,
        multiplicity='Bonferroni across four co-primary endpoints',approximate_coverage=True,
        secondary_results_cannot_rescue_primary=True,automatic_extension=False)


def results(summary):
    full=INDEX['mix100|residual|all|all_masks|own'];intact=INDEX['mix000|residual|all|all_masks|own'];values={}
    for time,ti in ((900,4),(1000,5)):
        a=summary['block_effects'][:,full,1,ti,0];b=summary['block_effects'][:,intact,1,ti,0]
        values[f'full_{time}']=a;values[f'full_minus_intact_{time}']=a-b
    return decide(values)
