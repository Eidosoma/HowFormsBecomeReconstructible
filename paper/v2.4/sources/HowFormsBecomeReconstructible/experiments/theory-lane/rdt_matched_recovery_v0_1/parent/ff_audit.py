"""Independent scalar reduction; no imports of selection/scoring implementations."""
import math
import statistics
from scipy.stats import t


def near(a,b):
    if abs(a-b)>1e-12:
        raise ArithmeticError(f'Independent scalar calculation differs: {a} vs {b}')


def evaluate(rows,forecasts,outcomes,result,repeats):
    blocks=sorted(set(r['block'] for r in rows)); flags=[]; checks=0
    for regime in ('matched','independent'):
        reductions={m:[] for m in ('successor32','direct64','pooled32','direct8','tt008')}
        for b in blocks:
            classes={m:[] for m in reductions}
            for c in (0,1):
                group=[r for r in rows if r['block']==b and r['current_pass']==c]
                if not 1<=len(group)<=2:raise ArithmeticError('Wrong class size')
                packet_losses={m:[] for m in reductions}
                for r in group:
                    f=[v for v in forecasts if v['key']==r['key'] and v['regime']==regime]
                    if len(f)!=1:raise ArithmeticError('Forecast completeness')
                    ys=[]
                    for rep in repeats:
                        labels=[y for y in outcomes if y['key']==r['key'] and y['regime']==regime and y['replicate']==rep]
                        if len(labels)!=1:raise ArithmeticError('Outcome completeness')
                        ys.append(labels[0]['passed'])
                    for m in reductions:
                        p=f[0]['probabilities'][m]
                        packet_losses[m].append(math.fsum((p-y)*(p-y) for y in ys)/len(ys))
                for m in reductions:classes[m].append(statistics.mean(packet_losses[m]))
            for m in reductions:reductions[m].append(statistics.mean(classes[m]))
        for m in reductions:near(statistics.mean(reductions[m]),result['regimes'][regime]['brier'][m])
        for rival,margin in [('direct64',0.),('pooled32',0.),('direct8',0.),('tt008',.002)]:
            values=[x-y for x,y in zip(reductions[rival],reductions['successor32'],strict=True)]
            mean=statistics.mean(values);sd=statistics.stdev(values)
            radius=float(t.ppf(.975,len(blocks)-1))*sd/math.sqrt(len(blocks))
            lo,hi=mean-radius,mean+radius
            flag='SUPPORTED' if lo>margin else 'REJECTED' if hi<=margin else 'UNRESOLVED'
            a=result['regimes'][regime]['contrasts'][rival]
            for name,v in [('mean_gain',mean),('sample_sd',sd),('lower',lo),('upper',hi)]:near(a[name],v)
            for x,y in zip(values,a['block_gains'],strict=True):near(x,y)
            if a['decision']!=flag or a['blocks']!=len(blocks):raise ArithmeticError('Wrong primary verdict')
            for field in ('history','current_pass'):
                near(math.fsum(x['gain_mass'][rival] for x in result['regimes'][regime]['strata'][field].values()),mean)
            if rival in ('direct64','pooled32'):flags.append(flag)
            checks+=1
        for m in reductions:
            bins=result['regimes'][regime]['calibration'][m]
            near(math.fsum(b['weight'] for b in bins),1.)
            near(math.fsum(b['weight']*b['brier'] for b in bins if b['weight']),statistics.mean(reductions[m]))
    decision=('ALL_FOUR_EQUAL_READ_ADVANTAGES_SUPPORTED' if all(f=='SUPPORTED' for f in flags)
        else 'AT_LEAST_ONE_ADVANTAGE_REJECTED' if 'REJECTED' in flags else 'UNRESOLVED')
    if result['decision']!=decision:raise ArithmeticError('Wrong joint verdict')
    return dict(status='PASS',independent_scalar_contrasts=checks,blocks=len(blocks),
                individual_repeated_losses_checked=True,diagnostic_mass_checks=True)
