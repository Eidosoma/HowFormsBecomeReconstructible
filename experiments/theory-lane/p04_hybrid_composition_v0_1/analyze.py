"""Fixed hybrid contrasts, prior forecasts and contemporaneous interaction."""
import csv
import math
import numpy as np
from common import arrays,read,write

CONTRASTS={'hybrid_minus_incoming':(3,0),'hybrid_minus_outgoing':(3,1),
    'hybrid_minus_scrambled':(3,4),'rewrite':(1,0),'rewrite_beyond_erasure':(1,2),
    'erasure_only':(2,0),'scrambled_minus_outgoing':(4,1)}
FORECASTS=('additive','incoming_reference','outgoing_reference')


def csv_write(path,rows):
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0.,center-half),min(1.,center+half)


def summary(values,cfg):
    x=np.asarray(values,float);assert x.shape==(len(cfg['blocks']),) and np.isfinite(x).all()
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    ix=rng.integers(len(x),size=(cfg['bootstrap_replicates'],len(x)))
    lo,hi=np.quantile(x[ix].mean(axis=1),[.025,.975])
    return dict(mean=float(x.mean()),by_block={str(b):float(v) for b,v in zip(cfg['blocks'],x)},
        descriptive_block_bootstrap_95=[float(lo),float(hi)],positive_blocks=int((x>0).sum()),
        tied_blocks=int((x==0).sum()),negative_blocks=int((x<0).sum()))


