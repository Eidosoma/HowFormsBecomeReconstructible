"""Declared uninterrupted endpoint, recovery and costs at whole-block resolution."""
import csv
import numpy as np
from common import ROOT,arrays,read,write

METRICS=('uninterrupted','terminal','ever_recovered','terminal_after_failure',
         'mean_cycle_success','initial_success_run','ever_opposite','terminal_opposite',
         'first_pass','first_pass_then_later_failure')


def summary(values,cfg):
    values=np.asarray(values,float);assert values.shape==(16,)
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    selected=[]
    for h in range(4):
        ids=np.array([i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h])
        selected.append(ids[rng.integers(4,size=(cfg['bootstrap_replicates'],4))])
    interval=np.quantile(values[np.concatenate(selected,axis=1)].mean(axis=1),[.025,.975])
    return dict(mean=float(values.mean()),by_block={str(b):float(x) for b,x in zip(cfg['blocks'],values)},
        descriptive_stratified_block_bootstrap_95=interval.tolist(),
        positive_blocks=int((values>0).sum()),tied_blocks=int((values==0).sum()),negative_blocks=int((values<0).sum()))


def endpoints(good,opposite):
    consecutive=np.logical_and.accumulate(good,axis=0)
    return dict(uninterrupted=consecutive[-1],terminal=good[-1],
        ever_recovered=(good[1:]&~good[:-1]).any(axis=0),
        terminal_after_failure=good[-1]&~good[:-1].all(axis=0),
        mean_cycle_success=good.mean(axis=0),initial_success_run=consecutive.sum(axis=0),
        ever_opposite=opposite.any(axis=0),terminal_opposite=opposite[-1],
        first_pass=good[0],first_pass_then_later_failure=good[0]&~good[1:].all(axis=0))


