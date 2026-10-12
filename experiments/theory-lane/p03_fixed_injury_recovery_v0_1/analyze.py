"""Fixed block summaries and probe/evaluation choices for fresh reads."""
import csv
import math

import numpy as np

from common import arrays,read,write

CHOICES=('always_incoming','always_outgoing','signed_transfer','unsigned_access','direct_read_probe')


def csv_write(path,rows):
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def wilson(successes,n):
    z=1.959963984540054
    p=successes/n
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    return [max(0.,center-half),min(1.,center+half)]


def summary(values,cfg):
    assert len(values)==len(cfg['blocks']) and np.isfinite(values).all()
    x=np.asarray(values,float)
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    indices=rng.integers(0,len(x),size=(cfg['bootstrap_replicates'],len(x)))
    lower,upper=np.quantile(x[indices].mean(axis=1),[.025,.975])
    return dict(mean=float(x.mean()),descriptive_block_bootstrap_95=[float(lower),float(upper)],
                by_block={str(b):float(v) for b,v in zip(cfg['blocks'],x)})


def weight(a,b):
    # Output is probability of choosing outgoing; exact ties split evenly.
    return np.where(b>a,1.,np.where(b<a,0.,.5))


def choices(data,cfg,bi):
    n=len(data['founders'])
    probes=np.take(data['both_pass'][bi],cfg['probe_replicates'],axis=2)
    rate=probes.mean(axis=2)
    return dict(always_incoming=np.zeros(n),always_outgoing=np.ones(n),
        signed_transfer=weight(data['signed_transfer'][:,0],data['signed_transfer'][:,1]),
        unsigned_access=weight(data['unsigned_access'][:,0],data['unsigned_access'][:,1]),
        direct_read_probe=weight(rate[:,0],rate[:,1]))


