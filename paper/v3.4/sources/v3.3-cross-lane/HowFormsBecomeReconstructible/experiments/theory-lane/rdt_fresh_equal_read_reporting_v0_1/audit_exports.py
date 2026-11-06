"""Independent scalar reconstruction from compact exports; no native data imports."""
from pathlib import Path
from collections import Counter
import csv
import json
import math
import hashlib
import time
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE/'results_v1'


def rows(name):
    with (OUT/(name+'.csv')).open() as f:return list(csv.DictReader(f))


def key(r):return int(r['block']),r['history'],int(r['founder']),int(r['recipient'])


def close(a,b,tolerance=3e-12):
    assert abs(float(a)-float(b))<tolerance,(a,b)


def main():
    start=time.monotonic();summary=json.loads((OUT/'SUMMARY.json').read_text())
    acquired=rows('acquisition');weights=rows('weights');forecasts=rows('forecasts');outcomes=rows('outcomes')
    assert len(acquired)==5120 and len(weights)==319 and len(forecasts)==638 and len(outcomes)==2552
    cell=Counter((int(r['block']),int(r['current_pass']),int(r['rule'])) for r in acquired)
    selected=Counter((int(r['block']),int(r['current_pass']),int(r['rule'])) for r in weights)
    selected_class=Counter((int(r['block']),int(r['current_pass'])) for r in weights)
    acquired_class=Counter(int(r['current_pass']) for r in acquired)
    assert acquired_class=={0:868,1:4252}
    for r in weights:
        b,c,s=int(r['block']),int(r['current_pass']),int(r['rule'])
        expansion=cell[b,c,s]/selected[b,c,s]
        close(r['expansion'],expansion)
        close(r['balanced'],1/(80*2*selected_class[b,c]))
        close(r['population'],expansion/5120)
        for cls,label in [(0,'fail'),(1,'pass')]:
            close(r['balanced_'+label],2*float(r['balanced']) if c==cls else 0)
            close(r['population_'+label],expansion/acquired_class[cls] if c==cls else 0)
    fp={(key(r),r['regime']):r for r in forecasts}
    fy={(key(r),r['regime'],int(r['replicate'])):r for r in outcomes}
    assert len(fp)==638 and len(fy)==2552
    constant=443/512
    models=['successor32','direct64','pooled32','direct8','tt008','development_constant']
    losses={};obs={};pred={}
    for regime in ('matched','independent'):
        for r in weights:
            k=key(r);ys=[int(fy[k,regime,j]['terminal_success']) for j in range(4)]
            obs[k,regime]=math.fsum(ys)/4
            for j in range(4):assert ys[j]==int(float(fy[k,regime,j]['terminal_margin'])>.25)
            for model in models:
                p=constant if model=='development_constant' else float(fp[k,regime]['p_'+model])
                pred[k,regime,model]=p
                losses[k,regime,model]=math.fsum((p-y)**2 for y in ys)/4
    source_by_profile={};score_lookup={}
    draw=np.random.default_rng(summary['bootstrap']['seed']).integers(0,80,(10000,80))
    for row in summary['summary']:
        profile,regime,model=row['profile'],row['regime'],row['model']
        N=np.zeros(80);D=np.zeros(80);Y=np.zeros(80);P=np.zeros(80);C=np.zeros(80)
        for r in weights:
            k=key(r);b=k[0];w=float(r[profile])
            N[b]+=w*losses[k,regime,model];D[b]+=w;Y[b]+=w*obs[k,regime]
            P[b]+=w*pred[k,regime,model];C[b]+=w*losses[k,regime,'development_constant']
        close(D.sum(),1.)
        for name,expect in [('brier',N.sum()),('terminal_success',Y.sum()),('mean_prediction',P.sum()),
                            ('calibration_bias',P.sum()-Y.sum()),('brier_skill',1-N.sum()/C.sum())]:close(row[name],expect)
        denominator=D[draw].sum(1)
        bs=N[draw].sum(1)/denominator;preval=Y[draw].sum(1)/denominator;ps=P[draw].sum(1)/denominator
        bs_constant=C[draw].sum(1)/denominator
        for label,values in [('brier',bs),('terminal_success',preval),('mean_prediction',ps),
                             ('calibration_bias',ps-preval),('brier_skill',1-bs/bs_constant)]:
            lo,hi=np.quantile(values,[.025,.975]);close(row[label+'_low'],lo);close(row[label+'_high'],hi)
        source_by_profile[profile,regime,model]=(N,D,Y,P,C)
        score_lookup[profile,regime,model]=(row,bs,bs_constant)
    for row in summary['comparisons']:
        profile,regime,model=row['profile'],row['regime'],row['rival']
        a,bs,_=score_lookup[profile,regime,model];b,candidate,_=score_lookup[profile,regime,'successor32']
        close(row['gain'],a['brier']-b['brier'])
        lo,hi=np.quantile(bs-candidate,[.025,.975]);close(row['bootstrap_low'],lo);close(row['bootstrap_high'],hi)
    for row in rows('block_scores'):
        n,d,y,p,c=source_by_profile[row['profile'],row['regime'],row['model']];b=int(row['block'])
        for name,value in [('block_weight',d[b]),('brier_numerator',n[b]),('success_numerator',y[b]),('prediction_numerator',p[b])]:close(row[name],value)
    calibration=rows('calibration');calibration_interval_checks=0
    for row in calibration:
        profile,regime,model=row['profile'],row['regime'],row['model'];bin_id=int(row['bin'])
        subset=[r for r in weights if float(r[profile])>0 and min(int(pred[key(r),regime,model]*10),9)==bin_id]
        mass=math.fsum(float(r[profile]) for r in subset);close(row['weight'],mass)
        assert int(row['packets'])==len(subset) and int(row['blocks'])==len({r['block'] for r in subset})
        if not subset:
            assert row['observed']==row['brier']==row['predicted']=='';continue
        pv=math.fsum(float(r[profile])*pred[key(r),regime,model] for r in subset)/mass
        yv=math.fsum(float(r[profile])*obs[key(r),regime] for r in subset)/mass
        bv=math.fsum(float(r[profile])*losses[key(r),regime,model] for r in subset)/mass
        close(row['predicted'],pv);close(row['observed'],yv);close(row['brier'],bv);close(row['bias'],pv-yv)
        # Check every nonempty-bin interval from direct resampling of independent source totals.
        D=np.zeros(80);Y=np.zeros(80);P=np.zeros(80);L=np.zeros(80)
        for r in subset:
            k=key(r);b=k[0];w=float(r[profile]);D[b]+=w;Y[b]+=w*obs[k,regime]
            P[b]+=w*pred[k,regime,model];L[b]+=w*losses[k,regime,model]
        denominator=D[draw].sum(1);ok=denominator>0
        assert ok.sum()==int(row['valid_bootstraps'])
        obs_b=Y[draw].sum(1)[ok]/denominator[ok];pre_b=P[draw].sum(1)[ok]/denominator[ok]
        loss_b=L[draw].sum(1)[ok]/denominator[ok]
        for label,values in [('observed',obs_b),('predicted',pre_b),('brier',loss_b),('bias',pre_b-obs_b)]:
            lo,hi=np.quantile(values,[.025,.975]);close(row[label+'_low'],lo);close(row[label+'_high'],hi)
        calibration_interval_checks+=1
    receipt=dict(status='PASS',seconds=time.monotonic()-start,scalar_scores_verified=72,
        paired_bootstrap_contrasts_verified=len(summary['comparisons']),block_contribution_rows_verified=len(rows('block_scores')),
        calibration_rows_verified=len(calibration),nonempty_calibration_intervals_verified=calibration_interval_checks,
        acquisition_records=5120,selected_records=319,future_outcomes=2552,source_blocks=80,
        predictions_changed=False,new_native_reads=0,new_model_fits=0,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with (OUT/'EXPORT_AUDIT.json').open('x') as file:json.dump(receipt,file,indent=2);file.write('\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
