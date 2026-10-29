"""Frozen predictions and stratum-specific repeatability; no fitting or targets."""
import numpy as np
from scipy.special import expit

from bridge import ROOT, P, read


def predict(boundary, extra, frozen):
    model=frozen['model'];x=np.asarray(boundary,float)
    if extra is not None:x=np.r_[x,float(extra)]
    scale=model['scaling'];z=(x-np.array(scale['mean']))/np.array(scale['scale'])
    if z.shape!=(len(model['coefficients'])-1,) or not np.isfinite(z).all():
        raise ValueError('Frozen predictor input shape/finite mismatch')
    return float(expit(np.r_[1.,z]@np.asarray(model['coefficients'])))


def forecasts(row,regime,arrays):
    models=read(ROOT/'FROZEN_MODELS.json')
    if not np.array_equal(arrays['probes'],np.arange(64)) or not np.array_equal(arrays['direct_probes'],np.r_[0:8,32:40]):
        raise ValueError('Wrong fixed repeat indices')
    q=arrays['successor_passed'][:,0].reshape(2,32).mean(axis=1)
    direct=arrays['direct_passed'][:,0].reshape(2,8).mean(axis=1)
    values=dict(candidate=[predict(row['boundary'],v,models['candidate']) for v in q],
                direct_rival=[predict(row['boundary'],v,models['direct_rival']) for v in direct],
                tt008=[predict(row['boundary'],None,models['tt008'])]*2)
    return dict(key=row['key'],block=row['block'],current_pass=row['current_pass'],regime=regime,
                q_rewrite=q.tolist(),q_direct=direct.tolist(),probabilities=values,
                differences={name:abs(v[1]-v[0]) for name,v in values.items()})


def coverage(selected):
    by={str(c):dict(records=sum(r['current_pass']==c for r in selected),
                       blocks=len({r['block'] for r in selected if r['current_pass']==c})) for c in (0,1)}
    good=all(v['records']>=P['selection']['minimum_records_per_stratum'] and
             v['blocks']>=P['selection']['minimum_blocks_per_stratum'] for v in by.values())
    return dict(passed=good,strata=by)


def analyze(selected,cases,bootstrap=True):
    expected={(tuple(r['key']),regime) for r in selected for regime in P['forcing']['regimes']}
    observed=[(tuple(r['key']),r['regime']) for r in cases]
    if len(observed)!=len(set(observed)) or set(observed)!=expected:
        raise ValueError('Incomplete or duplicate record/regime panel')
    cov=coverage(selected);groups={};precision=True
    random=np.random.default_rng(P['endpoint']['bootstrap_seed']);blocks=np.array(P['acquisition']['blocks'])
    draws=random.choice(blocks,size=(P['endpoint']['bootstrap_replicates'],len(blocks)),replace=True) if bootstrap else []
    for model in ('candidate','direct_rival','tt008'):
        groups[model]={}
        for regime in P['forcing']['regimes']:
            groups[model][regime]={}
            for c in (0,1):
                rows=[r for r in cases if r['regime']==regime and r['current_pass']==c]
                delta=np.array([r['differences'][model] for r in rows]);ids=np.array([r['block'] for r in rows])
                if not len(delta):
                    result=dict(records=0,blocks=0,p90=None,maximum=None,exceedances=0,bootstrap_ci95=None,empty_bootstrap_samples=0)
                else:
                    samples=[];empty=0
                    values={int(b):delta[ids==b] for b in blocks}
                    for draw in draws:
                        sample=np.concatenate([values[int(b)] for b in draw])
                        if len(sample):samples.append(float(np.quantile(sample,.9)))
                        else:empty+=1
                    result=dict(records=len(delta),blocks=len(set(ids)),p90=float(np.quantile(delta,.9)),
                        maximum=float(delta.max()),exceedances=int((delta>.1).sum()),
                        bootstrap_ci95=np.quantile(samples,[.025,.975]).tolist() if samples else None,
                        empty_bootstrap_samples=empty)
                if model=='candidate':precision &= result['p90'] is not None and result['p90']<=P['endpoint']['limit']
                groups[model][regime][str(c)]=result
    decision=('FRESH_PRECISION_COVERAGE_INSUFFICIENT' if not cov['passed'] else
              'FRESH_PRECISION_SCREEN_PASS' if precision else 'FRESH_PRECISION_SCREEN_FAILED')
    return dict(decision=decision,coverage=cov,candidate_precision_pass=bool(precision),groups=groups,
        selected_records=len(selected),acquisition_blocks=len(blocks),new_model_fits=0,new_future_outcomes=0,
        prospective_forecast_confirmation=False,previous_nested_selector_verdict_unchanged=True,
        uncertainty_scope='Descriptive block bootstrap; this small stratified panel supplies no population precision guarantee.',
        automatic_successor=False)


def report(result):
    lines=['# Fixed32 fresh-block precision pilot','', '**'+result['decision']+'**. Fixed coefficients and budget; no long-horizon outcomes.','',
        '| Model | Noise | Current expression | Records | p90 absolute repeat difference | Maximum |',
        '|---|---|---|---:|---:|---:|']
    for model,regimes in result['groups'].items():
        for regime,strata in regimes.items():
            for c,v in strata.items():
                lines.append(f"| {model} | {regime} | {'pass' if c=='1' else 'fail'} | {v['records']} | {v['p90']} | {v['maximum']} |")
    lines+=['','The frozen limit is p90 <= 0.10 in every candidate stratum/regime. Coverage requires at least 24 records from at least 12 blocks per stratum.',
        '','The candidate uses 64 native reads per repeat; retained8 uses eight. Together, both repeats and both regimes cost 288 native reads per selected record, plus independent audits. TT008 repeats hold B fixed and have zero difference by construction.',
        '',result['uncertainty_scope'],'','Fixed32 was chosen using exposed development evidence. Previous failed RDT reductions and the nested-budget selector retain their verdicts. A pass allows pricing a separate prospective outcome test; none starts automatically.','']
    return '\n'.join(lines)
