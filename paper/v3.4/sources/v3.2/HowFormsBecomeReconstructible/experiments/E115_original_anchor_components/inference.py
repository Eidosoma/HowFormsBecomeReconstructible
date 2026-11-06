"""One declared mixture contrast; every absolute outcome and harm retained."""
import itertools
import math
from collections import Counter
import numpy as np
from common import rng
from E105_cycle_input_control.inference import decision
from E113_component_threshold_diagnosis.inference import nullable_statistics, ratio, transition_counts, crossings, fmt
from E115_original_anchor_components.plan import PRIMARY, PRIOR_PRIMARY, MIDPOINT_PRIMARY, CONDITIONS, METRICS, SCOPES, settings, summary_keys, key


def summarize(mode,rows,pairs,prior,midpoint):
    cfg=settings(mode);blocks=cfg['blocks'];n=len(blocks)
    expected={(b,a,f,r,d) for b in blocks for a in range(4) for f in range(4) for r in range(cfg['recipients']) for d in (0,1)}
    assert len(rows)==len(expected) and {key(r) for r in rows}==expected
    measured=[r for r in rows if r['measured']];assert len(pairs)==8*len(measured)
    by_key={key(r):[] for r in measured}
    for p in pairs:by_key[key(p)].append(p)
    assert all(len(x)==8 for x in by_key.values())
    draws=rng('E115','original_anchor_bootstrap').integers(0,n,(cfg['bootstrap_samples'],n))
    resamples=np.array([np.bincount(d,minlength=n) for d in draws],float)
    result=dict(mode=mode,blocks=blocks,independent_sources=n,context_draw_rows=len(rows),measured_rows=len(measured),
        comparisons=len(pairs),groups={},independent_block_sums_checked=0,
        prior_primary=prior['primary'],prior_criterion_met=prior['criterion_met'],prior_primary_unchanged=True,
        midpoint_primary=midpoint['primary'],midpoint_criterion_met=midpoint['criterion_met'],midpoint_primary_unchanged=True,
        primary_key=PRIMARY,primary_group=cfg['primary_group'],bootstrap_samples=cfg['bootstrap_samples'],confidence=.95,
        secondary_intervals='pointwise; not simultaneous',source_outcomes_previously_known=True,
        new_source_blocks=0,new_reader_outcomes=True,new_streams=False,no_outcome_selection=True,
        norm_matched_across_C_F_average=True,variant_norms_not_forced_equal=True,original_diagonal_anchors=True,midpoint_centered=False,
        absolute_outcomes_and_individual_harms_retained=True,automatic_successor=False)
    for kind in ('native','mixture'):
        sums=[math.fsum(r['full_size_excess'] for r in rows if r['kind']==kind and r['task']==b) for b in blocks]
        assert sums==prior['groups'][kind+'/pooled/pooled']['eligible']['statistics'][PRIOR_PRIMARY]['block_sums']
        middle=[math.fsum(r['midpoint_excess'] for r in rows if r['kind']==kind and r['task']==b) for b in blocks]
        assert middle==midpoint['groups'][kind+'/pooled/pooled']['eligible']['statistics'][MIDPOINT_PRIMARY]['block_sums']
    for kind,history,draw in itertools.product(('native','mixture'),('pooled','sham','pulse'),('pooled','0','1')):
        part=[r for r in rows if r['kind']==kind and (history=='pooled' or r['history']==history) and (draw=='pooled' or r['draw']==int(draw))]
        group={}
        for scope in SCOPES:
            chosen=[r for r in part if scope=='all' or r[scope]]
            st,checked=nullable_statistics(chosen,blocks,resamples,summary_keys());result['independent_block_sums_checked']+=checked
            st.update(all_rows=len(part),measured_rows=sum(r['measured'] for r in chosen),
                zero_targets=sum(bool(r['zero_target']) for r in chosen),transitions={},cancellation={})
            for comp in ('m','d'):
                ps=[p for r in chosen if r['measured'] for p in by_key[key(r)] if p['component']==comp]
                st['transitions'][comp]=transition_counts(ps)
                for metric in METRICS:
                    value,checked=ratio(chosen,blocks,resamples,comp+'_'+metric+'_canceled',comp+'_'+metric+'_endpoint_total')
                    st['cancellation'][comp+'/'+metric]=value;result['independent_block_sums_checked']+=checked
            patterns=Counter(''.join(str(int(r[c+'_'+v+'_both'])) for c in CONDITIONS for v in ('C','F')) for r in chosen if r['measured'])
            assert sum(patterns.values())==st['measured_rows']
            st['observed_success_patterns']=dict(sorted(patterns.items()));st['success_pattern_order']='condition order, C then F'
            group[scope]=st
        result['groups'][kind+'/'+history+'/'+draw]=group
    primary=result['groups']['mixture/pooled/pooled']['eligible']['statistics'][PRIMARY]
    result['primary']=dict(**primary,decision=decision(primary),eligible_rows=result['groups']['mixture/pooled/pooled']['eligible']['rows'])
    result['criterion_met']=result['primary']['decision']=='POSITIVE'
    result['primary_source_counts']=dict(positive=sum(x>0 for x in primary['block_sums']),
        negative=sum(x<0 for x in primary['block_sums']),zero=sum(x==0 for x in primary['block_sums']))
    events=[p for p in pairs if p['both_endpoint_total']>0];cross=crossings(pairs)
    result['event_comparisons']=len(events);result['success_crossings']=len(cross)
    result['gains_and_losses']=dict(Counter(r['direction'] for r in cross))
    result['crossing_failure_classes']=dict(Counter(r['failure_class'] for r in cross))
    return result,events,cross


