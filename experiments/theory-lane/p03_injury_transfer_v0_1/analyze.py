"""Predeclared paired effects, block summaries and fixed diagnostic choices."""
import csv
import math
import numpy as np
from common import arrays,read,write

CHOICES=('always_incoming','always_outgoing','signed_transfer','unsigned_access')
CONTRASTS={'rewrite':(1,0),'beyond_erasure':(1,2),'erasure_only':(2,0)}


def csv_write(path,rows):
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    c=(p+z*z/(2*n))/den;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0.,c-h),min(1.,c+h)


def summary(values,cfg):
    x=np.asarray(values,float)
    assert x.shape==(len(cfg['blocks']),) and np.isfinite(x).all()
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    ix=rng.integers(len(x),size=(cfg['bootstrap_replicates'],len(x)))
    lo,hi=np.quantile(x[ix].mean(axis=1),[.025,.975])
    return dict(mean=float(x.mean()),by_block={str(b):float(y) for b,y in zip(cfg['blocks'],x)},
        descriptive_block_bootstrap_95=[float(lo),float(hi)],positive_blocks=int((x>0).sum()),
        tied_blocks=int((x==0).sum()),negative_blocks=int((x<0).sum()))


def choice_weights(data,regime):
    n=len(data['founders']);r=len(data['replicates'])
    answer=dict(always_incoming=np.zeros((n,r)),always_outgoing=np.ones((n,r)))
    for kind in CHOICES[2:]:
        a,b=data[kind][regime,:,0],data[kind][regime,:,1]
        answer[kind]=np.where(b>a,1.,np.where(b<a,0.,.5))
    return answer


