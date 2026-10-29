"""Network-level precision and three prospectively fixed timing contrasts."""
import math
from h079 import model as m

ALPHA=0.05
TARGET_HALF_WIDTH=0.10
CONTRASTS=('delayed_minus_on','delayed_minus_off','delayed_eight_minus_one')


def design():
    minimum=math.ceil(math.log(2/ALPHA)/(2*TARGET_HALF_WIDTH**2))
    assert minimum==185 and m.NETWORKS==192 and m.NETWORKS>=minimum
    return dict(independent_unit='network',networks=m.NETWORKS,
        minimum_networks_for_precision=minimum,target_absolute_half_width=TARGET_HALF_WIDTH,
        achieved_absolute_half_width=math.sqrt(math.log(2/ALPHA)/(2*m.NETWORKS)),
        absolute_interval_confidence=1-ALPHA,absolute_range=[0.,1.],
        simultaneous_lower_bound_confidence=1-ALPHA,contrast_family=list(CONTRASTS),
        contrast_range=[-1.,1.],
        simultaneous_contrast_radius=2*math.sqrt(math.log(len(CONTRASTS)/ALPHA)/(2*m.NETWORKS)),
        method='Hoeffding bounded-independent-network inequalities; union bound for the three contrasts',
        absolute_interval_and_contrast_family_joint_coverage_claimed=False,
        sample_size_independent_of_replication_outcomes=True)


def select(rows,**keys):
    found=[r for r in rows if all(r[k]==v for k,v in keys.items())]
    assert len(found)==1,keys
    return found[0]


def bounds(values,low,high,alpha=ALPHA,one_sided=False,family=1):
    assert values and high>low and 0<alpha<1 and family>=1
    assert all(math.isfinite(v) and low<=v<=high for v in values)
    mean=math.fsum(values)/len(values)
    radius=(high-low)*math.sqrt(math.log((1 if one_sided else 2)*family/alpha)/(2*len(values)))
    return dict(networks=len(values),mean=mean,lower=max(low,mean-radius),
        upper=high if one_sided else min(high,mean+radius),radius=radius,
        range=[low,high],confidence=1-alpha,one_sided=one_sided,family_size=family)


def evaluate(blocks,main):
    assert blocks
    if main:assert len(blocks)==m.NETWORKS
    rows=[];seen=set()
    for block in blocks:
        def rate(schedule,method='query_eight'):
            row=select(block['scores'],schedule=schedule,gap=4,scenario='own',method=method)
            assert row['task_total']==m.R==4 and 0<=row['task_correct']<=m.R
            return row['task_correct']/row['task_total'],row['block']
        own,identifier=rate('delayed')
        assert identifier not in seen;seen.add(identifier)
        on,bi=rate('on');off,bj=rate('off');first,bk=rate('delayed','query_one')
        assert bi==bj==bk==identifier
        record=dict(block=identifier,delayed_task_rate=own,
            delayed_minus_on=own-on,delayed_minus_off=own-off,delayed_eight_minus_one=own-first)
        for name in CONTRASTS:
            if name=='delayed_eight_minus_one':
                paired=select(block['effects'],schedule='delayed',gap=4,scenario='own',comparator='query_one')
            else:paired=select(block['schedule_effects'],contrast=name,gap=4,scenario='own',method='query_eight')
            assert paired['block']==identifier and paired['tasks']==m.R
            assert all(0<=paired[k]<=m.R for k in ('task_gains','task_losses'))
            assert (paired['task_gains']-paired['task_losses'])/paired['tasks']==record[name]
        rows.append(record)
    rows.sort(key=lambda r:r['block'])
    assert [r['block'] for r in rows]==list(range(len(rows)))
    absolute=bounds([r['delayed_task_rate'] for r in rows],0.,1.)
    comparisons={name:bounds([r[name] for r in rows],-1.,1.,one_sided=True,family=len(CONTRASTS)) for name in CONTRASTS}
    positive=all(r['lower']>0 for r in comparisons.values())
    return dict(independent_unit='network',networks=len(rows),design=design(),
        absolute_delayed_task_rate=absolute,simultaneous_task_contrasts=comparisons,
        all_three_population_benefits_supported=positive if main else None,
        population_task_rate_at_least_75_supported=absolute['lower']>=.75 if main else None,
        timing_iteration_verdict=('TIMING_AND_ITERATION_BENEFIT_REPLICATED' if positive else
            'NO_QUALIFIED_TIMING_AND_ITERATION_REPLICATION') if main else 'ENGINEERING_OR_SYNTHETIC_ONLY',
        capability_point_gates_remain_separate=True,ordinary_comparator_superiority_qualified=False,
        network_values=rows,inheritance_tested=False,predictors_fitted=0,next_campaign_launched=False)


