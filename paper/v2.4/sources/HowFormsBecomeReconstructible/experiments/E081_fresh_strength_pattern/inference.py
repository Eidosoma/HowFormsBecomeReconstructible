"""Single matched-total fresh-source prediction with paired whole-block inference."""
import numpy as np
from common import rng
from E081_fresh_strength_pattern.plan import SLOTS, STARTS, PRIMARY, PREDICTED, CONFIDENCE

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
        values=dict(pruning_h0=p0-i0,pruning_h1=p1-i1,ordinary_vs_pruned=m1-p1,filtered_vs_pruned=j1-p1,
            pattern_gain=j1-m1,pruning_advantage_change=(p1-i1)-(p0-i0),
            intact_temporal=i1-i0,pruned_temporal=p1-p0,filtered_vs_intact=j1-i1,
            I0_over_erased=i0-x[...,8],P0_over_erased=p0-x[...,8],
            I1_over_erased=i1-x[...,17],P1_over_erased=p1-x[...,17],
            OF_over_erased=m1-x[...,17],FF_over_erased=j1-x[...,17])
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
        return 'FRESH_MATCHED_TOTAL_PATTERN_CONFIRMED'
    if any(labels[k] not in (v,'UNRESOLVED') for k,v in zip(PRIMARY,PREDICTED,strict=True)):
        return 'PREDICTED_PATTERN_CONTRADICTED'
    return 'PREDICTED_PATTERN_UNRESOLVED'


def analyze(cases,controls,mode):
    B=len(cases);draws=rng('E081','strength_pattern','bootstrap').integers(0,B,(10000,B))
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
        primary_family_size=1,primary_confidence=CONFIDENCE,primary_arm_weighting='equal_within_block',
        source_boundary=1,additional_rewrites=1,fresh_sources=mode=='scientific',
        cohort_reused=False,prior_E073_through_E080_results_known=True,old_observations_pooled=False,
        statistics=stats)


def audit(cases,controls,summary,mode):
    from E015_functional_inheritance.audit import random
    B=len(cases);draws=random('E081','strength_pattern','bootstrap').integers(0,B,size=(10000,B))
    pools={}
    for start,name in ((0,'I0'),(4,'P0'),(9,'I1'),(13,'P1'),(18,'OF'),(22,'FF')):
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
                        ('pruning_h0',p0-i0),('pruning_h1',p1-i1),('ordinary_vs_pruned',m-p1),('filtered_vs_pruned',j-p1),
                        ('pattern_gain',j-m),('pruning_advantage_change',(p1-i1)-(p0-i0)),
                        ('intact_temporal',i1-i0),('pruned_temporal',p1-p0),('filtered_vs_intact',j-i1),
                        ('I0_over_erased',i0-x[8]),('P0_over_erased',p0-x[8]),
                        ('I1_over_erased',i1-x[17]),('P1_over_erased',p1-x[17]),
                        ('OF_over_erased',m-x[17]),('FF_over_erased',j-x[17])):
                        add(f'effect/{metric}/{history}/{kind}_{name}',value)
    assert set(expected)==set(summary['statistics'])
    names=('mixture_pattern_gain',)
    for key,samples in expected.items():
        x=np.array(samples);r=summary['statistics'][key]
        confidence=.95 if key in tuple('effect/both/pooled/'+n for n in names) else .95
        a=(1-confidence)/2
        np.testing.assert_array_equal(r['block_means'],x)
        assert r['mean']==x.mean() and r['confidence']==confidence
        np.testing.assert_array_equal(r['interval'],np.quantile(x[draws].mean(axis=1),[a,1-a]))
    ok=all(c['pass'] for c in controls);enabled=mode=='scientific' and ok;labels={}
    for name in names:
        lo,hi=summary['statistics'][f'effect/both/pooled/{name}']['interval']
        labels[name]=('POSITIVE_EFFECT' if lo>0 else 'NEGATIVE_EFFECT' if hi<0 else 'UNRESOLVED') if enabled else None
    directions=('POSITIVE_EFFECT',)
    match=all(labels[n]==d for n,d in zip(names,directions,strict=True))
    contradiction=any(labels[n] in ('POSITIVE_EFFECT','NEGATIVE_EFFECT') and labels[n]!=d
                      for n,d in zip(names,directions,strict=True))
    status=('TECHNICAL_ONLY' if mode!='scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else
            'FRESH_MATCHED_TOTAL_PATTERN_CONFIRMED' if match else
            'PREDICTED_PATTERN_CONTRADICTED' if contradiction else 'PREDICTED_PATTERN_UNRESOLVED')
    assert summary['status']==status and summary['controls_pass']==ok
    assert summary['prediction_supported']==(match if enabled else None)
    assert summary['primary_effects']==labels and summary['primary_confidence']==.95
    assert summary['primary_family_size']==1 and summary['predicted_directions']==dict(zip(names,directions,strict=True))
    assert summary['fresh_sources']==(mode=='scientific') and not summary['cohort_reused']
    assert summary['additional_rewrites']==1 and not summary['old_observations_pooled']
    return len(expected)