def analyze(folder,cfg):
    groups={b:arrays(folder/f'reads_{b:06d}.npz') for b in cfg['blocks']}
    read_rows,state_rows,block_rows,choice_rows=[],[],[],[]
    r=len(cfg['replicates'])
    for block,data in groups.items():
        n=len(data['founders'])
        assert data['both_pass'].shape==(2,n,4,r)
        for gi,regime in enumerate(cfg['regimes']):
            for vi,variant in enumerate(cfg['variants']):
                outcome=data['both_pass'][gi,:,vi]
                block_rows.append(dict(block=block,regime=regime,variant=variant,cases=n,reads=n*r,
                    successes=int(outcome.sum()),rate=float(outcome.mean())))
                for case in range(n):
                    context=dict(block=block,local_case=case,history=cfg['histories'][int(data['histories'][case])],
                        founder=int(data['founders'][case]),recipient=int(data['recipients'][case]),regime=regime,variant=variant)
                    count=int(outcome[case].sum());lo,hi=wilson(count,r)
                    state_rows.append(dict(**context,successes=count,reads=r,rate=count/r,
                        conditional_MC_wilson_lower=lo,conditional_MC_wilson_upper=hi))
                    for ri,rep in enumerate(cfg['replicates']):
                        ports=data['mean_ports'][gi,case,vi,ri].ravel()
                        read_rows.append(dict(**context,replicate=rep,success=int(outcome[case,ri]),
                            margin=float(data['min_margin'][gi,case,vi,ri]),
                            plus_a=float(ports[0]),plus_b=float(ports[1]),minus_a=float(ports[2]),minus_b=float(ports[3]),
                            signed_transfer=float(data['signed_transfer'][gi,case,vi,ri]),
                            unsigned_access=float(data['unsigned_access'][gi,case,vi,ri]),
                            overlap_with_original=int((data['masks'][gi,case,ri]&data['original_masks'][case]).sum())))
            for name,w in choice_weights(data,gi).items():
                attained=(1-w)*data['both_pass'][gi,:,0]+w*data['both_pass'][gi,:,1]
                for case in range(n):
                    for ri,rep in enumerate(cfg['replicates']):
                        choice_rows.append(dict(block=block,local_case=case,regime=regime,replicate=rep,rule=name,
                            weight_outgoing=float(w[case,ri]),attained_success=float(attained[case,ri])))
    for name,rows in [('reads',read_rows),('state_rates',state_rows),('block_summaries',block_rows),('choice_reads',choice_rows)]:
        csv_write(folder/(name+'.csv'),rows)
    rates,effects,choices,signed_contrasts={},{},{},{}
    for gi,regime in enumerate(cfg['regimes']):
        rates[regime]={};effects[regime]={};choices[regime]={};signed_contrasts[regime]={}
        for vi,variant in enumerate(cfg['variants']):
            values=[float(groups[b]['both_pass'][gi,:,vi].mean()) for b in cfg['blocks']]
            joined=np.concatenate([groups[b]['both_pass'][gi,:,vi] for b in cfg['blocks']])
            rates[regime][variant]=dict(**summary(values,cfg),reads=int(joined.size),successes=int(joined.sum()),
                cases_with_any_success=int(joined.any(axis=1).sum()),cases_with_all_success=int(joined.all(axis=1).sum()))
        for name,(a,b) in CONTRASTS.items():
            values=[float((d['both_pass'][gi,:,a].astype(int)-d['both_pass'][gi,:,b].astype(int)).mean()) for d in groups.values()]
            x=np.concatenate([d['both_pass'][gi,:,a] for d in groups.values()])
            y=np.concatenate([d['both_pass'][gi,:,b] for d in groups.values()])
            effects[regime][name]=dict(**summary(values,cfg),paired_reads=int(x.size),
                first_only=int((x&~y).sum()),second_only=int((y&~x).sum()),both_pass=int((x&y).sum()),both_fail=int((~x&~y).sum()))
        for rule in CHOICES:
            weights=[choice_weights(d,gi)[rule] for d in groups.values()]
            values=[float(((1-w)*d['both_pass'][gi,:,0]+w*d['both_pass'][gi,:,1]).mean()) for w,d in zip(weights,groups.values())]
            choices[regime][rule]=dict(**summary(values,cfg),outgoing_choices=sum(int((w==1).sum()) for w in weights),
                incoming_choices=sum(int((w==0).sum()) for w in weights),ties=sum(int((w==.5).sum()) for w in weights))
        for rival in ('always_incoming','always_outgoing','unsigned_access'):
            signed=choices[regime]['signed_transfer']['by_block'];base=choices[regime][rival]['by_block']
            signed_contrasts[regime][rival]=summary([signed[str(b)]-base[str(b)] for b in cfg['blocks']],cfg)
    shift=summary([effects['fresh']['rewrite']['by_block'][str(b)]-effects['original']['rewrite']['by_block'][str(b)] for b in cfg['blocks']],cfg)
    result=dict(status='DEVELOPMENT_ANALYSIS_COMPLETE',enrolled_cases=64,blocks=8,read_trials=len(read_rows),
        rate_summaries=rates,effects=effects,fresh_minus_original_rewrite_effect=shift,choices=choices,
        signed_choice_minus_rivals=signed_contrasts,
        primary_prediction='Fresh-injury outgoing minus incoming equal-block mean is positive.',
        primary_estimate_positive=effects['fresh']['rewrite']['mean']>0,
        interpretation='Outcome-informed development on exposed failed states; fresh mask and read draws; no general boundary claim.',
        conditional_precision='Sixteen independent mask/noise draws per case in the fresh regime; one original mask with sixteen read draws in the reference.',
        fitted_models=0)
    write(folder/'analysis.json',result)
    return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    primary=a['effects']['fresh']['rewrite'];lo,hi=primary['descriptive_block_bootstrap_95']
    direction='positive' if primary['mean']>0 else 'zero or negative'
    lines=['# Rewriting under new injury patterns','',
        '**Completed development experiment.** All 64 previously observed failures were retained. '
        'Each record received 16 new mask/noise draws and a paired original-mask reference, at 2,048 updates. '
        'Every current injury removes 24 non-port cells. No writing occurs during reads.','',
        f"The fresh-injury rewrite effect is **{100*primary['mean']:+.2f} percentage points**, with a descriptive eight-block bootstrap interval "
        f"[{100*lo:.2f}, {100*hi:.2f}] points. The observed estimate is {direction}; "
        'this directional check is not a significance test or independent confirmation.','',
        'Rates below weight blocks equally; pooled counts have 1,024 reads per record/regime and use different weighting.','',
        '| Injury regime | Record | Equal-block success | Pooled successes |','|---|---|---:|---:|']
    for regime in cfg['regimes']:
        for variant in cfg['variants']:
            r=a['rate_summaries'][regime][variant]
            lines.append(f"| {regime} | {variant} | {100*r['mean']:.2f}% | {r['successes']}/{r['reads']} |")
    lines+=['','| Block | Cases | Original rewrite (pp) | Fresh rewrite (pp) | Fresh beyond erasure (pp) | Fresh erasure only (pp) |','|---|---:|---:|---:|---:|---:|']
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        terms=[a['effects'][regime][effect]['by_block'][str(block)] for regime,effect in
               [('original','rewrite'),('fresh','rewrite'),('fresh','beyond_erasure'),('fresh','erasure_only')]]
        lines.append(f'| {block} | {n} | '+' | '.join(f'{100*v:+.2f}' for v in terms)+' |')
    shift=a['fresh_minus_original_rewrite_effect']
    lines+=['',f"The fresh-minus-original rewrite-effect difference is {100*shift['mean']:+.2f} points. "
        'Erasure-only applies the original injury deletions to the incoming packet. Its difference from outgoing '
        'includes reweighting and restoration of previously absent edges. It does not isolate edge signs. '
        'Incoming and erasure-only reads under the original mask are byte-identical, as required.','',
        '| Fixed choice | Original yield | Fresh yield |','|---|---:|---:|']
    for rule in CHOICES:
        lines.append('| '+rule+' | '+' | '.join(f"{100*a['choices'][regime][rule]['mean']:.2f}%" for regime in cfg['regimes'])+' |')
    lines+=['','Choices use the actual injury and fixed 64-step diagnostics; no native outcome selects a record. '
        'All 16 draws evaluate the choices. This differs from the previous probe/evaluation split and is not a '
        'budget-matched repair trial. Exact diagnostic ties receive half weight.','',
        'The cohort, earlier outcomes, and motivation are exposed. New patterns and read streams were fixed before '
        'new native outcomes. Uniform mask draws were not filtered for connectivity or favorable features. '
        'The eight blocks, not individual related reads, remain the inference units. A positive effect supports '
        'transfer within this selected panel and damage law; a zero or negative effect fails the directional '
        'prediction in the panel. Intervals describe uncertainty and do not create an unplanned acceptance gate.','',
        'Every known original native read was replayed byte for byte. All 8,192 output windows were independently '
        'rescored; every table and choice was checked. A separate flattened implementation replayed the first '
        'case in each block, draw 4, all four records and both injury regimes. Mask generation, deletion controls '
        'and sampled diagnostics were independently verified. These are separate implementations in one lane.','',
        '![Success rates and block effects](injury_transfer.png)','',
        'Raw arrays, analysis.json, four CSV tables, VERIFICATION.json and frozen inputs are retained. '
        'No automatic successor experiment is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
