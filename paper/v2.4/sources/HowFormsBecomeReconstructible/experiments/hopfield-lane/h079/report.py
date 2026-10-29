"""Storage, access, iteration and ordinary-comparator verdicts remain separate."""
from collections import defaultdict
import csv
import numpy as np
from h007.io import save
from h076 import report as previous
from h079 import model as m,inference
from h078 import measure

SEED,SAMPLES,INTERVALS=7907901,20000,1784
CI_KEYS=('schedule','gap','scenario','contrast','metric')
select=previous.select
csv_write=previous.csv_write


def reduce(rows,keys):
    groups={}
    for r in rows:
        key=tuple(r[k] for k in keys)
        if key not in groups:groups[key]={k:v for k,v in r.items() if k!='block'};continue
        for k,v in r.items():
            if k in ('block',*keys):continue
            absent=(k.startswith('donor_') and v==-1) or (k in measure.DYNAMIC and r.get('method') in m.BASELINES) or ('context_' in k and r.get('scenario')=='context_absent')
            if absent:assert v==groups[key][k]==-1
            elif k.startswith('min_'):groups[key][k]=min(groups[key][k],v)
            elif k=='max_coordinate_energy_increase':groups[key][k]=max(groups[key][k],v)
            else:groups[key][k]+=v
    return [groups[k] for k in sorted(groups)]


def network_values(block):
    rows=[]
    for schedule in m.SCHEDULES:
        one={k:[{kk:vv for kk,vv in r.items() if kk!='schedule'} for r in block[k] if r['schedule']==schedule] for k in measure.ONE_TABLE_KEYS}
        rows.extend(dict(schedule=schedule,**r) for r in previous.network_values(one))
    for r in block['schedule_effects']:
        for metric,n in (('task',r['tasks']),('query',r['queries']),('bit',r['bits']),('exact',r['queries'])):
            rows.append(dict(schedule=r['contrast'],block=r['block'],gap=r['gap'],scenario=r['scenario'],
                contrast=r['method'],metric=metric,value=(r[metric+'_gains']-r[metric+'_losses'])/n))
    for r in block['storage']:
        for metric,n in (('strict_patterns',r['patterns']),('fixed_patterns',r['patterns']),
                         ('response_unstable_bits',r['response_bits']),('context_unstable_bits',r['context_bits'])):
            rows.append(dict(schedule='nominal_record',block=r['block'],gap=-1,scenario=r['source'],contrast='stored_patterns',metric=metric,value=r[metric]/n))
    assert len(rows)==INTERVALS;return rows


def intervals(networks):
    grouped=defaultdict(list)
    for r in networks:grouped[tuple(r[k] for k in CI_KEYS)].append(r)
    blocks=sorted({r['block'] for r in networks});n=len(blocks)
    draws=np.random.default_rng(SEED).integers(n,size=(SAMPLES,n));counts=np.stack([(draws==i).sum(1) for i in range(n)],axis=1)
    result=[]
    for key in sorted(grouped):
        rows=sorted(grouped[key],key=lambda r:r['block']);assert [r['block'] for r in rows]==blocks
        values=np.asarray([r['value'] for r in rows]);sample=counts@values/n
        np.testing.assert_allclose(sample[:100],values[draws[:100]].mean(1),rtol=0,atol=1e-14)
        low,high=np.quantile(sample,[.025,.975])
        result.append(dict(zip(CI_KEYS,key),networks=n,mean=float(values.mean()),lower=float(low),upper=float(high)))
    return result


