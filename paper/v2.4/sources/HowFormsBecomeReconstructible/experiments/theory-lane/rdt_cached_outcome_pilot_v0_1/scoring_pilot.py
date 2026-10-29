"""Equal block/class Brier contrasts for the declared selected panel."""
import math
import numpy as np
from scipy.stats import t

MODELS = ('candidate','direct_rival','tt008')
REGIMES = ('matched','independent')
MARGINS = {'tt008':.002,'direct_rival':0.}


def validate(rows,forecasts,outcomes=None):
    keys = [tuple(r['key']) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate cohort record')
    blocks = sorted({r['block'] for r in rows})
    if len(blocks)<2:
        raise ValueError('At least two independent acquisition blocks required')
    if any(not any(r['block']==b and r['current_pass']==c for r in rows) for b in blocks for c in (0,1)):
        raise ValueError('Both expression classes required in every block')
    expected = {(key,regime) for key in keys for regime in REGIMES}
    enrolled = {tuple(r['key']):r for r in rows}
    def index(values,outcome=False):
        mapping = {}
        for row in values:
            key = (tuple(row['key']),row['regime'])
            if key not in expected or key in mapping:
                raise ValueError('Duplicate or undeclared record/regime')
            if outcome:
                if row['passed'] not in (0,1):raise ValueError('Binary native outcome required')
            else:
                original = enrolled[key[0]]
                if any(row[k]!=original[k] for k in ('block','history','current_pass')):
                    raise ValueError('Forecast metadata differs from enrollment')
                if set(row['probabilities']) != set(MODELS) or any(not math.isfinite(v) or not 0<=v<=1 for v in row['probabilities'].values()):
                    raise ValueError('Finite fixed-model probabilities required')
            mapping[key]=row
        if set(mapping)!=expected:raise ValueError('Complete cohort required before inference')
        return mapping
    return blocks,index(forecasts),index(outcomes,True) if outcomes is not None else None


def limits(values,margin):
    x=np.asarray(values,float);n=len(x)
    mean=float(x.mean());sd=float(x.std(ddof=1));radius=float(t.ppf(.975,n-1)*sd/np.sqrt(n))
    lo,hi=mean-radius,mean+radius
    return dict(blocks=n,block_values=x.tolist(),mean_gain=mean,sample_sd=sd,lower=lo,upper=hi,margin=margin,
                decision='SUPPORTED' if lo>margin else 'REJECTED' if hi<=margin else 'UNRESOLVED')


def analyze(rows,forecasts,outcomes):
    blocks,predictions,labels=validate(rows,forecasts,outcomes)
    result=dict(scope='SELECTED_PRECISION_PANEL_PILOT',records=len(rows),blocks=len(blocks),case_regimes=len(outcomes),
                weighting='Equal acquisition block, then equal current-fail/current-pass class within block.',regimes={},new_model_fits=0)
    decisions=[]
    for regime in REGIMES:
        keys=[(tuple(r['key']),regime) for r in rows]
        y=np.array([labels[k]['passed'] for k in keys]);bid=np.array([r['block'] for r in rows]);cls=np.array([r['current_pass'] for r in rows])
        p={m:np.array([predictions[k]['probabilities'][m] for k in keys]) for m in MODELS}
        loss={m:(v-y)**2 for m,v in p.items()}
        weights=np.array([1/(2*sum(q['block']==r['block'] and q['current_pass']==r['current_pass'] for q in rows)) for r in rows])
        score_blocks={m:[float(np.sum(weights[bid==b]*v[bid==b])) for b in blocks] for m,v in loss.items()}
        comparisons={m:limits(np.array(score_blocks[m])-score_blocks['candidate'],margin) for m,margin in MARGINS.items()}
        decisions.extend(v['decision'] for v in comparisons.values())
        calibration={}
        for m,values in p.items():
            bins=np.minimum((values*10).astype(int),9);calibration[m]=[]
            for index in range(10):
                mask=bins==index;weight=float(weights[mask].sum());n=int(mask.sum())
                calibration[m].append(dict(bin=index,records=n,panel_mass=weight/len(blocks),
                    mean_prediction=float(np.sum(weights[mask]*values[mask])/weight) if weight else None,
                    observed_fraction=float(np.sum(weights[mask]*y[mask])/weight) if weight else None))
        strata={}
        for c in (0,1):
            selected=cls==c
            strata[str(c)]=dict(records=int(selected.sum()),blocks=len(blocks),
                scores={m:float(np.mean([v[(bid==b)&selected].mean() for b in blocks])) for m,v in loss.items()})
        result['regimes'][regime]=dict(scores={m:float(np.mean(v)) for m,v in score_blocks.items()},
            score_blocks=score_blocks,primary=comparisons,calibration=calibration,current_expression=strata)
    result['decision']=('PILOT_ALL_FOUR_ADVANTAGES_SUPPORTED' if all(v=='SUPPORTED' for v in decisions)
        else 'PILOT_AT_LEAST_ONE_ADVANTAGE_REJECTED' if 'REJECTED' in decisions else 'PILOT_UNRESOLVED')
    result['interpretation']='Selected-panel outcome pilot with limited power; no inference to all 64 records per acquisition block, no completed 304-block test, and no RDT-specific law established.'
    return result


def report(result):
    lines=['# Cached precision-panel continuation pilot','', '**'+result['decision']+'**. '+result['interpretation'],'',
        '| Noise | Comparator | Brier gain | Lower limit | Upper limit | Required margin | Decision |',
        '|---|---|---:|---:|---:|---:|---|']
    for regime,value in result['regimes'].items():
        for rival,item in value['primary'].items():
            lines.append(f"| {regime} | {rival} | {item['mean_gain']:.8f} | {item['lower']:.8f} | {item['upper']:.8f} | {item['margin']:.3f} | {item['decision']} |")
    lines+=['',f"Complete selected panel: {result['records']} records, {result['blocks']} acquisition blocks, {result['case_regimes']} record/regime outcomes.",'',
        'Each block receives equal weight, with equal weight for its currently failing and passing strata. All first-repeat forecasts were sealed before these outcomes. Fixed coefficients, 18 full rewrites and a fresh terminal recipient; no refitting, replacement, cohort extension or partial-score decision.', '']
    return '\n'.join(lines)
