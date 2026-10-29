"""Source-block inference; historical endpoints never enter new intervals."""
from collections import defaultdict
import math
import numpy as np
from common import rng
from E099_saved_body_capture import data
from E099_saved_body_capture.plan import settings,identity,expected_identities,CONTRASTS,INTERACTIONS,PRIMARY,STARTS

LABELS=('both_fail','pruning_gain','pruning_harm','both_succeed')


def recurrence(rows,draw_key='draw'):
    contexts=defaultdict(set)
    for r in rows: contexts[identity(r)].add(r[draw_key])
    return dict(comparisons=len(rows),unique_contexts=len(contexts),independent_blocks=len({r['task'] for r in rows}),
        same_context_both_draws=sum(v=={0,1} for v in contexts.values()),
        identities=[dict(task=k[0],arm=k[1],founder=k[2],recipient=k[3],draws=sorted(v)) for k,v in sorted(contexts.items())])


def joint_table(rows,before,after,old=False):
    keys=[v+'_both' for v in (*before,*after)]
    values=np.array([[r[k] for k in keys] for r in rows],int)
    a,b=2*values[:,0]+values[:,1],2*values[:,2]+values[:,3]
    counts=np.bincount(4*a+b,minlength=16).reshape(4,4); scalar=np.zeros((4,4),int)
    for r in rows:
        codes=[]
        for i,p in (before,after):
            x,y=bool(r[i+'_both']),bool(r[p+'_both'])
            codes.append(3 if x and y else 2 if x else 1 if y else 0)
        scalar[tuple(codes)]+=1
    assert np.array_equal(counts,scalar) and counts.sum()==len(rows)
    conditional={}
    for j,label in enumerate(LABELS):
        denom=int(counts[j].sum())
        conditional[label]=dict(denominator=denom,empty=denom==0,later_gains=int(counts[j,1]),later_harms=int(counts[j,2]),
            later_gain_fraction=float(counts[j,1]/denom) if denom else None,
            later_harm_fraction=float(counts[j,2]/denom) if denom else None)
    draw_key='old_E098_draw' if old else 'draw'
    return dict(labels=list(LABELS),before=list(before),after=list(after),counts=counts.tolist(),conditional=conditional,
        comparisons=len(rows),comparison_space='E098_original_readers' if old else 'E099_new_matched_readers',
        after_gains=recurrence([r for r in rows if r[after[1]+'_both']>r[after[0]+'_both']],draw_key),
        after_harms=recurrence([r for r in rows if r[after[1]+'_both']<r[after[0]+'_both']],draw_key))


def factorial_table(rows):
    labels=('P_ind_O','P_ind_S','P_ind_M','P_ind_H')
    values=np.array([[r[k+'_both'] for k in labels] for r in rows],int)
    counts=np.bincount(values@np.array([8,4,2,1]),minlength=16).reshape(2,2,2,2)
    scalar=np.zeros((2,2,2,2),int)
    for r in rows: scalar[tuple(int(r[k+'_both']) for k in labels)]+=1
    assert np.array_equal(counts,scalar) and counts.sum()==len(rows)
    return dict(order=list(labels),counts=counts.tolist(),comparisons=len(rows))


def contrast_events(rows,name):
    values=[r[name+'_both'] for r in rows]
    out=dict(comparisons=len(rows),zero=sum(v==0 for v in values),
        distribution={str(v):values.count(v) for v in (-2.,-1.,0.,1.,2.)},
        positive=recurrence([r for r in rows if r[name+'_both']>0]),
        negative=recurrence([r for r in rows if r[name+'_both']<0]),
        interpretation='interaction_contrast' if name in INTERACTIONS else 'positive_is_gain_negative_is_harm')
    assert sum(out['distribution'].values())==len(rows)
    if name not in INTERACTIONS: assert not out['distribution']['-2.0'] and not out['distribution']['2.0']
    return out


def statistics(rows,keys,blocks,counts):
    assert not any(k.startswith(('old_E098_','source_writer_')) for k in keys)
    matrix=np.array([[r[k] for k in keys] for r in rows],float); tasks=np.array([r['task'] for r in rows])
    means=np.array([matrix[tasks==b].mean(0) for b in blocks])
    other=np.array([[math.fsum(r[k] for r in rows if r['task']==b)/sum(r['task']==b for r in rows)
                     for k in keys] for b in blocks])
    np.testing.assert_allclose(means,other,rtol=2e-12,atol=3e-14)
    bounds=np.quantile(counts@means/len(blocks),[.0125,.025,.975,.9875],axis=0)
    out={k:dict(mean=float(means[:,j].mean()),ci95=bounds[[1,2],j].tolist(),block_means=means[:,j].tolist()) for j,k in enumerate(keys)}
    for k in PRIMARY: out[k]['ci97_5']=bounds[[0,3],keys.index(k)].tolist()
    return out,means.size


