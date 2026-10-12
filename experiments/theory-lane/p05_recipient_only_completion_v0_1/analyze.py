"""Fixed equal-block effects, paired descriptive uncertainty, and native tables."""
import csv
import numpy as np
from common import arrays,read,write

CONTRASTS={
 'recipient_minus_outgoing':{6:1.,1:-1.},
 'recipient_minus_shuffled':{6:1.,7:-1.},
 'full_minus_common_completion':{4:1.,2:-1.},
 'own_minus_full_completion':{3:1.,4:-1.},
 'magnitude_removal':{5:1.,4:-1.},
 'support_removal':{6:1.,5:-1.},
 'recipient_minus_full_completion':{6:1.,4:-1.},
 'recipient_minus_full_own':{6:1.,3:-1.},
 'full_completion_minus_outgoing':{4:1.,1:-1.}}


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
    for label,left,right in (('recipient_vs_outgoing',6,1),('recipient_vs_shuffled',6,7)):
        a=np.concatenate([d['both_pass'][:,left] for d in panel.values()]);b=np.concatenate([d['both_pass'][:,right] for d in panel.values()])
        pairs[label]=dict(left_only=int((a&~b).sum()),right_only=int((b&~a).sum()),both=int((a&b).sum()),neither=int((~a&~b).sum()),reads=int(a.size))
    result=dict(status='DEVELOPMENT_ANALYSIS_COMPLETE',cases=sum(cfg['cases_per_block']),blocks=len(cfg['blocks']),
        read_contexts=len(reads),rate_summaries=rates,intended_effects=intended_effects,
        opposite_task_primary_effect=effects('opposite_pass')['recipient_minus_outgoing'],paired_counts=pairs,
        primary_direction_observed=intended_effects['recipient_minus_outgoing']['mean']>0,
        extra_live_edges=sum(int(d['outside_injury_missing_edges'].sum()) for d in panel.values()),
        fitted_models=0,interpretation='Fixed recipient-only sign and magnitude completion on exposed selected failures; not RDT confirmation.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    effect=a['intended_effects']['recipient_minus_outgoing'];lo,hi=effect['descriptive_block_bootstrap_95']
    judgment=('The primary directional forecast failed.' if effect['mean']<=0 else
              'The primary point estimate is positive, but its descriptive interval includes zero.' if lo<=0 else
              'The primary point estimate and its descriptive interval are positive.')
    lines=['# Completion from the surviving record','',
        f"Recipient-only completion minus outgoing intended-task success is {100*effect['mean']:+.2f} percentage points "
        f"(descriptive eight-block bootstrap interval {100*lo:+.2f} to {100*hi:+.2f}). {judgment}",'',
        'The fixed solver uses surviving edges, sixteen starts and at most sixty-four sweeps. Missing edges receive the median observed absolute weight. The primary rule receives no incoming record, donor information, original injury mask or output targets. Estimates weight the eight blocks equally. Every enrolled case is retained. New noise on exposed states remains development evidence.','',
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
    o=a['opposite_task_primary_effect'];ol,oh=o['descriptive_block_bootstrap_95']
    lines += ['',f"The primary effect on opposite-task success is {100*o['mean']:+.2f} pp [{100*ol:+.2f}, {100*oh:+.2f}]. Mixed and weak outputs pass neither complete mapping.",'',
        'Common completion retains the earlier donor-conditioned support and saved magnitudes. Full completion removes donor selection; support_imputed then replaces saved magnitudes; recipient_completion finally replaces historical support with all exactly zero outgoing edges. These contrasts follow one declared path and are not a full factorial decomposition. Full own and full completion have identical unsigned records. Recipient completion and its shuffled control share support, magnitudes and sign counts.','',
        f"Recipient repair adds {a['extra_live_edges']} edges outside the original injury across the panel. Thus only the historical-support repairs must always reproduce O under the original injury; recipient and shuffled repairs must do so when no such extra edges exist. Per-case support counts, imputed magnitudes and added absolute weight are retained in inputs/prepared/resources.csv.",'',
        'A positive primary estimate with an interval crossing zero leaves repair benefit unresolved. Benefit without an advantage over shuffled signs does not isolate inferred placement. A failure rejects this fixed rule on this panel, not all repair without historical records. Similar point estimates do not establish equivalence. The known lattice, input ports, algorithm, reader and additional edge resources remain supplied.','',
        'All 64 preparations were checked with a separate optimizer using Prim initialization and flat neighbor arrays; all nine records were reconstructed independently. Native dynamics were checked with the separate flat reader for the first case of every block, both injury regimes and all nine records. Original incoming replays and applicable masked controls passed. Raw windows, dual-task scores, tables and bootstrap intervals were checked independently within this lane. This is not external replication.','',
        'Earlier failed forecasts remain preserved. The current rule is a bounded heuristic, not a global optimizer. Results do not establish autonomous repair, general body-record complementarity, irreducible historical information or a distinct RDT law.','',
        'Frozen inputs, prepared resource diagnostics, raw reads, paired counts and verification receipts are retained. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
