"""Audited recovery over three bodies and fixed third-body primary comparisons."""
import argparse
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import cap_cpus, dump, sha
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); run = p.parse_args().run.resolve(); cap_cpus(8)
    a = json.loads((run/'INDEPENDENT_AUDIT.json').read_text()); s = json.loads((run/'summary.json').read_text())
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(run/'COMPLETE.json')
    dest = HERE/'figures'/run.name; dest.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = ['Unchanged', 'Half rollback', 'Full rollback']; colors = ['#60656a', '#008c87', '#b97828']
    for i, v in enumerate(s['variants']):
        stats = [s['groups'][str(d)][v]['both_cues'] for d in (1, 2, 3)]
        if any(st['mean'] is None for st in stats): continue
        values = 100*np.array([[st['mean'], *st['ci95']] for st in stats])
        y, lo, hi = values.T
        axes[0].errorbar(np.arange(1, 4)+(i-1)*.055, y, yerr=np.maximum(0, [y-lo, hi-y]),
            fmt='o-', capsize=4, color=colors[i], label=labels[i])
    axes[0].set(xticks=[1, 2, 3], xlim=(.75, 3.25), ylim=(-3, 103),
        xlabel='Body after first failure', ylabel='Both cues correct (%)')
    axes[0].legend(fontsize=9, loc='best'); axes[0].grid(axis='y', alpha=.2)
    for i, key in enumerate(('original', 'full_rollback', 'loss_reduction')):
        st = s['primary'][key]
        if st['mean'] is None: continue
        y, lo, hi = 100*np.array([st['mean'], *st['ci95']])
        axes[1].errorbar(y, i, xerr=np.maximum(0, [[y-lo], [hi-y]]), fmt='o', capsize=4, color='#8456a3')
        axes[1].plot(5 if i == 0 else 0, i, '|', color='black', ms=20, mew=1.2)
    axes[1].axvline(0, color='gray', lw=.7)
    axes[1].set(yticks=range(3), yticklabels=['Half − unchanged', 'Half − full', 'Fewer losses with half'],
        xlabel='Third body: percentage points, all eligible cases', ylim=(-.5, 2.5))
    axes[1].invert_yaxis(); axes[1].grid(axis='x', alpha=.2)
    for ax in axes: ax.spines[['top', 'right']].set_visible(False)
    title = 'EXCLUDED TECHNICAL RUN' if s['mode'] != 'scientific' else f"{s['cohort']['eligible']} first failures with three later bodies"
    fig.suptitle('E049 · Persistence after one rollback\n'+title)
    fig.text(.5, .035, 'Pointwise whole-block 95% intervals. Black ticks mark primary lower-bound requirements. Existing selected cases.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .08, 1, .9))
    for ext in ('png', 'svg'): fig.savefig(dest/f'persistence.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(summary_sha256=sha(run/'summary.json'), complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__ == '__main__': main()
