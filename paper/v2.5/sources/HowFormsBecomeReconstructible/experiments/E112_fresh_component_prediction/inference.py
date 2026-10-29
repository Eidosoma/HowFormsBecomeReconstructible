"""One frozen primary; source-cluster uncertainty and complete individual harms."""
import itertools
import numpy as np
from common import rng
from E098_writer_pairing_tradeoff.plan import ENDPOINTS, CONTRASTS as ORIGINAL_CONTRASTS
from E105_cycle_input_control.inference import statistics, decision, fmt
from E111_halfway_component_cross.inference import metric_keys, outcomes
from E112_fresh_component_prediction.plan import settings, CONDITIONS, METRICS, SCOPES, PRIMARY, key, identity


def original_outcomes(rows):
    result = {}
    for contrast in ORIGINAL_CONTRASTS:
        k = contrast+'_both'; grouped = {}
        for r in rows: grouped.setdefault(identity(r),[]).append(r)
        paired = [sorted(v,key=lambda x:x['draw']) for v in grouped.values() if len(v)==2]
        result[contrast] = dict(distribution={str(v):sum(r[k]==v for r in rows) for v in range(-2,3)},
            gain_identities=[list(key(r)) for r in rows if r[k]>0],
            harm_identities=[list(key(r)) for r in rows if r[k]<0],
            draw_recurrence={f'{a},{b}':sum(p[0][k]==a and p[1][k]==b for p in paired)
                             for a,b in itertools.product(range(-2,3),repeat=2)})
        assert sum(result[contrast]['distribution'].values())==len(rows)
        assert sum(result[contrast]['draw_recurrence'].values())==len(paired)
    return result


def summarize(mode, rows, original):
    cfg=settings(mode); blocks=cfg['blocks']; n=len(blocks)
    expected={(b,a,f,r,d) for b in blocks for a in range(4) for f in range(4)
              for r in range(cfg['recipients']) for d in (0,1)}
    assert len(rows)==len(original)==len(expected)
    assert {key(r) for r in rows}=={key(r) for r in original}==expected
    sample=rng('E112','frozen_symmetric_prediction').integers(0,n,(cfg['bootstrap_samples'],n))
    resamples=np.array([np.bincount(a,minlength=n) for a in sample],float)
    s=dict(mode=mode,independent_blocks=n,new_source_blocks=n if mode=='scientific' else 0,
        excluded_data_only=mode=='benchmark',context_draw_rows=len(rows),record_contexts=len(rows)//2,
        eligible_rows=sum(r['eligible'] for r in rows),longer_witness_rows=sum(r['longer_witness'] for r in rows),
        empty_witness_rows=sum(r['empty_witness'] for r in rows),groups={},original_groups={},
        primary_key=PRIMARY,primary_group=cfg['primary_group'],confidence=.95,bootstrap_samples=10000,
        inference_unit='whole source block; pooled row-weighted ratio within eligible mixture cases',
        independent_block_sums_checked=0,old_scientific_cases_pooled=False,
        secondary_intervals='pointwise exploratory, not simultaneous',automatic_successor=False)
    original_keys=[p+'_'+m for p in tuple(ENDPOINTS)+tuple(ORIGINAL_CONTRASTS) for m in METRICS]
    for kind,history,draw in itertools.product(('native','mixture'),('pooled','sham','pulse'),('pooled','0','1')):
        def choose(items):
            return [r for r in items if r['kind']==kind and (history=='pooled' or r['history']==history)
                    and (draw=='pooled' or r['draw']==int(draw))]
        part=choose(rows); group={}; label=kind+'/'+history+'/'+draw
        for scope in SCOPES:
            chosen=part if scope=='all' else [r for r in part if r[scope]]
            prefixes=('delta',) if scope=='all' else ('C','F','delta')
            keys=metric_keys(prefixes)+['gross_shared_minus_cue_'+p+'_'+m for p in prefixes for m in METRICS]
            stat,checked=statistics(chosen,blocks,resamples,keys)
            s['independent_block_sums_checked']+=checked
            stat.update(coverage=len(chosen)/len(part),unique_contexts=len({identity(r) for r in chosen}),
                        outcomes=outcomes(chosen))
            group[scope]=stat
        s['groups'][label]=group
        old=choose(original); st,checked=statistics(old,blocks,resamples,original_keys)
        st['outcomes']=original_outcomes(old); s['original_groups'][label]=st
        s['independent_block_sums_checked']+=checked
    g=s['groups']['mixture/pooled/pooled']['eligible']; stat=g['statistics'][PRIMARY]
    s['primary']=dict(**stat,decision=decision(stat),eligible_rows=g['rows'],nonempty_blocks=g['nonempty_blocks'],
        bootstrap_valid=g['bootstrap_valid'],bootstrap_empty=g['bootstrap_empty'],
        confirmatory=mode=='scientific',criterion='two-sided 95% interval lower bound > 0',
        qualification='natural-size whole-state swaps; no equal-amplitude or general biological claim')
    s['criterion_met']=mode=='scientific' and s['primary']['decision']=='POSITIVE'
    # All contrasts and both absolute records survive in cases.csv; this file is
    # the subset with any C/F discordance, never an outcome-selected denominator.
    events=[r for r in rows if r['measured'] and any(r[c+'_delta_both'] for c in CONDITIONS)]
    return s,events


