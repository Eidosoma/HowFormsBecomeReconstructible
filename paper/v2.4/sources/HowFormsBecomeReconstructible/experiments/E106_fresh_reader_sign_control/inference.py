"""One fixed prediction; clustered conditional estimates and individual outcomes."""
import itertools
import math
import numpy as np
from common import rng
from E106_fresh_reader_sign_control import data
from E106_fresh_reader_sign_control.plan import settings,VARIANTS,CONTRASTS,METRICS,PRIMARY,SCOPES

IDENTIFIERS=('task','arm','kind','history','founder','recipient','draw')


def decision(stat):
    if stat['ci95'] is None:return 'UNRESOLVED'
    lo,hi=stat['ci95']
    return 'POSITIVE' if lo>0 else 'NEGATIVE' if hi<0 else 'UNRESOLVED'


def statistics(rows,blocks,resamples,keys):
    values=np.array([[float(r[k]) for k in keys] for r in rows],float).reshape(len(rows),len(keys))
    task=np.array([int(r['task']) for r in rows]);counts=np.array([(task==b).sum() for b in blocks],int)
    sums=np.array([values[task==b].sum(0) for b in blocks])
    scalar=np.array([[math.fsum(float(v) for v in col) for col in values[task==b].T] for b in blocks])
    np.testing.assert_allclose(sums,scalar,rtol=2e-12,atol=3e-13)
    den=resamples@counts;valid=den>0;samples=(resamples@sums)[valid]/den[valid,None]
    bounds=np.quantile(samples,[.025,.975],axis=0) if valid.any() else None
    stats={k:dict(mean=float(sums[:,j].sum()/counts.sum()) if counts.sum() else None,
        ci95=bounds[:,j].tolist() if bounds is not None else None,block_sums=sums[:,j].tolist()) for j,k in enumerate(keys)}
    return dict(rows=len(rows),nonempty_blocks=int((counts>0).sum()),block_counts=counts.tolist(),
        bootstrap_valid=int(valid.sum()),bootstrap_empty=int((~valid).sum()),statistics=stats),sums.size


def outcomes(rows):
    bits=np.array([[int(r[v+'_both']) for v in VARIANTS] for r in rows],int).reshape(-1,4)
    assert np.isin(bits,[0,1]).all()
    coded=bits@np.array([8,4,2,1]);joint={}
    for code in range(16):
        label=format(code,'04b');n=int((coded==code).sum())
        assert n==sum(''.join(str(int(r[v+'_both'])) for v in VARIANTS)==label for r in rows)
        joint[label]=n
    events={}
    for name in CONTRASTS:
        key=name+'_both';distribution={str(d):sum(int(r[key])==d for r in rows) for d in range(-2,3)}
        assert sum(distribution.values())==len(rows)
        assert sum(d*distribution[str(d)] for d in range(-2,3))==sum(r[key] for r in rows)
        by_context={}
        for r in rows:by_context.setdefault(data.identity(r),[]).append(r)
        paired=[sorted(part,key=lambda r:int(r['draw'])) for part in by_context.values() if len(part)==2]
        recurrence={f'{a},{b}':sum(int(p[0][key])==a and int(p[1][key])==b for p in paired)
            for a,b in itertools.product(range(-2,3),repeat=2)}
        assert sum(recurrence.values())==len(paired)
        events[name]=dict(distribution=distribution,positive=sum(distribution[str(i)] for i in (1,2)),
            negative=sum(distribution[str(i)] for i in (-1,-2)),zero=distribution['0'],
            positive_identities=[list(data.identity(r)+(int(r['draw']),)) for r in rows if r[key]>0],
            negative_identities=[list(data.identity(r)+(int(r['draw']),)) for r in rows if r[key]<0],
            paired_contexts=len(paired),draw_recurrence=recurrence)
    return dict(joint_success_order='D W C F',joint_success=joint,contrasts=events)


def repeat_outcomes(rows):
    out={}
    for name in CONTRASTS:
        key=name+'_both';old=np.array([int(r['previous_'+key]) for r in rows]);new=np.array([int(r[key]) for r in rows])
        assert np.isin(old,range(-2,3)).all() and np.isin(new,range(-2,3)).all()
        counts={};identities={}
        scalar={f'{a},{b}':0 for a,b in itertools.product(range(-2,3),repeat=2)}
        for r in rows:scalar[f"{int(r['previous_'+key])},{int(r[key])}"]+=1
        for a,b in itertools.product(range(-2,3),repeat=2):
            label=f'{a},{b}';sel=(old==a)&(new==b);counts[label]=int(sel.sum());assert counts[label]==scalar[label]
            if a or b:identities[label]=[list(data.identity(r)+(int(r['draw']),)) for r,keep in zip(rows,sel) if keep]
        assert sum(counts.values())==len(rows)
        out[name]=dict(transition_order='previous E105, fresh E106 under the same stored injury',counts=counts,
            identities=identities,previous_positive=int((old>0).sum()),previous_negative=int((old<0).sum()),
            positive_persisted=int(((old>0)&(new>0)).sum()),positive_disappeared=int(((old>0)&(new==0)).sum()),
            positive_reversed=int(((old>0)&(new<0)).sum()),new_positive=int(((old<=0)&(new>0)).sum()),
            negative_persisted=int(((old<0)&(new<0)).sum()),negative_disappeared=int(((old<0)&(new==0)).sum()),
            negative_reversed=int(((old<0)&(new>0)).sum()),new_negative=int(((old>=0)&(new<0)).sum()))
    return out


