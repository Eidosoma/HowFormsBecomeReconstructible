"""Audited serial performance under the common normalized terminal reader."""
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
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); r = p.parse_args().run.resolve(); cap_cpus(8)
    a = json.loads((r/'INDEPENDENT_AUDIT.json').read_text())
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(r/'COMPLETE.json')
    s = json.loads((r/'summary.json').read_text()); dest = HERE/'figures'/r.name; dest.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 6), sharex=True, sharey=True)
    horizons = [0, 1, 3, 8, 16, 24, 32]
    labels = ['Standard / preserve', 'Standard / rewrite', 'Weak bridge / preserve', 'Weak bridge / rewrite',
              'Pure cue contrast / preserve', 'Weak bridge, reading blocked', 'Weak bridge, writing blocked',
              'Protected copy', 'Cumulative damaged copy']
    colors = ['#2457a7', '#839aba', '#ed9f22', '#ca442c', '#683f96', '#cccccc', '#999999', '#288b69', '#775344']
    for ax, injury in zip(axes, s['damage']):
        for i, name in enumerate(s['conditions']):
            points = [s['groups'][str(h)]['local_strength']['initial' if h == 0 else name]['both_cues'][injury]['own'] for h in horizons]
            means = np.array([100*st['mean'] for st in points]); intervals = np.array([np.array(st['ci95'])*100 for st in points])
            ax.errorbar(horizons, means, yerr=np.maximum(0, np.array([means-intervals[:, 0], intervals[:, 1]-means])),
                color=colors[i], label=labels[i], marker='o', ms=3, lw=1.8 if i == 2 else 1.0,
                ls='-' if i < 4 else '--', capsize=2, alpha=1 if i < 5 else .65)
        ax.axhline(75, ls=':', color='black', lw=.8)
        ax.set(title=injury.capitalize()+' terminal test', ylim=(-3, 103), xticks=[0, 8, 16, 24, 32], xlabel='Damaged replacements')
        ax.grid(alpha=.15); ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_ylabel('Both cues correct (%)')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=3, frameon=False, fontsize=8)
    scope = 'EXCLUDED TECHNICAL RUN' if s['mode'] != 'scientific' else '512 fresh lineages; thirty-two renewals'
    fig.suptitle('E040: weak repair through 32 damaged renewals · '+scope)
    fig.text(.5, .19, 'Common delayed normalized receiving. Pointwise whole-block 95% intervals; independent policy histories.', ha='center', fontsize=9)
    fig.tight_layout(rect=(.01, .22, 1, .92))
    for ext in ('png', 'svg'): fig.savefig(dest/f'serial_capture.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(summary_sha256=sha(r/'summary.json'), complete_sha256=sha(r/'COMPLETE.json'),
        audit_sha256=sha(r/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__ == '__main__': main()
