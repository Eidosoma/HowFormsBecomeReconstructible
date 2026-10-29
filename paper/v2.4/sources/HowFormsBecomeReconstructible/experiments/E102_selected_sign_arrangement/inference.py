"""Prespecified sign-arrangement contrast with all endpoints and harms."""
from collections import defaultdict
import math
import numpy as np
from common import rng
from E099_saved_body_capture.inference import joint_table as legacy_joint_table
from E100_saved_record_region_swap.inference import contrast_events as previous_events
from E101_cross_noise_components.inference import contrast_events as component_events
from E102_selected_sign_arrangement import data
from E102_selected_sign_arrangement.plan import settings,identity,expected_identities,CONTRASTS,INTERACTIONS,PRIMARY,STARTS,OLD100,CONTRASTS100,OLD101,CONTRASTS101


def recurrence(rows,draw_key='draw'):
    contexts=defaultdict(set)
    for r in rows: contexts[identity(r)].add(r[draw_key])
    return dict(comparisons=len(rows),unique_contexts=len(contexts),independent_blocks=len({r['task'] for r in rows}),
        same_context_both_draws=sum(v=={0,1} for v in contexts.values()),
        identities=[dict(task=k[0],arm=k[1],founder=k[2],recipient=k[3],draws=sorted(v)) for k,v in sorted(contexts.items())])


def outcome_table(rows,labels=tuple(STARTS)):
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
    assert not any(k.startswith(('old_','source_writer_')) for k in keys)
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
    if met: conclusion='ARRANGEMENT_CONTRIBUTES_WITH_REPEATED_SELECTED_TRANSFER'
    elif primary[PRIMARY[0]]['direction']=='NEGATIVE': conclusion='SHUFFLE_OUTPERFORMS_DONOR_ARRANGEMENT'
    elif primary[PRIMARY[0]]['direction']=='POSITIVE': conclusion='ARRANGEMENT_POSITIVE_SELECTED_TRANSFER_NOT_REPEATED'
    else: conclusion='ARRANGEMENT_ADVANTAGE_NOT_ESTABLISHED'
    return dict(primary=primary,conjunction_met=met,conclusion=conclusion)