def summarize(mode,rows):
    cfg=settings(mode);blocks=cfg['blocks'];n=len(blocks)
    idx=rng('E106','fresh_reader_bootstrap').integers(0,n,(cfg['bootstrap_samples'],n))
    resamples=np.array([np.bincount(a,minlength=n) for a in idx],float)
    keys=[k for k,v in rows[0].items() if k not in IDENTIFIERS and isinstance(v,(int,float,bool,np.number,np.bool_))]
    expected={(b,a,f,r,d) for b in blocks for a in range(4) for f in range(4) for r in range(cfg['recipients']) for d in (0,1)}
    assert len(rows)==len(expected) and {data.identity(r)+(r['draw'],) for r in rows}==expected
    result=dict(mode=mode,independent_blocks=n,record_contexts=len(rows)//2,context_draw_rows=len(rows),
        evaluated_context_draws=sum(r['evaluated'] for r in rows),groups={},independent_block_sums_checked=0,
        bootstrap_samples=cfg['bootstrap_samples'],confidence=.95,new_source_blocks=0,new_reader_nuisances=True,
        new_injuries=False,old_outcomes_cached=False,old_new_outcomes_pooled=False,
        source_outcomes_previously_known=True,writer_dynamics_repeated=False,primary_key=PRIMARY,
        primary_group='mixture/pooled/pooled/eligible',secondary_intervals='pointwise; not simultaneous')
    for kind,history,draw in itertools.product(('native','mixture'),('pooled','sham','pulse'),('pooled','0','1')):
        part=[r for r in rows if r['kind']==kind and (history=='pooled' or r['history']==history)
              and (draw=='pooled' or int(r['draw'])==int(draw))]
        group={}
        for scope in SCOPES:
            chosen=[r for r in part if scope=='all' or r[scope]]
            stat,checked=statistics(chosen,blocks,resamples,keys)
            stat.update(all_rows=len(part),coverage=len(chosen)/len(part),unique_contexts=len({data.identity(r) for r in chosen}),
                        outcomes=outcomes(chosen),repeat_outcomes=repeat_outcomes(chosen))
            group[scope]=stat;result['independent_block_sums_checked']+=checked
        result['groups'][kind+'/'+history+'/'+draw]=group
    p=result['groups']['mixture/pooled/pooled']['eligible']['statistics'][PRIMARY]
    result['primary']=dict(**p,decision=decision(p),eligible_rows=result['groups']['mixture/pooled/pooled']['eligible']['rows'])
    events=[];repeat_events=[]
    for r in rows:
        for name in CONTRASTS:
            if r[name+'_both']:
                events.append(dict(**{k:r[k] for k in IDENTIFIERS+('eligible','affected','evaluated')},contrast=name,
                    direction='positive' if r[name+'_both']>0 else 'negative',delta=r[name+'_both'],
                    **{v+'_'+m:r[v+'_'+m] for v in VARIANTS for m in METRICS}))
            if r[name+'_both'] or r['previous_'+name+'_both']:
                repeat_events.append(dict(**{k:r[k] for k in IDENTIFIERS+('eligible','affected','evaluated')},contrast=name,
                    previous_delta=r['previous_'+name+'_both'],fresh_delta=r[name+'_both'],
                    **{prefix+v+'_'+m:r[prefix+v+'_'+m] for prefix in ('','previous_') for v in VARIANTS for m in METRICS}))
    return result,events,repeat_events


def fmt(stat,scale=1):
    if stat['mean'] is None:return 'NA'
    lo,hi=stat['ci95'];return f"{stat['mean']*scale:.3f} [{lo*scale:.3f}, {hi*scale:.3f}]"