def report(s):
    lines=['# E115: equal-size changes from original halfway states','',
        'EXCLUDED TECHNICAL DATA.' if s['mode']=='benchmark' else 'New controlled reader outcomes on the complete known E112 cohort.',
        f"All {s['independent_sources']} sources / {s['context_draw_rows']} identities / {s['measured_rows']} eligible rows / {s['comparisons']} comparisons retained.",
        "Each original OO/NN halfway state is retained as an anchor. Move one component toward the opposite source by E114's common smaller mean absolute size, pooled across C/F.",
        'Every source, record, injury, cue clamp, later noise offset and earlier endpoint remains; no new writer dynamics.',
        f"**Sole eligible-mixture primary: {s['primary']['decision']}.** Gross anchored m−d sensitivity of C−F success: {fmt(s['primary'],100,3)} points.",
        f"E112 original mixture primary remains {s['prior_primary']['decision']}: {fmt(s['prior_primary'],100,3)} points.",
        f"E114 midpoint primary remains {s['midpoint_primary']['decision']}: {fmt(s['midpoint_primary'],100,3)} points.",
        'All other intervals are pointwise secondary whole-source intervals. This is not a fresh-source confirmation.','',
        '| Eligible group | Original mean m size | Original mean d size | Matched target size | Mean m scale | Mean d scale | Zero targets |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for kind in ('native','mixture'):
        g=s['groups'][kind+'/pooled/pooled']['eligible'];st=g['statistics']
        lines.append('| '+kind+' | '+' | '.join(fmt(st[k]) for k in ('original_m_size','original_d_size','target_size','m_scale','d_scale'))+f" | {g['zero_targets']} |")
    lines+=['','| Eligible group | Gross m C−F success change, points | Gross d change, points | Anchored m−d, points | Anchor minus midpoint excess, points |',
        '| --- | ---: | ---: | ---: | ---: |']
    for kind in ('native','mixture'):
        st=s['groups'][kind+'/pooled/pooled']['eligible']['statistics']
        lines.append('| '+kind+' | '+' | '.join(fmt(st[k],100,3) for k in ('m_both_contrast_abs','d_both_contrast_abs',PRIMARY,'anchor_minus_midpoint'))+' |')
    lines+=['','| Eligible group / component | Total absolute C/F success movement, points | Cancellation % | Joint gains / losses | Single-record changes | Opposed changes |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for kind,comp in itertools.product(('native','mixture'),('m','d')):
        g=s['groups'][kind+'/pooled/pooled']['eligible'];counts=g['transitions'][comp]['counts']
        lines.append('| '+kind+'/'+comp+' | '+fmt(g['statistics'][comp+'_both_endpoint_total'],100,3)+' | '+fmt(g['cancellation'][comp+'/both'],100,2)+
            f" | {counts['joint_gain']}/{counts['joint_loss']} | {sum(counts[k] for k in ('C_gain','C_loss','F_gain','F_loss'))} | {counts['C_gain_F_loss']+counts['C_loss_F_gain']} |")
    lines+=['','| Eligible group / condition | C success % | F success % | C−F success, points |',
        '| --- | ---: | ---: | ---: |']
    for kind,c in itertools.product(('native','mixture'),CONDITIONS):
        st=s['groups'][kind+'/pooled/pooled']['eligible']['statistics']
        lines.append('| '+kind+'/'+c+' | '+' | '.join(fmt(st[c+'_'+v+'_both'],100,3) for v in ('C','F','delta'))+' |')
    lines+=['',f"{s['event_comparisons']} comparisons change at least one success; {s['success_crossings']} record-level transitions. Gains/losses: {s['gains_and_losses']}.",
        'These are dependent condition observations. All identities, absolute outcomes, zero cases and individual harms remain in the ledgers.',
        'Both components receive the same pair-averaged norm; their C and F norms individually need not match.',
        'Comparisons with E114 midpoint placement and the E112 full-size rectangle are paired secondary contrasts. Each anchor and each later stream receives equal weight.',
        'Conclusions concern these natural directions, this norm and the smaller dose, under the existing paired-cue/reset/normalization apparatus.',
        'An unresolved interval is not equivalence or absence of a component contribution. No dose tuning, source extension or automatic successor.','']
    return '\n'.join(lines)


def plot(run,s):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(14,8));colors=('tab:blue','tab:orange')
    def point(ax,x,stat,color,scale=1,label=None):
        if stat['mean'] is None:return
        y=stat['mean']*scale;a,b=np.array(stat['ci95'])*scale
        ax.errorbar(x,y,yerr=[[max(0,y-a)],[max(0,b-y)]],fmt='o',capsize=4,color=color,label=label)
    for i,kind in enumerate(('native','mixture')):
        g=s['groups'][kind+'/pooled/pooled']['eligible'];st=g['statistics'];ax=axes[i,0]
        for j,k in enumerate(('original_m_size','original_d_size','target_size')):point(ax,j,st[k],('tab:blue','tab:orange','tab:green')[j])
        ax.set_xticks(range(3),['Original m','Original d','Matched m = d']);ax.set_ylabel('Mean absolute activity difference');ax.set_title(kind.capitalize()+': input size')
        ax=axes[i,1]
        for j,comp in enumerate(('m','d')):
            point(ax,j-.1,st[comp+'_both_endpoint_total'],'.5',100,'Total |ΔC|+|ΔF|' if j==0 else None)
            point(ax,j+.1,st[comp+'_both_contrast_abs'],colors[j],100,'Retained |ΔC−ΔF|' if j==0 else None)
        ax.set_xticks(range(2),['Shared m','Cue d']);ax.set_ylabel('Success change, points / comparison');ax.set_title('Anchored interventions');ax.legend(fontsize=8)
        ax=axes[i,2]
        point(ax,0,st['midpoint_excess'],'.5',100);point(ax,1,st[PRIMARY],'tab:purple',100)
        ax.set_xticks([0,1],['E114 midpoints','Original anchors']);ax.axhline(0,c='.5',lw=.8)
        ax.set_ylabel('Gross m−d C−F sensitivity, points');ax.set_title('Mixture anchored contrast is primary' if kind=='mixture' else 'Native contrast is secondary')
        for ax in axes[i]:ax.grid(axis='y',alpha=.15)
    title='E115: equal-size shared versus cue changes from original states'
    if s['mode']=='benchmark':title+='\nEXCLUDED TECHNICAL DATA'
    fig.suptitle(title);fig.text(.5,.01,'Known sources; 95% whole-source intervals. Original anchors, fixed later streams. All cases and harms retained.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.93));fig.savefig(run/'anchored.png',dpi=150);fig.savefig(run/'anchored.pdf');plt.close(fig)
