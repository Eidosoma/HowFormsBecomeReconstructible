"""Four signed fresh-source predictions with paired whole-block inference."""
import numpy as np
from common import rng
from E077_fresh_reconstruction_tradeoff.plan import SLOTS, STARTS, PRIMARY, PREDICTED, CONFIDENCE

SCORES = ('both', 'minimum_margin', 'aligned_transfer')
GROUPS = {s:(i,) for i,s in enumerate(SLOTS)}
for name,start in STARTS.items():
    for kind,k in (('native',0),('mixture',2)):
        GROUPS[f'{name}_{kind}_pooled'] = (start+k,start+k+1)


def effects(x, history):
    result={}
    for kind,offset in (('native',0),('mixture',2)):
        def take(start):
            i=start+offset
            return (x[...,i]+x[...,i+1])/2 if history=='pooled' else x[...,i+(history=='pulse')]
        i0,p0,i1,p1,m1,j1=[take(start) for start in (0,4,9,13,18,22)]
        values=dict(pruning_h0=p0-i0,pruning_h1=p1-i1,magnitudes_h1=m1-p1,joint_h1=j1-p1,
            signs_at_intact_magnitudes=j1-m1,pruning_advantage_change=(p1-i1)-(p0-i0),
            intact_temporal=i1-i0,pruned_temporal=p1-p0,joint_vs_intact=j1-i1,
            I0_over_erased=i0-x[...,8],P0_over_erased=p0-x[...,8],
            I1_over_erased=i1-x[...,17],P1_over_erased=p1-x[...,17],
            M1_over_erased=m1-x[...,17],J1_over_erased=j1-x[...,17])
        result.update({kind+'_'+name:value for name,value in values.items()})
    return result


def values(cases):
    out={}
    for metric in cases[0]:
        if metric=='margin':continue
        x=np.stack([c[metric] for c in cases]).mean(axis=(-2,-1))
        for label,slots in GROUPS.items():out[f'native/{metric}/{label}']=x[:,slots].mean(axis=-1)
        if metric in SCORES:
            for history in ('pooled','sham','pulse'):
                for name,v in effects(x,history).items():out[f'effect/{metric}/{history}/{name}']=v
    return out


def classification(interval):
    return 'POSITIVE_EFFECT' if interval[0]>0 else 'NEGATIVE_EFFECT' if interval[1]<0 else 'UNRESOLVED'


def verdict(mode,ok,labels):
    if mode!='scientific':return 'TECHNICAL_ONLY'
    if not ok:return 'NUMERICAL_CONTROL_FAILURE'
    if all(labels[k]==v for k,v in zip(PRIMARY,PREDICTED,strict=True)):
        return 'FRESH_TRADEOFF_AND_COMPATIBILITY_CONFIRMED'
    if any(labels[k] not in (v,'UNRESOLVED') for k,v in zip(PRIMARY,PREDICTED,strict=True)):
        return 'PREDICTED_PATTERN_CONTRADICTED'
    return 'PREDICTED_PATTERN_UNRESOLVED'


def analyze(cases,controls,mode):
    B=len(cases);draws=rng('E077','reconstruction_tradeoff','bootstrap').integers(0,B,(10000,B))
    primary={f'effect/both/pooled/{name}' for name in PRIMARY};stats={}
    for key,x in values(cases).items():
        confidence=CONFIDENCE if key in primary else .95;a=(1-confidence)/2
        stats[key]=dict(mean=float(x.mean()),confidence=confidence,block_means=x.tolist(),
            interval=np.quantile(x[draws].mean(axis=1),[a,1-a]).tolist())
    ok=all(c['pass'] for c in controls);enabled=mode=='scientific' and ok
    labels={name:classification(stats[f'effect/both/pooled/{name}']['interval']) if enabled else None for name in PRIMARY}
    return dict(status=verdict(mode,ok,labels),primary_effects=labels,
        predicted_directions=dict(zip(PRIMARY,PREDICTED,strict=True)),
        prediction_supported=all(labels[k]==v for k,v in zip(PRIMARY,PREDICTED,strict=True)) if enabled else None,
        controls_pass=ok,controls_by_block=controls,independent_blocks=B,
        lineages_per_slot=B*cases[0]['both'].shape[-2]*cases[0]['both'].shape[-1],
        primary_family_size=4,primary_confidence=CONFIDENCE,primary_arm_weighting='equal_within_block',
        source_boundary=1,additional_rewrites=1,fresh_sources=mode=='scientific',
        cohort_reused=False,prior_E073_through_E076_results_known=True,old_observations_pooled=False,
        statistics=stats)


