"""Streaming all-record endpoints and the frozen repair-call efficiency test."""
import csv
import numpy as np
from common import arrays,read,write

METRICS=('uninterrupted','terminal','first_pass','later_loss','ever_recovered','terminal_after_failure')
RESOURCE_KEYS=('repair_calls','added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds')
MECHANISM_KEYS=('available_edges','fallback_edges','returning_edges','returning_fallback_edges')


def bootstrap_indices(cfg):
    rng=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    groups=[]
    for h in range(4):
        ids=np.array([i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h])
        assert len(ids)>=2
        groups.append(ids[rng.integers(len(ids),size=(cfg['bootstrap_replicates'],len(ids)))])
    return np.concatenate(groups,axis=1)


def summarize(values,cfg,indices,divisor=1):
    x=np.asarray(values,float); assert x.shape==(len(cfg['blocks']),)
    resampled=x[indices].sum(axis=1)/(len(x)*divisor)
    return dict(mean=float(x.sum()/(len(x)*divisor)),by_block=dict(zip(map(str,cfg['blocks']),map(float,x/divisor))),
        one_sided_95_lower=float(np.quantile(resampled,.05)),
        one_sided_95_upper=float(np.quantile(resampled,.95)),
        two_sided_95=np.quantile(resampled,[.025,.975]).tolist(),
        positive_blocks=int((x>0).sum()),tied_blocks=int((x==0).sum()),negative_blocks=int((x<0).sum()))


def primary_test(block_counts,cfg,indices):
    counts=np.asarray(block_counts,int)
    assert counts.shape==(len(cfg['blocks']),3)
    result={}
    for name,coefs in cfg['primary_integer_coefficients'].items():
        values=counts@np.array(coefs)
        result[name]=summarize(values,cfg,indices,16*cfg['primary_divisors'][name])
    passed=all(s['one_sided_95_lower']>0 for s in result.values())
    contradicted=any(s['two_sided_95'][1]<0 for s in result.values())
    result['criterion_passed']=bool(passed)
    result['verdict']='SUPPORTED' if passed else ('CONTRADICTED' if contradicted else 'UNRESOLVED')
    mean=counts.mean(axis=0)/16; gain=mean[2]-mean[0]
    result['retained_benefit_fraction'] = float((mean[1]-mean[0])/gain) if gain>0 else None
    result['benefit_per_additional_call_ratio']=float(17*(mean[1]-mean[0])/(5*gain)) if gain>0 else None
    return result


def endpoints(good):
    return dict(uninterrupted=good.all(axis=0),terminal=good[-1],first_pass=good[0],
        later_loss=good[0]&~good[1:].all(axis=0),
        ever_recovered=(good[1:]&~good[:-1]).any(axis=0),
        terminal_after_failure=good[-1]&~good[:-1].all(axis=0))


