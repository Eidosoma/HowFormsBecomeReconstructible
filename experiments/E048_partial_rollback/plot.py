"""Audited next-body outcomes and paired changes."""
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
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    labels = ['Unchanged', 'Half rollback', 'Full rollback']
    for i, v in enumerate(s['variants']):
        st = s['groups'][v]['both_cues']
        if st['mean'] is None: continue
        y, lo, hi = 100*np.array([st['mean'], *st['ci95']])
        axes[0].errorbar(y, i, xerr=np.maximum(0, [[y-lo], [hi-y]]), fmt='o', capsize=4, color='#008c87')
    axes[0].set(yticks=range(3), yticklabels=labels, xlim=(-3, 103), xlabel='Next body: both cues correct (%)')
    axes[0].invert_yaxis()
    for i, low in enumerate(('original', 'full_rollback', 'loss_reduction')):
        st = s['primary'][low]
        if st['mean'] is None: continue
        y, lo, hi = 100*np.array([st['mean'], *st['ci95']])
        axes[1].errorbar(y, i, xerr=np.maximum(0, [[y-lo], [hi-y]]), fmt='o', capsize=4, color='#8456a3')
    axes[1].axvline(0, color='black', lw=.8)
    axes[1].axvline(5, color='gray', ls=':', lw=.8)
    axes[1].set(yticks=range(3), yticklabels=['Half − unchanged', 'Half − full', 'Fewer losses with half'],
        xlabel='Percentage points, all eligible cases', ylim=(-.5, 2.5))
    axes[1].invert_yaxis()
    for ax in axes:
        ax.grid(axis='x', alpha=.2); ax.spines[['top', 'right']].set_visible(False)
    title = 'EXCLUDED TECHNICAL RUN' if s['mode'] != 'scientific' else f"{s['cohort']['eligible']} first failures with a next body"
    fig.suptitle('E048 · Half rollback after first failure\n'+title)
    fig.text(.5, .035, 'Pointwise whole-block 95% intervals. Existing selected cases; one subsequent body only.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .08, 1, .9))
    for ext in ('png', 'svg'): fig.savefig(dest/f'partial_rollback.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(summary_sha256=sha(run/'summary.json'), complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__ == '__main__': main()