def decision(stats):
    primary={}
    for k in PRIMARY:
        st=stats[k]; lo,hi=st['ci97_5']
        primary[k]=dict(**st,direction='POSITIVE' if lo>0 else 'NEGATIVE' if hi<0 else 'UNRESOLVED',
            practical_reference=.03,relative_to_reference='ABOVE' if lo>.03 else 'BELOW' if hi<.03 else 'OVERLAPS')
    met=all(v['direction']=='POSITIVE' for v in primary.values())
    if met: conclusion='FILTERING_CONTRIBUTES_WITH_REPEATED_NOISE_GAIN'
    elif primary[PRIMARY[0]]['direction']=='NEGATIVE': conclusion='ORDINARY_SELECTED_CAPTURE_OUTPERFORMS_HYBRID'
    elif primary[PRIMARY[0]]['direction']=='POSITIVE': conclusion='FILTERING_POSITIVE_NOISE_GAIN_NOT_REPEATED'
    else: conclusion='FILTERING_CONTRIBUTION_NOT_ESTABLISHED'
    return dict(primary=primary,conjunction_met=met,conclusion=conclusion)


def analyze(rows,mode):
    cfg=settings(mode); ids=[identity(r)+(r['draw'],) for r in rows]
    assert len(ids)==len(set(ids)) and set(ids)==expected_identities(cfg)
    keys=[k for k in rows[0] if k not in data.IDENTIFIERS and not k.startswith(('old_E098_','source_writer_'))]
    blocks=cfg['blocks']; indices=rng('E099','bootstrap').integers(0,len(blocks),(cfg['bootstrap_samples'],len(blocks)))
    counts=np.array([np.bincount(v,minlength=len(blocks)) for v in indices],float)
    parent=data.pinned(mode,'summary.json')
    result=dict(mode=mode,independent_source_blocks=len(blocks),new_source_blocks=0,record_contexts=len(rows)//2,
        context_draw_pairs=len(rows),primary_confidence=.975,secondary_confidence=.95,groups={},
        bootstrap_samples=cfg['bootstrap_samples'],independent_block_means_checked=0,legacy_tables_checked=0,
        historical_endpoints_in_new_intervals=False,source_selection=False,automatic_extension=False,automatic_successor=False)
    for kind in ('native','mixture'):
        for history in ('pooled','sham','pulse'):
            part=[r for r in rows if r['kind']==kind and (history=='pooled' or r['history']==history)]
            stats,n=statistics(part,keys,blocks,counts); result['independent_block_means_checked']+=n
            group=dict(blocks=blocks,comparisons=len(part),statistics=stats,factorial=factorial_table(part),
                contrasts={c:contrast_events(part,c) for c in CONTRASTS},pruning_noise_tables={},legacy_E098_tables={},by_draw={})
            for capture in ('H','O'):
                group['pruning_noise_tables'][capture]=joint_table(part,('I_pair_'+capture,'P_pair_'+capture),('I_ind_'+capture,'P_ind_'+capture))
            for noise in ('paired','independent'):
                tab=joint_table(part,('old_E098_I0','old_E098_P0'),('old_E098_I1_'+noise,'old_E098_P1_'+noise),old=True)
                assert tab['counts']==parent['groups'][kind+'/'+history]['tables'][noise]['counts']
                assert tab['conditional']==parent['groups'][kind+'/'+history]['tables'][noise]['conditional']
                group['legacy_E098_tables'][noise]=tab; result['legacy_tables_checked']+=1
            draw_keys=[k for k in keys if k.endswith(('_both','_minimum_margin','_transfer'))]
            for draw in (0,1):
                sub=[r for r in part if r['draw']==draw]
                st,n=statistics(sub,draw_keys,blocks,counts); result['independent_block_means_checked']+=n
                group['by_draw'][str(draw)]=dict(comparisons=len(sub),statistics=st)
            for k in PRIMARY:
                assert k in group['statistics']
            result['groups'][kind+'/'+history]=group
    result['decision']=decision(result['groups']['mixture/pooled']['statistics'])
    result['primary_conclusion']=result['decision']['conclusion'] if mode=='scientific' else 'EXCLUDED_TECHNICAL_ONLY'
    result['criterion_met']=result['decision']['conjunction_met'] if mode=='scientific' else None
    result['new_joint_tables_checked']=12; result['factorial_tables_checked']=6
    return result


