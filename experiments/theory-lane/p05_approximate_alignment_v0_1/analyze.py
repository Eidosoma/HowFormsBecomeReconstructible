"""Fixed equal-block effects, paired descriptive uncertainty, and native tables."""
import csv
import numpy as np
from common import arrays,read,write

CONTRASTS={
 'mean_alignment_effect':{5:.5,6:.5,3:-.5,4:-.5},
 'same_alignment_effect':{5:1.,3:-1.},
 'opposite_alignment_effect':{6:1.,4:-1.},
 'aligned_minus_completion':{5:.5,6:.5,7:-1.},
 'own_minus_aligned':{2:1.,5:-.5,6:-.5},
 'completion_minus_outgoing':{7:1.,1:-1.},
 'aligned_minus_outgoing':{5:.5,6:.5,1:-1.},
 'own_minus_completion':{2:1.,7:-1.}}


def csv_write(path,rows):
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def summary(values,cfg):
    values=np.asarray(values,float);assert values.shape==(len(cfg['blocks']),)
    random=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    indices=random.integers(len(values),size=(cfg['bootstrap_replicates'],len(values)))
    interval=np.quantile(values[indices].mean(axis=1),[.025,.975])
    return dict(mean=float(values.mean()),by_block={str(b):float(x) for b,x in zip(cfg['blocks'],values)},
        descriptive_block_bootstrap_95=interval.tolist(),positive_blocks=int((values>0).sum()),
        tied_blocks=int((values==0).sum()),negative_blocks=int((values<0).sum()))