def synthetic_blocks(n,delayed=4,on=0,off=0,first=0):
    result=[]
    for identifier in range(n):
        scores=[dict(block=identifier,schedule=s,gap=4,scenario='own',method=method,
                     task_correct=value,task_total=4)
                for s,method,value in [('delayed','query_eight',delayed),('on','query_eight',on),
                                       ('off','query_eight',off),('delayed','query_one',first)]]
        def pair(other):
            return dict(block=identifier,gap=4,scenario='own',tasks=4,
                        task_gains=max(delayed-other,0),task_losses=max(other-delayed,0))
        result.append(dict(scores=scores,effects=[dict(pair(first),schedule='delayed',comparator='query_one')],
            schedule_effects=[dict(pair(on),contrast='delayed_minus_on',method='query_eight'),
                              dict(pair(off),contrast='delayed_minus_off',method='query_eight')]))
    return result


def fixtures():
    import copy
    tests=[]
    d=design();assert d['achieved_absolute_half_width']<=.1
    assert math.sqrt(math.log(2/ALPHA)/(2*(d['minimum_networks_for_precision']-1)))>.1
    tests.append('fixed network count meets a bounded-mean precision target without pilot variance assumptions')
    all_good=evaluate(synthetic_blocks(m.NETWORKS),True)
    assert all_good['timing_iteration_verdict']=='TIMING_AND_ITERATION_BENEFIT_REPLICATED'
    assert all_good['absolute_delayed_task_rate']['lower']<1 and all_good['absolute_delayed_task_rate']['upper']==1
    tests.append('positive synthetic effects qualify while all-one samples retain population uncertainty')
    null=evaluate(synthetic_blocks(m.NETWORKS,delayed=0),True)
    assert null['timing_iteration_verdict']=='NO_QUALIFIED_TIMING_AND_ITERATION_REPLICATION'
    assert null['absolute_delayed_task_rate']['upper']>0
    tests.append('zero effects do not qualify and all-zero samples retain population uncertainty')
    partial=evaluate(synthetic_blocks(m.NETWORKS,off=4),True)
    assert not partial['all_three_population_benefits_supported']
    tests.append('one failed comparator contrast prevents the joint timing verdict')
    negative=evaluate(synthetic_blocks(m.NETWORKS,delayed=1,on=4,off=4,first=4),True)
    assert all(r['mean']<0 for r in negative['simultaneous_task_contrasts'].values())
    tests.append('negative effects and losses remain negative')
    fractional=synthetic_blocks(m.NETWORKS,delayed=3)
    frac=evaluate(fractional,True)
    assert frac['absolute_delayed_task_rate']['mean']==.75
    assert not frac['population_task_rate_at_least_75_supported']
    tests.append('a 75 percent point estimate does not imply a 75 percent population lower bound')
    for label,mutate in [('duplicate networks',lambda b:b.__setitem__(1,copy.deepcopy(b[0]))),
                         ('corrupted paired gains',lambda b:b[0]['effects'][0].__setitem__('task_gains',0))]:
        bad=synthetic_blocks(m.NETWORKS);mutate(bad)
        try:evaluate(bad,True)
        except AssertionError:pass
        else:raise AssertionError(label+' accepted')
        tests.append('reject '+label)
    raw=bounds([0.,1.],0.,1.)
    assert raw['networks']==2 and raw['mean']==.5
    one=bounds([0.]*192,-1.,1.,one_sided=True,family=3)
    assert abs(math.exp(-2*192*(one['radius']/2)**2)-ALPHA/3)<1e-15
    tests.append('network denominator and three-comparison tail budget independently satisfy the exponential inequality')
    assert evaluate(synthetic_blocks(1),False)['timing_iteration_verdict']=='ENGINEERING_OR_SYNTHETIC_ONLY'
    tests.append('engineering and synthetic reports cannot issue replication verdicts')
    return dict(passed=True,count=len(tests),tests=tests,design=d)