def analyze(folder,cfg):
    tables,states,blocks,decision_rows=[],[],[],[]
    data_by_block={b:arrays(folder/f'reads_{b:06d}.npz') for b in cfg['blocks']}
    for block,data in data_by_block.items():
        n=len(data['founders'])
        assert data['both_pass'].shape==(3,n,3,16)
        assert data['replicates'].tolist()==cfg['replicates']
        assert not data['both_pass'][:,:,2].any()
        for bi,budget in enumerate(cfg['budgets']):
            for vi,variant in enumerate(cfg['variants']):
                outcome=data['both_pass'][bi,:,vi]
                blocks.append(dict(block=block,budget=budget,variant=variant,cases=n,reads=outcome.size,
                    successes=int(outcome.sum()),rate=float(outcome.mean())))
                for case in range(n):
                    context=dict(block=block,local_case=case,history=cfg['histories'][int(data['histories'][case])],
                                 founder=int(data['founders'][case]),recipient=int(data['recipients'][case]),budget=budget,variant=variant)
                    count=int(outcome[case].sum())
                    interval=wilson(count,16)
                    states.append(dict(**context,successes=count,reads=16,rate=count/16,
                        conditional_MC_wilson_lower=interval[0],conditional_MC_wilson_upper=interval[1],
                        signed_transfer=float(data['signed_transfer'][case,vi]),unsigned_access=float(data['unsigned_access'][case,vi])))
                    for ri in cfg['replicates']:
                        ports=data['mean_ports'][bi,case,vi,ri].ravel()
                        tables.append(dict(**context,replicate=ri,split='probe' if ri in cfg['probe_replicates'] else 'evaluation',
                            success=int(outcome[case,ri]),margin=float(data['min_margin'][bi,case,vi,ri]),
                            plus_a=float(ports[0]),plus_b=float(ports[1]),minus_a=float(ports[2]),minus_b=float(ports[3])))
            choice=choices(data,cfg,bi)
            evaluation=np.take(data['both_pass'][bi,:,:2],cfg['evaluation_replicates'],axis=2).mean(axis=2)
            for case in range(n):
                a,b=map(float,evaluation[case])
                for name,w in choice.items():
                    chosen=(1-w[case])*a+w[case]*b
                    decision_rows.append(dict(block=block,local_case=case,budget=budget,rule=name,
                        weight_outgoing=float(w[case]),incoming_evaluation_rate=a,outgoing_evaluation_rate=b,
                        evaluation_reads_per_record=12,attained_rate=float(chosen),
                        sample_oracle_rate=max(a,b),regret=float(max(a,b)-chosen)))
    csv_write(folder/'reads.csv',tables)
    csv_write(folder/'state_rates.csv',states)
    csv_write(folder/'block_summaries.csv',blocks)
    csv_write(folder/'choice_cases.csv',decision_rows)
    rates,rewrite,time_effects,decision_stats,decision_contrasts={},{},{},{},{}
    for bi,budget in enumerate(cfg['budgets']):
        rates[str(budget)]={}
        for vi,variant in enumerate(cfg['variants']):
            values=[float(data_by_block[b]['both_pass'][bi,:,vi].mean()) for b in cfg['blocks']]
            joined=np.concatenate([data_by_block[b]['both_pass'][bi,:,vi] for b in cfg['blocks']])
            entry=summary(values,cfg)
            entry.update(reads=int(joined.size),successes=int(joined.sum()),
                         states_with_any_success=int(joined.any(axis=1).sum()),states_with_all_success=int(joined.all(axis=1).sum()))
            rates[str(budget)][variant]=entry
        paired=np.concatenate([data_by_block[b]['both_pass'][bi,:,:2] for b in cfg['blocks']])
        a,b=paired[:,0],paired[:,1]
        delta=[float((data_by_block[block]['both_pass'][bi,:,1].astype(int)-data_by_block[block]['both_pass'][bi,:,0].astype(int)).mean()) for block in cfg['blocks']]
        rewrite[str(budget)]=summary(delta,cfg)
        rewrite[str(budget)].update(paired_reads=int(a.size),outgoing_only=int((b&~a).sum()),incoming_only=int((a&~b).sum()),
            both_pass=int((a&b).sum()),both_fail=int((~a&~b).sum()),
            positive_blocks=sum(d>0 for d in delta),negative_blocks=sum(d<0 for d in delta),tied_blocks=sum(d==0 for d in delta))
        decision_stats[str(budget)]={}
        for rule in CHOICES:
            group=[r for r in decision_rows if r['budget']==budget and r['rule']==rule]
            attained=[float(np.mean([r['attained_rate'] for r in group if r['block']==b])) for b in cfg['blocks']]
            regrets=[float(np.mean([r['regret'] for r in group if r['block']==b])) for b in cfg['blocks']]
            decision_stats[str(budget)][rule]=dict(yield_summary=summary(attained,cfg),regret_summary=summary(regrets,cfg),
                state_count=len(group),outgoing_choices=sum(r['weight_outgoing']==1 for r in group),
                incoming_choices=sum(r['weight_outgoing']==0 for r in group),ties=sum(r['weight_outgoing']==.5 for r in group))
        decision_contrasts[str(budget)]={}
        signed=decision_stats[str(budget)]['signed_transfer']['yield_summary']['by_block']
        for rule in ('always_incoming','always_outgoing','unsigned_access','direct_read_probe'):
            base=decision_stats[str(budget)][rule]['yield_summary']['by_block']
            decision_contrasts[str(budget)][rule]=summary([signed[str(b)]-base[str(b)] for b in cfg['blocks']],cfg)
    primary_index=cfg['budgets'].index(cfg['primary_budget'])
    for bi,budget in enumerate(cfg['budgets']):
        if bi==primary_index:
            continue
        time_effects[str(budget)]={}
        for vi,variant in enumerate(cfg['variants'][:2]):
            delta=[float((data_by_block[b]['both_pass'][bi,:,vi].astype(int)-data_by_block[b]['both_pass'][primary_index,:,vi].astype(int)).mean()) for b in cfg['blocks']]
            time_effects[str(budget)][variant]=summary(delta,cfg)
    result=dict(status='DEVELOPMENT_ANALYSIS_COMPLETE',enrolled_cases=64,blocks=8,read_trials=len(tables),
        state_rates=len(states),choice_rows=len(decision_rows),native_updates_per_fresh_body=max(cfg['budgets']),
        rate_summaries=rates,rewrite_effects=rewrite,time_effects_relative_to_native=time_effects,
        choices=decision_stats,signed_choice_minus_rivals=decision_contrasts,
        conditional_precision='16 independent fresh streams per case; Wilson intervals reflect Monte Carlo uncertainty only.',
        inference='Equal weight to eight blocks; block bootstrap intervals are descriptive for this exposed selected panel.',
        interpretation='Fixed-injury fresh-read ability and complete O rewrite intervention, not long-horizon recovery or autonomous repair.',
        fitted_models=0)
    write(folder/'analysis.json',result)
    return result