def report(summary):
    lines=['# E099 fixed-body capture', '',f"Mode: {summary['mode']}; **{summary['primary_conclusion']}**.",
        f"{summary['independent_source_blocks']} reused source blocks; {summary['record_contexts']} contexts; "
        f"{summary['context_draw_pairs']} new terminal context/draw rows. No writer dynamics repeated.", '',
        '| Primary pooled-mixture contrast | Mean (pp) | Adjusted 97.5% interval (pp) | Direction |',
        '| --- | ---: | --- | --- |']
    for key,stat in summary['decision']['primary'].items():
        lo,hi=stat['ci97_5']; lines.append(f"| {key} | {100*stat['mean']:.3f} | [{100*lo:.3f}, {100*hi:.3f}] | {stat['direction']} |")
    lines+=['','| Group | P-paired H=O (%) | P-ind O (%) | P-ind S (%) | P-ind M (%) | P-ind H (%) |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for label,g in summary['groups'].items():
        vals=[g['statistics'][k+'_both']['mean']*100 for k in ('P_pair_H','P_ind_O','P_ind_S','P_ind_M','P_ind_H')]
        lines.append('| '+label+' | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    lines+=['','H is unchanged hybrid capture; O uses ordinary selected coactivity; S has H signs and O magnitudes;',
        'M has O signs and H magnitudes. Supplying bodies and outside record bytes stay fixed within each capture comparison.',
        'Component effects are secondary pointwise 95% descriptions, not additional confirmatory claims.',
        'All individual harms, zeros, factorial configurations and pruning/noise tables are retained.',
        'Old E098 immediate/later endpoints are historical context only; their draws differ from these new readers.',
        'The difference identity separates one intervention path, not a unique or exclusive mediation fraction.','']
    return '\n'.join(lines)


def plot(run,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,8))
    for i,kind in enumerate(('native','mixture')):
        g=summary['groups'][kind+'/pooled']; st=g['statistics']
        names=('P_pair_H','P_ind_O','P_ind_S','P_ind_M','P_ind_H')
        y=np.array([100*st[k+'_both']['mean'] for k in names]); bounds=np.array([st[k+'_both']['ci95'] for k in names])*100
        axes[i,0].errorbar(range(5),y,yerr=np.maximum(0,np.stack((y-bounds[:,0],bounds[:,1]-y))),fmt='o',capsize=4,color='#1763a6')
        axes[i,0].set_xticks(range(5),['Paired\nH=O','Indep.\nO','Indep.\nS','Indep.\nM','Indep.\nH'])
        axes[i,0].set_ylim(0,100); axes[i,0].set_ylabel(kind.capitalize()+' pruned-record success (%)')
        for j,k in enumerate(('filter_pruned','noise_pruned_H','noise_pruned_O')):
            stat=st[k+'_both']; interval=stat['ci97_5'] if k+'_both' in PRIMARY and kind=='mixture' else stat['ci95']
            v=stat['mean']*100; lo,hi=[100*x for x in interval]
            axes[i,1].errorbar(j,v,yerr=[[max(0,v-lo)],[max(0,hi-v)]],fmt='o',capsize=4,color='#216b50')
        axes[i,1].axhline(0,color='.5',lw=.8); axes[i,1].axhline(3,color='.7',ls=':',lw=.8)
        axes[i,1].set_xticks(range(3),['Fixed body\nH−O','Noise gain\nH','Noise gain\nO'])
        axes[i,1].set_ylabel('Change (percentage points)')
        names=('filter_pruned','noise_pruned_H','sign_at_O_magnitude','sign_at_H_magnitude','magnitude_at_O_sign','magnitude_at_H_sign')
        gains=[g['contrasts'][k]['positive']['comparisons'] for k in names]
        harms=[-g['contrasts'][k]['negative']['comparisons'] for k in names]
        axes[i,2].bar(range(6),gains,color='#22824a',label='Gains'); axes[i,2].bar(range(6),harms,color='#b54942',label='Harms')
        axes[i,2].axhline(0,color='.5',lw=.8); axes[i,2].set_xticks(range(6),['H−O','Noise H','S−O','H−M','M−O','H−S'],rotation=25)
        axes[i,2].set_ylabel('Dependent case/draw comparisons'); axes[i,2].legend(fontsize=8)
        for ax in axes[i]: ax.grid(axis='y',alpha=.15)
    fig.suptitle('E099: capture on fixed bodies and every individual harm'+(' — EXCLUDED TECHNICAL DATA' if summary['mode']!='scientific' else ''))
    fig.text(.5,.01,'New matched readers on reused E098 sources. Mixture primaries: 97.5% block intervals; all others descriptive 95%.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.96)); fig.savefig(run/'capture.png',dpi=150); fig.savefig(run/'capture.pdf'); plt.close(fig)
