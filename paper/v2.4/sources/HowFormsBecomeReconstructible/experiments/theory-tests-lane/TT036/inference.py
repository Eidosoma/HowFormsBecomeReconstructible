"""Frozen block-level claims and explicit pointwise conditional uncertainty."""
from functools import lru_cache
import math
from scipy.stats import t,beta
from common import ALPHA,INDEX,BLOCKS,near

def interval(values,alpha=ALPHA):
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
    j=INDEX['residual|all|all_masks|own'];endpoints={}
    for endpoint in ('body','recipient'):
        values=summary[endpoint+'_stats_block_means'][:,j,1,0]
        assert len(values)==len(BLOCKS)==64
        ci=interval(values);near(ci['mean'],summary[endpoint+'_stats_equal_block'][j,1,0])
        endpoints[endpoint]=dict(interval=ci,margin=0.,classification='DIRECTIONAL_SUPERIORITY_PASS' if ci['lower_one_sided']>0 else 'NOT_CONFIRMED')
    joint=all(v['classification']=='DIRECTIONAL_SUPERIORITY_PASS' for v in endpoints.values())
    return dict(endpoints=endpoints,joint_classification='CONFIRMED_JOINT_STOPPING_BENEFIT' if joint else 'NOT_CONFIRMED',
        comparison='100_minus_1000',condition='residual|all|all_masks|own',credit='target',family_alpha=.05,
        per_endpoint_alpha=ALPHA,multiplicity='Bonferroni across two co-primary endpoints',approximate_coverage=True,
        population_units=64,secondary_results_cannot_rescue_primary=True,automatic_extension=False)
