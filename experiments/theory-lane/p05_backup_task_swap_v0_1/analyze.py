"""Fixed dual-task contrasts and a prespecified ordinary transport rival."""
import csv
import math
import numpy as np
from common import arrays,read,write

CONTRASTS={'same_minus_opposite':(4,5),'own_minus_same':(3,4),'own_minus_opposite':(3,5),
    'own_minus_scrambled':(3,6),'same_minus_outgoing':(4,1),'full_own_minus_common':(2,3),
    'full_own_minus_incoming':(2,0),'full_own_minus_outgoing':(2,1)}


def csv_write(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0.,center-half),min(1.,center+half)


def summary(values,cfg):
    x=np.asarray(values,float);assert x.shape==(len(cfg['blocks']),) and np.isfinite(x).all()
    r=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    ix=r.integers(len(x),size=(cfg['bootstrap_replicates'],len(x)))
    lo,hi=np.quantile(x[ix].mean(axis=1),[.025,.975])
    return dict(mean=float(x.mean()),by_block={str(b):float(v) for b,v in zip(cfg['blocks'],x)},
        descriptive_block_bootstrap_95=[float(lo),float(hi)],positive_blocks=int((x>0).sum()),
        tied_blocks=int((x==0).sum()),negative_blocks=int((x<0).sum()))


def pair_summary(data,first,second,field,cfg):
    x=np.concatenate([d[field][:,first] for d in data.values()]);y=np.concatenate([d[field][:,second] for d in data.values()])
    values=[float((d[field][:,first].astype(int)-d[field][:,second].astype(int)).mean()) for d in data.values()]
    return dict(**summary(values,cfg),paired_reads=int(x.size),first_only=int((x&~y).sum()),second_only=int((y&~x).sum()),
        both_pass=int((x&y).sum()),both_fail=int((~x&~y).sum()))


