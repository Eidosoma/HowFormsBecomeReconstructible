"""Render the complete development result with its applicability limits."""
from pathlib import Path

import numpy as np


def render(output,result,audit):
    output=Path(output);native=result['native'];scenarios=result['scenarios'];selected=result['selected_scenarios']
    names={'absorbing_loss':'Irreversible readiness loss','identity_flip':'Symmetric identity flips'}
    lines=['# Observation variability and rare loss uncertainty','',
        f"Status: {result['status']}. No native trajectory was generated. This is a measurement and uncertainty development study, not a full-model RDT confirmation.",'',
        'The existing eight-packet observations are reused. Their 48 exact binomial intervals form one family with at least 95% simultaneous coverage under the fixed conditional sampling design. They concern particular packets and fresh-recipient draws, not a population of founders or future rewriting. Variance estimates are descriptive and remain unclipped.','',
        '| Starting packet | Fixed A / B / neither | Simultaneous interval for A probability | Duplicate disagreements at 0 / 1 / 2 |',
        '| --- | --- | --- | --- |']
    for case in native['cases']:
        counts='/'.join(map(str,case['category_counts']));lo,hi=case['category_intervals'][0]
        disagreement='/'.join(str(r['category_disagreements']) for r in case['duplicate_pairs'])
        lines.append(f"| {case['id']} | {counts} | [{lo:.4f}, {hi:.4f}] | {disagreement} |")
    negatives=sum(r['negative_between_estimate'] for c in native['cases'] for r in c['duplicate_pairs'])
    lines += ['',f'{negatives} of 24 between-packet variance estimates are negative. These are finite-sample estimates, not negative physical variances. A fixed source packet has zero true between-packet variation at depth zero. See summary.json for every within/between component and duplicate-disagreement interval.','',
        'Two exact packet models have identical single-assay histories and later marginal success probabilities. One produces a fixed packet with noisy fresh-body expression; the other produces randomly readable or unreadable packets with deterministic expression. At expression probability .75, duplicate disagreement after renewal is .375 versus zero. The supplied two-mode HMM matches their single-observation law. Variable assays therefore do not by themselves refute that HMM, but single observations do not identify what its hidden state represents.','',
        '## Long horizon uncertainty inside restricted models','',
        'The following intervals are conditional on an exactly specified submodel. They are not native confidence intervals or a confidence region for all five candidate parameters. Every path has two short renewal observations; the long horizon is 32.','',
        '| Model | Short paths | Interval after no short losses or flips | Original width rule issues |',
        '| --- | ---: | --- | --- |']
    for row in result['zero_loss_intervals']:
        lo,hi=row['interval'];lines.append(f"| {names[row['model']]} | {row['paths']} | [{lo:.6f}, {hi:.6f}] | {row['issue_under_original_width_gate']} |")
    lines += ['', 'For irreversible loss, if s is two-cycle survival then horizon-32 success is s^16. Sixteen successful short paths give a two-sided exact 95% interval of [0.025, 1] for that long probability. Zero observed loss does not establish near-perfect persistence. The identity-flip submodel instead approaches a .5 terminal baseline because recovery to the ancestral identity is possible.','',
        '| Interval procedure | Lowest unconditional coverage in panel |',
        '| --- | ---: |']
    for method in ('exact','wilson'):
        rows=[r for r in scenarios if r['method']==method]
        worst=min(rows,key=lambda r:r['coverage'])
        lines.append(f"| {method} | {worst['coverage']:.6f} ({worst['model']}, n={worst['paths']}, H={worst['horizon']}, q={worst['hazard']}) |")
    regular=[r for r in scenarios if r['method']=='exact' and r['conditional_coverage_if_issued'] is not None]
    worst=min(regular,key=lambda r:(r['conditional_coverage_if_issued'],-r['issuance_probability']))
    adjusted=[r for r in selected if r['conditional_coverage_given_gate'] is not None]
    lowest=min(adjusted,key=lambda r:r['conditional_coverage_given_gate'])
    lines += ['',
        f"Selecting only exact intervals of width at most .10 does not preserve their unconditional guarantee among selected cases. The lowest selected coverage is {worst['conditional_coverage_if_issued']:.6f}, at {worst['model']}, n={worst['paths']}, H={worst['horizon']}, q={worst['hazard']}; issuance probability there is {worst['issuance_probability']:.8g}. The joint probability of issuing and missing is {worst['issued_and_missed_probability']:.8g}. All scenarios, including rare issuance, are retained.",'',
        f"After conditioning the binomial tail inversion on that fixed original selection set, the lowest coverage given selection in the exact panel is {lowest['conditional_coverage_given_gate']:.6f}. Corrected intervals may become wider than .10 or empty. They are retained without another width filter; a second filter would require another selection calculation. This correction is validated only for the two specified finite-binomial models.",'',
        'All panel probabilities are finite sums over possible counts, rather than Monte Carlo estimates. Coverage is evaluated before transforming the parameter, avoiding spurious coverage when tiny identity biases round to .5. Empty parameter sets remain unsupported. The exact method is Clopper-Pearson; Wilson is a standard approximate comparison. [Method documentation](https://docs.scipy.org/doc/scipy-1.16.1/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html).','',
        '| Desired horizon-32 lower bound | Best-case required short paths | Short renewal cycles |',
        '| ---: | ---: | ---: |']
    for row in result['zero_loss_sample_requirements']:
        lines.append(f"| >{row['target']} | {row['paths']} | {row['short_cycles']} |")
    lines += ['',
        'These requirements assume the absorbing-loss model, a fixed sample size, independent paths and no observed short loss. They are not native power estimates, population sample sizes or instructions to run until a favorable bound appears. The .10 width is an illustrative development target, not a frozen RDT confirmation margin.','',
        'The reused unrestricted-process example has identical observations through depth two and opposite horizon-32 outcomes. Short data cannot protect a forecast against unrestricted structural changes. The native full-rewrite forecast status remains ABSTAIN: its observation assumptions and full-model uncertainty have not been validated.','',
        f"The separate calculation audit passed {audit['native_intervals_checked']} native-family intervals, {audit['coverage_scenarios_checked']} probability scenarios, {audit['forecast_transformations_checked']} interval transformations, {audit['interval_tail_or_reference_checks']} endpoint checks and {audit['observation_pattern_probabilities_checked']} observation-pattern probabilities. Code, sources, arrays and software identities are retained.",'',
        '![Conditional observation uncertainty](observation_uncertainty.png)','',
        '![Long horizon calibration](uncertainty_calibration.png)','']
    with (output/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
    plots(output,result)


def plots(output,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cases=result['native']['cases'];y=np.arange(len(cases))
    probability=np.array([c['category_counts'][0]/c['fixed_assays'] for c in cases])
    bounds=np.array([c['category_intervals'][0] for c in cases])
    fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    axes[0].errorbar(probability,y,xerr=np.stack((probability-bounds[:,0],bounds[:,1]-probability)),fmt='o',capsize=3,color='#225b80')
    axes[0].set_xlim(-.03,1.03);axes[0].set_yticks(y,[c['id'] for c in cases]);axes[0].invert_yaxis()
    axes[0].set_xlabel('Fresh-assay ancestral-rule probability');axes[0].set_title('Fixed packet, 64 assays\n95% simultaneous family intervals')
    for depth,color in enumerate(('#3878a8','#d38423','#7a4e9b')):
        value=[c['duplicate_pairs'][depth]['between_packet_estimate'] for c in cases]
        axes[1].plot(value,y+(depth-1)*.18,'o',label=f'Depth {depth}',color=color)
    axes[1].axvline(0,color='#777',linewidth=1);axes[1].set_yticks(y,[c['id'] for c in cases]);axes[1].invert_yaxis()
    axes[1].set_xlabel('Unclipped between-packet variance estimate');axes[1].set_title('Descriptive components from 16 pairs\nNegative estimates reflect sampling variation')
    axes[1].legend(loc='best',fontsize=8)
    for ax in axes:ax.grid(axis='x',alpha=.2)
    fig.suptitle('Excluded technical observations' if result['status']=='EXCLUDED_TECHNICAL' else 'Fresh-body variation with selected packets')
    fig.savefig(output/'observation_uncertainty.png',dpi=160);fig.savefig(output/'observation_uncertainty.pdf');plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for row,model in enumerate(('absorbing_loss','identity_flip')):
        data=[r for r in result['zero_loss_intervals'] if r['model']==model]
        axes[row,0].plot([r['paths'] for r in data],[r['interval'][0] for r in data],'o-',color='#225b80',label='95% exact lower bound')
        axes[row,0].axhline(1,color='#777',linestyle='--',label='Upper bound and point estimate')
        axes[row,0].set_xscale('log',base=2);axes[row,0].set_xticks([16,64,256,1024],['16','64','256','1024']);axes[row,0].set_ylim(0,1.04)
        axes[row,0].set_xlabel('Independent two-renewal paths, all successful');axes[row,0].set_ylabel('Horizon-32 ancestral-rule probability');axes[row,0].legend(fontsize=8)
        ordinary=[r for r in result['scenarios'] if r['model']==model and r['paths']==16 and r['horizon']==32 and r['method']=='exact']
        corrected=[r for r in result['selected_scenarios'] if r['model']==model and r['paths']==16 and r['horizon']==32]
        x=np.arange(len(ordinary));hazards=[str(r['hazard']) for r in ordinary]
        axes[row,1].plot(x,[r['coverage'] for r in ordinary],'o-',label='Ordinary, unconditional',color='#225b80')
        axes[row,1].plot(x,[np.nan if r['conditional_coverage_if_issued'] is None else r['conditional_coverage_if_issued'] for r in ordinary],'s--',label='Ordinary, given width gate',color='#bd6439')
        axes[row,1].plot(x,[np.nan if r['conditional_coverage_given_gate'] is None else r['conditional_coverage_given_gate'] for r in corrected],'^:',label='Adjusted, given original gate',color='#458855')
        axes[row,1].axhline(.95,color='#777',linewidth=1);axes[row,1].set_xticks(x,hazards,rotation=45,ha='right');axes[row,1].set_ylim(-.02,1.04)
        axes[row,1].set_xlabel('Per-renewal loss or flip probability');axes[row,1].set_ylabel('Coverage, n=16 paths');axes[row,1].legend(fontsize=8)
        for ax in axes[row]:ax.set_title('Irreversible readiness loss' if model=='absorbing_loss' else 'Symmetric identity flips');ax.grid(alpha=.2)
    fig.suptitle('Exact submodel calculations: horizon 32\nSelection-adjusted intervals may widen; no second width filter')
    fig.savefig(output/'uncertainty_calibration.png',dpi=160);fig.savefig(output/'uncertainty_calibration.pdf');plt.close(fig)