def analyze(rows,mode):
    cfg=settings(mode); ids=[identity(r)+(r['draw'],) for r in rows]
    assert len(ids)==len(set(ids)) and set(ids)==expected_identities(cfg)
    keys=[k for k in rows[0] if k not in data.IDENTIFIERS and not k.startswith(('old_','source_writer_'))]
    blocks=cfg['blocks']; indices=rng('E102','bootstrap').integers(0,len(blocks),(cfg['bootstrap_samples'],len(blocks)))
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
            group=dict(blocks=blocks,comparisons=len(part),statistics=stats,outcomes=outcome_table(part),
                contrasts={c:contrast_events(part,c) for c in CONTRASTS},legacy_E098_tables={},legacy_E099_tables={},legacy_E100_tables={},legacy_E101_tables={},by_draw={})
            original=parent['groups'][kind+'/'+history]
            for noise in ('paired','independent'):
                tab=legacy_joint_table(part,('old_E098_I0','old_E098_P0'),('old_E098_I1_'+noise,'old_E098_P1_'+noise),old=True)
                for key in ('counts','conditional'):
                    assert tab[key]==original['legacy_E098_tables'][noise][key]
                group['legacy_E098_tables'][noise]=tab; result['legacy_tables_checked']+=1
            for capture in ('H','O'):
                tab=legacy_joint_table(part,('old_E099_I_pair_'+capture,'old_E099_P_pair_'+capture),
                    ('old_E099_I_ind_'+capture,'old_E099_P_ind_'+capture))
                tab['comparison_space']='E099_original_readers'
                for key in ('counts','conditional'):
                    assert tab[key]==original['legacy_E099_tables'][capture][key]
                group['legacy_E099_tables'][capture]=tab; result['legacy_tables_checked']+=1
            tab=outcome_table(part,tuple('old_E099_'+v for v in ('P_ind_O','P_ind_S','P_ind_M','P_ind_H')))
            assert tab['counts']==original['legacy_E099_tables']['factorial']['counts']
            group['legacy_E099_tables']['factorial']=tab; result['legacy_tables_checked']+=1
            tab=outcome_table(part,tuple('old_E100_'+v for v in OLD100))
            assert tab['counts']==original['legacy_E100_tables']['factorial']['counts']
            group['legacy_E100_tables']['factorial']=tab; result['legacy_tables_checked']+=1
            old_rows=[]
            for row in part:
                old={k:row[k] for k in ('task','arm','founder','recipient')}; old['draw']=row['old_E100_draw']
                old.update({v+'_both':row['old_E100_'+v+'_both'] for v in OLD100})
                for name,parts in CONTRASTS100.items(): old[name+'_both']=sum(c*old[v+'_both'] for v,c in parts.items())
                old_rows.append(old)
            events={name:previous_events(old_rows,name) for name in CONTRASTS100}
            assert events==original['legacy_E100_tables']['contrasts']
            group['legacy_E100_tables']['contrasts']=events
            tab=outcome_table(part,tuple('old_E101_'+v for v in OLD101))
            assert tab['counts']==original['factorial']['counts']
            group['legacy_E101_tables']['factorial']=tab; result['legacy_tables_checked']+=1
            old_rows=[]
            for row in part:
                old={k:row[k] for k in ('task','arm','founder','recipient')}; old['draw']=row['old_E101_draw']
                old.update({v+'_both':row['old_E101_'+v+'_both'] for v in OLD101})
                for name,parts in CONTRASTS101.items(): old[name+'_both']=sum(c*old[v+'_both'] for v,c in parts.items())
                old_rows.append(old)
            events={name:component_events(old_rows,name) for name in CONTRASTS101}
            assert events==original['contrasts']
            group['legacy_E101_tables']['contrasts']=events
            draw_keys=[k for k in keys if k.endswith(('_both','_minimum_margin','_transfer'))]
            for draw in (0,1):
                sub=[r for r in part if r['draw']==draw]
                st,n=statistics(sub,draw_keys,blocks,counts); result['independent_block_means_checked']+=n
                group['by_draw'][str(draw)]=dict(comparisons=len(sub),statistics=st)
            result['groups'][kind+'/'+history]=group
    result['decision']=decision(result['groups']['mixture/pooled']['statistics'])
    result['primary_conclusion']=result['decision']['conclusion'] if mode=='scientific' else 'EXCLUDED_TECHNICAL_ONLY'
    result['criterion_met']=result['decision']['conjunction_met'] if mode=='scientific' else None
    result['new_joint_tables_checked']=0; result['outcome_tables_checked']=6
    assert result['legacy_tables_checked']==42
    return result


def report(summary):
    lines=['# E102 selected sign arrangement with matched counts','',f"Mode: {summary['mode']}; **{summary['primary_conclusion']}**.",
        f"{summary['independent_source_blocks']} reused blocks; {summary['record_contexts']} contexts; "
        f"{summary['context_draw_pairs']} new context/draw rows. No ancestry or writer dynamics repeated.",'',
        '| Primary pooled-mixture contrast | Mean (pp) | Adjusted 97.5% interval (pp) | Direction |',
        '| --- | ---: | --- | --- |']
    for key,stat in summary['decision']['primary'].items():
        lo,hi=stat['ci97_5']; lines.append(f"| {key} | {100*stat['mean']:.3f} | [{100*lo:.3f}, {100*hi:.3f}] | {stat['direction']} |")
    lines+=['','| Group | B original (%) | M magnitude-only (%) | D donor (%) | S shuffled (%) |','| --- | ---: | ---: | ---: | ---: |']
    for label,g in summary['groups'].items():
        vals=[g['statistics'][k+'_both']['mean']*100 for k in STARTS]
        lines.append('| '+label+' | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    lines+=['','B = original; M = paired signs / independent magnitudes; D = independent signs and magnitudes; S = D with selected signs rearranged.',
        'Paired outside and support fixed. Selected donors use ordinary capture. One shuffle per record within two-draw survival strata.',
        'D/S sign counts match globally and after each injury. M/D/S magnitudes, denominators and absolute coupling match exactly.',
        'Other contrasts, native outcomes, margins and transfer are secondary pointwise 95%. All gains, harms, zeros and 16 outcome configurations retained.',
        'The four-record outcome table is not a new factorial design. All original E098/E099/E100/E101 endpoints remain historical.',
        'Old endpoints use different nuisances and enter neither new intervals nor new-minus-old comparisons.',
        'The shuffle conditions on masks only; local incident signs and signed strength sums can change. No fresh source histories.','']
    return '\n'.join(lines)


