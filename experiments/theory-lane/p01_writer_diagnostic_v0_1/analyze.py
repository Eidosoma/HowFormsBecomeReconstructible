"""Descriptive block summaries and fixed leave-one-block-out comparisons."""
import argparse
import csv
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from extract import ROOT, sha, stamp, write_json


def load_rows(path):
    with Path(path).open(newline='') as f:
        result=[]
        for row in csv.DictReader(f):
            result.append({k:(v if k in ('pairing','source_writer') else float(v) if v else None) for k,v in row.items()})
    return result


def design(rows, augmented):
    columns=['current_margin','current_pass','generation_fraction','tolerance_writer',
             'noise_0999','noise_0','reset_099']
    values=[]
    for r in rows:
        values.append([r['current_margin'],r['current_pass'],r['generation']/32,
                       float(r['source_writer']=='tolerance_rewrite'),
                       *[float(r['pairing']==p) for p in ('noise_0999','noise_0','reset_099')]])
    x=np.asarray(values)
    if augmented:
        added=['actual_signed_transfer','actual_unsigned_access','actual_conflict_mass','body_contrast_alignment']
        x=np.column_stack([x,*[[r[k] for r in rows] for k in added]])
        columns+=added
    return x,columns


def fit_predict(x,y,train,test,ridge):
    mean=x[train].mean(axis=0);scale=x[train].std(axis=0)
    scale=np.where(scale>1e-12,scale,1.)
    a=np.column_stack([np.ones(train.sum()),(x[train]-mean)/scale])
    b=np.column_stack([np.ones(test.sum()),(x[test]-mean)/scale])
    target=y[train]
    def objective(w):
        z=a@w
        loss=float(np.mean(np.logaddexp(0,z)-target*z)+ridge*.5*np.sum(w[1:]**2))
        gradient=a.T@(expit(z)-target)/len(target)
        gradient[1:]+=ridge*w[1:]
        return loss,gradient
    fit=minimize(objective,np.zeros(a.shape[1]),jac=True,method='L-BFGS-B',
                 options=dict(maxiter=500,ftol=1e-12,gtol=1e-7))
    if not fit.success:
        raise RuntimeError(str(fit.message))
    logits=b@fit.x
    return expit(logits),logits,dict(success=bool(fit.success),iterations=int(fit.nit),
        objective=float(fit.fun),mean=mean.tolist(),scale=scale.tolist(),coefficients=fit.x.tolist())


def cross_validate(rows,target,ridge):
    y=np.array([r[target] for r in rows]);blocks=np.array([int(r['block']) for r in rows])
    output=dict(target=target,rows=len(rows),independent_blocks=sorted(set(blocks.tolist())),
                status='EXPLORATORY_GROUPED_VALIDATION_ON_EXPOSED_COHORT',models={})
    predictions={}
    for augmented,name in [(False,'current_expression_and_context'),(True,'plus_mechanistic_features')]:
        x,columns=design(rows,augmented)
        p=np.zeros(len(y));logits=np.zeros(len(y));folds=[]
        for held in output['independent_blocks']:
            test=blocks==held;train=~test
            p[test],logits[test],fit=fit_predict(x,y,train,test,ridge)
            folds.append(dict(block=held,n=int(test.sum()),successes=int(y[test].sum()),
                brier=float(np.mean((p[test]-y[test])**2)),
                log_loss=float(np.mean(np.logaddexp(0,logits[test])-y[test]*logits[test])),fit=fit))
        output['models'][name]=dict(columns=columns,ridge=ridge,
            mean_block_brier=float(np.mean([f['brier'] for f in folds])),
            mean_block_log_loss=float(np.mean([f['log_loss'] for f in folds])),folds=folds)
        predictions[name]=p
    basic=output['models']['current_expression_and_context'];added=output['models']['plus_mechanistic_features']
    output['brier_improvement']=basic['mean_block_brier']-added['mean_block_brier']
    output['relative_brier_improvement']=output['brier_improvement']/basic['mean_block_brier'] if basic['mean_block_brier'] else None
    output['log_loss_improvement']=basic['mean_block_log_loss']-added['mean_block_log_loss']
    output['blocks_with_lower_brier']=sum(b['brier']>a['brier'] for b,a in zip(basic['folds'],added['folds'],strict=True))
    output['interpretation']='Descriptive comparison using fixed models and whole-block exclusion; no untouched-family confirmation, tuning search or causal mediation claim.'
    return output,predictions


def block_summary(rows,keys):
    block_ids=sorted(set(int(r['block']) for r in rows))
    result={}
    for key in keys:
        means=[float(np.mean([r[key] for r in rows if int(r['block'])==b])) for b in block_ids]
        result[key]=dict(mean=float(np.mean(means)),block_min=float(min(means)),block_max=float(max(means)),block_means=means)
    return result


