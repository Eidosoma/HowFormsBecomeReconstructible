"""Eight distinct verdicts, including the explicit information inequality of passive copying."""
from collections import defaultdict
from h007.io import save
from h085.report import write
from h100 import model as m,measure

KEYS=dict(cases=measure.CASE_KEYS,effects=('contrast','group','panel'),ledger=measure.LEDGER_KEYS)
DETAILS={'block','birth','record','read','kind'}
def aggregate(rows,keys):
    groups=defaultdict(list)
    for row in rows:groups[tuple(row[k] for k in keys)].append(row)
    result=[]
    for identity,items in sorted(groups.items()):
        out=dict(zip(keys,identity),networks=len({r['block'] for r in items}))
        for key in items[0]:
            if key in keys or key in DETAILS:continue
            assert all(isinstance(r[key],(int,float)) for r in items),key
            out[key]=sum(r[key] for r in items)
        if 'task_gains' in out:
            nets=[r['task_gains']-r['task_losses'] for r in items]
            out.update(networks_improved=sum(v>0 for v in nets),networks_worsened=sum(v<0 for v in nets),networks_tied=sum(v==0 for v in nets))
        result.append(out)
    return result
def score(rows,g=2,panel='heldout',source='own',mode='erased_reference_repair',route='rewrite',scope='lineage'):
    neural=route in ('rewrite','copy');policy='pair' if neural or scope=='local' else 'direct'
    reader=('pair' if g==0 else 'ordinary') if neural else 'direct'
    wanted=(scope,route,policy,g,source,reader,mode,panel)
    return next(r for r in rows if tuple(r[k] for k in measure.CASE_KEYS)==wanted)
def decisions(tables,calibrations):
    def capable(g,panel):
        own=score(tables['cases'],g,panel);rate=own['task_correct']/own['task_total']
        return rate>=.75 and all(rate-(r:=score(tables['cases'],g,panel,source))['task_correct']/r['task_total']>=.25 for source in ('donor','erased'))
    effects={r['contrast']:r for r in tables['effects'] if r['panel']=='heldout'}
    def better(names):return all((r:=effects[name])['task_gains']>r['task_losses'] and r['query_gains']>=r['query_losses'] for name in names)
    g0=capable(0,'heldout')
    return dict(calibration_recovery=all(r['calibration_recovery_passed'] and r['no_reference_unresolved'] for r in calibrations),
        heldout_g0=g0,heldout_g2=g0 and capable(2,'heldout'),trained_g2=capable(2,'trained'),
        reference_observations=better(['references_rewrite_g2','references_copy_g2']),
        observation_limited_copy=better(['observation_limited_copy_'+s for s in ('lineage','local')]),
        adaptive_copy=better(['adaptive_copy_'+s for s in ('lineage','local')]),
        native_controls=better(['native_'+s+'_'+method for s in ('lineage','local') for method in m.BASELINES]))
LABELS=dict(
    calibration_recovery=('CALIBRATION_RECOVERY_AND_UNRESOLVED_CONTROL_PASSED','CALIBRATION_RECOVERY_OR_UNRESOLVED_CONTROL_FAILED'),
    heldout_g0=('ACQUIRED_UNSEEN_COMBINATION_SCREEN_PASSED','ACQUIRED_UNSEEN_COMBINATION_SCREEN_FAILED'),
    heldout_g2=('UNSEEN_COMBINATIONS_RETAINED_THROUGH_TWO_HANDOFFS','UNSEEN_TWO_HANDOFF_RETENTION_SCREEN_FAILED'),
    trained_g2=('TAUGHT_TWO_HANDOFF_RETENTION_SCREEN_PASSED','TAUGHT_TWO_HANDOFF_RETENTION_SCREEN_FAILED'),
    reference_observations=('BENEFIT_FROM_INFORMATIVE_REFERENCE_INTERACTION','NO_OBSERVED_REFERENCE_INTERACTION_BENEFIT'),
    observation_limited_copy=('BENEFIT_OVER_COPY_WITHOUT_CALIBRATION_INFORMATION','NO_BENEFIT_OVER_COPY_WITHOUT_CALIBRATION_INFORMATION'),
    adaptive_copy=('BENEFIT_BEYOND_EQUALLY_INFORMED_ADAPTIVE_COPY','NO_BENEFIT_BEYOND_EQUALLY_INFORMED_ADAPTIVE_COPY'),
    native_controls=('BENEFIT_BEYOND_ALL_EQUALLY_INFORMED_NATIVE_CONTROLS','NO_BENEFIT_BEYOND_ALL_EQUALLY_INFORMED_NATIVE_CONTROLS'))
