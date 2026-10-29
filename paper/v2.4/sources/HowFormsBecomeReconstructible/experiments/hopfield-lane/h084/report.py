"""Fresh confirmation report with primary direction, magnitude, harms and costs."""
from pathlib import Path
from h007.io import save
from h081.report import write
from h083.report import reduce_rows
from h084 import model as m,measure,inference


def produce(out,blocks,main):
    out=Path(out);tables={k:[r for b in blocks for r in b[k]] for k in measure.ROW_COUNTS}
    aggregate={};serialized=0
    for kind,rows in tables.items():
        saved=write(out/(kind+'.csv'),rows);assert saved==rows;serialized+=len(saved)
        aggregate[kind]=reduce_rows(saved,measure.KEYS[kind])
        saved=write(out/(kind+'_aggregate.csv'),aggregate[kind]);assert saved==aggregate[kind];serialized+=len(saved)
    inferred=inference.evaluate(blocks,main)
    saved=write(out/'network_values.csv',inferred['network_values']);assert saved==inferred['network_values'];serialized+=len(saved)
    save(out/'inference.json',inferred)
    panels=reduce_rows(tables['queries'],('start','gap'))
    primary=inference.select(panels,start='delayed',gap=4)
    effect=inference.select(aggregate['effects'],start='delayed',gap=4,contrast='pair_minus_ordinary')
    scores=[r for r in aggregate['scores'] if r['start']=='delayed' and r['gap']==4]
    scope='FRESH_FIXED_RULE_CONFIRMATION' if main else 'ENGINEERING_OR_SYNTHETIC_ONLY'
    existence=('DOWNHILL_RESPONSE_PAIR_ESCAPE_ON_FRESH_NETWORKS' if primary['failed_fixed_pair_escape'] else
        'NO_DOWNHILL_RESPONSE_PAIR_ESCAPE_IN_FRESH_FAILURES' if primary['failed_nominal_fixed'] else
        'NO_FAILED_FIXED_ENDPOINTS') if main else 'ENGINEERING_OR_SYNTHETIC_ONLY'
    repair=('NET_TASK_GAIN_ON_FRESH_COHORT' if effect['task_gains']>effect['task_losses'] else
        'NO_NET_TASK_GAIN_ON_FRESH_COHORT') if main else 'ENGINEERING_OR_SYNTHETIC_ONLY'
    primary_rows=[r for r in tables['queries'] if r['start']=='delayed' and r['gap']==4]
    ranges={label:{key:dict(min=min(r[key] for r in rows),max=max(r[key] for r in rows)) if rows else None
        for key in ('minimum_pair_delta','minimum_single_delta','initial_target_energy_gap','pair_target_energy_gap')}
        for label,rows in (('all',primary_rows),('failed_fixed',[r for r in primary_rows if r['failed_nominal_fixed']]))}
    summary=dict(experiment='H084',classification=scope,networks=len(blocks),fresh_networks=main,
        neighborhood_result=existence,repair_result=repair,directional_verdict=inferred['directional_verdict'],
        mean_verdict=inferred['mean_verdict'],inference=inferred,primary_queries=primary,primary_effect=effect,
        primary_scores=scores,primary_ranges=ranges,panel_summaries=panels,panel_effects=aggregate['effects'],
        target_stability=aggregate['targets'][0],new_query_continuations=len(blocks)*m.pair.CONTINUATIONS,
        new_records=len(blocks),predictors=0,inherited_transitions=0,capability_qualification=False,
        comparative_superiority_qualified=False,arithmetic_cost_matched=False,
        response_pairs_only=True,one_pair_attempt=True,energy_tolerance=m.pair.ENERGY_TOL,
        diagnostic_rows=sum(map(len,tables.values())),source_score_rows=24*len(blocks),
        serialized_rows_checked=serialized,historical_verdicts_unchanged=True,next_campaign_launched=False)
    save(out/'summary.json',summary)
    lines=['# H084 — fresh confirmation of response-pair descent','',
        f'{scope}; {len(blocks)} independent networks, four related births and eight queries per birth.',
        'Primary: delayed-feedback endpoint, own source, gap four. Every success and failure is retained.',
        'One unchanged target-free H083 response-pair move, then eight ordinary sweeps; the ordinary',
        'control uses the same sweeps. Secondary selective starts release the gate in both arms.','',
        f"Directional confirmation: **{inferred['directional_verdict']}**.",
        f"Population mean qualification: **{inferred['mean_verdict']}**.",
        f'Neighborhood: **{existence}**. Finite-cohort repair: **{repair}**.','',
        f"Networks with positive / negative / tied task differences: **{inferred['positive_networks']} / {inferred['negative_networks']} / {inferred['tied_networks']}**.",
        f"One-sided exact network sign p = **{inferred['one_sided_exact_sign_p']:.8g}**.",
        f"Observed mean task difference: **{100*inferred['observed_mean_task_difference']:.4f} percentage points**.",
        f"Conservative one-sided 95% population-mean lower bound: **{100*inferred['population_mean_difference_bound']['lower']:.4f} percentage points**.",
        'The sign test concerns the probability of a positive rather than negative network effect.',
        'It does not establish a population-mean magnitude. Related queries/births are not independent',
        'replications; ties remain in the cohort and mean. Separate bounds have no joint coverage claim.','',
        '| Method | Complete tasks | Successful queries | Correct response bits |',
        '|---|---:|---:|---:|']
    for r in scores:lines.append(f"| {r['method']} | {r['task_correct']}/{r['task_total']} | {r['query_correct']}/{r['query_total']} | {r['bit_correct']}/{r['bit_total']} |")
    lines+=['',f"Primary task gains/losses: **{effect['task_gains']}/{effect['task_losses']}**; query gains/losses: **{effect['query_gains']}/{effect['query_losses']}**; bit gains/losses: **{effect['bit_gains']}/{effect['bit_losses']}**.",
        f"Of {primary['failed_nominal_fixed']} initially failed ordinary-fixed queries, {primary['failed_fixed_pair_escape']} admit a downhill response pair.",
        f"Pair moves applied: {primary['pair_selected']}; immediate bit-score regressions: {primary['immediate_bits_worsened']}.",
        f"Ordinary extra flips: {primary['ordinary_accepted_coordinate_flips']}; ordinary/pair final fixed queries: {primary['ordinary_final_fixed']}/{primary['pair_final_fixed']} of {primary['queries']}.",'',
        '| Start / gap | Comparison | Task gains / losses | Query gains / losses | Bit gains / losses |',
        '|---|---|---:|---:|---:|']
    for r in aggregate['effects']:
        lines.append(f"| {r['start']} / {r['gap']} | {r['contrast']} | {r['task_gains']} / {r['task_losses']} | {r['query_gains']} / {r['query_losses']} | {r['bit_gains']} / {r['bit_losses']} |")
    stable=summary['target_stability']
    lines+=['',f"Taught patterns without downhill response pairs: {stable['response_pair_stable']}/{stable['patterns']}.",
        'Secondary gate release is separate from the extra pair move. Secondary gaps and starts cannot',
        'replace the primary. Failure of this response-pair neighborhood does not exclude context pairs,',
        'larger moves, neutral paths or temporary energy increases. Only one pair attempt is made.','',
        'The pair arm adds 128 field dot products and 1,128 pair-delta evaluations per query, plus at most',
        'two flips, before the 640 coordinate trials shared by both arms. These arms are not compute-matched.',
        'Strong ordinary comparators retain the same teaching observations and complete input history.',
        'No efficiency, comparative-superiority, general capability or new inheritance qualification is made.','',
        'The fixed rule and sampling distribution were frozen before these outcomes. No old network is',
        'pooled. H083/H082/H081 and earlier H031/H033 verdicts remain unchanged. Richer inherited tasks',
        'remain separate. No private quotation, public-manuscript edit or automatic successor.','',
        '[Inference](inference.json), [network values](network_values.csv), [scores](scores.csv),',
        '[paired effects](effects.csv), [queries](queries.csv), [summary](summary.json), [figure](overview.png).']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');figure(out,summary);return summary


