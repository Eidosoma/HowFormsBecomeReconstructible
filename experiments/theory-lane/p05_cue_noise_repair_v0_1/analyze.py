"""Declared uninterrupted endpoint, recovery and costs at whole-block resolution."""
import csv
import numpy as np
from common import arrays,read,write

METRICS=('uninterrupted','terminal','ever_recovered','terminal_after_failure',
         'mean_cycle_success','initial_success_run','ever_opposite','terminal_opposite')


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
        ever_opposite=opposite.any(axis=0),terminal_opposite=opposite[-1])


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
    for ni,noise in enumerate(cfg['noise_regimes']):
        paired[noise]={}
        for metric in ('uninterrupted','terminal'):
            x=np.concatenate([ep[b][metric][2*ni+1] for b in cfg['blocks']])
            y=np.concatenate([ep[b][metric][2*ni] for b in cfg['blocks']])
            paired[noise][metric]=dict(repeated_only=int((x&~y).sum()),baseline_only=int((y&~x).sum()),
                both=int((x&y).sum()),neither=int((~x&~y).sum()),lineages=256)
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
            optimizer_starts_per_call=16,maximum_sweeps_per_call=64)
    primary=contrasts[cfg['primary_contrast']]['uninterrupted']
    result=dict(status='CUE_NOISE_REPAIR_ANALYZED',blocks=16,records=256,
        read_contexts=len(rows),rates=rates,contrasts=contrasts,paired_counts=paired,
        curves=curves,history_summaries=history,resources=resources,
        mechanism=mechanism_summary(panel,cfg),noise_diagnostics=noise_summary(panel,cfg),
        renewal_cpu_seconds=float(sum(d['renewal_cpu_seconds'].sum() for d in panel.values())),
        primary_direction_observed=primary['mean']>0,fitted_parameters=0,
        interpretation='Exposed cohort and exact replay of matched controls; only mismatched continuation outcomes are new. No external replication or unique RDT confirmation.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    p=a['contrasts'][cfg['primary_contrast']]['uninterrupted'];lo,hi=p['descriptive_stratified_block_bootstrap_95']
    judgment=('The primary directional forecast failed.' if p['mean']<=0 else
              'The positive estimate remains unresolved because its descriptive interval includes zero.' if lo<=0 else
              'The primary estimate and its descriptive interval are positive.')
    lines=['# Repeated repair under cue noise mismatch','',
        f"Under independent cue noise, repeated repair minus baseline uninterrupted success is {p['mean']*100:+.2f} percentage points, with descriptive 95% stratified block-bootstrap interval [{lo*100:+.2f}, {hi*100:+.2f}]. {judgment}",'',
        'All 256 starting records were retained for generations 15 to 32. The primary endpoint requires every subsequent reconstruction to pass both cues. Teaching and resets remain matched. Only the correlation of ongoing noise between the two cue episodes changes; marginal variance is fixed. Injury and reset draws are shared across all arms, and noise is shared across the two repair policies within each regime.','',
        '| Cue noise | Baseline uninterrupted | Repeated repair uninterrupted | Baseline generation 32 | Repeated repair generation 32 |',
        '|---|---:|---:|---:|---:|']
    for n in cfg['noise_regimes']:
        x=a['rates'][n+'_baseline'];y=a['rates'][n+'_repeated']
        values=[x['uninterrupted']['mean'],y['uninterrupted']['mean'],x['terminal']['mean'],y['terminal']['mean']]
        lines.append('| '+n+' | '+' | '.join(f'{v*100:.2f}%' for v in values)+' |')
    lines+=['','| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |',
            '|---|---:|---:|---:|']
    for name,c in a['contrasts'].items():
        e=c['uninterrupted'];l,h=e['descriptive_stratified_block_bootstrap_95']
        lines.append(f"| {name} | {e['mean']*100:+.2f} | [{l*100:+.2f}, {h*100:+.2f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    paired=a['paired_counts']['noise_0']['uninterrupted']
    lines+=['',f"Independent-noise paired uninterrupted outcomes: {paired['repeated_only']} repair-only successes, {paired['baseline_only']} baseline-only successes, {paired['both']} both, and {paired['neither']} neither.",'',
        'A shrinking repair advantage must be interpreted alongside absolute rates and each policy’s change from matched noise. Baseline improvement does not by itself show repair fragility. Descriptive contrasts do not establish equivalence or noninferiority. Secondary matched, slight-mismatch or terminal outcomes cannot rescue a failed primary forecast.','',
        '| Arm | Available fallback edges fraction | Returning fallback edges fraction | Repair calls | Added edge events |',
        '|---|---:|---:|---:|---:|']
    for name in cfg['variants']:
        d=a['mechanism'][name];r=a['resources'][name]
        ff='NA' if d['fallback_fraction'] is None else f"{d['fallback_fraction']*100:.2f}%"
        rf='NA' if d['returning_fallback_fraction'] is None else f"{d['returning_fallback_fraction']*100:.2f}%"
        lines.append(f"| {name} | {ff} | {rf} | {r['repair_calls']} | {int(r['added_edges'])} |")
    lines+=['','Fallback counts describe exact-zero contrast in the original writer; they do not identify a causal share of repair benefit. Returning edges are currently available edges incident to a cell absent in the previous reconstruction. The initial prior injury is retained from generation 14.','',
        '| Noise regime | Measured correlation | Plus variance | Minus variance |',
        '|---|---:|---:|---:|']
    for name,d in a['noise_diagnostics'].items():
        lines.append(f"| {name} | {d['correlation']:.6f} | {d['variance_plus']:.6f} | {d['variance_minus']:.6f} |")
    lines+=['',
        'Noise diagnostics refer to standard-normal forcing before multiplication by .02. Shared founders and repair-policy copies are counted once per original noise family; Gaussian draw counts are not the statistical inference units.',
        '',
        'The cohort and all matched-control trajectories were exposed before design. Both matched arms replayed the preceding experiment byte for byte through all 18 generations. Only the four mismatched arms contribute new continuation outcomes, generated after protocol freeze. This is a mechanism follow-up within one simulator, not a new-cohort validation or external replication.',
        '',
        'All optimizer results, repair constructions, body captures, damage masks, noise moments, saved-window scores, historical matched controls and analysis summaries were checked internally. Separate flat dynamics checks cover all six arms for case 0 at generations 15 and 32 in every block. Blocks are the inference units; intervals are descriptive paired bootstraps stratified across the four starting histories.',
        '',
        'Repair uses only its incoming record and the fixed solver options. Every branch writes its own successor. All records occupy 4096 bytes. Added edges, magnitudes, solver diagnostics and intervention CPU time are retained separately from audit costs. The apparatus, input ports, algorithm and resources remain supplied; no outcome uniquely confirms RDT or establishes autonomous maintenance.',
        '',
        'Generation curves, recovery, opposite-task expression, history summaries and resource details are retained in analysis.json and the raw evidence. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))


