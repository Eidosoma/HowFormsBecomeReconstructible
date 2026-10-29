"""Whole-source-block inference and complete endpoint/event tables."""
from collections import defaultdict
import math
import numpy as np
from common import rng
from E098_writer_pairing_tradeoff.plan import settings, identity, expected_identities, CONTRASTS, PRIMARY, ENDPOINTS
from E098_writer_pairing_tradeoff.data import IDENTIFIERS

LABELS = ('both_fail','pruning_gain','pruning_harm','both_succeed')


def recurrence(rows):
    contexts = defaultdict(set)
    for r in rows: contexts[identity(r)].add(r['draw'])
    return dict(comparisons=len(rows), unique_contexts=len(contexts),
        independent_blocks=len({r['task'] for r in rows}),
        same_context_both_draws=sum(v == {0,1} for v in contexts.values()),
        identities=[dict(task=k[0],arm=k[1],founder=k[2],recipient=k[3],draws=sorted(v))
                    for k,v in sorted(contexts.items())])


def table(rows, noise):
    values = np.array([[r['I0_both'],r['P0_both'],r['I1_'+noise+'_both'],r['P1_'+noise+'_both']]
                       for r in rows],int)
    codes0, codes1 = 2*values[:,0]+values[:,1],2*values[:,2]+values[:,3]
    counts = np.bincount(4*codes0+codes1,minlength=16).reshape(4,4)
    independent = np.zeros((4,4),int)
    for r in rows:
        a = LABELS.index('both_succeed' if r['I0_both'] and r['P0_both'] else
            'pruning_harm' if r['I0_both'] else 'pruning_gain' if r['P0_both'] else 'both_fail')
        i,p = r['I1_'+noise+'_both'],r['P1_'+noise+'_both']
        b = LABELS.index('both_succeed' if i and p else 'pruning_harm' if i else 'pruning_gain' if p else 'both_fail')
        independent[a,b] += 1
    assert np.array_equal(counts,independent) and counts.sum() == len(rows)
    conditional = {}
    for j,label in enumerate(LABELS):
        denom = int(counts[j].sum())
        conditional[label] = dict(denominator=denom, empty=denom==0,
            later_gain_fraction=float(counts[j,1]/denom) if denom else None,
            later_harm_fraction=float(counts[j,2]/denom) if denom else None,
            later_harms=int(counts[j,2]),later_gains=int(counts[j,1]))
    return dict(labels=list(LABELS), counts=counts.tolist(), comparisons=len(rows), conditional=conditional,
        later_gains=recurrence([r for r in rows if r['pruning_'+noise+'_both']>0]),
        later_harms=recurrence([r for r in rows if r['pruning_'+noise+'_both']<0]))


def contrast_events(rows,name):
    values = [r[name+'_both'] for r in rows]
    out = dict(comparisons=len(rows),zero=sum(v==0 for v in values),
        distribution={str(v):values.count(v) for v in (-2.,-1.,0.,1.,2.)},
        positive=recurrence([r for r in rows if r[name+'_both']>0]),
        negative=recurrence([r for r in rows if r[name+'_both']<0]),
        interpretation='difference_of_differences' if name=='interaction' else 'positive_is_gain_negative_is_harm')
    assert sum(out['distribution'].values()) == len(rows)
    if name != 'interaction': assert not out['distribution']['-2.0'] and not out['distribution']['2.0']
    return out


def statistics(rows,keys,blocks,counts):
    matrix = np.array([[r[k] for k in keys] for r in rows],float)
    tasks = np.array([r['task'] for r in rows])
    means = np.array([matrix[tasks==b].mean(0) for b in blocks])
    other = np.array([[math.fsum(r[k] for r in rows if r['task']==b)/sum(r['task']==b for r in rows)
                      for k in keys] for b in blocks])
    np.testing.assert_allclose(means,other,rtol=2e-12,atol=3e-14)
    draws = counts@means/len(blocks)
    intervals = np.quantile(draws,[.0125,.025,.975,.9875],axis=0)
    out = {k:dict(mean=float(means[:,j].mean()),ci95=intervals[[1,2],j].tolist(),
                  block_means=means[:,j].tolist()) for j,k in enumerate(keys)}
    for k in PRIMARY:
        j = keys.index(k); out[k]['ci97_5'] = intervals[[0,3],j].tolist()
    return out,means.size


