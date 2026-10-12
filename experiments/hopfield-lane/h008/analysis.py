"""Report fixed-cohort terminal durability and separately labeled diagnostics."""
from pathlib import Path
import json
import numpy as np
from h008 import engine as e
from h008.inference import mean_pairs, future_decision
from h007.io import save

METRICS = ('success', 'uninterrupted', 'own_retained', 'distinct',
           'joint_functional_retention', 'body_success')


def point(value):
    return 'unavailable' if value is None else f'{100*value:.2f}'


def pct(stat):
    value = point(stat['mean'])
    if stat['low'] is not None:
        value += f" [{100*stat['low']:.2f}, {100*stat['high']:.2f}]"
    return value


def analyze(out):
    out = Path(out)
    config = json.loads((out/'config.json').read_text())
    enrollment = json.loads((out/'ENROLLMENT.json').read_text())
    audited = json.loads((out/'audit.json').read_text())['passed']
    summary = dict(experiment='H008', classification=config['classification'], dose=e.DOSE,
                   current=enrollment['decision'], audit_passed=audited, futures_generated=enrollment['allow_futures'],
                   variants=e.VARIANTS, arms=e.ARMS, checkpoints=e.CHECKPOINTS,
                   decision=dict(qualified=False, gates={}), block_rows=[])
    if enrollment['allow_futures']:
        rows, eligibility, pair_metrics = [], [], {name: [] for name in METRICS}
        for seed in config['seeds']:
            eligible = e.load_candidate(out, seed)['eligible']
            forks = {name: [] for name in METRICS}
            for fork in range(e.FORKS):
                with np.load(out/f'future_{seed}_{fork:02d}.npz') as raw:
                    for name in METRICS:
                        forks[name].append(raw[name])
            averages = {name: np.mean(values, axis=0) for name, values in forks.items()}
            row = dict(seed=seed, matched=int(eligible.sum()))
            if eligible.any():
                row['metrics'] = {name: mean_pairs(values, eligible).tolist() for name, values in averages.items()}
            rows.append(row)
            eligibility.append(eligible)
            for name, values in averages.items():
                pair_metrics[name].append(values)
        np.savez_compressed(out/'pair_summary.npz', seeds=config['seeds'], eligible=np.array(eligibility),
                            variants=np.array(e.VARIANTS), arms=np.array(e.ARMS), checkpoints=e.CHECKPOINTS,
                            **{name: np.array(values) for name, values in pair_metrics.items()})
        block = {name: np.array([row['metrics'][name] for row in rows if row['matched']]) for name in METRICS}
        future = block['success'].reshape(-1, len(e.CHECKPOINTS), 2, len(e.ARMS))
        decision, estimate = future_decision(future, enrollment['decision']['passed'], config, audited)
        trajectory = {v: [estimate(future[:, c, i, 0]) for c in range(len(e.CHECKPOINTS))]
                      for i, v in enumerate(e.VARIANTS)}
        summary.update(decision=decision, block_rows=rows,
                       matched_means={name: values.mean(axis=0).tolist() if len(values) else None for name, values in block.items()},
                       renewal_trajectory=trajectory,
                       uninterrupted={v: {a: estimate(block['uninterrupted'].reshape(-1, 2, 7)[:, i, j])
                                          for j, a in enumerate(e.ARMS)} for i, v in enumerate(e.VARIANTS)})
        summary['verdict'] = 'DEVELOPMENT_CANDIDATE' if decision['qualified'] else 'DOES_NOT_QUALIFY'
    else:
        summary['verdict'] = 'PRESENT_GATE_FAILED'
    if config['mode'] == 'benchmark':
        summary['verdict'] = 'ENGINEERING_ONLY'
        summary['decision']['qualified'] = None
    save(out/'summary.json', summary)
    report(out, summary, config)
    plot(out, summary)
    return summary


