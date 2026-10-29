"""Six finite development verdicts with copying, repair and native ceilings separate."""
from collections import defaultdict
from h007.io import save
from h085.report import write
from h097 import model as m,measure

COMPARATOR_GROUPS={
    'physical_copy':tuple(measure.comparison(scope,'copy',2,'pair','ordinary') for scope in ('lineage','local')),
    'informed_repair':tuple(measure.comparison(scope,'copy_repair',2,'pair','ordinary') for scope in ('lineage','local')),
    'native_controls':tuple(measure.comparison(scope,method,2,'pair','ordinary') for scope in ('lineage','local') for method in m.BASELINES)}

def reduce(rows,keys):
    groups=defaultdict(list)
    for row in rows:groups[tuple(row[k] for k in keys)].append(row)
    result=[]
    for key,items in sorted(groups.items()):
        row=dict(zip(keys,key),networks=len({r['block'] for r in items}))
        for field in items[0]:
            if field in keys or field in measure.DETAILS:continue
            assert all(isinstance(r[field],(int,float)) for r in items),(keys,field)
            values=[r[field] for r in items]
            row[field]=min(values) if field.startswith('minimum_') else max(values) if field.startswith('maximum_') else sum(values)
        if 'task_gains' in row:
            nets=[r['task_gains']-r['task_losses'] for r in items]
            row.update(networks_improved=sum(v>0 for v in nets),networks_worsened=sum(v<0 for v in nets),networks_tied=sum(v==0 for v in nets))
        result.append(row)
    return result


def score(rows,condition,panel,g=2,reader='ordinary',source='own',route='rewrite',scope='lineage',policy='pair'):
    key=(condition,scope,route,policy,g,source,reader,panel)
    return next(r for r in rows if tuple(r[k] for k in measure.KEYS['cases'])==key)


def findings(a,main):
    def capable(panel,g,reader):
        own=score(a['cases'],'loss',panel,g,reader);rate=own['task_correct']/own['task_total']
        return rate>=.75 and all(rate-(r:=score(a['cases'],'loss',panel,g,reader,source))['task_correct']/r['task_total']>=.25 for source in ('donor','erased'))
    effects={r['contrast']:r for r in a['effects'] if r['condition']=='loss' and r['panel']=='heldout'}
    def better(names):return all((r:=effects[name])['task_gains']>r['task_losses'] and r['query_gains']>=r['query_losses'] for name in names)
    g0=capable('heldout',0,'pair')
    checks=dict(heldout_g0=g0,heldout_g2=g0 and capable('heldout',2,'ordinary'),trained_g2=capable('trained',2,'ordinary'),
        **{name:better(names) for name,names in COMPARATOR_GROUPS.items()})
    labels=dict(heldout_g0=('G0_HELDOUT_CAPABILITY_SCREEN_PASSED','G0_HELDOUT_CAPABILITY_SCREEN_FAILED'),
        heldout_g2=('G2_HELDOUT_CAPABILITY_RETAINED_UNDER_LOSS','G2_HELDOUT_INHERITANCE_SCREEN_FAILED'),
        trained_g2=('G2_TRAINED_CAPABILITY_SCREEN_PASSED','G2_TRAINED_CAPABILITY_SCREEN_FAILED'),
        physical_copy=('OBSERVED_G2_HELDOUT_BENEFIT_OVER_PHYSICAL_COPY','NO_OBSERVED_G2_HELDOUT_BENEFIT_OVER_PHYSICAL_COPY'),
        informed_repair=('OBSERVED_G2_HELDOUT_BENEFIT_BEYOND_INFORMED_REPAIR','NO_OBSERVED_G2_HELDOUT_BENEFIT_BEYOND_INFORMED_REPAIR'),
        native_controls=('OBSERVED_G2_HELDOUT_BENEFIT_BEYOND_ALL_NATIVE_CONTROLS','NO_OBSERVED_G2_HELDOUT_BENEFIT_BEYOND_ALL_NATIVE_CONTROLS'))
    return {k:labels[k][0 if v else 1] if main else 'ENGINEERING_OR_SYNTHETIC_ONLY' for k,v in checks.items()}


