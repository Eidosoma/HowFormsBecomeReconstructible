"""Paired source-block summaries of previously exposed development targets."""
from pc_common import *
import time
from pc_fit import future_brier

BOOTSTRAPS=10000
SEED=10720261102


def block_sum(values,w,blocks):
    a=np.asarray(values)
    if a.ndim==1:return np.bincount(blocks,weights=w*a,minlength=80)
    return np.stack([np.bincount(blocks,weights=w*a[:,j],minlength=80) for j in range(a.shape[1])],axis=1)


def interval(draw):
    good=np.isfinite(draw)
    if not good.any():return None,None
    return tuple(float(v) for v in np.quantile(np.asarray(draw)[good],[.025,.975]))


def estimates(values,w,blocks,counts):
    num=block_sum(values,w,blocks);mass=np.bincount(blocks,weights=w,minlength=80)
    den=counts@mass
    raw=counts@num
    if num.ndim>1:den=den[:,None]
    draws=np.divide(raw,den,out=np.full_like(raw,np.nan),where=den>0)
    return num.sum(axis=0)/mass.sum(),draws,num,mass


def logloss(p,y,floor):
    q=np.clip(p,floor,1-floor)
    return -(y[:,None]*np.log2(q)+(1-y[:,None])*np.log2(1-q))