def classify(stat,reference=.03):
    lo,hi = stat['ci97_5']
    return dict(**stat, direction='POSITIVE' if lo>0 else 'NEGATIVE' if hi<0 else 'UNRESOLVED',
        practical_reference=reference,
        relative_to_reference='ABOVE' if lo>reference else 'BELOW' if hi<reference else 'OVERLAPS')


def decision(stats):
    primary = {k:classify(stats[k]) for k in PRIMARY}
    conjunction = all(v['direction']=='POSITIVE' for v in primary.values())
    baseline = stats['pruning_paired_both']; cost = baseline['ci95'][1]<0
    conclusion = ('PENALTY_ATTENUATED_WITH_PRUNED_IMPROVEMENT' if cost else
        'POSITIVE_INTERACTION_AND_GAIN_WITHOUT_DEMONSTRATED_BASELINE_PENALTY') if conjunction else 'PREDICTION_NOT_ESTABLISHED'
    return dict(primary=primary, conjunction_met=conjunction, paired_baseline=baseline,
        paired_baseline_cost_negative=cost, conclusion=conclusion)


def analyze(rows,mode):
    cfg = settings(mode); ids = [identity(r)+(r['draw'],) for r in rows]
    assert len(ids)==len(set(ids)) and set(ids)==expected_identities(cfg)
    blocks = cfg['blocks']; keys = [k for k in rows[0] if k not in IDENTIFIERS]
    indices = rng('E098','bootstrap').integers(0,len(blocks),(cfg['bootstrap_samples'],len(blocks)))
    counts = np.array([np.bincount(row,minlength=len(blocks)) for row in indices],float)
    result = dict(mode=mode, independent_source_blocks=len(blocks), record_contexts=len(rows)//2,
        context_draw_pairs=len(rows), primary_confidence=.975, secondary_confidence=.95,
        bootstrap_samples=cfg['bootstrap_samples'], groups={}, old_scientific_cases_pooled=False,
        independent_block_means_checked=0, automatic_extension=False, automatic_successor=False)
    # Draw-specific intervals are secondary. All resamples select whole source blocks.
    for kind in ('native','mixture'):
        for history in ('pooled','sham','pulse'):
            part = [r for r in rows if r['kind']==kind and (history=='pooled' or r['history']==history)]
            stats,n = statistics(part,keys,blocks,counts); result['independent_block_means_checked'] += n
            group = dict(blocks=blocks,comparisons=len(part),statistics=stats,
                tables={s:table(part,s) for s in ('paired','independent')},
                contrasts={c:contrast_events(part,c) for c in CONTRASTS}, by_draw={})
            draw_keys = [k for k in keys if not k.startswith('writer_')]
            for draw in (0,1):
                sub = [r for r in part if r['draw']==draw]
                st,n = statistics(sub,draw_keys,blocks,counts); result['independent_block_means_checked'] += n
                group['by_draw'][str(draw)] = dict(comparisons=len(sub),statistics=st)
            # Each supplying writer is counted once, independently of terminal draws.
            writers = [r for r in part if r['draw']==0]
            group['writer_contexts'] = len(writers)
            group['writer_noise_events'] = {}
            for policy in ('I','P'):
                for phase in ('end','window'):
                    key = 'writer_'+phase+'_'+policy
                    diffs = [r[key+'_independent_both']-r[key+'_paired_both'] for r in writers]
                    group['writer_noise_events'][phase+'_'+policy] = dict(contexts=len(writers),
                        gains=sum(x>0 for x in diffs),harms=sum(x<0 for x in diffs),unchanged=sum(x==0 for x in diffs))
            result['groups'][kind+'/'+history] = group
    result['decision'] = decision(result['groups']['mixture/pooled']['statistics'])
    result['primary_conclusion'] = result['decision']['conclusion'] if mode=='scientific' else 'EXCLUDED_TECHNICAL_ONLY'
    result['criterion_met'] = result['decision']['conjunction_met'] if mode=='scientific' else None
    result['endpoint_tables_checked'] = 12
    return result