def report(summary):
    stats=summary['statistics']
    def fmt(key,scale=1):
        v=stats[key]
        return f'{scale*v["mean"]:.4f} [{scale*v["interval"][0]:.4f}, {scale*v["interval"][1]:.4f}]'
    lines=['# E081 fresh matched-total pattern confirmation','',summary['status'],'',
        'Primary: FF−OF mixture both-cue success at the same filtered selected total.',
        'OF uses ordinary magnitudes rescaled to that total; FF uses filtered magnitudes.',
        'Both use ordinary signs from the same intact body, original support and P1 outside bytes.',
        'All sources newly generated. Both pruning endpoints are new secondary observations, not reused outcomes.','',
        '| Primary effect | Points [95%] | Direction |','| --- | ---: | --- |']
    for name in PRIMARY:lines.append('| '+name+' | '+fmt('effect/both/pooled/'+name,100)+' | '+str(summary['primary_effects'][name])+' |')
    lines+=['','| Mixture condition | Successes | Success % [95%] | Selected total [95%] | Postinjury selected coupling share [95%] |',
        '| --- | ---: | ---: | ---: | ---: |']
    n=2*summary['lineages_per_slot']
    for c in ('I0','P0','I1','P1','OF','FF'):
        label=c+'_mixture_pooled'
        lines.append(f'| {c} | {round(stats["native/both/"+label]["mean"]*n)}/{n} | {fmt("native/both/"+label,100)} | {fmt("native/selected_mass/"+label)} | {fmt("native/postinjury_selected_coupling_share/"+label)} |')
    lines+=['','| Secondary mixture effect | Success points [95%] |','| --- | ---: |']
    for name in ('pruning_h0','pruning_h1','ordinary_vs_pruned','filtered_vs_pruned','pruning_advantage_change'):
        lines.append('| '+name+' | '+fmt('effect/both/pooled/mixture_'+name,100)+' |')
    lines+=['','| Pattern response effect, secondary | Difference [95%] |','| --- | ---: |']
    for metric in ('minimum_margin','aligned_transfer'):
        lines.append('| '+metric+' | '+fmt('effect/'+metric+'/pooled/mixture_pattern_gain')+' |')
    q=summary['individual_counts']['mixture_pooled']
    lines+=['','| Paired mixture comparison | Gains | Harms |','| --- | ---: | ---: |']
    for name,row in q['comparisons'].items():lines.append(f'| {name} | {row["gained"]} | {row["lost"]} |')
    lines+=['','Immediate/later pruning table, rows/columns harm/unchanged/benefit:',str(q['h0_rows_h1_columns']),
        f'Cases harmed at either pruning endpoint: {q["harmed_at_either_endpoint"]}.',
        f'Immediate beneficiaries later harmed: {q["immediate_benefit_later_harm"]}.','',
        '| All reader slots | Success % [95%] | Aligned transfer [95%] |','| --- | ---: | ---: |']
    for label in SLOTS:lines.append('| '+label+' | '+fmt('native/both/'+label,100)+' | '+fmt('native/aligned_transfer/'+label)+' |')
    lines+=['','Only pooled mixture FF−OF success is primary; all other intervals are pointwise secondary 95%.',
        'Whole source blocks are independent; histories, founders, recipients and edges are nested.',
        'Global selected totals are matched before injury. Local denominators, surviving totals and outside normalized coupling can differ.',
        'Finite weights above one are allowed and recorded. No clipping, support repair, outcome selection or excluded high-weight cases.',
        'A numerical/support failure suppresses the primary claim and preserves available endpoints.',
        'Unresolved is not equivalence. A positive result does not prove autonomous repair, persistence or a unique normalization mechanism.',
        'Interpret after independent replay, figure inspection and closeout.','']
    return '\n'.join(lines)

