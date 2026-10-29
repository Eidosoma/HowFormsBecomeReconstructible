"""Separate stable representation, retrieved capability and comparator benefit."""
from collections import defaultdict
from h007.io import save
from h085.report import write
from h095 import model as m,measure


def reduce(rows,keys):
    groups=defaultdict(list)
    for row in rows:groups[tuple(row[k] for k in keys)].append(row)
    result=[]
    for key,items in sorted(groups.items()):
        row=dict(zip(keys,key),networks=len({r['block'] for r in items}))
        for field in items[0]:
            if field in keys or field in measure.DETAILS:continue
            assert all(isinstance(r[field],(int,float)) for r in items),(keys,field)
            values=[r[field] for r in items];row[field]=min(values) if field.startswith('minimum_') else sum(values)
        if 'task_gains' in row:
            nets=[r['task_gains']-r['task_losses'] for r in items]
            row.update(networks_improved=sum(v>0 for v in nets),networks_worsened=sum(v<0 for v in nets),networks_tied=sum(v==0 for v in nets))
        result.append(row)
    return result


def score(rows,condition,panel,g=2,reader='ordinary',source='own',route='rewrite',scope='lineage',policy='pair'):
    key=(condition,scope,route,policy,g,source,reader,panel)
    return next(r for r in rows if tuple(r[k] for k in measure.KEYS['cases'])==key)


def arm(rows,panel,g=2,reader='ordinary'):
    key=('protected_minus_unprotected','lineage','rewrite','pair',g,'own',reader,panel)
    return next(r for r in rows if tuple(r[k] for k in measure.KEYS['arm_effects'])==key)


def transition(rows,condition,origin='own',reader='pair',g=0,panel='heldout',route='rewrite',policy='pair'):
    key=(condition,'lineage',route,policy,g,origin,reader,panel)
    return next(r for r in rows if tuple(r[k] for k in measure.KEYS['transitions'])==key)


def findings(a,main):
    def capable(panel,g,reader):
        own=score(a['cases'],'protected',panel,g,reader);rate=own['task_correct']/own['task_total']
        return rate>=.75 and all(rate-(r:=score(a['cases'],'protected',panel,g,reader,source))['task_correct']/r['task_total']>=.25 for source in ('donor','erased'))
    def gain(g,reader):
        r=arm(a['arm_effects'],'heldout',g,reader);return r['task_gains']>r['task_losses']
    protected=[transition(a['transitions'],'protected',origin=o,reader=r) for o in m.ORIGINS for r in m.READERS]
    preserved=all(all(row[k]==row['queries'] for k in ('context_matched_gap_end','context_matched_first_query_end','context_matched_recipient_end')) for row in protected)
    improved=transition(a['transitions'],'protected')['context_matched_recipient_end']>transition(a['transitions'],'unprotected')['context_matched_recipient_end']
    g0=capable('heldout',0,'pair') and gain(0,'pair')
    effects={(r['condition'],r['panel'],r['contrast']):r for r in a['effects']}
    inherited=effects['protected','heldout','inherited_g2_ordinary']
    comparators=[effects['protected','heldout',name] for name in measure.PRIMARY_COMPARATORS]
    checks=dict(context_transition=preserved and improved,heldout_g0=g0,heldout_g2=g0 and capable('heldout',2,'ordinary') and gain(2,'ordinary'),
        trained_g2=capable('trained',2,'ordinary'),inherited_record=inherited['task_gains']>inherited['task_losses'],
        comparators=all(r['task_gains']>r['task_losses'] and r['query_gains']>=r['query_losses'] for r in comparators))
    labels=dict(context_transition=('G0_HELDOUT_CONTEXT_TRANSITION_SCREEN_PASSED','G0_HELDOUT_CONTEXT_TRANSITION_SCREEN_FAILED'),
        heldout_g0=('G0_HELDOUT_CAPABILITY_SCREEN_PASSED','G0_HELDOUT_CAPABILITY_SCREEN_FAILED'),
        heldout_g2=('G2_HELDOUT_CAPABILITY_RETAINED','G2_HELDOUT_INHERITANCE_SCREEN_FAILED'),
        trained_g2=('G2_TRAINED_CAPABILITY_SCREEN_PASSED','G2_TRAINED_CAPABILITY_SCREEN_FAILED'),
        inherited_record=('POSITIVE_G2_HELDOUT_INHERITED_TASK_DIFFERENCE','NO_POSITIVE_G2_HELDOUT_INHERITED_TASK_DIFFERENCE'),
        comparators=('OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS','NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'))
    return {k:labels[k][0 if v else 1] if main else 'ENGINEERING_OR_SYNTHETIC_ONLY' for k,v in checks.items()}


