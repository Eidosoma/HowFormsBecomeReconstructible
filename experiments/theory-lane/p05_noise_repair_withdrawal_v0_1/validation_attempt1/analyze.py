"""Declared uninterrupted endpoint, recovery and costs at whole-block resolution."""
import csv
import numpy as np
from common import arrays,read,write

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
            execution_origin='current_run' if name=='one_time' else 'reused_previous_run')
    primary=contrasts[cfg['primary_contrast']]['uninterrupted']
    result=dict(status='REPAIR_WITHDRAWAL_ANALYZED',blocks=16,records=256,
        read_contexts=len(rows),simulated_read_contexts=4608,reused_control_contexts=9216,new_continuation_contexts=4352,rates=rates,contrasts=contrasts,paired_counts=paired,
        curves=curves,history_summaries=history,resources=resources,
        mechanism=mechanism_summary(panel,cfg),noise_diagnostics=noise_summary(panel,cfg),
        new_arm_renewal_cpu_seconds=float(sum(d['new_arm_renewal_cpu_seconds'].sum() for d in panel.values())),
        primary_direction_observed=primary['mean']>0,fitted_parameters=0,
        interpretation='Exposed cohort and reused independent-noise controls; only one-time repair after generation 15 is new. No external replication or unique RDT confirmation.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    p=a['contrasts'][cfg['primary_contrast']]['uninterrupted'];lo,hi=p['descriptive_stratified_block_bootstrap_95']
    judgment=('The primary directional forecast failed.' if p['mean']<=0 else
        'The positive estimate remains unresolved because its descriptive interval includes zero.' if lo<=0 else
        'The primary estimate and its descriptive interval are positive.')
    lines=['# Withdrawal of repair under independent cue noise','',
        f"Repeated minus one-time repair yields {p['mean']*100:+.2f} percentage points in uninterrupted success, with descriptive 95% stratified block-bootstrap interval [{lo*100:+.2f}, {hi*100:+.2f}]. {judgment}",'',
        'All 256 exposed starting records continue through generations 15–32. Both repair policies apply the identical first repair and have byte-identical first reconstructions. One-time repair then stops; repeated repair continues at every boundary. The no-repair and repeated-repair trajectories are verified controls copied from the completed cue-noise study. Only the one-time arm is simulated here.','',
        '| Policy | First rebuild passes | Uninterrupted passes | Generation 32 passes | Repair calls per lineage |',
        '|---|---:|---:|---:|---:|']
    for name in cfg['variants']:
        r=a['rates'][name]
        values=[f"{round(r[k]['mean']*256)}/256 ({r[k]['mean']*100:.2f}%)" for k in ('first_pass','uninterrupted','terminal')]
        lines.append('| '+name+' | '+' | '.join(values)+f" | {a['resources'][name]['repair_calls']//256} |")
    lines+=['','| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |',
        '|---|---:|---:|---:|']
    for name,c in a['contrasts'].items():
        e=c['uninterrupted'];l,h=e['descriptive_stratified_block_bootstrap_95']
        lines.append(f"| {name} | {e['mean']*100:+.2f} | [{l*100:+.2f}, {h*100:+.2f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    paired=a['paired_counts'][cfg['primary_contrast']]['uninterrupted']
    lost=round(a['rates']['one_time']['first_pass_then_later_failure']['mean']*256)
    lines+=['',f"Paired primary outcomes: {paired['left_only']} repeated-only, {paired['right_only']} one-time-only, {paired['both']} both and {paired['neither']} neither. After passing its first rebuild, {lost} one-time lineage(s) failed at a later rebuild.",'',
        'The exposed repeated arm already preserved every first-pass lineage. Given identical first reconstructions, repeated repair cannot have fewer uninterrupted successes on these fixed trajectories: the uncertain primary quantity is the number of subsequent failures after withdrawal. A zero gap fails the strict positive forecast. This direction is not a general test of repair superiority; any positive result supports a need for recurring correction for the observed losses in this setting. A small or zero difference does not establish equivalence or autonomous maintenance.','',
        'Independent noise is applied to the ongoing positive and negative cue episodes at fixed marginal variance; teaching and resets remain matched. Injury, reset and forcing draws are identical to the completed controls at every generation. All branches pass their own actual body-written successors. No branch is selected or stopped on outcome.','',
        '| Policy | Repair calls | Added edge events | Added absolute weight | Intervention CPU seconds | Timing source |',
        '|---|---:|---:|---:|---:|---|']
    for name,r in a['resources'].items():
        lines.append(f"| {name} | {r['repair_calls']} | {int(r['added_edges'])} | {r['added_abs_weight']:.6f} | {r['repair_cpu_seconds']:.6f} | {r['execution_origin']} |")
    lines+=['',
        'Stored intervention timings for the controls come from their original execution and are not new compute in this run. The current run performs 256 new optimizer calls and 4,608 reconstruction contexts, including 256 exposed first-rebuild replays; 4,352 later contexts are new continuation outcomes. The combined analysis includes 9,216 copied control contexts. All packets allocate 4,096 bytes, and reader work per policy is 18 times 2,048 updates per lineage. Counts of repair calls are not equal-weight or equal-time budgets. Audit CPU is recorded separately.','',
        'The cohort and controls were exposed before design. New withdrawal outcomes were generated after freezing the executable and prediction. Blocks are the inference units: 20,000 paired block-bootstrap replicates preserve the four starting-history strata. Intervals are descriptive. No terminal, recovery or other secondary result can rescue a failed uninterrupted primary; no practical-effect or equivalence margin was declared.','',
        'All new optimizer results are independently checked. Separate construction and writer checks cover the combined evidence, copied controls are checked byte for byte, and all noise moments, damage masks, scores, summaries and CSV rows are checked. Separate flat dynamics cover the new arm at generations 15 and 32 for cases 0 and 14 in every block. These are same-lane internal checks, not external replication. The apparatus, solver, ports and resources remain externally supplied.','',
        'Recovery, opposite-task expression, first-pass losses, generation curves, history summaries, noise/writer diagnostics and resource details are retained in analysis.json and raw evidence. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
