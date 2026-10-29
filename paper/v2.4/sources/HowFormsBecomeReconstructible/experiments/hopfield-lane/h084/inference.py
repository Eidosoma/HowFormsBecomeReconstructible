"""One exact network sign test; finite means and conservative mean bounds separate."""
import math
from h079.inference import bounds
from h084 import model as m

ALPHA=.05


def sign_tail(positive,negative):
    assert isinstance(positive,int) and isinstance(negative,int) and positive>=0 and negative>=0
    n=positive+negative
    return sum(math.comb(n,k) for k in range(positive,n+1))/(2**n) if n else 1.


def decide(values,main):
    assert values and all(math.isfinite(v) and -1<=v<=1 for v in values)
    positive=sum(v>0 for v in values);negative=sum(v<0 for v in values);ties=len(values)-positive-negative
    p=sign_tail(positive,negative);mean=math.fsum(values)/len(values)
    lower=bounds(values,-1.,1.,alpha=ALPHA,one_sided=True)
    passed=p<=ALPHA and mean>0
    return dict(networks=len(values),positive_networks=positive,negative_networks=negative,tied_networks=ties,
        discordant_networks=positive+negative,one_sided_exact_sign_p=p,alpha=ALPHA,
        observed_mean_task_difference=mean,population_mean_difference_bound=lower,
        directional_benefit_qualified=passed if main else None,
        population_mean_benefit_qualified=lower['lower']>0 if main else None,
        directional_verdict=('DIRECTIONAL_PAIR_TASK_BENEFIT_REPLICATED' if passed else
            'NO_QUALIFIED_DIRECTIONAL_PAIR_TASK_REPLICATION') if main else 'ENGINEERING_OR_SYNTHETIC_ONLY',
        mean_verdict=('POSITIVE_POPULATION_MEAN_TASK_GAIN_SUPPORTED' if lower['lower']>0 else
            'NO_QUALIFIED_POSITIVE_POPULATION_MEAN_TASK_GAIN') if main else 'ENGINEERING_OR_SYNTHETIC_ONLY',
        sign_null='Pr(network task difference > 0) <= Pr(network task difference < 0)',
        inference_unit='independent network; related births and queries stay nested',
        direction_does_not_qualify_population_mean=True,joint_coverage_claimed=False)


def select(rows,**keys):
    found=[r for r in rows if all(r[k]==v for k,v in keys.items())]
    assert len(found)==1,keys
    return found[0]


def evaluate(blocks,main):
    if main:assert len(blocks)==m.NETWORKS
    network=[]
    for block in blocks:
        ordinary,pair=[select(block['scores'],start='delayed',gap=4,method=method)
            for method in ('ordinary_continuation','pair_continuation')]
        assert ordinary['block']==pair['block'] and ordinary['task_total']==pair['task_total']==4
        effect=select(block['effects'],start='delayed',gap=4,contrast='pair_minus_ordinary')
        assert effect['block']==pair['block'] and effect['tasks']==4
        assert pair['task_correct']-ordinary['task_correct']==effect['task_gains']-effect['task_losses']
        task_rows=[r for r in block['tasks'] if r['start']=='delayed' and r['gap']==4]
        assert len(task_rows)==4 and {r['birth'] for r in task_rows}==set(range(4))
        assert all(r['block']==pair['block'] for r in task_rows)
        for name in ('task_gains','task_losses'):assert sum(r[name] for r in task_rows)==effect[name]
        network.append(dict(block=pair['block'],ordinary_tasks=ordinary['task_correct'],pair_tasks=pair['task_correct'],
            task_gains=effect['task_gains'],task_losses=effect['task_losses'],
            ordinary_task_rate=ordinary['task_correct']/4,pair_task_rate=pair['task_correct']/4,
            task_difference=(pair['task_correct']-ordinary['task_correct'])/4))
    network.sort(key=lambda r:r['block'])
    assert [r['block'] for r in network]==list(range(len(blocks))),'missing or duplicated network'
    result=decide([r['task_difference'] for r in network],main)
    result.update(network_values=network,
        ordinary_task_rate=bounds([r['ordinary_task_rate'] for r in network],0.,1.),
        pair_task_rate=bounds([r['pair_task_rate'] for r in network],0.,1.),
        fixed_confirmation_size=m.NETWORKS,observations_pooled_with_development=False,
        comparative_superiority_qualified=False,capability_qualification=False,
        inherited_transitions=0,next_campaign_launched=False)
    return result