def produce(out,blocks,main):
    tables={k:[r for b in blocks for r in b[k]] for k in measure.KINDS};aggregate={};serialized=0
    for kind,rows in tables.items():
        parsed=write(out/(kind+'.csv'),rows);serialized+=len(parsed);aggregate[kind]=reduce(parsed,measure.KEYS[kind])
        serialized+=len(write(out/(kind+'_aggregate.csv'),aggregate[kind]))
    primary={name:score(aggregate['cases'],'loss',panel,g,reader) for name,panel,g,reader in
        [('heldout_g0','heldout',0,'pair'),('heldout_g2','heldout',2,'ordinary'),('trained_g2','trained',2,'ordinary')]}
    comparators=[dict(group=group,**r) for group,names in COMPARATOR_GROUPS.items() for r in aggregate['effects']
        if r['condition']=='loss' and r['panel']=='heldout' and r['contrast'] in names]
    assert len(comparators)==12
    summary=dict(experiment='H097',classification='FIXED_DEVELOPMENT_PILOT' if main else 'ENGINEERING_OR_SYNTHETIC_ONLY',
        networks=len(blocks),root_seed=m.SEED,actual_handoffs=2,conditions=list(m.CONDITIONS),findings=findings(aggregate,main),
        primary_scores=primary,primary_comparators=comparators,**aggregate,diagnostic_rows=sum(map(len,tables.values())),serialized_rows_checked=serialized,
        observed_labels_per_packet=8,generated_labels_per_packet=16,new_observed_labels=0,heldout_truth_used_by_writers=False,
        physical_copy_has_protected_blueprint=False,native_controls_use_separate_substrate=True,
        available_pair_edges_per_child=4064,available_interaction_channels_per_child=24,regularization=.1,
        global_architecture_capacity_proven=False,completion_is_supplied_apparatus=True,first_query_context_hold=True,
        population_qualification=False,comparative_superiority_qualified=False,arithmetic_cost_matched=False,
        historical_verdicts_unchanged=True,private_sources_quoted=False,next_campaign_launched=False)
    save(out/'summary.json',summary)
    lines=['# H097 — physical connection loss across actual handoffs','',
        f"**{summary['classification']}**: {len(blocks)} independent networks, four related births, two actual handoffs.",
        'Each replacement loses exactly half its pairwise coupling sites and half its nonlinear response channels.',
        'The same masks constrain all neural methods. Reconstruction fits the remaining architecture from eight actual parent responses.',
        'Repair gets the same responses plus the incoming physical matrix. Copying carries surviving coefficients without a protected blueprint.',
        'The four native direct methods use a separate substrate; their ceilings remain visible.','']
    for key,value in summary['findings'].items():lines.append(f'{key}: **{value}**.')
    lines+=['','| Condition and lineage | G0 unseen tasks / queries | G2 unseen tasks / queries | G2 taught tasks / queries |','|---|---:|---:|---:|']
    for condition in m.CONDITIONS:
        for route in m.ROUTES:
            neural=route in m.NEURAL_ROUTES;cells=[]
            for panel,g,reader in [('heldout',0,'pair'),('heldout',2,'ordinary'),('trained',2,'ordinary')]:
                r=score(aggregate['cases'],condition,panel,g,reader if neural else 'direct',route=route,policy='pair' if neural else 'direct')
                cells.append(f"{r['task_correct']}/{r['task_total']}; {r['query_correct']}/{r['query_total']}")
            lines.append('| '+condition+' / '+route+' | '+' | '.join(cells)+' |')
    lines+=['','| G2 unseen comparator | Task gains / losses | Query gains / losses | Networks improved / worsened |','|---|---:|---:|---:|']
    for r in comparators:lines.append(f"| {r['contrast']} | {r['task_gains']} / {r['task_losses']} | {r['query_gains']} / {r['query_losses']} | {r['networks_improved']} / {r['networks_worsened']} |")
    lines+=['','Pattern fixedness, completion error, context transitions and retrieval scores are separate diagnostic tables.',
        'Stable patterns do not establish successful retrieval or global architectural capacity. Solver work distinguishes executed and reused fits.',
        'These are finite development comparisons. No population qualification, computational-efficiency claim, or RDT forecasting claim follows.',
        'Earlier causal and forecasting verdicts remain separately preserved in historical_verdicts.json.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');return summary
