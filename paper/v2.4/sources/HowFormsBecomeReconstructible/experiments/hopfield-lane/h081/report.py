"""Three separate development screens, paired harms and descriptive intervals."""
from collections import defaultdict
import csv
import numpy as np
from h007.io import save
from h076 import report as base
from h078.report import reduce
from h081 import model as m,measure

SEED,SAMPLES,INTERVALS=8108101,20000,3308
CI_KEYS=('policy','gap','scenario','contrast','metric')
select=base.select


def network_values(block):
    rows=[]
    for policy in m.POLICIES:
        one={k:[{kk:vv for kk,vv in r.items() if kk!='policy'} for r in block[k] if r['policy']==policy] for k in measure.old.ONE_TABLE_KEYS}
        rows.extend(dict(policy=policy,**r) for r in base.network_values(one))
    for r in block['policy_effects']:
        for metric,n in (('task',r['tasks']),('query',r['queries']),('bit',r['bits']),('exact',r['queries'])):
            rows.append(dict(block=r['block'],policy=m.PRIMARY,gap=r['gap'],scenario=r['scenario'],
                contrast='policy_minus__'+r['comparator'],metric=metric,value=(r[metric+'_gains']-r[metric+'_losses'])/n))
    for r in block['mechanism']:
        for metric in ('first_wrong_corrected','new_final_errors','vetoed_harm','vetoed_repair'):
            rows.append(dict(block=r['block'],policy=r['policy'],gap=r['gap'],scenario=r['scenario'],
                contrast='mechanism_per_response_bit',metric=metric,value=r[metric]/r['bits']))
    for r in block['storage']:
        for metric in ('policy_conditional_fixed_patterns','ordinary_conditional_fixed_patterns','nominal_conditional_fixed_patterns'):
            rows.append(dict(block=r['block'],policy=r['policy'],gap=-1,scenario=r['source'],
                contrast='taught_pattern_stability',metric=metric,value=r[metric]/r['patterns']))
    assert len(rows)==INTERVALS;return rows


def intervals(networks):
    grouped=defaultdict(list)
    for r in networks:grouped[tuple(r[k] for k in CI_KEYS)].append(r)
    blocks=sorted({r['block'] for r in networks});n=len(blocks)
    draws=np.random.default_rng(SEED).integers(n,size=(SAMPLES,n));counts=np.stack([(draws==i).sum(1) for i in range(n)],axis=1)
    rows=[]
    for key in sorted(grouped):
        group=sorted(grouped[key],key=lambda r:r['block']);assert [r['block'] for r in group]==blocks
        values=np.asarray([r['value'] for r in group]);sample=counts@values/n
        np.testing.assert_allclose(sample[:100],values[draws[:100]].mean(1),rtol=0,atol=1e-14)
        lo,hi=np.quantile(sample,[.025,.975])
        rows.append(dict(zip(CI_KEYS,key),networks=n,mean=float(values.mean()),lower=float(lo),upper=float(hi)))
    assert len(rows)==INTERVALS;return rows