def render(folder,cfg):
    a=read(folder/'analysis.json')
    assert read(folder/'VERIFICATION.json')['status']=='PASS'
    primary=a['rewrite_effects'][str(cfg['primary_budget'])]
    lines=['# Fixed-injury rereading of previously failing bodies','',
        '**Completed development experiment.** All 64 previously observed generation-14 failures were retained. '
        'Incoming and O-rewritten packets were read under the same original injury mask, fresh resets/noise and reader. '
        'No further writing occurred during a read. The source states and old terminal outcomes were already exposed.','',
        f"At the primary 2,048-update budget, the equal-block outgoing-minus-incoming success difference is **{100*primary['mean']:+.2f} percentage points**. "
        f"The descriptive eight-block bootstrap interval is [{100*primary['descriptive_block_bootstrap_95'][0]:.2f}, {100*primary['descriptive_block_bootstrap_95'][1]:.2f}] points. "
        f"Blocks: {primary['positive_blocks']} positive, {primary['tied_blocks']} tied, {primary['negative_blocks']} negative.",'',
        '## Fixed-injury native reads','',
        'Rates below give equal weight to blocks. Pooled counts have 1,024 reads per record option; related cases are not independent blocks. '
        'A case with any successes in 16 reads has demonstrated a successful reread in this finite sample, not a precisely known capacity.','',
        '| Total updates | Incoming rate | Outgoing rate | Erased rate | Incoming successes | Outgoing successes |',
        '|---|---:|---:|---:|---:|---:|']
    for budget in cfg['budgets']:
        r=a['rate_summaries'][str(budget)]
        lines.append(f"| {budget} | {100*r['incoming']['mean']:.2f}% | {100*r['outgoing']['mean']:.2f}% | {100*r['erased']['mean']:.2f}% | {r['incoming']['successes']}/1024 | {r['outgoing']['successes']}/1024 |")
    lines+=['',f"At 2,048 updates, outgoing alone passes {primary['outgoing_only']} paired reads, incoming alone {primary['incoming_only']}; "
            f"both pass {primary['both_pass']} and both fail {primary['both_fail']}.",'',
        'Initial settling stays at 1,024 updates. The three endpoints have 512, 1,024 and 3,072 amplification updates. '
        'They are prefixes of shared trajectories, not independent samples. Each score averages the last 32 outputs and requires both cues to exceed margin 0.25.','',
        '| Block | Cases | Outgoing minus incoming at 2,048 (pp) |','|---|---:|---:|']
    for b,n in zip(cfg['blocks'],cfg['cases_per_block']):
        lines.append(f"| {b} | {n} | {100*primary['by_block'][str(b)]:+.2f} |")
    lines+=['','## Fixed choices evaluated on fresh draws','',
        'Replicates 0–3 choose the direct-read baseline; replicates 4–15 evaluate every rule. '
        'Signed/unsigned diagnostics use no native probe outcomes. Ties receive half of each option. '
        'The diagnostic and direct-read choices have different measurement costs. These results do not constitute a budget-matched repair trial.','',
        '| Rule | 1,536-update yield | 2,048-update yield | 4,096-update yield | 2,048-update sample-oracle regret |',
        '|---|---:|---:|---:|---:|']
    for rule in CHOICES:
        values=[a['choices'][str(b)][rule]['yield_summary']['mean'] for b in cfg['budgets']]
        regret=a['choices']['2048'][rule]['regret_summary']['mean']
        lines.append('| '+rule+' | '+' | '.join(f'{100*v:.2f}%' for v in values)+f' | {100*regret:.2f} pp |')
    lines+=['','The sample oracle selects the record with the better observed evaluation mean for each case. '
        'It is optimistic and unavailable prospectively; regret is not regret against a known true optimum. '
        'All block yields, signed-minus-rival contrasts, paired outcomes and Monte Carlo intervals are retained in the CSV/JSON outputs.','',
        '## Scientific scope','',
        'Incoming reread success shows usable content under fresh draws despite the selected original failure. '
        'An outgoing advantage identifies the effect of this complete rewrite on fixed-injury fresh reading; '
        'it does not isolate signed transfer as its cause. A difference between time budgets locates a read-time constraint '
        'under this one damage contract. It does not establish a general damage/resource boundary.','',
        'Failure of the signed choice to improve on simple constant or unsigned choices narrows the lead even if rewriting helps. '
        'A successful signed choice remains a development result on exposed states, requiring an outcome-blind evaluation '
        'on genuinely unexposed contexts for confirmation. No model or time budget was selected after these outcomes.','',
        '## Verification','',
        'Every selected incoming native generation-14 read was reproduced byte for byte using its original stream. '
        'All scientific endpoints were independently rescored from their raw output windows. Erased outputs are cue-identical and never pass. '
        'A separate flattened-grid implementation reproduced the first enrolled case in every block at evaluation replicate 4, '
        'for all three record options and all three endpoints. Source/input hashes, all tables, choices and block summaries passed. '
        'This is a separate implementation within the theory lane, not an external replication.','',
        '![Fresh-read outcomes and paired rewrite effects](fixed_injury.png)','',
        'See `analysis.json`, `reads.csv`, `state_rates.csv`, `choice_cases.csv`, `block_summaries.csv`, '
        '`VERIFICATION.json`, the eight raw `reads_*.npz` files, and the frozen protocol/configuration under `inputs/`. '
        'No automatic successor experiment is launched.','']
    with (folder/'REPORT.md').open('x') as f:
        f.write('\n'.join(lines))