def csv_write(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def mechanism_summary(panel,cfg):
    result={}
    for vi,name in enumerate(cfg['variants']):
        counts={k:sum(int(d[k][:,vi].sum()) for d in panel.values())
                for k in ('available_edges','fallback_edges','returning_edges','returning_fallback_edges')}
        result[name]=dict(**counts,
            fallback_fraction=counts['fallback_edges']/counts['available_edges'] if counts['available_edges'] else None,
            returning_fallback_fraction=counts['returning_fallback_edges']/counts['returning_edges'] if counts['returning_edges'] else None)
    return result


def noise_summary(panel,cfg):
    sums=np.sum([d['noise_moments'].sum(axis=0) for d in panel.values()],axis=0)
    result={}
    for ni,name in enumerate(cfg['noise_regimes']):
        p,m,pp,mm,pm,n=sums[ni];mp=p/n;mn=m/n;vp=pp/n-mp*mp;vn=mm/n-mn*mn
        result[name]=dict(draws=int(n),mean_plus=float(mp),mean_minus=float(mn),
            variance_plus=float(vp),variance_minus=float(vn),
            correlation=float((pm/n-mp*mn)/np.sqrt(vp*vn)),
            target_correlation=cfg['correlations'][ni])
    return result


def analyze(folder,cfg):
    panel={b:arrays(folder/f'continuation_{b:06d}.npz') for b in cfg['blocks']}
    ep={b:endpoints(d['both_pass'],d['opposite_pass']) for b,d in panel.items()}
    rows=[];resource_rows=[];block_rows=[]
    for b,d in panel.items():
        for vi,name in enumerate(cfg['variants']):
            block_rows.append(dict(block=b,history=cfg['history_by_block'][str(b)],variant=name,
                **{k:float(ep[b][k][vi].mean()) for k in METRICS}))
        for gi,generation in enumerate(cfg['generations']):
            for vi,name in enumerate(cfg['variants']):
                for case in range(16):
                    keys=dict(block=b,generation=generation,variant=name,case=case)
                    rows.append(dict(**keys,intended=int(d['both_pass'][gi,vi,case]),
                        opposite=int(d['opposite_pass'][gi,vi,case]),
                        min_margin=float(d['min_margin'][gi,vi,case]),
                        opposite_margin=float(d['opposite_margin'][gi,vi,case]),
                        uninterrupted_so_far=int(d['both_pass'][:gi+1,vi,case].all())))
                    resource_rows.append(dict(**keys,repair_call=int(d['applied'][gi,vi,case]),
                        missing_edges=int(d['missing_edges'][gi,vi,case]),added_edges=int(d['added_edges'][gi,vi,case]),
                        added_abs_weight=float(d['added_abs_weight'][gi,vi,case]),
                        imputed_magnitude=float(d['magnitude'][gi,vi,case]),
                        repair_cpu_seconds=float(d['repair_cpu_seconds'][gi,vi,case]),
                        audit_cpu_seconds=float(d['audit_cpu_seconds'][gi,vi,case]),
                        record_bytes=4096))
    csv_write(folder/'reads.csv',rows);csv_write(folder/'resources.csv',resource_rows)
    csv_write(folder/'block_summaries.csv',block_rows)
    rates={name:{metric:summary([ep[b][metric][vi].mean() for b in cfg['blocks']],cfg)
                 for metric in METRICS} for vi,name in enumerate(cfg['variants'])}
    contrasts={}
    for label,coefficients in cfg['contrasts'].items():
        contrasts[label]={metric:summary([sum(coef*ep[b][metric][vi].astype(float) for vi,coef in enumerate(coefficients)).mean() for b in cfg['blocks']],cfg)
                          for metric in ('uninterrupted','terminal')}
    paired={}
    for label,(left,right) in cfg['comparison_pairs'].items():
        paired[label]={}
        for metric in ('uninterrupted','terminal'):
            x=np.concatenate([ep[b][metric][left] for b in cfg['blocks']])
            y=np.concatenate([ep[b][metric][right] for b in cfg['blocks']])
            paired[label][metric]=dict(left_only=int((x&~y).sum()),right_only=int((y&~x).sum()),
                both=int((x&y).sum()),neither=int((~x&~y).sum()),lineages=256,
                left=cfg['variants'][left],right=cfg['variants'][right])
    curves={}
    for vi,name in enumerate(cfg['variants']):
        curves[name]=[dict(generation=g,
            success=float(np.mean([d['both_pass'][gi,vi].mean() for d in panel.values()])),
            uninterrupted=float(np.mean([d['both_pass'][:gi+1,vi].all(axis=0).mean() for d in panel.values()])),
            opposite=float(np.mean([d['opposite_pass'][gi,vi].mean() for d in panel.values()])))
            for gi,g in enumerate(cfg['generations'])]
    history={name:{v:{metric:float(np.mean([ep[b][metric][vi].mean() for b in cfg['blocks']
                        if cfg['history_by_block'][str(b)]==hi]))
                        for metric in ('uninterrupted','terminal')} for vi,v in enumerate(cfg['variants'])}
             for hi,name in enumerate(cfg['histories'])}
    resources={}
    for vi,name in enumerate(cfg['variants']):
        fields={k:float(sum(d[k][:,vi].sum() for d in panel.values()))
                for k in ('added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds')}
        calls=sum(int(d['applied'][:,vi].sum()) for d in panel.values())
        resources[name]=dict(repair_calls=calls,**fields,
            added_edges_per_lineage=fields['added_edges']/256,
            record_bytes_per_boundary=4096,read_updates_per_lineage=18*2048,
            optimizer_starts_per_call=16,maximum_sweeps_per_call=64,
            execution_origin='current_run' if vi<3 else 'reused_previous_run')
    first_counts=np.array([ep[b]['first_pass'][0].sum() for b in cfg['blocks']])
    maintenance={name:conditional([ep[b]['uninterrupted'][vi].sum() for b in cfg['blocks']],first_counts,cfg)
                 for vi,name in enumerate(cfg['variants'])}
    rates_by_budget=[rates[name]['uninterrupted']['mean'] for name in cfg['variants']]
    result=dict(status='REPAIR_FREQUENCY_DEVELOPMENT_ANALYZED',blocks=16,records=256,
        read_contexts=len(rows),simulated_read_contexts=13824,reused_control_contexts=9216,
        new_continuation_contexts=13056,first_step_replay_contexts=768,rates=rates,contrasts=contrasts,paired_counts=paired,
        curves=curves,history_summaries=history,resources=resources,maintenance_among_common_first_pass=maintenance,
        common_first_pass_records=int(first_counts.sum()),common_first_fail_records=int(256-first_counts.sum()),
        population_curve_nondecreasing=bool(np.all(np.diff(rates_by_budget)>=0)),
        mechanism=mechanism_summary(panel,cfg),noise_diagnostics=noise_summary(panel,cfg),
        renewal_cpu_seconds=float(sum(d['renewal_cpu_seconds'].sum() for d in panel.values())),
        fitted_parameters=0,confirmatory_claim=False,
        interpretation='Exposed cohort, three newly generated schedules and two exact reused controls. Development curve; no minimum effective budget, equivalence, population law or unique RDT claim.')
    write(folder/'analysis.json',result);return result


def conditional(successes,eligible,cfg):
    successes=np.asarray(successes,int);eligible=np.asarray(eligible,int)
    assert np.all(successes<=eligible) and eligible.sum()>0
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']));ids=[]
    for h in range(4):
        pool=np.array([i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h])
        ids.append(pool[rng.integers(4,size=(cfg['bootstrap_replicates'],4))])
    selection=np.concatenate(ids,axis=1);den=eligible[selection].sum(axis=1)
    assert (den>0).all()
    interval=np.quantile(successes[selection].sum(axis=1)/den,[.025,.975])
    return dict(successes=int(successes.sum()),eligible=int(eligible.sum()),rate=float(successes.sum()/eligible.sum()),
        descriptive_stratified_block_bootstrap_95=interval.tolist())


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    audit=read(folder/'causal_audit/COMPLETE.json')
    lines=['# Repair frequency and continued reconstruction','',
        'The fixed 1-, 3-, 6-, 9- and 18-call schedules were evaluated on the same 256 exposed records and disturbance streams. The 1-, 3- and 6-call arms are new; the completed 9- and 18-call controls are copied and checked byte for byte. This is development evidence for selecting a future quantitative test, not a confirmation of a minimum effective budget.','',
        '| Calls per lineage | Repair generations | Uninterrupted success | Terminal success | Subsequent losses after first success |',
        '|---:|---|---:|---:|---:|']
    for vi,name in enumerate(cfg['variants']):
        r=a['rates'][name];n=round(r['uninterrupted']['mean']*256);t=round(r['terminal']['mean']*256)
        lost=round(r['first_pass_then_later_failure']['mean']*256)
        lines.append(f"| {cfg['repair_budgets'][vi]} | {', '.join(map(str,cfg['repair_generations'][vi]))} | {n}/256 ({100*n/256:.2f}%) | {t}/256 ({100*t/256:.2f}%) | {lost} |")
    lines+=['',f"All arms share the same first repair and byte-identical first reconstruction: {a['common_first_pass_records']} pass and {a['common_first_fail_records']} fail. Every record remains in the principal denominator and every branch continues after failure. The exposed eighteen-call arm already preserves every common-first-pass lineage, imposing the same known upper bound on uninterrupted success for all schedules in this cohort.",'',
        '| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |',
        '|---|---:|---:|---:|']
    for name,c in a['contrasts'].items():
        e=c['uninterrupted'];l,h=e['descriptive_stratified_block_bootstrap_95']
        lines.append(f"| {name} | {e['mean']*100:+.2f} | [{l*100:+.2f}, {h*100:+.2f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    lines+=['','| Calls | Uninterrupted among common-first-pass lineages | Descriptive 95% interval |',
        '|---:|---:|---:|']
    for vi,name in enumerate(cfg['variants']):
        q=a['maintenance_among_common_first_pass'][name];l,h=q['descriptive_stratified_block_bootstrap_95']
        lines.append(f"| {cfg['repair_budgets'][vi]} | {q['successes']}/{q['eligible']} ({q['rate']*100:.2f}%) | [{l*100:.2f}, {h*100:.2f}]% |")
    lines+=['',
        'The conditional maintenance summaries pool successes and eligible counts within each block bootstrap resample. They do not redefine enrollment or average unequal block ratios. All intervals are descriptive and preserve four history strata with 20,000 paired block resamples. No practical-effect margin, equivalence test or post-hoc pass threshold is applied. A nonmonotone curve is retained without smoothing; observed population monotonicity is '+str(a['population_curve_nondecreasing'])+'.','',
        '| Calls | Total calls | Added edge events | Added absolute weight | Repair CPU seconds | Timing origin |',
        '|---:|---:|---:|---:|---:|---|']
    for vi,name in enumerate(cfg['variants']):
        r=a['resources'][name]
        lines.append(f"| {cfg['repair_budgets'][vi]} | {r['repair_calls']} | {int(r['added_edges'])} | {r['added_abs_weight']:.6f} | {r['repair_cpu_seconds']:.6f} | {r['execution_origin']} |")
    c=audit['counts']
    lines+=['',f"The separate causal audit covers all ten first-later-failure policy events in the earlier warning/periodic/random experiment, deduplicated to seven incoming states. Under each saved current injury and forcing realization, current repair rescues {c['rescue_by_current_repair']} state(s), harms {c['harm_by_current_repair']}, and both choices fail for {c['both_fail']}. Every factual replay and both independent intervention calculations agree byte for byte.",'',
        'These selected-state counterfactuals estimate the effect of this one current-boundary intervention under realized forcing. Both-fail does not establish general irreparability or rule out earlier repair. They do not show the population effect of the warning policy or preserve its original nine-call budget. The warning forecast remains failed.','',
        'The main curve makes 2,560 new optimizer calls and 13,824 reconstruction contexts, including 768 exposed first-step replays and 13,056 new subsequent contexts. The combined evidence includes 9,216 copied control contexts and 6,912 previously executed control repairs. Timing origins are retained; copied costs are not charged as new compute. Every read uses 2,048 native updates per cue pair; each packet allocates 4,096 bytes. Counts of calls do not match added weights or actual intervention CPU.','',
        'All schedules start at generation 15. The one-call arm then stops; other schedules are regularly spaced over the specified eighteen-generation horizon. End-of-horizon phase and call count both belong to this exact schedule contract. This does not identify the best possible timing, a global minimum budget, indefinite persistence or a threshold across arbitrary injuries and apparatuses. Teaching and reset randomness remain matched; ongoing cue noise is independent. Reader, writer, ports, optimizer and resources remain supplied.','',
        'Every new optimizer result is checked separately; all five branches have independent preparation, capture, injury, noise, score, schedule, quota, resource and analysis checks. Flat dynamics cover the three new branches for cases 0 and 14 at generations 15 and 32 in every block. These are same-lane internal audits. No fresh-cohort confirmation or automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
