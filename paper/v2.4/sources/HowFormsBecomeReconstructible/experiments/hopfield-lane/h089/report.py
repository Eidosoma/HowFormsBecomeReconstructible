"""Separate trained retrieval, held-out capability and comparator verdicts."""
from collections import defaultdict
from pathlib import Path
from h007.io import save
from h085.report import write
from h089 import model as m,measure


def reduce(rows,keys):
    groups=defaultdict(list)
    for row in rows:groups[tuple(row[k] for k in keys)].append(row)
    result=[]
    for identity,items in sorted(groups.items()):
        row=dict(zip(keys,identity),networks=len({r['block'] for r in items}))
        for key in items[0]:
            if key in keys or key in measure.DETAILS:continue
            assert all(isinstance(r[key],(int,float)) for r in items),(key,keys)
            row[key]=sum(r[key] for r in items)
        if keys==measure.KEYS['effects']:
            values=[r['task_gains']-r['task_losses'] for r in items]
            row.update(networks_improved=sum(v>0 for v in values),networks_worsened=sum(v<0 for v in values),networks_tied=sum(v==0 for v in values))
        result.append(row)
    return result


def score(scores,panel,g=2,route='rewrite',policy='pair',reader='ordinary',source='own',scope='lineage'):
    key=(scope,route,policy,g,source,reader,panel)
    return next(r for r in scores if tuple(r[k] for k in measure.KEYS['cases'])==key)


def findings(scores,effects,main):
    index={(r['panel'],r['contrast']):r for r in effects}
    trained=score(scores,'trained',0,reader='pair');held=score(scores,'heldout')
    controls=[score(scores,'heldout',source=s) for s in ('donor','erased')]
    parity=[r for r in scores if r['scope']=='lineage' and r['route']=='parity_erm' and r['source']=='own']
    exact=all(r['bit_correct']==r['bit_total'] for r in parity)
    fraction=lambda r:r['task_correct']/r['task_total']
    checks=dict(trained_capability=fraction(trained)>=.75,
        heldout_capability=exact and fraction(held)>=.75 and all(fraction(held)-fraction(r)>=.25 for r in controls),
        inherited_record=index['heldout','inherited_g2_ordinary']['task_gains']>index['heldout','inherited_g2_ordinary']['task_losses'],
        comparators=all(index['heldout',k]['task_gains']>index['heldout',k]['task_losses'] and
            index['heldout',k]['query_gains']>=index['heldout',k]['query_losses'] for k in measure.PRIMARY_COMPARATORS))
    labels=dict(trained_capability=('G0_TRAINED_CAPABILITY_SCREEN_PASSED','G0_TRAINED_CAPABILITY_SCREEN_FAILED'),
        heldout_capability=('G2_HELDOUT_CAPABILITY_SCREEN_PASSED','G2_HELDOUT_CAPABILITY_SCREEN_FAILED'),
        inherited_record=('POSITIVE_G2_HELDOUT_INHERITED_TASK_DIFFERENCE','NO_POSITIVE_G2_HELDOUT_INHERITED_TASK_DIFFERENCE'),
        comparators=('POSITIVE_G2_HELDOUT_TASK_DIFFERENCE_AGAINST_EVERY_FIXED_COMPARATOR','NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS'))
    return {k:(labels[k][0 if v else 1] if main else 'ENGINEERING_OR_SYNTHETIC_ONLY') for k,v in checks.items()}