def report(s):
    p=s['primary'];lines=['# E112: prospective shared-versus-cue sensitivity','',
        ('EXCLUDED TECHNICAL DATA ONLY.' if s['excluded_data_only'] else 'Fresh-source scientific cohort.'),
        f"All {s['independent_blocks']} source blocks and {s['context_draw_rows']} context/injury rows retained.",
        f"Eligible rows: {s['eligible_rows']}; empty witnesses: {s['empty_witness_rows']}; longer witnesses: {s['longer_witness_rows']}.",
        'O/N label two independent noise streams of the same law, with the original O birth fixed.',
        'Condition letters are shared component m, cue component d, and later noise.',
        'The sole primary is gross m minus gross d sensitivity of C−F success, in eligible mixture cases.',
        f"Primary estimate (percentage points): {fmt(p,100)}. Decision: {p['decision']}.",
        'A positive lower 95% bound supports the prediction; an interval crossing zero is unresolved.',
        'A wholly negative interval supports the opposite ordering. There is no extension based on the answer.','',
        '| Eligible group | Gross m sensitivity (points) | Gross d sensitivity (points) | Difference (points) |',
        '| --- | ---: | ---: | ---: |']
    for kind in ('native','mixture'):
        st=s['groups'][kind+'/pooled/pooled']['eligible']['statistics']
        lines.append('| '+kind+' | '+' | '.join(fmt(st[k],100) for k in
            ('pooled_gross_shared_delta_both','pooled_gross_cue_delta_both',PRIMARY))+' |')
    lines+=['','| Group / condition | C success % | F success % | C−F points | Sign-flip losses | Sign-flip gains |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
    for kind,c in itertools.product(('native','mixture'),CONDITIONS):
        g=s['groups'][kind+'/pooled/pooled']['eligible'];st=g['statistics'];out=g['outcomes']['conditions'][c]['distribution']
        lines.append('| '+kind+'/'+c+' | '+' | '.join(fmt(st[c+'_'+v+'_both'],100) for v in ('C','F','delta'))+
                     f" | {out['1']} | {out['-1']} |")
    lines+=['','| Group / earlier endpoint | Intact success % | Pruned success % | Pruned−intact points |',
            '| --- | ---: | ---: | ---: |']
    for kind in ('native','mixture'):
        st=s['original_groups'][kind+'/pooled/pooled']['statistics']
        for stage,i,p,c in (('immediate','I0','P0','pruning_h0'),('after paired rewrite','I1_paired','P1_paired','pruning_paired'),
                            ('after independent rewrite','I1_independent','P1_independent','pruning_independent')):
            lines.append('| '+kind+'/'+stage+' | '+' | '.join(fmt(st[x+'_both'],100) for x in (i,p,c))+' |')
    lines+=['','All earlier endpoint scores and individual gains/harms are in original_cases.csv and original_events.csv.',
        'Both injury draws, failure classes, signed transfer, margins, effective normalized coupling, and all absolute C/F outcomes are retained.',
        'Both half-history sources and six additional late continuations were independently replayed; no invented missing-case outcomes.',
        'Unqualified witnesses receive no intervention and an exact zero contrast; their absolute crossed-reader outcomes are unmeasured.',
        'Only the mixture gross-sensitivity difference is primary. All other intervals are pointwise exploratory.',
        'Shared and cue swaps have their naturally different sizes. This does not isolate intrinsic importance per unit perturbation.',
        'The engineered apparatus retains paired cue noise, fixed resets, ideal normalization and floating-point precision.',
        'No sequential stopping, old-cohort pooling, automatic extension, restart or successor.','']
    return '\n'.join(lines)


def plot(run,s):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    def draw(ax,x,stat,color,label=None):
        if stat['mean'] is None:return
        m=100*stat['mean'];lo,hi=np.array(stat['ci95'])*100
        ax.errorbar(x,m,yerr=[[max(0,m-lo)],[max(0,hi-m)]],fmt='o',color=color,capsize=3,label=label)
    for row,kind in enumerate(('native','mixture')):
        st=s['groups'][kind+'/pooled/pooled']['eligible']['statistics'];ax=axes[row,0]
        for i,(k,color) in enumerate((('pooled_gross_shared_delta_both','tab:blue'),
                ('pooled_gross_cue_delta_both','tab:orange'),(PRIMARY,'tab:purple'))): draw(ax,i,st[k],color)
        ax.set_xticks(range(3),['Shared m','Cue d','m − d']);ax.axhline(0,c='.6',lw=.7)
        ax.set_ylabel('Success sensitivity (points)');ax.set_title(kind.capitalize()+(' — primary difference' if kind=='mixture' else ' — secondary'))
        ax=axes[row,1]
        for i,c in enumerate(CONDITIONS):
            for j,(v,color) in enumerate((('C','tab:blue'),('F','tab:orange'))):
                draw(ax,i+(j-.5)*.18,st[c+'_'+v+'_both'],color,v if i==0 else None)
        ax.set_xticks(range(8),CONDITIONS,rotation=45);ax.set_ylim(-2,102);ax.set_ylabel('Eligible success (%)');ax.legend()
        ax.set_title('All fresh crossed-reader outcomes');ax=axes[row,2]
        old=s['original_groups'][kind+'/pooled/pooled']['statistics']
        for i,(a,b) in enumerate((('I0','P0'),('I1_paired','P1_paired'),('I1_independent','P1_independent'))):
            for j,(v,color) in enumerate(((a,'tab:green'),(b,'tab:red'))):
                draw(ax,i+(j-.5)*.18,old[v+'_both'],color,('Intact','Pruned')[j] if i==0 else None)
        ax.set_xticks(range(3),['Immediate','Paired rewrite','Independent\nrewrite']);ax.set_ylim(-2,102)
        ax.set_ylabel('All-case success (%)');ax.set_title('Earlier functional endpoints retained');ax.legend()
        for ax in axes[row]:ax.grid(axis='y',alpha=.15)
    title='E112: does the component-sensitivity ordering predict fresh records?'
    if s['excluded_data_only']:title+='\nEXCLUDED TECHNICAL DATA'
    fig.suptitle(title)
    fig.text(.5,.01,'95% whole-source intervals. One mixture primary; other comparisons exploratory. Natural-size swaps, original birth fixed.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.93));fig.savefig(run/'endpoints.png',dpi=150);fig.savefig(run/'endpoints.pdf');plt.close(fig)