def report(summary):
    lines = ['# E098 writer cue pairing', '', f"Mode: {summary['mode']}; **{summary['primary_conclusion']}**.",
        f"{summary['independent_source_blocks']} independent source blocks; {summary['record_contexts']} contexts; "
        f"{summary['context_draw_pairs']} terminal context/draw rows.",
        'One writer realization per context; two terminal draws share its records.', '',
        '| Pooled mixtures: primary contrast | Mean (pp) | Adjusted 97.5% interval (pp) | Direction |',
        '| --- | ---: | --- | --- |']
    for key,stat in summary['decision']['primary'].items():
        lo,hi = stat['ci97_5']; lines.append(f"| {key} | {100*stat['mean']:.3f} | [{100*lo:.3f}, {100*hi:.3f}] | {stat['direction']} |")
    lines += ['', '| Group | h0 P−I (pp) | Paired h1 P−I (pp) | Independent h1 P−I (pp) | Pruned noise gain (pp) |',
        '| --- | ---: | ---: | ---: | ---: |']
    for label,g in summary['groups'].items():
        vals = [g['statistics'][k+'_both']['mean']*100 for k in
                ('pruning_h0','pruning_paired','pruning_independent','pruned_noise_gain')]
        lines.append('| '+label+' | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    lines += ['', 'Full 4×4 endpoint tables, every conditional denominator, individual gains/harms and draw recurrence',
        'are retained in summary.json, cases.csv and events.csv. Three percentage points is a practical reference,',
        'not the primary zero-effect threshold. A smaller penalty without pruned improvement fails the conjunction.',
        'Noise changes the supplying body beyond fallback activation; no exclusive mediation claim follows.', '']
    return '\n'.join(lines)


def plot(run,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes = plt.subplots(2,3,figsize=(15,8))
    for i,kind in enumerate(('native','mixture')):
        g = summary['groups'][kind+'/pooled']; st = g['statistics']
        for policy,color in (('I','#1763a6'),('P','#d56d21')):
            names = (policy+'0',policy+'1_paired',policy+'1_independent')
            y = [100*st[n+'_both']['mean'] for n in names]
            bounds = np.array([st[n+'_both']['ci95'] for n in names])*100
            axes[i,0].errorbar(range(3),y,yerr=np.maximum(0,np.stack((y-bounds[:,0],bounds[:,1]-y))),
                               marker='o',capsize=3,label='Intact' if policy=='I' else 'Pruned',color=color)
        axes[i,0].set_ylim(0,100); axes[i,0].set_xticks(range(3),['Immediate','Rebuilt\npaired noise','Rebuilt\nindependent noise'])
        axes[i,0].set_ylabel(kind.capitalize()+' success (%)'); axes[i,0].legend(fontsize=8)
        for j,name in enumerate(('interaction','pruned_noise_gain','intact_noise_gain')):
            stat = st[name+'_both']; interval = stat['ci97_5'] if name+'_both' in PRIMARY and kind=='mixture' else stat['ci95']
            value = stat['mean']*100; lo,hi = [x*100 for x in interval]
            axes[i,1].errorbar(j,value,yerr=[[max(0,value-lo)],[max(0,hi-value)]],fmt='o',capsize=4,color='#216b50')
        axes[i,1].axhline(0,color='.5',lw=.8); axes[i,1].axhline(3,color='.7',ls=':',lw=.8)
        axes[i,1].set_xticks(range(3),['Pruning\ninteraction','Pruned\nimprovement','Intact\nimprovement'])
        axes[i,1].set_ylabel('Change (percentage points)')
        names = ('pruning_h0','pruning_paired','pruning_independent','pruned_noise_gain')
        gains = [g['contrasts'][n]['positive']['comparisons'] for n in names]
        harms = [-g['contrasts'][n]['negative']['comparisons'] for n in names]
        axes[i,2].bar(range(4),gains,color='#22824a',label='Gains'); axes[i,2].bar(range(4),harms,color='#b54942',label='Harms')
        axes[i,2].axhline(0,color='.5',lw=.8); axes[i,2].set_xticks(range(4),['Prune\nh0','Prune h1\npaired','Prune h1\nindep.','Noise\non pruned'])
        axes[i,2].set_ylabel('Dependent context/draw comparisons'); axes[i,2].legend(fontsize=8)
        for ax in axes[i]: ax.grid(axis='y',alpha=.15)
    fig.suptitle('E098: both endpoints and individual harms'+(' — EXCLUDED TIMING/TECHNICAL DATA' if summary['mode']!='scientific' else ''))
    fig.text(.5,.01,'Whole-block intervals: pooled-mixture primaries 97.5%; others descriptive 95%. Writers are shared by two terminal draws.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.96)); fig.savefig(run/'endpoints.png',dpi=150); fig.savefig(run/'endpoints.pdf'); plt.close(fig)