def plot(run,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,8))
    contrasts=tuple(CONTRASTS)
    labels=['Donor −\nshuffle','Donor −\noriginal','Donor −\nmagnitude','Shuffle −\nmagnitude','Shuffle −\noriginal','Magnitude −\noriginal']
    for i,kind in enumerate(('native','mixture')):
        g=summary['groups'][kind+'/pooled']; st=g['statistics']
        y=np.array([100*st[k+'_both']['mean'] for k in STARTS]); bounds=np.array([st[k+'_both']['ci95'] for k in STARTS])*100
        axes[i,0].errorbar(range(4),y,yerr=np.maximum(0,np.stack((y-bounds[:,0],bounds[:,1]-y))),fmt='o',capsize=4,color='#1763a6')
        axes[i,0].set_xticks(range(4),['B\nOriginal','M\nMagnitudes only','D\nDonor','S\nShuffled signs'])
        axes[i,0].set_ylim(0,100); axes[i,0].set_ylabel(kind.capitalize()+' pruned-record success (%)')
        for j,k in enumerate(contrasts):
            stat=st[k+'_both']; interval=stat['ci97_5'] if k+'_both' in PRIMARY and kind=='mixture' else stat['ci95']
            v=stat['mean']*100; lo,hi=[100*x for x in interval]
            axes[i,1].errorbar(j,v,yerr=[[max(0,v-lo)],[max(0,hi-v)]],fmt='o',capsize=4,color='#216b50')
        axes[i,1].axhline(0,color='.5',lw=.8); axes[i,1].axhline(3,color='.7',ls=':',lw=.8)
        axes[i,1].set_xticks(range(6),labels,rotation=20); axes[i,1].set_ylabel('Change (percentage points)')
        names=contrasts
        gains=[g['contrasts'][k]['positive']['comparisons'] for k in names]
        harms=[-g['contrasts'][k]['negative']['comparisons'] for k in names]
        axes[i,2].bar(range(6),gains,color='#22824a',label='Gains'); axes[i,2].bar(range(6),harms,color='#b54942',label='Harms')
        axes[i,2].axhline(0,color='.5',lw=.8); axes[i,2].set_xticks(range(6),labels,rotation=20)
        axes[i,2].set_ylabel('Dependent case/draw comparisons'); axes[i,2].legend(fontsize=8)
        for ax in axes[i]: ax.grid(axis='y',alpha=.15)
    fig.suptitle('E102: selected sign arrangement at fixed strengths and sign counts'+(' — EXCLUDED TECHNICAL DATA' if summary['mode']!='scientific' else ''))
    fig.text(.5,.01,'One shuffle within fixed injury-survival strata per record; global and surviving sign counts preserved. Known sources. Mixture primaries: 97.5%; other intervals: 95%.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.96)); fig.savefig(run/'arrangement.png',dpi=150); fig.savefig(run/'arrangement.pdf'); plt.close(fig)