def decisions(grouped,main):
    capability={}
    for policy in m.POLICIES:
        one={k:[{kk:vv for kk,vv in r.items() if kk!='policy'} for r in grouped[k] if r['policy']==policy] for k in measure.old.ONE_TABLE_KEYS}
        capability[policy]=base.decision(one,[],main)
    chosen=select(grouped['mechanism'],policy=m.PRIMARY,gap=4,scenario='own')
    delayed=select(grouped['mechanism'],policy='delayed',gap=4,scenario='own')
    def delta(comparator):
        row=select(grouped['policy_effects'],gap=4,scenario='own',comparator=comparator)
        return (row['task_gains']-row['task_losses'])/row['tasks']
    harm=1-chosen['new_final_errors']/delayed['new_final_errors'] if delayed['new_final_errors'] else 0.
    repair=chosen['first_wrong_corrected']/delayed['first_wrong_corrected'] if delayed['first_wrong_corrected'] else 0.
    mechanism={name:dict(value=value,threshold=limit,passed=value>=limit) for name,value,limit in
        (('new_final_error_reduction',harm,.25),('initial_error_repair_retention',repair,.95),('task_gain_over_delayed',delta('delayed'),.10))}
    if not delayed['new_final_errors']:mechanism['new_final_error_reduction']['passed']=False
    if not delayed['first_wrong_corrected']:mechanism['initial_error_repair_retention']['passed']=False
    selective={p:dict(value=delta(p),threshold=.05,passed=delta(p)>=.05) for p in ('half_feedback','all_hysteresis')}
    verdict=lambda gates,label:(''+label+'_PASSED' if all(g['passed'] for g in gates.values()) else label+'_FAILED') if main else 'ENGINEERING_OR_SYNTHETIC_ONLY'
    return dict(mechanism_screen=verdict(mechanism,'SELECTIVE_FEEDBACK_MECHANISM_SCREEN'),mechanism_gates=mechanism,
        selectivity_screen=verdict(selective,'SELECTIVITY_OVER_SIMPLE_CONTROLS_SCREEN'),selectivity_gates=selective,
        capability_screen=capability[m.PRIMARY]['capability_screen'],policy_capability=capability,
        comparative_superiority_qualified=False,new_population_qualification=False)


def write(path,rows):
    base.csv_write(path,rows)
    with path.open() as f:parsed=list(csv.DictReader(f))
    assert len(parsed)==len(rows)
    for saved,wanted in zip(parsed,rows):assert all(saved[k]==str(v) for k,v in wanted.items())
    types={k:float if any(isinstance(r[k],float) for r in rows) else type(rows[0][k]) for k in rows[0]}
    return [{k:types[k](v) for k,v in r.items()} for r in parsed]


