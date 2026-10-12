"""Audited same-body capture/copying comparison; technical runs marked excluded."""
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
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path)
    r = p.parse_args().run.resolve(); cap_cpus(8)
    a = json.loads((r/'INDEPENDENT_AUDIT.json').read_text())
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(r/'COMPLETE.json')
    s = json.loads((r/'summary.json').read_text())
    dest = HERE/'figures'/r.name; dest.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.6), sharex=True, sharey=True)
    labels = ['Standard / preserve strong', 'Standard / rewrite all',
              'Cue contrast / preserve strong', 'Cue contrast / rewrite all',
              'Matched strength / preserve strong', 'Matched strength / rewrite all']
    for ax, injury in zip(axes, s['damage']):
        for i, condition in enumerate(s['conditions']):
            for reader, offset, color in (('fixed_four', -.12, '#888888'), ('local_strength', .12, '#008c87')):
                st = s['groups'][reader][condition]['both_cues'][injury]['own']
                v, lo, hi = [100*z for z in (st['mean'], *st['ci95'])]
                ax.errorbar(v, i+offset, xerr=np.maximum(0, [[v-lo], [hi-v]]), fmt='o', color=color,
                            capsize=3, label=reader if i == 0 else None)
        ax.axvline(75, ls=':', color='black', lw=.8)
        ax.set(title=injury.capitalize()+' terminal test', xlim=(-3, 103), xlabel='Both cues correct (%)')
        ax.grid(axis='x', alpha=.2); ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_yticks(range(6), labels); axes[0].invert_yaxis()
    handles, _ = axes[0].get_legend_handles_labels()
    fig.legend(handles, ['Fixed-four receiver', 'Normalized receiver'], loc='lower center', ncol=2, frameon=False)
    title = 'EXCLUDED TECHNICAL RUN' if s['mode'] != 'scientific' else '512 existing lineages; one generation-nine record'
    fig.suptitle('E035: capture content and copying strong weights · '+title)
    fig.text(.5, .09, 'Same rebuilt bodies and terminal timing. Pointwise whole-block 95% intervals; no new serial history.', ha='center', fontsize=9)
    fig.tight_layout(rect=(.02, .14, 1, .92))
    for ext in ('png', 'svg'): fig.savefig(dest/f'capture.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(summary_sha256=sha(r/'summary.json'), complete_sha256=sha(r/'COMPLETE.json'),
        audit_sha256=sha(r/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__ == '__main__':
    main()