def audit(cases,controls,summary,mode):
    from E015_functional_inheritance.audit import random
    B=len(cases);draws=random('E077','reconstruction_tradeoff','bootstrap').integers(0,B,size=(10000,B))
    pools={}
    for start,name in ((0,'I0'),(4,'P0'),(9,'I1'),(13,'P1'),(18,'M1'),(22,'J1')):
        for kind,k in (('native',0),('mixture',2)):pools[f'{name}_{kind}_pooled']=(start+k,start+k+1)
    expected={}
    def add(key,value):expected.setdefault(key,[]).append(value)
    for case in cases:
        for metric,array in case.items():
            if metric=='margin':continue
            x=np.array([np.sum(row)/row.size for row in array])
            for i,label in enumerate(SLOTS):add(f'native/{metric}/{label}',x[i])
            for label,(a,b) in pools.items():add(f'native/{metric}/{label}',(x[a]+x[b])/2)
            if metric not in ('both','minimum_margin','aligned_transfer'):continue
            for history in ('pooled','sham','pulse'):
                for kind,k in (('native',0),('mixture',2)):
                    starts=[i+k for i in (0,4,9,13,18,22)]
                    i0,p0,i1,p1,m,j=([(x[i]+x[i+1])/2 for i in starts] if history=='pooled'
                                   else [x[i+int(history=='pulse')] for i in starts])
                    for name,value in (
                        ('pruning_h0',p0-i0),('pruning_h1',p1-i1),('magnitudes_h1',m-p1),('joint_h1',j-p1),
                        ('signs_at_intact_magnitudes',j-m),('pruning_advantage_change',(p1-i1)-(p0-i0)),
                        ('intact_temporal',i1-i0),('pruned_temporal',p1-p0),('joint_vs_intact',j-i1),
                        ('I0_over_erased',i0-x[8]),('P0_over_erased',p0-x[8]),
                        ('I1_over_erased',i1-x[17]),('P1_over_erased',p1-x[17]),
                        ('M1_over_erased',m-x[17]),('J1_over_erased',j-x[17])):
                        add(f'effect/{metric}/{history}/{kind}_{name}',value)
    assert set(expected)==set(summary['statistics'])
    names=('mixture_pruning_h0','mixture_pruning_h1','mixture_magnitudes_h1','mixture_joint_h1')
    for key,samples in expected.items():
        x=np.array(samples);r=summary['statistics'][key]
        confidence=.9875 if key in tuple('effect/both/pooled/'+n for n in names) else .95
        a=(1-confidence)/2
        np.testing.assert_array_equal(r['block_means'],x)
        assert r['mean']==x.mean() and r['confidence']==confidence
        np.testing.assert_array_equal(r['interval'],np.quantile(x[draws].mean(axis=1),[a,1-a]))
    ok=all(c['pass'] for c in controls);enabled=mode=='scientific' and ok;labels={}
    for name in names:
        lo,hi=summary['statistics'][f'effect/both/pooled/{name}']['interval']
        labels[name]=('POSITIVE_EFFECT' if lo>0 else 'NEGATIVE_EFFECT' if hi<0 else 'UNRESOLVED') if enabled else None
    directions=('POSITIVE_EFFECT','NEGATIVE_EFFECT','NEGATIVE_EFFECT','POSITIVE_EFFECT')
    match=all(labels[n]==d for n,d in zip(names,directions,strict=True))
    contradiction=any(labels[n] in ('POSITIVE_EFFECT','NEGATIVE_EFFECT') and labels[n]!=d
                      for n,d in zip(names,directions,strict=True))
    status=('TECHNICAL_ONLY' if mode!='scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else
            'FRESH_TRADEOFF_AND_COMPATIBILITY_CONFIRMED' if match else
            'PREDICTED_PATTERN_CONTRADICTED' if contradiction else 'PREDICTED_PATTERN_UNRESOLVED')
    assert summary['status']==status and summary['controls_pass']==ok
    assert summary['prediction_supported']==(match if enabled else None)
    assert summary['primary_effects']==labels and summary['primary_confidence']==.9875
    assert summary['primary_family_size']==4 and summary['predicted_directions']==dict(zip(names,directions,strict=True))
    assert summary['fresh_sources']==(mode=='scientific') and not summary['cohort_reused']
    assert summary['additional_rewrites']==1 and not summary['old_observations_pooled']
    return len(expected)


def report(summary):
    stats=summary['statistics']
    def fmt(key,scale=1):
        r=stats[key]
        return f'{scale*r["mean"]:.4f} [{scale*r["interval"][0]:.4f}, {scale*r["interval"][1]:.4f}]'
    lines=['# E077 fresh reconstruction tradeoff','',summary['status'],'',
        'All source cases retained. New source generation; matched readers at both endpoints.',
        'The four-direction prediction requires every adjusted interval in its declared direction.','',
        '| Primary mixture effect | Points [98.75%] | Predicted | Observed direction |',
        '| --- | ---: | --- | --- |']
    for name in PRIMARY:
        lines.append('| '+name+' | '+fmt('effect/both/pooled/'+name,100)+' | '+summary['predicted_directions'][name]+' | '+str(summary['primary_effects'][name])+' |')
    lines+=['','| Condition | Successes | Success % [95%] | Aligned transfer [95%] |','| --- | ---: | ---: | ---: |']
    n=summary['lineages_per_slot']
    for label in SLOTS:
        lines.append(f'| {label} | {round(stats["native/both/"+label]["mean"]*n)}/{n} | {fmt("native/both/"+label,100)} | {fmt("native/aligned_transfer/"+label)} |')
    if 'individual_counts' in summary:
        q=summary['individual_counts']['mixture_pooled']
        lines+=['','| Paired mixture comparison | Gains | Harms |','| --- | ---: | ---: |']
        for name,row in q['comparisons'].items():lines.append(f'| {name} | {row["gained"]} | {row["lost"]} |')
        lines+=['','Immediate/later effect table (harm, unchanged, benefit on both axes):',
                str(q['h0_rows_h1_columns']),f'Cases harmed at either pruning endpoint: {q["harmed_at_either_endpoint"]}.']
    lines+=['','Both endpoints, all gains and individual harms remain part of the result.',
        'Whole blocks are independent; recipients, histories and connections are nested observations.',
        'Other intervals are secondary pointwise 95%. Unresolved is not equivalence.',
        'Magnitude changes include natural renormalization. Donor records are externally supplied.',
        'No autonomous repair, unique writer-branch mediation or robustness beyond the declared apparatus is established.',
        'Interpret after independent replay, figure inspection and artifact closeout.','']
    return '\n'.join(lines)