def analyze(folder):
    started=time.perf_counter()
    complete=json.loads((folder/'COMPLETE.json').read_text())
    assert complete['status']=='COMPLETE' and not complete['benchmark']
    assert sha(folder/'features.csv')==complete['features_sha256']
    for name,expected in complete['code_sha256'].items():assert sha(ROOT/name)==expected,name
    rows=load_rows(folder/'features.csv')
    cfg=json.loads((ROOT/'config.json').read_text())
    assert len(rows)==32768
    report=dict(status='RETROSPECTIVE_DEVELOPMENT_NOT_CONFIRMATORY',created_at_utc=stamp(),
        feature_sha256=sha(folder/'features.csv'),analysis_sha256=sha(Path(__file__)),
        cohort=dict(blocks=cfg['blocks'],lineages_per_condition=128,body_contexts=len(rows)),
        extraction_checks=complete['checks'],native_steps_rerun=0,terminal_counts=[],stages={},paired_generation_one=[])
    keys=['newly_substituted_fraction','sign_flip_fraction','raw_weight_change_mean','reader_row_l1_mean',
          'reader_row_l1_max','body_reader_change_mean','body_contrast_alignment','current_pass','next_pass',
          *[n+'_'+k for n in ('exact','tolerance','sign_restored') for k in
            ('signed_transfer','unsigned_access','conflict_mass','negative_plaquette_fraction','zero_denominator_fraction')]]
    # next_pass is omitted for stage summaries including the terminal boundary.
    for stage,select in [('generation1',lambda r:r['generation']==1),('generations2to32',lambda r:r['generation']>=2)]:
        report['stages'][stage]={}
        for pairing in cfg['pairings']:
            for policy in cfg['source_writers']:
                subset=[r for r in rows if select(r) and r['pairing']==pairing and r['source_writer']==policy]
                used_keys=keys if stage=='generation1' else [k for k in keys if k!='next_pass']
                report['stages'][stage][pairing+'/'+policy]=dict(n=len(subset),metrics=block_summary(subset,used_keys))
    initial=[r for r in rows if r['generation']==1]
    for pairing in cfg['pairings']:
        groups=[]
        for policy in cfg['source_writers']:
            subset=[r for r in initial if r['pairing']==pairing and r['source_writer']==policy]
            subset.sort(key=lambda r:(r['block'],r['founder'],r['recipient']))
            groups.append(subset)
            report['terminal_counts'].append(dict(pairing=pairing,writer=policy,
                success=int(sum(r['terminal_pass'] for r in subset)),total=len(subset),
                block_success=[int(sum(r['terminal_pass'] for r in subset if r['block']==b)) for b in cfg['blocks']]))
        exact,tol=groups
        for a,b in zip(exact,tol,strict=True):
            for key in ['current_margin','current_pass','body_contrast_alignment','exact_signed_transfer','tolerance_signed_transfer']:
                assert a[key]==b[key],('Common first body differs',pairing,key)
        contrast=dict(pairing=pairing,n=len(exact))
        for target in ('next_pass','terminal_pass'):
            a=np.array([r[target] for r in exact]);b=np.array([r[target] for r in tol])
            contrast[target]=dict(exact_success=int(a.sum()),tolerance_success=int(b.sum()),
                exact_only=int(np.sum((a==1)&(b==0))),tolerance_only=int(np.sum((a==0)&(b==1))))
        report['paired_generation_one'].append(contrast)
    targets=[('next_body',[r for r in rows if r['generation']<32],'next_pass'),('terminal_from_generation1',initial,'terminal_pass')]
    report['prediction_checks']={}
    prediction_rows=[]
    for name,data,target in targets:
        check,predictions=cross_validate(data,target,cfg['logistic_ridge'])
        report['prediction_checks'][name]=check
        for i,r in enumerate(data):
            item={k:r[k] for k in ('block','generation','pairing','source_writer','founder','recipient')}
            item.update(target=name,observed=r[target],**{k:float(v[i]) for k,v in predictions.items()})
            prediction_rows.append(item)
    with (folder/'held_out_predictions.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(prediction_rows[0]));w.writeheader();w.writerows(prediction_rows)
    report['prediction_sha256']=sha(folder/'held_out_predictions.csv')
    report['elapsed_seconds']=time.perf_counter()-started
    write_json(folder/'analysis.json',report)
    concise=dict(terminal_counts=report['terminal_counts'],paired_generation_one=report['paired_generation_one'],
        generation1_exact_source={p:{k:v['mean'] for k,v in report['stages']['generation1'][p+'/exact_rewrite']['metrics'].items()}
                                  for p in cfg['pairings']},
        prediction_checks={k:{n:v[n] for n in ('rows','brier_improvement','relative_brier_improvement','log_loss_improvement','blocks_with_lower_brier')} for k,v in report['prediction_checks'].items()},
        seconds=report['elapsed_seconds'])
    print(json.dumps(concise,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    analyze(parser.parse_args().folder)
