"""Native/common terminal success and numerical exposure, with provenance."""
import argparse
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import dump, sha, utc
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(run):
    s = json.loads((run / 'summary.json').read_text()); a = json.loads((run / 'INDEPENDENT_AUDIT.json').read_text())
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(run / 'COMPLETE.json')
    dest = HERE / 'figures' / run.name; dest.mkdir(parents=True, exist_ok=False)
    stats = s['statistics']; names = [r['id'] for r in s['regimes']]
    labels = ['Reference', 'Grid', 'Record noise', 'Floor', 'Grid + noise',
              'Grid + floor', 'Noise + floor', 'Grid + noise + floor', 'Arithmetic f32', 'All four']
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout='constrained')
    for row, (pairing, rho) in enumerate(s['pairings']):
        for offset, reader, color in ((-.08, 'native', '#0072B2'), (.08, 'common', '#D55E00')):
            x = np.arange(len(names)) + offset
            values = [stats[f'assay/32/{pairing}/{name}/{reader}/scattered'] for name in names]
            y = np.array([v['mean'] for v in values])*100
            low = np.array([v['ci95'][0] for v in values])*100; high = np.array([v['ci95'][1] for v in values])*100
            axes[row, 0].errorbar(x, y, yerr=np.maximum(0, np.vstack((y-low, high-y))), color=color, marker='o', ms=3, label=reader, capsize=2)
        axes[row, 0].set_title(f'Final success; rebuilding noise correlation {rho:g}')
        axes[row, 0].axhline(75, color='black', ls=':', lw=.8); axes[row, 0].set_ylim(-4, 104)
        for metric, color, label in (('floored_fraction', '#009E73', 'Live cells below floor'),
                                     ('channel_lost_fraction', '#CC79A7', 'Nonzero values lost in channel')):
            values = [stats[f'mechanism/{pairing}/{name}/{metric}']['mean']*100 for name in names]
            axes[row, 1].plot(range(len(names)), values, marker='o', ms=3, color=color, label=label)
        axes[row, 1].set_title(f'Numerical exposure; rebuilding noise correlation {rho:g}')
        axes[row, 1].set_ylim(-4, 104)
        for ax in axes[row]:
            ax.set_xticks(range(len(names)), labels, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel('Percent'); ax.grid(axis='y', alpha=.2)
    axes[0, 0].legend(fontsize=8); axes[0, 1].legend(fontsize=8)
    title = 'E053: fresh confirmation under combined numerical stresses'
    if s['mode'] != 'scientific': title += ' — EXCLUDED TECHNICAL RUN'
    fig.suptitle(title); fig.savefig(dest / 'numerical_robustness.png', dpi=150)
    fig.savefig(dest / 'numerical_robustness.svg'); plt.close(fig)
    dump(dest / 'provenance.json', dict(utc=utc(), summary_sha256=sha(run / 'summary.json'),
        audit_sha256=sha(run / 'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name: sha(p) for p in dest.glob('numerical_robustness.*')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); main(p.parse_args().run.resolve())