def analyze(folder,cfg):
    names=cfg['variants']; n=len(cfg['blocks']); ep=[]; curves=[]; opposite=[]; noise=[]
    resources={name:{key:0. for key in RESOURCE_KEYS} for name in names}
    mechanisms={name:{key:0 for key in MECHANISM_KEYS} for name in names}
    renewal_cpu=0.
    with (folder/'reads.csv').open('x',newline='') as f,(folder/'resources.csv').open('x',newline='') as rf,(folder/'block_summaries.csv').open('x',newline='') as bf:
        rw=csv.DictWriter(f,fieldnames=['block','generation','variant','case','intended','opposite','min_margin','opposite_margin','uninterrupted_so_far']);rw.writeheader()
        sw=csv.DictWriter(rf,fieldnames=['block','generation','variant','case','repair_call','missing_edges','added_edges','added_abs_weight','magnitude','repair_cpu_seconds','audit_cpu_seconds']);sw.writeheader()
        bw=csv.DictWriter(bf,fieldnames=['block','history','variant',*METRICS]);bw.writeheader()
        for b in cfg['blocks']:
            d=arrays(folder/f'continuation_{b:06d}.npz'); e=endpoints(d['both_pass']);ep.append(e)
            curves.append(d['both_pass'].mean(axis=2)); opposite.append(d['opposite_pass'].mean(axis=2))
            noise.append(d['noise_moments'].sum(axis=0)); renewal_cpu+=float(d['renewal_cpu_seconds'].sum())
            for vi,name in enumerate(names):
                bw.writerow(dict(block=b,history=cfg['history_by_block'][str(b)],variant=name,**{k:int(e[k][vi].sum()) for k in METRICS}))
                resources[name]['repair_calls']+=int(d['applied'][:,vi].sum())
                for key in RESOURCE_KEYS[1:]:resources[name][key]+=float(d[key][:,vi].sum())
                for key in MECHANISM_KEYS:mechanisms[name][key]+=int(d[key][:,vi].sum())
            prefix=np.logical_and.accumulate(d['both_pass'],axis=0)
            for gi,g in enumerate(cfg['generations']):
                for vi,name in enumerate(names):
                    for case in range(16):
                        keys=dict(block=b,generation=g,variant=name,case=case)
                        rw.writerow(dict(**keys,intended=int(d['both_pass'][gi,vi,case]),opposite=int(d['opposite_pass'][gi,vi,case]),
                            min_margin=float(d['min_margin'][gi,vi,case]),opposite_margin=float(d['opposite_margin'][gi,vi,case]),uninterrupted_so_far=int(prefix[gi,vi,case])))
                        sw.writerow(dict(**keys,repair_call=int(d['applied'][gi,vi,case]),**{key:float(d[key][gi,vi,case]) for key in ['missing_edges','added_edges','added_abs_weight','magnitude','repair_cpu_seconds','audit_cpu_seconds']}))
    indices=bootstrap_indices(cfg)
    counts={k:np.stack([e[k].sum(axis=1) for e in ep]) for k in METRICS}
    rates={name:{k:summarize(counts[k][:,vi]/16,cfg,indices) for k in METRICS} for vi,name in enumerate(names)}
    totals={name:{k:int(counts[k][:,vi].sum()) for k in METRICS} for vi,name in enumerate(names)}
    primary=primary_test(counts['uninterrupted'],cfg,indices)
    contrasts={label:{k:summarize((counts[k][:,left]-counts[k][:,right])/16,cfg,indices) for k in ('uninterrupted','terminal')}
        for label,left,right in [('six_minus_one',1,0),('eighteen_minus_six',2,1),('eighteen_minus_one',2,0)]}
    paired={}
    for label,left,right in [('six_minus_one',1,0),('eighteen_minus_six',2,1),('eighteen_minus_one',2,0)]:
        x=np.concatenate([e['uninterrupted'][left] for e in ep]);y=np.concatenate([e['uninterrupted'][right] for e in ep])
        paired[label]=dict(left_only=int((x&~y).sum()),right_only=int((y&~x).sum()),both=int((x&y).sum()),neither=int((~x&~y).sum()))
    assert np.array_equal(counts['first_pass'][:,0],counts['first_pass'][:,1]) and np.array_equal(counts['first_pass'][:,0],counts['first_pass'][:,2])
    eligible=counts['first_pass'][:,0]; den=eligible[indices].sum(axis=1); maintenance={}
    for vi,name in enumerate(names):
        numerator=counts['uninterrupted'][:,vi]; boot_n=numerator[indices].sum(axis=1)
        maintenance[name]=dict(successes=int(numerator.sum()),eligible=int(eligible.sum()),
            rate=float(numerator.sum()/eligible.sum()) if eligible.sum() else None,
            two_sided_95=np.quantile(boot_n[den>0]/den[den>0],[.025,.975]).tolist() if np.any(den>0) else None,
            empty_bootstrap_resamples=int((den==0).sum()))
    histories={}
    for h,label in enumerate(cfg['histories']):
        selected=[i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h]
        histories[label]={name:{k:float(counts[k][selected,vi].mean()/16) for k in ('uninterrupted','terminal')} for vi,name in enumerate(names)}
    result=dict(status='PROSPECTIVE_EFFICIENCY_ANALYZED',records=cfg['cohort_size'],blocks=n,primary=primary,
        counts=totals,rates=rates,contrasts=contrasts,paired_counts=paired,maintenance_among_common_first_pass=maintenance,
        common_first_pass_records=int(eligible.sum()),common_first_fail_records=cfg['cohort_size']-int(eligible.sum()),
        resources=resources,mechanism=mechanisms,noise_moments_total=np.sum(noise,axis=0).tolist(),
        generation_success_rates=np.mean(curves,axis=0).tolist(),generation_opposite_rates=np.mean(opposite,axis=0).tolist(),
        history_summaries=histories,renewal_cpu_seconds=renewal_cpu,
        scientific_status='PROSPECTIVE_SEED_HOLDOUT_EXPOSED_SCHEDULE_HYPOTHESIS',
        inference='Paired whole-block percentile bootstrap, stratified by four histories; 20,000 replicates. Approximate finite-sample coverage.',
        interpretation='This tests incremental benefit per repair call in one supplied apparatus over generations 15-32. It does not test equivalence, absolute reliability, minimum budget, total compute efficiency, autonomous apparatus or unique RDT content.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');p=a['primary'];n=cfg['cohort_size']
    lines=['# Prospective repair call efficiency','',f"The frozen criterion is {p['verdict']}. All {n} records in {len(cfg['blocks'])} fresh blocks remain enrolled, including failures at the common first repair. All three schedules continue after failure.",'',
        '| Repairs | Uninterrupted success | Terminal success | Later losses after first success |','|---:|---:|---:|---:|']
    for name,budget in zip(cfg['variants'],cfg['repair_budgets']):
        c=a['counts'][name];lines.append(f"| {budget} | {c['uninterrupted']}/{n} ({100*c['uninterrupted']/n:.2f}%) | {c['terminal']}/{n} ({100*c['terminal']/n:.2f}%) | {c['later_loss']} |")
    lines+=['', 'The primary prediction requires both continual repair to improve uninterrupted success over one initial repair, and six repairs to supply more than twice the added benefit per additional repair call of eighteen repairs. Additional calls are five and seventeen. Equivalently, G = p18 - p1 > 0 and D = p6 - (10/17)p18 - (7/17)p1 > 0. Both one-sided 95% lower bounds must be strictly positive. This is a conjunction; terminal recovery cannot rescue it. A negative verdict requires either one-sided 97.5% upper bound below zero, guarding the two possible negative components. Otherwise the verdict is unresolved.', '',
        '| Frozen contrast | Estimate in percentage points | One sided 95% lower bound |','|---|---:|---:|']
    for name in ('continual_benefit','double_call_efficiency'):
        s=p[name];lines.append(f"| {name} | {100*s['mean']:.3f} | {100*s['one_sided_95_lower']:.3f} |")
    lines+=['',f"The observed ratio of added benefit per additional repair call is {p['benefit_per_additional_call_ratio']}; it is undefined when the continual-minus-once benefit is not positive. All history strata, direct schedule contrasts and paired rescue/harm counts are retained in analysis.json.",'',
        '| Repairs | Total calls | Added edge events | Added absolute weight | Repair CPU seconds |','|---:|---:|---:|---:|---:|']
    for name,budget in zip(cfg['variants'],cfg['repair_budgets']):
        r=a['resources'][name];lines.append(f"| {budget} | {int(r['repair_calls'])} | {int(r['added_edges'])} | {r['added_abs_weight']:.3f} | {r['repair_cpu_seconds']:.3f} |")
    lines+=['',f"The fresh cohort contains {a['common_first_pass_records']} common-first-pass records and {a['common_first_fail_records']} common-first-fail records. Conditional maintenance is secondary and retains its own pooled denominator. Inference resamples whole paired blocks within four equally weighted history strata. Bootstrap coverage is approximate, and all secondary intervals are descriptive.",'',
        'The schedules and doubled-efficiency target were chosen after a five-budget development curve on separate exposed blocks. The target gives a concrete resource criterion without declaring an acceptable absolute loss in performance: six calls must preserve more than 10/17 of the added benefit at 5/17 of the additional calls. This is not noninferiority, a minimum budget or proof of an optimal schedule. Call counts do not measure total CPU, added weight or sensing cost.', '',
        'Teaching, the first fourteen renewals, every continuation and every control are newly generated under reserved namespaces. Ongoing cue noise is independent; teaching and reset pairing remain matched. The ordinary sign-graph repair, reader, writer, ports and resources remain supplied. No unique RDT mechanism or autonomous maintenance follows from this comparison.', '',
        'All optimizer results, preparations, captures, injury/noise streams, schedules, quotas, endpoints and tables receive separate checks. Independent flat dynamics cover teaching, one generation-14 case, and all three schedules at cases 0 and 14 at generations 15 and 32 in every block. These are same-lane internal checks, with selected rather than exhaustive continuation dynamics replay. The cohort is fixed; no optional extension, interim scientific verdict or automatic successor is used.']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines)+'\n')