def figure(out,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13,4.7),layout='constrained')
    p=summary['primary_queries'];s={r['method']:r for r in summary['primary_scores']};inf=summary['inference']
    methods=('query_eight','ordinary_continuation','pair_continuation','quadratic_ls','nearest_history')
    axes[0].bar(range(5),[100*s[k]['task_correct']/s[k]['task_total'] for k in methods],color='#287e8d')
    axes[0].set(xticks=range(5),xticklabels=['Initial','Ordinary +8','Pair +8','Quadratic','Nearest'],
        ylim=(0,105),ylabel='Complete tasks (%)',title='Primary endpoint continuation')
    axes[0].tick_params(axis='x',labelrotation=30)
    axes[1].bar(['Pair available','No pair descent'],[p['failed_fixed_pair_escape'],p['failed_fixed_no_pair_escape']],color=['#287e8d','#b04a3d'])
    axes[1].set(ylabel='Initially failed fixed queries',title='Response-pair neighborhood')
    axes[2].bar(['Positive','Negative','Tied'],[inf['positive_networks'],inf['negative_networks'],inf['tied_networks']],color=['#287e8d','#b04a3d','#969696'])
    axes[2].set(ylabel='Independent networks',title='Paired task difference')
    scope='fresh fixed-rule confirmation' if summary['fresh_networks'] else 'synthetic / engineering only'
    fig.suptitle(f"H084 · {summary['networks']} networks · {scope}")
    fig.savefig(out/'overview.png',dpi=180);fig.savefig(out/'overview.pdf');plt.close(fig)
