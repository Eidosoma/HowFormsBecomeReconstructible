"""Readable evidence tables; every confidence region is reported, without filtering."""
import csv
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
import json
import numpy as np
import support as s


def run(output):
    results=json.loads((output/'results.json').read_text());audit=json.loads((output/'AUDIT.json').read_text())
    audited={case['id']:case for case in audit['cases']};rows=[];records=[]
    for case in results['cases']:
        region=json.loads((output/(case['region']+'.json')).read_text());records.append((case,region,audited[case['id']]))
        for h,horizon in enumerate(s.PLAN['horizons']):
            for c,category in enumerate(['A','B','N']):
                bounds=region['outer_bounds'];w=region['witnesses'];truth=audited[case['id']]['truth_forecasts'];fit=region['candidate_fit']
                row=dict(id=case['id'],kind=case['kind'],n=region['n'],family=region['family'],horizon=horizon,category=category,
                    lower=None if bounds is None else bounds[h][c][0],upper=None if bounds is None else bounds[h][c][1],
                    feasible_minimum_upper=None if not w['points'] else w['minimum_upper'][h][c],
                    feasible_maximum_lower=None if not w['points'] else w['maximum_lower'][h][c],
                    proven_region_width=None if region['witness_width_lower_bound'] is None else region['witness_width_lower_bound'][h][c],
                    projection_gap=None if region['projection_gaps'] is None else max(region['projection_gaps'][h][c]),
                    point_forecast=fit['forecasts'][h][c] if fit['status']=='CONVERGED' else None,
                    truth=None if truth is None else truth[h][c],truth_in_region=audited[case['id']]['truth_in_region'],
                    feasibility=region['feasibility'],retained_leaves=region['retained_leaves'],
                    native_forecast_status=region['native_forecast_status'],region=case['region'])
                rows.append(row)
    with (output/'forecasts.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    aggregates=dict(case_count=len(records),unique_regions=results['unique_regions'],
        feasibility_counts={status:sum(r['feasibility']==status for _,r,_ in records) for status in ['WITNESS_PROVEN','UNRESOLVED','CERTIFIED_EMPTY']},
        fully_resolved_cases=sum(r['computation_resolved'] for _,r,_ in records),
        truth_membership=dict(inside=sum(a['truth_in_region'] is True for _,_,a in records),
            outside=sum(a['truth_in_region'] is False for _,_,a in records)),
        native_forecast_status=results['native_forecast_status'])
    s.dump(output/'summary.json',aggregates)
    def number(value):return '—' if value is None else f'{value:.4f}'
    def conservative(value,rounding):
        return '—' if value is None else str(Decimal.from_float(value).quantize(Decimal('0.0001'),rounding=rounding))
    lines=['# TT006 continuous full-model uncertainty', '',
        f"Classification: {results['classification']}. All {len(records)} cases are retained; {results['unique_regions']} distinct count/family combinations required computation. Exact rational audit: {audit['status']}.", '',
        'These are model-conditional simultaneous confidence enclosures over the continuous five-parameter domain. Native model forecasts remain **ABSTAIN**: the observation/transition assumptions have not been validated. No new native trajectories were generated.', '',
        'Each synthetic case has a 95% family across its 27 pattern cells. The 16 native tables share a 95% simultaneous family. Both horizons and all response categories are projections of the same parameter set. This is unconditional coverage under the specified iid-path model; selecting narrow results would require a separate guarantee.', '',
        'A witness width is a proved lower bound on the width of this particular confidence region. It is not a confidence interval or a lower bound on every possible statistical method. The projection gap measures unresolved computation between witnessed and outer endpoints. A missing witness means unresolved feasibility, not exclusion. Exact exclusion means no parameter in this restricted model satisfies the cell intervals.', '',
        f"Feasibility counts: {aggregates['feasibility_counts']}. Cases resolved to the .025 endpoint-gap target across all six forecasts: {aggregates['fully_resolved_cases']}/{len(records)}. Known synthetic truths inside/outside their regions: {aggregates['truth_membership']} (single development examples, not a coverage estimate).", '',
        'The conventional structured HMM is identical to the candidate. The output-Markov point comparator is retained only when all source categories are observed. The unrestricted-future reference is [0,1]. These comparisons do not establish predictive superiority.', '',
        '## Horizon 32, ancestral-rule category A', '',
        '| Case | n | Continuous outer bounds | Proved region width ≥ | Remaining endpoint gap ≤ | Point estimate | Known truth | Feasibility |',
        '|---|---:|---|---:|---:|---:|---:|---|']
    for row in rows:
        if row['horizon']!=32 or row['category']!='A':continue
        interval='empty' if row['lower'] is None else f"[{conservative(row['lower'],ROUND_FLOOR)}, {conservative(row['upper'],ROUND_CEILING)}]"
        lines.append(f"| {row['id']} | {row['n']} | {interval} | {conservative(row['proven_region_width'],ROUND_FLOOR)} | {conservative(row['projection_gap'],ROUND_CEILING)} | {number(row['point_forecast'])} | {number(row['truth'])} | {row['feasibility']} |")
    lines += ['', 'All categories at both horizons, unrounded endpoints and search gaps are in [forecasts.csv](forecasts.csv). The 27 confidence-cell brackets, optimizer attempts, unsupported comparators and all parameter boxes are retained under `regions/`. `AUDIT.json` verifies exact tails, partition coverage, excluded boxes, retained forecasts and feasible witnesses.', '',
        'Interpret native tables as conditional calculations for the previously exposed TT003 panel, not independent new population evidence. Synthetic sample-size comparisons draw separate fixed samples; their intervals need not narrow monotonically. Constructed alternating histories deliberately challenge the nonnegative identity-mode restriction.', '',
        '![All horizon-32 ancestral-rule bounds](uncertainty.png)', '']
    with (output/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    height=max(4.,len(records)*.25+2)
    fig,axis=plt.subplots(figsize=(13,height))
    selected=[r for r in rows if r['horizon']==32 and r['category']=='A']
    for i,row in enumerate(selected):
        if row['lower'] is None:axis.text(.5,i,'No compatible parameters',ha='center',va='center',color='#a33');continue
        axis.plot([row['lower'],row['upper']],[i,i],lw=3,color='#afc7db',solid_capstyle='butt')
        if row['feasible_minimum_upper'] is not None:
            axis.plot([row['feasible_minimum_upper'],row['feasible_maximum_lower']],[i,i],lw=6,color='#315f86',solid_capstyle='butt')
        if row['point_forecast'] is not None:axis.plot(row['point_forecast'],i,'o',color='#ba5d17',ms=4)
        if row['truth'] is not None:axis.plot(row['truth'],i,'x',color='black',ms=6)
    axis.set_yticks(range(len(selected)),[r['id'] for r in selected],fontsize=8);axis.set_ylim(len(selected)-.5,-.5)
    axis.set_xlim(-.025,1.025);axis.set_xlabel('Horizon-32 probability of ancestral-rule category A')
    axis.grid(axis='x',alpha=.2)
    axis.set_title('Continuous outer bounds (light); feasible span (dark)\nPoint fit (orange dot); synthetic truth (black cross). Native forecasts remain ABSTAIN.',fontsize=11)
    fig.tight_layout();fig.savefig(output/'uncertainty.png',dpi=150);plt.close(fig)
    # Round-trip the machine-readable presentation against its authoritative rows.
    with (output/'forecasts.csv').open(newline='') as f:loaded=list(csv.DictReader(f))
    if len(loaded)!=len(rows):raise ValueError('Report omitted cases')
    for original,saved in zip(rows,loaded,strict=True):
        for key,value in original.items():
            expected='' if value is None else str(value)
            if saved[key]!=expected:raise ValueError('Report field changed: '+key)
    s.dump(output/'REPORT_CHECK.json',dict(status='PASS',rows=len(rows),cases=len(records),scope='Unfiltered CSV round trip and links to independently audited regions.'))
    return aggregates
