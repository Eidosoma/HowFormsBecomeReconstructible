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
                        diagnostic_cpu_seconds=float(d['diagnostic_cpu_seconds'][gi,vi,case]),
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
                for k in ('added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds','diagnostic_cpu_seconds')}
        calls=sum(int(d['applied'][:,vi].sum()) for d in panel.values())
        resources[name]=dict(repair_calls=calls,**fields,
            added_edges_per_lineage=fields['added_edges']/256,
            record_bytes_per_boundary=4096,read_updates_per_lineage=18*2048,
            optimizer_starts_per_call=16,maximum_sweeps_per_call=64,
            execution_origin='current_run')
    primary=contrasts[cfg['primary_contrast']]['uninterrupted']
    result=dict(status='BUDGETED_REPAIR_ANALYZED',blocks=16,records=256,
        read_contexts=len(rows),simulated_read_contexts=18432,reused_control_contexts=0,new_continuation_contexts=18432,rates=rates,contrasts=contrasts,paired_counts=paired,
        curves=curves,history_summaries=history,resources=resources,
        mechanism=mechanism_summary(panel,cfg),noise_diagnostics=noise_summary(panel,cfg),
        renewal_cpu_seconds=float(sum(d['renewal_cpu_seconds'].sum() for d in panel.values())),
        warning_policy=dict(diagnostic_calls=4352,linear_transfer_updates_per_call=64,
            reason_counts={str(i):sum(int((d['warning_reason']==i).sum()) for d in panel.values()) for i in (1,2,3,4)},
            repair_calls_by_generation={str(g):sum(int(d['applied'][gi,0].sum()) for d in panel.values()) for gi,g in enumerate(cfg['generations'])},
            apparatus_numeric_bytes=(19+len(read(ROOT/'development/MODEL.json')['calibration_sorted_scores']))*8),
        primary_direction_observed=primary['mean']>0,fitted_parameters=7,
        interpretation='Frozen policy on new seeded lineages after exposed development; same programme, not external replication. Equal optimizer calls, separately accounted diagnostic CPU and edge additions. No unique RDT confirmation.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    p=a['contrasts'][cfg['primary_contrast']]['uninterrupted'];lo,hi=p['descriptive_stratified_block_bootstrap_95']
    judgment=('The primary directional forecast failed.' if p['mean']<=0 else
        'The positive estimate remains unresolved because its descriptive interval includes zero.' if lo<=0 else
        'The primary estimate and its descriptive interval are positive.')
    lines=['# Repair timing under a fixed call budget','',
        f"Warning minus evenly spaced repair yields {p['mean']*100:+.2f} percentage points in uninterrupted success, with descriptive 95% stratified block-bootstrap interval [{lo*100:+.2f}, {hi*100:+.2f}]. {judgment}",'',
        'All 256 fresh records were enrolled after matched teaching and 14 native renewals, without filtering on success. Each branch continues through generations 15–32 and writes its own successor. The warning, periodic and random policies each make exactly nine calls; the repeated reference makes eighteen. All share the first repair, injury, reset and noise, and have byte-identical first reconstructions.','',
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
    lines+=['',f"Paired primary outcomes: {paired['left_only']} warning-only, {paired['right_only']} periodic-only, {paired['both']} both and {paired['neither']} neither.",'',
        'The warning uses six measurements of the incoming record: missing and weak edges, weak nodes, node-strength variation, unsigned signal reach and signed output separation. A fixed ridge logistic model was trained on previously exposed, unrepaired steps from baseline and one-time-repair histories. Whole-block cross-validation, including all related trajectories within each held-out block, preceded model freezing. There were 33 failure observations from 20 distinct lineages in nine of sixteen blocks. The frozen calibration-rank rule spends remaining calls according to current risk and remaining time, forcing expenditure only when needed to meet the exact quota. No current body, injury, task identity or future outcome is available to the scheduler.','',
        '| Policy | Calls | Added edge events | Added absolute weight | Repair CPU seconds | Warning CPU seconds |',
        '|---|---:|---:|---:|---:|---:|']
    for name,r in a['resources'].items():
        lines.append(f"| {name} | {r['repair_calls']} | {int(r['added_edges'])} | {r['added_abs_weight']:.6f} | {r['repair_cpu_seconds']:.6f} | {r['diagnostic_cpu_seconds']:.6f} |")
    lines+=['',
        'The budget matches optimizer calls; it does not match actual CPU, added weights or edge events. Every call uses the same sixteen-start, sixty-four-sweep maximum solver. Warning timing includes feature extraction, model scoring, rank calculation and tie RNG; batched timings are divided equally among sixteen cases. It is measured at every generation after the first, including after quota exhaustion. Audit CPU is separate. The fixed model, scaling and calibration require '+str(a['warning_policy']['apparatus_numeric_bytes'])+' numeric bytes in shared external apparatus, in addition to fixed reader, ports, solver and RNG machinery. Each transmitted record remains 4,096 bytes. Offline development CPU is retained in development/COMPLETE.json. Allocated bytes are not an information-compression estimate.','',
        'The trial contains 18,432 new policy reconstruction contexts, plus 3,584 acquisition-history renewals and teaching. Every fresh first-generation outcome was produced after the protocol, model, full analysis and code snapshot were frozen. This is a prospective seed holdout for an exposed hypothesis in the same programme, not external preregistration or independent replication. The limited cohort is a feasibility pilot, not powered evidence for a small practical improvement. Twenty thousand paired block-bootstrap resamples preserve the four history strata; intervals remain descriptive. No practical-effect or equivalence margin was declared.','',
        'A nonpositive primary rejects the strict directional forecast; a positive estimate whose interval includes zero remains unresolved. Secondary terminal success, recovery, history strata or comparisons cannot rescue a failed uninterrupted primary. A benefit over periodic scheduling but not random scheduling gives weaker evidence for useful warning information. A close match to eighteen-call repair is not proof of equivalence. Risk prediction by itself does not show which failures repair can prevent.','',
        'All repair results have independent optimizer checks. Separate implementations verify all policy decisions and quotas, graph features, captures, injuries, noise moments, scores, endpoint summaries, bootstrap intervals and CSV rows. Acquisition is checked with separate flat dynamics; four-policy flat reconstruction checks cover two cases at generations 15 and 32 in each block. These are same-lane internal audits. Independent ongoing cue noise is used; teaching and birth resets remain matched. Reader/writer machinery and correction remain externally supplied. Ordinary graph correction remains a strong explanation, and this experiment does not test apparatus autonomy or a uniquely RDT mechanism.','',
        'Generation curves, all raw trajectories, intervention decisions, warnings and resource counts are saved. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
