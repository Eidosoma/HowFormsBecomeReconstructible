"""Separate scalar reduction of complete selected-panel predictions and outcomes."""
import math
import statistics
from scipy.stats import t


def evaluate(rows,forecasts,outcomes,result):
    blocks=sorted({r['block'] for r in rows})
    labels={(tuple(r['key']),r['regime']):r['passed'] for r in outcomes}
    predictions={(tuple(r['key']),r['regime']):r['probabilities'] for r in forecasts}
    expected={(tuple(r['key']),regime) for r in rows for regime in ('matched','independent')}
    if set(labels)!=expected or set(predictions)!=expected or len(outcomes)!=len(expected) or len(forecasts)!=len(expected):
        raise ArithmeticError('Independent audit requires complete unique case panel')
    decisions=[]
    for regime in ('matched','independent'):
        block_scores={m:[] for m in ('candidate','tt008','direct_rival')}
        for block in blocks:
            for model in block_scores:
                means=[]
                for current in (0,1):
                    group=[r for r in rows if r['block']==block and r['current_pass']==current]
                    if not group:raise ArithmeticError('Missing block/class cell')
                    errors=[(predictions[(tuple(r['key']),regime)][model]-labels[(tuple(r['key']),regime)])**2 for r in group]
                    means.append(math.fsum(errors)/len(errors))
                block_scores[model].append(math.fsum(means)/2)
        saved=result['regimes'][regime]
        for model,values in block_scores.items():
            if abs(statistics.mean(values)-saved['scores'][model])>1e-12:
                raise ArithmeticError('Independent weighted Brier mismatch')
        for rival,margin in [('tt008',.002),('direct_rival',0.)]:
            contrasts=[b-a for a,b in zip(block_scores['candidate'],block_scores[rival],strict=True)]
            mean=statistics.mean(contrasts);sd=statistics.stdev(contrasts)
            radius=float(t.ppf(.975,len(blocks)-1))*sd/math.sqrt(len(blocks))
            low,high=mean-radius,mean+radius
            decision='SUPPORTED' if low>margin else 'REJECTED' if high<=margin else 'UNRESOLVED'
            row=saved['primary'][rival]
            for field,value in [('mean_gain',mean),('sample_sd',sd),('lower',low),('upper',high)]:
                if abs(row[field]-value)>1e-12:raise ArithmeticError('Independent block inference mismatch')
            if row['decision']!=decision or row['blocks']!=len(blocks):
                raise ArithmeticError('Independent component decision mismatch')
            decisions.append(decision)
    decision=('PILOT_ALL_FOUR_ADVANTAGES_SUPPORTED' if all(v=='SUPPORTED' for v in decisions)
        else 'PILOT_AT_LEAST_ONE_ADVANTAGE_REJECTED' if 'REJECTED' in decisions else 'PILOT_UNRESOLVED')
    if result['decision']!=decision:raise ArithmeticError('Independent joint decision mismatch')
    return dict(status='PASS',independent_weighted_scores=6,independent_primary_comparisons=4,
                complete_cases=len(expected),block_class_weighting_checked=True)