def produce(out,blocks,main):
    tables={k:[r for b in blocks for r in b[k]] for k in measure.TABLE_KEYS}
    grouped={k:reduce(rows,measure.TABLE_KEYS[k]) for k,rows in tables.items()}
    networks=[r for b in blocks for r in network_values(b)];ci=intervals(networks)
    counts={}
    for name,rows in tables.items():
        parsed=write(out/(name+'.csv'),rows);assert reduce(parsed,measure.TABLE_KEYS[name])==grouped[name]
        write(out/(name+'_aggregate.csv'),grouped[name]);counts[name]=len(rows)
    write(out/'network_values.csv',networks);write(out/'intervals.csv',ci)
    summary=dict(experiment='H081',classification='fresh prospective development screen' if main else 'engineering or synthetic checks',
        networks=len(blocks),primary_policy=m.PRIMARY,primary_gap=4,policies=list(m.POLICIES),barrier_multiplier=m.BARRIER,
        bootstrap_seed=SEED,bootstrap_samples=SAMPLES,network_intervals=len(ci),**decisions(grouped,main),
        primary_scores=[r for r in grouped['scores'] if r['gap']==4 and r['scenario']=='own'],
        primary_mechanism=[r for r in grouped['mechanism'] if r['gap']==4 and r['scenario']=='own'],
        primary_policy_effects=[r for r in grouped['policy_effects'] if r['gap']==4 and r['scenario']=='own'],
        target_stability=grouped['storage'],record_budget_values=m.BUDGET,additional_learned_parameters=0,
        conventional_history_buffer_values=80,arithmetic_cost_matched=False,new_policy_paths_propagated=True,
        inherited_transitions=0,predictors_fitted=0,historical_verdicts_unchanged=True,next_campaign_launched=False)
    save(out/'summary.json',summary);save(out/'table_verification.json',dict(passed=True,rows=counts,
        network_values=len(networks),network_intervals=len(ci),serialized_reduction_exact=True))
    lines=['# H081 — a fixed selective-feedback rule','',f"{len(blocks)} networks; {summary['classification']}.",'',
        'The candidate applies a unit input-magnitude flip barrier only to cue-aligned response bits.',
        'Half feedback and a barrier on all bits are fixed mechanism controls. No threshold was tuned.',
        'All paths are propagated and independently replayed. Policy-fixed and ordinary-fixed endpoints',
        'remain distinct. Veto counts are local events, including repeated blocked proposals.',
        'All new policies share the delayed/off first sweep; always-on retains its different first sweep.',
        'Mechanism counts are relative to each policy\'s own first sweep.','',
        '| Policy | Complete tasks | Successful queries | New final errors | Initial errors corrected | Vetoed harm / repair |',
        '|---|---:|---:|---:|---:|---:|']
    for policy in m.POLICIES:
        r=select(grouped['scores'],policy=policy,gap=4,scenario='own',method='query_eight')
        z=select(grouped['mechanism'],policy=policy,gap=4,scenario='own')
        lines.append(f"| {policy} | {r['task_correct']}/{r['task_total']} | {r['query_correct']}/{r['query_total']} | {z['new_final_errors']} | {z['first_wrong_corrected']} | {z['vetoed_harm']} / {z['vetoed_repair']} |")
    lines+=['',f"Mechanism: **{summary['mechanism_screen']}**.",f"Selectivity: **{summary['selectivity_screen']}**.",
        f"Capability: **{summary['capability_screen']}**.",'','| Screen | Gate | Value | Threshold | Passed |','|---|---|---:|---:|---|']
    for screen,gates in (('mechanism',summary['mechanism_gates']),('selectivity',summary['selectivity_gates']),
                          ('capability',summary['policy_capability'][m.PRIMARY]['capability_gates'])):
        for name,g in gates.items():lines.append(f"| {screen} | {name} | {g['value']:.6f} | {g['threshold']} | {g['passed']} |")
    lines+=['','These are frozen point-estimate development screens. Whole-network 95% bootstrap intervals',
        'are descriptive, not a new multiplicity-adjusted population qualification. Secondary gaps and',
        'controls cannot replace the primary. Original zero/one/eight-sweep scores, source controls,',
        'paired gains/losses and linear/quadratic/nearest-history comparators are all retained.','',
        'H079 timing benefit and capability failure, H031 causal/forecast results, both H033 verdicts',
        'and H071/H076/H077/H078 history remain unchanged. No inherited transition, predictor, private',
        'quotation, public manuscript edit or automatic successor is included.','',
        '[Scores](scores.csv), [paired policy effects](policy_effects.csv), [mechanism](mechanism.csv),',
        '[intervals](intervals.csv), [summary](summary.json), [figure](overview.png).']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');figure(out,grouped,main);return summary


def figure(out,grouped,main):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained');x=np.arange(len(m.POLICIES))
    labels=('On','Delayed','Off','Selective','Half','All bits')
    scores=[select(grouped['scores'],policy=p,gap=4,scenario='own',method='query_eight') for p in m.POLICIES]
    mech=[select(grouped['mechanism'],policy=p,gap=4,scenario='own') for p in m.POLICIES]
    axes[0].bar(x,[100*r['task_correct']/r['task_total'] for r in scores],color='#287e8d');axes[0].axhline(75,color='black',ls='--',lw=.8)
    axes[0].set(ylabel='Complete tasks (%)',ylim=(0,105),title='Primary capability')
    for ax,key,title in ((axes[1],'new_final_errors','Initially correct bits ending wrong'),(axes[2],'first_wrong_corrected','Initial errors corrected')):
        ax.bar(x,[r[key] for r in mech],color='#b04a3d' if key=='new_final_errors' else '#287e8d');ax.set(title=title,ylabel='Response bits')
    for ax in axes:ax.set_xticks(x,labels,rotation=25)
    fig.suptitle('H081 · '+('fresh development' if main else 'engineering / synthetic')+f' · {scores[0]["task_total"]//4} networks')
    fig.savefig(out/'overview.png',dpi=180);fig.savefig(out/'overview.pdf');plt.close(fig)