def produce(out,blocks,main):
    tables={k:[r for b in blocks for r in b[k]] for k in measure.TABLE_KEYS}
    grouped={k:reduce(rows,measure.TABLE_KEYS[k]) for k,rows in tables.items()}
    networks=[r for b in blocks for r in network_values(b)];ci=intervals(networks);assert len(ci)==INTERVALS
    all_tables={**tables,**{k+'_aggregate':v for k,v in grouped.items()},'network_values':networks,'intervals':ci}
    for name,rows in all_tables.items():
        csv_write(out/(name+'.csv'),rows)
        with (out/(name+'.csv')).open() as f:
            for actual,wanted in zip(csv.DictReader(f),rows,strict=True):assert all(actual[k]==str(v) for k,v in wanted.items()),name
    for kind,keys in measure.TABLE_KEYS.items():
        with (out/(kind+'.csv')).open() as f:
            parsed=[{k:v if k in ('schedule','source','scenario','method','comparator','control','contrast') else float(v) if k.endswith('_sum') or k.startswith('min_') or k=='max_coordinate_energy_increase' else int(v) for k,v in r.items()} for r in csv.DictReader(f)]
        assert reduce(parsed,keys)==grouped[kind]
    decisions={}
    for schedule in m.SCHEDULES:
        one={k:[{kk:vv for kk,vv in r.items() if kk!='schedule'} for r in grouped[k] if r['schedule']==schedule] for k in measure.ONE_TABLE_KEYS}
        decisions[schedule]=previous.decision(one,[],main)
    contrasts={left+'_minus_'+right:select(grouped['schedule_effects'],contrast=left+'_minus_'+right,gap=4,scenario='own',method='query_eight') for left,right in measure.PAIRS}
    stability=select(grouped['storage'],source='own')
    summary=dict(experiment='H079',classification='fresh prospective timing replication' if main else 'engineering or synthetic checks',
        networks=len(blocks),primary_schedule='delayed',primary_gap=4,query_threshold_bits=44,task_response_bits=48,
        associations_per_task=8,fresh_births_per_network=4,bootstrap_seed=SEED,bootstrap_samples=SAMPLES,network_intervals=INTERVALS,
        schedules=list(m.SCHEDULES),feedback_tapes={k:v.tolist() for k,v in m.FEEDBACK.items()},schedule_decisions=decisions,
        capability_screen=decisions['delayed']['capability_screen'],primary_schedule_contrasts=contrasts,
        stored_pattern_diagnostics=stability,all_taught_patterns_strictly_stable=stability['strict_patterns']==stability['patterns'],
        record_budget_values=m.BUDGET,record_budget_bytes=8*m.BUDGET,materialized_matrix_bytes=m.N*m.N*8,
        learned_values=dict(projection=m.BUDGET,linear_ls=640,quadratic_ls=1120,nearest_history=1024),
        conventional_history_buffer_values=80,context_preparation_sweeps=4,query_window_sweeps=8,
        all_schedules_share_prequery_state=True,off_schedule_removes_response_response_edges_only=True,
        query_off_means_zero_free_updates=True,switch_work_separate_from_clamp_work=True,
        endpoint_flags_for_final_and_nominal_matrices=True,conventional_rows_repeated_by_schedule=True,
        acquisition_and_arithmetic_cost_matched=False,comparative_superiority_qualified=False,inheritance_tested=False,predictors_fitted=0,
        historical_verdicts_unchanged=True,next_campaign_launched=False)
    qualification=inference.evaluate(blocks,main)
    summary.update(replication_design=qualification['design'],
        timing_iteration_verdict=qualification['timing_iteration_verdict'],
        primary_absolute_task_interval=qualification['absolute_delayed_task_rate'],
        primary_simultaneous_task_contrasts=qualification['simultaneous_task_contrasts'],
        population_task_rate_at_least_75_supported=qualification['population_task_rate_at_least_75_supported'],
        replication_outcomes_pooled_with_development=False)
    save(out/'replication.json',qualification)
    assert __import__('json').loads((out/'replication.json').read_text())==qualification
    save(out/'summary.json',summary)
    save(out/'table_verification.json',dict(passed=True,rows={k:len(v) for k,v in all_tables.items()},serialized_reduction_exact=True))
    lines=['# H079 — query-onset response feedback','',f"**{len(blocks)} networks; {summary['classification']}.**",'',
        'All schedules use the same projection record and prepared state. On/delayed/off change only',
        'response-to-response feedback in the query window. Zero query sweeps means no free updates;',
        'feedback off retains all other connections. Switch and clamp work are separately audited.',
        'Ordinary controls share observations and explicit history; repeated rows are not extra evidence.','',
        '| Schedule | Gap | Condition | Reader | Complete tasks | Successful queries | Exact responses |',
        '|---|---:|---|---|---:|---:|---:|']
    for r in grouped['scores']:
        lines.append(f"| {r['schedule']} | {r['gap']} | {r['scenario']} | {r['method']} | {r['task_correct']}/{r['task_total']} | {r['query_correct']}/{r['query_total']} | {r['exact_correct']}/{r['query_total']} |")
    lines+=['',f"Nominal strictly stable taught patterns: {stability['strict_patterns']}/{stability['patterns']}.",'',
        '| Schedule | Primary criterion | Value | Threshold | Passed |','|---|---|---:|---:|---|']
    for schedule,result in decisions.items():
        for name,g in result['capability_gates'].items():lines.append(f"| {schedule} | {name} | {g['value']:.4f} | {g['threshold']:.2f} | {g['passed']} |")
    lines+=['',f"Primary delayed capability: **{summary['capability_screen']}**.",'',
        'Schedule rescue, benefit beyond continuous-off feedback, extra-sweep benefit and ordinary',
        'comparator gaps remain separate. All gates are unchanged exploratory point criteria, with',
        'descriptive whole-network intervals. No secondary-panel rescue, comparative-superiority',
        'qualification, inheritance result, RDT forecast or automatic next campaign is claimed.']
    absolute=qualification['absolute_delayed_task_rate']
    lines+=['',f"Prospective timing/iteration verdict: **{qualification['timing_iteration_verdict']}**.",'',
        f"Primary task rate: {absolute['mean']:.4f}; bounded-network 95% interval [{absolute['lower']:.4f}, {absolute['upper']:.4f}].",'',
        'The absolute interval and the following simultaneous one-sided family have separate 95% coverage statements.',
        'The seven capability gates remain point-estimate screens. Ordinary-comparator superiority is separate.','',
        '| Planned task contrast | Mean | Simultaneous lower bound |',
        '|---|---:|---:|']
    for name,value in qualification['simultaneous_task_contrasts'].items():
        lines.append(f"| {name} | {value['mean']:.4f} | {value['lower']:.4f} |")
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');figure(out,grouped,main)
    return summary


