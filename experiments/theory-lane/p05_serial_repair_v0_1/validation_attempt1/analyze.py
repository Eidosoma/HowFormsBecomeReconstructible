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
    for label,left,right in [('repeated_minus_baseline',2,0),('one_time_minus_baseline',1,0),
                             ('repeated_minus_one_time',2,1),('repeated_minus_shuffled',2,3)]:
        contrasts[label]={metric:summary([(ep[b][metric][left].astype(float)-ep[b][metric][right]).mean()
                                          for b in cfg['blocks']],cfg)
                          for metric in ('uninterrupted','terminal')}
    paired={}
    for metric in ('uninterrupted','terminal'):
        x=np.concatenate([ep[b][metric][2] for b in cfg['blocks']])
        y=np.concatenate([ep[b][metric][0] for b in cfg['blocks']])
        paired[metric]=dict(repeated_only=int((x&~y).sum()),baseline_only=int((y&~x).sum()),
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
    primary=contrasts['repeated_minus_baseline']['uninterrupted']
    result=dict(status='EXPOSED_COHORT_CONTINUATION_ANALYZED',blocks=16,records=256,
        read_contexts=len(rows),rates=rates,contrasts=contrasts,paired_counts=paired,
        curves=curves,history_summaries=history,resources=resources,
        renewal_cpu_seconds=float(sum(d['renewal_cpu_seconds'].sum() for d in panel.values())),
        primary_direction_observed=primary['mean']>0,fitted_parameters=0,
        interpretation='Mechanism follow-up on an exposed cohort; future branch outcomes generated after freeze, no external replication or distinctive RDT confirmation.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    p=a['contrasts']['repeated_minus_baseline']['uninterrupted'];lo,hi=p['descriptive_stratified_block_bootstrap_95']
    judgment=('The primary directional forecast failed.' if p['mean']<=0 else
              'The estimate is positive but its descriptive interval includes zero.' if lo<=0 else
              'The estimate and its descriptive interval are positive.')
    lines=['# Repeated repair through generation 32','',
        f"Repeated repair minus baseline uninterrupted success is {p['mean']*100:+.2f} percentage points, with descriptive 95% stratified block-bootstrap interval [{lo*100:+.2f}, {hi*100:+.2f}]. {judgment}",'',
        'All 256 exposed generation-14 records were followed through generations 15 to 32 in four branches. Each branch inherited its own body-written output. No lineage was dropped after failure. The primary endpoint requires all 18 subsequent rebuilding endpoints to pass; it does not require generation 14 to have passed.','',
        '| Schedule | Uninterrupted success | Generation 32 success | Ever recovered | Mean initial successful rebuilds |',
        '|---|---:|---:|---:|---:|']
    for v in cfg['variants']:
        r=a['rates'][v]
        lines.append(f"| {v} | {r['uninterrupted']['mean']*100:.2f}% | {r['terminal']['mean']*100:.2f}% | {r['ever_recovered']['mean']*100:.2f}% | {r['initial_success_run']['mean']:.2f} |")
    lines+=['','Generation 32 success refers to that reconstruction body, not an additional read of its outgoing record. Recovery means at least one failed endpoint followed by a passing endpoint. Terminal success cannot replace a failed primary forecast.','',
        '| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |',
        '|---|---:|---:|---:|']
    for label,c in a['contrasts'].items():
        e=c['uninterrupted'];l,h=e['descriptive_stratified_block_bootstrap_95']
        lines.append(f"| {label} | {e['mean']*100:+.2f} | [{l*100:+.2f}, {h*100:+.2f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    pc=a['paired_counts']['uninterrupted']
    lines+=['',f"Paired uninterrupted outcomes: {pc['repeated_only']} repeated-only successes, {pc['baseline_only']} baseline-only successes, {pc['both']} both, and {pc['neither']} neither.",'',
        '| Schedule | Repair calls | Added edge events | Repair CPU seconds |',
        '|---|---:|---:|---:|']
    for v,r in a['resources'].items():
        lines.append(f"| {v} | {r['repair_calls']} | {int(r['added_edges'])} | {r['repair_cpu_seconds']:.2f} |")
    lines+=['',
        'Added edge events count additions at each boundary, not unique persistent edges or allocated bytes. Every stored record remains 4096 bytes. Repair computation, independent audit computation, and common reconstruction computation are reported separately; CPU seconds are descriptive machine costs. No matched total compute budget or compression claim is made.',
        '',
        'The shuffled policy preserves support, magnitudes and the multiset of added signs relative to the coherent repair of its own incoming record. Branches diverge after the first reconstruction, so their later edge resources need not match. A difference between repeated and shuffled policies is a total longitudinal policy effect.',
        '',
        'The cohort and earlier outcomes were exposed before design. Future continuation outcomes were generated only after the executable protocol was frozen. Blocks are the inference units, with four per starting-history stratum. Intervals are descriptive; no practical-benefit margin, equivalence or noninferiority claim was specified.',
        '',
        'All repair constructions, all body-written captures, all damage masks, saved-window scores, chain continuity, schedules, tables and summaries were checked within this lane. Separate native dynamics checks cover case 0 in every block at generations 15 and 32. This is internal verification, not external replication.',
        '',
        'The fixed apparatus, algorithm, input ports and edge resources remain supplied, and cue randomness remains matched. A positive result supports finite continuation with conventional repair; it does not uniquely confirm RDT or establish autonomous maintenance. A failed primary narrows the benefit of this frozen policy on this cohort; secondary terminal recovery does not rescue it.',
        '',
        'Generation curves, history summaries, opposite-task outcomes, complete raw states and resource records are retained. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