def main(run,deadline):
    started=time.process_time();wall=time.monotonic()
    run=Path(run);folder=run/'analysis';folder.mkdir()
    data=load_arrays(run/'fitting/SCORING.npz',sha(run/'fitting/SCORING.npz'))
    schema=read(run/'fitting/SCORING_SCHEMA.json');cases=read(ROOT/'prepared/CASES.json')
    require(read(run/'fitting/PREDICTION_SEAL.json')['predictions_sha256']==sha(run/'fitting/HELD_FOLD_PREDICTIONS.csv'), 'Prediction scoring barrier')
    p=data['probability'];y=data['y'];ybar=y.mean(axis=1);blocks=data['block'].astype(int)
    names=schema['models'];M=len(names);require(p.shape==(638,M) and y.shape==(638,4),'Complete scoring panel')
    require(np.isin(y,[0,1]).all() and np.isfinite(p).all() and ((p>=0)&(p<=1)).all(),'Binary target probabilities')
    bs=future_brier(p,ybar[:,None]);ll=logloss(p,ybar,1e-6)
    # Explicitly verify aggregate-case scoring equals all individual futures.
    require(np.max(abs(bs-np.mean((p[:,:,None]-y[:,None,:])**2,axis=2)))<1e-14,'Individual-future Brier identity')
    counts=np.random.default_rng(SEED).multinomial(80,np.full(80,1/80),size=BOOTSTRAPS)
    summary=[];contrasts=[];calibration=[];block_rows=[];sensitivity=[]
    primary_pairs=[('depth1','depth2'),('depth0','depth1'),('depth0','depth2')]
    pairs=primary_pairs+[(r,d) for d in ('depth0','depth1','depth2') for r in ('cheap_all','boundary','no_body_expression','direct8','class_history')]
    for wi,profile in enumerate(PROFILES):
        for ri,regime in enumerate(REGIMES):
            require(time.time()<deadline,'Scoring deadline')
            w=data['weights'][:,wi]*(data['regime']==ri)
            active=w>0
            b,bd,bnum,mass=estimates(bs,w,blocks,counts)
            l,ld,lnum,_=estimates(ll,w,blocks,counts)
            pred,pd,pnum,_=estimates(p,w,blocks,counts)
            prev,yd,ynum,_=estimates(ybar,w,blocks,counts)
            constant=names.index('constant')
            for j,name in enumerate(names):
                bi=interval(bd[:,j]);li=interval(ld[:,j]);pi=interval(pd[:,j]);yi=interval(yd)
                skill=1-b[j]/b[constant];si=interval(1-bd[:,j]/bd[:,constant])
                bias=pred[j]-prev;ci=interval(pd[:,j]-yd)
                role='GROUPED_NEW_MODEL' if name in FAMILIES else 'FIXED_DEVELOPMENT_CONSTANT' if name=='constant' else 'EXPOSED_REFERENCE_NOT_SAME_TRAINING'
                summary.append(dict(profile=profile,regime=regime,model=name,role=role,
                    brier=float(b[j]),brier_low=bi[0],brier_high=bi[1],logloss_bits=float(l[j]),logloss_low=li[0],logloss_high=li[1],
                    terminal_success=float(prev),terminal_success_low=yi[0],terminal_success_high=yi[1],
                    mean_probability=float(pred[j]),probability_low=pi[0],probability_high=pi[1],
                    calibration_bias=float(bias),calibration_bias_low=ci[0],calibration_bias_high=ci[1],
                    brier_skill=float(skill),skill_low=si[0],skill_high=si[1],
                    records=int(active.sum()),futures=int(active.sum()*4),source_blocks=int((mass>0).sum()),
                    unweighted_terminal_successes=int(y[active].sum()),weight_sum=float(mass.sum())))
                for block in range(80):
                    block_rows.append(dict(profile=profile,regime=regime,block=block,model=name,
                        weight_mass=float(mass[block]),brier_numerator=float(bnum[block,j]),
                        logloss_numerator=float(lnum[block,j]),probability_numerator=float(pnum[block,j]),
                        terminal_success_numerator=float(ynum[block])))
                bins=np.minimum((p[:,j]*10).astype(int),9)
                for k in range(10):
                    chosen=active&(bins==k);ww=w*(bins==k)
                    rec=dict(profile=profile,regime=regime,model=name,bin=k,lower=k/10,upper=(k+1)/10,
                        records=int(chosen.sum()),futures=int(chosen.sum()*4),successes=int(y[chosen].sum()),
                        source_blocks=len(set(blocks[chosen].tolist())),weight_mass=float(ww.sum()),
                        mean_probability=None,terminal_success=None,probability_low=None,probability_high=None,
                        success_low=None,success_high=None,valid_bootstrap_draws=0)
                    if ww.sum():
                        pp,ppd,_,_=estimates(p[:,j],ww,blocks,counts)
                        yy,yyd,_,_=estimates(ybar,ww,blocks,counts)
                        pii=interval(ppd);yii=interval(yyd)
                        rec.update(mean_probability=float(pp),terminal_success=float(yy),probability_low=pii[0],
                            probability_high=pii[1],success_low=yii[0],success_high=yii[1],
                            valid_bootstrap_draws=int(np.isfinite(yyd).sum()))
                    calibration.append(rec)
            for rival,candidate in pairs:
                a,c=names.index(rival),names.index(candidate);gain=b[a]-b[c];ci=interval(bd[:,a]-bd[:,c])
                contrasts.append(dict(profile=profile,regime=regime,rival=rival,candidate=candidate,
                    brier_gain=float(gain),gain_low=ci[0],gain_high=ci[1],source_blocks=int((mass>0).sum()),
                    primary_development_contrast=profile=='balanced' and (rival,candidate)==('depth1','depth2'),
                    confirmatory=False))
            for floor in (1e-9,1e-6,1e-3):
                values=(w[:,None]*logloss(p,ybar,floor)).sum(axis=0)/w.sum()
                for j,name in enumerate(names):sensitivity.append(dict(profile=profile,regime=regime,model=name,floor=floor,logloss_bits=float(values[j])))
    predictions=[];outcomes=[];weights=[]
    for i,c in enumerate(cases):
        meta={k:c[k] for k in ('case_id','block','fold','history','founder','recipient','rule','current_pass','regime')}
        predictions.append(dict(**meta,**{'p_'+n:float(p[i,j]) for j,n in enumerate(names)},
                                q8=float(data['q'][i,0]),q0=float(data['q'][i,1]),q1=float(data['q'][i,2]),q2=float(data['q'][i,3])))
        weights.append(dict(**meta,**{profile:float(data['weights'][i,j]) for j,profile in enumerate(PROFILES)}))
        for r in range(4):outcomes.append(dict(**meta,replicate=r,terminal_success=int(y[i,r])))
    for name,rows in [('summary',summary),('contrasts',contrasts),('calibration',calibration),('block_scores',block_rows),
                      ('logloss_sensitivity',sensitivity),('predictions',predictions),('outcomes',outcomes),('weights',weights)]:
        write_csv(folder/(name+'.csv'),rows)
    primary=[r for r in contrasts if r['primary_development_contrast']]
    result=dict(status='COMPLETE_POST_HOC_DEVELOPMENT',source_blocks=80,records=319,cases=638,individual_futures=2552,
        primary_contrasts=primary,bootstrap=dict(samples=BOOTSTRAPS,seed=SEED,unit='whole source block',
            conditional_on_held_predictions=True,complete_training_uncertainty_propagated=False),
        inference_caveat='Descriptive post hoc intervals; fixed TT051 references have related-source development exposure. No prospective or RDT-specific qualification.',
        weights='Existing study-specific block/class/orientation expansion and original balanced estimand; each regime separately normalized.',
        population_scope='Realized 80 eligible-source acquisition panel under within-cell hash-rank exchangeability; no recovery of excluded/unsupported populations.',
        cost_qualification='60/30/20 branches passed the one-source technical CPU gate; no population-wide CPU or wall-time equality claim.',
        model_fits=read(run/'fitting/COMPLETE.json'),cpu_seconds=time.process_time()-started,wall_seconds=time.monotonic()-wall,
        original_e107_verdict_unchanged=True,new_confirmation_launched=False,manuscript_changed=False)
    write(folder/'SUMMARY.json',result)
    lines=['Probe-depth forecasting: post hoc grouped development','',
        '80 exposed source blocks; 319 selected records; 638 regime cases; 2552 saved futures.',
        'Eight outer folds keep all related records and conditions from each source together.',
        'Scaling, ridge selection and probability calibration use training folds only.',
        'New depth models use identical 70 cheap inputs plus their own probe fraction.',
        '', 'Primary development comparison: depth1 Brier minus depth2 Brier (positive favors depth2).']
    for r in primary:lines.append(f"{r['regime']}: {r['brier_gain']:+.7f} [{r['gain_low']:+.7f}, {r['gain_high']:+.7f}]")
    lines += ['', 'Absolute Brier by regime/class for the three depths and ordinary references:']
    for regime in REGIMES:
        for profile in ('balanced','balanced_fail','balanced_pass','population','population_fail','population_pass'):
            rows=[r for r in summary if r['regime']==regime and r['profile']==profile and r['model'] in ('depth0','depth1','depth2','cheap_all','boundary','no_body_expression','direct8')]
            lines.append(regime+' / '+profile+': '+', '.join(r['model']+'='+format(r['brier'],'.6f') for r in rows))
    lines += ['', 'These are development results, not a new confirmation. All prior failures and',
        'E107 primary findings retain their original status. The technical CPU match used',
        'four records from one block; caching does not reduce charged standalone probe work.',
        'Depth0/1/2 charge 60 native body reads each, including terminal capture; inherited',
        'writes are 0/30/40 and terminal reads 60/30/20. New study work measures only the',
        'missing 40 native reads per depth2 case, with two independent flat audit reads.',
        'The true task orientation, body and boundary history are supplied resources.',
        'Fixed TT051 references overlap related source development and are descriptive.',
        'The no-body ablation is retained separately; it does not replace the full principal.',
        'Intervals condition on held predictions and omit complete training uncertainty.',
        'Empty calibration bins are undefined; sparse bins retain represented-block counts.',
        'See summaries, calibration, log-loss sensitivity, block contributions and costs.',
        '', 'Deployment models are sealed separately from held-fold predictions. Any fresh',
        'confirmation must reserve untouched sources and freeze the full design first.',
        'No fresh continuation cohort was launched. The manuscript hold remains.']
    with (folder/'REPORT.txt').open('x') as f:f.write('\n'.join(lines)+'\n')
    return result
