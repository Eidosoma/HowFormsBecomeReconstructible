#!/usr/bin/env python3
"""Plot E041 terminal estimates with E046 history context; no new inference."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'paper_assets/data/forms-cellular-v0.14.json'
HISTORY = ROOT / 'paper_assets/data/functional-renewal-history-v1.json'
DEST = ROOT / 'paper_assets/figures'
INK, TEAL, AMBER, MUTED = '#123b49', '#087f8c', '#bf740e', '#54636b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'none', 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.edgecolor': '#b9c6cb',
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': INK})


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    data = json.loads(DATA.read_text())['e041']
    history = json.loads(HISTORY.read_text())
    vals = {(r['policy'], r['generation']): r for r in data['values']
            if r['terminal_injury'] == 'scattered24'}
    policies = [
        ('bridge_rewrite', 'Full repair-supporting rewrite', TEAL, '-'),
        ('bridge_preserve', 'Same writer, preserve strong', AMBER, '-'),
        ('standard_rewrite', 'Ordinary coactivity rewrite', '#855a92', '-'),
        ('masked_copy', 'Copy with matched erasures', '#7c8793', '--'),
        ('protected_copy', 'Protected exact copy', '#233e50', ':'),
    ]
    horizons = [1, 3, 8, 16, 24, 32]
    fig = plt.figure(figsize=(12.8, 7.2))
    fig.text(.045, .94, 'Reconstructible function after 32 damaged rebuilds',
             fontsize=19, weight='bold')
    fig.text(.045, .89, 'E041 terminal assays and E046 body histories  |  same 512 lineages in 32 independent blocks',
             fontsize=11.5, color=MUTED)
    ax = fig.add_axes([.085, .30, .47, .50])
    ax.set_title('A   Fresh-recipient success at tested horizons', loc='left', fontsize=12, weight='bold', pad=14)
    for policy, label, color, style in policies:
        y = [vals[policy, h]['both_cues_percent'] for h in horizons]
        ax.plot(horizons, y, color=color, linestyle=style, marker='o',
                ms=4.5, lw=2.3 if policy == 'bridge_rewrite' else 1.8, label=label)
    ax.fill_between(horizons, [vals['bridge_rewrite', h]['ci95_low'] for h in horizons],
                    [vals['bridge_rewrite', h]['ci95_high'] for h in horizons],
                    color=TEAL, alpha=.13, linewidth=0)
    ax.set_xlim(0, 33); ax.set_ylim(-3, 106)
    ax.set_xticks(horizons); ax.set_yticks([0, 25, 50, 75, 100])
    ax.grid(axis='y', color='#e7edef', zorder=0)
    ax.set_xlabel('Damaged rebuilds in the lineage', labelpad=9)
    ax.set_ylabel('Fresh recipients passing both cues (%)', labelpad=8)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.19), frameon=False,
              fontsize=9.5, ncol=2, columnspacing=1.7, handlelength=2.8)

    right = fig.add_axes([.795, .30, .17, .50])
    right.set_title('B   Fresh recipients after rebuild 32', loc='right', fontsize=12, weight='bold', pad=14)
    short = ['Full repair-supporting\nrewrite', 'Same writer,\npreserve strong',
             'Ordinary coactivity\nrewrite', 'Copy with\nmatched erasures',
             'Protected\nexact copy']
    for i, ((policy, label, color, style), display) in enumerate(zip(policies, short)):
        y = 4-i; row = vals[policy, 32]; mean = row['both_cues_percent']
        right.errorbar(mean, y, xerr=[[mean-row['ci95_low']], [row['ci95_high']-mean]],
                       fmt='o', ms=6, lw=2, capsize=4, color=color)
        right.text(-8, y, display, ha='right', va='center', fontsize=9.5, color=INK)
        right.text(mean, y+.29, f'{mean:.2f}%', ha='center', fontsize=10, weight='bold', color=color)
    right.set_xlim(-2, 108); right.set_ylim(-.55, 4.7)
    right.set_yticks([]); right.set_xticks([0, 50, 100])
    right.spines['left'].set_visible(False)
    right.grid(axis='x', color='#e7edef')
    right.set_xlabel('Both cues correct (%)', labelpad=9)
    fig.text(.605, .211, 'Primary full-rewrite gain: +10.94 points', fontsize=11, weight='bold')
    fig.text(.605, .179, '95% interval [6.84, 15.23]; 17 horizon-based criteria pass.', fontsize=9.5)
    fig.text(.605, .133,
             f"Full rewrite: {history['all_body_readouts_passed']}/{history['lineages']} "
             f"({history['all_body_readouts_passed_percent']:.2f}%) pass all 32 body readouts",
             fontsize=10, weight='bold')
    fig.text(.605, .105,
             f"{history['ever_body_failure']}/{history['lineages']} had at least one failed body "
             '(E046; descriptive).', fontsize=9.3, color=MUTED)
    fig.text(.045, .064, 'Every renewing body loses 24 cells. Fresh terminal readers also receive a scattered 24-cell injury.',
             fontsize=10.5)
    fig.text(.045, .030, 'Intervals are the saved pointwise 95% block-bootstrap estimates. Task and reconstruction machinery are supplied.',
             fontsize=9.5, color=MUTED)
    outputs = []
    for ext in ('png', 'svg'):
        p = DEST / f'data-functional-renewal-v2.{ext}'
        fig.savefig(p, dpi=240, facecolor='white', metadata={'Creator': 'Matplotlib'})
        outputs.append({'path': str(p.relative_to(ROOT)), 'sha256': sha(p)})
    plt.close(fig)
    record = {'figure_id': 'fig-functional-renewal', 'kind': 'reported-estimates',
              'png': 'data-functional-renewal-v2.png',
              'data': str(DATA.relative_to(ROOT)), 'data_sha256': sha(DATA),
              'plot_script': str(Path(__file__).relative_to(ROOT)), 'plot_script_sha256': sha(Path(__file__)),
              'source_report': data['source'], 'source_report_sha256': data['source_sha256'],
              'history_context': str(HISTORY.relative_to(ROOT)), 'history_context_sha256': sha(HISTORY),
              'history_source_report': history['source_report'],
              'history_source_report_sha256': history['source_report_sha256'],
              'history_scope': history['scope'],
              'selection': 'All six post-acquisition assay horizons for five named E041 policies, same cohort; terminal scattered injury.',
              'outputs': outputs, 'statistics_recomputed': False, 'new_trajectories': False,
              'intervals': data['intervals']}
    (DEST / 'functional-renewal-assets-v0.14.json').write_text(json.dumps(record, indent=2)+'\n')
    print('Rendered E041 comparison as PNG/SVG with provenance.')


if __name__ == '__main__':
    main()