def analyze(folder,cfg):
    forecast=read(folder/'inputs/prepared/forecasts.json')
    data={b:arrays(folder/f'reads_{b:06d}.npz') for b in cfg['blocks']}
    reads,states,blocks,forecast_reads,forecast_blocks=[],[],[],[],[]
    reps=len(cfg['replicates'])
    for block,d in data.items():
        n=len(d['founders']);assert d['both_pass'].shape==(2,n,6,reps)
        for gi,regime in enumerate(cfg['regimes']):
            for vi,variant in enumerate(cfg['variants']):
                outcome=d['both_pass'][gi,:,vi]
                blocks.append(dict(block=block,regime=regime,variant=variant,cases=n,reads=n*reps,
                    successes=int(outcome.sum()),rate=float(outcome.mean())))
                for case in range(n):
                    context=dict(block=block,local_case=case,history=cfg['histories'][int(d['histories'][case])],
                        founder=int(d['founders'][case]),recipient=int(d['recipients'][case]),regime=regime,variant=variant)
                    count=int(outcome[case].sum());lo,hi=wilson(count,reps)
                    states.append(dict(**context,successes=count,reads=reps,rate=count/reps,
                        conditional_MC_wilson_lower=lo,conditional_MC_wilson_upper=hi))
                    for ri,rep in enumerate(cfg['replicates']):
                        ports=d['mean_ports'][gi,case,vi,ri].ravel()
                        reads.append(dict(**context,replicate=rep,success=int(outcome[case,ri]),
                            margin=float(d['min_margin'][gi,case,vi,ri]),plus_a=float(ports[0]),plus_b=float(ports[1]),
                            minus_a=float(ports[2]),minus_b=float(ports[3]),
                            signed_transfer=float(d['signed_transfer'][gi,case,vi,ri]),unsigned_access=float(d['unsigned_access'][gi,case,vi,ri]),
                            overlap_with_original=int((d['masks'][gi,case,ri]&d['original_masks'][case]).sum()),
                            backup_nonzero_count=int(d['backup_nonzero_count'][case]),backup_sign_changes=int(d['backup_sign_changes'][case])))
        actual=d['both_pass'][1,:,3].astype(float)
        for rule in FORECASTS:
            p=forecast['by_block'][str(block)][rule];observed=float(actual.mean())
            forecast_blocks.append(dict(block=block,rule=rule,predicted_rate=p,observed_hybrid_rate=observed,
                error=observed-p,absolute_error=abs(observed-p),squared_rate_error=(observed-p)**2,
                brier=float(((actual-p)**2).mean()),cases=n,reads=n*reps))
            for case in range(n):
                for ri,rep in enumerate(cfg['replicates']):
                    y=int(actual[case,ri])
                    forecast_reads.append(dict(block=block,local_case=case,replicate=rep,rule=rule,
                        predicted_rate=p,hybrid_success=y,brier=(y-p)**2))
    for name,rows in [('reads',reads),('state_rates',states),('block_summaries',blocks),
                      ('forecast_reads',forecast_reads),('forecast_blocks',forecast_blocks)]:
        csv_write(folder/(name+'.csv'),rows)
    rates,effects,interactions={},{},{}
    for gi,regime in enumerate(cfg['regimes']):
        rates[regime]={};effects[regime]={}
        for vi,variant in enumerate(cfg['variants']):
            values=[float(d['both_pass'][gi,:,vi].mean()) for d in data.values()]
            joined=np.concatenate([d['both_pass'][gi,:,vi] for d in data.values()])
            rates[regime][variant]=dict(**summary(values,cfg),reads=int(joined.size),successes=int(joined.sum()),
                cases_with_any_success=int(joined.any(axis=1).sum()),cases_with_all_success=int(joined.all(axis=1).sum()))
        for name,(first,second) in CONTRASTS.items():
            values=[float((d['both_pass'][gi,:,first].astype(int)-d['both_pass'][gi,:,second].astype(int)).mean()) for d in data.values()]
            x=np.concatenate([d['both_pass'][gi,:,first] for d in data.values()]);y=np.concatenate([d['both_pass'][gi,:,second] for d in data.values()])
            effects[regime][name]=dict(**summary(values,cfg),paired_reads=int(x.size),first_only=int((x&~y).sum()),
                second_only=int((y&~x).sum()),both_pass=int((x&y).sum()),both_fail=int((~x&~y).sum()))
        values=[]
        for d in data.values():
            y=d['both_pass'][gi].astype(int)
            values.append(float((y[:,3]-y[:,1]-y[:,0]+y[:,2]).mean()))
        interactions[regime]=summary(values,cfg)
    prediction={}
    for rule in FORECASTS:
        group=[row for row in forecast_blocks if row['rule']==rule]
        prediction[rule]=dict(forecast_equal_block_mean=float(np.mean([row['predicted_rate'] for row in group])),
            error=summary([row['error'] for row in group],cfg),brier=summary([row['brier'] for row in group],cfg),
            mean_absolute_block_error=float(np.mean([row['absolute_error'] for row in group])),
            root_mean_square_block_error=float(np.sqrt(np.mean([row['squared_rate_error'] for row in group]))))
    brier_differences={}
    for rival in FORECASTS[1:]:
        brier_differences[rival]=summary([prediction['additive']['brier']['by_block'][str(b)]-prediction[rival]['brier']['by_block'][str(b)] for b in cfg['blocks']],cfg)
    control_shift=[]
    for b,d in data.items():
        y=d['both_pass'][1].astype(int)
        current=float((y[:,1]+y[:,0]-y[:,2]).mean())
        delta=current-forecast['by_block'][str(b)]['additive'];control_shift.append(delta)
        assert abs(prediction['additive']['error']['by_block'][str(b)]-interactions['fresh']['by_block'][str(b)]-delta)<2e-14
    result=dict(status='DEVELOPMENT_ANALYSIS_COMPLETE',enrolled_cases=sum(cfg['cases_per_block']),blocks=len(cfg['blocks']),
        read_trials=len(reads),rate_summaries=rates,effects=effects,factorial_interaction=interactions,
        frozen_forecast_evaluation=prediction,additive_brier_minus_rivals=brier_differences,
        contemporaneous_additive_control_shift=summary(control_shift,cfg),
        hybrid_beats_both_reference_point_estimates=all(effects['fresh'][k]['mean']>0 for k in ('hybrid_minus_incoming','hybrid_minus_outgoing')),
        correct_backup_beats_scrambled_point_estimate=effects['fresh']['hybrid_minus_scrambled']['mean']>0,
        frozen_forecast_value=forecast['additive_equal_block_mean'],
        backup_nonzero_edges=sum(int(d['backup_nonzero_count'].sum()) for d in data.values()),
        backup_changed_signs=sum(int(d['backup_sign_changes'].sum()) for d in data.values()),
        cases_with_no_sign_change=sum(int((d['backup_sign_changes']==0).sum()) for d in data.values()),
        interpretation='New hybrid interventions on exposed selected states; ordinary additive forecast; eight blocks; no accuracy threshold or equivalence claim.',
        supplied_resource='Incoming record remains accessible during writing; equal output length does not equalize total resources.',fitted_models=0)
    write(folder/'analysis.json',result)
    return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    h=a['rate_summaries']['fresh']['hybrid'];f=a['frozen_forecast_evaluation']['additive'];err=f['error']
    lines=['# Hybrid preservation and rewriting','',
        '**Completed development experiment.** All 64 exposed generation-14 failures were retained. Six fixed records '
        'were read under the original injury and 16 new paired mask/noise draws, each at 2,048 updates. '
        'The hybrid writes surviving edges and retains incoming values at edges unavailable during writing.','',
        f"Fresh-injury hybrid success is **{100*h['mean']:.2f}%**, versus the frozen additive forecast of **{100*a['frozen_forecast_value']:.2f}%**. "
        f"Observed minus forecast is {100*err['mean']:+.2f} percentage points, with descriptive block-bootstrap interval "
        f"[{100*err['descriptive_block_bootstrap_95'][0]:.2f}, {100*err['descriptive_block_bootstrap_95'][1]:.2f}]. "
        'Forecast accuracy is reported continuously; this interval is not an equivalence or acceptance test.','',
        'Rates weight the eight blocks equally; pooled counts use different weights.','',
        '| Injury | Record | Equal-block success | Pooled successes |','|---|---|---:|---:|']
    for regime in cfg['regimes']:
        for variant in cfg['variants']:
            r=a['rate_summaries'][regime][variant]
            lines.append(f"| {regime} | {variant} | {100*r['mean']:.2f}% | {r['successes']}/{r['reads']} |")
    lines+=['','| Fresh-injury comparison | Difference (pp) | Descriptive 95% interval (pp) | Positive / tied / negative blocks |',
        '|---|---:|---:|---:|']
    for name,r in a['effects']['fresh'].items():
        lo,hi=r['descriptive_block_bootstrap_95']
        lines.append(f"| {name} | {100*r['mean']:+.2f} | [{100*lo:.2f}, {100*hi:.2f}] | {r['positive_blocks']} / {r['tied_blocks']} / {r['negative_blocks']} |")
    j=a['factorial_interaction']['fresh'];shift=a['contemporaneous_additive_control_shift']
    lines+=['',f"The fresh four-way interaction H−O−I+D is {100*j['mean']:+.2f} points. "
        f"The new controls' additive reference shifts {100*shift['mean']:+.2f} points relative to the old forecast. "
        'These two terms sum to the observed forecast error. A nonzero interaction alone does not establish a distinct RDT mechanism.','',
        '| Frozen forecast for H | Mean prediction | Brier | Mean absolute block error (pp) | RMS block error (pp) |',
        '|---|---:|---:|---:|---:|']
    for rule,r in a['frozen_forecast_evaluation'].items():
        lines.append(f"| {rule} | {100*r['forecast_equal_block_mean']:.2f}% | {r['brier']['mean']:.6f} | "
            f"{100*r['mean_absolute_block_error']:.2f} | {100*r['root_mean_square_block_error']:.2f} |")
    lines+=['','| Block | Frozen H forecast | Observed H success | H−I (pp) | H−O (pp) | H−scrambled (pp) | Interaction (pp) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    frozen=read(folder/'inputs/prepared/forecasts.json')
    for b in cfg['blocks']:
        key=str(b);p=frozen['by_block'][key]['additive'];observed=h['by_block'][key]
        vals=[a['effects']['fresh'][k]['by_block'][key] for k in ('hybrid_minus_incoming','hybrid_minus_outgoing','hybrid_minus_scrambled')]+[j['by_block'][key]]
        lines.append(f'| {b} | {100*p:.2f}% | {100*observed:.2f}% | '+' | '.join(f'{100*v:+.2f}' for v in vals)+' |')
    lines+=['',f"The fixed sign permutations changed {a['backup_changed_signs']} of {a['backup_nonzero_edges']} backed-up nonzero edge signs; "
        f"{a['cases_with_no_sign_change']} cases had no sign change. Support and magnitudes are identical between H and scrambled H. "
        'Their unsigned-access diagnostics are exactly equal under every tested mask. Any performance difference concerns '
        'this sign placement under fixed magnitudes, not a complete source-specific heredity test.','',
        'Incoming-record access during writing is supplied. No writing occurs during the subsequent reads. '
        'The selected source states and earlier outcomes are exposed; predictions, permutations, masks and code were '
        'frozen before the new native outcomes. New random draws do not establish independent confirmation. '
        'The earlier failed transfer prediction remains unchanged.','',
        'All known original native reads were reproduced byte for byte. Every raw window, score, forecast and summary '
        'was independently checked. A separate flattened reader audited the first case of each block at draw 4 '
        'under both injury regimes for all six records. Independent checks also reconstructed masks, backups, '
        'sign permutations and forecast arithmetic. These are implementations within one research lane.','',
        '![Record success and frozen hybrid forecasts](hybrid_composition.png)','',
        'Raw arrays, five CSV tables, analysis.json, VERIFICATION.json and frozen inputs are retained. '
        'No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