def report(out, summary, config):
    current = summary['current']
    lines = ['# H008: durability after a coherent hidden-pattern intervention', '',
             config['classification']+'.', '', '**Decision: '+summary['verdict']+'.**', '',
             f"Fixed dose: {e.DOSE} hidden pairs. Fixed H007 membership: {current['matches']} packets across {current['nonempty_blocks']} networks. "
             'The original pre-replacement packets start new lineages; H007 survivors and outgoing packets do not select or initialize them.', '',
             '| Variant | Fresh current success, % [95% interval] |', '|---|---:|']
    for variant in e.VARIANTS:
        lines.append(f"| {variant} | {pct(current['current_success'][variant])} |")
    lines += ['', '| Current difference, swapped minus unchanged | Mean, points | 97.5% equivalence interval, points |', '|---|---:|---:|']
    for name, stat in current['differences'].items():
        lines.append(f"| {name} | {point(stat['mean'])} | [{point(stat['equivalence_low'])}, {point(stat['equivalence_high'])}] |")
    lines += ['', 'Failed current gates: '+(', '.join(k for k, v in current['gates'].items() if not v) or 'none')+'.']
    if not summary['futures_generated']:
        lines += ['', 'No new future was generated because independent current validation failed. '
                  'The fixed cohort was not rematched, no smaller dose was tried and no equivalence bound was widened.']
    else:
        decision = summary['decision']
        primary = decision['primary_contrast']
        lines += ['', '## Prespecified terminal test', '',
                  'Primary: **swapped minus unchanged renewal success after sixteen replacements**. '
                  'The two-sided question was declared before H008 outcomes. Absolute mean difference must reach '
                  'ten percentage points and the adjusted interval must exclude zero.', '',
                  f"Observed difference: **{pct(primary)} percentage points**. Adjusted two-sided interval: "
                  f"**[{point(primary['primary_low'])}, {point(primary['primary_high'])}] points**.", '',
                  '| Arm | Unchanged terminal success, % [95% interval] | Swapped terminal success, % [95% interval] |', '|---|---:|---:|']
        for arm in e.ARMS:
            lines.append('| '+arm+' | '+' | '.join(pct(decision['terminal'][v][arm]) for v in e.VARIANTS)+' |')
        lines += ['', '| Route contrast | Difference, points [95% interval] | Adjusted lower, points |', '|---|---:|---:|']
        for name, stat in decision['route_contrasts'].items():
            lines.append(f"| {name} | {pct(stat)} | {point(stat['directional_lower'])} |")
        lines += ['', 'Each variant must beat foreign, read-off, write-off and damaged copying by at least 15 points '
                  'with positive adjusted lower bounds. The nine-test family uses .05/9 per test: two primary tails '
                  'of .05/18 and one-sided control bounds at .05/9. Other displayed intervals are marginal 95%.', '',
                  'Failed qualification gates: '+(', '.join(k for k, v in decision['gates'].items() if not v) or 'none')+'.', '',
                  '## Retained diagnostics', '',
                  '| Additional replacements | Unchanged renewal function, % | Swapped renewal function, % | Distinct renewal packets, % | Joint functional exact retention, % |',
                  '|---|---:|---:|---:|---:|']
        means = summary['matched_means']
        if means['success'] is not None:
            for c, g in enumerate(e.CHECKPOINTS):
                lines.append(f"| {g} | {point(means['success'][c][0][0])} | {point(means['success'][c][1][0])} | "
                             f"{point(means['distinct'][g][0])} | {point(means['joint_functional_retention'][c][0])} |")
            lines += ['', '| Variant | Terminal exact self-retention, % | Uninterrupted renewal, % [95% interval] |', '|---|---:|---:|']
            for v, variant in enumerate(e.VARIANTS):
                lines.append(f"| {variant} | {point(means['own_retained'][-1][v][0])} | {pct(summary['uninterrupted'][variant]['renewal'])} |")
        lines += ['', 'Record distinctness and retention are separate from function. The joint exact-retention event '
                  'requires both original records to be reproduced and both checkpoint bodies and fresh readers to '
                  'function. Uninterrupted function requires all sixteen bodies and the terminal reader to pass. '
                  'None of these diagnostics, an intermediate horizon or a subgroup can rescue a failed primary.']
    lines += ['', 'All results average eligible packets and eight future branches within each network, then weight '
              'nonempty networks equally. Inference resamples complete network rows. The 24 development bases and '
              'dose feasibility were already exposed; fresh current and future tapes do not make this independent-base '
              'confirmation. Current equivalence is finite and applies to cohort means, not every individual pair.', '',
              'Both packets have identical visible blocks, weight histograms and record norms; shared base weights '
              'remain fixed and effective total norms are retained. Reconstruction uses the original body-only writer '
              'without a teacher or ancestral record. Copy controls retain their lower computational cost.', '',
              'No private data, code, text, citations or trained state entered this study. H004/H005/H006/H007 outcomes '
              'remain unchanged. No manuscript edit, release or later experiment is launched here.', '',
              f"Audit passed: {summary['audit_passed']}. Source networks: {len(config['seeds'])}.", '']
    if config['mode'] == 'benchmark':
        lines += ['Engineering forced all eight full-length branches using excluded seed 12900 to exercise the pipeline. '
                  'It cannot establish population equivalence or a scientific durability verdict.', '']
    (out/'REPORT.md').write_text('\n'.join(lines))