def analyze(folder,cfg):
    data={b:arrays(folder/f'reads_{b:06d}.npz') for b in cfg['blocks']}
    reads=[];states=[];blocks=[];rival_rows=[];rival_blocks=[]
    for block,d in data.items():
        for regime,prefix,reps in [('original','control_',cfg['original_replicates']),('fresh','',cfg['replicates'])]:
            for vi,variant in enumerate(cfg['variants']):
                target=d[prefix+'both_pass'][:,vi];other=d[prefix+'opposite_pass'][:,vi]
                n,r=target.shape;assert r==len(reps)
                blocks.append(dict(block=block,regime=regime,variant=variant,cases=n,reads=n*r,
                    successes=int(target.sum()),opposite_successes=int(other.sum()),neither=int((~(target|other)).sum()),
                    rate=float(target.mean()),opposite_rate=float(other.mean())))
                for case in range(n):
                    context=dict(block=block,local_case=case,history=cfg['histories'][int(d['histories'][case])],founder=int(d['founders'][case]),recipient=int(d['recipients'][case]),regime=regime,variant=variant)
                    lo,hi=wilson(int(target[case].sum()),r);ol,oh=wilson(int(other[case].sum()),r)
                    states.append(dict(**context,successes=int(target[case].sum()),opposite_successes=int(other[case].sum()),reads=r,
                        rate=float(target[case].mean()),opposite_rate=float(other[case].mean()),
                        conditional_MC_lower=lo,conditional_MC_upper=hi,opposite_conditional_MC_lower=ol,opposite_conditional_MC_upper=oh))
                    for ri,rep in enumerate(reps):
                        ports=d[prefix+'mean_ports'][case,vi,ri].ravel()
                        reads.append(dict(**context,replicate=rep,success=int(target[case,ri]),opposite_success=int(other[case,ri]),
                            margin=float(d[prefix+'min_margin'][case,vi,ri]),opposite_margin=float(d[prefix+'opposite_margin'][case,vi,ri]),
                            plus_a=float(ports[0]),plus_b=float(ports[1]),minus_a=float(ports[2]),minus_b=float(ports[3]),
                            signed_transfer=float(d[prefix+'signed_transfer'][case,vi,ri]),unsigned_access=float(d[prefix+'unsigned_access'][case,vi,ri])))
        delta=d['both_pass'][:,4].astype(int)-d['both_pass'][:,5].astype(int)
        qdelta=d['signed_transfer'][:,4]-d['signed_transfer'][:,5]
        rules={'signed_transport':np.sign(qdelta).astype(int),'task_label':np.ones_like(delta),'unsigned_tie':np.zeros_like(delta)}
        for rule,pref in rules.items():
            reward=pref*delta;disc=delta!=0;credit=np.where(pref==0,.5,(pref==delta).astype(float))*disc
            rival_blocks.append(dict(block=block,rule=rule,paired_reads=int(delta.size),discordant_reads=int(disc.sum()),
                predicted_ties=int((pref==0).sum()),reward=float(reward.mean()),discordant_credit=float(credit.sum()),
                discordant_accuracy=float(credit.sum()/disc.sum()) if disc.any() else None))
            for case in range(len(delta)):
                for ri,rep in enumerate(cfg['replicates']):
                    rival_rows.append(dict(block=block,local_case=case,replicate=rep,rule=rule,preference=int(pref[case,ri]),
                        signed_transfer_difference=float(qdelta[case,ri]),paired_success_difference=int(delta[case,ri]),reward=int(reward[case,ri]),
                        discordant=int(disc[case,ri]),discordant_credit=float(credit[case,ri])))
    for name,rows in [('reads',reads),('state_rates',states),('block_summaries',blocks),('rival_reads',rival_rows),('rival_blocks',rival_blocks)]:csv_write(folder/(name+'.csv'),rows)
    rates={}
    for regime,prefix in [('original','control_'),('fresh','')]:
        rates[regime]={}
        for vi,variant in enumerate(cfg['variants']):
            entry={}
            for label,field in [('intended','both_pass'),('opposite','opposite_pass')]:
                joined=np.concatenate([d[prefix+field][:,vi] for d in data.values()])
                entry[label]=dict(**summary([float(d[prefix+field][:,vi].mean()) for d in data.values()],cfg),
                    reads=int(joined.size),successes=int(joined.sum()),cases_with_any_success=int(joined.any(axis=1).sum()),cases_with_all_success=int(joined.all(axis=1).sum()))
            rates[regime][variant]=entry
    effects={k:pair_summary(data,x,y,'both_pass',cfg) for k,(x,y) in CONTRASTS.items()}
    replacement=pair_summary(data,5,4,'opposite_pass',cfg)
    rivals={}
    for rule in ('signed_transport','task_label','unsigned_tie'):
        rows=[r for r in rival_blocks if r['rule']==rule];disc=sum(r['discordant_reads'] for r in rows);credit=sum(r['discordant_credit'] for r in rows)
        rivals[rule]=dict(reward=summary([r['reward'] for r in rows],cfg),paired_reads=sum(r['paired_reads'] for r in rows),
            discordant_reads=disc,discordant_credit=credit,pooled_discordant_accuracy=credit/disc if disc else None,
            by_block_discordant_accuracy={str(r['block']):r['discordant_accuracy'] for r in rows},
            by_block_discordant_reads={str(r['block']):r['discordant_reads'] for r in rows},predicted_ties=sum(r['predicted_ties'] for r in rows))
    difference=summary([rivals['signed_transport']['reward']['by_block'][str(b)]-rivals['task_label']['reward']['by_block'][str(b)] for b in cfg['blocks']],cfg)
    totals={k:sum(int(d[k].sum()) for d in data.values()) for k in ('backup_nonzero_count','common_nonzero_count','donor_sign_differences','scramble_sign_changes','same_sign_changes','opposite_sign_changes')}
    result=dict(status='DEVELOPMENT_ANALYSIS_COMPLETE',enrolled_cases=sum(cfg['cases_per_block']),blocks=len(cfg['blocks']),read_trials=len(reads),
        rate_summaries=rates,fresh_intended_effects=effects,opposite_task_replacement=replacement,rivals=rivals,signed_reward_minus_task_label=difference,
        primary_direction_observed=effects['same_minus_opposite']['mean']>0,secondary_replacement_direction_observed=replacement['mean']>0,
        backup_totals=totals,identical_donor_cases=sum(int((d['donor_sign_differences']==0).sum()) for d in data.values()),
        zero_common_cases=sum(int((d['common_nonzero_count']==0).sum()) for d in data.values()),
        interpretation='Exposed selected failures, two taught tasks, fixed within-block donors and common support; development precursor to P05.',
        supplied_resource='Incoming and donor records and a fixed reader are supplied; no total resource equivalence or autonomous repair.',fitted_models=0)
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    primary=a['fresh_intended_effects']['same_minus_opposite'];secondary=a['opposite_task_replacement']
    lines=['# Task content in preserved backup signs','',
        '**Completed development experiment.** All 64 exposed recipient failures were retained. Donors came from the other founder pair at the same recipient index and writer history. Four hybrids share exact backup support and magnitudes; only sign placement differs.','',
        f"Same-task minus opposite-task backup success for the recipient task is **{100*primary['mean']:+.2f} percentage points**. "
        f"The predeclared directional prediction {'has the predicted sign' if a['primary_direction_observed'] else 'fails in this development panel'}. "
        'Uncertainty and block heterogeneity remain part of the result.','',
        'All rates weight the eight blocks equally; pooled successes have different case weights. Each option has 1,024 fresh-injury reads.','',
        '| Record | Intended task | Opposite task | Intended pooled successes | Opposite pooled successes |','|---|---:|---:|---:|---:|']
    for variant in cfg['variants']:
        r=a['rate_summaries']['fresh'][variant];i=r['intended'];o=r['opposite']
        lines.append(f"| {variant} | {100*i['mean']:.2f}% | {100*o['mean']:.2f}% | {i['successes']}/{i['reads']} | {o['successes']}/{o['reads']} |")
    lines+=['','| Intended-task comparison | Difference (pp) | Descriptive 95% interval (pp) | Positive / tied / negative blocks |','|---|---:|---:|---:|']
    for name,r in a['fresh_intended_effects'].items():
        lo,hi=r['descriptive_block_bootstrap_95'];lines.append(f"| {name} | {100*r['mean']:+.2f} | [{100*lo:.2f}, {100*hi:.2f}] | {r['positive_blocks']} / {r['tied_blocks']} / {r['negative_blocks']} |")
    lo,hi=secondary['descriptive_block_bootstrap_95']
    lines+=['',f"The separate replacement contrast, opposite-task success with opposite signs minus same-task signs, is **{100*secondary['mean']:+.2f} points**, "
        f"with descriptive interval [{100*lo:.2f}, {100*hi:.2f}] and {secondary['positive_blocks']} positive, {secondary['tied_blocks']} tied, {secondary['negative_blocks']} negative blocks. "
        'Loss of intended performance alone is not donor-task replacement. Full-donor rows assess nominal donor competence in this recipient context; no cases were removed based on that outcome.','',
        '| Fixed rule | Paired ordinal reward | Discordant accuracy | Discordant reads | Predicted ties |','|---|---:|---:|---:|---:|']
    for name,r in a['rivals'].items():
        acc='undefined' if r['pooled_discordant_accuracy'] is None else f"{100*r['pooled_discordant_accuracy']:.2f}%"
        lines.append(f"| {name} | {r['reward']['mean']:+.6f} | {acc} | {r['discordant_reads']} | {r['predicted_ties']} |")
    diff=a['signed_reward_minus_task_label'];lo,hi=diff['descriptive_block_bootstrap_95']
    lines+=['',f"Signed-network minus task-label ordinal reward is {diff['mean']:+.6f}, descriptive interval [{lo:+.6f}, {hi:+.6f}]. "
        'The signed rule is an ordinary fixed 64-step linear transport calculation, with no fitted parameters. Unsigned transport is identical for the four matched hybrids. Discordant accuracy is pooled and conditional on differing outcomes; primary contrasts and rewards use all paired reads and equal block weights.','',
        '| Block | Intended same minus opposite (pp) | Opposite replacement (pp) | Signed minus label reward |','|---|---:|---:|---:|']
    for b in cfg['blocks']:
        key=str(b);lines.append(f"| {b} | {100*primary['by_block'][key]:+.2f} | {100*secondary['by_block'][key]:+.2f} | {diff['by_block'][key]:+.6f} |")
    totals=a['backup_totals']
    lines+=['',f"The common support retains {totals['common_nonzero_count']} of {totals['backup_nonzero_count']} nonzero backup edges; "
        f"donors disagree on {totals['donor_sign_differences']} signs. All {a['identical_donor_cases']} identical-donor cases and {a['zero_common_cases']} zero-common-support cases remain in the analysis. "
        'The full-own versus common-own contrast measures the intervention caused by restricting support. Matching does not equalize donor sign counts or every structural property.','',
        'Under the original injury, outgoing and all five hybrid trajectories are identical. The erased record expresses neither mapping. Known original reads reproduce byte for byte. '
        'An independent flattened reader checks all ten options for the first case of every block under both injury regimes. Donor selection, record construction, masks, raw windows, dual-task scores, tables and block bootstraps were checked separately. These checks belong to the same research lane.','',
        'Incoming-record and donor access are supplied. This assay addresses task-related sign compatibility in two taught tasks; it does not establish arbitrary inherited messages, complementary content contributed by surviving bodies, apparatus autonomy, or a distinct RDT law. The earlier failed P03 transfer and P04 additive forecasts remain unchanged. New random draws on exposed states remain development evidence.','',
        '![Donor task success and paired block effects](backup_task_swap.png)','',
        'Raw arrays, five CSV tables, analysis.json, VERIFICATION.json and frozen inputs are retained. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
