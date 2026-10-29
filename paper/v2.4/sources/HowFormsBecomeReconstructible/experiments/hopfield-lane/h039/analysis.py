"""Unchanged per-network endpoints plus fixed fresh-cohort confirmation decisions."""
import json
import numpy as np
from h007.io import save
from h035 import design as base
from h038.analysis import summarize, csv_write, means, effects
from h039 import design as d
from h039.inference import infer


def analyze(out, summaries, classification):
    summaries = sorted(summaries, key=lambda s: s['block'])
    confirmation = classification == d.CLASSIFICATION
    config = json.loads((out/'config.json').read_text())
    if confirmation:
        assert [s['block'] for s in summaries] == config['settings']['confirmation_blocks']
    inference = infer(summaries, confirmation)
    names = ('outcome_rows', 'effect_rows', 'gap_rows', 'body_rows', 'path_rows')
    flat = {k: [r for s in summaries for r in s[k]] for k in names}
    for k, rows in flat.items():
        csv_write(out/(k+'.csv'), rows)
    outcomes = means(flat['outcome_rows'], ('generation', 'load', 'arm', 'reconstruction_gain', 'assay_gain'),
        ('trained_success', 'rule_a', 'rule_b', 'joint', 'donor_rule_a', 'donor_rule_b', 'donor_joint'), 'readouts')
    contrasts = effects(flat['effect_rows'], ('generation', 'load', 'arm', 'contrast'))
    gaps = effects(flat['gap_rows'], ('generation', 'load', 'reconstruction_gain', 'assay_gain', 'contrast'))
    bodies = means(flat['body_rows'], ('generation', 'load', 'arm', 'reconstruction_gain'),
        ('trained_success', 'donor_success', 'successful_so_far'), 'related_paths')
    paths = means(flat['path_rows'], ('load', 'arm', 'reconstruction_gain'),
        ('all_boundaries_success', 'donor_all_boundaries_success', 'mean_boundary_success', 'final_body_success'), 'related_paths')
    summary = dict(classification=classification, independent_source_networks=len(summaries),
        outcomes=outcomes, effects=contrasts, gaps=gaps, bodies=bodies, paths=paths,
        inference=inference, row_counts={k: len(v) for k, v in flat.items()}, primary_probe_count=8,
        audit_probe_excluded=True, confirmation=confirmation, writer_changes=False, predictor_fits=0,
        prior_verdicts_changed=False, private_material=False, manuscript_edit=False)
    save(out/'summary.json', summary)
    save(out/'inference.json', inference)
    lookup = {(r['generation'], r['load'], r['arm'], r['reconstruction_gain'], r['assay_gain']): r for r in outcomes}
    lines = ['# H039 — Fresh confirmation of guidance during inheritance', '',
        f'{classification}; {len(summaries)} independent base networks; eight primary probes per checkpoint.',
        'Network averages are the statistical units. The separate baseline audit assay is excluded.', '']
    if confirmation:
        decisions = inference['decisions']
        lines += [f"Primary: **{decisions['primary']}**.",
            f"Original final reader: **{decisions['original_reader']}**.",
            f"Uninterrupted inheritance: **{decisions['uninterrupted']}**.", '']
    else:
        lines += ['Engineering replay only; no population decision.', '']
    lines += ['| Generation | Record | 4 / 4 | 4 / 8 | 8 / 4 | 8 / 8 |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for g in base.CHECKPOINTS:
        for arm in ('renewal', 'protected_copy', 'damaged_copy'):
            values = [lookup[(g, 'both', arm, b, r)]['joint'] for b in (4, 8) for r in (4, 8)]
            lines.append(f'| {g} | {arm} | '+' | '.join(f'{v:.4%}' for v in values)+' |')
    lines += ['', 'Settings are reconstruction gain / assay gain.', '',
        '| Declared endpoint or contrast | Mean | Marginal 95% interval | Adjusted directional lower |',
        '| --- | ---: | --- | ---: |']
    for name, row in inference['estimates'].items():
        interval = 'engineering only' if row['low'] is None else f"[{row['low']:.4%}, {row['high']:.4%}]"
        lower = '—' if row['adjusted_lower'] is None else f"{row['adjusted_lower']:.4%}"
        lines.append(f"| {name} | {row['mean']:.4%} | {interval} | {lower} |")
    if confirmation:
        decisions = inference['decisions']
        failures = [k for k, v in decisions['controls'].items() if not v]
        failures += [name+'/'+gate for name, tests in decisions['contrast_gates'].items() for gate, ok in tests.items() if not ok]
        if not decisions['uninterrupted_absolute_gate']:
            failures.append('uninterrupted_success_at_least_half')
        lines += ['', 'Failed numerical gates: '+(', '.join(failures) or 'none')+'.',
            'Secondary claims require the complete primary decision. All numerical contrasts remain visible even when ineligible.']
    lines += ['', '| Load | Reconstruction gain | Mean body success | Final body success | Every boundary successful |',
        '| --- | ---: | ---: | ---: | ---: |']
    for row in paths:
        if row['arm'] == 'renewal':
            lines.append(f"| {row['load']} | {row['reconstruction_gain']} | {row['mean_boundary_success']:.4%} | "
                f"{row['final_body_success']:.4%} | {row['all_boundaries_success']:.4%} |")
    lines += ['', 'All arm/load/checkpoint/network outcomes, paired effects, copying gaps, body and path results are retained in CSV/JSON.',
        'The fixed 88-network plan targets marginal five-point precision using inflated development variability; attained widths are reported and never change the sample size.',
        'Directional bounds use a 12-contrast Bonferroni family and 100,000 joint whole-network bootstrap draws. Percentile inference is approximate; observed zero control rates do not prove zero population risk.',
        'Supplied apparatus guidance, learned record content and protected copying remain distinct. No superiority to copying, evolved machinery or RDT predictive advantage is claimed.',
        'No private material, manuscript edit or public release. Earlier verdicts remain unchanged.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    plot(out, lookup, inference, classification)
    return summary


def plot(out, lookup, inference, classification):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for b in (4, 8):
        for r in (4, 8):
            values = [lookup[(g, 'both', 'renewal', b, r)]['joint'] for g in base.CHECKPOINTS]
            axes[0].plot(base.CHECKPOINTS, values, marker='o', label=f'reconstruct {b}, assay {r}')
    axes[0].set(xlabel='Completed replacements', ylabel='Both-rule success in fresh recipients',
        xticks=base.CHECKPOINTS, ylim=(0, 1.03))
    axes[0].legend(fontsize=8)
    stats = [inference['estimates'][f'g16_{b}_{r}'] for b in (4, 8) for r in (4, 8)]
    axes[1].bar(np.arange(4), [x['mean'] for x in stats], color=['#607d8b', '#e49c39', '#459c66', '#b55454'])
    if stats[0]['low'] is not None:
        for i, row in enumerate(stats):
            axes[1].plot([i, i], [row['low'], row['high']], color='black')
            axes[1].plot([i-.06, i+.06], [row['low']]*2, color='black')
            axes[1].plot([i-.06, i+.06], [row['high']]*2, color='black')
    axes[1].set(xticks=np.arange(4), xticklabels=['4 / 4', '4 / 8', '8 / 4', '8 / 8'],
        xlabel='Reconstruction gain / assay gain', ylabel='Generation-16 joint success', ylim=(0, 1.03))
    axes[1].set_title('Marginal 95% network intervals' if stats[0]['low'] is not None else 'Engineering replay')
    for ax in axes:
        ax.grid(axis='y', alpha=.2)
    fig.suptitle(f"H039: {inference['networks']} networks ({classification.lower()})", fontsize=10)
    fig.tight_layout(); fig.savefig(out/'overview.png', dpi=160); fig.savefig(out/'overview.pdf'); plt.close(fig)