def plot(out, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), layout='constrained')
    differences = summary['current']['differences']
    for y, (name, stat) in enumerate(differences.items()):
        if stat['mean'] is None:
            continue
        axes[0].plot(100*stat['mean'], y, 'o', color='#117a59')
        if stat['equivalence_low'] is not None:
            axes[0].plot([100*stat['equivalence_low'], 100*stat['equivalence_high']], [y, y], color='#117a59')
    for bound in (-1, 1):
        axes[0].axvline(bound, linestyle=':', color='#8c4242')
    axes[0].axvline(0, color='#aaaaaa', linewidth=.7)
    axes[0].set_yticks(range(len(differences)), list(differences))
    axes[0].set(title='Fresh current equivalence', xlabel='Swapped minus unchanged (points)')
    if summary.get('matched_means', {}).get('success') is not None:
        means = summary['matched_means']
        x = [0, *e.CHECKPOINTS]
        for v, (variant, color) in enumerate(zip(e.VARIANTS, ['#777777', '#117a59'])):
            current = summary['current']['current_success'][variant]
            stats = [current, *summary['renewal_trajectory'][variant]]
            axes[1].plot(x, [100*s['mean'] for s in stats], '-o', color=color, label=variant)
            if all(s['low'] is not None for s in stats):
                axes[1].fill_between(x, [100*s['low'] for s in stats], [100*s['high'] for s in stats], color=color, alpha=.15)
            axes[2].plot(range(17), 100*np.array(means['own_retained'])[:, v, 0], color=color, label=variant+' exact input')
        axes[2].plot(range(17), 100*np.array(means['distinct'])[:, 0], '--', color='#364b63', label='pair remains distinct')
        axes[1].set(title='Common future: functional durability', xlabel='Additional replacements', ylabel='Fresh-reader success (%)', ylim=(-3, 103))
        axes[2].set(title='Separate record diagnostics', xlabel='Additional replacements', ylabel='Exact record comparisons (%)', ylim=(-3, 103))
        axes[1].legend(fontsize=8)
        axes[2].legend(fontsize=8)
    else:
        for ax in axes[1:]:
            ax.text(.5, .5, 'Current validation failed\nNo study futures generated', ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
    for ax in axes:
        if ax.axison:
            ax.grid(alpha=.15)
    fig.suptitle(f"H008 · {summary['verdict']} · fixed eight-pair hidden swap", fontsize=12)
    fig.savefig(Path(out)/'overview.png', dpi=160)
    fig.savefig(Path(out)/'overview.pdf')
    plt.close(fig)