def produce(out,blocks,main):
    out=Path(out);tables={kind:[r for block in blocks for r in block[kind]] for kind in measure.KINDS}
    aggregate={};serialized=0
    for kind,rows in tables.items():
        parsed=write(out/(kind+'.csv'),rows);serialized+=len(parsed)
        aggregate[kind]=reduce(parsed,measure.KEYS[kind])
        serialized+=len(write(out/(kind+'_aggregate.csv'),aggregate[kind]))
    effects={(r['panel'],r['contrast']):r for r in aggregate['effects']}
    verdicts=findings(aggregate['cases'],aggregate['effects'],main)
    summary=dict(experiment='H089',classification='FRESH_DEVELOPMENT_PILOT' if main else 'ENGINEERING_OR_SYNTHETIC_ONLY',
        networks=len(blocks),actual_handoffs=2,root_seed=m.SEED,findings=verdicts,
        primary_trained=score(aggregate['cases'],'trained',0,reader='pair'),primary_heldout=score(aggregate['cases'],'heldout'),
        primary_inherited_record=effects['heldout','inherited_g2_ordinary'],
        primary_comparators=[effects['heldout',k] for k in measure.PRIMARY_COMPARATORS],scores=aggregate['cases'],
        effects=aggregate['effects'],generalization=aggregate['generalization'],records=aggregate['records'],trajectories=aggregate['trajectories'],
        diagnostic_rows=sum(map(len,tables.values())),serialized_rows_checked=serialized,
        population_qualification=False,comparative_superiority_qualified=False,arithmetic_cost_matched=False,
        heldout_writing=False,teacher_rule_supplied_to_writer=False,public_parity_hypothesis_family=True,
        source_controls_passive=True,actual_parent_training_emissions_only=True,founder_teaching_only_at_g0=True,
        g2_outgoing_records_generated=False,private_sources_quoted=False,historical_verdicts_unchanged=True,next_campaign_launched=False)
    save(out/'summary.json',summary)
    lines=['# H089 — inherited responses to unseen combinations','',
        f"{summary['classification']}; {len(blocks)} independent networks, four related births each.",
        'Eight trained and eight held-out combinations; every context and query occurs in training.',
        'Only G0 receives correct teaching labels. Later writers receive actual parent training responses.',
        'Held-out assays are passive. The known parity family is supplied to an ordinary rule-fitting positive control.','']
    for key,value in verdicts.items():lines.append(f'{key}: **{value}**.')
    lines+=['','| Primary endpoint | Complete tasks | Successful queries | Correct bits |','|---|---:|---:|---:|']
    for label,r in [('G0 trained, actual pair reader',summary['primary_trained']),('G2 held-out, ordinary reader',summary['primary_heldout'])]:
        lines.append(f"| {label} | {r['task_correct']}/{r['task_total']} | {r['query_correct']}/{r['query_total']} | {r['bit_correct']}/{r['bit_total']} |")
    lines+=['','| Held-out contrast | Task gains / losses | Query gains / losses | Bit gains / losses | Networks + / − / tie |',
        '|---|---:|---:|---:|---:|']
    for name in ('expression_g0_rewrite_ordinary','inherited_g2_ordinary',*measure.PRIMARY_COMPARATORS):
        r=effects['heldout',name];lines.append(f"| {name} | {r['task_gains']} / {r['task_losses']} | {r['query_gains']} / {r['query_losses']} | {r['bit_gains']} / {r['bit_losses']} | {r['networks_improved']} / {r['networks_worsened']} / {r['networks_tied']} |")
    lines+=['','| Independent lineage / parent policy / reader | Generation | Panel | Complete tasks | Successful queries |','|---|---:|---|---:|---:|']
    for r in aggregate['cases']:
        if r['scope']=='lineage' and r['source']=='own':
            lines.append(f"| {r['route']} / {r['policy']} / {r['reader']} | {r['generation']} | {r['panel']} | {r['task_correct']}/{r['task_total']} | {r['query_correct']}/{r['query_total']} |")
    lines+=['','| Primary G2 trained / held-out success | Birth assays |','|---|---:|']
    for label in ('both_success','trained_only','heldout_only','neither'):
        count=sum(r['assays'] for r in aggregate['generalization'] if tuple(r[k] for k in measure.CASE_KEYS)==('lineage','rewrite','pair',2,'own','ordinary') and r['success_class']==label)
        lines.append(f'| {label} | {count} |')
    lines+=['','The 75% trained and 75% held-out / 25-point source-control criteria are development screens.',
        'All ten comparators must show positive task and nonnegative query differences for the joint advantage label.',
        'A perfect independent parity learner leaves no strict-superiority headroom. Its role is to show that the',
        'held-out task is inferable from the permitted examples with the supplied rule family. Failing trained',
        'retrieval and succeeding on training without generalizing are reported separately.',
        'Copying has coefficient access. Native estimators retain their own records and supplied algorithms;',
        'representation, storage and arithmetic are not matched. Related births are not independent networks.',
        'All panels, sources, paired losses, G2−G0 effects and resource counts remain available below.',
        'H031 causal / forecasting and H033 observation / comparator verdicts remain separate. No predictor search or automatic successor.','',
        '[Cases](cases.csv), [paired effects](effects.csv), [generalization](generalization.csv),',
        '[records](records.csv), [trajectories](trajectories.csv), [summary](summary.json), [figure](overview.png).']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');figure(out,summary);return summary


def figure(out,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.6),layout='constrained')
    styles=[('rewrite','ordinary','ordinary','Rewrite, ordinary parents','#9e6a29'),
        ('rewrite','pair','ordinary','Rewrite, pair parents','#287e8d'),('copy','pair','ordinary','Copy','#6a6a6a'),
        ('quadratic_ls','direct','direct','Quadratic LS','#7d509d'),('parity_erm','direct','direct','Parity ERM','#3f8755')]
    for ax,panel in zip(axes,m.PANELS):
        for route,p,reader,label,color in styles:
            rows=[score(summary['scores'],panel,g,route,p,reader) for g in range(3)]
            ax.plot(range(3),[100*r['task_correct']/r['task_total'] for r in rows],'o-',label=label,color=color)
        ax.set(xticks=range(3),xticklabels=['G0','G1','G2'],ylim=(-3,103),ylabel='Complete tasks (%)',title=panel.capitalize()+' combinations')
    axes[0].legend(fontsize=8)
    fig.suptitle(f"H089 · {summary['networks']} networks · ordinary neural recipients")
    fig.savefig(out/'overview.png',dpi=180);fig.savefig(out/'overview.pdf');plt.close(fig)