def analyze(folder,cfg):
    panel={b:arrays(folder/f'reads_{b:06d}.npz') for b in cfg['blocks']}
    reads=[];states=[];blocks=[];rates={}
    for regime,prefix,reps in (('fresh','',cfg['replicates']),('original','control_',cfg['original_replicates'])):
        rates[regime]={}
        for vi,variant in enumerate(cfg['variants']):
            rates[regime][variant]={}
            for label,field in (('intended','both_pass'),('opposite','opposite_pass')):
                joined=np.concatenate([d[prefix+field][:,vi] for d in panel.values()])
                rates[regime][variant][label]=dict(**summary([d[prefix+field][:,vi].mean() for d in panel.values()],cfg),
                    successes=int(joined.sum()),reads=int(joined.size))
            for block,data in panel.items():
                intended=data[prefix+'both_pass'][:,vi];opposite=data[prefix+'opposite_pass'][:,vi]
                blocks.append(dict(block=block,regime=regime,variant=variant,cases=len(intended),reads=int(intended.size),
                    intended=int(intended.sum()),opposite=int(opposite.sum()),neither=int((~(intended|opposite)).sum())))
                for case in range(len(intended)):
                    context=dict(block=block,case=case,regime=regime,variant=variant,founder=int(data['founders'][case]),recipient=int(data['recipients'][case]),history=int(data['histories'][case]))
                    states.append(dict(**context,reads=len(reps),intended=int(intended[case].sum()),opposite=int(opposite[case].sum())))
                    for ri,rep in enumerate(reps):
                        ports=data[prefix+'mean_ports'][case,vi,ri].ravel()
                        reads.append(dict(**context,replicate=rep,intended=int(intended[case,ri]),opposite=int(opposite[case,ri]),
                            margin=float(data[prefix+'min_margin'][case,vi,ri]),opposite_margin=float(data[prefix+'opposite_margin'][case,vi,ri]),
                            **dict(zip(('plus_a','plus_b','minus_a','minus_b'),map(float,ports)))))
    for name,rows in (('reads',reads),('state_rates',states),('block_summaries',blocks)):csv_write(folder/(name+'.csv'),rows)
    def effects(field):
        return {name:summary([sum(weight*data[field][:,vi].astype(float) for vi,weight in weights.items()).mean() for data in panel.values()],cfg)
                for name,weights in CONTRASTS.items()}
    intended_effects=effects('both_pass')
    pairs={}
    for label,left,right in (('same',5,3),('opposite',6,4)):
        a=np.concatenate([d['both_pass'][:,left] for d in panel.values()]);b=np.concatenate([d['both_pass'][:,right] for d in panel.values()])
        pairs[label]=dict(aligned_only=int((a&~b).sum()),unaligned_only=int((b&~a).sum()),both=int((a&b).sum()),neither=int((~a&~b).sum()),reads=int(a.size))
    result=dict(status='DEVELOPMENT_ANALYSIS_COMPLETE',cases=sum(cfg['cases_per_block']),blocks=len(cfg['blocks']),
        read_contexts=len(reads),rate_summaries=rates,intended_effects=intended_effects,
        opposite_task_alignment_effect=effects('opposite_pass')['mean_alignment_effect'],paired_counts=pairs,
        primary_direction_observed=intended_effects['mean_alignment_effect']['mean']>0,
        changed_backup_pairs=sum(int((d['backup_sign_changes']>0).sum()) for d in panel.values()),
        non_equivalent_pairs=sum(int((~d['hybrid_gauge_equivalent']).sum()) for d in panel.values()),
        fitted_models=0,interpretation='Fixed conventional approximate sign repair on exposed selected failures; not RDT confirmation.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    effect=a['intended_effects']['mean_alignment_effect'];lo,hi=effect['descriptive_block_bootstrap_95']
    judgment=('The primary directional forecast failed.' if effect['mean']<=0 else
              'The primary point estimate is positive, but its descriptive interval includes zero.' if lo<=0 else
              'The primary point estimate and its descriptive interval are positive.')
    lines=['# Approximate sign alignment performance','',
        f"Mean aligned-minus-unaligned intended-task success is {100*effect['mean']:+.2f} percentage points "
        f"(descriptive eight-block bootstrap interval {100*lo:+.2f} to {100*hi:+.2f}). {judgment}",'',
        'The fixed solver uses surviving edges, sixteen starts and at most sixty-four sweeps. The primary estimate averages both donor types within each case and weights the eight blocks equally. Every enrolled case is retained. New noise on exposed states remains development evidence.','',
        '| Record | Intended success | Opposite-task success | Pooled intended successes |',
        '|---|---:|---:|---:|']
    for name in cfg['variants']:
        r=a['rate_summaries']['fresh'][name]
        lines.append(f"| {name} | {100*r['intended']['mean']:.2f}% | {100*r['opposite']['mean']:.2f}% | {r['intended']['successes']}/{r['intended']['reads']} |")
    lines += ['','Percentages are equal-block means; pooled counts can imply a different weighting.','',
        '| Prespecified intended-task contrast | Difference, pp | Descriptive 95% interval, pp | Blocks positive / tied / negative |',
        '|---|---:|---:|---:|']
    for name,e in a['intended_effects'].items():
        low,high=e['descriptive_block_bootstrap_95']
        lines.append(f"| {name} | {100*e['mean']:+.2f} | [{100*low:+.2f}, {100*high:+.2f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    o=a['opposite_task_alignment_effect'];ol,oh=o['descriptive_block_bootstrap_95']
    lines += ['',f"The mean alignment effect on opposite-task success is {100*o['mean']:+.2f} pp [{100*ol:+.2f}, {100*oh:+.2f}]. Mixed and weak outputs pass neither complete mapping.",'',
        'The completion solver infers backup signs from the recipient record alone. Construction still supplies the common support and protected incoming magnitudes, as for the donor hybrids. A donor advantage over this particular completion algorithm would not establish irreducible historical information; a completion advantage would support an ordinary repair account.','',
        'All preparations were checked with a separate optimizer using Prim initialization and flat neighbor arrays. Native dynamics were checked with the separate flat reader for the first case of every block, both injury regimes and all nine records. Original incoming replays and masked-backup controls passed. All raw windows, dual-task scores, CSV tables, block means and bootstrap intervals were checked independently within this lane.','',
        'The exact-alignment infeasibility result and earlier failed forecasts remain unchanged. The current rule is a bounded heuristic, not a global optimizer. These results do not establish autonomous repair, general body-record complementarity, or a distinct RDT law.','',
        'Frozen inputs, prepared optimizer diagnostics, raw reads, paired counts and verification receipts are retained. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