def produce(out,blocks,calibrations,main):
    tables={};row_count=serialized=0
    for kind in KEYS:
        rows=[r for block in blocks for r in block[kind]];row_count+=len(rows)
        parsed=write(out/(kind+'.csv'),rows);serialized+=len(parsed);tables[kind]=aggregate(parsed,KEYS[kind])
        serialized+=len(write(out/(kind+'_aggregate.csv'),tables[kind]))
    gates=decisions(tables,calibrations)
    findings={k:LABELS[k][0 if v else 1] if main else 'ENGINEERING_OR_SYNTHETIC_ONLY' for k,v in gates.items()}
    primary={k:score(tables['cases'],g,panel) for k,g,panel in (('heldout_g0',0,'heldout'),('heldout_g2',2,'heldout'),('trained_g2',2,'trained'))}
    summary=dict(experiment='H100',classification='FRESH_FINITE_COHORT_CONFIRMATION' if main else 'ENGINEERING_OR_SYNTHETIC_ONLY',
        networks=len(blocks),root_seed=m.SEED,actual_handoffs_per_lineage=2,findings=findings,primary_scores=primary,**tables,
        diagnostic_rows=row_count,serialized_rows_checked=serialized,reference_events_per_repair=2,reference_values_per_repair=96,
        supplied_reference_port=True,learned_decoder_signs=48,calibration_affects_recurrence=False,
        physical_task_transmission_requires_semantic_decoder=False,information_unequal_copy_comparison_labelled=True,
        native_controls_use_separate_substrate=True,canonical_acquisitions_are_numerical_controls=True,
        fresh_confirmation=main,population_qualification=False,comparative_superiority_qualified=False,arithmetic_cost_matched=False,
        original_H097_acceptance='FAILED',H095_retention_recognized=True,historical_verdicts_unchanged=True,private_sources_quoted=False,next_campaign_launched=False)
    save(out/'summary.json',summary)
    lines=['# H100 — learned calibration and inherited unseen combinations','',
        f"**{summary['classification']}**: {len(blocks)} independent networks, four related births each, two actual handoffs.",
        'Only a learned output-polarity decoder is erased. The reference port, sign model and recurrent dynamics remain supplied apparatus.',
        'Two labelled reference commands provide 96 measured values identifying 48 polarity signs.',
        'Reference-observation benefit is distinct from benefit beyond equally informed copying and native methods.','']
    for key,value in findings.items():lines.append(f'{key}: **{value}**.')
    lines+=['','| G2 independent lineage and decoder | Unseen tasks / queries | Taught tasks / queries | Unresolved unseen bits |','|---|---:|---:|---:|']
    for route in m.ROUTES:
        for mode in m.MODES:
            a=score(tables['cases'],mode=mode,route=route);b=score(tables['cases'],panel='trained',mode=mode,route=route)
            lines.append(f"| {route} / {mode} | {a['task_correct']}/{a['task_total']}; {a['query_correct']}/{a['query_total']} | {b['task_correct']}/{b['task_total']}; {b['query_correct']}/{b['query_total']} | {a['unresolved_bits']} |")
    lines+=['','| Unseen paired comparison | Task gains / losses | Query gains / losses | Networks improved / worsened |','|---|---:|---:|---:|']
    for r in tables['effects']:
        if r['panel']=='heldout':lines.append(f"| {r['contrast']} | {r['task_gains']} / {r['task_losses']} | {r['query_gains']} / {r['query_losses']} | {r['networks_improved']} / {r['networks_worsened']} |")
    lines+=['','No-reference outputs are unresolved, not incorrect binary guesses. The information-unequal copy comparison cannot establish superiority over equally informed copying.',
        'The calibration formula is elementary and the references supply its missing information explicitly. The empirical target is inherited task retention under this boundary.',
        'Matched calibration tapes and canonical controls are not extra samples. The information ledger counts logical recipients separately from panels and recipient readers.',
        'No population-confidence, efficiency, arbitrary-meaning reconstruction, jointly learned recurrent-reader, or RDT forecasting claim is made.',
        'H095 acquired retention and comparator ties, H097 failure, H098 correction and H031/H033 separate verdicts remain preserved.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');return summary