def report(s):
    lines=['# E106 fresh-reader repeat of the matched-weight sign comparison','',
        f"Mode: {s['mode']}. Known source records and stored injuries; fresh E106 birth/noise, including a new D baseline for every row.",
        f"All {s['independent_blocks']} blocks, {s['record_contexts']} contexts and {s['context_draw_rows']} context/draw rows retained.",
        'D/W use original cycle magnitudes; C/F use one common arithmetic-mean magnitude. D/C keep signs; W/F flip them.',
        'C/F preserve every cell’s sorted positive and negative incident-weight multisets, before and after injury.','',
        f"**Primary: {s['primary']['decision']}**, eligible pooled-mixture C−F success: {fmt(s['primary'],100)} percentage points (95% whole-source interval).",
        'Only new outcomes enter the primary. Reader robustness on known source records; unresolved does not mean equivalent.','',
        '| Group / scope | Rows | D success % | W success % | C success % | F success % |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for kind,scope in itertools.product(('native','mixture'),('all','eligible','affected')):
        g=s['groups'][kind+'/pooled/pooled'][scope]
        lines.append('| '+kind+'/'+scope+' | '+str(g['rows'])+' | '+' | '.join(fmt(g['statistics'][v+'_both'],100) for v in VARIANTS)+' |')
    lines+=['','| Group / scope | D−W points | C−F points | C−D baseline change | F−W change | Interaction |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for kind,scope in itertools.product(('native','mixture'),('all','eligible')):
        g=s['groups'][kind+'/pooled/pooled'][scope]
        lines.append('| '+kind+'/'+scope+' | '+' | '.join(fmt(g['statistics'][c+'_both'],100) for c in CONTRASTS)+' |')
    lines+=['','| Eligible group / contrast | Positive cases | Negative cases | Zero cases |',
        '| --- | ---: | ---: | ---: |']
    for kind,c in itertools.product(('native','mixture'),CONTRASTS):
        z=s['groups'][kind+'/pooled/pooled']['eligible']['outcomes']['contrasts'][c]
        lines.append(f"| {kind}/{c} | {z['positive']} | {z['negative']} | {z['zero']} |")
    lines+=['','| Eligible group | E105 C−F points, historical | Fresh C−F points | Fresh−previous points | Old positive cases recurring / disappearing / reversing |',
        '| --- | ---: | ---: | ---: | --- |']
    for kind in ('native','mixture'):
        g=s['groups'][kind+'/pooled/pooled']['eligible'];st=g['statistics'];e=g['repeat_outcomes']['matched_arrangement']
        lines.append('| '+kind+' | '+f"{100*st['previous_matched_arrangement_both']['mean']:.3f}"+' | '+fmt(st[PRIMARY],100)+
            ' | '+fmt(st['repeat_change_both'],100)+f" | {e['positive_persisted']} / {e['positive_disappeared']} / {e['positive_reversed']} |")
    lines+=['','Positive D−W/C−F means keeping signs helps; positive C−D means equalization helps.',
        'Every individual event and zero remains; both earlier endpoints remain in original_cases.csv unchanged.',
        'Conditional intervals are ratios of resampled source sums/counts, retaining zero-eligible blocks.',
        'The C baseline can differ from D: C/F does not isolate the original-magnitude effect or a unique loop mediator.',
        'Matched static weight budgets do not fix activity-dependent input, which depends on the contributing neighbours.',
        'Old/new transitions compare the same record and stored injury, with independently seeded birth/noise.',
        'All identical-packet W/C/F outcomes derive from the same row’s new D read; no historical absolute score is reused.',
        'No new writer, source, injury, source selection, automatic extension or successor.','']
    return '\n'.join(lines)


def plot(run,s):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(15,8))
    for row,kind in enumerate(('native','mixture')):
        groups=s['groups'][kind+'/pooled/pooled']
        ax=axes[row,0]
        for j,(scope,color) in enumerate((('all','tab:blue'),('eligible','tab:orange'))):
            for i,v in enumerate(VARIANTS):
                st=groups[scope]['statistics'][v+'_both']
                if st['mean'] is None:continue
                y=100*st['mean'];lo,hi=np.array(st['ci95'])*100
                ax.errorbar(i+(j-.5)*.18,y,yerr=[[max(0,y-lo)],[max(0,hi-y)]],fmt='o',color=color,capsize=3,label=scope if i==0 else None)
        ax.set_xticks(range(4),VARIANTS);ax.set_ylabel('Success (%)');ax.set_ylim(-2,102);ax.legend()
        ax=axes[row,1]
        for i,c in enumerate(('original_arrangement','matched_arrangement','equalization_cost')):
            st=groups['eligible']['statistics'][c+'_both']
            if st['mean'] is None:continue
            y=100*st['mean'];lo,hi=np.array(st['ci95'])*100
            ax.errorbar(i,y,yerr=[[max(0,y-lo)],[max(0,hi-y)]],fmt='o',capsize=4,color='tab:orange')
        ax.set_xticks(range(3),['D−W','C−F','C−D']);ax.set_ylabel('Eligible success difference (points)');ax.axhline(0,c='.5',lw=.7)
        ax=axes[row,2]
        for j,(key,color) in enumerate((('positive','tab:green'),('negative','tab:red'))):
            vals=[groups['eligible']['outcomes']['contrasts'][c][key] for c in ('original_arrangement','matched_arrangement','equalization_cost')]
            ax.bar(np.arange(3)+(j-.5)*.32,vals,width=.3,color=color,label=key)
        ax.set_xticks(range(3),['D−W','C−F','C−D']);ax.set_ylabel('Eligible context/draw cases');ax.legend()
        for ax in axes[row]:ax.set_title(kind.capitalize());ax.grid(axis='y',alpha=.15)
    fig.suptitle('E106: matched-weight sign comparison under fresh reader birth/noise'+(' — EXCLUDED TECHNICAL DATA' if s['mode']=='benchmark' else ''))
    fig.text(.5,.015,'95% whole-source intervals. Only fresh eligible pooled-mixture C−F success is primary. Known sources and stored injuries; new baselines.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(run/'comparison.png',dpi=150);fig.savefig(run/'comparison.pdf');plt.close(fig)
