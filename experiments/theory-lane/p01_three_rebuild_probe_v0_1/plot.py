"""Standalone research figure; numerical results are read from the completed run."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
report = json.loads((ROOT/'results/analysis.json').read_text())
models = report['models']
pairs = [
    ('Generation 1 · additive context', 'g1_additive_expression', 'g1_additive_mechanistic', 'g1_feature_addition_reference'),
    ('Generation 3 · additive context', 'g3_additive_expression', 'g3_additive_mechanistic', 'g3_feature_addition'),
    ('Generation 3 · joint context', 'g3_joint_expression', 'g3_joint_mechanistic', 'g3_feature_addition_joint'),
    ('Generations 1–3 · joint context', 'history_joint_expression', 'history_joint_mechanistic', 'history_feature_addition')]
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
fig, (left, right) = plt.subplots(1, 2, figsize=(12.8, 5.4), gridspec_kw={'width_ratios': [1.2, 1]})
colors = ['#246b9b', '#b75f16']
for row, (label, base, extra, comparison) in enumerate(pairs):
    scores = [models[n]['mean_block_brier'] for n in (base, extra)]
    left.plot(scores, [row, row], color='#aeb6bd', lw=2, zorder=1)
    for j, score in enumerate(scores):
        left.scatter([score], [row], color=colors[j], s=55, zorder=3,
                     label=['Expression + context', '+ mechanistic features'][j] if row == 0 else None)
        left.annotate(f'{score:.5f}', (score, row), xytext=(0, 11 if j == 0 else -19),
                      textcoords='offset points', ha='center', color=colors[j], fontsize=9)
    comparison_row = next(r for r in report['comparisons'] if r['id'] == comparison)
    gains = [1000*r['brier_improvement'] for r in comparison_row['folds']]
    right.scatter(gains, row+np.linspace(-.16, .16, 8), color=colors[1], s=28, alpha=.8)
    right.scatter([np.mean(gains)], [row], color='#20252a', marker='D', s=31, zorder=4)
reference = models['condition_rate']['mean_block_brier']
left.axvline(reference, color='#405d40', ls='--', lw=1.5, label=f'Condition only: {reference:.5f}')
left.set_yticks(range(4), [p[0] for p in pairs])
left.set_xlim(.0598, .0667)
left.set_xlabel('Mean held-out Brier error (lower is better)')
left.set_title('Terminal forecast error', loc='left', pad=16, fontsize=12)
left.legend(loc='lower left', bbox_to_anchor=(-.01, 1.13), frameon=False, fontsize=9)
right.axvline(0, color='#59636b', lw=1)
right.set_yticks(range(4), [])
right.set_xlim(-9.2, 2)
right.set_xlabel('Brier improvement × 1,000\nNegative values mean added features worsened the forecast')
right.set_title('Each held-out block; diamonds show means', loc='left', pad=16, fontsize=12)
for ax in (left, right):
    ax.set_ylim(3.6, -.6)
    ax.grid(axis='x', alpha=.17)
fig.suptitle('The declared three-rebuild probe fails its terminal forecast check',
             fontsize=15, x=.03, y=.975, ha='left')
fig.text(.03, .02, 'Generation-32 scattered assay · 1,024 lineage-condition records · 8 exposed blocks · development analysis',
         fontsize=10, color='#434b51')
fig.subplots_adjust(left=.25, right=.985, top=.73, bottom=.2, wspace=.24)
for suffix in ('png', 'svg', 'pdf'):
    destination = ROOT/'results'/f'three_rebuild_forecast.{suffix}'
    if destination.exists():
        raise FileExistsError(destination)
    fig.savefig(destination, dpi=190, facecolor='white')
print('Saved three_rebuild_forecast.png, .svg and .pdf.')