def figure(out,grouped,main):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,8));x=np.arange(6)
    for ax,metric in zip(axes[0],('task','query')):
        for shift,schedule in zip((-.24,0,.24),m.SCHEDULES):
            rows=[select(grouped['scores'],schedule=schedule,gap=4,scenario='own',method=method) for method in m.METHODS]
            ax.bar(x+shift,[100*r[metric+'_correct']/r[metric+'_total'] for r in rows],width=.24,label=schedule)
        ax.set_xticks(x,('0 sweeps','1 sweep','8 sweeps','linear LS','quadratic LS','nearest'),rotation=18)
        ax.set(ylabel='Success (%)',ylim=(0,105),title='Complete tasks' if metric=='task' else 'Queries: at least 44/48 bits');ax.legend()
    ax=axes[1,0]
    for shift,schedule in zip((-.24,0,.24),m.SCHEDULES):
        rows=[select(grouped['scores'],schedule=schedule,gap=4,scenario=s,method='query_eight') for s in m.SCENARIOS]
        ax.bar(np.arange(5)+shift,[100*r['task_correct']/r['task_total'] for r in rows],width=.24,label=schedule)
    ax.set_xticks(np.arange(5),('own','context\nswapped','context\nabsent','foreign','erased'))
    ax.set(ylabel='Complete tasks (%)',ylim=(0,105),title='Eight query sweeps; four-sweep gap');ax.legend()
    ax=axes[1,1]
    for shift,gap in ((-.18,0),(.18,4)):
        rows=[select(grouped['scores'],schedule=s,gap=gap,scenario='own',method='query_eight') for s in m.SCHEDULES]
        ax.bar(np.arange(3)+shift,[100*r['task_correct']/r['task_total'] for r in rows],width=.36,label=f'gap {gap}')
    ax.set_xticks(np.arange(3),m.SCHEDULES);ax.set(ylabel='Complete tasks (%)',ylim=(0,105),title='Delay control; eight query sweeps');ax.legend()
    fig.suptitle('H079: timing of response feedback — '+('fresh replication' if main else 'engineering / synthetic checks'))
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'overview.png',dpi=170);fig.savefig(out/'overview.pdf');plt.close(fig)