def produce(out,blocks,main):
    tables={k:[r for b in blocks for r in b[k]] for k in measure.KINDS};aggregate={};serialized=0
    for kind,rows in tables.items():
        parsed=write(out/(kind+'.csv'),rows);serialized+=len(parsed);aggregate[kind]=reduce(parsed,measure.KEYS[kind])
        serialized+=len(write(out/(kind+'_aggregate.csv'),aggregate[kind]))
    primary={name:score(aggregate['cases'],'protected',panel,g,reader) for name,panel,g,reader in
        [('heldout_g0','heldout',0,'pair'),('heldout_g2','heldout',2,'ordinary'),('trained_g2','trained',2,'ordinary')]}
    comparators=[r for r in aggregate['effects'] if r['condition']=='protected' and r['panel']=='heldout' and r['contrast'] in measure.PRIMARY_COMPARATORS]
    summary=dict(experiment='H095',classification='FRESH_NETWORK_FIXED_MECHANISM_CONFIRMATION' if main else 'ENGINEERING_OR_SYNTHETIC_ONLY',
        networks=len(blocks),source_cohort='H095 seed 95095',root_seed=m.SEED,actual_handoffs=2,conditions=list(m.CONDITIONS),baseline_reused=False,
        findings=findings(aggregate,main),primary_scores=primary,primary_comparators=comparators,**aggregate,
        diagnostic_rows=sum(map(len,tables.values())),serialized_rows_checked=serialized,new_observed_labels=0,
        completion_is_supplied_apparatus=True,heldout_truth_used_by_writers=False,rule_used_during_neural_read=True,first_query_context_hold=True,true_context_resupplied=False,extra_context_buffer_values=0,
        population_qualification=False,comparative_superiority_qualified=False,arithmetic_cost_matched=False,
        historical_verdicts_unchanged=True,private_sources_quoted=False,next_campaign_launched=False)
    save(out/'summary.json',summary)
    lines=['# H095 — hold internal context during the first query sweep','',
        f"**{summary['classification']}**: {len(blocks)} matched networks; four related births; two actual handoffs.",
        'Fresh independent networks; the H094 mechanism and all six gates are fixed.',
        'All new writers fit the supplied parity family to eight actual observations and use',
        'their own sixteen predicted responses. Predictions are not extra observations.',
        'The energy and writer remain unchanged. Skip context-coordinate updates only',
        'during the first query sweep, holding their actual post-gap state; release them',
        'for all later query and continuation sweeps. No true context is supplied again.',
        'All neural controls receive the same schedule; native controls keep their apparatus.','']
    for key,value in summary['findings'].items():lines.append(f'{key}: **{value}**.')
    lines+=['','| Condition | G0 held-out tasks / queries | G2 held-out tasks / queries | G2 taught tasks / queries |','|---|---:|---:|---:|']
    for condition in m.CONDITIONS:
        cells=[]
        for panel,g,reader in [('heldout',0,'pair'),('heldout',2,'ordinary'),('trained',2,'ordinary')]:
            r=score(aggregate['cases'],condition,panel,g,reader);cells.append(f"{r['task_correct']}/{r['task_total']}; {r['query_correct']}/{r['query_total']}")
        lines.append('| '+condition+' | '+' | '.join(cells)+' |')
    lines+=['','| G0 intended patterns | Source | Panel | Full fixed / total |','|---|---|---|---:|']
    for r in aggregate['patterns']:lines.append(f"| {r['condition']} | {r['origin']} | {r['panel']} | {r['full_fixed']}/{r['patterns']} |")
    lines+=['','| Protected, G2 own | Scope | Panel | Complete tasks | Successful queries |','|---|---|---|---:|---:|']
    for r in aggregate['cases']:
        if r['condition']=='protected' and r['generation']==2 and r['source']=='own' and r['policy'] in ('pair','direct') and r['reader'] in ('ordinary','direct'):
            lines.append(f"| {r['route']} | {r['scope']} | {r['panel']} | {r['task_correct']}/{r['task_total']} | {r['query_correct']}/{r['query_total']} |")
    lines+=['','| G0 unseen context | Source | Before query | After first sweep | Recipient endpoint |','|---|---|---:|---:|---:|']
    for condition in m.CONDITIONS:
        for origin in m.ORIGINS:
            r=transition(aggregate['transitions'],condition,origin=origin)
            lines.append(f"| {condition} | {origin} | {r['context_matched_gap_end']}/{r['queries']} | {r['context_matched_first_query_end']}/{r['queries']} | {r['context_matched_recipient_end']}/{r['queries']} |")
    lines+=['','All passive sources, readers, original-packet disagreements and paired gains/losses',
        'are retained. Target stability, retrieval, handoff retention and comparator benefit',
        'are separate findings. Added apparatus is shared by controls; no cost match or',
        'population qualification. Both matched conditions are newly simulated.','',
        '[Cases](cases.csv), [completion diagnostics](completions.csv), [effects](effects.csv),',
        '[matched changes](arm_effects.csv), [geometry](geometry.csv), [context and learned-rule diagnostics](transitions.csv), [summary](summary.json), [figure](overview.png).']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');figure(out,summary);return summary


def figure(out,s):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),layout='constrained');pos=np.arange(3)
    for i,condition in enumerate(m.CONDITIONS):
        vals=[]
        for panel,g,reader in [('heldout',0,'pair'),('heldout',2,'ordinary'),('trained',2,'ordinary')]:
            r=score(s['cases'],condition,panel,g,reader);vals.append(100*r['task_correct']/r['task_total'])
        axes[0].bar(pos+(i-.5)*.32,vals,.32,label=condition)
        r=transition(s['transitions'],condition)
        axes[1].bar(condition,100*r['context_matched_recipient_end']/r['queries'])
    axes[0].set(xticks=pos,xticklabels=['G0 unseen\npair reader','G2 unseen\nordinary reader','G2 taught\nordinary reader'],ylim=(0,105),ylabel='Complete tasks (%)');axes[0].legend()
    axes[1].set(ylim=(0,105),ylabel='Context-matched endpoints (%)',title='G0 unseen recipient, released context')
    fig.suptitle(f"H095 · {s['networks']} matched networks · first-query context hold")
    fig.savefig(out/'overview.png',dpi=180);fig.savefig(out/'overview.pdf');plt.close(fig)
