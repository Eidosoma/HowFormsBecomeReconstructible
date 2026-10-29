"""Block-level inference; all directions and thresholds fixed before acquisition."""
import math
from scipy.stats import t
from common import BLOCKS, FIELDS, read_json
from design import ALPHA, claims, terms


def interval(values, alpha=ALPHA):
    values=list(values); n=len(values)
    assert n>=2 and all(math.isfinite(v) and -1<=v<=1 for v in values)
    mean=math.fsum(values)/n
    variance=math.fsum((x-mean)**2 for x in values)/(n-1)
    se=math.sqrt(variance/n)
    if se:
        radius=float(t.ppf(1-alpha,n-1))*se
        r95=float(t.ppf(.975,n-1))*se
        method='approximate paired block Student-t'
    else:
        radius=math.sqrt(2*math.log(1/alpha)/n)
        r95=math.sqrt(2*math.log(40)/n)
        method='bounded Hoeffding zero-variance fallback'
    clip=lambda x:max(-1.,min(1.,x))
    return dict(n=n,mean=mean,standard_error=se,lower_one_sided=clip(mean-radius),
        upper_one_sided=clip(mean+radius),alpha=alpha,
        pointwise_two_sided_95=[clip(mean-r95),clip(mean+r95)],method=method,
        hoeffding_lower_sensitivity=clip(mean-math.sqrt(2*math.log(1/alpha)/n)))


def contrasts(records):
    result={}
    for name,(left,right) in terms().items():
        a,b=records[left],records[right]
        assert len(a)==len(b) and all((x['world'],x['message'],x['replicate'])==(y['world'],y['message'],y['replicate']) for x,y in zip(a,b))
        def delta(pairs):
            pairs=list(pairs)
            return {k:math.fsum(x[k]-y[k] for x,y in pairs)/len(pairs) for k in FIELDS}
        result[name]=dict(left=left,right=right,mean=delta(zip(a,b)),
            messages=[delta((x,y) for x,y in zip(a,b) if x['message']==m) for m in range(4)])
    return result


def summary(directory):
    data={i:read_json(directory/f'tissue_{i}/records.json') for i in BLOCKS}
    arms=set(data[BLOCKS[0]])
    assert len(arms)==29 and all(set(rows)==arms for rows in data.values())
    def mean(rows):return {k:math.fsum(r[k] for r in rows)/len(rows) for k in FIELDS}
    arm_summary={}
    for name in sorted(arms):
        rows=[r for i in BLOCKS for r in data[i][name]]
        assert len(rows)==1024
        arm_summary[name]=dict(mean=mean(rows),messages=[mean([r for r in rows if r['message']==m]) for m in range(4)],
            blocks={i:mean(data[i][name]) for i in BLOCKS})
    results={}
    for name,(left,right) in terms().items():
        block_values=[math.fsum(a['accuracy']-b['accuracy'] for a,b in zip(data[i][left],data[i][right]))/16 for i in BLOCKS]
        pairs=[(a,b) for i in BLOCKS for a,b in zip(data[i][left],data[i][right])]
        differences=[a['accuracy']-b['accuracy'] for a,b in pairs]
        item=dict(left=left,right=right,blocks=dict(zip(BLOCKS,block_values)),mean=math.fsum(block_values)/64,
            record_changes=dict(improved=sum(x>0 for x in differences),worsened=sum(x<0 for x in differences),tied=sum(x==0 for x in differences)),
            messages=[math.fsum(a['accuracy']-b['accuracy'] for a,b in pairs if a['message']==m)/256 for m in range(4)])
        if name in claims():
            item['interval']=interval(block_values);item['margin']=claims()[name]['margin']
            item['classification']='PRACTICAL_SUPERIORITY_PASS' if item['interval']['lower_one_sided']>item['margin'] else 'NOT_CONFIRMED'
        results[name]=item
    return dict(primary=results['primary_capture_gain']['classification'],blocks=list(BLOCKS),population_units=64,
        records=1024,draws_per_record=4,arm_summaries=arm_summary,contrasts=results,
        formal_claims=list(claims()),family_alpha=.05,per_claim_alpha=ALPHA,
        no_record_selection=True,secondary_results_cannot_rescue_primary=True,
        finite_horizon='one 1000-step fresh read after 1000-step repair',serial_heredity_test=False)


def report(value):
    lines=['# TT021 prospective early-capture confirmation','',
        'Primary classification: **'+value['primary']+'**. All 64 new blocks and 1,024 records retained.',
        'Inference uses paired block means; four reader draws per record do not increase the 64 population units.','',
        '| Registered claim | Gain | One-sided 99% lower bound | Required margin | Classification |',
        '| --- | ---: | ---: | ---: | --- |']
    for name in claims():
        item=value['contrasts'][name]
        lines.append(f"| {name} | {100*item['mean']:.3f} pp | {100*item['interval']['lower_one_sided']:.3f} pp | {100*item['margin']:.1f} pp | {item['classification']} |")
    lines+=['','The five predeclared directional tests share a .05 error budget through Bonferroni (.01 each).',
        'Student-t coverage is approximate; zero variance uses the retained bounded fallback.',
        'The harm contrast is ordinary minus captured informative-record recognition.','',
        '| Record family | Unchanged | Ordinary | Captured live | Held snapshot | Captured fixed | Matched average |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for packet in ('common','residual'):
        names=['input__'+packet,packet+'__own__live',*['capture__'+packet+'__own__'+mode for mode in ('live','reference_held','fixed','average')]]
        values=[value['arm_summaries'][name]['mean']['accuracy'] for name in names]
        lines.append('| '+packet+' | '+' | '.join(f'{100*x:.3f}%' for x in values)+' |')
    lines+=['','All favorable and adverse per-record changes, message strata and source controls remain in SUMMARY.json.',
        'Held memory is a protected snapshot. Fixed-reading averaging is matched to its body stream and birth observation.',
        'Live feedback can change the body stream. Only the 2,048-byte record crosses to the fresh recipient.',
        'These results concern the supplied simulator and one receiving horizon; no serial or autonomous-repair claim.','']
    return '\n'.join(lines)
