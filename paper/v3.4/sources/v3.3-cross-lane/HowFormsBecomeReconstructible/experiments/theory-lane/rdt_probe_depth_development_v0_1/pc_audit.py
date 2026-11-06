"""Independent scalar replay of saved model probabilities and individual Brier."""
from pc_common import *
import math


def scalar(values,model):
    base,cal=model['base'],model['calibration']
    eta=math.fsum([base['coefficients'][0]]+[(float(x)-mu)/sd*b for x,mu,sd,b in
        zip(values,base['mean'],base['scale'],base['coefficients'][1:],strict=True)])
    z=cal['intercept']+cal['slope']*eta
    return 1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))


def audit_run(run):
    run=Path(run);folder=run/'fitting';schema=read(ROOT/'prepared/SCHEMA.json');cases=read(ROOT/'prepared/CASES.json')
    data=load_arrays(folder/'SCORING.npz',sha(folder/'SCORING.npz'))
    names=read(folder/'SCORING_SCHEMA.json')['models']
    x=np.column_stack((data['cheap'],data['q']));models=read(folder/'OUTER_MODELS.json')
    count=0
    for j,family in enumerate(FAMILIES):
        require(names[j]==family,'New model order')
        for i,c in enumerate(cases):
            model=models[family][str(c['fold'])]
            require(c['block'] not in model['training_source_blocks'] and c['fold'] not in model['training_folds'],
                    'Held source in training')
            require(model['training_source_blocks']==[b for b in range(80) if b%8!=c['fold']], 'Full grouped exclusions')
            positions=[schema['all_columns'].index(n) for n in model['columns']]
            require(abs(scalar(x[i,positions],model)-data['probability'][i,j])<1e-12,'Independent stored-model probability')
            count+=1
    summaries=csv_rows(run/'analysis/summary.csv');checked=0
    for row in summaries:
        j=names.index(row['model']);wi=PROFILES.index(row['profile']);ri=REGIMES.index(row['regime'])
        selected=[i for i,c in enumerate(cases) if REGIMES.index(c['regime'])==ri and data['weights'][i,wi]>0]
        denominator=math.fsum(float(data['weights'][i,wi]) for i in selected)*4
        num=math.fsum(float(data['weights'][i,wi])*(float(data['probability'][i,j])-int(y))**2
                      for i in selected for y in data['y'][i])
        require(abs(num/denominator-float(row['brier']))<1e-12,'Scalar individual-future Brier')
        prev=math.fsum(float(data['weights'][i,wi])*int(y) for i in selected for y in data['y'][i])/denominator
        require(abs(prev-float(row['terminal_success']))<1e-12,'Scalar terminal prevalence')
        checked+=1
    result=dict(status='PASS',utc=utc(),held_probability_replays=count,absolute_score_groups=checked,
        source_blocks=80,individual_futures=2552,new_native_reads=0,
        audit_code_sha256=sha(Path(__file__)),scope='Saved model predictions and absolute scores; bootstrap intervals are constructed by the separately tested whole-block scorer.')
    write(run/'SAVED_EVIDENCE_AUDIT.json',result)
    return result
